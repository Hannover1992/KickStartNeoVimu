#!/usr/bin/env python3
"""
truth_cutover.py — die Cutover-Write-Schicht (BL-385/386, Runbook Schritt 2+3).

Liefert die BEWIESENE Mechanik fuer den Model->Wahrheits-Cutover:
  backup_to_legacy   Original-Model heilig sichern -> {legacy}/{stem}.pre_truth.md (idempotent)
  swap_model_to_view Cutover: Original->legacy, dann Model.md := build_model_view(truths)
                     — NUR wenn roundtrip_ok (sonst KEIN Swap = kein Verlust; harter Guard)
  rollback_model     INV-MIG-11: Original byte-identisch aus legacy wiederherstellen
  cutover_model      Komposition: atomize -> write_truths -> swap (roundtrip-gated)

SICHERHEIT (BL-364-Fence): dieses Modul operiert auf UEBERGEBENEN Pfaden + ist vollstaendig TDD-bewiesen
(tmp-Fixtures). Der Live-Vault-Cutover ist der BEWUSSTE Fresh-Session-Akt MIT Backup — der Orchestrator-
`--write` (truth_migrate_orchestrator) bleibt absichtlich GEFENCED (ruft dieses Modul NICHT auf der echten
Vault). Hier ist die Mechanik bewiesen; die Verdrahtung + der reale Lauf = frische Session (Runbook).

Invarianten:
  INV-MIG-11: rollback stellt das Original BYTE-IDENTISCH wieder her (das einzige Netz, Vault nicht git).
  CUTOVER-SAFE-1: kein Swap ohne roundtrip_ok(original, truths) -> Verlust strukturell unmoeglich.
  CUTOVER-SAFE-2: backup_to_legacy ueberschreibt ein bestehendes Legacy NIE (das Original ist heilig).
"""
from __future__ import annotations

from pathlib import Path

import truth_atomizer as ta

try:
    import truth_census as tc
except Exception:
    tc = None  # type: ignore

_LEGACY_SUFFIX = ".pre_truth.md"


def legacy_path(model_path, legacy_dir) -> Path:
    """Deterministischer Legacy-Pfad fuer ein Model."""
    return Path(legacy_dir) / (Path(model_path).stem + _LEGACY_SUFFIX)


def backup_to_legacy(model_path, legacy_dir) -> Path:
    """Sichert das Original-Model byte-genau nach {legacy}/{stem}.pre_truth.md.
    CUTOVER-SAFE-2: idempotent — ein bereits gesichertes Original wird NIE ueberschrieben
    (sonst koennte ein 2. Lauf das heilige Original mit der View ueberschreiben)."""
    model_path = Path(model_path)
    legacy_dir = Path(legacy_dir)
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy = legacy_path(model_path, legacy_dir)
    if not legacy.exists():
        legacy.write_bytes(model_path.read_bytes())  # byte-genau, kein Text-Roundtrip-Risiko
    return legacy


def _is_segment_truths(truths) -> bool:
    """B2-SEGMENT-Truths erkennen (view_mode==verbatim ODER _verbatim vorhanden). Ein Model ist
    rein HEADING oder rein SEGMENT (atomize_model_file waehlt EINEN Pfad), darum genuegt `any`."""
    return any(t.get("view_mode") == "verbatim" or "_verbatim" in t for t in truths)


def swap_model_to_view(model_path, truths, legacy_dir) -> dict:
    """Cutover eines Models: Original->legacy-Backup, dann Model.md := generierte View.
    CUTOVER-SAFE-1 (B2-aware, BL-395): kein Swap ohne den jeweils RICHTIGEN Verlustfrei-Beweis —
      SEGMENT-Model: build_segment_view == Original BYTE-identisch (Partition; der parse-Roundtrip
        waere hier blind = exakt die BL-395-Lockstep-Falle auf der Write-Seite).
      HEADING-Model: roundtrip_ok(original, truths) (parse-Gleichheit).
    Sonst KEIN Swap (kein Verlust)."""
    model_path = Path(model_path)
    original = model_path.read_text(encoding="utf-8", errors="replace")
    if _is_segment_truths(truths):
        truths = sorted(truths, key=lambda t: t.get("seq", 0))
        view = ta.build_segment_view(truths)
        ok = (view == original)              # byte-identisch (Partition-Beweis)
        view_mode = "verbatim"
    else:
        ok = ta.roundtrip_ok(original, truths)
        view = ta.build_model_view(truths)
        view_mode = "heading"
    if not ok:
        return {"swapped": False, "reason": "roundtrip_failed"}
    legacy = backup_to_legacy(model_path, legacy_dir)
    model_path.write_text(view, encoding="utf-8")
    return {"swapped": True, "legacy": str(legacy), "view_mode": view_mode}


def rollback_model(model_path, legacy_dir) -> dict:
    """INV-MIG-11: stellt das Original BYTE-IDENTISCH aus dem Legacy-Backup wieder her."""
    model_path = Path(model_path)
    legacy = legacy_path(model_path, legacy_dir)
    if not legacy.exists():
        return {"restored": False, "reason": "no_legacy"}
    model_path.write_bytes(legacy.read_bytes())  # byte-genau
    return {"restored": True}


def cutover_model(model_path, namespace, *, truths_dir=None, legacy_dir=None) -> dict:
    """Voller per-Model-Cutover (Runbook Schritt 1+2): atomize -> write_truths -> swap (gated).

    B2-aware (BL-395): geht ueber atomize_model_file (Zwei-Pfad HEADING|SEGMENT) statt nur atomize,
    und gated auf das VOLLE Readiness-Urteil — exakt die Maschinen-Regel, die der Orchestrator als
    quarantine_reasons emittiert: kein Swap bei roundtrip_fail | low_coverage | schema_error |
    truth_count_loss. Damit kann ein (zukuenftiger, gefencter) Massen-`--write` strukturell NIE eine
    verlustige View schreiben (die 8 genuine no-W-def Models werden REFUSED, nicht korrumpiert)."""
    model_path = Path(model_path)
    truths_dir = Path(truths_dir) if truths_dir else (model_path.parent / "truths")
    legacy_dir = Path(legacy_dir) if legacy_dir else (model_path.parent / "_legacy")
    res = ta.atomize_model_file(model_path, namespace)
    truths = res["truths"]
    if not truths:
        return {"cutover": False, "reason": "no_truths"}
    if not res["roundtrip_ok"]:
        return {"cutover": False, "reason": "roundtrip_failed"}  # SICHER: kein Write bei Roundtrip-Fail
    if res.get("low_coverage"):
        return {"cutover": False, "reason": "low_coverage"}      # BL-395 (b): View deckt Quell-Body nicht
    if res.get("schema_errors"):
        return {"cutover": False, "reason": "schema_error"}
    text = model_path.read_text(encoding="utf-8", errors="replace")
    census = tc.count_wknots(text)["total_estimate"] if tc else res["knots"]
    if res["knots"] < census:
        return {"cutover": False, "reason": "truth_count_loss"}   # census-W-defs > atomisierte knots (BL-395 a); mirror quarantine_reasons
    written = ta.write_truths(truths, truths_dir)
    swap = swap_model_to_view(model_path, truths, legacy_dir)
    return {"cutover": swap.get("swapped", False), "knots": len(truths),
            "format_hint": res.get("format_hint"), "truths_written": written,
            "legacy": swap.get("legacy"), "view_mode": swap.get("view_mode")}
