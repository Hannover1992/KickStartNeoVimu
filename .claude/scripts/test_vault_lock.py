"""
test_vault_lock.py — BL-334 sub_batch_1: Tests for vault_lock.py (RED-first TDD)

vault_lock.py is a THIN wrapper over factory_lock.py that points at a separate
{vault_root}/_vault.lock file (scope="vault"), zweck-tagged ({health_heal, wave_fanin}).
Mechanism (os.replace atomicity, stale/TTL, heartbeat, reclaim+audit, HeartbeatDaemon)
is REUSED from factory_lock — NOT re-implemented (INV-VAULT-LOCK-6, No-5th-Lock-Machine).

Run: py -3 -m pytest .claude/scripts/test_vault_lock.py -v
"""

import time
import threading
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent))

import vault_lock as vl
import factory_lock as fl


@pytest.fixture
def tmp_vault(tmp_path):
    """Provide a temporary vault root for isolation."""
    return tmp_path


@pytest.fixture(autouse=True)
def patch_vault(tmp_vault, monkeypatch):
    """Patch VAULT_ROOT in both modules + no-op audit (side-effect free)."""
    monkeypatch.setattr(fl, "VAULT_ROOT", tmp_vault)
    monkeypatch.setattr(vl, "VAULT_ROOT", tmp_vault)
    monkeypatch.setattr(fl, "_emit_audit", lambda *a, **kw: None)
    yield


# ─── Test (a): acquire writes _vault.lock with holder/zweck/ttl/heartbeat ──────

def test_acquire_writes_vault_lock_file(tmp_vault):
    """acquire() creates a SEPARATE _vault.lock file (NOT _factory_lock.md)
    with holder/zweck(purpose)/ttl/heartbeat fields and scope='vault'."""
    ok = vl.acquire(zweck="health_heal", ttl=600, worker_id="heal-1",
                    timeout=0, vault_root=tmp_vault)
    assert ok is True

    vault_lock_path = vl._vault_lock_file_path(tmp_vault)
    assert vault_lock_path.name == "_vault.lock"
    assert vault_lock_path.exists()

    # factory_lock's own file must NOT be touched (separate file = INV-VAULT-LOCK-6)
    factory_lock_path = tmp_vault / fl.LOCK_FILE_NAME
    assert not factory_lock_path.exists()

    fm, _ = fl._read_lock(vault_lock_path)
    assert fm["holder"] == "heal-1"
    assert fm["scope"] == "vault"
    assert fm["purpose"] == "health_heal"   # zweck -> purpose field
    assert fm["ttl_seconds"] == 600
    assert "heartbeat_at" in fm


# ─── Test (b): is_locked detects a foreign lock ───────────────────────────────

def test_is_locked_detects_foreign_lock(tmp_vault):
    """is_locked() returns holder info dict when a lock is active."""
    assert vl.is_locked(vault_root=tmp_vault) is None
    vl.acquire(zweck="wave_fanin", worker_id="wave-A", timeout=0, vault_root=tmp_vault)
    info = vl.is_locked(vault_root=tmp_vault)
    assert info is not None
    assert info["holder"] == "wave-A"
    assert info["scope"] == "vault"
    assert info["purpose"] == "wave_fanin"


# ─── Test (c): release removes/frees the lock ─────────────────────────────────

def test_release_frees_lock(tmp_vault):
    """release() by the holder frees the vault lock."""
    vl.acquire(zweck="health_heal", worker_id="heal-1", timeout=0, vault_root=tmp_vault)
    assert vl.is_locked(vault_root=tmp_vault) is not None
    ok = vl.release(worker_id="heal-1", vault_root=tmp_vault)
    assert ok is True
    assert vl.is_locked(vault_root=tmp_vault) is None


# ─── Test (d): stale-detection (TTL expired -> safe-break) ────────────────────

def test_stale_lock_safe_break(tmp_vault):
    """A vault lock with ttl=1 becomes stale after 1.5s; a new acquire wins
    (stale safe-break inherited from factory_lock, INV-LOCK-2)."""
    vl.acquire(zweck="health_heal", ttl=1, worker_id="heal-old", timeout=0, vault_root=tmp_vault)
    time.sleep(1.5)
    # stale lock is treated as unlocked
    assert vl.is_locked(vault_root=tmp_vault) is None
    ok = vl.acquire(zweck="wave_fanin", ttl=300, worker_id="heal-new", timeout=0, vault_root=tmp_vault)
    assert ok is True
    info = vl.is_locked(vault_root=tmp_vault)
    assert info is not None
    assert info["holder"] == "heal-new"


# ─── Test (e): zweck-validation (closed vocabulary, fail-loud) ────────────────

def test_zweck_validation_accepts_known(tmp_vault):
    """Known zweck values health_heal + wave_fanin are accepted."""
    assert vl.acquire(zweck="health_heal", worker_id="w1", timeout=0, vault_root=tmp_vault) is True
    vl.release(worker_id="w1", vault_root=tmp_vault)
    assert vl.acquire(zweck="wave_fanin", worker_id="w2", timeout=0, vault_root=tmp_vault) is True


def test_zweck_validation_rejects_unknown(tmp_vault):
    """An unknown zweck raises ValueError (fail-loud, AK-4 closed set)."""
    with pytest.raises(ValueError):
        vl.acquire(zweck="garbage", worker_id="w1", timeout=0, vault_root=tmp_vault)
    # no lock was created on rejection
    assert vl.is_locked(vault_root=tmp_vault) is None


def test_zweck_vocabulary_constant():
    """The closed zweck set is exactly {health_heal, wave_fanin}."""
    assert set(vl.ZWECK_VOCABULARY) == {"health_heal", "wave_fanin"}


# ─── Test (f): roundtrip acquire -> is_locked -> release ──────────────────────

def test_roundtrip_acquire_is_locked_release(tmp_vault):
    """Full roundtrip: acquire -> is_locked sees it -> release -> is_locked None."""
    assert vl.acquire(zweck="wave_fanin", worker_id="wave-1", timeout=0, vault_root=tmp_vault) is True
    info = vl.is_locked(vault_root=tmp_vault)
    assert info is not None and info["holder"] == "wave-1"
    assert vl.release(worker_id="wave-1", vault_root=tmp_vault) is True
    assert vl.is_locked(vault_root=tmp_vault) is None


# ─── Test (g): heartbeat updates heartbeat_at ─────────────────────────────────

def test_heartbeat_updates_heartbeat_at(tmp_vault):
    """heartbeat() updates the heartbeat_at timestamp for the holder."""
    vl.acquire(zweck="health_heal", worker_id="heal-1", timeout=0, vault_root=tmp_vault)
    path = vl._vault_lock_file_path(tmp_vault)
    fm1, _ = fl._read_lock(path)
    hb_before = fm1.get("heartbeat_at", "")
    time.sleep(1.1)
    ok = vl.heartbeat(worker_id="heal-1", vault_root=tmp_vault)
    assert ok is True
    fm2, _ = fl._read_lock(path)
    assert fm2.get("heartbeat_at", "") != hb_before


# ─── Test (h): self-vs-foreign / second worker blocked ────────────────────────

def test_second_worker_blocked(tmp_vault):
    """A second worker cannot acquire while a non-stale vault lock is held."""
    vl.acquire(zweck="health_heal", ttl=300, worker_id="heal-1", timeout=0, vault_root=tmp_vault)
    ok = vl.acquire(zweck="wave_fanin", worker_id="other", timeout=0, vault_root=tmp_vault)
    assert ok is False
    # original holder unchanged
    info = vl.is_locked(vault_root=tmp_vault)
    assert info is not None and info["holder"] == "heal-1"


# ─── Test (i): vault lock and factory lock are independent files ──────────────

def test_vault_and_factory_locks_coexist(tmp_vault):
    """A factory (global) lock and a vault lock live in different files and
    do NOT clobber each other (the corruption-race the separate file prevents)."""
    fl.acquire(scope="global", worker_id="bdf-1", timeout=0, vault_root=tmp_vault)
    vl.acquire(zweck="health_heal", worker_id="heal-1", timeout=0, vault_root=tmp_vault)

    # both still readable, independent
    fac = fl.is_locked(scope="global", vault_root=tmp_vault)
    vlt = vl.is_locked(vault_root=tmp_vault)
    assert fac is not None and fac["holder"] == "bdf-1"
    assert vlt is not None and vlt["holder"] == "heal-1"


# ─── Test (j): HeartbeatDaemon is reused (not re-implemented) ─────────────────

def test_heartbeat_daemon_reused(tmp_vault):
    """vault_lock exposes a HeartbeatDaemon that keeps the vault lock alive
    (reused from factory_lock, INV-VAULT-LOCK-4)."""
    vl.acquire(zweck="health_heal", ttl=300, worker_id="heal-1", timeout=0, vault_root=tmp_vault)
    daemon = vl.HeartbeatDaemon(worker_id="heal-1", interval=1, vault_root=tmp_vault)
    daemon.start()
    path = vl._vault_lock_file_path(tmp_vault)
    fm1, _ = fl._read_lock(path)
    hb_before = fm1.get("heartbeat_at", "")
    time.sleep(1.4)
    daemon.stop()
    daemon.join(timeout=3)
    fm2, _ = fl._read_lock(path)
    assert fm2.get("heartbeat_at", "") != hb_before
