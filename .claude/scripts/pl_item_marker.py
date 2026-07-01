"""
pl_item_marker.py — BL-435 batch_1a

Hilfsfunktionen fuer das Markieren von PL-Items in _parking-lot.md Dateien.

VERTRAG (pure-string, kein File-IO):
  EINGABE:  content (str)  — kompletter _parking-lot.md Text
            item_id (str)  — PL-Item-ID, kanonisch '{bl}-AK-{n}-PL-1'
  AUSGABE:  mark_pl_done       -> str  (geflippter content; unveraendert wenn no-op)
            pl_item_is_done    -> bool (done-Erkennung ueber 6 Formate)
            is_canonical_pl_item -> bool (Schema-Guard auf kanonisches Format)

AKs:
  AK-1: mark_pl_done + pl_item_is_done Kern (Flip beider Signale, Idempotenz, Read-Back)
  AK-2: pl_item_is_done Toleranz-Matrix (5 Alt-Formate + kanonisch)
  AK-5: is_canonical_pl_item Schema-Guard (CANONICAL_PATTERN Validator)

Patterns:
  PT-CMD-007 Idempotenz   — Doppel-Aufruf liefert identisches Ergebnis.
  PT-CMD-011 Fail-Loud    — kanonischer Pfad nutzt strikten CANONICAL_PATTERN.
  PT-CMD-023 Graceful Degradation — leere/unbekannte Eingabe -> sichere Default-Rueckgabe.

Vorbild-Struktur: bl_index_updater.py (zelltreue Lokalisierung, Idempotenz, defensiv).
Keine externen Abhaengigkeiten ausser re.
"""

import re

# ---------------------------------------------------------------------------
# CANONICAL_PATTERN — Single Source of Truth (ADE-4)
# Kanonisches Format: - [ ] **{bl}-AK-{n}-PL-1** (status: open) — {title}
#                     - [x] **{bl}-AK-{n}-PL-1** (status: done) — {title}
# ---------------------------------------------------------------------------

CANONICAL_PATTERN = re.compile(
    r'^- \[( |x)\] \*\*(.+?)\*\* \(status: (open|done)\) — .+'
)


def _normalize_to_canonical_open(line: str, item_id: str) -> str:
    """
    Normalisiert single-line Alt-Formate auf kanonisch-open.

    Symmetrisch zu den pl_item_is_done-Detektoren (DETEKTOR-1, DETEKTOR-3, DETEKTOR-4).
    Wird in mark_pl_done VOR flip_pattern aufgerufen (AK-F1, BL-447).

    Unterstuetzte Alt-Formate (normalisierbar):
      - Kanonisch-open (DETEKTOR-0-analog): unveraendert zurueck
      - REAL-Hybrid: '- [ ] **{id}** [STATUS: ...] (status: open) — {title}'
      - Checkbox+STATUS-Tag: '- [ ] **{id}** [STATUS: ...]' (mit oder ohne titel)
      - Bold-Checkbox: '[ ] **{id}**' (kein Titel)

    Nicht normalisierbar (multi-line, strukturell):
      - Tabellen-Zeile (Format-2): Aufrufer landet in fail-loud Z103
      - Frontmatter-Header (Format-5): Aufrufer landet in fail-loud Z103

    Gibt kanonisch-open-Zeile zurueck: '- [ ] **{item_id}** (status: open) — {titel}'
    oder unveraendert wenn kein unterstuetztes Alt-Format erkannt.
    """
    # Wenn bereits kanonisch-open — unveraendert (flip_pattern greift direkt)
    canonical_open_pat = re.compile(
        r'^- \[ \] \*\*' + re.escape(item_id) + r'\*\* \(status: open\)'
    )
    if canonical_open_pat.match(line):
        return line

    bold_needle = f'**{item_id}**'
    if bold_needle not in line:
        return line

    # Bewahre trailing whitespace/newline des Originals (BL-447 Fix: splitlines(keepends=True)
    # liefert Zeile MIT \n; ohne Erhalt klebt naechste Zeile beim ''.join(lines) an).
    trailing = ''
    stripped_line = line.rstrip('\r\n')
    if len(stripped_line) < len(line):
        trailing = line[len(stripped_line):]

    # Versuche Titel zu extrahieren: alles nach ' — ' am Zeilenende (stripped)
    title = ''
    em_dash_idx = stripped_line.rfind(' — ')
    if em_dash_idx != -1:
        title = stripped_line[em_dash_idx + 3:].rstrip()

    # Format-1 / Hybrid: Zeile enthaelt '[ ] **{id}**' (open checkbox, kein [x])
    # Erkennt:
    #   '- [ ] **{id}** [STATUS: IN_ARBEIT] (status: open) — {title}'
    #   '- [ ] **{id}** [STATUS: IN_ARBEIT]'
    #   '- [ ] **{id}** (status: open) — {title}'  (schon kanonisch, oben abgefangen)
    open_cb_pat = re.compile(r'(?:^|[\s|])\[ \] \*\*' + re.escape(item_id) + r'\*\*')
    if open_cb_pat.search(line):
        if title:
            return f'- [ ] **{item_id}** (status: open) — {title}{trailing}'
        else:
            return f'- [ ] **{item_id}** (status: open) —{trailing}'

    # Format-3: Bold-Checkbox ohne list-prefix '[ ] **{id}**'
    # (offene Checkbox ohne '-' Prefix)
    bold_cb_open = re.compile(r'^\[ \] \*\*' + re.escape(item_id) + r'\*\*')
    if bold_cb_open.match(line.strip()):
        if title:
            return f'- [ ] **{item_id}** (status: open) — {title}{trailing}'
        else:
            return f'- [ ] **{item_id}** (status: open) —{trailing}'

    # Nicht normalisierbar (Tabellen-Zeile, Frontmatter, sonstiges)
    return line


def _locate_pl_line(content: str, item_id: str):
    """
    Findet die erste Zeile in content, die item_id als Bold-Segment enthaelt.

    Sucht nach **{item_id}** in jeder Zeile via splitlines(keepends=True).
    Gibt (line_index, lines) zurueck oder (None, lines) wenn nicht gefunden.
    Mehrfach-Treffer: erstes Match (defensiv: nur erste Zeile, kein multi-flip).

    Analogon zu _locate_row_cells in bl_index_updater.py.
    """
    if not item_id:
        return None, []
    lines = content.splitlines(keepends=True)
    needle = f"**{item_id}**"
    for idx, line in enumerate(lines):
        if needle in line:
            return idx, lines
    return None, lines


# ---------------------------------------------------------------------------
# mark_pl_done — AK-1: Haupt-Writer (Idempotenz-Check zuerst, atomares Flip)
# ---------------------------------------------------------------------------

def mark_pl_done(content: str, item_id: str) -> str:
    """
    Flippt kanonische open-Zeile auf done — atomar (beide Signale in einem re.sub).

    Idempotenz (ADE-2): Ruft pl_item_is_done ZUERST — wenn schon done, unveraendert.
    Defensiv: item_id leer/nicht gefunden -> content unveraendert zurueck, kein Crash.
    Nur erster Treffer wird geflippt (kein multi-flip).

    Entspricht update_index_row-Muster aus bl_index_updater.py (Z60-100).
    """
    if not item_id or not content:
        return content

    # Idempotenz-Check zuerst (PT-CMD-007 Idempotenz-Guard)
    if pl_item_is_done(content, item_id):
        return content

    line_idx, lines = _locate_pl_line(content, item_id)
    if line_idx is None:
        return content  # item_id nicht gefunden — defensiv unveraendert

    target_line = lines[line_idx]

    # Normalisiere Alt-Formate auf kanonisch-open (AK-F1, BL-447)
    # Symmetrisch zu pl_item_is_done-Detektoren; flip_pattern bleibt unveraendert strikt.
    target_line = _normalize_to_canonical_open(target_line, item_id)

    # Atomares Doppel-Flip: '[ ]' -> '[x]' UND 'status: open' -> 'status: done'
    # in einem einzigen re.sub (verhindert Partial-Update bei Regex-Fehler).
    # Gruppen: (1) Listen-Prefix '- ' | (2) offene Checkbox (verworfen, -> '[x]')
    #          (3) ' **{item_id}** (status: ' | (4) 'open' (verworfen, -> 'done')
    #          (5) Rest der Zeile ab ')'
    def _flip_open_to_done(match):
        list_prefix = match.group(1)
        between_checkbox_and_status = match.group(3)
        line_remainder = match.group(5)
        return f"{list_prefix}[x]{between_checkbox_and_status}done{line_remainder}"

    flip_pattern = (
        r'(- )(\[ \])( \*\*' + re.escape(item_id) + r'\*\* \(status: )(open)(\).*)'
    )
    flipped = re.sub(flip_pattern, _flip_open_to_done, target_line)

    if flipped == target_line:
        # Zeile gefunden aber Flip nicht moeglich — fail-loud (AK-F3, BL-447, W-CTRL-1)
        raise RuntimeError(
            f"mark_pl_done: item_id '{item_id}' gefunden aber nicht flippbar. "
            f"Zeile: {target_line!r}"
        )

    lines[line_idx] = flipped
    return ''.join(lines)


# ---------------------------------------------------------------------------
# pl_item_is_done — AK-1 + AK-2: Read-Back + Toleranz-Detektor-Kette
# ---------------------------------------------------------------------------

def pl_item_is_done(content: str, item_id: str) -> bool:
    """
    True wenn item_id im content als done markiert ist — erkennt 6 Formate.

    Erkennungs-Reihenfolge (kanonisch zuerst, sicherste zuerst):
      DETEKTOR-0: kanonisch '- [x] **{item_id}** (status: done) — {title}'
      DETEKTOR-1: Checkbox + STATUS-Tag '- [x] {item_id} [STATUS: ...]'
      DETEKTOR-2: Tabellen-Zeile '| {item_id} | done |'
      DETEKTOR-3: Bold-Checkbox '[x] **{item_id}**'
      DETEKTOR-4: Bold-ID PL-N Kurzform '- [x] **PL-{n}**' (fuer {bl}-AK-{n}-PL-1)
      DETEKTOR-5: Frontmatter-only '### {item_id}' + 'status: done' innerhalb 10 Zeilen

    Defensiv: unbekanntes Format / leere item_id -> False (niemals True bei Ambiguitaet).
    PT-CMD-023 Graceful Degradation.
    """
    if not item_id or not content:
        return False

    # Einmal splitten, von allen Detektoren wiederverwendet (DRY).
    lines = content.splitlines()

    # DETEKTOR-0: kanonisch (CANONICAL_PATTERN + item_id + status: done)
    canonical_done_pattern = re.compile(
        r'^- \[x\] \*\*' + re.escape(item_id) + r'\*\* \(status: done\)'
    )
    for line in lines:
        if canonical_done_pattern.match(line):
            return True

    # DETEKTOR-1: Checkbox + STATUS-Tag '- [x] {item_id} [STATUS: ...]'
    for line in lines:
        if f'[x] {item_id}' in line and '[STATUS:' in line:
            return True

    # DETEKTOR-2: Tabellen-Zeile mit item_id + done in derselben Zeile
    # z.B. '| BL-435-AK-1-PL-1 | done |'
    for line in lines:
        if item_id in line and '|' in line:
            cells = line.split('|')
            has_id = any(c.strip() == item_id for c in cells)
            has_done = any(c.strip() == 'done' for c in cells)
            if has_id and has_done:
                return True

    # DETEKTOR-3: Bold-Checkbox '[x] **{item_id}**'
    d3_pattern = re.compile(r'\[x\] \*\*' + re.escape(item_id) + r'\*\*')
    for line in lines:
        if d3_pattern.search(line):
            return True

    # DETEKTOR-4: Bold-ID PL-N Kurzform '- [x] **PL-{n}**'
    # Nur wenn item_id das Schema '{bl}-AK-{n}-PL-1' hat
    n_match = re.search(r'-AK-(\d+)-PL-\d+$', item_id)
    if n_match:
        ak_nummer = n_match.group(1)
        d4_pattern = re.compile(r'\[x\] \*\*PL-' + re.escape(ak_nummer) + r'\*\*')
        for line in lines:
            if d4_pattern.search(line):
                return True

    # DETEKTOR-5: Frontmatter-only '### {item_id}' + 'status: done' innerhalb 10 Zeilen
    header_marker = f'### {item_id}'
    for i, line in enumerate(lines):
        if line.strip() == header_marker:
            # Suche 'status: done' im Fenster der naechsten 10 Zeilen
            window = lines[i + 1: i + 11]
            for window_line in window:
                if window_line.strip() == 'status: done':
                    return True

    return False


# ---------------------------------------------------------------------------
# is_canonical_pl_item — AK-5: Schema-Guard (CANONICAL_PATTERN Validator)
# ---------------------------------------------------------------------------

def is_canonical_pl_item(line: str) -> bool:
    """
    True NUR wenn line exakt dem kanonischen Schema entspricht:
      '- [ ] **{bl}-AK-{n}-PL-1** (status: open) — {title}'
      '- [x] **{bl}-AK-{n}-PL-1** (status: done) — {title}'

    False fuer alle 5 Alt-Formate (Checkbox+STATUS-Tag, Tabellen-Zeile,
    Bold-Checkbox ohne status-Feld, PL-N Kurzform, Header-only).

    Nutzt CANONICAL_PATTERN (ADE-4: Single Source of Truth).
    Defensiv: kein Crash bei beliebigem line-Inhalt.
    """
    if not line:
        return False
    return bool(CANONICAL_PATTERN.match(line))
