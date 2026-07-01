#!/usr/bin/env python3
"""tdd_stages_ready.py — BL-329 batch_2 (AK-3): G-TDD-STAGES-READY (testbarer Helper).

Materialisiert das in `_TDD_init.md` als Pseudocode dokumentierte Gate
G-TDD-STAGES-READY als reinen, testbaren Validator. `_TDD_orchestrate` /
`_TDD_init` rufen es VOR dem Stufen-Loop.

Geprueft wird pro stage_N.md:
  - 11 BASIS-Pflichtfelder (BL-033, unveraendert):
        stufe, name, fokus, testbefehl, test_projekte, testpfad, fanout,
        mocks_erlaubt, blueprint_perspektive, testtyp, exit_criteria
  - FUER Infra-Stages (infrastruktur != "none"): zusaetzlich 3 Infra-Sektionen
    (11 -> 14):
        setup, teardown, health_check
    Fehlt eine -> BLOCK mit KORREKTIVEM Recovery-Hint (kein blosses "fehlt",
    sondern der Reparatur-Pfad: feedback_corrective_enforcement). Der Block der
    den Prozess stallt MUSS den Recovery-Pfad nennen.
  - Stages mit infrastruktur=none (oder ohne infrastruktur-Key — Abwaertskompat
    fuer Bestands-stage_1.md): KEINE Infra-Pflichtfelder, unveraendert.

ABWAERTSKOMPATIBEL: bestehende stage_N.md mit infrastruktur=none ODER ohne
infrastruktur-Feld laufen unveraendert durch (nur die 11 Basis-Felder).

Schwester: stage_infra_schema.py (AK-4) normalisiert die EINZELNEN
setup.commands-Eintraege; dieses Gate prueft nur die EXISTENZ der drei
Infra-Sektionen (Schema-Tiefen-Validierung der Commands ist Executor-Sache in
_TDD_setup/_TDD_teardown).

Exit codes (CLI):
  0 = PASS (alle Stages bereit)
  2 = BLOCK (mindestens eine Stage unvollstaendig / fehlt)
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 11 BASIS-Pflichtfelder (BL-033 — NICHT aendern, Regressions-Wache im Test).
BASE_REQUIRED_FIELDS = (
    "stufe",
    "name",
    "fokus",
    "testbefehl",
    "test_projekte",
    "testpfad",
    "fanout",
    "mocks_erlaubt",
    "blueprint_perspektive",
    "testtyp",
    "exit_criteria",
)

# 3 Infra-Sektionen — NUR Pflicht fuer Infra-Stages (11 -> 14, BL-329 AK-3).
INFRA_REQUIRED_SECTIONS = ("setup", "teardown", "health_check")


# ---------------------------------------------------------------------------
# Frontmatter-Parsing (eigenstaendig, kein externer State)
# ---------------------------------------------------------------------------


def parse_frontmatter(path: Path) -> Optional[dict]:
    """Lies das YAML-Frontmatter (zwischen den ersten zwei '---') aus path.

    Gibt None zurueck, wenn die Datei fehlt ODER kein Frontmatter-Block da ist.
    utf-8 mit errors='replace' (robust gegen handgeschriebene Umlaute).
    """
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fm_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    import yaml

    try:
        data = yaml.safe_load("\n".join(fm_lines))
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def stage_needs_infra(frontmatter: dict) -> bool:
    """True gdw. die Stage externe Infra braucht (infrastruktur != none).

    Kein infrastruktur-Feld == none-Default (Abwaertskompat fuer Bestands-Stages).
    """
    value = (frontmatter or {}).get("infrastruktur")
    if value is None:
        return False
    return str(value).strip().lower() != "none"


# ---------------------------------------------------------------------------
# Datenmodell
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """Ein Gate-Defekt an einer Stage. recovery_hint ist bei BLOCK PFLICHT."""

    stage: int
    field: str
    message: str
    recovery_hint: Optional[str] = None


@dataclass
class StageCheckResult:
    """Ergebnis fuer EINE stage_N.md."""

    stage: int
    path: Path
    findings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


@dataclass
class GateResult:
    """Aggregat ueber alle geprueften Stages."""

    results: list[StageCheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 2

    def all_findings(self) -> list[Finding]:
        out: list[Finding] = []
        for r in self.results:
            out.extend(r.findings)
        return out


# ---------------------------------------------------------------------------
# Recovery-Hints (korrektiv — feedback_corrective_enforcement)
# ---------------------------------------------------------------------------


def _infra_recovery_hint(stage: int, missing_section: str) -> str:
    """Korrektiver Reparatur-Pfad fuer eine fehlende Infra-Sektion.

    Nennt KONKRET was zu ergaenzen ist (nicht nur dass es fehlt) — der Block
    der den Prozess stallt traegt den Recovery-Pfad.
    """
    return (
        f"stage_{stage}.md {missing_section}-Sektion ergaenzen: "
        f"setup.commands + health_check + teardown.commands "
        f"(Infra-Stage infrastruktur != none braucht alle 3 Sektionen, BL-329 AK-3). "
        f"Vorlage: stage_3.md / stage_6.md. Danach erneut /_TDD_init oder Gate-Re-Check."
    )


def _base_recovery_hint(stage: int) -> str:
    return (
        f"stage_{stage}.md fehlende Basis-Pflichtfelder ergaenzen "
        f"(11 Pflichtfelder stufe..exit_criteria). Ausfuehren: /_TDD_init."
    )


def _missing_file_recovery_hint(stage: int) -> str:
    return (
        f"stage_{stage}.md fehlt. Stage-Dateien generieren: /_TDD_init "
        f"(oder die Stage in den aktiven Stufen deaktivieren)."
    )


# ---------------------------------------------------------------------------
# Core-Checks
# ---------------------------------------------------------------------------


def _is_missing(value: object, present: bool) -> bool:
    """Ein Pflichtfeld gilt als 'fehlend', wenn der Key NICHT vorhanden ODER None.

    BEWUSST KONSERVATIV (Abwaertskompat, Behavior-Catch BL-329 batch_2): ein
    EXPLIZIT gesetzter Leer-Wert (test_projekte: [] / testpfad: "") ist eine
    bewusste Autoren-Wahl und gilt als VORHANDEN — er wird NICHT geblockt. Reale
    Bestands-Stages tragen solche Leer-Werte legitim (stage_1 BL-111 PowerShell:
    test_projekte=[], testpfad=""; stage_6 Controller-E2E: test_projekte=[] weil
    PS-Test-Script statt .NET-Projekte). Das Gate guardet FEHLENDE/unkonfigurierte
    Felder (key-missing oder null), NICHT intentional-blanke. Diese Naht haelt die
    6 echten stage_N.md unveraendert gruen (KEIN BRUCH).
    """
    return (not present) or (value is None)


def check_stage_file(path: Path) -> StageCheckResult:
    """Pruefe EINE stage_N.md gegen Basis- + (konditional) Infra-Pflichtfelder."""
    stage = _stage_number_from_path(path)
    result = StageCheckResult(stage=stage, path=path)

    fm = parse_frontmatter(path)
    if fm is None:
        result.findings.append(
            Finding(
                stage=stage,
                field="__file__",
                message=f"stage_{stage}.md existiert nicht oder hat kein Frontmatter ({path}).",
                recovery_hint=_missing_file_recovery_hint(stage),
            )
        )
        return result

    # 1) 11 Basis-Pflichtfelder (BL-033, unveraendert).
    for f in BASE_REQUIRED_FIELDS:
        if _is_missing(fm.get(f), present=(f in fm)):
            result.findings.append(
                Finding(
                    stage=stage,
                    field=f,
                    message=f"Basis-Pflichtfeld '{f}' fehlt oder ist null in stage_{stage}.md.",
                    recovery_hint=_base_recovery_hint(stage),
                )
            )

    # 2) Infra-Sektionen NUR fuer Infra-Stages (infrastruktur != none).
    if stage_needs_infra(fm):
        for section in INFRA_REQUIRED_SECTIONS:
            if _is_missing(fm.get(section), present=(section in fm)):
                result.findings.append(
                    Finding(
                        stage=stage,
                        field=section,
                        message=(
                            f"Infra-Sektion '{section}' fehlt in stage_{stage}.md "
                            f"(infrastruktur={fm.get('infrastruktur')!r} != none -> Pflicht, BL-329 AK-3)."
                        ),
                        recovery_hint=_infra_recovery_hint(stage, section),
                    )
                )

    return result


def _check_vault_slice_set(stage: int, stage_dir: Path) -> StageCheckResult:
    """Validiere einen migrierten Vault-Slice-Satz via stage_slice_schema (AK-SLICE-SCHEMA).

    BL-392 AK-CONSUMER-REWRITE: ist eine Stage migriert (Vault-Slice-Verzeichnis da),
    prueft das Gate den 8-Slice-Satz mit dem Slice-Set-Validator (statt der
    Monolith-11+3-Logik) und mappt dessen missing/empty-Defekte auf Findings.
    """
    import stage_slice_schema as sss

    result = StageCheckResult(stage=stage, path=stage_dir)
    slice_result = sss.validate_slice_set(stage_dir)
    for err in slice_result.errors:
        result.findings.append(
            Finding(
                stage=stage,
                field=err.slice,
                message=err.message,
                recovery_hint=err.recovery_hint,
            )
        )
    return result


def check_stage_resolved(stage: int, target_dir: Path) -> StageCheckResult:
    """Pruefe Stage `n` ueber resolve_vault_stage (Dual-Read, BL-392 AK-CONSUMER-REWRITE).

    - Vault-Slice-Satz migriert -> Slice-Set-Validator (_check_vault_slice_set).
    - Legacy-Fallback (nicht migriert) -> die heutige Monolith-11+3-Validierung auf
      GENAU der Legacy-Datei (check_stage_file(handle.legacy_path)) — byte-identisch.
    - Nicht aufloesbar -> missing-file BLOCK (wie heute).

    `target_dir` wird als legacy_meta_dir durchgereicht, sodass das heutige
    explizite --target-dir-Verhalten erhalten bleibt.
    """
    import resolve_vault_stage as rvs

    try:
        handle = rvs.resolve_stage(stage, legacy_meta_dir=target_dir)
    except ValueError:
        # Ambiguitaet (>1 Vault-Stage-Verzeichnis fuer dieselbe Nummer) -> BLOCK.
        result = StageCheckResult(stage=stage, path=target_dir / f"stage_{stage}.md")
        result.findings.append(
            Finding(
                stage=stage,
                field="__ambiguous__",
                message=f"Mehrere Vault-Stage-Verzeichnisse fuer Stage {stage} (Ambiguitaet).",
                recovery_hint=_missing_file_recovery_hint(stage),
            )
        )
        return result

    if handle is None:
        # Weder Vault-Slice noch Legacy-Monolith -> missing (heutiges Verhalten).
        return check_stage_file(target_dir / f"stage_{stage}.md")
    if handle.is_legacy:
        return check_stage_file(handle.legacy_path)
    return _check_vault_slice_set(stage, handle.stage_dir)


def gate_stages_ready(target_dir: Path, active_stages: list[int]) -> GateResult:
    """G-TDD-STAGES-READY ueber alle aktiven Stufen. PASS gdw. jede Stage ok.

    BL-392 AK-CONSUMER-REWRITE: Stage-Resolution via resolve_vault_stage (Dual-Read) —
    KEIN direkter `target_dir / stage_N.md`-Read mehr; der Legacy-Monolith bleibt der
    Fallback (Backward-Compat), bis eine Stage in den Vault migriert ist.
    """
    gate = GateResult()
    for n in active_stages:
        gate.results.append(check_stage_resolved(n, target_dir))
    return gate


def _stage_number_from_path(path: Path) -> int:
    """Extrahiere N aus stage_N.md; Fallback 0 bei unerwartetem Namen."""
    import re

    m = re.search(r"stage_(\d+)", path.name)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_gate(gate: GateResult) -> None:
    if gate.ok:
        n = len(gate.results)
        print(f"G-TDD-STAGES-READY: PASS ({n} aktive Stufen validiert)")
        return
    print("G-TDD-STAGES-READY: BLOCK")
    for r in gate.results:
        if r.ok:
            print(f"  [PASS] stage_{r.stage}.md")
            continue
        for f in r.findings:
            print(f"  [BLOCK] stage_{f.stage}.md / {f.field}")
            print(f"     {f.message}")
            if f.recovery_hint:
                print(f"     -> {f.recovery_hint}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="G-TDD-STAGES-READY Gate (BL-033 + BL-329 AK-3 Infra-Stages)"
    )
    parser.add_argument(
        "--target-dir",
        default=".claude/meta/implementation",
        help="Verzeichnis mit stage_N.md (default: .claude/meta/implementation)",
    )
    parser.add_argument(
        "--stages",
        default="1,2,3,4,5,6",
        help="Komma-separierte aktive Stufen (default: 1,2,3,4,5,6)",
    )
    args = parser.parse_args(argv)

    target_dir = Path(args.target_dir)
    try:
        stages = [int(s.strip()) for s in args.stages.split(",") if s.strip()]
    except ValueError:
        print(f"ERROR: --stages muss komma-separierte Zahlen sein, war: {args.stages!r}", file=sys.stderr)
        return 2

    gate = gate_stages_ready(target_dir, stages)
    _print_gate(gate)
    return gate.exit_code


if __name__ == "__main__":
    # Windows-stdout default cp1252 -> Umlaute crashen. utf-8 erzwingen, fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))
