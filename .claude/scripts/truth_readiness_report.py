#!/usr/bin/env python3
"""
truth_readiness_report.py — Pre-Flight GO/NO-GO fuer den Cutover (BL-309 / BL-386).

Komponiert ALLE read-only Views zum EINEN Entscheidungs-Artefakt, das die frische Cutover-Session
liest (zero-error one-shot): Orchestrator-Readiness + Graph-Gesundheit + SRS-Verteilung + Dedup.
GO-for-Pilot nur wenn jede Einheit ready (roundtrip-ok + vollstaendig + schema-sauber).

READ-ONLY: keine Mutation. Das ist das Gate VOR dem irreversiblen Schritt.
"""
from __future__ import annotations

import concurrent.futures as cf
from pathlib import Path
from typing import Optional

import truth_atomize_batch as batch
import truth_migrate_orchestrator as orch
import truth_graph as tg
import truth_srs as tsrs
import truth_dedup as dd
import truth_verify as tv


def collect(vault: Optional[Path], repo_models: Optional[Path], jobs: int = 4) -> list[dict]:
    """Pro Model-Einheit: atomize + gates + backref (via Orchestrator.process_bl_unit). READ-ONLY."""
    models = [str(m) for m in batch.discover_models(vault, repo_models)]
    if jobs <= 1:
        return [orch.process_bl_unit(m) for m in models]
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(orch.process_bl_unit, models))


def go_for_pilot(results: list[dict]) -> bool:
    """GO nur wenn es Einheiten gibt UND jede ready ist (roundtrip-ok + vollstaendig + schema-sauber)."""
    return bool(results) and all(r.get("ready") for r in results)


def compose(vault: Optional[Path] = None, repo_models: Optional[Path] = None, jobs: int = 4) -> dict:
    """Der komplette Pre-Flight-Report (alle Views komponiert + GO/NO-GO)."""
    results = collect(vault, repo_models, jobs)
    truths = [t for r in results for t in r.get("_truths", [])]
    graph = tg.build_graph(truths)
    verification = tv.verify_all(truths)
    range_collapse = sorted(r["model"] for r in results if r.get("range_collapsed"))
    # GO nur wenn jede Einheit ready UND INV-MIG-10 clean UND KEIN Range-Heading-Kollaps (BL-391 B):
    # ein Kollaps (### W16-W19) wuerde beim --write einen merged Blob statt atomarer Truths schreiben
    # (still) -> GO=False ist die ehrliche Default. Der census==atomizer-Cross-Check ist hier strukturell
    # blind; das Span-Signal (detect_range_collapses) nicht. Per-Model-Cutover = expliziter Owner-Override.
    go = go_for_pilot(results) and verification["clean"] and not range_collapse
    return {
        "models": len(results),
        "knots": sum(r["knots"] for r in results),
        "ready": sum(1 for r in results if r.get("ready")),
        "go_for_pilot": go,
        "roundtrip_fails": sorted(r["model"] for r in results if not r.get("roundtrip_ok")),
        "incomplete": sorted(r["model"] for r in results if not r.get("complete", True)),
        "low_coverage": sorted(r["model"] for r in results if r.get("low_coverage")),
        "low_coverage_count": sum(1 for r in results if r.get("low_coverage")),
        # BL-395: deterministische Quarantaene-Liste (per-Model + Gruende) = der Cutover-Ausschluss-Scope.
        "quarantine": [{"model": r["model"], "reasons": orch.quarantine_reasons(r)} for r in results if not r.get("ready")],
        "quarantine_count": sum(1 for r in results if not r.get("ready")),
        "range_collapse": range_collapse,
        "range_collapse_count": len(range_collapse),
        "referenced_by_coverage": sum(1 for t in truths if t.get("referenced_by")),
        "graph": tg.graph_stats(graph),
        "srs": tsrs.srs_from_truths(truths),
        "dedup": dd.dedup_stats(truths),
        "verify": {"clean": verification["clean"], "id_collisions": verification["id_collision_count"],
                   "unresolved_edges": verification["unresolved_edges"]},
    }


def main(argv: list[str]) -> int:
    import argparse
    import json
    import sys
    p = argparse.ArgumentParser(prog="truth_readiness_report", description="BL-309 Pre-Flight GO/NO-GO (read-only)")
    p.add_argument("--vault", type=Path, default=None)
    p.add_argument("--repo-models", type=Path, default=None)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    rep = compose(args.vault, args.repo_models, args.jobs)
    print(f"GO-for-Pilot: {rep['go_for_pilot']}  ({rep['ready']}/{rep['models']} ready)")
    print(f"Knoten: {rep['knots']}  Graph: {rep['graph']['nodes']} Knoten/{rep['graph']['edges']} edges/{rep['graph']['isolated']} isoliert")
    print(f"SRS: {rep['srs']['srs']} (w_open {rep['srs']['w_open']}/{rep['srs']['w_total']})  referenced_by: {rep['referenced_by_coverage']}")
    print(f"Roundtrip-Fails: {len(rep['roundtrip_fails'])}  Unvollstaendig: {len(rep['incomplete'])}  Low-Coverage (BL-395): {rep['low_coverage_count']}  Dedup: {rep['dedup']['duplicate_groups']}")
    print(f"QUARANTAENE (NICHT in den Cutover-Write-Scope, BL-395): {rep['quarantine_count']} Models")
    print(f"Range-Heading-Kollaps (BL-391, LAUT, GO-blockierend): {rep['range_collapse_count']} Models {rep['range_collapse'][:20]}")
    print(f"INV-MIG-10 clean: {rep['verify']['clean']}  (ID-Kollisionen {rep['verify']['id_collisions']}, unresolved edges {rep['verify']['unresolved_edges']})")
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report: {args.out}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
