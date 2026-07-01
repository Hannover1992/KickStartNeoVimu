#!/usr/bin/env python3
"""
truth_atomize_batch.py — Hoch-parallelisierbarer Fan-Out-Treiber fuer die Atomisierung
(BL-309 Phase B, Wellen-Vorstufe / Konzept-Schritt 3.1 `_atomize_orchestrate` hoch-parallel).

WARUM parallelisierbar: jedes Model ist UNABHAENGIG — eigenes truths/-Verzeichnis, Original
unberuehrt, kein geteilter State, idempotent. Disjunkte Ausgabe = keine Write-Contention
(dieselbe truth_disjoint-Eigenschaft, die BL-230-Parallelitaet sicher macht).

Modi:
  --check (default): read-only Roundtrip-Readiness-Inventur ueber den Korpus (KEINE Mutation).
  --write          : echte Atomisierung (truths/ schreiben). Vault-Mutation -> gefenced (Phase C).

backend: thread (default, I/O-nebenlaeufig, test-freundlich) | process (CPU-Skalierung, CLI).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path
from typing import Callable, Optional

import truth_atomizer as ta

try:
    import truth_census as tc
    _is_candidate: Callable[[Path], bool] = tc.is_candidate
except ImportError:  # Fallback-Discovery
    def _is_candidate(path: Path) -> bool:
        return "Model" in str(path) or "model" in path.stem.lower()


def namespace_for(model_path: Path, vault_root: Optional[Path]) -> str:
    """Leitet den BL-SLUG-Namespace ab: Vault-BL = {Backlog/BL-XXX-slug}, sonst Datei-Stem."""
    parts = Path(model_path).parts
    for p in parts:
        if p.startswith("BL-") or "-" in p and p.split("-")[0].isupper() and p[:2].isalpha():
            # Vault-BL-Ordner (BL-309-slug / DCSRE-486-slug)
            if p[:3] in ("BL-",) or p.split("-")[0].isupper():
                return p
    return Path(model_path).stem.replace("_Model", "").replace(".md", "")


# Nicht-kanonische Verzeichnisse: Crumbs (Arbeitsnotizen), Sources/Snapshots, Legacy, Archiv, truths/.
_EXCLUDE_DIRS = {"Crumbs", "Sources", "_legacy", "archive", "_pileOfMud_snapshot", "truths"}
# "_archive" faengt datierte Archiv-Snapshots wie ".claude_archive_2026-05-02/" (BL-390 DCSRE-Befund:
# stale Archiv-Kopien von DCSRE-98/Dateiabholung leakten in die Discovery -> 9 INV-MIG-10-Kollisionen).
# ".deprecated" faengt explizit deprecate'te Ordner wie "....deprecated_2026-05-04/" (BL-393-Befund:
# 16 deprecated DCSRE-94/BL-125-Modelle leakten in die OmniCommand-Discovery; deprecated = NIE eine
# Migrations-Quelle -> ausschliessen, KEINE Kanonizitaets-Raterei). Beide: Substring auf dem rel-Pfad;
# fuehrender Punkt (".deprecated") trifft die Rename-Konvention, nicht eine Datei "deprecated_X_Model.md".
_EXCLUDE_SUBSTR = ("snapshot", "_modelsync_log", "_retract_log", "_archive", ".deprecated")


def is_canonical_model(path: Path) -> bool:
    """KANONISCHES Model (Migrations-Discovery): in 2_Model/ ODER stem endet _Model ODER stem==Model.
    Schliesst Crumbs/Sources/Logs/Snapshots/truths aus (sonst werden Arbeitsnotizen als Models
    atomisiert -> local_id-Kollision, INV-MIG-10-Befund BL-309)."""
    parts = set(path.parts)
    if parts & _EXCLUDE_DIRS:
        return False
    low = str(path).lower()
    if any(x in low for x in _EXCLUDE_SUBSTR):
        return False
    stem = path.stem
    return ("2_Model" in path.parts) or stem.endswith("_Model") or stem == "Model"


def discover_models(vault_root: Optional[Path], repo_models: Optional[Path]) -> list[Path]:
    """Findet KANONISCHE Models in Vault + Repo-Models (keine Crumbs/Snapshots/Logs).

    Cross-Root-Dedup (BL-390): dasselbe Model darf NICHT aus zwei Wurzeln doppelt
    entdeckt werden — sonst leiten beide denselben Namespace ab -> identische globale
    {ns}.{local_id} -> INV-MIG-10-Selbst-Kollision + Wrong-Version-Wins (z.B. stale Repo-
    Kopie ueberschreibt kanonische Vault-Truth im Graph-Node-Map). Vault (kanonisch) schlaegt
    Repo-Legacy (truth_resolver-Praezedenz atomic>...>repo). Schluessel = die ZUGEWIESENE
    Namespace (namespace_for), NICHT der Stem — sonst wuerden legitime gleichnamige Models aus
    verschiedenen BL-Ordnern (distinkte ns) faelschlich verworfen (= neuer Silent-Loss).
    Within-Root-Kollisionen (gleiche ns, selbe Wurzel) werden NICHT verworfen, damit echte
    Kollisionen weiter vom Verifier auffliegen (kein stilles Maskieren). Jeder Drop wird LAUT
    nach stderr gemeldet. OFFEN (BL-390 b): ob Repo-only-Legacy-Models in den Cutover-Write-
    Scope gehoeren, ist eine separate, NICHT von der Discovery entschiedene Frage."""
    found: list[Path] = []
    ns_first_root: dict[str, int] = {}
    dropped: list[tuple] = []
    for root_index, root in enumerate((vault_root, repo_models)):
        if root is None:
            continue
        root = Path(root)
        if not root.exists():
            continue
        for md in sorted(root.rglob("*.md")):
            # Exclusion RELATIV zur Scan-Wurzel pruefen (BL-390): sonst loest ein Ahnen-Ordner
            # ausserhalb des Vaults mit "_archive"/"snapshot" im Namen faelschlich ALLES aus.
            if not is_canonical_model(md.relative_to(root)):
                continue
            ns = namespace_for(md, vault_root)
            prev = ns_first_root.get(ns)
            if prev is not None and prev != root_index:
                # Gleiche ns aus FRUEHERER Wurzel (Vault) -> diese (Repo-Legacy) verwerfen, LAUT.
                dropped.append((ns, str(md)))
                continue
            ns_first_root.setdefault(ns, root_index)
            found.append(md)
    for ns, dup in dropped:
        print(f"[discover_models] cross-root DEDUP ns='{ns}': dropped legacy {dup} "
              f"(vault canonical kept) [BL-390]", file=sys.stderr)
    return found


def _process_one(model_path: str, namespace: str, write: bool, out_dir: Optional[str]) -> dict:
    """Worker: 1 Model atomisieren (in-memory) + optional schreiben. Picklebar (module-level)."""
    res = ta.atomize_model_file(Path(model_path), namespace)
    truths = res.pop("truths")
    text = Path(model_path).read_text(encoding="utf-8", errors="replace")
    # Census-Cross-Check (User-Fang 'nichts verlieren'): hat der Atomizer ALLE Knoten erwischt?
    # Faengt AUSSAGE-/TEXT-Format-Silent-Loss, bei dem der HEADING-Parser 0 findet aber Knoten existieren.
    try:
        import truth_census as _tc
        res["census_knots"] = _tc.count_wknots(text)["total_estimate"]
    except Exception:
        res["census_knots"] = res["knots"]
    res["complete"] = res["knots"] >= res["census_knots"]
    # BL-391 (B): Range-Heading-Kollaps LAUT. Der census==atomizer-Cross-Check ist hier strukturell
    # blind (beide unterzaehlen `### W16-W19` identisch als 1 Heading). Unabhaengiges Span-Signal ->
    # eigene Gate-Dimension (ueberlaedt complete/ready NICHT). KEIN --write bei Kollaps (sonst schreibt
    # der Cutover einen merged Blob statt atomarer Truths — still).
    collapses = ta.detect_range_collapses(text, {t["local_id"] for t in truths})
    res["collapsed_ids"] = sorted({cid for rc in collapses for cid in rc["collapsed_ids"]})
    res["range_collapsed"] = bool(res["collapsed_ids"])
    res["range_collapses"] = collapses
    res["write"] = None
    # NUR schreiben wenn vollstaendig + sauber + KEIN Range-Kollaps + Byte-Coverage ok (BL-395) — kein Write
    # bei Silent-Loss. low_coverage (View << Quell-Body) kommt aus atomize_model_file.
    if (write and res["roundtrip_ok"] and res["schema_errors"] == 0
            and res["complete"] and not res["range_collapsed"] and not res.get("low_coverage")):
        target = Path(out_dir) if out_dir else (Path(model_path).parent / "truths")
        res["write"] = ta.write_truths(truths, target)
    return res


def batch_atomize(
    jobs_list: list[tuple],
    *,
    jobs: int = 1,
    write: bool = False,
    backend: str = "thread",
) -> list[dict]:
    """jobs_list = [(model_path, namespace, out_dir), ...]. Pro Element unabhaengig."""
    if jobs <= 1:
        return [_process_one(str(mp), ns, write, out) for mp, ns, out in jobs_list]

    Executor = cf.ProcessPoolExecutor if backend == "process" else cf.ThreadPoolExecutor
    results: list[dict] = []
    with Executor(max_workers=jobs) as ex:
        futs = [ex.submit(_process_one, str(mp), ns, write, str(out) if out else None)
                for mp, ns, out in jobs_list]
        for f in cf.as_completed(futs):
            results.append(f.result())
    return results


def aggregate(results: list[dict]) -> dict:
    """Verdichtet die Resultate zur Readiness-Inventur."""
    total = len(results)
    knots = sum(r["knots"] for r in results)
    census_knots = sum(r.get("census_knots", r["knots"]) for r in results)
    rt_ok = sum(1 for r in results if r["roundtrip_ok"])
    # READY = roundtrip-ok UND vollstaendig (kein Silent-Loss) UND schema-sauber. Das ist die ehrliche Zahl.
    ready = sum(1 for r in results if r["roundtrip_ok"] and r.get("complete", True) and not r["schema_errors"] and not r.get("low_coverage"))
    non_heading = sorted(r["model"] for r in results if str(r["format_hint"]).startswith("NICHT"))
    incomplete = sorted(r["model"] for r in results if not r.get("complete", True))
    fails = sorted(r["model"] for r in results if not r["roundtrip_ok"] or r["schema_errors"])
    # BL-391 (B): Range-Heading-Kollaps als eigene LAUTE Dimension (nicht in complete/ready versteckt).
    range_collapse_models = sorted(r["model"] for r in results if r.get("range_collapsed"))
    range_collapse_ids = sum(len(r.get("collapsed_ids", [])) for r in results)
    low_coverage_models = sorted(r["model"] for r in results if r.get("low_coverage"))
    return {
        "models": total,
        "knots_extracted": knots,
        "knots_census": census_knots,
        "knot_coverage": round(knots / census_knots, 4) if census_knots else 1.0,
        "roundtrip_ok": rt_ok,
        "ready": ready,
        "ready_rate": round(ready / total, 4) if total else 1.0,
        "non_heading_count": len(non_heading),
        "incomplete_count": len(incomplete),
        "range_collapse_count": len(range_collapse_models),
        "range_collapse_ids": range_collapse_ids,
        "low_coverage_count": len(low_coverage_models),
        "low_coverage": low_coverage_models[:40],
        "non_heading": non_heading[:40],
        "fails": fails[:40],
        "range_collapse_models": range_collapse_models[:40],
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="truth_atomize_batch", description="BL-309 Phase B: paralleler Atomisier-Fan-Out")
    p.add_argument("--vault", type=Path, default=None, help="Vault-Root (Backlog/ wird gescannt)")
    p.add_argument("--repo-models", type=Path, default=None, help=".claude/models (Meta-Self, BL-385)")
    p.add_argument("--jobs", type=int, default=4, help="Parallele Worker (default 4)")
    p.add_argument("--backend", choices=["thread", "process"], default="thread")
    p.add_argument("--write", action="store_true", help="truths/ schreiben (Vault-Mutation, Phase C)")
    p.add_argument("--out", type=Path, default=None, help="JSON-Report-Pfad")
    args = p.parse_args(argv)

    models = discover_models(args.vault, args.repo_models)
    if not models:
        print("Keine Model-Kandidaten gefunden.", file=sys.stderr)
        return 1

    jobs_list = [(m, namespace_for(m, args.vault), None) for m in models]
    results = batch_atomize(jobs_list, jobs=args.jobs, write=args.write, backend=args.backend)
    summary = aggregate(results)

    print(f"Models: {summary['models']}  Knoten extrahiert/census: {summary['knots_extracted']}/{summary['knots_census']} (Coverage {summary['knot_coverage']*100:.1f}%)")
    print(f"READY (roundtrip+vollstaendig+schema): {summary['ready']}/{summary['models']} ({summary['ready_rate']*100:.1f}%)")
    print(f"Nicht-HEADING (Phase B2): {summary['non_heading_count']}  Unvollstaendig/Silent-Loss: {summary['incomplete_count']}")
    print(f"Range-Heading-Kollaps (BL-391, LAUT): {summary['range_collapse_count']} Models / {summary['range_collapse_ids']} kollabierte Ids")
    print(f"Low-Coverage (BL-395, View << Quell-Body): {summary['low_coverage_count']} Models")
    if summary["range_collapse_models"]:
        print(f"  -> {summary['range_collapse_models']}")
    print(f"Fails: {len(summary['fails'])}")
    if not args.write:
        print("[CHECK-only] read-only Readiness-Inventur, keine Mutation.")
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
