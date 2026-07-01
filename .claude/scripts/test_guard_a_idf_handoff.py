#!/usr/bin/env python3
"""Tests fuer guard_a_idf_handoff.py (BL-226 AK-4, INV-A-GUARD-1).

TDD Stage 1 (Atomic). Template: test_guard_geist9b_sdf_post_inline.py.
Der Guard blockt das A-Ende-Signal (routing=proceed + idf_invoke_required=true im
synthetischen _manifest.md) wenn KEIN _A_postRoute-Call vorausging — Ausnahme:
DEFER- oder A_RETRY-Marker (enden A-intern, INV-A-EXCEPT-1).

RED-Ring 1 (Edge Case = Fail-Loud BLOCK-Pfad): test_proceed_without_postroute_blocked.
RED-Ring 2 (Ausnahme INV-A-EXCEPT-1 = DEFER endet A-intern): test_defer_marker_not_blocked.
RED-Ring 3 (Ausnahme INV-A-EXCEPT-1 = A_RETRY endet A-intern): test_a_retry_marker_not_blocked.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_a_idf_handoff.py"


def run_guard(manifest_text, audit_lines):
    """Schreibt ein synthetisches _manifest.md + audit.jsonl, ruft den Guard via
    subprocess (PreToolUse/Stop-Event auf das _manifest.md) und gibt das JSON-Verdikt
    zurueck. enforceProcess=true deterministisch (Gate aktiv)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix="_manifest.md", delete=False, encoding="utf-8") as mf:
        mf.write(manifest_text)
        manifest_path = mf.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write("**enforceProcess:** true\n")
        sp_path = sp.name
    env = os.environ.copy()
    env["OMNI_A_IDF_HANDOFF_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    event = {"tool_name": "Edit", "tool_input": {"file_path": manifest_path, "new_string": manifest_text}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(manifest_path).unlink(missing_ok=True)
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


def test_proceed_without_postroute_blocked():
    """MIGRIERT (BL-350 AK-2, batch_2): testete urspruenglich den Pre-Block des
    Signal-Writes (exit 2). Das enforce-AFTER-write-Redesign ENTFERNT diesen
    Enforcement-Punkt — der Signal-Write ist jetzt IMMER erlaubt (continue=True),
    weil _A_postRoute genau dieses Signal legitim schreibt (Henne-Ei). Der Block
    passiert nun am Folge-Schritt (Skill-Load _IDF_orchestrate, siehe
    test_idf_orchestrate_load_without_postroute_blocked). Das ist KEINE Schwaechung:
    der Enforcement-Punkt wurde verschoben, nicht entfernt.

    Neue Soll-Semantik: A-Ende routing=proceed + idf_invoke_required=true OHNE
    vorausgehenden _A_postRoute -> Write passt durch (exit 0)."""
    manifest = (
        "A_PIPELINE_STATE:\n"
        "  routing_target: \"IDF\"\n"
        "  idf_invoke_required: true\n"
        "  completion_signal: \"ready_for_idf\"\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"}]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, (
        f"enforce-AFTER-write: Signal-Write ist immer erlaubt (exit 0 erwartet, "
        f"Block am IDF-Eintritt), war {proc.returncode}"
    )
    assert r.get("continue") is True, \
        "Signal-Write muss continue=True liefern (Enforcement am Folge-Schritt)"


def test_defer_marker_not_blocked():
    """RED Ring 2 (Ausnahme = DEFER): A-Ende-Signal (idf_invoke_required=true,
    routing_target=IDF) ABER mit DEFER-Marker -> endet A-intern (INV-A-EXCEPT-1),
    KEIN IDF-Handoff erwartet -> exit 0 (continue), KEIN BLOCK -- auch ohne
    vorausgegangenen _A_postRoute-Call."""
    manifest = (
        "A_PIPELINE_STATE:\n"
        "  routing_target: \"IDF\"\n"
        "  idf_invoke_required: true\n"
        "  a_decision: \"DEFER\"\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"}]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (DEFER endet A-intern, kein BLOCK), war {proc.returncode}"
    assert r.get("continue") is True, \
        "DEFER-Marker (INV-A-EXCEPT-1) darf NICHT blocken (continue=true erwartet)"


def test_a_retry_marker_not_blocked():
    """RED Ring 3 (Ausnahme = A_RETRY): A-Ende-Signal (idf_invoke_required=true,
    routing_target=IDF) ABER mit A_RETRY-Marker -> endet A-intern (INV-A-EXCEPT-1),
    KEIN IDF-Handoff erwartet -> exit 0 (continue), KEIN BLOCK -- auch ohne
    vorausgegangenen _A_postRoute-Call."""
    manifest = (
        "A_PIPELINE_STATE:\n"
        "  routing_target: \"IDF\"\n"
        "  idf_invoke_required: true\n"
        "  a_decision: \"A_RETRY\"\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"}]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (A_RETRY endet A-intern, kein BLOCK), war {proc.returncode}"
    assert r.get("continue") is True, \
        "A_RETRY-Marker (INV-A-EXCEPT-1) darf NICHT blocken (continue=true erwartet)"


# ---------------------------------------------------------------------------
# BL-350 AK-1/AK-5 — RED-Ring F2: Block-scoped signal detection
# has_signal muss Signal NUR im A_PIPELINE_STATE-Block detektieren,
# NICHT im gesamten new_text (over-match auf BERATER_OUTPUTS-Prosa).
# ---------------------------------------------------------------------------

# Realistische Manifest-Fixtures: grosses Manifest mit zwei Bloecken.
_MANIFEST_SIGNAL_IN_STATE_BLOCK = """\
# _manifest.md — Testfixture BL-350 F2

## BERATER_OUTPUTS

Phase 5c (plAggregation) abgeschlossen. Kein idf_invoke_required gesetzt.
Routing bleibt intern. routing_target ist noch offen.

---

## A_PIPELINE_STATE:
  routing_target: "IDF"
  idf_invoke_required: true
  completion_signal: "ready_for_idf"
  a_decision: "proceed"
"""

_MANIFEST_SIGNAL_ONLY_IN_BERATER_OUTPUTS = """\
# _manifest.md — Testfixture BL-350 F2 (over-match-Kernfall)

## BERATER_OUTPUTS

Blocker-Dokumentation: In einem frueheren Lauf war idf_invoke_required: true
gesetzt und routing_target: "IDF" konfiguriert — das fuehrte zu einem False-Block.
Dieses Verhalten ist dokumentiert und wird hier als Prosa-Referenz festgehalten.
Aktuell: A-Pipeline laeuft noch, kein Signal aktiv.

---

## A_PIPELINE_STATE:
  routing_target: "A_INTERNAL"
  idf_invoke_required: false
  a_decision: "proceed"
"""

_MANIFEST_SPLIT_ACROSS_BLOCKS = """\
# _manifest.md — Testfixture BL-350 F2 (split-signal)

## BERATER_OUTPUTS

routing_target: "IDF" — historische Notiz aus Phase 4b.

---

## A_PIPELINE_STATE:
  idf_invoke_required: true
  a_decision: "proceed"
  completion_signal: "pending"
"""


def test_signal_only_in_a_pipeline_state_block():
    """BL-350 F2 (AK-1) + AK-2-MIGRATION (batch_2): Signal-Strings (idf_invoke_required:
    true + routing_target: IDF) NUR im A_PIPELINE_STATE-Block.

    Dieser Test verifizierte urspruenglich, dass der block-scoped erkannte Signal-Write
    BLOCKT (exit 2). Das enforce-AFTER-write-Redesign (AK-2) entfernt den Write-Pre-Block:
    der Signal-Write ist jetzt IMMER erlaubt (continue=True). Die block-scoped Detektion
    (AK-1, F2) bleibt fuer Signal-Recognition/Logging erhalten und wird durch
    test_block_parser_extracts_a_pipeline_state + die prosa/split-Tests separat geprueft.

    Neue Soll-Semantik: Signal block-scoped erkannt -> Write passt durch (exit 0);
    Enforcement am Folge-Schritt (Skill-Load _IDF_orchestrate)."""
    manifest = _MANIFEST_SIGNAL_IN_STATE_BLOCK
    # kein _A_postRoute in Audit -> Write passt trotzdem durch (Block am IDF-Eintritt)
    audit = [{"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"}]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, (
        f"enforce-AFTER-write: block-scoped erkannter Signal-Write passt durch (exit 0), "
        f"war {proc.returncode}"
    )
    assert r.get("continue") is True, \
        "Signal-Write muss continue=True liefern (Enforcement am Folge-Schritt, nicht am Write)"


def test_signal_in_berater_outputs_prosa_ignored():
    """BL-350 F2 (AK-1) Kern-Testfall: Signal-Strings (idf_invoke_required: true +
    routing_target: IDF) AUSSCHLIESSLICH in BERATER_OUTPUTS-Prosa / Blocker-Doku,
    NICHT im A_PIPELINE_STATE-Block -> Guard DARF kein Signal erkennen -> exit 0.

    RED (F2-Bug): aktuell scannt has_signal das ganze new_text (L182) -> findet
    Strings in Prosa -> over-match -> blockt faelschlicherweise (exit 2).
    Dieser Test FAILT im RED-State, weil Guard exit 2 liefert statt exit 0."""
    manifest = _MANIFEST_SIGNAL_ONLY_IN_BERATER_OUTPUTS
    audit = [{"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"}]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, (
        f"Signal nur in BERATER_OUTPUTS-Prosa (nicht im A_PIPELINE_STATE-Block) -> "
        f"kein Guard-Trigger erwartet (exit 0), war {proc.returncode} "
        f"(F2-over-match-Bug: has_signal scannt whole new_text)"
    )
    assert r.get("continue") is True, \
        "BERATER_OUTPUTS-Prosa mit Signal-Strings darf Guard NICHT triggern (no false-block)"


def test_signal_split_across_blocks():
    """BL-350 F2 (AK-1): idf_invoke_required im A_PIPELINE_STATE, routing_target: IDF
    nur in BERATER_OUTPUTS-Prosa (split) -> kein vollstaendiges Signal im State-Block
    -> Guard erkennt KEIN Signal -> exit 0.

    RED: aktuell findet has_signal beide Strings anywhere in new_text -> falsches BLOCK
    (exit 2) statt exit 0. Test FAILT im RED-State."""
    manifest = _MANIFEST_SPLIT_ACROSS_BLOCKS
    audit = [{"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"}]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, (
        f"Split-Signal (routing_target nur in Prosa, idf_invoke_required im State-Block) -> "
        f"kein vollstaendiges Signal im A_PIPELINE_STATE-Block -> exit 0 erwartet, "
        f"war {proc.returncode} (F2-Bug: whole-text-Scan fasst beide zusammen)"
    )
    assert r.get("continue") is True, \
        "Split-Signal (beide Strings in verschiedenen Bloecken) darf Guard NICHT triggern"


def test_block_parser_extracts_a_pipeline_state():
    """BL-350 AK-5: Unit-Test fuer den Block-Parser-Helper (nach F2-Fix in GREEN).
    Prueft, dass _extract_a_pipeline_state_block den A_PIPELINE_STATE-Abschnitt isoliert.

    RED: Die Funktion existiert noch nicht in guard_a_idf_handoff.py -> ImportError /
    AttributeError -> Test failt."""
    import importlib.util
    guard_path = str(
        __file__.replace("test_guard_a_idf_handoff.py", "guard_a_idf_handoff.py")
    )
    spec = importlib.util.spec_from_file_location("guard_a_idf_handoff", guard_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert hasattr(mod, "_extract_a_pipeline_state_block"), (
        "_extract_a_pipeline_state_block nicht in guard_a_idf_handoff.py gefunden "
        "(F2-Block-Parser noch nicht implementiert — RED erwartet)"
    )
    fn = mod._extract_a_pipeline_state_block

    # positiver Fall: A_PIPELINE_STATE-Block vorhanden
    block = fn(_MANIFEST_SIGNAL_IN_STATE_BLOCK)
    assert "idf_invoke_required" in block, \
        "Block-Parser soll A_PIPELINE_STATE-Inhalt zurueckgeben"
    assert "BERATER_OUTPUTS" not in block, \
        "Block-Parser soll NICHT den BERATER_OUTPUTS-Abschnitt einschliessen"

    # negativer Fall: kein A_PIPELINE_STATE-Block -> leerer String
    block_empty = fn("Kein Block vorhanden.\nNur Prosa.\n")
    assert block_empty == "", \
        "Ohne A_PIPELINE_STATE-Block soll Block-Parser '' zurueckgeben"


# ---------------------------------------------------------------------------
# BL-350 AK-2 — RED-Ring F3: enforce-AFTER-write Redesign
#
# Problem (F3): Guard (PreToolUse) blockt den Signal-Write SELBST (exit 2).
# Aber _A_postRoute schreibt dieses Signal legitim — es braucht den Write,
# um danach zu routen. Ein Pre-Block des Writes ist eine Wand (un-erfuellbar).
#
# Soll-Semantik (enforce-AFTER-write, Vorbild guard_geist9b_sdf_post_inline):
#   Signal-Write (idf_invoke_required: true + routing_target: IDF in
#   A_PIPELINE_STATE-Block): IMMER continue=True (kein Pre-Block).
#   Enforcement passiert NACH dem Write, am Folge-Schritt:
#     Skill-Load _IDF_orchestrate OHNE vorausgehenden _A_postRoute -> BLOCK.
#
# RED: aktuell blockt der Guard den Write (exit 2) wenn kein postRoute in Audit.
# Diese Tests spezifizieren die Soll-Semantik; sie FAILEN im RED-State.
# ---------------------------------------------------------------------------


def run_guard_skill_load(skill_name, audit_lines):
    """Simuliert einen PreToolUse-Event fuer einen Skill-Load (kein Edit/Write).

    Modelliert den enforce-AFTER-write-Trigger: der Guard soll Skill-Load von
    _IDF_orchestrate pruefen (Folge-Schritt nach Signal-Write), nicht den Write selbst.

    Technische Umsetzung: tool_name='mcp__claude_ai__execute_skill' (analog zu
    wie Skill-Loads als Tool-Events erscheinen) mit skill_name im tool_input.
    Oder alternativ: der Guard kann als separater PreToolUse-Handler fuer
    Skill-Load-Events registriert sein — RED-Test spezifiziert die Soll-Semantik,
    GREEN-Worker entscheidet den konkreten Trigger-Mechanismus (SOA-1).
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write("**enforceProcess:** true\n")
        sp_path = sp.name
    env = os.environ.copy()
    env["OMNI_A_IDF_HANDOFF_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    # Skill-Load-Event: tool_name kein Edit/Write — aktueller Guard
    # gibt immer continue=True fuer Nicht-Edit/Write-Events.
    # Nach enforce-AFTER-write-Redesign soll der Guard _IDF_orchestrate-Skill-Load
    # pruefen. Wir modellieren das als generischen Skill-Load-Event.
    event = {
        "tool_name": "mcp__claude_ai__execute_skill",
        "tool_input": {"skill_name": skill_name},
    }
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


def test_signal_write_passes_under_enforce_true():
    """BL-350 AK-2 F3 (Kern-RED-Test): Legitimer A_PIPELINE_STATE Signal-Write
    (idf_invoke_required: true + routing_target: IDF) unter enforceProcess=true
    ohne vorangehenden _A_postRoute-Audit-Eintrag -> Guard BLOCKT NICHT (exit 0,
    continue=True).

    Das ist der F3-Kernfall: _A_postRoute schreibt dieses Signal selbst (SCHRITT 5
    des Berater-Flows). Wenn der Guard den Write pre-blockt, kann _A_postRoute
    nicht arbeiten -> un-erfuellbarer Block (Wand).

    RED: aktuell blockt der Guard (exit 2) weil kein postRoute in Audit vorausging.
    Test FAILT im RED-State (Guard gibt exit 2 statt exit 0).

    SOLL nach enforce-AFTER-write-Fix: Signal-Write immer durch -> exit 0."""
    # Audit enthaelt nur _A_orchestrate-Load, KEIN _A_postRoute-Eintrag
    # (das ist der typische Zustand WAEHREND _A_postRoute arbeitet:
    # es schreibt gerade das Signal, postRoute selbst ist noch nicht "ran").
    manifest = (
        "A_PIPELINE_STATE:\n"
        "  routing_target: \"IDF\"\n"
        "  idf_invoke_required: true\n"
        "  completion_signal: \"ready_for_idf\"\n"
        "  a_decision: \"proceed\"\n"
    )
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_A_postRoute"},  # postRoute geladen, aber Write kommt jetzt
    ]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, (
        f"F3 enforce-AFTER-write: Signal-Write durch _A_postRoute darf NICHT pre-geblockt "
        f"werden (exit 0 erwartet), war exit {proc.returncode}. "
        f"Guard blockt den Write selbst (Wand: un-erfuellbar wenn postRoute den Write macht)."
    )
    assert r.get("continue") is True, (
        "F3: Signal-Write (idf_invoke_required=true in A_PIPELINE_STATE-Block) "
        "muss continue=True liefern — Guard darf Schreiben nicht pre-blocken."
    )


def test_signal_write_no_postroute_in_audit_passes():
    """BL-350 AK-2 F3: Signal-Write ohne _A_postRoute UND ohne _A_orchestrate
    in Audit (z.B. Erst-Schreiben, frischer Audit) -> Guard BLOCKT NICHT.

    enforce-AFTER-write bedeutet: der Write-Schritt ist IMMER erlaubt.
    Enforcement ist dem Folge-Schritt (_IDF_orchestrate-Load) vorbehalten.

    RED: aktuell prueft Guard a_active/postroute_since und blockt wenn
    a_active=False ODER postroute_since=False -> exit 2. Test FAILT im RED-State."""
    manifest = (
        "A_PIPELINE_STATE:\n"
        "  routing_target: \"IDF\"\n"
        "  idf_invoke_required: true\n"
        "  a_decision: \"proceed\"\n"
    )
    # Leerer Audit: kein _A_orchestrate, kein _A_postRoute (z.B. frischer Start)
    audit = []
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, (
        f"F3 enforce-AFTER-write: Signal-Write mit leerem Audit -> kein Pre-Block "
        f"(exit 0 erwartet), war exit {proc.returncode}. "
        f"Enforcement gehoert zum Folge-Schritt (_IDF_orchestrate-Load), nicht zum Write."
    )
    assert r.get("continue") is True, (
        "Signal-Write mit leerem Audit muss immer durchgelassen werden "
        "(enforce-AFTER-write: Enforcement erst am Folge-Schritt)."
    )


def test_idf_orchestrate_load_without_postroute_blocked():
    """BL-350 AK-2 F3 (enforce-AFTER-write Folge-Schritt): Skill-Load
    _IDF_orchestrate ohne vorausgehenden _A_postRoute-Eintrag nach _A_orchestrate
    -> Guard BLOCKT (exit 2) + Recovery-Hint.

    Das ist der ECHTE Enforcement-Punkt: nicht der Write, sondern der IDF-Eintritt.
    _IDF_orchestrate darf nur via _A_postRoute -> _IDF_orchestrate-Seam aufgerufen
    werden (INV-A-GUARD-1).

    RED: aktuell gibt der Guard fuer Skill-Load-Events (tool_name != Edit/Write)
    immer continue=True (L202-204) — kein IDF-Load-Check. Test FAILT im RED-State
    (Guard gibt exit 0/continue=True statt exit 2)."""
    # Audit: _A_orchestrate lief, Signal-Write passierte (kein _A_postRoute)
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"},
        # kein _A_postRoute-Eintrag -> Handoff-Seam verletzt
    ]
    proc, r = run_guard_skill_load("_IDF_orchestrate", audit)
    assert proc.returncode == 2, (
        f"F3 enforce-AFTER-write: Skill-Load _IDF_orchestrate ohne vorausgehenden "
        f"_A_postRoute nach _A_orchestrate -> BLOCK erwartet (exit 2), "
        f"war exit {proc.returncode}. Guard prueft Skill-Load-Events noch nicht "
        f"(nur Edit/Write-Events abgefangen, L202-204 aktueller Guard)."
    )
    assert "Rufe Skill(_A_postRoute" in (r.get("message", "") + proc.stderr), \
        "Recovery-Hint 'Rufe Skill(_A_postRoute, args={bl-id}) -> _IDF_orchestrate' fehlt beim IDF-Load-Block"


if __name__ == "__main__":
    tests = [
        test_proceed_without_postroute_blocked,
        test_defer_marker_not_blocked,
        test_a_retry_marker_not_blocked,
        test_signal_only_in_a_pipeline_state_block,
        test_signal_in_berater_outputs_prosa_ignored,
        test_signal_split_across_blocks,
        test_block_parser_extracts_a_pipeline_state,
        test_signal_write_passes_under_enforce_true,
        test_signal_write_no_postroute_in_audit_passes,
        test_idf_orchestrate_load_without_postroute_blocked,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed+failed} ===")
    sys.exit(0 if failed == 0 else 1)
