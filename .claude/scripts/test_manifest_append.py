#!/usr/bin/env python3
"""Tests fuer manifest_append.py (BL-367 F8/F9 — gemeinsamer Manifest-Append-Helper)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from manifest_append import append_block, count_col0_fences  # noqa: E402

BOM = b"\xef\xbb\xbf"


# --- count_col0_fences (F8-Korrektur: nur Spalte-0-Fences) -----------------------------

def test_count_col0_fences_counts_only_col0():
    text = "```\nyaml\n```\n"            # 2 col-0 Fences
    assert count_col0_fences(text) == 2


def test_count_col0_fences_excludes_indented():
    # Eingerueckte / Prosa-``` (mit fuehrendem Whitespace) zaehlen NICHT (F8-KORREKTUR).
    text = "prosa:\n    ```\n    code\n    ```\nende\n"
    assert count_col0_fences(text) == 0


def test_count_col0_fences_mixed():
    text = "```\nblock\n```\nprosa\n    ```\n    indented\n    ```\n"  # 2 col-0 + 2 indent
    assert count_col0_fences(text) == 2


# --- Eigenschaft 1: utf-8 no-BOM -------------------------------------------------------

def test_strips_bom_on_read_and_writes_no_bom(tmp_path):
    f = tmp_path / "m.md"
    f.write_bytes(BOM + b"# Manifest\n**KEY:** val\n")
    append_block(str(f), "## NEU\nfeld: 1")
    raw = f.read_bytes()
    assert not raw.startswith(BOM), "BOM darf nach Write nicht mehr da sein"
    assert b"## NEU" in raw


def test_new_file_written_without_bom(tmp_path):
    f = tmp_path / "fresh.md"
    res = append_block(str(f), "## ERSTBLOCK\nx: 1")
    raw = f.read_bytes()
    assert not raw.startswith(BOM)
    assert res["ok"] and not res["existed"]
    assert "## ERSTBLOCK" in f.read_text(encoding="utf-8")


# --- Eigenschaft 2: col-0-fence-balanced ----------------------------------------------

def test_balanced_block_ok(tmp_path):
    f = tmp_path / "m.md"
    f.write_text("# M\n", encoding="utf-8")
    res = append_block(str(f), "## B\n```\nyaml: 1\n```")   # 2 col-0 Fences = balanciert
    assert res["ok"]
    assert res["col0_fences"] % 2 == 0


def test_odd_block_raises_no_write(tmp_path):
    f = tmp_path / "m.md"
    f.write_text("# M\n", encoding="utf-8")
    before = f.read_bytes()
    with pytest.raises(RuntimeError, match="Fence-Imbalance|Imbalance"):
        append_block(str(f), "## B\n```\nyaml: 1")          # 1 col-0 Fence = ungerade
    assert f.read_bytes() == before, "bei Fence-Imbalance darf NICHT geschrieben werden"


def test_preexisting_imbalance_raises(tmp_path):
    f = tmp_path / "m.md"
    f.write_text("# M\n```\noffen\n", encoding="utf-8")     # Bestand bereits 1 col-0 = ungerade
    with pytest.raises(RuntimeError, match="Bestand bereits unbalanciert"):
        append_block(str(f), "## B\nfeld: 1")               # Block balanciert, Bestand kaputt


def test_indented_prose_fence_does_not_break_balance(tmp_path):
    f = tmp_path / "m.md"
    f.write_text("# M\n", encoding="utf-8")
    # Block mit echtem col-0-Paar + eingerueckter Prosa-``` -> col-0 bleibt gerade.
    res = append_block(str(f), "## B\n```\nyaml: 1\n```\nNote:\n    ```\n    snippet\n    ```")
    assert res["ok"]


# --- Eigenschaft 3: line-separator-safe (kein Glue) -----------------------------------

def test_no_glue_when_existing_lacks_trailing_newline(tmp_path):
    f = tmp_path / "m.md"
    f.write_bytes(b"**KEY:** true")                          # KEIN trailing newline
    append_block(str(f), "**KEY2:** false")
    text = f.read_text(encoding="utf-8")
    assert "**KEY:** true**KEY2:**" not in text, "Zeilen duerfen nicht verklebt werden"
    lines = [l for l in text.replace("\r\n", "\n").split("\n") if l.strip()]
    assert "**KEY:** true" in lines and "**KEY2:** false" in lines


def test_preserves_crlf(tmp_path):
    f = tmp_path / "m.md"
    f.write_bytes(b"# M\r\n**KEY:** v\r\n")
    append_block(str(f), "## NEU\nz: 1")
    raw = f.read_bytes()
    assert b"\r\n" in raw, "CRLF-Stil muss erhalten bleiben"
    assert b"## NEU\r\n" in raw


def test_preserves_lf(tmp_path):
    f = tmp_path / "m.md"
    f.write_bytes(b"# M\n**KEY:** v\n")
    append_block(str(f), "## NEU\nz: 1")
    raw = f.read_bytes()
    assert b"\r\n" not in raw, "LF-Stil muss erhalten bleiben"
    assert b"## NEU\n" in raw


# --- Eigenschaft 4: post-write Re-Read-Assert (Marker) --------------------------------

def test_default_marker_is_first_nonempty_block_line(tmp_path):
    f = tmp_path / "m.md"
    res = append_block(str(f), "\n\n## DEFAULT-MARKER\nrest: 1")
    assert res["marker"] == "## DEFAULT-MARKER"
    assert res["ok"]


def test_custom_marker_present(tmp_path):
    f = tmp_path / "m.md"
    f.write_text("# M\n", encoding="utf-8")
    res = append_block(str(f), "## B\nUNIQUE_TOKEN_42: yes", marker="UNIQUE_TOKEN_42")
    assert res["ok"] and res["marker"] == "UNIQUE_TOKEN_42"


# --- Eigenschaft (Eingaben) -----------------------------------------------------------

def test_empty_block_raises(tmp_path):
    f = tmp_path / "m.md"
    with pytest.raises(ValueError):
        append_block(str(f), "   \n  \n")


def test_two_appends_both_present(tmp_path):
    f = tmp_path / "m.md"
    append_block(str(f), "## ERSTER\na: 1")
    append_block(str(f), "## ZWEITER\nb: 2")
    text = f.read_text(encoding="utf-8")
    assert "## ERSTER" in text and "## ZWEITER" in text
    assert count_col0_fences(text) % 2 == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
