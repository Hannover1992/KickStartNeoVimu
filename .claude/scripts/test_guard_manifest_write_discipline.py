#!/usr/bin/env python3
"""Tests fuer guard_manifest_write_discipline.classify_command (BL-367 INV-MANIFEST-WRITE-1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from guard_manifest_write_discipline import classify_command  # noqa: E402


def _v(cmd):
    return classify_command(cmd)[0]


# --- PASS: sanktionierter Helper -------------------------------------------------------

def test_helper_invocation_pass():
    assert _v('py -3 .claude/scripts/manifest_append.py X/_manifest.md --block-file b.md') == "PASS"


def test_helper_pass_even_with_python3_word():
    # Helper-Pfad enthaelt zwar ein Manifest, aber manifest_append -> PASS (Exemption gewinnt).
    assert _v('python3 .claude/scripts/manifest_append.py _manifest.md --block -') == "PASS"


# --- PASS: kein ad-hoc Write -----------------------------------------------------------

def test_read_manifest_pass():
    assert _v('Get-Content X/_manifest.md -Raw') == "PASS"


def test_git_add_manifest_pass():
    assert _v('git add .claude/_manifest.md') == "PASS"


def test_non_manifest_command_pass():
    assert _v('Out-File -FilePath notes.md') == "PASS"


def test_empty_pass():
    assert _v('') == "PASS"
    assert _v('   ') == "PASS"


# --- WARN: ad-hoc Manifest-Writes ------------------------------------------------------

def test_out_file_manifest_warn():
    assert _v('"block" | Out-File -Append X/_manifest.md') == "WARN"


def test_add_content_manifest_warn():
    assert _v('Add-Content -Path _manifest.md -Value "x: 1"') == "WARN"


def test_set_content_manifest_warn():
    assert _v('Set-Content _manifest.md $text') == "WARN"


def test_writealltext_manifest_warn():
    assert _v('[System.IO.File]::WriteAllText("_manifest.md", $t)') == "WARN"


def test_append_redirect_manifest_warn():
    assert _v('echo "x: 1" >> .claude/_manifest.md') == "WARN"


def test_python3_manifest_warn():
    assert _v('python3 append_block.py .claude/_manifest.md') == "WARN"


def test_factory_manifest_warn():
    assert _v('Add-Content _factory_manifest.md "x"') == "WARN"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
