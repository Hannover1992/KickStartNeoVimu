"""
bl_index_updater.py — BL-428 batch_1

Hilfsfunktionen fuer das programmatische Aktualisieren von _backlog_index.md Zeilen.
AK-1: index_row_has_done (Read-Back-Helper)
AK-2: line-anchored Regex verhindert BL-364/BL-3640-Kollision
AK-3: end_art-Parameter mit ENUM-Validierung + Fallback
AK-5: Idempotenz — doppelter Aufruf liefert identisches Ergebnis
BL-434: pipe-aware — Titel mit Pipe-Zeichen korrekt behandelt (Anker auf Vault-Pfad-Spalte)
"""

END_ART_ENUM = ["done", "deferred", "PO-question", "rolled-up"]


def _locate_row_cells(content: str, item_id: str):
    """
    Findet die Zeile in content, deren erste Datenspalte (cells[1]) exakt item_id ist.

    Verwendet split('|') statt [^|]*-Regex damit Pipe-Zeichen im Titel den Spalten-
    versatz nicht verursachen. cells[0]=='' (vor fuehrendem |), cells[1]==' BL-ID ',
    cells[-1]=='' (nach abschliessendem |).

    Gibt (line_index, cells, lines) zurueck oder (None, None, lines) wenn nicht gefunden.
    BL-364/BL-3640-Kollisionssicherheit: exakter strip-Vergleich auf cells[1].
    """
    lines = content.splitlines(keepends=True)
    for idx, line in enumerate(lines):
        cells = line.split('|')
        # cells[0]='' cells[1]=' BL-ID ' cells[2]=' Title ' ... cells[-1]='\n' or ''
        if len(cells) >= 2 and cells[1].strip() == item_id:
            return idx, cells, lines
    return None, None, lines


def _status_index(cells: list):
    """
    Ermittelt den Zell-Index der Status-Spalte.

    Strategie: Vault-Pfad-Spalte = erster Index i>=2 mit 'Backlog/' ODER 'Backlog\\'
    in cells[i] (separator-agnostisch — aeltere BLs nutzen Backslash-Pfade ohne .md).
    WICHTIG: NUR mit Separator anchorn (nicht nur "Backlog") — der Titel kann das
    Wort "Backlog" ohne Separator enthalten (BL-434 Anti-False-Positive).
    Fallback: '.md' in der Zelle (forward-slash-Pfad mit Extension).
    Status-Spalte = path_index - 1.

    Gibt den Index zurueck oder None wenn keine Vault-Pfad-Spalte gefunden (malformed).
    """
    # Primaer: 'Backlog/' oder 'Backlog\' als separator-agnostischer Anker
    for i in range(2, len(cells)):
        cc = cells[i]
        if 'Backlog/' in cc or 'Backlog\\' in cc:
            return i - 1
    # Fallback: '.md' in der Zelle (forward-slash-Pfade mit Extension)
    for i in range(2, len(cells)):
        if '.md' in cells[i] and '/' in cells[i]:
            return i - 1
    return None


def update_index_row(content: str, item_id: str, new_status: str = "DONE", end_art: str = "done") -> str:
    """
    Ersetzt die Status-Spalte der Zeile mit genau item_id in Spalte 1.

    Pipe-aware (BL-434): verwendet split('|') statt [^|]*-Regex — Titel mit Pipes
    verursachen keinen Spaltenversatz. Status-Anker: Spalte direkt vor Vault-Pfad
    (enthaelt 'Backlog/').

    line-anchored (AK-2): exakter strip-Vergleich auf cells[1] verhindert
    BL-364/BL-3640-Kollision.

    Idempotent (AK-5): wenn Status-Zelle bereits '{new_status} ({end_art})',
    wird content unveraendert zurueckgegeben.

    end_art nicht in END_ART_ENUM -> fallback "done".

    Defensiv: wenn keine Vault-Pfad-Spalte gefunden (malformed row),
    Zeile unveraendert lassen (kein Crash).
    """
    if end_art not in END_ART_ENUM:
        end_art = "done"

    expected_status = f"{new_status} ({end_art})"

    line_idx, cells, lines = _locate_row_cells(content, item_id)
    if line_idx is None:
        return content  # item_id nicht gefunden — unveraendert

    status_idx = _status_index(cells)
    if status_idx is None:
        return content  # malformed row — defensiv unveraendert

    # Idempotenz-Check
    if cells[status_idx].strip() == expected_status:
        return content

    # Status-Zelle aktualisieren; alle anderen Zellen (inkl. Titel-Pipes) unveraendert
    cells[status_idx] = f" {expected_status} "
    lines[line_idx] = '|'.join(cells)

    return ''.join(lines)


def index_row_has_done(content: str, item_id: str) -> bool:
    """
    True wenn die Zeile fuer item_id in der echten Status-Spalte 'DONE' enthaelt.

    Pipe-aware (BL-434): Anker auf Vault-Pfad-Spalte — 'DONE' im Titel-Fragment
    (z.B. '| tier|DONE inline | DRAFT | Backlog/...') fuehrt nicht zu True.

    Read-Back-Helper fuer AK-1: nach update_index_row aufrufen um Persistenz
    zu bestaetigen.
    """
    line_idx, cells, _ = _locate_row_cells(content, item_id)
    if line_idx is None:
        return False
    status_idx = _status_index(cells)
    if status_idx is None:
        return False
    return "DONE" in cells[status_idx]


def find_corrupted_rows(content: str) -> list:
    """
    Diagnose-Funktion: findet Zeilen die auf roh-Pipe-Korruption hindeuten.

    Heuristik: eine Zeile gilt als verdaechtig wenn
    - sie mehr Spalten hat als der Header (wenn vorhanden) ODER
    - die Status-Anker-Heuristik fehlschlaegt (kein 'Backlog/'/.md in erwarteter Position) ODER
    - 'DONE' oder 'DRAFT' mehrfach in der Zeile vorkommt.

    Reine Diagnose — keine Auto-Edits. Gibt Liste der verdaechtigen Rohzeilen zurueck.
    """
    lines = content.splitlines()
    corrupted = []

    # Header-Spaltenanzahl bestimmen (erste Zeile die mit '|' beginnt und BL-ID enthaelt)
    header_col_count = None
    for line in lines:
        if line.startswith('|') and 'BL-ID' in line:
            header_col_count = len(line.split('|'))
            break

    for line in lines:
        if not line.startswith('|'):
            continue
        # Trennzeilen (|---|...) ueberspringen
        stripped = line.replace('-', '').replace(' ', '').replace('|', '')
        if not stripped:
            continue

        cells = line.split('|')
        suspicious = False

        # Mehr Spalten als Header -> moeglicherweise Pipe im Inhalt
        if header_col_count is not None and len(cells) > header_col_count + 2:
            # Pruefe ob Vault-Pfad-Anker fehlt
            status_idx = _status_index(cells)
            if status_idx is None:
                suspicious = True

        # 'DONE' oder 'DRAFT' mehrfach in der Zeile
        if line.count('DONE') > 1 or line.count('DRAFT') > 1:
            suspicious = True

        if suspicious:
            corrupted.append(line)

    return corrupted
