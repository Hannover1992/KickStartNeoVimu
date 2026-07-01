#!/usr/bin/env python3
"""
guard_stage_acquire_enforce.py — BL-486 batch_3 C-FIX: enforced acquire-VOR-Spinup (DoD-6).

Schliesst die Enforcement-Luecke: VOR dem Container-/WebHost-/Worker-Spinup (Setup-Step
in dispatch_implement.js) MUESSEN alle unteilbaren Stage-Ressourcen acquiriert sein. Ist
eine Ressource belegt -> der Guard wartet (Backoff-Retry) und HAELT bei Timeout (return
False -> kein Spinup) statt blind zu spinup'en. Erfolg (alle acquiriert) -> return True
(GO) + Teardown-Hook-Registrierung, damit die Ressourcen am Stage-Teardown freigegeben
werden (release @ teardown via resource_allocator.register_teardown_hook).

Schicht (Blueprint §5): dieser Guard ist KONSUMENT der OBEREN Schicht resource_allocator
(ra). ra importiert stage_resource_registry (srr, untere Schicht) — der Guard liegt UEBER
ra, der Import ist daher KEIN Circular-Bruch (anders als srr.release_all, das ra NICHT
importieren darf).

C-CHK-Scanner-Vertrag (Blueprint 3.3, LOAD-BEARING): diese Datei MUSS existieren UND den
Literal-String 'acquire_all' als echten ra.acquire_all(...)-Aufruf enthalten. Erst dann
liefert sanity_check_stage._behavior_check_c_acquire PASS (C1=callsite_found, C2=guard_exists).

Mock-Konvention (Test G-C-2): acquire_all wird via Modul-Attribut ra.acquire_all(...)
aufgerufen (NICHT 'from resource_allocator import acquire_all'), damit
patch.object(ra, "acquire_all", ...) im Test greift.
"""

import sys
import time
from pathlib import Path
from typing import Callable, List, Optional

# Import-Konvention wie die Geschwister-Module (resource_allocator, stage_resource_registry)
sys.path.insert(0, str(Path(__file__).parent))

import resource_allocator as ra  # OBERE Schicht — Guard ist Konsument (kein Circular)


def enforce_stage_acquire(
    resource_ids: List[str],
    *,
    worker_id: str,
    vault_root: Optional[Path] = None,
    timeout: float = 60,
    backoff: Optional[List[float]] = None,
    teardown_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """Enforce acquire-VOR-Spinup fuer eine Liste unteilbarer Stage-Ressourcen (DoD-6).

    Retry-Loop um ra.acquire_all (atomic all-or-nothing). True = GO (alle Ressourcen
    acquiriert, Caller DARF spinup); False = HALT (Timeout abgelaufen, KEIN Spinup).

    Bei GO und gegebenem teardown_callback wird der Callback fuer jede resource_id via
    ra.register_teardown_hook registriert (release @ teardown, DoD-6).

    Deterministisch unter gemocktem time.sleep (Time-Triple wie ra.acquire_with_wait):
      - timeout : gesamte erlaubte Wartezeit (akkumuliert ueber Backoff-Schritte)
      - backoff : Sleep-Intervalle je Versuch (default [1,2,4,8,30]; letzter Wert wiederholt)
    """
    if backoff is None:
        backoff = [1, 2, 4, 8, 30]

    elapsed = 0.0
    attempt = 0

    while True:
        if ra.acquire_all(resource_ids, worker_id=worker_id, vault_root=vault_root):
            # GO: alle Ressourcen acquiriert -> Caller darf spinup.
            if teardown_callback is not None:
                for rid in resource_ids:
                    ra.register_teardown_hook(rid, teardown_callback)
            return True

        wait = backoff[min(attempt, len(backoff) - 1)]
        elapsed += wait
        if elapsed >= timeout:
            return False  # HALT: Timeout -> kein Spinup

        time.sleep(wait)
        attempt += 1
