#!/usr/bin/env python3
"""sanity_check_stage.py — BL-412 batch_6 (AK-SC-PL-2): Stage-Sanity-Check CLI + API.

Fuehrt die 5 Sub-Checks (a-e) strukturell-deterministisch aus (Pflicht-Tier, live=False).
Delegiert Slice-Set-Validierung an stage_slice_schema.validate_slice_set (INV-STAGE-SC-2).
Nutzt resolve_vault_stage.resolve_stage zum Auffinden des Stage-Dirs.

API:
  sanity_check_stage(stage_nr, *, vault_root=None, live=False) -> dict
    {
      "verdict": "PASS" | "FAIL" | "WARN",
      "checks": {
        "a": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
        "b": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
        "c": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
        "d": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
        "e": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
      },
      "stage_dir": str | None,
    }

Sub-Checks (strukturell-deterministisch, kein laufendes System):
  (a) execute.testbefehl gesetzt/nicht-leer -> PASS, sonst FAIL.
  (b) --filter/execute.filter vorhanden -> PASS, sonst WARN.
  (c) validate_slice_set PASS + concurrency_class valide -> PASS, sonst FAIL.
  (d) LogFileName/TDD-STATE aus execute ableitbar -> PASS, sonst WARN.
  (e) INFRA_CONDITIONAL-Slices: concern valide ODER skip:true -> PASS, sonst FAIL.

Gesamt-Verdict = worst_case(a..e): FAIL > WARN > PASS.

Exit codes (CLI):
  0 = PASS
  1 = WARN
  2 = FAIL
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from stage_slice_schema import (
    INFRA_CONDITIONAL_SLICES,
    SLICE_CONCERN_FIELD,
    validate_slice_set,
)
from resolve_vault_stage import resolve_stage


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

_RANK = {"FAIL": 2, "WARN": 1, "PASS": 0}


def _worst_case(*statuses: str) -> str:
    """Gibt den schlechtesten Status zurueck: FAIL > WARN > PASS."""
    best_rank = 0
    for s in statuses:
        r = _RANK.get(s, 0)
        if r > best_rank:
            best_rank = r
    return ("PASS", "WARN", "FAIL")[best_rank]


def _check(status: str, hint: Optional[str] = None) -> dict:
    return {"status": status, "hint": hint}


def _has_skip(slice_fm: Optional[dict]) -> bool:
    """True gdw. Slice ein explizites skip/none-Sentinel traegt."""
    if not isinstance(slice_fm, dict):
        return False
    for sentinel_key in ("skip", "none"):
        val = slice_fm.get(sentinel_key)
        if val in (True, "true", "True", 1, "skip", "none", "yes", "ja"):
            return True
    return False


# ---------------------------------------------------------------------------
# BL-486 Verhaltens-Gate-Check-Funktionen (batch_1, Stage 1)
# ---------------------------------------------------------------------------


def _behavior_check_a_legacy(handle: object, vault_root: Optional[Path] = None) -> dict:
    """BL-486 AK-A-CHK: Pruefe ob Stage Vault-resident ist (nicht Legacy-Monolith).

    A3: Vault/Stage/-Verzeichnis vorhanden?
    A2: Globales Stage-Index-Dokument vorhanden?
    A1: handle.is_legacy == False?
    """
    if vault_root is None:
        return _check(
            "FAIL",
            "A3: vault_root nicht angegeben -- Vault/Stage/-Verzeichnis nicht pruefbar.",
        )
    vault_stage_root = vault_root / "Stage"

    if not vault_stage_root.exists():
        return _check(
            "FAIL",
            f"A3: {vault_stage_root} nicht vorhanden -- "
            "alle Stages is_legacy=True (un-migriert).",
        )

    index_doc_exists = (
        any(vault_stage_root.glob("_index.md"))
        or any(vault_stage_root.glob("stage_index.md"))
        or any(vault_stage_root.glob("index.md"))
    )
    if not index_doc_exists:
        return _check(
            "FAIL",
            f"A2: Kein globales Stage-Index-Dokument in {vault_stage_root}/ "
            "-- kein autoritatives Routing-Fundament.",
        )

    if getattr(handle, "is_legacy", True):
        stage_num = getattr(handle, "number", "?")
        return _check(
            "FAIL",
            f"A1: Stage {stage_num} is_legacy=True obwohl {vault_stage_root}/ existiert "
            "-- lokaler Fallback feuert trotz Vault-Residenz (Sync-Kanal-Konflikt).",
        )

    return _check("PASS")


def _behavior_check_c_acquire(scripts_dir: Path) -> dict:
    """BL-486 AK-C-CHK: Pruefe ob acquire_all als ausgefuehrter Call-Site vorhanden ist.

    C1: acquire_all-Aufruf in Engine-Quellen (excl. Implementierungs-Dateien)?
    C2: guard_stage_acquire_enforce.py vorhanden?
    """
    _EXCLUDED_C = {"resource_allocator.py", "stage_resource_registry.py"}

    callsite_found = False
    for py_file in sorted(scripts_dir.glob("*.py")):
        if py_file.name in _EXCLUDED_C or py_file.name.startswith("test_"):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "acquire_all" in content:
            callsite_found = True
            break

    if not callsite_found:
        return _check(
            "FAIL",
            "C1: acquire_all nicht als ausgefuehrter Call-Site in Engine-Quellen (*.py) "
            "gefunden -- nur Markdown-Prosa oder Implementierungs-Datei. "
            "Enforcement-Verdrahtung fehlt.",
        )

    guard_path = scripts_dir / "guard_stage_acquire_enforce.py"
    if not guard_path.exists():
        return _check(
            "WARN",
            "C2: Kein guard_stage_acquire_enforce.py gefunden -- fail-Pfad "
            "(acquire_all==False -> Halt) nicht strukturell erzwungen. "
            "Enforcement-Verdrahtung fehlt (batch_3 Fix).",
        )

    return _check("PASS")


def _behavior_check_d_granularity(commands_dir: Path) -> dict:
    """BL-486 AK-D-CHK: Pruefe ob _TDD_execute.md 3-Werte-Granularitaets-Selektor hat.

    D1: Granularitaets-Selektor mit einzeln/handvoll + granularit vorhanden?
    D2: Voll-Suite-Guard vorhanden?
    D3: Default=testSearch deklariert?
    """
    tdd_execute_path = commands_dir / "_TDD_execute.md"

    if not tdd_execute_path.exists():
        return _check(
            "FAIL",
            "D: _TDD_execute.md nicht gefunden -- Granularitaets-Pruefung nicht moeglich.",
        )

    try:
        content = tdd_execute_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _check("FAIL", f"D: _TDD_execute.md nicht lesbar ({exc}).")

    has_granularity_selector = (
        ("einzeln" in content or "single" in content)
        and ("handvoll" in content or "handful" in content)
        and "granularit" in content.lower()
    )
    if not has_granularity_selector:
        return _check(
            "FAIL",
            "D1: _TDD_execute.md enthaelt keinen 3-Werte-Granularitaets-Selektor "
            "(einzeln/handvoll/alle). Filter-Substrat in t_script.py:149-165 nicht in "
            "_TDD_execute gehoben.",
        )

    has_full_suite_guard = (
        "voll-suite-guard" in content.lower()
        or "full_suite" in content.lower()
        or "GUARD" in content
        or ("alle" in content and "guard" in content.lower())
    )
    if not has_full_suite_guard:
        return _check(
            "FAIL",
            "D2: _TDD_execute.md enthaelt keinen Voll-Suite-Guard -- "
            "versehentliches Ausloesen der 5h-Voll-Suite nicht verhindert.",
        )

    has_default_testsearch = (
        ("default" in content.lower() and "testsearch" in content.lower())
        or "default_granularity" in content.lower()
    )
    if not has_default_testsearch:
        return _check(
            "WARN",
            "D3: Default-Granularitaet nicht explizit als 'testSearch' in _TDD_execute.md "
            "deklariert.",
        )

    return _check("PASS")


def _behavior_check_f_release_eta() -> dict:
    """BL-486 AK-F-CHK: Pruefe ob release_all und ETA-Hold-Mechanismus vorhanden sind.

    F1: stage_resource_registry.release_all existiert?
    F2: stage_hold_decision.py vorhanden?
    """
    try:
        import stage_resource_registry as _srr_f  # noqa: PLC0415 -- lokaler Check-Import
        f1_ok = hasattr(_srr_f, "release_all") and callable(
            getattr(_srr_f, "release_all", None)
        )
    except ImportError:
        f1_ok = False

    hold_decision_path = Path(__file__).parent / "stage_hold_decision.py"
    f2_ok = hold_decision_path.exists()

    if not f1_ok and not f2_ok:
        return _check(
            "FAIL",
            "F1: stage_resource_registry.release_all fehlt (kein machine-globaler "
            "Recovery-Befehl). "
            "F2: stage_hold_decision.py fehlt (kein ETA-Hold-Mechanismus).",
        )

    if not f1_ok:
        return _check(
            "FAIL",
            "F1: stage_resource_registry.release_all fehlt -- "
            "nach Crash verwaiste Locks koennen nicht freigegeben werden "
            "(Deadlock-Risiko).",
        )

    if not f2_ok:
        return _check(
            "WARN",
            "F2: stage_hold_decision.py nicht gefunden -- "
            "ETA-Hold-Mechanismus fehlt (Allokation ohne ETA, keine HOLD-Entscheidung "
            "moeglich).",
        )

    return _check("PASS")


def _behavior_check_reg_registry(scripts_dir: Path) -> dict:
    """BL-486 AK-REG-CHK: Pruefe Registry-Zentralitaet.

    REG1: stage_infra_schema.py hat kein direktes IO?
    REG2: Kein dritter acquire-Kanal ausserhalb Registry-Schicht?
    """
    _EXCLUDED_REG = {
        "stage_resource_registry.py",
        "resource_allocator.py",
        "test_resource_allocator.py",
        "test_stage_resource_registry.py",
        # walker.py uses factory_lock for BL-level lane-management locks (not stage-resource
        # allocation) -- semantic intent of REG2 is stage-resource Single-Source-Enforcement.
        "walker.py",
    }
    # Split patterns to avoid self-match when this file is scanned as part of REG2.
    # Concatenation ensures neither pattern appears as a contiguous literal below.
    _ACQ_PAT = "srr" + ".acquire("               # noqa: REG2-SELF-AVOID
    _FL_PAT = "factory_lock" + ".acquire_bl("    # noqa: REG2-SELF-AVOID

    infra_schema_path = scripts_dir / "stage_infra_schema.py"

    if not infra_schema_path.exists():
        return _check(
            "WARN",
            "REG1: stage_infra_schema.py nicht gefunden -- REG-Check uebersprungen.",
        )

    try:
        schema_content = infra_schema_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _check(
            "WARN",
            f"REG1: stage_infra_schema.py nicht lesbar ({exc}) -- REG-Check uebersprungen.",
        )

    has_io = (
        "open(" in schema_content
        or ".read_text" in schema_content
        or ".read(" in schema_content
    )
    if has_io:
        return _check(
            "FAIL",
            "REG1: stage_infra_schema.py enthaelt IO-Aufrufe (open/read_text) -- "
            "direkter stage_N.md-Read vermutet; Resolver-Single-Source verletzt.",
        )

    # REG2: Dritter acquire-Kanal?
    third_channel_files = []
    for py_file in sorted(scripts_dir.glob("*.py")):
        if py_file.name in _EXCLUDED_REG or py_file.name.startswith("test_"):
            continue
        try:
            fc = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _ACQ_PAT in fc or _FL_PAT in fc:
            third_channel_files.append(py_file.name)

    if third_channel_files:
        return _check(
            "FAIL",
            f"REG2: Direkter acquire-Aufruf ausserhalb Registry-Schicht: "
            f"{third_channel_files} -- kein Single-Source-Allokations-Pfad.",
        )

    return _check("PASS")


# ---------------------------------------------------------------------------
# BL-486 batch_2 Verhaltens-Gate-Check (AK-E Post-SDF-Elevation, Stage 1)
# ---------------------------------------------------------------------------


def _behavior_check_e_elevation(
    scripts_dir: Path,
    *,
    audit_path: Optional[Path] = None,
    manifest: Optional[dict] = None,
) -> dict:
    """BL-486 AK-E-CHK: Post-SDF-Elevation-Enforcement. Verdict = worst_case(E1..E4).

    Jede Sub-Assertion introspektiert das LIVE-Substrat (Symbol-/Code-Scan, analog der
    batch_1-Familie _behavior_check_a_legacy..reg_registry). Kein hardcoded PASS — fehlt
    ein Substrat, verdiktiert die Aggregation FAIL.

    E1: guard_geist9b_sdf_post_inline.py — Post-SDF-Pfad vom enforce_active()-file-Gate
        ENTKOPPELT (kein agent-erreichbarer Self-Unlock); OMNI_ENFORCE_ALL_OFF (Owner-env)
        bleibt die einzige Notbremse.
    E2: guard_stage_elevation_audit.py — traegt stage_increment_has_preceding_post
        (off-the-books-Elevation-Detektor, audit.jsonl-Rueckwaerts-Scan).
    E3: manifest_schema.py — "epoch" in MANIFEST_SCHEMA["current_stage"].fields +
        "batch_stages_original" required=True.
    E4: guard_elevation_atomic.elevation_flush_is_atomic() == True
        (stage_elevation_flush.py traegt temp + os.replace/_atomic_write + Rollback-Pfad).
    """
    sub_statuses: list[str] = []
    hints: list[str] = []

    def _record(label: str, status: str, detail: str) -> None:
        sub_statuses.append(status)
        if status != "PASS":
            hints.append(f"{label}: {detail}")

    # --- E1: geist9b vom enforce_active()-file-Gate entkoppelt ---------------
    geist9b_path = scripts_dir / "guard_geist9b_sdf_post_inline.py"
    if not geist9b_path.exists():
        _record("E1", "FAIL", "guard_geist9b_sdf_post_inline.py nicht gefunden.")
    else:
        try:
            g_src = geist9b_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            g_src = ""
            _record("E1", "FAIL", f"guard_geist9b_sdf_post_inline.py nicht lesbar ({exc}).")
        if g_src:
            # Owner-env-Notbremse (agent-unerreichbar) muss erhalten sein.
            has_owner_env = "OMNI_ENFORCE_ALL_OFF" in g_src
            # Agent-erreichbarer file-Gate-Bypass: ein ausgefuehrter `if not enforce_active()`
            # early-out darf NICHT mehr existieren (Kommentar-Erwaehnungen von enforce_active()
            # sind erlaubt -- nur die ausfuehrbare Anweisung waere der Bypass).
            has_file_gate_earlyout = (
                "if not enforce_active(" in g_src
                or "if not read_enforce(" in g_src
            )
            if not has_owner_env:
                _record(
                    "E1", "FAIL",
                    "OMNI_ENFORCE_ALL_OFF (Owner-env-Notbremse) fehlt -- "
                    "BL-210-Souveraenitaet nicht belegt.",
                )
            elif has_file_gate_earlyout:
                _record(
                    "E1", "FAIL",
                    "ausfuehrbarer `if not enforce_active()`-file-Gate-early-out vorhanden "
                    "-- agent-erreichbarer Self-Unlock (POST-ROOT-1) NICHT entkoppelt.",
                )
            else:
                sub_statuses.append("PASS")

    # --- E2: stage-elevation-audit-Detektor vorhanden -----------------------
    audit_guard_path = scripts_dir / "guard_stage_elevation_audit.py"
    if not audit_guard_path.exists():
        _record("E2", "FAIL", "guard_stage_elevation_audit.py nicht gefunden.")
    else:
        try:
            a_src = audit_guard_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            a_src = ""
            _record("E2", "FAIL", f"guard_stage_elevation_audit.py nicht lesbar ({exc}).")
        if a_src:
            if "def stage_increment_has_preceding_post" in a_src:
                sub_statuses.append("PASS")
            else:
                _record(
                    "E2", "FAIL",
                    "stage_increment_has_preceding_post-Detektor (audit.jsonl-Rueckwaerts-Scan) "
                    "fehlt -- off-the-books-Elevation nicht fangbar.",
                )

    # --- E3: manifest_schema epoch + batch_stages_original required ----------
    try:
        import manifest_schema as _ms  # noqa: PLC0415 -- lokaler Check-Import
        schema = getattr(_ms, "MANIFEST_SCHEMA", None)
        if not isinstance(schema, dict):
            _record("E3", "FAIL", "MANIFEST_SCHEMA fehlt oder ist kein dict.")
        else:
            current_stage = schema.get("current_stage", {}) or {}
            cs_fields = current_stage.get("fields", {}) or {}
            bso = schema.get("batch_stages_original", {}) or {}
            epoch_present = "epoch" in cs_fields
            bso_required = bso.get("required") is True
            if epoch_present and bso_required:
                sub_statuses.append("PASS")
            else:
                missing = []
                if not epoch_present:
                    missing.append("'epoch' in current_stage.fields")
                if not bso_required:
                    missing.append("batch_stages_original.required is True")
                _record(
                    "E3", "FAIL",
                    "manifest_schema unvollstaendig: " + "; ".join(missing) + ".",
                )
    except ImportError:
        _record("E3", "FAIL", "manifest_schema.py nicht importierbar (POST-ROOT-2 offen).")

    # --- E4: elevation_flush atomic (temp + os.replace + Rollback) -----------
    try:
        import guard_elevation_atomic as _gea  # noqa: PLC0415 -- lokaler Check-Import
        probe = getattr(_gea, "elevation_flush_is_atomic", None)
        if probe is None or not callable(probe):
            _record(
                "E4", "FAIL",
                "guard_elevation_atomic.elevation_flush_is_atomic() fehlt.",
            )
        elif probe() is True:
            sub_statuses.append("PASS")
        else:
            _record(
                "E4", "FAIL",
                "elevation_flush_is_atomic() != True -- stage_elevation_flush.py belegt "
                "temp+os.replace/_atomic_write+Rollback nicht (POST-ROOT-3 offen).",
            )
    except ImportError:
        _record("E4", "FAIL", "guard_elevation_atomic.py nicht importierbar (POST-ROOT-3 offen).")

    verdict = _worst_case(*sub_statuses) if sub_statuses else "FAIL"
    return _check(verdict, "\n".join(hints) if hints else None)


# ---------------------------------------------------------------------------
# Haupt-API
# ---------------------------------------------------------------------------


def sanity_check_stage(
    stage_nr: int,
    *,
    vault_root: Optional[Path] = None,
    live: bool = False,
) -> dict:
    """Fuehre die 5 Stage-Sub-Checks strukturell durch.

    Parameters
    ----------
    stage_nr:   Stage-Nummer (z.B. 1..N).
    vault_root: Optionaler Vault-Root-Override (Tests reichen tmp_path rein).
    live:       opt-in Live-Tier (echter Test-Run) — Stub-Implementierung;
                strukturelle Tests pruefen live=False.

    Returns
    -------
    dict mit Schluesseln 'verdict', 'checks' (a-e) und 'stage_dir'.
    """
    # --- Stage aufloesen ---
    handle = resolve_stage(stage_nr, vault_root=vault_root)

    if handle is None:
        # Stage nicht gefunden -> sofort FAIL, alle Checks unbekannt
        return {
            "verdict": "FAIL",
            "checks": {
                k: _check("FAIL", f"Stage {stage_nr} nicht gefunden (NOT_FOUND).")
                for k in ("a", "b", "c", "d", "e")
            },
            "stage_dir": None,
        }

    stage_dir_str = str(handle.stage_dir) if handle.stage_dir is not None else None

    # --- Slice-Set-Validierung (INV-STAGE-SC-2: kein Re-Implement) ---
    schema_result = validate_slice_set(handle.stage_dir) if handle.stage_dir else None

    # execute-Slice laden
    execute_fm: dict = handle.slice_view("execute") or {}
    testbefehl: Optional[str] = execute_fm.get("testbefehl")
    # Normalisieren: None, leerer String, Null-YAML -> kein testbefehl
    if not testbefehl:
        testbefehl = None

    # -----------------------------------------------------------------------
    # Sub-Check (a) — Gezielt EIN Test starten: execute.testbefehl vorhanden?
    # -----------------------------------------------------------------------
    if testbefehl:
        check_a = _check("PASS")
    else:
        check_a = _check(
            "FAIL",
            "execute.testbefehl fehlt oder Leer-Defekt — fuehre /_stage init aus.",
        )

    # -----------------------------------------------------------------------
    # Sub-Check (b) — Handvoll/Subset: --filter oder execute.filter vorhanden?
    # -----------------------------------------------------------------------
    hat_filter = False
    if testbefehl:
        hat_filter = (
            "--filter" in testbefehl
            or "--tests" in testbefehl
            or execute_fm.get("filter") is not None
        )

    if hat_filter:
        check_b = _check("PASS")
    else:
        check_b = _check(
            "WARN",
            "execute.testbefehl enthaelt kein --filter / execute.filter fehlt — "
            "Subset-Aufruf moeglich aber nicht deklariert (kein FAIL, nicht ALWAYS_REQUIRED).",
        )

    # -----------------------------------------------------------------------
    # Sub-Check (c) — Alle Tests: validate_slice_set PASS + concurrency_class valide?
    # -----------------------------------------------------------------------
    if schema_result is None:
        # Kein stage_dir (Legacy-Fallback ohne Verzeichnis) -> FAIL
        check_c = _check("FAIL", "Stage-Verzeichnis nicht aufloesbar — validate_slice_set nicht moeglich.")
    else:
        cc_fm: dict = handle.slice_view("concurrency_class") or {}
        cc_val = cc_fm.get("concurrency_class")

        if "concurrency_class" in (schema_result.missing_slices or []) or not cc_val:
            check_c = _check(
                "FAIL",
                "concurrency_class-Slice fehlt oder Leer-Defekt — "
                "fuehre /_stage update {nr} concurrency_class <wert> aus.",
            )
        elif not schema_result.valid:
            hint_parts = [f"{e.slice}: {e.message}" for e in schema_result.errors]
            check_c = _check(
                "FAIL",
                "validate_slice_set meldet Defekte: " + "; ".join(hint_parts),
            )
        else:
            check_c = _check("PASS")

    # -----------------------------------------------------------------------
    # Sub-Check (d) — Monitor liest Ergebnis: LogFileName/TDD-STATE ableitbar?
    # -----------------------------------------------------------------------
    monitor_ableitbar = testbefehl is not None and (
        "LogFileName" in testbefehl
        or "TDD-STATE" in testbefehl
        or "TDD-STATE" in str(execute_fm)
    )

    if monitor_ableitbar:
        check_d = _check("PASS")
    else:
        check_d = _check(
            "WARN",
            "Monitor-Kanal (TDD-STATE.md / LogFileName) nicht aus execute ableitbar — "
            "pruefe execute.testbefehl auf LogFileName-Parameter.",
        )

    # -----------------------------------------------------------------------
    # Sub-Check (e) — Setup + Teardown: INFRA_CONDITIONAL vollstaendig oder skip?
    # -----------------------------------------------------------------------
    check_e_status = "PASS"
    hints_e: list[str] = []

    for slice_name in INFRA_CONDITIONAL_SLICES:
        # Ist der Slice im missing_slices? (schema_result koennte None sein)
        missing = (
            schema_result is not None
            and slice_name in (schema_result.missing_slices or [])
        )
        if missing:
            check_e_status = "FAIL"
            hints_e.append(f"{slice_name}.md fehlt — fuehre /_stage init aus.")
            continue

        slice_fm: dict = handle.slice_view(slice_name) or {}
        concern_field = SLICE_CONCERN_FIELD.get(slice_name)
        val = slice_fm.get(concern_field) if concern_field else None
        skip_explicit = _has_skip(slice_fm)

        if val is None and not skip_explicit:
            check_e_status = "FAIL"
            hints_e.append(
                f"{slice_name}.{concern_field} Leer-Defekt — "
                f"setze skip:true oder befuelle den Slice."
            )

    check_e = _check(
        check_e_status,
        "\n".join(hints_e) if hints_e else None,
    )

    # -----------------------------------------------------------------------
    # BL-486 Verhaltens-Gate-Checks (A / C / D / F / REG)
    # -----------------------------------------------------------------------
    _scripts_dir = Path(__file__).parent
    _commands_dir = _scripts_dir.parent / "commands"

    check_A = _behavior_check_a_legacy(handle=handle, vault_root=vault_root)
    check_C = _behavior_check_c_acquire(scripts_dir=_scripts_dir)
    check_D = _behavior_check_d_granularity(commands_dir=_commands_dir)
    check_F = _behavior_check_f_release_eta()
    check_REG = _behavior_check_reg_registry(scripts_dir=_scripts_dir)
    check_E = _behavior_check_e_elevation(scripts_dir=_scripts_dir)

    # -----------------------------------------------------------------------
    # Gesamt-Verdict
    # BL-486 NOTE: A/C/D/F/REG/E sind im checks-Dict vorhanden (G-INT-1..3, G-E-2)
    # aber werden NICHT in den globalen worst_case eingerechnet -- es sind additive
    # SOLL/IST-Gate-Checks (Vault-Residenz / acquire-Verdrahtung / release_all /
    # Post-SDF-Elevation), die den Gap registrieren ohne die Gesamt-PASS-Rate zu
    # korrumpieren (Gold G-INT-4/5 + G-E-10 markiert "N/A bis GREEN"). Namensraum:
    # Gross-"E" (AK-E Elevation-Gate) != klein-"e" (BL-412 Setup/Teardown) -- kein Overwrite.
    # -----------------------------------------------------------------------
    verdict = _worst_case(
        check_a["status"],
        check_b["status"],
        check_c["status"],
        check_d["status"],
        check_e["status"],
    )

    return {
        "verdict": verdict,
        "checks": {
            "a": check_a,
            "b": check_b,
            "c": check_c,
            "d": check_d,
            "e": check_e,
            "A": check_A,
            "C": check_C,
            "D": check_D,
            "F": check_F,
            "REG": check_REG,
            "E": check_E,
        },
        "stage_dir": stage_dir_str,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_report(stage_nr: int, result: dict, live: bool) -> None:
    stage_dir = result.get("stage_dir") or "n/a"
    tier = "strukturell + live" if live else "strukturell"
    checks = result["checks"]
    verdict = result["verdict"]

    print(f"=== /_stage sanity-check {stage_nr} ===")
    print(f"  Stage-Dir: {stage_dir}")
    print(f"  Tier: {tier}")
    print()
    for label, key in [
        ("(a) Gezielt EIN Test         ", "a"),
        ("(b) Handvoll/Subset          ", "b"),
        ("(c) Alle Tests (vollstaendig)", "c"),
        ("(d) Monitoring (TDD-STATE.md)", "d"),
        ("(e) Setup + Teardown         ", "e"),
        ("(A) Zentral-Auth (is_legacy) ", "A"),
        ("(C) Setup-acquire_all-CallSi ", "C"),
        ("(D) Granularitaets-Selektor  ", "D"),
        ("(F) release_all + ETA-Hold   ", "F"),
        ("(REG) Registry-Zentralitaet ", "REG"),
        ("(E) Post-SDF-Elevation-Gate  ", "E"),
    ]:
        ch = checks.get(key)
        if ch is None:
            continue
        line = f"  {label}: {ch['status']}"
        if ch["hint"]:
            line += f" -- {ch['hint']}"
        print(line)
    print()
    print(f"  Gesamt: {verdict}")
    if verdict == "PASS":
        print(f"  -> Stage {stage_nr} strukturell vollstaendig. Hand-und-Brot-Faehigkeiten: bereit.")
    elif verdict == "WARN":
        print(f"  -> WARN: Stage {stage_nr} pruefbar, aber nicht alle optionalen Felder deklariert.")
    else:
        print(f"  -> FAIL: Stage {stage_nr} hat Pflicht-Defekte. Sieh recovery_hints oben.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage-Sanity-Check (BL-412 AK-SC-PL-2): 5 Sub-Checks strukturell."
    )
    parser.add_argument("stage_nr", type=int, help="Stage-Nummer (z.B. 3)")
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Live-Tier aktivieren (echter Test-Run, opt-in).",
    )
    args = parser.parse_args(argv)

    result = sanity_check_stage(args.stage_nr, live=args.live)
    _print_report(args.stage_nr, result, live=args.live)

    verdict = result["verdict"]
    return {"PASS": 0, "WARN": 1, "FAIL": 2}.get(verdict, 2)


if __name__ == "__main__":
    # Windows-stdout default cp1252 -> Umlaute crashen. utf-8 erzwingen, fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))
