#!/usr/bin/env python3
"""Tests fuer BL-385 — Repo-Meta-Self-Atomisierung Write-Scope (non-destruktiver Build).

RED-Worker (TDD red): diese Tests beschreiben die SOLL-Signatur, die ein separater GREEN-Worker
implementiert. Erwartung BEIM RED-Lauf:
  - AK-TARGET (Vault-only-Routing, neuer `truths_root`-Parameter)  -> RED (Feature fehlt)
  - AK-GATE   (Bootstrap-Selbstbezug-Gate, neuer `bootstrap_confirm`/`repo_meta_self`) -> RED
  - AK-LOCK   (Exclude-Regression-Lock gegen IST)                  -> GRUEN (charakterisierend)
  - Default-Regression (truths_root=None unveraendert)             -> GRUEN (Abwaertskompat)

Konvention: pytest-Stil, tmp-Vault wie test_truth_pilot_cutover.py; cutover_model wird via
monkeypatch gemockt um die durchgereichten kwargs zu asserten. KEIN Produktiv-Code hier.
"""
from __future__ import annotations

import truth_pilot_cutover as pc


def _mk(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _vault(tmp_path):
    """Mini-Vault: 1 ready HEADING + 1 ready SEGMENT + 1 Owner-Scope-out + 1 Prosa-Quarantaene
    (identisch zur Konvention in test_truth_pilot_cutover.py)."""
    _mk(tmp_path / "Backlog" / "BL-1" / "2_Model" / "H_Model.md", "### W01\nEine Wahrheit.\n\n### W02\nZwei.\n")
    _mk(tmp_path / "Backlog" / "BL-2" / "2_Model" / "S_Model.md", "- W1: erste Wahrheit\n- W2: zweite\n")
    _mk(tmp_path / "Backlog" / "BL-199" / "2_Model" / "BL-199_Model.md", "### W01\nReady aber per Owner ausgeschlossen.\n")
    _mk(tmp_path / "Backlog" / "BL-9" / "2_Model" / "P_Model.md", "# Titel\n\nNur Fliesstext ohne W-Knoten.\n")
    return tmp_path / "Backlog"


def _spy_cutover(monkeypatch):
    """Ersetzt tcut.cutover_model durch einen Spy, der alle (args, kwargs) sammelt und ein
    erfolgreiches Cutover-Ergebnis vortaeuscht (kein echter Write)."""
    calls = []

    def spy(model_path, namespace, **kwargs):
        calls.append({"model": model_path, "ns": namespace, "kwargs": kwargs})
        return {"cutover": True, "view_mode": "heading", "legacy": "fake_legacy"}

    monkeypatch.setattr(pc.tcut, "cutover_model", spy)
    return calls


# ---------------------------------------------------------------------------
# AK-TARGET — Vault-only-Routing (Ziel-Pfad durchreichen)  [RED erwartet]
# ---------------------------------------------------------------------------

def test_target_truths_root_passed_through_as_kwargs(tmp_path, monkeypatch):
    """AK-TARGET-1: bei gesetztem truths_root reicht execute() pro Model truths_dir + legacy_dir
    (abgeleitet aus dem Root) an cutover_model durch — nicht der bisher leere Aufruf."""
    calls = _spy_cutover(monkeypatch)
    root = tmp_path / "_meta_truths"
    rep = pc.execute(_vault(tmp_path), None, confirm=True, jobs=1, require_gate_go=False,
                     truths_root=root)
    assert rep["dry_run"] is False
    assert len(calls) == 2, "beide ready Models muessen cutover_model aufrufen"
    for c in calls:
        assert "truths_dir" in c["kwargs"] and c["kwargs"]["truths_dir"] is not None, \
            "truths_dir muss aus dem Vault-Root abgeleitet durchgereicht werden"
        assert "legacy_dir" in c["kwargs"] and c["kwargs"]["legacy_dir"] is not None, \
            "legacy_dir muss aus dem Vault-Root abgeleitet durchgereicht werden"
        # Ziel liegt UNTER dem gewaehlten Vault-Root, NICHT co-located am Model
        td = pc.Path(c["kwargs"]["truths_dir"])
        assert str(root) in str(td), "truths_dir muss unter dem Vault-Root liegen (nicht co-located)"


def test_target_per_model_collision_free_subdir(tmp_path, monkeypatch):
    """AK-TARGET-2: zwei verschiedene Models duerfen NIE in denselben truths_dir schreiben
    (deterministischer, kollisionsfreier Unter-Pfad je Model)."""
    calls = _spy_cutover(monkeypatch)
    root = tmp_path / "_meta_truths"
    pc.execute(_vault(tmp_path), None, confirm=True, jobs=1, require_gate_go=False,
               truths_root=root)
    truths_dirs = [str(c["kwargs"]["truths_dir"]) for c in calls]
    assert len(truths_dirs) == len(set(truths_dirs)), \
        "jeder truths_dir muss einzigartig sein (kein Model-Kollisions-Write)"


def test_target_default_none_unchanged_colocated(tmp_path, monkeypatch):
    """AK-TARGET-5 (Default-Regression, GRUEN): ohne truths_root bleibt der Aufruf parameterlos
    -> co-located Default. cutover_model darf KEIN truths_dir/legacy_dir bekommen."""
    calls = _spy_cutover(monkeypatch)
    rep = pc.execute(_vault(tmp_path), None, confirm=True, jobs=1, require_gate_go=False)
    assert rep["dry_run"] is False
    assert len(calls) == 2
    for c in calls:
        # co-located = entweder gar kein kwarg, oder explizit None
        assert c["kwargs"].get("truths_dir") is None, "Default muss co-located bleiben (truths_dir None/absent)"
        assert c["kwargs"].get("legacy_dir") is None, "Default muss co-located bleiben (legacy_dir None/absent)"


def test_target_dry_run_shows_resolved_target(tmp_path):
    """AK-TARGET-4: Dry-Run/plan zeigt das aufgeloeste Ziel, wenn truths_root gesetzt ist —
    der User sieht VOR dem Write, wohin geschrieben wuerde."""
    root = tmp_path / "_meta_truths"
    rep = pc.execute(_vault(tmp_path), None, jobs=1, require_gate_go=False, truths_root=root)
    assert rep["dry_run"] is True
    blob = repr(rep)
    assert "_meta_truths" in blob, "das gewaehlte Ziel-Root muss im Dry-Run-Output sichtbar sein"


def test_target_repo_meta_self_default_root_under_vault(tmp_path, monkeypatch):
    """AK-TARGET-3/AK-GATE: repo_meta_self=True ohne expliziten Root nutzt den Owner-Default-Root
    (_meta_truths unter dem Vault) — Ziel liegt im Vault, nicht co-located."""
    calls = _spy_cutover(monkeypatch)
    vault = _vault(tmp_path)
    pc.execute(vault, None, confirm=True, jobs=1, require_gate_go=False,
               repo_meta_self=True, bootstrap_confirm=True)
    assert len(calls) == 2
    for c in calls:
        td = str(c["kwargs"].get("truths_dir"))
        assert "_meta_truths" in td, "repo_meta_self ohne Root -> Default _meta_truths unter Vault"


# ---------------------------------------------------------------------------
# AK-GATE — Bootstrap-Selbstbezug-Gate (refuse-by-default)  [RED erwartet]
# ---------------------------------------------------------------------------

def test_gate_repo_meta_self_refuses_without_bootstrap_confirm(tmp_path, monkeypatch):
    """AK-GATE-1: repo_meta_self=True + confirm=True OHNE bootstrap_confirm -> Write VERWEIGERT,
    klarer Refuse-Marker, 0 Mutation (cutover_model NIE aufgerufen)."""
    calls = _spy_cutover(monkeypatch)
    rep = pc.execute(_vault(tmp_path), None, confirm=True, jobs=1, require_gate_go=False,
                     repo_meta_self=True, bootstrap_confirm=False)
    assert rep.get("aborted"), "muss ein aborted-Marker tragen (refuse-by-default)"
    assert "bootstrap" in str(rep.get("aborted")), "Refuse-Marker muss das Bootstrap-Gate benennen"
    assert calls == [], "0 Mutation: cutover_model darf NICHT aufgerufen werden"


def test_gate_repo_meta_self_passes_with_bootstrap_confirm(tmp_path, monkeypatch):
    """AK-GATE (offen): repo_meta_self=True + confirm=True + bootstrap_confirm=True laeuft durch."""
    calls = _spy_cutover(monkeypatch)
    rep = pc.execute(_vault(tmp_path), None, confirm=True, jobs=1, require_gate_go=False,
                     repo_meta_self=True, bootstrap_confirm=True)
    assert not rep.get("aborted"), "mit bootstrap_confirm=True darf das Gate NICHT abbrechen"
    assert rep["dry_run"] is False
    assert len(calls) == 2, "Gate offen -> echter Cutover-Pfad laeuft"


def test_gate_non_self_class_untouched_by_bootstrap_gate(tmp_path, monkeypatch):
    """AK-GATE-3: Nicht-Selbst-Klasse (repo_meta_self default False) ist vom Bootstrap-Gate
    UNBERUEHRT — confirm=True allein genuegt weiterhin."""
    calls = _spy_cutover(monkeypatch)
    rep = pc.execute(_vault(tmp_path), None, confirm=True, jobs=1, require_gate_go=False)
    assert not rep.get("aborted"), "normaler vault-per-BL-Scope darf NICHT vom Bootstrap-Gate geblockt werden"
    assert rep["dry_run"] is False
    assert len(calls) == 2


def test_gate_dry_run_always_allowed_for_repo_meta_self(tmp_path):
    """AK-GATE-2: Dry-Run (confirm=False) ist IMMER erlaubt, auch fuer repo_meta_self —
    Planung der Selbst-Klasse ist jederzeit erlaubt (kein Gate noetig)."""
    rep = pc.execute(_vault(tmp_path), None, confirm=False, jobs=1, require_gate_go=False,
                     repo_meta_self=True, bootstrap_confirm=False)
    assert not rep.get("aborted"), "Dry-Run der Selbst-Klasse darf nie vom Bootstrap-Gate geblockt werden"
    assert rep["dry_run"] is True


# ---------------------------------------------------------------------------
# AK-LOCK — Exclude-Regression-Lock (gegen IST, charakterisierend)  [GRUEN]
# ---------------------------------------------------------------------------

def test_lock_default_exclude_full_set_present(tmp_path):
    """AK-LOCK-1: DEFAULT_EXCLUDE enthaelt PERMANENT mindestens die explizit benannten Basenamen
    UND die volle aktuelle 8er-Menge. Versehentliches Entfernen laesst diesen Test FAILen."""
    expected = {
        "BacklogItem-Schema_Model",
        "Sprachnotiz_Patrick_Model",
        "stage_system_vault_zentral_loop_Model",
        "BL-199_Model",
        "BL-201_Model",
        "BL-208_Model",
        "adherence_research",
        "BL-372_Model",
    }
    actual = set(pc.DEFAULT_EXCLUDE)
    # die im Prompt namentlich geforderten Anker
    for must in ("Sprachnotiz_Patrick_Model", "BacklogItem-Schema_Model",
                 "stage_system_vault_zentral_loop_Model"):
        assert must in actual, f"{must} muss permanent scoped-out bleiben"
    # die volle 8er-Menge
    assert expected <= actual, "die volle DEFAULT_EXCLUDE-Menge (8) darf nicht schrumpfen"
    assert len(actual) >= 8, "DEFAULT_EXCLUDE darf nicht unter 8 Basenamen fallen"


def test_lock_empty_model_never_in_write_scope(tmp_path):
    """AK-LOCK: ein leeres/no-W-def Model (Prosa) erscheint NIE im write_scope —
    immer in skipped (quarantine ODER owner_scope_out)."""
    pl = pc.plan(_vault(tmp_path), None, jobs=1)
    scope_names = {pc.Path(s["model"]).name for s in pl["write_scope"]}
    assert "P_Model.md" not in scope_names, "Prosa-Model darf nie im write_scope landen"
    skipped = {pc.Path(s["model"]).name: s["reason"] for s in pl["skipped"]}
    assert "P_Model.md" in skipped
    assert ("quarantine" in skipped["P_Model.md"]) or (skipped["P_Model.md"] == "owner_scope_out")
