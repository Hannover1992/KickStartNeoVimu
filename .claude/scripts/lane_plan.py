#!/usr/bin/env python3
"""
lane_plan.py — BL-442 AK-5: Maschinen-Schema fuer _lane_plan.md.

Liest/schreibt LANE_PLAN YAML-Fence aus Markdown-Dateien.
Unterstuetzt Cross-Lane-Collision-Check (GAP-2 Roadmap lane-aware Fundament).

Funktionen:
  parse_lane_plan(path) -> dict   liest YAML-Fence mit LANE_PLAN-Key -> dict{lane: {...}}
  lane_of_bl(bl_id, plan) -> str|None
  is_collision(bl_id, my_lane, plan) -> bool
  write_lane_plan(path, plan) -> None  roundtrip-stabil, BOM-frei, reines LF
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# ---------------------------------------------------------------------------
# Interner Fallback-Parser fuer simple LANE_PLAN-Struktur (kein PyYAML)
# ---------------------------------------------------------------------------

def _fallback_parse_yaml(text: str) -> Dict[str, Any]:
    """Minimaler YAML-Parser fuer die LANE_PLAN-Struktur.

    Unterstuetzt:
    - Top-Level-Key: LANE_PLAN:
    - 2-Space-Indent fuer Lane-Keys (A:, B:, ...)
    - 4-Space-Indent fuer String-Felder (branch:, worktree:, current:)
    - 4-Space-Indent fuer List-Felder (domain:, queue:) im Inline-Format [a, b]
    """
    result: Dict[str, Any] = {}
    current_lane: Optional[str] = None
    in_lane_plan = False

    for line in text.splitlines():
        # Top-Level LANE_PLAN: erkennen
        if re.match(r'^LANE_PLAN:\s*$', line):
            in_lane_plan = True
            continue

        if not in_lane_plan:
            continue

        # Lane-Key (2 Spaces Einzug): "  A:"
        lane_match = re.match(r'^  ([A-Za-z0-9_-]+):\s*$', line)
        if lane_match:
            current_lane = lane_match.group(1)
            result[current_lane] = {}
            continue

        if current_lane is None:
            continue

        # Feld (4 Spaces Einzug): "    branch: roadmap-a"
        field_match = re.match(r'^    ([A-Za-z0-9_]+):\s*(.*)', line)
        if not field_match:
            continue

        key = field_match.group(1)
        val = field_match.group(2).strip()

        # Inline-Liste: [a, b, c]
        if val.startswith('[') and val.endswith(']'):
            inner = val[1:-1]
            if inner.strip() == '':
                result[current_lane][key] = []
            else:
                result[current_lane][key] = [item.strip() for item in inner.split(',')]
        else:
            result[current_lane][key] = val

    return result


# ---------------------------------------------------------------------------
# parse_lane_plan
# ---------------------------------------------------------------------------

_FENCE_PATTERN = re.compile(
    r'```yaml\s*\n(.*?)```',
    re.DOTALL,
)


def parse_lane_plan(path: "str | Path") -> Dict[str, Any]:
    """Liest die Datei, findet den ```yaml ... ``` Fence mit LANE_PLAN-Key,
    parst den Inhalt und gibt das Dict unter LANE_PLAN zurueck.

    Prosa/Frontmatter ausserhalb des Fence wird ignoriert.

    Args:
        path: Pfad zur Markdown-Datei.

    Returns:
        Dict {lane: {branch, worktree, domain, current, queue}} aus LANE_PLAN.

    Raises:
        ValueError: wenn kein passender LANE_PLAN-Fence gefunden wird.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    # Alle ```yaml ... ``` Fences suchen
    for match in _FENCE_PATTERN.finditer(text):
        block = match.group(1)
        if 'LANE_PLAN:' not in block:
            continue

        # Parsen
        if _HAS_YAML:
            data = _yaml.safe_load(block)
        else:
            data = {"LANE_PLAN": _fallback_parse_yaml(block)}

        if isinstance(data, dict) and "LANE_PLAN" in data:
            return data["LANE_PLAN"]

    raise ValueError(
        f"parse_lane_plan: Kein ```yaml LANE_PLAN:```-Fence in '{path}' gefunden."
    )


# ---------------------------------------------------------------------------
# lane_of_bl
# ---------------------------------------------------------------------------

def lane_of_bl(bl_id: str, plan: Dict[str, Any]) -> Optional[str]:
    """Gibt die Lane zurueck, in deren queue ODER current das bl_id steht.

    Args:
        bl_id: BL-Identifier (z.B. "BL-442").
        plan:  Ergebnis von parse_lane_plan (dict{lane: {...}}).

    Returns:
        Lane-Key (z.B. "B") oder None wenn nicht gefunden.
    """
    for lane, entry in plan.items():
        # current pruefen
        if entry.get("current") == bl_id:
            return lane
        # queue pruefen
        queue = entry.get("queue", [])
        if bl_id in queue:
            return lane
    return None


# ---------------------------------------------------------------------------
# is_collision
# ---------------------------------------------------------------------------

def is_collision(bl_id: str, my_lane: str, plan: Dict[str, Any]) -> bool:
    """Prueft ob eine andere Lane das BL-Item bereits haelt.

    Args:
        bl_id:   BL-Identifier.
        my_lane: Eigene Lane.
        plan:    Ergebnis von parse_lane_plan.

    Returns:
        True wenn lane_of_bl(bl_id) existiert UND != my_lane; sonst False.
    """
    owner = lane_of_bl(bl_id, plan)
    if owner is None:
        return False
    return owner != my_lane


# ---------------------------------------------------------------------------
# next_bl_for_lane
# ---------------------------------------------------------------------------

def next_bl_for_lane(
    my_lane: str,
    plan: Dict[str, Any],
    done: Optional[set] = None,
) -> Optional[str]:
    """Gibt das naechste baubare BL fuer my_lane zurueck.

    Iteriert plan[my_lane]["queue"] in Reihenfolge und skippt ein BL wenn:
    - bl in done (oder in plan[my_lane]["done"] wenn done-Param=None), ODER
    - bl in plan[my_lane]["parked"] (BL-371: parked-Skip, backward-compat), ODER
    - bl wird von einer ANDEREN Lane gehalten (steht in deren queue ODER current).

    Args:
        my_lane: Eigene Lane (z.B. "B").
        plan:    Ergebnis von parse_lane_plan.
        done:    Set bereits abgeschlossener BL-IDs. Default None -> liest aus
                 plan[my_lane].get("done", []) (backward-compat: uebergebenes Set
                 wird direkt verwendet, kein Merge).

    Returns:
        Erstes nicht-geskipptes BL oder None wenn keins uebrig.
    """
    lane_entry = plan.get(my_lane, {})

    if done is None:
        # BL-371: lese done aus plan-Feld (backward-compat fuer Caller ohne done-Param)
        done = set(lane_entry.get("done", []) or [])

    # BL-371: parked-Skip (backward-compat: fehlt "parked" -> kein Skip)
    parked = set(lane_entry.get("parked", []) or [])

    queue = lane_entry.get("queue", [])

    for bl in queue:
        # Skip wenn erledigt
        if bl in done:
            continue

        # BL-371: Skip wenn geparkt
        if bl in parked:
            continue

        # Skip wenn von einer ANDEREN Lane gehalten (queue ODER current).
        # "Gehalten von anderer Lane" = bl erscheint in der anderen Lane frueher (niedrigerer Index)
        # als in my_lane's queue, ODER bl ist in current einer anderen Lane.
        # Spezialfall: BL ist current einer anderen Lane -> immer skip.
        # BL in my_lane's queue: skip nur wenn eine andere Lane es an niedrigerem Index haelt.
        def _held_by_other(bl: str, my_lane: str, plan: Dict[str, Any]) -> bool:
            # Pruefen ob eine andere Lane bl als current haelt
            for l, entry in plan.items():
                if l != my_lane and entry.get("current") == bl:
                    return True
            # Queue-Positionen: my_lane-Index vs andere Lanes
            my_q = plan.get(my_lane, {}).get("queue", [])
            my_idx = my_q.index(bl) if bl in my_q else None
            for l, entry in plan.items():
                if l == my_lane:
                    continue
                other_q = entry.get("queue", [])
                if bl in other_q:
                    other_idx = other_q.index(bl)
                    if my_idx is None or other_idx < my_idx:
                        return True
            return False

        if _held_by_other(bl, my_lane, plan):
            continue

        return bl

    return None


def park_bl(lane: str, bl_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    """BL-371 AK-3: Traegt bl_id in plan[lane]["parked"] ein (idempotent, kein Duplikat).

    Andere Felder und andere Lanes werden nicht veraendert.

    Args:
        lane:  Lane-Key (z.B. "A").
        bl_id: BL-Identifier (z.B. "BL-100").
        plan:  Ergebnis von parse_lane_plan (wird in-place mutiert UND zurueckgegeben).

    Returns:
        Mutierter plan (selbes Objekt, fuer Bequemlichkeit).
    """
    lane_entry = plan.setdefault(lane, {})
    parked = list(lane_entry.get("parked", []) or [])
    if bl_id not in parked:
        parked.append(bl_id)
    lane_entry["parked"] = parked
    return plan


# ---------------------------------------------------------------------------
# write_lane_plan
# ---------------------------------------------------------------------------

def _dump_lane_plan_yaml(plan: Dict[str, Any]) -> str:
    """Serialisiert plan als YAML-String unter LANE_PLAN-Key.

    Nutzt PyYAML falls verfuegbar, sonst manuelles Dumping.
    """
    if _HAS_YAML:
        data = {"LANE_PLAN": plan}
        return _yaml.dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
    # Manuelles Dumping (Fallback)
    lines = ["LANE_PLAN:"]
    for lane, entry in plan.items():
        lines.append(f"  {lane}:")
        for key, val in entry.items():
            if isinstance(val, list):
                items = ", ".join(str(v) for v in val)
                lines.append(f"    {key}: [{items}]")
            else:
                lines.append(f"    {key}: {val}")
    return "\n".join(lines) + "\n"


def write_lane_plan(path: "str | Path", plan: Dict[str, Any]) -> None:
    """Schreibt die Datei mit dem LANE_PLAN-yaml-Fence.

    - Roundtrip-stabil und idempotent: parse(write(parse(x))) == parse(x).
    - BOM-frei UTF-8, reines LF.
    - Wenn die Datei schon einen ```yaml LANE_PLAN```-Fence hat: diesen ersetzen.
    - Wenn kein Fence vorhanden: Fence anhaengen.

    Args:
        path: Pfad zur Markdown-Datei.
        plan: Dict {lane: {...}} (Ausgabe von parse_lane_plan).
    """
    path = Path(path)

    yaml_content = _dump_lane_plan_yaml(plan)
    new_fence = f"```yaml\n{yaml_content}```"

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        # Bestehenden LANE_PLAN-Fence ersetzen
        if '```yaml' in existing and 'LANE_PLAN:' in existing:
            # Fence mit LANE_PLAN ersetzen
            def _replace_fence(m: re.Match) -> str:
                block = m.group(1)
                if 'LANE_PLAN:' in block:
                    return new_fence
                return m.group(0)

            new_text = _FENCE_PATTERN.sub(_replace_fence, existing)
        else:
            # Anhaengen
            separator = "\n" if existing and not existing.endswith("\n") else ""
            new_text = existing + separator + "\n" + new_fence + "\n"
    else:
        new_text = new_fence + "\n"

    # BOM-frei UTF-8, reines LF
    new_text = new_text.replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(new_text.encode("utf-8"))


# ---------------------------------------------------------------------------
# advance_current
# ---------------------------------------------------------------------------

def advance_current(
    my_lane: str,
    completed_bl_id: str,
    plan: Dict[str, Any],
) -> Dict[str, Any]:
    """Rueckt current fuer my_lane weiter und traegt completed_bl_id in done[] ein.

    Mutiert plan (deepcopy empfohlen vom Caller) und gibt ihn zurueck.
    Wenn der completed_bl_id nicht mehr in queue ist (bereits entfernt): kein Fehler.
    current wird auf das erste noch-nicht-done BL nach completed_bl_id gesetzt,
    oder auf None wenn die Queue leer ist.

    Args:
        my_lane:        Eigene Lane (z.B. "A").
        completed_bl_id: Gerade abgeschlossene BL-ID (z.B. "BL-441").
        plan:           Ergebnis von parse_lane_plan.

    Returns:
        Mutierter plan (selbes Objekt, fuer Bequemlichkeit als Return-Wert).
    """
    lane_entry = plan.get(my_lane, {})

    # done[] aktualisieren (idempotent, kein Duplikat)
    done = list(lane_entry.get("done", []) or [])
    if completed_bl_id not in done:
        done.append(completed_bl_id)
    lane_entry["done"] = done

    done_set = set(done)

    # naechstes nicht-done Item in queue suchen
    queue = lane_entry.get("queue", []) or []
    next_item = None
    for bl in queue:
        if bl not in done_set:
            next_item = bl
            break

    lane_entry["current"] = next_item
    plan[my_lane] = lane_entry
    return plan


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="lane_plan.py — LANE_PLAN-Fence Reader")
    parser.add_argument("--plan", required=True, help="Pfad zur _lane_plan.md Datei")
    parser.add_argument("--show", action="store_true", help="Plan ausgeben")
    args = parser.parse_args()

    plan = parse_lane_plan(args.plan)
    if args.show:
        for lane, entry in plan.items():
            print(f"Lane {lane}: {entry}")
