#!/usr/bin/env python3
"""stage_infra_schema.py — BL-329 batch_2 (AK-4): Prozess-Infra-Schema.

Reiner, deterministischer Parser/Normalisierer fuer stage_N.md setup.commands-
Eintraege. Hebt den Eintrag von einem nackten Befehls-STRING auf eine
strukturierte Prozess-Klasse (WebHost-Klasse): lokaler WebHost via
background-Start + PID-Capture, damit der Teardown ihn als Prozess-Kill stoppen
kann (statt nur docker-down).

KANONISCHES SCHEMA (4 Felder):
  - cmd:         der auszufuehrende Befehl (String).
  - cwd:         Arbeitsverzeichnis (None = Default-cwd des Aufrufers).
  - background:  True  -> Start-Process/detached, kehrt sofort zurueck
                 (WebHost-Klasse, kein run-to-completion).
                 False -> foreground, run-to-completion (heutige Semantik).
  - pid_capture: True  -> die gestartete PID wird getrackt
                 (TDD-STATE.setup_artifacts.pids) -> Teardown killt sie.
                 False -> kein PID-Tracking noetig.

KERN-CONSTRAINT (ABWAERTSKOMPATIBEL — NICHT VERHANDELBAR):
  Ein nackter String ("docker-compose up -d") = heutige Semantik:
  background=False (foreground, run-to-completion), cwd=None (default),
  pid_capture=False. Bestehende stage_N.md mit nackten setup.commands-Strings
  (alle Stages ausser einem etwaigen kuenftigen WebHost-Stage) laufen
  UNVERAENDERT durch. KEIN Bruch.

KONTRAKT (rein, deterministisch — KEIN State, KEIN IO, cwd-stabil per
Konstruktion: dieses Modul loest keine Pfade auf und fuehrt nichts aus):
  - normalize_setup_command(entry) -> NormalizedCommand | None
        entry == String   -> nackt-String-Defaults (Abwaertskompat).
        entry == dict      -> Felder uebernommen, fehlende per Default ergaenzt.
        entry leer/None/cmd-leer -> None (Skip-Signal, kein Crash).
  - normalize_setup_commands(entries) -> list[NormalizedCommand]
        Liste-Normalisierung; ueberspringt leere/None-Eintraege.

Andockung: zitiert vom /_TDD_setup- und /_TDD_teardown-Vertrag (Schema-Naht)
sowie vom G-TDD-STAGES-READY-Gate (tdd_stages_ready.py, AK-3). Die tatsaechliche
Ausfuehrung (Start-Process, PID-Capture, Kill) bleibt in _TDD_setup/_TDD_teardown
(Executor) — dieses Modul liefert NUR das normalisierte Schema.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional, Union

# Ein setup.commands-Eintrag ist entweder ein nackter String (Abwaertskompat)
# oder ein dict mit (Teil-)Schema. None/leer wird tolerant als Skip behandelt.
SetupCommandEntry = Union[str, dict, None]


def _coerce_bool(value: object) -> bool:
    """Truthy-tolerante Normalisierung auf echtes bool.

    YAML liefert i.d.R. schon bool, aber wir tolerieren String-Varianten
    ('true'/'false'/'yes'/'no') und Zahlen (0/1), damit handgeschriebene
    stage_N.md robust geparst werden. Unbekannte/leere Werte -> False
    (konservativer Default: kein Background, kein PID-Capture).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "ja", "on")
    return False


def _coerce_cwd(value: object) -> Optional[str]:
    """Leerer/whitespace-only cwd -> None (Default-cwd), sonst getrimmter String."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


@dataclass(frozen=True)
class NormalizedCommand:
    """Ein normalisierter setup.commands-Eintrag (kanonisches 4-Feld-Schema)."""

    cmd: str
    cwd: Optional[str] = None
    background: bool = False
    pid_capture: bool = False

    def expects_pid_kill(self) -> bool:
        """True gdw. der Teardown diese PID killen soll (Prozess-Klasse).

        Die WebHost-Klasse (background + pid_capture) ist genau der Fall, in
        dem der Teardown eine captured PID stoppt statt nur docker-down. Wir
        machen das an pid_capture fest (das explizite Tracking-Signal); ein
        background-Start ohne pid_capture taeusst keinen Kill vor.
        """
        return self.pid_capture

    def to_dict(self) -> dict:
        """Kanonisches 4-Feld-dict (stabile Reihenfolge fuer Round-Trip/Audit)."""
        return {
            "cmd": self.cmd,
            "cwd": self.cwd,
            "background": self.background,
            "pid_capture": self.pid_capture,
        }


def normalize_setup_command(entry: SetupCommandEntry) -> Optional[NormalizedCommand]:
    """Normalisiere EINEN setup.commands-Eintrag (String ODER dict).

    Abwaertskompat: nackter String -> Defaults (foreground, run-to-completion,
    cwd=default, kein pid_capture). Voll-/Teil-dict -> Felder uebernommen,
    fehlende per Default. Leerer/None-Eintrag (oder dict ohne nicht-leeren cmd)
    -> None (Skip-Signal).
    """
    if entry is None:
        return None

    # Abwaertskompat-Pfad: nackter String = heutige Semantik.
    if isinstance(entry, str):
        cmd = entry  # NICHT trimmen: der Befehl bleibt byte-genau erhalten.
        if not cmd.strip():
            return None  # leerer/whitespace-only String -> Skip.
        return NormalizedCommand(
            cmd=cmd,
            cwd=None,
            background=False,
            pid_capture=False,
        )

    # Schema-Pfad: dict mit (Teil-)Feldern.
    if isinstance(entry, dict):
        raw_cmd = entry.get("cmd")
        if raw_cmd is None or not str(raw_cmd).strip():
            return None  # dict ohne nutzbaren cmd -> Skip (kein Crash).
        return NormalizedCommand(
            cmd=str(raw_cmd),
            cwd=_coerce_cwd(entry.get("cwd")),
            background=_coerce_bool(entry.get("background")),
            pid_capture=_coerce_bool(entry.get("pid_capture")),
        )

    # Unbekannter Typ (Liste/Zahl) -> tolerant als Skip behandeln.
    return None


def normalize_setup_commands(entries: object) -> list[NormalizedCommand]:
    """Normalisiere eine LISTE von setup.commands-Eintraegen.

    Ueberspringt leere/None-Eintraege (kein None im Output). None oder leere
    Liste -> leere Liste.
    """
    if not entries or not isinstance(entries, (list, tuple)):
        return []
    out: list[NormalizedCommand] = []
    for entry in entries:
        nc = normalize_setup_command(entry)
        if nc is not None:
            out.append(nc)
    return out


if __name__ == "__main__":
    # Windows-stdout ist standardmaessig cp1252 -> Umlaute crashen mit
    # UnicodeEncodeError. utf-8 erzwingen (Py3.7+), fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    # Selbst-Demo (Vertrag-Selbsttest) — exit 0 bei erwartetem Verhalten.
    demos = [
        ("nackter String (Abwaertskompat)", "docker-compose up -d",
         {"background": False, "pid_capture": False, "cwd": None}),
        ("WebHost-dict (background + PID-Capture)",
         {"cmd": "dotnet run", "cwd": "src/Api", "background": True, "pid_capture": True},
         {"background": True, "pid_capture": True, "cwd": "src/Api"}),
        ("Teil-dict (nur cmd)", {"cmd": "npm run dev"},
         {"background": False, "pid_capture": False, "cwd": None}),
    ]
    ok_all = True
    for name, entry, expect in demos:
        nc = normalize_setup_command(entry)
        got = {"background": nc.background, "pid_capture": nc.pid_capture, "cwd": nc.cwd}
        status = "OK" if got == expect else "MISMATCH"
        if got != expect:
            ok_all = False
        print(f"[{status}] {name}: cmd={nc.cmd!r} -> {got} (expects_pid_kill={nc.expects_pid_kill()})")

    print(f"None-Eintrag         -> {normalize_setup_command(None)}")
    print(f"leerer String        -> {normalize_setup_command('')}")
    print(f"dict ohne cmd        -> {normalize_setup_command({'cwd': 'x'})}")
    sys.exit(0 if ok_all else 1)
