#!/usr/bin/env python3
"""truth_wid.py — DIE EINE kanonische W-ID-Lexikon-Definition (BL-395 c).

Vorher lebte das W-ID-Token-Regex 4x dupliziert (truth_atomizer._WREF_IN_TEXT, truth_backref_index._WREF,
truth_resolver._WID_TOKEN, truth_census._WID_TOKEN) UND es war ENGER als _HEADING_LINE (atomizer): der
HEADING-Parser erfasst local_ids mit '_'/langem Suffix (W7_REF, W10_REF, W14_REF), die Text-Referenz-Lexika
aber nicht (`\\d+[A-Za-z]?`, nur EIN Suffix-Buchstabe, kein '_'). Folge (Audit-Vektor 3, BL-395): W*_REF-Knoten
WERDEN als Truths erzeugt (Heading-Parse), aber JEDE textuelle Referenz auf sie war fuer forward_edges /
referenced_by / resolver UNSICHTBAR (das `\\b` nach 'W7' greift bei 'W7_REF' nicht, '_' ist Wort-Zeichen) ->
Verbindungs-Schicht-Verlust, von keinem Gate erfasst.

Fix: EINE Quelle. WID_BODY ist IDENTISCH mit dem local_id-Body in _HEADING_LINE -> Definition und Referenz
loesen denselben Key auf. Die Digit-First-Regel bleibt (W\\d...) -> deutsche W-Woerter (Warum/Workflow/Wellen/
Worker) matchen NICHT (kein Over-Match); '## W-Knoten'-Section-Heading ausgeschlossen via (?!Knoten\\b).
"""
import re

# W-ID-Body: W+Ziffer(+[A-Za-z0-9_]* Suffix) ODER W-GROSS-dashed. BL-395(c)/B2-Audit Gap-B: optionaler
# Bindestrich VOR den Ziffern (`-?\d+`) erfasst die Heading-Form `### W-01:` .. `### W-07` (BL-215), die
# der dashed-Zweig (verlangt [A-Z] nach `-`) verfehlte. `W-Knoten` bleibt ausgeschlossen (kein Digit/(?!Knoten)).
WID_BODY = r"W(?:-?\d+[A-Za-z0-9_]*|-(?!Knoten\b)[A-Z][A-Za-z0-9_-]*)"

# DIE kanonische Text-Referenz-Token-Form (wortgrenzen-gebunden) fuer ALLE Referenz-Schichten.
WID_TOKEN = re.compile(r"\b" + WID_BODY + r"\b")

# BL-395 b / B2: Line-start W-DEFINITION in JEDEM Format (Heading/Bullet/Tabelle/bare/Bold). DIE EINE Quelle
# fuer census-Zaehlung (count_wknots.member_defs) UND die B2-Segment-Grenze (atomize_segments) -> garantiert
# census-Zaehlung == Segment-Zahl (knots>=census fuer recovered Models). NUR Zeilenanfang -> Prosa-Erwaehnungen
# /Cross-Refs (mitten im Satz) sind KEINE Definitionen (kein Over-Count/Over-Segment).
# B2-Audit Gap-A: Praefix als SEQUENZ optionaler Gruppen (statt 1-Token-Alternation) -> kombinierte Marker
# wie `- **W1:**` (Bullet+Bold) und `| **W1** |` (Tabellenzelle+Bold) matchen. Reihenfolge: Heading-# ->
# Bullet/Pipe -> Bold. KEIN Quote-Praefix (`"W4:`): die einzigen Quote-Faelle im Korpus sind BL-372 quoted
# CROSS-REFS, KEINE Definitionen -> ein Quote-Praefix wuerde sie faelschlich zu Junk-Truths machen (Over-Match).
# Over-Seg-Guard: ein W-Id am Zeilenanfang, direkt gefolgt von einem Pfeil (`-->`/`->`), ist eine Mermaid-/
# Sequenz-Graph-KANTE, KEINE Definition -> negativer Lookahead schliesst sie aus (verhindert Pseudo-Truth-
# Knoten beim Cutover). Referenzen (WID_TOKEN) behalten Pfeil-Ziele = echte Kanten.
WDEF_LINE = re.compile(
    r"(?m)^[ \t]*(?:#{1,6}[ \t]+)?(?:[-*+|][ \t]*)?(?:\*\*[ \t]*)?(" + WID_BODY + r")\b(?![ \t]*-{1,2}>)"
)
