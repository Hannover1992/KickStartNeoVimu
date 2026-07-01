#!/usr/bin/env python3
"""cochange_coupling.py — BL-381 AK-2 / BL-342: read-only logische (Co-Commit-)Kopplung aus der Git-Historie.

Kazman SEI-TR 2020: "historical co-commit relations can reveal nonstructural forms of coupling, such as control,
data, timing, and resource-based coupling." Zwei Dateien sind LOGISCH gekoppelt, wenn sie oft im SELBEN Commit
geaendert werden — das enthuellt verborgene Schuld, die statische Analyse (DL/PC) NICHT sieht, UND ist ein
Konflikt-Wahrscheinlichkeits-Praediktor fuer den Parallel-Scheduler (BL-342 Parallel-Suitability).

STRIKT READ-ONLY: liest nur `git log`, schreibt nur den optionalen --out-Report. Mutiert keinen Code/State.

CLI: py -3 cochange_coupling.py [--since DATE] [--top N] [--glob SUBSTR] [--out PATH]
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path


def parse_git_log(text: str) -> list:
    """Parst `git log --name-only --pretty=format:===%H`-Output in Liste von Commit-Datei-Listen.

    Zeile startet mit '===' -> neuer Commit (Rest = Hash). Folgende nicht-leere Zeilen = geaenderte Dateien.
    """
    commits: list = []
    current: list | None = None
    for raw in text.splitlines():
        if raw.startswith("==="):
            current = []
            commits.append(current)
            continue
        f = raw.strip()
        if f and current is not None:
            current.append(f)
    return commits


def cochange_pairs(commits: list, cap: int = 40) -> Counter:
    """Zaehlt sortierte Datei-Paare pro Commit. Commits mit >cap Dateien = SKIP (Bulk-Op = Rauschen,
    kein logisches Kopplungs-Signal). Commits mit <2 Dateien tragen kein Paar bei."""
    pairs: Counter = Counter()
    for files in commits:
        uniq = sorted(set(files))
        if not (2 <= len(uniq) <= cap):
            continue
        for a, b in combinations(uniq, 2):
            pairs[(a, b)] += 1
    return pairs


def file_degree(pairs: Counter) -> Counter:
    """Co-Change-Grad je Datei = Summe der Paar-Counts, in denen sie vorkommt."""
    deg: Counter = Counter()
    for (a, b), n in pairs.items():
        deg[a] += n
        deg[b] += n
    return deg


def _git_log(since: str | None) -> str:
    cmd = ["git", "log", "--name-only", "--pretty=format:===%H"]
    if since:
        cmd.append(f"--since={since}")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout or ""


def _matches_glob(pair: tuple, glob: str | None) -> bool:
    if not glob:
        return True
    return glob in pair[0] or glob in pair[1]


def build_report(pairs: Counter, deg: Counter, top: int, glob: str | None) -> str:
    fp = [(p, n) for p, n in pairs.items() if _matches_glob(p, glob)]
    fp.sort(key=lambda x: x[1], reverse=True)
    lines = ["# Co-Commit-Coupling (BL-381 AK-2 / BL-342, read-only) ", ""]
    lines.append(f"Datei-Paare gesamt: {len(pairs)} · Dateien: {len(deg)}" + (f" · Glob: '{glob}'" if glob else ""))
    lines.append("")
    lines.append(f"## Top-{top} logisch gekoppelte Datei-Paare (Co-Commit-Count)")
    lines.append("| Co-Changes | Datei A | Datei B |")
    lines.append("|---|---|---|")
    for (a, b), n in fp[:top]:
        lines.append(f"| {n} | {a} | {b} |")
    lines.append("")
    lines.append(f"## Top-{top} Dateien nach Co-Change-Grad")
    lines.append("| Grad | Datei |")
    lines.append("|---|---|")
    for f, n in deg.most_common(top):
        lines.append(f"| {n} | {f} |")
    return "\n".join(lines) + "\n"


def main(argv: list) -> int:
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(description="BL-381 read-only Co-Commit-Coupling")
    ap.add_argument("--since", default=None)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--glob", default=None, help="Substring-Filter auf Datei-Paare")
    ap.add_argument("--cap", type=int, default=40, help="Max Dateien/Commit (>cap = Bulk-Skip)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv[1:])

    commits = parse_git_log(_git_log(args.since))
    pairs = cochange_pairs(commits, cap=args.cap)
    deg = file_degree(pairs)
    report = build_report(pairs, deg, args.top, args.glob)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"{len(commits)} Commits, {len(pairs)} Paare -> {args.out}")
    else:
        print(f"({len(commits)} Commits analysiert, cap={args.cap})")
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
