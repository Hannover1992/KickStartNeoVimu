#!/usr/bin/env python3
"""
roadmap_status.py — der deterministische Kern von /_roadmap (der Kompass).

Beantwortet drei Fragen aus Roadmap-Doc + Backlog-Index (+ optional per-BL Manifest):
  1. WO stehen wir   — welche Roadmap-BLs sind DONE, welche ist das aktuelle Ziel.
  2. WOHIN gehen wir  — die geordnete Restliste.
  3. NÄCHSTER BEFEHL  — der prozess-korrekte nächste Skill-Aufruf fuer das Ziel-BL
                        (UNREIF→/_A_orchestrate, reif→/_IDF_orchestrate, mid-flight→--resume),
                        IMMER Lead-self (INV-AO-CALLER), fresh-session-Hinweis fuer schwere Pipelines.

READ-ONLY. Re-implementiert kein Routing als Magie — es spiegelt die /_help-Pipeline-Reihenfolge
(A → IDF → SDF → SC/I) auf den Reifegrad des Ziel-BLs.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import lane_plan as _lp

_BL_RE = re.compile(r"\bBL-\d+\b")

# Reifegrad-Klassen → Pipeline-Entry (Prozess-Routing, /_help-konform)
_DONE = {"DONE", "ABGESCHLOSSEN"}
_RAW = {"UNREIF", "DRAFT"}                          # braucht A (Model/Spec existieren noch nicht)
_MATURED = {"READY", "SC-REIF", "REIF", "PLANNED"}  # A schon gelaufen → IDF


_ORDER_BLOCK = re.compile(r"ROADMAP-ORDER:START(.*?)ROADMAP-ORDER:END", re.S)


def parse_roadmap_order(text: str) -> list[str]:
    """BL-IDs in DOKUMENT-Reihenfolge (= Roadmap-Reihenfolge), dedupliziert (1. Vorkommen gewinnt).
    Wenn ein `ROADMAP-ORDER:START..END`-Block existiert, wird NUR dieser geparst (kuratierte Build-
    Reihenfolge — robust gegen BL-Erwaehnungen in der umgebenden Prosa); sonst das ganze Dokument."""
    text = text or ""
    m = _ORDER_BLOCK.search(text)
    if m:
        text = m.group(1)
    seen: set[str] = set()
    order: list[str] = []
    for m in _BL_RE.finditer(text):
        b = m.group(0)
        if b not in seen:
            seen.add(b)
            order.append(b)
    return order


def parse_index(index_text: str) -> dict:
    """Backlog-Index-Tabelle -> {bl_id: {status, reifegrad}}. Spalten:
    | BL-XXX | title | STATUS | path | created | updated | prio | REIFEGRAD |"""
    out: dict[str, dict] = {}
    for line in (index_text or "").splitlines():
        if not line.lstrip().startswith("| BL-"):
            continue
        cells = [c.strip() for c in line.split("|")]
        # cells[0]='' , cells[1]=BL-id, cells[2]=title, cells[3]=status, ... cells[-2]=reifegrad, cells[-1]=''
        if len(cells) < 5:
            continue
        bl = cells[1]
        if not _BL_RE.fullmatch(bl):
            continue
        status = cells[3].upper() if len(cells) > 3 else ""
        reifegrad = cells[-2].upper() if len(cells) >= 4 else ""
        out[bl] = {"status": status, "reifegrad": reifegrad}
    return out


def next_command_for_bl(bl_id: str, reifegrad: str | None, status: str | None = None,
                        *, a_done: bool = False, in_flight: bool = False) -> dict:
    """Der prozess-korrekte naechste Befehl fuer EINE BL. Lead fuehrt ihn SELBST aus (INV-AO-CALLER).
    Mega-Worker = via Agent(.., 'orchestrate ..') delegieren — VERBOTEN; der Skill spawnt selbst je Phase 1 Worker."""
    rg = (reifegrad or "").upper()
    st = (status or "").upper()
    lead = "Lead fuehrt SELBST aus (Skill-Load), NIE via Agent('orchestrate ..') = Mega-Worker. Motor gated-off → altmodisch Team."
    if st in _DONE or rg in _DONE:
        return {"command": None, "reason": "DONE — naechste Roadmap-BL nehmen", "fresh_session": False, "lead": lead}
    if in_flight:
        return {"command": f"/_SDF_orchestrate {bl_id} --resume",
                "reason": "Pipeline mid-flight → resume (kein Neustart, kein Doppel-Antrieb)", "fresh_session": False, "lead": lead}
    if a_done or rg in _MATURED:
        return {"command": f"/_IDF_orchestrate {bl_id}",
                "reason": "A bereits gelaufen (reif) → IDF (Parking-Lot + Batch-Plan) → auto-chain SDF → SC/I", "fresh_session": True, "lead": lead}
    if rg in _RAW or not rg:
        return {"command": f"/_A_orchestrate {bl_id}",
                "reason": "UNREIF/needs_a_pipeline → A baut Model/Spec/K-Score/Gap + auto-chain IDF→SDF→SC/I", "fresh_session": True, "lead": lead}
    return {"command": f"/_A_orchestrate {bl_id}",
            "reason": f"Reifegrad '{reifegrad}' unklar → konservativ A (Lead prueft /_help)", "fresh_session": True, "lead": lead}


def roadmap_status(roadmap_text: str, index: dict, done_ids: set | None = None,
                   lane_plan: dict | None = None, my_lane: str | None = None) -> dict:
    """Kompass-State: ordered/done/remaining/target + naechster Befehl. Eine Roadmap-BL gilt als DONE,
    wenn sie im done-Index liegt ODER ihr Index-status==DONE ODER sie gar nicht (mehr) im aktiven Index ist
    (DONE-Items wandern per INV-INDEX-SPLIT in den done-Index).

    lane_plan, my_lane (optional): wenn gesetzt, wird bei der target-Wahl ein BL uebersprungen,
    das von einer ANDEREN Lane gehalten wird (is_collision). Solche BLs landen in blocked_other_lane.
    Ohne diese Parameter: exaktes bisheriges Verhalten (target = erstes remaining BL).
    """
    order = parse_roadmap_order(roadmap_text)
    done_ids = set(done_ids or set())
    done, remaining, unknown = [], [], []
    blocked_other_lane: list[str] = []
    target = None
    for b in order:
        rec = index.get(b)
        is_done = (b in done_ids) or (rec is not None and rec.get("status", "") in _DONE)
        if is_done:
            done.append(b)
        elif rec is None:
            unknown.append(b)            # weder aktiv noch done bekannt — Lead prueft (Tippfehler? archiviert?)
        else:
            remaining.append(b)
            if target is None:
                if lane_plan and my_lane and _lp.is_collision(b, my_lane, lane_plan):
                    blocked_other_lane.append(b)
                else:
                    target = b
    nxt = None
    if target:
        rec = index.get(target, {})
        nxt = next_command_for_bl(target, rec.get("reifegrad"), rec.get("status"))
    return {"ordered": order, "done": done, "remaining": remaining, "unknown": unknown,
            "target": target, "next": nxt, "blocked_other_lane": blocked_other_lane}


def render_build_chain(bl_id: str, command: str | None) -> str:
    """Erzeugt den BAU-KETTE-Block fuer eine BL — reifegrad-bewusster Start-Punkt.

    Der Start-Punkt wird aus dem `command`-String abgeleitet (keine eigene Reifegrad-Logik —
    next_command_for_bl hat das bereits erledigt):
      - command == None / kein command  → DONE, kein Block
      - command enthaelt '/_A_orchestrate' → Kette ab A (vollstaendig)
      - command enthaelt '/_IDF_orchestrate'→ Kette ab IDF (A entfaellt)
      - command enthaelt '--resume'          → Kette ab SDF --resume
    """
    if not command:
        return ""
    cmd = command.strip()
    lines: list[str] = ["BAU-KETTE (auto-chain ab dem Start-Orchestrator):"]
    if "/_A_orchestrate" in cmd:
        lines.append(f"  A ({cmd})       → Wissensbasis: Model·Spec·K-Score·Gap·PL")
        lines.append(f"   ↓ IDF (/_IDF_orchestrate {bl_id})     → PL-Items → Batches")
        lines.append(f"   ↓ SDF (/_SDF_orchestrate {bl_id})     → pro Batch: C3-modusEntscheidung(M{{N}}) → /_I_orchestrate (bzw. /_SC_orchestrate M4–M7) … ALLE Batches")
        lines.append(f"   ↓ Post (/_SDF_orchestrate_post {bl_id}) → recalibrate·statusTransition·modelSync·loopDecision")
        lines.append(f"  → dann das naechste BL bei A")
    elif "/_IDF_orchestrate" in cmd:
        lines.append(f"  IDF ({cmd})     → PL-Items → Batches")
        lines.append(f"   ↓ SDF (/_SDF_orchestrate {bl_id})     → pro Batch: C3-modusEntscheidung(M{{N}}) → /_I_orchestrate (bzw. /_SC_orchestrate M4–M7) … ALLE Batches")
        lines.append(f"   ↓ Post (/_SDF_orchestrate_post {bl_id}) → recalibrate·statusTransition·modelSync·loopDecision")
        lines.append(f"  → dann das naechste BL bei IDF (oder A falls Reifegrad sinkt)")
    elif "--resume" in cmd:
        lines.append(f"  SDF ({cmd}) → fortsetzen ab letztem Checkpoint")
        lines.append(f"   ↓ Post (/_SDF_orchestrate_post {bl_id}) → recalibrate·statusTransition·modelSync·loopDecision")
        lines.append(f"  → dann das naechste BL")
    else:
        # Fallback: unbekannter Befehl — Kette zeigen aber generisch
        lines.append(f"  {cmd}")
        lines.append(f"   ↓ SDF (/_SDF_orchestrate {bl_id})     → pro Batch: C3-modusEntscheidung(M{{N}}) → Implement")
        lines.append(f"   ↓ Post (/_SDF_orchestrate_post {bl_id}) → recalibrate·statusTransition·modelSync·loopDecision")
    return "\n".join(lines)


def format_report(state: dict, epic: str | None = None) -> str:
    L = []
    L.append(f"# /_roadmap — Kompass{(' · ' + epic) if epic else ''}")
    L.append("")
    L.append(f"WO: {len(state['done'])}/{len(state['ordered'])} Roadmap-BLs DONE.")
    if state["target"]:
        nx = state["next"] or {}
        L.append(f"ZIEL (du bist hier): {state['target']}")
        L.append("")
        L.append(f"NAECHSTER BEFEHL: {nx.get('command') or '(Epic fertig → Goal-Gate)'}")
        L.append(f"    Grund: {nx.get('reason','')}")
        if nx.get("fresh_session"):
            L.append("    FRISCHE Session empfohlen (schwere Pipeline = frischer Kopf).")
        L.append(f"    {nx.get('lead','')}")
        L.append("")
        chain = render_build_chain(state["target"], nx.get("command"))
        if chain:
            for line in chain.splitlines():
                L.append(f"    {line}")
            L.append("")
    else:
        L.append("ZIEL: keine offene Roadmap-BL — Epic fertig (→ Goal-Gate / DONE).")
    L.append("")
    L.append(f"WOHIN (Rest, in Reihenfolge): {' → '.join(state['remaining']) or '—'}")
    if state["unknown"]:
        L.append(f"    unbekannt (nicht im Index — Lead pruefen): {', '.join(state['unknown'])}")
    return "\n".join(L)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="roadmap_status", description="/_roadmap Kompass-Kern (read-only)")
    p.add_argument("--roadmap", type=Path, default=Path(".claude/ROADMAP.md"))
    p.add_argument("--index", type=Path, required=True, help="Backlog-Index (aktiv)")
    p.add_argument("--done-index", type=Path, default=None, help="Backlog-Index (done/archiviert), optional")
    p.add_argument("--epic", default=None)
    p.add_argument("--lane", default=None, choices=["A", "B", "C"], help="Eigene Lane (A|B|C) fuer lane-aware target-Wahl")
    p.add_argument("--lane-plan", type=Path, default=None, help="Pfad zur _lane_plan.md Datei")
    args = p.parse_args(argv)

    roadmap_text = args.roadmap.read_text(encoding="utf-8", errors="replace") if args.roadmap.is_file() else ""
    index = parse_index(args.index.read_text(encoding="utf-8", errors="replace")) if args.index.is_file() else {}
    done_ids: set[str] = set()
    if args.done_index and args.done_index.is_file():
        done_ids = set(parse_index(args.done_index.read_text(encoding="utf-8", errors="replace")).keys())

    lp: dict | None = None
    if args.lane_plan and args.lane_plan.is_file():
        lp = _lp.parse_lane_plan(args.lane_plan)

    state = roadmap_status(roadmap_text, index, done_ids, lane_plan=lp, my_lane=args.lane)
    out = format_report(state, args.epic)
    try:                                  # Windows-Konsole (cp1252) bricht sonst an Emojis
        sys.stdout.reconfigure(encoding="utf-8")
        print(out)
    except (UnicodeEncodeError, AttributeError):
        sys.stdout.buffer.write(out.encode("utf-8", "replace") + b"\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
