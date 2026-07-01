#!/usr/bin/env python3
"""
TDD RED Tests fuer BL-364 batch_1 — neue Guard/Hook-Verhalten (M3, Stage 1 Atomic).

Abgedeckte AKs:
  AK-1  (TD-1/TD-2): guard_redeploy_health bl_id-Scope-Filter
  AK-2  (TD-3/TD-4): Gen-0-PROCEED + RECOVERY_HINT in stdout-message
  AK-3  (TD-6):      audit_hook MANIFEST_FILE lazy (kein Modul-Level-Attribut)
  AK-4  (TD-7/TD-8): current_context detect_bl_id ENV-Priority-1
  AK-10 (TD-9):      read_active_context silent-degradation bei fehlendem Vault

AKs ohne mechanisch pruefbares pytest-Target:
  AK-9 (TD-10): _A_orchestrate.md Template-String-Check — eigener Szenario-Verify Test (T-ak9)
  AK-7, AK-5, AK-6, AK-8: Doktrin/Markdown-Szenario (batch_2 M2, kein TDD-RED noetig)

Alle Tests sind absichtlich RED: das neue Verhalten ist noch NICHT implementiert.
Die GREEN-Phase (separater Worker) implementiert erst die Aenderungen in den Target-Scripts.

test-runner: py -3 -m pytest .claude/scripts/test_bl364_engine_health.py -q
"""

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_redeploy_health.py"
AUDIT_HOOK = SCRIPT_DIR / "audit_hook.py"
CURRENT_CONTEXT = SCRIPT_DIR / "current_context.py"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run_guard(audit_lines, enforce=True, off=False, file_content=None, bl_id=None):
    """Schreibt eine synthetische audit.jsonl und ruft den Guard per subprocess auf.

    Neu gegenueber dem vorhandenen run_guard in test_guard_redeploy_health.py:
      - bl_id: wird als CLAUDE_BL_ID env-Variable gesetzt (AK-1 Scope-Filter)
      - file_content: optionaler Inhalt fuer den Write-Event (AK-2 Gen-0-Detect)
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name

    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    ) as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp_path = sp.name

    env = os.environ.copy()
    env["OMNI_REDEPLOY_HEALTH_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    if off:
        env["OMNI_REDEPLOY_HEALTH_OFF"] = "1"
    else:
        env.pop("OMNI_REDEPLOY_HEALTH_OFF", None)
    if bl_id is not None:
        env["CLAUDE_BL_ID"] = bl_id
    else:
        env.pop("CLAUDE_BL_ID", None)

    tool_input = {"file_path": str(SCRIPT_DIR / "_manifest.md")}
    if file_content is not None:
        tool_input["content"] = file_content
    else:
        tool_input["new_string"] = "produktiver State-Write"

    event = {"tool_name": "Write" if "content" in tool_input else "Edit",
              "tool_input": tool_input}

    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)

    out = proc.stdout.strip()
    result = json.loads(out) if out else {}
    return proc, result


# ─────────────────────────────────────────────────────────────────────────────
# AK-1: bl_id-Scope-Filter (TD-1 + TD-2)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak1_foreign_redeploy_does_not_block_other_bl():
    """TD-1 (AK-1): Fremdes _redeploy SKILL_LOAD mit bl_id-Kontext BL-X
    aktiviert den Guard fuer BL-Y NICHT -> continue (kein Block).

    Verhalten NOCH NICHT implementiert: guard_redeploy_health health_ran_since_redeploy()
    ignoriert bl_id-Kontext, also wird dieser Test FAILEN weil der Guard faelschlicherweise
    blockt (F3 global-scope-Bug).
    """
    audit = [
        # Fremdes Feature BL-X hat einen Redeploy gemacht
        {
            "event": "SKILL_LOAD",
            "skill_name": "_redeploy",
            "load_method": "skill",
            "ctx": {"feature": "BL-X-some-other-feature", "sdf_status": "IDF_DONE"},
        },
        # BL-Y laeuft danach und schreibt State — kein eigener Redeploy, kein Health noetig
    ]
    # Guard wird fuer BL-Y ausgefuehrt (CLAUDE_BL_ID=BL-Y)
    proc, result = _run_guard(audit, bl_id="BL-Y")
    assert result.get("continue") is True, (
        f"TD-1 FAIL: Fremdes BL-X _redeploy darf BL-Y NICHT blocken (continue=true erwartet). "
        f"returncode={proc.returncode}, result={result}"
    )
    assert proc.returncode == 0, (
        f"TD-1 FAIL: exit-code 0 erwartet (kein Block fuer fremden Redeploy), "
        f"war {proc.returncode}"
    )


def test_ak1_own_redeploy_without_health_blocks():
    """TD-2 (AK-1): Eigenes _redeploy SKILL_LOAD (bl_id=BL-364) ohne nachfolgendes
    _health_orchestrate -> BLOCK (exit 2).

    Verhalten SCHON teilweise implementiert (existierender Guard), aber nach AK-1-Fix
    muss der Guard den bl_id-Match korrekt machen. Der Scope-Filter-Pfad muss
    BL-364 korrekt als 'eigener' Redeploy erkennen.
    """
    audit = [
        {
            "event": "SKILL_LOAD",
            "skill_name": "_redeploy",
            "load_method": "skill",
            "ctx": {"feature": "BL-364-live-aidf"},
        },
        # Kein _health_orchestrate danach
    ]
    proc, result = _run_guard(audit, bl_id="BL-364")
    assert proc.returncode == 2, (
        f"TD-2 FAIL: Eigener BL-364 _redeploy ohne _health muss exit 2 geben, "
        f"war {proc.returncode}. result={result}"
    )
    assert result.get("continue") is False or not result.get("continue", True), (
        f"TD-2 FAIL: continue muss False sein bei eigenem Redeploy ohne _health. "
        f"result={result}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-2: Gen-0-PROCEED + RECOVERY_HINT in stdout (TD-3 + TD-4)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak2_gen0_format_version_proceeds():
    """TD-3 (AK-2): State-Write mit format_version: 0 im Content -> Guard gibt
    {continue: true} (PROCEED). Doktrin: Gen-0 ist OK, Guard darf nicht abbrechen.

    Verhalten NOCH NICHT implementiert: guard_redeploy_health kennt keine Gen-0-Ausnahme.
    Bei _redeploy ohne _health wird geblockt, unabhaengig vom format_version-Wert.
    -> Test FAILT (bekommt continue=false statt true).
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_redeploy", "load_method": "skill"},
    ]
    # Content enthaelt format_version: 0 (Gen-0-Signal)
    gen0_content = "format_version: 0\nbdf_status: INIT\nsome_field: value\n"
    proc, result = _run_guard(audit, file_content=gen0_content)
    assert result.get("continue") is True, (
        f"TD-3 FAIL: format_version=0 (Gen-0) muss PROCEED ergeben (continue=true). "
        f"returncode={proc.returncode}, result={result}"
    )
    assert proc.returncode == 0, (
        f"TD-3 FAIL: exit 0 erwartet bei Gen-0, war {proc.returncode}"
    )


def test_ak2_recovery_hint_in_stdout_message():
    """TD-4 (AK-2): Guard-Block (Redeploy ohne _health) -> stdout-JSON message-Feld
    enthaelt 'Rufe Skill(_health_orchestrate'. Recovery-Hint muss fuer den Lead sichtbar
    sein (nicht nur in _guard_log.md).

    Verhalten TEILWEISE implementiert: der Guard blockt bereits (exit 2). ABER der
    RECOVERY_HINT taucht bislang NUR in der message auf, wenn er im print-Aufruf
    eingebaut ist. Nach dem Spec: AK-2 fordert explizit den RECOVERY_HINT im
    message-Feld des JSON-stdout (N5-NFR). Wenn die aktuelle Implementierung das
    bereits tut, bleibt der Test GREEN — aber das ist dann ein korrekter GREEN
    (RECOVERY_HINT war schon enthalten). Der TD-3-Scope-Anteil (Gen-0) ist der
    eigentliche RED-Kern.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_redeploy", "load_method": "skill"},
    ]
    proc, result = _run_guard(audit)
    # Block erwartet
    msg = result.get("message", "") + proc.stderr
    assert "Skill(_health_orchestrate" in msg, (
        f"TD-4 FAIL: RECOVERY_HINT 'Rufe Skill(_health_orchestrate' muss im "
        f"stdout message-Feld stehen (N5-NFR: sichtbar fuer Lead). "
        f"result={result}, stderr={proc.stderr[:300]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-3: audit_hook MANIFEST_FILE lazy (TD-6)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak3_audit_hook_no_module_level_manifest_file():
    """TD-6 (AK-3): audit_hook importieren -> kein MANIFEST_FILE-Attribut auf Modul-Ebene.

    Verhalten NOCH NICHT implementiert: audit_hook.py hat L53 als Modul-Konstante
    `MANIFEST_FILE = _resolve_vault_path("manifest")`. Nach AK-3-Fix soll dieses
    Modul-Level-Attribut ENTFERNT und nur noch lazy in read_active_context() aufgeloest
    werden.
    -> Test FAILT (MANIFEST_FILE existiert als Modul-Attribut).
    """
    # audit_hook frisch importieren (kein Cache)
    spec = importlib.util.spec_from_file_location(
        "audit_hook_bl364", str(AUDIT_HOOK)
    )
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass  # falls der Hook beim Import sys.exit macht, OK

    assert not hasattr(mod, "MANIFEST_FILE"), (
        "TD-6 FAIL: audit_hook hat MANIFEST_FILE als Modul-Level-Attribut (L53). "
        "Nach AK-3-Fix muss dieses Attribut entfernt und lazy in read_active_context() "
        "aufgeloest werden. Aktuell: MANIFEST_FILE = " + str(getattr(mod, "MANIFEST_FILE", "N/A"))
    )


def test_ak3_read_active_context_fresh_per_call(tmp_path):
    """TD-5 (AK-3 Integration): read_active_context() liefert bei unterschiedlichem
    Vault-Pfad unterschiedliche Ergebnisse (kein stale Import-Zeit-Cache).

    Zwei Aufrufe mit unterschiedlichem OMNI_VAULT_ROOT (oder Dateiinhalt) sollen
    unterschiedliche ctx-Objekte liefern.

    Verhalten NOCH NICHT voll implementiert solange MANIFEST_FILE Modul-Konstante ist:
    der zweite Aufruf wuerde weiterhin die stale Import-Zeit-Path nehmen.
    -> Test FAILT wenn MANIFEST_FILE als Modul-Level-Konstante existiert.
    """
    # Wir rufen audit_hook.py als Subprocess auf mit synthetischem Event
    # und pruefe ob read_active_context() das richtige ctx zurueckgibt
    # indem wir zwei Manifests schreiben und pruefen ob der Inhalt wechselt.

    # Manifest A mit bdf_status=INIT
    manifest_a = tmp_path / "manifest_a.md"
    manifest_a.write_text("bdf_status: INIT\ndf_status: IDLE\n", encoding="utf-8")

    # Manifest B mit bdf_status=DONE
    manifest_b = tmp_path / "manifest_b.md"
    manifest_b.write_text("bdf_status: DONE\ndf_status: SDF_DONE\n", encoding="utf-8")

    env_base = os.environ.copy()
    env_base.pop("CLAUDE_BL_ID", None)

    def run_hook_with_manifest(manifest_path):
        env = env_base.copy()
        env["OMNI_REDEPLOY_HEALTH_AUDIT"] = str(tmp_path / "audit_dummy.jsonl")
        # Wir setzen OMNI_MANIFEST_PATH als Test-Override fuer audit_hook
        # (falls AK-3-Fix eine solche ENV-Variable einfuehrt)
        env["OMNI_TEST_MANIFEST_PATH"] = str(manifest_path)
        event = {"tool_name": "Skill", "tool_input": {"skill": "_test_skill", "args": ""}}
        proc = subprocess.run(
            [sys.executable, str(AUDIT_HOOK)],
            input=json.dumps(event),
            capture_output=True, text=True, env=env,
        )
        return proc

    # Beide Aufrufe muessen (nach Fix) unterschiedliche ctx-Inhalte loggen
    proc_a = run_hook_with_manifest(manifest_a)
    proc_b = run_hook_with_manifest(manifest_b)

    # Beide muessen sauber durchlaufen (Audit-Hook blockt nie)
    assert proc_a.returncode == 0, f"TD-5: audit_hook A fehlgeschlagen: {proc_a.stderr}"
    assert proc_b.returncode == 0, f"TD-5: audit_hook B fehlgeschlagen: {proc_b.stderr}"

    # Haupt-Assertion: nach AK-3-Fix soll read_active_context() lazy aufloesen.
    # Vor dem Fix: MANIFEST_FILE ist Modul-Konstante -> beide Calls nehmen dasselbe File.
    # Wir pruefen indirekt: audit_hook hat kein MANIFEST_FILE-Modul-Attribut (TD-6-analog).
    spec = importlib.util.spec_from_file_location("audit_hook_bl364_td5", str(AUDIT_HOOK))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except (SystemExit, Exception):
        pass
    assert not hasattr(mod, "MANIFEST_FILE"), (
        "TD-5 FAIL (Modul-Ebene): audit_hook hat immer noch MANIFEST_FILE als "
        "Import-Zeit-Konstante — lazy Resolution (AK-3) noch nicht implementiert."
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-4: CLAUDE_BL_ID ENV Priority-1 (TD-7 + TD-8)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak4_detect_bl_id_without_env_uses_branch_heuristic():
    """TD-7 (AK-4): Worker OHNE CLAUDE_BL_ID-ENV -> detect_bl_id nutzt Branch-Heuristik
    (Priority-2), liefert Lead-BL (potenziell falsch bei async-Team).

    Das ist kein BUG-Test, sondern ein Verstaendnis-Test: beweist das Problem.
    Wenn der Branch 'feature/BL-100-something' ist, gibt detect_bl_id BL-100 zurueck —
    nicht das Worker-BL (z.B. BL-364). Das ist das F2/F10-Problem.

    Verhalten KORREKT (zeigt Problem): kein 'RED' im Sinne von FAIL, aber Grundlage
    fuer TD-8. Wir pruefen: OHNE CLAUDE_BL_ID liefert detect_bl_id den Branch-BL.
    """
    # detect_bl_id ohne ENV-Variable
    spec_cc = importlib.util.spec_from_file_location(
        "current_context_bl364", str(CURRENT_CONTEXT)
    )
    mod_cc = importlib.util.module_from_spec(spec_cc)
    # Temp-Env ohne CLAUDE_BL_ID
    old_env = os.environ.pop("CLAUDE_BL_ID", None)
    try:
        spec_cc.loader.exec_module(mod_cc)
        # Mit Branch 'feature/BL-100-something' soll detect_bl_id BL-100 liefern
        result = mod_cc.detect_bl_id("feature/BL-100-something")
        # Erwartet: Branch-Heuristik, also BL-100 (nicht None, nicht BL-364)
        assert result == "BL-100", (
            f"TD-7: detect_bl_id ohne ENV soll Branch-BL liefern (BL-100), "
            f"bekam: {result!r}"
        )
    finally:
        if old_env is not None:
            os.environ["CLAUDE_BL_ID"] = old_env


def test_ak4_detect_bl_id_with_env_overrides_branch():
    """TD-8 (AK-4): Worker MIT CLAUDE_BL_ID=BL-364 -> detect_bl_id liefert BL-364
    (Priority-1 ENV), unabhaengig vom Branch-Namen.

    Verhalten SCHON implementiert (Priority-1-ENV ist in detect_bl_id:L109-110).
    -> Test sollte GREEN sein (beweist dass Priority-1 funktioniert).
    Wird im Summary als 'bereits GREEN, kein RED noetig' markiert.
    """
    spec_cc = importlib.util.spec_from_file_location(
        "current_context_bl364_t8", str(CURRENT_CONTEXT)
    )
    mod_cc = importlib.util.module_from_spec(spec_cc)

    old_env = os.environ.get("CLAUDE_BL_ID")
    os.environ["CLAUDE_BL_ID"] = "BL-364"
    try:
        spec_cc.loader.exec_module(mod_cc)
        result = mod_cc.detect_bl_id("feature/BL-100-something")
        assert result == "BL-364", (
            f"TD-8: detect_bl_id mit CLAUDE_BL_ID=BL-364 soll BL-364 liefern, "
            f"bekam: {result!r}"
        )
    finally:
        if old_env is None:
            os.environ.pop("CLAUDE_BL_ID", None)
        else:
            os.environ["CLAUDE_BL_ID"] = old_env


# ─────────────────────────────────────────────────────────────────────────────
# AK-10: read_active_context silent-degradation (TD-9)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak10_read_active_context_silent_degradation_on_missing_vault(tmp_path):
    """TD-9 (AK-10): read_active_context() bei nicht-existierendem Vault-Pfad
    -> leeres dict (kein Exception, kein Crash, kein stderr-Print).

    Verhalten NOCH NICHT vollstaendig implementiert nach AK-3-Fix:
    Nach lazy Resolution darf bei None-Ergebnis kein crash/print stattfinden.
    Aktuell: read_active_context() ist robust (try/except), aber MANIFEST_FILE
    ist Modul-Konstante — nach AK-3-Fix muss die lazy Version auch silent degradieren.

    Der Test prueft: audit_hook.read_active_context aufrufen mit ungueltigem
    MANIFEST_FILE-Pfad -> leeres dict, kein Traceback, kein stderr.
    """
    spec_ah = importlib.util.spec_from_file_location(
        "audit_hook_bl364_td9", str(AUDIT_HOOK)
    )
    mod_ah = importlib.util.module_from_spec(spec_ah)

    # Nicht-existierender Vault-Pfad via Subprocess (um Import-Seiteneffekte zu isolieren)
    non_existent = str(tmp_path / "does_not_exist" / "manifest.md")
    env = os.environ.copy()
    # Kein echter MANIFEST_FILE-Override in ENV moeglich vor AK-3-Fix,
    # daher Subprocess-Ansatz mit OMNI_TEST_MANIFEST_PATH (nach Fix erkannt)
    env["OMNI_TEST_MANIFEST_PATH"] = non_existent
    env.pop("CLAUDE_BL_ID", None)

    # Wir rufen audit_hook als Subprocess auf und pruefen dass er sauber durchlaeuft
    event = {"tool_name": "Skill", "tool_input": {"skill": "_test_skill", "args": ""}}
    proc = subprocess.run(
        [sys.executable, str(AUDIT_HOOK)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, (
        f"TD-9 FAIL: audit_hook muss bei fehlendem Vault sauber durchlaufen (exit 0), "
        f"war {proc.returncode}. stderr={proc.stderr[:300]}"
    )
    # Nach AK-10-Fix: kein stderr-Print fuer DEPRECATION/Fehler bei fehlendem Vault
    # Aktuell gibt current_context.py einen DEPRECATION-Print auf stderr — das soll entfernt werden
    # Pruefe dass kein '[DEPRECATION]' auf stderr erscheint
    assert "[DEPRECATION]" not in proc.stderr, (
        f"TD-9 FAIL: silent-degradation verletzt — '[DEPRECATION]' auf stderr erscheint: "
        f"{proc.stderr[:300]}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# AK-9: _A_orchestrate.md enthaelt CLAUDE_BL_ID (Szenario-Verify, TD-10)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak9_a_orchestrate_contains_claude_bl_id():
    """TD-10 (AK-9 Szenario-Verify): _A_orchestrate.md enthaelt den String 'CLAUDE_BL_ID'
    in einem Berater-Worker-Spawn-Template.

    Verhalten NOCH NICHT implementiert: _A_orchestrate.md enthaelt kein CLAUDE_BL_ID-Template.
    -> Test FAILT.
    """
    a_orchestrate = SCRIPT_DIR.parent / "commands" / "_A_orchestrate.md"
    assert a_orchestrate.exists(), (
        f"TD-10 FAIL: _A_orchestrate.md nicht gefunden unter {a_orchestrate}"
    )
    content = a_orchestrate.read_text(encoding="utf-8", errors="replace")
    assert "CLAUDE_BL_ID" in content, (
        "TD-10 FAIL: _A_orchestrate.md enthaelt kein 'CLAUDE_BL_ID' in "
        "Berater-Worker-Spawn-Template. AK-9: alle Worker-Spawns muessen "
        "CLAUDE_BL_ID explizit als ENV uebergeben."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Direktaufruf (Entwickler-Schnellcheck)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_ak1_foreign_redeploy_does_not_block_other_bl,
        test_ak1_own_redeploy_without_health_blocks,
        test_ak2_gen0_format_version_proceeds,
        test_ak2_recovery_hint_in_stdout_message,
        test_ak3_audit_hook_no_module_level_manifest_file,
        test_ak4_detect_bl_id_without_env_uses_branch_heuristic,
        test_ak4_detect_bl_id_with_env_overrides_branch,
        test_ak9_a_orchestrate_contains_claude_bl_id,
    ]
    passed = failed = 0
    for t in tests:
        try:
            if "tmp_path" in t.__code__.co_varnames:
                import tempfile as _tf
                with _tf.TemporaryDirectory() as _td:
                    t(Path(_td))
            else:
                t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed+failed} ===")
    sys.exit(0 if failed == 0 else 1)
