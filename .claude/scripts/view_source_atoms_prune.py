#!/usr/bin/env python3
"""
view_source_atoms_prune.py — BL-491 G3-rest batch tool.

Surgically removes the NON-resolving (stale) `source_atoms:` entries from VIEW
frontmatters. The 4 parking-lot views (BL-387/459/474/477) carry frontmatter
`source_atoms` entries that are BL-folder-relative A-Pipeline stage docs
(`3_Spec/BL-X_Spec.md`, `2_Model/BL-X_Model.md`, ...) — wrong substrate, non-resolving
from the vault root. This tool clears those stale refs so a separate backfill step
(view_source_atoms_materialize) can ground the emptied views in their OWN-BL atoms.

FENCE — VIEW-FILES ONLY, FRONTMATTER ONLY:
  - Only ever writes `view_path`. NEVER opens / creates / touches an atom file or
    `_meta_truths/`. Atom mtimes stay unchanged.
  - The rewrite is SURGICAL + FRONTMATTER-SCOPED: it locates the `source_atoms:` block
    ONLY within the first `---`...`---` fence and NEVER touches body `- ` lines
    (e.g. a `## Verwandte Wahrheiten` section of `- Verwandt: W1 ...` summary lines).
    The body is preserved byte-for-byte. dry-run is the default and writes nothing.
    Idempotent.

Public API:
    read_source_atoms(view_path) -> list[str]
    _rewrite_source_atoms_block(content, new_atoms) -> str
    prune_unresolved_source_atoms(view_path, vault, *, write) -> dict
    run(vault, *, write, views=None) -> dict
    main(argv) -> int
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml  # PyYAML (available); robustly parses source_atoms frontmatter
except ImportError:  # pragma: no cover - regex fallback covers absence
    yaml = None  # type: ignore[assignment]

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from view_node_predicate import is_view_node  # noqa: E402

_KEY = "source_atoms:"


# ──────────────────────────────────────────────────────────────────────────────
# Frontmatter reading
# ──────────────────────────────────────────────────────────────────────────────
def _read_frontmatter_text(view_path) -> str:
    """Return the raw YAML frontmatter block (between the first two `---`),
    or "" when no well-formed frontmatter is present / file unreadable.

    Same shape as view_source_atoms_materialize._read_frontmatter_text — universal
    newlines (read_text) so CRLF and LF are handled uniformly."""
    try:
        content = Path(view_path).read_text(encoding="utf-8")
    except OSError:
        return ""
    if not content.startswith("---"):
        return ""
    end = content.find("\n---", 3)
    if end == -1:
        return ""
    return content[3:end]


def read_source_atoms(view_path) -> list[str]:
    """Parse the frontmatter and return the `source_atoms` list (path strings),
    or [] when absent / empty / malformed.

    YAML-first (tolerant of the real-vault UNINDENTED block sequence, the indented
    block sequence, and the inline flow list), with a line-scan fallback when PyYAML
    is unavailable.
    """
    fm = _read_frontmatter_text(view_path)
    if not fm:
        return []

    # Primary: real YAML parse — handles indented + unindented block sequences
    # and inline flow lists uniformly.
    if yaml is not None:
        try:
            data = yaml.safe_load(fm)
        except Exception:
            data = None
        if isinstance(data, dict):
            sa = data.get("source_atoms")
            if isinstance(sa, list):
                return [str(x) for x in sa]
            return []
        # Not a mapping -> treat as no usable frontmatter.
        return []

    # Fallback (YAML unavailable): line scan accepting a `source_atoms:` key
    # followed by `- ` items at ANY indentation (including column 0).
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith(_KEY):
            continue
        inline = stripped[len(_KEY):].strip()
        if inline:
            if inline in ("[]", "null", "~", "{}"):
                return []
            if inline.startswith("[") and inline.endswith("]"):
                inner = inline[1:-1].strip()
                if not inner:
                    return []
                return [
                    x.strip().strip('"').strip("'")
                    for x in inner.split(",")
                    if x.strip()
                ]
            return [inline]
        out: list[str] = []
        for nxt in lines[i + 1:]:
            ls = nxt.lstrip()
            if ls.startswith("- "):
                out.append(ls[2:].strip())
            else:
                break
        return out
    return []


# ──────────────────────────────────────────────────────────────────────────────
# Surgical, frontmatter-scoped block rewrite
# ──────────────────────────────────────────────────────────────────────────────
def _rewrite_source_atoms_block(content: str, new_atoms: list[str]) -> str:
    """Surgically replace (or remove) the `source_atoms:` block, FRONTMATTER ONLY.

    - Locate the `source_atoms:` key line within the frontmatter (between the first
      two `---` fences only). Body `- ` lines are NEVER considered.
    - Consume its block = the key line + following list-item lines (stripped form
      starts with `- `).
    - new_atoms non-empty -> replace with `source_atoms:` + one column-0 `- <atom>`
      line per atom, using the file's detected newline style (CRLF vs LF).
    - new_atoms empty -> REMOVE the whole block (key line + items) so the view has
      no `source_atoms` key.
    - Everything else (other FM fields, the `---` fences, the entire body) is
      preserved byte-for-byte.
    - No `source_atoms:` key (or no frontmatter) -> content returned unchanged.

    `nl.join(content.split(nl)) == content` exactly, so untouched lines (the whole
    body) round-trip byte-for-byte.
    """
    if not content.startswith("---"):
        return content

    nl = "\r\n" if "\r\n" in content else "\n"
    lines = content.split(nl)

    # Opening fence must be the first line.
    if not lines or lines[0].strip() != "---":
        return content

    # Locate the CLOSING fence -> bounds the frontmatter (keys live in lines[1:close]).
    close = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close = i
            break
    if close is None:
        return content

    # Locate the `source_atoms:` key line WITHIN the frontmatter only.
    key_idx = None
    for i in range(1, close):
        if lines[i].strip().startswith(_KEY):
            key_idx = i
            break
    if key_idx is None:
        return content

    # Consume the block: key line + following column-0/indented `- ` item lines,
    # never crossing the closing fence (so body `- ` lines stay untouched).
    end_idx = key_idx + 1
    while end_idx < close and lines[end_idx].lstrip().startswith("- "):
        end_idx += 1

    if new_atoms:
        replacement = ["source_atoms:"] + [f"- {a}" for a in new_atoms]
    else:
        replacement = []

    new_lines = lines[:key_idx] + replacement + lines[end_idx:]
    return nl.join(new_lines)


# ──────────────────────────────────────────────────────────────────────────────
# Prune (single view)
# ──────────────────────────────────────────────────────────────────────────────
def prune_unresolved_source_atoms(view_path, vault, *, write) -> dict:
    """Remove the non-resolving `source_atoms` entries from one view.

    An entry resolves iff `(vault / entry).exists()`. kept preserves order; removed
    are the non-resolving entries (also order-preserving). Idempotent: when nothing
    changes -> action "noop", no write. Otherwise write=True -> action "pruned"
    (rewrites ONLY view_path), write=False -> action "dry-run" (no write).
    """
    view_path = Path(view_path)
    vault = Path(vault)

    atoms = read_source_atoms(view_path)
    kept = [a for a in atoms if (vault / a).exists()]
    removed = [a for a in atoms if a not in kept]
    changed = kept != atoms

    result = {
        "view": str(view_path),
        "n_before": len(atoms),
        "n_kept": len(kept),
        "n_removed": len(removed),
        "removed": removed,
        "changed": changed,
        "action": "noop",
    }

    if not changed:
        return result

    if write:
        content = view_path.read_text(encoding="utf-8")
        new = _rewrite_source_atoms_block(content, kept)
        view_path.write_text(new, encoding="utf-8")
        result["action"] = "pruned"
    else:
        result["action"] = "dry-run"
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Discovery + batch run
# ──────────────────────────────────────────────────────────────────────────────
def _resolve_explicit_views(vault: Path, views) -> list[Path]:
    """Map an explicit `views` list (vault-rel or absolute paths) to abs Paths."""
    out: list[Path] = []
    for v in views:
        p = Path(v)
        if not p.is_absolute():
            p = vault / p
        out.append(p)
    return out


def _scan_unresolved_views(vault: Path) -> list[Path]:
    """All is_view_node views under vault that carry at least one NON-resolving
    `source_atoms` entry (the prune targets when no explicit list is given)."""
    out: list[Path] = []
    if not vault.is_dir():
        return out
    for p in sorted(vault.rglob("*.md")):
        if not is_view_node(str(p), str(vault)):
            continue
        atoms = read_source_atoms(p)
        if not atoms:
            continue
        if any(not (vault / a).exists() for a in atoms):
            out.append(p)
    return out


def run(vault, *, write, views=None) -> dict:
    """Batch prune.

    views given  -> operate on EXACTLY those (vault-rel or absolute paths).
    views None   -> scan all is_view_node views and prune those with unresolved refs.

    Returns {vault, write, results:[per-view dict], total_removed, views_changed}.
    """
    vault = Path(vault)
    if views is not None:
        targets = _resolve_explicit_views(vault, views)
    else:
        targets = _scan_unresolved_views(vault)

    results: list[dict] = []
    total_removed = 0
    views_changed = 0
    for v in targets:
        res = prune_unresolved_source_atoms(v, vault, write=write)
        results.append(res)
        total_removed += res["n_removed"]
        if res["changed"]:
            views_changed += 1

    return {
        "vault": str(vault),
        "write": write,
        "results": results,
        "total_removed": total_removed,
        "views_changed": views_changed,
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Prune NON-resolving (stale) source_atoms refs from view "
        "frontmatters (BL-491 G3-rest). VIEW-FILES ONLY. Default DRY-RUN."
    )
    parser.add_argument("--vault", required=True, help="Path to vault root")
    parser.add_argument(
        "--write", action="store_true", help="Destructive write (default: dry-run)"
    )
    parser.add_argument(
        "--view",
        action="append",
        default=None,
        help="Explicit target view (vault-rel or absolute). Repeatable. "
        "When omitted, all view nodes with unresolved source_atoms are scanned.",
    )
    parser.add_argument("--out", default=None, help="Write run report as JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress summary print")
    args = parser.parse_args(argv)

    vault = Path(args.vault)
    if not vault.is_dir():
        print(f"ERROR: vault is not a directory: {vault}", file=sys.stderr)
        return 2

    result = run(vault, write=args.write, views=args.view)

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    if not args.quiet:
        mode = "WRITE" if result["write"] else "DRY-RUN"
        print(
            f"[view_source_atoms_prune] {mode} vault={result['vault']} "
            f"views_changed={result['views_changed']} "
            f"total_removed={result['total_removed']}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
