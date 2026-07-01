#!/usr/bin/env python3
"""
resolve_vault_root.py — Single Source of Truth fuer Vault-Root-Resolution.

ARCH-N8 (BL-154 ARCH-Delta-3): Konsolidiert 3 konkurrierende Vault-Resolver
in eine kanonische 4-stufige Fallback-Kette.

Resolver-Reihenfolge (PFLICHT, nicht veraenderbar):
  1. ENV VAR `CLAUDE_VAULT_ROOT`           (PRIMAER — toolname-spezifisch, canonical)
  2. ENV VAR `OBSIDIAN_VAULT_PATH`         (BACKWARDS-COMPAT — deprecated nach 1 Release)
  3. Datei `.claude/.vault_root` im CWD   (per-project pin)
  4. vault-routing.json Path-Pattern-Detection (utf-8-sig BOM aware)
     -> Prueft path-pattern rules gegen CWD-Name
     -> Mapped auf vaults[vault].linux_path
  5. Heuristik: ~/Documents/{cwd_name}    (letzter Fallback)

Kanonische ENV-Var: CLAUDE_VAULT_ROOT
Deprecation-Hinweis: OBSIDIAN_VAULT_PATH wird in Release N+1 entfernt.
  Setze CLAUDE_VAULT_ROOT stattdessen (identischer Wert).

Pattern-Referenz: PT-SCR-002 (Vault-Path-Resolver-Scripts)
Lead-Follow:      Diese Datei = Lead. resolve_bl_path.py = Follow (delegiert hierher).

Aufruf:
  python3 resolve_vault_root.py
  -> /home/uczen/Documents/OmniCommand

  python3 resolve_vault_root.py --debug
  -> zeigt Resolver-Schritt der gematcht hat
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Kanonischer Pfad zu vault-routing.json (relativ zum Skript-Verzeichnis)
_VAULT_ROUTING_DEFAULT = Path(__file__).parent.parent / "config" / "vault-routing.json"

# Deprecated ENV-Var (Backwards-Compat, ARCH-N10)
_ENV_DEPRECATED = "OBSIDIAN_VAULT_PATH"
_ENV_CANONICAL = "CLAUDE_VAULT_ROOT"


def resolve_vault_root(
    cwd: Path | None = None,
    vault_routing_path: Path | None = None,
    *,
    debug: bool = False,
) -> Path:
    """Resolves den absoluten Vault-Root-Pfad.

    Args:
        cwd: Arbeitsverzeichnis (default: Path.cwd())
        vault_routing_path: Pfad zu vault-routing.json (default: .claude/config/vault-routing.json)
        debug: Gibt Resolver-Schritt als stderr-Meldung aus

    Returns:
        Absoluter Pfad zum Vault-Root

    Resolver-Reihenfolge:
        1. ENV CLAUDE_VAULT_ROOT          (canonical, PRIMAER)
        2. ENV OBSIDIAN_VAULT_PATH        (backwards-compat, deprecated)
        3. .claude/.vault_root pin-File   (per-project override)
        4. vault-routing.json Detection   (path-pattern auf CWD-Name)
        5. ~/Documents/{cwd_name}         (Heuristik, letzter Fallback)
    """
    if cwd is None:
        cwd = Path.cwd()
    if vault_routing_path is None:
        vault_routing_path = _VAULT_ROUTING_DEFAULT

    # ── Stufe 1: ENV CLAUDE_VAULT_ROOT (canonical) ─────────────────────────
    env_canonical = os.environ.get(_ENV_CANONICAL)
    if env_canonical:
        result = Path(env_canonical)
        if debug:
            print(f"[resolve_vault_root] Stufe 1 (ENV {_ENV_CANONICAL}): {result}", file=sys.stderr)
        return result

    # ── Stufe 2: ENV OBSIDIAN_VAULT_PATH (deprecated backwards-compat) ─────
    env_deprecated = os.environ.get(_ENV_DEPRECATED)
    if env_deprecated:
        result = Path(env_deprecated)
        if debug:
            print(
                f"[resolve_vault_root] Stufe 2 (ENV {_ENV_DEPRECATED}, DEPRECATED "
                f"— verwende {_ENV_CANONICAL} stattdessen): {result}",
                file=sys.stderr,
            )
        return result

    # ── Stufe 3: .claude/.vault_root pin-File ───────────────────────────────
    pin = cwd / ".claude" / ".vault_root"
    if pin.is_file():
        try:
            content = pin.read_text(encoding="utf-8").strip()
            if content:
                result = Path(content)
                if debug:
                    print(f"[resolve_vault_root] Stufe 3 (pin {pin}): {result}", file=sys.stderr)
                return result
        except OSError:
            pass  # pin nicht lesbar → naechste Stufe

    # ── Stufe 4: vault-routing.json Path-Pattern-Detection ─────────────────
    if vault_routing_path.is_file():
        try:
            # utf-8-sig beachtet BOM (Windows-generierte JSON-Dateien)
            raw = vault_routing_path.read_text(encoding="utf-8-sig")
            routing = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            routing = None

        if routing is not None:
            cwd_str = str(cwd)
            rules = routing.get("detection", {}).get("rules", [])
            vaults_cfg = routing.get("vaults", {})

            # Regeln nach Prioritaet sortieren (niedrigste Zahl = hoechste Prio)
            sorted_rules = sorted(rules, key=lambda r: r.get("priority", 999))

            for rule in sorted_rules:
                pattern = rule.get("pattern", "")
                if not pattern or pattern == "*":
                    continue  # Wildcard-Fallback ueberspringen in dieser Stufe
                if pattern.lower() in cwd_str.lower():
                    vault_key = rule.get("vault")
                    if vault_key and vault_key in vaults_cfg:
                        vault_entry = vaults_cfg[vault_key]
                        linux_path = vault_entry.get("linux_path", "")
                        if linux_path and linux_path != "UNKLAR":
                            result = Path(linux_path)
                            if debug:
                                print(
                                    f"[resolve_vault_root] Stufe 4 (vault-routing.json "
                                    f"pattern='{pattern}' → vault={vault_key}): {result}",
                                    file=sys.stderr,
                                )
                            return result

    # ── Stufe 5: Heuristik ~/Documents/{cwd_name} ───────────────────────────
    cwd_name = cwd.name
    candidate = Path.home() / "Documents" / cwd_name
    if debug:
        print(
            f"[resolve_vault_root] Stufe 5 (Heuristik ~/Documents/{cwd_name}): {candidate}",
            file=sys.stderr,
        )
    return candidate


def main(argv: list[str]) -> int:
    debug = "--debug" in argv
    result = resolve_vault_root(debug=debug)
    print(str(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
