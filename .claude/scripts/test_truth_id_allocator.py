#!/usr/bin/env python3
"""Tests fuer truth_id_allocator.py (BL-387 / EIN kollisionsfreier Allokator)."""
from __future__ import annotations

import truth_id_allocator as al


def test_next_is_max_plus_one():
    assert al.next_local_id({"W01", "W02", "W05"}) == "W06"


def test_max_plus_one_not_count_plus_one_with_gap():
    """DER Defekt-Fix: bei Luecke {W01,W03} ist count+1=W03 (KOLLISION); max+1=W04 ist korrekt."""
    assert al.next_local_id({"W01", "W03"}) == "W04"


def test_empty_starts_at_one():
    assert al.next_local_id(set()) == "W01"


def test_width_convention_preserved():
    assert al.next_local_id({"W001", "W002"}) == "W003"


def test_dashed_ids_ignored_for_number_but_no_collision():
    # W-AK-A ist nicht numerisch -> zaehlt nicht fuer max, aber Ergebnis darf nicht kollidieren
    assert al.next_local_id({"W01", "W-AK-A"}) == "W02"


def test_suffix_letter_id_counts_numeric():
    # W12a -> numerischer Teil 12 -> next = W13
    assert al.next_local_id({"W12a"}) == "W13"


def test_result_never_in_existing():
    existing = {"W01", "W02", "W04"}
    assert al.next_local_id(existing) not in existing


def test_allocate_batch_sequential_no_collision():
    out = al.allocate_batch({"W01"}, 3)
    assert out == ["W02", "W03", "W04"]
    assert len(set(out)) == 3


def test_w_number_helper():
    assert al.w_number("W07") == 7
    assert al.w_number("W12a") == 12
    assert al.w_number("W-IST-1") is None
