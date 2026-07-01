#!/usr/bin/env python3
"""
session_params_resolver.py — BL-174 AK-2: 3-Stufen-Inheritance Resolver fuer Session-Params.

Reihenfolge (highest priority first):
  1. {BL_FOLDER}/_session_params.md    — per-BL Override
  2. {VAULT}/_session_defaults.md      — Vault-weite Defaults
  3. FRAMEWORK_DEFAULTS (inline)       — Framework-Fallback

INV-PARAM-RESOLVE-1: resolve_param liefert genau einen Wert.
INV-PARAM-RESOLVE-2: BL > Vault > Framework, kein Skip.
INV-PARAM-OWNERSHIP: _owner-Suffix wird mitgeliefert via resolve_with_owner().

Builds on manifest_reader.py (BL-173) fuer File-Lock-Pattern.

CLI:
  py -3 session_params_resolver.py resolve --param=hil --bl-id=BL-174 [--vault-root=PATH]
  py -3 session_params_resolver.py resolve-all --bl-id=BL-174 [--vault-root=PATH]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# UTF-8 Windows-Konsole
# ---------------------------------------------------------------------------

def _configure_utf8_stdout() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# Framework-Defaults (AK-1) — INV-PARAM-RESOLVE-2 lowest priority
# ---------------------------------------------------------------------------

FRAMEWORK_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "hil":                  {"value": "off",     "_owner": "user"},
    "difficulty":           {"value": "normal",  "_owner": "user"},
    "ceiling":              {"value": "opus",    "_owner": "user"},
    "floor":                {"value": "sonnet",  "_owner": "user"},
    "tdd_stages":           {"value": [1, 2, 3, 4, 5, 6, 7], "_owner": "user"},
    "allowed_stages":       {"value": [], "_owner": "user"},  # BL-224 Strang B: IDF-Plan-Whitelist ([] = kein Filter, 486-safe)
    "tdd":                  {"value": False,     "_owner": "user"},
    "slicing":              {"value": False,     "_owner": "user"},
    "dark_factory":         {"value": False,     "_owner": "system"},
    "bdf":                  {"value": False,     "_owner": "user"},
    "prePr":                {"value": "report",  "_owner": "user"},
    "enforceProcess":       {"value": True,      "_owner": "system"},
    "pr_review_mode":       {"value": False,     "_owner": "user"},
    "pr_create_at_end":     {"value": False,     "_owner": "user"},
    "pattern_scan_threshold": {"value": 5,       "_owner": "system"},
    "step_adherence_reminder": {"value": "off",  "_owner": "user"},
    # BL-327 Parallel-Parameter-Dial (OFF -> SINGLE -> WAVE). Defaults false/1 =
    # heutiger serieller Pfad byte-identisch (Null-Risiko-Fallback). N=1 = SINGLE-Breite.
    "parallel_mode":        {"value": False,     "_owner": "user"},
    "nr_parallel_batches":  {"value": 1,         "_owner": "user"},
    # BL-330 Workflow-Dial (3 Modi, User-Design 2026-06-12). Owner-owned wie hil/floor.
    #   false  = alles altmodisch (Teams)            — heutiges Verhalten byte-identisch
    #   normal = gruene (hart-det) Zone als Workflow ; gelb + rot altmodisch
    #   fast   = gruen + gelb als Workflow           ; rot IMMER altmodisch
    # KEIN cognitive/all-Modus: die rote Zone (TDD-GREEN-Klarheit/C3-Modus/modelSync-
    # Wahrheit) ist NIE ueber den Dial schaltbar (Resolver-/resolve_vehicle-Invariante
    # in workflow_zones.py). Default "false". Aliase: true/on->normal, off->false.
    "workflow":             {"value": "false",   "_owner": "user"},
    # BL-373 (2026-06-16): Motor-Produktions-Lock (Gate-D-Schwelle). Der dispatch_implement-Motor
    # ist strukturell deterministisch (workflow_zones: green), aber VERBOTEN vor Gate-D
    # (feedback_motor_erst_nach_stabilisierung). Dieser Flag ist der TEMPORALE Lock: default False
    # (vor Gate-D IMMER off); der Architekt flippt ihn NACH Gate-D auf True. Gelesen vom
    # _SDF_orchestrate OUTER-LOOP Vehikel-Gate (motor_allowed = gate_d_passed AND vehicle==workflow).
    "motor_production_ready": {"value": False,    "_owner": "user"},
    # BL-403 (2026-06-18): IDF-Express-Lane-Dial (default-OFF, opt-in). Muster BL-327
    # (parallel_mode=false) + BL-330 (workflow=false). false = voller IDF-Pfad byte-identisch
    # zum Status quo (kein Express-Skip moeglich, AK-7/AK-8). true = Express-Gate-Evaluation
    # aktiv (6 UND-Bedingungen, AK-1). EINZIGE Stellschraube — kein Bypass-Feld. Gelesen vom
    # _IDF_orchestrate TIER-1-Vorab-Gate (Z607) + TIER-2-Confirm-Gate (Z955) als
    # (args.idf_express_lane ?? session_params_resolver(idf_express_lane) ?? false).
    # ABGRENZUNG behavior_identical: das ist KEIN Session-Dial — es ist ein per-ITEM
    # Caller-Arg/PL-Annotation (args.behavior_identical / pl_annotation.behavior_identical,
    # eine der vc3-Vorab-Bedingungen). Item-spezifisch, nicht session-global -> NICHT hier.
    "idf_express_lane":     {"value": False,    "_owner": "user"},
    # BL-425 (2026-06-20): Merge-Seam-Dials. Muster BL-327 (parallel_mode=false).
    #   merge=True        — Merge-Flow AN per Default (BL-442 AK-3/SOA-2=B Default-Flip
    #                       2026-06-20: war False; trifft ALLE Laeufe -> develop-Auto-Merge
    #                       am BL-Ende generell, auch Nicht-Lane. Bewusst gewollt.)
    #   merge_target      — Ziel-Branch fuer Merges (Default "develop")
    #   merge_timing      — Zeitpunkt des Merges: "per_bl" (pro BL) oder "end_only" (erst am Ende)
    # EINZIGE Stellschrauben — kein Bypass-Feld.
    "merge":                {"value": True,       "_owner": "user"},
    "merge_target":         {"value": "develop",  "_owner": "user"},
    "merge_timing":         {"value": "per_bl",   "_owner": "user"},
    # BL-442 (2026-06-20, W14): lane-Param — markiert die Roadmap-Lane (A|B|C) eines
    # Laufs fuer den Worktree-Parallel-Pfad (INV-WT-DIAL). Default None = kein
    # Lane-Override (Single-Lane/serieller Standard). KEIN A|B|C erzwungen — der
    # Param ist nur gueltig + resolvebar (kein "unbekannt"-Fehler); Lane-Overrides
    # (BL/Vault) reichen den Roh-String durch (_coerce_value-Fall-through).
    "lane":                 {"value": None,       "_owner": "user"},
    # BL-431 (2026-06-20): BL-Parallel-Dial (default-OFF, orthogonal zu parallel_mode).
    # parallel_mode steuert Fanout innerhalb eines BL-Batches (Wellen-Breite).
    # bl_parallel steuert ob mehrere BL-Items parallel (via Worktrees) bearbeitet werden.
    # Beides DEFAULT False — kein Bypass-Feld (force_bl_parallel -> ValueError).
    "bl_parallel":          {"value": False,      "_owner": "user"},
    # BL-365 (2026-06-21): N=1 Fast-Path-Dial (default-OFF, opt-in). Muster BL-327/BL-403.
    # false = voller IDF-Pfad byte-identisch zum Status quo (kein IDF-Bypass, AK-5 Regression).
    # true  = N=1 Fast-Path aktiv: bei actionable_count==1 wird Skill(_IDF_orchestrate)
    #         NICHT aufgerufen; Phase 1.6 befuellt DF_BATCH_STATE + BERATER_OUTPUTS_IDF-Namespace
    #         inline (Trivial-Planung); INV-MODUS-1 gewahrt: nur batch_mode_hints (ADVISORY),
    #         NIE batch_modes/modus (C3 Phase 1.1 bleibt einziger modus-Writer).
    # EINZIGE Stellschraube — kein Bypass-Feld.
    "n1_fastpath_bl365":    {"value": False,      "_owner": "user"},
    # BL-331 (2026-06-21): BDF Post-Item-Learning-Dial. Steuert welche Lern-Kanaele
    # nach einem BDF-Item aktiv sind. Sub-Keys: pt ("on"|"off"), model ("on"|"off").
    # Default: beide AN (autonomes Lernen in big_dark_factory+hil=off).
    # EINZIGE Stellschraube — Bypass-Felder (force_learning, skip_harvest,
    # learning_override, pt_override, model_override) -> ValueError (INV-LEARN-PARAM).
    "bdf_post_item_learning": {"value": {"pt": "on", "model": "on"}, "_owner": "user"},
}


# ---------------------------------------------------------------------------
# BL-436 D1: Stabile API fuer bl_parallel-Default-Abfrage
# ---------------------------------------------------------------------------

def get_bl_parallel_framework_default() -> tuple:
    """Gibt den Framework-Default fuer bl_parallel zurueck: (value, owner).

    BL-436: Stabile, versionierte API — kein direkter FRAMEWORK_DEFAULTS-Zugriff
    von aussen (Encapsulation). Andere Komponenten nutzen diese Funktion statt
    FRAMEWORK_DEFAULTS["bl_parallel"] direkt abzufragen.

    Returns:
        Tuple (False, "user") — bl_parallel ist default-OFF, owner=user.
    """
    entry = FRAMEWORK_DEFAULTS["bl_parallel"]
    return (entry["value"], entry["_owner"])


# Case-insensitive Param-Lookup (Fix 2026-06-01): /_param schreibt "**HiL:**" (CamelCase),
# der Framework-Key ist "hil" (lowercase). Ohne CI-Map wird hil NIE aus der Datei gelesen
# und bleibt faelschlich beim Default "off" — egal was der User via /_param setzt.
# (enforceProcess/prePr matchen schon, weil Datei + Key dieselbe Schreibung haben.)
_CI_KEYMAP = {k.lower(): k for k in FRAMEWORK_DEFAULTS}

# Model hierarchy for ceiling >= floor validation
_MODEL_RANK = {"haiku": 1, "sonnet": 2, "opus": 3}

# Thread-local lock for concurrent reads
_read_lock = threading.RLock()


# ---------------------------------------------------------------------------
# Validation (AK-3)
# ---------------------------------------------------------------------------

_VALID_VALUES: Dict[str, Any] = {
    "hil":        {"off", "cycle", "phase", "manual"},
    "difficulty": {"easy", "normal", "hard"},
    "ceiling":    {"haiku", "sonnet", "opus"},
    "floor":      {"haiku", "sonnet", "opus"},
    "tdd":        {True, False, "true", "false"},
    "slicing":    {True, False, "true", "false"},
    "bdf":        {True, False, "true", "false"},
    "dark_factory": {True, False, "true", "false"},
    "enforceProcess": {True, False, "true", "false"},
    "prePr":      {"report", "execute"},
    "pr_review_mode":  {True, False, "true", "false"},
    "pr_create_at_end": {True, False, "true", "false"},
    "step_adherence_reminder": {"off", "on"},
    "parallel_mode": {True, False, "true", "false"},  # BL-327: bool-like Master-Schalter
    # BL-330: 3-Modi-Enum OHNE cognitive/all (rot strukturell nie schaltbar). Aliase
    # (true/on/off) werden VOR der Validierung in _coerce_value auf den Enum gemappt.
    "workflow": {"false", "normal", "fast"},
    "motor_production_ready": {True, False, "true", "false"},  # BL-373 Gate-D Motor-Lock
    "idf_express_lane": {True, False, "true", "false"},  # BL-403: bool-like opt-in Dial (default false)
    "merge":            {True, False, "true", "false"},  # BL-425: bool-like Master-Schalter (default false)
    "merge_timing":     {"per_bl", "end_only"},          # BL-425: Merge-Zeitpunkt-Enum
    "bl_parallel":      {True, False, "true", "false"},  # BL-431: bool-like BL-Parallel-Dial (default false)
    "n1_fastpath_bl365": {True, False, "true", "false"}, # BL-365: bool-like N=1 Fast-Path-Dial (default false)
    # BL-331: bdf_post_item_learning ist dict — Validierung erfolgt in _coerce_value (Sub-Key-Check).
    # _VALID_VALUES-Eintrag absichtlich NICHT gesetzt (dict kann nicht in set membership
    # geprueft werden); validate_param faellt auf _coerce_value-Ergebnis durch.
}


# BL-327 AK-3: Verbotene Bypass-Felder (analog INV-MODUS-5). Kein zweiter
# Schreibweg am Dial vorbei — der Dial (parallel_mode/nr_parallel_batches) bleibt
# die EINZIGE Stellschraube fuer Parallelitaet. Taucht eines dieser Felder in
# einer Params-Quelle auf, blockt der Resolver mit ValueError.
_PARALLEL_BYPASS_FIELDS = frozenset(
    {"force_parallel", "wave_override", "parallel_override", "nr_parallel_override",
     "force_bl_parallel"}  # BL-431 AK-4: kein zweiter Schreibweg am bl_parallel-Dial
)

# BL-331 AK-4: Verbotene Bypass-Sub-Keys fuer bdf_post_item_learning (INV-LEARN-PARAM).
# Kein zweiter Schreibweg am Lern-Kanal vorbei — Sub-Keys sind AUSSCHLIESSLICH {pt, model}.
_LEARNING_BYPASS_SUBKEYS = frozenset(
    {"force_learning", "skip_harvest", "learning_override", "pt_override", "model_override"}
)
_LEARNING_VALID_SUBKEYS = frozenset({"pt", "model"})
_LEARNING_VALID_SUBVALUES = frozenset({"on", "off"})

# BL-330 AK-2: Verbotene Bypass-Felder fuer den Zonen-Dial (analog INV-MODUS-5 /
# BL-327). Der Dial (workflow_zone_tier + workflow_zone_burnin_passed) bleibt die
# EINZIGE Stellschraube — es gibt KEINEN zweiten Schreibweg, der den Burn-in-Gate
# oder die Tier-Whitelist umgeht. Diese Felder kodifizieren den explizit abgelehnten
# Ultracode/Auto-Workflow-Reflex (force_workflow/ultracode_force): taucht eines auf,
# blockt der Resolver mit ValueError.
_WORKFLOW_ZONE_BYPASS_FIELDS = frozenset(
    {"force_workflow", "ultracode_force", "workflow_zone_override", "motor_zone_force"}
)


def _coerce_value(param_name: str, raw: Any) -> Any:
    """Coerce string representations to native Python types."""
    if param_name == "bdf_post_item_learning":  # BL-331: dict Sub-Key-Validierung
        if not isinstance(raw, dict):
            raise ValueError(
                f"bdf_post_item_learning muss ein dict sein, got {type(raw).__name__!r}. "
                f"Erlaubte Sub-Keys: {sorted(_LEARNING_VALID_SUBKEYS)}."
            )
        # Bypass-Sub-Key-Check (INV-LEARN-PARAM)
        for key in raw:
            if key in _LEARNING_BYPASS_SUBKEYS:
                raise ValueError(
                    f"Verbotener Bypass-Sub-Key {key!r} in bdf_post_item_learning "
                    f"(INV-LEARN-PARAM, BL-331 AK-4). Erlaubte Sub-Keys: "
                    f"{sorted(_LEARNING_VALID_SUBKEYS)}."
                )
            if key not in _LEARNING_VALID_SUBKEYS:
                raise ValueError(
                    f"Unbekannter Sub-Key {key!r} in bdf_post_item_learning. "
                    f"Erlaubte Sub-Keys: {sorted(_LEARNING_VALID_SUBKEYS)}."
                )
            if raw[key] not in _LEARNING_VALID_SUBVALUES:
                raise ValueError(
                    f"Ungültiger Sub-Wert {raw[key]!r} fuer Sub-Key {key!r} in "
                    f"bdf_post_item_learning. Erlaubte Werte: {sorted(_LEARNING_VALID_SUBVALUES)}."
                )
        return raw
    if param_name == "parallel_mode":  # BL-327: bool, aber STRIKT (kein truthy-Surrogat)
        # Nur echte bool-likes coercen; jeder andere String bleibt roh, damit
        # validate_param() ihn gegen _VALID_VALUES als invalide ablehnt (AK-3.4).
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            low = raw.lower()
            if low == "true":
                return True
            if low == "false":
                return False
            return raw  # z.B. "maybe" -> bleibt String -> _VALID_VALUES-Reject
        return bool(raw)
    if param_name == "workflow":  # BL-330: 3-Modi-Enum mit freundlichen Aliasen
        # bool True/False (z.B. /_param workflow=true) -> normal/false.
        if isinstance(raw, bool):
            return "normal" if raw else "false"
        if isinstance(raw, str):
            low = raw.strip().lower()
            if low in ("true", "on"):
                return "normal"
            if low == "off":
                return "false"
            return low  # false/normal/fast (oder invalid -> _VALID_VALUES-Reject)
        return raw
    if param_name in ("tdd", "slicing", "bdf", "dark_factory",
                      "enforceProcess", "pr_review_mode", "pr_create_at_end",
                      "motor_production_ready",  # BL-373: bool Gate-D Motor-Lock
                      "idf_express_lane",        # BL-403: bool opt-in Express-Dial (default false)
                      "merge",                   # BL-425: bool Merge-Master-Schalter (default false)
                      "bl_parallel",             # BL-431: bool BL-Parallel-Dial (default false)
                      "n1_fastpath_bl365"):      # BL-365: bool N=1 Fast-Path-Dial (default false)
        if isinstance(raw, str):
            if raw.lower() == "true":
                return True
            if raw.lower() == "false":
                return False
        return bool(raw)
    if param_name in ("tdd_stages", "allowed_stages"):  # BL-224: allowed_stages analog tdd_stages
        if isinstance(raw, str):
            # Parse "[1,3,5]" or "1,3,5"
            nums = re.findall(r"\d+", raw)
            return [int(n) for n in nums]
        return raw
    if param_name in ("pattern_scan_threshold", "nr_parallel_batches"):  # BL-327: int (analog threshold)
        return int(raw)
    return raw


def validate_param(param_name: str, value: Any) -> Any:
    """Validate and coerce a param value. Raises ValueError on invalid."""
    if param_name not in FRAMEWORK_DEFAULTS:
        # Unknown param — return as-is with warning
        return value

    coerced = _coerce_value(param_name, value)

    if param_name in _VALID_VALUES:
        # For bool-like params, check after coercion
        valid_set = _VALID_VALUES[param_name]
        if coerced not in valid_set:
            raise ValueError(
                f"Invalid value '{value}' for param '{param_name}'. "
                f"Valid: {sorted(str(v) for v in valid_set)}"
            )

    if param_name in ("tdd_stages", "allowed_stages"):  # BL-224: gleiche Int-1-7-Listen-Validierung
        if not isinstance(coerced, list):
            raise ValueError(f"{param_name} must be a list, got {type(coerced)}")
        for stage in coerced:
            if not isinstance(stage, int) or stage < 1 or stage > 7:
                raise ValueError(f"{param_name} values must be integers 1-7, got {stage}")

    if param_name == "nr_parallel_batches":  # BL-327 AK-3.1: int >= 1 (analog tdd_stages-Range-Check)
        if not isinstance(coerced, int) or coerced < 1:
            raise ValueError(
                f"nr_parallel_batches must be an integer >= 1, got {coerced!r}"
            )

    return coerced


# ---------------------------------------------------------------------------
# BL-327 AK-3: Parallel-Dial Bypass-Guard (analog INV-MODUS-5)
# ---------------------------------------------------------------------------

def validate_no_parallel_bypass(param_keys: Any) -> None:
    """BL-327 AK-3: blockt verbotene Bypass-Felder (kein zweiter Schreibweg am
    Dial vorbei). Raised ValueError, sobald eines der `_PARALLEL_BYPASS_FIELDS`
    in den uebergebenen Param-Keys auftaucht (z.B. aus einer Params-Quelle).

    Der Dial (parallel_mode/nr_parallel_batches) bleibt die EINZIGE Stellschraube
    fuer Parallelitaet. Analog zur INV-MODUS-5-Pre-Write-Block-Doktrin.
    """
    keys = set(param_keys)
    offending = sorted(keys & _PARALLEL_BYPASS_FIELDS)
    if offending:
        raise ValueError(
            f"Parallel-Dial-Bypass blockiert (BL-327 AK-3, analog INV-MODUS-5): "
            f"verbotene Felder {offending} sind kein Schreibweg am Dial vorbei. "
            f"Nutze ausschliesslich parallel_mode + nr_parallel_batches."
        )


def validate_no_workflow_zone_bypass(param_keys: Any) -> None:
    """BL-330 AK-2: blockt verbotene Zonen-Dial-Bypass-Felder (analog INV-MODUS-5 /
    BL-327). Raised ValueError, sobald eines der `_WORKFLOW_ZONE_BYPASS_FIELDS` in
    den uebergebenen Param-Keys auftaucht.

    Der Zonen-Dial (workflow_zone_tier + workflow_zone_burnin_passed) bleibt die
    EINZIGE Stellschraube fuer die Workflow-Zonen-Aktivierung — kein Feld umgeht
    das Burn-in-Gate. force_workflow/ultracode_force kodifizieren den explizit
    abgelehnten Ultracode/Auto-Workflow-Reflex und sind strukturell verboten.
    """
    keys = set(param_keys)
    offending = sorted(keys & _WORKFLOW_ZONE_BYPASS_FIELDS)
    if offending:
        raise ValueError(
            f"Zonen-Dial-Bypass blockiert (BL-330 AK-2, analog INV-MODUS-5): "
            f"verbotene Felder {offending} sind kein Schreibweg am Dial vorbei "
            f"(Ultracode-Auto-Reflex bleibt abgelehnt). Nutze ausschliesslich "
            f"workflow_zone_tier + workflow_zone_burnin_passed."
        )


# ---------------------------------------------------------------------------
# File Parsing
# ---------------------------------------------------------------------------

def _parse_session_params_file(path: Path) -> Dict[str, Any]:
    """
    Parse a _session_params.md file into a dict of param -> value.
    Supports two formats:
      - **param:** value _owner: owner
      - YAML-table: | param | value | owner |
    Returns dict of {param_name: coerced_value}.
    """
    if not path.exists():
        return {}

    with _read_lock:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {}

    # BL-327 AK-3: Bypass-Guard — eine Params-Quelle darf KEINEN zweiten
    # Schreibweg am Dial vorbei enthalten. Scan der rohen Datei-Keys (die
    # Bypass-Felder sind absichtlich NICHT in FRAMEWORK_DEFAULTS, daher wuerden
    # die regulaeren Parser-Regexes sie ueberspringen — wir muessen sie roh sehen).
    file_keys = set(
        m.group(1).strip().lower()
        for m in re.finditer(r"^\*\*([a-zA-Z_]+):\*\*", text, re.MULTILINE)
    )
    file_keys |= set(
        m.group(1).strip().lower()
        for m in re.finditer(r"^\|\s*([a-zA-Z_]+)\s*\|", text, re.MULTILINE)
    )
    validate_no_parallel_bypass(file_keys)        # raises ValueError on bypass field
    validate_no_workflow_zone_bypass(file_keys)   # BL-330: same Pre-Write-Block-Doktrin

    result: Dict[str, Any] = {}

    # Format 1: **param:** value [_owner: owner]
    for match in re.finditer(
        r"^\*\*([a-zA-Z_]+):\*\*\s+([^\n_]+?)(?:\s+_owner:\s+\w+)?\s*$",
        text,
        re.MULTILINE,
    ):
        param = _CI_KEYMAP.get(match.group(1).strip().lower())
        raw_val = match.group(2).strip()
        if param is not None:
            try:
                result[param] = _coerce_value(param, raw_val)
            except (ValueError, TypeError):
                result[param] = raw_val

    # Format 2: Markdown table row | param | value | owner |
    for match in re.finditer(
        r"^\|\s*([a-zA-Z_]+)\s*\|\s*([^|]+?)\s*\|\s*(?:\w+)?\s*\|",
        text,
        re.MULTILINE,
    ):
        param_raw = match.group(1).strip()
        raw_val = match.group(2).strip()
        # Skip header rows
        if param_raw in ("Parameter", "---", "param"):
            continue
        param = _CI_KEYMAP.get(param_raw.lower())
        if param is not None:
            try:
                result[param] = _coerce_value(param, raw_val)
            except (ValueError, TypeError):
                result[param] = raw_val

    return result


# ---------------------------------------------------------------------------
# Path Resolution
# ---------------------------------------------------------------------------

def _find_vault_root(vault_root: Optional[str] = None) -> Optional[Path]:
    """Resolve vault root. Falls back to env var or heuristic search."""
    if vault_root:
        p = Path(vault_root)
        return p if p.exists() else None

    env_vault = None
    try:
        import os
        env_vault = os.environ.get("OMNI_VAULT_ROOT")
    except Exception:
        pass

    if env_vault:
        p = Path(env_vault)
        if p.exists():
            return p

    # Maschinen-Portabilitaet (2026-06-19, Maschine-B): den kanonischen Resolver
    # nutzen (resolve_vault_root.py -> vault-routing.json / CLAUDE_VAULT_ROOT,
    # ARCH-N8 Single-Source-of-Truth) STATT nur hardcodierter Administrator-Pfade.
    # Auf einem frischen Rechner (anderes Vault-Layout) fanden die Hardcodes den
    # Vault nie -> session_params fielen faelschlich auf Framework-Defaults
    # (enforceProcess=True self-block, tdd=False). Lazy-Import + breiter Except,
    # damit jeder Fehler weiterhin auf die Hardcode-Heuristik unten faellt.
    try:
        import sys as _sys
        _scripts_dir = str(Path(__file__).resolve().parent)
        if _scripts_dir not in _sys.path:
            _sys.path.insert(0, _scripts_dir)
        from resolve_vault_root import resolve_vault_root as _resolve_canonical
        cand = _resolve_canonical()
        if cand is not None and (cand / "_backlog_index.md").exists():
            return cand
    except Exception:
        pass

    # Heuristic: look for _backlog_index.md in common locations (Backward-Compat
    # Fallback, falls der kanonische Resolver nichts liefert).
    candidates = [
        Path("C:/Users/Administrator/Documents/OmniCommand"),
        Path.home() / "Documents/OmniCommand",
    ]
    for c in candidates:
        if (c / "_backlog_index.md").exists():
            return c

    return None


_TICKET_ID_RE = re.compile(r"([A-Za-z]+-\d+)")


def _extract_ticket_id(s: Optional[str]) -> Optional[str]:
    """BL-234 AK-2: extrahiert die Ticket-ID ({PREFIX}-{N}) aus einem bl_id ODER einem
    vollen Feature-Namen (z.B. 'DCSRE-1944_QDVS_TP_SA_Anlegen' -> 'DCSRE-1944').
    So koennen Caller (Orchestrator) den name direkt durchreichen. Kein Match -> unveraendert.
    """
    if not s:
        return s
    m = _TICKET_ID_RE.search(s)
    return m.group(1) if m else s


def _find_bl_folder(
    bl_id: str,
    vault_root: Optional[Path],
    backlog_subfolder: Optional[str] = None,
) -> Optional[Path]:
    """Find the BL folder for a given bl_id (e.g. 'BL-174') oder Feature-Namen.

    BL-234 AK-3: respektiert den vault-routing.json `backlog.subfolder`
    (z.B. 'DCSRE/Backlog' fuer den DCSRE-Vault), nicht nur hardcoded 'Backlog'.
    Faellt additiv auf 'Backlog' zurueck (OmniCommand-Layout unveraendert = 486-safe).
    BL-234 AK-2: akzeptiert Name ODER bl_id (Ticket-Extraktion).
    """
    if vault_root is None:
        return None

    # BL-234 AK-2: Name -> Ticket-ID normalisieren (z.B. 'DCSRE-1944_QDVS...' -> 'DCSRE-1944').
    bl_id = _extract_ticket_id(bl_id)

    # BL-234 AK-3: Subfolder via vault-routing.json (CWD-basiert), Fallback "Backlog".
    # Lazy-Import gegen Modul-Lade-Zyklen; jeder Fehler -> Hardcode-Fallback.
    if backlog_subfolder is None:
        try:
            from resolve_bl_path import _resolve_backlog_subfolder
            backlog_subfolder = _resolve_backlog_subfolder()
        except Exception:
            backlog_subfolder = "Backlog"

    # Kandidaten: konfigurierter Subfolder zuerst, dann hardcoded "Backlog" (Backward-Compat).
    candidate_dirs = [vault_root / backlog_subfolder]
    if backlog_subfolder != "Backlog":
        candidate_dirs.append(vault_root / "Backlog")

    # Match folder starting with bl_id (case-insensitive) oder exaktes "BL-NNN".
    prefix = bl_id.upper() + "-"
    pattern_exact = bl_id.upper()

    for backlog_dir in candidate_dirs:
        if not backlog_dir.exists():
            continue
        try:
            for entry in backlog_dir.iterdir():
                if entry.is_dir():
                    name_upper = entry.name.upper()
                    if name_upper == pattern_exact or name_upper.startswith(prefix):
                        return entry
        except OSError:
            continue

    return None


# ---------------------------------------------------------------------------
# Core Resolution Logic (INV-PARAM-RESOLVE-1/2)
# ---------------------------------------------------------------------------

def _load_layers(
    bl_id: Optional[str],
    vault_root: Optional[str],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load BL-layer and Vault-layer dicts.
    Returns (bl_layer, vault_layer).
    """
    vr = _find_vault_root(vault_root)

    bl_layer: Dict[str, Any] = {}
    vault_layer: Dict[str, Any] = {}

    # Vault-Default layer: {VAULT}/_session_defaults.md
    if vr is not None:
        vault_defaults_path = vr / "_session_defaults.md"
        if not vault_defaults_path.exists():
            # Backward-compat fallback: _session_params.md
            vault_defaults_path = vr / "_session_params.md"
        vault_layer = _parse_session_params_file(vault_defaults_path)

    # BL-Override layer
    if bl_id is not None and vr is not None:
        bl_folder = _find_bl_folder(bl_id, vr)
        if bl_folder is not None:
            bl_params_path = bl_folder / "_session_params.md"
            bl_layer = _parse_session_params_file(bl_params_path)

    return bl_layer, vault_layer


def _resolve_one(
    param_name: str,
    bl_layer: Dict[str, Any],
    vault_layer: Dict[str, Any],
) -> Any:
    """Single-param 3-Stufen-Lookup gegen bereits geladene Layer.
    BL > Vault > Framework. None fuer unbekannte Params."""
    if param_name in bl_layer:
        return bl_layer[param_name]
    if param_name in vault_layer:
        return vault_layer[param_name]
    if param_name in FRAMEWORK_DEFAULTS:
        return FRAMEWORK_DEFAULTS[param_name]["value"]
    return None


def _apply_parallel_dial_clamp(
    param_name: str,
    value: Any,
    bl_layer: Dict[str, Any],
    vault_layer: Dict[str, Any],
) -> Any:
    """BL-327 AK-3.2 Kombinations-Regel: parallel_mode=false ⇒ nr_parallel_batches
    wird auf 1 ERZWUNGEN (OFF hat per Definition fanout 1). Clamp, KEIN Error.
    Bei parallel_mode=true bleibt N wie gesetzt.
    """
    if param_name != "nr_parallel_batches":
        return value
    parallel_mode = _resolve_one("parallel_mode", bl_layer, vault_layer)
    if parallel_mode is False or parallel_mode == "false":
        return 1
    return value


def resolve_param(
    param_name: str,
    bl_id: Optional[str] = None,
    vault_root: Optional[str] = None,
) -> Any:
    """
    Resolve a single session param via 3-Stufen-Inheritance.

    Priority: BL-Override > Vault-Default > Framework-Default
    Returns the resolved value (not the _owner).
    Returns None for unknown params (not in FRAMEWORK_DEFAULTS).

    INV-PARAM-RESOLVE-1: exactly one value returned.
    INV-PARAM-RESOLVE-2: BL > Vault > Framework, no skip.
    BL-327 AK-3.2: parallel_mode=false ⇒ nr_parallel_batches geklemmt auf 1.
    """
    bl_layer, vault_layer = _load_layers(bl_id, vault_root)
    value = _resolve_one(param_name, bl_layer, vault_layer)
    value = _apply_parallel_dial_clamp(param_name, value, bl_layer, vault_layer)
    return value


def resolve_with_owner(
    param_name: str,
    bl_id: Optional[str] = None,
    vault_root: Optional[str] = None,
) -> Tuple[Any, str]:
    """
    Like resolve_param but also returns the _owner.
    Returns (value, owner_str).
    """
    value = resolve_param(param_name, bl_id=bl_id, vault_root=vault_root)
    owner = FRAMEWORK_DEFAULTS.get(param_name, {}).get("_owner", "system")
    return value, owner


def resolve_all_params(
    bl_id: Optional[str] = None,
    vault_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve all known params via 3-Stufen-Inheritance.
    Returns {param_name: resolved_value} for all FRAMEWORK_DEFAULTS keys.
    """
    bl_layer, vault_layer = _load_layers(bl_id, vault_root)

    result: Dict[str, Any] = {}
    for param_name, fw_entry in FRAMEWORK_DEFAULTS.items():
        value = _resolve_one(param_name, bl_layer, vault_layer)
        # BL-327 AK-3.2: false=>N=1-Clamp gilt auch im Bulk-Pfad.
        value = _apply_parallel_dial_clamp(param_name, value, bl_layer, vault_layer)
        result[param_name] = value

    return result


# ---------------------------------------------------------------------------
# BL-343 PL-343-2: Guard-Fallback-Helper (env-present-Pfad byte-gleich, env-absent
# -> Resolver-Fallback statt BLOCK-Default). Schliesst die "korrekter-Block-stallt-
# Prozess"-Fehlerklasse (Maschine-nicht-Context): der Guard wird vom Harness OHNE
# gesetztes OMNI_SESSION_PARAMS gerufen -> fiel bisher auf seinen BLOCK-Default,
# obwohl der self-resolvbare Session-State enforceProcess:false sagt.
#
# Geschwister-Guards (idf_sdf/redeploy_health/a_idf/geist9b/param_writer) teilen die
# read_enforce-Klasse — Sibling-Wiring ist Folge-Scope; hier verdrahtet nur
# guard_stage_seam_handoff.py diese Helper.
# ---------------------------------------------------------------------------

# Byte-gleich zur env-present-Logik der Guards (guard_stage_seam_handoff.read_enforce/
# read_hil): NUR der Match-Ausdruck zaehlt. Beim env-present-Zweig wird genau diese
# Logik gegen die Datei laufen gelassen -> Bestands-Verhalten der 4
# test_guard_stage_seam_handoff.py-Tests intakt.
_ENFORCE_FALSE_RE = re.compile(r"enforceProcess\s*:?\*?\*?\s*false", re.IGNORECASE)
_HIL_RE = re.compile(r"(GLOBAL_HIL|HiL|hil)\s*:?\s*\**\s*(\w+)", re.IGNORECASE)


def _read_enforce_from_env_file(sp: str) -> bool:
    """env-present-Pfad (byte-gleich zum Guard-Bestand): enforceProcess:false -> False,
    sonst BLOCK-Default True. Lese-/Match-Fehler -> True (fail-safe)."""
    try:
        txt = Path(sp).read_text(encoding="utf-8", errors="replace")
        if _ENFORCE_FALSE_RE.search(txt):
            return False
    except Exception:
        pass
    return True


def _read_hil_from_env_file(sp: str) -> str:
    """env-present-Pfad (byte-gleich zum Guard-Bestand): erster (GLOBAL_HIL|HiL|hil)-Wert
    lowercased, sonst Default 'off'. Lese-/Match-Fehler -> 'off' (fail-safe)."""
    try:
        txt = Path(sp).read_text(encoding="utf-8", errors="replace")
        m = _HIL_RE.search(txt)
        if m:
            return m.group(2).lower()
    except Exception:
        pass
    return "off"


def read_enforce_with_fallback(env_path: Optional[str] = None) -> bool:
    """enforceProcess fuer Guards mit env-absent-Fallback (BL-343 PL-343-2).

    - env_path gesetzt + existent (OMNI_SESSION_PARAMS) -> heutige env-Logik (byte-gleich
      zum Guard-Bestand): enforceProcess:false -> False, sonst BLOCK-Default True.
    - SONST (env-absent) -> resolve_param('enforceProcess') (self-resolving, OHNE env;
      honoriert OMNI_VAULT_ROOT). Resolver-Fehler/Exception -> fail-safe BLOCK-Default True.

    KEIN Vault-IO erzwingen: der Resolver liest nur, was self-resolvbar ist; fehlt der
    State, faellt resolve_param auf den Framework-Default (enforceProcess=True) zurueck.
    """
    if env_path and Path(env_path).exists():
        return _read_enforce_from_env_file(env_path)
    try:
        val = resolve_param("enforceProcess")
        # resolve_param liefert bereits den coerced bool (FRAMEWORK_DEFAULTS/Datei).
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() != "false"
        # None (unbekannt) o.ae. -> fail-safe BLOCK.
        return True
    except Exception:
        return True


def read_hil_with_fallback(env_path: Optional[str] = None) -> str:
    """HiL-Wert fuer Guards mit env-absent-Fallback (BL-343 PL-343-2).

    - env_path gesetzt + existent -> heutige env-Logik (byte-gleich): erster Wert lowercased,
      sonst Default 'off'.
    - SONST -> resolve_param('hil') (self-resolving, OHNE env). Resolver-Fehler -> 'off'.
    """
    if env_path and Path(env_path).exists():
        return _read_hil_from_env_file(env_path)
    try:
        val = resolve_param("hil")
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
        return "off"
    except Exception:
        return "off"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="BL-174: Session-Params 3-Stufen-Inheritance Resolver"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # resolve
    p_resolve = sub.add_parser("resolve", help="Resolve a single param")
    p_resolve.add_argument("--param", required=True, help="Param name (e.g. hil)")
    p_resolve.add_argument("--bl-id", default=None, help="BL ID (e.g. BL-174)")
    p_resolve.add_argument("--vault-root", default=None, help="Vault root path")
    p_resolve.add_argument("--json", action="store_true", help="Output as JSON")

    # resolve-all
    p_all = sub.add_parser("resolve-all", help="Resolve all params")
    p_all.add_argument("--bl-id", default=None, help="BL ID (e.g. BL-174)")
    p_all.add_argument("--vault-root", default=None, help="Vault root path")
    p_all.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def main() -> None:
    _configure_utf8_stdout()
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "resolve":
        value = resolve_param(
            param_name=args.param,
            bl_id=args.bl_id,
            vault_root=args.vault_root,
        )
        if getattr(args, "json", False):
            print(json.dumps({"param": args.param, "value": value}))
        else:
            print(f"{args.param}={value!r}")

    elif args.command == "resolve-all":
        all_params = resolve_all_params(
            bl_id=args.bl_id,
            vault_root=args.vault_root,
        )
        if getattr(args, "json", False):
            print(json.dumps(all_params, default=str))
        else:
            for k, v in sorted(all_params.items()):
                print(f"{k}={v!r}")


if __name__ == "__main__":
    main()
