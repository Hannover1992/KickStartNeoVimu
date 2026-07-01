#!/usr/bin/env python3
"""
BL-387 RED-Tests: Consumer-Wiring — K-Score + akExtraktion auf truth_resolver/truth_consume.

RED-Hebel (muessen jetzt FAILEN — IST-Stand):
- test_kscore_references_truth_consume: 0 truth_consume in _K_score.md -> FAIL
- test_akextraktion_references_truth_resolver: 0 resolve in _A_berater_akExtraktion.md SCHRITT 3 -> FAIL
- test_both_skills_backward_compat_marker: kein backward-compat-Marker in beiden Skills -> FAIL
- test_resolve_source_atomic_first_characterization: Test fehlend (RED=fehlend) -> FAIL

Kanarien / Regression-Floors (muessen JETZT SCHON passen — bleiben GREEN durch GREEN-Bau):
- test_kscore_score_aggregate_canary: Score-Aggregat (x 0.40 / x 0.35 / x 0.25) present
- test_akextraktion_source_w_canary: source_w present
- test_truth_resolver_unchanged: truth_resolver.py byte-unveraendert (git diff leer)
- test_no_atom_writes_no_views: keine neuen truth/*.md / keine View-Files im git diff
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Pfad-Anker: Skill-Dateien + truth_resolver relativ zu dieser Datei
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent.absolute()  # .claude/scripts/
_CLAUDE_DIR = _SCRIPTS_DIR.parent                 # .claude/
_REPO_ROOT = _CLAUDE_DIR.parent                   # OmniCommand-wtA/
_COMMANDS_DIR = _CLAUDE_DIR / "commands"

_KSCORE_MD = _COMMANDS_DIR / "_K_score.md"
_AKEXTRAKTION_MD = _COMMANDS_DIR / "_A_berater_akExtraktion.md"
_TRUTH_RESOLVER_PY = _SCRIPTS_DIR / "truth_resolver.py"

# ---------------------------------------------------------------------------
# Hilfsfunktion: SCHRITT-3-Block aus _A_berater_akExtraktion.md extrahieren
# ---------------------------------------------------------------------------

def _extract_schritt3_block(text: str) -> str:
    """Extrahiert den Text zwischen 'SCHRITT 3:' und dem naechsten 'SCHRITT' Heading."""
    pat = re.compile(r"SCHRITT 3:.*?(?=SCHRITT \d+:|\Z)", re.S)
    m = pat.search(text)
    return m.group(0) if m else ""


# ---------------------------------------------------------------------------
# STRUKTUR-TESTS (RED-Hebel)
# ---------------------------------------------------------------------------

class TestStructuralKScore:
    """AK-1: _K_score.md muss an Resolve-Stellen truth_consume/truth_resolver/resolve referenzieren."""

    def test_kscore_references_truth_consume(self):
        """RED-HEBEL: _K_score.md enthaelt 'truth_consume' an min. 1 Resolve-Stelle.
        IST: Grep=0 truth_consume -> FAIL."""
        assert _KSCORE_MD.exists(), f"_K_score.md nicht gefunden: {_KSCORE_MD}"
        content = _KSCORE_MD.read_text(encoding="utf-8", errors="replace")
        # Resolve-Stellen: truth_consume ODER truth_resolver (mindestens 1 Vorkommen)
        resolve_terms = re.compile(r"truth_consume|truth_resolver")
        hits = resolve_terms.findall(content)
        assert len(hits) >= 1, (
            f"_K_score.md enthaelt 0 Treffer fuer 'truth_consume|truth_resolver' "
            f"an den 4 Resolve-Stellen (E02/D03/model_refs_status/SRS-Block). "
            f"IST: Model.md frei gelesen (kein resolve). AK-1 RED."
        )


class TestStructuralAkExtraktion:
    """AK-2: _A_berater_akExtraktion.md SCHRITT 3 muss truth_resolver/resolve_truth_refs referenzieren."""

    def test_akextraktion_references_truth_resolver(self):
        """RED-HEBEL: SCHRITT-3-Block enthaelt 'resolve_truth_refs' oder 'truth_resolver'.
        IST: Z166 Read(model_path) + Z169 FOR Pattern 'W-\\d+' (kein resolve) -> FAIL."""
        assert _AKEXTRAKTION_MD.exists(), f"_A_berater_akExtraktion.md nicht gefunden: {_AKEXTRAKTION_MD}"
        content = _AKEXTRAKTION_MD.read_text(encoding="utf-8", errors="replace")
        schritt3 = _extract_schritt3_block(content)
        assert schritt3, "_A_berater_akExtraktion.md: 'SCHRITT 3:' Block nicht gefunden"
        resolve_pat = re.compile(r"resolve_truth_refs|truth_resolver")
        hits = resolve_pat.findall(schritt3)
        assert len(hits) >= 1, (
            f"SCHRITT-3-Block enthaelt 0 Treffer fuer 'resolve_truth_refs|truth_resolver'. "
            f"IST: Read(model_path) + W-\\d+-Regex (kein resolve). AK-2 RED.\n"
            f"SCHRITT-3-Block (Auszug): {schritt3[:300]!r}"
        )


class TestStructuralBackwardCompatMarker:
    """AK-3: BEIDE Skills tragen den backward-compat-Marker."""

    def test_both_skills_backward_compat_marker(self):
        """RED-HEBEL: BEIDE Skills enthalten 'source=atomic' UND ('backward-compat' ODER 'legacy-fallback').
        IST: kein Marker in beiden Skills (Grep=0) -> FAIL."""
        assert _KSCORE_MD.exists(), f"_K_score.md nicht gefunden: {_KSCORE_MD}"
        assert _AKEXTRAKTION_MD.exists(), f"_A_berater_akExtraktion.md nicht gefunden: {_AKEXTRAKTION_MD}"

        kscore_content = _KSCORE_MD.read_text(encoding="utf-8", errors="replace")
        akext_content = _AKEXTRAKTION_MD.read_text(encoding="utf-8", errors="replace")

        atomic_pat = re.compile(r"source=atomic")
        compat_pat = re.compile(r"backward-compat|legacy-fallback|source=legacy")

        # _K_score.md muss BEIDE Teile enthalten
        kscore_has_atomic = bool(atomic_pat.search(kscore_content))
        kscore_has_compat = bool(compat_pat.search(kscore_content))

        # _A_berater_akExtraktion.md muss BEIDE Teile enthalten
        akext_has_atomic = bool(atomic_pat.search(akext_content))
        akext_has_compat = bool(compat_pat.search(akext_content))

        errors = []
        if not kscore_has_atomic:
            errors.append("_K_score.md: 'source=atomic' fehlt")
        if not kscore_has_compat:
            errors.append("_K_score.md: 'backward-compat' / 'legacy-fallback' / 'source=legacy' fehlt")
        if not akext_has_atomic:
            errors.append("_A_berater_akExtraktion.md: 'source=atomic' fehlt")
        if not akext_has_compat:
            errors.append("_A_berater_akExtraktion.md: 'backward-compat' / 'legacy-fallback' / 'source=legacy' fehlt")

        assert not errors, (
            f"backward-compat-Marker fehlt in Skills:\n"
            + "\n".join(f"  - {e}" for e in errors)
            + "\nIST: kein Marker in beiden Skills. AK-3 RED."
        )


# ---------------------------------------------------------------------------
# BEHAVIORAL characterization (RED=fehlend -> nach GREEN gruen)
# ---------------------------------------------------------------------------

class TestBehavioralResolveCharacterization:
    """AK-3b: truth_resolver.resolve() source=atomic bei Atom, source=legacy sonst."""

    def test_resolve_source_atomic_first_characterization(self, tmp_path):
        """Behavioral characterization (AK-3b):
        - NUR Alt-Model (HEADING-Format) -> resolve("W01") -> source == 'legacy' (backward-compat)
        - Nach Atom-Anlage ({bl_folder}/2_Model/truths/W01.md, type:truth) -> source == 'atomic'

        truth_resolver.py UNVERAENDERT (READ-ONLY Charakterisierung — beschreibt IST-Verhalten).

        Atom-Erkennung laut _find_atomic (truth_resolver.py:124-131):
          _model_dirs(bl_folder) sucht bl_folder/2_Model/, bl_folder/Model/, bl_folder/Models/, bl_folder selbst.
          Atom: {model_dir}/truths/{local_id}.md (muss existieren und als Datei vorliegen).
          Legacy: _scan_models_for_wknot sucht *Model*.md / *.md im model_dir,
                  extract_wknot_legacy findet ^#{1,6}[ \\t]+W01\\b (HEADING-Format).
        """
        # sys.path einfuegen damit truth_resolver importierbar ist
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import truth_resolver  # noqa: PLC0415

        # --- Schritt 1: NUR legacy Alt-Model (HEADING-Format) anlegen ---
        bl_folder = tmp_path / "Backlog" / "BL-X"
        model_dir = bl_folder / "2_Model"
        model_dir.mkdir(parents=True, exist_ok=True)

        legacy_model_text = (
            "---\ntype: model\n---\n\n"
            "## W01 Beispiel-Wahrheit (HEADING-Format)\n"
            "status: OFFEN\n"
            "Body-Text der legacy-Wahrheit.\n"
        )
        (model_dir / "BL-X_Model.md").write_text(legacy_model_text, encoding="utf-8")

        # resolve ohne Atom -> MUSS source=legacy sein (backward-compat == Vorher-Verhalten)
        r1 = truth_resolver.resolve("W01", bl_folder=bl_folder)
        assert r1.found is True, (
            f"resolve('W01', bl_folder={bl_folder}) sollte found=True liefern "
            f"(Alt-Model mit HEADING '## W01' vorhanden), war: found={r1.found}, note={r1.note!r}"
        )
        assert r1.source == truth_resolver.SOURCE_LEGACY, (
            f"resolve ohne Atom muss source='legacy' liefern (backward-compat), "
            f"war: source={r1.source!r}, note={r1.note!r}"
        )

        # --- Schritt 2: Atom anlegen -> atomic-first ---
        # _find_atomic sucht: {bl_folder}/2_Model/truths/W01.md
        truths_dir = model_dir / "truths"
        truths_dir.mkdir(parents=True, exist_ok=True)
        atom_text = (
            "---\n"
            "id: W01\n"
            "type: truth\n"
            "status: OFFEN\n"
            "text: Beispiel-Atom\n"
            "---\n"
            "Atom-Body.\n"
        )
        (truths_dir / "W01.md").write_text(atom_text, encoding="utf-8")

        # resolve MIT Atom -> MUSS source=atomic sein (atomic-first)
        r2 = truth_resolver.resolve("W01", bl_folder=bl_folder)
        assert r2.found is True, (
            f"resolve('W01') mit Atom ({truths_dir / 'W01.md'}) sollte found=True liefern, "
            f"war: found={r2.found}, note={r2.note!r}"
        )
        assert r2.source == truth_resolver.SOURCE_ATOMIC, (
            f"resolve mit Atom muss source='atomic' liefern (atomic-first), "
            f"war: source={r2.source!r}, note={r2.note!r}"
        )


# ---------------------------------------------------------------------------
# KANARIEN / REGRESSION-FLOORS (heute GREEN, muessen GREEN bleiben)
# ---------------------------------------------------------------------------

class TestCanaryFloors:
    """AK-4: Regression-Floor — heute GREEN, durch GREEN-Bau NICHT umkippen."""

    def test_kscore_score_aggregate_canary(self):
        """KANARIENVOGEL: _K_score.md Score-Aggregat (x 0.40 / x 0.35 / x 0.25) unberuehrt.
        GREEN heute (Z840-849). Der GREEN-Worker darf diesen Block NICHT mit-editieren."""
        assert _KSCORE_MD.exists(), f"_K_score.md nicht gefunden: {_KSCORE_MD}"
        content = _KSCORE_MD.read_text(encoding="utf-8", errors="replace")
        assert re.search(r"× 0\.40", content) or re.search(r"x 0\.40", content), (
            "_K_score.md: Score-Aggregat 'x 0.40' fehlt (geloeschter Logik-Block = Over-Edit)"
        )
        assert re.search(r"× 0\.35", content) or re.search(r"x 0\.35", content), (
            "_K_score.md: Score-Aggregat 'x 0.35' fehlt (geloeschter Logik-Block = Over-Edit)"
        )
        assert re.search(r"× 0\.25", content) or re.search(r"x 0\.25", content), (
            "_K_score.md: Score-Aggregat 'x 0.25' fehlt (geloeschter Logik-Block = Over-Edit)"
        )

    def test_akextraktion_source_w_canary(self):
        """KANARIENVOGEL: _A_berater_akExtraktion.md source_w present.
        GREEN heute (Z239). source_w-Erste-Ref-Semantik darf durch GREEN-Bau NICHT entfernt werden."""
        assert _AKEXTRAKTION_MD.exists(), f"_A_berater_akExtraktion.md nicht gefunden: {_AKEXTRAKTION_MD}"
        content = _AKEXTRAKTION_MD.read_text(encoding="utf-8", errors="replace")
        assert "source_w" in content, (
            "_A_berater_akExtraktion.md: 'source_w' fehlt (source_w-Block geloescht = Over-Edit)"
        )

    def test_truth_resolver_unchanged(self):
        """KANARIENVOGEL: truth_resolver.py byte-unveraendert (git diff --numstat leer).
        GREEN heute. truth_resolver.py ist READ-ONLY Substrat — darf durch KEINEN Worker editiert werden."""
        try:
            result = subprocess.run(
                ["git", "diff", "--numstat",
                 str(_TRUTH_RESOLVER_PY.relative_to(_REPO_ROOT))],
                cwd=str(_REPO_ROOT),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                pytest.skip(f"git nicht verfuegbar oder Fehler: {result.stderr!r}")
            diff_output = result.stdout.strip()
            assert diff_output == "", (
                f"truth_resolver.py wurde modifiziert (git diff nicht leer):\n{diff_output}\n"
                f"AK-4: Substrat MUSS byte-unveraendert bleiben."
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            pytest.skip(f"git nicht ausfuehrbar: {exc}")

    def test_no_atom_writes_no_views(self):
        """KANARIENVOGEL: keine neuen 2_Model/truths/*.md im Repo + truth_consume.py/truth_srs.py unveraendert.
        GREEN heute. Out-of-Scope-Fence (AK-4): kein Atom-Write (C), kein View (B), Substrat READ-ONLY."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=A"],
                cwd=str(_REPO_ROOT),
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                pytest.skip(f"git nicht verfuegbar: {result.stderr!r}")
            new_files = result.stdout.strip().splitlines()
            atom_writes = [f for f in new_files if re.search(r"2_Model[/\\]truths[/\\]", f)]
            assert atom_writes == [], (
                f"Neue Atom-Dateien gefunden (Scope-Creep, AK-4 C-Fence):\n"
                + "\n".join(f"  {f}" for f in atom_writes)
            )
            # Zusaetzlich: truth_consume.py + truth_srs.py unveraendert
            for substrat in ("truth_consume.py", "truth_srs.py"):
                result2 = subprocess.run(
                    ["git", "diff", "--numstat", f".claude/scripts/{substrat}"],
                    cwd=str(_REPO_ROOT),
                    capture_output=True, text=True, timeout=30,
                )
                if result2.returncode == 0:
                    assert result2.stdout.strip() == "", (
                        f"{substrat} wurde modifiziert (git diff nicht leer) — Substrat READ-ONLY (AK-4)."
                    )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            pytest.skip(f"git nicht ausfuehrbar: {exc}")


# ---------------------------------------------------------------------------
# Entry-Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
