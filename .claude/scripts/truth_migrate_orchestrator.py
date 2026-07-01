#!/usr/bin/env python3
"""
truth_migrate_orchestrator.py — /_W_atom_migration_orchestrator (BL-386, read-only Spine).

Komponiert die bewiesenen Komponenten zur globalen Migration:
  discover (Models) -> [pro BL-Unit: atomize -> census-gate -> roundtrip-gate -> apply_backrefs R1]
  -> korpus-weit: dedup_stats (R4) + referenced_by-Coverage -> Readiness-Report.

mode: global (ganzer Scope) | bl:{ticket} (ein BL) | pilot (erste N ready).

HART GEFENCED: dieser Build mutiert den Vault NICHT. --write ist ein No-Op, das die Fence-Regel
meldet (Live-Cutover = Phase C: frische Session + Backup, weil Vault nicht git, BL-364).
Komponenten: truth_atomize_batch · truth_atomizer · truth_backref_index · truth_dedup · truth_census.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

import truth_atomize_batch as batch
import truth_atomizer as ta
import truth_backref_index as bi
import truth_dedup as dd
import truth_normalize as tn  # BL-398: Stage 2 (Model-Vorab-Normalisierung VOR atomize)

try:
    import truth_census as tc
except ImportError:
    tc = None  # type: ignore

_TICKET_DIR = re.compile(r"^[A-Z][A-Z0-9_]*-\d+")


def _bl_folder_of(model_path: Path) -> Optional[Path]:
    """Findet den BL-/Ticket-Ordner-Vorfahren (fuer Backref-Surfaces). None bei Repo-Meta-Models."""
    for parent in Path(model_path).parents:
        if _TICKET_DIR.match(parent.name):
            return parent
    return None


def process_bl_unit(model_path: str, *, normalize: bool = False, legacy_dir=None) -> dict:
    """Eine Migrations-Einheit (1 Model): [Stage 2 normalize] -> atomize + census-gate +
    roundtrip-gate + R1-Backrefs. READ-ONLY am QUELL-Model. Picklebar (module-level).

    BL-398 Stage 2: normalize=True haengt truth_normalize.normalize_model(...) als Stage 2 VOR
    atomize ein. Die Normalisierung laeuft auf einer KOPIE im legacy_dir-Scope (NIE in-place am
    Quell-Model -> DRY-RUN-Erhalt). Result um normalized/format_hint/stage2_legacy ergaenzt; bei
    nicht-content-faithfulem Model bleibt Stage 2 wirkungslos -> Stage 3 SEGMENT-Pfad (Quarantaene
    intakt, kein stiller Verlust).
    """
    mp = Path(model_path)
    bl_folder = _bl_folder_of(mp)
    if bl_folder:
        # Multi-kanonische-Model-BLs disambiguieren (sonst kollidieren gleiche local_ids ueber
        # die Models, INV-MIG-10). Singletons behalten die saubere {BL-SLUG}.{local_id}-Form.
        siblings = [m for m in bl_folder.rglob("*.md") if batch.is_canonical_model(m)]
        ns = f"{bl_folder.name}/{mp.stem}" if len(siblings) > 1 else bl_folder.name
    else:
        ns = mp.stem.replace("_Model", "")

    # ── Stage 2 (BL-398): content-faithful-guarded Normalisierung auf einer KOPIE. ──
    normalized = False
    stage2_legacy = None
    atomize_path = mp
    if normalize:
        ld = Path(legacy_dir) if legacy_dir else (mp.parent / "_legacy")
        ld.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as _td:
            copy_path = Path(_td) / mp.name
            shutil.copyfile(mp, copy_path)
            n = tn.normalize_model(copy_path, legacy_dir=ld)
            normalized = bool(n["normalized"])
            stage2_legacy = n.get("legacy")
            if normalized and n.get("content_faithful"):
                # normalisierte (schlanke HEADING-)Form als persistente Stage-2-Ausgabe behalten,
                # damit Stage 3 nicht erneut den driftenden Quell-Body atomisiert.
                staged = ld / (mp.stem + ".normalized.md")
                staged.write_text(copy_path.read_text(encoding="utf-8"), encoding="utf-8")
                atomize_path = staged
            # nicht content-faithful: atomize_path bleibt das Quell-Model (SEGMENT-Pfad).

    res = ta.atomize_model_file(atomize_path, ns)
    truths = res.pop("truths")
    text = mp.read_text(encoding="utf-8", errors="replace")
    census = tc.count_wknots(text)["total_estimate"] if tc else res["knots"]
    complete = res["knots"] >= census
    # BL-391 (B): Range-Heading-Kollaps (### W16-W19) als eigene LAUTE Gate-Dimension. Der census==
    # atomizer-Cross-Check ist strukturell blind (beide unterzaehlen identisch); das Span-Signal nicht.
    collapsed_ids = sorted({cid for rc in ta.detect_range_collapses(text, {t["local_id"] for t in truths})
                            for cid in rc["collapsed_ids"]})
    if bl_folder:  # R1 Inverse-Index nur wo Referenzier-Surfaces existieren (Vault-BLs)
        bi.apply_backrefs(truths, bi.build_backref_index(bl_folder))
    # BL-395 (b): Byte-Coverage-Gate — ready erfordert auch, dass die generierte View den Quell-Body
    # rekonstruiert (sonst Inhalts-Verlust beim Cutover, den der parse-Roundtrip nicht sieht).
    low_coverage = bool(res.get("low_coverage"))
    ready = bool(res["roundtrip_ok"]) and complete and not res["schema_errors"] and not low_coverage
    return {
        "model": str(mp), "ns": ns, "knots": res["knots"], "census": census,
        "roundtrip_ok": res["roundtrip_ok"], "complete": complete,
        "schema_errors": res["schema_errors"], "ready": ready,
        "coverage": res.get("coverage"), "low_coverage": low_coverage,
        "range_collapsed": bool(collapsed_ids), "collapsed_ids": collapsed_ids,
        "backref_count": sum(1 for t in truths if t.get("referenced_by")),
        # BL-398 Stage-2-Observables:
        "format_hint": res["format_hint"], "normalized": normalized,
        "stage2_legacy": stage2_legacy,
        "_truths": truths,
    }


def quarantine_reasons(r: dict) -> list:
    """BL-395: WARUM ein Model NICHT in den Cutover-Write-Scope darf — als deterministische MASCHINEN-
    Entscheidung (nicht Lead-Augenmass). Leere Liste = ready (darf geschrieben werden). Diese Gruende
    sind genau die Gate-Dimensionen, auf die _process_one den --write blockt — der Quarantaene-Output
    ist damit das Observable derselben Maschinen-Regel, die den Write physisch verhindert."""
    reasons = []
    if not r.get("roundtrip_ok"):
        reasons.append("roundtrip_fail")
    if not r.get("complete", True):
        reasons.append("truth_count_loss")     # census-W-Definitionen > atomisierte knots (BL-395 a)
    if r.get("low_coverage"):
        reasons.append("low_byte_coverage")     # generierte View << Quell-Body (BL-395 b)
    if r.get("range_collapsed"):
        reasons.append("range_collapse")        # ### W16-W19 (BL-391)
    if r.get("schema_errors"):
        reasons.append("schema_error")
    return reasons


def run(
    vault: Optional[Path] = None,
    repo_models: Optional[Path] = None,
    *,
    mode: str = "global",
    jobs: int = 4,
    write: bool = False,
    normalize: bool = False,
) -> dict:
    """Read-only Migrations-Orchestrierung. Returns Readiness-Report (kein Write).

    BL-398: normalize=True faedelt Stage 2 (truth_normalize) in die Per-Model-Kette ein
    (DRY-RUN/gefenced — kein truths/-Write). normalize=False -> Verhalten UNVERAENDERT.
    """
    models = [str(m) for m in batch.discover_models(vault, repo_models)]
    if mode.startswith("bl:"):
        ticket = mode.split(":", 1)[1].lower()
        models = [m for m in models if ticket in m.lower()]

    def _process(m):
        return process_bl_unit(m, normalize=normalize)

    if jobs <= 1:
        results = [_process(m) for m in models]
    else:
        with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
            results = list(ex.map(_process, models))

    if mode == "pilot":
        results = [r for r in results if r["ready"]][:3]

    all_truths = [t for r in results for t in r["_truths"]]
    dedup = dd.dedup_stats(all_truths)
    backref_cov = sum(1 for t in all_truths if t.get("referenced_by"))

    fenced_note = None
    if write:
        fenced_note = ("FENCED: Live-Cutover ist Phase C (frische Session + Backup, Vault nicht git). "
                       "Dieser Orchestrator laeuft read-only - kein truths/-Write.")

    return {
        "mode": mode,
        "models": len(results),
        "knots": sum(r["knots"] for r in results),
        "ready": sum(1 for r in results if r["ready"]),
        "roundtrip_fails": sorted(r["model"] for r in results if not r["roundtrip_ok"]),
        "incomplete": sorted(r["model"] for r in results if not r["complete"]),
        "low_coverage": sorted(r["model"] for r in results if r.get("low_coverage")),
        "range_collapse": sorted(r["model"] for r in results if r.get("range_collapsed")),
        # BL-395: QUARANTAENE = die deterministische "NICHT in den Cutover-Write-Scope"-Liste (per-Model +
        # Gruende). Der Cutover-Write konsumiert das; Per-Model-Override ist VERBOTEN (still-Verlust-Schutz).
        "quarantine": [{"model": r["model"], "reasons": quarantine_reasons(r)} for r in results if not r["ready"]],
        "referenced_by_coverage": backref_cov,
        "dedup": dedup,
        "write_fenced": fenced_note,
        # BL-398 Stage-2-Observables (DoD-W.3): messbarer Slimming-/Heading-Gewinn durch Stage 2.
        "stage2_normalized": sum(1 for r in results if r.get("normalized")),
        "stage2_heading_gain": sum(1 for r in results if r.get("normalized")
                                   and r.get("format_hint") == "HEADING"),
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="truth_migrate_orchestrator",
                                description="BL-386 /_W_atom_migration_orchestrator (read-only Spine)")
    p.add_argument("--vault", type=Path, default=None)
    p.add_argument("--repo-models", type=Path, default=None)
    p.add_argument("--mode", default="global", help="global | bl:{ticket} | pilot")
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--write", action="store_true", help="GEFENCED: No-Op (Live-Cutover = Phase C)")
    p.add_argument("--normalize", action="store_true",
                   help="BL-398: Stage 2 (truth_normalize) VOR atomize einhaengen (DRY-RUN)")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    rep = run(args.vault, args.repo_models, mode=args.mode, jobs=args.jobs,
              write=args.write, normalize=args.normalize)
    print(f"mode={rep['mode']}  Models: {rep['models']}  Knoten: {rep['knots']}")
    print(f"READY: {rep['ready']}/{rep['models']}  Roundtrip-Fails: {len(rep['roundtrip_fails'])}  Unvollstaendig: {len(rep['incomplete'])}")
    print(f"Range-Heading-Kollaps (BL-391, LAUT): {len(rep['range_collapse'])} Models {rep['range_collapse'][:20]}")
    print(f"Low-Coverage (BL-395, View << Quell-Body): {len(rep['low_coverage'])} Models")
    print(f"QUARANTAENE (Maschinen-Ausschluss vom Cutover-Write, BL-395): {len(rep['quarantine'])} Models")
    print(f"referenced_by-Coverage: {rep['referenced_by_coverage']} Truths  Dedup: {rep['dedup']}")
    if rep["write_fenced"]:
        print(f"[{rep['write_fenced']}]")
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
