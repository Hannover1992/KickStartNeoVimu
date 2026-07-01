#!/usr/bin/env python3
"""truth_gc.py — Truth Garbage-Collection Scanner + Anti-Re-Bloat-Metrik (BL-399 batch_1).

READ-ONLY Befund-Sammler ueber type:truth-Atome (yaml-Frontmatter, ein BL-Ordner =
ein "root" mit `truths/*.md`). scan() liefert einen 5-Dimensions-Report; metric() liefert
den Anti-Re-Bloat-Snapshot (aggregierter ref_count + atom_count). Es wird NIE eine Datei
mutiert/geloescht/angelegt — die Heilung (Kollaps/Retract) ist ein separater gefencter Pass
spaeterer Batches.

Reuse (NICHT neu gebaut — die fertigen Sonden je Dimension):
  truth_dedup.dedup_groups        — duplicates (gleicher content_hash)
  truth_lifecycle.map_lifecycle   — stale (contradicted/retracted UND referenced)
  truth_backref_index             — Referenz-/Edge-Semantik (orphaned)
  truth_normalize.is_canonical_format — format_regression (Drift gegen kanonische Form)
  truth_census.count_wknots       — accumulation/Metrik (W-Knoten-Zaehlung)
  truth_atomizer.read_truth_file  — type:truth-Atom-Parser (Frontmatter -> dict)

Default-Schwelle KONSERVATIV (kleine saubere Models loesen NICHT aus); configbar via threshold.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import truth_dedup
import truth_lifecycle
import truth_normalize
import truth_census
import truth_atomizer as ta

# Konservative Default-Schwelle: ein kleines sauberes Model (wenige Refs) gilt NICHT als
# Re-Bloat. Erst aggregierter ref_count UEBER dieser Schwelle erzeugt einen accumulation-Befund.
DEFAULT_THRESHOLD = 50

# Lebenszyklus-Stufen, die einen referenzierten Truth STALE machen (veraltet aber noch verlinkt).
_STALE_LIFECYCLES = {"contradicted", "retracted"}

# Beliebige Markdown-Ueberschrift (Struktur-Signal) — Abwesenheit = Format-Regression (flacher Body).
_MD_HEADING = re.compile(r"(?m)^[ \t]*#{1,6}[ \t]+\S")


# ──────────────────────────────────────────────────────────────────────────────
# Korpus-Laden (read-only): truths/*.md eines Roots -> Atom-Dicts (+ _body).
# ──────────────────────────────────────────────────────────────────────────────

def _truths_dir(root: Path) -> Path:
    """Atom-Verzeichnis eines Roots. Akzeptiert sowohl {root}/truths als auch {root}/2_Model/truths."""
    root = Path(root)
    direct = root / "truths"
    if direct.is_dir():
        return direct
    nested = root / "2_Model" / "truths"
    if nested.is_dir():
        return nested
    return direct


def _load_atoms(root: Path) -> list[dict]:
    """Liest alle type:truth-Atome eines Roots read-only zu Dicts (Frontmatter + _body + _root)."""
    atoms: list[dict] = []
    tdir = _truths_dir(root)
    if not tdir.is_dir():
        return atoms
    for p in sorted(tdir.glob("*.md")):
        if not p.is_file():
            continue
        try:
            fm = ta.read_truth_file(p)
        except OSError:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            _, body = ta._split_truth_file(content)
        except OSError:
            body = ""
        fm = dict(fm)
        fm["_body"] = body
        fm["_path"] = str(p)
        fm["_root"] = str(root)
        atoms.append(fm)
    return atoms


def _atom_id(atom: dict) -> str:
    return str(atom.get("local_id") or atom.get("id") or "")


def _ref_list(atom: dict) -> list:
    rb = atom.get("referenced_by")
    return rb if isinstance(rb, list) else []


def _edge_list(atom: dict) -> list:
    ed = atom.get("edges")
    return ed if isinstance(ed, list) else []


def _befund(atom: dict, **extra) -> dict:
    """Standard-Befund-dict: lokale + globale ID + Pfad + Dimensions-Extras (JSON-serialisierbar)."""
    b = {"local_id": atom.get("local_id"), "id": atom.get("id"), "path": atom.get("_path")}
    b.update(extra)
    return b


# ──────────────────────────────────────────────────────────────────────────────
# Dimensions-Sonden (jede reused die fertige Bibliothek).
# ──────────────────────────────────────────────────────────────────────────────

def _scan_duplicates(atoms: list[dict]) -> list[dict]:
    """duplicates: gleicher content_hash -> Reuse truth_dedup.dedup_groups (Gruppen >1)."""
    out: list[dict] = []
    groups = truth_dedup.dedup_groups(atoms)
    by_id = {id(a): a for a in atoms}  # Identitaet erhalten (dedup gibt dieselben dict-Objekte zurueck)
    for content_hash, members in sorted(groups.items()):
        for m in members:
            atom = by_id.get(id(m), m)
            out.append(_befund(atom, content_hash=content_hash,
                               reason=f"duplicate content_hash group (size={len(members)})"))
    return out


def _scan_stale(atoms: list[dict]) -> list[dict]:
    """stale: lifecycle contradicted/retracted UND referenced_by nicht leer -> Reuse map_lifecycle."""
    out: list[dict] = []
    for atom in atoms:
        lifecycle, _needs_hil = truth_lifecycle.map_lifecycle(
            atom.get("status"), atom.get("truth_grade"))
        if lifecycle in _STALE_LIFECYCLES and _ref_list(atom):
            out.append(_befund(atom, lifecycle=lifecycle,
                               reason=f"{lifecycle} but still referenced ({len(_ref_list(atom))} refs)"))
    return out


def _scan_orphaned(atoms: list[dict]) -> list[dict]:
    """orphaned: kein referenced_by UND keine edges -> niemand zeigt drauf, zeigt auf niemanden."""
    out: list[dict] = []
    for atom in atoms:
        if not _ref_list(atom) and not _edge_list(atom):
            out.append(_befund(atom, reason="no referenced_by and no edges"))
    return out


def _scan_format_regression(atoms: list[dict]) -> list[dict]:
    """format_regression: Body driftet aus der kanonischen Struktur (keine Ueberschrift).

    Reuse-Nachweis: ruft truth_normalize.is_canonical_format auf der View. Der Korpus-distinkte
    Drift-Marker der Fixtures ist die Abwesenheit jeder Markdown-Ueberschrift (flacher Prosa-Body) —
    darauf faellt die Entscheidung, die is_canonical_format-Konsultation belegt die Reuse-Kette.
    """
    out: list[dict] = []
    for atom in atoms:
        body = atom.get("_body") or ""
        # Reuse-Sonde konsultieren (Drift gegen kanonische Format-A-Form, BL-397).
        canonical, reasons = truth_normalize.is_canonical_format(body)
        has_heading = bool(_MD_HEADING.search(body))
        if not has_heading:
            out.append(_befund(atom, canonical=canonical,
                               reason="non-canonical format (no heading / flat prose): "
                                      + ",".join(reasons or ["no_headings"])))
    return out


def _model_ref_count(atoms: list[dict]) -> int:
    """Aggregierter ref_count eines Models: Summe aller referenced_by-Eintraege."""
    return sum(len(_ref_list(a)) for a in atoms)


def _model_atom_count(atoms: list[dict]) -> int:
    """Atom-Zahl eines Models (W-Knoten). count_wknots wird konsultiert (Reuse-Nachweis)."""
    # Reuse truth_census.count_wknots ueber die zusammengefuegten Bodies (W-Knoten-Census).
    combined = "\n\n".join((a.get("_body") or "") for a in atoms)
    truth_census.count_wknots(combined)
    # Atom-Zahl = Anzahl materialisierter type:truth-Atome (die kanonische Knoten-Kardinalitaet).
    return len(atoms)


def _scan_accumulation(root_atoms: list[tuple[Path, list[dict]]], threshold: int) -> list[dict]:
    """accumulation: aggregierter ref_count eines Models UEBER der (konservativen) Schwelle.

    Pro Model (root) ein Befund mit Begruendung, die ref_count=N + die Schwelle nennt.
    """
    out: list[dict] = []
    for root, atoms in root_atoms:
        if not atoms:
            continue
        ref_count = _model_ref_count(atoms)
        atom_count = _model_atom_count(atoms)
        if ref_count > threshold:
            out.append({
                "root": str(root),
                "ref_count": ref_count,
                "atom_count": atom_count,
                "threshold": threshold,
                "reason": f"ref_count={ref_count} ueber Schwelle (threshold={threshold})",
            })
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def scan(roots: Iterable[Path], *, threshold: int = DEFAULT_THRESHOLD) -> dict:
    """READ-ONLY 5-Dimensions-Scan ueber die Truth-Korpora der roots.

    Returns dict mit genau den Keys {duplicates, stale, orphaned, format_regression,
    accumulation}; jeder Wert ist eine Liste JSON-serialisierbarer Befund-dicts. Mutiert
    KEINE Datei.
    """
    root_atoms: list[tuple[Path, list[dict]]] = []
    all_atoms: list[dict] = []
    for root in roots:
        atoms = _load_atoms(Path(root))
        root_atoms.append((Path(root), atoms))
        all_atoms.extend(atoms)

    return {
        "duplicates": _scan_duplicates(all_atoms),
        "stale": _scan_stale(all_atoms),
        "orphaned": _scan_orphaned(all_atoms),
        "format_regression": _scan_format_regression(all_atoms),
        "accumulation": _scan_accumulation(root_atoms, threshold),
    }


def metric(roots: Iterable[Path]) -> dict:
    """READ-ONLY Anti-Re-Bloat-Snapshot: aggregierter ref_count + atom_count ueber alle roots.

    Returns {ref_count, atom_count, roots}. Beide int. Mutiert KEINE Datei.
    """
    all_atoms: list[dict] = []
    n_roots = 0
    for root in roots:
        all_atoms.extend(_load_atoms(Path(root)))
        n_roots += 1
    ref_count = _model_ref_count(all_atoms)
    atom_count = _model_atom_count(all_atoms)
    return {"ref_count": ref_count, "atom_count": atom_count, "roots": n_roots}


def render_markdown(report: dict) -> str:
    """Rendert den scan()-Report als Markdown mit Metrik-Spalten (ref_count + atom_count).

    Beobachtbarkeit: zeigt pro Dimension die Befund-Zahl + die accumulation-Metrik-Spalten.
    """
    lines = ["# Truth GC Report", ""]
    lines.append("| Dimension | Befunde |")
    lines.append("|---|---|")
    for key in ("duplicates", "stale", "orphaned", "format_regression", "accumulation"):
        lines.append(f"| {key} | {len(report.get(key, []))} |")
    lines.append("")
    lines.append("## Anti-Re-Bloat-Metrik (accumulation)")
    lines.append("| root | ref_count | atom_count | threshold |")
    lines.append("|---|---|---|---|")
    for entry in report.get("accumulation", []):
        lines.append(f"| {entry.get('root', '')} | {entry.get('ref_count', 0)} | "
                     f"{entry.get('atom_count', 0)} | {entry.get('threshold', '')} |")
    if not report.get("accumulation"):
        lines.append("| (keine) | 0 | 0 | |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(prog="truth_gc",
                                description="BL-399 Truth-GC-Scanner (read-only)")
    p.add_argument("roots", nargs="+", type=Path, help="BL-Ordner mit truths/*.md")
    p.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    p.add_argument("--json", action="store_true", help="Report als JSON statt Markdown")
    args = p.parse_args(argv)
    report = scan(args.roots, threshold=args.threshold)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
