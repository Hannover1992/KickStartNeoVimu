#!/usr/bin/env python3
"""Tests fuer truth_dedup.py (BL-309 R4 / Duplikat-Detektor)."""
from __future__ import annotations

import hashlib

import truth_dedup as dd


def _t(tid, text, chash=None):
    d = {"id": tid, "local_id": tid.split(".")[-1], "text": text}
    if chash is not None:
        d["content_hash"] = chash
    return d


def test_dedup_groups_finds_same_content():
    truths = [_t("BL-a.W01", "gleiche Aussage"), _t("BL-b.W02", "gleiche Aussage"), _t("BL-c.W03", "andere")]
    groups = dd.dedup_groups(truths)
    assert len(groups) == 1
    members = list(groups.values())[0]
    assert {dd._truth_id(t) for t in members} == {"BL-a.W01", "BL-b.W02"}


def test_no_duplicates_empty():
    truths = [_t("BL-a.W01", "eins"), _t("BL-a.W02", "zwei")]
    assert dd.dedup_groups(truths) == {}


def test_alias_plan_canonical_is_smallest_id():
    truths = [_t("BL-b.W02", "x"), _t("BL-a.W01", "x"), _t("BL-c.W03", "x")]
    plan = dd.alias_plan(truths)
    assert len(plan) == 1
    assert plan[0]["canonical"] == "BL-a.W01"
    assert plan[0]["aliases"] == ["BL-b.W02", "BL-c.W03"]


def test_uses_content_hash_field_when_present():
    # gleiche content_hash -> Duplikat, auch bei abweichendem text-Feld (hash ist autoritativ)
    h = hashlib.sha256("kanonisch".encode("utf-8")).hexdigest()
    truths = [_t("BL-a.W01", "text egal", chash=h), _t("BL-b.W02", "anders egal", chash=h)]
    assert len(dd.dedup_groups(truths)) == 1


def test_dedup_stats():
    truths = [_t("BL-a.W01", "x"), _t("BL-b.W02", "x"), _t("BL-c.W03", "y")]
    stats = dd.dedup_stats(truths)
    assert stats["duplicate_groups"] == 1
    assert stats["duplicate_members"] == 2
    assert stats["collapsible_to_alias"] == 1  # 2 Mitglieder -> 1 kanonisch + 1 Alias
