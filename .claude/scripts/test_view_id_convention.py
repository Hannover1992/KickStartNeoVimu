#!/usr/bin/env python3
"""RED tests fuer view_id_convention.py (BL-491 AC-2, ARTIFACT 1).

STRIKT TDD RED: das Modul `view_id_convention` existiert noch NICHT.
Der Import am Modul-Kopf MUSS fehlschlagen -> Collection-Error = korrektes ROT.
Ein SEPARATER GREEN-Worker implementiert `view_id_convention.py` spaeter und macht
diese Tests gruen OHNE die Tests zu aendern (INV-BUILD-GRAIN: RED-Worker != GREEN-Worker).

Vertrag (siehe bl491_ac2_spec.md ARTIFACT 1) — reine Funktionen, kein IO:
  PREFIX = "view::"
  derive_view_id(view_rel: str) -> str
      # normalisiert Backslashes -> "/", strippt fuehrendes "./", PREFIX + rel.
      # deterministisch, eindeutig (Pfade sind eindeutig), stabil.
  resolve_view_id(fm: dict, view_rel: str) -> str
      # fm.get("id") non-empty str -> die fm-id (Frontmatter gewinnt, backward-compat).
      # sonst -> derive_view_id(view_rel).
  is_derived_id(view_id: str) -> bool
      # view_id.startswith(PREFIX)
"""
from __future__ import annotations

# RED: dieses Modul existiert noch NICHT -> ModuleNotFoundError bei Collection (= ROT).
import view_id_convention
from view_id_convention import derive_view_id, resolve_view_id, is_derived_id  # noqa: F401


# ---------------------------------------------------------------------------
# PREFIX
# ---------------------------------------------------------------------------

class TestPrefix:
    def test_prefix_value(self):
        assert view_id_convention.PREFIX == "view::"


# ---------------------------------------------------------------------------
# derive_view_id
# ---------------------------------------------------------------------------

class TestDerive:
    def test_deterministic(self):
        rel = "Backlog/BL-365-x/6_PL/BL-365-parking-lot.md"
        assert derive_view_id(rel) == derive_view_id(rel)

    def test_has_prefix(self):
        vid = derive_view_id("Backlog/BL-1/2_Model/X_Model.md")
        assert vid.startswith("view::")

    def test_spec_example(self):
        rel = "Backlog/BL-365-x/6_PL/BL-365-parking-lot.md"
        assert derive_view_id(rel) == "view::Backlog/BL-365-x/6_PL/BL-365-parking-lot.md"

    def test_backslash_normalized(self):
        # Windows-Separatoren werden auf "/" normalisiert.
        assert (
            derive_view_id("Backlog\\BL-1\\6_PL\\BL-1-parking-lot.md")
            == "view::Backlog/BL-1/6_PL/BL-1-parking-lot.md"
        )

    def test_strips_leading_dot_slash(self):
        assert (
            derive_view_id("./Backlog/BL-1/2_Model/X_Model.md")
            == "view::Backlog/BL-1/2_Model/X_Model.md"
        )

    def test_strips_leading_dot_backslash(self):
        # Fuehrendes ".\" (Backslash-Variante) wird nach Normalisierung ebenfalls gestrippt.
        assert (
            derive_view_id(".\\Backlog/BL-1/2_Model/X_Model.md")
            == "view::Backlog/BL-1/2_Model/X_Model.md"
        )

    def test_distinct_paths_distinct_ids(self):
        a = derive_view_id("Backlog/BL-1/6_PL/BL-1-parking-lot.md")
        b = derive_view_id("Backlog/BL-2/6_PL/BL-2-parking-lot.md")
        assert a != b

    def test_derive_is_derived(self):
        assert is_derived_id(derive_view_id("Backlog/BL-1/2_Model/X_Model.md")) is True


# ---------------------------------------------------------------------------
# resolve_view_id
# ---------------------------------------------------------------------------

REL = "Backlog/BL-7/6_PL/BL-7-parking-lot.md"
DERIVED = "view::Backlog/BL-7/6_PL/BL-7-parking-lot.md"


class TestResolve:
    def test_fm_id_wins_when_nonempty_str(self):
        assert resolve_view_id({"id": "VIEW.Sample"}, REL) == "VIEW.Sample"

    def test_fm_id_not_derived(self):
        # Eine echte Frontmatter-id ist KEINE derived id.
        assert is_derived_id(resolve_view_id({"id": "VIEW.Sample"}, REL)) is False

    def test_derives_when_id_missing(self):
        assert resolve_view_id({}, REL) == DERIVED

    def test_derives_when_id_none(self):
        assert resolve_view_id({"id": None}, REL) == DERIVED

    def test_derives_when_id_empty(self):
        assert resolve_view_id({"id": ""}, REL) == DERIVED

    def test_derives_when_id_whitespace(self):
        assert resolve_view_id({"id": "   "}, REL) == DERIVED

    def test_derives_when_id_non_str(self):
        assert resolve_view_id({"id": 123}, REL) == DERIVED

    def test_derived_result_is_derived(self):
        assert is_derived_id(resolve_view_id({}, REL)) is True


# ---------------------------------------------------------------------------
# is_derived_id
# ---------------------------------------------------------------------------

class TestIsDerived:
    def test_true_for_prefixed(self):
        assert is_derived_id("view::Backlog/BL-1/6_PL/x-parking-lot.md") is True

    def test_false_for_plain_id(self):
        assert is_derived_id("VIEW.Sample") is False

    def test_false_for_empty(self):
        assert is_derived_id("") is False

    def test_false_for_near_miss_prefix(self):
        # Nur exaktes "view::"-Prefix zaehlt.
        assert is_derived_id("view:Backlog/x.md") is False
