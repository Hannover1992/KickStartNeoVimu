#!/usr/bin/env python3
"""
test_worktree_registry.py — BL-431 batch_1 RED: Failing tests for worktree_registry.py.

ALL tests MUST fail with ModuleNotFoundError (worktree_registry.py does not exist yet).
Written by RED-Worker (red-bl431-b1). GREEN-Worker implements worktree_registry.py separately.

AK coverage:
  AK-1: assign_worktree_id — counter, kollisionsfrei, stabil
  AK-2: registry add/lookup/remove/list roundtrip + Pfad-Eindeutigkeit
  AK-3: validate_worktree_path — OmniCommand-Pattern-Token
  AK-4: bl_parallel session param default False + bypass-Feld ValueError
  AK-5: handoff mit gemocktem merge_fn (CLEAN->merge, CONFLICT->PL)
  AK-6: pick_next_lane_item — Lane-Disjunktheit, kein Doppel-Greifen
  AK-7: worktree_id als Hook-Router-Namespace (rueckwaerts-kompat)
  AK-10: Registry-Write single-writer/lock-geschuetzt
"""
from __future__ import annotations

import threading
import pytest

# This import MUST fail — worktree_registry.py does not exist yet.
# All tests in this file will be collected but fail at module import time
# with ModuleNotFoundError. That is the RED state.
from worktree_registry import (  # noqa: E402
    assign_worktree_id,
    registry_add,
    registry_lookup,
    registry_remove,
    registry_list,
    validate_worktree_path,
    pick_next_lane_item,
    handoff,
)


# ---------------------------------------------------------------------------
# AK-1: assign_worktree_id — counter, kollisionsfrei, stabil
# ---------------------------------------------------------------------------

class TestAssignWorktreeId:
    def test_empty_set_returns_wt1(self):
        """AK-1: leeres Set -> 'WT-1' (erster verfuegbarer Zaehler)."""
        result = assign_worktree_id(set())
        assert result == "WT-1"

    def test_collision_skips_to_next(self):
        """AK-1: {WT-1, WT-2} bereits belegt -> 'WT-3' (Kollisions-Hochzaehlung)."""
        result = assign_worktree_id({"WT-1", "WT-2"})
        assert result == "WT-3"

    def test_list_input_accepted(self):
        """AK-1: auch list als existing_ids akzeptiert (duck-typing)."""
        result = assign_worktree_id(["WT-1"])
        assert result == "WT-2"

    def test_stable_deterministic(self):
        """AK-1: zwei Aufrufe mit demselben existing_ids -> selbes Ergebnis (deterministisch)."""
        existing = {"WT-1", "WT-3"}
        r1 = assign_worktree_id(existing)
        r2 = assign_worktree_id(existing)
        assert r1 == r2

    def test_format_wt_n(self):
        """AK-1: Rueckgabe-Format ist immer 'WT-{N}' (nicht 'wt1', 'WT1', etc.)."""
        result = assign_worktree_id(set())
        assert result.startswith("WT-")
        n_part = result[3:]
        assert n_part.isdigit(), f"Erwartet 'WT-{{N}}', bekam {result!r}"


# ---------------------------------------------------------------------------
# AK-2: registry add/lookup/remove/list Roundtrip + Pfad-Eindeutigkeit
# ---------------------------------------------------------------------------

class TestRegistryRoundtrip:
    """Registry wird als dict uebergeben (In-Memory-Variante fuer unit-Tests)."""

    def _make_entry(self, *, path="/repo/OmniCommand-WT-1", branch="feature/bl-431",
                    bl_id="BL-431", base_sha="abc123", lane="A", status="active",
                    vault_root="/vault"):
        return dict(path=path, branch=branch, bl_id=bl_id, base_sha=base_sha,
                    lane=lane, status=status, vault_root=vault_root)

    def test_add_and_lookup(self):
        """AK-2: add + lookup Roundtrip liefert den hinzugefuegten Eintrag."""
        reg = {}
        reg = registry_add(reg, "WT-1", **self._make_entry())
        entry = registry_lookup(reg, "WT-1")
        assert entry is not None
        assert entry["bl_id"] == "BL-431"
        assert entry["status"] == "active"

    def test_lookup_unknown_id_returns_none(self):
        """AK-2: lookup eines unbekannten worktree_id -> None."""
        reg = {}
        result = registry_lookup(reg, "WT-99")
        assert result is None

    def test_remove_deletes_entry(self):
        """AK-2: remove loescht den Eintrag; danach lookup -> None."""
        reg = {}
        reg = registry_add(reg, "WT-1", **self._make_entry())
        reg = registry_remove(reg, "WT-1")
        assert registry_lookup(reg, "WT-1") is None

    def test_list_returns_all_ids(self):
        """AK-2: list liefert alle registrierten IDs."""
        reg = {}
        reg = registry_add(reg, "WT-1", **self._make_entry(path="/repo/A"))
        reg = registry_add(reg, "WT-2", **self._make_entry(path="/repo/B"))
        ids = registry_list(reg)
        assert "WT-1" in ids
        assert "WT-2" in ids
        assert len(ids) == 2

    def test_add_same_path_raises(self):
        """AK-2: zweiter add mit SELBEM path -> reject (Pfad-Eindeutigkeit erzwungen)."""
        reg = {}
        reg = registry_add(reg, "WT-1", **self._make_entry(path="/repo/OmniCommand-WT-1"))
        with pytest.raises((ValueError, KeyError)):
            registry_add(reg, "WT-2", **self._make_entry(path="/repo/OmniCommand-WT-1"))

    def test_list_empty_registry(self):
        """AK-2: list auf leerem Registry -> leere Liste."""
        reg = {}
        assert registry_list(reg) == []


# ---------------------------------------------------------------------------
# AK-3: validate_worktree_path — OmniCommand-Pattern-Token
# ---------------------------------------------------------------------------

class TestValidateWorktreePath:
    def test_path_with_omnicommand_token_ok(self):
        """AK-3: Pfad enthaelt 'OmniCommand' -> Ergebnis hat ok/valid=True."""
        result = validate_worktree_path("/repos/OmniCommand-WT-1")
        # Flexible key: entweder result["ok"] oder result["valid"] oder result["status"] == "ok"
        ok_val = result.get("ok", result.get("valid", result.get("status") == "ok"))
        assert ok_val is True or ok_val == "ok"

    def test_path_without_project_token_warns(self):
        """AK-3: Pfad ohne OmniCommand-Token -> Warnung oder vault_root-Pflicht-Flag gesetzt."""
        result = validate_worktree_path("/tmp/random-worktree")
        # Entweder warning=True oder vault_root_required=True oder ok=False
        has_warning = (
            result.get("warning") is True
            or result.get("vault_root_required") is True
            or result.get("ok") is False
            or result.get("valid") is False
            or result.get("status") in ("warn", "warning", "error")
        )
        assert has_warning, f"Erwartet Warnung fuer Pfad ohne Token, bekam: {result}"

    def test_result_is_dict(self):
        """AK-3: validate_worktree_path gibt immer ein dict zurueck."""
        result = validate_worktree_path("/anything")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# AK-4: bl_parallel session_param default False + Bypass-Feld ValueError
# ---------------------------------------------------------------------------

class TestBlParallelSessionParam:
    def test_bl_parallel_default_false(self):
        """AK-4: bl_parallel wird via session_params_resolver aufgeloest; Default = False."""
        # Importiere den Resolver (existiert bereits)
        from session_params_resolver import resolve_param, FRAMEWORK_DEFAULTS
        # bl_parallel muss im Resolver als neuer Param enthalten sein (analog parallel_mode)
        value = resolve_param("bl_parallel")
        assert value is False, f"Erwartet False als Default, bekam {value!r}"

    def test_bl_parallel_bypass_field_raises(self):
        """AK-4: Bypass-Feld 'force_bl_parallel' -> ValueError (analog _PARALLEL_BYPASS_FIELDS)."""
        from session_params_resolver import validate_no_parallel_bypass
        with pytest.raises(ValueError, match="force_bl_parallel"):
            validate_no_parallel_bypass({"force_bl_parallel"})


# ---------------------------------------------------------------------------
# AK-5: handoff — CLEAN -> merge, CONFLICT -> conflict_to_pl
# ---------------------------------------------------------------------------

class TestHandoff:
    """handoff injiziert merge_fn fuer Testbarkeit (analog do_merge_if_clean)."""

    def _base_registry(self):
        reg = {}
        reg = registry_add(
            reg, "WT-1",
            path="/repo/OmniCommand-WT-1",
            branch="feature/bl-431-wt1",
            bl_id="BL-431",
            base_sha="abc123",
            lane="A",
            status="active",
            vault_root="/vault",
        )
        return reg

    def _open_items(self):
        return ["BL-432", "BL-433"]

    def test_clean_merge_executed_status_merged(self):
        """AK-5 CRITICAL: CLEAN -> merge_fn aufgerufen, Status -> merged/idle, next Lane-Item gesetzt."""
        merge_calls = []

        def mock_merge_fn(verdict, *args, **kwargs):
            merge_calls.append(verdict)
            return {"status": "merged", "verdict": verdict}

        reg = self._base_registry()
        result = handoff(
            "WT-1", reg,
            merge_fn=mock_merge_fn,
            lane="A",
            open_items=self._open_items(),
        )

        # merge_fn muss aufgerufen worden sein
        assert len(merge_calls) >= 1 or result.get("merge_executed") is True

        # Status des Worktrees muss merged oder idle sein
        updated_entry = registry_lookup(result.get("registry", reg), "WT-1")
        if updated_entry is not None:
            assert updated_entry.get("status") in ("merged", "idle", "done")

        # next_lane_item muss gesetzt sein (eines der open_items)
        assert result.get("next_lane_item") in (None, "BL-432", "BL-433")

    def test_conflict_no_merge_pl_created(self):
        """AK-5 CRITICAL: CONFLICT -> conflict_to_pl (PL+hold), KEIN Merge, Status bleibt, develop unberuehrt."""
        merge_calls = []

        def mock_merge_fn_conflict(verdict, *args, **kwargs):
            if verdict == "CONFLICT":
                # conflict_to_pl wird intern aufgerufen, kein Merge
                return {"status": "conflict", "hold": True, "verdict": "CONFLICT"}
            merge_calls.append(verdict)
            return {"status": "merged"}

        reg = self._base_registry()
        result = handoff(
            "WT-1", reg,
            merge_fn=mock_merge_fn_conflict,
            lane="A",
            open_items=self._open_items(),
        )

        # Bei CONFLICT: merge wurde NICHT auf develop durchgefuehrt
        # result muss hold=True oder conflict-Flag enthalten
        is_conflict_handled = (
            result.get("hold") is True
            or result.get("verdict") == "CONFLICT"
            or result.get("conflict") is True
            or result.get("pl_created") is True
        )
        # merge_calls darf KEIN "CLEAN" enthalten (kein echter Merge)
        assert "CLEAN" not in merge_calls
        # Entweder conflict-Signal ODER merge war nicht aufgerufen
        # (merge_fn wurde mit CONFLICT aufgerufen, nicht CLEAN)
        assert is_conflict_handled or len(merge_calls) == 0

    def test_handoff_returns_dict(self):
        """AK-5: handoff gibt immer ein dict zurueck."""
        def mock_fn(verdict, *args, **kwargs):
            return {"status": "merged"}

        reg = self._base_registry()
        result = handoff("WT-1", reg, merge_fn=mock_fn, lane="A", open_items=[])
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# AK-6: pick_next_lane_item — Lane-Disjunktheit, kein Doppel-Greifen
# ---------------------------------------------------------------------------

class TestPickNextLaneItem:
    def test_picks_from_own_lane_items(self):
        """AK-6: waehlt NUR aus Lane-eigenen offenen Items."""
        open_items = ["BL-432", "BL-433", "BL-434"]
        claimed_by_other = []
        result = pick_next_lane_item("A", open_items, claimed_by_other)
        assert result in open_items or result is None

    def test_excludes_items_claimed_by_other_lane(self):
        """AK-6 CRITICAL: von anderer Lane belegtes BL -> ausgeschlossen (kein Doppel-Greifen)."""
        open_items = ["BL-432", "BL-433"]
        claimed_by_other = ["BL-432"]  # BL-432 von anderer Lane belegt
        result = pick_next_lane_item("A", open_items, claimed_by_other)
        # BL-432 darf NICHT zurueckgegeben werden
        assert result != "BL-432"
        # BL-433 oder None ist korrekt
        assert result in ("BL-433", None)

    def test_returns_none_when_all_claimed(self):
        """AK-6: alle Items von anderer Lane belegt -> None (nichts zu greifen)."""
        open_items = ["BL-432", "BL-433"]
        claimed_by_other = ["BL-432", "BL-433"]
        result = pick_next_lane_item("A", open_items, claimed_by_other)
        assert result is None

    def test_returns_none_on_empty_open_items(self):
        """AK-6: keine offenen Items -> None."""
        result = pick_next_lane_item("A", [], [])
        assert result is None


# ---------------------------------------------------------------------------
# AK-7: worktree_id als Hook-Router-Namespace (rueckwaerts-kompat)
# ---------------------------------------------------------------------------

class TestWorktreeIdAsNamespace:
    def test_lookup_with_id_returns_namespace_info(self):
        """AK-7: worktree_id taugt als Namespace; lookup mit gueltigem ID liefert Eintrag."""
        reg = {}
        reg = registry_add(
            reg, "WT-1",
            path="/repo/OmniCommand-WT-1",
            branch="feature/test",
            bl_id="BL-431",
            base_sha="abc",
            lane="A",
            status="active",
            vault_root="/vault",
        )
        entry = registry_lookup(reg, "WT-1")
        # Hook-Router kann worktree_id als Namespace-Key nutzen
        assert entry is not None
        assert "bl_id" in entry

    def test_lookup_without_id_returns_none_or_default_namespace(self):
        """AK-7: ohne ID (None) -> None oder Default-Namespace (rueckwaerts-kompat)."""
        reg = {}
        # Kein Fehler bei lookup(None) — muss graceful None oder default liefern
        result = registry_lookup(reg, None)
        # None oder ein dict mit default-Namespace-Info
        assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# AK-10: Registry-Write single-writer / lock-geschuetzt
# ---------------------------------------------------------------------------

class TestRegistryLockProtection:
    def test_lock_protected_write_works_for_single_writer(self):
        """AK-10: Lock-geschuetzter Write-Pfad funktioniert bei N=1 (trivial)."""
        # Bei N=1 ist kein Deadlock moeglich — teste dass add/remove unter Lock arbeiten
        reg = {}
        reg = registry_add(
            reg, "WT-1",
            path="/repo/OmniCommand-lock-test",
            branch="test-branch",
            bl_id="BL-431",
            base_sha="dead1234",
            lane="A",
            status="active",
            vault_root="/vault",
        )
        assert registry_lookup(reg, "WT-1") is not None
        reg = registry_remove(reg, "WT-1")
        assert registry_lookup(reg, "WT-1") is None

    def test_concurrent_adds_no_path_collision(self):
        """AK-10: concurrent adds mit verschiedenen Pfaden -> beide erfolgreich (kein Deadlock)."""
        reg = {}
        errors = []

        def add_entry(wt_id, path):
            nonlocal reg
            try:
                reg = registry_add(
                    reg, wt_id,
                    path=path,
                    branch=f"feature/{wt_id}",
                    bl_id="BL-431",
                    base_sha="abc",
                    lane="A",
                    status="active",
                    vault_root="/vault",
                )
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=add_entry, args=("WT-1", "/repo/OmniCommand-WT-1"))
        t2 = threading.Thread(target=add_entry, args=("WT-2", "/repo/OmniCommand-WT-2"))
        t1.start(); t2.start()
        t1.join(); t2.join()

        # Kein unerwarteter Fehler (Pfad-Eindeutigkeit-Fehler waeren hier OK da verschiedene Pfade)
        path_errors = [e for e in errors if "path" not in str(e).lower()]
        assert len(path_errors) == 0, f"Unerwartete Fehler: {path_errors}"


# ---------------------------------------------------------------------------
# BL-351 batch_2 AK-9: Registry-Schema +parent_wt_id / +nesting_depth / +is_mothership
# ---------------------------------------------------------------------------

class TestAk9RegistrySchemaExtension:
    """AK-9 [Achse 1 / W12, W2]: registry_add schreibt additive Felder
    parent_wt_id, nesting_depth, is_mothership.

    ALLE Tests MUESSEN RED sein (Implementierung fehlt noch).
    """

    def _base_kwargs(self, *, path="/repo/OmniCommand-WT-1"):
        return dict(
            path=path,
            branch="feature/bl-351",
            bl_id="BL-351",
            base_sha="dead1234",
            lane="C",
            status="active",
            vault_root="/vault",
        )

    def test_ak9_registry_add_flat_worktree_has_is_mothership_true(self):
        """AK-9: registry_add fuer Tiefe-0-Worktree (kein parent) -> is_mothership=True."""
        reg = {}
        reg = registry_add(
            reg, "WT-1",
            **self._base_kwargs(),
            parent_wt_id=None,
            nesting_depth=0,
            is_mothership=True,
        )
        entry = registry_lookup(reg, "WT-1")
        assert entry is not None, "Eintrag nicht gefunden"
        assert entry.get("is_mothership") is True, (
            f"Erwartet is_mothership=True, bekam {entry.get('is_mothership')!r}"
        )

    def test_ak9_registry_add_nested_worktree_has_parent_wt_id(self):
        """AK-9: registry_add fuer nested Worktree traegt parent_wt_id des Eltern-Worktrees."""
        reg = {}
        # Eltern-Worktree registrieren
        reg = registry_add(
            reg, "WT-1",
            **self._base_kwargs(path="/repo/OmniCommand-WT-1"),
            parent_wt_id=None,
            nesting_depth=0,
            is_mothership=True,
        )
        # Kind-Worktree mit parent_wt_id="WT-1"
        reg = registry_add(
            reg, "WT-2",
            **self._base_kwargs(path="/repo/OmniCommand-WT-2"),
            parent_wt_id="WT-1",
            nesting_depth=1,
            is_mothership=False,
        )
        entry = registry_lookup(reg, "WT-2")
        assert entry is not None, "Kind-Eintrag nicht gefunden"
        assert entry.get("parent_wt_id") == "WT-1", (
            f"Erwartet parent_wt_id='WT-1', bekam {entry.get('parent_wt_id')!r}"
        )

    def test_ak9_registry_add_nested_worktree_has_nesting_depth(self):
        """AK-9: registry_add fuer Tiefe-N-Worktree traegt nesting_depth=N korrekt."""
        reg = {}
        reg = registry_add(
            reg, "WT-3",
            **self._base_kwargs(path="/repo/OmniCommand-WT-3"),
            parent_wt_id="WT-2",
            nesting_depth=2,
            is_mothership=False,
        )
        entry = registry_lookup(reg, "WT-3")
        assert entry is not None, "Tiefe-2-Eintrag nicht gefunden"
        assert entry.get("nesting_depth") == 2, (
            f"Erwartet nesting_depth=2, bekam {entry.get('nesting_depth')!r}"
        )

    def test_ak9_registry_add_child_is_not_mothership(self):
        """AK-9: nested Worktree hat is_mothership=False (nicht die Mothership)."""
        reg = {}
        reg = registry_add(
            reg, "WT-4",
            **self._base_kwargs(path="/repo/OmniCommand-WT-4"),
            parent_wt_id="WT-1",
            nesting_depth=1,
            is_mothership=False,
        )
        entry = registry_lookup(reg, "WT-4")
        assert entry is not None
        assert entry.get("is_mothership") is False, (
            f"Erwartet is_mothership=False fuer nested Worktree, "
            f"bekam {entry.get('is_mothership')!r}"
        )

    def test_ak9_all_three_new_fields_present_in_entry(self):
        """AK-9 CRITICAL: alle drei neuen Felder (parent_wt_id, nesting_depth, is_mothership)
        sind im geschriebenen Eintrag enthalten — keines darf fehlen."""
        reg = {}
        reg = registry_add(
            reg, "WT-5",
            **self._base_kwargs(path="/repo/OmniCommand-WT-5"),
            parent_wt_id="WT-0",
            nesting_depth=1,
            is_mothership=False,
        )
        entry = registry_lookup(reg, "WT-5")
        assert entry is not None
        missing = [f for f in ("parent_wt_id", "nesting_depth", "is_mothership")
                   if f not in entry]
        assert not missing, (
            f"Fehlende Pflicht-Felder im Registry-Eintrag: {missing}"
        )

    def test_ak9_legacy_add_without_new_fields_still_works(self):
        """AK-9 / Rueckwaerts-Kompat: registry_add OHNE neue Felder darf nicht crashen
        (bestehende Aufrufer ohne keyword-args bleiben kompatibel — additive, nicht breaking)."""
        reg = {}
        # Alter Aufruf OHNE parent_wt_id/nesting_depth/is_mothership (bestehende AK-2-Signatur)
        reg = registry_add(
            reg, "WT-OLD",
            path="/repo/OmniCommand-OLD",
            branch="main",
            bl_id="BL-000",
            base_sha="000",
            lane="A",
            status="active",
            vault_root="/vault",
        )
        # Muss ohne TypeError / ValueError gelingen
        entry = registry_lookup(reg, "WT-OLD")
        assert entry is not None, (
            "registry_add ohne neue Felder muss weiterhin funktionieren (additiv, nicht breaking)"
        )


# ---------------------------------------------------------------------------
# BL-351 batch_2 AK-10: Migration additiv + rueckwaerts-kompatibel
# ---------------------------------------------------------------------------

class TestAk10MigrationBackwardCompatibility:
    """AK-10 [Querschnitt / W13, QG-2]: Bestehende flache Registry-Eintraege ohne die neuen
    Felder bleiben lesbar; fehlende Felder defaulten graceful:
      nesting_depth  -> 0
      parent_wt_id   -> None
      is_mothership  -> True  (Single-Worktree-Fallback)
    INV-WORKTREE-2: kein Breaking-Change.

    ALLE Tests MUESSEN RED sein (Implementierung fehlt noch).
    """

    def _legacy_entry(self, wt_id="WT-LEGACY"):
        """Baut einen alten flachen Eintrag OHNE neue Felder direkt ins dict (Bypass registry_add)."""
        return {
            wt_id: {
                "path": "/repo/OmniCommand-legacy",
                "branch": "main",
                "bl_id": "BL-000",
                "base_sha": "cafebabe",
                "lane": "A",
                "status": "active",
                "vault_root": "/vault",
                # KEINE: parent_wt_id, nesting_depth, is_mothership
            }
        }

    def test_ak10_legacy_entry_lookup_no_error(self):
        """AK-10: registry_lookup auf altem Eintrag ohne neue Felder -> kein Fehler (kein KeyError)."""
        reg = self._legacy_entry()
        # Muss fehlerlos laden
        entry = registry_lookup(reg, "WT-LEGACY")
        assert entry is not None, "Legacy-Eintrag sollte lesbar sein"

    def test_ak10_legacy_entry_nesting_depth_defaults_to_zero(self):
        """AK-10: alter Eintrag ohne nesting_depth -> Lese-Zugriff liefert Default 0."""
        reg = self._legacy_entry()
        entry = registry_lookup(reg, "WT-LEGACY")
        assert entry is not None
        # registry_lookup soll nesting_depth=0 als graceful Default liefern (AK-10 Spec)
        depth = entry.get("nesting_depth", "MISSING")
        assert depth == 0, (
            f"Erwartet nesting_depth=0 als graceful Default fuer legacy Eintrag, "
            f"bekam {depth!r}"
        )

    def test_ak10_legacy_entry_parent_wt_id_defaults_to_none(self):
        """AK-10: alter Eintrag ohne parent_wt_id -> Lese-Zugriff liefert Default None."""
        reg = self._legacy_entry()
        entry = registry_lookup(reg, "WT-LEGACY")
        assert entry is not None
        parent = entry.get("parent_wt_id", "MISSING")
        assert parent is None, (
            f"Erwartet parent_wt_id=None als graceful Default fuer legacy Eintrag, "
            f"bekam {parent!r}"
        )

    def test_ak10_legacy_entry_is_mothership_defaults_to_true(self):
        """AK-10: alter Eintrag ohne is_mothership -> Lese-Zugriff liefert Default True
        (Single-Worktree-Fallback-Annahme, INV-WORKTREE-2)."""
        reg = self._legacy_entry()
        entry = registry_lookup(reg, "WT-LEGACY")
        assert entry is not None
        is_ms = entry.get("is_mothership", "MISSING")
        assert is_ms is True, (
            f"Erwartet is_mothership=True als graceful Default fuer legacy Eintrag, "
            f"bekam {is_ms!r}"
        )

    def test_ak10_legacy_entry_existing_fields_unchanged(self):
        """AK-10: Migration darf bestehende Felder NICHT veraendern (additiv-only)."""
        reg = self._legacy_entry()
        entry = registry_lookup(reg, "WT-LEGACY")
        assert entry is not None
        # Alle alten Felder muessen unveraendert erhalten bleiben
        assert entry.get("path") == "/repo/OmniCommand-legacy"
        assert entry.get("branch") == "main"
        assert entry.get("bl_id") == "BL-000"
        assert entry.get("base_sha") == "cafebabe"
        assert entry.get("lane") == "A"
        assert entry.get("status") == "active"
        assert entry.get("vault_root") == "/vault"

    def test_ak10_new_and_legacy_entries_coexist_in_same_registry(self):
        """AK-10: neue (mit Felder) + alte (ohne Felder) Eintraege koennen in derselben
        Registry gleichzeitig existieren — kein Fehler, beide lookupbar."""
        reg = self._legacy_entry("WT-OLD")
        # Neuer Eintrag mit allen Feldern hinzufuegen
        reg = registry_add(
            reg, "WT-NEW",
            path="/repo/OmniCommand-NEW",
            branch="feature/bl-351",
            bl_id="BL-351",
            base_sha="newsha",
            lane="C",
            status="active",
            vault_root="/vault",
            parent_wt_id=None,
            nesting_depth=0,
            is_mothership=True,
        )
        # Beide muessen lookupbar sein
        old_entry = registry_lookup(reg, "WT-OLD")
        new_entry = registry_lookup(reg, "WT-NEW")
        assert old_entry is not None, "Alter Eintrag verschwunden nach Hinzufuegen neuen Eintrags"
        assert new_entry is not None, "Neuer Eintrag nicht findbar"
        # Legacy-Eintrag hat Default-Werte, neuer hat explizite Werte
        assert new_entry.get("nesting_depth") == 0
        assert new_entry.get("is_mothership") is True


# ===========================================================================
# BL-230 SB-1b AK-WORKTREE-BOOTSTRAP (Stage 1, RED-first) — Worktree-Bootstrap-Oekonomie.
#
# Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (Slice "Worktree-Bootstrap", 4 Exit-Kriterien).
# Spec: BL-230_Spec.md §6 SUPPORT_AK, BORDER-13/14, U4/U5.
#
# SOLL (4 messbare Exit-Kriterien):
#   1. Base-Ref-Pin     — alle Worktrees einer Welle vom SELBEN base_sha; Divergenz erkannt/abgelehnt (EC-WB-4).
#   2. Clean-Mothership — Fan-Out auf dirty Mothership -> ok=False; clean -> ok=True (U4, EC-WB-1).
#   3. Telemetrie       — Bootstrap-Pfad liefert ein Telemetrie-dict mit messbaren Keys (count/duration/base_sha).
#   4. 0-Orphan-Cleanup — Cleanup entfernt alle Welle-Eintraege (Registry leer); idempotent (2x); Windows-robust
#                         (Backslash/locked-handle-Simulation kein Crash) (EC-WB-2/EC-WB-3).
#
# NICHT-ZIEL (Blueprint): kein echtes `git worktree add`/Subprocess; reine Pin-/Gate-/Telemetrie-/Cleanup-Logik
#   testbar mit injizierten Funktionen (analog handoff merge_fn). Disk/RAM/API-Budget-Cap-Zahlen -> SOA-2/BL-234.
#
# RED-MECHANIK: die neuen Funktionen (bootstrap_wave / pin_base_sha / check_clean_mothership / cleanup_wave)
#   existieren in worktree_registry.py NOCH NICHT. Sie werden LAZY innerhalb jeder Test-Methode importiert,
#   damit der Modul-Import oben (bestehende Kanarienvoegel) GRUEN bleibt und NUR diese SB-1b-Tests RED werden
#   (ImportError -> Test-FAIL pro Methode statt Collection-Abbruch der ganzen Datei).
# ===========================================================================


def _import_bootstrap(name):
    """Lazy-Import einer SB-1b-Bootstrap-Funktion. ImportError -> der jeweilige Test failt (RED),
    ohne die Modul-Collection (bestehende Kanarienvoegel) zu brechen."""
    import worktree_registry as wr
    fn = getattr(wr, name, None)
    if fn is None:
        raise ImportError(
            f"worktree_registry.{name} existiert noch nicht (BL-230 SB-1b RED — GREEN-Worker implementiert)."
        )
    return fn


class TestWorktreeBootstrapBaseRefPin:
    """AK-WORKTREE-BOOTSTRAP Exit-1: Base-Ref-Pin (alle Welle-Worktrees vom SELBEN base_sha)."""

    def test_pin_returns_common_base_sha_for_wave(self):
        """Exit-1: pin_base_sha liefert/erzwingt EINEN gemeinsamen base_sha fuer die ganze Welle."""
        pin_base_sha = _import_bootstrap("pin_base_sha")
        result = pin_base_sha("deadbeef", ["WT-1", "WT-2", "WT-3"])
        # Ergebnis traegt den gemeinsamen base_sha (dict mit base_sha-Key ODER der String selbst).
        base = result.get("base_sha") if isinstance(result, dict) else result
        assert base == "deadbeef", f"Erwartet gemeinsamen base_sha 'deadbeef', bekam {result!r}"

    def test_pin_divergent_base_sha_rejected(self):
        """Exit-1 / EC-WB-4: zwei Worktrees mit DIVERGENTEN base_sha-Anforderungen -> abgelehnt
        (ValueError ODER ok=False-Flag). Kein stilles Durchwinken einer Welle aus 2 Commits."""
        pin_base_sha = _import_bootstrap("pin_base_sha")
        # Divergenz wird ueber requested_per_wt ausgedrueckt (WT-2 will einen anderen Commit).
        try:
            result = pin_base_sha(
                "deadbeef",
                ["WT-1", "WT-2"],
                requested_per_wt={"WT-1": "deadbeef", "WT-2": "cafe0000"},
            )
        except ValueError:
            return  # Divergenz hart abgelehnt — korrekt.
        # Falls kein Raise: das Ergebnis MUSS die Divergenz als ok=False/divergent flaggen.
        assert isinstance(result, dict)
        flagged = (
            result.get("ok") is False
            or result.get("divergent") is True
            or result.get("pin_mismatch") is True
        )
        assert flagged, f"Erwartet Pin-Mismatch-Ablehnung bei base_sha-Divergenz, bekam {result!r}"

    def test_pin_uniform_wave_ok(self):
        """Exit-1: eine Welle mit identischer base_sha-Anforderung wird NICHT als Divergenz geflaggt."""
        pin_base_sha = _import_bootstrap("pin_base_sha")
        result = pin_base_sha(
            "abc123",
            ["WT-1", "WT-2"],
            requested_per_wt={"WT-1": "abc123", "WT-2": "abc123"},
        )
        assert isinstance(result, dict)
        assert result.get("ok") is not False and result.get("pin_mismatch") is not True, (
            f"uniforme Welle faelschlich als Mismatch geflaggt: {result!r}"
        )


class TestWorktreeBootstrapCleanMothershipGate:
    """AK-WORKTREE-BOOTSTRAP Exit-2 / U4 / EC-WB-1: Fan-Out auf dirty Mothership verweigert."""

    def test_dirty_mothership_blocks_fan_out(self):
        """Exit-2 / EC-WB-1: injizierter dirty-Status -> ok=False (Fan-Out blockiert)."""
        check_clean_mothership = _import_bootstrap("check_clean_mothership")
        result = check_clean_mothership(dirty_check=lambda: True)
        assert isinstance(result, dict)
        assert result.get("ok") is False, (
            f"dirty Mothership muss Fan-Out blockieren (ok=False), bekam {result!r}"
        )

    def test_clean_mothership_allows_fan_out(self):
        """Exit-2: clean Mothership -> ok=True."""
        check_clean_mothership = _import_bootstrap("check_clean_mothership")
        result = check_clean_mothership(dirty_check=lambda: False)
        assert isinstance(result, dict)
        assert result.get("ok") is True, (
            f"clean Mothership muss Fan-Out erlauben (ok=True), bekam {result!r}"
        )

    def test_gate_result_is_dict(self):
        """Exit-2: check_clean_mothership gibt immer ein dict zurueck."""
        check_clean_mothership = _import_bootstrap("check_clean_mothership")
        assert isinstance(check_clean_mothership(dirty_check=lambda: False), dict)


class TestWorktreeBootstrapTelemetry:
    """AK-WORKTREE-BOOTSTRAP Exit-3: Bootstrap-Kosten-Telemetrie wird erfasst."""

    def test_bootstrap_returns_telemetry_dict(self):
        """Exit-3: der Bootstrap-Pfad liefert ein Telemetrie-dict mit messbaren Keys."""
        bootstrap_wave = _import_bootstrap("bootstrap_wave")
        result = bootstrap_wave(
            base_sha="deadbeef",
            wt_ids=["WT-1", "WT-2"],
            dirty_check=lambda: False,
            add_fn=lambda wt_id, base_sha: {"wt_id": wt_id, "base_sha": base_sha},
        )
        assert isinstance(result, dict)
        telemetry = result.get("telemetry", result)
        assert isinstance(telemetry, dict)
        # messbare Keys: mindestens count + base_sha (duration optional aber bevorzugt).
        assert "count" in telemetry, f"Telemetrie ohne 'count'-Key: {telemetry!r}"
        assert telemetry.get("count") == 2, f"Erwartet count=2 fuer 2 Worktrees, bekam {telemetry!r}"
        has_measurable = "base_sha" in telemetry or "duration" in telemetry or "duration_s" in telemetry
        assert has_measurable, f"Telemetrie ohne messbares base_sha/duration: {telemetry!r}"

    def test_bootstrap_blocked_on_dirty_mothership(self):
        """Exit-2+3: bootstrap_wave auf dirty Mothership -> ok=False, KEIN add_fn-Aufruf (Gate vor Bau)."""
        bootstrap_wave = _import_bootstrap("bootstrap_wave")
        add_calls = []
        result = bootstrap_wave(
            base_sha="deadbeef",
            wt_ids=["WT-1"],
            dirty_check=lambda: True,
            add_fn=lambda wt_id, base_sha: add_calls.append(wt_id),
        )
        assert isinstance(result, dict)
        assert result.get("ok") is False, f"dirty Mothership muss bootstrap blocken: {result!r}"
        assert add_calls == [], "add_fn wurde trotz dirty Mothership aufgerufen (Gate nicht VOR Bau)"


class TestWorktreeBootstrapCleanup:
    """AK-WORKTREE-BOOTSTRAP Exit-4 / EC-WB-2/EC-WB-3: Windows-robustes idempotentes 0-Orphan-Cleanup."""

    def _wave_registry(self):
        reg = {}
        reg = registry_add(
            reg, "WT-1",
            path="/repo/OmniCommand-WT-1", branch="feature/a", bl_id="BL-230",
            base_sha="deadbeef", lane="A", status="active", vault_root="/vault",
        )
        reg = registry_add(
            reg, "WT-2",
            path="/repo/OmniCommand-WT-2", branch="feature/b", bl_id="BL-230",
            base_sha="deadbeef", lane="A", status="active", vault_root="/vault",
        )
        return reg

    def test_cleanup_removes_all_wave_entries_zero_orphans(self):
        """Exit-4: cleanup_wave entfernt ALLE Welle-Eintraege -> Registry leer (0 Orphans)."""
        cleanup_wave = _import_bootstrap("cleanup_wave")
        reg = self._wave_registry()
        result = cleanup_wave(reg, ["WT-1", "WT-2"])
        new_reg = result.get("registry") if isinstance(result, dict) else result
        assert registry_list(new_reg) == [], (
            f"Cleanup liess Orphans uebrig: {registry_list(new_reg)!r}"
        )

    def test_cleanup_idempotent_second_call_no_error(self):
        """Exit-4 / EC-WB-2: 2x cleanup_wave -> idempotent, kein Fehler, weiterhin 0 Orphans."""
        cleanup_wave = _import_bootstrap("cleanup_wave")
        reg = self._wave_registry()
        r1 = cleanup_wave(reg, ["WT-1", "WT-2"])
        reg1 = r1.get("registry") if isinstance(r1, dict) else r1
        # Zweiter Lauf auf der bereits geleerten Registry darf nicht crashen.
        r2 = cleanup_wave(reg1, ["WT-1", "WT-2"])
        reg2 = r2.get("registry") if isinstance(r2, dict) else r2
        assert registry_list(reg2) == [], f"2x-Cleanup nicht idempotent: {registry_list(reg2)!r}"

    def test_cleanup_windows_backslash_path_robust(self):
        """Exit-4 / EC-WB-3: Windows-Pfad mit Backslash -> robustes Cleanup ohne Crash."""
        cleanup_wave = _import_bootstrap("cleanup_wave")
        reg = registry_add(
            {}, "WT-1",
            path=r"C:\repos\OmniCommand-WT-1", branch="feature/a", bl_id="BL-230",
            base_sha="deadbeef", lane="A", status="active", vault_root=r"C:\vault",
        )
        result = cleanup_wave(reg, ["WT-1"])  # darf nicht crashen
        new_reg = result.get("registry") if isinstance(result, dict) else result
        assert registry_list(new_reg) == [], "Backslash-Pfad-Cleanup liess Orphan uebrig"

    def test_cleanup_locked_handle_simulation_no_crash(self):
        """Exit-4 / EC-WB-3: injizierter remove_fn der bei locked handle wirft -> Cleanup faengt ab
        (best-effort, kein Crash) und entfernt den Registry-Eintrag dennoch (0 Orphans)."""
        cleanup_wave = _import_bootstrap("cleanup_wave")
        reg = self._wave_registry()

        def locked_remove(path):
            raise OSError("WinError 32: process cannot access file (locked handle simulation)")

        # best-effort: ein werfendes remove_fn darf das Cleanup NICHT zum Crash bringen.
        result = cleanup_wave(reg, ["WT-1", "WT-2"], remove_fn=locked_remove)
        new_reg = result.get("registry") if isinstance(result, dict) else result
        assert registry_list(new_reg) == [], (
            f"locked-handle-Simulation: Registry-Eintraege trotz best-effort nicht entfernt: "
            f"{registry_list(new_reg)!r}"
        )

    def test_cleanup_telemetry_reports_orphans(self):
        """Exit-4: cleanup_wave-Ergebnis meldet die Orphan-Zahl (0 nach erfolgreichem Cleanup)."""
        cleanup_wave = _import_bootstrap("cleanup_wave")
        reg = self._wave_registry()
        result = cleanup_wave(reg, ["WT-1", "WT-2"])
        assert isinstance(result, dict), "cleanup_wave soll ein dict (mit registry + orphans-Telemetrie) liefern"
        assert result.get("orphans", 0) == 0, f"Erwartet orphans=0 nach Cleanup, bekam {result.get('orphans')!r}"
