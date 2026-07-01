#!/usr/bin/env python3
"""
_manifest_resolver.py — Shared per-BL-folder-aware Manifest-Resolution.

Fixt die systemische flat-vault-Annahme in den Guards (BL-RCA-Round17, 2026-05-28):
  ALT: guard liest vault_root/_manifest.md
  REALITAET: DCSRE & co nutzen PER-BL-FOLDER Manifeste
             (Backlog/BL-NNN-.../_manifest.md), NICHT vault_root/_manifest.md
  FOLGE: guard_geist5/6/9 fanden den IDF-Vertrag nicht -> "Manifest nicht gefunden"
         -> SDF-Handoff blockiert (false-positive), brauchte manuellen hook_workaround.

current_context.py berechnet bl_manifest_path bereits korrekt — die Guards
ignorierten es nur und nahmen vault_root/_manifest.md an. Dieser Helper exponiert
die per-BL-Aufloesung an alle Guards.

Resolution-Reihenfolge (per-BL ZUERST, dann factory/legacy/vault-Fallback):
  1. bl_manifest_path       (current_context.py — per-BL-folder, DCSRE-Fall)
  2. factory_manifest_path  (BL-173 split)
  3. legacy_manifest_path   (vault_root/_manifest.md, OmniCommand-Fall)
  4. vault_root/_factory_manifest.md + vault_root/_manifest.md (harter Fallback)

Cross-Platform: subprocess IMMER [sys.executable, ...] (Windows hat kein 'python').
Robustheit: current_context.py emittiert evtl. einen [DEPRECATION]-Prefix vor dem
            JSON — wir suchen das erste '{' und parsen ab dort.
"""

import json
import subprocess
import sys
from pathlib import Path


def _read_context(script_dir, root_dir):
    """current_context.py --format=json robust parsen (Prefix-tolerant)."""
    try:
        cc = Path(script_dir) / "current_context.py"
        if cc.is_file():
            # timeout=15 (BL-RESILIENZ 2026-05-29): current_context.py spawnt intern 2
            # Sub-Subprozesse (resolve_vault_root + resolve_bl_path, je timeout=5s = bis 10s).
            # Mit 8s wurde current_context im langsamen Worktree gekillt -> leerer stdout ->
            # JSONDecodeError -> Manifest unaufloesbar -> Guard-Stall am IDF->SDF-Seam. 15s gibt Raum.
            proc = subprocess.run(
                [sys.executable, str(cc), "--format=json"],
                capture_output=True, text=True, timeout=15, cwd=str(root_dir),
            )
            out = proc.stdout or ""
            i = out.find("{")
            if i >= 0:
                return json.loads(out[i:])
    except Exception:
        pass
    return {}


def resolve_manifest_candidates(script_dir, root_dir, vault_root=None):
    """Geordnete Kandidaten-Pfade, per-BL-folder ZUERST, dann Fallbacks."""
    cands = []
    ctx = _read_context(script_dir, root_dir)
    for key in ("bl_manifest_path", "factory_manifest_path", "legacy_manifest_path"):
        v = ctx.get(key)
        if v:
            cands.append(Path(v))
    if vault_root:
        cands.append(Path(vault_root) / "_factory_manifest.md")
        cands.append(Path(vault_root) / "_manifest.md")
    # Dedup unter Erhalt der Reihenfolge
    seen, ordered = set(), []
    for c in cands:
        s = str(c)
        if s not in seen:
            seen.add(s)
            ordered.append(c)
    return ordered


def read_active_manifest(script_dir, root_dir, vault_root=None):
    """(content, path) des ersten EXISTIERENDEN Kandidaten, sonst ('', None)."""
    for c in resolve_manifest_candidates(script_dir, root_dir, vault_root):
        try:
            if c.is_file():
                return c.read_text(encoding="utf-8", errors="replace"), c
        except Exception:
            continue
    return "", None


def _self_test():
    sd = Path(__file__).parent
    rd = sd.parent.parent
    cands = resolve_manifest_candidates(sd, rd, vault_root=rd / ".claude" / "analysis")
    print(f"[SELF-TEST] {len(cands)} Kandidaten aufgeloest:")
    for c in cands:
        print(f"  {'EXISTS' if c.is_file() else 'absent'}  {c}")
    content, path = read_active_manifest(sd, rd, vault_root=rd)
    print(f"[SELF-TEST] aktives Manifest: {path} ({len(content)} chars)")
    # Kandidaten muessen mindestens 1 sein (Fallback greift immer wenn vault_root gesetzt)
    if not cands:
        print("[SELF-TEST FAIL] keine Kandidaten")
        return 1
    print("[SELF-TEST PASS]")
    return 0


if __name__ == "__main__":
    sys.exit(_self_test())
