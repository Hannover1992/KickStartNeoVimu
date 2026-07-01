#!/usr/bin/env python3
"""
truth_pilot_cutover.py — der EXPLIZITE, gefencte Pilot-Cutover-Treiber (BL-385/386, PHASE B).

DRY-RUN by DEFAULT: ohne `--confirm` wird NICHTS geschrieben — es kommt nur der Plan (welche Models,
welche ausgeschlossen + Grund). Das ist die turnkey-Vorbereitung; der echte Write ist der bewusste
Fresh-Session-Akt MIT Vault-Backup (BL-364).

Sicherheits-Schichten (alle aktiv):
  1. INV-MIG-GATE: die Gate-Strasse (truth_gate_check) MUSS EXTRACTION-GO=True liefern, sonst Abbruch.
  2. --confirm ist PFLICHT fuer jeden Write (Default = Dry-Run-Plan, 0 Mutation).
  3. Owner-Scope-out: die genuine no-W-def Quarantaene (DEFAULT_EXCLUDE) wird EXPLIZIT exkludiert —
     KEIN census==0-Auto-Exclude (das brachte den Silent-Loss-Blindfleck zurueck; BL-395/BL-396).
  4. active_bls: aktive BLs werden ausgeschlossen (kein Cutover unter laufender Arbeit).
  5. Backup: cutover_model sichert jedes Original byte-genau nach {model.parent}/_legacy (INV-MIG-11).
  6. --limit: Pilot-Trio (erste N) vor der Voll-Welle.

Der Orchestrator (truth_migrate_orchestrator) bleibt absichtlich READ-ONLY (--write = No-Op-Fence);
DIESER Treiber ist der EINE, klar gegatete, dry-run-default Write-Pfad. NIE aus geladenem/compact-Kontext
mit --confirm fahren — nur frische Session + Backup.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path
from typing import Optional

import truth_atomize_batch as batch
import truth_cutover as tcut
import truth_gate_check as gc
import truth_migrate_orchestrator as orch

# Die 8 genuine no-extractable-W-def Models (BL-395/BL-396, Owner-Scope-out 2026-06-17). EXPLIZITE Liste
# (Basename ohne .md) — NICHT census==0-Auto-Exclude. Anpassbar per --exclude / --exclude-file.
DEFAULT_EXCLUDE = [
    "BacklogItem-Schema_Model",
    "Sprachnotiz_Patrick_Model",
    "stage_system_vault_zentral_loop_Model",
    "BL-199_Model",
    "BL-201_Model",
    "BL-208_Model",
    "adherence_research",
    "BL-372_Model",
]


def _results(vault, repo_models, jobs):
    models = [str(m) for m in batch.discover_models(vault, repo_models)]
    if jobs <= 1:
        return [orch.process_bl_unit(m) for m in models]
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(orch.process_bl_unit, models))


def plan(vault: Optional[Path], repo_models: Optional[Path] = None, *,
         exclude=None, active_bls=(), jobs: int = 4) -> dict:
    """Dry-Run-Plan: write_scope (ready, NICHT exkludiert, NICHT aktiv) + skipped (mit Grund). KEIN Write."""
    exclude = set(DEFAULT_EXCLUDE if exclude is None else exclude)
    active = set(active_bls)
    write_scope, skipped = [], []
    for r in _results(vault, repo_models, jobs):
        name = Path(r["model"]).stem
        if not r.get("ready"):
            skipped.append({"model": r["model"], "reason": "quarantine:" + ",".join(orch.quarantine_reasons(r))})
        elif name in exclude:
            skipped.append({"model": r["model"], "reason": "owner_scope_out"})
        elif any(b and b in r["model"] for b in active):
            skipped.append({"model": r["model"], "reason": "active_bl"})
        else:
            write_scope.append({"model": r["model"], "ns": r["ns"]})
    return {"total": len(write_scope) + len(skipped), "scope_count": len(write_scope),
            "skipped_count": len(skipped), "write_scope": write_scope, "skipped": skipped}


# Default-Root fuer den Repo-Meta-Self-Scope (Owner-Bootstrap): _meta_truths UNTER dem Vault.
# Vault-only-Routing statt co-located, damit der Selbst-Cutover die Original-Models nicht in-place anfasst.
DEFAULT_META_ROOT = "_meta_truths"


def _resolve_truths_root(vault: Optional[Path], truths_root, repo_meta_self: bool):
    """Loest das Ziel-Root auf: expliziter truths_root gewinnt; sonst bei repo_meta_self der
    Default _meta_truths unter dem Vault; sonst None (= co-located Default in cutover_model)."""
    if truths_root is not None:
        return Path(truths_root)
    if repo_meta_self:
        base = Path(vault) if vault is not None else Path(".")
        return base / DEFAULT_META_ROOT
    return None


def _model_target(root: Path, model_path) -> tuple:
    """Kollisionsfreier truths_dir + legacy_dir je Model UNTER root. Pro Model ein eigener
    Unter-Pfad (Stem), damit zwei Models NIE in denselben Ziel-Ordner schreiben."""
    stem = Path(model_path).stem
    sub = root / stem
    return sub / "truths", sub / "_legacy"


def execute(vault: Optional[Path], repo_models: Optional[Path] = None, *, confirm: bool = False,
            limit: Optional[int] = None, exclude=None, active_bls=(), jobs: int = 4,
            require_gate_go: bool = True, truths_root=None, repo_meta_self: bool = False,
            bootstrap_confirm: bool = False) -> dict:
    """Cutover-Lauf. confirm=False (Default) -> Dry-Run-Plan, 0 Mutation. confirm=True -> cutover_model
    pro Model im Scope (mit _legacy-Backup). require_gate_go=True -> Abbruch wenn Gate-Strasse != GO.

    Vault-only-Routing (BL-385): bei gesetztem truths_root (oder repo_meta_self) wird je Model ein
    kollisionsfreier Ziel-Pfad UNTER dem Root an cutover_model durchgereicht (statt co-located). Ohne
    Ziel bleibt der Aufruf parameterlos (co-located Default).
    Bootstrap-Gate (BL-385): der Repo-Meta-Self-Scope (repo_meta_self=True) verweigert einen ECHTEN
    Write (confirm=True) refuse-by-default — nur mit bootstrap_confirm=True laeuft er durch. Dry-Run
    (confirm=False) ist fuer die Selbst-Klasse jederzeit erlaubt (kein Gate)."""
    root = _resolve_truths_root(vault, truths_root, repo_meta_self)

    # Bootstrap-Selbstbezug-Gate: nur fuer den ECHTEN Write der Selbst-Klasse, refuse-by-default.
    if repo_meta_self and confirm and not bootstrap_confirm:
        return {"aborted": "bootstrap_confirm_required",
                "reason": "repo_meta_self write refused without bootstrap_confirm (BL-385 bootstrap gate)"}

    if require_gate_go:
        gate = gc.run_gates(vault, repo_models, jobs=jobs)
        if not gate["extraction_go"]:
            return {"aborted": "gate_not_go",
                    "failed_gates": [s["name"] for s in gate["steps"] if not s["pass"]]}
    pl = plan(vault, repo_models, exclude=exclude, active_bls=active_bls, jobs=jobs)
    scope = pl["write_scope"][:limit] if limit else pl["write_scope"]
    if not confirm:
        rep = {"dry_run": True, "would_cutover": [s["model"] for s in scope],
               "scope_count": len(scope), "skipped_count": pl["skipped_count"], "plan": pl}
        if root is not None:
            rep["truths_root"] = str(root)
            rep["resolved_targets"] = [str(_model_target(root, s["model"])[0]) for s in scope]
        return rep
    done = []
    for s in scope:
        if root is not None:
            td, ld = _model_target(root, s["model"])
            res = tcut.cutover_model(s["model"], s["ns"], truths_dir=td, legacy_dir=ld)
        else:
            res = tcut.cutover_model(s["model"], s["ns"])
        done.append({"model": s["model"], "cutover": res.get("cutover"),
                     "view_mode": res.get("view_mode"), "legacy": res.get("legacy")})
    return {"dry_run": False, "count": len(done),
            "cutover_ok": sum(1 for d in done if d["cutover"]), "results": done}


def rollback(vault: Optional[Path], repo_models: Optional[Path] = None, *,
             exclude=None, active_bls=(), jobs: int = 4) -> dict:
    """Rollt jedes Model im write_scope byte-identisch aus seinem _legacy-Backup zurueck (INV-MIG-11).
    No-Op fuer Models ohne Backup (noch nicht geschrieben)."""
    pl = plan(vault, repo_models, exclude=exclude, active_bls=active_bls, jobs=jobs)
    out = []
    for s in pl["write_scope"]:
        legacy_dir = Path(s["model"]).parent / "_legacy"
        out.append({"model": s["model"], **tcut.rollback_model(s["model"], legacy_dir)})
    return {"restored": sum(1 for o in out if o.get("restored")), "results": out}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="truth_pilot_cutover",
                                description="BL-385/386 Pilot-Cutover (DRY-RUN default; --confirm fuer Write)")
    p.add_argument("--vault", type=Path, default=None)
    p.add_argument("--repo-models", type=Path, default=None)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--limit", type=int, default=None, help="nur erste N Models (Pilot-Trio: --limit 3)")
    p.add_argument("--exclude-file", type=Path, default=None, help="Datei mit je-Zeile Basename-Scope-out (sonst DEFAULT_EXCLUDE)")
    p.add_argument("--active-bls", default="", help="komma-getrennte aktive BL-Marker (ausgeschlossen)")
    p.add_argument("--confirm", action="store_true", help="ECHTER Write (sonst Dry-Run-Plan). NUR fresh session + Backup!")
    p.add_argument("--rollback", action="store_true", help="write_scope aus _legacy byte-identisch zurueckrollen")
    p.add_argument("--no-gate", action="store_true", help="(nur Debug) Gate-Strasse-GO-Check ueberspringen")
    p.add_argument("--truths-root", type=Path, default=None, help="Welle-2: Vault-Truth-Root fuer Repo-Meta (BL-385, z.B. {vault}/_meta_truths)")
    p.add_argument("--repo-meta-self", action="store_true", help="Welle-2: Repo-Meta-Self-Klasse (.claude/models) -> Vault-Routing + Bootstrap-Gate (BL-385)")
    p.add_argument("--bootstrap-confirm", action="store_true", help="Welle-2: separates Bootstrap-Gate fuer Repo-Meta-Self --confirm (refuse-by-default, BL-385)")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)

    exclude = None
    if args.exclude_file and args.exclude_file.is_file():
        exclude = [l.strip() for l in args.exclude_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    active = [b.strip() for b in args.active_bls.split(",") if b.strip()]

    if args.rollback:
        rep = rollback(args.vault, args.repo_models, exclude=exclude, active_bls=active, jobs=args.jobs)
        print(f"ROLLBACK: {rep['restored']} Models byte-identisch wiederhergestellt.")
    else:
        rep = execute(args.vault, args.repo_models, confirm=args.confirm, limit=args.limit,
                      exclude=exclude, active_bls=active, jobs=args.jobs, require_gate_go=not args.no_gate,
                      truths_root=args.truths_root, repo_meta_self=args.repo_meta_self,
                      bootstrap_confirm=args.bootstrap_confirm)
        if rep.get("aborted"):
            print(f"ABBRUCH: {rep['aborted']}  Rote Gates: {rep.get('failed_gates')}")
            return 2
        if rep.get("dry_run"):
            print(f"DRY-RUN (kein Write). Write-Scope: {rep['scope_count']} Models  Ausgeschlossen: {rep['skipped_count']}")
            print("--- Owner-Scope-out + Quarantaene (NICHT geschrieben) ---")
            for s in rep["plan"]["skipped"]:
                print(f"   SKIP  {Path(s['model']).name:<45} {s['reason']}")
            print(f"\n[DRY-RUN] Fuer den ECHTEN Cutover: --confirm (NUR frische Session + Vault-Backup, BL-364).")
        else:
            print(f"CUTOVER: {rep['cutover_ok']}/{rep['count']} Models geswapped (Original je in _legacy gesichert).")
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Report: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
