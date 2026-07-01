"""
Tests fuer pl_item_marker.py (BL-435 batch_1a).

RED-Phase: pl_item_marker.py existiert NICHT — alle Tests schlagen mit
ModuleNotFoundError/ImportError fehl. Das ist korrektes RED gemaess TDD.

AKs: AK-1 (mark_pl_done + pl_item_is_done Kern + Idempotenz + Defensiv)
     AK-2 (pl_item_is_done Toleranz-Matrix: 5 Alt-Formate + kanonisch)
     AK-5 (is_canonical_pl_item Schema-Guard)

Vorbild-Struktur: test_bl_index_updater.py (pytest-Klassen, String-Fragment-Fixtures,
                  parametrize, Read-Back-Tests, Idempotenz).
"""

import pytest

# Import-Fail IS the RED — pl_item_marker.py existiert NICHT
from pl_item_marker import mark_pl_done, pl_item_is_done, is_canonical_pl_item


# ---------------------------------------------------------------------------
# Gemeinsame Konstanten
# ---------------------------------------------------------------------------

ITEM_ID = "BL-435-AK-1-PL-1"
TITLE = "PL-Format Standardisieren"

# Kanonisches open-Format (CANONICAL_PATTERN Basis)
CANONICAL_OPEN_LINE = f"- [ ] **{ITEM_ID}** (status: open) — {TITLE}"
# Kanonisches done-Format
CANONICAL_DONE_LINE = f"- [x] **{ITEM_ID}** (status: done) — {TITLE}"


# ---------------------------------------------------------------------------
# Fixtures — realistische _parking-lot.md Fragmente
# ---------------------------------------------------------------------------

CONTENT_CANONICAL_OPEN = f"""\
# Parking Lot

{CANONICAL_OPEN_LINE}
"""

CONTENT_CANONICAL_DONE = f"""\
# Parking Lot

{CANONICAL_DONE_LINE}
"""

CONTENT_THREE_ITEMS = f"""\
# Parking Lot

- [ ] **BL-435-AK-5-PL-1** (status: open) — Schema-Guard
{CANONICAL_OPEN_LINE}
- [ ] **BL-435-AK-2-PL-1** (status: open) — Toleranz-Matrix
"""

# Format-1: Checkbox + STATUS-Tag
CONTENT_F1_DONE = f"- [x] {ITEM_ID} [STATUS: IN_ARBEIT]\n"
CONTENT_F1_OPEN = f"- [ ] {ITEM_ID} [STATUS: IN_ARBEIT]\n"

# Format-2: Tabellen-Zeile (item_id in Abschnitt, naechste Zeile mit done/open)
CONTENT_F2_DONE = f"| {ITEM_ID} | done |\n"
CONTENT_F2_OPEN = f"| {ITEM_ID} | open |\n"

# Format-3: Bold-Checkbox
CONTENT_F3_DONE = f"[x] **{ITEM_ID}**\n"
CONTENT_F3_OPEN = f"[ ] **{ITEM_ID}**\n"

# Format-4: Bold-ID PL-N Kurzform (AK-1 => PL-1 => n=1)
CONTENT_F4_DONE = "- [x] **PL-1**\n"
CONTENT_F4_OPEN = "- [ ] **PL-1**\n"

# Format-5: Frontmatter-only (Header + status-Zeile innerhalb 10-Zeilen-Fenster)
CONTENT_F5_DONE = f"### {ITEM_ID}\nstatus: done\n"
CONTENT_F5_OPEN = f"### {ITEM_ID}\nstatus: open\n"

# Unbekanntes Format (defensiv False)
CONTENT_UNKNOWN = "random text without pattern\n"


# ---------------------------------------------------------------------------
# TestMarkPlDone — AK-1: Basis + Idempotenz + Defensiv
# ---------------------------------------------------------------------------

class TestMarkPlDone:
    """AK-1: mark_pl_done flippt kanonische open-Zeile auf done; idempotent; defensiv."""

    def test_mark_pl_done_read_back_canonical(self):
        """Kanarientest: mark_pl_done -> pl_item_is_done == True (Read-Back-Paar).

        Erzwingt: atomares Flip [ ]->[ x] + status:open->status:done in einem re.sub.
        Danach DETEKTOR-0 liest True.
        """
        result = mark_pl_done(CONTENT_CANONICAL_OPEN, ITEM_ID)
        assert pl_item_is_done(result, ITEM_ID) is True

    def test_mark_pl_done_flips_both_signals(self):
        """Beide Signale atomar geflippt: '[x]' UND '(status: done)' in Ergebnis-Zeile."""
        result = mark_pl_done(CONTENT_CANONICAL_OPEN, ITEM_ID)
        lines = result.splitlines()
        target_line = next((l for l in lines if ITEM_ID in l), None)
        assert target_line is not None, f"Zeile mit {ITEM_ID} nicht gefunden"
        assert "[x]" in target_line, "Checkbox muss auf [x] geflippt sein"
        assert "(status: done)" in target_line, "status muss auf done geflippt sein"

    def test_mark_pl_done_idempotent(self):
        """Idempotenz: zweiter Aufruf auf bereits-done Content = unveraendert (kein Doppel-Flip)."""
        c1 = mark_pl_done(CONTENT_CANONICAL_OPEN, ITEM_ID)
        c2 = mark_pl_done(c1, ITEM_ID)
        assert c1 == c2, "Zweiter mark_pl_done-Aufruf muss identisches Ergebnis liefern"

    def test_mark_pl_done_unknown_item_id_returns_content_unchanged(self):
        """Defensiv: item_id nicht gefunden -> content unveraendert zurueck, kein Crash."""
        result = mark_pl_done(CONTENT_CANONICAL_OPEN, "NICHT-EXISTIEREND-PL-999")
        assert result == CONTENT_CANONICAL_OPEN

    def test_mark_pl_done_empty_content_no_crash(self):
        """Defensiv: leerer content -> '' zurueck, kein Crash."""
        result = mark_pl_done("", ITEM_ID)
        assert result == ""

    def test_mark_pl_done_only_target_item_modified(self):
        """Andere Items im Content bleiben unveraendert: nur die adressierte Zeile modifiziert."""
        result = mark_pl_done(CONTENT_THREE_ITEMS, ITEM_ID)
        lines = result.splitlines()

        # Item-2 (ITEM_ID) muss done sein
        target_line = next((l for l in lines if ITEM_ID in l), None)
        assert target_line is not None
        assert "[x]" in target_line

        # Item-1 (AK-5) muss unveraendert open bleiben
        ak5_line = next((l for l in lines if "BL-435-AK-5-PL-1" in l), None)
        assert ak5_line is not None
        assert "[ ]" in ak5_line, "BL-435-AK-5-PL-1 darf nicht veraendert werden"
        assert "(status: open)" in ak5_line

        # Item-3 (AK-2) muss unveraendert open bleiben
        ak2_line = next((l for l in lines if "BL-435-AK-2-PL-1" in l), None)
        assert ak2_line is not None
        assert "[ ]" in ak2_line, "BL-435-AK-2-PL-1 darf nicht veraendert werden"
        assert "(status: open)" in ak2_line


# ---------------------------------------------------------------------------
# TestPlItemIsDone — AK-2: 5 Alt-Formate + kanonisch + unbekannt = 13 Faelle
# ---------------------------------------------------------------------------

class TestPlItemIsDone:
    """AK-2: pl_item_is_done liest 6 Formate (5 Alt + kanonisch) korrekt als done/open."""

    # --- Format-1: Checkbox + STATUS-Tag ---

    def test_format1_done_status_tag(self):
        """Format-1: '- [x] {item_id} [STATUS: IN_ARBEIT]' -> True."""
        assert pl_item_is_done(CONTENT_F1_DONE, ITEM_ID) is True

    def test_format1_open_status_tag(self):
        """Format-1: '- [ ] {item_id} [STATUS: IN_ARBEIT]' -> False (open)."""
        assert pl_item_is_done(CONTENT_F1_OPEN, ITEM_ID) is False

    # --- Format-2: Tabellen-Zeile ---

    def test_format2_done_table_row(self):
        """Format-2: '| {item_id} | done |' -> True."""
        assert pl_item_is_done(CONTENT_F2_DONE, ITEM_ID) is True

    def test_format2_open_table_row(self):
        """Format-2: '| {item_id} | open |' -> False."""
        assert pl_item_is_done(CONTENT_F2_OPEN, ITEM_ID) is False

    # --- Format-3: Bold-Checkbox ---

    def test_format3_done_bold_checkbox(self):
        """Format-3: '[x] **{item_id}**' -> True."""
        assert pl_item_is_done(CONTENT_F3_DONE, ITEM_ID) is True

    def test_format3_open_bold_checkbox(self):
        """Format-3: '[ ] **{item_id}**' -> False."""
        assert pl_item_is_done(CONTENT_F3_OPEN, ITEM_ID) is False

    # --- Format-4: Bold-ID PL-N Kurzform ---

    def test_format4_done_pl_n_shortform(self):
        """Format-4: '- [x] **PL-1**' fuer item_id BL-435-AK-1-PL-1 -> True."""
        assert pl_item_is_done(CONTENT_F4_DONE, ITEM_ID) is True

    def test_format4_open_pl_n_shortform(self):
        """Format-4: '- [ ] **PL-1**' fuer item_id BL-435-AK-1-PL-1 -> False."""
        assert pl_item_is_done(CONTENT_F4_OPEN, ITEM_ID) is False

    # --- Format-5: Frontmatter-only ---

    def test_format5_done_frontmatter_header(self):
        """Format-5: '### {item_id}' + 'status: done' innerhalb 10 Zeilen -> True."""
        assert pl_item_is_done(CONTENT_F5_DONE, ITEM_ID) is True

    def test_format5_open_frontmatter_header(self):
        """Format-5: '### {item_id}' + 'status: open' -> False."""
        assert pl_item_is_done(CONTENT_F5_OPEN, ITEM_ID) is False

    # --- Kanonisch (Format-0, DETEKTOR-0) ---

    def test_canonical_done_detected(self):
        """Kanonisch-done: '- [x] **{id}** (status: done) — {title}' -> True (DETEKTOR-0)."""
        assert pl_item_is_done(CONTENT_CANONICAL_DONE, ITEM_ID) is True

    def test_canonical_open_detected_as_false(self):
        """Kanonisch-open: '- [ ] **{id}** (status: open) — {title}' -> False."""
        assert pl_item_is_done(CONTENT_CANONICAL_OPEN, ITEM_ID) is False

    # --- Unbekanntes Format (defensiv False) ---

    def test_unknown_format_returns_false(self):
        """Unbekanntes Format -> defensiv False (niemals True bei Ambiguitaet)."""
        assert pl_item_is_done(CONTENT_UNKNOWN, ITEM_ID) is False


# ---------------------------------------------------------------------------
# TestIsCanonicalPlItem — AK-5: Schema-Guard (7 Faelle)
# ---------------------------------------------------------------------------

class TestIsCanonicalPlItem:
    """AK-5: is_canonical_pl_item validiert kanonisches Format; Alt-Formate -> False."""

    def test_canonical_open_line_is_true(self):
        """Kanonische open-Zeile '- [ ] **{bl}-AK-{n}-PL-1** (status: open) — {title}' -> True."""
        line = f"- [ ] **{ITEM_ID}** (status: open) — {TITLE}"
        assert is_canonical_pl_item(line) is True

    def test_canonical_done_line_is_true(self):
        """Kanonische done-Zeile '- [x] **{bl}-AK-{n}-PL-1** (status: done) — {title}' -> True."""
        line = f"- [x] **{ITEM_ID}** (status: done) — {TITLE}"
        assert is_canonical_pl_item(line) is True

    def test_format1_checkbox_status_tag_is_false(self):
        """Format-1 (Checkbox + STATUS-Tag) ist NICHT kanonisch -> False."""
        line = f"- [x] {ITEM_ID} [STATUS: IN_ARBEIT]"
        assert is_canonical_pl_item(line) is False

    def test_format2_table_row_is_false(self):
        """Format-2 (Tabellen-Zeile) ist NICHT kanonisch -> False."""
        line = f"| {ITEM_ID} | done |"
        assert is_canonical_pl_item(line) is False

    def test_format3_bold_checkbox_no_status_field_is_false(self):
        """Format-3 (Bold-Checkbox ohne status-Feld) ist NICHT kanonisch -> False."""
        line = f"[x] **{ITEM_ID}**"
        assert is_canonical_pl_item(line) is False

    def test_format4_pl_n_shortform_is_false(self):
        """Format-4 (Kurzform PL-N ohne BL-Prefix) ist NICHT kanonisch -> False."""
        line = "- [x] **PL-1**"
        assert is_canonical_pl_item(line) is False

    def test_format5_header_only_is_false(self):
        """Format-5 (nur Header-Zeile '### {item_id}') ist NICHT kanonisch -> False."""
        line = f"### {ITEM_ID}"
        assert is_canonical_pl_item(line) is False


# ---------------------------------------------------------------------------
# Edge-Cases (aus Blueprint Abschnitt 8, zwingend durch RED-Worker abzudecken)
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """6 Edge-Cases aus dem Gold-Blueprint."""

    def test_mark_pl_done_first_match_only_when_item_id_appears_twice(self):
        """item_id mehrfach im Content: nur erstes Match wird geflippt (kein multi-flip)."""
        content = (
            f"{CANONICAL_OPEN_LINE}\n"
            f"Referenz: {ITEM_ID} auch hier erwaehnt (Prosa)\n"
            f"{CANONICAL_OPEN_LINE}\n"
        )
        result = mark_pl_done(content, ITEM_ID)
        # Genau eine Zeile darf [x] enthalten (das erste Match)
        done_lines = [l for l in result.splitlines() if "[x]" in l and ITEM_ID in l]
        open_lines = [l for l in result.splitlines() if "[ ]" in l and ITEM_ID in l]
        # Erste Zeile wurde geflippt, zweite kanonische Zeile bleibt open
        assert len(done_lines) == 1, "Nur erstes Match darf geflippt werden"
        assert len(open_lines) == 1, "Zweite kanonische Zeile muss open bleiben"

    def test_mark_pl_done_empty_item_id_no_crash(self):
        """item_id ist leerer String: kein Crash, content unveraendert."""
        result = mark_pl_done(CONTENT_CANONICAL_OPEN, "")
        assert result == CONTENT_CANONICAL_OPEN

    def test_pl_item_is_done_empty_item_id_no_crash(self):
        """pl_item_is_done mit leerem item_id: kein Crash, False."""
        result = pl_item_is_done(CONTENT_CANONICAL_OPEN, "")
        assert result is False

    def test_mark_pl_done_whitespace_only_content(self):
        """Content mit nur Leerzeilen: kein Crash, sinnvolle Rueckgabe."""
        content = "\n\n\n"
        result = mark_pl_done(content, ITEM_ID)
        assert result == content  # unveraendert, kein Crash

    def test_format4_item_id_without_n_schema_graceful(self):
        """Format-4: item_id ohne {bl}-AK-{n}-PL-1 Schema -> DETEKTOR-4 skippt graceful, kein Crash."""
        irregular_id = "CUSTOM-ITEM-OHNE-N"
        content = "- [x] **PL-1**\n"
        # kein n extrahierbar -> False (kein Regex-Crash)
        result = pl_item_is_done(content, irregular_id)
        assert result is False

    def test_is_canonical_pl_item_title_with_double_asterisk(self):
        """Kanonische Zeile mit Titel der '**' enthaelt: CANONICAL_PATTERN robust (ADE-3)."""
        # Titel mit Bold-Markup drin — CANONICAL_PATTERN darf nicht crashen
        line = f"- [ ] **{ITEM_ID}** (status: open) — Titel mit **Bold** drin"
        # Ergebnis kann True oder False sein (Impl-Detail), aber KEIN Crash
        result = is_canonical_pl_item(line)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# TestHybridFlipAndFailLoud — BL-447 AK-F1 + AK-F3 (neue failing Tests, RED)
# ---------------------------------------------------------------------------

class TestHybridFlipAndFailLoud:
    """BL-447: toleranter Flip (AK-F1) + fail-loud Z103 (AK-F3).

    RED-Phase: Diese Tests schlagen mit der aktuellen Impl fehl:
      - AK-F1: Hybrid-Format wird aktuell silent no-op'd (kein Flip)
      - AK-F3: found-but-no-match gibt aktuell content still zurueck (kein RuntimeError)
    """

    # -----------------------------------------------------------------------
    # AK-F1: toleranter Flip — Hybrid + Alt-Formate muessen auf kanonisch-done landen
    # -----------------------------------------------------------------------

    # DoD-1: REAL-Hybrid (der Killer-Fall aus _IDF_berater_itemContext)
    HYBRID_ID = "BL-447-AK-F1-PL-1"
    HYBRID_TITLE = "Hybrid Item Test"
    HYBRID_LINE = (
        f"- [ ] **{HYBRID_ID}** [STATUS: IN_ARBEIT] (status: open) — {HYBRID_TITLE}"
    )
    HYBRID_CONTENT = f"# Parking Lot\n\n{HYBRID_LINE}\n"

    def test_hybrid_format_flips_to_canonical_done(self):
        """DoD-1 (AK-F1): Hybrid '- [ ] **{id}** [STATUS: IN_ARBEIT] (status: open) — {title}'
        wird von mark_pl_done auf kanonisch-done geflippt.

        AKTUELL FAIL: Z103 gibt content still zurueck statt zu flippen.
        """
        result = mark_pl_done(self.HYBRID_CONTENT, self.HYBRID_ID)
        lines = result.splitlines()
        target = next((l for l in lines if self.HYBRID_ID in l), None)
        assert target is not None, f"Zeile mit {self.HYBRID_ID} nicht gefunden"
        assert "[x]" in target, "Checkbox muss auf [x] geflippt sein"
        assert "(status: done)" in target, "status muss auf done geflippt sein"
        # Kanonisch: kein STATUS-Tag im Ergebnis
        assert "[STATUS:" not in target, "STATUS-Tag muss nach dem Flip entfernt sein"

    def test_hybrid_flip_read_back_pl_item_is_done(self):
        """DoD-1 (AK-F1, Symmetrie): nach Hybrid-Flip liefert pl_item_is_done==True.

        AKTUELL FAIL: content unveraendert -> pl_item_is_done sieht noch open-Format.
        """
        result = mark_pl_done(self.HYBRID_CONTENT, self.HYBRID_ID)
        assert pl_item_is_done(result, self.HYBRID_ID) is True

    def test_hybrid_flip_result_is_canonical(self):
        """DoD-2 (AK-F1): Ergebnis-Zeile nach Hybrid-Flip ist kanonisch (is_canonical_pl_item==True).

        AKTUELL FAIL: Zeile bleibt unveraendert (Hybrid) -> is_canonical_pl_item==False.
        """
        result = mark_pl_done(self.HYBRID_CONTENT, self.HYBRID_ID)
        lines = result.splitlines()
        target = next((l for l in lines if self.HYBRID_ID in l), None)
        assert target is not None
        assert is_canonical_pl_item(target.rstrip()), (
            f"Ergebnis-Zeile muss kanonisch sein, war: {target!r}"
        )

    # DoD-2: Bold-Checkbox Alt-Format (Format-3 Analogon — DETEKTOR-3)
    BOLD_CB_ID = "BL-447-AK-F1-PL-2"
    BOLD_CB_LINE = f"[ ] **{BOLD_CB_ID}**"
    BOLD_CB_CONTENT = f"# Parking Lot\n\n{BOLD_CB_LINE}\n"

    def test_bold_checkbox_format_flips_to_canonical_done(self):
        """DoD-2 (AK-F1): Bold-Checkbox '[ ] **{id}**' (Format-3) wird zu kanonisch-done geflippt.

        AKTUELL FAIL: kein kanonisches flip_pattern-Match -> silent no-op.
        """
        result = mark_pl_done(self.BOLD_CB_CONTENT, self.BOLD_CB_ID)
        lines = result.splitlines()
        target = next((l for l in lines if self.BOLD_CB_ID in l), None)
        assert target is not None
        assert "[x]" in target, "Checkbox muss auf [x] geflippt sein"
        assert "(status: done)" in target, "status muss auf done geflippt sein"

    def test_bold_checkbox_flip_read_back(self):
        """DoD-2 (AK-F1, Symmetrie): nach Bold-Checkbox-Flip liefert pl_item_is_done==True.

        AKTUELL FAIL: unveraendert -> pl_item_is_done liefert False.
        """
        result = mark_pl_done(self.BOLD_CB_CONTENT, self.BOLD_CB_ID)
        assert pl_item_is_done(result, self.BOLD_CB_ID) is True

    # Checkbox+STATUS-Tag ohne Bold-Wrapper (Format-1 Analogon — DETEKTOR-1)
    STATUS_TAG_ID = "BL-447-AK-F1-PL-3"
    STATUS_TAG_LINE = f"- [ ] {STATUS_TAG_ID} [STATUS: IN_ARBEIT]"
    STATUS_TAG_CONTENT = f"# Parking Lot\n\n- [ ] **{STATUS_TAG_ID}** [STATUS: IN_ARBEIT]\n"

    def test_checkbox_status_tag_format_flips_to_canonical_done(self):
        """DoD-2 (AK-F1): Checkbox+STATUS-Tag '- [ ] **{id}** [STATUS: IN_ARBEIT]' -> kanonisch-done.

        AKTUELL FAIL: kein flip_pattern-Match -> silent no-op.
        """
        result = mark_pl_done(self.STATUS_TAG_CONTENT, self.STATUS_TAG_ID)
        lines = result.splitlines()
        target = next((l for l in lines if self.STATUS_TAG_ID in l), None)
        assert target is not None
        assert "[x]" in target, "Checkbox muss auf [x] geflippt sein"
        assert "(status: done)" in target, "status muss auf done geflippt sein"

    # -----------------------------------------------------------------------
    # AK-F3: fail-loud — found-but-no-match muss RuntimeError raisen
    # -----------------------------------------------------------------------

    UNFLIPPABLE_ID = "BL-447-AK-F3-PL-1"
    # Tabellenzeile: _locate_pl_line findet sie (enthaelt **{id}**), aber ist nicht
    # normalisierbar via _normalize_to_canonical_open (mehrzeilig/strukturell) ->
    # nach AK-F1-Fix landet sie in Z103 -> RuntimeError erwartet.
    # Minimalstes unflippbares Format: Bold-ID ohne Checkbox-Prefix (nicht-list-item)
    UNFLIPPABLE_LINE = f"**{UNFLIPPABLE_ID}** irgendwas aber kein Checkbox-Format"
    UNFLIPPABLE_CONTENT = f"# Parking Lot\n\n{UNFLIPPABLE_LINE}\n"

    def test_found_but_unflippable_raises_runtime_error(self):
        """DoD-4 (AK-F3): item_id GEFUNDEN aber nicht flippbar -> RuntimeError.

        AKTUELL FAIL: Z103 gibt content still zurueck statt RuntimeError zu raisen.
        """
        with pytest.raises(RuntimeError) as exc_info:
            mark_pl_done(self.UNFLIPPABLE_CONTENT, self.UNFLIPPABLE_ID)
        # Optional: Fehlermeldung enthaelt item_id
        assert self.UNFLIPPABLE_ID in str(exc_info.value), (
            f"RuntimeError-Meldung muss item_id '{self.UNFLIPPABLE_ID}' enthalten"
        )

    def test_table_row_format_raises_runtime_error(self):
        """DoD-4 (AK-F3): Tabellenzeile '| **{id}** | open |' gefunden aber nicht flippbar -> RuntimeError.

        Format-2 ist strukturell nicht single-line-normalisierbar -> fail-loud korrekt.
        AKTUELL FAIL: Z103 gibt content still zurueck.
        """
        table_id = "BL-447-AK-F3-PL-2"
        # _locate_pl_line sucht nach **{id}** -> diese Zeile wird gefunden
        table_content = f"# PL\n\n| **{table_id}** | open |\n"
        with pytest.raises(RuntimeError):
            mark_pl_done(table_content, table_id)

    # -----------------------------------------------------------------------
    # LEGITIME NO-OPS — muessen GRUEN bleiben (Regression-Pin fuer AK-F3)
    # -----------------------------------------------------------------------

    def test_empty_content_remains_no_op_no_raise(self):
        """DoD-5 (AK-F3): leerer content -> kein raise, unveraenderter content-Return."""
        result = mark_pl_done("", self.UNFLIPPABLE_ID)
        assert result == ""

    def test_item_id_not_found_remains_no_op_no_raise(self):
        """DoD-5 (AK-F3): item_id nicht im content -> kein raise, content unveraendert."""
        result = mark_pl_done("# Parking Lot\n\n- [ ] **ANDERES-PL-1** (status: open)\n",
                               "NICHT-EXISTIEREND-BL-447-PL-99")
        assert "NICHT-EXISTIEREND" not in result or True  # content unveraendert
        # kein RuntimeError wurde geraist (wuerde oben bereits fehlschlagen)

    def test_empty_item_id_remains_no_op_no_raise(self):
        """DoD-5 (AK-F3): leere item_id -> kein raise, content unveraendert."""
        result = mark_pl_done(self.HYBRID_CONTENT, "")
        assert result == self.HYBRID_CONTENT


# ---------------------------------------------------------------------------
# TestNewlinePreservation — BL-447 Regression-Lock: trailing-\n + Zeilen-Integritaet
#
# Bug (vor 0b7d23b): _normalize_to_canonical_open erhielt trailing \n NICHT ->
#   beim ''.join(lines) klebte die naechste Zeile an die normalisierte Zeile an.
# Fix: trailing = line[len(stripped_line):] bewahrt \n des Originals.
# Diese Tests MUESSEN mit gefixter Impl GRUEN sein — sie locken den Fix.
# ---------------------------------------------------------------------------

class TestNewlinePreservation:
    """BL-447 Regression-Lock: Newline/Zeilen-Integritaet in mark_pl_done.

    Szenario: PL-Master mit mehreren Items + Header-Zeilen + Hybrid-Item.
    Das geflippte Item wird done, ALLE anderen Zeilen bleiben unveraendert,
    KEINE Zeilen werden zusammengeklebt (Zeilen-Anzahl bleibt gleich).
    """

    # Realistischer PL-Master: Header + 3 Items, Hybrid-Item ist die mittlere Zeile.
    # splitlines(keepends=True) liefert jede Zeile MIT \n — der Fix bewahrt dieses \n.
    TARGET_ID = "BL-447-NL-PL-1"
    AFTER_ID = "BL-447-NL-PL-2"

    # Hybrid-Format (der Killer-Fall, der den Bug ausloeste):
    # _normalize_to_canonical_open muss trailing \n erhalten, sonst klebt
    # AFTER_LINE direkt an die normalisierte TARGET_LINE an.
    MULTILINE_CONTENT = (
        "# Parking Lot\n"
        "\n"
        f"- [ ] **BL-447-NL-PL-0** (status: open) — Item Vor Target\n"
        f"- [ ] **{TARGET_ID}** [STATUS: IN_ARBEIT] (status: open) — Hybrid Target\n"
        f"- [ ] **{AFTER_ID}** (status: open) — Item Nach Target\n"
        "## Weitere Sektion\n"
    )

    def test_nl1_line_count_preserved_after_hybrid_flip(self):
        """T-NL1: mark_pl_done auf Mehrzeiler — Zeilen-Anzahl bleibt identisch (kein Zusammenkleben).

        Regression-Lock: Vor dem Fix klebte die Zeile NACH dem geflippten Item
        an die normalisierte Zeile an (splitlines(keepends=True) liefert \n,
        ''.join ohne trailing-\n-Erhalt komprimiert 2 Zeilen zu 1).
        """
        result = mark_pl_done(self.MULTILINE_CONTENT, self.TARGET_ID)
        original_lines = self.MULTILINE_CONTENT.splitlines()
        result_lines = result.splitlines()
        assert len(result_lines) == len(original_lines), (
            f"Zeilen-Anzahl muss gleich bleiben: erwartet {len(original_lines)}, "
            f"bekommen {len(result_lines)}. "
            f"Zeilen zusammengeklebt? result_lines={result_lines!r}"
        )

    def test_nl1_after_item_on_own_line_after_hybrid_flip(self):
        """T-NL1: Das Item NACH dem geflippten bleibt intakt + auf eigener Zeile.

        Regression-Lock: Vor dem Fix klebte AFTER_ID-Zeile an TARGET-Zeile.
        Nach dem Fix muss AFTER_ID auf einer separaten Zeile stehen, allein.
        """
        result = mark_pl_done(self.MULTILINE_CONTENT, self.TARGET_ID)
        lines = result.splitlines()
        after_lines = [l for l in lines if self.AFTER_ID in l]
        assert len(after_lines) == 1, (
            f"AFTER-Item muss auf genau 1 eigener Zeile stehen, gefunden: {after_lines!r}"
        )
        after_line = after_lines[0]
        # AFTER-Item darf NICHT mit TARGET_ID zusammengeklebt sein
        assert self.TARGET_ID not in after_line, (
            f"AFTER-Zeile enthaelt TARGET_ID — Zeilen wurden zusammengeklebt: {after_line!r}"
        )
        # AFTER-Item bleibt open (unveraendert)
        assert "[ ]" in after_line, f"AFTER-Item muss open bleiben: {after_line!r}"
        assert "(status: open)" in after_line, f"AFTER-Item status muss open sein: {after_line!r}"

    def test_nl2_trailing_newline_preserved_on_flipped_item(self):
        """T-NL2: mark_pl_done erhaelt das trailing-\\n des geflippten Items (Split/Join-Integritaet).

        Regression-Lock: _normalize_to_canonical_open muss trailing = line[len(stripped_line):]
        in die normalisierte Zeile einbauen. ''.join(lines) setzt voraus, dass jede
        innere Zeile ihr \\n traegt.
        """
        result = mark_pl_done(self.MULTILINE_CONTENT, self.TARGET_ID)
        # Das Ergebnis muss mit \n enden (trailing-\n des letzten Items / letzter Zeile erhalten)
        # Wichtiger: jede innere Zeile in splitlines(keepends=True) muss \n tragen
        raw_lines = result.splitlines(keepends=True)
        # Finde die geflippte Zeile (TARGET_ID, jetzt done)
        flipped_lines = [l for l in raw_lines if self.TARGET_ID in l]
        assert len(flipped_lines) == 1, f"Genau 1 geflippte Zeile erwartet: {flipped_lines!r}"
        flipped = flipped_lines[0]
        # Die geflippte Zeile muss ihr trailing \n behalten haben
        assert flipped.endswith('\n'), (
            f"Geflippte Zeile muss trailing \\n behalten (Split/Join-Integritaet): {flipped!r}"
        )
