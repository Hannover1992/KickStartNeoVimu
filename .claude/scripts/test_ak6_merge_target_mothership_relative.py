#!/usr/bin/env python3
"""
test_ak6_merge_target_mothership_relative.py — BL-351 batch_3 AK-6 RED-Tests.

AK-6 [Achse 2 / W8, W15]: Handoff-/Merge-Ziel ist Mothership-relativ, NICHT hart "develop".

Spec (BL-351_Spec.md, AK-6):
  Given ein Handoff aus einem nested Worktree mit Mothership auf `roadmap-c`,
  When `merge_target` ermittelt wird,
  Then ist `merge_target = roadmap-c`, NICHT `develop`;
  bei Tiefe 0 bleibt `develop` Default.

Defekt-Ort: `worktree_aware_params.py` — es fehlt eine Funktion `resolve_merge_target()`
  (oder aequivalent), die `get_mothership_branch()` befragt statt "develop" hart zu liefern.
  `session_params_resolver.FRAMEWORK_DEFAULTS["merge_target"]["value"] == "develop"` ist der
  statische Fallback — korrekt NUR fuer Tiefe 0. Bei Tiefe > 0 muss `get_mothership_branch()`
  befragt werden (SA-3, F-10).

RED-Erwartung: ImportError (Funktion existiert noch nicht) ODER AssertionError
  (Funktion liefert "develop" statt Mothership-Branch).

Alle Tests testen AUSSCHLIESSLICH die merge_target-Ableitungslogik des AUFRUFERS
(nicht merge_seam.merge_exec selbst — bereits parametrisiert, W15).

Regeln: NUR Tests. KEINE Impl. RED!=GREEN (RED-Worker != GREEN-Worker).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

# ---------------------------------------------------------------------------
# Import-Ziel: resolve_merge_target aus worktree_aware_params.
# Diese Funktion EXISTIERT NOCH NICHT → Import-RED.
# Sobald GREEN-Worker sie implementiert, aendern sich die Tests von ImportError
# auf Verhaltenspruefung — dann gelten die assert-basierten Tests.
# ---------------------------------------------------------------------------
try:
    from worktree_aware_params import resolve_merge_target  # type: ignore[attr-defined]
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


def _mk_subprocess_result(stdout: str, returncode: int = 0) -> MagicMock:
    """Erzeugt ein subprocess.CompletedProcess-Mock."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


# ---------------------------------------------------------------------------
# Hilfsfunktion: resolve_merge_target MUSS importierbar sein.
# ---------------------------------------------------------------------------

class TestAK6ImportGuard(unittest.TestCase):
    """Vorab-Guard: resolve_merge_target muss in worktree_aware_params existieren."""

    def test_ak6_resolve_merge_target_importable(self):
        """AK-6 RED: resolve_merge_target() muss aus worktree_aware_params importierbar sein.

        ERWARTET FEHLSCHLAG (RED): Funktion existiert noch nicht → ImportError-Pfad.
        GREEN-Worker implementiert die Funktion; dann wird dieser Test gruen.
        """
        self.assertTrue(
            _IMPORT_OK,
            "resolve_merge_target ist NICHT in worktree_aware_params exportiert. "
            "GREEN-Worker muss resolve_merge_target(cwd=None) implementieren."
        )


# ---------------------------------------------------------------------------
# AK-6 Kern-Tests: Tiefe 0 = "develop", Tiefe > 0 = Mothership-Branch
# ---------------------------------------------------------------------------

@unittest.skipUnless(_IMPORT_OK, "resolve_merge_target nicht importierbar — Import-RED")
class TestAK6MergeTargetMothershipRelative(unittest.TestCase):
    """AK-6: merge_target wird Mothership-relativ abgeleitet."""

    def test_ak6_merge_target_depth_0_returns_develop(self):
        """AK-6 / SA-3: Bei Tiefe 0 (Mothership = aktueller Root) → 'develop' als Default.

        Tiefe 0 bedeutet: cwd IST die Mothership. Ergebnis darf 'develop' sein,
        aber NICHT weil hardkodiert — sondern weil Mothership-Branch 'develop' ist
        (oder Fallback auf Default). Test monkeypatcht resolve_nesting_depth=0
        und get_mothership_branch=None (kein Branch ermittelbar → Default).
        """
        with patch("worktree_aware_params.resolve_nesting_depth", return_value=0):
            with patch("worktree_aware_params.get_mothership_branch", return_value=None):
                result = resolve_merge_target()
        self.assertEqual(
            result, "develop",
            f"Bei Tiefe 0 und keinem Mothership-Branch → Default 'develop' erwartet, "
            f"bekam: {result!r}"
        )

    def test_ak6_merge_target_depth_1_returns_mothership_branch(self):
        """AK-6 KERN: Bei Tiefe 1 (nested Worktree) → Mothership-Branch, NICHT 'develop'.

        Mothership ist auf Branch 'roadmap-c' → merge_target = 'roadmap-c'.
        """
        with patch("worktree_aware_params.resolve_nesting_depth", return_value=1):
            with patch("worktree_aware_params.get_mothership_branch", return_value="roadmap-c"):
                result = resolve_merge_target()
        self.assertEqual(
            result, "roadmap-c",
            f"Bei Tiefe 1 und Mothership-Branch='roadmap-c' → 'roadmap-c' erwartet, "
            f"bekam: {result!r}"
        )

    def test_ak6_merge_target_nested_depth_2_returns_mothership_branch(self):
        """AK-6: Bei Tiefe 2 (doppelt nested) → Mothership-Branch, NICHT 'develop'."""
        with patch("worktree_aware_params.resolve_nesting_depth", return_value=2):
            with patch("worktree_aware_params.get_mothership_branch", return_value="feature/lane-b"):
                result = resolve_merge_target()
        self.assertNotEqual(
            result, "develop",
            "Bei Tiefe 2 darf merge_target NICHT hart 'develop' sein."
        )
        self.assertEqual(
            result, "feature/lane-b",
            f"Bei Tiefe 2 und Mothership-Branch='feature/lane-b' → 'feature/lane-b' erwartet, "
            f"bekam: {result!r}"
        )

    def test_ak6_merge_target_not_hardcoded_develop_at_depth_1(self):
        """AK-6 CRITICAL: Bei Tiefe 1 darf merge_target NIEMALS hart 'develop' sein.

        Auch wenn get_mothership_branch() 'develop' liefert (Mothership auf develop-Branch),
        muss der Weg ueber get_mothership_branch() fuehren, NICHT ueber eine Konstante.
        Test differenziert: Mothership-Branch='roadmap-c' → darf NICHT 'develop' zurueck.
        """
        with patch("worktree_aware_params.resolve_nesting_depth", return_value=1):
            with patch("worktree_aware_params.get_mothership_branch", return_value="roadmap-c"):
                result = resolve_merge_target()
        self.assertNotEqual(
            result, "develop",
            "Bei depth=1 und Mothership-Branch='roadmap-c': merge_target='develop' gefunden. "
            "Defekt: hardkodierter 'develop'-Wert — muss get_mothership_branch() befragt werden."
        )

    def test_ak6_merge_target_depth_0_mothership_branch_known_uses_it(self):
        """AK-6 / SA-3: Bei Tiefe 0 UND bekanntem Mothership-Branch → Mothership-Branch verwenden.

        SA-3: 'develop nur als Default bei Tiefe 0' bedeutet Fallback, nicht Zwang.
        Wenn get_mothership_branch() bei Tiefe 0 einen Branch liefert, darf dieser
        genutzt werden (tiefen-agnostisch).
        """
        with patch("worktree_aware_params.resolve_nesting_depth", return_value=0):
            with patch("worktree_aware_params.get_mothership_branch", return_value="roadmap-c"):
                result = resolve_merge_target()
        # Bei Tiefe 0 + bekanntem Mothership-Branch: Mothership-Branch verwenden
        self.assertEqual(
            result, "roadmap-c",
            f"Bei Tiefe 0 und bekanntem Mothership-Branch='roadmap-c' → 'roadmap-c' erwartet, "
            f"bekam: {result!r}. SA-3: develop nur als Fallback wenn kein Branch ermittelbar."
        )

    def test_ak6_get_mothership_branch_is_called_at_depth_1(self):
        """AK-6 MECHANISMUS: get_mothership_branch() MUSS bei Tiefe > 0 aufgerufen werden.

        Prueft dass die Implementierung tatsaechlich get_mothership_branch() konsultiert
        und nicht einfach den session_params_resolver-Default zurueckgibt.
        """
        call_log: list[str] = []

        def tracking_get_mothership_branch() -> str:
            call_log.append("called")
            return "roadmap-c"

        with patch("worktree_aware_params.resolve_nesting_depth", return_value=1):
            with patch(
                "worktree_aware_params.get_mothership_branch",
                side_effect=tracking_get_mothership_branch,
            ):
                resolve_merge_target()

        self.assertGreater(
            len(call_log), 0,
            "get_mothership_branch() wurde bei depth=1 NICHT aufgerufen. "
            "Defekt: merge_target wird ohne Mothership-Abfrage bestimmt."
        )


# ---------------------------------------------------------------------------
# AK-6 Integration: merge_seam.merge_exec bekommt Mothership-Branch als Ziel
# ---------------------------------------------------------------------------

@unittest.skipUnless(_IMPORT_OK, "resolve_merge_target nicht importierbar — Import-RED")
class TestAK6MergeSeamCallerIntegration(unittest.TestCase):
    """AK-6 Integration: der Aufrufer von merge_seam uebergibt den Mothership-Branch."""

    def test_ak6_merge_exec_receives_mothership_branch_not_develop(self):
        """AK-6 Integration: merge_seam.merge_exec bekommt 'roadmap-c', nicht 'develop'.

        Simuliert den typischen Aufrufer-Flow: resolve_merge_target() wird aufgerufen,
        Ergebnis wird an merge_seam.merge_exec() weitergegeben. Das merge_target-Argument
        muss den Mothership-Branch enthalten, nicht 'develop'.
        """
        import merge_seam  # bereits implementiert (BL-425)

        captured_merge_target: list[str] = []

        def capturing_merge_exec(current_branch, merge_target, *, run=None):
            captured_merge_target.append(merge_target)
            m = MagicMock()
            m.returncode = 0
            m.stdout = "fast-forward"
            m.stderr = ""
            return merge_seam.merge_exec.__wrapped__(current_branch, merge_target, run=lambda *a, **kw: m) \
                if hasattr(merge_seam.merge_exec, "__wrapped__") else {
                    "status": "merged",
                    "returncode": 0,
                    "stdout": "fast-forward",
                    "stderr": "",
                    "merge_target": merge_target,
                }

        with patch("worktree_aware_params.resolve_nesting_depth", return_value=1):
            with patch("worktree_aware_params.get_mothership_branch", return_value="roadmap-c"):
                derived_target = resolve_merge_target()

        # Simuliere Aufrufer: uebergibt derived_target an merge_exec
        capturing_merge_exec("worktree-branch/BL-351", derived_target)

        self.assertEqual(
            captured_merge_target[0], "roadmap-c",
            f"merge_exec erhielt merge_target={captured_merge_target[0]!r}, "
            f"erwartet 'roadmap-c'. Defekt im Aufrufer."
        )
        self.assertNotEqual(
            captured_merge_target[0], "develop",
            "merge_exec erhielt 'develop' statt Mothership-Branch 'roadmap-c'."
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
