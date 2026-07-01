"""OneDrive-Sync-Delay-Mock fuer Multi-Machine-Test-Simulation.

Wrapper um Path.write_text / Path.mkdir mit konfigurierbarer Latency.
Production-Schutz: Default OFF (BL195_SYNC_DELAY_ENABLED != 1).

Delay-Profile (BL195_SYNC_PROFILE):
  INSTANT           -- 0s (default)
  ONEDRIVE_TYPICAL  -- 30s
  ONEDRIVE_SLOW     -- 60s
  ONEDRIVE_OFFLINE  -- 300s
"""
import os
import time
from contextlib import contextmanager
from pathlib import Path


class SyncDelayProfile:
    """Konfigurierbare Sync-Delay-Profile in Sekunden."""

    INSTANT = 0
    ONEDRIVE_TYPICAL = 30
    ONEDRIVE_SLOW = 60
    ONEDRIVE_OFFLINE = 300


def get_delay_s() -> float:
    """
    Liest aktuell konfigurierten Delay in Sekunden.
    Gibt 0 zurueck wenn BL195_SYNC_DELAY_ENABLED != 1 (Production-Schutz).
    """
    if os.environ.get("BL195_SYNC_DELAY_ENABLED", "0") != "1":
        return 0.0
    profile_name = os.environ.get("BL195_SYNC_PROFILE", "INSTANT")
    return float(getattr(SyncDelayProfile, profile_name, 0))


@contextmanager
def sync_delay():
    """
    Context-Manager: fuehrt Code aus, wartet danach den konfigurierten Delay.
    Kein Delay wenn BL195_SYNC_DELAY_ENABLED != 1.
    """
    delay = get_delay_s()
    yield
    if delay > 0:
        time.sleep(delay)


def delayed_write(path: Path, content: str) -> None:
    """
    Schreibt content in path, simuliert danach OneDrive-Sync-Delay.
    Kein Delay wenn BL195_SYNC_DELAY_ENABLED != 1.
    """
    with sync_delay():
        path.write_text(content, encoding="utf-8")


def delayed_mkdir(path: Path) -> None:
    """
    Erstellt Verzeichnis (inkl. Eltern), simuliert danach OneDrive-Sync-Delay.
    Kein Delay wenn BL195_SYNC_DELAY_ENABLED != 1.
    """
    with sync_delay():
        path.mkdir(parents=True, exist_ok=True)
