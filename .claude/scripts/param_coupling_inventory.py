#!/usr/bin/env python3
"""
param_coupling_inventory.py — BL-159 AK-5b PL-AK5b-07 / PL-AK5b-09

CLI: python param_coupling_inventory.py [scan|verify]

Mode scan:
  Parsed _param.md, sucht nach "if Y -> set X" Mustern (implizite Kopplungen),
  gibt Markdown-Tabelle aus.

Mode verify:
  Prueft ob alle gefundenen Kopplungen entweder als Validation (erlaubt) oder
  als explizit deklariert (mit HiL-Kommentar in Kopplungs-Matrix) gelten.

Exit-Codes:
  0 = OK (keine Kopplungen oder alle explizit deklariert)
  1 = WARN (nur Validations gefunden, keine impliziten Werte-Mutationen)
  2 = ERROR (implizite Kopplungen ohne HiL-Confirm-Dokumentation gefunden)
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field

# Pfade relativ zum Skript-Verzeichnis
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PARAM_MD = PROJECT_ROOT / ".claude" / "commands" / "_param.md"

# Muster fuer implizite Kopplungen: "bei X setze Y" oder "X=true → Y=Z"
# Erkennt Saetze wie: "dark_factory=true setzt hil=off" oder "A=true → B=C"
COUPLING_PATTERNS = [
    # "Param A → Param B" oder "A -> B" (Pfeil-Notation)
    re.compile(
        r"`(?P<src_param>[a-z_]+)=(?P<src_val>[a-z_]+)`\s*(?:→|->)\s*`(?P<tgt_param>[a-z_]+)=(?P<tgt_val>[a-z_]+)`",
        re.IGNORECASE,
    ),
    # "Bei X=true: setze Y=Z" (Schritt-Notation)
    re.compile(
        r"bei\s+`?(?P<src_param>[a-z_]+)=(?P<src_val>[a-z_]+)`?.*?setze\s+`?(?P<tgt_param>[a-z_]+)=(?P<tgt_val>[a-z_]+)`?",
        re.IGNORECASE | re.DOTALL,
    ),
    # "X=true mutiert Y=Z" (Mutations-Notation)
    re.compile(
        r"`(?P<src_param>[a-z_]+)=(?P<src_val>[a-z_]+)`\s+mutiert\s+`(?P<tgt_param>[a-z_]+)=(?P<tgt_val>[a-z_]+)`",
        re.IGNORECASE,
    ),
]

# Muster fuer Validations (erlaubt): ceiling >= floor, etc.
VALIDATION_PATTERNS = [
    re.compile(r"ceiling.*?>=.*?floor", re.IGNORECASE),
    re.compile(r"validier", re.IGNORECASE),
    re.compile(r"FEHLER.*?darf nicht", re.IGNORECASE),
    re.compile(r"INV-.*?\d+.*?Validat", re.IGNORECASE),
]

# Erlaubte Kopplungs-Quellen laut Kopplungs-Matrix (AK-5b)
MATRIX_ALLOWED: set[tuple[str, str, str, str]] = {
    ("dark_factory", "true", "hil", "off"),
    ("dark_factory", "true", "GLOBAL_MODUS", "big_dark_factory"),
}

# Schluessel-Woerter die HiL-Dokumentation anzeigen
HIL_KEYWORDS = ["hil-pause", "hil_pause", "user-confirm", "user_confirm", "ownership-guard", "ownership_guard"]


@dataclass
class CouplingFinding:
    src_param: str
    src_val: str
    tgt_param: str
    tgt_val: str
    context: str
    lineno: int
    is_validation: bool = False
    is_matrix_declared: bool = False
    has_hil_comment: bool = False
    coupling_class: str = field(default="UNBEKANNT")

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.src_param, self.src_val, self.tgt_param, self.tgt_val)

    @property
    def status(self) -> str:
        if self.is_validation:
            return "VALIDATION (erlaubt)"
        if self.is_matrix_declared and self.has_hil_comment:
            return "EXPLIZIT (Matrix + HiL)"
        if self.is_matrix_declared:
            return "MATRIX-DEKLARIERT"
        return "IMPLIZIT — HiL fehlt"


def load_param_md() -> list[str]:
    if not PARAM_MD.exists():
        print(f"FEHLER: _param.md nicht gefunden unter {PARAM_MD}", file=sys.stderr)
        sys.exit(2)
    return PARAM_MD.read_text(encoding="utf-8").splitlines()


def is_validation_context(line: str, context: str) -> bool:
    """Pruefte ob ein Treffer in einem Validations-Kontext liegt."""
    return any(p.search(context) for p in VALIDATION_PATTERNS)


def has_hil_in_context(context: str) -> bool:
    """Prueft ob der Kontext HiL-Dokumentation enthaelt."""
    lower = context.lower()
    return any(kw in lower for kw in HIL_KEYWORDS)


def determine_coupling_class(src_param: str, tgt_param: str, is_matrix: bool) -> str:
    """Bestimmt die Kopplungs-Klasse analog zur Kopplungs-Matrix."""
    if src_param == "dark_factory" and tgt_param == "hil":
        return "KRITISCH"
    if src_param == "dark_factory" and tgt_param in ("GLOBAL_MODUS", "global_modus"):
        return "HOCH"
    if is_matrix:
        return "HOCH"
    return "UNBEKANNT"


def scan_couplings(lines: list[str]) -> list[CouplingFinding]:
    """Scannt _param.md nach impliziten Kopplungen, gibt Liste zurueck."""
    findings: list[CouplingFinding] = []
    seen_keys: set[tuple[str, str, str, str]] = set()

    for lineno, line in enumerate(lines, start=1):
        # Kontext: 2 Zeilen vor und nach fuer HiL-Erkennung
        ctx_start = max(0, lineno - 3)
        ctx_end = min(len(lines), lineno + 3)
        context = "\n".join(lines[ctx_start:ctx_end])

        for pattern in COUPLING_PATTERNS:
            for match in pattern.finditer(line):
                src_param = match.group("src_param")
                src_val = match.group("src_val")
                tgt_param = match.group("tgt_param")
                tgt_val = match.group("tgt_val")
                key = (src_param, src_val, tgt_param, tgt_val)

                if key in seen_keys:
                    continue
                seen_keys.add(key)

                is_val = is_validation_context(line, context)
                is_matrix = key in MATRIX_ALLOWED
                has_hil = has_hil_in_context(context)
                cls = determine_coupling_class(src_param, tgt_param, is_matrix)

                findings.append(CouplingFinding(
                    src_param=src_param,
                    src_val=src_val,
                    tgt_param=tgt_param,
                    tgt_val=tgt_val,
                    context=line.strip(),
                    lineno=lineno,
                    is_validation=is_val,
                    is_matrix_declared=is_matrix,
                    has_hil_comment=has_hil,
                    coupling_class=cls,
                ))

    return findings


def render_table(findings: list[CouplingFinding]) -> str:
    """Gibt Markdown-Tabelle der Kopplungen aus."""
    if not findings:
        return "_Keine Kopplungen gefunden._\n"

    header = (
        "| Zeile | Parameter A | Wert A | Parameter B | Wert B | Klasse | Status |\n"
        "|-------|-------------|--------|-------------|--------|--------|--------|\n"
    )
    rows = []
    for f in findings:
        rows.append(
            f"| {f.lineno} | `{f.src_param}` | `{f.src_val}` | `{f.tgt_param}` | `{f.tgt_val}` "
            f"| {f.coupling_class} | {f.status} |"
        )
    return header + "\n".join(rows) + "\n"


def cmd_scan() -> int:
    """Mode scan: Gibt Kopplungs-Inventar als Markdown-Tabelle aus."""
    lines = load_param_md()
    findings = scan_couplings(lines)

    print("## Kopplungs-Inventar — _param.md\n")
    print(f"Quelle: `{PARAM_MD}`\n")
    print(render_table(findings))

    implizit = [f for f in findings if not f.is_validation and not f.is_matrix_declared]
    validations = [f for f in findings if f.is_validation]
    matrix = [f for f in findings if f.is_matrix_declared]

    print(f"**Zusammenfassung:** {len(findings)} Kopplungen gefunden.")
    print(f"- Matrix-deklariert: {len(matrix)}")
    print(f"- Validations (erlaubt): {len(validations)}")
    print(f"- Implizit ohne HiL-Dokumentation: {len(implizit)}")

    if implizit:
        return 2
    if validations:
        return 1
    return 0


def cmd_verify() -> int:
    """Mode verify: Prueft ob alle Kopplungen entweder Validation oder explizit sind."""
    lines = load_param_md()
    findings = scan_couplings(lines)

    errors: list[CouplingFinding] = []
    warnings: list[CouplingFinding] = []

    for f in findings:
        if f.is_validation:
            continue
        if f.is_matrix_declared and f.has_hil_comment:
            continue
        if f.is_matrix_declared:
            # Matrix-deklariert aber kein HiL-Kommentar im Kontext
            warnings.append(f)
        else:
            # Vollstaendig undokumentierte implizite Kopplung
            errors.append(f)

    print("## Kopplungs-Verification — _param.md\n")

    if errors:
        print("### FEHLER: Implizite Kopplungen ohne HiL-Dokumentation\n")
        print(render_table(errors))

    if warnings:
        print("### WARNUNG: Matrix-deklariert, HiL-Kontext nicht klar\n")
        print(render_table(warnings))

    if not errors and not warnings:
        print("OK: Alle Kopplungen sind entweder Validations oder Matrix-deklariert mit HiL.")
        return 0

    if errors:
        print(f"FEHLER: {len(errors)} implizite Kopplung(en) ohne Dokumentation gefunden. "
              "INV-COUP-1 verletzt.")
        return 2

    print(f"WARNUNG: {len(warnings)} Matrix-deklariert, HiL-Nachweis unklar.")
    return 1


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "scan"

    if mode == "scan":
        sys.exit(cmd_scan())
    elif mode == "verify":
        sys.exit(cmd_verify())
    else:
        print(f"Unbekannter Mode: {mode!r}. Nutze 'scan' oder 'verify'.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
