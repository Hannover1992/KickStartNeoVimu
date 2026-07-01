#!/usr/bin/env python3
"""
resolve_lock_root.py — Single Source of Truth fuer Lock-Root-Resolution.

BL-368 AK-LEDGER-PL-1: Resolver fuer den Lock-Ledger-Root-Pfad.

Resolver-Reihenfolge:
  1. ENV VAR `OMNI_LOCK_ROOT`   (PRIMAER — cross-worktree stabil, maschinen-global)
  2. resolve_vault_root()       (Default — Lock-Ledger haengt am Vault-Root)

Kanonische ENV-Var: OMNI_LOCK_ROOT

Aufruf:
  python3 resolve_lock_root.py
  -> /home/uczen/Documents/OmniCommand

  python3 resolve_lock_root.py --debug
  -> zeigt Resolver-Schritt der gematcht hat

─────────────────────────────────────────────────────────────────────────────
PL-2 DOKTRIN: Machine-Global Lock-Root-Koordination (BL-368 AK-LEDGER-PL-2)
─────────────────────────────────────────────────────────────────────────────

WARUM ein expliziter Lock-Root-Resolver:

Der Lock-Ledger (``.locks/``) koordiniert konkurrierende BL-Laeufe auf
Dateiebene. Damit diese Koordination funktioniert, MUESSEN alle Worktrees
derselben Maschine denselben Lock-Root sehen. Ohne explizite Koordination
berechnet jeder Worktree seinen eigenen Vault-Root — und landet bei
identischer Konfiguration zwar am selben Ort, aber das ist eine implizite
Annahme, keine Garantie.

Sobald ein Worktree einen abweichenden Vault-Root haette (z.B. anderer
`CLAUDE_VAULT_ROOT`, anderes Pin-File oder andere Heuristik), entsteht ein
Lost-Lock: Worktree A schreibt eine Lock-Datei in seinen Lock-Root,
Worktree B schreibt in seinen eigenen — beide halten ihren Lock fuer
exklusiv, ohne den des anderen zu sehen. Das fuehrt zu stiller Korruption
des Ledger-Zustands unter parallelem Zugriff.

OMNI_LOCK_ROOT als primaere Stufe loest das strukturell:
  - Die ENV-Var wird maschinen-global gesetzt (z.B. in Shell-Profile oder
    Launcher-Skript) und gilt fuer alle Worktrees desselben Prozessbaums.
  - Sie ist cross-worktree stabil: unabhaengig von `cwd`, Pin-Files oder
    vault-routing.json liefert sie immer denselben Pfad.
  - Kein Worktree kann diesen Wert lokal ueberschreiben.

DEFAULT = Vault-Root (OMNI_LOCK_ROOT nicht gesetzt):

Ohne OMNI_LOCK_ROOT faellt der Resolver auf `resolve_vault_root()` zurueck.
Das ist rueckwaerts-kompatibel zum bisherigen Verhalten von
`factory_lock._bl_locks_root`, das den Lock-Ledger ebenfalls relativ zum
Vault-Root ableitet. In Single-Worktree-Setups ist dieser Fallback sicher —
der Lost-Lock-Fehler tritt nur bei echtem Worktree-Split auf.

BL-351-NAHT — Grundlage fuer Worktree-Parallelitaet und Lock-Governance:

Dieser Resolver ist der Ledger-Ort, den die folgenden Schichten voraussetzen:

  AK-WAIT (T3, BL-368 Allocator):
    Wartet auf Freigabe eines Locks. Der Warte-Mechanismus liest
    `{lock_root}/.locks/{bl_id}.lock`. Ohne einen gemeinsamen Lock-Root
    sehen konkurrierende Worktrees die Locks des jeweils anderen nicht.

  AK-ALLOCATOR (T4, BL-368 Allocator):
    Verwaltet den Slot-Pool fuer parallele BL-Ausfuehrung. Der Allocator
    schreibt und prueft den Ledger unter `{lock_root}/.locks/`. Ohne
    machine-global koordinierten Lock-Root kann er keine worktree-globalen
    Slot-Limits durchsetzen.

  AK-FORCE-CLEAR (T7, BL-368 Allocator):
    Raeume verwaiste Locks auf (z.B. nach Absturz). Funktioniert nur, wenn
    alle Locks im selben Verzeichnis liegen — d.h. in einem einzigen,
    machine-global bekannten Lock-Root.

  INV-WT-DIAL (BL-431, Worktree-Parallelitaet):
    Jeder Worktree laeuft als eigene Roadmap-Lane. Lanes sind datei-disjunkt,
    aber der Lock-Ledger koordiniert ihre Slot-Belegung maschinen-global.
    Ohne diesen Resolver wuerde BL-431 bei mehr als einem Worktree stille
    Doppel-Belegungen riskieren.

Kurz: resolve_lock_root() ist die Naht zwischen dem lokalen Dateisystem und
der maschinenweiten Lock-Koordination. Wer den Ledger schreibt oder liest,
MUSS diesen Resolver verwenden — kein direktes Ableiten aus Vault-Root oder
Hartkodieren von Pfaden.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Importiert resolve_vault_root aus demselben Verzeichnis
sys.path.insert(0, str(Path(__file__).parent))
from resolve_vault_root import resolve_vault_root  # noqa: E402

_ENV_LOCK_ROOT = "OMNI_LOCK_ROOT"


def resolve_lock_root(
    cwd: Path | None = None,
    *,
    debug: bool = False,
) -> Path:
    """Resolves den absoluten Lock-Root-Pfad.

    Args:
        cwd: Arbeitsverzeichnis (default: Path.cwd(), wird an resolve_vault_root() weitergegeben)
        debug: Gibt Resolver-Schritt als stderr-Meldung aus

    Returns:
        Absoluter Pfad zum Lock-Root (immer pathlib.Path, ~ expandiert)

    Resolver-Reihenfolge:
        1. ENV OMNI_LOCK_ROOT    (canonical, PRIMAER — cross-worktree stabil)
        2. resolve_vault_root()  (Default — Lock-Ledger haengt am Vault-Root)
    """
    # ── Stufe 1: ENV OMNI_LOCK_ROOT (canonical, cross-worktree stabil) ─────────
    env_lock = os.environ.get(_ENV_LOCK_ROOT)
    if env_lock:
        result = Path(env_lock).expanduser()
        if debug:
            print(f"[resolve_lock_root] Stufe 1 (ENV {_ENV_LOCK_ROOT}): {result}", file=sys.stderr)
        return result

    # ── Stufe 2: Vault-Root (Default) ──────────────────────────────────────────
    result = resolve_vault_root(cwd=cwd)
    if debug:
        print(f"[resolve_lock_root] Stufe 2 (resolve_vault_root): {result}", file=sys.stderr)
    return result


def main(argv: list[str]) -> int:
    debug = "--debug" in argv
    result = resolve_lock_root(debug=debug)
    print(str(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
