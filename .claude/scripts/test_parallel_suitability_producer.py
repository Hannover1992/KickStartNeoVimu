"""
test_parallel_suitability_producer.py — BL-342 Phase-7.8 Compute-Bridge (RED zuerst).

Der deterministische Compute-Driver fuer die IDF-Phase-7.8 (parallelSuitability).
Komponiert sub_batch_targets (file_index->ziel_dateien) + parallel_suitability
(Konflikt-Inseln/Suitability) zum KANONISCHEN, SERIALISIERBAREN DF_BATCH_STATE.
parallel_suitability-Block. CLI-Bruecke: Worker pipet {batch_items_per_batch,
file_index} als JSON rein -> bekommt den Block als JSON raus (manifest-I/O bleibt
worker-seitig wie bei allen Beratern; nur die BERECHNUNG ist deterministisch/python).

Run aus Repo-Root:  py -3 -m pytest .claude/scripts/test_parallel_suitability_producer.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import parallel_suitability_producer as psp

MODULE = str(Path(__file__).parent / "parallel_suitability_producer.py")

# ECHTE 486 v6-orphan file_index (Ground-Truth, _manifest.md Z2738-2745)
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


# ─── produce_block: kanonischer Block, serialisierbar ────────────────────────────
def test_produce_block_isolated_parallel():
    bipb = {"chips": ["PR2-DUC-1", "PR2-DUC-3", "PR2-DUC-4", "PR2-DUC-5", "PR2-DUC-6"],
            "timemask": ["PR2-DUC-13"]}
    blk = psp.produce_block(bipb, F486_V6)
    assert blk["conflict_islands"] == 2
    assert blk["suitable"] is True
    assert blk["ziel_dateien_per_batch"]["timemask"] == ["time-mask.directive.ts"]


def test_produce_block_hub_couples_serial():
    bipb = {"hub": ["PR2-DUC-2"], "oz": ["PR2-DUC-7"]}
    blk = psp.produce_block(bipb, F486_V6)
    assert blk["conflict_islands"] == 1
    assert blk["recommended_N"] == 1


def test_produce_block_matrix_is_json_serializable():
    bipb = {"hub": ["PR2-DUC-2"], "oz": ["PR2-DUC-7"]}
    blk = psp.produce_block(bipb, F486_V6)
    # matrix muss eine LISTE (keine tuple-keys) sein -> JSON/YAML-serialisierbar
    assert isinstance(blk["matrix"], list)
    s = json.dumps(blk)          # darf NICHT werfen (tuple-keys waeren ein TypeError)
    assert "selbstauskunft-details-qdvtp.component.ts" in s
    entry = blk["matrix"][0]
    assert set(entry.keys()) == {"pair", "status", "files"}
    assert entry["pair"] == ["hub", "oz"]


def test_produce_block_has_format_version_and_reason():
    blk = psp.produce_block({"a": ["i1"]}, {"f.ts": ["i1"]})
    assert blk["format_version"] == psp.FORMAT_VERSION
    assert isinstance(blk["reason"], str) and blk["reason"]


def test_produce_block_none_tolerant_trivial():
    blk = psp.produce_block(None, None)
    assert blk["recommended_N"] == 1
    assert blk["suitable"] is False
    assert blk["matrix"] == []
    json.dumps(blk)              # serialisierbar auch im Trivial-Fall


# ─── CLI-Bruecke: JSON stdin -> JSON stdout (der echte Worker-Pfad) ──────────────
def test_cli_roundtrip_json_stdin_stdout():
    payload = json.dumps({
        "batch_items_per_batch": {"hub": ["PR2-DUC-2"], "oz": ["PR2-DUC-7"]},
        "file_index": F486_V6,
    })
    proc = subprocess.run([sys.executable, MODULE], input=payload,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["conflict_islands"] == 1
    assert out["recommended_N"] == 1


def test_cli_change_type_map_flows_through():
    payload = json.dumps({
        "batch_items_per_batch": {"a": ["i1"], "b": ["i2"]},
        "file_index": {"x.ts": ["i1"], "y.ts": ["i2"]},
        "change_type_map": {"a": "add", "b": "add"},
    })
    proc = subprocess.run([sys.executable, MODULE], input=payload,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    # 2 disjunkte Inseln + build_share=1.0 (beide add) -> build-parallel, suitable
    assert out["conflict_islands"] == 2
    assert out["build_share"] == 1.0
    assert out["suitable"] is True


# ─── BL-415: Resource-Divisibilitaet (T-a1, T-a2, T-a3, T-b1, T-b2, T-b3, T-c1, T-c2) ──

# Fixtures fuer Resource-Conflict-Tests
_BIPB_TWO_DISJOINT = {"batch_1": ["i1"], "batch_2": ["i2"]}
_FILE_INDEX_DISJOINT = {"file_a.ts": ["i1"], "file_b.ts": ["i2"]}
_BATCH_STAGES_SAME_STAGE = {"batch_1": [1], "batch_2": [1]}

_RESOURCES_UNTEILBAR = {
    1: {
        "resource_ids": ["docker_integration_stack"],
        "divisibility": {"docker_integration_stack": "unteilbar"},
    }
}

_RESOURCES_TEILBAR = {
    1: {
        "resource_ids": ["shared_cache"],
        "divisibility": {"shared_cache": "teilbar"},
    }
}

_RESOURCES_NO_SHARED = {
    1: {
        "resource_ids": ["res_only_batch_1"],
        "divisibility": {"res_only_batch_1": "unteilbar"},
    },
    2: {
        "resource_ids": ["res_only_batch_2"],
        "divisibility": {"res_only_batch_2": "unteilbar"},
    },
}
_BATCH_STAGES_DIFFERENT = {"batch_1": [1], "batch_2": [2]}


def test_produce_block_no_resource_params_backward_compat():
    """T-a1: AK-1 — ohne neue Parameter unveraendertes Verhalten, kein resource_conflicts-Key."""
    blk = psp.produce_block(_BIPB_TWO_DISJOINT, _FILE_INDEX_DISJOINT)
    # bestehende Felder unveraendert
    assert "matrix" in blk
    assert "recommended_N" in blk
    # das neue Feld darf NICHT im Block sein (Backward-Compat)
    assert "resource_conflicts" not in blk


def test_produce_block_unteilbar_resource_conflict():
    """T-a2: AK-2 — unteilbare Ressource geteilt -> matrix-Eintrag resource_conflict + recommended_N sinkt."""
    # Baseline ohne Resource-Params: 2 disjunkte Batches -> recommended_N = 2
    blk_baseline = psp.produce_block(_BIPB_TWO_DISJOINT, _FILE_INDEX_DISJOINT)
    baseline_N = blk_baseline["recommended_N"]

    # Mit unteilbarer geteilter Ressource auf Stage 1
    blk = psp.produce_block(
        _BIPB_TWO_DISJOINT,
        _FILE_INDEX_DISJOINT,
        batch_stages=_BATCH_STAGES_SAME_STAGE,
        resources_per_stage=_RESOURCES_UNTEILBAR,
    )
    # Das Paar muss resource_conflict-Status haben
    pair_statuses = {tuple(e["pair"]): e["status"] for e in blk["matrix"]}
    assert pair_statuses.get(("batch_1", "batch_2")) == "resource_conflict" or \
           pair_statuses.get(("batch_2", "batch_1")) == "resource_conflict", \
        f"Erwartet resource_conflict in matrix, bekommen: {blk['matrix']}"
    # recommended_N muss kleiner sein als Baseline (Konflikt-Kante reduziert Parallelitaet)
    assert blk["recommended_N"] < baseline_N, \
        f"Erwartet recommended_N < {baseline_N}, bekommen: {blk['recommended_N']}"


def test_produce_block_teilbar_resource_no_conflict():
    """T-a3: AK-2 — teilbare Ressource geteilt -> disjoint bleibt (kein resource_conflict)."""
    blk = psp.produce_block(
        _BIPB_TWO_DISJOINT,
        _FILE_INDEX_DISJOINT,
        batch_stages=_BATCH_STAGES_SAME_STAGE,
        resources_per_stage=_RESOURCES_TEILBAR,
    )
    pair_statuses = {tuple(e["pair"]): e["status"] for e in blk["matrix"]}
    pair_status = pair_statuses.get(("batch_1", "batch_2")) or \
                  pair_statuses.get(("batch_2", "batch_1"))
    assert pair_status == "disjoint", \
        f"Teilbare Ressource soll disjoint lassen, bekommen: {pair_status}"


def test_resource_conflicts_field_present_with_conflicts():
    """T-b1: AK-3(a) — resource_conflicts-Feld vorhanden mit mind. 1 Eintrag bei Konflikt."""
    blk = psp.produce_block(
        _BIPB_TWO_DISJOINT,
        _FILE_INDEX_DISJOINT,
        batch_stages=_BATCH_STAGES_SAME_STAGE,
        resources_per_stage=_RESOURCES_UNTEILBAR,
    )
    assert "resource_conflicts" in blk, "resource_conflicts-Feld fehlt im Block"
    assert isinstance(blk["resource_conflicts"], list)
    assert len(blk["resource_conflicts"]) >= 1, \
        "Mindestens 1 Eintrag erwartet bei unteilbarem Konflikt"
    entry = blk["resource_conflicts"][0]
    assert "resource_id" in entry
    assert "divisibility" in entry
    assert "batches" in entry
    assert entry["resource_id"] == "docker_integration_stack"
    assert entry["divisibility"] == "unteilbar"


def test_resource_conflicts_field_empty_no_conflicts():
    """T-b2: AK-3(b) — resource_conflicts ist leere Liste wenn batch_stages vorhanden aber keine Konflikte."""
    blk = psp.produce_block(
        _BIPB_TWO_DISJOINT,
        _FILE_INDEX_DISJOINT,
        batch_stages=_BATCH_STAGES_DIFFERENT,
        resources_per_stage=_RESOURCES_NO_SHARED,
    )
    assert "resource_conflicts" in blk, \
        "resource_conflicts-Feld muss vorhanden sein wenn batch_stages uebergeben"
    assert blk["resource_conflicts"] == [], \
        f"Erwartet leere Liste bei keinen Konflikten, bekommen: {blk['resource_conflicts']}"


def test_resource_conflicts_field_absent_no_batch_stages():
    """T-b3: AK-3(c) — resource_conflicts-Feld fehlt komplett wenn batch_stages=None."""
    blk = psp.produce_block(
        _BIPB_TWO_DISJOINT,
        _FILE_INDEX_DISJOINT,
        batch_stages=None,
        resources_per_stage=_RESOURCES_UNTEILBAR,
    )
    assert "resource_conflicts" not in blk, \
        f"resource_conflicts darf NICHT im Block sein wenn batch_stages=None: {list(blk.keys())}"


def test_overlap_dominates_resource_conflict():
    """T-c1: AK-5 — overlap-Status dominiert resource_conflict wenn Datei-Konflikt vorhanden."""
    # batch_1 und batch_2 teilen dieselbe Datei UND eine unteilbare Ressource
    bipb_overlap = {"batch_1": ["i1", "i_shared"], "batch_2": ["i2", "i_shared"]}
    file_index_overlap = {
        "file_a.ts": ["i1", "i_shared"],
        "file_b.ts": ["i2", "i_shared"],
    }
    blk = psp.produce_block(
        bipb_overlap,
        file_index_overlap,
        batch_stages=_BATCH_STAGES_SAME_STAGE,
        resources_per_stage=_RESOURCES_UNTEILBAR,
    )
    pair_statuses = {tuple(e["pair"]): e["status"] for e in blk["matrix"]}
    pair_status = pair_statuses.get(("batch_1", "batch_2")) or \
                  pair_statuses.get(("batch_2", "batch_1"))
    assert pair_status == "overlap", \
        f"overlap muss resource_conflict dominieren, bekommen: {pair_status}"


def test_default_divisibility_unteilbar():
    """T-c2: AK-6 — Default-Teilbarkeit 'unteilbar' wenn divisibility-dict Eintrag fehlt."""
    # resource_ids nennt die Ressource, aber divisibility-dict ist leer -> Default greift
    resources_missing_divisibility_entry = {
        1: {
            "resource_ids": ["mystery_resource"],
            "divisibility": {},  # kein Eintrag fuer mystery_resource -> Default = unteilbar
        }
    }
    blk = psp.produce_block(
        _BIPB_TWO_DISJOINT,
        _FILE_INDEX_DISJOINT,
        batch_stages=_BATCH_STAGES_SAME_STAGE,
        resources_per_stage=resources_missing_divisibility_entry,
    )
    pair_statuses = {tuple(e["pair"]): e["status"] for e in blk["matrix"]}
    pair_status = pair_statuses.get(("batch_1", "batch_2")) or \
                  pair_statuses.get(("batch_2", "batch_1"))
    assert pair_status == "resource_conflict", \
        f"Default-Divisibility muss als unteilbar behandelt werden, bekommen: {pair_status}"
