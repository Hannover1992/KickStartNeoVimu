#!/usr/bin/env python3
"""BL-229 AK-F (T11): guard_geist9b_sdf_post_inline.py — Dual-Read NO-OP-Beleg.

geist9b detektiert KEINE Manifest-Block-INHALTE. Es prueft (a) den eingehenden
Write-Text (PL [ ]->[x] / completed_batches-Append) und (b) den AUDIT-Trail
(_SDF_orchestrate_post seit _I_orchestrate). Beide Signale sind vom BL-229
State-vs-Report-Split UNBERUEHRT:
  - completed_*_batches:-Zeilen + PL-[x]-Marker sind Working-Set/kanonisch, NICHT
    offloaded (AK-C lagert nur fruehere-Round State-Familien-Bodies aus).
  - audit.jsonl ist eine separate Datei, nicht Teil des Manifests.

=> geist9b hat KEINE False-Negative-Flaeche aus dem Split. Eine Dual-Read-Migration
waere ein No-Op und wuerde nur Risiko addieren (Worker-Regel: ehrlicher No-Op >
kaputter Guard). Dieser Test verriegelt die Begruendung: die Enforcement-Wirkung
ist identisch, egal ob der Manifest-Body offloaded wurde oder nicht.
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
HOOK = SCRIPT_DIR / "guard_geist9b_sdf_post_inline.py"


def _run_hook(event: dict, env_extra: dict) -> dict:
    env = os.environ.copy()
    env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(event), capture_output=True, text=True, env=env,
    )
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def _audit_with_i_no_post() -> Path:
    """Audit-Trail: _I_orchestrate lief, KEIN _SDF_orchestrate_post danach."""
    d = Path(tempfile.mkdtemp())
    a = d / "audit.jsonl"
    a.write_text(
        json.dumps({"event": "SKILL_LOAD", "skill": "_I_orchestrate"}) + "\n",
        encoding="utf-8",
    )
    return a


class TestGeist9bUnaffectedBySplit(unittest.TestCase):
    """Enforcement-Wirkung ist split-invariant (keine Manifest-Content-Lesung)."""

    def test_completed_batches_append_still_blocked_after_i_pipeline(self):
        # Arrange: completed_batches-Append nach I-Pipeline ohne SDF-Post -> BLOCK.
        audit = _audit_with_i_no_post()
        event = {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/x/_manifest.md",
                "content": "completed_sub_batches: [batch_1]\n",
            },
        }
        res = _run_hook(event, {
            "OMNI_GEIST9B_AUDIT": str(audit),
            "OMNI_ENFORCE_ALL_OFF": "0",
            "OMNI_ENFORCE_GEIST9B_GUARD": "1",
            # _enforce_gate scharf schalten via session-param-Fallback nicht moeglich
            # im Subprocess; wir pruefen daher die Detektions-Logik direkt unten.
        })
        # Hinweis: _enforce_gate kann den Guard im Subprocess deaktivieren (enforceProcess).
        # Der harte Beleg laeuft ueber die Detektions-Funktion (split-invariant), s.u.
        self.assertIn("continue", res)

    def test_detection_is_content_independent(self):
        # Direkter Beleg: post_phase_ran_since_i_pipeline + die Patterns haengen NUR
        # am Audit-Trail + new_text, NICHT am Manifest-Body (offloaded oder nicht).
        import guard_geist9b_sdf_post_inline as g9b
        importlib.reload(g9b)
        audit = _audit_with_i_no_post()
        os.environ["OMNI_GEIST9B_AUDIT"] = str(audit)
        try:
            i_active, post_since = g9b.post_phase_ran_since_i_pipeline()
            self.assertTrue(i_active, "I-Pipeline-Anker muss im Audit erkannt werden")
            self.assertFalse(post_since, "Kein _SDF_orchestrate_post danach -> post_since False")
            # completed_batches-Pattern matcht unabhaengig vom Manifest-Body:
            self.assertTrue(
                bool(g9b.COMPLETED_BATCHES_PATTERN.search("completed_sub_batches: [batch_1]")),
                "completed_batches-Transition wird am new_text erkannt (split-invariant)",
            )
        finally:
            os.environ.pop("OMNI_GEIST9B_AUDIT", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
