#!/usr/bin/env python3
"""resolve_vault_meta.py — 5-Stufen Meta-Resolution (BL-193 AK-2, AK-7, AK-10).

Lookup-Reihenfolge:
  1. Local-Override:      .claude/meta-override/{path}          (projekt-lokal, optional) [BL-193 AK-10]
  2. Vault-Typ:           {VAULT}/Meta/Typen/{TYP}/{path}       (online primary)
  3. meta-cache-Typ:      .claude/meta-cache/Typen/{TYP}/{path} (offline fallback) [BL-193 AK-7]
  4. Vault-Universal:     {VAULT}/Meta/Universal/{path}          (online universal)
  5. meta-cache-Universal:.claude/meta-cache/Universal/{path}    (offline universal) [BL-193 AK-7]
Erste Treffer gewinnt. Override gewinnt immer — kein Merge, kein implicit warn (ausser --verbose).
"""
import os
import sys
from pathlib import Path


def resolve_vault_root() -> Path:
    """Resolve vault root via die kanonische SSoT (BL-376 Fund #3 / BL-374-Klasse).

    Delegiert an die kanonische resolve_vault_root.py-SSoT (ARCH-N8) statt lokalem
    env -> .vault_root-walkup -> HARDCODED-OmniCommand-Default. Der hardcoded
    `Documents/OmniCommand`-Fallback ist RAUS — exakt die BL-374-Defekt-Klasse
    (divergenter Resolver mit hardcoded Fallback -> Cross-Projekt-Contamination), eine
    Ebene tiefer als pattern_library. ImportError (SSoT fehlt) propagiert = fail-safe
    (lieber lauter Fehler als falsch-geratener Vault). Die SSoT deckt env CLAUDE_VAULT_ROOT
    (PRIMAER) + OBSIDIAN_VAULT_PATH + .vault_root-pin + vault-routing.json + cwd-Heuristik —
    env-first bleibt erhalten (resolve_meta / resolve_command_sidecar unveraendert).
    """
    import resolve_vault_root as rvr   # kanonische SSoT (ARCH-N8) — kein hardcoded Default, kein except:pass
    return Path(rvr.resolve_vault_root())


def resolve_project_typ() -> str:
    """Detect project type from cwd path."""
    cwd_str = str(Path.cwd()).replace("\\", "/")
    if "OmniCommand" in cwd_str:
        return "DCSRE"  # OmniCommand uses DCSRE flavors
    if "DCSRE" in cwd_str:
        return "DCSRE"
    if "CenCoCo" in cwd_str or "cencoco" in cwd_str.lower():
        return "CenCoCo"
    return "DCSRE"  # default


def _resolve_cache_root() -> Path:
    """Locate .claude/meta-cache/ by walking up from cwd."""
    for parent in [Path.cwd(), *Path.cwd().parents]:
        candidate = parent / ".claude" / "meta-cache"
        if candidate.exists():
            return candidate
    return Path.cwd() / ".claude" / "meta-cache"


def _resolve_legacy_meta(rel_path: str) -> "Path | None":
    """Tier 6: legacy repo-local .claude/meta/{path} (BL-193 command-migration).

    Walk up from cwd for a .claude/meta/{rel_path} that exists. This is the
    redeploy-populated directory that the pre-migration commands hardcoded.
    Keeping it as the FINAL fallback guarantees the command-migration
    ({META}/X tokens) never downgrades: worst case a {META}/X token resolves
    to exactly the literal .claude/meta/X path the command used before.
    """
    for parent in [Path.cwd(), *Path.cwd().parents]:
        legacy = parent / ".claude" / "meta" / rel_path
        if legacy.exists():
            return legacy
    return None


def resolve_meta(rel_path: str, verbose: bool = False) -> "Path | None":
    """Resolve a meta file via 5-tier lookup. Returns Path or None."""
    # 1. Local-Override (.claude/meta-override/ — per-project, never committed) [BL-193 AK-10]
    local = Path.cwd() / ".claude" / "meta-override" / rel_path
    vault = resolve_vault_root()
    typ = resolve_project_typ()
    if local.exists():
        if verbose:
            print(f"[RESOLVED] via local-override: {local}", file=sys.stderr)
            # Stale-warn: if override older than vault-typ counterpart [BL-193 AK-10 PL-2]
            try:
                _typ_check = vault / "Meta" / "Typen" / typ / rel_path
                if _typ_check.exists() and local.stat().st_mtime < _typ_check.stat().st_mtime:
                    print(
                        f"[WARN] override may be stale: {rel_path} (override older than vault)",
                        file=sys.stderr,
                    )
            except OSError:
                pass
        return local
    # 2. Vault-Typ (online primary)
    try:
        typ_path = vault / "Meta" / "Typen" / typ / rel_path
        if typ_path.exists():
            if verbose:
                print(f"[RESOLVED] via vault-typ ({typ}): {typ_path}", file=sys.stderr)
            return typ_path
    except OSError:
        pass
    # 3. meta-cache-Typ (offline fallback) [BL-193 AK-7]
    cache_root = _resolve_cache_root()
    cache_typ = cache_root / "Typen" / typ / rel_path
    if cache_typ.exists():
        if verbose:
            print(f"[RESOLVED] via meta-cache-typ ({typ}): {cache_typ}", file=sys.stderr)
        return cache_typ
    # 4. Vault-Universal (online universal)
    try:
        uni_path = vault / "Meta" / "Universal" / rel_path
        if uni_path.exists():
            if verbose:
                print(f"[RESOLVED] via vault-universal: {uni_path}", file=sys.stderr)
            return uni_path
    except OSError:
        pass
    # 5. meta-cache-Universal (offline universal fallback) [BL-193 AK-7]
    cache_uni = cache_root / "Universal" / rel_path
    if cache_uni.exists():
        if verbose:
            print(f"[RESOLVED] via meta-cache-universal: {cache_uni}", file=sys.stderr)
        return cache_uni
    # 6. Legacy repo-local .claude/meta/ (redeploy-populated, final non-downgrading fallback) [BL-193]
    legacy = _resolve_legacy_meta(rel_path)
    if legacy is not None:
        if verbose:
            print(f"[RESOLVED] via legacy .claude/meta/: {legacy}", file=sys.stderr)
        return legacy
    return None


def resolve_command_sidecar(command_name: str) -> "Path | None":
    """BL-372 AK-9: resolve the command-keyed meta-sidecar path (thin adapter).

    Meta-Sidecar-Runtime-Konvention (BL-372): jeder Command DARF einen projekt-
    spezifischen Sidecar bei {vault_root}/_meta/commands/{command_name}_Meta.md tragen.
    Dieser DUENNE Adapter baut auf resolve_vault_root() (mehrstufig: env
    CLAUDE_VAULT_ROOT -> .vault_root walk-up -> Default) -> bildet den command-keyed
    Pfad -> gibt den Path zurueck wenn er existiert, sonst None. Exakt die resolve_meta-
    Semantik "erster Treffer oder None" (KEIN Crash): eine fehlende Datei ist KEIN
    Fehler (Always-Try-Load, AK-2/AK-3).

    SA-2 (feedback_markdown_engine_bootstrap): der KERN von BL-372 ist die Markdown-
    Always-Try-Load-Konvention je Command-Doc; dieser Resolver ist die OPTIONALE
    duenne Code-Stuetze fuer Commands, die einen aufgeloesten Pfad-String brauchen.
    Der projekt-spezifische INHALT lebt im Sidecar (Vault, nie redeployt); der Command
    selbst bleibt agnostisch.

    BL-372 AK-1/AK-8: '_meta/' ist der GEMEINSAME Vault-Meta-Wurzelkanon — command-keyed
    unter _meta/commands/ (BL-372), domain-keyed unter _meta/{domain}/ (BL-302 erbt).
    """
    vault = resolve_vault_root()
    sidecar = vault / "_meta" / "commands" / f"{command_name}_Meta.md"
    return sidecar if sidecar.exists() else None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Resolve a meta file via 5-tier lookup (resolve_meta) "
                    "or a command-keyed sidecar (BL-372 resolve_command_sidecar)."
    )
    parser.add_argument("rel_path", nargs="?", default=None,
                        help="Relative path to the meta file (resolve_meta)")
    parser.add_argument("--command-sidecar", metavar="COMMAND_NAME", default=None,
                        help="BL-372 AK-9: resolve {vault_root}/_meta/commands/{COMMAND_NAME}_Meta.md instead")
    parser.add_argument("--verbose", action="store_true", help="Print resolution-path to stderr")
    args = parser.parse_args()

    if args.command_sidecar is not None:
        # BL-372: Always-Try-Load — eine fehlende Sidecar-Datei ist KEIN Fehler (exit 0).
        sc = resolve_command_sidecar(args.command_sidecar)
        if sc:
            print(sc)
        else:
            print(f"NONE: no sidecar for command '{args.command_sidecar}'", file=sys.stderr)
        sys.exit(0)

    if args.rel_path is None:
        parser.error("either rel_path or --command-sidecar is required")
    result = resolve_meta(args.rel_path, verbose=args.verbose)
    if result:
        print(result)
        sys.exit(0)
    else:
        print(f"NOT_FOUND: {args.rel_path}", file=sys.stderr)
        sys.exit(2)
