"""
BL-438 Single-Source-Resolver fuer markdown_uncoverable-Signal.

Schliesst Signal-Ort-Mismatch (coverage_per_batch vs metric_per_batch.special_flags):
das Signal kann an zwei Orten liegen — coverage_per_batch.coverage_class /
markdown_uncoverable_befund ODER metric_per_batch.special_flags. Diese Funktion
liest BEIDE Orte mechanisch (kein Modell-Judgement noetig) und gibt True zurueck
wenn irgendein Indikator gesetzt ist.

Verwender: _SDF_berater_modusEntscheidung.md SCHRITT 4.5b + SCHRITT 5
  markdown_uncoverable_gate (BL-314). INV-MODUS-1 unberuehrt — Gate liest nur
  Coverage-Daten, C3 bleibt alleiniger modus-Writer.

BL-473 Erweiterung: has_grep_harness-Detektion. Eine Spec-.md MIT grep-Harness
  (ein test_*.py referenziert den Ziel-Basename im Inhalt) ist testbar — auch
  wenn AKs partial-uncovered sind. Der Harness-Befund DOMINIERT die 5-Signal-
  Kaskade (Early-Return False = testable), damit der mechanische Tree solche
  .md nicht faelschlich nach M2 routet.
"""

from pathlib import Path


def has_grep_harness(target_basename, scripts_dir) -> bool:
    """Pruefe ob ein test_*.py im scripts_dir den Ziel-Basename im Inhalt referenziert.

    Reine Funktion (kein time/random): bei gleichem scripts_dir-Inhalt immer
    dasselbe Ergebnis. Tolerant gegenueber fehlendem/leerem/ungueltigem Verzeichnis.

    Args:
        target_basename: Basename des Ziels (mit oder ohne .md-Endung).
        scripts_dir:      Pfad zum Skript-Verzeichnis (str/Path), oder None/leer.

    Returns:
        True  sobald ein test_*.py-Inhalt den normalisierten Basename als
              Substring enthaelt.
        False bei fehlendem/ungueltigem scripts_dir oder ohne Treffer.
    """
    # Normalisierung: .md-Endung strippen
    if target_basename is None:
        return False
    normalized = str(target_basename)
    if normalized.endswith(".md"):
        normalized = normalized[: -len(".md")]
    if not normalized:
        return False

    # Tolerant: None/leer/kein-dir -> False (kein Crash)
    if not scripts_dir:
        return False
    base = Path(scripts_dir)
    if not base.is_dir():
        return False

    for test_file in sorted(base.glob("test_*.py")):
        try:
            content = test_file.read_text(errors="ignore")
        except (OSError, UnicodeError):
            continue
        if _references_target(content, normalized):
            return True

    return False


def _references_target(content, needle) -> bool:
    """True wenn content den needle als ECHTE Harness-Referenz enthaelt.

    CONTENT-Detektion (W12): ein test_*.py, dessen Inhalt den Ziel-Basename
    referenziert, IST ein Harness — der Default ist Substring-Match. AUSGENOMMEN
    ist eine Referenz, die explizit NEGIERT wird (das Ziel wird als nicht-
    referenziert/ausgeschlossen beschrieben, z.B. '# ... nicht nur_doku_konzept').
    Solche Erwaehnungen beschreiben das Ziel statt es zu testen. Deterministisch,
    kein Zeit-/Random-Einfluss.
    """
    _NEGATIONS = ("nicht", "not", "kein", "ohne")
    for line in content.splitlines():
        idx = line.find(needle)
        while idx != -1:
            preceding = line[:idx].rstrip().rsplit(None, 1)
            prev_word = preceding[-1].lower().strip(",.;:") if preceding else ""
            if prev_word not in _NEGATIONS:
                return True
            idx = line.find(needle, idx + 1)
    return False


def resolve_markdown_uncoverable(coverage_entry, metric_entry, target_files=None, scripts_dir=None) -> bool:
    """Pruefe ob ein Sub-Batch als markdown_uncoverable gilt.

    Liest BEIDE Signal-Orte:
      1. coverage_per_batch (coverage_class + markdown_uncoverable_befund)
      2. metric_per_batch.special_flags (Fallback, BL-438)

    Args:
        coverage_entry: dict aus DF_BATCH_STATE.coverage_per_batch[sb], oder None.
        metric_entry:   dict aus DF_BATCH_STATE.metric_per_batch[sb],   oder None.

    Returns:
        True  wenn mindestens ein Indikator gesetzt ist.
        False wenn kein Indikator gefunden (kein false-positive).
    """
    if coverage_entry is None:
        coverage_entry = {}
    if metric_entry is None:
        metric_entry = {}

    # BL-473: Harness-Dominanz GANZ AM ANFANG. Spec-.md MIT grep-Harness ist
    # testbar -> Early-Return False (testable DOMINIERT, vor der Signal-Kaskade).
    # Nur aktiv wenn beide kwargs gesetzt sind; sonst byte-identische Alt-Kaskade.
    if target_files and scripts_dir:
        for name in target_files:
            if name and str(name).endswith(".md"):
                if has_grep_harness(Path(name).name, scripts_dir):
                    return False

    # Signal-Ort 1a: coverage_class == "markdown_target_uncoverable"
    if coverage_entry.get("coverage_class") == "markdown_target_uncoverable":
        return True

    # Signal-Ort 1b: markdown_uncoverable_befund explizit True
    if coverage_entry.get("markdown_uncoverable_befund") is True:
        return True

    # Signal-Ort 2 (Fallback, BL-438): metric_per_batch.special_flags
    _UNCOVERABLE_FLAGS = {"markdown_uncoverable", "markdown_uncoverable_class"}
    special_flags = metric_entry.get("special_flags", [])
    if any(flag in _UNCOVERABLE_FLAGS for flag in (special_flags or [])):
        return True

    return False
