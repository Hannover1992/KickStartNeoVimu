"""
BL-466: M2-Pfad-State-Seam-Haertung + Regression-Verifikation + Epic-BL-463-Termination
RED-Worker: BL-466 batch_1 Stage 1 Iteration 1

Tests pruefen den Inhalt von .claude/commands/_I_orchestrate.md via grep/parse.
T6 + T9 MUESSEN JETZT FAILEN (RED) — Marker fehlen noch (M2-SEAM-HARDENED=0, EPIC-TERMINATION=0).
T1-T5 + T7 + T8 sind Charakterisierung/Regression (initial GREEN, duerfen NICHT brechen).

Blueprint: BL-466_blueprint.md (9 Asserts T1-T9)
RED-Hebel: T6 ('M2-SEAM-HARDENED' Marker fehlt), T9 ('EPIC-TERMINATION' Marker fehlt).
BASELINE_COMMIT: b2029bf (pre-BL-466, HEAD == Baseline).
Muster: analog test_bl464_i_state_machine.py / test_bl465_inv_spawn.py
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

I_ORCHESTRATE   = COMMANDS_DIR / "_I_orchestrate.md"
A_ORCHESTRATE   = COMMANDS_DIR / "_A_orchestrate.md"
IDF_ORCHESTRATE = COMMANDS_DIR / "_IDF_orchestrate.md"

# Baseline commit pre-BL-466 (A/IDF zuletzt angefasst)
BASELINE_COMMIT = "b2029bf"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── T1: STATE-MACHINE + 14 Phasen-Literale (lockt BL-464) — GREEN ─────────────

def test_ac1_state_machine_seven_phases_present():
    """
    T1 (Charakterisierung / Regression — initial GREEN, lockt BL-464):
    _I_orchestrate.md muss mind. 1 '## STATE-MACHINE'-Block enthalten UND alle 14
    BLUEPRINT../VERIFY_RUNNING/_DONE-Literale.

    Heute GREEN (BL-464 DONE): 1 STATE-MACHINE-Block + alle 14 Literale vorhanden.
    Darf NICHT brechen — Regression-Guard gegen unbeabsichtigtes STATE-MACHINE-Loeschen.
    """
    text = _read(I_ORCHESTRATE)

    assert text.count("## STATE-MACHINE") >= 1, (
        f"'## STATE-MACHINE' Block fehlt in _I_orchestrate.md — "
        f"BL-464 STATE-MACHINE wurde entfernt oder umbenannt (Regression T1). "
        f"gefunden: {text.count('## STATE-MACHINE')} (erwartet: >= 1)."
    )

    required_literals = [
        "BLUEPRINT_RUNNING",  "BLUEPRINT_DONE",
        "GOLDDEFINE_RUNNING", "GOLDDEFINE_DONE",
        "TESTSEARCH_RUNNING", "TESTSEARCH_DONE",
        "RED_RUNNING",        "RED_DONE",
        "GREEN_RUNNING",      "GREEN_DONE",
        "REFACTOR_RUNNING",   "REFACTOR_DONE",
        "VERIFY_RUNNING",     "VERIFY_DONE",
    ]
    missing = [lit for lit in required_literals if lit not in text]
    assert not missing, (
        f"Fehlende Phasen-Literale in _I_orchestrate.md (Regression T1): {missing}. "
        f"BL-464 STATE-MACHINE muss alle 14 Status-Transitionen (BLUEPRINT..VERIFY) deklarieren."
    )


# ── T2: [GATE P >=5 (lockt BL-465) — GREEN ────────────────────────────────────

def test_ac1_five_gate_p_markers_present():
    """
    T2 (Charakterisierung / Regression — initial GREEN, lockt BL-465):
    _I_orchestrate.md muss mind. 5 '[GATE P'-Marker enthalten.

    Heute GREEN (BL-465 DONE): 5x [GATE P vorhanden (P1-P5).
    Darf NICHT brechen — Regression-Guard gegen Gate-Entfernung.
    """
    text = _read(I_ORCHESTRATE)

    gate_count = text.count("[GATE P")
    assert gate_count >= 5, (
        f"'[GATE P' Marker zu selten in _I_orchestrate.md (Regression T2) — "
        f"gefunden: {gate_count} (erwartet: >= 5). "
        f"BL-465 hat 5 Gates (P1-P5) eingefuegt — duerfen NICHT entfernt werden."
    )


# ── T3: Modus-Geltung — STATE-HANDOFF + NICHT an tdd_enabled + modus-unabhaengig — GREEN ──

def test_ac1_modus_geltung_state_handoff_not_tdd():
    """
    T3 (Charakterisierung — initial GREEN, lockt Z652-656):
    _I_orchestrate.md muss enthalten:
      - 'STATE-HANDOFF'
      - re.search(r'NICHT\\s+an\\s+tdd_enabled', text)
      - re.search(r'modus.unabh[aae]ngig', text, re.I)

    Heute GREEN (BL-464 STATE-MACHINE AC-6 DONE): alle 3 Marker vorhanden.
    """
    text = _read(I_ORCHESTRATE)

    assert "STATE-HANDOFF" in text, (
        "'STATE-HANDOFF' fehlt in _I_orchestrate.md (Regression T3) — "
        "Modus-Geltungs-Note (BL-464 AC-6) muss unveraendert bleiben."
    )

    has_nicht_tdd = bool(re.search(r"NICHT\s+an\s+tdd_enabled", text))
    assert has_nicht_tdd, (
        "'NICHT an tdd_enabled' Phrase fehlt in _I_orchestrate.md (Regression T3) — "
        "die Modus-Geltungs-Note muss erklaeren, dass der Seam NICHT an tdd_enabled haengt "
        "(BL-464 AC-6, Z652-656)."
    )

    # Matcht 'modus-unabhaengig' (ASCII ae) und 'modus-unabhaengig' (Unicode ae)
    has_modus_unabh = bool(re.search(r"modus.unabh(ae|[aä])ngig", text, re.I))
    assert has_modus_unabh, (
        "'modus-unabhaengig' Phrase fehlt in _I_orchestrate.md (Regression T3) — "
        "die Modus-Geltungs-Note muss 'modus-unabhaengig' deklarieren (BL-464 AC-6, Z652-656)."
    )


# ── T4: M2 degeneriert (exit_code=0) >= 2 UND kein M2-skip/entfernt/ueberspringen — GREEN ──

def test_ac1_m2_degeneration_not_skip():
    """
    T4 (Charakterisierung — initial GREEN, lockt Z663/665):
    _I_orchestrate.md muss enthalten:
      - re.findall(r'M2 degeneriert \\(exit_code=0\\)', text) >= 2
      - 'M2 skip' not in text
      - 'M2 entfernt' not in text
      - 'M2 ueberspringen' not in text

    Heute GREEN (BL-464 DONE): M2 degeneriert-Formel 2x vorhanden (Z663+665),
    keine Verbots-Woerter (skip/entfernt/ueberspringen).
    """
    text = _read(I_ORCHESTRATE)

    m2_deg_matches = re.findall(r"M2 degeneriert \(exit_code=0\)", text)
    assert len(m2_deg_matches) >= 2, (
        f"'M2 degeneriert (exit_code=0)' zu selten in _I_orchestrate.md (Regression T4) — "
        f"gefunden: {len(m2_deg_matches)} (erwartet: >= 2, Z663+665). "
        f"BL-464 RED/refactor-Tabellenzeilen muessen unveraendert bleiben."
    )

    assert "M2 skip" not in text, (
        "'M2 skip' gefunden in _I_orchestrate.md (T4) — "
        "M2 darf NICHT als 'skip' bezeichnet werden; korrekt ist 'M2 degeneriert (exit_code=0)'."
    )

    assert "M2 entfernt" not in text, (
        "'M2 entfernt' gefunden in _I_orchestrate.md (T4) — "
        "M2-Phase ist NICHT entfernt, sondern degeneriert zur exit_code=0-Transition."
    )

    assert "M2 ueberspringen" not in text, (
        "'M2 ueberspringen' gefunden in _I_orchestrate.md (T4) — "
        "M2 wird NICHT uebersprungen; korrekt ist 'M2 degeneriert (exit_code=0)'."
    )


# ── T5: Spawn-Bloecke (Z1086-1146) NICHT tdd-geklammert — GREEN ───────────────

def test_ac1_gate_phase_marker_not_tdd_klammered():
    """
    T5 (Charakterisierung / Modus-Unabhaengigkeit — initial GREEN):
    Die 5 Phase-Spawn-Bloecke (Z1086-1146) duerfen NICHT von einem 'IF tdd_enabled'-Block
    umklammert sein.

    Konkret:
      - Kein '[GATE P'-Marker steht gemeinsam mit 'tdd_enabled' auf derselben Zeile
      - 'IF tdd_enabled' kommt NICHT in _I_orchestrate.md vor (heute: 0 Treffer = GREEN)

    Heute GREEN: keine IF-tdd_enabled-Klammer um die Phase-Spawn-Bloecke.
    """
    text = _read(I_ORCHESTRATE)
    lines = text.splitlines()

    # Check 1: kein [GATE P] zusammen mit tdd_enabled auf derselben Zeile
    for i, line in enumerate(lines):
        if "[GATE P" in line:
            assert "tdd_enabled" not in line, (
                f"Zeile Z{i+1} enthaelt '[GATE P' UND 'tdd_enabled' zusammen — "
                f"Gate-Marker duerfen NICHT tdd-geklammert sein (T5, modus-Unabhaengigkeit). "
                f"Zeile: {line.strip()}"
            )

    # Check 2: kein IF tdd_enabled in der Datei (wuerde Phase-Spawn-Bloecke umklammern)
    assert "IF tdd_enabled" not in text, (
        "'IF tdd_enabled' gefunden in _I_orchestrate.md (T5) — "
        "die Phase-1..5-Spawn-Bloecke (Z1086-1146) duerfen NICHT von einem "
        "IF-tdd_enabled-Klammer-Block umschlossen sein (modus-unabhaengiger State-Seam, AK-1(e))."
    )


# ── T6: [RED-HEBEL] M2-SEAM-HARDENED-Marker + konsolidiertes Haertungs-Statement — RED ──

def test_ac1_m2_seam_hardened_marker_present():
    """
    T6 (RED-HEBEL — initial FAIL):
    _I_orchestrate.md muss enthalten:
      - 'M2-SEAM-HARDENED' (Marker fuer konsolidiertes Haertungs-Statement)
      - re.search(r'State-Seam.*tr[aae]gt.*Phasen-Trennung.*modus-unabh', text, re.S|re.I)
        (das konsolidierte Haertungs-Statement aus Blueprint Z88-95)

    Heute RED: 'M2-SEAM-HARDENED' = 0 Treffer (verifiziert) -> FAIL.
    Nach GREEN (GREEN-Worker fuegt Statement nahe Z656 ein): beide Bedingungen erfuellt -> PASS.
    """
    text = _read(I_ORCHESTRATE)

    assert "M2-SEAM-HARDENED" in text, (
        "'M2-SEAM-HARDENED' Marker fehlt in _I_orchestrate.md (RED-Hebel T6) — "
        "GREEN-Worker muss das konsolidierte Haertungs-Statement (BL-466 Blueprint Z88-95) "
        "direkt nach Z656 einfuegen: '[M2-SEAM-HARDENED] (BL-466 ...) Der State-Seam traegt "
        "die Phasen-Trennung modus-unabhaengig ...' (AK-1 RED-Hebel)."
    )

    # Matcht 'traegt' (ASCII ae) und 'trägt' (Unicode ae)
    has_hardening_statement = bool(
        re.search(
            r"State-Seam.*tr(ae|[aä])gt.*Phasen-Trennung.*modus.unabh",
            text,
            re.S | re.I,
        )
    )
    assert has_hardening_statement, (
        "Konsolidiertes Haertungs-Statement fehlt in _I_orchestrate.md (RED-Hebel T6) — "
        "das Statement muss 'State-Seam traegt die Phasen-Trennung modus-unabhaengig' "
        "als zusammenhaengende Phrase enthalten (BL-466 Blueprint Z88, AK-1 RED-Hebel)."
    )


# ── T7: BL-230-Cluster >= 31 — GREEN ──────────────────────────────────────────

def test_ac3_bl230_cluster_stable():
    """
    T7 (Regression / BL-230-Cluster — initial GREEN):
    _I_orchestrate.md muss mind. 31 Pattern-B/Rollover/POST_HANDOVER/...-Cluster-Treffer
    enthalten (stabil-gegen-Baseline, NICHT harte ==-Magic-Number).

    Cluster-Pattern: Pattern B | Rollover | POST_HANDOVER | fanOut | fanIn | mitose | resume_zaehler
    Zusaetzlich: 'resume_zaehler' + 'INVARIANTE W11' + 'POST_HANDOVER' einzeln geprueft.

    Heute GREEN (Ist=46 >= 31, verifiziert). Das additive Statement (GREEN-Worker) darf
    den Cluster-Zaehler nicht auf < 31 senken.
    """
    text = _read(I_ORCHESTRATE)

    cluster_matches = re.findall(
        r"Pattern B|Rollover|POST_HANDOVER|fanOut|fanIn|mitose|resume_zaehler",
        text,
        re.I,
    )
    cluster_count = len(cluster_matches)
    assert cluster_count >= 31, (
        f"BL-230-Cluster-Zaehler zu niedrig in _I_orchestrate.md (Regression T7) — "
        f"gefunden: {cluster_count} (erwartet: >= 31). "
        f"Pattern B / Rollover / POST_HANDOVER / fanOut / fanIn / mitose / resume_zaehler-Treffer "
        f"duerfen nicht auf < 31 sinken (BL-466 AK-3, stabil-gegen-Baseline)."
    )

    assert "resume_zaehler" in text, (
        "'resume_zaehler' fehlt in _I_orchestrate.md (Regression T7) — "
        "INVARIANTE W11 / Pattern-B-Rollover muss unveraendert erhalten bleiben (AK-3)."
    )

    assert "INVARIANTE W11" in text, (
        "'INVARIANTE W11' fehlt in _I_orchestrate.md (Regression T7) — "
        "der Rollover-Wachpunkt muss byte-identisch erhalten bleiben (AK-3)."
    )

    assert "POST_HANDOVER" in text, (
        "'POST_HANDOVER' fehlt in _I_orchestrate.md (Regression T7) — "
        "der POST_HANDOVER-Block muss unveraendert bleiben (AK-3)."
    )


# ── T8: A/IDF byte-identisch vs b2029bf — GREEN ───────────────────────────────

def test_ac2_aidf_byte_identical():
    """
    T8 (Regression — initial GREEN):
    git diff --quiet b2029bf -- _A_orchestrate.md _IDF_orchestrate.md -> returncode 0.

    BL-466 darf _A_orchestrate.md und _IDF_orchestrate.md NICHT anfassen (AK-2, NZ).
    Heute GREEN: HEAD == b2029bf == git_baseline (verifiziert).
    """
    a_rel   = ".claude/commands/_A_orchestrate.md"
    idf_rel = ".claude/commands/_IDF_orchestrate.md"

    result = subprocess.run(
        ["git", "diff", "--quiet", BASELINE_COMMIT, "--", a_rel, idf_rel],
        cwd=str(REPO_ROOT),
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"_A_orchestrate.md oder _IDF_orchestrate.md haben sich gegenueber Baseline "
        f"{BASELINE_COMMIT} geaendert (Regression T8) — "
        f"BL-466 darf diese Dateien NICHT anfassen (AK-2, NICHT-Ziel NZ-1). "
        f"git diff stdout: {result.stdout.decode(errors='replace')}"
    )


# ── T9: [RED-HEBEL] EPIC-TERMINATION-Marker + BL-463 TERMINATED/DONE + TDD 2. Notnagel — RED ──

def test_ac4_epic_termination_documented():
    """
    T9 (RED-HEBEL — initial FAIL):
    _I_orchestrate.md muss enthalten:
      - 'EPIC-TERMINATION' (Marker fuer Epic-Abschluss-Statement)
      - re.search(r'BL-463.*TERMINATED|BL-463.*DONE', text) (Epic-Status)
      - re.search(r'TDD.*2\\.?\\s*Notnagel', text, re.I) (TDD als 2. Notnagel deklariert)

    Heute RED: 'EPIC-TERMINATION' = 0 Treffer, 'BL-463.*TERMINATED' = 0 (verifiziert) -> FAIL.
    Nach GREEN (GREEN-Worker fuegt Statement + Epic-Doku ein): alle 3 Bedingungen erfuellt -> PASS.

    Hinweis: Die BL-463-Vault-Node-Aktualisierung (status->DONE) ist Doku-Inspektion und
    wird NICHT via Python-Assert geprueft (nur der [EPIC-TERMINATION]-Marker IM _I_orchestrate.md
    ist testbar, AK-4(i) vs AK-4(ii) Split, Blueprint Z105-107).
    """
    text = _read(I_ORCHESTRATE)

    assert "EPIC-TERMINATION" in text, (
        "'EPIC-TERMINATION' Marker fehlt in _I_orchestrate.md (RED-Hebel T9) — "
        "GREEN-Worker muss das Epic-Termination-Statement (BL-466 Blueprint Z97-101) "
        "einfuegen: '[EPIC-TERMINATION] BL-463 = TERMINATED/DONE (BL-464 + BL-465 + BL-466)' "
        "(AK-4(i) RED-Hebel)."
    )

    has_bl463_terminated = bool(
        re.search(r"BL-463.*TERMINATED|BL-463.*DONE", text)
    )
    assert has_bl463_terminated, (
        "'BL-463.*TERMINATED' oder 'BL-463.*DONE' fehlt in _I_orchestrate.md (RED-Hebel T9) — "
        "das Epic-Termination-Statement muss BL-463 explizit als TERMINATED/DONE deklarieren "
        "(BL-466 Blueprint Z97, AK-4(i))."
    )

    has_tdd_notnagel = bool(
        re.search(r"TDD.*2\.?\s*Notnagel", text, re.I)
    )
    assert has_tdd_notnagel, (
        "'TDD ... 2. Notnagel' Phrase fehlt in _I_orchestrate.md (RED-Hebel T9) — "
        "das M2-SEAM-HARDENED-Statement muss TDD/RED!=GREEN als '2. Notnagel' einordnen "
        "(primaerer Schutz = state-getriebener Vertrag, NICHT TDD; "
        "BL-466 Blueprint Z93-95, AK-4(i))."
    )
