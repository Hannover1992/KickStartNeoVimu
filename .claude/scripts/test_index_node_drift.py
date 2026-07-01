"""
BL-348 RED Tests — index_node_drift.py (Header-Aware Index/Node Drift Scanner)

RED-Worker: NUR Failing Tests. KEIN Production-Code. KEIN git-commit.
Modul .claude/scripts/index_node_drift.py existiert NOCH NICHT → alle Imports failen.

Contract fuer GREEN-Worker:
  parse_index_rows(index_text: str) -> dict[str, dict]
    - Header-aware: findet Header-Zeile, mappt Spalten-Namen -> Index
    - Extrahiert pro BL-Zeile die STATUS-Spalte NICHT positional
    - "hoch"/"medium" in Prioritaets-Spalte darf NICHT als Status erkannt werden

  classify_drift(bl_id: str, index_status: str, node_status: str | None) -> str | None
    - kind in {"stale_index", "over_optimistic_index", "node_defect", "cosmetic", None}
    - stale_index: node=DONE aber index != DONE (case-insensitive)
    - over_optimistic_index: index=DONE aber node in {DRAFT, READY, HOLD, ...} != done
    - node_defect: node_status in {None, "NO_STATUS", "NULL_BYTES"}
    - cosmetic: DEPRECATED <-> {DECOMPOSED, ABSORBED}
    - None: in-sync (beide gleich / beide done-aequivalent)

  scan_drift(vault_root: str,
             read_index_fn=None,
             read_done_fn=None,
             read_node_fn=None) -> list[dict]
    - liest _backlog_index.md + _backlog_index_done.md + Node-Frontmatter
    - DI-bar: read_index_fn/read_done_fn/read_node_fn injizierbar fuer Tests
    - Ergebnis: list[{bl_id, index_status, node_status, kind}]
"""
import textwrap

import pytest


# ---------------------------------------------------------------------------
# T1: parse_index_rows -- Header-Aware, Anti-False-Positive auf Prio-Spalte
# ---------------------------------------------------------------------------
def test_parse_index_rows_header_aware_no_prio_false_positive():
    """T1: KERN-Anti-False-Positive.

    Tabelle mit Header-Reihenfolge BL | Title | Status | Path | ... | Prio | Reifegrad.
    Eine BL-Zeile hat status=DONE und prio=hoch.
    parse_index_rows muss status=="DONE" liefern, NICHT "hoch".
    """
    from index_node_drift import parse_index_rows  # noqa: F401 -- RED: ImportError erwartet

    index_text = textwrap.dedent("""\
        # Backlog Index

        | BL | Title | Status | Path | Prio | Reifegrad |
        |---|---|---|---|---|---|
        | BL-001 | Test Feature | DONE | Backlog/BL-001 | hoch | REIF |
        | BL-002 | Other Feature | SC-REIF | Backlog/BL-002 | medium | DRAFT |
    """)

    result = parse_index_rows(index_text)

    assert "BL-001" in result, "BL-001 muss in result sein"
    assert result["BL-001"]["status"] == "DONE", (
        f"Status muss 'DONE' sein, nicht '{result['BL-001']['status']}' "
        "(Anti-False-Positive: 'hoch' aus Prio-Spalte darf nicht als Status erkannt werden)"
    )
    assert result["BL-002"]["status"] == "SC-REIF", (
        "BL-002 Status muss 'SC-REIF' sein"
    )


# ---------------------------------------------------------------------------
# T2: classify_drift -- over_optimistic_index
# ---------------------------------------------------------------------------
def test_classify_drift_over_optimistic_index():
    """T2: index=DONE aber node=DRAFT -> 'over_optimistic_index' (GEFAEHRLICH)."""
    from index_node_drift import classify_drift  # noqa: F401 -- RED: ImportError erwartet

    result = classify_drift("BL-001", index_status="DONE", node_status="DRAFT")

    assert result == "over_optimistic_index", (
        f"Erwartet 'over_optimistic_index', bekommen: {result!r}"
    )


# ---------------------------------------------------------------------------
# T3: classify_drift -- stale_index
# ---------------------------------------------------------------------------
def test_classify_drift_stale_index():
    """T3: index=SC-REIF aber node=DONE -> 'stale_index'."""
    from index_node_drift import classify_drift  # noqa: F401 -- RED: ImportError erwartet

    result = classify_drift("BL-002", index_status="SC-REIF", node_status="DONE")

    assert result == "stale_index", (
        f"Erwartet 'stale_index', bekommen: {result!r}"
    )


# ---------------------------------------------------------------------------
# T4: classify_drift -- node_defect (None und NO_STATUS)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("node_status", [None, "NO_STATUS", "NULL_BYTES"])
def test_classify_drift_node_defect(node_status):
    """T4: node_status in {None, 'NO_STATUS', 'NULL_BYTES'} -> 'node_defect'."""
    from index_node_drift import classify_drift  # noqa: F401 -- RED: ImportError erwartet

    result = classify_drift("BL-003", index_status="DRAFT", node_status=node_status)

    assert result == "node_defect", (
        f"node_status={node_status!r} muss 'node_defect' liefern, bekommen: {result!r}"
    )


# ---------------------------------------------------------------------------
# T5: classify_drift -- in-sync (beide DONE)
# ---------------------------------------------------------------------------
def test_classify_drift_in_sync_both_done():
    """T5: index=DONE und node=DONE -> None (in-sync, kein Drift)."""
    from index_node_drift import classify_drift  # noqa: F401 -- RED: ImportError erwartet

    result = classify_drift("BL-004", index_status="DONE", node_status="DONE")

    assert result is None, (
        f"In-sync muss None liefern, bekommen: {result!r}"
    )


# ---------------------------------------------------------------------------
# T6: scan_drift -- end-to-end via DI-Fixtures
# ---------------------------------------------------------------------------
def test_scan_drift_end_to_end_one_over_optimistic_no_prio_false_positive(tmp_path):
    """T6: End-to-End scan_drift gegen tmp-fixture-vault.

    1 over-optimistic BL (index=DONE, node=DRAFT) + 1 in-sync BL (beide DONE).
    Erwartung: genau 1 Drift (over_optimistic_index), 0 False-Positives auf Prio-Spalte.
    DI: read_index_fn/read_done_fn/read_node_fn injiziert, kein echter Vault-Read.
    """
    from index_node_drift import scan_drift  # noqa: F401 -- RED: ImportError erwartet

    # Mini-Index: BL-010 = DONE (over-optimistic), BL-020 = DONE (in-sync)
    # Header: BL | Title | Prio | Status | Path  (Prio VOR Status — haertester Test)
    index_text = textwrap.dedent("""\
        | BL | Title | Prio | Status | Path |
        |---|---|---|---|---|
        | BL-010 | Over-Optimistic | hoch | DONE | Backlog/BL-010 |
        | BL-020 | In-Sync | medium | DONE | Backlog/BL-020 |
    """)

    # Node-Status: BL-010 = DRAFT (over-optimistic), BL-020 = DONE (in-sync)
    node_statuses = {
        "BL-010": "DRAFT",
        "BL-020": "DONE",
    }

    def read_index_fn():
        return index_text

    def read_done_fn():
        # Keine DONE-Index-Eintraege in separater done-Datei
        return ""

    def read_node_fn(bl_id):
        return node_statuses.get(bl_id)

    results = scan_drift(
        vault_root=str(tmp_path),
        read_index_fn=read_index_fn,
        read_done_fn=read_done_fn,
        read_node_fn=read_node_fn,
    )

    drift_kinds = [r["kind"] for r in results]

    assert len(results) == 1, (
        f"Genau 1 Drift erwartet (over_optimistic BL-010), "
        f"bekommen: {len(results)} — {results}"
    )
    assert drift_kinds == ["over_optimistic_index"], (
        f"Erwartet ['over_optimistic_index'], bekommen: {drift_kinds}"
    )
    assert results[0]["bl_id"] == "BL-010", (
        f"Drift muss BL-010 sein, bekommen: {results[0]['bl_id']}"
    )
    # Explizit: kein False-Positive auf "hoch"/"medium" aus Prio-Spalte
    for r in results:
        assert r["kind"] != "node_defect" or r.get("node_status") not in ("hoch", "medium"), (
            "False-Positive: 'hoch'/'medium' aus Prio-Spalte als node_status erkannt"
        )


# ---------------------------------------------------------------------------
# T7: parse_index_rows -- ECHTES Header-Format ("BL-ID" statt "BL")
# ---------------------------------------------------------------------------
def test_parse_index_rows_real_header_format():
    """T7: Echter _backlog_index.md Header hat Spalte 'BL-ID', nicht 'BL'.

    Der ECHTE Header lautet:
      | BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad |
      |-------|-------|--------|------------|---------|-----------|

    parse_index_rows sucht bisher nach 'BL' in cells_upper.
    'BL-ID'.upper() == 'BL-ID' != 'BL' -> header_idx bleibt None -> gibt {} zurueck.
    Dieser Test failt JETZT (RED) weil parse_index_rows den Header nicht erkennt.

    GREEN-Erwartung: parse_index_rows muss 'BL-ID' als BL-Spalte akzeptieren
    (neben 'BL' fuer Rueckwaerts-Kompatibilitaet) und die Daten-Zeilen korrekt lesen.
    """
    from index_node_drift import parse_index_rows

    index_text = textwrap.dedent("""\
        ---
        format_version: 1
        backlog_counter: 10
        ---

        # Backlog Index

        | BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad |
        |-------|-------|--------|------------|---------|-----------|
        | BL-001 | Wahrheiten_Taxonomie | DONE | Backlog\\BL-001-wahrheiten-taxonomie.md | 2026-04-02 |  |
        | BL-002 | Backlog_Reifegradrouting | DRAFT | Backlog\\BL-002-backlog-reifegradrouting.md | 2026-04-02 | REIF |
        | BL-003 | ObsidianFirst_FireTogether | SC-REIF | Backlog\\BL-003-obsidianfirst-firetogether.md | 2026-04-02 | SC-REIF |
    """)

    result = parse_index_rows(index_text)

    assert len(result) > 0, (
        f"parse_index_rows muss Zeilen finden bei Header 'BL-ID' — "
        f"aktuell liefert es 0 Zeilen (Header-Match fehlt fuer 'BL-ID')"
    )
    assert "BL-001" in result, "BL-001 muss in result sein"
    assert result["BL-001"]["status"] == "DONE", (
        f"BL-001 Status muss 'DONE' sein, bekommen: {result.get('BL-001', {}).get('status')!r}"
    )
    assert "BL-002" in result, "BL-002 muss in result sein"
    assert result["BL-002"]["status"] == "DRAFT", (
        f"BL-002 Status muss 'DRAFT' sein, bekommen: {result.get('BL-002', {}).get('status')!r}"
    )
    assert "BL-003" in result, "BL-003 muss in result sein"
    assert result["BL-003"]["status"] == "SC-REIF", (
        f"BL-003 Status muss 'SC-REIF' sein, bekommen: {result.get('BL-003', {}).get('status')!r}"
    )


# ---------------------------------------------------------------------------
# T8: parse_index_rows -- Smoke-Test gegen echte _backlog_index.md
# ---------------------------------------------------------------------------
REAL_BACKLOG_INDEX = (
    r"C:\Users\hanno\Documents\Work\Wissen\Berechtigung"
    r"\OmniCommand\OmniCommand\_backlog_index.md"
)


@pytest.mark.skipif(
    not __import__("os").path.isfile(REAL_BACKLOG_INDEX),
    reason="Echte _backlog_index.md nicht gefunden — Smoke-Test uebersprungen",
)
def test_parse_index_rows_real_file_smoke():
    """T8: Smoke-Test gegen die echte _backlog_index.md.

    Erwartet: parse_index_rows liefert >50 Zeilen (der echte Index hat 400+).
    Failt JETZT weil parse_index_rows 'BL-ID' nicht als Header-Spalte erkennt -> 0 Zeilen.
    """
    from index_node_drift import parse_index_rows
    import os

    with open(REAL_BACKLOG_INDEX, encoding="utf-8") as f:
        real_text = f.read()

    result = parse_index_rows(real_text)

    assert len(result) > 50, (
        f"Echte _backlog_index.md muss >50 Zeilen liefern, bekommen: {len(result)} "
        f"(Header 'BL-ID' wird von parse_index_rows nicht erkannt)"
    )


# ---------------------------------------------------------------------------
# T_DRN1: _default_read_node -- tmp-fixture mit YAML-Frontmatter status: DONE
# ---------------------------------------------------------------------------
def test_DRN1_default_read_node_flat_file_with_status(tmp_path):
    """T_DRN1: _default_read_node liest Status aus FLAT .md-Datei in Backlog/.

    Fixture: {tmp_vault}/Backlog/BL-999-foo.md mit YAML-Frontmatter status: DONE.
    Erwartung: _default_read_node(tmp_vault, 'BL-999') == 'DONE'.

    Failt JETZT (RED): _default_read_node prueft nur entry.is_dir() —
    flache .md-Dateien werden nie gelesen -> liefert None statt 'DONE'.
    """
    from index_node_drift import _default_read_node

    backlog_dir = tmp_path / "Backlog"
    backlog_dir.mkdir()
    node_file = backlog_dir / "BL-999-foo.md"
    node_file.write_text(
        "---\nid: BL-999\nstatus: DONE\n---\n\n# Foo\n",
        encoding="utf-8",
    )

    result = _default_read_node(str(tmp_path), "BL-999")

    assert result == "DONE", (
        f"Erwartet 'DONE', bekommen: {result!r}. "
        "Bug: _default_read_node iteriert nur Verzeichnisse (entry.is_dir()), "
        "liest aber keine flachen .md-Dateien direkt in Backlog/."
    )


# ---------------------------------------------------------------------------
# T_DRN2: _default_read_node -- Defekt-Signale (kein status / NULL_BYTES)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("content,expected_set", [
    # Datei ohne status:-Zeile -> muss None oder "NO_STATUS" liefern, kein Crash
    ("---\nid: BL-998\ntitle: No Status Here\n---\n", {None, "NO_STATUS"}),
    # NULL_BYTES in Datei -> muss None oder "NO_STATUS" oder "READ_ERR" liefern, kein Crash
    ("---\nid: BL-997\n\x00\x00\x00\n---\n", {None, "NO_STATUS", "READ_ERR", "NULL_BYTES"}),
])
def test_DRN2_default_read_node_defect_signals(tmp_path, content, expected_set):
    """T_DRN2: _default_read_node liefert definiertes Defekt-Signal bei defekten Nodes.

    Bei .md-Datei ohne status: muss None oder 'NO_STATUS' kommen (kein Crash).
    Bei NULL_BYTES muss ein definiertes Signal kommen (kein unbehandelter UnicodeDecodeError).

    Failt JETZT (RED) fuer den NULL_BYTES-Fall: _default_read_node oeffnet mit
    encoding='utf-8' ohne errors='replace' -> UnicodeDecodeError statt Signal.
    (Der no-status Fall failt ebenfalls wegen is_dir()-Bug aus T_DRN1.)
    """
    from index_node_drift import _default_read_node

    backlog_dir = tmp_path / "Backlog"
    backlog_dir.mkdir()
    bl_id = "BL-998" if "\x00" not in content else "BL-997"
    node_file = backlog_dir / f"{bl_id}-defekt.md"
    node_file.write_bytes(content.encode("utf-8", errors="replace"))

    try:
        result = _default_read_node(str(tmp_path), bl_id)
    except Exception as exc:
        pytest.fail(
            f"_default_read_node darf nicht crashen bei defekter Datei, "
            f"bekommen: {type(exc).__name__}: {exc}"
        )

    assert result in expected_set, (
        f"Erwartet eines aus {expected_set!r}, bekommen: {result!r}"
    )


# ---------------------------------------------------------------------------
# T_DRN3: _default_read_node -- Real-Smoke gegen echten Vault (BL-001 = DONE)
# ---------------------------------------------------------------------------
REAL_VAULT = (
    r"C:\Users\hanno\Documents\Work\Wissen\Berechtigung"
    r"\OmniCommand\OmniCommand"
)

import os as _os

@pytest.mark.skipif(
    not _os.path.isdir(_os.path.join(REAL_VAULT, "Backlog")),
    reason="Echter Vault nicht gefunden — Real-Smoke uebersprungen",
)
def test_DRN3_default_read_node_real_vault_bl001():
    """T_DRN3: Real-Smoke — _default_read_node(REAL_VAULT, 'BL-001') == 'DONE'.

    BL-001-wahrheiten-taxonomie.md existiert, hat status: DONE, 0 NULL_BYTES.
    Failt JETZT (RED): _default_read_node liefert None wegen is_dir()-Bug
    (liest nur Verzeichnisse, aber BL-001 ist eine flache .md-Datei).
    """
    from index_node_drift import _default_read_node

    result = _default_read_node(REAL_VAULT, "BL-001")

    assert result == "DONE", (
        f"_default_read_node(REAL_VAULT, 'BL-001') muss 'DONE' liefern, "
        f"bekommen: {result!r}. "
        "Root-Cause: entry.is_dir() filtert flache .md-Dateien heraus."
    )


# ---------------------------------------------------------------------------
# T_BODY1: _default_read_node -- NO_FRONTMATTER-Node mit body-status (dir+flat)
# ---------------------------------------------------------------------------
def test_BODY1_default_read_node_no_frontmatter_body_status(tmp_path):
    """T_BODY1: Node OHNE ---Frontmatter-Block, aber Body enthaelt 'status: DONE'.

    Fixture spiegelt das echte BL-179-Muster: BEIDE Formen existieren gleichzeitig --
      - Verzeichnis BL-998-foo/  mit _manifest.md (kein status:-Feld direkt)
      - Flache Datei BL-998-foo.md mit body-status (kein --- Frontmatter-Block)

    Wenn scandir das Verzeichnis zuerst findet und daraus NO_STATUS/kein-status
    zurueckgibt, muss _default_read_node trotzdem den echten Status aus der flachen
    .md-Datei lesen ('DONE') und diesen zurueckliefern.

    RED: Aktuell liefert _default_read_node 'NO_STATUS' weil das Verzeichnis-Ergebnis
    die Suche abbricht bevor die flache Datei (mit body-status) geprueft wird.

    GREEN-Contract: _default_read_node gibt 'DONE' zurueck (body-status aus flacher
    Datei, auch wenn kein ---Frontmatter-Block vorhanden).
    """
    from index_node_drift import _default_read_node

    backlog_dir = tmp_path / "Backlog"
    backlog_dir.mkdir()

    # Verzeichnis-Eintrag (simuliert BL-998-foo/ Unterordner)
    bl_dir = backlog_dir / "BL-998-foo"
    bl_dir.mkdir()
    manifest = bl_dir / "_manifest.md"
    manifest.write_text(
        "---\ntype: bl-manifest\nbl_id: BL-998\n---\n\n# BL-998 Manifest\n",
        encoding="utf-8",
    )

    # Flache .md-Datei OHNE ---Frontmatter-Block, aber mit body-status
    flat_file = backlog_dir / "BL-998-foo.md"
    flat_file.write_text(
        "# BL-998 Titel\n\n## Status\n\nstatus: DONE\n\nBeschreibung folgt.\n",
        encoding="utf-8",
    )

    result = _default_read_node(str(tmp_path), "BL-998")

    assert result == "DONE", (
        f"Erwartet 'DONE' (body-status aus flacher .md-Datei), bekommen: {result!r}. "
        "Bug: scandir-Ergebnis des Verzeichnisses (NO_STATUS/_manifest.md) bricht die "
        "Suche ab, bevor die flache .md-Datei mit body-status geprueft wird."
    )


# ---------------------------------------------------------------------------
# T_BODY2: _default_read_node -- Frontmatter-Pfad bleibt (Regression)
# ---------------------------------------------------------------------------
def test_BODY2_default_read_node_frontmatter_regression(tmp_path):
    """T_BODY2: Node MIT ---Frontmatter-Block und status: DRAFT.

    Regression-Test: Der Frontmatter-Pfad muss weiterhin funktionieren
    nachdem body-status unterstuetzt wird.

    GREEN: Erwartet 'DRAFT' (aus Frontmatter). Sollte JETZT schon GRUEN sein
    (Frontmatter-Pfad war nie kaputt). Bestaetigt Nicht-Regression.
    """
    from index_node_drift import _default_read_node

    backlog_dir = tmp_path / "Backlog"
    backlog_dir.mkdir()
    node_file = backlog_dir / "BL-997-bar.md"
    node_file.write_text(
        "---\nid: BL-997\nstatus: DRAFT\ntitle: Bar\n---\n\n# Bar\n",
        encoding="utf-8",
    )

    result = _default_read_node(str(tmp_path), "BL-997")

    assert result == "DRAFT", (
        f"Regression: Frontmatter-Pfad muss 'DRAFT' liefern, bekommen: {result!r}."
    )


# ---------------------------------------------------------------------------
# T_BODY3: _default_read_node -- Real-Smoke BL-179 (NO_FRONTMATTER-Pillar-Node)
# ---------------------------------------------------------------------------
REAL_VAULT_BODY = (
    r"C:\Users\hanno\Documents\Work\Wissen\Berechtigung"
    r"\OmniCommand\OmniCommand"
)

import os as _os_body

@pytest.mark.skipif(
    not _os_body.path.isdir(_os_body.path.join(REAL_VAULT_BODY, "Backlog")),
    reason="Echter Vault nicht gefunden — T_BODY3 Real-Smoke uebersprungen",
)
def test_BODY3_default_read_node_real_vault_bl179_body_status():
    """T_BODY3: Real-Smoke -- _default_read_node(REAL_VAULT, 'BL-179') liefert 'DONE'.

    BL-179 ist ein Pillar-Node: Die flache Datei BL-179-pillar-01-pipeline-topologie.md
    hat YAML-Frontmatter mit status: DONE. ABER das gleichnamige Verzeichnis
    BL-179-pillar-01-pipeline-topologie/ wird von scandir zuerst gefunden und liefert
    'NO_STATUS' (aus _manifest.md, das kein direktes status:-Feld hat).

    Aktuelles Verhalten (RED): _default_read_node gibt 'NO_STATUS' zurueck weil
    der Verzeichnis-Scan die Suche abbricht.

    Erwartetes Verhalten (GREEN): 'DONE' -- der tatsaechliche Status aus der
    flachen .md-Datei (Frontmatter ODER body-status soll beide zaehlen).
    """
    from index_node_drift import _default_read_node

    result = _default_read_node(REAL_VAULT_BODY, "BL-179")

    assert result == "DONE", (
        f"_default_read_node(REAL_VAULT, 'BL-179') muss 'DONE' liefern, "
        f"bekommen: {result!r}. "
        "Root-Cause: Verzeichnis BL-179-pillar-01-pipeline-topologie/ wird zuerst "
        "gescannt und liefert NO_STATUS (_manifest.md hat kein status:-Feld direkt), "
        "obwohl die flache Datei BL-179-pillar-01-pipeline-topologie.md "
        "status: DONE im Frontmatter traegt."
    )


# ---------------------------------------------------------------------------
# T_BODY4: _default_read_node -- echter Defekt: kein status: irgendwo -> NO_STATUS
# ---------------------------------------------------------------------------
def test_BODY4_default_read_node_no_status_anywhere_remains_defect(tmp_path):
    """T_BODY4: Node ohne JEDES 'status:'-Vorkommen -> None oder 'NO_STATUS' (Defekt).

    Sichert: body-status-Unterstuetzung hebt ECHTE statuslose Nodes nicht faelschlich
    zu einem gueltigen Status. Kein status: in Frontmatter UND kein status: im Body
    muss ein Defekt-Signal bleiben.

    GREEN: Erwartet None oder 'NO_STATUS'. Sollte JETZT schon GRUEN sein.
    Sicherheitsnetz gegen Ueberanpassung im GREEN-Schritt.
    """
    from index_node_drift import _default_read_node

    backlog_dir = tmp_path / "Backlog"
    backlog_dir.mkdir()
    node_file = backlog_dir / "BL-996-kein-status.md"
    node_file.write_text(
        "# BL-996\n\nKeine Status-Zeile vorhanden.\n\n## Beschreibung\n\nText.\n",
        encoding="utf-8",
    )

    result = _default_read_node(str(tmp_path), "BL-996")

    assert result in (None, "NO_STATUS"), (
        f"Erwartet None oder 'NO_STATUS' fuer statuslose Node, bekommen: {result!r}. "
        "Echter Defekt muss Defekt-Signal bleiben (body-status-Fix darf nicht "
        "statuslose Nodes faelschlich als gueltig markieren)."
    )


# ---------------------------------------------------------------------------
# T_MAIN1: main() smoke-test via subprocess on tmp-fixture-vault
# ---------------------------------------------------------------------------
def test_MAIN1_main_cli_smoke_exit_code_and_report(tmp_path):
    """T_MAIN1: Smoke-test for main() CLI entry-point.

    Builds a minimal fixture vault with:
      - _backlog_index.md: BL-900 (index=DONE), BL-901 (index=DRAFT)
      - _backlog_index_done.md: empty
      - Backlog/BL-900-test.md: status=DRAFT  (over_optimistic_index)
      - Backlog/BL-901-test.md: status=DONE   (stale_index)

    Expectations:
      - exit_code == 1 (2 drifts found)
      - stdout contains 'BL-900' (over_optimistic_index drift)
    """
    import subprocess

    # Build fixture vault
    index_text = (
        "| BL-ID | Title | Status |\n"
        "|-------|-------|--------|\n"
        "| BL-900 | Over-Optimistic | DONE |\n"
        "| BL-901 | Stale | DRAFT |\n"
    )
    (tmp_path / "_backlog_index.md").write_text(index_text, encoding="utf-8")
    (tmp_path / "_backlog_index_done.md").write_text("", encoding="utf-8")

    backlog = tmp_path / "Backlog"
    backlog.mkdir()
    (backlog / "BL-900-test.md").write_text(
        "---\nstatus: DRAFT\n---\n", encoding="utf-8"
    )
    (backlog / "BL-901-test.md").write_text(
        "---\nstatus: DONE\n---\n", encoding="utf-8"
    )

    script = (
        r"C:\Users\hanno\RiderProjects\OmniCommand-wtA"
        r"\.claude\scripts\index_node_drift.py"
    )

    proc = subprocess.run(
        ["py", "-3", script, str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 1, (
        f"Expected exit_code=1 (drifts present), got {proc.returncode}.\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "BL-900" in proc.stdout, (
        f"Expected 'BL-900' in stdout report.\nstdout: {proc.stdout}"
    )


# ---------------------------------------------------------------------------
# T_NORM1..T_NORM5: Status-Normalisierung — Parenthetik-Strip + case-fold
# BL Layer-4 Bug: "DONE (done)" != "DONE" -> false stale_index
# Contract fuer GREEN: normalize_status(s) = first_token(s).strip().upper()
# ---------------------------------------------------------------------------

def test_NORM1_classify_drift_index_annotation_in_sync():
    """T_NORM1: KERN — index='DONE (done)', node='DONE' -> None (in-sync, NICHT stale_index).

    Aktueller Bug: idx = 'DONE (done)'.upper() = 'DONE (DONE)' != 'DONE'
    -> Zweig 3 (stale_index) schlaegt an: node==DONE und idx!='DONE' -> 'stale_index'.
    GREEN-Fix: Parenthetik strippen -> idx = 'DONE', dann idx==node -> None.
    """
    from index_node_drift import classify_drift

    result = classify_drift("BL-x", "DONE (done)", "DONE")

    assert result is None, (
        f"'DONE (done)' vs 'DONE' muss None (in-sync) liefern, bekommen: {result!r}. "
        "Bug: Parenthetik-Annotation wird nicht gestrippt -> faelschlich stale_index."
    )


def test_NORM2_classify_drift_node_annotation_in_sync():
    """T_NORM2: node='DONE (done)', index='DONE' -> None (umgekehrt, node-Annotation).

    Wenn der Node 'DONE (done)' traegt und der Index 'DONE' ist, muss ebenfalls
    None (in-sync) kommen — nicht over_optimistic_index.
    GREEN-Fix: node-Normalisierung muss genauso greifen wie index-Normalisierung.
    """
    from index_node_drift import classify_drift

    result = classify_drift("BL-x", "DONE", "DONE (done)")

    assert result is None, (
        f"'DONE' vs node='DONE (done)' muss None (in-sync) liefern, bekommen: {result!r}. "
        "Bug: node-Parenthetik wird nicht gestrippt -> faelschlich over_optimistic_index."
    )


def test_NORM3_classify_drift_real_drift_not_swallowed():
    """T_NORM3: Echte Drift bleibt — index='DONE', node='DRAFT' -> 'over_optimistic_index'.

    Normalisierung darf echte Drifts NICHT verschlucken.
    Dieser Test sollte bereits GRUEN sein (kein Annotations-Problem hier).
    Sicherheitsnetz gegen Ueberanpassung im GREEN-Schritt.
    """
    from index_node_drift import classify_drift

    result = classify_drift("BL-x", "DONE", "DRAFT")

    assert result == "over_optimistic_index", (
        f"Echte Drift muss 'over_optimistic_index' liefern, bekommen: {result!r}."
    )


def test_NORM4_classify_drift_lowercase_in_sync():
    """T_NORM4: case-fold — index='done' (lowercase), node='DONE' -> None.

    Die echte Index-Spalte kann lowercase 'done' tragen.
    .upper() ist bereits implementiert, aber Parenthetik-Annotation ist der Blocker.
    Mit reinem 'done' sollte das bereits funktionieren — hier als Regression-Anker.
    Wenn dieser Test GRUEN ist: case-fold ok, Parenthetik-Strip ist der alleinige Bug.
    """
    from index_node_drift import classify_drift

    result = classify_drift("BL-x", "done", "DONE")

    assert result is None, (
        f"'done' vs 'DONE' muss None (in-sync) liefern, bekommen: {result!r}. "
        "case-fold (.upper()) sollte bereits greifen — Regression-Anker."
    )


REAL_VAULT_NORM = (
    r"C:\Users\hanno\Documents\Work\Wissen\Berechtigung"
    r"\OmniCommand\OmniCommand"
)

import os as _os_norm

@pytest.mark.skipif(
    not _os_norm.path.isdir(_os_norm.path.join(REAL_VAULT_NORM, "Backlog")),
    reason="Echter Vault nicht gefunden — T_NORM5 Real-Smoke uebersprungen",
)
def test_NORM5_scan_drift_real_vault_stale_index_count_drops():
    """T_NORM5: Real-Scan-Smoke — stale_index-Count sinkt deutlich (<5) nach Fix.

    Vor dem Fix: ~20 von 22 stale_index sind 'DONE (done)' False-Positives.
    Nach dem Fix: nur echte stale_index bleiben (<5 erwartet).
    Zusaetzlich: kein einziger Eintrag mit index_status='DONE (done)' darf
    als stale_index klassifiziert sein.

    RED: Aktuell >= 5 stale_index (die 20 'DONE (done)'-FPs schlagen durch).
    GREEN: < 5 stale_index, 0 'DONE (done)'-False-Positives.
    """
    from index_node_drift import scan_drift

    drifts = scan_drift(REAL_VAULT_NORM)

    stale = [d for d in drifts if d["kind"] == "stale_index"]
    done_annotation_false_positives = [
        d for d in stale
        if "(" in d.get("index_status", "")
    ]

    assert len(done_annotation_false_positives) == 0, (
        f"0 'DONE (done)'-False-Positives erwartet, bekommen: {len(done_annotation_false_positives)}. "
        f"Betroffene: {[d['bl_id'] for d in done_annotation_false_positives]}"
    )
    assert len(stale) < 5, (
        f"Nach Fix: < 5 echte stale_index erwartet, bekommen: {len(stale)}. "
        f"Wenn > 5: entweder Fix fehlt oder echte Drifts vorhanden. "
        f"stale BLs: {[d['bl_id'] for d in stale]}"
    )
