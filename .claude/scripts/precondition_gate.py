#!/usr/bin/env python3
"""precondition_gate.py — BL-409 batch_1 (AK-GATE-PL-1): Precondition-Gate fuer Stage-Start.

Prueft die drei Precondition-Kategorien in deterministischer Reihenfolge, bevor eine
Stage gestartet wird:
  1. Vorgaenger-Stages DONE + QG erfuellt (predecessor)
  2. Substrat-Artefakte vorhanden (substrat)
  3. Ressourcen frei/claimbar (resource)

API:
  @dataclass
  class PreconditionResult:
      verdict: Literal["PASS", "BLOCK", "WAIT"]
      category: Optional[Literal["predecessor", "substrat", "resource"]]  # None bei PASS
      message: str
      blocking_item: Optional[str]  # None bei PASS

  check_preconditions(stage_nr, *, vault_root=None, resource_timeout=60.0) -> PreconditionResult

Verdikt-Semantik:
  PASS  - alle Preconditions erfuellt
  BLOCK - strukturelles Problem (Vorgaenger/Substrat), manueller Eingriff noetig
  WAIT  - Ressource temporaer belegt, Caller soll spaeter neu versuchen

Pruef-Reihenfolge (deterministisch — W5):
  Substrat-BLOCK stoppt vor Ressourcen-Check (T-b4: kein ueberfluessiger Lock).
  Erst Struktur pruefen, dann Ressourcen (structural-BLOCK beats resource-WAIT).

Stateless (kein persistenter WAIT-State, F5): KEIN eigener Lock/rmtree.
Delegiert an:
  - resolve_vault_stage.resolve_stage  (Vorgaenger + Target Stage-Handle)
  - stage_slice_schema.validate_slice_set  (Substrat-Check)
  - resource_allocator.claim / acquire_with_wait  (Ressourcen-Check)

Forward-Seam-Kommentar: Lock-Transfer Gate->BL-408-Setup (NOT-YET).

Exit codes (CLI):
  0 = PASS
  2 = BLOCK oder WAIT
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).parent))

import resource_allocator
from resolve_vault_stage import resolve_stage
from stage_slice_schema import validate_slice_set


# ---------------------------------------------------------------------------
# Ergebnis-Typ
# ---------------------------------------------------------------------------

@dataclass
class PreconditionResult:
    """Ergebnis der Precondition-Gate-Pruefung."""

    verdict: Literal["PASS", "BLOCK", "WAIT"]
    category: Optional[Literal["predecessor", "substrat", "resource"]]
    message: str
    blocking_item: Optional[str]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

_WORKER_ID = "precondition_gate"


def _qg_erfuellt(qg_value: object) -> bool:
    """True gdw. qg-Wert als erfuellt gilt (nur "PASS" — alles andere inkl. None/OPEN -> False)."""
    return isinstance(qg_value, str) and qg_value.strip().upper() == "PASS"


# ---------------------------------------------------------------------------
# Kategorie-1: Vorgaenger-Stage-Check (predecessor)
# ---------------------------------------------------------------------------

def _check_predecessor(
    stage_nr: int,
    predecessor_stages: Optional[list],
    vault_root: Optional[Path],
) -> Optional[PreconditionResult]:
    """Prueft alle deklarierten Vorgaenger-Stages auf DONE + QG=PASS.

    stage_nr=1 ODER predecessor_stages None/leer -> trivial PASS (None).
    Partielle PASS-Verhinderung (W14): stufe=DONE allein genuegt nicht, QG muss PASS sein.
    """
    if not predecessor_stages:
        return None

    for pred_nr in predecessor_stages:
        pred_handle = resolve_stage(pred_nr, vault_root=vault_root)
        if pred_handle is None:
            return PreconditionResult(
                verdict="BLOCK",
                category="predecessor",
                message=f"Vorgaenger-Stage {pred_nr} nicht aufloesbar (nicht gefunden).",
                blocking_item=str(pred_nr),
            )

        # _index.stufe muss DONE sein
        index_view = pred_handle.slice_view("_index")
        stufe = (index_view or {}).get("stufe")
        if not isinstance(stufe, str) or stufe.strip().upper() != "DONE":
            return PreconditionResult(
                verdict="BLOCK",
                category="predecessor",
                message=(
                    f"Vorgaenger-Stage {pred_nr} hat stufe='{stufe}' (erwartet: DONE). "
                    f"Stage muss erst abgeschlossen werden."
                ),
                blocking_item=str(pred_nr),
            )

        # exit_criteria.qg muss PASS sein (Partial-PASS-Verhinderung W14)
        ec_view = pred_handle.slice_view("exit_criteria")
        qg = (ec_view or {}).get("qg")
        if not _qg_erfuellt(qg):
            return PreconditionResult(
                verdict="BLOCK",
                category="predecessor",
                message=(
                    f"Vorgaenger-Stage {pred_nr}: stufe=DONE aber exit_criteria.qg='{qg}' "
                    f"(erwartet: PASS). Partial-PASS-Verhinderung (W14): QG muss erfuellt sein."
                ),
                blocking_item=str(pred_nr),
            )

    return None


# ---------------------------------------------------------------------------
# Kategorie-2: Substrat-Check (substrat)
# ---------------------------------------------------------------------------

def _check_substrat(stage_dir: Path) -> Optional[PreconditionResult]:
    """Prueft den Slice-Satz des Target-Stage-Verzeichnisses via validate_slice_set.

    BLOCK gdw. Slice-Set unvollstaendig/ungueltig.
    """
    result = validate_slice_set(stage_dir)
    if result.valid:
        return None

    # Erstbesten Defekt als blocking_item nennen
    first_missing = result.missing_slices[0] if result.missing_slices else None
    first_error = result.errors[0].slice if result.errors else None
    blocking = first_missing or first_error

    msg_parts = []
    if result.missing_slices:
        msg_parts.append(f"Fehlende Slices: {', '.join(result.missing_slices)}")
    for err in result.errors:
        msg_parts.append(f"{err.slice}: {err.message}")

    return PreconditionResult(
        verdict="BLOCK",
        category="substrat",
        message="Substrat-Check FAIL — " + "; ".join(msg_parts),
        blocking_item=blocking,
    )


# ---------------------------------------------------------------------------
# Kategorie-3: Ressourcen-Check (resource)
# ---------------------------------------------------------------------------

def _check_resources(
    resources: Optional[list],
    resource_timeout: float,
    vault_root: Optional[Path],
) -> Optional[PreconditionResult]:
    """Prueft ob alle deklarierten Ressourcen claimbar sind.

    Erst non-blocking claim; bei Contention acquire_with_wait mit resource_timeout.
    WAIT gdw. mindestens eine Ressource nach timeout noch belegt.
    """
    if not resources:
        return None

    for res_id in resources:
        # Non-blocking single-attempt
        acquired = resource_allocator.claim(
            res_id,
            worker_id=_WORKER_ID,
            vault_root=vault_root,
        )
        if acquired:
            continue

        # Ressource belegt -> blockierend warten
        acquired = resource_allocator.acquire_with_wait(
            res_id,
            worker_id=_WORKER_ID,
            timeout=resource_timeout,
            vault_root=vault_root,
        )
        if not acquired:
            return PreconditionResult(
                verdict="WAIT",
                category="resource",
                message=(
                    f"Ressource '{res_id}' ist belegt und konnte innerhalb von "
                    f"{resource_timeout}s nicht acquired werden. Spaeter neu versuchen."
                ),
                blocking_item=str(res_id),
            )

    return None


# ---------------------------------------------------------------------------
# Oeffentliche API
# ---------------------------------------------------------------------------

def check_preconditions(
    stage_nr: int,
    *,
    vault_root: Optional[Path] = None,
    resource_timeout: float = 60.0,
) -> PreconditionResult:
    """Prueft alle Preconditions einer Stage in deterministischer Reihenfolge.

    Pruef-Reihenfolge (W5 — deterministisch):
      1. Vorgaenger-Stages DONE + QG erfuellt (predecessor)
      2. Substrat-Artefakte vollstaendig (substrat)
      3. Ressourcen claimbar (resource)

    Bei BLOCK in Kategorie 1 oder 2 wird Kategorie 3 nicht mehr geprueft
    (T-b4: kein ueberfluessiger Lock bei Struct-BLOCK).

    Stateless: kein persistenter WAIT-State.
    Forward-Seam: Lock-Transfer Gate->BL-408-Setup (NOT-YET).
    """
    # Target-Stage aufloesen
    target_handle = resolve_stage(stage_nr, vault_root=vault_root)

    # Preconditions aus exit_criteria.preconditions lesen
    preconditions: dict = {}
    if target_handle is not None:
        ec_view = target_handle.slice_view("exit_criteria")
        raw_prec = (ec_view or {}).get("preconditions")
        if isinstance(raw_prec, dict):
            preconditions = raw_prec

    predecessor_stages = preconditions.get("predecessor_stages") if preconditions else None
    resources_list = preconditions.get("resources") if preconditions else None

    # --- Kategorie 1: Vorgaenger ---
    block = _check_predecessor(stage_nr, predecessor_stages, vault_root)
    if block is not None:
        return block

    # --- Kategorie 2: Substrat ---
    # Target-Stage-Verzeichnis fuer validate_slice_set
    if target_handle is not None and target_handle.stage_dir is not None:
        block = _check_substrat(target_handle.stage_dir)
    else:
        # Kein Stage-Dir -> Substrat nicht prufbar -> BLOCK
        block = PreconditionResult(
            verdict="BLOCK",
            category="substrat",
            message=f"Stage {stage_nr} hat kein aufloesbaresStage-Verzeichnis (Substrat nicht pruefbar).",
            blocking_item=str(stage_nr),
        )
    if block is not None:
        return block

    # --- Kategorie 3: Ressourcen ---
    # Erst nach Substrat-PASS (T-b4 garantiert: claim wird nicht aufgerufen bei Substrat-BLOCK)
    wait = _check_resources(resources_list, resource_timeout, vault_root)
    if wait is not None:
        return wait

    return PreconditionResult(
        verdict="PASS",
        category=None,
        message="Alle Preconditions erfuellt.",
        blocking_item=None,
    )


# ---------------------------------------------------------------------------
# CLI (analog sanity_check_stage.py)
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Precondition-Gate fuer Stage-Start (BL-409 AK-GATE-PL-1). "
                    "Prueft Vorgaenger-Stages, Substrat-Artefakte und Ressourcen."
    )
    parser.add_argument("stage_nr", type=int, help="Stage-Nummer (1..N)")
    parser.add_argument(
        "--resource-timeout",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Timeout fuer acquire_with_wait bei Ressourcen-Contention (default: 60s)",
    )
    args = parser.parse_args(argv)

    result = check_preconditions(args.stage_nr, resource_timeout=args.resource_timeout)

    status_line = f"PRECONDITION-GATE: {result.verdict}"
    if result.category is not None:
        status_line += f" [{result.category}]"
    print(status_line)
    print(f"  {result.message}")
    if result.blocking_item is not None:
        print(f"  blocking_item: {result.blocking_item}")

    return 0 if result.verdict == "PASS" else 2


if __name__ == "__main__":
    # Windows-stdout default cp1252 -> Umlaute crashen. utf-8 erzwingen, fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))
