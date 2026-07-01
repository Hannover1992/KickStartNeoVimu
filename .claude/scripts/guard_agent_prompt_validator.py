#!/usr/bin/env python3
"""
Claude Code Hook — Agent-Prompt-Validator (Guard-Enforcement CS6+CS7)

Pre-Hook auf Tool-Calls: Erkennt ANTI-PATTERNS in Agent-Prompts.
- Anti-Pattern 1: Mega-Agent — ein Agent-Prompt enthaelt MEHRERE Pipeline-Commands
- Anti-Pattern 2: BDF→Agent() direkt statt BDF→SDF (CS6-F06 Repeat)
- Anti-Pattern 3: Agent() fuer Orchestrator-Calls statt Skill() (INV-PM-2)
- Anti-Pattern 4: Direkte Implementation via Agent statt SC→SDF→I Pipeline (CS8)

enforceProcess=true (Default): BLOCKIERT Violations (continue=false)
enforceProcess=false: NUR Warning (continue=true) — User-Override bei Prozess-Problemen
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"


def _coerce_text(val):
    """Flacht jede tool_input-Prompt-Shape zu durchsuchbarem String.

    Agent/Task-Prompts koennen dict (strukturierter Prompt) oder list
    (Content-Bloecke) sein, nicht nur str. re.search() auf ein Nicht-str wirft
    'expected string or bytes-like object, got dict' -> der bare except in
    main() faellt dann OPEN. Coercion zu str degradiert sauber (Command-Namen
    matchen weiter im serialisierten JSON). Root-Cause des Dauer-Fail-Open seit
    2026-05-24 (BL-210).
    """
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        for k in ("text", "content", "prompt", "value", "message", "description"):
            if k in val:
                return _coerce_text(val[k])
        try:
            return json.dumps(val, ensure_ascii=False)[:20000]
        except Exception:
            return str(val)[:20000]
    if isinstance(val, (list, tuple)):
        return "\n".join(_coerce_text(v) for v in val)[:20000]
    return str(val)[:20000]


def _resolve_vault_path(key):
    """Resolve process state file path from vault-routing.json."""
    routing_path = Path(__file__).parent.parent / "config" / "vault-routing.json"
    if routing_path.exists():
        try:
            with open(routing_path, encoding='utf-8') as f:
                routing = json.load(f)
            for rule in routing.get("detection", {}).get("rules", []):
                psf = rule.get("process_state_files", {})
                if key in psf:
                    return Path(psf[key])
        except Exception:
            pass
    # Fallback: alte lokale Pfade
    fallbacks = {
        "manifest": ROOT_DIR / ".claude" / "analysis" / "_manifest.md",
        "manifest_protokoll": ROOT_DIR / ".claude" / "analysis" / "_manifest_protokoll.md",
        "backlog_index": ROOT_DIR / ".claude" / "analysis" / "_backlog_index.md",
        "session_params": ROOT_DIR / ".claude" / "analysis" / "_session_params.md",
        "task": ROOT_DIR / ".claude" / "Task.md",
        "parking_lot": ROOT_DIR / ".claude" / "analysis" / "_parking-lot.md",
    }
    return fallbacks.get(key)


SESSION_PARAMS_FILE = _resolve_vault_path("session_params")
LOG_FILE = ROOT_DIR / ".hook_debug.log"

# [BL-422 AK-1] A-Pipeline-Wellen-Skills: spawnen intern Wellen -> MUESSEN Lead-Skill-geladen
# werden, NICHT an Agent delegiert (INV-AO-CALLER).
WAVE_SKILLS = ["_spec", "_K_score", "_model", "_gap"]

# Pipeline-Commands die Wellen brauchen
PIPELINE_COMMANDS = [
    "_W_fetch", "_taskDefinition", "_model", "_spec", "_gap", "_K_score",
    "_SC_observe", "_SC_hypothese", "_SC_implement", "_SC_ergebnis",
    "_I_orchestrate", "_A_orchestrate", "_SC_orchestrate",
]

# Orchestrator-Commands die NUR via Skill() aufgerufen werden duerfen (INV-PM-2)
# BL-439 F-08: _IDF_orchestrate, _SDF_orchestrate_post, _PostBatch_/_PrePhase_/_W_/_BL_orchestrate ergaenzt.
# WICHTIG: _SDF_orchestrate_post VOR _SDF_orchestrate (laengster Praefix zuerst beim cmd-Scan).
ORCHESTRATOR_COMMANDS = [
    "_A_orchestrate", "_SC_orchestrate", "_I_orchestrate",
    "_IDF_orchestrate", "_SDF_orchestrate_post", "_SDF_orchestrate",
    "_TDD_orchestrate", "_WP_orchestrate",
    "_BDF_orchestrate", "_BL_orchestrate", "_W_orchestrate",
    "_PostBatch_orchestrate", "_PrePhase_orchestrate",
    "_stage_orchestrate", "_T_orchestrate",
    "_DiffReduce", "_AC_orchestrate", "_smoothing",
    "_W_push_orchestrate", "_finish", "_Pre_PR_orchestrate",
]

# BDF-Interne Commands die NICHT direkt an Agent delegiert werden duerfen
BDF_INTERNAL = ["_BDF_orchestrate", "_BDF_batchPlan"]

# BL-064 T2 RF-02: ORCHESTRATOR_ONLY Schicht 1 — reine Orchestrator-Routing-Prompts
# BL-439 F-08: _IDF_orchestrate, _SDF_orchestrate_post u.a. _X_orchestrate ergaenzt.
ORCHESTRATOR_ONLY_COMMANDS = {
    "_A_orchestrate", "_SC_orchestrate", "_I_orchestrate",
    "_IDF_orchestrate", "_SDF_orchestrate_post", "_SDF_orchestrate",
    "_TDD_orchestrate", "_BDF_orchestrate", "_BL_orchestrate",
    "_W_orchestrate", "_PostBatch_orchestrate", "_PrePhase_orchestrate",
    "_stage_orchestrate", "_T_orchestrate", "_DiffReduce",
    "_AC_orchestrate", "_smoothing", "_W_push_orchestrate",
    "_finish", "_Pre_PR_orchestrate", "_WP_orchestrate",
}

# BL-064 T2 RF-02: Erlaubte 2er-Paare aus Pipeline-Workflow (Schicht 3)
# KRITISCH (INV-03/RF-07): _W_fetch DARF NIE in dieser Liste auftauchen
ALLOWED_COMMAND_PAIRS = {
    frozenset(["_taskDefinition", "_model"]),
    frozenset(["_spec", "_K_score"]),
    frozenset(["_gap", "_K_score"]),
    frozenset(["_model", "_gap"]),
    frozenset(["_K_score", "_I_orchestrate"]),
    frozenset(["_taskDefinition", "_A_orchestrate"]),
    frozenset(["_spec", "_A_orchestrate"]),
    frozenset(["_gap", "_SC_orchestrate"]),
}

# ── Mega-Worker-Diskriminator (BL-210, 2026-05-28) ─────────────────────────
# STRUKTURELL, nicht lexikalisch: ein Worker der einen ORCHESTRATOR ausfuehrt
# (Mega-/Dispatch-Worker) vs. ein Worker der EINE Phase macht (legit, von
# I_orchestrate/TDD gespawnt). Generische Verben allein sind KEIN Signal — sie
# stehen in jedem legitimen Worker-Prompt ("fuehre die Analyse aus").
SINGLE_PHASE_COMMANDS = [
    "_I_cleanCodeSlice", "_I_cleanCodeArchitect", "_I_codeAtomic", "_I_codeSystem",
    "_I_blueprintArchitect", "_I_blueprintQG", "_I_goldDefine", "_I_diffAudit",
    "_I_verify", "_I_testSearch", "_TDD_red", "_TDD_green", "_TDD_refactor",
    "_TDD_execute", "_TDD_check", "_berater_",
]
# Execution-Verb das DIREKT einen Orchestrator-Namen governt ("run _I_orchestrate",
# "fuehre Skill(_I_orchestrate) aus"). NICHT "fuehre die Blueprint-Analyse fuer ...".
_EXEC_GOVERNS_ORCH_RE = re.compile(
    r'\b(run|execute|fuehre|führe|ausfuehren|ausführen|starte|laufe|spawne)\s+'
    r'(?:den\s+|the\s+|das\s+|skill\(|/|_)*'
    r'(I_orchestrate|SC_orchestrate|SDF_orchestrate_post|SDF_orchestrate|A_orchestrate|'
    r'IDF_orchestrate|TDD_orchestrate|BDF_orchestrate|PostBatch_orchestrate)\b',
    re.IGNORECASE,
)
# Klammer-Paren-Form (BL-439 Blindspot): `Skill(_X_orchestrate)` / `Skill('_X_orchestrate')`.
# Verb-unabhaengig — die Paren-Notation IST das Exec-Signal (ein Orchestrator-Name in
# Skill()-Klammern in einem Agent-Prompt = INV-AO-CALLER-Verletzung). Aus ORCHESTRATOR_COMMANDS
# generiert (laengster Praefix zuerst, damit _SDF_orchestrate_post vor _SDF_orchestrate matcht).
_PAREN_ORCH_RE = re.compile(
    r'skill\(\s*["\']?(' + "|".join(re.escape(c) for c in
        sorted(ORCHESTRATOR_COMMANDS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)
# Strukturelle Rollen-Marker: der Worker IST ein Dispatcher (kein Single-Phase-Arbeiter).
_DISPATCH_ROLE_MARKERS = [
    "dispatch-worker", "dispatch worker", "dispatch-agent", "dispatch agent",
    "dispatch-step", "phase-2-dispatch", "phase 2 dispatch", "phase-2 dispatch",
    "puppet-master", "puppet master",
]


def is_orchestrator_exec_contract(prompt_text):
    """True wenn der Spawn-Prompt einen Agent anweist, einen ORCHESTRATOR
    auszufuehren (Mega-/Dispatch-Worker) statt eine Single-Phase zu machen.

    (a) praeziser Single-Phase-Command genannt -> IMMER legit (False);
    (b) Dispatcher-Rollen-Marker ("SDF-Phase-2-Dispatch-Worker") -> Verletzung;
    (c) Execution-Verb governt direkt einen Orchestrator-Namen -> Verletzung.
    """
    txt = prompt_text if isinstance(prompt_text, str) else _coerce_text(prompt_text)
    low = txt.lower()
    # BL-439 AK-5: Orchestrator-Paren-Match hat PRIORITAET vor der SINGLE_PHASE/Berater-
    # Whitelist. Ein KOMBINIERTER Prompt (Skill(_X_orchestrate) + _berater_) rutschte sonst
    # durch den _berater_-early-return (Z davor) BEVOR _PAREN_ORCH_RE geprueft wurde.
    # _PAREN_ORCH_RE matcht NUR Orchestrator-Namen (nicht _berater_) -> reine Berater-Prompts
    # fallen weiter zur Whitelist durch (FP-sicher, T-f09-4/5).
    if _PAREN_ORCH_RE.search(txt):  # BL-439: Skill(_X_orchestrate) Klammer-Form
        return True
    if any(c.lower() in low for c in SINGLE_PHASE_COMMANDS):
        return False
    if any(m in low for m in _DISPATCH_ROLE_MARKERS):
        return True
    if _EXEC_GOVERNS_ORCH_RE.search(txt):
        return True
    return False


def read_modus():
    """Liest DF_BATCH_STATE.modus (M1..M9) aus dem Manifest — READ-ONLY (INV-MODUS-1).

    Aufloesung: OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST (Test-Override) >
    _resolve_vault_path('manifest') > None. Jede Exception -> None (FAIL-OPEN).
    Regex: modus\\s*:\\s*"?(M[0-9])"? (case-insensitive). [BL-423 AK-b]
    """
    import os as _os
    try:
        path = None
        env_path = _os.environ.get("OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST")
        if env_path:
            path = Path(env_path)
        else:
            path = _resolve_vault_path("manifest")
        if path is None or not path.is_file():
            return None
        content = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'modus\s*:\s*"?(M[0-9])"?', content, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    except Exception:
        return None
    return None


# ── Monolithic-Build-Worker-Diskriminator (BL-423 AK-b, Check 5) ───────────
# Ein Worker der im selben Prompt Test-SCHREIBEN UND Implementieren buendelt
# kollabiert RED- und GREEN-Rolle (false-GREEN-Risiko). NUR in M2/M3 relevant
# (M1/None short-circuit), NUR ohne Single-Phase-Whitelist-Eintrag.
_MONO_TEST_SIGNAL_RE = re.compile(
    r'schreib\w*.{0,20}test'
    r'|tests?\s+und\b'
    r'|write\s+tests?'
    r'|unit-?tests?.{0,20}(und|and)\b',
    re.IGNORECASE | re.DOTALL,
)
_MONO_IMPL_SIGNAL_RE = re.compile(
    r'implementier'
    r'|implement\b'
    r'|baue\b.{0,30}(controller|dto|mapping|code|klasse)',
    re.IGNORECASE | re.DOTALL,
)


def detect_monolithic_build_worker(prompt, tool_name, modus):
    """True wenn ein Worker-Spawn Test-Schreiben UND Impl im selben Prompt buendelt
    (RED+GREEN-Kollaps) — nur in M2/M3, nur ohne Single-Phase-Whitelist. [BL-423 AK-b]

    Returns (is_violation, hint|None).
    """
    if modus not in ("M2", "M3"):
        return (False, None)  # IV-b2: M1/None short-circuit
    low = (prompt or "").lower()
    if any(c.lower() in low for c in SINGLE_PHASE_COMMANDS):
        return (False, None)  # IV-b3: Whitelist-Inversion (legitimer Single-Phase)
    test_signal = bool(_MONO_TEST_SIGNAL_RE.search(prompt or ""))
    impl_signal = bool(_MONO_IMPL_SIGNAL_RE.search(prompt or ""))
    if test_signal and impl_signal:
        return (True, "Lead laedt Skill(_I_orchestrate); RED-Worker != GREEN-Worker (test+impl getrennt)")
    return (False, None)


# ── M1-Skeleton-Overreach-Diskriminator (BL-400 AK-1..AK-5, Check 6) ────────
# Schwester von Check 5 fuer den M1-Fast-Lane-Vektor: ein M1-Skelett-Worker der
# MEHR als das sanktionierte 4-Step-Subset buendelt (Skelett-fremde Steps) ODER
# ein Lead-inline-Code-Emit ohne _I_orchestrate/--scope=skeleton-Handschuh.
# NUR in M1 relevant (andere Modi short-circuit, analog Check-5-IV-b2).
#
# Sanktioniertes 4-Step-Subset (PASS): architecturalLibrary, patternLibrary,
# semanticLibrary, codeAtomic. Steps AUSSERHALB = Overreach.
M1_SKELETON_SUBSET = [
    "_I_architecturalLibrary", "_I_patternLibrary",
    "_I_semanticLibrary", "_I_codeAtomic",
]
# Skelett-fremde Steps: alles aus SINGLE_PHASE_COMMANDS jenseits des 4-Step-Subsets,
# plus Stufen-Loop-/Fan-Marker. Nennung im M1-Prompt = Scope-Ueberschreitung (AK-2).
_M1_OVERREACH_STEPS = [
    "_I_testSearch", "_I_blueprintQG", "_I_blueprintArchitect", "_I_goldDefine",
    "_I_cleanCodeSlice", "_I_cleanCodeArchitect", "_I_codeSystem", "_I_codeIntegration",
    "_I_codeE2E", "_I_codeFullSystem", "_I_diffAudit", "_I_verify",
    "_I_mitose", "_I_fanOut", "_I_fanIn", "_I_requirementCheck",
    "_TDD_red", "_TDD_green", "_TDD_refactor", "_TDD_execute", "_TDD_check",
]
# Sanktionierter Handschuh-Marker: M1 via Skill(_I_orchestrate --scope=skeleton)
# ODER ein einzelner Skelett-Subset-Step. Praesenz -> legit (kein Overreach).
_M1_SCOPE_SKELETON_RE = re.compile(r'--scope=skeleton', re.IGNORECASE)
# Lead-inline-Code-Emit-Signal: der Lead schreibt selbst Code OHNE Worker/Skill-Load (AK-3).
_M1_INLINE_EMIT_RE = re.compile(
    r'(schreib\w*\s+direkt|inline|selbst\s+implementier|lead\s+implementiert\s+selbst'
    r'|kein\s+worker|kein\s+skill-?load|ohne\s+skill-?load)',
    re.IGNORECASE | re.DOTALL,
)


def detect_anonymous_wellen_spawn(prompt, tool_input_dict):
    """BL-422 AK-4: Erkennt anonyme Agent-Spawns mit Wellen-Worker-Marker.

    Definition anonym: Wellen-Koordinations-Marker im Prompt UND KEIN name UND KEIN team_name
    im tool_input_dict. Benannte Member (name + team_name beide gesetzt) -> PASS.
    Kein Wellen-Marker im Prompt -> PASS (AK-4 greift nicht).
    Single-Phase-Command im Prompt -> PASS (legit Single-Phase-Worker, kein Wellen-Spawn).

    FP-Schutz: Explorer-Prompts sind erste Wellen-Stufe (autark, kein Koordinations-
    Input von anderen Rollen noetig) -> PASS (FP-Schutz analog AK-1 wellen-marker-Pfad).
    Drafter/Synthese benoetigen Koordinations-Outputs anderer Rollen -> echte Violation.

    Returns (is_violation: bool, hint: str|None).
    [BL-422 AK-4, INV-VEHIKEL-3]
    """
    if not prompt:
        return (False, None)
    # Single-Phase-Command-Whitelist: legitimer Single-Phase-Worker, kein Wellen-Spawn
    low = prompt.lower()
    if any(c.lower() in low for c in SINGLE_PHASE_COMMANDS):
        return (False, None)
    # Nur wenn Wellen-Worker-Marker vorhanden (Drafter/Synthese/Wellen-Koordinator)
    if not is_wellen_worker_marker(prompt):
        return (False, None)
    # FP-Schutz: Explorer-Prompts sind autarke erste Wellen-Stufe -> PASS
    # (analog AK-1 wellen_worker_marker FP-Schutz, BL-422 AK-4 FP-Erweiterung)
    header = prompt[:200].lower()
    if header.startswith("explorer"):
        return (False, None)
    # Benannte Member: name + team_name beide gesetzt -> kein FP
    agent_name = (tool_input_dict or {}).get("name")
    team_name = (tool_input_dict or {}).get("team_name")
    if agent_name and team_name:
        return (False, None)
    # Anonym: Wellen-Koordinations-Marker (Drafter/Synthese) + fehlende Identitaet
    hint = (
        "ANON_WELLEN_SPAWN: anonymer Agent-Spawn mit Wellen-Marker erkannt. "
        "INV-VEHIKEL-3 fordert benannte Member (name + team_name) + TaskCreate(blockedBy). "
        "FIX: Agent(name='...', team_name='...') ODER TaskCreate(blockedBy=[...]) verwenden. "
        "Benannte Member sichern gegenseitige Sichtbarkeit (false-GREEN-Schutz, INV-BUILD-GRAIN)."
    )
    return (True, hint)


def detect_m1_skeleton_overreach(prompt, tool_name, modus):
    """True wenn ein M1-Skelett-Worker das sanktionierte 4-Step-Subset ueberschreitet
    (Skelett-fremde Steps) oder ein Lead-inline-Code-Emit ohne _I_orchestrate-Handschuh
    beschreibt. NUR in M1 (andere Modi short-circuit). [BL-400 AK-1..AK-5]

    Returns (is_violation, hint|None).
    """
    if modus not in ("M1",):
        return (False, None)  # AK-1: Modus-Gate short-circuit (analog Check-5-IV-b2)
    txt = prompt or ""
    # AK-4b: sanktionierter Handschuh-Marker (Skill(_I_orchestrate --scope=skeleton))
    # -> der vollstaendige Subset-Dispatch ist KEIN Overreach.
    if _M1_SCOPE_SKELETON_RE.search(txt):
        return (False, None)
    low = txt.lower()
    # AK-2: Skelett-fremde Steps (Overreach) — Nennung jenseits des 4-Step-Subsets.
    overreach_hint = (
        "M1 = 4-Step-Subset (architecturalLibrary, patternLibrary, semanticLibrary, "
        "codeAtomic); Skill(_I_orchestrate --scope=skeleton), keine Skelett-fremden Steps buendeln"
    )
    if any(s.lower() in low for s in _M1_OVERREACH_STEPS):
        return (True, overreach_hint)
    # AK-3: Lead-inline-Code-Emit ohne Skill-Handschuh -> Verletzung.
    if _M1_INLINE_EMIT_RE.search(txt):
        return (True, (
            "INV-PM-1 ABSOLUT: M1 via Skill(_I_orchestrate --worker-mode --scope=skeleton), "
            "kein Lead-Self-Inline"
        ))
    # AK-4a: legitimer Single-Phase-Skelett-Step (nur Subset-Eintrag) -> PASS.
    return (False, None)


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true.

    Aufloesung (BL-350 Fix): OMNI_SESSION_PARAMS (Test-Override) >
    vault-resolved SESSION_PARAMS_FILE > Default true."""
    import os as _os
    _enforce_re = re.compile(r'\*\*enforceProcess:\*\*\s*(true|false)', re.IGNORECASE)
    # OMNI_SESSION_PARAMS env override (Test-Helper-Prioritaet, vgl. guard_a_idf_handoff.py)
    sp = _os.environ.get("OMNI_SESSION_PARAMS")
    if sp and Path(sp).exists():
        try:
            content = Path(sp).read_text(encoding="utf-8", errors="replace")
            m = _enforce_re.search(content)
            if m:
                return m.group(1).lower() == "true"
        except Exception:
            pass
        return True  # Temp-file vorhanden aber kein Match -> konservativ enforce
    try:
        if SESSION_PARAMS_FILE and SESSION_PARAMS_FILE.exists():
            content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
            m = _enforce_re.search(content)
            if m:
                return m.group(1).lower() == "true"
    except Exception:
        pass
    return True  # Default: enforce


def is_wellen_worker_marker(prompt_text):
    """BL-064 T4 RF-04/RF-08: Case-insensitive Header-Suffix-Matcher.
    Erste 200 Zeichen, lowercase. Suffix-Liste IDENTISCH zu guard_wellen_reminder.py."""
    if not prompt_text:
        return False
    header = prompt_text[:200].lower()
    suffixes = ["-e0", "-d0", "-synthese", "explorer", "drafter",
                "synthese", "welle", "worker", "observe"]
    return any(suffix in header for suffix in suffixes)


def detect_mega_agent(prompt_text):
    """Erkennt Mega-Agent. BL-064 T2 RF-02: 3-Schichten-Whitelist mit Goldstandard-Schutz."""
    if not prompt_text:
        return False, []
    found = []
    for cmd in PIPELINE_COMMANDS:
        pattern = rf'(?:^|[\s/])({re.escape(cmd)})\b'
        if re.search(pattern, prompt_text):
            found.append(cmd)
    if len(found) <= 1:
        return False, found

    # BL-064 T2 RF-02 Schicht 1: Reine Orchestrator-Routing-Prompts erlaubt
    if all(cmd in ORCHESTRATOR_ONLY_COMMANDS for cmd in found):
        return False, found

    # BL-064 T2 RF-02 Schicht 2: 1 Non-Orch + 1-2 Orch (mit _W_fetch Goldstandard-Schutz, INV-03)
    non_orch = [c for c in found if c not in ORCHESTRATOR_ONLY_COMMANDS]
    orch_part = [c for c in found if c in ORCHESTRATOR_ONLY_COMMANDS]
    if len(non_orch) == 1 and 1 <= len(orch_part) <= 2 and "_W_fetch" not in non_orch:
        return False, found

    # BL-064 T2 RF-02 Schicht 3: Statische Pair-Matrix (genau 2 Commands)
    if len(found) == 2 and frozenset(found) in ALLOWED_COMMAND_PAIRS:
        return False, found

    return True, found


def detect_bdf_bypass(prompt_text):
    """Erkennt ob BDF direkt an Agent delegiert statt ueber SDF."""
    if not prompt_text:
        return False
    has_bdf_context = any(kw in prompt_text for kw in ["BDF", "BigDarkFactory", "BATCH", "SCANNING"])
    has_direct_pipeline = any(cmd in prompt_text for cmd in ["_model", "_spec", "_gap", "_I_orchestrate", "_SC_orchestrate"])
    has_sdf_routing = any(kw in prompt_text for kw in ["SDF", "_SDF_orchestrate", "task_source"])
    return has_bdf_context and has_direct_pipeline and not has_sdf_routing


def detect_orchestrator_via_agent(prompt_text, tool_name):
    """Erkennt ob ein Orchestrator via Agent() statt Skill() aufgerufen wird (INV-PM-2)."""
    if not prompt_text or tool_name != "Agent":
        return False, None
    # NEU (BL-210 Mega-Worker-Backstop): ein Worker-Spawn der einen ORCHESTRATOR
    # AUSFUEHRT (Dispatch-Worker) ist immer Verletzung — VOR der Schicht-1-Ausnahme,
    # sonst wuerde ein "run _I_orchestrate"-Vertrag als reines Routing durchgewunken.
    if is_orchestrator_exec_contract(prompt_text):
        for cmd in ORCHESTRATOR_COMMANDS:
            if re.search(rf'(?:^|[\s/("\'])({re.escape(cmd)})\b', prompt_text):
                return True, cmd
        return True, "_<orchestrator>"

    # Schicht 1: Reine Orchestrator-Routing-Prompts (z.B. Finish-Trio) — erlaubt
    found_pipeline = [cmd for cmd in PIPELINE_COMMANDS
                      if re.search(rf'(?:^|[\s/("\'])({re.escape(cmd)})\b', prompt_text)]
    if found_pipeline and all(cmd in ORCHESTRATOR_ONLY_COMMANDS for cmd in found_pipeline):
        return False, None

    # [BL-422 AK-1] Wave-Skill-Exec-via-Agent: A-Wellen-Skill an Agent delegiert statt Lead-Skill-Handschuh.
    # FP-Schutz: NUR wenn KEIN Wellen-Worker-Marker (legitimes Wellen-Member) UND kein SINGLE_PHASE-Eintrag.
    if not is_wellen_worker_marker(prompt_text) \
       and not any(c.lower() in prompt_text.lower() for c in SINGLE_PHASE_COMMANDS):
        for cmd in WAVE_SKILLS:
            # Exec-Verb governt den Wave-Skill-Namen ODER "lade Skill _spec"
            if re.search(rf'\b(run|execute|fuehre|führe|ausfuehren|ausführen|starte|spawne|lade)\b[^\n]{{0,40}}\b{re.escape(cmd)}\b',
                         prompt_text, re.IGNORECASE):
                return True, cmd

    for cmd in ORCHESTRATOR_COMMANDS:
        # Suche nach "Fuehre /_X_orchestrate aus", "/_X_orchestrate {NAME}" oder
        # Klammer-Paren-Form "Skill(_X_orchestrate)" / "Skill('_X_orchestrate')" (BL-439).
        pattern = rf'(?:^|[\s/("\'])({re.escape(cmd)})\b'
        if re.search(pattern, prompt_text):
            # Erlaubt: Wenn der Prompt TEIL einer Welle ist (z.B. Explorer/Drafter)
            if not is_wellen_worker_marker(prompt_text):
                return True, cmd
    return False, None


def detect_direct_impl_bypass(prompt_text, tool_name):
    """DEAKTIVIERT 2026-05-04 (BL-151) — siehe Folge-Task NEU-GUARD-2.

    Originale Anti-Pattern-Detection (CS8): Team Lead spawnt Worker die direkt
    .claude/commands/*.md editieren statt SC→SDF→I Pipeline zu nutzen.

    PROBLEM: Substring-Match auf '_SDF_'/'_TDD_'/'_IDF_' im Prompt war zu grob.
    Jeder legitime Worker-Spawn der einen Berater-Skill nennt wurde geblockt.
    Whitelist-Aufblähung (30+ Marker) hat den Check funktional ausgehöhlt.

    REPLACEMENT: implementation_gate.py auf Edit/Write-Tools — feiner-granular,
    fängt echte Direct-Impl-Bypasses auf Tool-Call-Ebene ab.

    Folge-Task BL-151 NEU-GUARD-2: Refactor mit präzisem Tool-Call-Match (regex
    auf Edit\\(.\\.claude/commands/_X_) statt Substring im Prompt-Text.
    """
    return False, None
    # ============================================================================
    # AUSKOMMENTIERTER ORIGINAL-CODE — bei Reaktivierung zuerst Refactor (NEU-GUARD-2)
    # ============================================================================
    if not prompt_text or tool_name != "Agent":
        return False, None

    # Implementation-Keywords im Prompt
    impl_keywords = [
        "implementiere", "implementieren", "fuege ein", "editiere", "editieren",
        "schreibe in", "aendere", "patch", "fix", "einfuegen",
        "IMPLEMENTIERE", "SCHREIBE", "Insert", "Cluster",
        "I-Worker", "impl-", "Implement",
    ]

    # Ziel-Dateien die NUR durch I_orchestrate editiert werden duerfen
    protected_paths = [
        ".claude/commands/", ".claude/meta/", ".claude/scripts/",
        "_orchestrate.md", "_BDF_", "_SDF_", "_A_orchestrate", "_SC_",
        "_I_orchestrate", "_TDD_", "_WP_",
    ]

    has_impl_keyword = any(kw.lower() in prompt_text.lower() for kw in impl_keywords)
    has_protected_path = any(path in prompt_text for path in protected_paths)

    if not (has_impl_keyword and has_protected_path):
        return False, None

    # ERLAUBT: Wellen-Worker (Explorer/Drafter/Synthese) — die LESEN nur
    is_wellen = any(
        suffix in prompt_text
        for suffix in ["-E0", "-D0", "-synthese", "Explorer", "Drafter", "Observe", "observe"]
    )
    if is_wellen:
        return False, None

    # ERLAUBT: Worker die explizit von I_orchestrate gespawnt wurden
    is_i_worker = any(
        marker in prompt_text
        for marker in ["_I_cleanCodeSlice", "_I_codeAtomic", "_I_codeSystem",
                       "I_PIPELINE_STATE", "Slice", "Blueprint", "goldDefine"]
    )
    if is_i_worker:
        return False, None

    # ERLAUBT (NEU 2026-05-04): SDF/IDF/BDF/TDD-Worker Marker
    is_sdf_worker = any(
        marker in prompt_text
        for marker in ["_SDF_berater_", "_IDF_berater_", "_BDF_orchestrate",
                       "archBrief", "patternBrief", "modusEntscheidung",
                       "executionDispatch", "batchEnde", "recalibrate",
                       "postItem", "statusTransition", "stateMaintain",
                       "loopDecision", "garbageCollection",
                       "SDF Phase", "IDF Phase", "BDF Phase",
                       "DF_PIPELINE_STATE", "DF_BATCH_STATE",
                       "plAggregation", "akExtraktion", "validator",
                       "itemContext", "dependencyAnalyzer", "clustering",
                       "sequencePlanner", "batchPlan", "resumeGuard",
                       "specParse",
                       # TDD-Worker (NEU 2026-05-04, Iteration 2)
                       "_TDD_red", "_TDD_green", "_TDD_refactor",
                       "_TDD_execute", "_TDD_check", "_TDD_orchestrate",
                       "TDD Ring", "TDD Stufe", "TDD Stage",
                       "Ring 1", "Ring 2", "Ring 3",
                       "GOLD reached", "RED FAIL", "GREEN PASS",
                       "TDD_PIPELINE_STATE", "TDD_STATE", "TDD_INSTRUCTIONS"]
    )
    if is_sdf_worker:
        return False, None

    # ERLAUBT: I-Pipeline ist aktiv (i_status=RUNNING) — Agent-Spawns sind I_orchestrate Workers
    # guard_implementation_gate.py auf Edit|Write ist die echte Enforcement-Ebene
    try:
        manifest_path = _resolve_vault_path("manifest")
        if manifest_path.exists():
            manifest_content = manifest_path.read_text(encoding='utf-8')
            if "i_status: RUNNING" in manifest_content:
                return False, None
            if "sc_status: RUNNING" in manifest_content:
                return False, None
            if "sdf_status: RUNNING" in manifest_content:
                return False, None
            if "df_status: ITEM_LOOP" in manifest_content:
                return False, None
            if "idf_status: AK_PER_PL" in manifest_content:
                return False, None
    except Exception:
        pass

    # Finde welche geschuetzte Datei betroffen ist
    affected = [p for p in protected_paths if p in prompt_text]
    return True, affected


def append_guard_log(violation_type, details, blocked):
    """Appende Violation an GUARD_LOG Datei."""
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass


def append_audit_event(violation_type, details, blocked, ctx=None):
    """BL-064 T5 RF-05: Unified Audit-Schema fuer alle Guards.

    BL-439 AK-4: OMNI_AUDIT_JSONL_OVERRIDE (Test-Override) leitet die Zeile in einen
    isolierten temp-Pfad um, damit Tests das Event-Schema pruefen koennen.
    """
    import os as _os
    try:
        event = {
            "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "event": "GUARD_BLOCK" if blocked else "GUARD_WARN",
            "level": "BLOCK" if blocked else "WARN",
            "violation": violation_type,
            "details": details,
            "ctx": ctx or {"guard": "agent_prompt_validator"},
        }
        override = _os.environ.get("OMNI_AUDIT_JSONL_OVERRIDE")
        if override:
            audit_path = Path(override)
        else:
            AUDIT_DIR = ROOT_DIR / ".claude" / "audit"
            AUDIT_DIR.mkdir(parents=True, exist_ok=True)
            audit_path = AUDIT_DIR / "audit.jsonl"
        with open(audit_path, "a", encoding='utf-8') as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


def detect_phantom_opus(tool_name, tool_input):
    """Check 8: Phantom-opus — subagent_type='general-opus'/'opus' existiert nicht im Carrier.

    Carrier-Kanon BL-125/BL-461: opus-Tier via general-sonnet/general-purpose + model-Override,
    NIEMALS als subagent_type='general-opus'. Gibt (True, st) wenn Violation, (False, None) sonst.
    """
    if tool_name != "Agent":
        return (False, None)
    st = (tool_input.get("subagent_type") or "").strip().lower()
    if st in {"general-opus", "opus"}:
        return (True, st)
    return (False, None)


# Check 9: Haiku-Floor — Reasoning-Skills unter dem Floor (BL-452)
_REASONING_SKILL_RE = re.compile(
    r"Skill\(\s*_[A-Za-z_]+_berater_[A-Za-z_]+"
    r"|Skill\(\s*_TDD_(?:init|red|green|refactorCode|refactorTests|check|execute)\b"
    r"|Skill\(\s*_[A-Za-z_]+orchestrate\b",
    re.IGNORECASE,
)


def detect_haiku_floor_violation(tool_name, tool_input):
    """Check 9: Haiku-Floor — general-haiku fuer Reasoning-Spawn (berater/TDD-Kern/orchestrate).

    feedback_haiku_verboten + INV-NO-HAIKU-IN-TDD (BL-452):
    Berater + TDD-Kern + Orchestratoren benoetigen min. sonnet.
    Mechanische Executors (kein Reasoning-Skill-Load) sind exempt.
    Gibt (True, reason_str) wenn Violation, (False, None) sonst.
    """
    if tool_name != "Agent":
        return (False, None)
    st = (tool_input.get("subagent_type") or "").strip().lower()
    if st not in {"general-haiku", "haiku"}:
        return (False, None)
    prompt = str(tool_input.get("prompt") or tool_input.get("description") or "")
    m = _REASONING_SKILL_RE.search(prompt)
    if m:
        return (True, "matched reasoning-skill: " + m.group(0).strip())
    return (False, None)


def main():
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
        hook_data = json.loads(sys.stdin.read())
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        if tool_name not in ["Agent", "TaskCreate", "SendMessage"]:
            print(json.dumps({"continue": True}))
            return

        prompt = ""
        if isinstance(tool_input, dict):
            prompt = (_coerce_text(tool_input.get("prompt"))
                      or _coerce_text(tool_input.get("description"))
                      or _coerce_text(tool_input.get("message")))
        else:
            prompt = _coerce_text(tool_input)

        enforce = read_enforce_process()

        # Check 1: Mega-Agent
        is_mega, found_cmds = detect_mega_agent(prompt)
        if is_mega:
            warning = (
                f"[GUARD-VIOLATION] MEGA-AGENT erkannt! "
                f"Agent-Prompt enthaelt {len(found_cmds)} Pipeline-Commands: {found_cmds}. "
                f"DCSRE-98: Jeder Command braucht eigenen Agent. "
                f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
            )
            print(json.dumps({
                "continue": not enforce,
                "message": warning
            }))
            append_guard_log("MEGA_AGENT", f"{len(found_cmds)} Commands in 1 Agent: {found_cmds}", enforce)
            append_audit_event("MEGA_AGENT", f"{len(found_cmds)} Commands in 1 Agent: {found_cmds}", enforce)
            return

        # Check 2: BDF-Bypass
        if detect_bdf_bypass(prompt):
            warning = (
                "[GUARD-VIOLATION] BDF→Agent() direkt erkannt! "
                "BDF MUSS ueber SDF routen (BDF→SDF→SC/I). "
                f"{'BLOCKIERT.' if enforce else 'WARNING.'}"
            )
            print(json.dumps({
                "continue": not enforce,
                "message": warning
            }))
            append_guard_log("BDF_BYPASS", "BDF→Agent() direkt statt BDF→SDF", enforce)
            append_audit_event("BDF_BYPASS", "BDF→Agent() direkt statt BDF→SDF", enforce)
            return

        # Check 3: Orchestrator via Agent() statt Skill() (INV-PM-2)
        is_orch_agent, orch_cmd = detect_orchestrator_via_agent(prompt, tool_name)
        if is_orch_agent:
            warning = (
                f"[GUARD-VIOLATION] Orchestrator '{orch_cmd}' via Agent() statt Skill() "
                f"(Mega-/Dispatch-Worker, INV-AO-CALLER / INV-PM-2).\n"
                f"  -> STATTDESSEN Handschuh-Wechsel: der Team Lead laedt SELBST "
                f"Skill({orch_cmd if orch_cmd.startswith('_') else '_I_orchestrate'} --stage=<X> --batch=<id>). "
                f"KEIN Agent/Worker fuehrt einen Orchestrator aus — SDF spawnt keinen Dispatch-Worker. "
                f"I_orchestrate spawnt SEINE eigenen Single-Phase-Worker selbst.\n"
                f"  {'BLOCKIERT.' if enforce else 'WARNING (enforceProcess=false).'}"
            )
            print(json.dumps({
                "continue": not enforce,
                "message": warning
            }))
            # BL-439 AK-4: spec-konformes distinktes Event fuer den Delegations-Block.
            append_guard_log("ORCHESTRATOR_DELEGATION_BLOCKED", f"{orch_cmd} via Agent() statt Skill()", enforce)
            append_audit_event("ORCHESTRATOR_DELEGATION_BLOCKED", f"{orch_cmd} via Agent() statt Skill()", enforce)
            return

        # Check 4: Direkte Implementation via Agent statt SC→SDF→I (CS8)
        is_direct_impl, affected_paths = detect_direct_impl_bypass(prompt, tool_name)
        if is_direct_impl:
            warning = (
                f"[GUARD-VIOLATION] DIREKTE IMPLEMENTATION via Agent erkannt! "
                f"Betroffene Pfade: {affected_paths}. "
                f"CS8: Implementation MUSS durch SC→SDF→I Pipeline laufen. "
                f"Team Lead darf KEINE Worker spawnen die direkt editieren. "
                f"Nutze Skill(_SC_orchestrate) oder Skill(_I_orchestrate). "
                f"{'BLOCKIERT.' if enforce else 'WARNING.'}"
            )
            print(json.dumps({
                "continue": not enforce,
                "message": warning
            }))
            append_guard_log("DIRECT_IMPL_BYPASS", f"Agent editiert {affected_paths} direkt statt SC→SDF→I", enforce)
            append_audit_event("DIRECT_IMPL_BYPASS", f"Agent editiert {affected_paths} direkt statt SC→SDF→I", enforce)
            return

        # Check 5: Monolithic-Build-Worker — test+impl-Buendelung in 1 Worker (BL-423 AK-b)
        modus = read_modus()
        is_mono, mono_hint = detect_monolithic_build_worker(prompt, tool_name, modus)
        if is_mono:
            try:
                from _enforce_gate import enforce_active as _ea
                enforce = _ea()
            except Exception:
                enforce = read_enforce_process()
            msg = ("[GUARD-VIOLATION] MONOLITHIC_BUILD_WORKER: test+impl in 1 Worker (modus=" + str(modus)
                   + ") — RED+GREEN-Kollaps.\n  -> FIX: " + mono_hint + ". "
                   + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (enforceProcess=false Opt-out)."))
            append_guard_log("MONOLITHIC_BUILD_WORKER", "test+impl-Buendelung modus=" + str(modus), enforce)
            append_audit_event("MONOLITHIC_BUILD_WORKER", "test+impl-Buendelung modus=" + str(modus), enforce)
            print(json.dumps({"continue": not enforce, "message": msg}))
            return

        # Check 6: M1-Skeleton-Overreach — Skelett-Scope-Ueberschreitung / Lead-inline-Emit (BL-400 AK-5)
        is_m1_over, m1_hint = detect_m1_skeleton_overreach(prompt, tool_name, modus)
        if is_m1_over:
            try:
                from _enforce_gate import enforce_active as _ea
                enforce = _ea()
            except Exception:
                enforce = read_enforce_process()
            msg = ("[GUARD-VIOLATION] M1_SKELETON_OVERREACH: M1-Skelett-Scope ueberschritten (modus=" + str(modus)
                   + ").\n  -> FIX: " + m1_hint + ". "
                   + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (enforceProcess=false Opt-out)."))
            append_guard_log("M1_SKELETON_OVERREACH", "Skelett-Scope-Ueberschreitung modus=" + str(modus), enforce)
            append_audit_event("M1_SKELETON_OVERREACH", "Skelett-Scope-Ueberschreitung modus=" + str(modus), enforce)
            print(json.dumps({"continue": not enforce, "message": msg}))
            return

        # Check 7: Anonymer Wellen-Spawn — Wellen-Marker ohne name/team_name (BL-422 AK-4)
        if tool_name == "Agent":
            is_anon, anon_hint = detect_anonymous_wellen_spawn(prompt, tool_input if isinstance(tool_input, dict) else {})
            if is_anon:
                msg = (
                    f"[GUARD-VIOLATION] ANON_WELLEN_SPAWN: {anon_hint} "
                    f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
                )
                append_guard_log("ANON_WELLEN_SPAWN", "anonymer Wellen-Spawn ohne name/team_name", enforce)
                append_audit_event("ANON_WELLEN_SPAWN", "anonymer Wellen-Spawn ohne name/team_name", enforce)
                print(json.dumps({"continue": not enforce, "message": msg}))
                return

        # Check 8: Phantom-opus — general-opus Subagent-Type existiert nicht (Carrier-Kanon BL-125/BL-461)
        if tool_name == "Agent":
            is_phantom, st = detect_phantom_opus(tool_name, tool_input if isinstance(tool_input, dict) else {})
            if is_phantom:
                msg = ("[GUARD-VIOLATION] PHANTOM_OPUS: subagent_type=" + st + " existiert nicht "
                       "(Carrier-Kanon BL-125/BL-461). -> nutze general-sonnet + model=opus-Override "
                       "ODER general-purpose (erbt Parent-Modell); fuer ceiling-Tier-Berater ohne general-opus "
                       "den verfuegbaren Top-Tier (general-sonnet). "
                       + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNING (enforceProcess=false)."))
                append_guard_log("PHANTOM_OPUS", "subagent_type=" + st + " (Carrier-Kanon: general-opus existiert nicht)", enforce)
                append_audit_event("PHANTOM_OPUS", "subagent_type=" + st + " (Carrier-Kanon: general-opus existiert nicht)", enforce)
                print(json.dumps({"continue": not enforce, "message": msg}))
                return

        # Check 9: Haiku-Floor — general-haiku fuer Reasoning-Spawn (BL-452)
        if tool_name == "Agent":
            is_floor, fr = detect_haiku_floor_violation(tool_name, tool_input if isinstance(tool_input, dict) else {})
            if is_floor:
                msg = ("[GUARD-VIOLATION] HAIKU_FLOOR_VIOLATION: general-haiku fuer Reasoning-Spawn (" + fr + ") "
                       "unter Floor (feedback_haiku_verboten / INV-NO-HAIKU-IN-TDD: Berater+TDD-Kern min sonnet; "
                       "mechanische Executors exempt). -> general-sonnet nutzen. "
                       + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNING (enforceProcess=false)."))
                append_guard_log("HAIKU_FLOOR_VIOLATION", "general-haiku reasoning-spawn: " + fr, enforce)
                append_audit_event("HAIKU_FLOOR_VIOLATION", "general-haiku reasoning-spawn: " + fr, enforce)
                print(json.dumps({"continue": not enforce, "message": msg}))
                return

        # Kein Verstoss
        print(json.dumps({"continue": True}))

    except Exception as e:
        try:
            with open(LOG_FILE, "a", encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] guard_agent_prompt_validator Error: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
