#!/usr/bin/env python3
"""
migrate_to_source_provenance.py — Brownfield-Migration auf source_provenance Schema

BL-160 AK-7: Bestehende Vault-Docs ohne source_provenance werden markiert mit:
    source_provenance:
      source: "legacy_pre_BL-160"
      source_kind: "legacy"
      fetched_at: "2026-05-17"

Stufen-Migration:
    Phase 1: Model.md
    Phase 2: Spec.md
    Phase 3: Crumbs + 3_Audit
    Phase 4: alle uebrigen

Roll-Back: --rollback-tag <TAG> entfernt legacy-Frontmatter wieder.

Aufruf:
    python migrate_to_source_provenance.py plan <vault_root>
        Dry-Run: zeigt welche Docs migriert werden wuerden, KEIN Write.

    python migrate_to_source_provenance.py apply <vault_root> [--phase=1|2|3|4|all] [--limit=N]
        Echte Migration. Idempotent (skipt Docs die schon source_provenance haben).

    python migrate_to_source_provenance.py rollback <vault_root> --tag <TAG>
        Entfernt legacy-Frontmatter aller Docs die mit dem Tag migriert wurden.
        TAG = source_provenance.fetched_at (z.B. "2026-05-17").

Exit-Codes:
    0  OK
    1  WARN (Schema-Issues nach Migration)
    2  ERROR (Migration-Failure, Rollback empfohlen)
    3  USAGE / Internal-Error
"""

import sys
import argparse
import re
import shutil
from pathlib import Path
from datetime import date
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install via: pip install pyyaml", file=sys.stderr)
    sys.exit(3)


# Phase-Filter Mapping (Glob-Patterns relative to vault_root)
PHASE_PATTERNS = {
    1: ["**/2_Model/*.md"],
    2: ["**/3_Spec/*.md"],
    3: ["**/Crumbs/*.md", "**/3_Audit/*.md"],
    4: ["**/*.md"],  # alle uebrigen, mit skip-already-migrated
}

LEGACY_MARKER = {
    "source": "legacy_pre_BL-160",
    "source_kind": "legacy",
}


def read_frontmatter(path: Path) -> tuple[Optional[dict], str]:
    """Liest YAML-Frontmatter + Body. Returns (fm_dict, body) oder (None, content)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\n(.+?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None, text
    return (fm if isinstance(fm, dict) else None), m.group(2)


def write_frontmatter_atomic(path: Path, fm: dict, body: str) -> None:
    """Atomic write via tmp-file + rename."""
    new_text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n" + body
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(path)


def has_source_provenance(fm: Optional[dict]) -> bool:
    """True wenn Doc bereits source_provenance hat (idempotent skip)."""
    return fm is not None and "source_provenance" in fm and fm["source_provenance"]


def gather_candidates(vault_root: Path, phase: str) -> list[Path]:
    """Sammelt Markdown-Dateien je nach Phase. Skipt Sources/_pileOfMud_snapshot/ + bereits migrierte."""
    phases = [1, 2, 3, 4] if phase == "all" else [int(phase)]
    found: set[Path] = set()
    for ph in phases:
        for pattern in PHASE_PATTERNS[ph]:
            for p in vault_root.glob(pattern):
                rel = str(p.relative_to(vault_root)).replace("\\", "/")
                if "Sources/_pileOfMud_snapshot/" in rel:
                    continue
                found.add(p)
    return sorted(found)


def cmd_plan(vault_root: Path, phase: str = "all") -> int:
    """Dry-Run — zeigt was migriert wuerde."""
    if not vault_root.exists():
        print(f"ERROR: vault_root {vault_root} nicht gefunden", file=sys.stderr)
        return 2
    candidates = gather_candidates(vault_root, phase)
    plan: list[Path] = []
    skipped: int = 0
    for path in candidates:
        fm, _ = read_frontmatter(path)
        if has_source_provenance(fm):
            skipped += 1
            continue
        plan.append(path)
    print(f"Plan (Phase {phase}): {len(plan)} Migration, {skipped} schon migriert (SKIP)")
    for p in plan[:30]:
        print(f"  + {p.relative_to(vault_root)}")
    if len(plan) > 30:
        print(f"  ... und {len(plan) - 30} weitere")
    return 0


def cmd_apply(vault_root: Path, phase: str = "all", limit: Optional[int] = None) -> int:
    """Echte Migration."""
    if not vault_root.exists():
        print(f"ERROR: vault_root {vault_root} nicht gefunden", file=sys.stderr)
        return 2
    today = date.today().isoformat()
    candidates = gather_candidates(vault_root, phase)
    migrated: int = 0
    skipped: int = 0
    failed: int = 0
    for path in candidates:
        if limit is not None and migrated >= limit:
            break
        try:
            fm, body = read_frontmatter(path)
            if fm is None:
                # Datei ohne Frontmatter — Skelett-Strategie: SKIP (kann SB-5 fuellen)
                skipped += 1
                continue
            if has_source_provenance(fm):
                skipped += 1
                continue
            fm["source_provenance"] = {
                **LEGACY_MARKER,
                "fetched_at": today,
            }
            write_frontmatter_atomic(path, fm, body)
            migrated += 1
        except Exception as exc:
            print(f"FAIL: {path}: {exc}", file=sys.stderr)
            failed += 1
    print(f"Migration (Phase {phase}): {migrated} migriert, {skipped} SKIP, {failed} FAIL")
    if failed:
        return 2
    return 0


def cmd_rollback(vault_root: Path, tag: str) -> int:
    """Rollback: entfernt source_provenance Block bei docs die mit `tag` (fetched_at) markiert sind."""
    if not vault_root.exists():
        print(f"ERROR: vault_root {vault_root} nicht gefunden", file=sys.stderr)
        return 2
    reverted: int = 0
    for path in vault_root.rglob("*.md"):
        rel = str(path.relative_to(vault_root)).replace("\\", "/")
        if "Sources/_pileOfMud_snapshot/" in rel:
            continue
        fm, body = read_frontmatter(path)
        if not fm or "source_provenance" not in fm:
            continue
        sp = fm.get("source_provenance") or {}
        if sp.get("source") == LEGACY_MARKER["source"] and str(sp.get("fetched_at")) == tag:
            del fm["source_provenance"]
            write_frontmatter_atomic(path, fm, body)
            reverted += 1
    print(f"Rollback (tag={tag}): {reverted} Docs zurueckgesetzt")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="migrate_to_source_provenance",
        description="BL-160 AK-7 SB-4 SKELETT — Brownfield-Migration",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Dry-Run")
    p_plan.add_argument("vault_root", type=Path)
    p_plan.add_argument("--phase", default="all")

    p_apply = sub.add_parser("apply", help="Echte Migration")
    p_apply.add_argument("vault_root", type=Path)
    p_apply.add_argument("--phase", default="all")
    p_apply.add_argument("--limit", type=int, default=None)

    p_rollback = sub.add_parser("rollback", help="Rollback")
    p_rollback.add_argument("vault_root", type=Path)
    p_rollback.add_argument("--tag", required=True)

    args = parser.parse_args()
    if args.cmd == "plan":
        return cmd_plan(args.vault_root, args.phase)
    if args.cmd == "apply":
        return cmd_apply(args.vault_root, args.phase, args.limit)
    if args.cmd == "rollback":
        return cmd_rollback(args.vault_root, args.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
