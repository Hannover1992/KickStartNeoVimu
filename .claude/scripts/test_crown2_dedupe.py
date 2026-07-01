# -*- coding: utf-8 -*-
"""Tests fuer crown2_dedupe.py (BL-252 AK-4 — Cluster<->Bestands-Backlog-Dedupe).

M3, RED->GREEN. Reiner/deterministischer Matcher + cwd-stabiler Loader.
Nutzt ausschliesslich tmp-Fixtures — mutiert NIEMALS die echten Live-Dateien.

Der mechanisierbare Teil von Crown-2 Phase 4 (DEDUPE): bevor pro echtem Cluster
ein BL generiert wird, prueft dieser Helper, ob bereits ein Bestands-BL die
Abweichung abdeckt. Die opus-Adjudikation (genuine vs noise) lebt NICHT hier,
sondern im Skill — hier nur die deterministische Signatur<->BL-Matchung.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crown2_dedupe import (  # noqa: E402
    cluster_already_tracked,
    cluster_signature_from_cluster,
    load_existing_bls,
    _normalize,
)


# ---------------------------------------------------------------------------
# Fixtures: Mini-Index + Mini-Backlog-Nodes (alle in tmp)
# ---------------------------------------------------------------------------

def _write_index(path, rows):
    """rows: Liste von (bl_id, title, status)."""
    lines = [
        "---",
        "format_version: 1",
        "backlog_counter: 345",
        'backlog_last_update: "2026-06-13"',
        "---",
        "",
        "# Backlog Index",
        "",
        "| BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad |",
        "|-------|-------|--------|------------|---------|-----------|",
    ]
    for bl_id, title, status in rows:
        lines.append(
            f"| {bl_id} | {title} | {status} | Backlog\\{bl_id}.md | 2026-06-01 |  |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_bl(backlog_dir, bl_id, title, status, body=""):
    fp = backlog_dir / f"{bl_id}.md"
    fp.write_text(
        "---\n"
        f"id: {bl_id}\n"
        f'title: "{title}"\n'
        f"status: {status}\n"
        "---\n\n"
        f"# {bl_id}\n\n{body}\n",
        encoding="utf-8",
    )
    return fp


@pytest.fixture
def vault(tmp_path):
    backlog = tmp_path / "Backlog"
    backlog.mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Kern-Matcher: cluster_already_tracked
# ---------------------------------------------------------------------------

def test_known_cluster_matches_existing_bl():
    """Bekannter Cluster (kind + Schluessel-Evidence-Terme) -> match (skip)."""
    existing = [
        {
            "bl_id": "BL-344",
            "title": "factory_lock.acquire_bl TOCTOU-Races: false-stale-Reclaim",
            "body": "zwei TOCTOU-Races in acquire_bl unter Gleichzeitigkeit",
        },
        {"bl_id": "BL-001", "title": "Wahrheiten Taxonomie", "body": ""},
    ]
    sig = {
        "kind": "stale_lock_reclaim",
        "terms": ["acquire_bl", "TOCTOU", "factory_lock"],
    }
    hit = cluster_already_tracked(sig, existing)
    assert hit == "BL-344"


def test_new_cluster_no_match():
    """Neuer Cluster -> kein match (generate)."""
    existing = [
        {"bl_id": "BL-344", "title": "factory_lock TOCTOU", "body": "lock races"},
        {"bl_id": "BL-001", "title": "Wahrheiten Taxonomie", "body": ""},
    ]
    sig = {
        "kind": "param_mutation_blocked",
        "terms": ["session_params", "bypass_field", "workflow_dial"],
    }
    hit = cluster_already_tracked(sig, existing)
    assert hit is False


def test_empty_backlog_no_match():
    """Leerer Bestands-Backlog -> kein match (generate)."""
    sig = {"kind": "guard_block", "terms": ["geist9", "loopDecision"]}
    assert cluster_already_tracked(sig, []) is False


def test_signature_without_terms_requires_strong_kind_match():
    """Ohne Terme reicht ein blosser kind-Treffer NICHT (zu schwach -> kein match)."""
    existing = [
        {"bl_id": "BL-344", "title": "lock stale reclaim irgendwas", "body": ""},
    ]
    sig = {"kind": "stale_lock_reclaim", "terms": []}
    # Konservativ: ohne Schluessel-Terme keine verlaessliche Dedupe -> generate.
    assert cluster_already_tracked(sig, existing) is False


def test_partial_term_overlap_below_threshold_no_match():
    """Nur 1 von vielen Termen trifft -> unter Schwelle -> kein match."""
    existing = [
        {"bl_id": "BL-100", "title": "irgendein lock thema", "body": "acquire stuff"},
    ]
    sig = {
        "kind": "stale_lock_reclaim",
        # nur "acquire" trifft, "TOCTOU"/"heartbeat"/"reclaim"/"mkdir" nicht
        "terms": ["acquire", "TOCTOU", "heartbeat", "reclaim", "mkdir"],
    }
    assert cluster_already_tracked(sig, existing) is False


def test_case_insensitive_and_substring_matching():
    """Matching ist case-insensitiv und term-substring-tolerant."""
    existing = [
        {
            "bl_id": "BL-345",
            "title": "import-zeitiges sys.exit() crasht pytest-Bulk-Collection",
            "body": "INTERNALERROR SystemExit beim Import",
        },
    ]
    sig = {
        "kind": "test_hygiene",
        "terms": ["SYS.EXIT", "PyTest", "INTERNALError"],
    }
    assert cluster_already_tracked(sig, existing) == "BL-345"


# ---------------------------------------------------------------------------
# cluster_signature_from_cluster: Cluster -> Signatur
# ---------------------------------------------------------------------------

def test_signature_from_cluster_extracts_kind_and_terms():
    cluster = {
        "kind": "guard_block",
        "signals": [
            {"kind": "guard_block", "evidence": {"guard": "geist9", "hook": "loopDecision"}},
            {"kind": "guard_block", "evidence": {"guard": "geist9", "phase": "PostBatch"}},
        ],
    }
    sig = cluster_signature_from_cluster(cluster)
    assert sig["kind"] == "guard_block"
    # Schluessel-Evidence-Terme aus den Signal-evidence-Werten extrahiert
    assert "geist9" in [t.lower() for t in sig["terms"]]


# ---------------------------------------------------------------------------
# load_existing_bls: cwd-stabiler Loader (Index + offene Nodes)
# ---------------------------------------------------------------------------

def test_load_existing_bls_reads_index_and_bodies(vault):
    _write_index(
        vault / "_backlog_index.md",
        [
            ("BL-001", "Erstes Thema", "DONE"),
            ("BL-344", "factory_lock TOCTOU", "DONE"),
            ("BL-345", "pytest collection crash", "DRAFT"),
        ],
    )
    _write_bl(vault / "Backlog", "BL-344", "factory_lock TOCTOU", "DONE",
              body="acquire_bl reclaim race heartbeat")
    _write_bl(vault / "Backlog", "BL-345", "pytest collection crash", "DRAFT",
              body="sys.exit INTERNALERROR import-time")

    bls = load_existing_bls(vault)
    ids = {b["bl_id"] for b in bls}
    assert "BL-344" in ids
    assert "BL-345" in ids
    # Body aus dem Node-File ist mitgeladen (fuer Term-Matching)
    bl344 = next(b for b in bls if b["bl_id"] == "BL-344")
    assert "heartbeat" in bl344["body"].lower()


def test_load_existing_bls_open_only(vault):
    """open_only=True filtert DONE/DECOMPOSED raus (nur offene Items)."""
    _write_index(
        vault / "_backlog_index.md",
        [
            ("BL-001", "Erledigtes", "DONE"),
            ("BL-345", "Offenes", "DRAFT"),
        ],
    )
    _write_bl(vault / "Backlog", "BL-345", "Offenes", "DRAFT", body="b")
    bls = load_existing_bls(vault, open_only=True)
    ids = {b["bl_id"] for b in bls}
    assert "BL-345" in ids
    assert "BL-001" not in ids


def test_load_existing_bls_missing_index_robust(vault):
    """Fehlender Index -> leere Liste, kein Crash."""
    assert load_existing_bls(vault) == []


def test_load_existing_bls_no_param_uses_default_resolution():
    """Ohne vault_root-Param crasht der Loader nicht (cwd-stabile Default-Aufloesung)."""
    # Default-Vault existiert evtl. nicht in der Testumgebung -> robust [] erwartet,
    # aber NIEMALS Crash und NIEMALS cwd-relativ.
    result = load_existing_bls()
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# _normalize Helper (Determinismus-Basis)
# ---------------------------------------------------------------------------

def test_normalize_lowercases_and_strips():
    assert _normalize("  ACQUIRE_BL  ") == "acquire_bl"
    assert _normalize(None) == ""
    assert _normalize(42) == "42"
