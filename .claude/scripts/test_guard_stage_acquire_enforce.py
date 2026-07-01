"""
test_guard_stage_acquire_enforce.py — BL-486 batch_3 C-FIX: Tests fuer guard_stage_acquire_enforce.py

RED: guard_stage_acquire_enforce.py existiert noch NICHT -> ModuleNotFoundError beim Collect.
KEIN Produktiv-Code in dieser Datei (GREEN-Worker separiert, INV-BUILD-GRAIN, M3).

guard_stage_acquire_enforce.enforce_stage_acquire() Signatur:
  enforce_stage_acquire(
      resource_ids,
      *,
      worker_id,
      vault_root=None,
      timeout=60,
      backoff=None,
      teardown_callback=None,
  ) -> bool
    True = GO (alle Ressourcen acquired, Caller darf spinup)
    False = HALT (timeout abgelaufen, kein Spinup)

Retry-Loop: resource_allocator.acquire_all -> True=GO / False=Retry mit Backoff.
Teardown-Hook: bei GO wird teardown_callback via resource_allocator.register_teardown_hook registriert.

Run (aus Repo-Root, cwd-robust):
  py -3 -m pytest .claude/scripts/test_guard_stage_acquire_enforce.py -v
"""

import sys
import pathlib

import pytest

# Add scripts dir to path (selbe Konvention wie test_resource_allocator.py)
sys.path.insert(0, str(pathlib.Path(__file__).parent))

import factory_lock as fl
import stage_resource_registry as srr
import resource_allocator as ra

# NEU — existiert noch NICHT => ModuleNotFoundError beim Collect = RED (akzeptierte Konvention)
import guard_stage_acquire_enforce as gse


# ─── Fixtures (identisch zu test_stage_resource_registry.py + test_resource_allocator.py) ───

@pytest.fixture
def tmp_vault(tmp_path):
    """Isolierter vault_root unter tmp_path — .locks/ entsteht dort, nicht im echten Vault."""
    return tmp_path


@pytest.fixture(autouse=True)
def patch_vault(tmp_vault, monkeypatch):
    """Patch VAULT_ROOT + no-op _emit_audit -> echtes .locks/ und audit.jsonl unberuehrt."""
    monkeypatch.setattr(fl, "VAULT_ROOT", tmp_vault)
    monkeypatch.setattr(fl, "_emit_audit", lambda *a, **kw: None)
    yield


# ─── G-C-2: Blocked->HALT (Retry-Loop, time.sleep bewiesen) ──────────────────

def test_enforce_blocked_resource_returns_false(tmp_vault):
    """G-C-2: belegte Ressource -> enforce_stage_acquire gibt False (HALT) zurueck.

    Invariante: acquire_all wurde >= 2 mal aufgerufen (Retry-Loop-Beweis).
    time.sleep wurde aufgerufen (Backoff-Beweis).

    RED: ModuleNotFoundError (guard_stage_acquire_enforce nicht existiert).
    """
    from unittest.mock import patch, patch as mock_patch

    # r1 von anderem Worker belegen
    assert srr.acquire("r1", "other", vault_root=tmp_vault) is True

    with patch("time.sleep") as mock_sleep:
        with mock_patch.object(ra, "acquire_all", return_value=False) as mock_acq:
            result = gse.enforce_stage_acquire(
                ["r1"],
                worker_id="w1",
                vault_root=tmp_vault,
                timeout=5,
            )

    assert result is False, f"enforce_stage_acquire muss False (HALT) zurueckgeben, bekam: {result}"
    assert mock_acq.call_count >= 2, (
        f"acquire_all muss mindestens 2x aufgerufen werden (Retry-Loop), "
        f"aber nur {mock_acq.call_count}x aufgerufen"
    )
    assert mock_sleep.call_count >= 1, (
        f"time.sleep muss mindestens 1x aufgerufen werden (Backoff), "
        f"aber {mock_sleep.call_count}x aufgerufen"
    )


# ─── G-C-3: Normalpfad: freie Ressource -> acquire ok -> GO (True) ───────────

def test_enforce_free_resource_returns_true(tmp_vault):
    """G-C-3: freie Ressource r3 -> enforce_stage_acquire gibt True (GO) zurueck.

    Nach erfolgreichem enforce ist r3 LOCKED (Lock wurde gesetzt).

    RED: ModuleNotFoundError (guard_stage_acquire_enforce nicht existiert).
    """
    # r3 ist frei (kein prior acquire)
    result = gse.enforce_stage_acquire(
        ["r3"],
        worker_id="w1",
        vault_root=tmp_vault,
        timeout=10,
    )
    assert result is True, f"enforce_stage_acquire muss True (GO) zurueckgeben, bekam: {result}"

    # Lock wurde gesetzt -> r3 nicht mehr FREE
    states = srr.lookup_free(["r3"], tmp_vault)
    assert states["r3"] == "LOCKED", (
        f"r3 muss nach enforce_stage_acquire LOCKED sein, ist: {states['r3']}"
    )


# ─── G-C-4: teardown-Hook nach erfolgreichem acquire registriert ──────────────

def test_enforce_registers_teardown_hook(tmp_vault):
    """G-C-4: bei GO wird teardown_callback in ra._TEARDOWN_HOOKS["r2"] registriert.

    RED: ModuleNotFoundError (guard_stage_acquire_enforce nicht existiert).
    """
    # Sicherstellen dass der Hook-Dict sauber ist fuer diesen Test
    ra._TEARDOWN_HOOKS.pop("r2", None)

    cb = lambda rid: None  # noqa: E731

    result = gse.enforce_stage_acquire(
        ["r2"],
        worker_id="w1",
        vault_root=tmp_vault,
        teardown_callback=cb,
        timeout=10,
    )
    assert result is True, f"enforce_stage_acquire muss True zurueckgeben, bekam: {result}"

    assert "r2" in ra._TEARDOWN_HOOKS, (
        "r2 muss nach enforce_stage_acquire in ra._TEARDOWN_HOOKS registriert sein"
    )
    assert cb in ra._TEARDOWN_HOOKS["r2"], (
        "teardown_callback muss in ra._TEARDOWN_HOOKS['r2'] enthalten sein"
    )


# ─── G-C-1: Datei-Existenz + acquire_all-Literal + C-CHK via echter API ───────

def test_guard_file_exists_and_c_chk_pass(tmp_vault):
    """G-C-1 + G-C-6: guard_stage_acquire_enforce.py existiert + enthaelt 'acquire_all' +
    sanity_check_stage._behavior_check_c_acquire liefert PASS (nach GREEN-Build).

    Im RED-Moment:
    - Datei existiert NICHT -> assert fehlschlaegt (statisch, RED)
    - C-CHK liefert FAIL (C2=Datei fehlt) -> assert fehlschlaegt (RED)

    Nach GREEN (GREEN-Worker baut guard_stage_acquire_enforce.py):
    - Datei existiert
    - 'acquire_all' Literal vorhanden
    - C-CHK liefert PASS (C1+C2 beide True)

    RED: ModuleNotFoundError (guard_stage_acquire_enforce nicht existiert) ODER
         FileNotFoundError (Datei nicht auf Dateisystem) ODER AssertionError (C-CHK FAIL).
    """
    import sanity_check_stage as scs

    guard_path = pathlib.Path(".claude/scripts/guard_stage_acquire_enforce.py")
    # Fallback: absoluter Pfad (cwd-robust)
    if not guard_path.exists():
        guard_path = pathlib.Path(__file__).parent / "guard_stage_acquire_enforce.py"

    # C2: Datei-Existenz (statisch)
    assert guard_path.exists(), (
        f"guard_stage_acquire_enforce.py muss existieren: {guard_path} nicht gefunden"
    )

    # C1: acquire_all-Literal (statisch)
    content = guard_path.read_text(encoding="utf-8")
    assert "acquire_all" in content, (
        "guard_stage_acquire_enforce.py muss das Literal 'acquire_all' als echten "
        "Funktionsaufruf enthalten (C-CHK-Scanner-Vertrag)"
    )

    # C-CHK via echter API (NICHT Gold-Doc-Illustration mit engine_root/c1_callsite_found)
    # Reale Signatur: sanity_check_stage._behavior_check_c_acquire(scripts_dir: Path) -> dict
    scripts_dir = pathlib.Path(__file__).parent
    r = scs._behavior_check_c_acquire(scripts_dir=scripts_dir)
    assert r["status"] != "FAIL", (
        f"_behavior_check_c_acquire muss nach GREEN-Build PASS/WARN liefern, bekam: {r}"
    )
