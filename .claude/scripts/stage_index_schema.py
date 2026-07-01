#!/usr/bin/env python3
"""stage_index_schema.py — BL-392 batch_4 (AK-INDEX): `_index`-Slice-Schema + slice_map-Konsistenz-Check.

Schwester von stage_slice_schema.py (batch_1, 8-Slice-Satz-Validator) +
resolve_vault_stage.py (batch_2, glob-faehiger Resolver) + stage_slice_migrate.py
(batch_3, Monolith->8-Slice-Migrator). Dieses Modul formalisiert den `_index`-Slice
als Identitaets-ANKER einer Stage und prueft, dass seine `slice_map` nicht luegt.

`_index`-SCHEMA (PL-1, projekt-agnostisch — W-SCHEMA-2):
  Der `_index.md`-Frontmatter MUSS tragen:
    - `stufe` (int)            — die Stage-Nummer (Identitaet).
    - `name` (str)             — der lesbare Postfix-Name.
    - `maintainability` (Slot) — RESERVIERT, Format OFFEN (W-AK-MAINT): Boolean?
      Sub-Stage-Hierarchie (`stage_3.1`)? Zahl? batch_4 ERFINDET das Format NICHT —
      der Slot muss nur PRAESENT sein (auch `None` ist konform). Die Praezisierung
      ist die offene OQ W-AK-MAINT (Spec Sec 5).
    - `slice_map` (Map)        — concern -> Slice-Dateiname ueber die 8 kanonischen
      Slices (stage_slice_schema.CANONICAL_SLICES); ein Eintrag darf `skip` tragen
      (Concern bewusst nicht da, explizit > implizit).

slice_map-KONSISTENZ-CHECK (PL-1, der Kern):
  `check_index_slice_map(stage_handle_or_dir) -> SliceMapConsistency` prueft, dass die
  `slice_map` im `_index` GENAU die Slices listet, die real im Stage-Verzeichnis
  vorhanden sind. Realitaets-Quelle ist `resolve_vault_stage.StageHandle.slice_paths`
  (batch_2) bzw. — bei direktem Verzeichnis-Argument — das Datei-Listing:
    - `missing_in_map`: Slice liegt als Datei im Verzeichnis, fehlt aber in der Map.
    - `extra_in_map`:   Map listet einen Slice (NICHT als skip), aber die Datei fehlt.
  RED-Pfad = Map divergiert vom Verzeichnis -> `consistent=False` (BLOCK). Ein als
  `skip` markierter Map-Eintrag braucht KEINE Datei (W-SLICE-3).

PROJEKT-AGNOSTISCH (Schicht-Grenze, W-SCHEMA-2, feedback_command_layer_purity):
  Dieses Modul kodiert NUR welche Felder + welches Format (Engine). KEINE projekt-
  spezifischen Werte (kein Flavor-/Infra-konkreter Inhalt). Das Narrativ + der
  konkrete maintainability-Wert sind Vault-Sache (PL-2-Inhalt, nicht hier).

read-only: dieses Modul liest `_index.md` + das Stage-Verzeichnis-Listing und mutiert
nichts. fail-safe: fehlendes `_index.md` / Legacy-Handle (in-memory) -> consistent=False
mit Hinweis (kein Crash).

Andockung: Kern, gegen den BL-412 `/_stage sanity-check` prueft; nutzt die batch_2-
Slice-Resolution als Realitaets-Quelle (AK-INDEX, slice_map ⟷ Verzeichnis).

Exit codes (CLI):
  0 = PASS (_index-Schema valide UND slice_map konsistent)
  2 = BLOCK (Schema-Defekt ODER slice_map divergiert vom Verzeichnis)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

# Die 8 kanonischen Slices sind in stage_slice_schema (batch_1) definiert —
# single source, damit Index-Schema + Slice-Schema nie auseinanderlaufen.
from stage_slice_schema import CANONICAL_SLICES

# ---------------------------------------------------------------------------
# _index-Schema (W-SLICE-1 / AK-INDEX)
# ---------------------------------------------------------------------------

# Pflichtfelder des _index-Frontmatter (Identitaets-Anker + slice_map).
INDEX_REQUIRED_FIELDS = ("stufe", "name", "maintainability", "slice_map")

# Explizite skip/none-Sentinels in der slice_map (W-SLICE-3): "bewusst nicht da".
SKIP_SENTINELS = ("skip", "none")


# ---------------------------------------------------------------------------
# Datenmodell
# ---------------------------------------------------------------------------


@dataclass
class IndexSchemaResult:
    """Ergebnis der _index-Schema-Validierung."""

    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def exit_code(self) -> int:
        return 0 if self.valid else 2


@dataclass
class SliceMapConsistency:
    """Ergebnis des slice_map-Konsistenz-Checks (Map ⟷ Verzeichnis).

    - consistent:     True gdw. Map und reales Verzeichnis deckungsgleich (skip-aware).
    - missing_in_map: Slices, die als Datei vorliegen, aber in der Map FEHLEN.
    - extra_in_map:   Map-Eintraege (nicht skip), deren Datei im Verzeichnis fehlt.
    - note:           Optionaler Hinweis (z.B. _index.md fehlt / Legacy-Handle).
    """

    consistent: bool
    missing_in_map: list[str] = field(default_factory=list)
    extra_in_map: list[str] = field(default_factory=list)
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# _index-Schema-Validierung (dict-basiert — IO-frei)
# ---------------------------------------------------------------------------


def _is_skip_value(value: object) -> bool:
    """True gdw. ein slice_map-Wert ein skip/none-Sentinel ist (Concern bewusst nicht da)."""
    return isinstance(value, str) and value.strip().lower() in SKIP_SENTINELS


def validate_index_dict(index_fm: dict) -> IndexSchemaResult:
    """Validiere ein `_index`-Frontmatter (dict) gegen das AK-INDEX-Schema.

    Pflicht: stufe(int) + name + maintainability(Slot, Format OFFEN — nur PRAESENZ) +
    slice_map(Map). Der maintainability-Slot muss vorhanden sein, sein WERT ist aber
    nicht weiter eingeschraenkt (W-AK-MAINT offen) — auch None ist konform. Die
    slice_map muss eine Map sein; ihre INHALTLICHE Konsistenz gegen das Verzeichnis
    prueft check_index_slice_map (das braucht die Platte).
    """
    result = IndexSchemaResult()
    index_fm = index_fm if isinstance(index_fm, dict) else {}

    # Pflichtfeld-Praesenz (maintainability: PRAESENZ genuegt, None erlaubt).
    for field_name in INDEX_REQUIRED_FIELDS:
        if field_name not in index_fm:
            result.errors.append(
                f"_index: Pflichtfeld '{field_name}' fehlt "
                f"(BL-392 AK-INDEX: stufe/name/maintainability/slice_map sind Pflicht)."
            )

    # stufe MUSS int sein (Identitaets-Anker; '3' als String ist ein Defekt).
    if "stufe" in index_fm and not isinstance(index_fm["stufe"], int):
        result.errors.append(
            f"_index: 'stufe' muss int sein (ist {type(index_fm['stufe']).__name__}: "
            f"{index_fm['stufe']!r}) — die Stage-Nummer, nicht ihre String-Form."
        )

    # name MUSS ein nicht-leerer String sein.
    if "name" in index_fm:
        name = index_fm["name"]
        if not isinstance(name, str) or not name.strip():
            result.errors.append("_index: 'name' muss ein nicht-leerer String sein (lesbarer Postfix).")

    # slice_map MUSS eine Map sein (kein Liste/String).
    if "slice_map" in index_fm and not isinstance(index_fm["slice_map"], dict):
        result.errors.append(
            f"_index: 'slice_map' muss eine Map (concern -> Slice-Dateiname) sein, "
            f"ist {type(index_fm['slice_map']).__name__}."
        )

    # maintainability: bewusst KEINE Format-Pruefung (W-AK-MAINT offen, Slot reserviert).
    # PRAESENZ wird oben ueber INDEX_REQUIRED_FIELDS erzwungen; der Wert (None/Bool/
    # Sub-Stage-String/Zahl) bleibt frei, bis die OQ adjudiziert ist.

    return result


# ---------------------------------------------------------------------------
# slice_map-Bau aus dem realen Verzeichnis (Round-Trip-Helfer)
# ---------------------------------------------------------------------------


def build_slice_map(stage_dir: Union[str, Path]) -> dict[str, str]:
    """Baue die `slice_map` aus den real vorhandenen `{slice}.md`-Dateien eines Verzeichnisses.

    Pro kanonischem Slice: liegt `{slice}.md` im Verzeichnis -> Dateiname; sonst der
    explizite `skip`-Sentinel (W-SLICE-3: ein nicht vorhandener Concern wird bewusst
    als skip markiert, nicht weggelassen). Eine so gebaute Map ist per Konstruktion
    konsistent (check_index_slice_map gibt consistent=True).
    """
    stage_dir = Path(stage_dir)
    smap: dict[str, str] = {}
    for slice_name in CANONICAL_SLICES:
        if (stage_dir / f"{slice_name}.md").exists():
            smap[slice_name] = f"{slice_name}.md"
        else:
            smap[slice_name] = "skip"
    return smap


# ---------------------------------------------------------------------------
# slice_map-Konsistenz-Check (der Kern — Map ⟷ Verzeichnis)
# ---------------------------------------------------------------------------


def _read_index_slice_map(stage_dir: Path) -> Optional[dict]:
    """Lies die `slice_map` aus `{stage_dir}/_index.md`. None wenn _index.md / slice_map fehlt."""
    index_path = stage_dir / "_index.md"
    fm = _parse_frontmatter(index_path)
    if not isinstance(fm, dict):
        return None
    smap = fm.get("slice_map")
    return smap if isinstance(smap, dict) else None


def _present_slice_files(stage_dir: Path) -> set[str]:
    """Die kanonischen Slices, die als `{slice}.md` real im Verzeichnis liegen."""
    return {name for name in CANONICAL_SLICES if (stage_dir / f"{name}.md").exists()}


def _consistency_from_dir(stage_dir: Path) -> SliceMapConsistency:
    """Konsistenz-Check gegen ein echtes Stage-Verzeichnis (Datei-Listing als Realitaet)."""
    if not stage_dir.exists() or not stage_dir.is_dir():
        return SliceMapConsistency(
            consistent=False,
            note=f"Stage-Verzeichnis fehlt: {stage_dir}",
        )

    smap = _read_index_slice_map(stage_dir)
    if smap is None:
        return SliceMapConsistency(
            consistent=False,
            note=f"_index.md fehlt oder traegt keine slice_map: {stage_dir / '_index.md'}",
        )

    present = _present_slice_files(stage_dir)

    # missing_in_map: Datei da, aber kein Map-Eintrag.
    missing_in_map = sorted(present - set(smap.keys()))

    # extra_in_map: Map listet einen Slice (NICHT als skip), aber die Datei fehlt.
    extra_in_map = sorted(
        name
        for name, value in smap.items()
        if name in CANONICAL_SLICES and not _is_skip_value(value) and name not in present
    )

    consistent = not missing_in_map and not extra_in_map
    return SliceMapConsistency(
        consistent=consistent,
        missing_in_map=missing_in_map,
        extra_in_map=extra_in_map,
    )


def check_index_slice_map(stage_handle_or_dir) -> SliceMapConsistency:
    """Prueft: die `slice_map` im `_index` listet GENAU die real vorhandenen Slices.

    Akzeptiert ENTWEDER:
      - ein `resolve_vault_stage.StageHandle` (batch_2; nutzt `stage_dir` als Realitaets-
        Quelle — ein Legacy/in-memory-Handle hat keinen `stage_dir` -> consistent=False
        mit Hinweis, kein Crash), ODER
      - direkt ein Stage-Verzeichnis (Path/str).

    Realitaets-Quelle ist immer das Datei-Listing des Stage-Verzeichnisses (die echten
    `{slice}.md`); die `slice_map` aus `_index.md` wird dagegen geprueft. Divergenz ->
    consistent=False (BLOCK) mit missing_in_map / extra_in_map. skip-markierte Map-
    Eintraege brauchen KEINE Datei (W-SLICE-3 explizit > implizit).
    """
    # Handle-Pfad (Duck-Typing auf das StageHandle-Interface): hat es stage_dir/is_legacy?
    stage_dir = getattr(stage_handle_or_dir, "stage_dir", None)
    is_legacy = getattr(stage_handle_or_dir, "is_legacy", None)

    if is_legacy is True or (stage_dir is None and not isinstance(stage_handle_or_dir, (str, Path))):
        # Legacy-Handle (in-memory, kein echtes Verzeichnis) ODER ein Handle ohne stage_dir:
        # der Datei-basierte Konsistenz-Check ist nicht anwendbar -> fail-safe.
        return SliceMapConsistency(
            consistent=False,
            note=(
                "Legacy/in-memory Handle ohne Stage-Verzeichnis: slice_map-Konsistenz "
                "ist nur auf einen migrierten Vault-Slice-Satz anwendbar (kein Crash)."
            ),
        )

    if stage_dir is not None:
        return _consistency_from_dir(Path(stage_dir))

    # Direktes Verzeichnis-Argument (Path/str).
    return _consistency_from_dir(Path(stage_handle_or_dir))


# ---------------------------------------------------------------------------
# Frontmatter-Parsing (Spiegel stage_slice_schema/resolve_vault_stage)
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: Path) -> Optional[dict]:
    """Lies das YAML-Frontmatter (zwischen den ersten zwei '---') aus path.

    None wenn die Datei fehlt ODER kein Frontmatter-Block da ist. utf-8 mit
    errors='replace' (robust gegen handgeschriebene Umlaute).
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_result(stage_dir: Path, schema_res: IndexSchemaResult, cons: SliceMapConsistency) -> None:
    ok = schema_res.valid and cons.consistent
    if ok:
        print(f"STAGE-INDEX: PASS ({stage_dir} — _index-Schema valide + slice_map konsistent)")
        return
    print(f"STAGE-INDEX: BLOCK ({stage_dir})")
    for err in schema_res.errors:
        print(f"  [SCHEMA] {err}")
    if not cons.consistent:
        if cons.note:
            print(f"  [SLICE-MAP] {cons.note}")
        for name in cons.missing_in_map:
            print(f"  [SLICE-MAP] '{name}' liegt im Verzeichnis, fehlt aber in slice_map.")
        for name in cons.extra_in_map:
            print(f"  [SLICE-MAP] slice_map listet '{name}', aber die Datei fehlt (nicht skip).")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="_index-Slice-Schema + slice_map-Konsistenz-Check (BL-392 AK-INDEX)."
    )
    parser.add_argument(
        "stage_dir",
        help="Stage-Verzeichnis mit _index.md + den {slice}.md-Slices",
    )
    args = parser.parse_args(argv)

    stage_dir = Path(args.stage_dir)
    index_fm = _parse_frontmatter(stage_dir / "_index.md") or {}
    schema_res = validate_index_dict(index_fm)
    cons = check_index_slice_map(stage_dir)
    _print_result(stage_dir, schema_res, cons)
    return 0 if (schema_res.valid and cons.consistent) else 2


if __name__ == "__main__":
    # Windows-stdout default cp1252 -> Umlaute crashen. utf-8 erzwingen, fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))
