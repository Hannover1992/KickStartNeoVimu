#!/usr/bin/env python3
"""
truth_resolver.py — Dual-Read Resolver fuer Wahrheits-Referenzen (BL-309 Phase A2).

Ersetzt die heutige LLM-Pseudocode-Interpretation von `resolve_truth_refs` (laut
Truth-Migration-Architektur_2026-06-10 selbst eine Drift-Quelle) durch DETERMINISTISCHES
Python. Waehrend der Migration laufen alle Konsumenten (K-Score, PL, Spec) UNVERAENDERT
weiter, weil der Resolver in fester Prioritaet aufloest:

  1. atomic-first   {bl_folder}/2_Model/truths/{local_id}.md   (type:truth, das Ziel-Format)
  2. alias-map      {vault}/_meta/truth_alias_map.json          (Konnektions-Erhalt, never-renumber)
  3. legacy-parse   {bl_folder}/2_Model/*Model*.md              (Alt-Format, dominant HEADING ~97%)
  4. repo-fallback  .claude/models/*.md                         (~96 Meta-Self-Modelle, BL-385)
  5. stub/not_found archived_stub_pending_dcs                   (lautes Signal, kein stiller Verlust)

DITA-Lektion (Assay): das ist keyref (dynamische, kontext-abhaengige Aufloesung). conref
(statische Inklusion in Views) macht der View-Generator, nicht der Resolver.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

SOURCE_ATOMIC = "atomic"
SOURCE_ALIAS = "alias"
SOURCE_LEGACY = "legacy"
SOURCE_REPO = "repo"
SOURCE_NOT_FOUND = "not_found"

# BL-395(c): EINE kanonische W-ID-Lexikon-Quelle (truth_wid = identisch mit _HEADING_LINE local_id) statt
# 4x Duplikat. Fallback unifiziert mit _HEADING_LINE (inkl. '_'-Suffix -> W7_REF-Referenzen aufloesbar).
try:
    from truth_wid import WID_TOKEN as _WID_TOKEN
except ImportError:
    _WID_TOKEN = re.compile(r"\bW(?:\d+[A-Za-z0-9_]*|-(?!Knoten\b)[A-Z][A-Za-z0-9_-]*)\b")


@dataclass
class Resolution:
    """Ergebnis einer Referenz-Aufloesung."""
    found: bool
    source: str
    resolved_id: Optional[str]
    truth: Optional[dict]
    note: str = ""


def split_ref(ref: str) -> tuple[Optional[str], str]:
    """'BL-309-slug.W01' -> ('BL-309-slug','W01'); 'W01' -> (None,'W01'). Punkt = Fork-1-Trenner."""
    ref = str(ref).strip()
    if "." in ref:
        ns, _, lid = ref.rpartition(".")
        return ns, lid
    return None, ref


def _read_frontmatter(path: Path) -> Optional[dict]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    if yaml is not None:
        try:
            fm = yaml.safe_load(block)
            return fm if isinstance(fm, dict) else None
        except yaml.YAMLError:
            return None
    # Minimal-Fallback ohne PyYAML
    fm: dict = {}
    for line in block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def load_alias_map(vault_root: Optional[Path]) -> dict:
    """Liest {vault}/_meta/truth_alias_map.json. Akzeptiert Liste[{old_ref,...}] oder Map."""
    if vault_root is None:
        return {}
    p = Path(vault_root) / "_meta" / "truth_alias_map.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, list):
        return {e["old_ref"]: e for e in data if isinstance(e, dict) and "old_ref" in e}
    if isinstance(data, dict):
        return data
    return {}


# BL-309-post: Ordner-Konventions-Agnostik. Migrierte BLs nutzen Model/ (singular)
# oder Models/ (plural) statt 2_Model/; teils ist bl_folder SELBST der Model-Ordner.
# Deterministische Reihenfolge: 2_Model zuerst, dann Model, Models, dann bl_folder-selbst.
_MODEL_SUBDIRS = ("2_Model", "Model", "Models")


def _model_dirs(bl_folder: Optional[Path]) -> list[Path]:
    """Kandidat-Model-Ordner unter bl_folder (Split-Brain-tolerant) + bl_folder selbst."""
    if bl_folder is None:
        return []
    bl = Path(bl_folder)
    dirs = [bl / s for s in _MODEL_SUBDIRS] + [bl]
    return [d for d in dirs if d.is_dir()]


def _find_atomic(bl_folder: Optional[Path], local_id: str) -> Optional[dict]:
    if bl_folder is None:
        return None
    for d in _model_dirs(bl_folder):
        p = d / "truths" / f"{local_id}.md"
        if p.is_file():
            return _read_frontmatter(p)
    return None


def extract_wknot_legacy(model_text: str, local_id: str) -> Optional[dict]:
    """Extrahiert einen W-Knoten aus Alt-Model-Text (dominantes HEADING-Format ~97%, Census).

    Findet '#{1,6} {local_id}' und captured den Body bis zum naechsten Heading.
    Voller 6-Format-faithful-Extract ist Sache des Atomizers (Phase B) — hier reicht
    der Resolver-Fallback (Referenz auf ETWAS aufloesen waehrend der Migration).
    """
    pat = re.compile(
        r"(?m)^#{1,6}[ \t]+" + re.escape(local_id) + r"\b[^\n]*\n(.*?)(?=^#{1,6}[ \t]|\Z)",
        re.S,
    )
    m = pat.search(model_text)
    if not m:
        return None
    return {"local_id": local_id, "text": m.group(1).strip(), "_legacy": True}


def _scan_models_for_wknot(model_dirs: list[Path], local_id: str) -> Optional[dict]:
    seen: set[Path] = set()
    for d in model_dirs:
        if d is None or not d.exists():
            continue
        candidates: list[Path] = []
        if d.is_dir():
            candidates = sorted(set(d.glob("*Model*.md")) | set(d.glob("*.md")))
        elif d.is_file():
            candidates = [d]
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            try:
                txt = c.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            kn = extract_wknot_legacy(txt, local_id)
            if kn:
                kn["source_file"] = str(c)
                return kn
    return None


def resolve(
    ref: str,
    *,
    bl_folder: Optional[Path] = None,
    vault_root: Optional[Path] = None,
    repo_models: Optional[Path] = None,
    alias_map: Optional[dict] = None,
    _depth: int = 0,
) -> Resolution:
    """Dual-Read-Aufloesung in fester Prioritaet. Zyklen-sicher (_depth-Cap)."""
    if alias_map is None:
        alias_map = load_alias_map(vault_root)
    _ns, local_id = split_ref(ref)

    # 1. atomic-first
    atomic = _find_atomic(bl_folder, local_id)
    if atomic:
        return Resolution(True, SOURCE_ATOMIC, atomic.get("id", str(ref)), atomic)

    # 2. alias-map (rekursiv, Tiefen-Cap gegen Zyklen)
    if str(ref) in alias_map and _depth < 8:
        entry = alias_map[str(ref)]
        target = entry.get("resolves_to") if isinstance(entry, dict) else entry
        if target and str(target) != str(ref):
            r = resolve(
                target, bl_folder=bl_folder, vault_root=vault_root,
                repo_models=repo_models, alias_map=alias_map, _depth=_depth + 1,
            )
            if r.found:
                return Resolution(True, SOURCE_ALIAS, r.resolved_id, r.truth,
                                  note=f"alias {ref} -> {target} (via {r.source})")

    # 3. legacy-parse (BL-Model) — ordner-konventions-agnostisch (BL-309-post)
    legacy = _scan_models_for_wknot(_model_dirs(bl_folder), local_id)
    if legacy:
        return Resolution(True, SOURCE_LEGACY, str(ref), legacy, note="legacy Model parse")

    # 4. repo-fallback (.claude/models)
    repo = _scan_models_for_wknot([repo_models], local_id) if repo_models else None
    if repo:
        return Resolution(True, SOURCE_REPO, str(ref), repo, note="repo .claude/models fallback")

    # 5. nicht aufgeloest (lautes Signal, kein stiller Verlust)
    return Resolution(False, SOURCE_NOT_FOUND, None, None, note=f"unresolved: {ref}")


def resolve_truth_refs(
    text: str,
    *,
    bl_folder: Optional[Path] = None,
    vault_root: Optional[Path] = None,
    repo_models: Optional[Path] = None,
) -> dict[str, Resolution]:
    """Findet ALLE W-Referenzen in text + loest jede auf. Deterministischer Ersatz fuer
    die LLM-Pseudocode-resolve_truth_refs. Returns {ref: Resolution}."""
    alias_map = load_alias_map(vault_root)
    refs = sorted(set(_WID_TOKEN.findall(text)))
    return {
        r: resolve(r, bl_folder=bl_folder, vault_root=vault_root,
                   repo_models=repo_models, alias_map=alias_map)
        for r in refs
    }
