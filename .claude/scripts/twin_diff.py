"""
BL-308 Twin-Diff Pflicht-Gate (deterministischer Referenz-Konformanz-Vergleich
vor BATCH_DONE, faengt stille Drift).

conformance_diff = Anker-basierter Struktur-Vergleich (nicht naiver Text-Diff)
+ Subst-Map-Normalisierung.

twin_diff_gate = der Gate-Decider (graceful PASS wenn kein Twin -> Proportionalitaet).

Reine Logik, deterministisch.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Anker-Extraktion
# ---------------------------------------------------------------------------

def _extract_anchors(source: Any) -> set[str]:
    """Extrahiert Anker-Menge aus dict-Format oder str (zeilenweise).

    dict: erwartet {"anchors": [...]}
    str:  zeilenweise Anker (leere Zeilen werden ignoriert)
    """
    if isinstance(source, dict):
        anchors = source.get("anchors", [])
        return {str(a).strip() for a in anchors if str(a).strip()}
    if isinstance(source, str):
        return {line.strip() for line in source.splitlines() if line.strip()}
    return set()


# ---------------------------------------------------------------------------
# 1. conformance_diff
# ---------------------------------------------------------------------------

def conformance_diff(
    actual: Any,
    reference: Any,
    subst_map: list[dict] | None = None,
) -> dict:
    """5-Schritt-Anker-Mechanik (AK-9).

    Schritt 1: Substitutions-Map laden/normalisieren
    Schritt 2: Anker aus actual + reference extrahieren
    Schritt 3: Substitution auf reference-Anker anwenden
    Schritt 4: Anker-Mengen vergleichen (Mengen-Identitaet, reihenfolge-unabhaengig)
    Schritt 5: Rest-Delta via Verdikt-Matrix klassifizieren

    Args:
        actual:    dict {"anchors": [...]} oder str (zeilenweise Anker)
        reference: dict {"anchors": [...]} oder str (zeilenweise Anker)
        subst_map: Liste von {"from": str, "to": str}-Eintraegen oder None

    Returns:
        {
            'conformant': bool,
            'deviations': list[{
                'path':     str | None,
                'anchor':   str,
                'expected': str | None,
                'actual':   str | None,
                'kind':     'missing_in_actual' | 'missing_in_reference' | 'mismatch'
            }]
        }
    """
    # Schritt 1: Subst-Map normalisieren
    normalized_subst: list[dict] = subst_map if subst_map else []

    # Schritt 2: Anker extrahieren
    actual_anchors: set[str] = _extract_anchors(actual)
    reference_anchors: set[str] = _extract_anchors(reference)

    # Schritt 3: Substitution auf reference-Anker anwenden
    #            Jeder Eintrag {"from": X, "to": Y} ersetzt X durch Y in den
    #            reference-Ankern, damit sie mit actual verglichen werden koennen.
    substituted_reference: set[str] = set()
    for anchor in reference_anchors:
        result = anchor
        for entry in normalized_subst:
            src = entry.get("from", "")
            dst = entry.get("to", "")
            if src:
                result = result.replace(src, dst)
        substituted_reference.add(result)

    # Schritt 4: Mengen-Vergleich (reihenfolge-unabhaengig)
    missing_in_actual = substituted_reference - actual_anchors      # in ref, nicht in actual
    extra_in_actual = actual_anchors - substituted_reference        # in actual, nicht in ref

    # Schritt 5: Verdikt-Matrix klassifizieren
    deviations: list[dict] = []

    for anchor in sorted(missing_in_actual):
        deviations.append({
            "path": None,
            "anchor": anchor,
            "expected": anchor,
            "actual": None,
            "kind": "missing_in_actual",
        })

    for anchor in sorted(extra_in_actual):
        deviations.append({
            "path": None,
            "anchor": anchor,
            "expected": None,
            "actual": anchor,
            "kind": "missing_in_reference",
        })

    conformant = len(deviations) == 0

    return {
        "conformant": conformant,
        "deviations": deviations,
    }


# ---------------------------------------------------------------------------
# 2. format_deviations + parse_deviations
# ---------------------------------------------------------------------------

# Trenn-Marker zwischen Eintraegen im Markdown-Output
_ENTRY_SEPARATOR = "---"
_FIELD_PATTERN = re.compile(r"^- \*\*(\w+)\*\*: (.*)$")


def format_deviations(deviations: list[dict]) -> str:
    """Serialisiert eine Deviations-Liste als Markdown-String (AK-5/11).

    5-Felder-Schema pro Deviation: anchor, expected, actual, kind, severity.

    Fehlende Felder werden als leerer String ausgegeben, damit parse_deviations
    einen sauberen round-trip liefern kann.

    Args:
        deviations: Liste von Deviation-Dicts

    Returns:
        Markdown-String
    """
    if not deviations:
        return ""

    lines: list[str] = []
    for i, dev in enumerate(deviations):
        if i > 0:
            lines.append(_ENTRY_SEPARATOR)
        lines.append(f"- **anchor**: {dev.get('anchor', '')}")
        lines.append(f"- **expected**: {dev.get('expected', '')}")
        lines.append(f"- **actual**: {dev.get('actual', '')}")
        lines.append(f"- **kind**: {dev.get('kind', '')}")
        lines.append(f"- **severity**: {dev.get('severity', '')}")

    return "\n".join(lines)


def parse_deviations(md: str) -> list[dict]:
    """Parst format_deviations-Output zurueck zu list[dict] (round-trip, AK-11).

    Args:
        md: Markdown-String, Ausgabe von format_deviations

    Returns:
        Liste von Deviation-Dicts mit Feldern anchor, expected, actual, kind, severity
    """
    if not md or not md.strip():
        return []

    results: list[dict] = []

    # Teile nach Separator auf
    raw_blocks = md.strip().split(_ENTRY_SEPARATOR)
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        entry: dict = {}
        for line in block.splitlines():
            line = line.strip()
            m = _FIELD_PATTERN.match(line)
            if m:
                field, value = m.group(1), m.group(2)
                entry[field] = value
        if entry:
            results.append(entry)

    return results


# ---------------------------------------------------------------------------
# 3. twin_path
# ---------------------------------------------------------------------------

def twin_path(bl_folder: str) -> Path:
    """Twin-Ordner-Konvention (AK-13): gibt {bl_folder}/Twin/ zurueck.

    Args:
        bl_folder: Pfad zum BL-Ordner (str oder Path-kompatibel)

    Returns:
        pathlib.Path: {bl_folder}/Twin
    """
    return Path(bl_folder) / "Twin"


# ---------------------------------------------------------------------------
# 4. twin_diff_gate
# ---------------------------------------------------------------------------

def twin_diff_gate(
    actual: Any,
    reference: Any,
    twin_available: bool,
    deviations_md: str | None = None,
) -> dict:
    """Gate-Decider VOR BATCH_DONE (AK-4/8).

    Args:
        actual:         Implementierungs-Anker (dict oder str)
        reference:      Twin-Referenz-Anker (dict oder str)
        twin_available: Gibt es einen Twin? False -> graceful PASS (Proportionalitaet)
        deviations_md:  Optionale vorberechnete Deviations (Markdown-String)

    Returns:
        {
            'pass':      bool,
            'deviations': list,
            'verdict':   'PASS' | 'FAIL' | 'SKIPPED'
        }
    """
    # Kein Twin -> graceful PASS (Proportionalitaet, AK-6)
    if not twin_available:
        return {
            "pass": True,
            "deviations": [],
            "verdict": "PASS",
        }

    # Twin vorhanden -> Konformanz pruefen
    diff_result = conformance_diff(actual, reference)

    if diff_result["conformant"]:
        return {
            "pass": True,
            "deviations": [],
            "verdict": "PASS",
        }
    else:
        return {
            "pass": False,
            "deviations": diff_result["deviations"],
            "verdict": "FAIL",
        }


# ---------------------------------------------------------------------------
# 5. twin_ref_schema + validate_twin_ref
# ---------------------------------------------------------------------------

_TWIN_REF_ALLOWED: list[str] = ["IS-IDENTICAL", "IS-ADAPTED", "IS-NEW"]


def twin_ref_schema() -> dict:
    """Schema-Beschreibung des twin_ref-Feldes (AK-8).

    Returns:
        {'allowed_values': list[str], 'default': None}
    """
    return {
        "allowed_values": list(_TWIN_REF_ALLOWED),
        "default": None,
    }


def validate_twin_ref(value: Any) -> bool:
    """Validiert einen twin_ref-Wert gegen das Schema (AK-8).

    Erlaubt: 'IS-IDENTICAL' | 'IS-ADAPTED' | 'IS-NEW' | None
    Jeden anderen Wert -> False.

    Args:
        value: Zu pruefender Wert

    Returns:
        True wenn gueltig, False sonst
    """
    if value is None:
        return True
    return value in _TWIN_REF_ALLOWED
