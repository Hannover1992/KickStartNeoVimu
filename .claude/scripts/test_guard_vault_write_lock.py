#!/usr/bin/env python3
"""Tests fuer guard_vault_write_lock.py (BL-334 sub_batch_2, AK-2, Write-Seam).

TDD Stage 1 (Atomic), Modus M3. HookGuard-Mirror #5 — Spiegel von
test_guard_idf_sdf_handoff.py (subprocess + JSON-stdin + tmp-vault + OMNI_*-Env
+ exit-Assertion).

Der Guard ist ein PreToolUse-Hook auf JEDEM Edit/Write. Er BLOCKt (enforce=true) /
WARNt (enforce=false) einen Write UNTER {vault_root}, wenn ein FREMDES non-stale
vault-Heal-Lock aktiv ist (INV-VAULT-LOCK-5). HOECHSTE VORSICHT: fail-open ist
heilig — jeder Bug -> PASS (exit 0), niemals Vault zumauern.

Test-Matrix:
  (a) kein Lock                       -> PASS exit0
  (b) non-vault-Pfad (Engine-Repo)    -> PASS exit0
  (c) Kill-Switch (ALL_OFF / LOCAL)   -> PASS exit0
  (d) self-holder                     -> PASS exit0 (Heiler darf schreiben)
  (e) fremdes Lock + enforce=true     -> BLOCK exit2 + Hint nennt holder+zweck
  (f) fremdes Lock + enforce=false    -> WARN exit0 + Hint im message
  (g) AK-5 2-Session-Stall: acquire(A) -> guard(B) BLOCK; release(A) -> guard(B) PASS
  (h) fail-open: kaputter input / fehlender vault_root -> PASS exit0
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_vault_write_lock.py"

# vault_lock import (zum Lock-Setup im Test); reuse SB1-Modul.
sys.path.insert(0, str(SCRIPT_DIR))
import vault_lock  # noqa: E402


def run_guard(file_path, vault_root=None, worker_id="worker-B",
              enforce=True, kill_switch=None, raw_input=None):
    """Ruft den Guard via subprocess mit einem PreToolUse-Edit-Event auf file_path.

    vault_root   -> VAULT_ROOT env (Pfad-Praefix-Match + _vault.lock-Heimat).
    worker_id    -> OMNI_WORKER_ID env (self-Identitaet).
    enforce      -> schreibt enforceProcess true/false in _session_params.md (OMNI_SESSION_PARAMS).
    kill_switch  -> setzt OMNI_ENFORCE_ALL_OFF / OMNI_VAULT_WRITE_LOCK_OFF.
    raw_input    -> wenn gesetzt: roher stdin-String (fail-open-Test fuer kaputten Input).
    """
    env = os.environ.copy()
    # Defensive: alte Kill-Switches aus der Umgebung entfernen, sonst PASSt jeder Test.
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    env.pop("OMNI_VAULT_WRITE_LOCK_OFF", None)
    if vault_root is not None:
        env["VAULT_ROOT"] = str(vault_root)
    if worker_id is not None:
        env["OMNI_WORKER_ID"] = worker_id
    if kill_switch:
        env[kill_switch] = "1"

    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp_path = sp.name
    env["OMNI_SESSION_PARAMS"] = sp_path

    if raw_input is None:
        event = {"tool_name": "Edit", "tool_input": {"file_path": str(file_path), "new_string": "x"}}
        stdin = json.dumps(event)
    else:
        stdin = raw_input

    proc = subprocess.run([sys.executable, str(GUARD)], input=stdin,
                          capture_output=True, text=True, env=env)
    Path(sp_path).unlink(missing_ok=True)
    verdict = {}
    if proc.stdout.strip():
        try:
            verdict = json.loads(proc.stdout.strip())
        except Exception:
            verdict = {}
    return proc, verdict


def _make_vault():
    """tmp-vault-root (eigenes Verzeichnis -> eigene _vault.lock)."""
    d = tempfile.mkdtemp(prefix="vault_lock_test_")
    return Path(d)


def _vault_file(vault_root):
    """Ein Ziel-Pfad UNTER vault_root (legitimer Vault-Write)."""
    f = vault_root / "Backlog" / "BL-999" / "_manifest.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x", encoding="utf-8")
    return f


# ── (a) kein Lock -> PASS ────────────────────────────────────────────────────
def test_no_lock_passes():
    vr = _make_vault()
    target = _vault_file(vr)
    proc, r = run_guard(target, vault_root=vr, enforce=True)
    assert proc.returncode == 0, f"erwartet exit 0 (kein Lock), war {proc.returncode}; stderr={proc.stderr}"
    assert r.get("continue") is True, "kein Lock -> continue=true erwartet"


# ── (b) non-vault-Pfad (Engine-Repo) -> PASS ─────────────────────────────────
def test_non_vault_path_passes():
    vr = _make_vault()
    # Engine-Repo-Pfad liegt NICHT unter vr -> PASS, selbst wenn ein Lock aktiv ist.
    vault_lock.force_release(vault_root=vr)
    vault_lock.acquire(zweck="health_heal", worker_id="worker-A", ttl=600, vault_root=vr)
    engine_path = SCRIPT_DIR / "guard_idf_sdf_handoff.py"  # Engine-Repo, kein Vault
    proc, r = run_guard(engine_path, vault_root=vr, worker_id="worker-B", enforce=True)
    vault_lock.release(worker_id="worker-A", vault_root=vr)
    assert proc.returncode == 0, f"erwartet exit 0 (non-vault-Pfad), war {proc.returncode}; stderr={proc.stderr}"
    assert r.get("continue") is True, "non-vault-Pfad -> continue=true erwartet"


# ── (c) Kill-Switch -> PASS ──────────────────────────────────────────────────
def test_kill_switch_all_off_passes():
    vr = _make_vault()
    target = _vault_file(vr)
    vault_lock.force_release(vault_root=vr)
    vault_lock.acquire(zweck="health_heal", worker_id="worker-A", ttl=600, vault_root=vr)
    proc, r = run_guard(target, vault_root=vr, worker_id="worker-B", enforce=True,
                        kill_switch="OMNI_ENFORCE_ALL_OFF")
    vault_lock.release(worker_id="worker-A", vault_root=vr)
    assert proc.returncode == 0, f"erwartet exit 0 (ALL_OFF Kill-Switch), war {proc.returncode}"
    assert r.get("continue") is True, "OMNI_ENFORCE_ALL_OFF -> continue=true erwartet"


def test_kill_switch_local_off_passes():
    vr = _make_vault()
    target = _vault_file(vr)
    vault_lock.force_release(vault_root=vr)
    vault_lock.acquire(zweck="health_heal", worker_id="worker-A", ttl=600, vault_root=vr)
    proc, r = run_guard(target, vault_root=vr, worker_id="worker-B", enforce=True,
                        kill_switch="OMNI_VAULT_WRITE_LOCK_OFF")
    vault_lock.release(worker_id="worker-A", vault_root=vr)
    assert proc.returncode == 0, f"erwartet exit 0 (LOCAL Kill-Switch), war {proc.returncode}"
    assert r.get("continue") is True, "OMNI_VAULT_WRITE_LOCK_OFF -> continue=true erwartet"


# ── (d) self-holder -> PASS ──────────────────────────────────────────────────
def test_self_holder_passes():
    vr = _make_vault()
    target = _vault_file(vr)
    vault_lock.force_release(vault_root=vr)
    vault_lock.acquire(zweck="health_heal", worker_id="worker-SELF", ttl=600, vault_root=vr)
    # guard laeuft als DERSELBE worker -> der Heiler darf seinen eigenen Vault schreiben.
    proc, r = run_guard(target, vault_root=vr, worker_id="worker-SELF", enforce=True)
    vault_lock.release(worker_id="worker-SELF", vault_root=vr)
    assert proc.returncode == 0, f"erwartet exit 0 (self-holder darf schreiben), war {proc.returncode}"
    assert r.get("continue") is True, "self-holder -> continue=true erwartet"


# ── (e) fremdes Lock + enforce=true -> BLOCK exit2 + Hint ─────────────────────
def test_foreign_lock_enforce_true_blocks():
    vr = _make_vault()
    target = _vault_file(vr)
    vault_lock.force_release(vault_root=vr)
    vault_lock.acquire(zweck="health_heal", worker_id="worker-A", ttl=600, vault_root=vr)
    proc, r = run_guard(target, vault_root=vr, worker_id="worker-B", enforce=True)
    vault_lock.release(worker_id="worker-A", vault_root=vr)
    assert proc.returncode == 2, f"erwartet exit 2 (BLOCK), war {proc.returncode}; stderr={proc.stderr}"
    msg = r.get("message", "") + proc.stderr
    assert "worker-A" in msg, f"Recovery-Hint muss holder (worker-A) nennen; msg={msg!r}"
    assert "health_heal" in msg, f"Recovery-Hint muss zweck (health_heal) nennen; msg={msg!r}"


# ── (f) fremdes Lock + enforce=false -> WARN exit0 + Hint ─────────────────────
def test_foreign_lock_enforce_false_warns():
    vr = _make_vault()
    target = _vault_file(vr)
    vault_lock.force_release(vault_root=vr)
    vault_lock.acquire(zweck="health_heal", worker_id="worker-A", ttl=600, vault_root=vr)
    proc, r = run_guard(target, vault_root=vr, worker_id="worker-B", enforce=False)
    vault_lock.release(worker_id="worker-A", vault_root=vr)
    assert proc.returncode == 0, f"erwartet exit 0 (enforce=false -> WARN), war {proc.returncode}"
    assert r.get("continue") is True, "enforce=false -> continue=true (WARN-only)"
    assert "worker-A" in r.get("message", ""), "WARN-message muss holder nennen"
    assert "WARN" in r.get("message", "").upper(), "WARN-Markierung muss im message stehen"


# ── (g) AK-5 2-Session-Stall ─────────────────────────────────────────────────
def test_ak5_two_session_stall():
    """acquire(zweck=health_heal, worker=A) -> guard(worker=B, enforce=true) BLOCKt.
    release(A) -> guard(worker=B) PASSt. Belegt das 2-Session-Stall-Primitiv:
    Session B wird gestallt solange A heilt, und frei sobald A released."""
    vr = _make_vault()
    target = _vault_file(vr)
    vault_lock.force_release(vault_root=vr)
    # Session A acquired das Heal-Lock.
    acq = vault_lock.acquire(zweck="health_heal", worker_id="worker-A", ttl=600, vault_root=vr)
    assert acq is True, "Setup: A musste das vault-Lock erwerben"
    # Session B versucht zu schreiben -> BLOCK.
    proc, r = run_guard(target, vault_root=vr, worker_id="worker-B", enforce=True)
    assert proc.returncode == 2, f"Stall: B muss bei aktivem A-Heal blocken (exit 2), war {proc.returncode}"
    # A released.
    rel = vault_lock.release(worker_id="worker-A", vault_root=vr)
    assert rel is True, "Setup: A musste releasen koennen"
    # Session B versucht erneut -> PASS (Lock frei).
    proc2, r2 = run_guard(target, vault_root=vr, worker_id="worker-B", enforce=True)
    assert proc2.returncode == 0, f"nach release(A): B muss passieren (exit 0), war {proc2.returncode}"
    assert r2.get("continue") is True, "nach release(A): continue=true erwartet"


# ── (h) fail-open: kaputter input / fehlender vault_root -> PASS ─────────────
def test_fail_open_broken_input():
    vr = _make_vault()
    proc, r = run_guard(vr / "x.md", vault_root=vr, raw_input="{ this is not json")
    assert proc.returncode == 0, f"fail-open: kaputter stdin -> exit 0, war {proc.returncode}"
    assert r.get("continue") is True, "kaputter input -> continue=true (fail-open)"


def test_fail_open_no_vault_root():
    """vault_root nicht ermittelbar (VAULT_ROOT zeigt ins Nirgendwo / kein Lock-File
    lesbar) -> fail-open PASS. Auch ein Pfad ohne aufloesbares vault_root muss PASSen."""
    # Kein VAULT_ROOT, kein worker_id -> alles unsicher -> fail-open.
    env = os.environ.copy()
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    env.pop("OMNI_VAULT_WRITE_LOCK_OFF", None)
    env.pop("VAULT_ROOT", None)
    env.pop("OMNI_WORKER_ID", None)
    event = {"tool_name": "Edit", "tool_input": {}}  # kein file_path
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, f"fail-open: fehlender file_path/vault_root -> exit 0, war {proc.returncode}"
    r = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    assert r.get("continue") is True, "fehlender file_path -> continue=true (fail-open)"


def test_non_edit_write_tool_passes():
    """Nicht-Edit/Write-Tool (z.B. Read) -> PASS (Guard ist nur fuer Write-Seam)."""
    vr = _make_vault()
    env = os.environ.copy()
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    env.pop("OMNI_VAULT_WRITE_LOCK_OFF", None)
    event = {"tool_name": "Read", "tool_input": {"file_path": str(vr / "x.md")}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    assert proc.returncode == 0, f"Nicht-Write-Tool -> exit 0, war {proc.returncode}"


if __name__ == "__main__":
    tests = [
        test_no_lock_passes,
        test_non_vault_path_passes,
        test_kill_switch_all_off_passes,
        test_kill_switch_local_off_passes,
        test_self_holder_passes,
        test_foreign_lock_enforce_true_blocks,
        test_foreign_lock_enforce_false_warns,
        test_ak5_two_session_stall,
        test_fail_open_broken_input,
        test_fail_open_no_vault_root,
        test_non_edit_write_tool_passes,
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
    print(f"\n=== {passed}/{passed+failed} ===")
    sys.exit(0 if failed == 0 else 1)
