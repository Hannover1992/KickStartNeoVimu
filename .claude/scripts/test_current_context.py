#!/usr/bin/env python3
"""
test_current_context.py — BL-317 SB-1 (AK-2) current-context-Härtung.

RED-first TDD. Härtet die load-bearing current_context-Pfad-Auflösung OHNE
Backward-Compat zu brechen (INV-G3-2, BL-310-Klasse: 3× Live-Pipeline-Fail an
genau dieser Fehlerklasse).

Behavior-Contract (NON-WEAKENING):
  (a) __file__-Anker: subprocess-Aufrufe von resolve_vault_root.py / resolve_bl_path.py
      müssen über einen __file__-basierten Repo-Root-Anker laufen, sodass current_context
      bei CWD≠Repo-Root NICHT mehr still bricht (vorher: null-Felder).
  (b) bl_id-Regex additiv: Motor-Branch-Schemata ({slug}_B-N) liefern die echte bl_id
      und missdeuten NIE den _B-N-Suffix als eigene bl_id. ADDITIV — bestehende
      BL-{N}/{PREFIX}-{N}-Treffer dürfen NICHT regredieren.
  (c) fail-safe BEWAHREN: Exception → valides null-JSON, KEIN Hard-Crash (INV-G3-2).
  (d) Non-Regression: Standard-Aufruf (CWD=Repo-Root) liefert dieselben Felder wie vorher.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import current_context  # noqa: E402  (in-process Tests)

SCRIPT = Path(__file__).resolve().parent / "current_context.py"
REPO_ROOT = SCRIPT.resolve().parents[2]
PY = sys.executable

# Feld-Set, das der Standard-Aufruf liefern MUSS (Non-Regression-Snapshot-Keys).
EXPECTED_KEYS = {
    "branch", "bl_id", "vault_root", "bl_folder", "cwd", "project_name",
    "factory_manifest_path", "factory_manifest_exists",
    "legacy_manifest_path", "manifest_mode",
    "bl_manifest_path", "bl_manifest_exists",
}


def _run(cwd: str, fmt: str = "json") -> subprocess.CompletedProcess:
    """Ruft current_context.py als Subprozess auf — absoluter Skript-Pfad, definiertes CWD."""
    return subprocess.run(
        [PY, str(SCRIPT), f"--format={fmt}"],
        capture_output=True, text=True, cwd=cwd, timeout=30,
    )


def _parse_json_stdout(stdout: str) -> dict:
    """
    Extrahiert das JSON-Objekt aus stdout (Deprecation-Warnings gehen auf stderr,
    aber wir sind robust: nimm ab der ersten '{').
    """
    idx = stdout.find("{")
    assert idx != -1, f"kein JSON in stdout: {stdout!r}"
    return json.loads(stdout[idx:])


class TestAFileAnchor(unittest.TestCase):
    """(a) __file__-Anker: CWD≠Repo-Root darf NICHT mehr still brechen."""

    def test_a_cwd_not_repo_root_resolves_vault_root(self):
        """Aus einem tmp-dir aufgerufen → vault_root MUSS korrekt aufgelöst sein (vorher: None)."""
        with tempfile.TemporaryDirectory() as tmp:
            cp = _run(tmp, "json")
            self.assertEqual(cp.returncode, 0, f"stderr={cp.stderr!r}")
            ctx = _parse_json_stdout(cp.stdout)
            self.assertIsNotNone(
                ctx["vault_root"],
                "vault_root darf bei CWD≠Repo-Root NICHT None sein (AK-2a: __file__-Anker)",
            )

    def test_a_cwd_not_repo_root_matches_repo_root_result(self):
        """vault_root aus tmp-dir == vault_root aus Repo-Root (Anker, nicht CWD)."""
        from_root = _parse_json_stdout(_run(str(REPO_ROOT), "json").stdout)
        with tempfile.TemporaryDirectory() as tmp:
            from_tmp = _parse_json_stdout(_run(tmp, "json").stdout)
        self.assertEqual(
            from_tmp["vault_root"], from_root["vault_root"],
            "vault_root muss CWD-unabhängig (über __file__-Anker) aufgelöst werden",
        )

    def test_a_cwd_field_still_reflects_actual_cwd(self):
        """cwd-Feld MUSS weiterhin das echte CWD reflektieren (nicht den Anker)."""
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _parse_json_stdout(_run(tmp, "json").stdout)
            self.assertEqual(
                Path(ctx["cwd"]).resolve(), Path(tmp).resolve(),
                "cwd-Feld muss das tatsächliche Arbeitsverzeichnis bleiben",
            )


class TestBBlIdRegex(unittest.TestCase):
    """(b) bl_id-Regex additiv: Motor-Branch {slug}_B-N korrekt + non-regression."""

    # --- ADDITIV: Motor-Branch-Schemata liefern die echte bl_id ---
    def test_b_motor_branch_yields_real_bl_id(self):
        self.assertEqual(
            current_context.detect_bl_id("feature/BL-317-current-context-haertung_B-3"),
            "BL-317",
        )

    def test_b_motor_branch_short_batch_index(self):
        self.assertEqual(
            current_context.detect_bl_id("feature/BL-317-haertung_B-12"),
            "BL-317",
        )

    def test_b_motor_branch_prefix_scheme(self):
        self.assertEqual(
            current_context.detect_bl_id("feature/DCSRE-486-frontend_B-2"),
            "DCSRE-486",
        )

    # --- KERN-DEFEKT: der _B-N Motor-Suffix darf NIE als bl_id missdeutet werden ---
    def test_b_bare_motor_suffix_not_misread_as_bl_id(self):
        """'B-3' allein ist ein Motor-Suffix, KEINE bl_id."""
        self.assertNotEqual(
            current_context.detect_bl_id("B-3"), "B-3",
            "_B-N-Motor-Suffix darf NICHT als bl_id missdeutet werden (AK-2b)",
        )

    def test_b_leading_motor_suffix_not_misread(self):
        """'feature/B-3-worktree' → der B-3-Token ist Motor-Suffix, keine bl_id."""
        self.assertNotEqual(
            current_context.detect_bl_id("feature/B-3-worktree"), "B-3",
            "B-N-Token darf NICHT als bl_id missdeutet werden (AK-2b)",
        )

    def test_b_lowercase_slug_motor_suffix_not_misread(self):
        """'feature/some-slug_B-3' → KEINE bl_id (kein echtes BL/PREFIX), NIE 'B-3'."""
        self.assertNotEqual(
            current_context.detect_bl_id("feature/some-slug_B-3"), "B-3",
        )

    # --- NON-REGRESSION: bestehende BL-{N} / {PREFIX}-{N} Treffer bleiben ---
    def test_b_regression_plain_bl(self):
        self.assertEqual(current_context.detect_bl_id("feature/BL-317-foo"), "BL-317")

    def test_b_regression_plain_bl_no_suffix(self):
        self.assertEqual(current_context.detect_bl_id("feature/BL-317"), "BL-317")

    def test_b_regression_prefix_scheme(self):
        self.assertEqual(current_context.detect_bl_id("feature/DCSRE-486-bar"), "DCSRE-486")

    def test_b_regression_no_match_branch(self):
        self.assertIsNone(current_context.detect_bl_id("feature/bdf-2026-05-14"))

    def test_b_regression_none_branch(self):
        self.assertIsNone(current_context.detect_bl_id(None))

    def test_b_regression_env_override_wins(self):
        old = os.environ.get("CLAUDE_BL_ID")
        os.environ["CLAUDE_BL_ID"] = "BL-999"
        try:
            self.assertEqual(
                current_context.detect_bl_id("feature/BL-317-foo"), "BL-999",
                "ENV CLAUDE_BL_ID muss weiterhin Vorrang haben",
            )
        finally:
            if old is None:
                del os.environ["CLAUDE_BL_ID"]
            else:
                os.environ["CLAUDE_BL_ID"] = old


class TestCFailSafe(unittest.TestCase):
    """(c) fail-safe BEWAHREN (INV-G3-2): kaputter Kontext → valides null-JSON, KEIN Crash."""

    def test_c_gather_exception_yields_valid_null_json(self):
        """gather() wirft → main() liefert valides JSON mit allen Feldern null + exit 0."""
        orig = current_context.gather

        def boom():
            raise RuntimeError("simulierter gather-Crash")

        current_context.gather = boom
        try:
            import io
            buf = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = buf
            try:
                rc = current_context.main(["current_context.py", "--format=json"])
            finally:
                sys.stdout = old_stdout
        finally:
            current_context.gather = orig

        self.assertEqual(rc, 0, "fail-safe MUSS exit 0 liefern, kein Hard-Crash")
        out = buf.getvalue()
        self.assertTrue(out.strip(), "stdout darf NIE leer sein (BL-310-Klasse)")
        ctx = json.loads(out)  # MUSS valides JSON sein
        self.assertIsNone(ctx["branch"])
        self.assertIsNone(ctx["bl_id"])
        self.assertIsNone(ctx["vault_root"])
        self.assertIn("_error", ctx)

    def test_c_never_empty_stdout_on_crash(self):
        """Letzte Verteidigung: selbst ein harter Crash → '{}' statt leerem stdout."""
        cp = _run(str(REPO_ROOT), "json")
        self.assertTrue(cp.stdout.strip(), "stdout darf NIE leer sein")
        # parsebar
        _parse_json_stdout(cp.stdout)


class TestDNonRegression(unittest.TestCase):
    """(d) Standard-Aufruf (CWD=Repo-Root) liefert exakt dieselben Felder/Werte wie vorher."""

    def test_d_repo_root_has_all_expected_keys(self):
        ctx = _parse_json_stdout(_run(str(REPO_ROOT), "json").stdout)
        self.assertEqual(set(ctx.keys()), EXPECTED_KEYS)

    def test_d_repo_root_core_fields_correct(self):
        ctx = _parse_json_stdout(_run(str(REPO_ROOT), "json").stdout)
        # cwd == repo root
        self.assertEqual(Path(ctx["cwd"]).resolve(), REPO_ROOT)
        # vault_root aufgelöst (nicht None) + project_name abgeleitet
        self.assertIsNotNone(ctx["vault_root"])
        self.assertNotEqual(ctx["project_name"], "Unknown")

    def test_d_kv_format_still_works(self):
        cp = _run(str(REPO_ROOT), "kv")
        self.assertEqual(cp.returncode, 0)
        # kv-Output enthält die Kern-Keys
        for key in ("branch=", "bl_id=", "vault_root=", "cwd=", "project_name="):
            self.assertIn(key, cp.stdout, f"kv-Output fehlt '{key}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
