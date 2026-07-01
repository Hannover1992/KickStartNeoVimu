#!/usr/bin/env python3
"""
wikilink_materializer.py — BL-450 batch_1 Stage 1 + BL-460 B-3b AK-4

Materializes [[wikilink]] entries into atom Markdown bodies.
Appends links under WIKILINK_SECTION_HEADER (non-destructive, idempotent).

API:
    build_wikilink(dst_atom_path, vault_root, label) -> str
    has_wikilink_section(body) -> bool
    get_existing_wikilinks(body) -> list[str]
    append_wikilinks(atom_path, edges, vault_root) -> int
    is_source_atom_planted(existing_atoms, atom_id) -> bool
    _rebuild_frontmatter_with_source_atoms(raw_fm, new_source_atoms) -> str
    write_source_atoms(view_path, atom_ids, vault_root, *, report_path=None) -> (bool, str)
    main(argv=None) -> int
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# ─── Optional gate imports (fail-open on ImportError) ───
try:
    import write_gate_guard
except ImportError:
    write_gate_guard = None  # type: ignore[assignment]

try:
    import dry_run_reporter
except ImportError:
    dry_run_reporter = None  # type: ignore[assignment]

# ─── Constants (OQ-2-Mitigation) ───
WIKILINK_SECTION_HEADER: str = "## Verwandte Wahrheiten"
WIKILINK_TEMPLATE: str = "[[{rel_path}|{label}]]"

# ─── Pattern to extract wikilink targets ───
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def build_wikilink(dst_atom_path: Path, vault_root: Path, label: str) -> str:
    """Return a [[wikilink]] string for dst_atom_path relative to vault_root."""
    rel = dst_atom_path.relative_to(vault_root)
    rel_str = str(rel).replace("\\", "/")
    return WIKILINK_TEMPLATE.format(rel_path=rel_str, label=label)


def _split_raw_frontmatter(content: str) -> tuple[str, str]:
    """Split content into (raw_frontmatter, body), keeping the frontmatter verbatim.

    Unlike a YAML-parsing split, the frontmatter block is preserved as an opaque
    string (including its closing ``---``) so it can be re-prepended byte-for-byte.
    This is what makes body edits non-destructive to the frontmatter (NFR N5).
    Returns ("", content) when no well-formed frontmatter is present.
    """
    if not content.startswith("---"):
        return "", content
    end_fm = content.find("\n---", 3)
    if end_fm == -1:
        return "", content
    raw_frontmatter = content[: end_fm + 4]  # includes closing ---\n
    body = content[end_fm + 4:]
    return raw_frontmatter, body


def has_wikilink_section(body: str) -> bool:
    """Return True if WIKILINK_SECTION_HEADER is present in body."""
    return WIKILINK_SECTION_HEADER in body


def get_existing_wikilinks(body: str) -> list[str]:
    """Extract all [[link]] targets from the wikilink section block."""
    if not has_wikilink_section(body):
        return []
    # Only look in the section after the header
    section_start = body.index(WIKILINK_SECTION_HEADER)
    section_body = body[section_start:]
    return _WIKILINK_RE.findall(section_body)


def append_wikilinks(atom_path: Path, edges: list[dict], vault_root: Path) -> int:
    """Append wikilinks for edges that are not yet present in atom_path.

    Non-destructive: existing body content above the section is preserved.
    Idempotent: links already present are skipped.

    Returns number of new links written.
    """
    content = atom_path.read_text(encoding="utf-8")

    frontmatter, body = _split_raw_frontmatter(content)

    existing_links = get_existing_wikilinks(body)

    new_lines: list[str] = []
    for edge in edges:
        dst_path_str = edge.get("dst_path")
        ziel = edge.get("ziel")

        if dst_path_str:
            # Legacy/full form: resolve via filesystem path
            dst_path = Path(dst_path_str)
            label = edge.get("label") or ziel or dst_path.stem
            try:
                rel = str(dst_path.relative_to(vault_root)).replace("\\", "/")
            except ValueError:
                rel = dst_path.name

            # Idempotenz: skip if already linked
            if rel in existing_links:
                continue

            link = build_wikilink(dst_path, vault_root, label)
        elif ziel:
            # Real-shape form: only ziel available, build simple [[ziel|label]]
            label = edge.get("label") or ziel
            # Use last segment after "." as display label (e.g. "_meta_truths.W7" -> "W7")
            display = label.split(".")[-1] if "." in label else label
            link = f"[[{ziel}|{display}]]"
            # Idempotenz: skip if ziel is already in existing links
            if ziel in existing_links:
                continue
        else:
            continue

        new_lines.append(f"- Verwandt: {link}")

    if not new_lines:
        return 0

    # Append under section header
    if has_wikilink_section(body):
        body = body.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n"
    else:
        section = f"\n\n{WIKILINK_SECTION_HEADER}\n" + "\n".join(new_lines) + "\n"
        body = body.rstrip("\n") + section

    atom_path.write_text(frontmatter + body, encoding="utf-8")
    return len(new_lines)


def _parse_frontmatter_yaml(content: str) -> dict:
    """Parse YAML frontmatter from content. Returns {} on failure."""
    if not content.startswith("---"):
        return {}
    end_fm = content.find("\n---", 3)
    if end_fm == -1:
        return {}
    yaml_text = content[3:end_fm].strip()
    if not _HAS_YAML:
        return {}
    try:
        parsed = _yaml.safe_load(yaml_text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def _extract_edges(fm: dict) -> list[dict]:
    """Extract edges from frontmatter as list of dicts.

    Tolerates:
    - dict-form with dst_path: {"rel": ..., "ziel": ..., "dst_path": ...}
    - dict-form with ziel only (real-shape): {"rel": ..., "ziel": "NS-B.W7"}
    - string-form: "NS-B.W7" or "[[NS-B.W7]]" -> normalized to {"ziel": ..., "_from_str": True}

    Returns all edges that have at least a ziel or dst_path target.
    dst_path remains supported as legacy/fallback.
    """
    raw_edges = fm.get("edges") or []
    if not isinstance(raw_edges, list):
        return []

    result: list[dict] = []
    for edge in raw_edges:
        if isinstance(edge, dict):
            # Accept edge if it has dst_path OR ziel (real-shape without dst_path)
            if edge.get("dst_path") or edge.get("ziel"):
                result.append(edge)
            # else: dict with neither -> skip
        elif isinstance(edge, str) and edge.strip():
            # String-form: normalize to dict with ziel, stripping [[ ]] if present
            raw = edge.strip()
            ziel = raw.strip("[]").strip()
            if ziel:
                result.append({"ziel": ziel, "_from_str": True})
        # other types: skip silently
    return result


def is_source_atom_planted(existing_atoms: list, atom_id: str) -> bool:
    """Return True if atom_id is already in existing_atoms.

    Mirrors keyword_edge_writer.is_edge_planted: handles heterogeneous lists
    (dict-form with atom_id key, string-form, None) without crashing.

    Args:
        existing_atoms: List from parsed source_atoms: YAML field (may be
                        heterogeneous after manual edits).
        atom_id:        The atom identifier to check for.

    Returns:
        True  — atom already present (idempotent skip)
        False — atom not yet present (should be added)
    """
    for entry in existing_atoms:
        if entry is None:
            continue
        if isinstance(entry, str):
            if entry == atom_id:
                return True
        elif isinstance(entry, dict):
            if entry.get("atom_id") == atom_id:
                return True
        # Other types: ignored
    return False


def _rebuild_frontmatter_with_source_atoms(
    raw_fm: str,
    new_source_atoms: list[str],
) -> str:
    """Rebuild the raw frontmatter string with an updated source_atoms: list.

    Strategy: line-scan replace/append approach (no full YAML round-trip to
    avoid field reordering / comment loss):
    - If "source_atoms:" line exists: replace the entire source_atoms block
      (multi-line list) with the new list.
    - If not: append "source_atoms:\\n  - atom\\n" before closing "---".

    Preserves all other frontmatter fields byte-for-byte (non-destructive).

    Args:
        raw_fm:           The full raw frontmatter block (including both --- delimiters).
        new_source_atoms: Complete merged list (existing + newly added atoms).

    Returns:
        Updated raw frontmatter string.

    Raises:
        ValueError: if raw_fm does not start with ``---`` (no clean frontmatter —
            leading BOM or no frontmatter). Defense-in-depth (BL-491 AC-1 / F-2):
            the bare-block-prepend else-path that prepended a delimiter-less
            ``source_atoms:`` block at byte 0 (corrupting the file) is thereby
            structurally unreachable.
    """
    # ── Defense-in-depth (BL-491 AC-1 / F-2): never operate on non-frontmatter ──
    if not raw_fm.startswith("---"):
        raise ValueError(
            "raw_fm does not start with '---' — refusing to rebuild source_atoms "
            "(would prepend a bare block and corrupt the file)"
        )

    # Build the source_atoms YAML block lines
    new_block_lines: list[str] = ["source_atoms:"]
    for atom in new_source_atoms:
        new_block_lines.append(f"  - {atom}")

    lines = raw_fm.splitlines(keepends=True)

    # Find if source_atoms: key exists
    sa_start: int = -1
    for i, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        if stripped == "source_atoms:" or stripped.startswith("source_atoms:"):
            sa_start = i
            break

    if sa_start >= 0:
        # Find extent of the source_atoms block: the key line + all continuation lines
        # (lines that start with spaces/dashes, i.e. list items)
        sa_end = sa_start + 1
        while sa_end < len(lines):
            l = lines[sa_end]
            stripped = l.rstrip("\r\n")
            # continuation: indented list item
            if stripped.startswith("  ") or stripped.startswith("\t"):
                sa_end += 1
            else:
                break

        # Replace the block
        replacement = [bl + "\n" for bl in new_block_lines]
        lines = lines[:sa_start] + replacement + lines[sa_end:]
    else:
        # Append before closing ---
        # Find the closing --- line
        close_idx = -1
        for i in range(len(lines) - 1, -1, -1):
            stripped = lines[i].rstrip("\r\n")
            if stripped == "---":
                close_idx = i
                break

        insert_lines = [bl + "\n" for bl in new_block_lines]
        if close_idx >= 0:
            lines = lines[:close_idx] + insert_lines + lines[close_idx:]
        else:
            lines = lines + insert_lines

    result = "".join(lines)
    # Ensure no trailing newline was added to the closing ---
    # (keep original style: _split_raw_frontmatter expects "---" at end)
    return result


def write_source_atoms(
    view_path: Path,
    atom_ids: list[str],
    vault_root: Path,
    *,
    report_path: Path | None = None,
    gate_mode: str = "vault",
) -> tuple[bool, str]:
    """Materialize source_atoms: frontmatter + [[wikilink]] body for a view file.

    Idempotent: calling twice with the same atom_ids produces no change on
    the second call (changed=False, reason="already_present").

    Write-Gate integration (fail-open on ImportError):
        Checks write_gate_guard.is_write_gated(vault_root) if available.
        Checks dry_run_reporter.assert_dry_run_before_write(report_path) if
        report_path is not None and module is available.

    Args:
        view_path:    Path to the View .md file to update.
        atom_ids:     List of atom IDs to add.
        vault_root:   Vault root for wikilink relative paths and gate check.
        report_path:  Optional path to prior dry-run JSON report. If None,
                      the dry-run gate is SKIPPED.

    Returns:
        (True,  "changed")           — at least 1 new atom or wikilink written.
        (False, "already_present")   — all atoms already present.
        (False, "BLOCKED: <reason>") — write gated.
        (False, "error: <reason>")   — IO or parse failure.
    """
    # ── Gate 1: write gate (mode-dependent) ───────────────────────────────
    if gate_mode == "target":
        # Per-target mode: check TARGET file for null bytes instead of vault-wide gate
        try:
            if Path(view_path).exists() and Path(view_path).read_bytes().count(0) > 0:
                return (False, f"BLOCKED: target corrupt (null bytes): {view_path}")
        except Exception:
            pass  # fail-open on unexpected read errors (consistent with existing fail-open style)
    else:
        # Default vault mode: vault-wide write gate
        _wgg = write_gate_guard  # module-level attribute (patchable)
        if _wgg is not None:
            try:
                gated, gate_reason = _wgg.is_write_gated(vault_root)
                if gated:
                    return False, f"BLOCKED: {gate_reason}"
            except Exception:
                pass  # fail-open on unexpected errors

    # ── Gate 2: dry_run_reporter (only if report_path given) ───────────────
    if report_path is not None:
        _drr = dry_run_reporter  # module-level attribute (patchable)
        if _drr is not None:
            try:
                ok, drr_reason = _drr.assert_dry_run_before_write(report_path)
                if not ok:
                    return False, f"BLOCKED: no dry-run — {drr_reason}"
            except Exception:
                pass  # fail-open
        else:
            # dry_run_reporter not available — do our own existence check
            try:
                if not Path(report_path).exists():
                    return False, f"BLOCKED: no dry-run — report missing: {report_path}"
            except Exception:
                pass  # fail-open

    # ── Short-circuit: no atom_ids given ──────────────────────────────────
    if not atom_ids:
        return False, "already_present"

    # ── Read view file ──────────────────────────────────────────────────────
    try:
        content = view_path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"error: {exc}"

    raw_fm, body = _split_raw_frontmatter(content)
    fm_dict = _parse_frontmatter_yaml(content)
    existing: list = fm_dict.get("source_atoms") or []
    if not isinstance(existing, list):
        existing = []

    # ── Determine new atoms ────────────────────────────────────────────────
    new_atoms = [a for a in atom_ids if not is_source_atom_planted(existing, a)]

    # ── CHOKE-POINT (BL-491 AC-1 / F-2): refuse on no clean frontmatter ────
    # _split_raw_frontmatter returns raw_fm=="" whenever content does NOT
    # literally start with "---" (leading BOM OR a no-frontmatter view). If we
    # have real work (new_atoms) but no clean "---" frontmatter to append into,
    # writing would prepend a BARE source_atoms: block at byte 0 and corrupt the
    # file. Refuse here, BEFORE any write touches disk.
    if new_atoms and raw_fm == "":
        return (
            False,
            "error: no clean frontmatter — refusing to prepend source_atoms (would corrupt)",
        )

    fm_changed = False
    if new_atoms:
        merged = list(existing) + new_atoms
        # Normalize existing to string form for rebuild
        merged_strs: list[str] = []
        for entry in merged:
            if isinstance(entry, str):
                merged_strs.append(entry)
            elif isinstance(entry, dict):
                aid = entry.get("atom_id")
                if aid:
                    merged_strs.append(str(aid))
            # None: skip
        new_raw_fm = _rebuild_frontmatter_with_source_atoms(raw_fm, merged_strs)
        # Write updated frontmatter + original body
        try:
            view_path.write_text(new_raw_fm + body, encoding="utf-8")
        except OSError as exc:
            return False, f"error: {exc}"
        fm_changed = True

    # ── Append wikilinks to body (idempotent via append_wikilinks) ─────────
    edges = [{"ziel": a} for a in atom_ids]
    try:
        n_links = append_wikilinks(view_path, edges, vault_root)
    except Exception as exc:
        return False, f"error: {exc}"

    changed = fm_changed or (n_links > 0)
    if changed:
        return True, "changed"
    return False, "already_present"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. --vault REQUIRED, --dry-run optional."""
    parser = argparse.ArgumentParser(description="Materialize wikilinks in atom files")
    parser.add_argument("--vault", required=True, help="Path to vault root")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    parser.add_argument("--write", action="store_true", help="Destructive write mode (gated)")
    parser.add_argument(
        "--source-atoms-mode",
        action="store_true",
        help="Activate source_atoms frontmatter writer (BL-460 B-3b AK-4)",
    )
    parser.add_argument("--report", default=None, help="Path to dry-run report for gate check")
    args = parser.parse_args(argv)

    vault_root = Path(args.vault)
    if not vault_root.exists():
        print(f"ERROR: vault path does not exist: {vault_root}", file=sys.stderr)
        return 2

    # ── source-atoms-mode path ─────────────────────────────────────────────
    if args.source_atoms_mode:
        if args.write:
            # Gated write: check gate first
            _wgg = write_gate_guard
            if _wgg is not None:
                try:
                    gated, gate_reason = _wgg.is_write_gated(vault_root)
                    if gated:
                        print(
                            f"[wikilink_materializer] BLOCKED by write gate: {gate_reason}",
                            file=sys.stderr,
                        )
                        return 1
                except Exception:
                    pass  # fail-open

            # Write source_atoms for all .md files that have source_atoms_mode_trigger
            # (In practice, B-4 will call write_source_atoms directly; CLI is a thin wrapper)
            report_path = Path(args.report) if args.report else None
            atoms_written = 0
            for md_file in vault_root.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                fm = _parse_frontmatter_yaml(content)
                # Only process files that have a source_atoms_mode_trigger flag
                if not fm.get("source_atoms_mode_trigger"):
                    continue
                atom_ids_from_fm = fm.get("source_atoms") or []
                if not isinstance(atom_ids_from_fm, list):
                    continue
                atom_ids_strs = [str(a) for a in atom_ids_from_fm if a is not None]
                changed, reason = write_source_atoms(
                    md_file, atom_ids_strs, vault_root, report_path=report_path
                )
                if "BLOCKED" in reason:
                    print(
                        f"[wikilink_materializer] BLOCKED: {reason}",
                        file=sys.stderr,
                    )
                    return 1
                if changed:
                    atoms_written += 1
            print(
                f"[wikilink_materializer] source-atoms-mode write: "
                f"atoms_written={atoms_written} vault={vault_root}"
            )
            return 0
        else:
            # Dry-run source-atoms-mode: preview only
            count = 0
            for md_file in vault_root.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                except OSError:
                    continue
                fm = _parse_frontmatter_yaml(content)
                if fm.get("source_atoms"):
                    count += 1
            print(
                f"[wikilink_materializer] source-atoms-mode dry-run: "
                f"views_with_source_atoms={count} vault={vault_root}"
            )
            return 0

    # ── Legacy wikilink-body path (backward-compatible) ────────────────────
    dry_run: bool = args.dry_run
    atoms_written = 0
    edges_written = 0

    for atom_file in vault_root.rglob("*.md"):
        try:
            content = atom_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        fm = _parse_frontmatter_yaml(content)
        edges = _extract_edges(fm)

        if not edges:
            continue

        if dry_run:
            # In dry-run: count edges that would be written (not yet present)
            _, body = _split_raw_frontmatter(content)
            existing = set(get_existing_wikilinks(body))
            would_write = 0
            for edge in edges:
                dst_path_str = edge.get("dst_path")
                ziel = edge.get("ziel")
                if dst_path_str:
                    dst_path = Path(dst_path_str)
                    try:
                        rel = str(dst_path.relative_to(vault_root)).replace("\\", "/")
                    except ValueError:
                        rel = dst_path.name
                    if rel not in existing:
                        would_write += 1
                elif ziel:
                    if ziel not in existing:
                        would_write += 1
            if would_write > 0:
                atoms_written += 1
                edges_written += would_write
        else:
            try:
                written = append_wikilinks(atom_file, edges, vault_root)
            except Exception:
                continue
            if written > 0:
                atoms_written += 1
                edges_written += written

    print(
        f"[wikilink_materializer] vault={vault_root} "
        f"atoms_written={atoms_written} edges_written={edges_written} dry_run={dry_run}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
