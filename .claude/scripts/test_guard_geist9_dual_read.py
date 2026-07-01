#!/usr/bin/env python3
"""BL-229 AK-F (T11): guard_geist9_post_sdf.py grep-safe nach Offload-Split.

geist9 verlangt 4 BERATER_OUTPUTS (recalibrate/postItem/statusTransition/modelSync)
im Manifest bevor Skill(loopDecision/PostBatch) laeuft. Nach dem AK-C-Offload
liegen die Phase-3-Berater-Outputs frueherer Rounds in _manifest_history_{date}.md
(im Manifest nur die letzte Round). Ohne Dual-Read -> 4 Outputs faelschlich
"missing" -> Guard blockt (False-Negative, Stall am Batch-Ende).

RED (vor Migration): read_manifest() liefert nur den Manifest-Body -> 4 missing.
GREEN (nach Migration): read_manifest() liefert Dual (Manifest + History + Pointer)
-> alle 4 gefunden, missing=[].

Test-Seam: OMNI_GEIST9_MANIFEST (bestehender Test-Override) zeigt auf das Manifest
im Offload-BL-Folder. Die migrierte read_manifest ergaenzt die ausgelagerten
History-/Pointer-Bodies des gleichen Folders.
"""
import importlib
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _bl_folder_with_offloaded_phase3() -> Path:
    """BL-Folder: Phase-3-Berater-Outputs sind offloaded (nicht im Manifest-Body)."""
    d = Path(tempfile.mkdtemp())
    bl = d / "BL-G9"
    bl.mkdir()
    (bl / "_manifest.md").write_text(
        "---\nbl_id: BL-G9\n---\n\n## DF_BATCH_STATE\nstatus: batch_done\n",
        encoding="utf-8",
    )
    (bl / "_manifest_history_2026-06-10.md").write_text(
        "# Manifest-Historie (ausgelagert 2026-06-10)\n\n"
        "## BERATER_OUTPUTS.recalibrate_round10\n\n```yaml\nstatus: DONE\n```\n\n"
        "## BERATER_OUTPUTS.postItem_round10\n\n```yaml\nstatus: DONE\n```\n\n"
        "## BERATER_OUTPUTS.statusTransition_round10\n\n```yaml\nstatus: DONE\n```\n\n"
        "## BERATER_OUTPUTS.modelSync_round10\n\n```yaml\nstatus: DONE\n```\n",
        encoding="utf-8",
    )
    return bl


def _missing_after_grep(g9, manifest_text: str):
    """Repliziert geist9's missing-Berechnung auf gegebenem Text."""
    missing = []
    for label, pattern in g9.REQUIRED_BERATER:
        if not re.search(pattern, manifest_text, re.IGNORECASE):
            missing.append(label)
    return missing


class TestGeist9DualRead(unittest.TestCase):

    def setUp(self):
        import guard_geist9_post_sdf as g9
        importlib.reload(g9)
        self.g9 = g9
        self.bl = _bl_folder_with_offloaded_phase3()
        self._prev_env = os.environ.get("OMNI_GEIST9_MANIFEST")
        os.environ["OMNI_GEIST9_MANIFEST"] = str(self.bl / "_manifest.md")

    def tearDown(self):
        if self._prev_env is None:
            os.environ.pop("OMNI_GEIST9_MANIFEST", None)
        else:
            os.environ["OMNI_GEIST9_MANIFEST"] = self._prev_env

    def test_dual_read_finds_offloaded_phase3_outputs(self):
        manifest_text = self.g9.read_manifest()
        missing = _missing_after_grep(self.g9, manifest_text)
        self.assertEqual(
            missing, [],
            f"Phase-3-Outputs sind offloaded, muessen via Dual-Read gefunden werden; missing={missing}",
        )

    def test_true_missing_still_detected(self):
        # Arrange: BL-Folder OHNE Phase-3-Outputs (weder inline noch offloaded).
        d = Path(tempfile.mkdtemp())
        bl = d / "BL-G9-MISS"
        bl.mkdir()
        (bl / "_manifest.md").write_text(
            "---\nbl_id: BL-G9-MISS\n---\n\n## DF_BATCH_STATE\nstatus: batch_done\n",
            encoding="utf-8",
        )
        os.environ["OMNI_GEIST9_MANIFEST"] = str(bl / "_manifest.md")
        text = self.g9.read_manifest()
        missing = _missing_after_grep(self.g9, text)
        self.assertEqual(set(missing),
                         {"recalibrate", "postItem", "statusTransition", "modelSync"},
                         "Echte fehlende Outputs muessen weiterhin missing sein")


if __name__ == "__main__":
    unittest.main(verbosity=2)
