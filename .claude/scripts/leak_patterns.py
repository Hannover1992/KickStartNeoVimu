#!/usr/bin/env python3
"""
leak_patterns.py — Kanonische Leak-Pattern-Liste fuer Commit-Messages (BL-295 AK-3).

SINGLE-SOURCE (AK-3-shared): Diese Liste ist die EINE Quelle der Leak-Patterns. Sie wird
geteilt von:
  - dem git commit-msg-Hook `commit_msg_leak_guard.py` (AK-2, defense-in-depth, faengt
    auch manuelle Commits — BL-295-Symptom: 486-Commits mit `(PR-Review Duc PR2-DUC-X)`
    raw gepusht), und
  - dem `_stage_orchestrate.md` Phase-2.3 Security-Gate (Skill-Pfad, Pruefung 1-5).
Gate + Hook DUERFEN NICHT driften — bei Pattern-Aenderung NUR diese Datei editieren.

Defense-in-depth gegen internen Prozess-Info-Leak in der git-History — UNABHAENGIG wer
committet (Motor/Hand/MANUELL).

AUSNAHME (kein Leak): JIRA-Ticket-ID `DCSRE-\\d+` ist fachlich erlaubt. Die `BL-\\d+`-Regel
ist auf das `BL-`-Praefix begrenzt (\\b), trifft also kein `DCSRE-\\d+` — kein generisches
`\\w+-\\d+`, das JIRA-Tickets faelschlich faengt.

DIP: Keine Repo-/Prozess-Logik — nur Pattern-Definition + reiner Text-Scan.
"""

import re


class LeakMatch:
    """Ein Leak-Treffer. str()/repr() enthalten den pattern_id (Test prueft
    `pattern_id in str(treffer)`) plus den matchenden Text-Ausschnitt."""

    __slots__ = ("pattern_id", "match", "beschreibung")

    def __init__(self, pattern_id, match, beschreibung):
        self.pattern_id = pattern_id
        self.match = match
        self.beschreibung = beschreibung

    def __str__(self):
        return f"{self.pattern_id}: {self.match!r} ({self.beschreibung})"

    def __repr__(self):
        return f"LeakMatch({self.pattern_id!r}, {self.match!r})"


# ---------------------------------------------------------------------------
# Pattern-Definitionen (id, kompiliertes regex, beschreibung)
# Reihenfolge aus _stage_orchestrate Phase 2.3 Pruefung 1-5.
# ---------------------------------------------------------------------------

# COAUTH — Co-Authored-By / Co-Author Trailer (Pruefung 1+2)
_COAUTH_RE = re.compile(r"co-?authored?-by:|co-?author:", re.IGNORECASE)

# ANTHROPIC — Erwaehnung des Vendor-Namens (Pruefung 3)
_ANTHROPIC_RE = re.compile(r"\banthropic\b", re.IGNORECASE)

# CLAUDE_TRAILER — `claude` NUR im Trailer-Kontext (Pruefung 4). Scope auf Zeilen die
# wie ein Trailer aussehen (Co-Authored-By:/Co-Author:/Signed-off-by: o.ae.), damit
# normaler Fliesstext mit dem Wort "claude" nicht faelschlich triggert.
_CLAUDE_RE = re.compile(r"\bclaude\b", re.IGNORECASE)
_TRAILER_LINE_RE = re.compile(
    r"^\s*(co-?authored?-by|co-?author|signed-off-by|on-behalf-of)\s*:",
    re.IGNORECASE,
)

# PROC_XREF — Prozess-Cross-Referenzen (Pruefung 5). `\bBL-\d+\b` ist praefix-gebunden,
# damit `DCSRE-\d+` (JIRA-Ticket) NICHT als interner BL-Leak gewertet wird.
_PROC_XREF_RE = re.compile(
    r"Gr\.\d+"
    r"|PR-Gruppe"
    r"|PR-Review"
    r"|PR2-DUC"
    r"|PL-Item"
    r"|\b(?:BDF|SDF|IDF)\b"
    r"|\bBL-\d+\b"
    r"|Parking.?Lot"
    r"|mode=answer"
    r"|Handschuh.?Wechsel"
    r"|\bWellen\b"
    r"|K-Score"
    r"|_[A-Z]_orchestrate"
    r"|/_\w+",
    re.IGNORECASE,
)

# PLACEHOLDER — die GESAMTE getrimmte Message ist ein Platzhalter (kein Teil-Match).
_PLACEHOLDER_RE = re.compile(
    r"^(?:Unwichtig|WIP|tmp|test|asdf|xxx|\.)\.?\s*$",
    re.IGNORECASE,
)


def _scan_lines(text):
    """Zeilenweiser Scan fuer COAUTH/ANTHROPIC/CLAUDE_TRAILER/PROC_XREF."""
    hits = []
    for line in text.splitlines():
        m = _COAUTH_RE.search(line)
        if m:
            hits.append(LeakMatch("COAUTH", m.group(0), "Co-Authored-By/Co-Author Trailer"))

        m = _ANTHROPIC_RE.search(line)
        if m:
            hits.append(LeakMatch("ANTHROPIC", m.group(0), "Anthropic-Erwaehnung"))

        # CLAUDE nur in Trailer-Zeilen werten (false-positive-Schutz im Fliesstext).
        if _TRAILER_LINE_RE.match(line):
            m = _CLAUDE_RE.search(line)
            if m:
                hits.append(LeakMatch("CLAUDE_TRAILER", m.group(0), "Claude im Trailer-Kontext"))

        m = _PROC_XREF_RE.search(line)
        if m:
            hits.append(LeakMatch("PROC_XREF", m.group(0), "Prozess-Cross-Referenz"))
    return hits


def scan_message(text):
    """Scannt die GESAMTE Commit-Message (Titel + Body + Trailer) auf interne
    Prozess-Info-Leaks. Gibt eine Liste von LeakMatch zurueck (leer = clean).

    DCSRE-\\d+ (JIRA-Ticket) ist KEIN Leak und liefert []."""
    if text is None:
        return []

    hits = _scan_lines(text)

    # PLACEHOLDER nur, wenn die GESAMTE (getrimmte) Message ein Platzhalter ist.
    stripped = text.strip()
    if _PLACEHOLDER_RE.match(stripped):
        hits.append(LeakMatch("PLACEHOLDER", stripped, "Platzhalter-Message ohne fachlichen Inhalt"))

    return hits
