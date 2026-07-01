#!/usr/bin/env python3
"""
worktree_hook_router.py — Cross-Worktree-Hook-Routing (BL-172 AK-4).

Entscheidet ob ein Hook-Call fuer den aktuellen Worktree relevant ist.
Filtert Hook-Calls die zu fremden Namespaces gehoeren.

INV-WORKTREE-1: Jeder Worktree verarbeitet NUR seine eigenen Hook-Calls.
INV-WORKTREE-3: Namespace-Resolution NUR via get_worktree_namespace().

Aufruf (CLI):
  py -3 worktree_hook_router.py route --hook=session_params_write --payload='...'
  py -3 worktree_hook_router.py list-hooks
  py -3 worktree_hook_router.py namespace
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

_SCRIPT_DIR = Path(__file__).parent.absolute()

# Lazy-import AK-1 helper to avoid circular dependency issues at module level
def _get_namespace(worktree_id: Optional[str] = None) -> Optional[str]:
    """Delegiert an worktree_aware_params.get_worktree_namespace()."""
    sys.path.insert(0, str(_SCRIPT_DIR))
    try:
        from worktree_aware_params import get_worktree_namespace
        return get_worktree_namespace(worktree_id)
    except ImportError as e:
        raise RuntimeError(
            f"worktree_aware_params.py nicht gefunden in {_SCRIPT_DIR}: {e}"
        ) from e


# ── Hook-Registry ──────────────────────────────────────────────────────────────

# Hooks die Namespace-Filterung benoetigen
_NAMESPACE_SCOPED_HOOKS = frozenset({
    "session_params_write",
    "session_params_read",
    "param_change",
    "guard_session_params_protection",
    "audit_hook",
    "pre_write",
    "post_write",
    # BL-317 SB-4 (AK-1): die echten Pipeline-Guards die das Manifest CWD-relativ
    # loesen (via current_context / _manifest_resolver). In Multi-Worktree muss
    # ein Worker NUR seine eigenen Hook-Calls verarbeiten (INV-WORKTREE-1).
    # Logischer Hook-Name = Script-Basename (ohne .py).
    "guard_geist5_idf_to_sdf",
    "guard_geist6_sdf_internal",
    "guard_geist9_post_sdf",
    "guard_stab10_skill_args",
    "guard_step_adherence_reminder",
})

# Hooks die IMMER global (fuer alle Worktrees) ausgefuehrt werden
_GLOBAL_HOOKS = frozenset({
    "conflict_check",
    "vault_health",
    "git_status",
})


def is_hook_relevant(
    hook_name: str,
    payload: Optional[dict] = None,
    worktree_id: Optional[str] = None,
) -> tuple[bool, str]:
    """Bestimmt ob ein Hook fuer den aktuellen Worktree relevant ist.

    Args:
        hook_name: Name des Hooks (z.B. 'session_params_write').
        payload: Optionales Payload-Dictionary (kann 'worktree_id' enthalten).
        worktree_id: Optionale explizite Worktree-ID fuer Tests.

    Returns:
        Tuple (relevant: bool, reason: str).
        relevant=True  → Hook SOLL ausgefuehrt werden.
        relevant=False → Hook SOLL uebersprungen werden (fremder Namespace).
    """
    if payload is None:
        payload = {}

    # Globale Hooks immer ausfuehren
    if hook_name in _GLOBAL_HOOKS:
        return True, f"global-hook: {hook_name} wird immer ausgefuehrt"

    current_ns = _get_namespace(worktree_id)

    # Single-Worktree-Modus: alle Hooks relevant (INV-WORKTREE-2)
    if current_ns is None:
        return True, "single-worktree-mode: kein Namespace-Filter aktiv"

    # Namespace-scoped Hooks: Payload-Namespace pruefen
    if hook_name in _NAMESPACE_SCOPED_HOOKS:
        payload_ns = payload.get("worktree_id") or payload.get("namespace")
        if payload_ns is None:
            # Kein Namespace im Payload → fuer aktuellen Worktree relevant
            return True, f"namespace={current_ns}: kein Payload-Namespace → relevant"

        payload_ns_clean = payload_ns.replace("/", "_").replace("\\", "_").strip()
        if payload_ns_clean == current_ns:
            return True, f"namespace={current_ns}: Payload-Namespace stimmt ueberein"
        else:
            return (
                False,
                f"namespace-mismatch: current={current_ns}, payload={payload_ns_clean} → skip",
            )

    # Unbekannter Hook: sicherheitshalber ausfuehren
    return True, f"unbekannter-hook: {hook_name} → ausfuehren (safe default)"


def route_hook(
    hook_name: str,
    payload: Optional[dict] = None,
    worktree_id: Optional[str] = None,
) -> dict:
    """Haupt-Routing-Funktion. Gibt Routing-Entscheidung als Dictionary zurueck.

    Args:
        hook_name: Name des Hooks.
        payload: Optionales Payload-Dictionary.
        worktree_id: Optionale explizite Worktree-ID.

    Returns:
        Dictionary mit keys: hook, relevant, reason, namespace, mode.
    """
    if payload is None:
        payload = {}

    current_ns = _get_namespace(worktree_id)
    mode = "multi" if current_ns is not None else "single"

    relevant, reason = is_hook_relevant(hook_name, payload, worktree_id)

    return {
        "hook": hook_name,
        "relevant": relevant,
        "reason": reason,
        "namespace": current_ns,
        "mode": mode,
    }


def route_hooks_batch(
    hooks: list[dict],
    worktree_id: Optional[str] = None,
) -> list[dict]:
    """Verarbeitet mehrere Hook-Routing-Entscheidungen auf einmal.

    Args:
        hooks: Liste von Dictionaries mit 'hook' (str) und optional 'payload' (dict).
        worktree_id: Optionale explizite Worktree-ID.

    Returns:
        Liste von Routing-Dictionaries.
    """
    results = []
    for h in hooks:
        hook_name = h.get("hook", "")
        payload = h.get("payload", {})
        results.append(route_hook(hook_name, payload, worktree_id))
    return results


# ── settings.json-Entrypoint (BL-317 SB-4, AK-1) ─────────────────────────────────

def route_hook_event(event: Optional[dict]) -> tuple[bool, dict]:
    """Fail-open Routing-Entrypoint fuer einen Claude-Code-PreToolUse-Event.

    Dies ist der Adapter, der in settings.json eingehaengt wird (via `hook`-CLI).
    Er klassifiziert NIE als Block: der Rueckgabe-`continue`-Flag ist IMMER True.
    Im Multi-Worktree-Fall wird ein fremder Namespace lediglich als
    `relevant=False` in der Diagnostik vermerkt (advisory) — der Tool-Call laeuft
    trotzdem weiter. So bleibt der Single-Worktree-Pfad bit-identisch (Z88-89:
    namespace==None → relevant=True) und das Immunsystem wird NIE zugemauert.

    INV-G3-1 (Router fail-open): JEDE Exception → continue=True. Ein kaputter
    Router darf den Tool-Call NICHT blockieren.

    Args:
        event: Das PreToolUse-Event-Dict (tool_name/tool_input/...), oder None.

    Returns:
        Tuple (continue_flag: bool, payload: dict). continue_flag ist IMMER True.
        payload traegt Routing-Diagnostik (hook/relevant/reason/namespace/mode).
    """
    try:
        if not isinstance(event, dict):
            return True, {"relevant": True, "reason": "fail-open: kein dict-Event", "mode": "single"}

        # Hook-Name: bevorzugt explizites Feld, sonst tool_name als Surrogat.
        hook_name = event.get("hook") or event.get("hook_name") or event.get("tool_name") or ""

        # Worktree-Hinweis aus dem Event ziehen (falls vorhanden) — sonst leeres Payload.
        payload: dict = {}
        if event.get("worktree_id"):
            payload["worktree_id"] = event["worktree_id"]
        elif event.get("namespace"):
            payload["namespace"] = event["namespace"]

        result = route_hook(hook_name, payload)
        # continue ist IMMER True (INV-G3-1): skip = advisory, kein Block.
        return True, result
    except Exception as e:  # noqa: BLE001 — fail-open ist heilig
        return True, {"relevant": True, "reason": f"fail-open: {e}", "mode": "single"}


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cmd_route(args: argparse.Namespace) -> int:
    """CLI: route --hook=NAME --payload='JSON'."""
    payload: dict = {}
    if args.payload:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as e:
            print(f"ERROR: Ungueltige Payload-JSON: {e}", file=sys.stderr)
            return 2

    result = route_hook(args.hook, payload)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status = "RELEVANT" if result["relevant"] else "SKIP"
        print(f"[{status}] hook={result['hook']}")
        print(f"  namespace={result['namespace']}")
        print(f"  mode={result['mode']}")
        print(f"  reason={result['reason']}")

    # Exit-Code: 0 = relevant, 1 = skip (ermoeglicht Shell-Nutzung als Guard)
    return 0 if result["relevant"] else 1


def _cmd_list_hooks(_args: argparse.Namespace) -> int:
    """CLI: list-hooks — zeigt bekannte Hook-Kategorien."""
    print("Namespace-scoped Hooks (werden gefiltert bei Multi-Worktree):")
    for h in sorted(_NAMESPACE_SCOPED_HOOKS):
        print(f"  - {h}")
    print("\nGlobale Hooks (werden immer ausgefuehrt):")
    for h in sorted(_GLOBAL_HOOKS):
        print(f"  - {h}")
    return 0


def _cmd_namespace(_args: argparse.Namespace) -> int:
    """CLI: namespace — zeigt aktuellen Worktree-Namespace."""
    ns = _get_namespace()
    mode = "multi" if ns is not None else "single"
    print(f"namespace={ns if ns is not None else '(none)'}")
    print(f"mode={mode}")
    return 0


def _cmd_hook(_args: argparse.Namespace) -> int:
    """CLI: hook — settings.json-PreToolUse-Entrypoint (BL-317 SB-4, AK-1).

    Liest das Claude-Code-Event von stdin und gibt {"continue": true} aus.
    INV-G3-1 (fail-open): IMMER continue:true, exit 0 — der Router blockiert NIE
    einen Tool-Call (Muster guard_vault_write_lock). Im Single-Worktree-Modus
    (namespace==None) ist das Verhalten bit-identisch zu "kein Router".
    """
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Kaputter/leerer stdin → fail-open continue (NIE Block).
        print(json.dumps({"continue": True}))
        return 0

    try:
        _cont, _diag = route_hook_event(event)
    except Exception:
        _cont = True
    # continue ist IMMER True (INV-G3-1). Diagnostik bewusst NICHT ausgegeben,
    # um die Hook-Ausgabe minimal/byte-stabil zu halten.
    print(json.dumps({"continue": True}))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Cross-Worktree-Hook-Routing (BL-172 AK-4)"
    )
    subparsers = parser.add_subparsers(dest="command")

    route_p = subparsers.add_parser("route", help="Routing-Entscheidung fuer einen Hook")
    route_p.add_argument("--hook", required=True, help="Hook-Name")
    route_p.add_argument("--payload", default="", help="Hook-Payload als JSON-String")
    route_p.add_argument("--json", action="store_true", help="JSON-Ausgabe")

    subparsers.add_parser("list-hooks", help="Zeigt bekannte Hook-Kategorien")
    subparsers.add_parser("namespace", help="Zeigt aktuellen Worktree-Namespace")
    subparsers.add_parser("hook", help="settings.json-PreToolUse-Entrypoint (fail-open, immer continue)")

    args = parser.parse_args(argv[1:])

    if args.command == "route":
        return _cmd_route(args)
    elif args.command == "list-hooks":
        return _cmd_list_hooks(args)
    elif args.command == "namespace":
        return _cmd_namespace(args)
    elif args.command == "hook":
        return _cmd_hook(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    # INV-G3-1: im settings.json-`hook`-Pfad ist fail-open HEILIG. Selbst ein
    # unerwarteter Crash (argparse, Import, IO) darf den Tool-Call NIE blockieren.
    _is_hook_path = len(sys.argv) >= 2 and sys.argv[1] == "hook"
    if _is_hook_path:
        try:
            sys.exit(main(sys.argv))
        except SystemExit:
            raise
        except Exception:
            print(json.dumps({"continue": True}))
            sys.exit(0)
    else:
        sys.exit(main(sys.argv))
