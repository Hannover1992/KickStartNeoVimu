"""truth_search.py — thematische Suche ueber Truth-Atome (BL-389 batch_3, AK-WFETCH-ATOMS DoD-3).

API:
    search_truths(query, *, atom_index=None, roots=None) -> list[dict]

Dual-Eingabe:
  - atom_index={keyword: [entries]}  -> Lookup direkt im uebergebenen Index.
  - roots=[...]                      -> Live-Walk via build_truth_atom_index.

Ergebnis: [{path, bl_id, vault_origin, node_type, score}, ...] absteigend score,
Tie-Breaker alphabetisch nach path. Leer/no-match/None-index -> [] (kein Crash).
Deterministisch: gleicher Input -> gleicher Output.
"""

from __future__ import annotations

import os
import re

from truth_keywords import extract_keywords


def _parse_frontmatter_full(content: str) -> dict:
    """Parse YAML frontmatter mit Block-Sequence-Unterstuetzung (  - item).

    Erweiterung von quality_node_health.parse_frontmatter fuer YAML-Listen
    im Block-Format, die parse_frontmatter nicht unterstuetzt.
    Reine Funktion (kein IO).
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)

    result: dict = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue

        m = re.match(r'^(\S[^:]*?):\s*(.*)', line)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()

            if val == "":
                # Moeglicherweise Block-Sequence: naechste Zeilen mit "  - item"
                items = []
                j = i + 1
                while j < len(fm_lines) and re.match(r'^\s+-\s+(.*)', fm_lines[j]):
                    item_m = re.match(r'^\s+-\s+(.*)', fm_lines[j])
                    items.append(item_m.group(1).strip().strip("'\""))
                    j += 1
                if items:
                    result[key] = items
                    i = j
                    continue
                else:
                    result[key] = None
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                result[key] = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
            else:
                result[key] = val.strip("'\"")
        i += 1

    return result


def _walk_truth_atoms(root: str) -> list[dict]:
    """Walkt einen Root und liefert truth-Atom-Dicts fuer type:truth-.md-Dateien.

    Parst YAML-Frontmatter mit Block-Sequence-Unterstuetzung (_parse_frontmatter_full).
    Gibt [{path, bl_id, vault_origin, node_type, keywords}, ...] zurueck.
    """
    atoms = []
    for dirpath, _dirs, files in os.walk(root):
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root).replace(os.sep, "/")
            try:
                with open(fpath, encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError:
                continue
            fm = _parse_frontmatter_full(content)
            if fm.get("type") != "truth":
                continue
            keywords = fm.get("keywords") or []
            if isinstance(keywords, str):
                keywords = [keywords]
            atoms.append({
                "path": rel,
                "bl_id": fm.get("bl"),
                "vault_origin": str(root),
                "node_type": fm.get("node_type") or "truth",
                "keywords": keywords,
            })
    return atoms


def _build_atom_index_from_roots(roots: list) -> dict:
    """Baut Inverted-Index {keyword: [entries]} aus roots via _walk_truth_atoms.

    Reuse von build_truth_atom_index wo moeglich; eigener Walk als Fallback fuer
    YAML-Block-Sequence-Frontmatter (parse_frontmatter-Limitation).
    """
    from build_retrieval_index import build_truth_atom_index
    # Versuche zuerst den kanonischen Index-Builder.
    candidate = build_truth_atom_index(roots)
    if candidate:
        return candidate

    # Fallback: eigener Walk mit Block-Sequence-Unterstuetzung.
    index: dict = {}
    for root in roots or []:
        for atom in _walk_truth_atoms(root):
            for kw in atom.get("keywords") or []:
                entry = {
                    "path": atom["path"],
                    "bl_id": atom["bl_id"],
                    "vault_origin": atom["vault_origin"],
                    "node_type": atom["node_type"],
                }
                index.setdefault(kw, []).append(entry)

    # Determinismus: Entry-Listen stabil nach path sortieren.
    return {
        kw: sorted(entries, key=lambda e: str(e.get("path") or ""))
        for kw, entries in index.items()
    }


def search_truths(query: str, *, atom_index: dict | None = None, roots: list | None = None) -> list[dict]:
    """Thematische Query -> ranked Truth-Atome.

    Args:
        query:      Freitext-Query.
        atom_index: Vorberechneter Inverted-Index {keyword: [entries]}.
                    Mutually exclusive mit roots (atom_index hat Vorrang).
        roots:      Liste von Vault-Roots fuer Live-Walk (via build_truth_atom_index).

    Returns:
        Liste von Treffern [{path, bl_id, vault_origin, node_type, score}, ...],
        absteigend nach score, Tie-Breaker alphabetisch nach path.
        [] bei leerer/no-match Query, leerem Index oder None-Eingaben.
    """
    # Resolve atom_index: entweder direkt uebergeben oder live bauen.
    if atom_index is None and roots is not None:
        atom_index = _build_atom_index_from_roots(roots)

    # Graceful: None oder leerer Index -> []
    if not atom_index:
        return []

    # Keywords aus Query extrahieren (Stopwords/Kurzwoerter raus via Lead).
    keywords = extract_keywords(query)
    if not keywords:
        return []

    # Score-Akkumulation: jeder Atom zaehlt Treffer (keyword-Matches).
    # Entry-Identity via path (Schluessel).
    scores: dict[str, int] = {}
    entries_by_path: dict[str, dict] = {}

    for kw in keywords:
        for entry in atom_index.get(kw) or []:
            path = entry.get("path") or ""
            scores[path] = scores.get(path, 0) + 1
            if path not in entries_by_path:
                entries_by_path[path] = entry

    if not scores:
        return []

    # Ergebnis-Liste aufbauen + score-Feld einfuegen.
    results = []
    for path, score in scores.items():
        base = entries_by_path[path]
        results.append({
            "path": base.get("path"),
            "bl_id": base.get("bl_id"),
            "vault_origin": base.get("vault_origin"),
            "node_type": base.get("node_type"),
            "score": score,
        })

    # Ranking: absteigend score, Tie-Breaker alphabetisch nach path (deterministisch).
    results.sort(key=lambda r: (-r["score"], r["path"] or ""))
    return results
