"""BL-442 AK-1: SDF-post -> BDF aktiver Redirect-Entscheider (GAP-1).

Dieses Modul ist der GAP-1-Fix-Entscheider: _SDF_orchestrate_post Phase 4 TERMINATE
ruft im Lane/Goal-Modus `if should_chain_bdf(...): Skill(redirect_target())` statt
nur passivem df_status=DONE.

Ohne diesen aktiven Chain blieb der BDF-Loop passiv (df_status=DONE-Signal ohne
Rueckkehr-Trigger), was dazu fuehrte, dass neue Backlog-Items nach SDF-TERMINATE
nicht automatisch in den naechsten BDF-Zyklus flossen.
"""
from __future__ import annotations

import argparse
import sys


def should_chain_bdf(
    mode: str,
    all_items_done: bool,
    no_chain: bool = False,
    bdf_loop_active: bool = False,
) -> bool:
    """Entscheide ob _SDF_orchestrate_post aktiv zu _BDF_orchestrate chainen soll.

    Gibt True zurueck genau dann wenn:
    - all_items_done ist True (Queue/Parking-Lot durch)
    - no_chain ist False (kein expliziter Unterdruekungs-Flag)
    - bdf_loop_active ist False (kein aktiver BDF-Loop laeuft)
    - mode != "big_dark_factory" (BDF-Modus treibt selbst; kein Doppel-Antrieb)

    Args:
        mode: Aktueller SDF/BDF-Modus (z.B. "lane", "goal", "big_dark_factory").
        all_items_done: True wenn alle Items in der aktuellen Queue/dem Parking-Lot
            abgearbeitet sind.
        no_chain: Wenn True, wird der Redirect explizit unterdrueckt.
        bdf_loop_active: Wenn True, laeuft bereits ein BDF-Loop (Doppel-Antrieb
            vermeiden). Bei mode="big_dark_factory" typischerweise True.

    Returns:
        True wenn aktiver BDF-Redirect ausgefuehrt werden soll, sonst False.
    """
    return (
        all_items_done
        and not no_chain
        and not bdf_loop_active
        and mode != "big_dark_factory"
    )


def redirect_target() -> str:
    """Gibt das Ziel-Skill fuer den BDF-Redirect zurueck.

    Returns:
        "_BDF_orchestrate" — das Skill das bei aktivem Redirect via
        Skill(redirect_target()) aufgerufen werden soll.
    """
    return "_BDF_orchestrate"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BL-442 AK-1: SDF-post BDF Redirect-Entscheider"
    )
    parser.add_argument("--mode", required=True, help="SDF/BDF-Modus")
    parser.add_argument(
        "--all-items-done",
        action="store_true",
        default=False,
        help="Alle Items abgearbeitet",
    )
    parser.add_argument(
        "--no-chain",
        action="store_true",
        default=False,
        help="Redirect explizit unterdruecken",
    )
    parser.add_argument(
        "--bdf-loop-active",
        action="store_true",
        default=False,
        help="BDF-Loop bereits aktiv",
    )
    args = parser.parse_args()

    result = should_chain_bdf(
        mode=args.mode,
        all_items_done=args.all_items_done,
        no_chain=args.no_chain,
        bdf_loop_active=args.bdf_loop_active,
    )
    target = redirect_target()
    print(f"should_chain_bdf={result}")
    print(f"redirect_target={target}")
    sys.exit(0 if result else 1)
