#!/usr/bin/env python3
"""truth_normalize.py — Model-Vorab-Normalisierung (BL-397).

Drift-Erkenner + Korrektor: bringt ein driftetes Model (Bullet/Tabelle/Bold/bare/Range)
VOR der Atomisierung in die kanonische Format-A-Form (### W{n}-Headings + atomarer Body),
GENAU DANN wenn der Transform content-faithful ist (gleiche W-Definitionen per Census +
0 Content-Verlust). Der HEADING-Atomize-Pfad (truth_atomizer.atomize_model_file) liefert
dann format_hint=="HEADING" -> schlanke View statt SEGMENT-Verbatim-Fallback (Slimming).

GUARDED (CUTOVER-SAFE-1-Analogon): kein Persist ohne content_faithful. Backup nach
{legacy}/{stem}.pre_normalize.md (idempotent, DISJUNKT zu truth_cutover .pre_truth.md),
Rollback byte-identisch (INV-MIG-11-Muster).

Reuse (NICHT neu gebaut):
  truth_atomizer  — atomize_model_file/heading_adequate-Logik/_content_preserved/parse_model_headings
  truth_cutover   — backup-/rollback-Muster (eigener Suffix .pre_normalize.md)
  truth_census    — count_wknots/_WDEF_LINE (Census-Gleichheit, Drift-Distanz)
  truth_wid       — WDEF_LINE/_HEADING_LINE-Lexikon
  truth_gate_check— run_gates (Voll-Gruen-Beweis auf normalisiertem Model)

CLI: py -3 truth_normalize.py classify <model.md>  (read-only; exit 0)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import truth_atomizer as ta
import truth_census as tc
from truth_wid import WDEF_LINE, WID_BODY

_LEGACY_SUFFIX = ".pre_normalize.md"  # DISJUNKT zu truth_cutover _LEGACY_SUFFIX (.pre_truth.md)

# Heading-Form einer W-Definition (### W1 ...). Identisch zum atomizer-Lexikon-Praefix.
_HEADING_LINE = ta._HEADING_LINE

# Range-Heading (### W1-W3) -> Atomaritaets-Kollaps.
_RANGE_HEADING = ta._RANGE_HEADING

# Drift-Marker-Detektoren je W-Definitions-Zeile (Zeilenanfang).
_BULLET_DEF = re.compile(r"(?m)^[ \t]*[-*+][ \t]*(?:\*\*[ \t]*)?(" + WID_BODY + r")\b")
_TABLE_DEF = re.compile(r"(?m)^[ \t]*\|[ \t]*(?:\*\*[ \t]*)?(" + WID_BODY + r")\b")
_BOLD_DEF = re.compile(r"(?m)^[ \t]*\*\*[ \t]*(" + WID_BODY + r")\*\*")
_BARE_DEF = re.compile(r"(?m)^[ \t]*(" + WID_BODY + r")[ \t]*:")

_WS = re.compile(r"\s+")


# ──────────────────────────────────────────────────────────────────────────────
# AK-1: is_canonical_format
# ──────────────────────────────────────────────────────────────────────────────

def _heading_count(text: str) -> int:
    return len(_HEADING_LINE.findall(text))


def _census_total(text: str) -> int:
    return tc.count_wknots(text)["total_estimate"]


def is_canonical_format(text: str) -> tuple[bool, list[str]]:
    """AK-1: kanonisch <-> heading_adequate (HEADING-Atomize-Pfad). Returns (bool, [reasons]).

    Gruende (maschinen-lesbar): no_headings | census_undercover | content_not_preserved |
    range_collapsed. Konsistent mit atomize_model_file().format_hint=="HEADING" (DoD-1.2/1.4).
    """
    reasons: list[str] = []
    headings = _heading_count(text)
    census = _census_total(text)

    # Range-Heading: packt N Wahrheiten unter EINE Ueberschrift -> Atomaritaets-Verlust.
    if list(_RANGE_HEADING.finditer(text)):
        reasons.append("range_collapsed")

    if headings == 0:
        reasons.append("no_headings")
    elif headings < census:
        reasons.append("census_undercover")

    # Content-Erhalt: deckt die reine HEADING-View den Quell-Body verlustfrei (nur Whitespace)?
    src_body = ta._body_without_frontmatter(text).strip()
    knots_h = ta.atomize(text, "BL-397-canon")
    view_h = ta.build_model_view(knots_h) if knots_h else ""
    if src_body and not ta._content_preserved(view_h, src_body):
        reasons.append("content_not_preserved")

    ok = not reasons
    return ok, reasons


# ──────────────────────────────────────────────────────────────────────────────
# AK-2: classify_drift / classify_corpus
# ──────────────────────────────────────────────────────────────────────────────

def _segment_reason(text: str) -> dict:
    """3-teilige Aufschluesselung der heading_adequate-Bedingungen (DoD-2.3)."""
    headings = _heading_count(text)
    census = _census_total(text)
    src_body = ta._body_without_frontmatter(text).strip()
    knots_h = ta.atomize(text, "BL-397-seg")
    view_h = ta.build_model_view(knots_h) if knots_h else ""
    return {
        "no_headings": headings == 0,
        "census_undercover": headings < census,
        "content_not_preserved": bool(src_body) and not ta._content_preserved(view_h, src_body),
    }


def classify_drift(text: str) -> dict:
    """AK-2: {drift_type, distance, segment_reason}. distance = WDEF_LINE - _HEADING_LINE."""
    wdef = len(WDEF_LINE.findall(text))
    headings = _heading_count(text)
    distance = wdef - headings
    seg = _segment_reason(text)

    drift_type = _drift_type(text, headings, distance)

    return {"drift_type": drift_type, "distance": distance, "segment_reason": seg}


def _drift_type(text: str, headings: int, distance: int) -> str:
    """Dominanter Drift-Typ. Reihenfolge: Range-Heading > Format-Marker > heading_clean."""
    if list(_RANGE_HEADING.finditer(text)):
        return "range_heading"
    # Heading-Definitionen sauber abgedeckt + keine Range -> kanonisch.
    if distance <= 0 and headings > 0:
        # Pruefe Content-Erhalt: ein clean-Heading-Model ist heading_clean.
        ok, _ = is_canonical_format(text)
        if ok:
            return "heading_clean"
    # Drift-Marker zaehlen -> dominanter Marker bestimmt den Typ.
    counts = {
        "table": len(_TABLE_DEF.findall(text)),
        "bullet": len(_BULLET_DEF.findall(text)),
        "bold": len(_BOLD_DEF.findall(text)),
        "bare": len(_BARE_DEF.findall(text)),
    }
    # Prioritaet: table > bullet > bold > bare (spezifischer Marker zuerst).
    for typ in ("table", "bullet", "bold", "bare"):
        if counts[typ] > 0:
            return typ
    return "heading_clean" if headings > 0 else "bare"


def classify_corpus(texts: list[str]) -> dict:
    """AK-2 DoD-2.4: read-only Histogramm drift_type -> count."""
    hist: dict[str, int] = {}
    for t in texts:
        dt = classify_drift(t)["drift_type"]
        hist[dt] = hist.get(dt, 0) + 1
    return hist


# ──────────────────────────────────────────────────────────────────────────────
# AK-3/AK-4: normalize (Korrektor) — Drift -> kanonische Heading-Form
# ──────────────────────────────────────────────────────────────────────────────

def _split_def_rest(line: str, marker_re: re.Pattern) -> tuple[str, str] | None:
    """Zerlegt eine Drift-Def-Zeile in (local_id, rest_text). None wenn kein Match."""
    m = marker_re.match(line)
    if not m:
        return None
    lid = m.group(1)
    rest = line[m.end():]
    # Trenner nach der ID abraeumen: ':', '—', '-', '|', '**', Whitespace.
    rest = re.sub(r"^[ \t]*(?:\*\*)?[ \t]*[:\-–—|][ \t]*", " ", rest)
    rest = rest.replace("**", " ")
    rest = rest.strip(" \t|")
    return lid, rest


def _normalize_bullet_bold_bare(text: str, marker_re: re.Pattern) -> str | None:
    """Wandelt Bullet/Bold/bare-Def-Zeilen in ### W{n}-Headings + Body um."""
    lines = text.split("\n")
    out: list[str] = []
    converted = 0
    for line in lines:
        sd = _split_def_rest(line, marker_re)
        if sd is not None:
            lid, rest = sd
            out.append(f"### {lid}")
            if rest:
                out.append(rest)
            out.append("")
            converted += 1
        else:
            out.append(line)
    if converted == 0:
        return None
    return ("\n".join(out).rstrip("\n") + "\n")


def _normalize_table(text: str) -> str | None:
    """Wandelt Tabellen-Zellen (| W1 | Aussage |) in ### W{n}-Headings + Body um.
    Separator-Zeilen (|----|) + Header-Zeilen (ohne W-Id) werden gedroppt."""
    lines = text.split("\n")
    out: list[str] = []
    converted = 0
    for line in lines:
        stripped = line.strip()
        # Separator-Zeile (nur |, -, :, Whitespace) -> droppen.
        if stripped and set(stripped) <= set("|-: \t"):
            continue
        m = _TABLE_DEF.match(line)
        if m:
            lid = m.group(1)
            # Restliche Zellen nach der ID = der Body.
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # erste Zelle ist die ID; Rest ist Aussage.
            body = " ".join(c for c in cells[1:] if c)
            body = re.sub(r"^[ \t]*[:\-–—][ \t]*", "", body).strip()
            out.append(f"### {lid}")
            if body:
                out.append(body)
            out.append("")
            converted += 1
        else:
            # Header-Zeile (Tabellen-Kopf ohne W-Id) droppen, sonst behalten.
            if "|" in line and not m:
                continue
            out.append(line)
    if converted == 0:
        return None
    return ("\n".join(out).rstrip("\n") + "\n")


def _normalize_range(text: str) -> str | None:
    """Split eines Range-Headings (### W1-W3 + Member-Bullets) in den Bullet-Body.
    Ergebnis ist NICHT zwingend kanonisch (Member sind Bullets) -> multi-round konvergiert weiter."""
    out: list[str] = []
    changed = False
    lines = text.split("\n")
    for line in lines:
        if _RANGE_HEADING.match(line):
            changed = True
            continue  # Range-Heading droppen; die Member-Bullets darunter bleiben (-> Bullet-Drift)
        out.append(line)
    if not changed:
        return None
    return ("\n".join(out).rstrip("\n") + "\n")


def _one_round(text: str) -> str | None:
    """Ein Normalisierungs-Schritt nach Drift-Typ. None wenn kein Transform anwendbar."""
    dt = _drift_type(text, _heading_count(text), len(WDEF_LINE.findall(text)) - _heading_count(text))
    if dt == "range_heading":
        return _normalize_range(text)
    if dt == "table":
        return _normalize_table(text)
    if dt == "bullet":
        return _normalize_bullet_bold_bare(text, _BULLET_DEF)
    if dt == "bold":
        return _normalize_bullet_bold_bare(text, _BOLD_DEF)
    if dt == "bare":
        return _normalize_bullet_bold_bare(text, _BARE_DEF)
    return None


def _census_ids(text: str) -> set:
    """Distinkte W-Def-local_ids (Census-Gleichheits-Orakel, reuse truth_census._WDEF_LINE)."""
    return set(tc._WDEF_LINE.findall(text))


def _content_faithful(original: str, normalized: str) -> bool:
    """content-faithful: gleiche W-Def-Menge (census-gleich) + 0 Content-Verlust.

    Content-Erhalt: jede W-Id aus dem Original ist erhalten (keine verloren/erfunden) UND
    die normalisierte Form atomisiert zu format_hint=="HEADING" (schlanke View ohne Verlust).
    """
    if _census_ids(original) != _census_ids(normalized):
        return False
    ok, _ = is_canonical_format(normalized)
    return ok


def normalize_text(text: str) -> str | None:
    """AK-3 (in-mem): Drift -> kanonische Form. None wenn nicht content-faithful erzeugbar."""
    res = normalize_until_canonical(text)
    if res["status"] == "konvergiert" and _content_faithful(text, res["text"]):
        return res["text"]
    return None


def normalize_until_canonical(text: str, *, max_rounds: int = 5) -> dict:
    """AK-4: multi-round bis heading_adequate ODER 'nicht_normalisierbar' (harter Cap).

    Returns {status, rounds, reasons, text?}. status in {konvergiert, nicht_normalisierbar}.
    """
    current = text
    rounds = 0
    ok, reasons = is_canonical_format(current)
    if ok:
        return {"status": "konvergiert", "rounds": 0, "reasons": [], "text": current}

    while rounds < max_rounds:
        nxt = _one_round(current)
        rounds += 1
        if nxt is None or nxt == current:
            # kein Fortschritt mehr -> nicht normalisierbar
            _, reasons = is_canonical_format(current)
            return {"status": "nicht_normalisierbar", "rounds": rounds,
                    "reasons": reasons or ["no_transform"], "text": current}
        current = nxt
        ok, reasons = is_canonical_format(current)
        if ok:
            return {"status": "konvergiert", "rounds": rounds, "reasons": [], "text": current}

    # Cap erreicht ohne Konvergenz.
    _, reasons = is_canonical_format(current)
    return {"status": "nicht_normalisierbar", "rounds": rounds,
            "reasons": reasons or ["cap_reached"], "text": current}


def _legacy_path(model_path: Path, legacy_dir: Path) -> Path:
    return Path(legacy_dir) / (Path(model_path).stem + _LEGACY_SUFFIX)


def _backup(model_path: Path, legacy_dir: Path) -> Path:
    """Sichert das Original byte-genau -> {legacy}/{stem}.pre_normalize.md (idempotent)."""
    legacy_dir = Path(legacy_dir)
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy = _legacy_path(model_path, legacy_dir)
    if not legacy.exists():
        legacy.write_bytes(Path(model_path).read_bytes())
    return legacy


def normalize_model(model_path, *, legacy_dir=None) -> dict:
    """AK-3: normalisiert ein Model auf Platte. GUARDED: kein Persist ohne content_faithful.

    Returns {normalized, format_hint, content_faithful, legacy, reason?}.
    """
    model_path = Path(model_path)
    legacy_dir = Path(legacy_dir) if legacy_dir else (model_path.parent / "_legacy")
    original = model_path.read_text(encoding="utf-8", errors="replace")

    # Bereits kanonisch -> nichts zu tun (idempotent), aber Backup trotzdem sichern.
    ok, _ = is_canonical_format(original)
    if ok:
        legacy = _backup(model_path, legacy_dir)
        hint = ta.atomize_model_file(model_path, "BL-397-norm")["format_hint"]
        return {"normalized": False, "format_hint": hint, "content_faithful": True,
                "legacy": str(legacy), "reason": "already_canonical"}

    res = normalize_until_canonical(original)
    faithful = (res["status"] == "konvergiert"
                and _content_faithful(original, res.get("text", "")))

    if not faithful:
        # GUARDED: kein Write (CUTOVER-SAFE-1-Analogon).
        return {"normalized": False, "format_hint": None, "content_faithful": False,
                "legacy": None, "reason": res.get("reasons") and ", ".join(res["reasons"])
                or "not_content_faithful"}

    # content-faithful -> Backup + Write.
    legacy = _backup(model_path, legacy_dir)
    model_path.write_text(res["text"], encoding="utf-8")
    hint = ta.atomize_model_file(model_path, "BL-397-norm")["format_hint"]
    return {"normalized": True, "format_hint": hint, "content_faithful": True,
            "legacy": str(legacy)}


def rollback(model_path, legacy_dir) -> dict:
    """AK-3 DoD-3.5: stellt das Original BYTE-IDENTISCH aus .pre_normalize.md wieder her."""
    model_path = Path(model_path)
    legacy = _legacy_path(model_path, legacy_dir)
    if not legacy.exists():
        return {"restored": False, "reason": "no_legacy"}
    model_path.write_bytes(legacy.read_bytes())
    return {"restored": True}


# ──────────────────────────────────────────────────────────────────────────────
# AK-5: slimming_gain
# ──────────────────────────────────────────────────────────────────────────────

def slimming_gain(texts: list[str]) -> dict:
    """AK-5: HEADING-Anteil-Steigerung nach Normalisierung bei content-loss==0.

    Returns {heading_before, heading_after, gain, content_loss}.
    heading_before/after = Anzahl Models, die heading_adequate (kanonisch) sind.
    content_loss = Anzahl Models mit echtem Content-Verlust beim Transform.
    """
    before = 0
    after = 0
    content_loss = 0
    for t in texts:
        ok_before, _ = is_canonical_format(t)
        if ok_before:
            before += 1
            after += 1
            continue
        normalized = normalize_text(t)
        if normalized is None:
            continue
        ok_after, _ = is_canonical_format(normalized)
        if ok_after:
            after += 1
        # content-faithful by construction (normalize_text guarded) -> 0 Verlust.
        if _census_ids(t) != _census_ids(normalized):
            content_loss += 1
    return {"heading_before": before, "heading_after": after,
            "gain": after - before, "content_loss": content_loss}


# ──────────────────────────────────────────────────────────────────────────────
# AK-6: CLI (read-only classify)
# ──────────────────────────────────────────────────────────────────────────────

def main(argv) -> int:
    p = argparse.ArgumentParser(prog="truth_normalize",
                                description="BL-397 Model-Vorab-Normalisierung (Drift-Erkenner + Korrektor)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("classify", help="read-only Drift-Klassifikation eines Models")
    pc.add_argument("model", type=Path, help="Model.md")

    args = p.parse_args(argv)

    if args.cmd == "classify":
        if not args.model.is_file():
            print(f"ERROR: {args.model} nicht gefunden", file=sys.stderr)
            return 2
        text = args.model.read_text(encoding="utf-8", errors="replace")
        d = classify_drift(text)
        ok, reasons = is_canonical_format(text)
        print(f"Model: {args.model}")
        print(f"Drift-Typ: {d['drift_type']}  (distance={d['distance']})")
        print(f"Kanonisch: {ok}  Gruende: {reasons}")
        print(f"Segment-Reason: {d['segment_reason']}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
