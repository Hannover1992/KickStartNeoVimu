#!/usr/bin/env python3
"""
truth_atomizer.py — Der Migrations-Anstoss: Model -> atomare Wahrheiten (BL-309 Phase B).

Das ist `_atomize_orchestrate` in Code-Form. Pro Model:
  1. parse_model_headings  — alle W-Knoten extrahieren (HEADING-Format, ~97% per Census)
  2. atomize               — je Knoten ein type:truth-Dict (Schema-konform, content_hash)
  3. build_model_view      — generierte View aus den Wahrheiten (Rebuildability-LAW, BL-384)
  4. roundtrip_ok          — BEWEIS: parse(alt) == parse(View) feldweise + Heading byte-identisch
  5. write_truths          — truths/{local_id}.md schreiben (idempotent, Original UNBERUEHRT)

SICHERHEIT (BL-364-Fence): dieses Modul MUTIERT keine Live-Models. write_truths schreibt
NUR in ein Ziel-truths-Verzeichnis; der Cutover (Model.md -> View swap) ist NICHT hier
(Phase C, fresh Session). CLI ist default --check (Roundtrip-Beweis, kein Write).

Nicht-HEADING-Formate (AUSSAGE-/TEXT-Feld/yaml, ~3% per Census) liefern hier [] +
laute Warnung — der faithful Multi-Format-Extract ist Phase B2 (TODO, ehrlicher first-cut).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

try:
    import truth_schema
except ImportError:
    truth_schema = None  # type: ignore

try:
    import truth_census as _tc  # B2: census fuer die HEADING-vs-SEGMENT-Pfad-Entscheidung in atomize_model_file
except ImportError:
    _tc = None  # type: ignore

try:
    import truth_lifecycle as _tl
except ImportError:
    _tl = None  # type: ignore


def _default_lifecycle(status: str, grade: str) -> str:
    """Reife aus status/grade ableiten (BL-309 R2); Fallback asserted wenn Modul fehlt."""
    return _tl.map_lifecycle(status, grade)[0] if _tl else "asserted"


try:
    import truth_keywords as _tk
except ImportError:
    _tk = None  # type: ignore

# Vorwaerts-Kanten: W-Refs IM Text einer Wahrheit (= ihre ausgehenden Verbindungen).
# Zusammen mit dem Inverse-Index (referenced_by) = die bidirektionale Verbindung (User-Kern).
try:
    from truth_wid import WID_TOKEN as _WREF_IN_TEXT  # BL-395(c): EINE kanonische W-ID-Lexikon-Quelle (= _HEADING_LINE)
except ImportError:  # Fallback unifiziert mit _HEADING_LINE local_id-Body (inkl. '_'-Suffix -> W7_REF aufloesbar)
    _WREF_IN_TEXT = re.compile(r"\bW(?:\d+[A-Za-z0-9_]*|-(?!Knoten\b)[A-Z][A-Za-z0-9_-]*)\b")


def _keywords(text: str) -> list:
    """R3 thematische Schluesselwoerter (one-shot Capture; Suche=BL-389 spaeter)."""
    return _tk.extract_keywords(text) if _tk else []


def _forward_edges(text: str, self_id: str) -> list[dict]:
    """Forward-Edges aus W-Refs im Text (typisiert relates_to, Selbst-Ref ausgeschlossen)."""
    refs = sorted(set(_WREF_IN_TEXT.findall(text or "")))
    return [{"rel": "relates_to", "ziel": r} for r in refs if r != self_id]


try:
    import truth_typ as _tt
except ImportError:
    _tt = None  # type: ignore


def _typ(heading: str, text: str) -> str:
    """typ-Erkennung FRAGE/SOLL/FESTSTELLUNG (one-shot Capture); Fallback FESTSTELLUNG."""
    return _tt.detect_typ(heading, text) if _tt else "FESTSTELLUNG"

# Volle Heading-ZEILE (group 1, byte-verbatim) + local_id (group 2).
# Identisches W-Lexikon wie truth_census/truth_resolver (W+Ziffer | W-GROSS, NICHT W-Knoten).
_HEADING_LINE = re.compile(
    r"(?m)^(#{1,6}[ \t]+(W(?:\d+[A-Za-z0-9_]*|-(?!Knoten\b)[A-Z][A-Za-z0-9_-]*))\b[^\n]*)$"
)  # local_id: W01 | W12a | W7_REF | W-DERIV-1 (Suffix-tolerant; Census zaehlt W\d-Praefix -> hier auch)

# BL-391 (B) Range-Heading-Detektor: `### W16-W19` / `## W01–W07` packen N atomare Wahrheiten
# unter EINE Ueberschrift. Der HEADING-Parser oben extrahiert nur die ERSTE Nummer (W16) als
# local_id -> W17/W18/W19 werden NIE eigene Truths (Atomaritaets-Verlust). Dieses Span-Signal ist
# UNABHAENGIG vom Heading-Count -> es bricht den Lockstep-Unterzaehl (census==atomizer), an dem der
# Silent-Loss-Cross-Check strukturell blind ist. Hyphen + En-Dash (–) + Em-Dash (—).
_RANGE_HEADING = re.compile(r"(?m)^#{1,6}[ \t]+W(\d+)[ \t]*[-–—][ \t]*W(\d+)\b")
_RANGE_SPAN_CAP = 500  # pathologische Spans (Tippfehler) nicht enumerieren

# BL-391 (A): Member-Start-Zeile innerhalb eines Range-Bodys. Deckt die 3 realen Body-Formate ab:
#   "- W16: ..." (BL-050 Dash-Bullet)  ·  "W1: ..." (PrePR bare)  ·  "**W01**" (BL-111 Bold-Marker).
# Optionaler Bullet + optionales **; danach W<Ziffer>. Continuation-Zeilen (Quelle:/Typ:/Prosa) matchen NICHT
# (sie beginnen nicht mit W<Ziffer> am Zeilenanfang). Erster-Cut bewusst grob — der Verbatim-Gruppen-Knoten
# ist das verlustfreie Netz (Roundtrip), die Slice-Praezision ist eine verfeinerbare Enrichment-Dimension.
_MEMBER_LINE = re.compile(r"^[ \t]*(?:[-*+][ \t]+)?(?:\*\*)?[ \t]*(W\d+[A-Za-z0-9_]*)\b")

# B2 (faithful Multi-Format-Extract): Line-start W-DEFINITION in JEDEM Format (Heading/Bullet/Tabelle/bare/
# Bold) = Segment-Grenze. EINE kanonische Quelle (truth_wid.WDEF_LINE, == census._WDEF_LINE -> garantiert
# Segment-Zahl == census-Zahl). Fallback identisch.
try:
    from truth_wid import WDEF_LINE as _SEG_DEF
except ImportError:
    _SEG_DEF = re.compile(r"(?m)^[ \t]*(?:#{1,6}[ \t]+|[-*+|][ \t]*|\*\*[ \t]*)?(W(?:\d+[A-Za-z0-9_]*|-(?!Knoten\b)[A-Z][A-Za-z0-9_-]*))\b")

# Frontmatter-Feld-Reihenfolge (deterministisch => idempotenter Write).
# seq + view_mode (BL-395 Cutover-Wiring): nur SEGMENT-Truths tragen view_mode="verbatim";
# seq (Dokument-Position) tragen ALLE Truths -> die View ist aus dem truths/-Verzeichnis
# ordnungs-korrekt rebuildbar (BL-384 Rebuildability-LAW, disk-rebuild). Beide am Ende
# angehaengt -> die bestehende Feld-Reihenfolge der HEADING-Truths bleibt stabil. Das Schema
# (validate_truth) ist allowlist-tolerant -> Zusatzfelder erzeugen 0 Issues (kein Quarantaene-Risiko).
_FM_ORDER = [
    "type", "id", "local_id", "typ", "herkunft", "status", "status_verbatim",
    "truth_grade", "lifecycle", "maturity_evidence", "text", "original_heading",
    "derived_from", "content_hash", "keywords", "referenced_by", "source",
    "seq", "view_mode",
]


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_model_headings(text: str) -> list[dict]:
    """Extrahiert ALLE W-Knoten (HEADING-Format). Body = Text bis zum naechsten Heading.

    Returns [{local_id, original_heading (byte-verbatim Zeile), text}]. Leer, wenn keine
    W-Headings (dann ist es ein Nicht-HEADING-Format -> Phase B2).
    """
    matches = list(_HEADING_LINE.finditer(text))
    knots: list[dict] = []
    for i, m in enumerate(matches):
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip("\n").strip()
        knots.append({
            "local_id": m.group(2),
            "original_heading": m.group(1),
            "text": body,
        })
    return knots


def detect_range_collapses(text: str, extracted_local_ids=None) -> list[dict]:
    """BL-391 (B): findet Range-Headings (### W16-W19) + die implizierten W-Ids im Span.

    `extracted_local_ids` (die vom Atomizer tatsaechlich gewonnenen local_ids): nur implizierte
    Ids, die NICHT separat als eigene Wahrheit existieren, zaehlen als kollabiert (kein
    False-Positive, falls Sub-Ids doch eigene `### Wn`-Headings haben). Ohne Argument wird
    konservativ angenommen, dass nur die Start-Id gewonnen wurde (= was der HEADING-Parser tut).

    Returns: list[{heading, start_id, end_id, implied_count, collapsed_ids}] — nur Ranges mit
    echtem Kollaps (collapsed_ids != []). LAUT-Signal fuer Census/Gate/Readiness (PFLICHT vor --write).
    """
    extracted = set(extracted_local_ids) if extracted_local_ids is not None else None
    out: list[dict] = []
    for m in _RANGE_HEADING.finditer(text):
        start_s, end_s = m.group(1), m.group(2)
        start, end = int(start_s), int(end_s)
        if end <= start or (end - start) > _RANGE_SPAN_CAP:
            continue  # keine echte aufsteigende Range / pathologisch
        width = len(start_s)  # Null-Padding der Start-Id erhalten (W01-W07 -> W01..W07)
        implied = [f"W{n:0{width}d}" for n in range(start, end + 1)]
        start_id = f"W{start_s}"
        if extracted is None:
            collapsed = [i for i in implied if i != start_id]
        else:
            collapsed = [i for i in implied if i not in extracted]
        if collapsed:
            out.append({
                "heading": m.group(0).strip(),
                "start_id": start_id,
                "end_id": f"W{end_s}",
                "implied_count": len(implied),
                "collapsed_ids": collapsed,
            })
    return out


def _slice_range_body(body: str, implied_ids: list[str]) -> dict:
    """BL-391 (A): zerlegt den Body eines Range-Headings in Member-Slices {Wn: text}.

    Ein Member beginnt an der ersten Zeile, die (nach optionalem Bullet/`**`) mit der Member-Id
    startet (nur Ids aus `implied_ids` zaehlen); er reicht bis zur naechsten Member-Start-Zeile.
    Continuation-Zeilen (eingerueckte `Quelle:`/`Typ:`/Prosa) gehoeren zum vorausgehenden Member.
    Erster-Cut (verbatim Gruppen-Knoten ist das Netz): unbekanntes Format -> Member ohne Slice ("").
    """
    id_set = set(implied_ids)
    lines = body.split("\n")
    starts: list[tuple] = []
    for i, line in enumerate(lines):
        m = _MEMBER_LINE.match(line)
        if m and m.group(1) in id_set:
            starts.append((i, m.group(1)))
    slices: dict = {}
    for k, (li, wid) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        if wid not in slices:  # erstes Vorkommnis gewinnt
            slices[wid] = "\n".join(lines[li:end]).strip()
    return slices


def atomize(text: str, namespace: str) -> list[dict]:
    """Model-Text -> Liste von type:truth-Dicts. Legacy-HEADING hat kein typ/herkunft/status
    -> konservative Defaults (UNGRADED/vault_hypothesis), die das Phase-2-HiL-Gate verfeinert.
    Die Roundtrip-relevanten Felder (original_heading, text) sind verlustfrei."""
    truths: list[dict] = []
    seen: dict[str, int] = {}  # wiederholte Headings (Multi-Sektion-Model) verlustfrei disambiguieren
    for k in parse_model_headings(text):
        lid = k["local_id"]
        seen[lid] = seen.get(lid, 0) + 1
        if seen[lid] > 1:
            lid = f"{lid}~{seen[lid]}"  # 2. "### W1" -> W1~2 (kein Overwrite-Verlust; INV-MIG-10)
        t = {
            "type": "truth",
            "id": f"{namespace}.{lid}",
            "local_id": lid,
            "typ": _typ(k["original_heading"], k["text"]),  # FRAGE/SOLL/FESTSTELLUNG (one-shot Capture)
            "herkunft": "INTERN",
            "status": "UNGRADED",          # statuslos-Legacy-Default (Konzept-Doc)
            "truth_grade": "vault_hypothesis",
            "lifecycle": _default_lifecycle("UNGRADED", "vault_hypothesis"),  # R2-Ableitung; reift via SC/BL-325
            "text": k["text"],
            "original_heading": k["original_heading"],  # byte-verbatim (Roundtrip parst DIES, nicht local_id)
            "content_hash": _sha256(k["text"]),
        }
        kw = _keywords(k["text"])               # R3 (one-shot Capture; Suche-Index = BL-389)
        if kw:
            t["keywords"] = kw
        fe = _forward_edges(k["text"], lid)     # Forward-Edges (bidirektional mit referenced_by)
        if fe:
            t["edges"] = fe
        truths.append(t)

    # ── BL-391 (A): Range-Heading-Member-Atomisierung ──
    # Der Range-Heading (### W16-W19) wurde oben als EIN view-tragender Gruppen-Knoten (start_id W16,
    # verbatim Body) extrahiert -> Roundtrip unveraendert. Hier ergaenzen wir die KOLLABIERTEN Member
    # (W17/W18/W19) als atomare Kind-Wahrheiten: enrichment, derived_from=Gruppe, NICHT view-bearing
    # (build_model_view skippt sie). Damit sieht detect_range_collapses sie in extracted_local_ids ->
    # (B)-Gate cleart + GO=TRUE; und kein Byte geht verloren (die Gruppe haelt den Verbatim-Body).
    knot_by_lid = {t["local_id"]: t for t in truths}
    for rc in detect_range_collapses(text):
        group = knot_by_lid.get(rc["start_id"])
        if group is None:
            continue  # kein Gruppen-Body zum Slicen -> Gate bleibt laut (sichtbar), kein stiller Kind-Stub
        start_n, end_n = int(rc["start_id"][1:]), int(rc["end_id"][1:])
        width = len(rc["start_id"]) - 1
        implied = [f"W{n:0{width}d}" for n in range(start_n, end_n + 1)]
        slices = _slice_range_body(group["text"], implied)
        for cid in rc["collapsed_ids"]:
            seen[cid] = seen.get(cid, 0) + 1
            lid = cid if seen[cid] == 1 else f"{cid}~{seen[cid]}"  # reale ### Wn (falls vorhanden) gewann oben
            slice_text = slices.get(cid, "")
            child_heading = f"### {lid}"
            child = {
                "type": "truth",
                "id": f"{namespace}.{lid}",
                "local_id": lid,
                "typ": _typ(child_heading, slice_text),
                "herkunft": "INTERN",
                "status": "UNGRADED",
                "truth_grade": "vault_hypothesis",
                "lifecycle": _default_lifecycle("UNGRADED", "vault_hypothesis"),
                "text": slice_text,
                "original_heading": child_heading,
                "derived_from": group["local_id"],
                "content_hash": _sha256(slice_text),
            }
            ckw = _keywords(slice_text)
            if ckw:
                child["keywords"] = ckw
            cfe = _forward_edges(slice_text, lid)
            if cfe:
                child["edges"] = cfe
            truths.append(child)

    # BL-384 disk-rebuild: Dokument-Position persistieren -> rebuild_view_from_truths_dir
    # rekonstruiert die View aus den geschriebenen Dateien in korrekter Reihenfolge (Glob ist
    # alphabetisch, nicht doc-order). View-tragende Knoten kommen zuerst (doc-order), derived
    # Kinder danach (in build_model_view ohnehin uebersprungen) -> seq der View-Knoten = doc-order.
    for i, t in enumerate(truths):
        t["seq"] = i
    return truths


def parse_truth_segments(text: str):
    """B2: partitioniert den Text an W-DEFINITIONS-Zeilenanfaengen (_SEG_DEF == truth_wid.WDEF_LINE,
    format-agnostisch: Heading/Bullet/Tabelle/bare/Bold) in (preamble, segments). Jedes Segment ist der
    VERBATIM-Span von der Def-Zeile bis zur naechsten. KERN-INVARIANTE: preamble + concat(seg.verbatim)
    == text byte-identisch (echte Partition, kein Byte verloren)."""
    starts = [(m.start(), m.group(1)) for m in _SEG_DEF.finditer(text)]
    if not starts:
        return text, []
    preamble = text[:starts[0][0]]
    segs: list[dict] = []
    for i, (pos, lid) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        segs.append({"local_id": lid, "verbatim": text[pos:end]})
    return preamble, segs


def atomize_segments(text: str, namespace: str) -> list[dict]:
    """B2 (faithful Multi-Format-Extract): 1 atomare Wahrheit pro W-Definition, format-agnostisch
    (Heading/Bullet/Tabelle/bare/Bold). Fuer Models, die der HEADING-Parser unterdeckt (die BL-395-
    Quarantaene: pure-nonheading/mixed/yaml). build_segment_view = concat(_verbatim) == Source byte-
    identisch -> Byte-Coverage 1.0, kein Silent-Loss. Die 155 HEADING-ready-Models bleiben auf dem
    UNVERAENDERTEN HEADING-Pfad (atomize) — dieser Pfad greift nur im Fallback."""
    preamble, segs = parse_truth_segments(text)
    truths: list[dict] = []
    seen: dict[str, int] = {}
    for idx, seg in enumerate(segs):
        base = seg["local_id"]
        seen[base] = seen.get(base, 0) + 1
        lid = base if seen[base] == 1 else f"{base}~{seen[base]}"  # verlustfreie Disambiguierung (INV-MIG-10)
        verbatim = seg["verbatim"]
        def_line = verbatim.split("\n", 1)[0]
        is_heading = bool(re.match(r"^[ \t]*#{1,6}[ \t]", def_line))
        if is_heading:
            body_after = verbatim.split("\n", 1)[1] if "\n" in verbatim else ""
            text_field = body_after.strip() or verbatim.strip()  # leer-Body-Heading (Range-Gruppe) -> Def-Zeile
        else:
            text_field = verbatim.strip()                        # Bullet/Tabelle/bare: die Zeile(n) SIND der Inhalt
        # 1. Segment traegt die Praeambel (inkl. Frontmatter) in _verbatim -> concat == Source byte-identisch.
        vb = (preamble + verbatim) if idx == 0 else verbatim
        t = {
            "type": "truth",
            "id": f"{namespace}.{lid}",
            "local_id": lid,
            "typ": _typ(def_line, text_field),
            "herkunft": "INTERN",
            "status": "UNGRADED",
            "truth_grade": "vault_hypothesis",
            "lifecycle": _default_lifecycle("UNGRADED", "vault_hypothesis"),
            "text": text_field,
            "original_heading": def_line,
            "_verbatim": vb,                                     # Body der Truth-Datei (View-Rekonstruktion, BL-384)
            "seq": idx,                                          # Dokument-Position -> ordnungs-korrekter disk-rebuild
            "view_mode": "verbatim",                             # Marker: View = concat(_verbatim), nicht heading+text
            "content_hash": _sha256(text_field),
        }
        kw = _keywords(text_field)
        if kw:
            t["keywords"] = kw
        fe = _forward_edges(text_field, lid)
        if fe:
            t["edges"] = fe
        truths.append(t)
    return truths


def build_segment_view(truths: list[dict]) -> str:
    """B2-View: exakte Rekonstruktion = concat(_verbatim). Byte-identisch zum Original (Partition)."""
    return "".join(t.get("_verbatim", "") for t in truths)


def _census_estimate(text: str) -> int:
    """B2-Pfad-Entscheidung: census-Schaetzung (W-Definitionen) ueber truth_census; Fallback = Heading-Zahl."""
    if _tc is not None:
        return _tc.count_wknots(text)["total_estimate"]
    return len(parse_model_headings(text))


def build_model_view(truths: list[dict]) -> str:
    """Generierte View aus Wahrheiten (Rebuildability-LAW). Heading-Zeile byte-verbatim + Body.

    BL-391 (A): derived_from-getaggte Range-Member-Kinder sind ENRICHMENT, nicht view-bearing —
    sie werden uebersprungen, damit parse(View) == parse(Original) byte-identisch bleibt (Roundtrip)."""
    parts: list[str] = []
    for t in truths:
        if t.get("derived_from"):
            continue
        parts.append(t["original_heading"])
        if t.get("text"):
            parts.append("")
            parts.append(t["text"])
        parts.append("")
    return "\n".join(parts).rstrip("\n") + "\n"


def _knot_key(knots: list[dict]) -> list[tuple]:
    return [(k["local_id"], k["original_heading"], k["text"]) for k in knots]


def roundtrip_ok(original_text: str, truths: list[dict]) -> bool:
    """INV-MIG-2/3-BEWEIS: parse(alt) == parse(generierte View) feldweise + Heading byte-identisch."""
    view = build_model_view(truths)
    return _knot_key(parse_model_headings(original_text)) == _knot_key(parse_model_headings(view))


def truth_to_md(t: dict) -> str:
    """type:truth-Dict -> Markdown-Datei-Inhalt (Frontmatter deterministisch sortiert = idempotent).

    HEADING-Truth: Body = original_heading (kosmetisch; die Daten liegen im Frontmatter).
    SEGMENT-Truth (view_mode==verbatim): Body = EXAKTE _verbatim-Bytes — ohne Zusatz-Whitespace, denn
    concat(Body) ueber alle Segmente eines Models == Quelle byte-identisch (BL-384 disk-rebuild)."""
    fm = {k: t[k] for k in _FM_ORDER if k in t and t[k] is not None}
    if yaml is not None:
        dumped = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    else:  # Minimal-Fallback
        dumped = "".join(f"{k}: {v}\n" for k, v in fm.items())
    if "_verbatim" in t:  # SEGMENT-Truth -> Body = exakte Verbatim-Bytes (kein \n\n-Wrapper)
        return f"---\n{dumped}---\n{t['_verbatim']}"
    return f"---\n{dumped}---\n\n{t['original_heading']}\n"


def write_truths(truths: list[dict], truths_dir: Path) -> dict:
    """Schreibt truths/{local_id}.md. Idempotent: identischer Inhalt -> Skip (0 Diff).
    Original-Model wird NICHT angefasst (Phase-B-Garantie)."""
    truths_dir = Path(truths_dir)
    truths_dir.mkdir(parents=True, exist_ok=True)
    written, skipped = 0, 0
    for t in truths:
        target = truths_dir / f"{t['local_id']}.md"
        content = truth_to_md(t)
        if target.is_file() and target.read_text(encoding="utf-8") == content:
            skipped += 1
            continue
        target.write_text(content, encoding="utf-8")
        written += 1
    return {"written": written, "skipped": skipped, "total": len(truths)}


def _split_truth_file(content: str) -> tuple[str, str]:
    """Geschriebenes Truth-File -> (frontmatter_text, body). body = exakte Bytes nach der schliessenden
    Frontmatter-Fence (`\\n---\\n`); fuer view_mode==verbatim IST body das _verbatim. Gleiche Fence-Konvention
    wie truth_resolver._read_frontmatter (find ab Index 3 -> die Open-Fence wird nicht mitgematcht)."""
    if not content.startswith("---\n"):
        return "", content
    idx = content.find("\n---\n", 3)
    if idx == -1:
        return "", content
    return content[4:idx], content[idx + 5:]


def read_truth_file(path: Path) -> dict:
    """Liest eine geschriebene Truth-Datei zurueck zu einem Dict (Frontmatter + ggf. _verbatim-Body).
    Umkehrung von truth_to_md fuer den disk-rebuild (BL-384)."""
    content = Path(path).read_text(encoding="utf-8")
    fm_text, body = _split_truth_file(content)
    fm: dict = {}
    if fm_text:
        if yaml is not None:
            try:
                loaded = yaml.safe_load(fm_text)
                fm = loaded if isinstance(loaded, dict) else {}
            except yaml.YAMLError:
                fm = {}
        else:
            for line in fm_text.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip()
    if fm.get("view_mode") == "verbatim":
        fm["_verbatim"] = body
    return fm


def rebuild_view_from_truths_dir(truths_dir: Path) -> str:
    """BL-384 Rebuildability-LAW: rekonstruiert die Model-View AUS DEN GESCHRIEBENEN Truth-Dateien
    (nicht aus In-Memory-Truths) -> beweist, dass truths/ selbst-genuegsam ist. SEGMENT-Model
    (irgendeine Truth view_mode==verbatim): concat(_verbatim) in seq-Reihenfolge == Quelle byte-identisch.
    HEADING-Model: build_model_view auf den nach seq sortierten Truths."""
    truths = [read_truth_file(p) for p in sorted(Path(truths_dir).glob("*.md"))]
    truths.sort(key=lambda t: t.get("seq", 0))
    if any(t.get("view_mode") == "verbatim" for t in truths):
        return build_segment_view(truths)
    return build_model_view(truths)


# BL-395 (b): die generierte View muss >=_COVERAGE_FLOOR des Quell-Bodys (ohne Frontmatter) rekonstruieren,
# sonst droht INHALTS-Verlust beim Cutover (die View ERSETZT das Model — BL-384). Unabhaengig vom parse-
# basierten Roundtrip, der nur Parser-Selbstkonsistenz prueft (View-aus-Headings vs Original-Headings),
# NICHT Byte-Erhalt: ein reines Bullet-Model parst beidseitig zu 0 Headings -> roundtrip GRUEN, View=leer.
_COVERAGE_FLOOR = 0.5
_FM_BLOCK = re.compile(r"\A---\n.*?\n---\n?", re.S)
_WS = re.compile(r"\s+")


def _body_without_frontmatter(text: str) -> str:
    """Quell-Body ohne YAML-Frontmatter (Metadaten, kein Wahrheits-Inhalt) — Coverage-Nenner."""
    m = _FM_BLOCK.match(text)
    return text[m.end():] if m else text


def _content_preserved(view: str, src_body: str) -> bool:
    """BL-396: verliert die HEADING-View NUR Whitespace (= ok, kanonische Reformatierung) oder echten
    Content? Whitespace-normalisierter Vergleich: gleich -> kein Content-Verlust (HEADING-Pfad sicher,
    schlanke View); ungleich -> die View droppt Real-Content (Preamble vor dem 1. W-Heading / Nicht-W-
    Sektion) -> NICHT adequat -> Fallback SEGMENT-Pfad (byte-identisch). Praeziser als der 0.5-Byte-Floor,
    der bis ~48% Real-Verlust durchliess (OmniCommandUltraThink 3228B Preamble, census+roundtrip blind)."""
    return _WS.sub("", view) == _WS.sub("", src_body)


def atomize_model_file(model_path: Path, namespace: str) -> dict:
    """Liest ein Model, atomisiert + prueft Roundtrip/Schema/Byte-Coverage. KEIN Write.
    B2 Zwei-Pfad: HEADING-Pfad zuerst (155 ready-Models + Range-(A), UNVERAENDERT). Deckt er den Korpus
    NICHT (knots<census ODER low-coverage = die BL-395-Quarantaene), faellt er auf den SEGMENT-Pfad
    (atomize_segments, View==Source byte-identisch) -> recovert die Nicht-HEADING-Models verlustfrei."""
    text = Path(model_path).read_text(encoding="utf-8", errors="replace")
    src_body = _body_without_frontmatter(text).strip()
    census = _census_estimate(text)

    truths_h = atomize(text, namespace)                                   # HEADING-Pfad (clean-Heading + Range-(A))
    view_h = build_model_view(truths_h) if truths_h else ""
    cov_h = (len(view_h.strip()) / len(src_body)) if src_body else 1.0
    # BL-396: HEADING-Pfad NUR adequat wenn er CONTENT-verlustfrei ist (nur Whitespace-Reformatierung).
    # Sonst -> SEGMENT-Pfad (byte-identisch), der die Preamble/Nicht-W-Sektion erhaelt. Loest den
    # Preamble-Silent-Loss, den der 0.5-Byte-Floor durchliess (census==atomizer + roundtrip waren blind).
    heading_adequate = (bool(truths_h) and len(truths_h) >= census
                        and _content_preserved(view_h, src_body))

    if heading_adequate:
        truths, view, rt, path = truths_h, build_model_view(truths_h), roundtrip_ok(text, truths_h), "HEADING"
    else:
        truths = atomize_segments(text, namespace)                        # B2 SEGMENT-Pfad (Recovery)
        view = build_segment_view(truths)
        rt = (view == text)                                               # byte-identisch (Partition-Beweis)
        path = "SEGMENT-B2" if truths else "LEER (kein W-Signal)"

    schema_issues = 0
    if truth_schema is not None:
        for t in truths:
            schema_issues += sum(1 for s, _ in truth_schema.validate_truth(t) if s == "ERROR")
    coverage = (len(view.strip()) / len(src_body)) if src_body else 1.0
    return {
        "model": str(model_path),
        "knots": len(truths),
        "roundtrip_ok": rt,
        "schema_errors": schema_issues,
        "coverage": round(coverage, 4),
        "low_coverage": coverage < _COVERAGE_FLOOR,
        "format_hint": path,
        "truths": truths,
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="truth_atomizer", description="BL-309 Phase B: Model -> atomare Wahrheiten")
    p.add_argument("model", type=Path, help="Model.md")
    p.add_argument("--namespace", required=True, help="BL-SLUG (z.B. BL-309-truth-migration)")
    p.add_argument("--write", action="store_true", help="truths/ schreiben (sonst nur Roundtrip-CHECK)")
    p.add_argument("--out", type=Path, default=None, help="Ziel-truths-Verzeichnis (default {model_dir}/truths)")
    args = p.parse_args(argv)

    if not args.model.is_file():
        print(f"ERROR: {args.model} nicht gefunden", file=sys.stderr)
        return 2

    res = atomize_model_file(args.model, args.namespace)
    print(f"Model: {res['model']}")
    print(f"Knoten: {res['knots']} ({res['format_hint']})")
    print(f"Roundtrip-Beweis: {'OK' if res['roundtrip_ok'] else 'FAIL'}")
    print(f"Schema-Errors: {res['schema_errors']}")

    if not res["roundtrip_ok"] or res["schema_errors"]:
        print("ABBRUCH: kein Write (Roundtrip/Schema nicht sauber).", file=sys.stderr)
        return 1
    if args.write:
        out = args.out or (args.model.parent / "truths")
        stats = write_truths(res["truths"], out)
        print(f"Geschrieben: {stats}")
    else:
        print("[CHECK-only] kein Write (--write fuer echtes Schreiben).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
