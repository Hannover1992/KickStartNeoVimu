"""build_retrieval_index.py — BL-242 / batch_1 / Stage 1 (Atomic)

Pre-computed Read-Index Builder — die ungebaute Index-Haelfte von BL-161.
7 atomare, isoliert unit-testbare reine Funktionen (Laserpointer-Inseln H1-H7).

Stage-1 Mock-Grenze (stage_1.md): KEIN reales Vault-File-IO. Jede Insel ist eine
reine Funktion (parsed_nodes / wikilinks / files als Argument). Realer Vault-Walk +
Artefakt-Schreiben = Stage 3.

H1 (AK-CTX-3): Reuse-Substrat / Import-Disziplin (DRY, PT-GEN-LeadFollow).
  Die 3 Lead-Parser werden per IDENTITAET gebunden (Re-Use, kein Re-Implement) —
  dieses Modul kompiliert KEIN eigenes Muster und parst KEINE Knoten-Metadaten selbst.
"""

# --- H1 (AK-CTX-3): Lead-Parser per Identitaet re-exportieren (DRY, kein eigenes Muster) ---
from quality_node_health import parse_frontmatter  # noqa: F401
from quality_tag_cluster import extract_tags
from quality_edge_health import extract_wikilinks  # noqa: F401


# --- H7 (AK-3): Coverage-Report-Counter (Report-only, No-Side-Effect) ---
def compute_coverage(files):
    """Report {total, with_keywords, missing, pct} ueber die keyword-Abdeckung.

    Report-only (A6/SOA-2): mutiert die Eingabe nicht. total==0 -> pct=0.0 (Guard).
    """
    total = len(files)
    missing = [f["path"] for f in files if not f.get("keywords")]
    with_keywords = total - len(missing)
    pct = round(with_keywords / total * 100, 1) if total else 0.0
    return {
        "total": total,
        "with_keywords": with_keywords,
        "missing": missing,
        "pct": pct,
    }


# --- H2 (AK-1): build_keyword_index ---
def build_keyword_index(parsed_nodes):
    """Je Keyword die referenzierenden Knoten ({path, bl_id, vault_origin, node_type})."""
    idx = {}
    for node in parsed_nodes:
        for kw in node.get("keywords") or []:
            idx.setdefault(kw, []).append({
                "path": node.get("path"),
                "bl_id": node.get("bl_id"),
                "vault_origin": node.get("vault_origin"),
                "node_type": node.get("node_type"),
            })
    return idx


# --- H3 (AK-1): build_edge_index ---
def build_edge_index(parsed_nodes):
    """Frontmatter-edges nach Quell-Knoten ({target, edge_type, path})."""
    idx = {}
    for node in parsed_nodes:
        edges = node.get("edges")
        if not edges:
            continue
        src = node.get("path")
        idx[src] = []
        for e in edges:
            target = e.get("target")
            if target is None:
                target = e.get("ziel")
            edge_type = e.get("edge_type")
            if edge_type is None:
                edge_type = e.get("rel")
            idx[src].append({"target": target, "edge_type": edge_type, "path": src})
    return idx


# --- H4 (AK-1): build_tag_index (via extract_tags Lead, lowercase) ---
def build_tag_index(parsed_nodes):
    """Je Tag die Files ({path, vault_origin}); Tags via extract_tags (Lead)."""
    idx = {}
    for node in parsed_nodes:
        for tag in extract_tags(node.get("frontmatter") or {}):
            idx.setdefault(tag, []).append({
                "path": node.get("path"),
                "vault_origin": node.get("vault_origin"),
            })
    return idx


# --- H5 (AK-1): build_anchor_index (Score bc*0.6 + fw*0.4, BL-161 AK-2.3) ---
def build_anchor_index(nodes, wikilinks):
    """Score == round(backlink_count*0.6 + frontmatter_weight*0.4) je Knoten."""
    backlink_count = {}
    for link in wikilinks:
        tgt = link.get("target")
        backlink_count[tgt] = backlink_count.get(tgt, 0) + 1
    idx = {}
    for node in nodes:
        path = node.get("path")
        bc = backlink_count.get(path, 0)
        fw = node.get("frontmatter_weight", 0)
        idx[path] = {"score": round(bc * 0.6 + fw * 0.4)}
    return idx


# --- H6 (AK-1): build_backlinks ({referenced_by, references}, BL-161 AK-3.1) ---
def build_backlinks(nodes, wikilinks):
    """Schema {path: {referenced_by, references}} + bidirektionale Konsistenz."""
    idx = {node.get("path"): {"referenced_by": [], "references": []} for node in nodes}
    for link in wikilinks:
        src = link.get("source")
        tgt = link.get("target")
        if src in idx:
            idx[src]["references"].append(tgt)
        if tgt in idx:
            idx[tgt]["referenced_by"].append(src)
    return idx


# ===========================================================================
# batch_2 — H8-H11: Cross-Vault-Merge / Tag-Materializer / Praezisions-Query /
# Incremental-Patch. Reine Funktionen (Stage-1 Mock-Grenze: KEIN reales
# Vault-File-IO, KEINE vault-routing.json-Resolution, KEIN realer 2-Vault-Walk,
# KEIN realer grep). Verdrahtung = Stage 3.
# ===========================================================================


# --- H8 (AK-CTX-1): merge_vault_indexes (Cross-Vault, vault_origin, SOA-1) ---
def merge_vault_indexes(index_a, index_b):
    """Mergt zwei pro-Vault Index-Dicts in einen Cross-Vault-Index.

    Gleicher Key in beiden Vaults -> Eintragslisten konkateniert; jeder Eintrag
    traegt sein (im Fixture bereits gesetztes) vault_origin. index_b is None/leer
    -> graceful Pass-through von index_a (Single-Vault, SOA-1).
    """
    if not index_b:
        return index_a
    merged = {key: list(entries) for key, entries in index_a.items()}
    for key, entries in index_b.items():
        merged[key] = merged.get(key, []) + list(entries)
    return merged


# --- H9 (AK-2): render_tag_index_md (reiner Markdown-String, kein File-IO) ---
def render_tag_index_md(tag_index):
    """Rendert das tag_index-Dict als _Tag-Index.md-Markdown-STRING.

    Pro Tag eine Sektion (deterministisch sortiert) mit allen referenzierenden
    File-Pfaden. Reine str-Rueckgabe -- KEIN open()/write() (Datei-Schreiben =
    Stage 3).
    """
    lines = ["# Tag-Index", ""]
    for tag in sorted(tag_index):
        lines.append("## {}".format(tag))
        for entry in tag_index[tag]:
            lines.append("- {}".format(entry.get("path")))
        lines.append("")
    return "\n".join(lines)


# --- H10 (AK-4): query (Praezisions-Graph-Walk, thematisch statt grep) ---
def query(term, keyword_index, edge_index):
    """Gerichteter Graph-Walk: Treffer aus keyword_index[term] + Edge-Nachbarn.

    Liefert NUR thematische Knoten (kein Fliesstext-Rauschen wie grep). Term ohne
    Treffer -> []. Keyword-Treffer als dict (mit path), Edge-Nachbarn als
    target-Pfad-String.
    """
    term_entries = keyword_index.get(term) or []
    hits = list(term_entries)
    for entry in term_entries:
        src = entry.get("path")
        for edge in edge_index.get(src) or []:
            target = edge.get("target")
            if target is not None:
                hits.append(target)
    return hits


# --- H11 (AK-6): patch_index (inkrementell, nur path-Eintraege) ---
def patch_index(index, path, new_entries):
    """Inkrementeller Patch: ersetzt NUR die Eintraege die `path` referenzieren.

    Pro Key werden Eintraege mit entry["path"] == path entfernt, dann die
    new_entries[key] eingefuegt. Keys/Eintraege ohne `path`-Bezug bleiben
    bit-identisch (frische Dict-Kopie, keine Eingabe-Mutation).
    """
    new_entries = new_entries or {}
    patched = {}
    for key, entries in index.items():
        kept = [e for e in entries if e.get("path") != path]
        patched[key] = kept + list(new_entries.get(key) or [])
    return patched


# ===========================================================================
# batch_2 — Stage 3 (Scheinwerfer / Integration, mocks_erlaubt=nein):
# CLI-Haut main(argv) + build_index()-Orchestrator. Verdrahtet die reinen
# Stage-1-Fn (H8-H11) zum echten technischen Durchstich: reale
# resolve_vault_root-Resolution -> realer .md-Walk via Lead-Parser ->
# merge_vault_indexes -> reales {VAULT}/_Tag-Index.md-File-Write.
# Minimal-Impl (TDD GREEN): die 4 reinen Fn werden UNVERAENDERT aufgerufen.
# ===========================================================================

import argparse  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402

# Lead-Parser (DRY, PT-GEN-LeadFollow): kein eigenes Frontmatter/Tag/Link-Parsing.
from quality_node_health import parse_frontmatter  # noqa: E402,F811
from resolve_vault_root import resolve_vault_root  # noqa: E402


def _extract_block_sequence(content, key):
    """Fallback: extract a YAML block-sequence (list of dicts) from raw frontmatter.

    parse_frontmatter (Lead) handles only inline lists; block sequences like
        edges:
        - rel: relates_to
          ziel: NS.B1
    are not parsed. This helper fills that gap for the 'edges' key WITHOUT
    touching the Lead parser (DRY-principle preserved: Lead stays unchanged).
    Pure string operations only — no re.* calls (AK-CTX-3 / DRY guard).
    Returns [] when key not found or value is not a block sequence.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)

    # Locate `key:` line with no trailing value (block sequence marker)
    key_prefix = key + ":"
    start = None
    for idx, line in enumerate(fm_lines):
        if line.rstrip() == key_prefix or line.rstrip() == key_prefix + " ":
            start = idx + 1
            break
    if start is None:
        return []

    # Collect block-sequence dicts  (- field: val  /  continuation: val)
    items = []
    current = None
    for line in fm_lines[start:]:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith("- ") and ":" in stripped:
            # New dict item: `- fieldname: value`
            if current is not None:
                items.append(current)
            field_part = stripped[2:]  # strip "- "
            colon_pos = field_part.index(":")
            field_key = field_part[:colon_pos].strip()
            field_val = field_part[colon_pos + 1:].strip()
            current = {field_key: field_val}
        elif indent >= 2 and current is not None and ":" in stripped:
            # Continuation field: `  fieldname: value`
            colon_pos = stripped.index(":")
            field_key = stripped[:colon_pos].strip()
            field_val = stripped[colon_pos + 1:].strip()
            current[field_key] = field_val
        else:
            # Non-block line ends the sequence
            break
    if current is not None:
        items.append(current)
    return items


def _walk_vault_nodes(root):
    """Realer .md-Walk eines Vault-Roots -> Liste paritaeter Knoten-Dicts.

    Jeder Knoten traegt vault_origin == root. parse_frontmatter (Lead) liefert
    keywords/tags/node_type; raw_tags bleibt im Original-Case (J9-Render).
    _Tag-Index.md selbst wird beim Walk uebersprungen (Artefakt, kein Knoten).
    """
    nodes = []
    for dirpath, _dirs, files in os.walk(root):
        for fname in files:
            if not fname.endswith(".md") or fname == "_Tag-Index.md":
                continue
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root).replace(os.sep, "/")
            try:
                with open(fpath, encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError:
                continue
            fm = parse_frontmatter(content) or {}
            # J12 (batch_3/Stage 3): Body-[[Wikilinks]] als {source, target}-Edges
            # einsammeln (DRY: extract_wikilinks Lead) -> Substrat fuer
            # build_anchor_index/build_backlinks (die wikilinks als dict erwarten).
            wikilinks = [
                {"source": rel, "target": tgt}
                for tgt in extract_wikilinks(content)
            ]
            nodes.append({
                "path": rel,
                "bl_id": fm.get("bl"),
                "vault_origin": str(root),
                "node_type": fm.get("node_type"),
                "keywords": fm.get("keywords") or [],
                "raw_tags": fm.get("tags") or [],
                "frontmatter": fm,
                "wikilinks": wikilinks,
                "edges": fm.get("edges") or _extract_block_sequence(content, "edges"),
            })
    return nodes


def _build_raw_tag_index(nodes):
    """Raw-case Tag-Index je Vault: {raw_tag: [{path, vault_origin}, ...]}.

    Strukturell die Tag-Aggregator-Form (analog build_tag_index/H4), aber ueber
    node["raw_tags"] (Original-Case) statt extract_tags (das lowercased) — J9
    rendert _Tag-Index.md mit dem Original-Tag ('topic/Modus', nicht 'topic/modus').
    Extract-Method aus build_index (DRY/SRP, _TDD_refactorCode 6e): build_index
    haelt nur noch die Walk/Merge-Orchestrierung, nicht die Tag-Schleife inline.
    """
    idx = {}
    for node in nodes:
        for tag in node.get("raw_tags") or []:
            idx.setdefault(tag, []).append({
                "path": node.get("path"),
                "vault_origin": node.get("vault_origin"),
            })
    return idx


def _write_index_json(out_dir, built):
    """Serialisiert die 4 maschinellen Indizes (keyword/edge/anchor/backlinks)
    deterministisch nach {out_dir}/_*.json (Extract-Method aus main, _TDD_refactorCode
    6e — DRY/SRP analog _build_raw_tag_index: der build-Pfad haelt nur noch die
    Befehls-Orchestrierung, nicht die Serialisierungs-Mechanik inline).

    PT-GEN-LeadFollow: ruft die Leads serialize_index_json (H12) + backlinks_schema
    (H14) per IDENTITAET (kein zweites JSON-Format). Backlinks werden vor der
    Persistenz in die kanonische backlinks_schema-Form gehoben — die In-Memory-Form
    {referenced_by, references} bleibt fuer den batch_1-Aggregator-Vertrag
    UNVERAENDERT (additiv, kein Schema-Bruch). os.makedirs(exist_ok=True): Output-Dir
    wird idempotent angelegt (auch fuer den leeren Vault -> valides {}-JSON).
    """
    os.makedirs(out_dir, exist_ok=True)
    backlinks_json = {
        path: backlinks_schema(path, entry["referenced_by"], entry["references"])
        for path, entry in built["backlinks"].items()
    }
    index_files = {
        "_keyword_index.json": built["keyword_index"],
        "_edge_index.json": built["edge_index"],
        "_anchor_index.json": built["anchor_index"],
        "_backlinks.json": backlinks_json,
    }
    for fname, index in index_files.items():
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as fh:
            fh.write(serialize_index_json(index))


def build_index(roots):
    """Cross-Vault-Build-Orchestrator (J8): realer Walk je Root -> pro-Vault
    keyword/edge/tag-Index -> merge_vault_indexes ueber alle Roots.

    SOA-1: genau 1 Root -> Single-Vault graceful (Pass-through). Leerer Root ->
    leere Indizes (kein Crash). Jeder keyword-Eintrag traegt vault_origin.
    Rueckgabe: {keyword_index, edge_index, tag_index, anchor_index, backlinks}
    (tag_index = raw-case fuer J9-Render; anchor_index/backlinks = J12-Integration
    via build_anchor_index/build_backlinks ueber den Body-Wikilink-Walk).
    """
    keyword_index = {}
    edge_index = {}
    tag_index = {}
    all_nodes = []
    all_wikilinks = []
    for root in roots or []:
        nodes = _walk_vault_nodes(root)
        keyword_index = merge_vault_indexes(keyword_index, build_keyword_index(nodes))
        edge_index = merge_vault_indexes(edge_index, build_edge_index(nodes))
        tag_index = merge_vault_indexes(tag_index, _build_raw_tag_index(nodes))
        # J12: anchor/backlinks ueber ALLE Knoten + Body-Wikilinks (cross-vault).
        all_nodes.extend(nodes)
        for node in nodes:
            all_wikilinks.extend(node.get("wikilinks") or [])
    return {
        "keyword_index": keyword_index,
        "edge_index": edge_index,
        "tag_index": tag_index,
        # J12 (batch_3/Stage 3): die 2 fehlenden maschinellen Indizes, ueber die
        # bereits vorhandenen batch_1-Aggregatoren (kein Neu-Format, PT-GEN-LeadFollow).
        "anchor_index": build_anchor_index(all_nodes, all_wikilinks),
        "backlinks": build_backlinks(all_nodes, all_wikilinks),
    }


# --- BL-274 SB-2 (Stage 1, Atomic): MAP-cut — reine, seiteneffektfreie Kern-Funktionen ---
# AK-2 cut_sections + AK-3 _derive_map_slots. Schwestern von build_index (:295) /
# _walk_vault_nodes (:207). KEIN I/O, KEIN Lock, KEIN Dispatch (INV-STAGE-8): Stage 1
# verifiziert die Politik (Schnitt-Korrektheit, B-1-Slot-Zahl), nicht die Verdrahtung.

def _derive_map_slots(parallelism_budget):
    """BL-274 AK-3: reine Ableitung der parallelen Map-Slots aus dem
    parallelism_budget (BL-194 W9, read-only — nicht neu definiert).

    Invariante: _derive_map_slots(B) == max(B-1, 0). 1 Slot bleibt fuer den
    Lead/Orchestrator (PT-CMD-005 Wellen). B=1 -> 0 parallele Slots -> serieller
    Lauf (heutiges Verhalten, kein Regress / Kanarienvogel).
    """
    return max(parallelism_budget - 1, 0)


def cut_sections(roots, strategy="toplevel_dir_range"):
    """BL-274 AK-2: partitioniert den Root-Set in N Sektionen. Jede Sektion ist
    eine Root-Liste (list[root]), die genau eine atomare Map-Einheit
    build_index([sektion]) fuettert (AE-1: exakt das build_index(roots)-
    Eingabeformat, kein neues Section-DTO).

    Default-Strategy `toplevel_dir_range` (SA-1): je Root genau eine Sektion ->
    lueckenlose Voll-Abdeckung (Vereinigung == Root-Set), disjunkt (keine
    unkontrollierte Ueberlappung), deterministisch/resume-stabil (gleicher Input
    -> gleiche Partition, PT-CMD-007/PT-CMD-006). Leerer Root-Set -> [].
    """
    return [[root] for root in roots or []]


def _build_and_persist(root):
    """BL-275 AK-S1: baut den Index UND persistiert ihn (DRY-Helfer fuer `build`
    + `--incremental`). Schreibt {root}/_Tag-Index.md + die 4 maschinellen Indizes
    als deterministisches JSON nach {root}/.claude/output/retrieval_index/.
    Gibt das built-Dict zurueck."""
    built = build_index(roots=[root])
    rendered = render_tag_index_md(built["tag_index"])
    with open(os.path.join(root, "_Tag-Index.md"), "w", encoding="utf-8") as fh:
        fh.write(rendered)
    out_dir = os.path.join(root, ".claude", "output", "retrieval_index")
    _write_index_json(out_dir, built)
    return built


def main(argv):
    """CLI-Haut (DT-5): build / query / --incremental. Lead-Vorbild
    resolve_vault_root.py:155 (main(argv) -> int).

    exit_code-Matrix: build aufloesbar -> 0; query mit Treffer -> 0, ohne -> 1;
    --incremental Pfad nicht im Vault -> 1, sonst 0.
    """
    parser = argparse.ArgumentParser(prog="build_retrieval_index")
    parser.add_argument("command", nargs="?", default="build")
    parser.add_argument("--term", default=None)
    parser.add_argument("--path", default=None)
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--root", "--vault", dest="root", default=None)
    args = parser.parse_args(argv)

    root = args.root if args.root else str(resolve_vault_root())

    # --incremental --path=X: nur X-Eintraege patchen; X nicht im Vault -> exit 1
    if args.incremental:
        if not args.path:
            return 1
        target = os.path.join(root, args.path)
        if not os.path.exists(target):
            return 1
        # BL-275 AK-S1: jetzt PERSISTIEREND (vorher throwaway in-memory build_index ->
        # der Forward-Write-Seam in _W_push_global waere ein No-Op gewesen).
        _build_and_persist(root)  # Minimal: voller Re-Walk + Persist (Feature-Ende-Granularitaet, tragbar)
        return 0

    if args.command == "query":
        if not args.term:
            return 1
        built = build_index(roots=[root])
        hits = query(args.term, built["keyword_index"], built["edge_index"])
        return 0 if hits else 1

    # default: build — DRY ueber _build_and_persist (identisches Verhalten:
    # _Tag-Index.md + die 4 maschinellen JSON-Indizes deterministisch, sort_keys).
    _build_and_persist(root)
    return 0


# ===========================================================================
# BL-242 / batch_3 / Stage 1 (Atomic) — H12-H14: Index-Serialisierung / Form
# (AK-CTX-2). Reine Funktionen gegen Fixtures, KEIN File-IO (Mock-Grenze
# Stage 1 / sub-1-batch_3.md). PT-GEN-LeadFollow: H13/H14 exponieren die
# bereits in build_anchor_index/build_backlinks (batch_1) vorhandene
# Score-/Schema-Form isoliert (kein Neu-Format), H12 serialisiert das
# build_index-Output-Dict (kein eigenes Index-Format).
# ===========================================================================

def anchor_score(backlink_count, frontmatter_weight):  # noqa: E302
    """H13 (AK-CTX-2 / BL-161 AK-2.3): Anchor-Score backlink_count*0.6 +
    frontmatter_weight*0.4. Reine Arithmetik, KEIN IO. Score auf 10
    Nachkommastellen normiert (IEEE-754-Determinismus: 4*0.6+6*0.4 ergibt
    roh 4.800000000000001 -> stabil 4.8; alle anderen Fixture-Tupel bleiben
    bit-identisch zum rohen bc*0.6+fw*0.4)."""
    return round(backlink_count * 0.6 + frontmatter_weight * 0.4, 10)


def backlinks_schema(path, referenced_by, references):
    """H14 (AK-CTX-2 / BL-161 AK-3.1): Backlinks-Eintrag exakt Keys
    {path, referenced_by, references}; Listen stabil sortiert. Reine
    (args) -> dict-Fn, KEIN IO."""
    return {
        "path": path,
        "referenced_by": sorted(referenced_by),
        "references": sorted(references),
    }


def serialize_index_json(index):
    """H12 (AK-CTX-2): deterministischer JSON-String fuer ein Index-Dict
    (sort_keys=True, kanonische Separatoren). Reine dict -> str-Fn, KEIN
    File-IO (open()/json.dump = Stage 3)."""
    import json
    return json.dumps(index, sort_keys=True, separators=(",", ":"))


# ===========================================================================
# BL-389 / batch_2 / Stage 3 — AK-ATOM-INDEX (DoD-2): build_truth_atom_index
# Realer type:truth-.md-Walk -> Inverted-Keyword-Index {keyword: [entry,...]}.
# Reuse (DRY, PT-GEN-LeadFollow): _walk_vault_nodes (realer .md-Walk via Lead
# parse_frontmatter), build_keyword_index (Inverted-Index-Aggregator),
# merge_vault_indexes (Cross-Root-Merge), serialize_index_json (Persistenz).
# Fallback: truth_keywords.extract_keywords wenn keywords[] fehlt aber Text da.
# ===========================================================================

def _truth_keyword_nodes(root):
    """Walkt einen Root und liefert NUR die type:truth-Knoten in der von
    build_keyword_index erwarteten Form ({path, bl_id, vault_origin, node_type,
    keywords}). keywords aus frontmatter; Fallback truth_keywords.extract_keywords
    ueber den text-Inhalt wenn keywords[] fehlt aber Text vorhanden ist."""
    from truth_keywords import extract_keywords

    truth_nodes = []
    for node in _walk_vault_nodes(root):
        fm = node.get("frontmatter") or {}
        if fm.get("type") != "truth":
            continue  # node_type-/type-Filter: nur echte Wahrheiten
        keywords = node.get("keywords") or []
        if not keywords:
            # Fallback (A11): keywords[] fehlt -> aus text-Inhalt extrahieren.
            # NUR wiederkehrende (freq>=2) Begriffe gelten als thematisch — so
            # erzeugt eine triviale 1x-Erwaehnung (A8) KEINEN false-positiven Key,
            # waehrend ein 3x-wiederholter Begriff (A11) als Atom-Keyword zaehlt.
            text = fm.get("text") or ""
            keywords = [
                kw for kw in extract_keywords(text)
                if text.lower().count(kw.lower()) >= 2
            ]
        truth_nodes.append({
            "path": node.get("path"),
            "bl_id": node.get("bl_id"),
            "vault_origin": node.get("vault_origin"),
            "node_type": node.get("node_type"),
            "keywords": keywords,
        })
    return truth_nodes


def build_truth_atom_index(roots, persist=False):
    """AK-ATOM-INDEX (DoD-2): deterministischer Inverted-Index ueber type:truth-
    Dateien: {keyword: [{path, bl_id, vault_origin, node_type}, ...]}.

    Walkt jeden Root (realer .md-Walk via _walk_vault_nodes / Lead-parse_frontmatter),
    filtert auf fm.type == 'truth', baut den Inverted-Index via build_keyword_index
    (Reuse) und mergt ueber alle Roots via merge_vault_indexes (Reuse). keywords[]
    aus Frontmatter; Fallback truth_keywords.extract_keywords ueber den Text wenn
    keywords[] fehlt. Entry-Listen werden stabil nach path sortiert (Determinismus).

    persist=True: schreibt den Index deterministisch nach {root}/_keyword_index.json
    (je Root denselben Gesamt-Index, via serialize_index_json / Reuse).
    """
    index = {}
    for root in roots or []:
        nodes = _truth_keyword_nodes(root)
        index = merge_vault_indexes(index, build_keyword_index(nodes))

    # Determinismus: jede Entry-Liste stabil nach path sortieren (kein Set/Hash-Drift).
    index = {
        kw: sorted(entries, key=lambda e: str(e.get("path") or ""))
        for kw, entries in index.items()
    }

    if persist:
        payload = serialize_index_json(index)
        for root in roots or []:
            with open(os.path.join(root, "_keyword_index.json"), "w", encoding="utf-8") as fh:
                fh.write(payload)

    return index


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
