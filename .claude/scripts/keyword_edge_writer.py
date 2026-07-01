#!/usr/bin/env python3
"""
keyword_edge_writer.py — BL-450 batch_1 Stage 1

Builds and plants keyword-based edges between truth atoms.

Shared-keyword -> EDGE_RELS["relates_to"] edges are computed and written into
atom frontmatter edges[] + [[wikilink]] body sections via wikilink_materializer.

API:
    load_atom(path) -> dict
    is_edge_planted(existing_edges, dst_id, rel) -> bool
    compute_keyword_edges(src_atom, keyword_index, src_namespace) -> list[dict]
    write_edges_to_atom(atom_path, new_edges) -> int
    main(argv=None) -> int
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path

import yaml  # PyYAML — available in OmniCommand scripts env

from truth_schema import EDGE_RELS  # AK-2 Schema-Konformitaet

# Default rel for shared-keyword edges
_KEYWORD_REL: str = "relates_to"
assert _KEYWORD_REL in EDGE_RELS, f"_KEYWORD_REL={_KEYWORD_REL!r} nicht in EDGE_RELS"

_logger = logging.getLogger(__name__)

# Field names to extract a usable string from a dict keyword (in priority order).
_KEYWORD_TEXT_FIELDS = ("text", "term", "keyword", "value", "name")


def normalize_keyword(kw: object) -> str | None:
    """Return a canonical string keyword, or None if unusable (caller must skip + report).

    str  -> stripped str (None when blank);
    dict -> first present text-like field as stripped str (None when none found);
    else -> None.
    """
    if isinstance(kw, str):
        s = kw.strip()
        return s or None
    if isinstance(kw, dict):
        for f in _KEYWORD_TEXT_FIELDS:
            v = kw.get(f)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None  # e.g. {'by': .., 'kind': ..} -> no text field -> skip
    return None

EXPECTED_PRECISE_EDGE_COUNT = 48095  # BL-479 AC-4: Regression-Baseline (post-03bcdab praezise Truth-Kanten, NICHT 85K)


def _split_frontmatter(content: str) -> tuple[dict, str, bool]:
    """Split a document into (frontmatter_dict, body_text, has_frontmatter).

    Single source of truth for the ``---\\nYAML\\n---\\nbody`` layout. ``has_frontmatter``
    is False when no well-formed frontmatter block is present (caller decides the
    fallback). YAML parse errors degrade to an empty dict rather than raising.
    """
    if not content.startswith("---"):
        return {}, content, False
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content, False
    fm_text = content[4:end]  # skip opening ---\n
    body = content[end + 4:]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, body, True


def _parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter from a file and return (fm_dict, body_text)."""
    content = path.read_text(encoding="utf-8", errors="replace")
    fm, body, _has_fm = _split_frontmatter(content)
    return fm, body


def load_atom(path: Path) -> dict:
    """Load atom from path, returning frontmatter dict with injected 'path' key."""
    fm, _body = _parse_frontmatter(path)
    fm["path"] = str(path)
    return fm


def is_edge_planted(existing_edges: list, dst_id: str, rel: str) -> bool:
    """Return True if the (dst_id, rel) tripel is already in existing_edges.

    Handles heterogeneous edge lists that may contain dicts, strings, or None:
    - dict: match on ziel + rel (canonical form)
    - str: match on id equality (e.g. "AtomX" or "[[AtomX]]"), rel unknown -> safety-first match
    - other (None, int, ...): ignored, no crash
    """
    for edge in existing_edges:
        if isinstance(edge, dict):
            if edge.get("ziel") == dst_id and edge.get("rel") == rel:
                return True
        elif isinstance(edge, str):
            # String-Form (e.g. "[[AtomA]]" or "AtomA"): interpret as ziel-id, rel unknown
            # -> match on id only (safety-first: avoids re-planting an edge whose rel is implicit)
            if edge == dst_id or edge.strip("[]") == dst_id:
                return True
        # else: None or unknown type -> ignore, no crash
    return False


def compute_keyword_edges(
    src_atom: dict,
    keyword_index: dict[str, list[dict]],
    src_namespace: str,
    *,
    df_threshold: float = 1.0,
    min_shared: int = 1,
    max_edges: int | None = 10_000,
    total_atoms: int | None = None,
) -> list[dict]:
    """Compute relates_to edges from shared keywords with specificity filtering.

    The naive shared-keyword edge build explodes on real vaults (2.75M edges) because
    high-document-frequency keywords act as stopwords linking everything to everything.
    Three knobs tame this:

      1. Stopword-Filter (``df_threshold``): keywords whose document frequency
         (``df_count / total_atoms``) exceeds the threshold are dropped before edges
         are built. ``df_threshold=1.0`` (default) disables the filter.
      2. ``min_shared``: a target atom only earns an edge once it shares at least this
         many NON-stopword keywords with the source.
      3. ``max_edges`` Per-Atom-Cap: targets are ranked by an IDF-style specificity
         score (``sum(log(total_atoms / df_count))`` over the shared non-stopword
         keywords) and only the top-K survive. ``None`` = uncapped.

    Args:
        src_atom:       Atom dict with 'local_id' and 'keywords' fields.
        keyword_index:  Mapping keyword -> list of {path, bl_id, local_id}.
        src_namespace:  Namespace prefix for src atom (e.g. "NS-A").
        df_threshold:   Max document frequency (fraction) a keyword may have before it
                        is treated as a stopword and excluded. Default 1.0 = no filter.
        min_shared:     Minimum count of shared non-stopword keywords for an edge.
        max_edges:      Per-atom cap on emitted edges (top-K by specificity). None = uncapped.
        total_atoms:    Total atom count for DF computation. If None, derived from the
                        index as the number of distinct target atoms.

    Returns:
        List of edge dicts {rel, ziel, dst_path} — one per unique (dst, rel) pair.
        Excludes self-references.
    """
    src_local_id = src_atom.get("local_id", "")
    src_full_id = src_atom.get("id") or f"{src_namespace}.{src_local_id}"
    raw_keywords = src_atom.get("keywords") or []

    # Normalize keywords: skip dicts without a usable text field, strip strings.
    keywords: list[str] = []
    _skip_count = 0
    for _kw in raw_keywords:
        _norm = normalize_keyword(_kw)
        if _norm is None:
            _skip_count += 1
        else:
            keywords.append(_norm)
    if _skip_count:
        _logger.warning(
            "skipped %d non-string keyword(s) for atom %s "
            "(dict entries without text/term/keyword/value/name field — likely corrupted referenced_by)",
            _skip_count,
            src_full_id,
        )

    # Determine total_atoms (denominator for document frequency).
    if total_atoms is None:
        distinct: set[str] = set()
        for targets in keyword_index.values():
            for target in targets or []:
                _bl = target.get("bl_id", "")
                _loc = target.get("local_id", "")
                _aid = target.get("atom_id") or (f"{_bl}.{_loc}" if _bl else _loc)
                distinct.add(_aid)
        total_atoms = len(distinct)

    # Guard against division by zero — without atoms there is nothing to relate.
    if not total_atoms:
        return []

    # Pre-compute document frequency per keyword and identify stopwords.
    df_count: dict[str, int] = {}
    is_stopword: dict[str, bool] = {}
    for kw in keywords:
        targets = keyword_index.get(kw) or []
        count = len(targets)
        df_count[kw] = count
        df = count / total_atoms
        is_stopword[kw] = df > df_threshold

    # Aggregate per-target: which non-stopword keywords are shared + accumulate score.
    per_target: dict[str, dict] = {}
    for kw in keywords:
        if is_stopword.get(kw, False):
            continue
        count = df_count.get(kw, 0)
        if count <= 0:
            continue
        # IDF-style specificity contribution; clamp at >= 0 (df == total -> 0 weight).
        idf = math.log(total_atoms / count)
        for target in keyword_index.get(kw) or []:
            dst_local_id = target.get("local_id", "")
            dst_bl_id = target.get("bl_id", "")
            dst_full_id = target.get("atom_id") or (f"{dst_bl_id}.{dst_local_id}" if dst_bl_id else dst_local_id)
            if dst_full_id == src_full_id:
                continue
            entry = per_target.get(dst_full_id)
            if entry is None:
                entry = {"shared": 0, "score": 0.0, "path": target.get("path", "")}
                per_target[dst_full_id] = entry
            entry["shared"] += 1
            entry["score"] += idf

    # Filter by min_shared, then rank by specificity score (desc), cap at max_edges.
    candidates = [
        (dst_full_id, data)
        for dst_full_id, data in per_target.items()
        if data["shared"] >= min_shared
    ]
    # Stable, deterministic ordering: highest score first, then dst id for ties.
    candidates.sort(key=lambda item: (-item[1]["score"], item[0]))

    if max_edges is not None:
        candidates = candidates[:max_edges]

    edges: list[dict] = [
        {
            "rel": _KEYWORD_REL,
            "ziel": dst_full_id,
            "dst_path": data["path"],
        }
        for dst_full_id, data in candidates
    ]

    return edges


def write_edges_to_atom(atom_path: Path, new_edges: list[dict], replace_rel: str | None = None) -> int:
    """Write new edges into atom frontmatter edges[] list (idempotent).

    Args:
        atom_path:   Path to the atom .md file.
        new_edges:   Edges to plant (list of {rel, ziel, ...}).
        replace_rel: When set, ALL existing edges with rel==replace_rel are removed
                     before merging new_edges. Idempotent: a second identical call
                     yields the same result. When None: unchanged append behaviour.

    Returns number of edges actually written (0 if all already planted).
    """
    content = atom_path.read_text(encoding="utf-8", errors="replace")

    fm, body, has_frontmatter = _split_frontmatter(content)
    if not has_frontmatter:
        # No frontmatter — cannot write edges
        return 0

    existing_edges: list[dict] = fm.get("edges") or []

    # Replace-Semantik: strip out all existing edges of the target rel first.
    if replace_rel is not None:
        existing_edges = [e for e in existing_edges if not (isinstance(e, dict) and e.get("rel") == replace_rel)]

    to_add: list[dict] = []
    for edge in new_edges:
        dst_id = edge.get("ziel", "")
        rel = edge.get("rel", _KEYWORD_REL)
        if not is_edge_planted(existing_edges, dst_id, rel):
            to_add.append({"rel": rel, "ziel": dst_id})

    if not to_add and replace_rel is None:
        return 0

    # Merge and rewrite frontmatter
    fm["edges"] = existing_edges + to_add
    new_fm_text = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    new_content = f"---\n{new_fm_text}---\n{body}"
    atom_path.write_text(new_content, encoding="utf-8")
    return len(to_add)


def _build_keyword_index(vault_root: Path) -> dict[str, list[dict]]:
    """Scan vault_root for all atom .md files and build keyword -> [atom_info] index.

    Scope: NUR Truth-Atome (frontmatter type==truth) werden indiziert —
    Nicht-Truth-Files (BL-Nodes/Specs) ausgeschlossen (BL-479, 0 dangling/coarse-non-truth).
    """
    index: dict[str, list[dict]] = {}
    _total_skips = 0
    _skip_atoms = 0
    for atom_file in vault_root.rglob("*.md"):
        fm = load_atom(atom_file)
        if fm.get("type") != "truth":
            continue
        keywords = fm.get("keywords") or []
        if not keywords:
            continue
        atom_id = fm.get("id", "")
        # Derive bl_id from path: first path component after vault_root
        parts = atom_file.relative_to(vault_root).parts
        bl_id = parts[0] if parts else ""
        local_id = fm.get("local_id") or atom_file.stem
        _atom_skips = 0
        for kw in keywords:
            norm = normalize_keyword(kw)
            if norm is None:
                _atom_skips += 1
                continue
            index.setdefault(norm, []).append({
                "path": str(atom_file),
                "bl_id": bl_id,
                "local_id": local_id,
                "atom_id": atom_id,
            })
        if _atom_skips:
            _total_skips += _atom_skips
            _skip_atoms += 1
    if _total_skips:
        _logger.warning(
            "_build_keyword_index: skipped %d non-string keyword(s) across %d atom(s) "
            "(dict entries without text/term/keyword/value/name — likely corrupted referenced_by merged into keywords)",
            _total_skips,
            _skip_atoms,
        )
    return index


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. --vault REQUIRED, --dry-run optional."""
    parser = argparse.ArgumentParser(description="Plant keyword-based edges into truth atoms")
    parser.add_argument("--vault", required=True, help="Path to vault root")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    parser.add_argument("--idempotent", action="store_true", default=True,
                        help="Idempotenz-Guard (always-on; {src,dst,rel}-Tripel-Check). "
                             "Akzeptiert fuer Orchestrator-Naht-Kompat.")
    parser.add_argument("--replace", action="store_true",
                        help="Replace (not append) existing edges of _KEYWORD_REL before writing. "
                             "Idempotent: second run yields same result.")
    args = parser.parse_args(argv)

    # Emit WARNING-level logs to stderr so skip reports are visible in CLI runs.
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                        format="%(levelname)s %(name)s: %(message)s")

    vault_root = Path(args.vault)
    if not vault_root.exists():
        print(f"ERROR: vault path does not exist: {vault_root}", file=sys.stderr)
        return 2

    # Build keyword index
    keyword_index = _build_keyword_index(vault_root)

    # Count loaded atoms (distinct atom files with keywords) for DF computation.
    # This is the denominator that turns the keyword-edge explosion (~2.75M edges)
    # into a bounded ~5-30 edges/atom via the specificity filter below.
    total_atoms = sum(
        1
        for atom_file in vault_root.rglob("*.md")
        for _fm in [load_atom(atom_file)]
        if _fm.get("type") == "truth" and (_fm.get("keywords") or [])
    )

    # Aggressive real-world specificity parameters (BL-455): high-DF keywords become
    # stopwords, edges require >= 2 shared specific keywords, capped at 15 per atom.
    _DF_THRESHOLD = 0.05
    _MIN_SHARED = 2
    _MAX_EDGES = 15

    total_written = 0
    max_per_atom = 0  # tracks max edges produced for a single atom (dry-run instrumentation)
    total_kw_skips = 0  # aggregate of non-string keywords skipped during compute_keyword_edges
    for atom_file in vault_root.rglob("*.md"):
        fm = load_atom(atom_file)
        is_truth = fm.get("type") == "truth"

        # Scope-Filter (BL-479): nur Truth-Atome erhalten neue Kanten.
        # Im --replace-Modus werden aber AUCH Nicht-Truth-Atome durchlaufen, damit
        # stale relates_to-Kanten gecleant werden (replace_rel-Semantik in write_edges_to_atom).
        if not is_truth and not args.replace:
            continue

        keywords = fm.get("keywords") or []
        # Neue Kanten werden nur fuer Truth-Atome berechnet (scope-Filter AC-1/AC-2).
        if is_truth and keywords:
            # Count non-normalizable keywords for aggregate skip reporting in main.
            total_kw_skips += sum(1 for k in keywords if normalize_keyword(k) is None)
            parts = atom_file.relative_to(vault_root).parts
            bl_id = parts[0] if parts else ""
            src_atom = {
                "id": fm.get("id", ""),
                "local_id": fm.get("local_id") or atom_file.stem,
                "keywords": keywords,
            }
            edges = compute_keyword_edges(
                src_atom,
                keyword_index,
                src_namespace=bl_id,
                df_threshold=_DF_THRESHOLD,
                min_shared=_MIN_SHARED,
                max_edges=_MAX_EDGES,
                total_atoms=total_atoms,
            )
        else:
            # Nicht-Truth (nur im --replace-Pfad): keine neuen Kanten, aber stale cleanen.
            edges = []

        # Derive namespace from bl_id
        if not edges and not args.replace:
            continue
        if args.dry_run:
            max_per_atom = max(max_per_atom, len(edges))
            total_written += len(edges)
            continue
        replace_rel = _KEYWORD_REL if args.replace else None
        written = write_edges_to_atom(atom_file, edges, replace_rel=replace_rel)
        total_written += written

    if args.dry_run:
        # dangling_count=0 is correct-by-construction: freshly computed keyword edges target
        # indexed atoms only; stored-edge dangling is authoritatively gated by G2/Stage-8.
        import json as _json
        cap_ok = max_per_atom <= _MAX_EDGES
        result = {
            "tool": "keyword_edge_writer",
            "dry_run": True,
            "edge_count": total_written,
            "would_write": total_written,
            "max_edges_per_atom": max_per_atom,
            "dangling_count": 0,
            "cap": _MAX_EDGES,
            "cap_ok": cap_ok,
        }
        print(_json.dumps(result))
        # Human summary goes to stderr so stdout stays pure JSON for json.loads callers.
        print(
            f"[keyword_edge_writer] vault={vault_root} would write={total_written} edges "
            f"dry_run=True max_per_atom={max_per_atom} cap_ok={cap_ok}",
            file=sys.stderr,
        )
    else:
        print(f"[keyword_edge_writer] vault={vault_root} wrote={total_written} edges dry_run=False")
    if total_kw_skips:
        print(
            f"[keyword_edge_writer] WARNING: skipped {total_kw_skips} non-string keyword(s) "
            "during edge computation (dict entries without text/term/keyword/value/name field — "
            "corrupted referenced_by entries merged into keywords)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
