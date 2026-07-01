#!/usr/bin/env python3
"""RED-phase tests for truth_hash_heal (module does not exist yet).

All tests must fail with ModuleNotFoundError until truth_hash_heal.py is
implemented. No vault touched -- all fixtures use tmp_path only.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

# RED: this import will fail until the module is created
import truth_hash_heal
from truth_hash_heal import expected_hash, heal, main


# ---------------------------------------------------------------------------
# Internal helper (not the module under test)
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_atom(
    path: Path,
    text_val: str,
    content_hash_val: str,
    atom_id: str = "atom-001",
    local_id: str = "loc-001",
    body: str = "\nThis is the body of the atom.\n",
) -> str:
    """Write a minimal type:truth atom .md file; return the exact content string."""
    content = (
        "---\n"
        "type: truth\n"
        f"id: {atom_id}\n"
        f"local_id: {local_id}\n"
        f"text: {text_val}\n"
        f"content_hash: {content_hash_val}\n"
        "---\n"
        + body
    )
    path.write_text(content, encoding="utf-8")
    return content


def _parse_fm(content: str) -> dict:
    """Return yaml-parsed frontmatter dict from atom content string."""
    close = content.index("\n---\n", 4)  # first \n---\n after opening ---\n
    fm_text = content[4:close]           # skip leading ---\n
    return yaml.safe_load(fm_text)


def _body_after_fm(content: str) -> str:
    """Return the body string (everything after the closing ---\\n)."""
    close = content.index("\n---\n", 4)
    return content[close + len("\n---\n"):]


# ---------------------------------------------------------------------------
# Test 1: expected_hash primitive
# ---------------------------------------------------------------------------

def test_expected_hash_known_string():
    """expected_hash(text) == hashlib.sha256(text.encode('utf-8')).hexdigest()."""
    text = "Hello, OmniCommand truth atom!"
    assert expected_hash(text) == _sha256(text)


def test_expected_hash_empty_string():
    assert expected_hash("") == _sha256("")


def test_expected_hash_unicode():
    text = "Korrektheit und Kohaerenz im Vault"
    assert expected_hash(text) == _sha256(text)


def test_expected_hash_64_hex_chars():
    """Result is a 64-character hex string (sha256 output width)."""
    result = expected_hash("any text")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# Test 2: dry-run on wrong-hash atom
# ---------------------------------------------------------------------------

def test_heal_dryrun_wrong_hash(tmp_path):
    """Dry-run: mismatched>=1, would_update>=1, updated==0, file on disk UNCHANGED."""
    atom = tmp_path / "atom.md"
    text_val = "the canonical text"
    wrong_hash = "deadbeef" + "0" * 56  # 64-char hex, intentionally wrong
    _write_atom(atom, text_val, wrong_hash)
    original_bytes = atom.read_bytes()

    result = heal(tmp_path, apply=False)

    assert result["mismatched"] >= 1
    assert result["would_update"] >= 1
    assert result["updated"] == 0
    assert atom.read_bytes() == original_bytes, "dry-run must not modify file on disk"


def test_heal_dryrun_returns_expected_keys(tmp_path):
    """heal() return dict has all required int keys."""
    result = heal(tmp_path, apply=False)
    for key in ("scanned", "mismatched", "would_update", "updated", "backed_up"):
        assert key in result, f"Missing key: {key}"
        assert isinstance(result[key], int), f"Key {key} must be int"


# ---------------------------------------------------------------------------
# Test 3: apply on wrong-hash atom
# ---------------------------------------------------------------------------

def test_heal_apply_wrong_hash_updates_content_hash(tmp_path):
    """Apply: updated>=1; content_hash == sha256(text) after heal."""
    atom = tmp_path / "atom.md"
    text_val = "the canonical text for healing"
    wrong_hash = "deadbeef" + "0" * 56
    _write_atom(atom, text_val, wrong_hash)

    result = heal(tmp_path, apply=True)

    assert result["updated"] >= 1

    after = atom.read_text(encoding="utf-8")
    fm = _parse_fm(after)
    assert fm["content_hash"] == _sha256(text_val), (
        "content_hash must equal sha256(text) after heal"
    )


def test_heal_apply_text_field_unchanged(tmp_path):
    """Apply: text field value is UNCHANGED after heal."""
    atom = tmp_path / "atom.md"
    text_val = "unchanged text value"
    wrong_hash = "deadbeef" + "0" * 56
    _write_atom(atom, text_val, wrong_hash)

    heal(tmp_path, apply=True)

    after = atom.read_text(encoding="utf-8")
    fm = _parse_fm(after)
    assert fm["text"] == text_val, "text field must be unchanged"


def test_heal_apply_other_frontmatter_fields_intact(tmp_path):
    """Apply: id and local_id fields are preserved byte-identical."""
    atom = tmp_path / "atom.md"
    text_val = "some text"
    wrong_hash = "deadbeef" + "0" * 56
    _write_atom(atom, text_val, wrong_hash, atom_id="atom-XYZ", local_id="loc-XYZ")

    heal(tmp_path, apply=True)

    after = atom.read_text(encoding="utf-8")
    fm = _parse_fm(after)
    assert fm["id"] == "atom-XYZ"
    assert fm["local_id"] == "loc-XYZ"


def test_heal_apply_body_byte_identical(tmp_path):
    """Apply: body (after closing ---) is byte-identical to original."""
    atom = tmp_path / "atom.md"
    text_val = "body preservation test"
    wrong_hash = "deadbeef" + "0" * 56
    body = "\nFirst body line.\nSecond body line.\nThird body line.\n"
    original_content = _write_atom(atom, text_val, wrong_hash, body=body)
    original_body = _body_after_fm(original_content)

    heal(tmp_path, apply=True)

    after = atom.read_text(encoding="utf-8")
    assert _body_after_fm(after) == original_body, "body must be byte-identical"


# ---------------------------------------------------------------------------
# Test 4: idempotent -- already correct hash
# ---------------------------------------------------------------------------

def test_heal_correct_hash_no_op(tmp_path):
    """Atom with correct hash: mismatched==0, would_update==0, file unchanged."""
    atom = tmp_path / "atom.md"
    text_val = "already correct content"
    correct_hash = _sha256(text_val)
    _write_atom(atom, text_val, correct_hash)
    original_bytes = atom.read_bytes()

    result = heal(tmp_path, apply=True)

    assert result["mismatched"] == 0
    assert result["would_update"] == 0
    assert result["updated"] == 0
    assert atom.read_bytes() == original_bytes, "correct atom must not be touched"


def test_heal_idempotent_second_run(tmp_path):
    """Running heal twice on a healed atom: second run is a no-op."""
    atom = tmp_path / "atom.md"
    text_val = "idempotent test text"
    wrong_hash = "cafebabe" + "0" * 56
    _write_atom(atom, text_val, wrong_hash)

    result1 = heal(tmp_path, apply=True)
    assert result1["updated"] >= 1

    result2 = heal(tmp_path, apply=True)
    assert result2["updated"] == 0, "second heal must be a no-op (idempotent)"
    assert result2["mismatched"] == 0


# ---------------------------------------------------------------------------
# Test 5: surgical -- only the content_hash: line changes
# ---------------------------------------------------------------------------

def test_heal_surgical_only_content_hash_line_changes(tmp_path):
    """Exactly one line changes after heal: the content_hash: line."""
    atom = tmp_path / "atom.md"
    text_val = "surgical precision text"
    wrong_hash = "baadf00d" + "0" * 56

    # Write directly so we control exact line order and body
    before_content = (
        "---\n"
        "type: truth\n"
        "id: atom-001\n"
        "local_id: loc-001\n"
        f"text: {text_val}\n"
        f"content_hash: {wrong_hash}\n"
        "---\n"
        "\nBody line one.\nBody line two.\n"
    )
    atom.write_text(before_content, encoding="utf-8")
    before_lines = before_content.splitlines(keepends=True)

    heal(tmp_path, apply=True)

    after_content = atom.read_text(encoding="utf-8")
    after_lines = after_content.splitlines(keepends=True)

    # Same number of lines (no lines added or removed)
    assert len(before_lines) == len(after_lines), (
        f"Line count changed: before={len(before_lines)} after={len(after_lines)}"
    )

    # Collect differing lines
    changed = [
        (i, bl, al)
        for i, (bl, al) in enumerate(zip(before_lines, after_lines))
        if bl != al
    ]

    assert len(changed) == 1, (
        f"Expected exactly 1 changed line, got {len(changed)}: {changed}"
    )

    _idx, before_line, after_line = changed[0]
    assert before_line.startswith("content_hash:"), (
        f"Changed line is not content_hash: {before_line!r}"
    )
    assert after_line.startswith("content_hash:"), (
        f"Replacement line does not start with content_hash: {after_line!r}"
    )
    new_hash_val = after_line.split(":", 1)[1].strip().rstrip("\n")
    assert new_hash_val == _sha256(text_val), (
        f"New hash value wrong: {new_hash_val!r} != {_sha256(text_val)!r}"
    )


def test_heal_surgical_all_other_lines_present_in_order(tmp_path):
    """All non-content_hash lines from before appear in the same order after."""
    atom = tmp_path / "atom.md"
    text_val = "order preservation text"
    wrong_hash = "baadf00d" + "0" * 56

    before_content = (
        "---\n"
        "type: truth\n"
        "id: atom-001\n"
        "local_id: loc-001\n"
        f"text: {text_val}\n"
        f"content_hash: {wrong_hash}\n"
        "---\n"
        "\nBody line one.\nBody line two.\n"
    )
    atom.write_text(before_content, encoding="utf-8")
    non_hash_before = [
        ln for ln in before_content.splitlines(keepends=True)
        if not ln.startswith("content_hash:")
    ]

    heal(tmp_path, apply=True)

    after_content = atom.read_text(encoding="utf-8")
    non_hash_after = [
        ln for ln in after_content.splitlines(keepends=True)
        if not ln.startswith("content_hash:")
    ]

    assert non_hash_before == non_hash_after, (
        "All non-content_hash lines must be identical in order"
    )


# ---------------------------------------------------------------------------
# Test 6: backup
# ---------------------------------------------------------------------------

def test_heal_backup_file_created_with_relative_path(tmp_path):
    """backup_dir: backup file exists at backup_dir / atom.relative_to(root)."""
    sub = tmp_path / "sub"
    sub.mkdir()
    atom = sub / "atom.md"
    text_val = "backup path test"
    wrong_hash = "cafebabe" + "0" * 56
    _write_atom(atom, text_val, wrong_hash)

    backup_dir = tmp_path / "backups"
    heal(tmp_path, apply=True, backup_dir=backup_dir)

    rel = atom.relative_to(tmp_path)
    backup_file = backup_dir / rel
    assert backup_file.exists(), f"Backup not found at {backup_file}"


def test_heal_backup_bytes_equal_original(tmp_path):
    """Backup bytes == original pre-heal content encoded utf-8 (LF convention)."""
    atom = tmp_path / "atom.md"
    text_val = "backup byte equality test"
    wrong_hash = "cafebabe" + "0" * 56
    original_content = _write_atom(atom, text_val, wrong_hash)
    # LF-normalized convention (read_text + encode, matching truth_keyword_demerge)
    expected_backup_bytes = original_content.encode("utf-8")

    backup_dir = tmp_path / "backups"
    heal(tmp_path, apply=True, backup_dir=backup_dir)

    backup_file = backup_dir / "atom.md"
    assert backup_file.read_bytes() == expected_backup_bytes, (
        "Backup bytes must equal original pre-heal content bytes"
    )


def test_heal_backed_up_equals_updated(tmp_path):
    """backed_up count == updated count when backup_dir is provided."""
    for i in range(2):
        atom = tmp_path / f"atom{i}.md"
        text_val = f"text for atom {i}"
        wrong_hash = f"{i:064x}"  # wrong hash
        _write_atom(atom, text_val, wrong_hash)

    backup_dir = tmp_path / "backups"
    result = heal(tmp_path, apply=True, backup_dir=backup_dir)

    assert result["backed_up"] == result["updated"]


def test_heal_no_backup_without_backup_dir(tmp_path):
    """backed_up==0 when backup_dir is not provided."""
    atom = tmp_path / "atom.md"
    text_val = "no backup test"
    wrong_hash = "deadbeef" + "0" * 56
    _write_atom(atom, text_val, wrong_hash)

    result = heal(tmp_path, apply=True, backup_dir=None)

    assert result["backed_up"] == 0


def test_heal_backup_contains_pre_heal_hash(tmp_path):
    """Backup yaml still has the old wrong hash (not the new one)."""
    atom = tmp_path / "atom.md"
    text_val = "pre-heal hash in backup"
    wrong_hash = "deadbeef" + "0" * 56
    _write_atom(atom, text_val, wrong_hash)

    backup_dir = tmp_path / "backups"
    heal(tmp_path, apply=True, backup_dir=backup_dir)

    backup_content = (backup_dir / "atom.md").read_text(encoding="utf-8")
    fm = _parse_fm(backup_content)
    assert fm["content_hash"] == wrong_hash, (
        "Backup must preserve original (wrong) content_hash"
    )


# ---------------------------------------------------------------------------
# Test 7: main() CLI
# ---------------------------------------------------------------------------

def test_main_dryrun_exits_0_no_change(tmp_path):
    """main([root]) dry-run: exits 0, no changes written."""
    atom = tmp_path / "atom.md"
    text_val = "cli dryrun text"
    wrong_hash = "0" * 64
    _write_atom(atom, text_val, wrong_hash)
    original_bytes = atom.read_bytes()

    rc = main([str(tmp_path)])

    assert rc == 0
    assert atom.read_bytes() == original_bytes, "dry-run must not modify file"


def test_main_apply_exits_0_and_heals(tmp_path):
    """main([root, '--apply']): exits 0, heals wrong hashes."""
    atom = tmp_path / "atom.md"
    text_val = "cli apply text"
    wrong_hash = "0" * 64
    _write_atom(atom, text_val, wrong_hash)

    rc = main([str(tmp_path), "--apply"])

    assert rc == 0
    after = atom.read_text(encoding="utf-8")
    fm = _parse_fm(after)
    assert fm["content_hash"] == _sha256(text_val)


def test_main_nonexistent_root_returns_2(tmp_path):
    """main with non-existent path returns 2."""
    rc = main([str(tmp_path / "nonexistent_dir")])
    assert rc == 2


def test_main_file_as_root_returns_2(tmp_path):
    """main with a file path (not dir) returns 2."""
    f = tmp_path / "not_a_dir.txt"
    f.write_text("x", encoding="utf-8")
    rc = main([str(f)])
    assert rc == 2


def test_main_apply_with_backup_dir(tmp_path):
    """main([root, '--apply', '--backup-dir', dir]) creates backup."""
    atom = tmp_path / "atom.md"
    text_val = "cli backup text"
    wrong_hash = "0" * 64
    original_content = _write_atom(atom, text_val, wrong_hash)

    backup_dir = tmp_path / "cli_backups"
    rc = main([str(tmp_path), "--apply", "--backup-dir", str(backup_dir)])

    assert rc == 0
    backup_file = backup_dir / "atom.md"
    assert backup_file.exists()
    assert backup_file.read_bytes() == original_content.encode("utf-8")


# ---------------------------------------------------------------------------
# Test 8: scanned count and type filtering
# ---------------------------------------------------------------------------

def test_heal_scanned_counts_all_md_files(tmp_path):
    """scanned == total number of .md files in tree, regardless of type."""
    correct = _sha256("some text")
    for i in range(3):
        f = tmp_path / f"atom{i}.md"
        _write_atom(f, "some text", correct)

    result = heal(tmp_path, apply=False)
    assert result["scanned"] == 3


def test_heal_skips_non_truth_type(tmp_path):
    """Non-truth type atoms are not counted as mismatched even if hash is wrong."""
    bad_hash = "deadbeef" + "0" * 56
    atom = tmp_path / "edge.md"
    atom.write_text(
        "---\n"
        "type: truth_edge\n"
        "id: edge-001\n"
        "text: some edge text\n"
        f"content_hash: {bad_hash}\n"
        "---\n"
        "\nEdge body.\n",
        encoding="utf-8",
    )

    result = heal(tmp_path, apply=False)

    assert result["mismatched"] == 0, (
        "Non-truth type atoms must not be counted as mismatched"
    )


def test_heal_mixed_atoms_only_heals_wrong(tmp_path):
    """With one correct and one wrong atom, only wrong is updated."""
    text_ok = "text with correct hash"
    text_bad = "text with wrong hash"

    atom_ok = tmp_path / "ok.md"
    _write_atom(atom_ok, text_ok, _sha256(text_ok))

    atom_bad = tmp_path / "bad.md"
    wrong_hash = "deadbeef" + "0" * 56
    _write_atom(atom_bad, text_bad, wrong_hash)

    result = heal(tmp_path, apply=True)

    assert result["mismatched"] == 1
    assert result["updated"] == 1

    # ok atom unchanged
    fm_ok = _parse_fm(atom_ok.read_text(encoding="utf-8"))
    assert fm_ok["content_hash"] == _sha256(text_ok)

    # bad atom healed
    fm_bad = _parse_fm(atom_bad.read_text(encoding="utf-8"))
    assert fm_bad["content_hash"] == _sha256(text_bad)


def test_heal_empty_dir(tmp_path):
    """Empty directory: scanned==0, all counts 0, exits cleanly."""
    result = heal(tmp_path, apply=True)
    assert result["scanned"] == 0
    assert result["mismatched"] == 0
    assert result["updated"] == 0


def test_heal_walks_subdirectories(tmp_path):
    """heal scans .md files in nested subdirectories."""
    sub = tmp_path / "nested" / "deeper"
    sub.mkdir(parents=True)
    atom = sub / "deep_atom.md"
    text_val = "deep text"
    wrong_hash = "deadbeef" + "0" * 56
    _write_atom(atom, text_val, wrong_hash)

    result = heal(tmp_path, apply=True)

    assert result["scanned"] >= 1
    assert result["updated"] >= 1
    fm = _parse_fm(atom.read_text(encoding="utf-8"))
    assert fm["content_hash"] == _sha256(text_val)
