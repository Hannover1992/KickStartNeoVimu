#!/usr/bin/env python3
"""
test_pile_relevance.py — BL-346 AK-3 Forward-Verify

Coverage (pileOfMud-Relevanz-Gate, Phase 0.5):
  Der Gate filtert fremdes/unzuordenbares Live-pileOfMud-Material BEVOR es als
  BL-Findings extrahiert wird. Relevanz-Wahrheit = der per-BL Snapshot
  ({bl_folder}/Sources/_pileOfMud_snapshot/) mit source_provenance.original_hash.

  T1  Snapshot {a,b} + Live {a,b,fremd} -> relevant={a,b}, foreign={fremd}
  T2  Snapshot {a,b} + Live {a,b,fremd}: foreign wird LAUT gemeldet (skip_reason)
  T3  KEIN Snapshot + Live {fremd} -> 0 relevant (Fall BL-282, kein Garbage)
  T4  Fresh-Intake: Snapshot == Live {a,b} -> alle relevant (ABWAERTSKOMPAT)
  T5  Snapshot {a} + Live {a'} (Name-Match, Hash-Drift) -> a' foreign (content_drift)
  T6  Leerer Live-Pile -> relevant=[] foreign=[] (kein Crash)
  T7  Snapshot ohne Hash-Frontmatter (legacy) -> Name-Match genuegt (relevant)
  T8  is_mature_consolidated_epic: 0 relevant + reicher Node + superseded -> True (AK-2)
  T9  is_mature_consolidated_epic: frischer Pile-BL (relevant>0) -> False

Run (BEIDE cwd):
  py -3 -m pytest .claude/scripts/test_pile_relevance.py -q          # Repo-Root
  py -3 -m pytest test_pile_relevance.py -q                          # in .claude/scripts/
Exit 0 = alle PASS.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# cwd-stabil (BL-336): Import-Pfad an die Script-Heimat pinnen, NICHT an cwd.
SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pile_relevance as pr  # noqa: E402


SNAPSHOT_REL = "Sources/_pileOfMud_snapshot"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_snapshot(bl_folder: Path, basename: str, body: str, original_hash: str | None) -> Path:
    snap_dir = bl_folder / SNAPSHOT_REL
    snap_dir.mkdir(parents=True, exist_ok=True)
    target = snap_dir / basename
    if original_hash is None:
        fm = "---\ntype: pile_snapshot\n---\n"
    else:
        fm = (
            "---\n"
            "source_provenance:\n"
            "  source_kind: voice-note\n"
            f"  original_hash: {original_hash}\n"
            "---\n"
        )
    target.write_text(fm + body, encoding="utf-8")
    return target


def _write_live(pile_dir: Path, basename: str, body: str) -> Path:
    pile_dir.mkdir(parents=True, exist_ok=True)
    f = pile_dir / basename
    f.write_text(body, encoding="utf-8")
    return f


def test_t1_relevant_partition(tmp_path):
    bl = tmp_path / "BL-900-fresh"
    live = tmp_path / "pileOfMud"
    body_a, body_b, body_f = "Inhalt A", "Inhalt B", "Fremdes Material"
    _write_snapshot(bl, "a.md", body_a, _sha256(body_a))
    _write_snapshot(bl, "b.md", body_b, _sha256(body_b))
    fa = _write_live(live, "a.md", body_a)
    fb = _write_live(live, "b.md", body_b)
    ff = _write_live(live, "fremd.md", body_f)

    res = pr.partition_pile_by_relevance(bl, [fa, fb, ff])
    rel = {Path(p).name for p in res["relevant"]}
    foreign = {Path(p["path"]).name for p in res["foreign"]}
    assert rel == {"a.md", "b.md"}, rel
    assert foreign == {"fremd.md"}, foreign
    assert res["snapshot_present"] is True
    assert res["snapshot_count"] == 2


def test_t2_foreign_loud_reason(tmp_path):
    bl = tmp_path / "BL-900-fresh"
    live = tmp_path / "pileOfMud"
    _write_snapshot(bl, "a.md", "A", _sha256("A"))
    fa = _write_live(live, "a.md", "A")
    ff = _write_live(live, "fremd.md", "X")
    res = pr.partition_pile_by_relevance(bl, [fa, ff])
    foreign = res["foreign"]
    assert len(foreign) == 1
    entry = foreign[0]
    assert "skip_reason" in entry and entry["skip_reason"], entry
    # "No silent caps" — die Begruendung ist nicht-leer und benennt die Fremdheit.
    assert "snapshot" in entry["skip_reason"].lower()


def test_t3_no_snapshot_foreign_only(tmp_path):
    # Fall BL-282: konsolidierter EPIC ohne Snapshot, Live-Pile fremd.
    bl = tmp_path / "BL-282-feuerkreis"
    bl.mkdir(parents=True, exist_ok=True)
    live = tmp_path / "pileOfMud"
    ff1 = _write_live(live, "AssayOutputRouting.md", "x")
    ff2 = _write_live(live, "BL-229_SEED.md", "y")
    res = pr.partition_pile_by_relevance(bl, [ff1, ff2])
    assert res["relevant"] == [], res["relevant"]
    assert len(res["foreign"]) == 2
    assert res["snapshot_present"] is False


def test_t4_fresh_intake_all_relevant(tmp_path):
    # ABWAERTSKOMPAT: Snapshot == Live (frisches Intake) -> alle relevant.
    bl = tmp_path / "BL-901-fresh-intake"
    live = tmp_path / "pileOfMud"
    for name, body in [("note1.md", "eins"), ("note2.txt", "zwei")]:
        _write_snapshot(bl, name, body, _sha256(body))
        _write_live(live, name, body)
    live_files = sorted(live.glob("*"))
    res = pr.partition_pile_by_relevance(bl, live_files)
    rel = {Path(p).name for p in res["relevant"]}
    assert rel == {"note1.md", "note2.txt"}, rel
    assert res["foreign"] == []


def test_t5_name_match_hash_drift_is_foreign(tmp_path):
    bl = tmp_path / "BL-902"
    live = tmp_path / "pileOfMud"
    _write_snapshot(bl, "a.md", "Original-Inhalt", _sha256("Original-Inhalt"))
    fa = _write_live(live, "a.md", "GEAENDERTER Inhalt einer anderen Session")
    res = pr.partition_pile_by_relevance(bl, [fa])
    assert res["relevant"] == [], res["relevant"]
    assert len(res["foreign"]) == 1
    assert "drift" in res["foreign"][0]["skip_reason"].lower()


def test_t6_empty_live_pile(tmp_path):
    bl = tmp_path / "BL-903"
    _write_snapshot(bl, "a.md", "A", _sha256("A"))
    res = pr.partition_pile_by_relevance(bl, [])
    assert res["relevant"] == []
    assert res["foreign"] == []
    assert res["snapshot_present"] is True


def test_t7_legacy_snapshot_no_hash_name_match(tmp_path):
    # Snapshot ohne original_hash (pre-BL-160 / legacy): Name-Match genuegt.
    bl = tmp_path / "BL-904"
    live = tmp_path / "pileOfMud"
    _write_snapshot(bl, "legacy.md", "irgendwas", original_hash=None)
    fa = _write_live(live, "legacy.md", "anderer Live-Inhalt")
    res = pr.partition_pile_by_relevance(bl, [fa])
    rel = {Path(p).name for p in res["relevant"]}
    assert rel == {"legacy.md"}, rel
    assert res["foreign"] == []


def test_t8_mature_consolidated_epic_true(tmp_path):
    # AK-2: 0 relevante Pile-Files + reicher Node + superseded-Sources -> consolidated EPIC.
    bl = tmp_path / "BL-282-feuerkreis"
    bl.mkdir(parents=True, exist_ok=True)
    node = (
        "---\nid: BL-282\n---\n# Feuerkreis\n"
        + "\n".join(f"- **AK-{i}:** ein Akzeptanzkriterium" for i in range(1, 17))
        + "\nSupersedes BL-240/249/250/263.\n"
    )
    is_epic = pr.is_mature_consolidated_epic(
        relevant_count=0,
        node_text=node,
        node_ak_count=16,
        has_superseded=True,
    )
    assert is_epic is True


def test_t9_mature_consolidated_epic_false_for_fresh(tmp_path):
    is_epic = pr.is_mature_consolidated_epic(
        relevant_count=5,
        node_text="# Frisch\n- AK-1: x",
        node_ak_count=1,
        has_superseded=False,
    )
    assert is_epic is False


if __name__ == "__main__":
    sys.exit(__import__("pytest").main([__file__, "-q"]))
