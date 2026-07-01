#!/usr/bin/env python3
"""pl_defer_filter.py — BL-304 AK-3 (Defer-Marker-Guard beim Batch-Schnitt).

Rein + deterministisch: ein als Defer markiertes PL-Item darf beim Batch-Schnitt
NICHT in der aktiven Batch-Formation verbleiben (es bleibt im PL fuer eine spaetere /
eigene Runde — NICHT geloescht, nur aus der aktiven Auswahl gefiltert).

Live-Fall (DCSRE-486 batch_PL23): `[~] DEFER 2026-06-09b — eigener Chip-Delegate-Batch`
(T2076) blieb im aktiven Batch -> inflationierte k_max -> erzwang M2 fuer alle 11 Items
statt M1-MULTI fuer die trivialen. Dieser Filter schliesst genau solche Defer-Inseln aus.

Kanonischer Defer-Filter — zitiert von den drei PL-lesenden Batch-Formations-Beratern
(_IDF_berater_clustering Phase 5, _IDF_berater_sequencePlanner Phase 6,
_IDF_berater_batchPlanner Phase 7) als gemeinsame, einheitliche Defer-Exclusion-Naht
(EINE Wahrheit statt 3 divergenter Inline-Filter).

KONSERVATIV (Anti-Ueber-Filter, AK-3 explizit): NUR eindeutige Defer-Marker filtern.
  Defer  ==  Status-Marker `[~]`  ODER  `DEFER`-Token (Wort-Grenze) im Item-Text.
  `[ ]` (offen) und `[x]` (done) werden vom Defer-Filter NICHT angefasst — die
  uebergeordnete "welcher Marker ist aktiv-batch-faehig"-Entscheidung bleibt beim
  Caller. AK-3 entfernt AUSSCHLIESSLICH die Defer-Inseln, orthogonal zum Modus
  (INV-MODUS-1 unberuehrt).

Kontrakt:
- parse_pl_line(line)            -> dict | None   (None fuer Nicht-Item-Zeilen)
- is_defer_marked(item)          -> bool          (True NUR bei eindeutigem Defer)
- filter_active_batch_items(its) -> list          (Defer raus, None-tolerant, idempotent)
"""
import re

# PL-Item-Zeile: "- [<marker>] <text>"  — marker ∈ { ' ', 'x', '~', '!', '?' }.
# (Status-Konvention: [ ] offen, [x] done, [~] FREEZE/DEFER, [!] BLOCKER, [?] HOLD.)
_PL_LINE_RE = re.compile(r"^\s*[-*]\s*\[(?P<marker>[ x~!?])\]\s*(?P<text>.*)$")

# DEFER-Token als ganzes Wort (case-insensitive). Wort-Grenze verhindert, dass z.B.
# "defernotwendig" o.ae. faelschlich matcht — konservativ, nur der explizite Marker.
_DEFER_TOKEN_RE = re.compile(r"\bDEFER\b", re.IGNORECASE)


def parse_pl_line(line):
    """Parst eine rohe PL-Markdown-Zeile in ein Item-dict — oder None.

    Returns dict {marker, defer, text} fuer eine valide Checkbox-Item-Zeile,
    sonst None (Header, Legende ohne Checkbox, Leerzeile, Aggregat-Block etc.).

    defer = True gdw. marker == '~'  ODER  text enthaelt das DEFER-Token.
    """
    if not isinstance(line, str):
        return None
    m = _PL_LINE_RE.match(line)
    if not m:
        return None
    marker = m.group("marker")
    text = m.group("text").strip()
    defer = (marker == "~") or bool(_DEFER_TOKEN_RE.search(text))
    return {"marker": marker, "defer": defer, "text": text}


def is_defer_marked(item):
    """Reines Praedikat: ist das (geparste) Item ein eindeutiges Defer-Item?

    None-tolerant (None -> False). Erwartet ein dict aus parse_pl_line; faellt
    defensiv auf die rohe Marker-/Text-Inspektion zurueck, falls noetig.
    """
    if not item or not isinstance(item, dict):
        return False
    if "defer" in item:
        return bool(item["defer"])
    # Defensiver Fallback, falls ein Caller ein Item ohne vorberechnetes defer-Flag
    # uebergibt (z.B. {marker, text} aus anderem Parser).
    marker = item.get("marker")
    text = item.get("text", "") or ""
    return marker == "~" or bool(_DEFER_TOKEN_RE.search(text))


def filter_active_batch_items(items):
    """Gibt nur die NICHT-defer-markierten Items zurueck — fuer die aktive Batch-Bildung.

    Defer-Items werden NICHT geloescht (sie bleiben im PL fuer eine spaetere Runde),
    nur aus der aktiven Auswahl entfernt. None-Eintraege werden defensiv verworfen.
    Idempotent: filter(filter(x)) == filter(x).
    """
    if not items:
        return []
    return [item for item in items if item is not None and not is_defer_marked(item)]
