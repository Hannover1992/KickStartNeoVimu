"""orchestrator_phase_registration.py — BL-362: Phase-Registrierungs-Completeness-Checker.

Statische Drift-Prävention für Orchestrator-Skills (IDF/SDF/A/BDF). Fängt die 7.7-Klasse:
eine Phase mit Resume-Einstiegspunkt (`IF resume_phase IN [..., "X"]:`) MUSS in der
`resolve_resume_phase`-Whitelist UND der Resume-Tabelle registriert sein. Fehlt sie dort,
startet ein Resume nach Crash from-scratch (stiller Bug — so geschehen bei Phase 7.7
TEST_SEARCH, ~2 Wochen unentdeckt, gefixt + getrackt als BL-362).

Deterministisch, statisch (pre-runtime), kein Live-Pipeline-Risiko. Erklärbar: jede
Violation nennt die Phase + die fehlende Fläche.

Kern-Assertion: resume_guard_phases ⊆ (whitelist_phases ∩ resume_table_phases).
"""
import re
import sys
from pathlib import Path
from typing import List, Set

# `resume_phase IN [ ... ]` — das REGISTRIERTE Phase = der LETZTE quoted-Token in der Liste
# (Konvention `[null, ..., "X"]`: der Block resumed AT "X").
_GUARD_RE = re.compile(r"resume_phase\s+IN\s+\[([^\]]*)\]")
_QUOTED_UPPER_RE = re.compile(r'"([A-Z_][A-Z0-9_]*)"')
# Resume-Tabelle-Zeile: erste Zelle ist ein backtick-Token (| `INIT` | ... |).
# Phase-Tabelle-Zeilen (| 7.7 | `TEST_SEARCH` | ...) haben eine ZAHL als erste Zelle → matchen NICHT.
_TABLE_FIRST_CELL_RE = re.compile(r"^\|\s*`([A-Z_][A-Z0-9_]*)`\s*\|")


def resume_guard_phases(md: str) -> Set[str]:
    """Phasen mit Resume-Einstiegspunkt = letzter quoted-Token je `resume_phase IN [...]`."""
    phases: Set[str] = set()
    for m in _GUARD_RE.finditer(md):
        toks = _QUOTED_UPPER_RE.findall(m.group(1))
        if toks:
            phases.add(toks[-1])
    return phases


def _subroutine_body(md: str) -> str:
    """Body der resolve_resume_phase-Subroutine (bis zum schließenden Code-Fence)."""
    idx = md.find("resolve_resume_phase")
    if idx == -1:
        return ""
    rest = md[idx:]
    fence = rest.find("```")
    return rest[:fence] if fence != -1 else rest


def whitelist_phases(md: str) -> Set[str]:
    """Alle quoted Uppercase-Tokens im resolve_resume_phase-Subroutine-Body (= anerkannte
    Resume-Stati). Mehrzeilige IN-Listen werden mitgefangen."""
    return set(_QUOTED_UPPER_RE.findall(_subroutine_body(md)))


def resume_table_phases(md: str) -> Set[str]:
    """Phasen mit einer Resume-Tabellen-Zeile (erste Zelle = backtick-Uppercase-Token)."""
    phases: Set[str] = set()
    for line in md.splitlines():
        m = _TABLE_FIRST_CELL_RE.match(line)
        if m:
            phases.add(m.group(1))
    return phases


def check_orchestrator(md: str) -> List[str]:
    """Liste erklärbarer Registrierungs-Violations ([] = vollständig registriert)."""
    guards = resume_guard_phases(md)
    wl = whitelist_phases(md)
    rt = resume_table_phases(md)
    violations: List[str] = []
    for p in sorted(guards):
        if p not in wl:
            violations.append(
                f"Phase '{p}' hat einen Resume-Guard (resume_phase IN [...,'{p}']), "
                f"fehlt aber in der resolve_resume_phase-Whitelist -> Resume startet from-scratch (7.7-Klasse)."
            )
        if p not in rt:
            violations.append(
                f"Phase '{p}' hat einen Resume-Guard, fehlt aber in der Resume-Tabelle "
                f"(| `{p}` | Springe zu Phase ... |) -> undokumentiertes Resume-Ziel."
            )
    return violations


# --- Increment-2: Resume-Mechanismus-Klassifikation (SDF/A/BDF generalisieren) ----
# Increment-1 prueft NUR die whitelist-Resume-Mechanik (IDF: resume_phase IN [...] in der
# resolve_resume_phase-Whitelist und der Resume-Tabelle). SDF/A/BDF benutzen STRUKTURELL
# ANDERE Resume-Mechanismen -> Increment-1 meldete dort [N/A] (korrekt, kein False-Positive).
# Increment-2 macht den Checker mechanismus-BEWUSST: er klassifiziert jeden Orchestrator
# ueber robuste Struktur-Marker und (a) wendet die 7.7-whitelist-Pruefung auf JEDEN
# whitelist-Orchestrator an (zukunftssicher, NICHT IDF-hardcoded), (b) dokumentiert die
# dispatch-states der state-/factory-Mechanismen statt stillem N/A.
#
# SEVERITY-SPLIT (gemessen 2026-06-15 gegen alle 29 *_orchestrate.md — der generische
# --resume-Marker ist ZU BREIT um "muss eines von 4 Mustern matchen" zu bedeuten; 7
# Orchestratoren mit legitimem state-Resume (_I_ I_PIPELINE_STATE/resume_zaehler etc.)
# wuerden sonst als False-DRIFT flaggen = process_audit prose-match-Gotcha):
#   HARTE DRIFT (exit 1) NUR wo das Signal STARK ist:
#     - whitelist-7.7-Gap (check_orchestrator): bewiesene stille-Resume-Bug-Klasse.
#     - broken-whitelist: resume_phase IN [...]-Guards vorhanden, aber KEINE
#       resolve_resume_phase-Subroutine -> Guards zeigen ins Leere (Dispatch-Surface fehlt).
#   WARN (exit 0) wo das Signal SCHWACH ist:
#     - unclassified: generischer Resume-Marker, kein Mechanismus, keine whitelist-Intent.
#       Auditor-Urteil — entweder Checker-Vokabular unvollstaendig, oder Resume unterspezifiziert.
# BEWUSST KEIN value-coverage-scraper. Eine falsche DRIFT auf der universalen Engine ist
# schlimmer als ehrliches N/A — darum die Trennung harte-DRIFT vs WARN.
#
# Mechanismen (gemessen 2026-06-15 gegen die echten 4 Orchestratoren):
#   whitelist          IDF  resolve_resume_phase + resume_phase IN [...] + Resume-Tabelle
#   state_dispatch     SDF  Phase-0 LITE-RESUME-GUARD: IF batch_status == "STARTED|READY|DONE"
#   factory_state      BDF  Resume-Detection: IF bdf_status == / IN [...] (FACTORY_STATES)
#   idempotent_berater A    "Berater sind individuell idempotent (lesen eigenen Output)"

_STATE_DISPATCH_RE = re.compile(r'\bbatch_status\s*==\s*"([A-Z_][A-Z0-9_]*)"')
_FACTORY_STATE_EQ_RE = re.compile(r'\bbdf_status\s*==\s*"([A-Z_][A-Z0-9_]*)"')
_FACTORY_STATE_IN_RE = re.compile(r'\bbdf_status\s+IN\s+\[([^\]]*)\]')
_IDEMPOTENT_RE = re.compile(r"Berater sind individuell idempotent", re.IGNORECASE)
# generische Resume-Marker (zum Erkennen von "Resume vorhanden aber unklassifiziert")
_RESUME_MARKER_RE = re.compile(
    r"--resume\b|Resume-Detection|Resume-Guard|LITE-RESUME|resume_phase|resume_point",
    re.IGNORECASE)

MECHANISMS = ("whitelist", "state_dispatch", "factory_state", "idempotent_berater")


def detect_mechanisms(md: str) -> Set[str]:
    """Robuste Mechanismus-Detektion ueber starke Struktur-Marker (KEIN value-scrape)."""
    m: Set[str] = set()
    if "resolve_resume_phase" in md:
        m.add("whitelist")
    if _STATE_DISPATCH_RE.search(md):
        m.add("state_dispatch")
    if _FACTORY_STATE_EQ_RE.search(md) or _FACTORY_STATE_IN_RE.search(md):
        m.add("factory_state")
    if _IDEMPOTENT_RE.search(md):
        m.add("idempotent_berater")
    return m


def handled_states(md: str) -> Set[str]:
    """States, auf die der Resume-Dispatch verzweigt (SDF batch_status + BDF bdf_status).
    Robust (== / IN-Branches), rein dokumentarisch — KEINE pass/fail-Ableitung daraus."""
    states: Set[str] = set(_STATE_DISPATCH_RE.findall(md))
    states |= set(_FACTORY_STATE_EQ_RE.findall(md))
    for inlist in _FACTORY_STATE_IN_RE.findall(md):
        states |= set(_QUOTED_UPPER_RE.findall(inlist))
    return states


def classify_and_check(md: str) -> dict:
    """Mechanismus-bewusster Resume-Report mit Severity-Split.
    violations=[] heisst keine HARTE DRIFT (whitelist-7.7-Gap / broken-whitelist).
    warnings = schwache Signale (unclassified) — Auditor-Urteil, KEIN exit-1."""
    mechs = detect_mechanisms(md)
    guards = resume_guard_phases(md)
    has_resume_marker = bool(_RESUME_MARKER_RE.search(md)) or bool(guards)
    violations: List[str] = []
    warnings: List[str] = []
    if "whitelist" in mechs:
        violations.extend(check_orchestrator(md))            # 7.7-Gap (bewiesene Bug-Klasse)
    elif guards:
        # resume_phase IN [...]-Guards vorhanden, aber KEINE resolve_resume_phase-Subroutine
        # -> whitelist-Resume intendiert, Dispatch-Surface fehlt komplett (Guards ins Leere).
        violations.append(
            f"Resume-Guards {sorted(guards)} (resume_phase IN [...]) vorhanden, aber KEINE "
            f"resolve_resume_phase-Subroutine -> whitelist-Resume ohne Dispatch-Surface (broken)."
        )
    elif has_resume_marker and not mechs:
        # generischer Marker (--resume etc.), kein Mechanismus, keine whitelist-Intent = SCHWACH
        warnings.append(
            "Resume-Marker (z.B. --resume) vorhanden, aber kein erkanntes Mechanismus-Muster "
            "-> unklassifiziert. Schwaches Signal (Marker-Heuristik): entweder der Mechanismus "
            "ist dem Checker-Vokabular unbekannt (Vokabular erweitern), oder Resume unterspezifiziert."
        )
    if mechs:
        label = sorted(mechs)
    elif guards:
        label = ["whitelist_broken"]
    elif has_resume_marker:
        label = ["unclassified"]
    else:
        label = ["none"]
    return {
        "mechanisms": label,
        "handled_states": sorted(handled_states(md)),
        "whitelist_guards": sorted(guards),
        "violations": violations,
        "warnings": warnings,
    }


def main(argv: List[str] = None) -> int:
    """CLI: scan ein oder mehrere Orchestrator-Skill-Files. Exit 1 wenn Violations.

    Usage: py -3 orchestrator_phase_registration.py <skill.md> [<skill2.md> ...]
    Mechanismus-bewusst (Increment-2): whitelist-Orchestratoren werden 7.7-geprueft,
    state_dispatch/factory_state/idempotent_berater werden klassifiziert (dispatch-states
    dokumentiert), unklassifiziertes Resume = DRIFT. Kein Resume-Marker = [N/A]."""
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        sys.stderr.write("usage: orchestrator_phase_registration.py <skill.md> [...]\n")
        return 2
    total = 0
    for path in argv:
        p = Path(path)
        if not p.is_file():
            sys.stdout.write(f"[SKIP] nicht gefunden: {path}\n")
            continue
        md = p.read_text(encoding="utf-8")
        rep = classify_and_check(md)
        mechs = rep["mechanisms"]
        viol = rep["violations"]
        warn = rep["warnings"]
        if viol:
            total += len(viol)
            sys.stdout.write(f"[DRIFT] {p.name}: {len(viol)} Violation(s) [mechanism={','.join(mechs)}]\n")
            for v in viol:
                sys.stdout.write(f"        - {v}\n")
        elif warn:
            sys.stdout.write(f"[WARN] {p.name}: {len(warn)} Warnung(en) [mechanism={','.join(mechs)}] (exit 0)\n")
            for w in warn:
                sys.stdout.write(f"        - {w}\n")
        elif mechs == ["none"]:
            sys.stdout.write(f"[N/A]  {p.name}: keine Resume-Mechanik (nicht anwendbar)\n")
        elif "whitelist" in mechs:
            sys.stdout.write(f"[OK]   {p.name}: whitelist-Resume, {len(rep['whitelist_guards'])} Guards, alle registriert\n")
        else:
            st = ",".join(rep["handled_states"]) or "-"
            sys.stdout.write(f"[CLASSIFIED] {p.name}: mechanism={','.join(mechs)} dispatch_states=[{st}]\n")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
