#!/usr/bin/env python3
"""
budget_watch.py — BL-338 / batch_PL3 / PL-338-7 (Budget-Watch, DETECTOR-ONLY, M3).

Binaer-/grosse Artefakte (Screenshots, Presentations, PDFs) sind BY-DESIGN gross — der
Budget-Watch ist ein reiner DETEKTOR fuers Reporting: er weist die GROESSE aus und flaggt
over_budget gegen gc_budgets (falls fuer den Typ ein Budget existiert), HEILT aber NICHTS.

KERN-INVARIANTE (PL-338-7 §read-only, oberster Kanarienvogel G7c): watch_budget
veraendert/loescht/erzeugt KEINE Datei. Es liest ausschliesslich (size via stat). Es ruft
NIEMALS slim/delete o.ae. — das ist die definierende Invariante dieses Moduls.

cwd-STABILITAETS-MANDAT (PL-336-4-Lehre): watch_budget verwendet den uebergebenen `root`
1:1 (Path(root)), NIE cwd-relativ re-interpretiert.

Aufruf:
  python3 .claude/scripts/budget_watch.py ROOT [--typ TYP]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Budget-Registry. Modul-globaler Name `resolve_budget` ist der Monkeypatch-Anker
# in test_budget_watch.py (monkeypatch.setattr(bw, "resolve_budget", ...)).
from gc_budgets import resolve_budget  # noqa: F401


def watch_budget(root: str, typ: str | None = None) -> list:
    """Scannt einen Root rekursiv + meldet je Datei {path, size_bytes, budget, over_budget}.

    DETEKTOR-ONLY: liest nur (stat). over_budget = size > budget, wobei das Budget aus
    resolve_budget(typ) kommt. budget None (kein Budget fuer den Typ / unbekannt) ->
    over_budget immer False, kein Crash (G7d). Veraendert NIE eine Datei (G7c).

    cwd-stabil: der uebergebene `root` wird 1:1 verwendet. (PL-338-7, 2026-06-13)
    """
    base = Path(root)  # 1:1 (cwd-STABIL)
    budget = resolve_budget(typ)  # None -> nie over_budget, kein Crash

    report: list[dict] = []
    if not base.exists():
        return report

    paths = [base] if base.is_file() else sorted(base.rglob("*"))
    for p in paths:
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size  # READ-ONLY: nur Metadaten lesen, nie schreiben
        except OSError:
            continue
        over = budget is not None and size > budget
        report.append({
            "path": str(p),
            "size_bytes": size,
            "budget": budget,
            "over_budget": over,
        })
    return report


def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(description="BL-338 budget_watch — Detector-only Budget-Report")
    ap.add_argument("root")
    ap.add_argument("--typ", default=None)
    ap.add_argument("--format", default="text", choices=("text", "json"))
    args = ap.parse_args(argv)

    report = watch_budget(args.root, typ=args.typ)
    if args.format == "json":
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    for r in report:
        flag = "OVER" if r["over_budget"] else "ok"
        print(f"[{flag}] {r['size_bytes']:>10} B  budget={r['budget']}  {r['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
