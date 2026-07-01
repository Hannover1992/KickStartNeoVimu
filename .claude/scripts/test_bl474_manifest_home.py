#!/usr/bin/env python3
"""BL-474 RED-Tests: W_fetch State-WRITE nach bl_folder normieren (a) +
INV-A-ORDER-4-Read auf read_bl_block (c).

RED-Hebel (muessen jetzt FAILEN — IST-Stand):
- test_wfetch_state_write_targets_bl_folder: Z79 = '{VAULT}/_manifest.md' (Pattern A: State) -> FAIL
- test_wfetch_no_global_state_write: bare {VAULT}/_manifest.md in STATE-WRITE-Zeile -> FAIL
- test_inv_a_order_4_uses_read_bl_block: Z714 kein read_bl_block-Bezug -> FAIL

Praezision-Kanarie (heute GREEN, bleibt GREEN — Schutz gegen Over-Edit):
- test_wfetch_read_still_global: Z54/Z145 LESE-Stellen referenzieren {VAULT}/_manifest.md

Behavioral-Tests (Characterization read_bl_block-Fallback — sollten JETZT SCHON passen):
- test_read_bl_block_finds_wfetch_in_bl_folder: bl_folder-first (Z365-370)
- test_read_bl_block_finds_wfetch_via_global_fallback: global-legacy-Fallback (Z383-391)

Kanarien / Regression-Floors:
- test_manifest_reader_unchanged: manifest_reader.py git-unveraendert
- test_manifest_dual_read_floor: test_manifest_reader_dual_read.py gruen
- test_manifest_split_integration_floor: test_manifest_split_integration.py gruen (falls vorhanden)

FLOOR-HINWEIS: Die bestehenden manifest-Tests (test_manifest_reader.py 11/11 +
test_manifest_reader_dual_read.py) laufen separat als Floor-Beleg — sie werden hier
NICHT ausgefuehrt, nur referenziert.

_parse_field_path-Granularitaet (verifiziert am echten Reader, Z149-157):
  '.' wird NUR am ERSTEN Punkt gesplittet: 'BERATER_OUTPUTS.wfetch.status'
  -> block='BERATER_OUTPUTS', field='wfetch.status'
  _read_field_from_manifest sucht dann im Block die Zeile 'wfetch.status: <value>'
  (YAML-like flat key). Die Fixture nutzt daher FLACHE Schreibweise:
    ## BERATER_OUTPUTS
    wfetch.status: DONE
  (NICHT verschachteltes YAML 'wfetch:\\n  status: DONE' — das findet der Reader nicht.)
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Pfad-Anker (relativ zum Repo-Root via __file__)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent.absolute()
_CLAUDE_DIR = _SCRIPTS_DIR.parent                    # .claude/
_REPO_ROOT = _CLAUDE_DIR.parent                      # OmniCommand-wtA/
_W_FETCH_MD = _CLAUDE_DIR / "commands" / "_W_fetch.md"
_A_ORCHESTRATE_MD = _CLAUDE_DIR / "commands" / "_A_orchestrate.md"

# Python-API-Import (READ-ONLY — manifest_reader.py wird NIE editiert)
sys.path.insert(0, str(_SCRIPTS_DIR))
import manifest_reader


# ---------------------------------------------------------------------------
# STRUKTUR-TESTS auf _W_fetch.md
# ---------------------------------------------------------------------------

class TestWFetchStateWriteLocation:
    """AK-1: die Pattern-A-State-WRITE-Stelle (Z79) soll bl_folder referenzieren.

    IST: '{VAULT}/_manifest.md   (Pattern A: State)' -> bl_folder-Assert FAIL,
         bare-global-Treffer in der SCHREIBT-Zeile FAIL.
    SOLL (GREEN): '{bl_folder}/_manifest.md   (Pattern A: State, per-BL)'
    """

    def _read_wfetch(self) -> str:
        assert _W_FETCH_MD.exists(), f"_W_fetch.md nicht gefunden: {_W_FETCH_MD}"
        return _W_FETCH_MD.read_text(encoding="utf-8")

    def test_wfetch_state_write_targets_bl_folder(self):
        """RED-HEBEL (AK-1a): die Zeile mit 'Pattern A: State' in der SCHREIBT-Sektion
        referenziert '{bl_folder}/_manifest.md' (per-BL), NICHT bare '{VAULT}/_manifest.md'.

        IST (Z79): '4. {VAULT}/_manifest.md   (Pattern A: State)' -> FAIL
        SOLL (GREEN): '4. {bl_folder}/_manifest.md   (Pattern A: State, per-BL)'
        """
        content = self._read_wfetch()

        # Finde die Zeile die 'Pattern A: State' (State-WRITE-Anker) enthaelt
        pattern_a_lines = [
            line for line in content.splitlines()
            if "Pattern A: State" in line
        ]
        assert len(pattern_a_lines) >= 1, (
            "Keine Zeile mit 'Pattern A: State' in _W_fetch.md gefunden — "
            "Anker fehlt oder umbenannt"
        )

        # Alle Pattern-A-State-Zeilen muessen bl_folder referenzieren, NICHT bare {VAULT}
        state_write_line = pattern_a_lines[0]
        assert "{bl_folder}" in state_write_line or "bl_folder" in state_write_line, (
            f"RED-HEBEL: 'Pattern A: State'-Zeile referenziert NICHT bl_folder:\n"
            f"  IST:  {state_write_line!r}\n"
            f"  SOLL: Zeile muss '{{bl_folder}}/_manifest.md' enthalten"
        )

    def test_wfetch_no_global_state_write(self):
        """RED-HEBEL (AK-1b / Negativ): die STATE-WRITE-Deklarationszeile (Pattern A: State)
        enthaelt KEIN bare '{VAULT}/_manifest.md'.

        IST (Z79): Zeile = '|    4. {VAULT}/_manifest.md   (Pattern A: State)       |' -> FAIL
        SOLL: '{VAULT}/_manifest.md' kommt in dieser Zeile NICHT vor (stattdessen bl_folder).
        """
        content = self._read_wfetch()

        pattern_a_lines = [
            line for line in content.splitlines()
            if "Pattern A: State" in line
        ]
        assert len(pattern_a_lines) >= 1, (
            "Keine 'Pattern A: State'-Zeile gefunden — Anker fehlt"
        )

        state_write_line = pattern_a_lines[0]
        # In dieser Zeile darf KEIN bare '{VAULT}/_manifest.md' vorkommen
        assert "{VAULT}/_manifest.md" not in state_write_line, (
            f"RED-HEBEL: STATE-WRITE-Zeile enthaelt noch bare '{{VAULT}}/_manifest.md':\n"
            f"  {state_write_line!r}\n"
            f"  GREEN-Ziel: Zeile muss '{{bl_folder}}/_manifest.md' enthalten"
        )

    def test_wfetch_read_still_global(self):
        """PRAEZISIONS-KANARIE (AK-1c / gegen Over-Edit des GREEN-Workers):
        die LESE-Stellen (Z54 Input PFLICHT 1. + Z145 Schritt 0a) referenzieren WEITER
        '{VAULT}/_manifest.md'. Nur der STATE-WRITE wird normiert; LESEN bleibt global.

        IST: Z54/Z145 = '{VAULT}/_manifest.md' -> GREEN heute, bleibt GREEN.
        """
        content = self._read_wfetch()
        lines = content.splitlines()

        # Z54-Bereich: "LIEST (Input) - PFLICHT" Sektion, erster Eintrag = {VAULT}/_manifest.md
        # Erkenne anhand des Kontextes: Zeile beginnt mit '|    1. {VAULT}/_manifest.md'
        lese_input_lines = [
            line for line in lines
            if re.search(r"1\.\s+\{VAULT\}/_manifest\.md", line)
        ]
        assert len(lese_input_lines) >= 1, (
            "KANARIENVOGEL-MISS: Z54-Bereich (LIEST Input 1. {VAULT}/_manifest.md) "
            "nicht gefunden — LESE-Stelle faelschlich entfernt? (Over-Edit)"
        )

        # Z145-Bereich: 'Lies `{VAULT}/_manifest.md`' (Schritt 0a)
        schritt_0a_lines = [
            line for line in lines
            if re.search(r"Lies\s+`\{VAULT\}/_manifest\.md`", line)
        ]
        assert len(schritt_0a_lines) >= 1, (
            "KANARIENVOGEL-MISS: Z145-Bereich ('Lies `{VAULT}/_manifest.md`', Schritt 0a) "
            "nicht gefunden — LESE-Stelle faelschlich entfernt? (Over-Edit)"
        )


# ---------------------------------------------------------------------------
# STRUKTUR-TEST auf _A_orchestrate.md
# ---------------------------------------------------------------------------

class TestAOrchestrateINVAOrder4:
    """AK-2: INV-A-ORDER-4-Guard (Z714) soll read_bl_block nutzen.

    IST: 'wfetch_status = BERATER_OUTPUTS.wfetch.status ?? "MISSING"' -> FAIL
    SOLL (GREEN): 'wfetch_status = manifest_reader.read_bl_block(bl_id, "BERATER_OUTPUTS.wfetch.status") ?? "MISSING"'
    """

    def _read_a_orchestrate(self) -> str:
        assert _A_ORCHESTRATE_MD.exists(), (
            f"_A_orchestrate.md nicht gefunden: {_A_ORCHESTRATE_MD}"
        )
        return _A_ORCHESTRATE_MD.read_text(encoding="utf-8")

    def _find_wfetch_status_guard_line(self, content: str) -> str | None:
        """Findet die Zeile 'wfetch_status = ...' im INV-A-ORDER-4-Guard-Kontext."""
        for line in content.splitlines():
            # Die Guard-Zeile weist wfetch_status zu
            if re.search(r"wfetch_status\s*=", line):
                return line
        return None

    def test_inv_a_order_4_uses_read_bl_block(self):
        """RED-HEBEL (AK-2a): die wfetch.status-Lese-Stelle (Guard, ~Z714) referenziert
        'read_bl_block'.

        IST: 'wfetch_status = BERATER_OUTPUTS.wfetch.status ?? "MISSING"' -> FAIL
        SOLL: 'wfetch_status = manifest_reader.read_bl_block(bl_id, ...)' oder aehnlich.
        """
        content = self._read_a_orchestrate()
        guard_line = self._find_wfetch_status_guard_line(content)

        assert guard_line is not None, (
            "Keine 'wfetch_status = ...'-Zeile in _A_orchestrate.md gefunden — "
            "Guard-Anker fehlt oder umbenannt"
        )

        assert "read_bl_block" in guard_line, (
            f"RED-HEBEL: Guard-Zeile referenziert NICHT 'read_bl_block':\n"
            f"  IST:  {guard_line!r}\n"
            f"  SOLL: Zeile muss 'read_bl_block' enthalten (toleranter Reader)"
        )

    def test_inv_a_order_4_not_bl_folder_only_read(self):
        """RED-HEBEL (AK-2b / Negativ): die Guard-Lese-Stelle ist kein
        bl_folder-only-Direkt-Read mehr (= kein 'BERATER_OUTPUTS.wfetch.status ?? ...'
        ohne read_bl_block-Referenz).

        IST: 'BERATER_OUTPUTS.wfetch.status ?? "MISSING"' ohne read_bl_block -> FAIL
        SOLL: mit read_bl_block (Fallback schon vorhanden, nur verdrahten).
        """
        content = self._read_a_orchestrate()
        guard_line = self._find_wfetch_status_guard_line(content)

        assert guard_line is not None, (
            "Keine 'wfetch_status = ...'-Zeile in _A_orchestrate.md gefunden"
        )

        # Wenn es KEIN read_bl_block hat, aber BERATER_OUTPUTS.wfetch direkt liest:
        # das ist der bl_folder-only-Direkt-Read (IST-Stand) -> FAIL
        if "read_bl_block" not in guard_line:
            # Bestaetigen, dass es ein Direkt-Read ist (IST-Muster)
            is_direct_read = (
                "BERATER_OUTPUTS.wfetch.status" in guard_line
                or "BERATER_OUTPUTS" in guard_line
            )
            if is_direct_read:
                pytest.fail(
                    f"RED-HEBEL: Guard-Zeile ist bl_folder-only-Direkt-Read (kein Fallback):\n"
                    f"  IST:  {guard_line!r}\n"
                    f"  SOLL: 'manifest_reader.read_bl_block(...)' nutzen (toleranter Reader)"
                )
            else:
                # Unbekannte Form — auch nicht gruen
                pytest.fail(
                    f"RED-HEBEL: Guard-Zeile hat KEIN 'read_bl_block' und kein bekanntes Muster:\n"
                    f"  {guard_line!r}"
                )
        # Wenn read_bl_block vorhanden -> PASS (GREEN nach Edit)


# ---------------------------------------------------------------------------
# BEHAVIORAL-TESTS (Characterization read_bl_block — Python-API direkt, tmp_path)
# ---------------------------------------------------------------------------
#
# _parse_field_path-Granularitaet (VERIFIZIERT am echten Reader, Z149-157):
#   'BERATER_OUTPUTS.wfetch.status' -> block='BERATER_OUTPUTS', field='wfetch.status'
#   _read_field_from_manifest sucht dann die Zeile 'wfetch.status: <value>' im Block.
#   Die Fixture schreibt FLACHES YAML: '## BERATER_OUTPUTS\nwfetch.status: DONE\n'
#   (NICHT verschachteltes YAML 'wfetch:\n  status: "DONE"' — das findet der Reader NICHT.)
#
# Diese Tests sollten SCHON JETZT passen (Fallback Z383-391 existiert bereits).
# Sie sind Characterization/Stall-Schutz-Pins (AK-3).

# Fixture-Inhalt: flaches YAML passend zur 2-stufigen _parse_field_path-Semantik
_WFETCH_BLOCK_FLAT = "## BERATER_OUTPUTS\nwfetch.status: DONE\n"


def _write_bl_manifest(vault_root: Path, bl_id: str, content: str) -> None:
    """Schreibt ein per-BL-Manifest: {vault_root}/Backlog/{bl_id}/_manifest.md."""
    bl_folder = vault_root / "Backlog" / bl_id
    bl_folder.mkdir(parents=True, exist_ok=True)
    (bl_folder / "_manifest.md").write_text(content, encoding="utf-8")


def _write_global_manifest(vault_root: Path, content: str) -> None:
    """Schreibt das globale Manifest: {vault_root}/_manifest.md."""
    (vault_root / "_manifest.md").write_text(content, encoding="utf-8")


def test_read_bl_block_finds_wfetch_in_bl_folder(tmp_path):
    """BEHAVIORAL (AK-3a): read_bl_block findet wfetch.status NUR in bl_folder.

    Slot NUR in {bl_folder}/_manifest.md -> read_bl_block findet es via bl_folder-first (Z365-370).
    Characterization-Pin: manifest_reader.py UNVERAENDERT, Fallback existiert bereits.

    field_path='BERATER_OUTPUTS.wfetch.status' -> block='BERATER_OUTPUTS', field='wfetch.status'
    Fixture: flaches '## BERATER_OUTPUTS\\nwfetch.status: DONE\\n'
    """
    # Arrange: Slot NUR in bl_folder, KEIN globales Manifest
    _write_bl_manifest(tmp_path, "BL-474-T", _WFETCH_BLOCK_FLAT)

    # Act: bl_folder-first (Z365-370)
    val = manifest_reader.read_bl_block(
        "BL-474-T", "BERATER_OUTPUTS.wfetch.status", vault_root=tmp_path
    )

    # Assert: Slot gefunden
    assert val == "DONE", (
        f"Erwartet 'DONE' via bl_folder-first (Z365-370), got: {val!r}\n"
        f"Fixture: {_WFETCH_BLOCK_FLAT!r}"
    )


def test_read_bl_block_finds_wfetch_via_global_fallback(tmp_path):
    """BEHAVIORAL (AK-3b): read_bl_block findet wfetch.status via global-legacy-Fallback.

    Slot NUR im globalen {vault_root}/_manifest.md, bl_folder fehlt/leer
    -> read_bl_block findet via Fallback (Z383-391, COMPAT-WARNING auf stderr).
    Characterization-Pin: manifest_reader.py UNVERAENDERT, Fallback existiert bereits.
    """
    # Arrange: Slot NUR global, KEIN bl_folder-Manifest (oder bl_folder-Ordner gar nicht)
    _write_global_manifest(tmp_path, _WFETCH_BLOCK_FLAT)
    # bl_folder existiert NICHT -> _find_bl_folder gibt None zurueck -> direkt Fallback

    # Act: global-legacy-Fallback (Z383-391)
    val = manifest_reader.read_bl_block(
        "BL-474-T-NOFOLDER", "BERATER_OUTPUTS.wfetch.status", vault_root=tmp_path
    )

    # Assert: Slot gefunden via Fallback (COMPAT-WARNING auf stderr — kein Silent)
    assert val == "DONE", (
        f"Erwartet 'DONE' via global-legacy-Fallback (Z383-391), got: {val!r}\n"
        f"Hinweis: COMPAT-WARNING wird auf stderr erwartet (non-silent Fallback)"
    )


# ---------------------------------------------------------------------------
# KANARIEN / REGRESSION-FLOORS
# ---------------------------------------------------------------------------

class TestRegressionFloors:
    """AK-4: Immunsystem-Floor — heute GREEN, durch GREEN-Bau NICHT umkippen."""

    def test_manifest_reader_unchanged(self):
        """KANARIENVOGEL (AK-4a): manifest_reader.py byte-unveraendert (git-diff leer).

        Prueft via 'git diff --numstat -- .claude/scripts/manifest_reader.py'.
        Wenn git nicht verfuegbar oder kein Repo: pytest.skip.
        """
        git_exe = "git"
        manifest_rel = ".claude/scripts/manifest_reader.py"

        try:
            result = subprocess.run(
                [git_exe, "diff", "--numstat", "--", manifest_rel],
                cwd=str(_REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("git nicht verfuegbar — manifest_reader-Unveraendert-Check uebersprungen")

        if result.returncode != 0:
            pytest.skip(
                f"git diff fehlgeschlagen (rc={result.returncode}) — "
                f"kein Git-Repo oder kein Zugriff"
            )

        # git diff --numstat gibt leer aus wenn keine Aenderungen
        diff_output = result.stdout.strip()
        assert diff_output == "", (
            f"KANARIENVOGEL-MISS: manifest_reader.py hat unstaged Aenderungen!\n"
            f"git diff --numstat:\n{diff_output}\n"
            f"manifest_reader.py MUSS byte-unveraendert sein (AK-4a, W4-Falle)"
        )

    def test_manifest_dual_read_floor(self):
        """KANARIENVOGEL (AK-4c): test_manifest_reader_dual_read.py gruen.

        Fuer den RED-Worker: diese Tests laufen SEPARAT via 'py -3 -m pytest
        .claude/scripts/test_manifest_reader_dual_read.py -q' (Floor-Beleg).
        Hier nur ein Smoke-Check: die Test-Datei existiert und ist importierbar.
        """
        dual_read_path = _SCRIPTS_DIR / "test_manifest_reader_dual_read.py"
        assert dual_read_path.exists(), (
            f"KANARIENVOGEL-MISS: test_manifest_reader_dual_read.py fehlt: {dual_read_path}"
        )

    def test_manifest_split_integration_floor(self):
        """KANARIENVOGEL (AK-4c): test_manifest_split_integration.py (falls vorhanden) gruen.

        Smoke-Check: falls die Datei existiert, ist sie vorhanden (Ausfuehrung separat).
        """
        split_path = _SCRIPTS_DIR / "test_manifest_split_integration.py"
        if not split_path.exists():
            pytest.skip("test_manifest_split_integration.py nicht vorhanden — Skip")
        assert split_path.exists()  # redundant, aber explizit fuer den Floor-Check

    def test_wfetch_read_still_global_floor(self):
        """KANARIENVOGEL (AK-4d): _W_fetch-LESE-Verhalten unveraendert (wie AK-1c,
        hier als expliziter Floor — doppelte Absicherung gegen Over-Edit).

        Die Lese-Stellen Z54/Z145 referenzieren {VAULT}/_manifest.md — das BLEIBT.
        """
        assert _W_FETCH_MD.exists(), f"_W_fetch.md nicht gefunden: {_W_FETCH_MD}"
        content = _W_FETCH_MD.read_text(encoding="utf-8")

        # Mindestens eine LESE-Stelle muss {VAULT}/_manifest.md enthalten
        lese_global_hits = [
            line for line in content.splitlines()
            if "{VAULT}/_manifest.md" in line
        ]
        assert len(lese_global_hits) >= 1, (
            "KANARIENVOGEL-MISS: KEIN '{VAULT}/_manifest.md' mehr in _W_fetch.md! "
            "Die LESE-Stellen (Z54/Z145) muessen unveraendert bleiben — "
            "GREEN-Worker hat zu viel normiert (Over-Edit)"
        )


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
