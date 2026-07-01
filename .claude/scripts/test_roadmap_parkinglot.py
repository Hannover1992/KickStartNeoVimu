#!/usr/bin/env python3
"""TDD fuer roadmap_parkinglot.py (BL-418) — Within-BL-Kompass. Inline-Fixtures, keine Vault-Abhaengigkeit."""
from __future__ import annotations

import textwrap
from pathlib import Path

import roadmap_parkinglot as rp


def _mk_bl(tmp: Path, *, with_idf: bool, with_post: bool) -> Path:
    f = tmp / "BL-999-test"
    (f / "2_Model").mkdir(parents=True)
    (f / "3_Spec").mkdir()
    (f / "2_Model" / "BL-999_Model.md").write_text("---\nx: 1\n---\n", encoding="utf-8")
    (f / "3_Spec" / "BL-999_Spec.md").write_text("---\nx: 1\n---\n", encoding="utf-8")
    (f / "4_K-Score").mkdir()
    (f / "4_K-Score" / "BL-999-K-SCORE.md").write_text(textwrap.dedent("""\
        ---
        k_score: 55.0
        k_label: MEDIUM
        ak_details:
          AK-1:
            srs_pro_ak: 48
            k_score_pro_ak: 78
          AK-2:
            srs_pro_ak: 16
            k_score_pro_ak: 44
        ---
        # K-Score
        """), encoding="utf-8")
    (f / "6_PL").mkdir()
    status = "done" if with_post else "pending"
    (f / "6_PL" / "BL-999-parking-lot.md").write_text(textwrap.dedent(f"""\
        ---
        items_total: 2
        items_done: {2 if with_post else 0}
        ---
        # PL Master -- BL-999

        ### BL-999-AK-1-PL-1
        - **id:** BL-999-AK-1-PL-1
        - **source_aks:** AK-1
        - **classification:** code-coverable
        - **k_score:** 78.0
        - **srs:** 48
        - **dependencies:** (keine)
        - **status:** {status}

        ### BL-999-AK-2-PL-1
        - **id:** BL-999-AK-2-PL-1
        - **source_aks:** AK-2
        - **classification:** markdown_uncoverable
        - **k_score:** 44.0
        - **srs:** 16
        - **dependencies:** AK-1-PL-1
        - **status:** {status}
        """), encoding="utf-8")
    mani = "# BL-999 Manifest\n\n## A_PIPELINE_STATE\nphase: COMPLETED\nk_score: 55.0\nrouting_target: IDF\n"
    if with_idf:
        mani += textwrap.dedent("""
        ## BERATER_OUTPUTS_IDF

        ```yaml
        batchPlan:
          sub_batches:
            batch_1:
              items: ["BL-999-AK-1-PL-1"]
              aggregates: {k_score_avg: 78.0}
            batch_2:
              items: ["BL-999-AK-2-PL-1"]
              aggregates: {k_score_avg: 44.0}
        stagePlanner:
          batch_stages: {batch_1: [1], batch_2: [1]}
        ```
        """)
    if with_post:
        mani += "\n## DF_BATCH_STATE\nbatch_status: DONE\ncompleted_sub_batches: [batch_1, batch_2]\nbatch_modes:\n  batch_1: M3\n  batch_2: M2\n"
        mani += "\n## POST_STATE\ngap: 0\nstatus_recommendation: DONE\n"
    (f / "_manifest.md").write_text(mani, encoding="utf-8")
    return f


def test_parse_pl(tmp_path):
    f = _mk_bl(tmp_path, with_idf=False, with_post=False)
    pl = rp.parse_pl(f)
    assert pl["present"] and len(pl["items"]) == 2
    assert pl["items"][0]["id"] == "BL-999-AK-1-PL-1"
    assert pl["items"][0]["k_score"] == "78.0"
    assert pl["items"][1]["source_aks"] == "AK-2"


def test_parse_kscore(tmp_path):
    f = _mk_bl(tmp_path, with_idf=False, with_post=False)
    ks = rp.parse_kscore(f)
    assert ks["present"] and ks["k_label"] == "MEDIUM"
    assert ks["ak_details"]["AK-1"]["k_score_pro_ak"] == 78


def test_manifest_authoritative_subbatches(tmp_path):
    f = _mk_bl(tmp_path, with_idf=True, with_post=True)
    mani = rp.parse_manifest(f)
    sb = rp.subbatches(mani, rp.parse_pl(f))
    assert sb["mode"] == "autoritativ"
    assert len(sb["batches"]) == 2
    b1 = sb["batches"][0]
    assert b1["stage"] == [1] and b1["modus"] == "M3" and b1["done"] is True


def test_projection_when_no_idf(tmp_path):
    f = _mk_bl(tmp_path, with_idf=False, with_post=False)
    sb = rp.subbatches(rp.parse_manifest(f), rp.parse_pl(f))
    assert sb["mode"] == "projektion"
    # AK-1-PL-1 (dep-frei) in Schicht 1, AK-2-PL-1 (dep AK-1-PL-1) in Schicht 2
    assert len(sb["batches"]) == 2
    assert "BL-999-AK-1-PL-1" in sb["batches"][0]["items"]
    assert "BL-999-AK-2-PL-1" in sb["batches"][1]["items"]


def test_progress_kweighted(tmp_path):
    f_done = _mk_bl(tmp_path / "a", with_idf=True, with_post=True)
    p = rp.progress(rp.parse_pl(f_done))
    assert p["k_pct"] == 100.0 and p["done"] == 2 and p["total"] == 2
    f_open = _mk_bl(tmp_path / "b", with_idf=False, with_post=False)
    p2 = rp.progress(rp.parse_pl(f_open))
    assert p2["k_pct"] == 0.0 and p2["done"] == 0


def test_stages_progression(tmp_path):
    f = _mk_bl(tmp_path, with_idf=True, with_post=False)
    stages = {s["stufe"]: s["done"] for s in rp.detect_stages(f, rp.parse_manifest(f))}
    assert stages["A-Pipeline"] is True and stages["IDF"] is True and stages["Post"] is False


def test_render_smoke(tmp_path):
    f = _mk_bl(tmp_path, with_idf=False, with_post=False)
    out = rp.render("BL-999", f, rp.parse_manifest(f), rp.parse_pl(f), rp.parse_kscore(f))
    assert "Within-BL-Kompass" in out
    assert "PROJEKTION" in out                 # vor IDF
    assert "/_IDF_orchestrate BL-999" in out   # naechster Befehl
    assert "K-gewichtet" in out
