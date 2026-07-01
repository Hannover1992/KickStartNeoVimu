#!/usr/bin/env python3
"""
gc_budgets.py — Bloat-Budget-Registry (BL-338 / batch_PL1 / PL-338-1, M3 Stufe 1).

Generalisiert den O(1)-Budget-Begriff aus manifest_slim.py (Working-Set-
Schwellwert) auf eine Policy-Registry je Langzeit-Artefakt-Typ: pro Typ ein
{budget_bytes|budget_lines, strategy_hint}, aufgeloest aus EINER YAML-Quelle.

Stil-Vorlage: resolve_format_version.py (find_*_yaml / load_* / resolve_*,
dependency-freier Minimal-Parser, Dual-Read-Resilienz NIE Crash).

cwd-STABILITAETS-MANDAT (PL-336-4-Lehre):
  find_gc_budgets_yaml() loest den REPO_FALLBACK __file__-RELATIV auf
  (Path(__file__).resolve().parent.parent / "config" / "gc_budgets.yaml"),
  NICHT cwd-relativ. So liefert resolve_budget(typ) aus JEDEM cwd identische
  Werte (vermeidet die cwd-Artefakt-false-GREEN von BL-335/336).

Kern-Prinzip — Dual-Read-Resilienz (NIE Crash):
  - find_gc_budgets_yaml()->None / Datei fehlt -> load_gc_budgets() == {}
  - unbekannter Typ                           -> resolve_budget() == None
  - budget None / unbekannter Typ             -> over_budget() == False

Aufruf:
  python3 .claude/scripts/gc_budgets.py [TYP]
  python3 .claude/scripts/gc_budgets.py --format=json
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# __file__-RELATIVER Fallback (cwd-INVARIANT) — der Kern von G_cwd.
# .../.claude/scripts/gc_budgets.py -> parent.parent == .../.claude
REPO_FALLBACK = Path(__file__).resolve().parent.parent / "config" / "gc_budgets.yaml"

ROOT_KEY = "gc_budgets"


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


def find_gc_budgets_yaml() -> Path | None:
    """Vault-First: vault/config/gc_budgets.yaml -> __file__-relativer Repo-Fallback.

    Der Repo-Fallback ist __file__-RELATIV (cwd-invariant): liefert aus jedem cwd
    denselben existierenden Pfad ODER None — nie ein cwd-relatives Phantom (G_cwd).
    Datei fehlt -> None.
    """
    vault = resolve_vault_root()
    if vault is not None:
        candidate = vault / "config" / "gc_budgets.yaml"
        if candidate.is_file():
            return candidate
    if REPO_FALLBACK.is_file():
        return REPO_FALLBACK
    return None


def parse_yaml_minimal(text: str) -> dict:
    """Minimaler YAML-Parser fuer gc_budgets.yaml (ohne PyYAML-Dependency).

    Unterstuetzt die Struktur:
      gc_budgets:
        {typ}:
          budget_bytes: {int}    (ODER budget_lines: {int})
          strategy_hint: {str}
    Fuer komplexe YAMLs PyYAML installieren — dieser Parser ist Fallback.
    """
    try:
        import yaml  # type: ignore
        for doc in yaml.safe_load_all(text):
            if isinstance(doc, dict) and ROOT_KEY in doc:
                return doc
        return {}
    except ImportError:
        pass

    # Minimal-Parser: gc_budgets: {typ: {budget_bytes|budget_lines, strategy_hint}}
    out: dict = {ROOT_KEY: {}}
    in_root = False
    current_typ: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith(f"{ROOT_KEY}:"):
            in_root = True
            continue
        if not in_root:
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 2 and stripped.endswith(":"):
            # neuer Typ-Eintrag (z.B. "  manifest:")
            current_typ = stripped[:-1].strip()
            out[ROOT_KEY][current_typ] = {}
        elif indent >= 4 and current_typ is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()
            if k in ("budget_bytes", "budget_lines"):
                try:
                    out[ROOT_KEY][current_typ][k] = int(v)
                except ValueError:
                    out[ROOT_KEY][current_typ][k] = v
            else:
                # strategy_hint o.ae.: als String (Quotes optional abstreifen).
                out[ROOT_KEY][current_typ][k] = v.strip('"').strip("'")
    return out


def load_gc_budgets() -> dict:
    """Laedt die Registry-Map {typ: {budget_bytes|budget_lines, strategy_hint}}.

    find_gc_budgets_yaml()->None ODER Datei fehlt/unlesbar -> leere Map (kein Crash).
    """
    path = find_gc_budgets_yaml()
    if path is None:
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    config = parse_yaml_minimal(text)
    return config.get(ROOT_KEY, {}) or {}


def resolve_budget(typ: str) -> int | None:
    """Budget-Zahlwert fuer einen Artefakt-Typ (budget_bytes bevorzugt, sonst budget_lines).

    unbekannter Typ / fehlende Registry / kein numerischer Wert -> None (KEIN KeyError/Crash).
    """
    config = load_gc_budgets()
    entry = config.get(typ)
    if not isinstance(entry, dict):
        return None
    for key in ("budget_bytes", "budget_lines"):
        if key in entry:
            try:
                return int(entry[key])
            except (TypeError, ValueError):
                return None
    return None


def over_budget(typ: str, actual: int) -> bool:
    """True, wenn actual den Policy-Schwellwert des Typs ueberschreitet.

    budget None (unbekannter Typ / fehlende Registry) -> False (kein Crash, kein
    falscher Alarm). Vergleich strikt: actual > budget.
    """
    budget = resolve_budget(typ)
    if budget is None:
        return False
    return actual > budget


def main(argv: list[str]) -> int:
    fmt = None
    typ = None
    for arg in argv[1:]:
        if arg.startswith("--format="):
            fmt = arg.split("=", 1)[1]
        elif not arg.startswith("--"):
            typ = arg

    path = find_gc_budgets_yaml()
    if path is None:
        print("ERROR: gc_budgets.yaml weder in Vault noch in Repo gefunden", file=sys.stderr)
        return 1

    config = load_gc_budgets()

    if fmt == "json":
        json.dump(config, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if typ is not None:
        budget = resolve_budget(typ)
        print("" if budget is None else budget)
        return 0

    # Default: alle Typen mit Budget + strategy_hint.
    for t, entry in config.items():
        if isinstance(entry, dict):
            budget = entry.get("budget_bytes", entry.get("budget_lines", ""))
            print(f"{t}\t{budget}\t{entry.get('strategy_hint', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
