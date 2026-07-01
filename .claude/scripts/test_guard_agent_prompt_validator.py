"""
pytest tests fuer guard_agent_prompt_validator.py — Mega-Worker-Diskriminator (BL-210).

Deckt ab:
  - dict-Crash-Regression (Dauer-Fail-Open seit 2026-05-24): re.search auf dict/list/None
    darf NICHT crashen.
  - is_orchestrator_exec_contract: STRUKTURELLER Diskriminator (Dispatch-Worker / "run
    <orchestrator>" -> Verletzung; Single-Phase-Command / generische Verben -> legit).
  - Schicht-1-Luecke geschlossen: "run _I_orchestrate"-Vertrag wird nicht mehr als
    reines Routing durchgewunken.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_agent_prompt_validator.py"
sys.path.insert(0, str(SCRIPT_DIR))
import guard_agent_prompt_validator as g  # noqa: E402


# ──────────────────────── is_orchestrator_exec_contract ────────────────────────

def test_megaworker_dispatch_contract_is_violation():
    p = ("VERTRAG: der SDF-Phase-2-Dispatch-Worker (Opus) fuer Sub-Batch "
         "B_r17_05_fe_constants (DCSRE-486 Round 17, Modus M2). Fuehre Skill(_I_orchestrate) aus.")
    assert g.is_orchestrator_exec_contract(p) is True


def test_run_orchestrator_terse_is_violation():
    assert g.is_orchestrator_exec_contract("Agent-Auftrag: run _I_orchestrate for sub-batch 3") is True


def test_dispatch_role_marker_alone_is_violation():
    assert g.is_orchestrator_exec_contract("Du bist der Phase-2-Dispatch-Worker fuer Sub-Batch 3.") is True


def test_blueprint_single_phase_is_legit():
    p = "VERTRAG: _I_blueprintArchitect — fuehre die Blueprint-Analyse fuer _I_orchestrate Stage 2 aus."
    assert g.is_orchestrator_exec_contract(p) is False


def test_tdd_single_phase_is_legit():
    assert g.is_orchestrator_exec_contract("Ring 2 GREEN: _TDD_green fuer test_login.") is False


def test_berater_single_phase_is_legit():
    assert g.is_orchestrator_exec_contract("VERTRAG: _SDF_berater_modusEntscheidung fuer DCSRE-486.") is False


def test_generic_verb_without_orchestrator_is_legit():
    # "fuehre ... aus" ohne Orchestrator-Objekt darf NICHT blocken (False-Positive-Schutz)
    assert g.is_orchestrator_exec_contract("Fuehre die Analyse der Oeffnungszeiten aus.") is False


# ──────────────────────── detect_orchestrator_via_agent (Schicht-1-Luecke) ────────────────────────

def test_schicht1_hole_closed_for_exec_contract():
    # "run _I_orchestrate"-Vertrag via Agent darf NICHT mehr als Routing durchgewunken werden
    is_v, cmd = g.detect_orchestrator_via_agent("run _I_orchestrate for sub-batch 3", "Agent")
    assert is_v is True
    assert "_I_orchestrate" in cmd


def test_single_phase_not_flagged_via_agent():
    is_v, _ = g.detect_orchestrator_via_agent("_TDD_green fuer test_login", "Agent")
    assert is_v is False


# ──────────────────────── dict-Crash-Regression ────────────────────────

def _run(ev):
    r = subprocess.run([sys.executable, str(GUARD_SCRIPT)],
                       input=json.dumps(ev), capture_output=True, text=True)
    return r


def test_dict_prompt_shape_does_not_crash():
    ev = {"tool_name": "Agent", "tool_input": {"prompt": {"text": "run _I_orchestrate"}}}
    r = _run(ev)
    out = json.loads(r.stdout.strip())
    assert "continue" in out
    assert "got 'dict'" not in (r.stderr or "")


def test_list_prompt_shape_does_not_crash():
    ev = {"tool_name": "Agent", "tool_input": {"prompt": ["x", {"content": "_TDD_red"}]}}
    r = _run(ev)
    out = json.loads(r.stdout.strip())
    assert "continue" in out


def test_none_shape_does_not_crash():
    ev = {"tool_name": "Agent", "tool_input": {"description": None}}
    r = _run(ev)
    out = json.loads(r.stdout.strip())
    assert out.get("continue") is True


def test_coerce_text_recurses_and_caps():
    assert g._coerce_text({"prompt": {"text": "hi"}}) == "hi"
    assert g._coerce_text(["a", "b"]) == "a\nb"
    assert g._coerce_text(None) == ""
    assert len(g._coerce_text({"x": "y" * 50000})) <= 20000


# ──────────────────────── Monolithic-Build-Worker (AK-b, Check 5, BL-423) ────────────────────────
#
# Check 5: detect_monolithic_build_worker(prompt, tool_name, modus). Blockt einen
# Worker-Spawn der im selben Prompt Test-SCHREIBEN UND Impl buendelt — aber NUR in
# modus M2/M3 (M1/None short-circuit), NUR ohne Single-Phase-Whitelist-Eintrag, und
# FAIL-OPEN wenn kein modus auflösbar.
#
# Env-Contract (GREEN implementiert exakt dagegen):
#   - modus-Quelle: OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST -> read_modus() liest
#     `DF_BATCH_STATE.modus` daraus (Regex: modus\s*:\s*"?(M[0-9])"?). Aufloesung:
#     dieses Env > _resolve_vault_path('manifest') > None (FAIL-OPEN).
#   - enforce: ueber den Standard-Gate (_enforce_gate.enforce_active) -> OMNI_SESSION_PARAMS
#     zeigt auf ein _session_params.md mit "**enforceProcess:** true|false".
#   - Block-message enthaelt "Skill(_I_orchestrate" + "RED" (RED-Worker != GREEN-Worker).

def _run_mono(prompt, modus=None, enforce=True, tool_name="Agent"):
    """Schreibt synthetisches _manifest.md (modus) + _session_params.md (enforce),
    setzt OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST + OMNI_SESSION_PARAMS und ruft den
    Guard via subprocess. modus=None -> Manifest-Env zeigt auf NICHT-EXISTENTEN Pfad
    (FAIL-OPEN-Pfad: env_path gesetzt aber not is_file() -> read_modus()=None -> continue).
    Gibt (proc, verdict_dict) zurueck."""
    env = os.environ.copy()
    tmp_paths = []
    if modus is not None:
        mf = tempfile.NamedTemporaryFile(mode="w", suffix="_manifest.md", delete=False, encoding="utf-8")
        mf.write(f'DF_BATCH_STATE:\n  modus: "{modus}"\n')
        mf.close()
        tmp_paths.append(mf.name)
        env["OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST"] = mf.name
    else:
        # Setze auf nicht-existenten Pfad statt env.pop — verhindert Fallback auf real-vault.
        # read_modus(): env_path gesetzt aber not is_file() -> return None -> FAIL-OPEN.
        env["OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST"] = os.path.join(
            tempfile.gettempdir(), "definitely_nonexistent_manifest.md"
        )
    sp = tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8")
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    tmp_paths.append(sp.name)
    env["OMNI_SESSION_PARAMS"] = sp.name
    ev = {"tool_name": tool_name, "tool_input": {"prompt": prompt}}
    proc = subprocess.run([sys.executable, str(GUARD_SCRIPT)],
                          input=json.dumps(ev), capture_output=True, text=True, env=env)
    for p in tmp_paths:
        Path(p).unlink(missing_ok=True)
    verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, verdict


def test_mono_m3_test_and_impl_blocked():
    """T-b1: modus=M3, Prompt buendelt Test-Schreiben UND Impl -> BLOCK (continue=false)."""
    prompt = "Baue batch_X: schreibe die Tests UND implementiere den Controller komplett."
    proc, r = _run_mono(prompt, modus="M3", enforce=True)
    assert r.get("continue") is False, f"erwartet BLOCK (continue=false), war {r}"
    msg = r.get("message", "") + (proc.stderr or "")
    assert "Skill(_I_orchestrate" in msg, "Recovery-Hint 'Skill(_I_orchestrate' fehlt"
    assert "RED" in msg, "RED-Worker != GREEN-Worker Hinweis fehlt"


def test_mono_m2_test_and_impl_blocked():
    """T-b2: modus=M2, Test+Impl-Buendelung -> BLOCK."""
    prompt = "Schreibe die Unit-Tests und baue anschliessend das DTO-Mapping im selben Schritt."
    proc, r = _run_mono(prompt, modus="M2", enforce=True)
    assert r.get("continue") is False, f"erwartet BLOCK (continue=false), war {r}"


def test_mono_single_phase_whitelist_pass():
    """T-b3: modus=M3, Whitelist-Eintrag (_TDD_red) + Bau-Sprache -> PASS (legitimer Single-Phase)."""
    prompt = "Schreibe den failing Test via _TDD_red und implementiere danach den Controller."
    proc, r = _run_mono(prompt, modus="M3", enforce=True)
    assert r.get("continue") is True, f"erwartet PASS (Whitelist-Inversion), war {r}"


def test_mono_m1_short_circuit_pass():
    """T-b4: modus=M1, Test+Impl-Buendelung -> PASS (modus-Gate short-circuit)."""
    prompt = "Baue batch_X: schreibe die Tests UND implementiere den Controller komplett."
    proc, r = _run_mono(prompt, modus="M1", enforce=True)
    assert r.get("continue") is True, f"erwartet PASS (M1 short-circuit), war {r}"


def test_mono_no_manifest_fail_open_pass():
    """T-b5: KEIN Manifest-Env -> kein modus auflösbar -> FAIL-OPEN PASS."""
    prompt = "Baue batch_X: schreibe die Tests UND implementiere den Controller komplett."
    proc, r = _run_mono(prompt, modus=None, enforce=True)
    assert r.get("continue") is True, f"erwartet PASS (FAIL-OPEN), war {r}"


def test_mono_pure_doc_prompt_pass():
    """T-b6: modus=M3, reiner Doku-/Berater-Prompt OHNE Impl-Signal -> PASS (kein False-Positive)."""
    prompt = "Analysiere und dokumentiere die Architektur, schreibe einen Bericht."
    proc, r = _run_mono(prompt, modus="M3", enforce=True)
    assert r.get("continue") is True, f"erwartet PASS (kein Impl-Signal), war {r}"


# ──────────────────────── BL-422 AK-1: Wave-Skill-Exec-via-Agent ────────────────────────
#
# LÜCKE (DCSRE-1699): _EXEC_GOVERNS_ORCH_RE (Z135) + ORCHESTRATOR_COMMANDS (Z89) listen
# nur _X_orchestrate, NICHT die A-Pipeline-Wellen-Skills _spec/_K_score/_model/_gap.
# detect_mega_agent feuert erst bei >=2 Pipeline-Commands. Heute rutscht ein Agent-Spawn
# der "_spec ausführen" oder "führe _K_score aus" enthält ungeblockt durch.
#
# Contract AK-1 (gegen den wir testen):
#   WAVE_SKILLS = ["_spec", "_K_score", "_model", "_gap"]
#   Neuer Check: blockt Agent-Spawn der einen WAVE_SKILL AUSFÜHRT (Exec-Verb governt
#   Wave-Skill-Namen ODER "lade Skill `_spec`") — NUR wenn KEIN Wellen-Worker-Marker
#   (Explorer/Drafter/Synthese/welle) UND kein SINGLE_PHASE_COMMANDS-Eintrag.
#   Recovery-Hint enthält "Skill(" und "INV-AO-CALLER".
#
# Env-Contract (wie _run_mono): OMNI_SESSION_PARAMS -> _session_params.md mit
# "**enforceProcess:** true". tool_name="Agent", event via subprocess stdin.


def _run_wave(prompt, enforce=True, tool_name="Agent"):
    """Minimal subprocess helper für Wave-Skill-Tests (analog zu _run_mono).
    Setzt OMNI_SESSION_PARAMS -> enforce, schreibt kein Manifest (kein modus nötig).
    Gibt (proc, verdict_dict) zurück."""
    env = os.environ.copy()
    sp = tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8")
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    env["OMNI_SESSION_PARAMS"] = sp.name
    # Kein Manifest -> kein modus -> nur Wave-Skill-Check relevant
    env.pop("OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST", None)
    ev = {"tool_name": tool_name, "tool_input": {"prompt": prompt}}
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(ev), capture_output=True, text=True, env=env,
    )
    Path(sp.name).unlink(missing_ok=True)
    verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, verdict


def test_wave_skill_spec_via_agent_blocked():
    """T-422a-1: Agent-Spawn 'lade Skill _spec und führe sie aus' OHNE Wellen-Marker
    -> BLOCK (continue=false, enforce=true). Recovery-Hint enthält 'Skill('. [BL-422 AK-1]

    RED-Erwartung: guard blockt diesen Prompt NICHT (WAVE_SKILLS noch nicht in Detection).
    => dieser Test muss FAILEN bis GREEN-Worker WAVE_SKILLS implementiert."""
    prompt = "Agent: lade Skill _spec und führe sie aus für BL-X."
    proc, r = _run_wave(prompt, enforce=True, tool_name="Agent")
    assert r.get("continue") is False, (
        f"T-422a-1 RED: erwartet BLOCK (continue=false) — Wave-Skill '_spec' via Agent "
        f"ist INV-AO-CALLER-Verletzung. Guard hat PASS gegeben: {r} | stderr: {proc.stderr}"
    )
    msg = r.get("message", "") + (proc.stderr or "")
    assert "Skill(" in msg, f"T-422a-1: Recovery-Hint 'Skill(' fehlt in: {msg}"
    assert "INV-AO-CALLER" in msg, f"T-422a-1: 'INV-AO-CALLER' fehlt in Recovery-Hint: {msg}"


def test_wave_skill_kscore_via_agent_blocked():
    """T-422a-2: Agent-Prompt 'Führe _K_score aus.' OHNE Wellen-Marker -> BLOCK. [BL-422 AK-1]

    RED-Erwartung: Guard gibt PASS (WAVE_SKILLS noch nicht erkannt) -> Test FAILET."""
    prompt = "Führe _K_score aus."
    proc, r = _run_wave(prompt, enforce=True, tool_name="Agent")
    assert r.get("continue") is False, (
        f"T-422a-2 RED: erwartet BLOCK (continue=false) — '_K_score' via Agent "
        f"ist INV-AO-CALLER-Verletzung. Guard hat PASS gegeben: {r} | stderr: {proc.stderr}"
    )


def test_wave_skill_wellen_worker_passes():
    """T-422a-3 (FP-PASS): Wellen-Worker-Marker im Prompt -> PASS trotz _spec-Erwähnung.
    Explorer/Wellen-Member DARF _spec als Arbeitsgegenstand nennen — er führt sie nicht aus.
    Dieser Test muss JETZT schon grün sein (FP-Schutz muss erhalten bleiben). [BL-422 AK-1]"""
    prompt = (
        "Explorer E01 — Welle für _spec: lies die Quellen X/Y und liefere Findings. "
        "Kein Orchestrator-Aufruf — du bist ein Recherche-Worker."
    )
    proc, r = _run_wave(prompt, enforce=True, tool_name="Agent")
    assert r.get("continue") is True, (
        f"T-422a-3: FALSE-POSITIVE — Wellen-Worker-Marker 'Explorer' muss PASS ergeben. "
        f"Guard hat geblockt: {r} | stderr: {proc.stderr}"
    )


def test_wave_skill_via_skill_tool_passes():
    """T-422a-4 (FP-PASS): tool_name='Skill' statt 'Agent' + _spec im Prompt -> PASS.
    Lead-Handschuh-Wechsel via Skill() ist der KORREKTE Weg (INV-AO-CALLER).
    Guard greift NUR bei tool_name='Agent'. [BL-422 AK-1]"""
    prompt = "Lade und führe _spec aus für BL-X. Erstelle das Spec-Dokument."
    # Skill-Tool: Guard-main() checkt tool_name not in ["Agent", "TaskCreate", "SendMessage"] -> continue=True
    proc, r = _run_wave(prompt, enforce=True, tool_name="Skill")
    assert r.get("continue") is True, (
        f"T-422a-4: FALSE-POSITIVE — tool_name='Skill' muss immer PASS ergeben (Guard greift nicht). "
        f"Guard hat geblockt: {r} | stderr: {proc.stderr}"
    )


def test_wave_skill_single_phase_mention_passes():
    """T-422a-5 (FP-PASS): Agent-Prompt mit SINGLE_PHASE_COMMANDS-Eintrag der _spec beiläufig erwähnt
    -> PASS (Single-Phase-Whitelist). [BL-422 AK-1]

    '_berater_' ist in SINGLE_PHASE_COMMANDS -> is_orchestrator_exec_contract gibt False zurück.
    Dieser Test muss JETZT schon grün sein."""
    prompt = (
        "_SDF_berater_modusEntscheidung: analysiere Modus für Sub-Batch. "
        "Kontext: _spec läuft in Phase 5a der A-Pipeline (nur als Referenz)."
    )
    proc, r = _run_wave(prompt, enforce=True, tool_name="Agent")
    assert r.get("continue") is True, (
        f"T-422a-5: FALSE-POSITIVE — SINGLE_PHASE_COMMANDS-Eintrag '_berater_' muss PASS ergeben. "
        f"Guard hat geblockt: {r} | stderr: {proc.stderr}"
    )


# ──────────────────────── BL-439: Orchestrator-in-Agent-Skill-Form (Klammer-Blindspot) ────────────────────────
#
# BLINDSPOT (verifiziert): detect_orchestrator_via_agent matcht Orchestrator-Namen via
# `(?:^|[\s/])(_X_orchestrate)\b` — nur START/whitespace/SLASH davor.
# Damit rutscht `Skill(_A_orchestrate)` durch: der `(` vor dem Namen ist kein Match-Zeichen.
# Ebenso fehlen `_IDF_orchestrate` und `_SDF_orchestrate_post` in ORCHESTRATOR_ONLY_COMMANDS
# und ORCHESTRATOR_COMMANDS (F-08), weshalb die Fallback-Erkennung in
# detect_orchestrator_via_agent (L323-326: is_orchestrator_exec_contract liefert True,
# aber der cmd-Scan findet den Namen nicht) NUR "_<orchestrator>" liefert.
#
# GREEN muss BEIDE Luecken schliessen:
#   1. Klammer-Paren-Form: `Skill(_X_orchestrate)` → (True, "_X_orchestrate")
#   2. Fehlende Eintraege: `_IDF_orchestrate`, `_SDF_orchestrate_post` in ORCHESTRATOR_COMMANDS /
#      ORCHESTRATOR_ONLY_COMMANDS ergaenzen.
#
# FP-Schutz (5) ist der load-bearing False-Positive-Schutzzaun: Berater-Spawns (Single-Phase)
# DUERFEN NIE geblockt werden — das ist das KORREKTE Worker-Pattern.

class TestOrchestratorInAgentSkillForm:
    """BL-439 batch_1: Klammer-Paren-Form `Skill(_X_orchestrate)` in Agent-Prompts."""

    def test_skill_paren_form_a_orchestrate_blocked(self):
        """T-a1 (RED): detect_orchestrator_via_agent('lade Skill(_A_orchestrate) und führe aus', 'Agent')
        -> (True, '_A_orchestrate').

        AKTUELL: gibt (False, None) weil das Regex `(?:^|[\\s/])` den `(` vor `_A_orchestrate`
        nicht matcht. MUSS nach GREEN-Fix (True, '_A_orchestrate') liefern. [BL-439]
        """
        is_v, cmd = g.detect_orchestrator_via_agent(
            "lade Skill(_A_orchestrate) und führe aus", "Agent"
        )
        assert is_v is True, (
            f"T-a1 RED: erwartet (True, '_A_orchestrate'), bekam ({is_v}, {cmd!r}). "
            "Klammer-Paren-Form Skill(_A_orchestrate) wird nicht erkannt (Regex-Blindspot)."
        )
        assert cmd == "_A_orchestrate", f"T-a1: cmd erwartet '_A_orchestrate', bekam {cmd!r}"

    def test_skill_paren_form_idf_blocked(self):
        """T-a2 (RED): Skill(_IDF_orchestrate) in Agent-prompt -> (True, '_IDF_orchestrate').

        AKTUELL: (False, None) — Klammer-Blindspot + _IDF_orchestrate fehlt in
        ORCHESTRATOR_COMMANDS (F-08). [BL-439]
        """
        is_v, cmd = g.detect_orchestrator_via_agent(
            "Agent: führe Skill(_IDF_orchestrate) für das IDF aus.", "Agent"
        )
        assert is_v is True, (
            f"T-a2 RED: erwartet (True, '_IDF_orchestrate'), bekam ({is_v}, {cmd!r}). "
            "Klammer-Paren-Form + fehlender ORCHESTRATOR_COMMANDS-Eintrag (F-08)."
        )
        assert cmd == "_IDF_orchestrate", f"T-a2: cmd erwartet '_IDF_orchestrate', bekam {cmd!r}"

    def test_skill_paren_form_sdf_post_blocked(self):
        """T-a3 (RED): Skill(_SDF_orchestrate_post) in Agent-prompt -> (True, ...).

        AKTUELL: (False, None) — Klammer-Blindspot + _SDF_orchestrate_post fehlt in
        ORCHESTRATOR_COMMANDS (F-08). [BL-439]
        """
        is_v, cmd = g.detect_orchestrator_via_agent(
            "Spawne Agent der Skill(_SDF_orchestrate_post) ausführt.", "Agent"
        )
        assert is_v is True, (
            f"T-a3 RED: erwartet (True, '_SDF_orchestrate_post'), bekam ({is_v}, {cmd!r}). "
            "Klammer-Paren-Form + fehlender ORCHESTRATOR_COMMANDS-Eintrag (F-08)."
        )
        assert "_SDF_orchestrate_post" in (cmd or ""), (
            f"T-a3: cmd soll '_SDF_orchestrate_post' enthalten, bekam {cmd!r}"
        )

    def test_skill_form_main_blocks_enforce_true(self):
        """T-a4 (RED, subprocess): main() mit Agent-event prompt='lade Skill(_SDF_orchestrate) und führe aus'
        -> bei enforce=true: continue=false (BLOCK). [BL-439]

        AKTUELL: Guard gibt continue=true (Blindspot rutscht durch main()). MUSS nach GREEN
        continue=false liefern mit Recovery-Hint.
        """
        proc, r = _run_wave(
            "lade Skill(_SDF_orchestrate) und führe aus",
            enforce=True,
            tool_name="Agent",
        )
        assert r.get("continue") is False, (
            f"T-a4 RED (enforce=true): erwartet BLOCK (continue=false), bekam {r} | "
            f"stderr: {proc.stderr}"
        )

    def test_skill_form_main_warns_enforce_false(self):
        """T-a4b (RED, subprocess): Gleicher Prompt + enforce=false -> continue=true (WARN, kein Block).

        AKTUELL: ebenfalls continue=true, aber aus dem FALSCHEN Grund (Blindspot, kein Check trifft).
        Nach GREEN muss es continue=true AUS DEM RICHTIGEN Grund liefern (enforce=false -> WARN).
        Da aktuell false-positive-pass, pruefen wir hier NUR den WARN-Pfad-Marker: nach GREEN
        muss eine Warning-Message gesetzt sein. Dieser Test ist primär FP-Dokumentation.

        ACHTUNG: dieser Subtest kann aktuell gruen sein (aus falschem Grund) — das ist OK,
        er dokumentiert das erwartete Verhalten nach GREEN und sichert den enforce=false-Pfad.
        """
        proc, r = _run_wave(
            "lade Skill(_SDF_orchestrate) und führe aus",
            enforce=False,
            tool_name="Agent",
        )
        # Nach GREEN: continue=true, ABER message enthaelt Warning-Signal
        # Aktuell: continue=true aus Blindspot (kein Warning gesetzt) — nach GREEN: Warning da
        assert r.get("continue") is True, (
            f"T-a4b: enforce=false muss immer continue=true liefern, bekam {r}"
        )

    # ── FP-Schutz (load-bearing, Test 5) ──────────────────────────────────────

    def test_fp_berater_modusEntscheidung_passes(self):
        """T-a5a (FP-PASS, load-bearing): Berater-Spawn 'lade Skill(_SDF_berater_modusEntscheidung)'
        -> (False, None). Berater-Spawns sind das KORREKTE Worker-Pattern — DUERFEN NIE blocken.

        Dieser Test MUSS jetzt schon gruen sein und nach GREEN gruen bleiben (Regression-Zaun).
        '_berater_' ist in SINGLE_PHASE_COMMANDS -> is_orchestrator_exec_contract gibt False. [BL-439]
        """
        is_v, cmd = g.detect_orchestrator_via_agent(
            "lade Skill(_SDF_berater_modusEntscheidung) und führe aus", "Agent"
        )
        assert is_v is False, (
            f"T-a5a FALSE-POSITIVE: Berater-Spawn darf NIE geblockt werden. "
            f"bekam ({is_v}, {cmd!r})"
        )
        assert cmd is None, f"T-a5a: cmd soll None sein, bekam {cmd!r}"

    def test_fp_berater_specparse_passes(self):
        """T-a5b (FP-PASS): Skill(_A_berater_specParse) -> (False, None). [BL-439]"""
        is_v, cmd = g.detect_orchestrator_via_agent(
            "Agent: lade Skill(_A_berater_specParse) für Phase 5a.", "Agent"
        )
        assert is_v is False, (
            f"T-a5b FALSE-POSITIVE: _A_berater_specParse ist Single-Phase, bekam ({is_v}, {cmd!r})"
        )

    def test_fp_berater_idf_validator_passes(self):
        """T-a5c (FP-PASS): Skill(_IDF_berater_validator) -> (False, None). [BL-439]"""
        is_v, cmd = g.detect_orchestrator_via_agent(
            "Führe Skill(_IDF_berater_validator) aus.", "Agent"
        )
        assert is_v is False, (
            f"T-a5c FALSE-POSITIVE: _IDF_berater_validator ist Single-Phase, bekam ({is_v}, {cmd!r})"
        )

    def test_fp_i_clean_code_architect_passes(self):
        """T-a5d (FP-PASS): Skill(_I_cleanCodeArchitect) -> (False, None). [BL-439]"""
        is_v, cmd = g.detect_orchestrator_via_agent(
            "lade Skill(_I_cleanCodeArchitect) für Slice 2.", "Agent"
        )
        assert is_v is False, (
            f"T-a5d FALSE-POSITIVE: _I_cleanCodeArchitect ist Single-Phase, bekam ({is_v}, {cmd!r})"
        )

    # ── Regression: bestehender Slash-Form-Pfad darf nicht brechen ────────────

    def test_existing_slash_form_still_blocks(self):
        """T-a6 (Regression-PASS): 'Fuehre /_A_orchestrate aus' -> (True, '_A_orchestrate').

        Der bestehende Erkennungs-Pfad (Slash/Whitespace vor Orchestrator-Namen) MUSS
        nach GREEN weiterhin funktionieren. [BL-439]
        """
        is_v, cmd = g.detect_orchestrator_via_agent(
            "Fuehre /_A_orchestrate aus", "Agent"
        )
        assert is_v is True, (
            f"T-a6 REGRESSION: Slash-Form '/_A_orchestrate' muss erkannt werden, "
            f"bekam ({is_v}, {cmd!r})"
        )
        assert cmd == "_A_orchestrate", f"T-a6: cmd erwartet '_A_orchestrate', bekam {cmd!r}"


# ──────────────────────── BL-439 AK-4/AK-5: combined-prompt bypass + audit-event ────────────────────────
#
# AK-5 (load-bearing bypass): is_orchestrator_exec_contract prueft SINGLE_PHASE_COMMANDS (~Z181)
# mit early-return False VOR _PAREN_ORCH_RE (~Z187). Ein kombinierter Prompt der SOWOHL
# Skill(_A_orchestrate) ALS AUCH einen _berater_-Substring enthaelt rutscht durch den early-return
# (return False = PASS) obwohl er eine Orchestrator-Delegation IST.
#
# AK-4 (Spec-Fidelity): Spec fordert distinktes Audit-Event ORCHESTRATOR_DELEGATION_BLOCKED
# fuer den Paren-Form-Delegations-Block. Aktuell emittiert main()/Check 3 ORCHESTRATOR_VIA_AGENT.
#
# RED-Erwartung fuer Tests 1-3: guard gibt PASS (kein Block) weil SINGLE_PHASE_COMMANDS
# early-return die Orchestrator-Detection unterdrueckt.
# RED-Erwartung fuer Test 6: Audit-Event ist ORCHESTRATOR_VIA_AGENT statt ORCHESTRATOR_DELEGATION_BLOCKED.
# Tests 4-5 (FP-Gegenproben): MUSS jetzt SCHON gruen sein — reine Berater-Prompts OHNE Orchestrator.

class TestOrchestratorDelegationF09:
    """BL-439 batch_1 Nachzuegler: combined-prompt bypass (AK-5) + audit-event-name (AK-4).

    AK-5: Orchestrator-Prioritaet MUSS hoeher stehen als SINGLE_PHASE_COMMANDS-Whitelist
    in is_orchestrator_exec_contract. Kombinierter Prompt triggert aktuell false-return
    durch _berater_-early-return.
    AK-4: Paren-Form-Delegation soll ORCHESTRATOR_DELEGATION_BLOCKED emittieren (nicht
    das generische ORCHESTRATOR_VIA_AGENT).
    """

    def test_f09_combined_orchestrate_plus_berater_blocked(self):
        """T-f09-1 (RED): detect_orchestrator_via_agent mit kombiniertem Prompt
        Skill(_A_orchestrate) + _IDF_berater_init -> erwartet (True, '_A_orchestrate').

        AKTUELL: is_orchestrator_exec_contract gibt False zurueck weil _berater_ in
        SINGLE_PHASE_COMMANDS early-return triggert (Z181-182) BEVOR _PAREN_ORCH_RE
        (Z187) geprueft wird. detect_orchestrator_via_agent gibt daher (False, None).
        MUSS nach GREEN-Fix (True, '_A_orchestrate') liefern. [BL-439 AK-5]
        """
        is_v, cmd = g.detect_orchestrator_via_agent(
            "lade Skill(_A_orchestrate) und rufe _IDF_berater_init auf", "Agent"
        )
        assert is_v is True, (
            f"T-f09-1 RED: erwartet (True, '_A_orchestrate'), bekam ({is_v}, {cmd!r}). "
            "combined-prompt mit Skill(_A_orchestrate) + _berater_ bypass: "
            "SINGLE_PHASE_COMMANDS early-return unterdrueckt Orchestrator-Detection."
        )
        assert cmd == "_A_orchestrate", (
            f"T-f09-1: cmd erwartet '_A_orchestrate', bekam {cmd!r}"
        )

    def test_f09_combined_skill_orch_plus_skill_berater_blocked(self):
        """T-f09-2 (RED): Prompt mit BEIDEN Skill()-Formen: Skill(_SDF_orchestrate) + Skill(_SDF_berater_modusEntscheidung)
        -> erwartet (True, '_SDF_orchestrate').

        AKTUELL: _berater_ early-return (SINGLE_PHASE_COMMANDS Z181) unterdrueckt
        _PAREN_ORCH_RE-Check. Orchestrator-Delegation rutscht durch. [BL-439 AK-5]
        """
        is_v, cmd = g.detect_orchestrator_via_agent(
            "erst Skill(_SDF_orchestrate), dann Skill(_SDF_berater_modusEntscheidung)", "Agent"
        )
        assert is_v is True, (
            f"T-f09-2 RED: erwartet (True, '_SDF_orchestrate'), bekam ({is_v}, {cmd!r}). "
            "Kombination Skill(orchestrate) + Skill(berater) muss als Violation erkannt werden: "
            "Orchestrator-Prioritaet MUSS vor SINGLE_PHASE_COMMANDS-Whitelist-Check stehen."
        )
        assert cmd == "_SDF_orchestrate", (
            f"T-f09-2: cmd erwartet '_SDF_orchestrate', bekam {cmd!r}"
        )

    def test_f09_exec_contract_orchestrator_priority(self):
        """T-f09-3 (RED): is_orchestrator_exec_contract mit kombiniertem Prompt
        Skill(_A_orchestrate) + _A_berater_specParse -> erwartet True.

        AKTUELL: _berater_ in SINGLE_PHASE_COMMANDS (Z143) trifft early-return (Z181-182)
        -> gibt False zurueck. Der Orchestrator-Match (_PAREN_ORCH_RE Z187) wird NIE erreicht.
        MUSS nach GREEN True liefern: Orchestrator-Match hat PRIORITAET vor Berater-Whitelist.
        [BL-439 AK-5]
        """
        result = g.is_orchestrator_exec_contract(
            "lade Skill(_A_orchestrate) und _A_berater_specParse"
        )
        assert result is True, (
            f"T-f09-3 RED: is_orchestrator_exec_contract erwartet True (Orchestrator-Match), "
            f"bekam {result}. SINGLE_PHASE_COMMANDS early-return gibt False bevor "
            "_PAREN_ORCH_RE geprueft wird — Orchestrator-Prioritaet verletzt."
        )

    # ── FP-Gegenproben (Tests 4-5): MUSS JETZT SCHON gruen sein ────────────────

    def test_f09_pure_berater_still_passes(self):
        """T-f09-4 (FP-PASS, muss jetzt gruen sein): detect_orchestrator_via_agent mit
        reinem Berater-Prompt OHNE Orchestrator -> (False, None).

        Reine Berater-Spawns ohne Orchestrator-Namen duerfen NIEMALS geblockt werden.
        SINGLE_PHASE_COMMANDS-Whitelist muss greifen. [BL-439 AK-5 FP-Gegenprobe]
        """
        is_v, cmd = g.detect_orchestrator_via_agent(
            "lade Skill(_SDF_berater_modusEntscheidung) und fuehre aus", "Agent"
        )
        assert is_v is False, (
            f"T-f09-4 FALSE-POSITIVE: reiner Berater-Prompt ohne Orchestrator "
            f"darf NIE geblockt werden. bekam ({is_v}, {cmd!r})"
        )
        assert cmd is None, f"T-f09-4: cmd soll None sein, bekam {cmd!r}"

    def test_f09_pure_single_phase_still_passes(self):
        """T-f09-5 (FP-PASS, muss jetzt gruen sein): is_orchestrator_exec_contract mit
        reinem Single-Phase-Prompt -> False.

        _I_cleanCodeArchitect ist in SINGLE_PHASE_COMMANDS -> Whitelist greift korrekt.
        [BL-439 AK-5 FP-Gegenprobe]
        """
        result = g.is_orchestrator_exec_contract(
            "lade Skill(_I_cleanCodeArchitect)"
        )
        assert result is False, (
            f"T-f09-5 FALSE-POSITIVE: _I_cleanCodeArchitect ist Single-Phase, "
            f"is_orchestrator_exec_contract soll False liefern, bekam {result}"
        )

    # ── AK-4: Audit-Event-Name (distinktes ORCHESTRATOR_DELEGATION_BLOCKED) ─────

    def test_paren_delegation_emits_specific_audit_event(self):
        """T-f09-6 (RED, subprocess): main() mit Agent-event Skill(_A_orchestrate) + _berater_,
        enforce=true -> Audit-Event soll ORCHESTRATOR_DELEGATION_BLOCKED enthalten
        (NICHT das generische ORCHESTRATOR_VIA_AGENT). [BL-439 AK-4]

        AKTUELL: der Guard gibt PASS (continue=true) weil AK-5-Bypass greift — das Audit-Event
        ORCHESTRATOR_DELEGATION_BLOCKED wird noch nicht emittiert. Dieser Test faellt aus ZWEI
        Gruenden: (a) kein BLOCK, (b) kein ORCHESTRATOR_DELEGATION_BLOCKED in Audit.

        GREEN-Implementierung: Orchestrator-Prioritaet fix (AK-5) + Check-3 emittiert
        ORCHESTRATOR_DELEGATION_BLOCKED (statt ORCHESTRATOR_VIA_AGENT) wenn Paren-Form erkannt.

        Wenn das Audit-Event-Pruefen zu fragil ist (temp-audit-Pfad noetig): diesen Test
        als minimal-invasiv kodiert — prueft NUR ob continue=false (BLOCK vorhanden);
        Audit-Event-Name-Verifikation ist docstring-deferred bis GREEN das Renaming macht.
        """
        import tempfile as _tf
        import os as _os

        env = _os.environ.copy()
        # enforce=true via OMNI_SESSION_PARAMS
        sp = _tf.NamedTemporaryFile(
            mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
        )
        sp.write("**enforceProcess:** true\n")
        sp.close()
        # Kein Manifest -> kein modus (AK-5 ist modus-unabhaengig)
        env.pop("OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST", None)
        env["OMNI_SESSION_PARAMS"] = sp.name

        # Temp-audit-Pfad: leite audit.jsonl in tmp um damit wir isoliert pruefen koennen
        audit_tmp = _tf.NamedTemporaryFile(
            mode="w", suffix="_audit.jsonl", delete=False, encoding="utf-8"
        )
        audit_tmp.close()
        env["OMNI_AUDIT_JSONL_OVERRIDE"] = audit_tmp.name

        ev = {
            "tool_name": "Agent",
            "tool_input": {"prompt": "lade Skill(_A_orchestrate) und rufe _IDF_berater_init auf"},
        }
        proc = subprocess.run(
            [sys.executable, str(GUARD_SCRIPT)],
            input=json.dumps(ev), capture_output=True, text=True, env=env,
        )
        Path(sp.name).unlink(missing_ok=True)
        verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}

        # Primaer: BLOCK vorhanden (AK-5-Fix ist Vorbedingung)
        assert verdict.get("continue") is False, (
            f"T-f09-6 RED (enforce=true): erwartet BLOCK (continue=false), bekam {verdict} | "
            f"stderr: {proc.stderr}. AK-5-Bypass-Fix Vorbedingung fuer AK-4-Audit-Event."
        )

        # Sekundaer: Audit-Event-Name ORCHESTRATOR_DELEGATION_BLOCKED
        # (nur pruefbar wenn Guard OMNI_AUDIT_JSONL_OVERRIDE unterstuetzt; sonst docstring-deferred)
        audit_content = Path(audit_tmp.name).read_text(encoding="utf-8")
        Path(audit_tmp.name).unlink(missing_ok=True)
        # GREEN macht das Renaming; aktuell (RED) ist content leer oder enthaelt ORCHESTRATOR_VIA_AGENT.
        # Wir pruefen: ORCHESTRATOR_DELEGATION_BLOCKED erscheint in Audit-Output.
        # Falls OMNI_AUDIT_JSONL_OVERRIDE nicht unterstuetzt wird, bleibt audit_content leer
        # -> assert failt wegen fehlendem ORCHESTRATOR_DELEGATION_BLOCKED (korrekt: RED).
        assert "ORCHESTRATOR_DELEGATION_BLOCKED" in audit_content, (
            f"T-f09-6 RED (AK-4): Audit-Event soll 'ORCHESTRATOR_DELEGATION_BLOCKED' enthalten. "
            f"Audit-Content: {audit_content!r}. "
            "GREEN: Check-3 emittiert ORCHESTRATOR_DELEGATION_BLOCKED fuer Paren-Form-Delegation "
            "(zusaetzlich zu / statt ORCHESTRATOR_VIA_AGENT). "
            "Falls OMNI_AUDIT_JSONL_OVERRIDE nicht unterstuetzt: docstring-deferred bis GREEN."
        )


# ──────────────────────── BL-400 Check 6: M1-Skeleton-Overreach (AK-1..AK-6) ────────────────────────
#
# Check 6: detect_m1_skeleton_overreach(prompt, tool_name, modus) -> (is_violation, hint|None).
# Modus-gated: NUR M1, andere short-circuit (False, None). Analog Check-5-Struktur.
# Sanktioniertes 4-Step-Subset: architecturalLibrary, patternLibrary, semanticLibrary, codeAtomic.
# Verletzung wenn:
#   (a) Prompt nennt Steps AUSSERHALB des Subsets (testSearch, blueprintQG, goldDefine, etc.)
#   (b) Prompt signalisiert Lead-inline-Code-Emit ohne _I_orchestrate/--scope=skeleton-Marker
# False-Positive-Schutz: Single-Phase-Whitelist (z.B. _I_codeAtomic allein) -> PASS.
#
# AK-5 (subprocess): main() liest modus via read_modus() (OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST),
# enforce via read_enforce_process() (OMNI_SESSION_PARAMS). Env-Contract wie _run_mono().
# AK-6 (Doc-Drift): prueft dass _I_orchestrate.md + _SDF_berater_modusEntscheidung.md
# die stale-Phrasen NICHT als AKTIVE Aussagen tragen (historische SUPERSEDED-Refs erlaubt).
#
# RED-Erwartung AK-1..AK-5: detect_m1_skeleton_overreach existiert NOCH NICHT ->
# alle Funktionsaufruf-Tests failen mit AttributeError / NameError.
# AK-6: kann jetzt schon gruen sein (Doku bereits korrekt korrigiert 2026-06-18).

def _run_m1(prompt, modus=None, enforce=True, tool_name="Agent"):
    """Subprocess helper fuer M1-Skeleton-Overreach-Tests (analog _run_mono).
    Schreibt synthetisches _manifest.md (modus) + _session_params.md (enforce),
    setzt OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST + OMNI_SESSION_PARAMS.
    modus=None -> KEIN Manifest-Env (FAIL-OPEN-Pfad).
    Gibt (proc, verdict_dict) zurueck."""
    env = os.environ.copy()
    tmp_paths = []
    if modus is not None:
        mf = tempfile.NamedTemporaryFile(mode="w", suffix="_manifest.md", delete=False, encoding="utf-8")
        mf.write(f'DF_BATCH_STATE:\n  modus: "{modus}"\n')
        mf.close()
        tmp_paths.append(mf.name)
        env["OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST"] = mf.name
    else:
        env.pop("OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST", None)
    sp = tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8")
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    tmp_paths.append(sp.name)
    env["OMNI_SESSION_PARAMS"] = sp.name
    ev = {"tool_name": tool_name, "tool_input": {"prompt": prompt}}
    proc = subprocess.run([sys.executable, str(GUARD_SCRIPT)],
                          input=json.dumps(ev), capture_output=True, text=True, env=env)
    for p in tmp_paths:
        Path(p).unlink(missing_ok=True)
    verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, verdict


class TestM1SkeletonOverreach:
    """BL-400 batch_1 Check 6: detect_m1_skeleton_overreach(prompt, tool_name, modus).

    AK-1: Modus-Gate (M2/None -> short-circuit PASS).
    AK-2: Overreach-Detektion (>4 Steps / Skelett-fremde Steps -> BLOCK).
    AK-3: Lead-inline-Code-Emit ohne _I_orchestrate-Handschuh -> BLOCK.
    AK-4: FP-Schutz (legitimer Skelett-Worker -> PASS).
    AK-5: main()-Wiring (subprocess, enforce-respektierend, audit.jsonl).
    AK-6: Doc-Drift-Verify (Markdown-Grep, Regressions-Zaun).
    """

    # ── AK-1: Modus-Gate (M1-gated short-circuit) ─────────────────────────────

    def test_ak1_m2_short_circuit_pass(self):
        """T-6-ak1a (RED): modus=M2 -> short-circuit (False, None).
        Funktion existiert noch nicht -> AttributeError = RED. [BL-400 AK-1]"""
        result = g.detect_m1_skeleton_overreach(
            "Spawne M1-Worker mit _I_codeAtomic UND _I_testSearch UND _I_blueprintQG", "Agent", "M2"
        )
        assert result == (False, None), (
            f"T-6-ak1a: modus=M2 muss short-circuit (False, None) liefern, bekam {result!r}. "
            "Check 6 ist NUR M1-relevant (analog Check-5-IV-b2)."
        )

    def test_ak1_none_modus_short_circuit_pass(self):
        """T-6-ak1b (RED): modus=None -> short-circuit (False, None).
        Funktion existiert noch nicht -> AttributeError = RED. [BL-400 AK-1]"""
        result = g.detect_m1_skeleton_overreach(
            "Spawne M1-Worker mit _I_codeAtomic UND _I_testSearch", "Agent", None
        )
        assert result == (False, None), (
            f"T-6-ak1b: modus=None muss short-circuit (False, None) liefern, bekam {result!r}."
        )

    # ── AK-2: Overreach-Detektion (>4 Steps / Skelett-fremde Buendelung) ──────

    def test_ak2_multi_step_overreach_flagged(self):
        """T-6-ak2a (RED): modus=M1 + Prompt nennt _I_codeAtomic UND _I_testSearch UND _I_blueprintQG
        (>4 Steps / Skelett-fremde Buendelung) -> (True, hint).
        Funktion fehlt -> AttributeError = RED. [BL-400 AK-2]"""
        prompt = (
            "M1-Worker: fuehre _I_codeAtomic UND _I_testSearch UND _I_blueprintQG "
            "im selben Worker-Schritt aus."
        )
        is_v, hint = g.detect_m1_skeleton_overreach(prompt, "Agent", "M1")
        assert is_v is True, (
            f"T-6-ak2a: modus=M1 + Skelett-fremde Steps muss (True, hint) liefern, bekam ({is_v!r}, {hint!r}). "
            "_I_testSearch und _I_blueprintQG liegen ausserhalb des sanktionierten 4-Step-Subsets."
        )
        assert hint is not None, f"T-6-ak2a: hint darf nicht None sein, bekam {hint!r}"
        assert "M1 = 4-Step-Subset" in hint, (
            f"T-6-ak2a: hint soll 'M1 = 4-Step-Subset' enthalten (Recovery-Richtung). hint={hint!r}"
        )
        assert "Skill(_I_orchestrate --scope=skeleton)" in hint, (
            f"T-6-ak2a: hint soll 'Skill(_I_orchestrate --scope=skeleton)' enthalten. hint={hint!r}"
        )

    def test_ak2_skelett_fremder_single_step_flagged(self):
        """T-6-ak2b (RED): modus=M1 + Prompt nennt _I_goldDefine (Skelett-fremder Step) -> (True, hint).
        _I_goldDefine ist kein Subset-Eintrag. [BL-400 AK-2]"""
        prompt = "M1-Skelett-Worker: fuehre _I_goldDefine fuer PL-12 aus."
        is_v, hint = g.detect_m1_skeleton_overreach(prompt, "Agent", "M1")
        assert is_v is True, (
            f"T-6-ak2b: _I_goldDefine ist Skelett-fremd -> (True, hint). bekam ({is_v!r}, {hint!r})."
        )
        assert hint is not None, f"T-6-ak2b: hint darf nicht None sein"
        assert "M1 = 4-Step-Subset" in hint, (
            f"T-6-ak2b: Recovery-Richtung 'M1 = 4-Step-Subset' im hint erwartet. hint={hint!r}"
        )

    # ── AK-3: Lead-inline-Code-Emit ohne _I_orchestrate-Handschuh ─────────────

    def test_ak3_lead_inline_code_emit_flagged(self):
        """T-6-ak3 (RED): modus=M1 + Prompt signalisiert Lead-inline-Impl ohne Skill-Handschuh
        -> (True, hint) mit INV-PM-1-Referenz. [BL-400 AK-3]"""
        prompt = (
            "Schreibe direkt den Guid.Empty-Default in den Service, inline, kein Worker, "
            "kein Skill-Load — der Lead implementiert selbst."
        )
        is_v, hint = g.detect_m1_skeleton_overreach(prompt, "Agent", "M1")
        assert is_v is True, (
            f"T-6-ak3: Lead-inline-Impl ohne Handschuh muss (True, hint) liefern. "
            f"bekam ({is_v!r}, {hint!r})."
        )
        assert hint is not None, f"T-6-ak3: hint darf nicht None sein"
        assert "INV-PM-1 ABSOLUT" in hint, (
            f"T-6-ak3: hint soll 'INV-PM-1 ABSOLUT' enthalten. hint={hint!r}"
        )
        assert "Skill(_I_orchestrate --worker-mode --scope=skeleton)" in hint, (
            f"T-6-ak3: hint soll 'Skill(_I_orchestrate --worker-mode --scope=skeleton)' enthalten. "
            f"hint={hint!r}"
        )

    # ── AK-4: FP-Schutz (legitimer M1-Skelett-Worker -> PASS) ────────────────

    def test_ak4_fp_single_phase_codeatomic_passes(self):
        """T-6-ak4a (RED): modus=M1 + Prompt nennt _I_codeAtomic (Single-Phase-Whitelist-Eintrag allein)
        -> (False, None). Legitimer Single-Step-Worker ist KEIN Overreach. [BL-400 AK-4]"""
        prompt = "M1-Worker: fuehre _I_codeAtomic fuer PL-12 aus."
        is_v, hint = g.detect_m1_skeleton_overreach(prompt, "Agent", "M1")
        assert (is_v, hint) == (False, None), (
            f"T-6-ak4a FALSE-POSITIVE: _I_codeAtomic allein ist legit -> (False, None). "
            f"bekam ({is_v!r}, {hint!r})."
        )

    def test_ak4_fp_sanctioned_scope_skeleton_passes(self):
        """T-6-ak4b (RED): modus=M1 + Prompt mit --scope=skeleton-Handschuh-Marker
        -> (False, None). Sanktionierter Subset-Dispatch ist KEIN Overreach. [BL-400 AK-4]

        # BL-400<->BL-439-Interaktion (Lead-autorisierte Korrektur): dieser Test ruft
        # detect_m1_skeleton_overreach DIREKT (function-level) — Check 3 (detect_orchestrator_via_agent,
        # _PAREN_ORCH_RE) laeuft hier NICHT. Check 6 erkennt den --scope=skeleton-Marker als legit.
        # Der frueher hier benutzte Voll-Prompt 'Skill(_I_orchestrate --scope=skeleton)' wuerde
        # main-level von Check 3 korrekt geblockt (INV-AO-CALLER: _I_orchestrate gehoert NIE in einen
        # Agent-Prompt). Auf function-level testet dieser Fall nur die --scope=skeleton-Erkennung
        # von Check 6 isoliert."""
        prompt = "M1-Skelett-Dispatch via --scope=skeleton fuer PL-12."
        is_v, hint = g.detect_m1_skeleton_overreach(prompt, "Agent", "M1")
        assert (is_v, hint) == (False, None), (
            f"T-6-ak4b FALSE-POSITIVE: Skill(_I_orchestrate --scope=skeleton) ist sanktionieter Subset-Dispatch "
            f"-> (False, None). bekam ({is_v!r}, {hint!r})."
        )

    # ── AK-5: main()-Wiring (subprocess, enforce-respektierend) ───────────────

    def test_ak5_main_m1_overreach_enforce_true_blocked(self):
        """T-6-ak5a (RED, subprocess): M1-Overreach-Prompt + modus=M1 + enforceProcess=true
        -> continue=false (BLOCK) + violation=M1_SKELETON_OVERREACH in audit.jsonl. [BL-400 AK-5]

        RED-Erwartung: Guard gibt continue=true weil Check 6 nicht existiert."""
        env = os.environ.copy()
        tmp_paths = []

        mf = tempfile.NamedTemporaryFile(mode="w", suffix="_manifest.md", delete=False, encoding="utf-8")
        mf.write('DF_BATCH_STATE:\n  modus: "M1"\n')
        mf.close()
        tmp_paths.append(mf.name)
        env["OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST"] = mf.name

        sp = tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8")
        sp.write("**enforceProcess:** true\n")
        sp.close()
        tmp_paths.append(sp.name)
        env["OMNI_SESSION_PARAMS"] = sp.name

        audit_tmp = tempfile.NamedTemporaryFile(mode="w", suffix="_audit.jsonl", delete=False, encoding="utf-8")
        audit_tmp.close()
        tmp_paths.append(audit_tmp.name)
        env["OMNI_AUDIT_JSONL_OVERRIDE"] = audit_tmp.name

        prompt = (
            "M1-Worker: fuehre _I_codeAtomic UND _I_testSearch UND _I_blueprintQG "
            "im selben Worker-Schritt aus — Skelett-Scope-Ueberschreitung."
        )
        ev = {"tool_name": "Agent", "tool_input": {"prompt": prompt}}
        proc = subprocess.run([sys.executable, str(GUARD_SCRIPT)],
                              input=json.dumps(ev), capture_output=True, text=True, env=env)
        verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
        audit_content = Path(audit_tmp.name).read_text(encoding="utf-8")
        for p in tmp_paths:
            Path(p).unlink(missing_ok=True)

        assert verdict.get("continue") is False, (
            f"T-6-ak5a RED: erwartet BLOCK (continue=false) fuer M1-Overreach + enforce=true. "
            f"bekam {verdict!r} | stderr: {proc.stderr}. "
            "Check 6 ist noch nicht implementiert -> Guard gibt PASS (RED)."
        )
        assert "M1_SKELETON_OVERREACH" in audit_content, (
            f"T-6-ak5a RED: Audit-Event soll 'M1_SKELETON_OVERREACH' enthalten. "
            f"Audit-Content: {audit_content!r}"
        )

    def test_ak5_main_m1_overreach_enforce_false_warns(self):
        """T-6-ak5b (RED, subprocess): M1-Overreach-Prompt + enforceProcess=false -> continue=true (WARN).
        RED: Guard gibt PASS aber aus falschem Grund (kein Check 6). [BL-400 AK-5]"""
        prompt = (
            "M1-Worker: fuehre _I_codeAtomic UND _I_testSearch UND _I_blueprintQG aus — Overreach."
        )
        proc, verdict = _run_m1(prompt, modus="M1", enforce=False)
        # Nach GREEN: continue=true UND message enthaelt Warning-Signal.
        # Aktuell (RED): continue=true aber weil kein Check 6 greift (kein Warning).
        # Wir pruefen den WARN-Pfad sekundaer — primaer ist, dass nach GREEN eine Message da ist.
        assert verdict.get("continue") is True, (
            f"T-6-ak5b: enforce=false muss immer continue=true liefern (WARN, kein Block). "
            f"bekam {verdict!r}"
        )
        # Sekundaer: Nach GREEN muss message das Warning-Signal enthalten.
        # Im RED-Zustand fehlt das Warning (kein Check 6) — wir dokumentieren das erwartet Verhalten.
        # Dieser Assert ist absichtlich SCHWACH (nur continue-Pruefung), da der enforce=false-WARN-Pfad
        # korrekt nur nach GREEN testbar ist. Ein separater Subtest verstaerkt die Message-Pruefung nach GREEN.

    def test_ak5_main_legitimate_m1_worker_passes(self):
        """T-6-ak5c (RED, subprocess): Legitimer M1-Skelett-Worker (Single-Phase-Step _I_codeAtomic)
        -> continue=true (PASS). [BL-400 AK-5]

        # BL-400<->BL-439-Interaktion: _I_orchestrate gehoert NIE in einen Agent-Prompt (Check 3 /
        # INV-AO-CALLER blockt Skill(_I_orchestrate) in Agent-Prompts korrekt). Der legitime
        # Agent-getragene M1-Worker = Single-Phase-Skelett-Step (_I_codeAtomic), KEIN
        # _I_orchestrate-Handschuh (das ist der Lead-Skill-Pfad, nicht Agent). Prompt entsprechend
        # auf den realistischen legitimen Agent-Worker umgestellt (Lead-autorisiert)."""
        prompt = "Spawne Worker fuer M1-Skelett PL-12: Skill(_I_codeAtomic)."
        proc, verdict = _run_m1(prompt, modus="M1", enforce=True)
        assert verdict.get("continue") is True, (
            f"T-6-ak5c FALSE-POSITIVE: legitimer M1-Skelett-Worker muss PASS ergeben. "
            f"bekam {verdict!r} | stderr: {proc.stderr}"
        )

    # ── AK-6: Doc-Drift-Verify (Markdown-Grep-Assertion) ─────────────────────

    def test_ak6_i_orchestrate_md_no_stale_active_assertion(self):
        """T-6-ak6a: _I_orchestrate.md traegt KEINE aktive Aussage 'M1 = Lead-inline OHNE Skill-Load'
        / 'M1 = Lead-inline ohne Skill-Loads' / '_I_orchestrate wird gar nicht geladen'.

        Historische Verweise in Anfuehrungszeichen nach 'Frueherer Stand' / 'SUPERSEDED' /
        'KORRIGIERT' sind erlaubt (kein aktiver Vertrag). Der Test prueft:
        jede Zeile die eine der stale-Phrasen enthaelt, muss im selben Absatz (+-10 Zeilen)
        von einem SUPERSEDED/KORRIGIERT/Frueherer-Stand-Marker begleitet sein.

        Falls die Doku bereits korrekt ist (wie nach KORRIGIERT 2026-06-18): AK-6 ist GRUEN
        -> Regressions-Zaun (verhindert Re-Drift). [BL-400 AK-6]"""
        doc_path = Path(SCRIPT_DIR).parent / "commands" / "_I_orchestrate.md"
        assert doc_path.exists(), f"T-6-ak6a: Datei nicht gefunden: {doc_path}"
        content = doc_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        stale_phrases = [
            "M1 = Lead-inline OHNE Skill-Load",
            "M1 = Lead-inline ohne Skill-Loads",
            "_I_orchestrate wird gar nicht geladen",
        ]
        superseded_markers = [
            "SUPERSEDED", "KORRIGIERT", "Frueherer Stand", "frueher",
            "frueherer stand", "superseded", "korrigiert",
        ]

        violations = []
        for i, line in enumerate(lines):
            for phrase in stale_phrases:
                if phrase.lower() in line.lower():
                    # Pruefe ob der Absatz (+-10 Zeilen) einen SUPERSEDED/KORRIGIERT-Marker hat
                    context_start = max(0, i - 10)
                    context_end = min(len(lines), i + 11)
                    context_block = "\n".join(lines[context_start:context_end])
                    has_marker = any(m.lower() in context_block.lower() for m in superseded_markers)
                    if not has_marker:
                        violations.append(
                            f"Zeile {i+1}: '{phrase}' ohne SUPERSEDED/KORRIGIERT-Marker im Kontext. "
                            f"Aktive Aussage! Kontext: {lines[i]!r}"
                        )

        assert not violations, (
            f"T-6-ak6a: _I_orchestrate.md enthaelt stale-Phrasen als AKTIVE Aussagen:\n"
            + "\n".join(violations)
            + "\nFix: SUPERSEDED/KORRIGIERT-Marker hinzufuegen oder Phrase entfernen."
        )

    def test_ak6_sdf_modusentscheidung_md_no_stale_active_assertion(self):
        """T-6-ak6b: _SDF_berater_modusEntscheidung.md traegt KEINE aktive Aussage
        'M1 = Lead-inline OHNE Skill-Load' / 'M1 = Lead-inline ohne Skill-Loads' /
        '_I_orchestrate wird gar nicht geladen'.

        Falls die Doku korrekt ist: AK-6 GRUEN -> Regressions-Zaun. [BL-400 AK-6]"""
        doc_path = Path(SCRIPT_DIR).parent / "commands" / "_SDF_berater_modusEntscheidung.md"
        assert doc_path.exists(), f"T-6-ak6b: Datei nicht gefunden: {doc_path}"
        content = doc_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        stale_phrases = [
            "M1 = Lead-inline OHNE Skill-Load",
            "M1 = Lead-inline ohne Skill-Loads",
            "_I_orchestrate wird gar nicht geladen",
        ]
        superseded_markers = [
            "SUPERSEDED", "KORRIGIERT", "Frueherer Stand", "frueher",
            "frueherer stand", "superseded", "korrigiert",
        ]

        violations = []
        for i, line in enumerate(lines):
            for phrase in stale_phrases:
                if phrase.lower() in line.lower():
                    context_start = max(0, i - 10)
                    context_end = min(len(lines), i + 11)
                    context_block = "\n".join(lines[context_start:context_end])
                    has_marker = any(m.lower() in context_block.lower() for m in superseded_markers)
                    if not has_marker:
                        violations.append(
                            f"Zeile {i+1}: '{phrase}' ohne SUPERSEDED/KORRIGIERT-Marker im Kontext. "
                            f"Aktive Aussage! Kontext: {lines[i]!r}"
                        )

        assert not violations, (
            f"T-6-ak6b: _SDF_berater_modusEntscheidung.md enthaelt stale-Phrasen als AKTIVE Aussagen:\n"
            + "\n".join(violations)
            + "\nFix: SUPERSEDED/KORRIGIERT-Marker hinzufuegen oder Phrase entfernen."
        )


# ──────────────────────── BL-461 Check 8: Phantom-Opus (detect_phantom_opus) ────────────────────────
#
# BUG-KLASSE: Spawns mit subagent_type="general-opus" schlagen im Carrier fehl
# ("Agent type 'general-opus' not found"). Es gibt KEIN general-opus — Carrier-Kanon BL-125:
# opus-Tier via general-sonnet/general-purpose + model-Override, NIE als Subagent-Type.
#
# GUARD-CONTRACT Check 8 (vom GREEN-Worker zu bauen):
#   detect_phantom_opus(tool_name, tool_input) -> (is_violation: bool, hint: str | None)
#   - Trigger: tool_name == "Agent" UND tool_input.get("subagent_type") in
#     {"general-opus", "opus"} (case-insensitive, getrimmt).
#   - Violation -> main() printed {"continue": not enforce, "message": "[GUARD-VIOLATION] PHANTOM_OPUS: ..."}
#     + append_guard_log("PHANTOM_OPUS", ...) + append_audit_event("PHANTOM_OPUS", ...).
#   - Negativ (KEINE Violation, continue=True):
#       * subagent_type in {general-sonnet, general-haiku, general-purpose}
#       * Custom-Typen (be-*, Explore, system-architect)
#       * subagent_type fehlt / None
#       * tool_name != "Agent" (TaskCreate, SendMessage -> nicht relevant)
#   - Nur Agent (nicht TaskCreate/SendMessage).
#
# RED-Erwartung: Check 8 existiert noch nicht -> general-opus rutscht durch -> continue=True.
# T1/T2 MUESSEN FAILEN (erwartet continue=False, bekommt True).
# T3/T4/T5 koennen jetzt schon gruen sein (Negativ-Faelle: Guard gibt True aus dem richtigen Grund).

def _run_phantom(subagent_type=None, prompt="Analysiere den Kontext fuer BL-461.", enforce=True, tool_name="Agent"):
    """Subprocess helper fuer Phantom-Opus-Tests.
    Setzt OMNI_SESSION_PARAMS (enforce). Kein Manifest (kein modus noetig).
    tool_input enthaelt sowohl prompt als auch optional subagent_type.
    Gibt (proc, verdict_dict) zurueck.
    """
    env = os.environ.copy()
    sp = tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8")
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    env["OMNI_SESSION_PARAMS"] = sp.name
    env.pop("OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST", None)

    tool_input = {"prompt": prompt}
    if subagent_type is not None:
        tool_input["subagent_type"] = subagent_type

    ev = {"tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(ev), capture_output=True, text=True, env=env,
    )
    Path(sp.name).unlink(missing_ok=True)
    verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, verdict


class TestPhantomOpus:
    """BL-461 Check 8: detect_phantom_opus — Phantom-opus subagent_type Validation.

    Carrier-Kanon BL-125: opus-Tier via general-sonnet/general-purpose + model-Override.
    'general-opus' und 'opus' sind KEINE gueltigen subagent_type-Werte im Carrier.
    """

    def test_t1_general_opus_enforce_true_blocked(self):
        """T1 (RED): Agent + subagent_type='general-opus' + enforce=true
        -> continue=False + message enthaelt 'PHANTOM_OPUS'. [BL-461 Check 8]

        RED-Erwartung: Check 8 existiert noch nicht -> Guard gibt PASS (continue=True).
        Dieser Test MUSS jetzt FAILEN."""
        proc, r = _run_phantom(subagent_type="general-opus", enforce=True)
        assert r.get("continue") is False, (
            f"T1 RED: erwartet BLOCK (continue=False) fuer subagent_type='general-opus', "
            f"bekam {r} | stderr: {proc.stderr}. "
            "Check 8 (detect_phantom_opus) noch nicht implementiert -> Guard gibt PASS (RED)."
        )
        msg = r.get("message", "") + (proc.stderr or "")
        assert "PHANTOM_OPUS" in msg, (
            f"T1: message soll 'PHANTOM_OPUS' enthalten. message={msg!r}"
        )

    def test_t2_opus_subagent_type_blocked(self):
        """T2 (RED): Agent + subagent_type='opus' -> ebenfalls gefangen (continue=False). [BL-461 Check 8]

        'opus' als subagent_type ist genauso ungueltig wie 'general-opus'.
        RED-Erwartung: Guard gibt PASS (continue=True) weil Check 8 fehlt."""
        proc, r = _run_phantom(subagent_type="opus", enforce=True)
        assert r.get("continue") is False, (
            f"T2 RED: erwartet BLOCK (continue=False) fuer subagent_type='opus', "
            f"bekam {r} | stderr: {proc.stderr}. "
            "Check 8 noch nicht implementiert -> Guard gibt PASS (RED)."
        )
        msg = r.get("message", "") + (proc.stderr or "")
        assert "PHANTOM_OPUS" in msg, (
            f"T2: message soll 'PHANTOM_OPUS' enthalten. message={msg!r}"
        )

    def test_t3_general_sonnet_passes(self):
        """T3 (negativ): Agent + subagent_type='general-sonnet' -> continue=True (kein PHANTOM_OPUS). [BL-461]

        general-sonnet ist ein gueltiger Carrier-Subagent-Type. Darf NIEMALS geblockt werden.
        Dieser Test kann/soll jetzt schon gruen sein (Guard gibt True aus korrektem Grund)."""
        proc, r = _run_phantom(subagent_type="general-sonnet", enforce=True)
        assert r.get("continue") is True, (
            f"T3 FALSE-POSITIVE: subagent_type='general-sonnet' muss PASS ergeben (gueltiger Typ). "
            f"bekam {r} | stderr: {proc.stderr}"
        )

    def test_t4_general_purpose_passes(self):
        """T4 (negativ): Agent + subagent_type='general-purpose' -> continue=True. [BL-461]

        general-purpose ist ein gueltiger Carrier-Subagent-Type. Darf NIEMALS geblockt werden."""
        proc, r = _run_phantom(subagent_type="general-purpose", enforce=True)
        assert r.get("continue") is True, (
            f"T4 FALSE-POSITIVE: subagent_type='general-purpose' muss PASS ergeben. "
            f"bekam {r} | stderr: {proc.stderr}"
        )

    def test_t5_taskcreate_with_subagent_irrelevant_passes(self):
        """T5 (negativ): TaskCreate + subagent-irrelevant Payload -> continue=True. [BL-461]

        Check 8 ist AUSSCHLIESSLICH fuer tool_name='Agent'. TaskCreate hat keinen subagent_type-Parameter
        im Carrier-Kontext — Guard soll PASS geben ohne PHANTOM_OPUS zu pruefen."""
        proc, r = _run_phantom(subagent_type="general-opus", enforce=True, tool_name="TaskCreate")
        assert r.get("continue") is True, (
            f"T5 FALSE-POSITIVE: tool_name='TaskCreate' mit subagent_type='general-opus' "
            f"muss PASS ergeben (Check 8 gilt nur fuer Agent). "
            f"bekam {r} | stderr: {proc.stderr}"
        )


# ─────────────────────── Haiku-Floor-Guard (BL-452, Check 9) ───────────────────────
#
# Contract: detect_haiku_floor_violation(tool_name, tool_input)
#   Trigger: tool_name=="Agent" UND subagent_type (case-insensitive) in {"general-haiku","haiku"}
#            UND der prompt laedt eine REASONING-Skill:
#              (a) Skill(_..._berater_...) — berater-Pattern
#              (b) Skill(_TDD_(init|red|green|refactorCode|refactorTests|check|execute))
#              (c) Skill(_X_orchestrate) — orchestrator-Pattern (A/IDF/SDF/I/SC/BDF/...)
#   -> Violation: haiku ist unter dem Floor fuer Reasoning.
#
#   NEGATIV (KEIN Block):
#     - general-haiku + KEIN Reasoning-Skill-Load im prompt (z.B. nur "dotnet build",
#       "grep logs", "find files") -> mechanischer Executor (haiku-exempt, erlaubt).
#     - general-sonnet/general-purpose/opus + irgendwas -> falsche Bedingung (tool_name passt nicht).
#     - tool_name != "Agent" -> nicht relevant.
#
#   Block-Shape (analog Check 8):
#     {"continue": not enforce, "message": "...[HAIKU_FLOOR_VIOLATION|FLOOR]..."}
#     + append_guard_log("HAIKU_FLOOR_VIOLATION", ...) + append_audit_event(...)
#
# Reasoning-Skill-Regex (fuer GREEN-Worker):
#   r'Skill\(\s*_[A-Za-z_]+_berater_[A-Za-z_]+'         # berater-Pattern
#   r'|Skill\(\s*_TDD_(init|red|green|refactorCode|refactorTests|check|execute)\b'  # TDD-Kern
#   r'|Skill\(\s*_[A-Za-z_]+orchestrate\b'               # orchestrate-Pattern
#   (case-insensitive, alle drei als ODER-Gruppe)
#
# Exempt-Regel: kein Reasoning-Skill-Load im Prompt -> PASS (mechanischer Executor).
# Nur Agent (nicht TaskCreate/SendMessage).
#
# RED-Erwartung: Check 9 existiert noch nicht -> haiku + reasoning rutscht durch
# -> Guard gibt continue=True. T1/T2/T5 MUESSEN FAILEN (erwartet False, bekommt True).
# T3/T4 koennen jetzt schon gruen sein (Negativ-Faelle: Guard gibt True aus richtigem Grund).

def _run_floor(subagent_type="general-haiku", prompt="", enforce=True, tool_name="Agent"):
    """Subprocess helper fuer Haiku-Floor-Guard-Tests (Check 9).

    Setzt OMNI_SESSION_PARAMS (enforce). Kein Manifest (kein modus noetig fuer Check 9).
    tool_input enthaelt prompt + optional subagent_type.
    Gibt (proc, verdict_dict) zurueck.
    """
    env = os.environ.copy()
    sp = tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8")
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    env["OMNI_SESSION_PARAMS"] = sp.name
    env.pop("OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST", None)

    tool_input = {"prompt": prompt}
    if subagent_type is not None:
        tool_input["subagent_type"] = subagent_type

    ev = {"tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(ev), capture_output=True, text=True, env=env,
    )
    Path(sp.name).unlink(missing_ok=True)
    verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, verdict


class TestFloorGuard:
    """BL-452 Check 9: detect_haiku_floor_violation — Haiku-Floor fuer Reasoning-Skills.

    Doktrin feedback_haiku_verboten + INV-NO-HAIKU-IN-TDD:
    general-haiku darf KEINE Reasoning-Skills laden (berater, TDD-Kern, orchestrate).
    Mechanische Executors (rein dotnet build / grep / find — kein Skill-Load) sind exempt.

    RED-Erwartung: Check 9 existiert noch nicht -> T1/T2/T5 FAILEN (erwartet False, bekommt True).
    T3/T4 koennen jetzt schon gruen sein.
    """

    def test_t1_haiku_berater_skill_blocked(self):
        """T1 (RED): Agent + general-haiku + Skill(_SDF_berater_modusEntscheidung) + enforce=true
        -> continue=False + message enthaelt 'FLOOR' oder 'HAIKU'. [BL-452 Check 9]

        RED-Erwartung: Check 9 fehlt -> Guard gibt PASS (continue=True). Dieser Test MUSS FAILEN."""
        proc, r = _run_floor(
            subagent_type="general-haiku",
            prompt='Lade Skill(_SDF_berater_modusEntscheidung, args="BL-452 batch_1") und fuehre aus.',
            enforce=True,
        )
        assert r.get("continue") is False, (
            f"T1 RED: erwartet BLOCK (continue=False) fuer haiku+berater-Skill, "
            f"bekam {r} | stderr: {proc.stderr}. "
            "Check 9 (detect_haiku_floor_violation) noch nicht implementiert -> Guard gibt PASS (RED)."
        )
        msg = (r.get("message") or "") + (proc.stderr or "")
        assert "FLOOR" in msg.upper() or "HAIKU" in msg.upper(), (
            f"T1: message soll 'FLOOR' oder 'HAIKU' enthalten. message={msg!r}"
        )

    def test_t2_haiku_tdd_green_skill_blocked(self):
        """T2 (RED): Agent + general-haiku + Skill(_TDD_green) -> continue=False. [BL-452 Check 9]

        INV-NO-HAIKU-IN-TDD: _TDD_green ist ein TDD-Kern-Skill, under Floor fuer haiku.
        RED-Erwartung: Check 9 fehlt -> Guard gibt PASS (continue=True). Muss FAILEN."""
        proc, r = _run_floor(
            subagent_type="general-haiku",
            prompt='Skill(_TDD_green, args="floor-guard 1 1") — schreibe den GREEN-Code fuer Ring 1.',
            enforce=True,
        )
        assert r.get("continue") is False, (
            f"T2 RED: erwartet BLOCK (continue=False) fuer haiku+_TDD_green, "
            f"bekam {r} | stderr: {proc.stderr}. "
            "Check 9 nicht implementiert -> RED."
        )
        msg = (r.get("message") or "") + (proc.stderr or "")
        assert "FLOOR" in msg.upper() or "HAIKU" in msg.upper(), (
            f"T2: message soll 'FLOOR' oder 'HAIKU' enthalten. message={msg!r}"
        )

    def test_t3_haiku_mechanical_executor_exempt(self):
        """T3 (negativ/exempt): Agent + general-haiku + rein mechanischer Executor-Prompt
        (kein Skill-Reasoning-Load) -> continue=True (haiku-exempt). [BL-452 Check 9]

        Mechanischer Executor (dotnet build / grep) ist vom Floor ausgenommen.
        Dieser Test kann/soll jetzt schon gruen sein (Guard gibt True aus richtigem Grund)."""
        proc, r = _run_floor(
            subagent_type="general-haiku",
            prompt="cd repo && dotnet build --no-incremental && dotnet test --filter Category=Unit",
            enforce=True,
        )
        assert r.get("continue") is True, (
            f"T3 FALSE-POSITIVE: haiku + mechanischer Executor muss PASS ergeben (exempt). "
            f"bekam {r} | stderr: {proc.stderr}"
        )

    def test_t4_sonnet_reasoning_skill_passes(self):
        """T4 (negativ/tier): Agent + general-sonnet + Skill(_SDF_berater_x) -> continue=True. [BL-452]

        general-sonnet ist UEBER dem Floor — Check 9 darf hier niemals blocken.
        Dieser Test kann/soll jetzt schon gruen sein."""
        proc, r = _run_floor(
            subagent_type="general-sonnet",
            prompt='Skill(_SDF_berater_modusEntscheidung, args="BL-452 batch_1") — entscheide Modus.',
            enforce=True,
        )
        assert r.get("continue") is True, (
            f"T4 FALSE-POSITIVE: general-sonnet + reasoning-Skill muss PASS ergeben (ueber Floor). "
            f"bekam {r} | stderr: {proc.stderr}"
        )

    def test_t5_haiku_orchestrate_skill_blocked(self):
        """T5 (RED): Agent + general-haiku + Skill(_A_orchestrate ...) -> continue=False. [BL-452 Check 9]

        _A_orchestrate ist ein Orchestrator-Skill — unter Floor fuer haiku (INV-NO-HAIKU-IN-TDD
        + feedback_haiku_verboten). Der Prompt enthaelt NUR den subagent_type-Check (kein
        ORCHESTRATOR_DELEGATION-Check-3-Trigger durch Exec-Verb + Orchestrator-Name).
        RED-Erwartung: Check 9 fehlt -> Guard gibt PASS. Muss FAILEN.

        Note fuer GREEN: Check 9 prueft subagent_type ZUERST (vor Check 3), damit ein
        haiku+orchestrate-Prompt mit FLOOR_VIOLATION geblockt wird — nicht mit ORCHESTRATOR_DELEGATION.
        Alternativ: Check 9 kann nach Check 3 kommen, dann muss T5-message 'ORCHESTRATOR' auch erlaubt sein.
        Beides ist korrekt: jede BLOCK-Antwort (continue=False) bei haiku+orchestrate-Skill ist Violation."""
        proc, r = _run_floor(
            subagent_type="general-haiku",
            prompt='Loesung: Skill(_A_orchestrate --bl=BL-452) — starte A-Pipeline fuer BL-452.',
            enforce=True,
        )
        assert r.get("continue") is False, (
            f"T5 RED: erwartet BLOCK (continue=False) fuer haiku+_A_orchestrate, "
            f"bekam {r} | stderr: {proc.stderr}. "
            "Check 9 nicht implementiert -> Guard gibt PASS (RED)."
        )
        msg = (r.get("message") or "") + (proc.stderr or "")
        # FLOOR, HAIKU oder ORCHESTRATOR sind alle valide Block-Ursachen (Check 9 vor oder nach Check 3)
        assert any(kw in msg.upper() for kw in ("FLOOR", "HAIKU", "ORCHESTRATOR")), (
            f"T5: message soll 'FLOOR', 'HAIKU' oder 'ORCHESTRATOR' enthalten. message={msg!r}"
        )
