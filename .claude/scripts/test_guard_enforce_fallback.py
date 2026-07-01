#!/usr/bin/env python3
"""Tests fuer guard_stage_seam_handoff.py enforce/hil-Fallback (BL-343 / PL-343-2).

TDD Stage 1 (Atomic), Modus M3. Additiv zu test_guard_stage_seam_handoff.py — KEINE
bestehende Assert beruehrt. Schliesst die env-Defect-Wurzel: read_enforce()/read_hil()
lesen heute AUSSCHLIESSLICH os.environ['OMNI_SESSION_PARAMS']. Fehlt diese env (der
Normalfall in der Maschine — der Guard wird vom Harness ohne gesetztes
OMNI_SESSION_PARAMS gerufen), faellt der Guard auf seinen BLOCK-Default zurueck und
blockiert AUCH dann, wenn der Session-State self-resolvbar `enforceProcess: false`
saegt. Das ist die "korrekter-Block-stallt-Prozess"-Fehlerklasse (Maschine-nicht-Context).

GOLD-CONTRACT B (PL-343-2):
  GREEN-Fix: read_enforce()/read_hil() delegieren — wenn OMNI_SESSION_PARAMS-env ABSENT
  ist — auf session_params_resolver.resolve_param('enforceProcess'/'hil') (lazy-import;
  Resolver-Fehler -> heutiger BLOCK-Default als fail-safe). Der env-PRESENT-Pfad bleibt
  UNVERAENDERT (Bestands-Verhalten der 4 test_guard_stage_seam_handoff.py-Tests intakt).
  Empfehlung: ein gemeinsamer Helper (z.B. session_params_resolver.read_enforce_with_fallback)
  statt N-fach copy-paste (Geschwister-Guards idf_sdf/redeploy_health/a_idf/geist9b/
  param_writer teilen die read_enforce-Klasse — Sibling-Wiring = Folge-Scope, hier nur
  guard_stage_seam + Helper).

Isolation (PFLICHT): KEIN echtes Vault/Session-IO. Der self-resolvbare State wird ueber
OMNI_VAULT_ROOT auf ein tmp-Verzeichnis mit EINER _session_defaults.md gepinnt; der
Resolver (session_params_resolver._find_vault_root) honoriert OMNI_VAULT_ROOT VOR der
hardcoded Heuristik -> es wird NIE das echte Vault gelesen. OMNI_SESSION_PARAMS wird im
RED/GREEN-Kern bewusst aus der env ENTFERNT (env-absent-Pfad).

RED-Beweis (heute): read_enforce() ignoriert den self-resolvbaren State, faellt auf
BLOCK-Default -> Guard blockt (exit 2 / continue:false) trotz enforceProcess:false. Die
Erwartung (WARN: exit 0 / continue:true) FAILT -> RED. GREEN = naechster Worker
(read_enforce/read_hil-Fallback-Wiring).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_stage_seam_handoff.py"

# Stage-/Batch-Ende-Progression (Seam-Skip-Lage, 1:1 wie test_guard_stage_seam_handoff.py).
SEAM_MANIFEST = (
    "DF_BATCH_STATE:\n"
    "  stage_done: true\n"
    '  completed_sub_batches: ["SB-enforcefallback"]\n'
    "- [x] BL-343-PL-343-2 (Stage 1 GREEN, commit)\n"
)
# audit: Stage-GREEN (_I_orchestrate-Ende) ABER KEIN _stage_orchestrate seither -> Seam-Skip.
SEAM_AUDIT = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]


def _write_tmp_vault(enforce: bool, hil: str = "off") -> Path:
    """Tmp-'Vault' mit EINER _session_defaults.md (self-resolvbar via OMNI_VAULT_ROOT).

    KEIN echtes Vault-IO: der Resolver honoriert OMNI_VAULT_ROOT vor der Heuristik.
    """
    d = Path(tempfile.mkdtemp(prefix="omni_enforce_fallback_"))
    (d / "_session_defaults.md").write_text(
        f"**enforceProcess:** {'true' if enforce else 'false'}\n**HiL:** {hil}\n",
        encoding="utf-8",
    )
    return d


def _run_guard(manifest_text, audit_lines, *, session_params_env=None,
               vault_root=None):
    """Ruft den Guard via subprocess (PreToolUse-Edit auf _manifest.md).

    session_params_env=None  -> OMNI_SESSION_PARAMS wird aus der env ENTFERNT (env-absent).
    session_params_env=<path>-> OMNI_SESSION_PARAMS = <path> (env-present, Bestands-Pfad).
    vault_root=<path>        -> OMNI_VAULT_ROOT = <path> (self-resolvbarer Session-State).

    Gibt (proc, verdikt_json) zurueck. Saeubert die tmp-Dateien.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix="_manifest.md", delete=False,
                                     encoding="utf-8") as mf:
        mf.write(manifest_text)
        manifest_path = mf.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False,
                                     encoding="utf-8") as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name

    env = os.environ.copy()
    env["OMNI_STAGE_SEAM_AUDIT"] = audit_path
    # env-absent-Pfad: OMNI_SESSION_PARAMS MUSS weg (sonst greift der Bestands-Pfad).
    if session_params_env is None:
        env.pop("OMNI_SESSION_PARAMS", None)
    else:
        env["OMNI_SESSION_PARAMS"] = str(session_params_env)
    if vault_root is not None:
        env["OMNI_VAULT_ROOT"] = str(vault_root)

    event = {"tool_name": "Edit",
             "tool_input": {"file_path": manifest_path, "new_string": manifest_text}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(manifest_path).unlink(missing_ok=True)
    Path(audit_path).unlink(missing_ok=True)
    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


def test_env_absent_enforce_false_self_resolved_warns():
    """RED-Kern (PL-343-2): OMNI_SESSION_PARAMS env ABSENT, ABER self-resolvbar
    enforceProcess:false (tmp-Vault via OMNI_VAULT_ROOT). Seam-Skip-Lage (Stage-Ende
    ohne _stage_orchestrate seit Stage-GREEN), hil=off.

    Erwartung GREEN: read_enforce() delegiert auf den Resolver -> enforceProcess==False
    -> der Guard feuert als WARN (exit 0, continue:true), NICHT als Block.
    RED heute: env-absent -> read_enforce() BLOCK-Default (True) -> exit 2 / continue:false
    -> diese Asserts FAILEN (kein echtes Vault/env-IO: alles tmp + gepinnt)."""
    vault = _write_tmp_vault(enforce=False, hil="off")
    try:
        proc, r = _run_guard(SEAM_MANIFEST, SEAM_AUDIT,
                             session_params_env=None, vault_root=vault)
    finally:
        (vault / "_session_defaults.md").unlink(missing_ok=True)
        vault.rmdir()
    assert proc.returncode == 0, (
        f"erwartet exit 0 (env-absent + self-resolved enforceProcess=false -> WARN), "
        f"war {proc.returncode} (stdout={proc.stdout!r})"
    )
    assert r.get("continue") is True, (
        "env-absent + self-resolved enforceProcess=false muss continue=true setzen "
        f"(WARN-only, kein Block), war {r!r}"
    )
    assert "Skill(_stage_orchestrate" in r.get("message", ""), (
        "Recovery-Hint muss auch im WARN-Pfad im message stehen"
    )
    assert "WARN" in r.get("message", "").upper(), (
        "WARN-Markierung muss im message-Text stehen (enforceProcess=false -> WARNED)"
    )


def test_env_present_enforce_false_still_warns():
    """ZUSATZ (Bestands-Verhalten unveraendert): env-PRESENT mit enforceProcess:false
    (OMNI_SESSION_PARAMS gesetzt) -> weiterhin WARN (exit 0, continue:true). Belegt: der
    GREEN-Fix aendert NUR den env-absent-Zweig; der env-present-Pfad (der die 4
    Bestands-Tests in test_guard_stage_seam_handoff.py traegt) bleibt byte-gleich.

    (Heute schon WARN — dieser Test ist die Regressions-Wache fuer den env-present-Pfad,
    nicht der RED-Beweis. Er darf NIE roetlich werden, weder vor noch nach GREEN.)"""
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md",
                                     delete=False, encoding="utf-8") as sp:
        sp.write("**enforceProcess:** false\n**HiL:** off\n")
        sp_path = sp.name
    try:
        proc, r = _run_guard(SEAM_MANIFEST, SEAM_AUDIT,
                             session_params_env=sp_path, vault_root=None)
    finally:
        Path(sp_path).unlink(missing_ok=True)
    assert proc.returncode == 0, (
        f"env-present enforceProcess=false -> WARN (exit 0), war {proc.returncode}"
    )
    assert r.get("continue") is True, (
        "env-present enforceProcess=false muss continue=true setzen (WARN-only)"
    )
    assert "Skill(_stage_orchestrate" in r.get("message", ""), (
        "Recovery-Hint muss im WARN-message stehen (env-present-Pfad unveraendert)"
    )


if __name__ == "__main__":
    tests = [
        test_env_absent_enforce_false_self_resolved_warns,
        test_env_present_enforce_false_still_warns,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed + failed} ===")
    sys.exit(0 if failed == 0 else 1)
