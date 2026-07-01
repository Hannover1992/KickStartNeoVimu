#!/usr/bin/env python3
"""
truth_gate_check.py — Die Pre-Flight-GATE-STRASSE der Truth-Migration (BL-309-Familie), Schritt fuer Schritt.

DAS ist der "Prozess der Migration" als MASCHINEN-Output (User-Direktive: alles muss als Prozess im
Migrations-Orchestrator abgebildet sein — kein Lead-Augenmass). Jedes Gate ist ein benannter SCHRITT mit
PASS/FAIL + Detail. GO = ALLE Gates gruen. Reproduzierbar, deterministisch, vor JEDEM `--write` zu fahren.

READ-ONLY GEGEN DEN QUELL-VAULT: kein Gate mutiert die Quelle. Die Write-Pfad-Gates (Cutover INV-MIG-11,
disk-rebuild BL-384) laufen auf TEMP-KOPIEN -> die Mechanik wird auf ECHTEN Daten bewiesen, ohne den Vault
anzufassen. (Der echte `--write` bleibt ein separater, gefencter Fresh-Session-Akt, BL-364.)

Die 10 Gates (Mapping auf die BL-Familie):
  1 Discovery/Dedup     INV-MIG-10   cross-root-Dedup, 0 ID-Kollisionen
  2 Roundtrip           INV-MIG-2/3  jedes ready Model roundtrippt (SEGMENT byte- / HEADING parse-identisch)
  3 Vollstaendigkeit    BL-395 (a)   census-W-Definitionen <= atomisierte knots
  4 Content-Erhalt      BL-395 (b)+BL-396  content-loss==0 (SEGMENT byte-identisch / HEADING content-gleich)
  5 Range-Kollaps       BL-391       0 merged Range-Bloecke (### W16-W19)
  6 Schema              truth_schema 0 ERROR in den ready-Truths
  7 Quarantaene-Determ. BL-395       ready+quarantine==total, jede Quarantaene mit Gruenden (Maschinen-Output)
  8 Cutover-Sicherheit  INV-MIG-11   ready -> verlustfreier Swap; quarantine -> REFUSED; Rollback byte-identisch
  9 Disk-Rebuild        BL-384       ready-Truths rekonstruieren die View aus DEN DATEIEN (byte/parse-identisch)
 10 Dedup-Soundness     R4           Dup-Gruppen sind genuine Cross-File-Kopien (alias-kollabierbar, kein Merge-Loss)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

import truth_atomizer as ta
import truth_cutover as tcut
import truth_migrate_orchestrator as orch
import truth_readiness_report as rr


def _gate(step: int, name: str, ok: bool, detail) -> dict:
    return {"step": step, "name": name, "pass": bool(ok), "detail": detail}


def dedup_sound(dd: dict) -> bool:
    """R4-Kollaps-Verlustfreiheit: jede content-hash-Dup-Gruppe ist byte-identisch und
    verlustfrei zu (canonical + (n-1) Aliase) kollabierbar — fuer JEDE Gruppengroesse (n>=2),
    nicht nur Paare. Pruefung = alias-plan-Vollstaendigkeit:
    collapsible_to_alias == duplicate_members - duplicate_groups.
    (BL-395-Fix: alt `groups==collapsible` schlug faelschlich bei n>=3 fehl — das war
    algebraisch "jede Gruppe hat GENAU 2 Mitglieder". Die echte Loss=0-Garantie ist, dass
    der Alias-Plan jede Dup-Gruppe auf 1 kanonische + (n-1) Aliase abbildet, also genau
    `members - groups` kollabierbare Aliase entstehen — fuer beliebige Gruppengroesse.)"""
    members = dd.get("duplicate_members", 0)
    groups = dd.get("duplicate_groups", 0)
    collapsible = dd.get("collapsible_to_alias", 0)
    return collapsible == members - groups


def _content_lossless(result: dict) -> bool:
    """BL-396/BL-395(b): rekonstruiert die View des ready Models den Quell-Content verlustfrei?
    SEGMENT (view_mode==verbatim): build_segment_view == Quell-Text BYTE-identisch.
    HEADING: build_model_view ist content-gleich (Whitespace-norm) zum Quell-Body."""
    truths = result.get("_truths") or []
    text = Path(result["model"]).read_text(encoding="utf-8", errors="replace")
    if any(t.get("view_mode") == "verbatim" for t in truths):
        return ta.build_segment_view(sorted(truths, key=lambda t: t.get("seq", 0))) == text
    body = ta._body_without_frontmatter(text).strip()
    return ta._content_preserved(ta.build_model_view(truths), body)


def run_gates(vault: Optional[Path], repo_models: Optional[Path], *, jobs: int = 4,
              cutover_sample: int = 3) -> dict:
    """Faehrt die ganze Gate-Strasse. READ-ONLY gegen den Quell-Vault. Returns Schritt-fuer-Schritt-Report."""
    results = rr.collect(vault, repo_models, jobs)
    truths = [t for r in results for t in r.get("_truths", [])]
    rep = orch.run(vault, repo_models, mode="global", jobs=jobs)
    ready = [r for r in results if r.get("ready")]
    quarantined = [r for r in results if not r.get("ready")]

    steps: list[dict] = []

    # ── Gate 1: Discovery / Dedup / ID-Kollisionen (INV-MIG-10) ──
    import truth_verify as tv
    ver = tv.verify_all(truths)
    steps.append(_gate(1, "discovery_dedup_inv_mig_10", ver["id_collision_count"] == 0,
                        {"id_collisions": ver["id_collision_count"], "models": len(results)}))

    # ── Gate 2: Roundtrip (INV-MIG-2/3) — ueber die READY-Menge (die wir schreiben werden; Quarantaene
    #    faellt roundtrip by-design, das pruefen Gate 7/8). ──
    rt_fails = [r["model"] for r in ready if not r.get("roundtrip_ok")]
    steps.append(_gate(2, "roundtrip_inv_mig_2_3", not rt_fails, {"fails": len(rt_fails), "sample": rt_fails[:10]}))

    # ── Gate 3: Vollstaendigkeit / census (BL-395 a) — READY-Menge ──
    incomplete = [r["model"] for r in ready if not r.get("complete", True)]
    steps.append(_gate(3, "completeness_census_bl395a", not incomplete, {"incomplete": len(incomplete)}))

    # ── Gate 4: Content-Erhalt (BL-395 b + BL-396) — DER Verlustfrei-Gate ──
    content_losers = [r["model"] for r in ready if not _content_lossless(r)]
    steps.append(_gate(4, "content_preservation_bl395b_bl396", not content_losers,
                       {"content_loss_models": len(content_losers), "sample": content_losers[:10],
                        "ready_checked": len(ready)}))

    # ── Gate 5: Range-Kollaps (BL-391) — READY-Menge (ein ready-aber-kollabiertes Model schriebe einen
    #    merged Blob; ein kollabiertes Quarantaene-Model wird ohnehin nicht geschrieben). ──
    rc = [r["model"] for r in ready if r.get("range_collapsed")]
    steps.append(_gate(5, "range_collapse_bl391", not rc, {"range_collapse_models": len(rc), "sample": rc[:10]}))

    # ── Gate 6: Schema (truth_schema, 0 ERROR) ──
    schema_err = sum(r.get("schema_errors", 0) for r in ready)
    steps.append(_gate(6, "schema_clean", schema_err == 0, {"schema_errors": schema_err}))

    # ── Gate 7: Quarantaene-Determinismus (BL-395, Maschinen-Output) ──
    q_have_reasons = all(orch.quarantine_reasons(r) for r in quarantined)
    partition_ok = (len(ready) + len(quarantined) == len(results))
    steps.append(_gate(7, "quarantine_determinism_bl395", q_have_reasons and partition_ok,
                       {"ready": len(ready), "quarantine": len(quarantined), "total": len(results),
                        "every_quarantine_has_reasons": q_have_reasons,
                        "quarantine_list": [{"model": Path(r["model"]).name, "reasons": orch.quarantine_reasons(r)}
                                            for r in quarantined]}))

    # ── Gate 8: Cutover-Sicherheit (INV-MIG-11 + refuse) — auf TEMP-Kopien ──
    refused = 0
    refuse_fail = []
    with tempfile.TemporaryDirectory() as td:
        for i, r in enumerate(quarantined):
            src = Path(r["model"])
            tmp = Path(td) / f"q{i}" / "2_Model" / src.name
            tmp.parent.mkdir(parents=True)
            before = src.read_bytes()
            tmp.write_bytes(before)
            res = tcut.cutover_model(tmp, "BL-q")
            if res.get("cutover") is False and tmp.read_bytes() == before and not (tmp.parent / "_legacy").exists():
                refused += 1
            else:
                refuse_fail.append(src.name)
        rollback_ok = 0
        rollback_fail = []
        for i, r in enumerate(ready[:max(0, cutover_sample)]):
            src = Path(r["model"])
            tmp = Path(td) / f"r{i}" / "2_Model" / src.name
            tmp.parent.mkdir(parents=True)
            original = src.read_bytes()
            tmp.write_bytes(original)
            cm = tcut.cutover_model(tmp, "BL-r")
            tcut.rollback_model(tmp, tmp.parent / "_legacy")
            if cm.get("cutover") and tmp.read_bytes() == original:
                rollback_ok += 1
            else:
                rollback_fail.append(src.name)
    g8 = (refused == len(quarantined)) and (not rollback_fail) and (rollback_ok == min(cutover_sample, len(ready)))
    steps.append(_gate(8, "cutover_safety_inv_mig_11", g8,
                       {"quarantine_refused": f"{refused}/{len(quarantined)}", "refuse_fail": refuse_fail,
                        "rollback_byte_identical": f"{rollback_ok}/{min(cutover_sample, len(ready))}",
                        "rollback_fail": rollback_fail}))

    # ── Gate 9: Disk-Rebuild (BL-384) — Truths rekonstruieren die View aus DEN DATEIEN ──
    rebuild_ok = 0
    rebuild_fail = []
    with tempfile.TemporaryDirectory() as td:
        for i, r in enumerate(ready):
            truths_r = r.get("_truths") or []
            text = Path(r["model"]).read_text(encoding="utf-8", errors="replace")
            outdir = Path(td) / f"m{i}"
            ta.write_truths(truths_r, outdir)
            rebuilt = ta.rebuild_view_from_truths_dir(outdir)
            if any(t.get("view_mode") == "verbatim" for t in truths_r):
                ok = (rebuilt == text)                                    # byte-identisch
            else:
                ok = (rebuilt == ta.build_model_view(truths_r))           # disk == in-memory View
            if ok:
                rebuild_ok += 1
            else:
                rebuild_fail.append(Path(r["model"]).name)
    steps.append(_gate(9, "disk_rebuild_bl384", not rebuild_fail,
                       {"rebuilt_ok": f"{rebuild_ok}/{len(ready)}", "fail_sample": rebuild_fail[:10]}))

    # ── Gate 10: Dedup-Soundness (R4) ──
    dd = rep["dedup"]
    # BL-395: zertifiziert alias-plan-Verlustfreiheit (collapsible == members - groups), NICHT mehr
    # `groups == collapsible` (das forderte faelschlich n==2 pro Gruppe und schlug bei n>=3 byte-
    # identischen Dup-Gruppen fehl, obwohl diese verlustfrei alias-kollabierbar sind). Siehe dedup_sound().
    sound = dedup_sound(dd)
    steps.append(_gate(10, "dedup_soundness_r4", sound,
                       {"duplicate_groups": dd.get("duplicate_groups"),
                        "duplicate_members": dd.get("duplicate_members"),
                        "collapsible_to_alias": dd.get("collapsible_to_alias")}))

    go = all(s["pass"] for s in steps)
    return {
        "vault": str(vault) if vault else None,
        "models": len(results), "ready": len(ready), "quarantine": len(quarantined),
        "knots": sum(r["knots"] for r in results),
        "gates_passed": sum(1 for s in steps if s["pass"]),
        "gates_total": len(steps),
        "extraction_go": go,                       # GO fuer die read-only Extraktion (alle Gates gruen)
        "write_fenced": "Cutover-`--write` bleibt separater Fresh-Session-Akt (BL-364) + Owner-Scope-out der Quarantaene + DCS quiescenz-gated.",
        "steps": steps,
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="truth_gate_check",
                                description="BL-309 Pre-Flight Gate-Strasse (read-only; Schritt fuer Schritt)")
    p.add_argument("--vault", type=Path, default=None)
    p.add_argument("--repo-models", type=Path, default=None)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--cutover-sample", type=int, default=3, help="Anzahl ready-Models fuer den End-zu-End Rollback-Beweis (temp)")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    rep = run_gates(args.vault, args.repo_models, jobs=args.jobs, cutover_sample=args.cutover_sample)
    print(f"=== Truth-Migration Gate-Strasse — {rep['vault']} ===")
    print(f"Models: {rep['models']}  ready: {rep['ready']}  quarantine: {rep['quarantine']}  Knoten: {rep['knots']}")
    for s in rep["steps"]:
        mark = "PASS" if s["pass"] else "FAIL"
        print(f"  [{mark}] Gate {s['step']:>2}  {s['name']}")
        if not s["pass"]:
            print(f"          -> {s['detail']}")
    print(f"\nGates: {rep['gates_passed']}/{rep['gates_total']}  EXTRACTION-GO (read-only): {rep['extraction_go']}")
    print(f"[{rep['write_fenced']}]")
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report: {args.out}")
    return 0 if rep["extraction_go"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
