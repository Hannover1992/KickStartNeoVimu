"""
Tests fuer bl_index_updater.py (BL-428 batch_1).

RED-Phase: bl_index_updater.py existiert NICHT — alle Tests schlagen mit
ModuleNotFoundError fehl. Das ist korrektes RED gemaess TDD.
"""

import pytest

# Import-Fail IS the RED — kein bl_index_updater.py vorhanden
from bl_index_updater import update_index_row, index_row_has_done, END_ART_ENUM


# ---------------------------------------------------------------------------
# Fixtures — realistische _backlog_index.md Fragmente
# ---------------------------------------------------------------------------

HEADER = """\
| BL-ID | Title | Status | Vault-Pfad | Created | Updated | Spec-Link | Reifegrad |
|-------|-------|--------|------------|---------|---------|-----------|-----------|
"""

INDEX_WITH_COLLISION = (
    HEADER
    + "| BL-364 | Engine-Health | IN_PROGRESS | /Backlog/BL-364.md | 2026-04-10 | 2026-06-01 | null | REIF |\n"
    + "| BL-3640 | Engine-Health-Extended | PLANNED | /Backlog/BL-3640.md | 2026-05-01 | 2026-06-01 | null | REIF |\n"
)

INDEX_WITH_DRAFT = (
    HEADER
    + "| BL-428 | bl_index_updater | IN_PROGRESS | /Backlog/BL-428.md | 2026-06-20 | 2026-06-20 | null | REIF |\n"
)

INDEX_WITH_EXISTING_DONE = (
    HEADER
    + "| BL-100 | OldFeature | DONE | /Backlog/BL-100.md | 2026-01-01 | 2026-01-01 | null | REIF |\n"
    + "| BL-428 | bl_index_updater | IN_PROGRESS | /Backlog/BL-428.md | 2026-06-20 | 2026-06-20 | null | REIF |\n"
)


# ---------------------------------------------------------------------------
# AK-2: line-anchored — Substring-Kollision BL-364 vs BL-3640
# ---------------------------------------------------------------------------

class TestLineAnchoredCollision:
    """AK-2: update_index_row trifft GENAU die BL-364-Zeile, nie BL-3640."""

    def test_only_bl364_row_gets_done_status(self):
        result = update_index_row(INDEX_WITH_COLLISION, "BL-364", "DONE", "done")
        lines = result.splitlines()
        bl364_line = next(l for l in lines if "| BL-364 |" in l)
        bl3640_line = next(l for l in lines if "| BL-3640 |" in l)

        assert "DONE" in bl364_line, "BL-364-Zeile muss DONE enthalten"
        assert "DONE" not in bl3640_line, "BL-3640-Zeile darf NICHT veraendert werden"

    def test_bl3640_row_unchanged_byte_for_byte(self):
        original_bl3640 = next(
            l for l in INDEX_WITH_COLLISION.splitlines() if "| BL-3640 |" in l
        )
        result = update_index_row(INDEX_WITH_COLLISION, "BL-364", "DONE", "done")
        result_bl3640 = next(l for l in result.splitlines() if "| BL-3640 |" in l)

        assert original_bl3640 == result_bl3640


# ---------------------------------------------------------------------------
# AK-3: alle 4 END_ART_ENUM-Werte + unbekannter Fallback
# ---------------------------------------------------------------------------

class TestEndArtEnum:
    """AK-3: Status-Zelle enthaelt DONE ({end_art}) fuer alle Enum-Werte."""

    @pytest.mark.parametrize("end_art", ["done", "deferred", "PO-question", "rolled-up"])
    def test_known_end_art_appears_in_status_cell(self, end_art):
        result = update_index_row(INDEX_WITH_DRAFT, "BL-428", "DONE", end_art)
        bl428_line = next(l for l in result.splitlines() if "| BL-428 |" in l)
        assert f"DONE ({end_art})" in bl428_line

    def test_unknown_end_art_falls_back_to_done(self):
        result = update_index_row(INDEX_WITH_DRAFT, "BL-428", "DONE", "foo")
        bl428_line = next(l for l in result.splitlines() if "| BL-428 |" in l)
        assert "DONE (done)" in bl428_line

    def test_end_art_enum_contains_exactly_four_values(self):
        assert set(END_ART_ENUM) == {"done", "deferred", "PO-question", "rolled-up"}


# ---------------------------------------------------------------------------
# AK-6: Rueckwaertskompat — bestehende DONE-Zeile bleibt BYTE-IDENTISCH
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """AK-6: update auf BL-428 beruehrt BL-100-Zeile nicht."""

    def test_existing_done_row_byte_identical_after_unrelated_update(self):
        original_bl100 = next(
            l for l in INDEX_WITH_EXISTING_DONE.splitlines() if "| BL-100 |" in l
        )
        result = update_index_row(INDEX_WITH_EXISTING_DONE, "BL-428", "DONE", "done")
        result_bl100 = next(l for l in result.splitlines() if "| BL-100 |" in l)

        assert original_bl100 == result_bl100


# ---------------------------------------------------------------------------
# AK-1: Read-Back-Helper index_row_has_done
# ---------------------------------------------------------------------------

class TestIndexRowHasDone:
    """AK-1: index_row_has_done liefert True nach Update, False vorher."""

    def test_returns_true_after_update(self):
        updated = update_index_row(INDEX_WITH_DRAFT, "BL-428", "DONE", "done")
        assert index_row_has_done(updated, "BL-428") is True

    def test_returns_false_before_update(self):
        assert index_row_has_done(INDEX_WITH_DRAFT, "BL-428") is False

    def test_returns_false_for_nonexistent_id(self):
        assert index_row_has_done(INDEX_WITH_DRAFT, "BL-999") is False


# ---------------------------------------------------------------------------
# AK-5 (Idempotenz-nah): zweifaches Update liefert identisches Ergebnis
# ---------------------------------------------------------------------------

class TestIdempotency:
    """AK-5: update_index_row zweimal angewandt = idempotent, kein doppelter Suffix."""

    def test_double_update_idempotent(self):
        first = update_index_row(INDEX_WITH_DRAFT, "BL-428", "DONE", "done")
        second = update_index_row(first, "BL-428", "DONE", "done")
        assert first == second

    def test_no_double_status_suffix(self):
        first = update_index_row(INDEX_WITH_DRAFT, "BL-428", "DONE", "done")
        second = update_index_row(first, "BL-428", "DONE", "done")
        bl428_line = next(l for l in second.splitlines() if "| BL-428 |" in l)
        # "DONE (done) (done)" wuerde doppelten Suffix zeigen
        assert bl428_line.count("DONE (done)") == 1


# ---------------------------------------------------------------------------
# BL-434: Pipe-in-Title — Bug: [^|]* verrutscht Spalten wenn Titel Pipes hat
# Markdown-Schema: | BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad |
# ---------------------------------------------------------------------------

# Fixture-Zeilen fuer Pipe-in-Title-Tests (6-Spalten-Schema ohne Updated/Spec-Link)
PIPE_TITLE_HEADER = """\
| BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad |
|-------|-------|--------|------------|---------|-----------|
"""

PIPE_TITLE_DRAFT = (
    PIPE_TITLE_HEADER
    + "| BL-X | Model-Tier -> floor|middle|ceiling, keine Literale | DRAFT | Backlog/bl-x.md | 2026-06-20 | UNREIF |\n"
)

DONE_IN_TITLE_DRAFT = (
    PIPE_TITLE_HEADER
    + "| BL-Y | Implement DONE-marker logic | DRAFT | Backlog/bl-y.md | 2026-06-20 | UNREIF |\n"
)

# Fixture fuer den False-Positive-Bug: Pipe im Titel, wobei das Fragment VOR dem
# ersten Pipe "DONE inline" lautet — [^|]* stoppt nach "tier|", liest "DONE inline"
# als Status-Zelle → index_row_has_done gibt faelschlich True (Status=DRAFT)
PIPE_TITLE_DONE_FRAGMENT = (
    PIPE_TITLE_HEADER
    + "| BL-Z | tier|DONE inline | DRAFT | Backlog/bl-z.md | 2026-06-20 | UNREIF |\n"
)


class TestPipeInTitle:
    """BL-434: Spaltenversatz wenn Titel selbst Pipe-Zeichen enthaelt."""

    def test_update_pipe_in_title_only_status_changes(self):
        """Status-Spalte wird korrekt gesetzt; Titel-Pipes und Vault-Pfad bleiben intakt."""
        result = update_index_row(PIPE_TITLE_DRAFT, "BL-X", "DONE", "done")

        # Vault-Pfad muss erhalten bleiben
        assert "Backlog/bl-x.md" in result, "Vault-Pfad-Spalte muss unveraendert bleiben"

        # Titel-Pipes muessen erhalten bleiben
        assert "floor|middle|ceiling" in result, "Titel-Pipes muessen unveraendert bleiben"

        # index_row_has_done muss True zurueckgeben (echte Status-Spalte)
        assert index_row_has_done(result, "BL-X") is True, (
            "index_row_has_done muss True sein nach korrektem Update"
        )

        # DONE darf NICHT mitten im Titel stehen (vor dem Vault-Pfad)
        # Robuste Pruefung: Zeile parsen — Status-Spalte ist Spalte 3 (0-indexed: 2)
        bl_x_line = next(l for l in result.splitlines() if "| BL-X |" in l)
        # Spalten via naivem Split auf " | " — Pipe-Titel macht diesen Split fragil;
        # darum pruefen wir strukturell: nach dem letzten Vorkommen von "floor|middle|ceiling"
        # muss das FIRST echte Status-Token (DONE (done)) stehen, NICHT davor
        pipe_title_end = bl_x_line.index("floor|middle|ceiling") + len("floor|middle|ceiling")
        segment_after_title = bl_x_line[pipe_title_end:]
        assert "DONE (done)" in segment_after_title, (
            "DONE (done) muss NACH dem Titel-Abschnitt stehen, nicht mitten drin injiziert"
        )

    def test_has_done_ignores_done_in_title(self):
        """index_row_has_done gibt False wenn DONE nur im Pipe-Titel steht, Status=DRAFT.

        Fixture: | BL-Z | tier|DONE inline | DRAFT | Backlog/bl-z.md | ...
        Buggy [^|]*: group1 endet nach "tier|", group2 = "DONE inline " → "DONE" drin → True.
        Erwartung nach Fix (pipe-aware, Anker auf Vault-Pfad): False (echte Status = DRAFT).
        """
        result = index_row_has_done(PIPE_TITLE_DONE_FRAGMENT, "BL-Z")
        assert result is False, (
            "index_row_has_done darf sich nicht vom 'DONE' im Pipe-Titel taeuschen lassen; "
            "echte Status-Spalte = DRAFT, also muss False zurueckkommen"
        )

    def test_has_done_true_after_correct_update(self):
        """Nach update_index_row auf BL-X (Pipe-Titel) muss index_row_has_done True sein."""
        updated = update_index_row(PIPE_TITLE_DRAFT, "BL-X", "DONE", "done")
        assert index_row_has_done(updated, "BL-X") is True

    def test_update_pipe_idempotent(self):
        """Zweifaches update_index_row auf BL-X (Pipe-Titel) = identisches Ergebnis."""
        first = update_index_row(PIPE_TITLE_DRAFT, "BL-X", "DONE", "done")
        second = update_index_row(first, "BL-X", "DONE", "done")
        assert first == second, "Doppeltes Update muss idempotent sein; Titel-Pipes duerfen nicht akkumulieren"


# ---------------------------------------------------------------------------
# BL-434 Regression: Backslash-Pfad-Anker (aeltere BLs ohne .md-Suffix)
# Fixture: | BL-W | Foo fuer Backlog + Bar | DONE | Backlog\bl-w-slug | 2026-05-19 | REIF |
# Fallen: "Backlog" ohne Separator im Titel + Backslash-Pfad ohne .md in Pfad-Spalte
# ---------------------------------------------------------------------------

BACKSLASH_PATH_HEADER = """\
| BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad |
|-------|-------|--------|------------|---------|-----------|
"""

BACKSLASH_PATH_DONE = (
    BACKSLASH_PATH_HEADER
    + "| BL-W | Foo fuer Backlog + Bar | DONE | Backlog\\bl-w-slug | 2026-05-19 | REIF |\n"
)

BACKSLASH_PATH_DRAFT = (
    BACKSLASH_PATH_HEADER
    + "| BL-W | Foo fuer Backlog + Bar | DRAFT | Backlog\\bl-w-slug | 2026-05-19 | REIF |\n"
)


class TestBackslashPath:
    """BL-434 Regression: Backslash-Pfad-Anker fuer aeltere BLs ohne .md-Suffix."""

    def test_backslash_path_has_done(self):
        """index_row_has_done gibt True fuer Backslash-Pfad + 'Backlog'-Wort im Titel.

        Fixture: | BL-W | Foo fuer Backlog + Bar | DONE | Backlog\\bl-w-slug | ...
        Beide Fallen: 'Backlog' im Titel (kein Separator) + Backslash-Pfad ohne .md.
        _status_index muss auf Backlog\\ anchorn und korrekt True zurueckgeben.
        """
        assert index_row_has_done(BACKSLASH_PATH_DONE, "BL-W") is True, (
            "index_row_has_done muss True geben fuer Backslash-Pfad-Zeile mit DONE-Status"
        )

    def test_backslash_path_update(self):
        """update_index_row auf Backslash-Pfad-Zeile aendert nur Status; Pfad bleibt."""
        result = update_index_row(BACKSLASH_PATH_DRAFT, "BL-W", "DONE", "done")
        assert "Backlog\\bl-w-slug" in result, "Backslash-Pfad muss unveraendert bleiben"
        assert index_row_has_done(result, "BL-W") is True, (
            "index_row_has_done muss True sein nach Update auf Backslash-Pfad-Zeile"
        )
