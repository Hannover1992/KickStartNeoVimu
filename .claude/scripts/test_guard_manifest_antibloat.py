#!/usr/bin/env python3
"""Tests fuer guard_manifest_antibloat.py (BL-229 AK-D)."""
import json
import os
import subprocess
import sys
from pathlib import Path

from guard_manifest_antibloat import (
    check_antibloat,
    count_suffixed_state_blocks,
    _is_suffixed_state_header,
)

GUARD = Path(__file__).parent / "guard_manifest_antibloat.py"


# ── Header-Klassifikation ──
def test_header_round_paren():
    assert _is_suffixed_state_header("## DF_BATCH_STATE (Round 17 - recluster)")
    assert _is_suffixed_state_header("## IDF_PIPELINE_STATE (Round 11)")


def test_header_round_suffix():
    assert _is_suffixed_state_header("## BERATER_OUTPUTS_plBewertung_round15")


def test_header_bare_canonical_not_suffixed():
    assert not _is_suffixed_state_header("## DF_BATCH_STATE")
    assert not _is_suffixed_state_header("## BERATER_OUTPUTS")


def test_header_non_state_round_ignored():
    # round im Titel aber keine State-Familie -> kein Treffer (kein Fehl-Block)
    assert not _is_suffixed_state_header("## Retrospektive (Round 3 notes)")


# ── count ──
def test_count_mixed():
    content = (
        "## DF_BATCH_STATE\n...\n"
        "## DF_BATCH_STATE (Round 5)\n...\n"
        "## IDF_PIPELINE_STATE (Round 11)\n...\n"
        "## BERATER_OUTPUTS_modusEntscheidung_round7\n...\n"
    )
    assert count_suffixed_state_blocks(content) == 3


# ── check_antibloat ──
def test_block_append_suffixed():
    old = "## DF_BATCH_STATE\nstate\n"
    new = old + "## DF_BATCH_STATE (Round 6)\nhistory\n"
    allow, reason = check_antibloat(old, new)
    assert allow is False and "AK-D" in reason and "1 round-suffixed" in reason


def test_allow_bare_overwrite():
    old = "## DF_BATCH_STATE\nold-state\n## DF_BATCH_STATE (Round 5)\nhist\n"
    new = "## DF_BATCH_STATE\nNEW-state\n## DF_BATCH_STATE (Round 5)\nhist\n"
    allow, _ = check_antibloat(old, new)
    assert allow is True


def test_allow_offload_reduces_suffixed():
    old = "## X (Round 1)\n## DF_BATCH_STATE (Round 5)\n"
    new = "## DF_BATCH_STATE\n"  # slim: suffixed weg
    allow, _ = check_antibloat(old, new)
    assert allow is True


def test_allow_empty_to_bare():
    allow, _ = check_antibloat("", "## DF_BATCH_STATE\nstate\n")
    assert allow is True


# ── Hook (default disarmed + armed-block) ──
def test_hook_disarmed_by_default():
    r = subprocess.run([sys.executable, str(GUARD)], input="{}", capture_output=True, text=True)
    assert json.loads(r.stdout)["continue"] is True


def test_hook_armed_blocks_append(tmp_path):
    m = tmp_path / "_manifest.md"
    m.write_text("## DF_BATCH_STATE\nstate\n", encoding="utf-8")
    event = {"tool_input": {"file_path": str(m),
                            "content": "## DF_BATCH_STATE\nstate\n## DF_BATCH_STATE (Round 6)\nh\n"}}
    env = {**os.environ, "OMNI_MANIFEST_ANTIBLOAT": "on"}
    r = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                       capture_output=True, text=True, env=env)
    out = json.loads(r.stdout)
    assert out["continue"] is False and "AK-D" in out["message"]
