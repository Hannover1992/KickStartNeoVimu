"""
test_phase78_geist5_forward_verify.py — GATE-C C1 Live-Forward-Verify (BL-342 / BL-230 Roadmap).

Beweist die Phase-1a-SUITABILITY-Haelfte END-TO-END gegen ECHTE 486-Daten + die ECHTE Engine:
  (1) der ECHTE Producer (parallel_suitability_producer.produce_block) rechnet einen sinnvollen
      parallel_suitability-Block auf der ECHTEN 486 file_index (F486_V6, FE-orphan, Ground-Truth);
  (2) der ECHTE Handover-Guard guard_geist5_idf_to_sdf.py PASST mit dem ADDITIVEN
      parallel_suitability-Block im Manifest (= Phase 7.8 schreibt additiv, ohne den IDF->SDF-
      Contract zu brechen) — gefahren als echter Hook-Subprozess mit enforce=ON.

Das ist die GOAL-Akzeptanz fuer Gate-C C1: "Phase 7.8 schreibt DF_BATCH_STATE.parallel_suitability
ADDITIV + guard_geist5 PASS". Integrationsebene (echte Engine-Skripte + echte 486-Daten + echter
Guard) — NICHT der volle 14-Phasen-Live-IDF-Lauf (der bleibt einer frischen Session = Gate-A).

Run aus Repo-Root:  py -3 -m pytest .claude/scripts/test_phase78_geist5_forward_verify.py -v
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import parallel_suitability_producer as psp

SCRIPTS = Path(__file__).parent
GUARD = str(SCRIPTS / "guard_geist5_idf_to_sdf.py")

# ─── ECHTE 486 v6 file_index (FE-orphan, Ground-Truth, identisch zu test_sub_batch_targets) ───
F486_V6 = {
    "autocomplete-chips-field.ts": ["PR2-DUC-1", "PR2-DUC-2", "PR2-DUC-3",
                                    "PR2-DUC-4", "PR2-DUC-5", "PR2-DUC-6"],
    "selbstauskunft-details-qdvtp.component.ts": ["PR2-DUC-2", "PR2-DUC-7",
                                                  "PR2-DUC-8", "PR2-DUC-12"],
    "selbstauskunft-qdvtp-form-mappers.ts": ["PR2-DUC-2", "PR2-DUC-11"],
    "selbstauskunft-details-qdvs.component.ts": ["PR2-DUC-2", "PR2-DUC-11"],
    "selbstauskunft-form-converters.ts": ["PR2-DUC-2"],
    "validation-constants.ts": ["PR2-DUC-7"],
    "time-mask.directive.ts": ["PR2-DUC-13"],
}

# Sub-Batches ueber die ECHTEN DUC-Items: DUC-2 + DUC-7 teilen
# selbstauskunft-details-qdvtp.component.ts (Konflikt-Insel); DUC-13 ist isoliert (time-mask).
DUC_BIPB = {
    "sb_qdvtp_2": ["PR2-DUC-2"],
    "sb_qdvtp_7": ["PR2-DUC-7"],
    "sb_timemask_13": ["PR2-DUC-13"],
}

# ─── ECHTE 486 DF_BATCH_STATE-Anker (real _manifest.bak_2026-06-05_pre_split.md Z2281-2304) ───
REAL_BIPB = """    batch_1: [AK-CTX-2]
    batch_2: [AK-1]
    batch_3: [AK-CTX-3, AK-2, AK-4, AK-CTX-4]
    batch_5: [AK-13, AK-3]
    batch_6: [AK-9, AK-14, AK-6]"""
REAL_STAGES = """    batch_1: [1]
    batch_2: [1]
    batch_3: [1, 3]
    batch_5: [1, 3, 6]
    batch_6: [1, 3]"""
REAL_MODE_HINTS = """    batch_1: M2
    batch_5: M3
    batch_6: M3"""


# ═══════════════════════════════════════════════════════════════════════════════
# (1) ECHTER Producer auf ECHTER 486 file_index
# ═══════════════════════════════════════════════════════════════════════════════
def test_producer_block_shape_on_real_486():
    blk = psp.produce_block(DUC_BIPB, F486_V6)
    for key in ("format_version", "story_type", "conflict_islands", "largest_island",
                "build_share", "recommended_N", "suitable", "reason",
                "ziel_dateien_per_batch", "matrix"):
        assert key in blk, f"fehlendes Block-Feld: {key}"
    assert isinstance(blk["recommended_N"], int) and 1 <= blk["recommended_N"] <= 3


def test_producer_ziel_dateien_reflect_real_coupling():
    blk = psp.produce_block(DUC_BIPB, F486_V6)
    zd = blk["ziel_dateien_per_batch"]
    # isolierter Sub-Batch beruehrt genau die time-mask-Directive
    assert zd["sb_timemask_13"] == ["time-mask.directive.ts"]
    # DUC-2 ist der Hub: beruehrt 5 Dateien (autocomplete + 4 selbstauskunft-*)
    assert len(zd["sb_qdvtp_2"]) == 5
    assert "selbstauskunft-details-qdvtp.component.ts" in zd["sb_qdvtp_2"]


def test_producer_matrix_marks_real_shared_file_conflict():
    blk = psp.produce_block(DUC_BIPB, F486_V6)
    # finde das Paar (sb_qdvtp_2, sb_qdvtp_7) — teilt selbstauskunft-details-qdvtp.component.ts
    def files_for(a, b):
        for e in blk["matrix"]:
            if set(e["pair"]) == {a, b}:
                return e["files"]
        return None
    shared = files_for("sb_qdvtp_2", "sb_qdvtp_7")
    assert shared is not None
    assert "selbstauskunft-details-qdvtp.component.ts" in shared   # ECHTE Datei-Kollision
    # der isolierte Sub-Batch teilt mit dem Hub KEINE Datei
    iso = files_for("sb_qdvtp_2", "sb_timemask_13")
    assert iso == []


def test_producer_cli_roundtrip_on_real_data():
    payload = json.dumps({"batch_items_per_batch": DUC_BIPB, "file_index": F486_V6})
    proc = subprocess.run([sys.executable, str(SCRIPTS / "parallel_suitability_producer.py")],
                          input=payload, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    blk = json.loads(proc.stdout)
    assert blk["ziel_dateien_per_batch"]["sb_timemask_13"] == ["time-mask.directive.ts"]


# ═══════════════════════════════════════════════════════════════════════════════
# (2) ECHTER guard_geist5-Hook gegen Manifest mit additivem parallel_suitability-Block
# ═══════════════════════════════════════════════════════════════════════════════
def _manifest(with_block=True, with_stages=True):
    block_line = ""
    if with_block:
        blk = psp.produce_block(DUC_BIPB, F486_V6)
        # additiv, einzeilig (kein versehentliches Anker-Match) — Worker schreibt es via Edit
        block_line = "- parallel_suitability: " + json.dumps(blk, ensure_ascii=False) + "\n"
    # Kanonisches Manifest-Format = no-dash plain YAML keys (wie guard_geist5's eigener
    # Contract-Test + die Live-Pipeline; das 2026-06-05-BACKUP nutzte dash-Style, der
    # NICHT die kanonische Repr ist — siehe Roadmap-Note).
    stages = f"batch_stages:\n{REAL_STAGES}\n" if with_stages else ""
    return (
        "---\nformat_version: 1\n---\n"
        "## IDF_PIPELINE_STATE\n"
        "idf_status: IDF_DONE\n\n"
        "## DF_BATCH_STATE\n"
        f"batch_items_per_batch:\n{REAL_BIPB}\n"
        f"batch_mode_hints:\n{REAL_MODE_HINTS}\n"
        f"{stages}"
        f"{block_line}"
    )


def _run_guard(manifest_text, tmp_path):
    (tmp_path / "_manifest.md").write_text(manifest_text, encoding="utf-8")
    env = dict(os.environ)                       # erbt PYTEST_CURRENT_TEST -> enforce_active=True
    env["OMNI_GEIST5_VAULT_ROOT"] = str(tmp_path)
    env["OMNI_ENFORCE_GEIST5_GUARD"] = "1"       # read_enforce_process -> True (BLOCK bei Violation)
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    env.pop("OMNI_SESSION_PARAMS", None)
    hook = json.dumps({"tool_name": "Skill", "tool_input": {"skill": "_SDF_orchestrate"}})
    proc = subprocess.run([sys.executable, GUARD], input=hook,
                          capture_output=True, text=True, env=env)
    assert proc.stdout.strip(), f"kein Guard-Output. stderr={proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_geist5_PASSES_with_additive_parallel_suitability(tmp_path):
    """GATE-C C1 KERN-BEWEIS: Phase-7.8-Block additiv im Manifest -> Handover-Guard PASST."""
    out = _run_guard(_manifest(with_block=True, with_stages=True), tmp_path)
    assert out.get("continue") is True, f"guard blockte trotz erfuelltem Contract: {out}"


def test_geist5_baseline_passes_without_block(tmp_path):
    """Negativ-Kontrolle: ohne den Block PASST der Guard auch -> der Block ist REIN ADDITIV."""
    out = _run_guard(_manifest(with_block=False, with_stages=True), tmp_path)
    assert out.get("continue") is True, f"Baseline-Contract sollte passen: {out}"


def test_geist5_still_blocks_missing_anchor_even_with_block(tmp_path):
    """Der additive Block darf einen ECHTEN Contract-Gap NICHT maskieren:
    fehlt batch_stages, blockt der Guard auch MIT parallel_suitability-Block (enforce=ON)."""
    out = _run_guard(_manifest(with_block=True, with_stages=False), tmp_path)
    assert out.get("continue") is False, f"Guard haette wegen fehlendem batch_stages blocken muessen: {out}"
    assert "batch_stages" in out.get("message", "")
