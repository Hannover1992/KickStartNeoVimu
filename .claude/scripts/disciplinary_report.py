# -*- coding: utf-8 -*-
"""disciplinary_report.py — BL-324 AK-1/AK-2: Feldjaeger Lead-Abweichungs-Capture.

DER FELDJAEGER. Wenn der Lead/Architekt BEWUSST gegen oder AUSSERHALB des
designten Prozesses handelt — improvisiert, overrided, defert ohne Prozess-Pfad,
faengt etwas das die Maschine uebersah, leakt ueber eine Tier-Grenze, schliesst
eine Foresight-Luecke — dann MUSS diese Abweichung SICHTBAR werden. Die Abweichung
darf RICHTIG sein (`was_correct=True`), aber sie ist das Signal dafuer, was die
Maschine noch nicht selbst kann.

  *** Flexibilitaet ist erlaubt; Stille ist es nicht. ***

NICHT-punitiv: dies ist ein LERN-Strom, kein Straf-Register. Jeder Eintrag ist
ein Datenpunkt fuer die Maschinen-Selbstgenuegsamkeit (siehe
[[feedback_machine_not_context]]).

Verhaeltnis zu den Nachbarn (NICHT dupliziert):
  * Maschinen-Detektion der AUDIT-sichtbaren Abweichungen lebt in
    `deviation_signals.py` (BL-252 AK-1, read-only Sammler). DIESES Modul deckt
    die NICHT-audit-detektierbaren Lead-SELBST-Meldungen ab (Urteils-Calls,
    begruendete Overrides, machine-missed-catches). Die Hook-/Maschinen-Detektion
    ist das ZIEL (batch_2 ueber deviation_signals); die Lead-Selbstmeldung ist die
    UEBERGANGS-KRUECKE (sonst ist es wieder "Agent macht's, nicht Maschine").
  * Der Lern-Loop (Abweichung -> proper-fix-BL via /_backlog) lebt in
    Crown-2 (`_crown2_orchestrate`). DIESES Modul speist dort EIN; es baut weder
    den BL-Writer noch den Generator nach. BL-324 = die LEAD-Teilmenge von Crown-2.

Design-Eigenschaften (strikt, analog [[deviation_signals.py]] / [[crown2_dedupe.py]]):
  * cwd-stabil: Default-Report-Pfad via `Path(__file__).resolve()` — NIE
    cwd-relativ. Siehe [[feedback_lead_verify_from_repo_root]] (cwd-Artefakt-
    false-GREEN-Falle, BL-336).
  * robust: fehlende/leere/kaputte Datei -> {}/[] kein Crash. append faengt
    OS-Fehler ab (Audit-Muster aus factory_lock._emit_audit) und blockiert nie.
  * __main__ utf-8-sicher (Windows-cp1252-Falle, der a96eb1c-Fang).

Schema (`REQUIRED_FIELDS` + automatisch gestempeltes `ts`):
  deviation_class    : str  — eine der `DEVIATION_CLASSES` (5 belegte Klassen).
  kontext            : str  — WO/WANN (Session, BL, Phase, Seam).
  lead_reasoning     : str  — WARUM der Lead so handelte (der Urteils-Call).
  machine_should_have: str  — was die MASCHINE haette tun/fangen sollen.
  learning_signal    : str  — die abgeleitete Lehre (-> oft ein proper-fix-BL).
  was_correct        : bool — war die Abweichung im Ergebnis richtig?
  proposed_hardening : str  — Fix-Skizze (was die Maschine lernen muss).
  ts                 : str  — Zeitstempel (auto-gestempelt, wenn nicht gegeben).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Die 5 belegten Lead-Abweichungs-Klassen (BL-324 Kern-Prinzip).
DEVIATION_CLASSES = (
    "bewusster_override",            # Lead overrided einen Prozess-Schritt bewusst.
    "improvisation_ohne_prozesspfad",  # Lead improvisiert, weil kein Prozess-Pfad existiert.
    "machine_missed_catch",          # Lead faengt, was die Maschine uebersah.
    "tier_leak",                     # Etwas leakt ueber eine Tier-/Zonen-Grenze.
    "foresight_luecke",              # Lead schliesst eine Vorausschau-Luecke der Maschine.
)

# Pflichtfelder (ts wird automatisch gestempelt und ist daher NICHT Pflicht-Input).
REQUIRED_FIELDS = (
    "deviation_class",
    "kontext",
    "lead_reasoning",
    "machine_should_have",
    "learning_signal",
    "was_correct",
    "proposed_hardening",
)

# Volles Report-Schema (Pflichtfelder + auto-Zeitstempel).
REPORT_FIELDS = REQUIRED_FIELDS + ("ts",)

REPORT_FILE_NAME = "disciplinary_report.jsonl"


# ---------------------------------------------------------------------------
# Pfad-Aufloesung (cwd-stabil, BL-336)
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Repo-Root = zwei Ebenen ueber dieser Datei (.claude/scripts/<file>)."""
    return Path(__file__).resolve().parents[2]


def _default_report_path() -> Path:
    """Default-Report-Pfad: neben audit.jsonl unter .claude/audit/.

    cwd-stabil ueber Path(__file__).resolve() — NIE cwd-relativ (sonst
    cwd-Artefakt-false-GREEN-Falle, [[feedback_lead_verify_from_repo_root]]).
    """
    return _repo_root() / ".claude" / "audit" / REPORT_FILE_NAME


def _resolve_report_path(report_path=None) -> Path:
    return Path(report_path) if report_path is not None else _default_report_path()


def _now_iso() -> str:
    """ISO-8601 UTC mit Z-Suffix (analog factory_lock._now_iso)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Validierung (rein/deterministisch)
# ---------------------------------------------------------------------------

def _validate(entry) -> bool:
    """True genau dann, wenn `entry` ein schema-gueltiger Report-Eintrag ist.

    Rein/deterministisch, kein Seiteneffekt. Konservativ: fehlt EIN Pflichtfeld
    oder ist die Klasse unbekannt -> reject.
    """
    if not isinstance(entry, dict):
        return False
    for field in REQUIRED_FIELDS:
        if field not in entry:
            return False
    if entry.get("deviation_class") not in DEVIATION_CLASSES:
        return False
    # was_correct ist ein explizites bool (richtig/falsch der Abweichung) —
    # NICHT truthy-Strings wie "yes" durchwinken.
    if not isinstance(entry.get("was_correct"), bool):
        return False
    return True


# ---------------------------------------------------------------------------
# Schreiben (append-only, robust — Muster: factory_lock._emit_audit)
# ---------------------------------------------------------------------------

def append_report(entry, report_path=None) -> bool:
    """Validiert + appended EINEN Report-Eintrag als JSONL-Zeile.

    Args:
      entry: dict mit den `REQUIRED_FIELDS`. `ts` wird gestempelt, wenn fehlend.
      report_path: Ziel-jsonl (cwd-stabiler Default, wenn None). Tests geben
        IMMER eine tmp-Datei mit — NIE eine echte Live-Prod-jsonl mutieren.

    Returns:
      True bei erfolgreichem Append, False bei Schema-Reject ODER OS-Fehler
      (robust: ein Audit/Report-Fehler darf den Aufrufer NIE crashen).
    """
    if not _validate(entry):
        return False
    record = {k: entry[k] for k in REQUIRED_FIELDS}
    ts = entry.get("ts")
    record["ts"] = ts if ts else _now_iso()
    try:
        path = _resolve_report_path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Aggregation (read-only, robust)
# ---------------------------------------------------------------------------

def aggregate_by_class(report_path=None) -> dict:
    """Liest die Report-jsonl und gruppiert nach `deviation_class`.

    Returns:
      {class: {"count": int, "was_correct_count": int, "entries": [..]}}.
      Robust: fehlende/leere Datei -> {}. Kaputte Zeilen, Nicht-dicts und
      Eintraege mit unbekannter deviation_class werden uebersprungen (nie Crash).
    """
    path = _resolve_report_path(report_path)
    result: dict = {}
    try:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue  # kaputte Zeile -> ueberspringen
                if not isinstance(obj, dict):
                    continue
                cls = obj.get("deviation_class")
                if cls not in DEVIATION_CLASSES:
                    continue  # unbekannte/eingeschmuggelte Klasse -> nicht aggregieren
                bucket = result.setdefault(
                    cls, {"count": 0, "was_correct_count": 0, "entries": []}
                )
                bucket["count"] += 1
                if obj.get("was_correct") is True:
                    bucket["was_correct_count"] += 1
                bucket["entries"].append(obj)
    except OSError:
        return {}
    return result


# ---------------------------------------------------------------------------
# CLI (read-only, utf-8-sicher — Windows-cp1252-Falle, a96eb1c-Fang)
# ---------------------------------------------------------------------------

def _cli_main(argv=None):
    import argparse

    # Windows-stdout UND -stderr sind standardmaessig cp1252 -> json.dumps(
    # ensure_ascii=False) mit Umlauten (stdout) bzw. das em-dash in der
    # Summary-Zeile (stderr) crasht mit UnicodeEncodeError. BEIDE Streams auf
    # utf-8 umstellen (Py3.7+); fail-safe falls ein Stream nicht reconfigurierbar
    # ist. Der a96eb1c-Fang: nicht nur stdout, auch stderr.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        description="BL-324 Feldjaeger — Lead-Abweichungs-Report (read-only Aggregat)."
    )
    parser.add_argument(
        "--aggregate", action="store_true",
        help="Aggregations-View nach deviation_class (Default-Aktion).",
    )
    parser.add_argument(
        "--report-path", default=None,
        help="Pfad zur Report-jsonl (cwd-stabiler Default, wenn weggelassen).",
    )
    args = parser.parse_args(argv)

    # Das CLI ist STRIKT read-only: es appended NICHT (Lead-Capture laeuft ueber
    # das /_disciplinary_report-Skill, das append_report aufruft). --aggregate ist
    # die Default-Aktion; ein blosser Lauf zeigt ebenfalls das Aggregat.
    agg = aggregate_by_class(report_path=args.report_path)
    total = sum(b["count"] for b in agg.values())
    print(f"Disciplinary-Report — {total} Lead-Abweichung(en) in {len(agg)} Klasse(n):",
          file=sys.stderr)
    print(json.dumps(
        {cls: {"count": b["count"], "was_correct_count": b["was_correct_count"]}
         for cls, b in sorted(agg.items())},
        ensure_ascii=False, indent=2,
    ))
    return 0


if __name__ == "__main__":  # pragma: no cover — manueller Live-Lauf (read-only)
    sys.exit(_cli_main())
