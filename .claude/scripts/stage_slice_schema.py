#!/usr/bin/env python3
"""stage_slice_schema.py — BL-392 batch_1 (AK-SLICE-SCHEMA): globaler Stage-Slice-Schema-Validator.

Schwester von tdd_stages_ready.py: hebt den Stage-Schema-Check vom monolithischen
stage_N.md-Frontmatter auf den ATOMAREN 8-Slice-Satz (BL-392). Eine Stage ist nach
Atomisierung ein Verzeichnis aus 8 Slice-Dateien (1 Datei pro Concern), nicht mehr
ein YAML-Block in einer Datei.

KANONISCHE 8 SLICES (W-SLICE-1, W-AK-MON: Monitor in execute, KEIN 9.):
  _index, execute, setup, teardown, health_check, resources,
  concurrency_class, exit_criteria

PFLICHT-REGELN:
  - IMMER Pflicht: _index + execute + exit_criteria.
  - Pflicht WENN resources.infrastruktur NICHT in {none, skip}: setup + teardown
    + health_check (exakt der Spiegel von tdd_stages_ready.stage_needs_infra —
    nur dass die Infra-Quelle jetzt der resources-Slice ist, nicht das
    Monolith-Frontmatter).
  - resources + concurrency_class sind Deklarations-Slices (immer erwartet als
    Teil des 8-Satzes; ihr Fehlen ist eine Slice-Set-Unvollstaendigkeit, aber sie
    sind nicht Always-Required im Sinne der Pflicht-3 — sie tragen Deklaration,
    kein Lifecycle-Concern).

SKIP-SENTINEL (W-SLICE-3, explizit > implizit — verschaerft tdd_stages_ready._is_missing):
  Hat eine Stage einen Concern NICHT (z.B. Stage-1-Unit-Test braucht kein Setup),
  traegt der Slice EXPLIZIT skip/none (`skip: true` / `none: true` / Concern-Feld ==
  "skip"/"none"). Ein LEERER Slice (Datei da, aber Concern-Feld weder gesetzt noch
  skip/none) ist BLOCK mit korrektivem Recovery-Hint. Das ist die Naht gegen
  _is_missing: dort galt intentional-blank (test_projekte: []) als VORHANDEN; hier
  muss "bewusst nicht da" ein explizites skip/none-Sentinel sein, damit
  "Concern bewusst nicht da" von "Concern vergessen/leer" unterscheidbar bleibt.

PROJEKT-AGNOSTISCH (Schicht-Grenze, W-SCHEMA-2, feedback_command_layer_purity):
  Dieses Modul kodiert NUR welche Slices + welches Format (Engine). KEINE
  projekt-spezifischen Werte (kein DCSRE-/docker-Inhalt). Die Slice-INHALTE
  (testbefehl, echte Constraints, Narrativ) sind Vault-Sache (spaetere Batches).

EINGABE / AUSGABE:
  - validate_slice_dict(slice_set: dict) — slice_name -> Frontmatter-dict (oder
    None fuer fehlend).
  - validate_slice_set(stage_dir: Path) — Verzeichnis mit {slice_name}.md-Dateien
    (read-only, fail-safe: fehlendes Verzeichnis -> alle Pflicht-Slices missing).
  - Beide liefern ein SliceSchemaResult mit {valid, missing_slices, errors}.

Andockung: Kern, gegen den BL-412 `/_stage sanity-check` prueft; Konsument der
resolve_vault_stage-Slice-Resolution (BL-392 AK-GLOB, AK-CONSUMER-REWRITE).

Exit codes (CLI):
  0 = PASS (Slice-Satz konform)
  2 = BLOCK (mindestens ein Pflicht-Slice fehlt / leer)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Kanonische Slice-Struktur (W-SLICE-1)
# ---------------------------------------------------------------------------

# Die 8 kanonischen Slices in Lese-Reihenfolge.
CANONICAL_SLICES = (
    "_index",
    "execute",
    "setup",
    "teardown",
    "health_check",
    "resources",
    "concurrency_class",
    "exit_criteria",
)

# IMMER Pflicht — unabhaengig von Infra.
ALWAYS_REQUIRED_SLICES = ("_index", "execute", "exit_criteria")

# Pflicht NUR fuer Infra-Stages (resources.infrastruktur != none/skip).
# Spiegel von tdd_stages_ready.INFRA_REQUIRED_SECTIONS.
INFRA_CONDITIONAL_SLICES = ("setup", "teardown", "health_check")

# Deklarations-Slices — tragen Deklaration (infra/concurrency), kein Lifecycle-Concern.
DECLARATION_SLICES = ("resources", "concurrency_class")

# Explizite skip/none-Sentinels (W-SLICE-3): "bewusst nicht da" — KONFORM.
SKIP_SENTINELS = ("skip", "none")

# Pro Slice das Concern-Leitfeld, dessen Fehlen einen LEEREN Slice markiert
# (wenn weder das Feld noch ein skip/none-Sentinel da ist). Projekt-agnostisch:
# nur die Feld-NAMEN, keine Werte.
SLICE_CONCERN_FIELD = {
    "_index": "stufe",
    "execute": "testbefehl",
    "setup": "commands",
    "teardown": "commands",
    "health_check": "command",
    "resources": "infrastruktur",
    "concurrency_class": "concurrency_class",
    # exit_criteria Concern-Leitfeld: `qg` (Abnahme-Qualitaets-Gate, IMMER-Pflicht-Nachweis).
    # Optionales Zusatzfeld `preconditions` (BL-409 AK-1, AK-SCHEMA-PL-1):
    #   preconditions:
    #     predecessor_stages: [2]          # Stage-Nummern die DONE sein muessen (list[int]|null)
    #     resources: ["gpu-pool"]          # resource_ids fuer claim/acquire_with_wait (list[str]|null)
    #     substrat:                        # Glob-Pfad-Checks ausserhalb Slice-Set (optional)
    #       - path: "Stage/stage_2_*/exit_criteria.md"
    #         required: true
    # OPTIONAL/additiv: fehlendes oder null-preconditions = bisheriges Verhalten (kein Breaking-Change).
    # Validierung der preconditions-Struktur liegt bei precondition_gate.py (BL-409), nicht hier.
    "exit_criteria": "qg",
}


# ---------------------------------------------------------------------------
# Datenmodell
# ---------------------------------------------------------------------------


@dataclass
class SliceError:
    """Ein Slice-Defekt (leer / infra-Pflicht verletzt). recovery_hint ist Pflicht."""

    slice: str
    message: str
    recovery_hint: Optional[str] = None


@dataclass
class SliceSchemaResult:
    """Ergebnis der Slice-Satz-Validierung (Ausgabe-Vertrag {valid, missing_slices, errors})."""

    missing_slices: list[str] = field(default_factory=list)
    errors: list[SliceError] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.missing_slices and not self.errors

    @property
    def exit_code(self) -> int:
        return 0 if self.valid else 2


# ---------------------------------------------------------------------------
# Infra-Erkennung (Spiegel tdd_stages_ready.stage_needs_infra) + skip-Naht
# ---------------------------------------------------------------------------


def slice_needs_infra(resources_fm: Optional[dict]) -> bool:
    """True gdw. die Stage externe Infra braucht (resources.infrastruktur != none/skip).

    Exakter Spiegel von tdd_stages_ready.stage_needs_infra, erweitert um den
    skip-Sentinel: kein infrastruktur-Feld == none-Default; infrastruktur in
    {none, skip} == keine Infra-Pflicht (Abwaertskompat + BL-392-skip-Naht).
    """
    value = (resources_fm or {}).get("infrastruktur")
    if value is None:
        return False
    return str(value).strip().lower() not in SKIP_SENTINELS


# ---------------------------------------------------------------------------
# skip-Sentinel / Leer-Erkennung (W-SLICE-3)
# ---------------------------------------------------------------------------


def _is_skip(slice_name: str, slice_fm: Optional[dict]) -> bool:
    """True gdw. der Slice ein EXPLIZITES skip/none-Sentinel traegt.

    Akzeptiert (in dieser Reihenfolge):
      - `skip: <truthy>` oder `none: <truthy>` (dedizierte Sentinel-Keys),
      - das Concern-Leitfeld dieses Slices == "skip"/"none" (z.B.
        `resources: {infrastruktur: skip}` oder `health_check: {command: none}`).
    Das ist das "bewusst nicht da"-Signal (explizit > implizit). Praezise: nur das
    Concern-Leitfeld wird auf den String-Sentinel geprueft, NICHT beliebige andere
    Felder (sonst markierte ein zufaelliges `note: none` faelschlich den ganzen
    Slice als skip).
    """
    if not isinstance(slice_fm, dict):
        return False
    for sentinel in SKIP_SENTINELS:
        if _truthy(slice_fm.get(sentinel)):
            return True
    concern = SLICE_CONCERN_FIELD.get(slice_name)
    if concern is not None:
        value = slice_fm.get(concern)
        if isinstance(value, str) and value.strip().lower() in SKIP_SENTINELS:
            return True
    return False


def _truthy(value: object) -> bool:
    """skip: true / skip: "skip" / skip: 1 -> True; None/False/leer -> False."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "ja", "on", "skip", "none")
    return False


def _is_empty(slice_name: str, slice_fm: Optional[dict]) -> bool:
    """True gdw. der Slice LEER ist: Datei/dict da, aber Concern weder gesetzt noch skip.

    Leer = das Concern-Leitfeld fehlt/None UND kein (gueltiger) skip/none-Sentinel.
    Ein explizit gesetztes Concern-Feld (auch leerer String/Liste, intentional-blank)
    gilt — wie bei tdd_stages_ready._is_missing — als VORHANDEN; nur das voellige
    Fehlen ohne skip-Markierung ist der Leer-Defekt.

    WICHTIG (Behavior-Catch): skip wird NUR fuer NICHT-Always-Required-Slices
    geehrt. Ein Always-Required-Slice (_index/execute/exit_criteria) ist der
    Identitaets-/Ausfuehrungs-/Abnahme-Anker — er DARF nicht weg-geskippt werden.
    `_index: {skip: true}` oder `execute: {skip: true}` ist daher ein Leer-Defekt,
    nicht konform (sonst koennte eine Stage ohne echten Testbefehl durch die
    sanity-check rutschen, BL-412).
    """
    if not isinstance(slice_fm, dict):
        return False  # gar nicht da -> das ist "missing", nicht "empty".
    if slice_name not in ALWAYS_REQUIRED_SLICES and _is_skip(slice_name, slice_fm):
        return False
    concern = SLICE_CONCERN_FIELD.get(slice_name)
    if concern is None:
        return False
    present = concern in slice_fm
    value = slice_fm.get(concern)
    # key-missing ODER null -> leer (intentional-blank wie [] / "" gilt als gesetzt).
    return (not present) or (value is None)


# ---------------------------------------------------------------------------
# Recovery-Hints (korrektiv — feedback_corrective_enforcement)
# ---------------------------------------------------------------------------


def _missing_slice_hint(slice_name: str, infra: bool) -> str:
    if slice_name in ALWAYS_REQUIRED_SLICES:
        reason = "Pflicht IMMER"
    elif slice_name in INFRA_CONDITIONAL_SLICES:
        reason = "Pflicht WEIL resources.infrastruktur != none/skip"
    else:
        reason = "Teil des kanonischen 8-Slice-Satzes"
    return (
        f"Slice '{slice_name}.md' fehlt im Stage-Verzeichnis ({reason}, BL-392 AK-SLICE-SCHEMA). "
        f"Slice anlegen ODER — falls Concern bewusst nicht da — explizit als skip/none-Sentinel "
        f"(LEER ist verboten). Vorlage: die 8 kanonischen Slices "
        f"(_index/execute/setup/teardown/health_check/resources/concurrency_class/exit_criteria)."
    )


def _empty_slice_hint(slice_name: str) -> str:
    concern = SLICE_CONCERN_FIELD.get(slice_name, "<concern>")
    if slice_name in ALWAYS_REQUIRED_SLICES:
        # Always-Required: skip ist KEINE Option — Concern muss real gefuellt sein.
        return (
            f"Slice '{slice_name}.md' ist LEER (Concern-Feld '{concern}' weder gesetzt noch null). "
            f"'{slice_name}' ist IMMER Pflicht (Identitaets-/Ausfuehrungs-/Abnahme-Anker) und "
            f"darf NICHT geskippt werden — Concern '{concern}' real ausfuellen "
            f"(BL-392 AK-SLICE-SCHEMA, skip nur fuer optionale Concerns)."
        )
    return (
        f"Slice '{slice_name}.md' ist LEER (Concern-Feld '{concern}' weder gesetzt noch skip/none). "
        f"Concern '{concern}' ausfuellen ODER — falls bewusst nicht da — explizit "
        f"'skip: true' bzw. 'none: true' setzen (W-SLICE-3 explizit > implizit, LEER verboten)."
    )


# ---------------------------------------------------------------------------
# Core-Validierung (dict-basiert — IO-frei)
# ---------------------------------------------------------------------------


def validate_slice_dict(slice_set: dict) -> SliceSchemaResult:
    """Validiere einen Slice-Satz (slice_name -> Frontmatter-dict).

    Ein nicht enthaltener/None Slice gilt als FEHLEND (missing_slices). Ein
    enthaltener, aber leerer Slice (Concern weder gesetzt noch skip) ist ein
    Empty-Defekt (errors). Infra-konditionale Slices werden nur gefordert, wenn
    resources.infrastruktur != none/skip.
    """
    result = SliceSchemaResult()
    slice_set = slice_set or {}

    resources_fm = slice_set.get("resources")
    needs_infra = slice_needs_infra(resources_fm if isinstance(resources_fm, dict) else None)

    # Welche Slices sind in DIESEM Satz Pflicht?
    required = set(ALWAYS_REQUIRED_SLICES) | set(DECLARATION_SLICES)
    if needs_infra:
        required |= set(INFRA_CONDITIONAL_SLICES)

    for slice_name in CANONICAL_SLICES:
        fm = slice_set.get(slice_name)
        is_present = isinstance(fm, dict)

        if slice_name in required and not is_present:
            result.missing_slices.append(slice_name)
            result.errors.append(
                SliceError(
                    slice=slice_name,
                    message=f"Pflicht-Slice '{slice_name}' fehlt im Slice-Satz.",
                    recovery_hint=_missing_slice_hint(slice_name, needs_infra),
                )
            )
            continue

        # Da, aber leer? (nur fuer praesente Slices; skip ist konform).
        if is_present and _is_empty(slice_name, fm):
            result.errors.append(
                SliceError(
                    slice=slice_name,
                    message=f"Slice '{slice_name}' ist leer (Concern weder gesetzt noch skip/none).",
                    recovery_hint=_empty_slice_hint(slice_name),
                )
            )

    return result


# ---------------------------------------------------------------------------
# Frontmatter-Parsing (eigenstaendig — Spiegel tdd_stages_ready.parse_frontmatter)
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


def load_slice_set(stage_dir: Path) -> dict:
    """Lade einen Slice-Satz aus einem Verzeichnis ({slice_name}.md -> Frontmatter).

    read-only, fail-safe: fehlende Slice-Datei -> nicht im dict (gilt dann als
    missing). Fehlt das Verzeichnis ganz -> leeres dict. Ein leeres Frontmatter
    ({}) bleibt als leeres dict erhalten (-> Empty-Defekt, nicht missing).
    """
    out: dict = {}
    if not stage_dir.exists() or not stage_dir.is_dir():
        return out
    for slice_name in CANONICAL_SLICES:
        path = stage_dir / f"{slice_name}.md"
        if not path.exists():
            continue
        fm = parse_frontmatter(path)
        # Datei da, aber kein parsbares fm -> als leeren Slice fuehren (Empty),
        # nicht als fehlend (die Datei IST da).
        out[slice_name] = fm if isinstance(fm, dict) else {}
    return out


def validate_slice_set(stage_dir: Path) -> SliceSchemaResult:
    """Validiere den Slice-Satz eines Stage-Verzeichnisses (Datei-basiert).

    Liest {slice_name}.md aus stage_dir und delegiert an validate_slice_dict.
    Fail-safe: fehlendes Verzeichnis -> alle Pflicht-Slices fehlend (kein Crash).
    """
    slice_set = load_slice_set(Path(stage_dir))
    return validate_slice_dict(slice_set)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_result(stage_dir: Path, result: SliceSchemaResult) -> None:
    if result.valid:
        print(f"STAGE-SLICE-SCHEMA: PASS ({stage_dir} — 8-Slice-Satz konform)")
        return
    print(f"STAGE-SLICE-SCHEMA: BLOCK ({stage_dir})")
    for name in result.missing_slices:
        print(f"  [MISSING] {name}.md")
    for err in result.errors:
        print(f"  [BLOCK] {err.slice} — {err.message}")
        if err.recovery_hint:
            print(f"     -> {err.recovery_hint}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage-Slice-Schema-Validator (BL-392 AK-SLICE-SCHEMA, 8 Slices + skip-Sentinel)"
    )
    parser.add_argument(
        "stage_dir",
        help="Verzeichnis mit den 8 {slice_name}.md-Slices einer Stage",
    )
    args = parser.parse_args(argv)

    stage_dir = Path(args.stage_dir)
    result = validate_slice_set(stage_dir)
    _print_result(stage_dir, result)
    return result.exit_code


if __name__ == "__main__":
    # Windows-stdout default cp1252 -> Umlaute crashen. utf-8 erzwingen, fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))
