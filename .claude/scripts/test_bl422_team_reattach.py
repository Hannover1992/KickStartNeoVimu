"""
BL-422 AK-3 Content-Verify Tests — RED phase (Stufe 1, Iteration 1)

Testziel: _A_orchestrate.md soll Team-Kontext-Resilienz dokumentieren:
  - Re-Attach an bestehendes Team (statt Neu-Anlage bei TeamCreate-Re-Establishment)
  - Task-Board-Persistenz auch nach Kontext-Wachstum / Session-Drift

Diese Tests FAILEN jetzt (RED) weil die Dokumentation noch nicht existiert.
KEINE Impl in diesem Schritt.
"""

import pathlib
import re

REPO_ROOT = pathlib.Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
A_ORCHESTRATE_PATH = REPO_ROOT / ".claude" / "commands" / "_A_orchestrate.md"


def _read_content() -> str:
    """Liest _A_orchestrate.md und gibt den Inhalt zurueck."""
    return A_ORCHESTRATE_PATH.read_text(encoding="utf-8")


def test_a_orchestrate_documents_reattach():
    """
    _A_orchestrate.md muss Re-Attach-Resilienz-Doku enthalten:
      - Keyword "re-attach" ODER "Re-Attach" ODER "reattach"
      - Keyword "Task-Board" ODER "task_board"
      - Keyword "BL-422"
      - Keyword "Session-Drift" ODER "Drift" allein reicht NICHT —
        es muss ein Bezug zu Re-Attach-Kontext vorhanden sein.

    FAILt jetzt = RED (Doku noch nicht geschrieben).
    """
    content = _read_content()

    # Pruefe re-attach Varianten
    has_reattach = bool(
        re.search(r"re-attach|Re-Attach|reattach", content, re.IGNORECASE)
    )
    assert has_reattach, (
        "FAIL (RED): _A_orchestrate.md enthaelt KEIN 're-attach'/'Re-Attach'/'reattach'. "
        "AK-3 Doku fehlt noch — erwartet nach GREEN-Phase."
    )

    # Pruefe Task-Board Varianten
    has_taskboard = bool(re.search(r"Task-Board|task_board", content))
    assert has_taskboard, (
        "FAIL (RED): _A_orchestrate.md enthaelt KEIN 'Task-Board'/'task_board'. "
        "AK-3 Task-Board-Persistenz-Doku fehlt noch."
    )

    # Pruefe BL-422 Referenz
    has_bl422 = "BL-422" in content
    assert has_bl422, (
        "FAIL (RED): _A_orchestrate.md enthaelt KEIN 'BL-422'. "
        "Traceability-Referenz fehlt noch."
    )

    # Pruefe Session-Drift im Re-Attach-Kontext
    # "Drift" existiert schon — aber Re-Attach-Kontext muss nahe dabei stehen
    # Pruefe ob re-attach UND Session-Drift im gleichen Abschnitt vorkommen
    has_session_drift_with_reattach = bool(
        re.search(r"(?:re-attach|reattach).*?(?:Session-Drift|Drift)", content, re.IGNORECASE | re.DOTALL)
        or re.search(r"(?:Session-Drift).*?(?:re-attach|reattach)", content, re.IGNORECASE | re.DOTALL)
    )
    assert has_session_drift_with_reattach, (
        "FAIL (RED): _A_orchestrate.md verbindet 're-attach' nicht mit 'Session-Drift'. "
        "AK-3 Resilience-Kontext fehlt noch."
    )


def test_a_orchestrate_taskboard_persistence():
    """
    _A_orchestrate.md muss Task-Board-Persistenz dokumentieren:
      - "Task-Board" ODER "task_board" UND
      - "erhalten" ODER "persist" ODER "verloren" (als Negation — "NICHT verloren")

    FAILt jetzt = RED (Persistenz-Doku noch nicht geschrieben).
    """
    content = _read_content()

    # Pruefe Task-Board Varianten
    has_taskboard = bool(re.search(r"Task-Board|task_board", content))
    assert has_taskboard, (
        "FAIL (RED): _A_orchestrate.md enthaelt KEIN 'Task-Board'/'task_board'. "
        "AK-3 Task-Board-Doku fehlt noch."
    )

    # Pruefe Persistenz-Vokabular
    has_persistence_vocab = bool(
        re.search(r"erhalten|persist|verloren", content, re.IGNORECASE)
        and re.search(r"Task-Board|task_board", content)
    )
    assert has_persistence_vocab, (
        "FAIL (RED): _A_orchestrate.md dokumentiert keine Task-Board-Persistenz "
        "('erhalten'/'persist'/'verloren' im Task-Board-Kontext). "
        "AK-3 Persistenz-Aussage fehlt noch."
    )

    # Haerterer Check: Persistenz-Aussage muss in Naehe von Task-Board stehen
    # Extrahiere Abschnitte die Task-Board erwaehnen und pruefe Naehe zu Persistenz-Worten
    taskboard_sections = []
    for match in re.finditer(r"Task-Board|task_board", content):
        start = max(0, match.start() - 300)
        end = min(len(content), match.end() + 300)
        taskboard_sections.append(content[start:end])

    has_persistence_near_taskboard = any(
        re.search(r"erhalten|persist|verloren|Kontext-Wachstum|Re-Establishment", section, re.IGNORECASE)
        for section in taskboard_sections
    )
    assert has_persistence_near_taskboard, (
        "FAIL (RED): Task-Board-Erwaehnung in _A_orchestrate.md hat KEINEN Persistenz-Kontext "
        "('erhalten'/'persist'/'verloren'/'Kontext-Wachstum' in Naehe). "
        "AK-3 Task-Board-Persistenz-Semantik fehlt noch."
    )
