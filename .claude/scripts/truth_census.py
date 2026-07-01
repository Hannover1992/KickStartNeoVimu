#!/usr/bin/env python3
"""truth_census.py — BL-309 PHASE-1.1 read-only Truth-Census (den Brocken messen, NULL Mutation).

Walkt alle Model-Dateien (Vault-BL-Ordner 2_Model/ + alte Model/ + Vault-Root *Model* + .claude/models-Repo)
und zaehlt die eingebetteten W{n}-Wahrheits-Knoten + klassifiziert ihre Format-Generation. STRIKT READ-ONLY:
schreibt NUR den Report (--out), beruehrt NIE einen Model. Erster-Cut-Census via Mehr-Muster-Detektion
(walker-unabhaengiger Naeherungs-Nenner); die volle 6-Format-Roundtrip-Genauigkeit kommt im BL-309-Vollbau.

CLI: py -3 truth_census.py [--vault PATH] [--repo-models PATH] [--out PATH] [--quiet]
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_VAULT = r"C:/Users/Administrator/Documents/OmniCommand"
DEFAULT_REPO_MODELS = ".claude/models"

# Exclude (Logs/Snapshots = keine Wahrheiten, Konzept Schritt 3 Walker-Exclude).
_SKIP_SUBSTR = ("_modelSync_log", "_modelsync_log", "_retract_log", "_snapshot", ".pre_truth", "_legacy")

# W-Knoten-Signale (Mehr-Muster, walker-unabhaengig).
# PRAEZISIERT 2026-06-16: W-Knoten-ID = W+Ziffer (W01/W1) ODER W-GROSSBUCHSTABE (W-IST-1/W-AK-A) — schliesst
# deutsche W-Woerter aus (Warum/Workflow/Worker/Wellen = W+Kleinbuchstabe, KEINE Knoten). Verhindert die
# Heading-Ueberzaehlung des Erster-Cut (Lexikon-Probe 'Worker-#' war der Verraeter).
# GEHAERTET 2026-06-16 (b309-census-v3 inline-recovery): negativer Lookahead (?!Knoten\b) schliesst die
# Section-Ueberschrift "## W-Knoten" (+ "W-Knoten-Uebersicht" etc.) aus — das ist die UEBERSCHRIFT, die eine
# Knoten-Liste einleitet, NICHT ein Knoten selbst (W-K kollidierte mit W-[A-Z]). Der letzte benannte Ueberzaehler.
_WKNOT_HEADING = re.compile(r"(?m)^#{1,6}[ \t]+(W\d|W-(?!Knoten\b)[A-Z])")  # ### W01 / ## W-IST-1 / ### W-AK-A (NICHT ## W-Knoten)
_FIELD_AUSSAGE = re.compile(r"(?im)^\s*\*\*\s*aussage\s*:?\s*\*\*")        # **Aussage:** (juengste Generation)
_FIELD_TEXT = re.compile(r"(?im)^\s*\*\*\s*text\s*:?\s*\*\*")              # **text:** (aeltere Feld-Form)
_TRUTH_FM = re.compile(r"(?im)^\s*type\s*:\s*truth\b")                     # type: truth (Ziel-Format A)
_WAHRHEITEN_KEY = re.compile(r"(?im)^\s*wahrheits_knoten\s*:")             # yaml-Aggregat-Key
try:
    from truth_wid import WID_TOKEN as _WID_TOKEN  # BL-395(c): EINE kanonische W-ID-Lexikon-Quelle (= _HEADING_LINE)
except ImportError:  # Fallback unifiziert mit _HEADING_LINE local_id-Body (W+Ziffer+[A-Za-z0-9_]* | W-GROSS, NICHT W-Knoten)
    _WID_TOKEN = re.compile(r"\bW(?:\d+[A-Za-z0-9_]*|-(?!Knoten\b)[A-Z][A-Za-z0-9_-]*)\b")

# BL-395: W-DEFINITIONS-Zeile — ein W-Knoten, der am ZEILENANFANG definiert wird, in JEDEM Format:
# Heading (### W01), Dash-/Bullet-Liste (- W1:), Tabellen-Zelle (| W7 |), Bold-Marker (**W01**), bare (W1:).
# Bricht den census==atomizer-HEADING-Lockstep (BL-395 Audit-Befund): der reine HEADING-Census unterzaehlte
# Bullet-/Tabellen-/yaml-Knoten identisch auf 0 wie der HEADING-Atomizer -> complete=knots>=0=True ->
# Silent-total-Loss als 'ready' durchgewunken (41 Models / 1208 W-Truths). member_defs ist ein UNABHAENGIGES
# Signal -> der bestehende complete-Gate faengt den Verlust. NUR Zeilenanfang (nach optionalem Marker) ->
# Prosa-Erwaehnungen + Cross-Refs (W-Token mitten im Satz = Referenz, KEIN Definitions-Knoten) zaehlen NICHT
# (kein Over-Count auf sauberen HEADING-Models: deren member_defs == headings).
try:
    from truth_wid import WDEF_LINE as _WDEF_LINE  # BL-395(c): EINE kanonische Quelle (== B2-Segment-Grenze)
except ImportError:
    _WDEF_LINE = re.compile(
        r"(?m)^[ \t]*(?:#{1,6}[ \t]+|[-*+|][ \t]*|\*\*[ \t]*)?(W(?:\d+[A-Za-z0-9_]*|-(?!Knoten\b)[A-Z][A-Za-z0-9_-]*))\b"
    )
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.S)  # yaml-Frontmatter-Block (BL-203 wahrheits_knoten)


def is_candidate(path: Path) -> bool:
    """Kandidaten-Filter: 2_Model/ ODER Model/ ODER *model*-Stem (Vault) bzw. repo-models."""
    s = str(path).replace("\\", "/")
    if any(sub in s for sub in _SKIP_SUBSTR):
        return False
    parts = path.parts
    return ("2_Model" in parts or "Model" in parts or "model" in path.stem.lower())


def count_wknots(text: str) -> dict:
    """Mehr-Muster-Zaehlung. total_estimate = max der unabhaengigen Signale (Anti-Doppelzaehlung)."""
    headings = len(_WKNOT_HEADING.findall(text))
    aussage = len(_FIELD_AUSSAGE.findall(text))
    field_text = len(_FIELD_TEXT.findall(text))
    field_markers = aussage + field_text
    truth_fm = len(_TRUTH_FM.findall(text))
    # BL-395: W-DEFINITIONEN (Zeilenanfang, format-agnostisch) als UNABHAENGIGES Signal -> bricht den
    # HEADING-Lockstep (Bullet/Tabelle/bare/Bold-Knoten, die der reine HEADING-Parser auf 0 verfehlt). Distinct.
    member_defs = len(set(_WDEF_LINE.findall(text)))
    # BL-395: yaml-Aggregat (wahrheits_knoten:) -> distinkte W-Ids im Frontmatter (BL-203-Silent-Loss-Klasse).
    fm = _FRONTMATTER_RE.match(text)
    wahr_yaml = len(set(_WID_TOKEN.findall(fm.group(1)))) if (fm and _WAHRHEITEN_KEY.search(text)) else 0
    # Naeherungs-Nenner: das STAERKSTE unabhaengige Signal. member_defs/wahr_yaml heben den frueheren
    # 0-Blindfleck fuer Nicht-HEADING-Formate auf (BL-395) -> complete = knots >= census wird ein echter
    # Coverage-Gate statt eines census==atomizer-Lockstep-No-Op.
    total_estimate = max(headings, field_markers, truth_fm, member_defs, wahr_yaml)
    return {
        "headings": headings,
        "field_aussage": aussage,
        "field_text": field_text,
        "truth_frontmatter": truth_fm,
        "member_defs": member_defs,
        "wahr_yaml": wahr_yaml,
        "total_estimate": total_estimate,
    }


def classify_format(text: str) -> str:
    """Format-Generation (Naeherung, nach dominantem Marker)."""
    if _TRUTH_FM.search(text):
        return "ZIEL_ATOMIC (type:truth)"
    if _FIELD_AUSSAGE.search(text):
        return "AUSSAGE-Feld (juengste)"
    if _FIELD_TEXT.search(text):
        return "TEXT-Feld (aeltere)"
    if _WAHRHEITEN_KEY.search(text):
        return "WAHRHEITEN_KNOTEN-yaml"
    if _WKNOT_HEADING.search(text):
        return "HEADING-only (aelteste)"
    return "KEIN-W-Signal"


def census_file(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    counts = count_wknots(text)
    has_signal = counts["total_estimate"] > 0 or _WAHRHEITEN_KEY.search(text)
    if not has_signal:
        return None
    return {"path": str(path), "counts": counts, "format": classify_format(text),
            "id_lexicon": sorted(set(_WID_TOKEN.findall(text)))[:8]}


def walk(vault: str, repo_models: str) -> list:
    out = []
    seen = set()
    for root in (Path(vault), Path(repo_models)):
        if not root.is_dir():
            continue
        for p in root.rglob("*.md"):
            if p in seen or not is_candidate(p):
                continue
            seen.add(p)
            rec = census_file(p)
            if rec:
                out.append(rec)
    return out


def build_report(records: list, vault: str, repo_models: str) -> tuple:
    total_files = len(records)
    total_knots = sum(r["counts"]["total_estimate"] for r in records)
    by_format = Counter(r["format"] for r in records)
    knots_by_format = Counter()
    for r in records:
        knots_by_format[r["format"]] += r["counts"]["total_estimate"]
    top = sorted(records, key=lambda r: r["counts"]["total_estimate"], reverse=True)[:15]
    id_variants = Counter()
    for r in records:
        for tok in r["id_lexicon"]:
            # ID-Lexikon-Form (W01 vs W-IST-1 vs W1) — grob nach Schema
            form = re.sub(r"\d+", "#", tok)
            id_variants[form] += 1

    lines = ["# Truth-Census (BL-309 PHASE-1.1, read-only) — 2026-06-16", ""]
    lines.append(f"**Vault:** `{vault}` · **Repo-Models:** `{repo_models}`")
    lines.append(f"**Model-Dateien mit W-Signal:** {total_files}")
    lines.append(f"**W-Knoten (Naeherungs-Nenner, max-Signal/Datei):** ~{total_knots}")
    lines.append("")
    lines.append("## Format-Generationen (Dateien / geschaetzte Knoten)")
    lines.append("| Format-Generation | Dateien | ~Knoten |")
    lines.append("|---|---|---|")
    for fmt, n in by_format.most_common():
        lines.append(f"| {fmt} | {n} | {knots_by_format[fmt]} |")
    lines.append("")
    lines.append(f"## ID-Lexikon-Varianten (Form-Proben, Top): {dict(id_variants.most_common(10))}")
    lines.append("")
    lines.append("## Top-15 Dateien nach Knoten-Zahl")
    lines.append("| ~Knoten | Format | Datei |")
    lines.append("|---|---|---|")
    for r in top:
        lines.append(f"| {r['counts']['total_estimate']} | {r['format']} | {r['path']} |")
    lines.append("")
    lines.append("## Caveats (Ehrlichkeit)")
    lines.append("- ERSTER-CUT: Naeherungs-Nenner (max der Einzel-Signale je Datei), kein feldweiser Roundtrip.")
    lines.append("- Die volle walker-unabhaengige Kardinalitaet (INV-MIG-1) + 6-Format-Feld-Synonym-Map kommt im BL-309-Vollbau.")
    lines.append("- Protokoll-/Snapshot-/Legacy-Dateien ausgeschlossen; archivierte Truths (D-Familie _Protokoll.md) ggf. noch nicht voll erfasst.")
    lines.append("- W-<TitleCaseWort>-Kollisionsklasse: '## W-Knoten' (benannter Ueberzaehler) ist jetzt ausgeschlossen, "
                 "ein RESTSCHWANZ derselben Klasse bleibt (z.B. 'W-Commands' als Section-Wort). Die regex-Heuristik wird "
                 "bewusst NICHT weiter verfeinert (first-cut) — der strukturelle Walker des BL-309-Vollbaus (INV-MIG-1) loest "
                 "ID-vs-Wort exakt auf statt zu raten. Restliche Ueberzaehlung daher klein, aber >0.")
    summary = (f"Truth-Census: {total_files} Model-Dateien mit W-Signal, ~{total_knots} W-Knoten, "
               f"{len(by_format)} Format-Generationen.")
    return "\n".join(lines) + "\n", summary


def main(argv) -> int:
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="BL-309 read-only Truth-Census")
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--repo-models", default=DEFAULT_REPO_MODELS)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv[1:])

    records = walk(args.vault, args.repo_models)
    report, summary = build_report(records, args.vault, args.repo_models)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
    if not args.quiet:
        print(report if not args.out else summary + f"\nReport -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
