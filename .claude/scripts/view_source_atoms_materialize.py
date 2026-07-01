#!/usr/bin/env python3
"""
view_source_atoms_materialize.py — BL-460 (Lane B) batch tool.

Raises FORWARD view->atom coverage (Capstone-Gate G3): for every substrate-having
VIEW that LACKS a `source_atoms:` block, write the view's OWN-BL truth atoms as
`source_atoms:` plus a `## Verwandte Wahrheiten` wikilink section — VIEW-FILES-ONLY.

Substrate-grounded, NEVER fabricated: the atoms written are exactly the BL's own
`truths/*.md` files (the view's "Quell-Atome"). The keyword-scoring engine
(view_forward_reference) is DEGRADED on the real vault and is deliberately NOT used.

FENCE: writes ONLY view files. Atom / truths files are never touched (their mtimes
stay unchanged — guaranteed by wikilink_materializer.write_source_atoms). dry-run is
the default and writes nothing at all. Idempotent.

Reuse primitives (do not reinvent):
    wikilink_materializer.write_source_atoms(view, atom_paths, vault, gate_mode="target")
    view_node_predicate.is_view_node(path_str, vault_root_str)

Public API:
    bl_of_view(view_path) -> str | None
    own_atoms_for_bl(bl, vault) -> list[str]          # sorted, vault-rel, forward-slash
    view_has_source_atoms(view_path) -> bool
    discover_targets(vault, *, parking_only=False) -> list[dict]
    materialize_view(view_path, vault, *, write, ensure_frontmatter=False) -> dict
    run(vault, *, write=False, parking_only=False, ensure_frontmatter=False) -> dict
    main(argv) -> int

BL-491 follow-on (`--ensure-frontmatter`): for genuinely-frontmatter-less views
(garbage-free after AC-1 but with NO `---` frontmatter), create a minimal DERIVED
(non-fabricated, path-only) frontmatter, then write OWN-BL source_atoms. NEVER touches
corrupt files (reuses view_decorrupt.find_stray_run_end). VIEW-FILES ONLY.
    _view_classify_type(view_rel) -> str
    _view_feature(view_rel) -> str | None
    _minimal_frontmatter_block(view_rel, *, newline="\\r\\n") -> str
    _is_frontmatter_less(view_path) -> bool
    _create_minimal_frontmatter(view_path, vault) -> bool
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml  # PyYAML (available); robustly parses source_atoms frontmatter
except ImportError:  # pragma: no cover - regex fallback covers absence
    yaml = None  # type: ignore[assignment]

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from wikilink_materializer import write_source_atoms  # noqa: E402
from view_node_predicate import is_view_node  # noqa: E402
import view_decorrupt  # noqa: E402  (sibling import; reused by _is_frontmatter_less)

_BL_RE = re.compile(r"BL-\d+")


# ──────────────────────────────────────────────────────────────────────────────
# Substrate helpers
# ──────────────────────────────────────────────────────────────────────────────
def bl_of_view(view_path) -> str | None:
    """Extract the BL id (e.g. "BL-479") from a view path via regex, else None."""
    m = _BL_RE.search(str(view_path))
    return m.group(0) if m else None


def own_atoms_for_bl(bl: str, vault: Path) -> list[str]:
    """Sorted, deduped, vault-relative (forward-slash) paths of every `*.md`
    under any `Backlog/<bl>*/**/truths/` directory. Returns [] if none.

    The `**/truths` glob matches a `truths` dir at any depth, including directly
    under the BL folder (`**` may match zero segments). The trailing `-` in the
    folder pattern keeps BL-001 from also matching BL-0010.
    """
    vault = Path(vault)
    if not vault.is_dir():
        return []
    found: set[str] = set()
    for pattern in (
        f"Backlog/{bl}-*/**/truths/*.md",  # canonical `BL-<NNN>-<slug>` folder(s)
        f"Backlog/{bl}/**/truths/*.md",     # tolerate a slug-less `BL-<NNN>` folder
    ):
        for p in vault.glob(pattern):
            if p.is_file():
                found.add(p.relative_to(vault).as_posix())
    return sorted(found)


def _read_frontmatter_text(view_path) -> str:
    """Return the raw YAML frontmatter block (between the first two `---`),
    or "" when no well-formed frontmatter is present / file unreadable."""
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


def view_has_source_atoms(view_path) -> bool:
    """True iff the view's frontmatter declares a NON-EMPTY `source_atoms:` value.

    Robust across ALL real-vault frontmatter forms:
      - UNINDENTED block sequence (`source_atoms:\\n- a\\n- b`, items at column 0,
        the real-vault format, same YAML style as atom keywords)  -> True
      - INDENTED block sequence (`source_atoms:\\n  - a`, write_source_atoms output) -> True
      - inline flow list (`source_atoms: [a, b]`)                  -> True
      - empty (`source_atoms: []`) / absent / `null` / `~`         -> False
    """
    fm = _read_frontmatter_text(view_path)
    if not fm:
        return False

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
                return len(sa) > 0
            return bool(sa)  # truthy scalar -> present; None/'' -> absent

    # Fallback (YAML unavailable or unparseable): line scan that accepts a
    # `source_atoms:` key followed by at least one `- ` item at ANY indentation
    # (including column 0) before the next top-level key.
    lines = fm.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped == "source_atoms:" or stripped.startswith("source_atoms:")):
            continue
        inline = stripped[len("source_atoms:"):].strip()
        if inline:
            if inline in ("[]", "null", "~", "{}"):
                return False
            if inline.startswith("[") and inline.endswith("]"):
                return bool(inline[1:-1].strip())
            return True  # some scalar/inline value present
        # block form: any `- item` (indented OR column 0) before the next key
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            if nxt.lstrip().startswith("- "):
                return True
            # first non-blank, non-list line ends the block (empty source_atoms)
            break
        return False
    return False


# ──────────────────────────────────────────────────────────────────────────────
# Discovery
# ──────────────────────────────────────────────────────────────────────────────
def _is_parking_view(view: Path) -> bool:
    """A `**/6_PL/*-parking-lot.md` view."""
    return (
        view.name.lower().endswith("-parking-lot.md")
        and view.parent.name.lower() == "6_pl"
    )


def discover_targets(vault: Path, *, parking_only: bool = False) -> list[dict]:
    """Enumerate materialization TARGETS.

    A view is a TARGET iff:
        is_view_node(view, vault) AND own_atoms_for_bl(bl) is non-empty
        AND NOT view_has_source_atoms(view).

    Views are enumerated via `vault.rglob('*.md')` filtered by is_view_node
    (and, when parking_only=True, restricted to `**/6_PL/*-parking-lot.md`).

    Each result dict: {view: <abs Path>, rel: <vault-rel str>, bl: "BL-x",
    own_atoms: [paths], has_sources: bool}.
    """
    vault = Path(vault)
    targets: list[dict] = []
    if not vault.is_dir():
        return targets

    for view in sorted(vault.rglob("*.md")):
        if parking_only and not _is_parking_view(view):
            continue
        if not is_view_node(str(view), str(vault)):
            continue
        bl = bl_of_view(view)
        if not bl:
            continue
        own = own_atoms_for_bl(bl, vault)
        if not own:
            continue
        if view_has_source_atoms(view):
            continue
        targets.append(
            {
                "view": view.absolute(),
                "rel": view.relative_to(vault).as_posix(),
                "bl": bl,
                "own_atoms": own,
                "has_sources": False,
            }
        )
    return targets


# ──────────────────────────────────────────────────────────────────────────────
# Materialization (single view)
# ──────────────────────────────────────────────────────────────────────────────
def _has_clean_frontmatter(view_path) -> bool:
    """True iff the view starts with a well-formed `---` frontmatter block at byte 0
    (no BOM, no stray pre-frontmatter content) with a closing `---`.

    SAFETY (Verifier-Fund 2026-06-26): many real Model/arc42 views are PRE-corrupted —
    they start with stray `source_atoms:` blocks or a BOM BEFORE the real frontmatter.
    For those, write_source_atoms finds no frontmatter and APPENDS another stray block
    at the top -> it worsens the corruption. We refuse to write such views, never worsen
    them; de-corrupting them is a separate fix (view/model generator owner)."""
    try:
        raw = Path(view_path).read_bytes()
    except OSError:
        return False
    if not raw.startswith(b"---"):           # BOM / stray content before frontmatter -> unsafe
        return False
    return b"\n---" in raw[3:]                # has a closing fence


# ──────────────────────────────────────────────────────────────────────────────
# BL-491 follow-on — minimal DERIVED frontmatter for genuinely-frontmatter-less views
# ──────────────────────────────────────────────────────────────────────────────
def _view_classify_type(view_rel: str) -> str:
    """Path-derived view type from the vault-rel path (lowercased parts):
    `/arc42/` -> "arc42", `/6_PL/` -> "parking_lot", basename ends `_model.md`
    -> "model", else "view". NON-fabricated (only path structure)."""
    parts = [p for p in re.split(r"[\\/]+", str(view_rel)) if p]
    lowered = [p.lower() for p in parts]
    if "arc42" in lowered:
        return "arc42"
    if "6_pl" in lowered:
        return "parking_lot"
    base = lowered[-1] if lowered else ""
    if base.endswith("_model.md"):
        return "model"
    return "view"


def _view_feature(view_rel: str) -> str | None:
    """If the vault-rel path is `Backlog/<folder>/...` -> return `<folder>`
    (the BL folder slug, original case). Else None."""
    parts = [p for p in re.split(r"[\\/]+", str(view_rel)) if p]
    if len(parts) >= 2 and parts[0] == "Backlog":
        return parts[1]
    return None


def _minimal_frontmatter_block(view_rel: str, *, newline: str = "\r\n") -> str:
    """Build a minimal, DETERMINISTIC, NON-fabricated frontmatter block (only
    path-derived fields): opening `---`, `type:`, optional `feature:` (omitted
    when None), `view_frontmatter_generated: BL-491`, `edges: []`, closing `---`,
    then ONE blank line. Every line joined by `newline`. Valid YAML; no dates,
    no item_count, no status (those would be fabricated)."""
    typ = _view_classify_type(view_rel)
    feature = _view_feature(view_rel)
    lines = ["---", f"type: {typ}"]
    if feature is not None:
        lines.append(f"feature: {feature}")
    lines += ["view_frontmatter_generated: BL-491", "edges: []", "---"]
    # closing `---` + ONE blank line (an empty line == one more newline)
    return newline.join(lines) + newline + newline


def _is_frontmatter_less(view_path) -> bool:
    """True iff the file does NOT start with `---` AND is NOT corrupt.

    Reuses `view_decorrupt.find_stray_run_end(raw)` (returns not-None iff the file
    has a leading stray `source_atoms:` run = corrupt). This GUARANTEES we NEVER
    treat a still-corrupt file as frontmatter-less (so it never gets frontmatter)."""
    try:
        raw = Path(view_path).read_bytes()
    except OSError:
        return False
    return (not raw.startswith(b"---")) and (
        view_decorrupt.find_stray_run_end(raw) is None
    )


def _create_minimal_frontmatter(view_path, vault) -> bool:
    """Prepend a minimal DERIVED frontmatter block to a genuinely-frontmatter-less
    view. Operates on BYTES — the ORIGINAL raw bytes are preserved byte-for-byte as
    a suffix (body verbatim). VIEW-FILES ONLY.

    No-op (returns False, writes nothing) when the file already has frontmatter OR
    is corrupt (`_is_frontmatter_less` False) -> idempotent. Otherwise detects the
    body newline style (CRLF if the first body line ends `\\r\\n`, else LF), builds
    the block with that newline, writes `block.encode("utf-8") + raw`, returns True.
    """
    view_path = Path(view_path)
    vault = Path(vault)
    if not _is_frontmatter_less(view_path):
        return False
    raw = view_path.read_bytes()
    # Detect body newline style from the first line.
    nl_idx = raw.find(b"\n")
    if nl_idx > 0 and raw[nl_idx - 1: nl_idx] == b"\r":
        nl = "\r\n"
    else:
        nl = "\n"
    try:
        view_rel = view_path.relative_to(vault).as_posix()
    except ValueError:
        view_rel = view_path.as_posix()
    block = _minimal_frontmatter_block(view_rel, newline=nl)
    view_path.write_bytes(block.encode("utf-8") + raw)
    return True


def materialize_view(
    view_path: Path, vault: Path, *, write: bool, ensure_frontmatter: bool = False
) -> dict:
    """Materialize one view's OWN-BL source_atoms.

    write=False (dry-run) -> writes NOTHING (action "dry-run").
    0 own atoms          -> writes NOTHING (action "skip").
    write=True           -> wikilink_materializer.write_source_atoms(..., gate_mode="target"):
        (True,  "changed")          -> action "written",    n_added=len(own_atoms)
        (False, "already_present")  -> action "idempotent", n_added=0
        (False, other)              -> action "skip"/"error" (BLOCKED -> skip), n_added=0
    """
    view_path = Path(view_path)
    vault = Path(vault)
    bl = bl_of_view(view_path)
    own_atoms = own_atoms_for_bl(bl, vault) if bl else []
    n_own = len(own_atoms)

    result = {
        "view": str(view_path),
        "bl": bl,
        "n_own_atoms": n_own,
        "n_added": 0,
        "action": None,
        "reason": None,
        "created_frontmatter": False,
    }

    if n_own == 0:
        result["action"] = "skip"
        result["reason"] = "no_substrate"
        return result

    # BL-491 follow-on control flow. `needs_fm` is True ONLY when the view lacks a
    # clean `---` frontmatter, the mode is ON, AND the file is GENUINELY frontmatter-
    # less (not corrupt — _is_frontmatter_less reuses view_decorrupt). When the mode
    # is OFF (default), needs_fm is False -> behavior EXACTLY unchanged.
    clean = _has_clean_frontmatter(view_path)
    needs_fm = (not clean) and ensure_frontmatter and _is_frontmatter_less(view_path)

    if (not clean) and (not needs_fm):
        # Pre-corrupted view (BOM / stray pre-frontmatter blocks), or mode off:
        # refuse to write, never worsen it. Reported in BOTH dry-run and write modes.
        result["action"] = "skip"
        result["reason"] = "malformed_frontmatter"
        return result

    if not write:
        result["action"] = "dry-run"
        result["reason"] = "would_create_frontmatter" if needs_fm else "dry-run"
        return result

    if needs_fm:
        # Create a minimal DERIVED frontmatter so write_source_atoms has a clean
        # `---` block to write into; the original body is preserved byte-for-byte.
        _create_minimal_frontmatter(view_path, vault)

    changed, reason = write_source_atoms(
        view_path, own_atoms, vault, gate_mode="target"
    )
    result["created_frontmatter"] = needs_fm
    result["reason"] = reason
    if changed:
        result["action"] = "written"
        result["n_added"] = n_own
    elif reason == "already_present":
        result["action"] = "idempotent"
        result["n_added"] = 0
    elif reason.startswith("error"):
        result["action"] = "error"
    else:
        # BLOCKED / any other non-changed outcome
        result["action"] = "skip"
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Batch run
# ──────────────────────────────────────────────────────────────────────────────
def run(
    vault: Path,
    *,
    write: bool = False,
    parking_only: bool = False,
    ensure_frontmatter: bool = False,
) -> dict:
    """Batch over discover_targets, materializing each.

    Returns {vault, targets:N, written:<count written>, dry_run:(not write),
             results:[per-view dict, ...]}.
    """
    vault = Path(vault)
    targets = discover_targets(vault, parking_only=parking_only)
    results: list[dict] = []
    written = 0
    for t in targets:
        res = materialize_view(
            t["view"], vault, write=write, ensure_frontmatter=ensure_frontmatter
        )
        if res["action"] == "written":
            written += 1
        results.append(res)
    return {
        "vault": str(vault),
        "targets": len(targets),
        "written": written,
        "dry_run": (not write),
        "results": results,
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Materialize OWN-BL source_atoms into substrate-having views "
        "lacking them (BL-460, Lane B). Default DRY-RUN."
    )
    parser.add_argument("--vault", required=True, help="Path to vault root")
    parser.add_argument(
        "--write", action="store_true", help="Destructive write (default: dry-run)"
    )
    parser.add_argument(
        "--parking-only",
        action="store_true",
        help="Restrict to **/6_PL/*-parking-lot.md views",
    )
    parser.add_argument(
        "--ensure-frontmatter",
        action="store_true",
        help="Create minimal DERIVED frontmatter for genuinely-frontmatter-less "
        "views before writing source_atoms (default OFF; never touches corrupt files)",
    )
    parser.add_argument("--out", default=None, help="Write run report as JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress summary print")
    args = parser.parse_args(argv)

    vault = Path(args.vault)
    if not vault.is_dir():
        print(f"ERROR: vault is not a directory: {vault}", file=sys.stderr)
        return 2

    result = run(
        vault,
        write=args.write,
        parking_only=args.parking_only,
        ensure_frontmatter=args.ensure_frontmatter,
    )

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    if not args.quiet:
        mode = "DRY-RUN" if result["dry_run"] else "WRITE"
        print(
            f"[view_source_atoms_materialize] {mode} vault={result['vault']} "
            f"targets={result['targets']} written={result['written']}"
            + (f" parking_only" if args.parking_only else "")
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
