#!/usr/bin/env python3
"""
resolve_format_version.py — Single Source fuer format_versions.yaml-Resolution (BL-333).

1:1-Analog zu load_layers.py (Vault-First-Config-Loader + PT-GEN-LeadFollow,
Loader=Lead der Versions-Wahrheit). Registry: je Langzeit-Artefakt-Typ
{version, seit_bl, migrations_chain}.

Resolver-Reihenfolge (analog ARCH-N7):
  1. {vault_root}/config/format_versions.yaml   ← PRIMAER (projekt-spezifisch)
  2. .claude/config/format_versions.yaml        ← FALLBACK (Repo-Default OmniCommand)

Kern-Prinzip — Dual-Read-Resilienz (NIE Crash):
  - unbekannter Typ / fehlende Registry -> resolve_format_version() == None (Gen-0-Sentinel)
  - ungestempeltes Frontmatter -> read_format_version() == 0 (Generation-0)
  - Loader nicht ladbar (version=None) -> stamp_format_version_lines() laesst Stamp WEG

Aufruf:
  python3 .claude/scripts/resolve_format_version.py [TYP]
  python3 .claude/scripts/resolve_format_version.py --format=json

Exit:
  0 = OK (Registry geladen)
  1 = Fehler (keine Registry gefunden, kein Fallback)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# __file__-RELATIVER Fallback (cwd-INVARIANT) — der Kern von G_cwd (BL-343 PL-343-1).
# .../.claude/scripts/resolve_format_version.py -> parent.parent == .../.claude
REPO_FALLBACK = Path(__file__).resolve().parent.parent / "config" / "format_versions.yaml"

# Single Source fuer den Frontmatter-Stempel-Key (kein Magic-String an 4 Stellen:
# read_format_version / stamp_format_version_lines (Idempotenz + Emit)).
STAMP_KEY = "format_version"
STAMP_PREFIX = f"{STAMP_KEY}:"


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


def find_format_versions_yaml() -> Path | None:
    """Vault-First: vault/config/format_versions.yaml -> .claude/config/format_versions.yaml."""
    vault = resolve_vault_root()
    if vault is not None:
        candidate = vault / "config" / "format_versions.yaml"
        if candidate.is_file():
            return candidate
    if REPO_FALLBACK.is_file():
        return REPO_FALLBACK
    return None


def parse_yaml_minimal(text: str) -> dict:
    """Minimaler YAML-Parser fuer format_versions.yaml (ohne PyYAML-Dependency).

    Unterstuetzt die Struktur:
      format_versions:
        {typ}:
          version: {int}
          seit_bl: {str}
          migrations_chain: []
    Fuer komplexe YAMLs PyYAML installieren — dieser Parser ist Fallback.
    """
    try:
        import yaml  # type: ignore
        for doc in yaml.safe_load_all(text):
            if isinstance(doc, dict) and "format_versions" in doc:
                return doc
        return {}
    except ImportError:
        pass

    # Minimal-Parser: format_versions: {typ: {version, seit_bl, migrations_chain}}
    out: dict = {"format_versions": {}}
    in_root = False
    current_typ: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("format_versions:"):
            in_root = True
            continue
        if not in_root:
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 2 and stripped.endswith(":"):
            # neuer Typ-Eintrag (z.B. "  manifest:")
            current_typ = stripped[:-1].strip()
            out["format_versions"][current_typ] = {}
        elif indent >= 4 and current_typ is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()
            if k == "version":
                try:
                    out["format_versions"][current_typ][k] = int(v)
                except ValueError:
                    out["format_versions"][current_typ][k] = v
            elif k == "migrations_chain":
                # nur Inline-Leerliste unterstuetzt (Minimal-Fallback)
                out["format_versions"][current_typ][k] = []
            else:
                out["format_versions"][current_typ][k] = v.strip('"').strip("'")
    return out


def load_format_versions() -> dict:
    """Laedt die Registry-Map {typ: {version, seit_bl, migrations_chain}}.

    Fehlende Registry-Datei -> leere Map (kein Crash).
    """
    path = find_format_versions_yaml()
    if path is None:
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    config = parse_yaml_minimal(text)
    return config.get("format_versions", {}) or {}


def resolve_format_version(typ: str) -> int | None:
    """Aktuelle format_version fuer einen Artefakt-Typ.

    unbekannter Typ / fehlende Registry -> None (Gen-0-Sentinel, KEIN Crash).
    """
    config = load_format_versions()
    entry = config.get(typ)
    if not isinstance(entry, dict):
        return None
    try:
        return int(entry.get("version"))
    except (TypeError, ValueError):
        return None


def read_format_version(fm_text: str) -> int:
    """Liest die format_version aus einem Frontmatter-Text.

    Dual-Read-Resilienz: fehlender Stempel == Generation-0 (0), NIE Crash.
    """
    if not fm_text:
        return 0
    for raw in fm_text.splitlines():
        line = raw.strip()
        if line.startswith(STAMP_PREFIX):
            val = line.split(":", 1)[1].strip().strip('"').strip("'")
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0
    return 0


def stamp_format_version_lines(lines: list[str], typ: str, version: int | None) -> list[str]:
    """Stempelt eine `format_version:`-Zeile additiv + idempotent in Frontmatter-Lines.

    Writer=Follow (PT-GEN-LeadFollow): der Wert kommt via Loader-Call (Parameter `version`),
    kein eigenes Versions-Literal.

    - version is None (Loader nicht ladbar) -> Stamp WEGGELASSEN, kein Crash (Symmetrie G2e).
    - format_version bereits vorhanden -> kein Duplikat (idempotent).
    - sonst additiv: 1 Zeile nach der oeffnenden `---` einfuegen (oder am Anfang, falls
      kein Fence-Marker vorhanden).
    """
    if version is None:
        return list(lines)
    # Idempotent: vorhandener Stempel -> unveraendert.
    for ln in lines:
        if ln.startswith(STAMP_PREFIX):
            return list(lines)
    stamp = f"{STAMP_KEY}: {version}"
    out: list[str] = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.strip() == "---":
            out.append(stamp)
            inserted = True
    if not inserted:
        # Kein Fence-Marker -> additiv an den Anfang.
        out.insert(0, stamp)
    return out


def check_migration_disposition(fm: dict) -> list[str]:
    """WARN-Haken (non-blocking): fehlt `migration_disposition` -> 1 WARN.

    Eskaliert NIE zu exit!=0. REQUIRED-Pflichtfelder bleiben unberuehrt.
    Wertebereich (Konvention): retroaktiv | forward-compat-only | hybrid.
    """
    if "migration_disposition" not in fm or not str(fm.get("migration_disposition", "")).strip():
        return ["WARN: 'migration_disposition' fehlt (non-blocking; "
                "retroaktiv|forward-compat-only|hybrid)"]
    return []


def check_migration_disposition_manifest(text: str) -> list[str]:
    """WARN-Haken fuer Manifest-Frontmatter-Text (Follow zu check_migration_disposition).

    non-blocking; C1/C2/C3 unveraendert.
    """
    fm: dict = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line == "---":
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return check_migration_disposition(fm)


def main(argv: list[str]) -> int:
    fmt = None
    typ = None
    for arg in argv[1:]:
        if arg.startswith("--format="):
            fmt = arg.split("=", 1)[1]
        elif not arg.startswith("--"):
            typ = arg

    path = find_format_versions_yaml()
    if path is None:
        print("ERROR: format_versions.yaml weder in Vault noch in Repo gefunden", file=sys.stderr)
        return 1

    config = load_format_versions()

    if fmt == "json":
        json.dump(config, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if typ is not None:
        version = resolve_format_version(typ)
        if version is None:
            print("")  # Gen-0-Sentinel: leere Ausgabe, exit 0 (kein Crash)
        else:
            print(version)
        return 0

    # Default: alle Typen mit Version.
    for t, entry in config.items():
        if isinstance(entry, dict):
            print(f"{t}\t{entry.get('version', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
