#!/usr/bin/env python3
"""BL-229 AK-F (T10): process_audit.py Dual-Read auf geslimmtem Manifest.

RED (vor Migration): Wenn der BERATER_OUTPUTS-Inhalt fuer die zu auditierende Round
durch den AK-C-Offload in _manifest_history_{date}.md ausgelagert ist (im Manifest
steht nur noch die LETZTE Round), liefert die Manifest-only-Grep ein False-Negative:
  - R1a (batch_modes ohne modusEntscheidung-Berater-Output) feuert faelschlich
  - R5 (patternLibrary 0 Spawns) feuert faelschlich
  - R6 (goldDefine 0 Spawns) feuert faelschlich
-> Verdict RED, obwohl die Phasen GELAUFEN sind (Inhalt nur ausgelagert).

GREEN (nach Migration): process_audit liest Dual (Manifest + History + Pointer),
findet die ausgelagerten Treffer -> GREEN, kein False-Negative (INV-POINTER-1).
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import process_audit as pa


def _bl_folder_with_offloaded_round(round_audit: int) -> Path:
    """Erzeugt einen BL-Folder, dessen Manifest die zu auditierende Round NICHT
    mehr inline traegt (sie ist offloaded) — aber batch_modes referenzieren sie.

    Manifest: batch_modes gesetzt + LETZTE Round (round_audit+1) inline.
    History:  modusEntscheidung/patternLibrary/goldDefine fuer round_audit ausgelagert
              (im kanonischen underscore-round-Format das die Greps matchen).
    """
    d = Path(tempfile.mkdtemp())
    bl = d / "BL-DUALREAD"
    bl.mkdir()

    # Manifest: batch_modes + DF_BATCH_STATE + nur die LETZTE Round inline.
    # (Die letzte Round ist NICHT die auditierte round_audit -> Manifest-Grep
    #  fuer round_audit findet inline NICHTS -> False-Negative ohne Dual-Read.)
    (bl / "_manifest.md").write_text(
        "---\nbl_id: BL-DUALREAD\n---\n\n"
        "## DF_BATCH_STATE\n"
        "batch_modes:\n"
        "  batch_1: M3\n"
        "modus_set_by: _SDF_berater_modusEntscheidung\n\n"
        f"## BERATER_OUTPUTS_modusEntscheidung_round{round_audit + 1}\n\n"
        "```yaml\nmodus: M3\nstatus: DONE\n```\n",
        encoding="utf-8",
    )

    # AK-C-Offload: die fuer round_audit relevanten BERATER_OUTPUTS sind hier
    # (ausgelagert, kanonisches underscore-round-Format wie es die Greps suchen).
    (bl / "_manifest_history_2026-06-10.md").write_text(
        "# Manifest-Historie (ausgelagert 2026-06-10)\n\n"
        f"## BERATER_OUTPUTS.modusEntscheidung_round{round_audit}\n\n"
        "```yaml\nmodus: M2\nstatus: DONE\n```\n\n"
        f"## BERATER_OUTPUTS.patternLibrary_round{round_audit}\n\n"
        "```yaml\npatterns: [P1]\nstatus: DONE\n```\n\n"
        f"## BERATER_OUTPUTS.goldDefine_round{round_audit}\n\n"
        "```yaml\ngold: defined\nstatus: DONE\n```\n",
        encoding="utf-8",
    )
    return bl


class TestProcessAuditDualRead(unittest.TestCase):
    """T10: process_audit GREEN auf geslimmtem Manifest (Inhalt offloaded)."""

    def test_no_false_negative_when_berater_outputs_offloaded(self):
        # Arrange: audit Round 10, deren Berater-Outputs offloaded sind.
        round_audit = 10
        bl = _bl_folder_with_offloaded_round(round_audit)

        # Act
        findings = pa.run_all_checks(str(bl), None, round_audit)
        rule_ids = {f[0] for f in findings}

        # Assert: KEIN False-Negative auf den MANIFEST-GREP-Rules. Die Phasen sind
        # gelaufen (Inhalt offloaded), also duerfen R1a/R5/R6 NICHT feuern.
        # (R4 ist audit-event-basiert, nicht Manifest-Grep -> ausserhalb Dual-Read-Scope.)
        self.assertNotIn("R1a", rule_ids,
                         "R1a darf NICHT feuern: modusEntscheidung ist offloaded, nicht fehlend")
        self.assertNotIn("R5", rule_ids,
                         "R5 darf NICHT feuern: patternLibrary ist offloaded, nicht fehlend")
        self.assertNotIn("R6", rule_ids,
                         "R6 darf NICHT feuern: goldDefine ist offloaded, nicht fehlend")

    def test_inline_path_still_works_backward_compat(self):
        # Arrange: klassisches Manifest OHNE Offload (alles inline) — Backward-Compat.
        d = Path(tempfile.mkdtemp())
        bl = d / "BL-INLINE"
        bl.mkdir()
        (bl / "_manifest.md").write_text(
            "---\nbl_id: BL-INLINE\n---\n\n"
            "## DF_BATCH_STATE\n"
            "batch_modes:\n  batch_1: M3\n"
            "modus_set_by: _SDF_berater_modusEntscheidung\n\n"
            "## BERATER_OUTPUTS.modusEntscheidung_round11\n\n"
            "```yaml\nmodus: M3\nstatus: DONE\n```\n\n"
            "## BERATER_OUTPUTS.patternLibrary_round11\n\n"
            "```yaml\npatterns: [P1]\n```\n\n"
            "## BERATER_OUTPUTS.goldDefine_round11\n\n"
            "```yaml\ngold: x\n```\n",
            encoding="utf-8",
        )

        # Act
        findings = pa.run_all_checks(str(bl), None, 11)
        rule_ids = {f[0] for f in findings}

        # Assert: inline-Treffer weiterhin gefunden (keine R1a/R5/R6).
        self.assertNotIn("R1a", rule_ids)
        self.assertNotIn("R5", rule_ids)
        self.assertNotIn("R6", rule_ids)

    def test_true_positive_still_detected_after_dual_read(self):
        # Arrange: batch_modes gesetzt, ABER modusEntscheidung WEDER inline NOCH offloaded.
        # Dual-Read darf echte Verletzungen NICHT maskieren (Enforcement bleibt scharf).
        d = Path(tempfile.mkdtemp())
        bl = d / "BL-TRUEPOS"
        bl.mkdir()
        (bl / "_manifest.md").write_text(
            "---\nbl_id: BL-TRUEPOS\n---\n\n"
            "## DF_BATCH_STATE\n"
            "batch_modes:\n  batch_1: M3\n",  # kein modusEntscheidung, kein hints/shadow/set_by
            encoding="utf-8",
        )
        # Leeres History (nichts ausgelagert das den Fehler maskiert)
        (bl / "_manifest_history_2026-06-10.md").write_text(
            "# Manifest-Historie (leer)\n", encoding="utf-8"
        )

        # Act
        findings = pa.run_all_checks(str(bl), None, 11)
        rule_ids = {f[0] for f in findings}

        # Assert: R1a UND R1b feuern weiterhin (echte Verletzung bleibt erkannt).
        self.assertIn("R1a", rule_ids,
                     "R1a MUSS feuern: modusEntscheidung wirklich nirgends (kein Masking)")
        self.assertIn("R1b", rule_ids,
                     "R1b MUSS feuern: kein hints/shadow/set_by-Vorgaenger")


if __name__ == "__main__":
    unittest.main(verbosity=2)
