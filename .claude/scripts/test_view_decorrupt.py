"""RED-phase tests for view_decorrupt (BL-491 AC-1, Artifact 1).

These tests intentionally target a module `view_decorrupt` that does NOT yet
exist. They MUST fail (collection/import error or assertion) until the GREEN
worker implements the module. All inputs are constructed in BYTES with explicit
CRLF (\\r\\n) and the UTF-8 BOM, matching the two real corruption shapes.
"""

import json

import pytest

import view_decorrupt  # noqa: E402  -- intentionally absent in RED state


BOM = b"\xef\xbb\xbf"


# ---------------------------------------------------------------------------
# Faithful corrupt-fixture builders (byte-exact reproductions of the real defect)
# ---------------------------------------------------------------------------

def _shape_a_raw():
    """Shape A: stray run x5 + BOM + real `---\\ntype: model` frontmatter + body.

    The BOM is part of the corruption prefix that gets REMOVED (the goal is a file
    starting with a single well-formed `---`), so the expected `real` output does
    NOT include the BOM; the BOM lives only in the corrupt `raw`.
    """
    stray = b"source_atoms:\r\n  - _meta_truths/BL-129_Model/truths/W11.md\r\n" * 5
    real = b"---\r\ntype: model\r\nid: BL-065\r\n---\r\n\r\n# Body\r\n"
    return stray + BOM + real, real


def _shape_b_raw():
    """Shape B: stray run + heading body (no frontmatter, no BOM)."""
    stray = b"source_atoms:\r\n  - Backlog/BL-050/Model/truths/W17.md\r\n" * 3
    real = b"# BL-365 Parking Lot\r\n\r\ncontent\r\n"
    return stray + real, real


# ---------------------------------------------------------------------------
# 1. Shape A: BOM-glued real frontmatter, decorrupted == exact suffix
# ---------------------------------------------------------------------------

def test_shape_a_decorrupts_to_real_frontmatter_suffix():
    raw, real = _shape_a_raw()
    out, reason = view_decorrupt.decorrupt_bytes(raw)
    assert reason == "decorrupted"
    assert out is not None
    # Cut point: real content begins after the stray run AND after the BOM.
    cut = view_decorrupt.find_stray_run_end(raw)
    assert cut == len(raw) - len(real)
    # decorrupted output starts at the real `---` (BOM swallowed)
    assert out.startswith(b"---")
    # exact suffix + byte-identical to the original real frontmatter+body
    assert out == raw[cut:]
    assert out == real
    assert raw.endswith(out)


# ---------------------------------------------------------------------------
# 2. Shape B: no-frontmatter heading body, decorrupted == exact suffix
# ---------------------------------------------------------------------------

def test_shape_b_decorrupts_to_heading_suffix():
    raw, real = _shape_b_raw()
    out, reason = view_decorrupt.decorrupt_bytes(raw)
    assert reason == "decorrupted"
    assert out is not None
    cut = view_decorrupt.find_stray_run_end(raw)
    assert out.startswith(b"# BL-365 Parking Lot")
    assert out == raw[cut:]
    assert out == real
    assert raw.endswith(out)


# ---------------------------------------------------------------------------
# 3. Repeated headers (3x source_atoms: blocks) all stripped in one pass
# ---------------------------------------------------------------------------

def test_repeated_headers_all_stripped_one_pass():
    block = (
        b"source_atoms:\r\n"
        b"  - Backlog/BL-001/Model/truths/W01.md\r\n"
        b"  - Backlog/BL-002/Model/truths/W02.md\r\n"
    )
    real = b"# Heading After Three Blocks\r\n\r\nbody text\r\n"
    raw = block * 3 + real
    out, reason = view_decorrupt.decorrupt_bytes(raw)
    assert reason == "decorrupted"
    assert out == real
    assert raw.endswith(out)
    # no stray source_atoms header remains
    assert b"source_atoms:" not in out


# ---------------------------------------------------------------------------
# 4. Idempotency: decorrupt twice -> second call is a clean skip
# ---------------------------------------------------------------------------

def test_idempotency_second_pass_skips_clean(tmp_path):
    raw, real = _shape_b_raw()
    p = tmp_path / "view.md"
    p.write_bytes(raw)

    r1 = view_decorrupt.decorrupt_file(p, write=True)
    assert r1["action"] == "decorrupt"
    assert p.read_bytes() == real

    r2 = view_decorrupt.decorrupt_file(p, write=True)
    assert r2["action"] == "skip"
    assert r2["reason"] == "clean"
    assert p.read_bytes() == real


# ---------------------------------------------------------------------------
# 5. Clean file (starts ---) -> None / skip / byte-identical
# ---------------------------------------------------------------------------

def test_clean_frontmatter_file_not_corrupt(tmp_path):
    clean = b"---\r\ntype: model\r\nid: BL-100\r\n---\r\n\r\n# Title\r\n\r\nbody\r\n"
    assert view_decorrupt.find_stray_run_end(clean) is None
    out, reason = view_decorrupt.decorrupt_bytes(clean)
    assert out is None
    assert reason == "clean"

    p = tmp_path / "clean.md"
    p.write_bytes(clean)
    res = view_decorrupt.decorrupt_file(p, write=True)
    assert res["action"] == "skip"
    assert res["reason"] == "clean"
    assert p.read_bytes() == clean


# ---------------------------------------------------------------------------
# 6. Legit no-frontmatter file with a mid-body --- HR but NO stray prefix
# ---------------------------------------------------------------------------

def test_legit_midbody_hr_not_corrupt(tmp_path):
    raw = b"## Inhalt\r\n\r\n---\r\n\r\nmore text\r\n"
    assert view_decorrupt.find_stray_run_end(raw) is None
    out, reason = view_decorrupt.decorrupt_bytes(raw)
    assert out is None
    assert reason == "clean"

    p = tmp_path / "legit.md"
    p.write_bytes(raw)
    res = view_decorrupt.decorrupt_file(p, write=True)
    assert res["action"] == "skip"
    assert p.read_bytes() == raw


# ---------------------------------------------------------------------------
# 7. saw_header required: indented list item with no source_atoms: header
# ---------------------------------------------------------------------------

def test_saw_header_required(tmp_path):
    # starts with an indented `- foo/bar.md` but NO `source_atoms:` header line
    raw = b"  - foo/bar.md\r\n  - baz/qux.md\r\n\r\n# Real Heading\r\n\r\nbody\r\n"
    assert view_decorrupt.find_stray_run_end(raw) is None
    out, reason = view_decorrupt.decorrupt_bytes(raw)
    assert out is None
    assert reason == "clean"


# ---------------------------------------------------------------------------
# 8. empty_after_decorrupt: only a stray block, no real body -> refuse, no write
# ---------------------------------------------------------------------------

def test_empty_after_decorrupt_refused_not_written(tmp_path):
    raw = (
        b"source_atoms:\r\n"
        b"  - Backlog/BL-001/Model/truths/W01.md\r\n"
        b"  - Backlog/BL-002/Model/truths/W02.md\r\n"
    )
    out, reason = view_decorrupt.decorrupt_bytes(raw)
    assert out is None
    assert reason == "empty_after_decorrupt"

    p = tmp_path / "only_stray.md"
    p.write_bytes(raw)
    res = view_decorrupt.decorrupt_file(p, write=True)
    assert res["action"] == "skip"
    assert res["reason"] == "empty_after_decorrupt"
    # must NOT be written/modified
    assert p.read_bytes() == raw


# ---------------------------------------------------------------------------
# 9. SUFFIX invariant: for a corrupt input, raw.endswith(decorrupted_bytes)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("builder", [_shape_a_raw, _shape_b_raw])
def test_suffix_invariant(builder):
    raw, real = builder()
    cut = view_decorrupt.find_stray_run_end(raw)
    out, reason = view_decorrupt.decorrupt_bytes(raw)
    assert reason == "decorrupted"
    assert out is not None
    # load-bearing safety property
    assert raw.endswith(out)
    assert out == raw[cut:]
    assert out == real


# ---------------------------------------------------------------------------
# 10. _meta_truths/ exclusion: discover_corrupt skips a corrupt atom file
# ---------------------------------------------------------------------------

def test_meta_truths_excluded_from_discover(tmp_path):
    raw_b, _ = _shape_b_raw()

    # a corrupt view file (should be discovered)
    view = tmp_path / "Backlog" / "BL-365" / "view.md"
    view.parent.mkdir(parents=True)
    view.write_bytes(raw_b)

    # a corrupt file under _meta_truths/ (must NEVER be touched/discovered)
    atom = tmp_path / "_meta_truths" / "BL-129_Model" / "truths" / "W11.md"
    atom.parent.mkdir(parents=True)
    atom.write_bytes(raw_b)

    found = view_decorrupt.discover_corrupt(tmp_path)
    found_resolved = {p.resolve() for p in found}
    assert view.resolve() in found_resolved
    assert atom.resolve() not in found_resolved


# ---------------------------------------------------------------------------
# 11. dry-run default: decorrupt_file(write=False) does NOT modify disk
# ---------------------------------------------------------------------------

def test_dry_run_default_does_not_modify_disk(tmp_path):
    raw, real = _shape_a_raw()
    p = tmp_path / "view.md"
    p.write_bytes(raw)

    res = view_decorrupt.decorrupt_file(p, write=False)
    assert res["action"] == "decorrupt"
    # disk is UNCHANGED in dry-run
    assert p.read_bytes() == raw


# ---------------------------------------------------------------------------
# 12. write mode: decorrupt_file(write=True) writes decorrupted bytes
# ---------------------------------------------------------------------------

def test_write_mode_persists_decorrupted_bytes(tmp_path):
    raw, real = _shape_a_raw()
    p = tmp_path / "view.md"
    p.write_bytes(raw)

    res = view_decorrupt.decorrupt_file(p, write=True)
    assert res["action"] == "decorrupt"
    assert res["shape"] == "A"
    assert res["removed_bytes"] == len(raw) - len(real)
    # reread == the new (decorrupted) bytes, exact suffix of the original
    assert p.read_bytes() == real
    assert raw.endswith(p.read_bytes())


# ---------------------------------------------------------------------------
# Bonus coverage of run() / main() public API (still part of Artifact 1 surface)
# ---------------------------------------------------------------------------

def test_run_default_dry_run_zero_writes(tmp_path):
    raw_a, real_a = _shape_a_raw()
    raw_b, real_b = _shape_b_raw()
    (tmp_path / "a.md").write_bytes(raw_a)
    (tmp_path / "b.md").write_bytes(raw_b)

    report = view_decorrupt.run(tmp_path, write=False)
    assert report["vault"] == str(tmp_path)
    assert report["write"] is False
    assert report["total_candidates"] == 2
    # dry-run: nothing on disk changed
    assert (tmp_path / "a.md").read_bytes() == raw_a
    assert (tmp_path / "b.md").read_bytes() == raw_b


def test_main_default_is_dry_run(tmp_path):
    raw_b, _ = _shape_b_raw()
    p = tmp_path / "b.md"
    p.write_bytes(raw_b)
    rc = view_decorrupt.main(["--vault", str(tmp_path)])
    assert rc == 0
    # default (no --write) performs ZERO writes
    assert p.read_bytes() == raw_b


def test_main_write_mode_modifies_and_optional_out(tmp_path):
    raw_b, real_b = _shape_b_raw()
    p = tmp_path / "b.md"
    p.write_bytes(raw_b)
    out_json = tmp_path / "report.json"
    rc = view_decorrupt.main(
        ["--vault", str(tmp_path), "--write", "--out", str(out_json), "--quiet"]
    )
    assert rc == 0
    assert p.read_bytes() == real_b
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["write"] is True
