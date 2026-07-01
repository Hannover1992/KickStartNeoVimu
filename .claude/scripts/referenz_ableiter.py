"""referenz_ableiter.py — BL-460 B-4 / AK-2 + AK-CTX-2
Referenz-Ableiter: semantisches Atom-Match + Konfidenz-Score fuer Views.

Interface:
    score_view(view_path, vault_root, *, atom_index, conf_threshold=0.70,
               within_bl_boost=1.4, per_view_cap=15) -> list[dict]

Abhaengigkeiten:
    truth_search.py  — search_truths(query, atom_index=...) -> [{path, bl_id, score, ...}]
    truth_keywords.py — extract_keywords(text) -> [str]

Design-Wahrheiten aus SC HANDOFF:
  DT-AK-2-1:  truth_search.py ist die authoritative Inventar-Lookup-API.
  DT-AK-2-2:  View-Text vollstaendig lesen (Frontmatter + Body).
  DT-AK-2-3:  bl_id aus View-Frontmatter (`bl` oder `bl-item`).
  DT-AK-2-4:  Relative Normierung (relativ zu Top-Match).
  DT-AK-CTX-2-1: Sub-threshold markieren, NICHT verwerfen.
  DT-AK-CTX-2-3: Per-View-Cap beinhaltet sub-threshold Eintraege.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Optional


# ---------------------------------------------------------------------------
# Frontmatter-Parser (subset — nur fuer bl-Feld-Extraktion benoetigt)
# ---------------------------------------------------------------------------

def _parse_view_bl(content: str) -> Optional[str]:
    """Extrahiert bl_id aus View-Frontmatter (`bl:` oder `bl-item:`).

    Liest YAML-Frontmatter (---...---). Gibt None zurueck wenn kein `bl:`-Feld.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        # match `bl: BL-460` or `bl-item: BL-460`
        m = re.match(r'^bl(?:-item)?:\s*(.+)', stripped)
        if m:
            return m.group(1).strip().strip("'\"")

    return None


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def score_view(
    view_path: str,
    vault_root: str,
    *,
    atom_index: Optional[dict] = None,
    conf_threshold: float = 0.70,
    within_bl_boost: float = 1.4,
    per_view_cap: int = 15,
) -> list[dict]:
    """Bestimmt source_atom-Kandidaten fuer eine View.

    Args:
        view_path:       Absoluter Pfad zur View-Datei (.md).
        vault_root:      Vault-Root (fuer bl_id-Extraktion + live-Index-Build falls kein atom_index).
        atom_index:      Vorberechneter Inverted-Index {keyword: [entries]}.
                         Falls None: kein Vault-IO im unit-Test-Pfad -> [].
        conf_threshold:  Untere Konfidenz-Grenze (default 0.70). Matches darunter:
                         sub_threshold=True (markiert, nicht verworfen).
        within_bl_boost: Multiplikator fuer Atome aus derselben BL wie die View (default 1.4).
        per_view_cap:    Maximale Anzahl Eintraege inkl. sub-threshold (default 15).

    Returns:
        list[dict] absteigend nach confidence, max per_view_cap Eintraege:
          {atom_id, bl_id, confidence, sub_threshold, raw_score, boosted_score}
        [] bei nicht-lesbarer View / keinen salient Terms / leerem/None-Index.
    """
    # --- Guard: leerer/None Index -> [] ------------------------------------------
    if not atom_index:
        return []

    # --- View einlesen -----------------------------------------------------------
    try:
        with open(view_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError:
        return []

    # --- bl_id der View extrahieren ----------------------------------------------
    view_bl_id = _parse_view_bl(content)

    # --- Salient Terms extrahieren -----------------------------------------------
    from truth_keywords import extract_keywords
    query_terms = extract_keywords(content)
    if not query_terms:
        return []

    # --- Atom-Lookup via truth_search --------------------------------------------
    from truth_search import search_truths
    query = " ".join(query_terms)
    raw_results = search_truths(query, atom_index=atom_index)

    if not raw_results:
        return []

    # --- Boost anwenden ----------------------------------------------------------
    boosted: list[dict] = []
    for r in raw_results:
        raw_score = r.get("score", 0)
        atom_bl = r.get("bl_id")
        if view_bl_id and atom_bl == view_bl_id and within_bl_boost != 1.0:
            bs = raw_score * within_bl_boost
        else:
            bs = float(raw_score)
        boosted.append({
            "_path": r.get("path") or "",
            "_bl_id": atom_bl,
            "raw_score": raw_score,
            "boosted_score": bs,
        })

    # --- Sortieren nach boosted_score desc, Tie-Breaker alphabetisch path --------
    boosted.sort(key=lambda x: (-x["boosted_score"], x["_path"]))

    # --- Confidence normalisieren -------------------------------------------------
    top_bs = boosted[0]["boosted_score"] if boosted else 0.0
    if top_bs == 0.0:
        return []

    results: list[dict] = []
    for item in boosted:
        conf = item["boosted_score"] / top_bs
        results.append({
            "atom_id": item["_path"],
            "bl_id": item["_bl_id"],
            "confidence": conf,
            "sub_threshold": conf < conf_threshold,
            "raw_score": item["raw_score"],
            "boosted_score": item["boosted_score"],
        })

    # --- Cap ---------------------------------------------------------------------
    return results[:per_view_cap]


# ---------------------------------------------------------------------------
# Real-Vault Helper (CLI / Integration-Pfad, nicht unit-test-relevant)
# ---------------------------------------------------------------------------

def build_atom_index_from_vault(vault_root: str) -> dict:
    """Baut Inverted-Index aus dem echten Vault via truth_search._build_atom_index_from_roots.

    Verwendung: CLI + dry_run_reporter (einmaliger Pre-Build vor dem Schwarm).
    Unit-Tests nutzen injizierte atom_index; dieser Helper wird dort NICHT aufgerufen.
    """
    from truth_search import _build_atom_index_from_roots
    return _build_atom_index_from_roots([vault_root])


# ---------------------------------------------------------------------------
# CLI-Einstiegspunkt
# ---------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    """CLI: referenz_ableiter.py <view_path> <vault_root> [--threshold=0.70] [--cap=15]"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Referenz-Ableiter: score_view fuer eine View gegen den Vault.",
    )
    parser.add_argument("view_path", help="Pfad zur View-Datei")
    parser.add_argument("vault_root", help="Vault-Root (fuer Index-Build)")
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--cap", type=int, default=15)
    parser.add_argument("--boost", type=float, default=1.4)
    args = parser.parse_args(argv)

    if not os.path.isfile(args.view_path):
        print(f"ERROR: View nicht gefunden: {args.view_path}", file=sys.stderr)
        return 2

    atom_index = build_atom_index_from_vault(args.vault_root)
    if not atom_index:
        print(f"ERROR: Kein Atom-Index aus {args.vault_root}", file=sys.stderr)
        return 3

    results = score_view(
        args.view_path,
        args.vault_root,
        atom_index=atom_index,
        conf_threshold=args.threshold,
        within_bl_boost=args.boost,
        per_view_cap=args.cap,
    )

    if not results:
        print("Keine Kandidaten gefunden.")
        return 1

    for r in results:
        flag = "[sub-threshold]" if r["sub_threshold"] else ""
        print(
            f"  conf={r['confidence']:.3f} raw={r['raw_score']} boosted={r['boosted_score']:.2f}"
            f"  {r['atom_id']}  {flag}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
