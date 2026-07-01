#!/usr/bin/env python3
"""
truth_capstone_gate.py — BL-484 Capstone-Gate (Stage 8 der BL-483-Pipeline).

Gegeben ein Vault-Root prueft dieses Modul die SECHS Capstone-Kriterien G1-G6, die
beweisen, dass der Vault ein vollstaendiger, verbundener, verlustfreier, forward-
garantierter Truth-Graph ist ("auf der anderen Seite"). Pro Kriterium GRUEN/ROT.
ROT nennt die fehlende BL-483-Pipeline-Stage (`missing_stage`).

"Migration erfolgreich" == alle 6 GRUEN (`migration_complete`).

NO-FALSE-GREEN: ein Kriterium ist GRUEN nur, wenn sein Check tatsaechlich auf echten
Daten lief UND bestand. Leerer Vault / nicht-lauffaehiger Check -> ROT.

Read-only auf dem echten Vault. G4 (Forward-Garantie-LIVE) nutzt eine TEMP-Sandbox,
niemals den echten Vault.

Reuse (kein Re-Invent): truth_backref_materialize, truth_edge_backref, truth_verify,
truth_atomizer, view_node_predicate, view_forward_reference, wikilink_materializer.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import yaml

# --- Reuse-Module (bare imports; conftest legt scripts-dir auf sys.path) ---
from truth_backref_materialize import (
    _iter_truth_atoms,
    _parse_frontmatter,
)
from truth_edge_backref import build_edge_backref_index  # noqa: F401 (semantik-Referenz; siehe _edge_backref_from_atoms)
from truth_verify import verify_all
from truth_atomizer import _sha256
from view_node_predicate import is_view_node
from view_id_convention import resolve_view_id, is_derived_id
from wikilink_materializer import has_wikilink_section, _split_raw_frontmatter
import view_forward_reference  # NOTE: per-Attribut aufgerufen, damit der Test-Monkeypatch greift (G4 ROT)


GATES = ["G1", "G2", "G3", "G4", "G5", "G6"]

_HEX64 = re.compile(r"^[0-9a-f]{64}$")

# Per-Gate Namen (non-empty str, vertraglich).
GATE_NAMES = {
    "G1": "truths_are_nodes",
    "G2": "edges_bidirectional",
    "G3": "views_are_referents",
    "G4": "forward_garantie_live",
    "G5": "loss_zero",
    "G6": "navigable",
}

# Per-Gate missing_stage-Strings (konkrete BL-483-Stage je ROT-Ursache).
_STAGE = {
    "G1": "Atomize/Substrat (BL-309 truth_atomizer)",
    "G2_dangling": "Edge-Writer truth-scope (keyword_edge_writer BL-479)",
    "G2_backref": "referenced_by-Inversion (truth_edge_backref BL-451)",
    "G3_unresolved": "View->Atom source_atoms (BL-460 forward)",
    "G3_backref": "View-referenced_by-Inversion (BL-460 follow-on / atom-side view backref)",
    "G4": "Forward-Garantie hook/engine (BL-480/BL-388 view-forward)",
    "G5": "Census-Lockstep / Rebuild (BL-384/BL-395 content-preservation)",
    "G6_index": "Edge-Index (truth_backref_index)",
    "G6_wikilink": "Wikilink-Rematerialize (truth_wikilink_rematerialize BL-451 AC-2a)",
}


# ---------------------------------------------------------------------------
# Atom-/View-Loader (yaml.safe_load fuer voll-korrektes Frontmatter-Parsing)
# ---------------------------------------------------------------------------

def _load_atoms(vault: Path) -> list[dict]:
    """Laedt alle truth-Atome unter vault als Dict-Liste.

    Jedes Atom: {path, rel, content, body, fm, id, local_id, type, keywords,
                 text, content_hash, edges, referenced_by}.
    """
    atoms: list[dict] = []
    for path, content, local_id in _iter_truth_atoms(vault):
        parsed = _parse_frontmatter(content)
        if parsed is None:
            continue
        fm_text = parsed[0]
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            fm = {}
        if not isinstance(fm, dict):
            fm = {}
        _, body = _split_raw_frontmatter(content)
        edges = fm.get("edges") or []
        if not isinstance(edges, list):
            edges = []
        referenced_by = fm.get("referenced_by") or []
        if not isinstance(referenced_by, list):
            referenced_by = []
        try:
            rel = str(path.relative_to(vault)).replace("\\", "/")
        except ValueError:
            rel = str(path)
        atoms.append({
            "path": path,
            "rel": rel,
            "content": content,
            "body": body,
            "fm": fm,
            "id": fm.get("id"),
            "local_id": fm.get("local_id", local_id),
            "type": fm.get("type"),
            "keywords": fm.get("keywords") or [],
            "text": fm.get("text"),
            "content_hash": fm.get("content_hash"),
            "edges": edges,
            "referenced_by": referenced_by,
        })
    return atoms


def _load_views(vault: Path) -> list[dict]:
    """Enumeriert View-Nodes (is_view_node) unter vault. Jede View: {path, rel, fm,
    id, source_atoms}."""
    views: list[dict] = []
    vault_str = str(vault)
    for f in sorted(vault.rglob("*.md")):
        if not f.is_file():
            continue
        if not is_view_node(str(f), vault_str):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parsed = _parse_frontmatter(content)
        if parsed is None:
            fm = {}
        else:
            try:
                fm = yaml.safe_load(parsed[0]) or {}
            except yaml.YAMLError:
                fm = {}
            if not isinstance(fm, dict):
                fm = {}
        source_atoms = fm.get("source_atoms") or []
        if not isinstance(source_atoms, list):
            source_atoms = []
        try:
            rel = str(f.relative_to(vault)).replace("\\", "/")
        except ValueError:
            rel = str(f)
        views.append({
            "path": f,
            "rel": rel,
            "fm": fm,
            "id": resolve_view_id(fm, rel),
            "source_atoms": source_atoms,
        })
    return views


def _edge_backref_from_atoms(atoms: list[dict]) -> dict[str, list[dict]]:
    """In-Memory-Aequivalent von truth_edge_backref.build_edge_backref_index(root),
    aber aus den bereits geladenen Atom-Dicts gebaut (KEIN zweiter rglob-Lese-Pass
    ueber den Vault — Performance auf grossen Vaults). Repliziert EXAKT die Semantik:
    invertiert edges[].ziel -> {B_id: [{by:A_id, kind:"truth_edge"}]}, mit Dangling-
    Filter (ziel nicht im id_set), Self-Edge-Filter (ziel==A) und Dedup auf (B,A)."""
    id_set = {a["id"] for a in atoms if a.get("id")}
    index: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for a in atoms:
        a_id = a.get("id")
        if not a_id:
            continue
        for e in a.get("edges") or []:
            if not isinstance(e, dict):
                continue
            ziel = e.get("ziel")
            if not ziel or not isinstance(ziel, str):
                continue
            if ziel not in id_set:      # Dangling
                continue
            if ziel == a_id:            # Self-Edge
                continue
            key = (ziel, a_id)
            if key in seen:             # Dedup
                continue
            seen.add(key)
            index[ziel].append({"by": a_id, "kind": "truth_edge"})
    return dict(index)


def _gate(gid: str, green: bool, detail: dict, stage: str | None) -> dict:
    """Baut das vertragliche Gate-Dict. missing_stage MUSS None sein wenn green."""
    return {
        "gate": gid,
        "name": GATE_NAMES[gid],
        "green": bool(green),
        "missing_stage": None if green else stage,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# G1 — Truths=Nodes (substrat-vollstaendig)
# ---------------------------------------------------------------------------

def check_g1(vault: Path, atoms: list[dict]) -> dict:
    malformed: list[str] = []
    for a in atoms:
        aid = a["id"]
        lid = a["local_id"]
        ok = (
            a["type"] == "truth"
            and isinstance(aid, str) and aid.strip()
            and isinstance(lid, str) and str(lid).strip()
            and str(aid).endswith("." + str(lid))
        )
        if not ok:
            malformed.append(a["rel"])

    truths = [{"id": a["id"], "local_id": a["local_id"], "edges": a["edges"]} for a in atoms]
    verify = verify_all(truths)

    green = (
        len(atoms) > 0
        and not malformed
        and verify["id_collision_count"] == 0
        and len(verify["id_local_inconsistencies"]) == 0
    )
    detail = {
        "atom_count": len(atoms),
        "malformed": len(malformed),
        "malformed_samples": malformed[:5],
        "id_collision_count": verify["id_collision_count"],
        "id_local_inconsistencies": len(verify["id_local_inconsistencies"]),
    }
    return _gate("G1", green, detail, _STAGE["G1"])


# ---------------------------------------------------------------------------
# G2 — Bidirektionale Edges (forward + referenced_by, 0 dangling, truth-scoped)
# ---------------------------------------------------------------------------

def check_g2(vault: Path, atoms: list[dict], edge_index: dict[str, list[dict]]) -> dict:
    id_set = {a["id"] for a in atoms if a["id"]}
    atom_by_id = {a["id"]: a for a in atoms if a["id"]}

    # (a) Dangling: forward edges[].ziel deren ziel NICHT im id_set ist —
    #     SELBST gezaehlt ueber die rohen edges (die Index-Inversion droppt dangling).
    dangling: list[dict] = []
    for a in atoms:
        for e in a["edges"]:
            if not isinstance(e, dict):
                continue
            ziel = e.get("ziel")
            if ziel is None:
                continue
            if ziel not in id_set:
                dangling.append({"from": a["id"], "ziel": ziel})

    # (b) Missing-Backref: fuer jedes {B:[{by:A}]} aus der Edge-Inversion muss
    #     B.referenced_by (kind truth_edge) by==A enthalten.
    computed = edge_index
    missing_backref: list[dict] = []
    for b_id, entries in computed.items():
        atom = atom_by_id.get(b_id)
        if atom is None:
            for entry in entries:
                missing_backref.append({"B": b_id, "by": entry.get("by")})
            continue
        on_disk = {
            e.get("by")
            for e in atom["referenced_by"]
            if isinstance(e, dict) and e.get("kind") == "truth_edge"
        }
        for entry in entries:
            by = entry.get("by")
            if by not in on_disk:
                missing_backref.append({"B": b_id, "by": by})

    # (c) Scope: jeder materialisierte truth_edge `by` loest auf ein existierendes Atom auf.
    scope_violations: list[dict] = []
    for a in atoms:
        for e in a["referenced_by"]:
            if not isinstance(e, dict) or e.get("kind") != "truth_edge":
                continue
            by = e.get("by")
            if by not in id_set:
                scope_violations.append({"atom": a["id"], "by": by})

    green = not dangling and not missing_backref and not scope_violations

    if dangling:
        stage = _STAGE["G2_dangling"]
    else:
        stage = _STAGE["G2_backref"]

    detail = {
        "dangling": len(dangling),
        "dangling_samples": dangling[:5],
        "missing_backref": len(missing_backref),
        "missing_backref_samples": missing_backref[:5],
        "scope_violations": len(scope_violations),
        "scope_samples": scope_violations[:5],
        "edge_backref_keys": len(computed),
    }
    return _gate("G2", green, detail, stage)


# ---------------------------------------------------------------------------
# G3 — Views-as-Referents (source_atoms bidirektional)
# ---------------------------------------------------------------------------

def check_g3(vault: Path, atoms: list[dict], views: list[dict]) -> dict:
    atom_by_rel = {a["rel"]: a for a in atoms}

    views_with_sources = 0
    views_with_derived_id = 0
    views_without_id = 0
    unresolved: list[dict] = []
    missing_view_backref: list[dict] = []

    for v in views:
        srcs = v["source_atoms"]
        if not srcs:
            continue
        views_with_sources += 1
        view_id = v["id"]
        if is_derived_id(view_id):
            # id-lose View bekommt eine stabile PATH-derived id (view::<rel>) — ihr
            # backward-link ist jetzt benennbar/verifizierbar (BL-491 AC-2).
            views_with_derived_id += 1
        if not (isinstance(view_id, str) and view_id.strip()):
            # Defensive: resolve_view_id liefert immer einen non-empty str -> ~immer 0.
            views_without_id += 1
        for src in srcs:
            src_str = str(src).replace("\\", "/")
            resolved_path = (vault / src_str)
            atom = atom_by_rel.get(src_str)
            if not resolved_path.exists() or atom is None:
                unresolved.append({"view": v["rel"], "source": src_str})
                continue
            # Backward: das Atom muss die View als referenced_by nennen (any kind).
            bys = {
                e.get("by")
                for e in atom["referenced_by"]
                if isinstance(e, dict)
            }
            if view_id not in bys:
                missing_view_backref.append({"view": view_id, "view_rel": v["rel"], "atom": src_str})

    green = (
        views_with_sources > 0
        and not unresolved
        and not missing_view_backref
    )

    if unresolved:
        stage = _STAGE["G3_unresolved"]
    else:
        stage = _STAGE["G3_backref"]

    detail = {
        "view_count": len(views),
        "views_with_sources": views_with_sources,
        "views_with_derived_id": views_with_derived_id,
        "views_without_id": views_without_id,
        "unresolved": len(unresolved),
        "unresolved_samples": unresolved[:5],
        "missing_view_backref": len(missing_view_backref),
        "missing_view_backref_samples": missing_view_backref[:5],
    }
    return _gate("G3", green, detail, stage)


# ---------------------------------------------------------------------------
# G4 — FORWARD-GARANTIE aktiv (LIVE — nicht statisch)
# ---------------------------------------------------------------------------

def _hook_registered(vault: Path) -> bool:
    """Info-only: ist der PostToolUse-Forward-Hook in einer settings.json registriert?"""
    for cand in (
        vault / ".claude" / "settings.json",
        Path(__file__).resolve().parent.parent / "settings.json",
    ):
        try:
            if cand.exists():
                txt = cand.read_text(encoding="utf-8", errors="replace")
                if "hook_view_forward_reference" in txt or "view_forward_reference" in txt:
                    return True
        except OSError:
            continue
    return False


def _build_sandbox_atom_content(atom: dict) -> str:
    """Re-serialisiert ein Atom mit INLINE-Flow-keywords (`[a, b]`), damit die
    Index-Builder (quality_node_health.parse_frontmatter / truth_search) die
    keywords lesen koennen — die yaml-Block-Sequence-Form (`- a`) lesen sie NICHT.
    """
    kw = [str(k) for k in (atom.get("keywords") or [])]
    base = {
        "type": "truth",
        "id": atom.get("id"),
        "local_id": atom.get("local_id"),
        "content_hash": atom.get("content_hash") or "",
        "text": atom.get("text") or "",
    }
    dumped = yaml.safe_dump(base, allow_unicode=True, sort_keys=False, default_flow_style=False)
    kw_line = "keywords: [" + ", ".join(kw) + "]\n"
    return f"---\n{dumped}{kw_line}---\n\n" + (atom.get("text") or "") + "\n"


def _build_sandbox_view_content(atom: dict) -> str:
    """View-Body enthaelt die Atom-keywords (wiederholt) + den Atom-Text, damit
    score_view das Atom ueber conf_threshold vorschlaegt."""
    kw = [str(k) for k in (atom.get("keywords") or [])]
    text = atom.get("text") or ""
    kw_blob = " ".join(kw)
    body = (
        "\n# Probe Forward-Garantie View\n\n"
        + (kw_blob + " ") * 3
        + "\n\n"
        + (text + " ") * 2
        + "\n"
    )
    fm = {
        "id": "PROBE.ForwardView",
        "tags": ["type/model"],
        "bl": "BL-PROBE",
    }
    dumped = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{dumped}---\n{body}"


def check_g4(vault: Path, atoms: list[dict], *, live: bool = True) -> dict:
    detail: dict = {"hook_registered": _hook_registered(vault), "live": live}

    if not live:
        detail["reason"] = "live check skipped (--no-live-g4) -> not verified"
        return _gate("G4", False, detail, _STAGE["G4"])

    # Atom mit keywords + text waehlen (robustes Scoring-Substrat).
    src = None
    for a in atoms:
        if a.get("keywords") and a.get("text"):
            src = a
            break
    if src is None and atoms:
        src = atoms[0]
    if src is None:
        detail["reason"] = "kein Atom im Vault -> Forward-Garantie nicht pruefbar"
        return _gate("G4", False, detail, _STAGE["G4"])

    try:
        with tempfile.TemporaryDirectory(prefix="capstone_g4_") as td:
            sandbox = Path(td)
            atom_rel = "Backlog/BL-PROBE/2_Model/truths/probe_atom.md"
            atom_path = sandbox / atom_rel
            atom_path.parent.mkdir(parents=True, exist_ok=True)
            atom_path.write_text(_build_sandbox_atom_content(src), encoding="utf-8")

            view_rel = "Backlog/BL-PROBE/2_Model/Probe_Model.md"
            view_path = sandbox / view_rel
            view_path.parent.mkdir(parents=True, exist_ok=True)
            view_path.write_text(_build_sandbox_view_content(src), encoding="utf-8")

            # Vorzustand: View hat KEINE source_atoms.
            before = yaml.safe_load(_parse_frontmatter(view_path.read_text(encoding="utf-8"))[0]) or {}
            before_sources = before.get("source_atoms") or []

            # OPERATIVER ENGINE-CALL — per Attribut auf view_forward_reference, damit der
            # Test-Monkeypatch (no-op) korrekt G4 ROT erzwingt.
            engine_result = view_forward_reference.forward_reference_new_view(
                str(view_path), str(sandbox), write=True
            )

            # Re-Read: produzierte die Engine einen Referenten?
            after_content = view_path.read_text(encoding="utf-8")
            after_parsed = _parse_frontmatter(after_content)
            after_fm = yaml.safe_load(after_parsed[0]) if after_parsed else {}
            after_sources = (after_fm or {}).get("source_atoms") or []

            produced = len(after_sources) > len(before_sources) or (
                len(after_sources) > 0 and not before_sources
            )

            detail.update({
                "atom_used": src.get("id"),
                "engine_action": engine_result.get("action") if isinstance(engine_result, dict) else None,
                "engine_n_proposed": engine_result.get("n_proposed") if isinstance(engine_result, dict) else None,
                "before_source_count": len(before_sources),
                "after_source_count": len(after_sources),
                "after_sources_sample": [str(s) for s in after_sources[:3]],
            })
            return _gate("G4", produced, detail, _STAGE["G4"])
    except Exception as exc:  # noqa: BLE001 — Check konnte nicht laufen -> ROT (NO-FALSE-GREEN)
        detail["error"] = f"{type(exc).__name__}: {exc}"
        return _gate("G4", False, detail, _STAGE["G4"])


# ---------------------------------------------------------------------------
# G5 — Loss=0 (content_hash byte-coverage / census-lockstep)
# ---------------------------------------------------------------------------

def check_g5(vault: Path, atoms: list[dict]) -> dict:
    hash_mismatch: list[str] = []
    empty_text: list[str] = []
    for a in atoms:
        ch = a["content_hash"]
        text = a["text"]
        if not isinstance(text, str) or text == "":
            empty_text.append(a["rel"])
        valid_hex = isinstance(ch, str) and bool(_HEX64.match(ch))
        expected = _sha256(text) if isinstance(text, str) else None
        if not valid_hex or expected is None or ch != expected:
            hash_mismatch.append(a["rel"])

    truths = [{"id": a["id"], "local_id": a["local_id"]} for a in atoms]
    verify = verify_all(truths)
    collisions = verify["id_collision_count"]

    green = not hash_mismatch and not empty_text and collisions == 0
    detail = {
        "atom_count": len(atoms),
        "hash_mismatch": len(hash_mismatch),
        "hash_mismatch_samples": hash_mismatch[:5],
        "empty_text": len(empty_text),
        "id_collision_count": collisions,
    }
    return _gate("G5", green, detail, _STAGE["G5"])


# ---------------------------------------------------------------------------
# G6 — Navigierbar (wikilinks / edge-index)
# ---------------------------------------------------------------------------

def check_g6(vault: Path, atoms: list[dict], edge_index: dict[str, list[dict]]) -> dict:
    id_set = {a["id"] for a in atoms if a["id"]}
    index = edge_index

    index_non_empty = len(index) > 0
    bad_keys = [k for k in index if k not in id_set]
    index_ok = index_non_empty and not bad_keys

    missing_wikilinks: list[str] = []
    atoms_with_edges = 0
    for a in atoms:
        if not a["edges"]:
            continue
        atoms_with_edges += 1
        if not has_wikilink_section(a["body"]):
            missing_wikilinks.append(a["rel"])

    green = index_ok and not missing_wikilinks

    if not index_ok:
        stage = _STAGE["G6_index"]
    else:
        stage = _STAGE["G6_wikilink"]

    detail = {
        "edge_index_keys": len(index),
        "index_non_empty": index_non_empty,
        "bad_keys": len(bad_keys),
        "bad_key_samples": bad_keys[:5],
        "atoms_with_edges": atoms_with_edges,
        "missing_wikilinks": len(missing_wikilinks),
        "missing_wikilink_samples": missing_wikilinks[:5],
    }
    return _gate("G6", green, detail, stage)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_capstone_gate(vault: Path, *, live_g4: bool = True) -> dict:
    """Prueft G1-G6 auf vault. Read-only auf dem echten Vault (G4 nutzt TEMP-Sandbox)."""
    vault = Path(vault)
    atoms = _load_atoms(vault)
    views = _load_views(vault)
    # Edge-Inversion EINMAL aus den geladenen Atomen (kein zusaetzlicher Vault-Lese-Pass).
    edge_index = _edge_backref_from_atoms(atoms)

    gates = [
        check_g1(vault, atoms),
        check_g2(vault, atoms, edge_index),
        check_g3(vault, atoms, views),
        check_g4(vault, atoms, live=live_g4),
        check_g5(vault, atoms),
        check_g6(vault, atoms, edge_index),
    ]

    green_count = sum(1 for g in gates if g["green"])
    migration_complete = green_count == len(GATES)

    return {
        "vault": str(vault),
        "atoms": len(atoms),
        "views": len(views),
        "gates": gates,
        "green_count": green_count,
        "total": len(GATES),
        "migration_complete": migration_complete,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_report(result: dict) -> str:
    lines = [
        f"Capstone-Gate (BL-484) — vault: {result['vault']}",
        f"atoms={result['atoms']} views={result['views']} "
        f"green={result['green_count']}/{result['total']} "
        f"migration_complete={result['migration_complete']}",
        "",
    ]
    for g in result["gates"]:
        status = "GREEN" if g["green"] else "ROT  "
        line = f"  [{status}] {g['gate']} {g['name']}"
        if not g["green"]:
            line += f"  -> missing_stage: {g['missing_stage']}"
        lines.append(line)
    return "\n".join(lines)


def main(argv) -> int:
    parser = argparse.ArgumentParser(
        prog="truth_capstone_gate",
        description="BL-484 Capstone-Gate (Stage 8): G1-G6 GRUEN/ROT auf einem Vault.",
    )
    parser.add_argument("--vault", required=True, help="Vault-Root (read-only)")
    parser.add_argument("--out", default=None, help="Report-JSON-Pfad")
    parser.add_argument("--quiet", action="store_true", help="kein stdout")
    parser.add_argument("--no-live-g4", action="store_true", help="G4-LIVE-Run ueberspringen")
    args = parser.parse_args(argv)

    vault = Path(args.vault)
    if not vault.is_dir():
        if not args.quiet:
            print(f"ERROR: {vault} ist kein Verzeichnis", file=sys.stderr)
        return 2

    result = run_capstone_gate(vault, live_g4=not args.no_live_g4)

    if args.out:
        Path(args.out).write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    if not args.quiet:
        print(_format_report(result))

    return 0 if result["migration_complete"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
