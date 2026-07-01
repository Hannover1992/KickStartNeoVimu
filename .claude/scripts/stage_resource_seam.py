#!/usr/bin/env python3
"""stage_resource_seam.py — BL-392 batch_5 (AK-RES-SEAM): die Naht Slices -> Ressourcen-Registry.

Read-only DEKLARATIONS-Naht zwischen den atomisierten Stage-Slices (batch_1/2/3:
stage_slice_schema / resolve_vault_stage.StageHandle / die `resources.md`- +
`concurrency_class.md`-Slices) und der vorhandenen ressourcen-zentrischen
FREE/LOCKED-Registry `stage_resource_registry` (BL-247/BL-368). Sie extrahiert aus den
zwei Deklarations-Slices die Ressourcen-Deklaration einer Stage:

    stage_resources(stage_handle_or_resources_slice, concurrency_slice=None)
      -> {
          "resource_ids":     [<freie Strings>],
          "divisibility":     {<id>: "teilbar"|"unteilbar"},
          "concurrency_class": <str|None>,
          "depends_on":       [<freie Strings>],
      }

PRODUCER vs CONSUMER (W-RES-2, KEIN Doppel-Producer):
  Diese Naht ist der **PRODUCER**: sie DEKLARIERT die Ressourcen aus den Slices
  (was eine Stage braucht + ob teilbar). Sie GOVERNT NICHT — sie ruft KEIN
  acquire/release/lock auf der Registry. Die **Governance** (FREE/LOCKED-Locking,
  acquire/release/acquire_all/Region-Lock) ist der **CONSUMER**: das ist
  `stage_resource_registry` selbst, betrieben von BL-368 (Registry-Governance).
  Die Naht reicht dem Consumer nur die deklarierten resource_ids; sie nimmt nie
  ein Lock. So entsteht kein zweiter Producer und keine doppelte Lock-Semantik.

FREIER-STRING-FORMAT + ROUND-TRIP-DoD (W-RES-2 adjudiziert):
  resource_ids bleiben **freie Strings** im heutigen `concurrency_depends_on`-Format
  (z.B. "docker_integration_stack", "container_budget:max_container_parallel" mit ':').
  Die Naht enkodiert/normalisiert sie NICHT — sie reicht sie verbatim weiter. Der
  Round-Trip ist damit verlustfrei by-construction: was die Naht uebergibt, kommt aus
  der Registry via `stage_resource_registry.render()`/`lookup_free()` (intern
  `_fs_safe` -> `_fs_unsafe`) als ORIGINAL-String zurueck — inkl. ':' (das die Registry
  reversibel als `~3a` FS-safe haelt). Die Naht muss dafuer NICHTS tun ausser die
  Strings unveraendert durchzureichen.

EINGABE-FLEXIBILITAET:
  - Ein `resolve_vault_stage.StageHandle` (Vault-Slice ODER Legacy-Monolith): die Naht
    zieht die resources- + concurrency_class-Views via `handle.slice_view(...)`.
  - ODER direkt das resources-Slice-dict (+ optional das concurrency_class-Slice-dict).
  Beides liefert dieselbe Deklaration (single code path nach der View-Aufloesung).

RESSOURCEN-QUELLE (heutiges Format respektiert):
  1. Trägt der resources-Slice eine explizite `resources`-Liste (Eintraege
     {id, divisibility}), bilden deren ids die resource_ids + die divisibility-Map.
  2. Fehlt diese Liste (heutiges Format traegt die Beziehung NUR im
     `concurrency_depends_on`), leitet die Naht die resource_ids aus `depends_on`
     (freie Strings) ab — divisibility dann unbekannt -> Default `DEFAULT_DIVISIBILITY`.
  So geht kein Concern verloren, egal welches der beiden Formate die Stage traegt.

skip/leer (W-SLICE-3): ein skip-Sentinel-Slice ODER ein leerer/None-Slice -> leere
Ressourcen-Deklaration (kein Crash). "bewusst keine Ressourcen" ist legitim.

read-only: dieses Modul liest Slice-Frontmatter (in-memory dicts ODER via StageHandle)
und mutiert weder Vault noch State noch Registry. projekt-agnostisch (nur Slice-Format,
keine projekt-spezifischen Ressourcen-Werte — die kommen aus dem Vault-Slice).

Exit codes (CLI, read-only Vorschau):
  0 = Deklaration extrahiert (auch leere ist OK).
  2 = Stage nicht aufloesbar (CLI nur — die API gibt eine leere Deklaration, kein Crash).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

# Die zwei Deklarations-Slices, aus denen die Naht liest (Spiegel DECLARATION_SLICES
# in stage_slice_schema). resources -> Ressourcen + Teilbarkeit; concurrency_class ->
# concurrency_class + concurrency_depends_on.
RESOURCES_SLICE_NAME = "resources"
CONCURRENCY_SLICE_NAME = "concurrency_class"

# Default-Teilbarkeit, wenn eine resource_id NUR aus depends_on abgeleitet wird (das
# heutige Format traegt dort keine Teilbarkeit). "unteilbar" ist die sichere Annahme:
# eine Ressource ohne deklarierte Teilbarkeit wird konservativ als NICHT teilbar
# behandelt (der Consumer/Governance darf nicht versehentlich teilen). W-RES-1-Geist.
DEFAULT_DIVISIBILITY = "unteilbar"

# Erlaubte Teilbarkeits-Werte (freier-String-Deklaration, aber kanonisch zwei Werte).
DIVISIBILITY_VALUES = ("teilbar", "unteilbar")

# skip/none-Sentinels (Spiegel stage_slice_schema.SKIP_SENTINELS): "bewusst nicht da".
_SKIP_SENTINELS = ("skip", "none")


# ---------------------------------------------------------------------------
# Slice-Aufloesung (StageHandle ODER direkte Slice-dicts)
# ---------------------------------------------------------------------------


def _looks_like_stage_handle(obj: Any) -> bool:
    """True gdw. obj ein StageHandle-aehnliches Objekt ist (hat slice_view-Methode).

    Duck-Typing statt isinstance-Import, damit die Naht nicht hart an
    resolve_vault_stage koppelt (sie nutzt nur das slice_view-Protokoll, read-only).
    """
    return hasattr(obj, "slice_view") and callable(getattr(obj, "slice_view"))


def _resolve_slices(
    stage_or_resources: Union[Any, Optional[dict]],
    concurrency_slice: Optional[dict],
) -> tuple[dict, dict]:
    """Loese (resources_fm, concurrency_fm) auf — aus StageHandle ODER direkten dicts.

    - StageHandle: ziehe beide Views via slice_view (read-only). Ein None-View
      (Slice fehlt) wird zu {} normalisiert.
    - direktes dict: stage_or_resources IST der resources-Slice; concurrency_slice
      (optional) der concurrency_class-Slice.
    Beide Rueckgaben sind immer dicts (nie None) — fail-safe fuer die Extraktion.
    """
    if _looks_like_stage_handle(stage_or_resources):
        resources_fm = stage_or_resources.slice_view(RESOURCES_SLICE_NAME) or {}
        concurrency_fm = stage_or_resources.slice_view(CONCURRENCY_SLICE_NAME) or {}
        return (
            resources_fm if isinstance(resources_fm, dict) else {},
            concurrency_fm if isinstance(concurrency_fm, dict) else {},
        )
    # Direkte Slice-dicts.
    resources_fm = stage_or_resources if isinstance(stage_or_resources, dict) else {}
    concurrency_fm = concurrency_slice if isinstance(concurrency_slice, dict) else {}
    return resources_fm, concurrency_fm


# ---------------------------------------------------------------------------
# skip/leer-Erkennung (W-SLICE-3)
# ---------------------------------------------------------------------------


def _is_skip_slice(slice_fm: dict) -> bool:
    """True gdw. der Slice ein explizites skip/none-Sentinel traegt (bewusst leer)."""
    if not isinstance(slice_fm, dict):
        return True
    for sentinel in _SKIP_SENTINELS:
        value = slice_fm.get(sentinel)
        if value is True or (isinstance(value, str) and value.strip().lower() in _SKIP_SENTINELS):
            return True
    return False


# ---------------------------------------------------------------------------
# Extraktion: depends_on + concurrency_class (concurrency_class-Slice)
# ---------------------------------------------------------------------------


def _extract_depends_on(concurrency_fm: dict) -> List[str]:
    """Die concurrency_depends_on-Liste (freie Strings) — verbatim, kein Re-Encode.

    Robust: fehlt das Feld ODER ist es kein Listen-Typ -> []. Einzel-Eintraege werden
    zu str gecastet (defensiv gegen handgeschriebenes YAML), bleiben aber inhaltlich
    der Original-String (inkl. ':'), damit der Registry-Round-Trip verlustfrei ist.
    """
    if _is_skip_slice(concurrency_fm):
        return []
    raw = concurrency_fm.get("concurrency_depends_on")
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def _extract_concurrency_class(concurrency_fm: dict) -> Optional[str]:
    """Die concurrency_class (z.B. 'DEPENDS') — None wenn nicht deklariert/skip."""
    if _is_skip_slice(concurrency_fm):
        return None
    value = concurrency_fm.get("concurrency_class")
    return str(value) if value is not None else None


# ---------------------------------------------------------------------------
# Extraktion: resource_ids + divisibility (resources-Slice, Fallback depends_on)
# ---------------------------------------------------------------------------


def _normalize_divisibility(value: Any) -> str:
    """Normalisiere einen Teilbarkeits-Wert auf 'teilbar'|'unteilbar' (Default sonst).

    Freier-String-Deklaration, aber kanonisch zwei Werte. Unbekanntes/fehlendes ->
    DEFAULT_DIVISIBILITY (konservativ unteilbar, Governance darf nicht falsch teilen).
    """
    if isinstance(value, str) and value.strip().lower() in DIVISIBILITY_VALUES:
        return value.strip().lower()
    return DEFAULT_DIVISIBILITY


def _extract_explicit_resources(resources_fm: dict) -> Optional[tuple[List[str], Dict[str, str]]]:
    """Lies eine EXPLIZITE `resources`-Liste ([{id, divisibility}, ...]) aus dem Slice.

    Returns (resource_ids, divisibility) wenn eine Liste da ist, sonst None (-> Caller
    faellt auf den depends_on-Ableitungs-Pfad zurueck). Eintraege ohne 'id' werden
    uebersprungen (robust); Reihenfolge bleibt erhalten (Deklarations-Reihenfolge).
    Die ids bleiben FREIE Strings (kein Re-Encode -> Round-Trip-verlustfrei).
    """
    raw = resources_fm.get("resources")
    if not isinstance(raw, list):
        return None
    resource_ids: List[str] = []
    divisibility: Dict[str, str] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        rid = entry.get("id")
        if rid is None:
            continue
        rid = str(rid)
        resource_ids.append(rid)
        divisibility[rid] = _normalize_divisibility(entry.get("divisibility"))
    return resource_ids, divisibility


def _resource_ids_from_depends_on(depends_on: List[str]) -> tuple[List[str], Dict[str, str]]:
    """Fallback: leite resource_ids aus depends_on ab (heutiges Format, freie Strings).

    Teilbarkeit ist im depends_on-Format nicht deklariert -> DEFAULT_DIVISIBILITY.
    Duplikate werden zusammengefasst (erste Vorkommens-Reihenfolge bleibt).
    """
    resource_ids: List[str] = []
    divisibility: Dict[str, str] = {}
    for rid in depends_on:
        if rid not in divisibility:
            resource_ids.append(rid)
            divisibility[rid] = DEFAULT_DIVISIBILITY
    return resource_ids, divisibility


# ---------------------------------------------------------------------------
# Oeffentliche API: die Naht
# ---------------------------------------------------------------------------


def stage_resources(
    stage_handle_or_resources_slice: Union[Any, Optional[dict]],
    concurrency_slice: Optional[dict] = None,
) -> Dict[str, Any]:
    """Extrahiere die Ressourcen-DEKLARATION einer Stage aus ihren zwei Slices.

    Eingabe:
      - ein resolve_vault_stage.StageHandle (Vault-Slice ODER Legacy-Monolith), ODER
      - das resources-Slice-dict direkt (+ optional concurrency_slice-dict).

    Rueckgabe (PRODUCER-Deklaration, KEIN Lock genommen):
      {
        "resource_ids":     [<freie Strings, verbatim>],
        "divisibility":     {<id>: "teilbar"|"unteilbar"},
        "concurrency_class": <str|None>,
        "depends_on":       [<freie Strings, verbatim>],
      }

    Producer-only (W-RES-2): diese Funktion ruft NIE acquire/release/lock — sie
    deklariert nur. Die Governance ist BL-368 (stage_resource_registry, der Consumer).

    Round-Trip-DoD (W-RES-2): die resource_ids/depends_on werden verbatim
    durchgereicht; ihr Round-Trip via stage_resource_registry (render/_fs_unsafe) ist
    damit verlustfrei (inkl. ':'-Eintraege). Die Naht enkodiert nichts.

    skip/leer/None (W-SLICE-3): skip-Sentinel ODER leerer/None-Slice -> leere
    Deklaration (kein Crash). read-only.
    """
    resources_fm, concurrency_fm = _resolve_slices(
        stage_handle_or_resources_slice, concurrency_slice
    )

    # concurrency_class-Slice -> depends_on (freie Strings) + concurrency_class.
    depends_on = _extract_depends_on(concurrency_fm)
    concurrency_class = _extract_concurrency_class(concurrency_fm)

    # resources-Slice -> resource_ids + divisibility. Skip/leer -> Fallback auf
    # depends_on (das die Ressourcen-Beziehung im heutigen Format traegt).
    resource_ids: List[str]
    divisibility: Dict[str, str]
    explicit = None if _is_skip_slice(resources_fm) else _extract_explicit_resources(resources_fm)
    if explicit is not None:
        resource_ids, divisibility = explicit
        # depends_on kann zusaetzliche, nicht in der resources-Liste deklarierte ids
        # tragen (z.B. budget-Constraints) -> additiv ergaenzen (Default-Teilbarkeit),
        # damit kein depends_on-Concern verloren geht.
        for rid in depends_on:
            if rid not in divisibility:
                resource_ids.append(rid)
                divisibility[rid] = DEFAULT_DIVISIBILITY
    else:
        # Kein expliziter resources-List (oder skip) -> aus depends_on ableiten.
        resource_ids, divisibility = _resource_ids_from_depends_on(depends_on)

    return {
        "resource_ids": resource_ids,
        "divisibility": divisibility,
        "concurrency_class": concurrency_class,
        "depends_on": depends_on,
    }


# ---------------------------------------------------------------------------
# CLI (read-only Vorschau: Deklaration einer Stage aus ihren Slices)
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Stage-Ressourcen-Deklarations-Naht (BL-392 AK-RES-SEAM, read-only, PRODUCER-only). "
        "Loest eine Stage via resolve_vault_stage auf und gibt die Ressourcen-Deklaration aus."
    )
    parser.add_argument("number", type=int, help="Stage-Nummer (1..N)")
    args = parser.parse_args(argv)

    # CLI nutzt den Resolver (batch_2), um aus der Stage-Nummer den Handle zu holen.
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from resolve_vault_stage import resolve_stage
    except ImportError as exc:  # SSoT/Resolver fehlt -> fail-loud (kein falsch-leeres OK).
        print(f"IMPORT_ERROR: resolve_vault_stage nicht ladbar ({exc})", file=sys.stderr)
        return 2

    handle = resolve_stage(args.number)
    if handle is None:
        print(f"NOT_FOUND: keine Stage {args.number} (Vault-Slice ODER Legacy-Monolith)", file=sys.stderr)
        return 2

    decl = stage_resources(handle)
    print(json.dumps(decl, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    # Windows-stdout default cp1252 -> Umlaute crashen. utf-8 erzwingen, fail-safe.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main(sys.argv[1:]))
