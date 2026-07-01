#!/usr/bin/env python3
"""
load_layers.py — Single Source fuer layers.yaml-Resolution (ARCH-Delta-11 NEW-Y5).

Konsolidiert die Vault-First Layer-Detection-Logik aus mehreren Beratern:
  _SDF_berater_patternBrief, _PT_arch_init, _SL_init, _PT_seedImport,
  _AC_orchestrate, _architecturalBoundaries, _SC_implement.

Resolver-Reihenfolge (ARCH-N7):
  1. {vault_root}/config/layers.yaml      ← PRIMAER (projekt-spezifisch)
  2. .claude/config/layers.yaml           ← FALLBACK (Repo-Default OmniCommand)

Aufruf:
  python3 .claude/scripts/load_layers.py [--format=glob_map|json|yaml]

  --format=glob_map  → Tab-getrennt: glob<TAB>layer_id (Default)
                        Beispiel: **/Controllers/**\tBE-CONT
  --format=json      → JSON-Dump des kompletten layers-Configs
  --format=yaml      → Raw YAML-Inhalt der gefundenen layers.yaml

Exit:
  0 = OK (layers.yaml geladen)
  1 = Fehler (keine layers.yaml gefunden, kein Fallback)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_FALLBACK = Path(".claude/config/layers.yaml")


def resolve_vault_root() -> Path | None:
    """Delegiert an resolve_vault_root.py (Single Source fuer VAULT_ROOT)."""
    try:
        result = subprocess.run(
            [sys.executable, ".claude/scripts/resolve_vault_root.py"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def find_layers_yaml() -> Path | None:
    """Vault-First: vault/config/layers.yaml -> .claude/config/layers.yaml."""
    vault = resolve_vault_root()
    if vault is not None:
        candidate = vault / "config" / "layers.yaml"
        if candidate.is_file():
            return candidate
    if REPO_FALLBACK.is_file():
        return REPO_FALLBACK
    return None


def parse_yaml_minimal(text: str) -> dict:
    """Minimaler YAML-Parser fuer layers.yaml (ohne PyYAML-Dependency).

    Unterstuetzt nur die Struktur: layers: [{id, label, path_globs, id_prefix}].
    Fuer komplexe YAMLs PyYAML installieren — dieser Parser ist Fallback.
    """
    try:
        import yaml  # type: ignore
        # layers.yaml kann Multi-Doc-Header (Frontmatter + Body) haben.
        # Nimm das erste Document mit `layers`-Key.
        for doc in yaml.safe_load_all(text):
            if isinstance(doc, dict) and "layers" in doc:
                return doc
        return {}
    except ImportError:
        pass

    # Minimal-Parser: Top-level layers: list-of-dicts
    out: dict = {"layers": []}
    in_layers = False
    current: dict = {}
    in_globs = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("layers:"):
            in_layers = True
            continue
        if not in_layers:
            continue
        if line.startswith("  - "):  # neuer Layer-Eintrag
            if current:
                out["layers"].append(current)
            current = {}
            in_globs = False
            kv = line[4:].strip()
            if ":" in kv:
                k, _, v = kv.partition(":")
                current[k.strip()] = v.strip().strip('"').strip("'")
        elif line.startswith("    "):
            stripped = line.strip()
            if stripped.startswith("- "):  # path_globs Eintrag
                if in_globs:
                    current.setdefault("path_globs", []).append(
                        stripped[2:].strip().strip('"').strip("'")
                    )
            elif ":" in stripped:
                k, _, v = stripped.partition(":")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "path_globs":
                    in_globs = True
                    current["path_globs"] = []
                else:
                    in_globs = False
                    current[k] = v
    if current:
        out["layers"].append(current)
    return out


def main(argv: list[str]) -> int:
    fmt = "glob_map"
    for arg in argv[1:]:
        if arg.startswith("--format="):
            fmt = arg.split("=", 1)[1]

    path = find_layers_yaml()
    if path is None:
        print("ERROR: layers.yaml weder in Vault noch in Repo gefunden", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")

    if fmt == "yaml":
        sys.stdout.write(text)
        return 0

    config = parse_yaml_minimal(text)

    if fmt == "json":
        json.dump(config, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    # glob_map (Default): glob<TAB>layer_id pro Zeile
    for layer in config.get("layers", []):
        lid = layer.get("id", "")
        for glob in layer.get("path_globs", []) or []:
            sys.stdout.write(f"{glob}\t{lid}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
