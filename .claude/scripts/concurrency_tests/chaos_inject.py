"""Chaos-Injection-Framework fuer BL-195 Concurrency-Tests.

Flag-basierte Inject-Points (Production-Pollution-Schutz: default OFF).
Aktivierung: BL195_CHAOS_ENABLED=1 + BL195_CHAOS_POINT=<point>

Inject-Points (ChaosPoint-Enum):
  crash-after-dispatch  -- SystemExit nach Dispatch
  stale-heartbeat       -- delegiert an lock_steal_simulator
  sync-delay            -- time.sleep(delay_s)
  none                  -- kein Inject (default)
"""
import os
import time
from enum import Enum


class ChaosPoint(Enum):
    CRASH_AFTER_DISPATCH = "crash-after-dispatch"
    STALE_HEARTBEAT = "stale-heartbeat"
    SYNC_DELAY = "sync-delay"
    NONE = "none"


def chaos_active() -> bool:
    """True nur wenn BL195_CHAOS_ENABLED=1 gesetzt — Production-Schutz."""
    return os.environ.get("BL195_CHAOS_ENABLED", "0") == "1"


def maybe_inject(point: ChaosPoint, *, delay_s: float = 0.0) -> None:
    """
    Prueft ob Chaos aktiv und ob dieser Punkt der konfigurierte Inject-Point ist.
    Kein Effekt wenn chaos_active() == False (Production-Schutz).

    Args:
        point:   Der Inject-Point der gerade erreicht wird.
        delay_s: Verzoegerung in Sekunden fuer SYNC_DELAY-Punkt.
    """
    if not chaos_active():
        return
    active = os.environ.get("BL195_CHAOS_POINT", ChaosPoint.NONE.value)
    if active != point.value:
        return
    if point == ChaosPoint.CRASH_AFTER_DISPATCH:
        raise SystemExit(f"[CHAOS] injected crash at {point.value}")
    if point == ChaosPoint.STALE_HEARTBEAT:
        # Stale-Heartbeat-Manipulation wird an lock_steal_simulator delegiert.
        # Hier kein direkter Effekt — der Aufrufer muss lock_steal_simulator.force_stale() aufrufen.
        return
    if point == ChaosPoint.SYNC_DELAY:
        time.sleep(delay_s)
