#!/usr/bin/env python3
"""BL-229 AK-F (T11): guard_geist7c_done_claim_proof.py — Dual-Read NO-OP-Beleg.

geist7c detektiert KEINE Manifest-Block-INHALTE. Es prueft (a) den eingehenden
Write-Text (PL [x] + Test-Evidenz-Token wie '813/813'/'passed'+Tool) und (b) den
AUDIT-Trail (_TDD_execute/_I_verify/_T_orchestrate seit Batch-Anker). Beide Signale
sind vom BL-229 State-vs-Report-Split UNBERUEHRT:
  - PL-[x]-Marker + Claim-Text leben in parking-lot.md / im Write selbst, NICHT im
    offloaded _manifest_history (AK-C lagert nur Manifest-State-Familien aus).
  - audit.jsonl ist separat, nicht Teil des Manifests.

=> Keine False-Negative-Flaeche aus dem Split. Dual-Read-Migration waere No-Op
(Worker-Regel: ehrlicher No-Op > kaputter Guard). Test verriegelt: Detektion ist
content-independent (split-invariant).
"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))


def _audit_with_anchor_no_testexec() -> Path:
    d = Path(tempfile.mkdtemp())
    a = d / "audit.jsonl"
    a.write_text(
        json.dumps({"event": "SKILL_LOAD", "skill": "_I_orchestrate"}) + "\n",
        encoding="utf-8",
    )
    return a


class TestGeist7cUnaffectedBySplit(unittest.TestCase):

    def test_evidence_detection_is_content_independent(self):
        import guard_geist7c_done_claim_proof as g7c
        importlib.reload(g7c)

        # PL-[x]-Transition wird am new_text erkannt, nicht am Manifest-Body:
        self.assertTrue(bool(g7c.PL_DONE_PATTERN.search("### [x] PL-007 done")))
        # Text-Evidenz (Zahlen / passed+Tool) wird am Claim-Text erkannt:
        self.assertTrue(bool(g7c.NUM_RATIO.search("813/813 passed")))
        self.assertTrue(bool(g7c.PROOF_KEYWORDS.search("test suite GREEN")))

    def test_audit_testexec_is_content_independent(self):
        import guard_geist7c_done_claim_proof as g7c
        importlib.reload(g7c)
        audit = _audit_with_anchor_no_testexec()
        os.environ["OMNI_GEIST7C_AUDIT"] = str(audit)
        try:
            # Kein Test-Exec-Skill seit dem Batch-Anker -> kein audit-Beweis
            # (haengt NUR am Audit-Trail, nicht am Manifest-Inhalt).
            self.assertFalse(g7c.has_audit_test_exec())
        finally:
            os.environ.pop("OMNI_GEIST7C_AUDIT", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
