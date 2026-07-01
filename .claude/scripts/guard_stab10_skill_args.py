#!/usr/bin/env python3
"""
guard_stab10_skill_args.py — Intra-Skill Stabilization Hook S#10 (Pflicht-Args).

PreToolUse-Hook fuer Skill-Tool:
  Blockiert Skill-Aufrufe ohne Pflicht-Args, um stille Skip-Drift (Phantom-DONE)
  zu verhindern.

Hintergrund:
  Skill(_A_orchestrate) ohne BL-ID-Arg fuehrt zu einem Skill der "garnichts" macht
  weil er nicht weiss welches BL er bearbeiten soll. Skill returnt aber exit_code:0
  -> Phantom-DONE in Audit-Trail, aber keine Arbeit verrichtet.

Pflicht-Args-Map (welcher Skill braucht welche Args):
  _A_orchestrate         : erstes positional BL-\\d+ ODER --resume
  _IDF_orchestrate       : erstes positional BL-\\d+ ODER --resume
  _SDF_orchestrate       : --batch= ODER --task-source= ODER --resume
  _I_orchestrate         : --stage= ODER --resume
  _SC_orchestrate        : --batch= ODER --resume
  _PostBatch_orchestrate : BL-Name positional ODER --stages=
  _Pre_PR_orchestrate    : KEINE Pflicht (nackt erlaubt)

Skills die NICHT in der Map sind: passthrough (kein Check).

Pragmatik-Override: `--allow-noargs` Marker in args umgeht den Block.

Modi:
  enforceProcess=true  (Default) -> BLOCK (continue=false)
  enforceProcess=false           -> WARN (continue=true, message=...)

Test-Override: OMNI_ENFORCE_STAB10_GUARD=1 erzwingt enforce=true (pytest).

Style-Reference: guard_modus_writer.py, guard_a_routing_target.py.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# ----------------------------------------------------------------------------
# Pflicht-Args-Map: Skill-Name -> Regel-Spec
# ----------------------------------------------------------------------------
# Regel-Spec ist eine Liste von Regel-Dicts. Mindestens EINE Regel muss matchen.
# Regel-Typen:
#   {"type": "positional_regex", "pattern": r"^BL-\d+$"}  -> erstes Token matched Pattern
#   {"type": "flag_prefix", "value": "--resume"}          -> Flag (mit/ohne Wert) im args
#   {"type": "flag_with_value", "value": "--batch="}      -> --batch=<wert>
# Die "decline_reason" wird im Block-Message fuer den User angezeigt.
PFLICHT_ARGS_MAP: dict[str, dict] = {
    "_A_orchestrate": {
        "rules": [
            {"type": "positional_regex", "pattern": r"^[A-Z]+-\d+$"},
            {"type": "flag_prefix", "value": "--resume"},
            {"type": "flag_with_value", "value": "--bl-id="},
        ],
        "decline_reason": (
            "erstes positional Arg muss '[A-Z]+-\\d+' (BL-XXX, DCSRE-XXX, ...) ODER '--resume' ODER '--bl-id=...' gesetzt sein"
        ),
    },
    "_IDF_orchestrate": {
        "rules": [
            {"type": "positional_regex", "pattern": r"^[A-Z]+-\d+$"},
            {"type": "flag_prefix", "value": "--resume"},
            {"type": "flag_with_value", "value": "--bl-id="},
            {"type": "flag_prefix", "value": "--pl-only"},  # parking-lot loop mode (v3.0)
        ],
        "decline_reason": (
            "erstes positional Arg muss '[A-Z]+-\\d+' (BL-XXX, DCSRE-XXX, ...) ODER '--resume' ODER '--bl-id=...' ODER '--pl-only' gesetzt sein"
        ),
    },
    "_SDF_orchestrate": {
        "rules": [
            {"type": "flag_with_value", "value": "--batch="},
            {"type": "flag_with_value", "value": "--task-source="},
            {"type": "flag_prefix", "value": "--resume"},
        ],
        "decline_reason": (
            "braucht '--batch=<id>' ODER '--task-source=<src>' ODER '--resume' Flag"
        ),
    },
    "_I_orchestrate": {
        "rules": [
            {"type": "flag_with_value", "value": "--stage="},
            {"type": "flag_prefix", "value": "--resume"},
        ],
        "decline_reason": (
            "braucht '--stage=<n>' ODER '--resume' Flag"
        ),
    },
    "_SC_orchestrate": {
        "rules": [
            {"type": "flag_with_value", "value": "--batch="},
            {"type": "flag_prefix", "value": "--resume"},
        ],
        "decline_reason": (
            "braucht '--batch=<id>' ODER '--resume' Flag"
        ),
    },
    "_PostBatch_orchestrate": {
        "rules": [
            {"type": "positional_regex", "pattern": r"^BL-[A-Za-z0-9_-]+$"},
            {"type": "flag_with_value", "value": "--stages="},
        ],
        "decline_reason": (
            "braucht BL-Name positional (BL-...) ODER '--stages=<list>' Flag"
        ),
    },
    "_Pre_PR_orchestrate": {
        "rules": [],  # leer = keine Pflicht (passthrough)
        "decline_reason": "",
    },
}

# Pragmatik-Override-Marker
ALLOW_NOARGS_MARKER = "--allow-noargs"


# ----------------------------------------------------------------------------
# Session-Params + enforce-Toggle
# ----------------------------------------------------------------------------


def _resolve_vault_session_params() -> Path:
    try:
        import subprocess
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5,
                cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                vault_root_str = proc.stdout.strip()
                if vault_root_str:
                    return Path(vault_root_str) / "_session_params.md"
    except Exception:
        pass
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


SESSION_PARAMS_FILE = _resolve_vault_session_params()


def read_enforce_process() -> bool:
    """Liest enforceProcess aus _session_params.md.
    Test-Override: OMNI_ENFORCE_STAB10_GUARD=1 erzwingt enforce=true.
    Default: True wenn Datei fehlt (sicher).
    """
    if os.environ.get("OMNI_ENFORCE_STAB10_GUARD") == "1":
        return True
    if os.environ.get("OMNI_ENFORCE_STAB10_GUARD") == "0":
        return False
    try:
        if not SESSION_PARAMS_FILE.exists():
            return True
        content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
        if m:
            return m.group(1).strip().lower() == "true"
    except Exception:
        pass
    return True


# ----------------------------------------------------------------------------
# B (state-aware Auto-Resume): Ein nackter Orchestrator-Aufruf wird akzeptiert
# wenn der persistierte State resumebar ist — der Orchestrator liest ihn via
# --resume-Semantik selbst. Verhindert dass ein KORREKTER Block den Prozess
# stallt, obwohl die Info die das fehlende Flag liefern wuerde bereits im State
# liegt (DF_BATCH_STATE). Das ist der eigentliche Self-Heal: kein Block, kein
# Retry-Zyklus — der Prozess laeuft einfach weiter.
#
# Konservativ (BL-RESILIENZ 2026-05-28): NUR fuer _SDF_orchestrate, und NUR wenn
# der aktuelle DF_BATCH_STATE-Block NICHT-TERMINAL ist (sonst bleibt der Block —
# echter Phantom-Skip-Schutz: ein nackter Call ohne resumebaren State macht nix).
#
# Kill-Switch: OMNI_STAB10_NO_AUTORESUME=1  -> B deaktiviert (Block wie zuvor).
# Test-Override: OMNI_STAB10_AUTORESUME_MANIFEST=<pfad> -> B liest diese Datei.
# ----------------------------------------------------------------------------

STATE_RESUMABLE_SKILLS = {"_SDF_orchestrate"}
# PRAEZISIERT 2026-05-31 (DCSRE-486 Round-19 Live-Stall, Compact-Anomalie): NUR die echten
# Batch-Lifecycle-Felder batch_status/df_status zaehlen als terminal. FRUEHER matchte das nackte
# `status:` JEDES `status: DONE` im Scope — und _current_df_batch_scope slict bis EOF, also auch den
# nachfolgenden IDF_FINAL_SUMMARY/finalSummary-Block (`status: DONE` = BERATER fertig, NICHT Batch
# fertig). Folge: nach IDF_DONE (neuer Batch geplant) blockte ein nackter _SDF_orchestrate, weil der
# finalSummary-`status:DONE` faelschlich als Batch-terminal gelesen wurde -> Prozess stallte.
_TERMINAL_STATE_RE = re.compile(
    r"(?:batch_status|df_status)\s*[:=]\s*\"?(DONE|COMPLETE|COMPLETED|ABORTED|CLOSED|FINISHED|EMPTY)",
    re.IGNORECASE,
)
# ERWEITERT 2026-05-31: IDF-geplant-pending-Signale. Nach IDF_DONE (--no-chain/--pl-only/Compact)
# liegt der neue Batch in coverage_per_batch/metric_per_batch/IDF_FINAL_SUMMARY (recommended_next) —
# das IST resumebarer State (SDF soll den geplanten Batch fahren), auch wenn die kanonische
# batch_items_per_batch-Map (noch) stale ist. Erkennt der Hook diese Signale -> Auto-Resume statt Stall.
_RESUMABLE_SIGNAL_RE = re.compile(
    r"(batch_order|current_sub_batch|batch_items_per_batch|batch_mode_hints|"
    r"batch_modes|batch_stages|READY_FOR|IN_PROGRESS|RESUME|"
    r"coverage_per_batch|metric_per_batch|batch_coverage_verdict|recommended_next|"
    r"idf_status|IDF_DONE)",
    re.IGNORECASE,
)
# Resume-Chain-Signale IM ARGS-STRING (Fallback wenn Manifest unlesbar, BL-RESILIENZ 2026-05-29):
# Wenn current_context.py im Worktree leeren/non-JSON-stdout liefert (Subprozess crasht still),
# kann das Manifest NICHT gelesen werden -> B kann den resumebaren State nicht sehen -> Block stallt
# den IDF->SDF-Handover. Ein args-String mit diesen Chain-Markern BEWEIST aber einen legitimen
# Pipeline-Handoff (IDF-Auto-Chain) -> Auto-Resume statt Stall (corrective-enforcement).
# Phantom-Skip-Schutz bleibt: WIRKLICH nackte args (kein Marker) -> kein Auto-Resume.
_ARGS_RESUME_SIGNAL_RE = re.compile(
    r"(--from=|IDF_DONE|current_sub_batch|DF_BATCH_STATE|batch_mode_hints|batch_modes|Goal\s*=)",
    re.IGNORECASE,
)


def _read_active_manifest_content() -> str:
    """Aktiven Manifest-Inhalt lesen (per-BL-folder-aware via _manifest_resolver).

    Test-Gating: bei gesetztem OMNI_ENFORCE_STAB10_GUARD (pytest-Modus) ohne
    expliziten Manifest-Override ist B deaktiviert — sonst wuerden die
    Bestandstests den ECHTEN Repo-State sehen und nicht-deterministisch werden.
    """
    if os.environ.get("OMNI_STAB10_NO_AUTORESUME") == "1":
        return ""
    test_path = os.environ.get("OMNI_STAB10_AUTORESUME_MANIFEST")
    if test_path:
        try:
            p = Path(test_path)
            return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        except Exception:
            return ""
    # pytest-Modus ohne B-Override -> B aus (deterministische Bestandstests)
    if os.environ.get("OMNI_ENFORCE_STAB10_GUARD") is not None:
        return ""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from _manifest_resolver import read_active_manifest

        vault_root = SESSION_PARAMS_FILE.parent
        content, _p = read_active_manifest(SCRIPT_DIR, ROOT_DIR, vault_root=vault_root)
        return content or ""
    except Exception:
        return ""


def _current_df_batch_scope(content: str) -> str:
    """Slice ab dem LETZTEN DF_BATCH_STATE-Vorkommen.

    Das Manifest ist append-only — nur der AKTUELLE Block zaehlt, nicht
    historische Rounds (verhindert false-positive durch alte terminale States).
    """
    if not content:
        return ""
    idx = content.rfind("DF_BATCH_STATE")
    return content[idx:] if idx >= 0 else ""


def has_resumable_state(skill_name: str, args_str: str = "") -> tuple[bool, str]:
    """True wenn resumebar — via Manifest ODER (Fallback) via Resume-Chain-Signal im args.

    Reihenfolge:
      1. Manifest lesbar + TERMINAL  -> False (expliziter Done-State, respektieren).
      2. Manifest lesbar + Resume-Signal -> True.
      3. Manifest leer/unlesbar ODER ohne Signal -> ARGS-CHAIN-FALLBACK:
         args enthaelt Chain-Marker (--from=, IDF_DONE, current_sub_batch, DF_BATCH_STATE,
         batch_mode_hints, Goal=) -> True (legitimer Pipeline-Handoff, Manifest gerade unlesbar).
      4. sonst -> False (Phantom-Skip-Schutz: nackte args ohne State + ohne Chain-Marker).

    Der Args-Fallback ist LOAD-BEARING fuer den IDF->SDF-Handover: current_context.py kann im
    Worktree still scheitern (leerer stdout), dann ist das Manifest unlesbar — der args-Kontext
    ist dann die einzige verlaessliche Legitimitaets-Quelle (BL-RESILIENZ 2026-05-29).
    """
    if skill_name not in STATE_RESUMABLE_SKILLS:
        return False, "skill not in resumable set"
    scope = _current_df_batch_scope(_read_active_manifest_content())
    if scope and _TERMINAL_STATE_RE.search(scope):
        return False, "DF_BATCH_STATE terminal (Manifest)"
    if scope and _RESUMABLE_SIGNAL_RE.search(scope):
        return True, "manifest: DF_BATCH_STATE non-terminal + resumable signal"
    # Args-Chain-Fallback (Manifest leer/unlesbar ODER scope ohne Signal):
    if args_str and _ARGS_RESUME_SIGNAL_RE.search(args_str):
        return True, "args: resume-chain signal (Manifest unlesbar/ohne Signal)"
    return False, "no resumable state + no args chain-signal"


# ----------------------------------------------------------------------------
# Args-Tokenizing + Rule-Matching
# ----------------------------------------------------------------------------


def tokenize_args(args_str: str) -> list[str]:
    """Zerlegt args-String in Tokens (whitespace-split).

    Wir nehmen einfaches whitespace-split — Skill-Args sind im Regel-Fall
    flach (BL-218 --refresh-aks --foo=bar). Quoted-Strings werden NICHT
    extra behandelt; das ist akzeptabel weil unsere Patterns auf
    Pattern-Match basieren, nicht auf voll-strikter Shell-Parsing.
    """
    if not args_str:
        return []
    return [t for t in args_str.strip().split() if t]


def get_first_positional(tokens: list[str]) -> str | None:
    """Gibt erstes Token zurueck das NICHT mit '-' beginnt, sonst None."""
    for t in tokens:
        if not t.startswith("-"):
            return t
    return None


def rule_matches(rule: dict, tokens: list[str]) -> bool:
    """Prueft ob eine Regel von den Tokens erfuellt wird."""
    rtype = rule.get("type", "")
    if rtype == "positional_regex":
        pattern = rule.get("pattern", "")
        first_pos = get_first_positional(tokens)
        if first_pos is None:
            return False
        try:
            return bool(re.match(pattern, first_pos))
        except re.error:
            return False
    elif rtype == "flag_prefix":
        # Flag mit oder ohne Wert: --resume, --resume=foo, --resume bar
        flag = rule.get("value", "")
        for t in tokens:
            if t == flag:
                return True
            if t.startswith(flag + "="):
                return True
        return False
    elif rtype == "flag_with_value":
        # Flag MIT inline-Wert: --batch=<x>
        flag_eq = rule.get("value", "")
        for t in tokens:
            if t.startswith(flag_eq) and len(t) > len(flag_eq):
                return True
        return False
    return False


def build_recovery_command(skill_name: str, args_str: str, rule_spec: dict) -> str:
    """A (aktionable Recovery): konstruiert das EXAKTE Retry-Kommando das den
    Block aufloest und den Prozess fortsetzt.

    Praeferenz-Reihenfolge:
      1. '--resume' wenn als Regel erlaubt — ECHTES Self-Heal: der Orchestrator
         liest seinen persistierten State (DF_BATCH_STATE / Round-State) und setzt
         dort fort. Kein Stall, keine manuelle Arg-Rekonstruktion.
      2. erste flag_with_value-Regel als Platzhalter (--batch=<wert>).
      3. positional-Regel als Hinweis (<BL-XXX>).

    Hintergrund: Ein korrekter Block der nur 'fehlt Flag' sagt, laesst den
    Prozess stehen (der Agent weiss nicht WELCHES Flag WIE). Ein Block der das
    fertige Kommando mitliefert ist eine Wegweisung statt einer Sackgasse.
    """
    rules = rule_spec.get("rules") or []
    base = f"/{skill_name} {args_str}".rstrip()
    # 1. --resume bevorzugen (Self-Heal via State-Resume)
    for r in rules:
        if r.get("type") == "flag_prefix" and r.get("value") == "--resume":
            return f"{base} --resume"
    # 2. erste flag_with_value-Regel
    for r in rules:
        if r.get("type") == "flag_with_value":
            return f"{base} {r['value']}<wert>".rstrip()
    # 3. positional-Regel
    for r in rules:
        if r.get("type") == "positional_regex":
            return f"/{skill_name} <{r.get('pattern', 'BL-XXX')}> {args_str}".rstrip()
    return base


def args_satisfy_rules(args_str: str, rule_spec: dict) -> tuple[bool, str]:
    """Prueft ob args mindestens eine Regel der rule_spec erfuellen.

    Returns:
        (ok, reason) — ok=True wenn Pflicht erfuellt; reason erklaert bei False.
    """
    rules = rule_spec.get("rules") or []
    decline_reason = rule_spec.get("decline_reason", "")

    # Pragmatik-Override greift IMMER (auch wenn rules leer)
    if args_str and ALLOW_NOARGS_MARKER in args_str:
        return True, f"override via {ALLOW_NOARGS_MARKER}"

    if not rules:
        # Keine Pflicht-Regeln -> immer ok
        return True, "no required args (passthrough)"

    tokens = tokenize_args(args_str)
    for rule in rules:
        if rule_matches(rule, tokens):
            return True, f"rule matched: {rule}"

    return False, decline_reason


# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------


def append_guard_log(skill_name: str, args_str: str, reason: str, blocked: bool) -> None:
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = (
            f"- [{timestamp}] **STAB10_SKILL_ARGS** [{action}]: "
            f"skill={skill_name} args={args_str!r} reason={reason}\n"
        )
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def append_debug_log(msg: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] guard_stab10_skill_args: {msg}\n")
    except Exception:
        pass


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------


def main() -> None:
    # === Globaler Owner-Kill-Switch (BL-223): enforceProcess=false -> Guard aus ===
    import os as _os, json as _json
    if _os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(_json.dumps({"continue": True}))
        return
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sd = str(_P(__file__).parent.absolute())
        if _sd not in _sys.path:
            _sys.path.insert(0, _sd)
        from _enforce_gate import enforce_active
        if not enforce_active():
            print(_json.dumps({"continue": True}))
            return
    except Exception:
        pass
    try:
        raw = sys.stdin.read()
        hook_data = json.loads(raw)
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        # Frueh-Exit: Nur Skill-Tool relevant
        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        if not isinstance(tool_input, dict):
            print(json.dumps({"continue": True}))
            return

        skill_name = (tool_input.get("skill") or "").strip()
        args_str = tool_input.get("args") or ""

        # Passthrough fuer Skills die nicht in der Pflicht-Map stehen
        if skill_name not in PFLICHT_ARGS_MAP:
            print(json.dumps({"continue": True}))
            return

        rule_spec = PFLICHT_ARGS_MAP[skill_name]
        ok, reason = args_satisfy_rules(args_str, rule_spec)

        if ok:
            print(json.dumps({"continue": True}))
            return

        # B (state-aware Auto-Resume): BEVOR wir blocken — haelt der State die
        # fehlende Info schon? Dann ist es kein Phantom-Skip sondern ein
        # legitimer Resume. Block waere zwar "korrekt" (Flag fehlt formal),
        # wuerde aber den Prozess stallen obwohl alles Noetige im State liegt.
        resumable, why = has_resumable_state(skill_name, args_str)
        if resumable:
            recovery = build_recovery_command(skill_name, args_str, rule_spec)
            auto_msg = (
                f"[STAB10 AUTO-RESUME] Skill({skill_name}) ohne explizites Flag — "
                f"aber {why}. Als impliziter --resume akzeptiert: der Orchestrator "
                f"liest DF_BATCH_STATE selbst und setzt fort. Prozess laeuft weiter "
                f"(statt korrektem-Block-mit-Stall). Explizit waere: {recovery}"
            )
            append_guard_log(skill_name, args_str, f"AUTO-RESUME ({why})", blocked=False)
            print(json.dumps({"continue": True, "message": auto_msg}))
            return

        # Violation: Pflicht-Arg fehlt -> evtl. Phantom-Skip
        enforce = read_enforce_process()
        recovery = build_recovery_command(skill_name, args_str, rule_spec)
        message = (
            f"[GUARD-VIOLATION] STAB10_SKILL_ARGS (Intra-Skill Stabilization S#10): "
            f"Skill({skill_name}) ohne Pflicht-Arg — moegliche Phantom-Skip. args={args_str!r}.\n"
            f"  -> RETRY (loest Block, setzt Prozess fort): {recovery}\n"
            f"  -> Required: {reason}\n"
            f"  -> Pragmatik-Override: '{ALLOW_NOARGS_MARKER}' im args wenn bewusst nackt aufgerufen.\n"
            f"  {'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )
        print(json.dumps({
            "continue": not enforce,
            "message": message,
        }))
        append_guard_log(skill_name, args_str, f"{reason} | recovery={recovery}", enforce)

    except json.JSONDecodeError as e:
        append_debug_log(f"JSONDecodeError: {e}")
        print(json.dumps({"continue": True}))
    except Exception as e:
        append_debug_log(f"Unexpected error: {e}")
        # Fail-open bei Hook-Fehler — Pipeline darf nicht durch Guard-Bug stehen
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
