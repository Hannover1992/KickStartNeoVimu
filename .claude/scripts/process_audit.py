#!/usr/bin/env python3
"""
BL-NEW-RCA-486-Round11: Process-Audit-Script (Ring 2 RCA-Fix).

Scannt audit.jsonl + per-BL _manifest.md und vergleicht IST gegen /_help SOLL.
Erkennt strukturelle Process-Bypasses bevor sie als COMPLETE-WITH-DEBT akzeptiert werden.

Trigger:
  - Manuell: py -3 .claude/scripts/process_audit.py --bl-folder={path} --round={N}
  - Auto via Stop-Hook bei Goal-Hook-Termination
  - Auto via _PostBatch_orchestrate Phase Ende

Detector-Rules (CRITICAL/HIGH/MEDIUM):
  R1 (CRITICAL): DF_BATCH_STATE.batch_modes ohne BERATER_OUTPUTS.modusEntscheidung_*
    R1a (alter Drift):  batch_modes gesetzt, aber kein modusEntscheidung-Berater-Output
    R1b (neuer Drift):  batch_modes gesetzt, aber kein batch_mode_hints-Vorgaenger
                        UND kein shadow_corrected_at-Marker → IDF hat batch_modes direkt
                        gesetzt ohne Anti-Shadow-Korrektur (INV-MODUS-1-SHADOW, BL-218)
  R2 (CRITICAL): mode: lead_fallback ohne pragmatik_reason
  R3 (CRITICAL): I_PIPELINE_STATE_round{N}.md fehlt aber DF_BATCH_STATE sub_batches done
  R4 (HIGH):     0 RED-Test-Skill-Loads bei M3-Batch (TDD invertiert)
  R5 (HIGH):     _I_patternLibrary 0 Spawns pro Batch
  R6 (HIGH):     _I_goldDefine 0 Spawns pro Batch
  R7 (MEDIUM):   kein _PostBatch_orchestrate Skill-Load nach loopDecision=TERMINATE
  R8 (MEDIUM):   modelSync SKIP ohne _SDF_berater_modelSync Output

BL-341 (Detektor-Haertung, NON-WEAKENING):
  - R5/R6 erkennen patternLibrary/goldDefine-Evidenz auch in BARE-KEY-Form
    (### patternLibrary / patternLibrary: ) zusaetzlich zur dotted
    BERATER_OUTPUTS.patternLibrary-Form (AK-1).
  - GATED altmodisch-Downgrade (AK-2): wuerde R5/R6 feuern UND das Manifest
    traegt den expliziten Kollaps-Marker (driver: ALTMODISCH in
    ## SDF_FINAL_CLOSURE), wird das Finding auf Severity INFO herabgestuft
    (exit-neutral). OHNE Marker (full-pipeline/Motor) bleibt es HIGH.
    Das ist GATED, kein Blanket-Suppress.
  - R1a robust (AK-3): has_berater-Match case-insensitive + bare-key
    ### modusEntscheidung-Header als gueltiger Berater-Output anerkannt.

Severity-Raenge:
  CRITICAL/HIGH -> RED (exit 2)
  MEDIUM        -> YELLOW (exit 1)
  INFO          -> exit-neutral (gated altmodisch-Downgrade, BL-341); hebt das
                   Verdikt NIE an. INFO-only -> GREEN (exit 0).

Exit-Codes:
  0 = GREEN (alle Rules pass, oder nur INFO-Findings)
  1 = YELLOW (nur MEDIUM-Findings)
  2 = RED (CRITICAL oder HIGH-Findings)

Usage:
  py -3 process_audit.py --bl-folder=C:/path/to/BL-N --round=11
  py -3 process_audit.py --audit-jsonl=.claude/audit/audit.jsonl --bl-folder=... --round=N
  py -3 process_audit.py --self-test    # interner Smoke-Test
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Rule-Defs
RULES = {
    "R1":  ("CRITICAL", "batch_modes ohne BERATER_OUTPUTS.modusEntscheidung_*"),
    "R1a": ("CRITICAL", "batch_modes gesetzt, aber kein modusEntscheidung-Berater-Output (alter Drift)"),
    "R1b": ("CRITICAL", "batch_modes ohne batch_mode_hints-Vorgaenger und ohne shadow_corrected_at (neuer Drift, INV-MODUS-1-SHADOW BL-218)"),
    "R2": ("CRITICAL", "mode: lead_fallback ohne pragmatik_reason"),
    "R3": ("CRITICAL", "I_PIPELINE_STATE_round{N}.md fehlt aber sub_batches done"),
    "R4": ("HIGH",     "0 RED-Tests bei M3-Batch (TDD invertiert)"),
    "R5": ("HIGH",     "_I_patternLibrary 0 Spawns"),
    "R6": ("HIGH",     "_I_goldDefine 0 Spawns"),
    "R7": ("MEDIUM",   "kein _PostBatch_orchestrate nach loopDecision=TERMINATE"),
    "R8": ("MEDIUM",   "modelSync SKIP ohne Berater-Output"),
}


def read_manifest(bl_folder):
    """Lese per-BL _manifest.md als Dual-Read-Union (BL-229 AK-F, 2026-06-10).

    Liefert Manifest-Body PLUS ausgelagerte Report-/History-Bodies
    (_manifest_history_*.md via AK-C-Offload, 6_PL/BERATER_OUTPUTS/*.md via
    AK-B-Pointer). Sonst liefert eine Compliance-Grep nach dem State-vs-Report-
    Split ein False-Negative (Phase faelschlich als nicht-gelaufen -> RED-Block).
    INV-POINTER-1: inhaltlich identisch egal ob inline/pointer/offloaded. Die
    Inline-Lesung bleibt 1:1 erhalten — Pointer/History kommen NUR additiv hinzu.
    """
    path = Path(bl_folder) / "_manifest.md"
    if not path.exists():
        return ""
    manifest_text = path.read_text(encoding="utf-8", errors="replace")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from _dual_read_manifest import dual_read_text
        return dual_read_text(manifest_text, manifest_path=path, bl_folder=Path(bl_folder))
    except Exception:
        # Fallback: reine Inline-Lesung (kein Dual-Read-Helper) — Backward-Compat.
        return manifest_text


def grep_manifest(manifest, pattern):
    """Grep auf Manifest-String, return list of matched lines."""
    return [l for l in manifest.splitlines() if re.search(pattern, l)]


def has_altmodisch_marker(manifest):
    """BL-341 AK-2: expliziter altmodisch-Kollaps-Marker (driver: ALTMODISCH).

    Der Marker steht per Konvention in ## SDF_FINAL_CLOSURE als echtes
    YAML-Key-Feld (driver: "ALTMODISCH (Team+Lead), ...").

    LINE-ANCHORED (BL-341 Review-Fix, NON-WEAKENING-Praezisierung): der Regex
    matcht NUR eine echte `driver:`-Key-ZEILE (Zeilen-Anfang, optional Whitespace,
    dann driver:), NICHT eine blosse PROSA-Erwaehnung von "driver: ALTMODISCH"
    im quoted Wert eines ANDEREN Keys (z.B. `grounding: "...driver: ALTMODISCH..."`
    — diese Zeile beginnt mit `grounding:`, nicht `driver:`). Ohne Line-Anchor
    haette jedes full-pipeline-Manifest, das den Marker nur DOKUMENTIERT,
    faelschlich den INFO-Downgrade bekommen = WEAKENING.

    grep_manifest wendet re.search per ZEILE an (splitlines()), daher ankert `^`
    bereits pro Zeile; (?m) ist additiv-robust falls das Pattern je auf einem
    Multi-Line-String genutzt wird. Das ist der EINZIGE Gate fuer den
    R5/R6-Severity-Downgrade — ohne echtes driver:-Feld (full-pipeline/Motor)
    bleibt R5/R6 HIGH (NON-WEAKENING).
    """
    return bool(grep_manifest(manifest, r"(?im)^\s*driver\s*:\s*['\"]?\s*ALTMODISCH\b"))


def read_audit(audit_path):
    """Lese audit.jsonl falls vorhanden."""
    p = Path(audit_path)
    if not p.exists():
        return []
    events = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except Exception:
            pass
    return events


def check_r1_batch_modes_without_berater(manifest, round_n):
    """R1 CRITICAL: batch_modes without BERATER_OUTPUTS.modusEntscheidung.

    Aufgeteilt in zwei Sub-Checks (BL-218 AK-6):
      R1a (alter Drift):  batch_modes vorhanden, aber kein modusEntscheidung-Berater-Output.
      R1b (neuer Drift):  batch_modes vorhanden, aber weder batch_mode_hints noch
                          shadow_corrected_at → IDF hat batch_modes direkt geschrieben
                          ohne Anti-Shadow-Korrektur (INV-MODUS-1-SHADOW, BL-218).

    Gibt eine Liste von Findings zurueck (0, 1 oder 2 Eintraege).
    """
    findings = []
    has_batch_modes = bool(grep_manifest(manifest, r"^\s*batch_modes\s*:"))

    if not has_batch_modes:
        return findings  # kein batch_modes → kein Drift moeglich

    # R1a: alter Drift — batch_modes ohne Berater-Output
    # BL-341 AK-3: case-insensitive (klein-c3 == Gross-C3) + bare-key
    #   ### modusEntscheidung-Header als gueltiger Berater-Output anerkannt
    #   (zusaetzlich zur dotted BERATER_OUTPUTS.modusEntscheidung-Form).
    has_berater = bool(grep_manifest(
        manifest,
        rf"(?i)BERATER_OUTPUTS\.modusEntscheidung.*round{round_n}|BERATER_OUTPUTS\.modusEntscheidung_v3_1[3456]|last_berater.*C3|last_berater.*modusEntscheidung|^###\s+modusEntscheidung\b",
    ))
    if not has_berater:
        findings.append(("R1a", RULES["R1a"][0], RULES["R1a"][1]))

    # R1b: neuer Drift — batch_modes ohne batch_mode_hints-Vorgaenger und ohne shadow_corrected_at
    # Erlaubte Vorgaenger:
    #   1. batch_mode_hints vorhanden (IDF hat hints geschrieben; C3 hat dann batch_modes gesetzt)
    #   2. shadow_corrected_at vorhanden (IDF Phase 7.6 Anti-Shadow hat batch_modes→batch_mode_hints
    #      bereits korrigiert, d.h. batch_modes stammt in diesem Fall von C3)
    #   3. modus_set_by: "_SDF_berater_modusEntscheidung" (expliziter INV-MODUS-1-Whitelist-Marker)
    has_hints = bool(grep_manifest(manifest, r"^\s*batch_mode_hints\s*:"))
    has_shadow_corrected = bool(grep_manifest(manifest, r"shadow_corrected_at\s*:"))
    has_modus_set_by_c3 = bool(grep_manifest(
        manifest, r"modus_set_by\s*:\s*['\"]?_SDF_berater_modusEntscheidung['\"]?"
    ))
    if not has_hints and not has_shadow_corrected and not has_modus_set_by_c3:
        findings.append(("R1b", RULES["R1b"][0], RULES["R1b"][1]))

    return findings


def check_r2_lead_fallback(manifest):
    """R2 CRITICAL: mode: lead_fallback ohne pragmatik_reason."""
    has_lead_fb = bool(grep_manifest(manifest, r"mode:\s*lead_fallback"))
    has_reason = bool(grep_manifest(manifest, r"pragmatik_reason\s*:"))
    if has_lead_fb and not has_reason:
        return ("R2", RULES["R2"][0], RULES["R2"][1])
    return None


def check_r3_i_pipeline_state_missing(bl_folder, round_n):
    """R3 CRITICAL: I_PIPELINE_STATE_round{N}.md fehlt aber sub_batches done."""
    impl_dir = Path(bl_folder) / "7_Implementation"
    has_state_file = (impl_dir / f"I_PIPELINE_STATE_round{round_n}.md").exists()
    manifest = read_manifest(bl_folder)
    has_done_sub_batches = bool(grep_manifest(manifest,
        rf"DF_BATCH_STATE_round{round_n}_completed|POST_SDF_PHASE_3_STATE_round_batch_v3_1[3456]"))
    if has_done_sub_batches and not has_state_file:
        return ("R3", RULES["R3"][0], RULES["R3"][1])
    return None


def check_r4_no_red_tests(manifest, audit_events, round_n):
    """R4 HIGH: 0 RED-Tests bei M3-Batch."""
    has_m3 = bool(grep_manifest(manifest, r":\s*M3\b|modus:\s*M3"))
    red_test_events = [e for e in audit_events
                       if "_TDD_red" in str(e) or "TDD_red" in str(e.get("skill", ""))
                       or "TDD_red" in str(e.get("command", ""))]
    if has_m3 and not red_test_events:
        return ("R4", RULES["R4"][0], RULES["R4"][1])
    return None


def check_r5_pattern_library_missing(manifest):
    """R5 HIGH: _I_patternLibrary 0 Spawns pro Batch.

    BL-341 AK-1: Evidenz wird auch in BARE-KEY-Form anerkannt
      - dotted:   BERATER_OUTPUTS.patternLibrary
      - bare-key: ### patternLibrary   ODER   patternLibrary:
    Wenn die Evidenz in IRGENDEINER Form da ist -> kein Finding.

    BL-341 AK-2 (GATED, NON-WEAKENING): wuerde das Finding feuern UND das
    Manifest traegt den driver: ALTMODISCH-Kollaps-Marker -> Severity INFO
    (exit-neutral). OHNE Marker bleibt HIGH.
    """
    has_pl_output = bool(grep_manifest(
        manifest,
        r"BERATER_OUTPUTS\.patternLibrary|^###\s+patternLibrary\b|^\s*patternLibrary\s*:",
    ))
    has_batch_state = bool(grep_manifest(manifest, r"DF_BATCH_STATE"))
    if has_batch_state and not has_pl_output:
        sev = "INFO" if has_altmodisch_marker(manifest) else RULES["R5"][0]
        return ("R5", sev, RULES["R5"][1])
    return None


def check_r6_gold_define_missing(manifest):
    """R6 HIGH: _I_goldDefine 0 Spawns.

    BL-341 AK-1: Evidenz wird auch in BARE-KEY-Form anerkannt
      - dotted:   BERATER_OUTPUTS.goldDefine
      - bare-key: ### goldDefine   ODER   goldDefine:
    Wenn die Evidenz in IRGENDEINER Form da ist -> kein Finding.

    BL-341 AK-2 (GATED, NON-WEAKENING): wuerde das Finding feuern UND das
    Manifest traegt den driver: ALTMODISCH-Kollaps-Marker -> Severity INFO
    (exit-neutral). OHNE Marker bleibt HIGH.
    """
    has_gd_output = bool(grep_manifest(
        manifest,
        r"BERATER_OUTPUTS\.goldDefine|^###\s+goldDefine\b|^\s*goldDefine\s*:",
    ))
    has_batch_state = bool(grep_manifest(manifest, r"DF_BATCH_STATE"))
    if has_batch_state and not has_gd_output:
        sev = "INFO" if has_altmodisch_marker(manifest) else RULES["R6"][0]
        return ("R6", sev, RULES["R6"][1])
    return None


def check_r7_postbatch_missing(audit_events, manifest):
    """R7 MEDIUM: kein _PostBatch_orchestrate nach TERMINATE."""
    has_terminate = bool(grep_manifest(manifest, r"loopDecision:\s*TERMINATE"))
    pb_events = [e for e in audit_events
                 if "_PostBatch_orchestrate" in str(e.get("skill", ""))
                 or "_PostBatch_orchestrate" in str(e.get("command", ""))]
    if has_terminate and not pb_events:
        return ("R7", RULES["R7"][0], RULES["R7"][1])
    return None


def check_r8_modelsync_phantom(manifest):
    """R8 MEDIUM: modelSync SKIP ohne Berater-Output."""
    skip_lines = grep_manifest(manifest, r"phase_3_5_modelSync:\s*SKIP|modelSync:\s*SKIP")
    has_modelsync_output = bool(grep_manifest(manifest, r"BERATER_OUTPUTS\.modelSync.*round"))
    if skip_lines and not has_modelsync_output:
        return ("R8", RULES["R8"][0], RULES["R8"][1])
    return None


def run_all_checks(bl_folder, audit_path, round_n):
    """Run all Rules + collect findings."""
    manifest = read_manifest(bl_folder)
    audit_events = read_audit(audit_path) if audit_path else []
    findings = []

    # R1 returns a list (R1a + R1b sub-checks, BL-218 AK-6)
    findings.extend(check_r1_batch_modes_without_berater(manifest, round_n))

    for fn in [
        lambda: check_r2_lead_fallback(manifest),
        lambda: check_r3_i_pipeline_state_missing(bl_folder, round_n),
        lambda: check_r4_no_red_tests(manifest, audit_events, round_n),
        lambda: check_r5_pattern_library_missing(manifest),
        lambda: check_r6_gold_define_missing(manifest),
        lambda: check_r7_postbatch_missing(audit_events, manifest),
        lambda: check_r8_modelsync_phantom(manifest),
    ]:
        result = fn()
        if result:
            findings.append(result)
    return findings


def verdict_from_findings(findings):
    """Map Findings -> Exit-Code/Color.

    BL-341 AK-2: INFO ist exit-NEUTRAL — es hebt das Verdikt NIE an.
      CRITICAL/HIGH -> RED (2)
      MEDIUM        -> YELLOW (1)
      INFO-only / keine Findings -> GREEN (0)
    INFO entsteht NUR durch den gated altmodisch-Downgrade (driver: ALTMODISCH)
    von R5/R6; full-pipeline ohne Marker bleibt HIGH/RED (NON-WEAKENING).
    """
    if not findings:
        return (0, "GREEN")
    sevs = {f[1] for f in findings}
    if "CRITICAL" in sevs or "HIGH" in sevs:
        return (2, "RED")
    if "MEDIUM" in sevs:
        return (1, "YELLOW")
    # nur INFO (oder andere nicht-eskalierende Raenge) -> exit-neutral GREEN
    return (0, "GREEN")


def self_test():
    """Smoke-Test: erstellt temp Manifeste mit Verletzungen, prueft Detection.

    Test A: Baseline + alle alten Rules (R1a, R2, R3, R5, R6, R7, R8).
    Test B: BL-218 AK-6 — R1b (neuer Drift: batch_modes ohne batch_mode_hints/shadow_corrected_at).
    Test C: BL-218 AK-6 — R1b CLEAR (batch_modes + modus_set_by C3 → kein R1b).
    """
    import tempfile
    failures = []

    # ── Test A: Baseline (R1a + R2 + R3 + R5 + R6 + R7 + R8) ──
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-A"
        bl_folder.mkdir()
        # batch_modes ohne Berater + ohne hints/shadow → R1a + R1b
        (bl_folder / "_manifest.md").write_text(
            "## DF_BATCH_STATE_round11\n"
            "batch_modes:\n"
            "  batch_v3_13: M2\n"
            "mode: lead_fallback\n"
            "DF_BATCH_STATE_round11_completed\n"
            "POST_SDF_PHASE_3_STATE_round_batch_v3_13\n"
            "phase_3_5_modelSync: SKIP\n"
            "loopDecision: TERMINATE\n",
            encoding="utf-8",
        )
        findings = run_all_checks(str(bl_folder), None, 11)
        rule_ids = set(f[0] for f in findings)
        expected = {"R1a", "R1b", "R2", "R3", "R5", "R6", "R7", "R8"}
        missing = expected - rule_ids
        if missing:
            failures.append(f"Test-A FAIL: missing detection: {missing}")
        rc, color = verdict_from_findings(findings)
        if color != "RED":
            failures.append(f"Test-A FAIL: expected RED, got {color}")

    # ── Test B: R1b neuer Drift — batch_modes, kein hints, kein shadow, kein C3-marker ──
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-B"
        bl_folder.mkdir()
        # Berater-Output vorhanden (R1a clear), aber kein hints/shadow → R1b fires
        (bl_folder / "_manifest.md").write_text(
            "## DF_BATCH_STATE\n"
            "batch_modes:\n"
            "  batch_1: M2\n"
            "BERATER_OUTPUTS.modusEntscheidung_round11: {}\n"
            "last_berater: C3\n",
            encoding="utf-8",
        )
        findings = run_all_checks(str(bl_folder), None, 11)
        rule_ids = set(f[0] for f in findings)
        if "R1b" not in rule_ids:
            failures.append("Test-B FAIL: R1b not detected (batch_modes ohne hints/shadow)")
        if "R1a" in rule_ids:
            failures.append("Test-B FAIL: R1a should NOT fire (berater-output present)")

    # ── Test C: R1b CLEAR — batch_modes + modus_set_by C3 vorhanden ──
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-C"
        bl_folder.mkdir()
        (bl_folder / "_manifest.md").write_text(
            "## DF_BATCH_STATE\n"
            "batch_modes:\n"
            "  batch_1: M2\n"
            "modus_set_by: _SDF_berater_modusEntscheidung\n"
            "BERATER_OUTPUTS.modusEntscheidung_round11: {}\n"
            "last_berater: C3\n",
            encoding="utf-8",
        )
        findings = run_all_checks(str(bl_folder), None, 11)
        rule_ids = set(f[0] for f in findings)
        if "R1b" in rule_ids:
            failures.append("Test-C FAIL: R1b should NOT fire (modus_set_by C3 present)")

    # ── Test D: R1b CLEAR via batch_mode_hints ──
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-D"
        bl_folder.mkdir()
        (bl_folder / "_manifest.md").write_text(
            "## DF_BATCH_STATE\n"
            "batch_modes:\n"
            "  batch_1: M2\n"
            "batch_mode_hints:\n"
            "  batch_1: M3\n"
            "BERATER_OUTPUTS.modusEntscheidung_round11: {}\n"
            "last_berater: C3\n",
            encoding="utf-8",
        )
        findings = run_all_checks(str(bl_folder), None, 11)
        rule_ids = set(f[0] for f in findings)
        if "R1b" in rule_ids:
            failures.append("Test-D FAIL: R1b should NOT fire (batch_mode_hints present)")

    # ══════════════════════════════════════════════════════════════════════
    # BL-341 (Detektor-Haertung, NON-WEAKENING): Test-E..H + Dogfood
    # ══════════════════════════════════════════════════════════════════════

    # Audit-Fixture mit 1 TDD_red-Event: unterdrueckt das OUT-OF-SCOPE R4
    # (0-RED-Tests bei M3) — analog real-altmodisch-M3-BLs, deren Build TDD_red
    # ins globale audit.jsonl schreibt. So isolieren Test-E/F den R5/R6-Pfad.
    def _write_red_audit(folder):
        ap = Path(folder) / "audit.jsonl"
        ap.write_text('{"skill": "_TDD_red", "phase": "6a"}\n', encoding="utf-8")
        return str(ap)

    # ── Test E (AK-2): altmodisch-Manifest → R5/R6 = INFO → verdict NICHT RED ──
    # batch_modes + modus_set_by + bare-key ### modusEntscheidung + driver: ALTMODISCH,
    # KEINE patternLibrary/goldDefine-Slots. R1a clean, R5/R6 -> INFO -> exit 0/1.
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-E"
        bl_folder.mkdir()
        (bl_folder / "_manifest.md").write_text(
            "## SDF_FINAL_CLOSURE\n"
            'driver: "ALTMODISCH (Team+Lead), kein Motor-LAUF."\n'
            "## DF_BATCH_STATE\n"
            "modus_set_by: _SDF_berater_modusEntscheidung\n"
            "batch_modes:\n"
            "  sub_batch_1: M3\n"
            "batch_mode_hints:\n"
            "  sub_batch_1: M3\n"
            "## BERATER_OUTPUTS\n"
            "### modusEntscheidung\n"
            'last_berater: "_SDF_berater_modusEntscheidung (worker-sdf-c3-sb1)"\n',
            encoding="utf-8",
        )
        findings = run_all_checks(str(bl_folder), _write_red_audit(tmp), 1)
        by_rule = {f[0]: f[1] for f in findings}
        rule_ids = set(by_rule)
        if "R1a" in rule_ids:
            failures.append("Test-E FAIL: R1a should NOT fire (bare-key ### modusEntscheidung + modus_set_by present)")
        if "R4" in rule_ids:
            failures.append("Test-E FAIL: R4 should NOT fire (audit-fixture liefert TDD_red; R4 out-of-scope)")
        if by_rule.get("R5") != "INFO":
            failures.append(f"Test-E FAIL: R5 should be INFO (altmodisch downgrade), got {by_rule.get('R5')}")
        if by_rule.get("R6") != "INFO":
            failures.append(f"Test-E FAIL: R6 should be INFO (altmodisch downgrade), got {by_rule.get('R6')}")
        rc, color = verdict_from_findings(findings)
        if rc not in (0, 1):
            failures.append(f"Test-E FAIL: expected exit 0/1 (NICHT RED), got exit {rc}/{color}")

    # ── Test F (AK-2 NON-WEAKENING): full-pipeline OHNE driver: ALTMODISCH ──
    # batch_modes, kein driver-Marker, keine patternLibrary/goldDefine → R5/R6 bleibt HIGH → exit 2.
    # R4 via Audit-Fixture unterdrueckt, damit das RED-Verdikt NACHWEISLICH von
    # R5/R6=HIGH getragen wird (nicht vom out-of-scope R4).
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-F"
        bl_folder.mkdir()
        (bl_folder / "_manifest.md").write_text(
            "## DF_BATCH_STATE\n"
            "modus_set_by: _SDF_berater_modusEntscheidung\n"
            "batch_modes:\n"
            "  sub_batch_1: M3\n"
            "batch_mode_hints:\n"
            "  sub_batch_1: M3\n"
            "## BERATER_OUTPUTS\n"
            "### modusEntscheidung\n"
            'last_berater: "_SDF_berater_modusEntscheidung (worker-sdf-c3-sb1)"\n',
            encoding="utf-8",
        )
        findings = run_all_checks(str(bl_folder), _write_red_audit(tmp), 1)
        by_rule = {f[0]: f[1] for f in findings}
        if "R4" in by_rule:
            failures.append("Test-F FAIL: R4 should NOT fire (audit-fixture liefert TDD_red; RED muss von R5/R6 kommen)")
        if by_rule.get("R5") != "HIGH":
            failures.append(f"Test-F FAIL (NON-WEAKENING): R5 must stay HIGH ohne driver-Marker, got {by_rule.get('R5')}")
        if by_rule.get("R6") != "HIGH":
            failures.append(f"Test-F FAIL (NON-WEAKENING): R6 must stay HIGH ohne driver-Marker, got {by_rule.get('R6')}")
        rc, color = verdict_from_findings(findings)
        if color != "RED" or rc != 2:
            failures.append(f"Test-F FAIL (NON-WEAKENING): expected RED/exit-2 (full-pipeline), got exit {rc}/{color}")

    # ── Test G (AK-1): bare-key patternLibrary/goldDefine-Slots → R5/R6 KEIN Finding ──
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-G"
        bl_folder.mkdir()
        (bl_folder / "_manifest.md").write_text(
            "## DF_BATCH_STATE\n"
            "modus_set_by: _SDF_berater_modusEntscheidung\n"
            "batch_modes:\n"
            "  sub_batch_1: M3\n"
            "batch_mode_hints:\n"
            "  sub_batch_1: M3\n"
            "## BERATER_OUTPUTS\n"
            "### modusEntscheidung\n"
            'last_berater: "_SDF_berater_modusEntscheidung (worker-sdf-c3-sb1)"\n'
            "### patternLibrary\n"
            "consumed: 3\n"
            "### goldDefine\n"
            "gold_criteria: [...]\n",
            encoding="utf-8",
        )
        findings = run_all_checks(str(bl_folder), None, 1)
        rule_ids = set(f[0] for f in findings)
        if "R5" in rule_ids:
            failures.append("Test-G FAIL: R5 should NOT fire (bare-key ### patternLibrary present, AK-1)")
        if "R6" in rule_ids:
            failures.append("Test-G FAIL: R6 should NOT fire (bare-key ### goldDefine present, AK-1)")

    # ── Test H (AK-3): R1a robust — last_berater nur klein-c3 (case-insensitive) ──
    # Einziges Berater-Signal ist ein KLEINgeschriebenes "c3" (kein modusEntscheidung-Wort,
    # kein dotted-Output). Case-insensitive last_berater.*C3 MUSS matchen → kein R1a.
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-H"
        bl_folder.mkdir()
        (bl_folder / "_manifest.md").write_text(
            "## DF_BATCH_STATE\n"
            "modus_set_by: _SDF_berater_modusEntscheidung\n"
            "batch_modes:\n"
            "  sub_batch_1: M3\n"
            "batch_mode_hints:\n"
            "  sub_batch_1: M3\n"
            "last_berater: worker-sdf-c3-sb1\n",
            encoding="utf-8",
        )
        findings = run_all_checks(str(bl_folder), None, 1)
        rule_ids = set(f[0] for f in findings)
        if "R1a" in rule_ids:
            failures.append("Test-H FAIL: R1a should NOT fire (last_berater klein-c3, case-insensitive AK-3)")

    # ── Test I (AK-2 NON-WEAKENING-2, PROSA-FALLE): "driver: ALTMODISCH" NUR ──
    # ── als Prosa im quoted Wert eines ANDEREN Keys (grounding:) → KEIN echtes ──
    # ── driver:-Feld → has_altmodisch_marker MUSS False → R5/R6 bleibt HIGH → RED. ──
    # Beweist: blosse Erwaehnung des Markers (Doku/Kommentar) triggert NICHT den
    # Downgrade (Review-Fix: Line-Anchor ^\s*driver: statt loses \bdriver:).
    with tempfile.TemporaryDirectory() as tmp:
        bl_folder = Path(tmp) / "BL-TEST-I"
        bl_folder.mkdir()
        (bl_folder / "_manifest.md").write_text(
            "## A_PIPELINE_STATE\n"
            'grounding: "R5 dotted-only; Kollaps-Marker: driver: ALTMODISCH in SDF_FINAL_CLOSURE (nur erwaehnt, kein echtes Feld)."\n'
            "## DF_BATCH_STATE\n"
            "modus_set_by: _SDF_berater_modusEntscheidung\n"
            "batch_modes:\n"
            "  sub_batch_1: M3\n"
            "batch_mode_hints:\n"
            "  sub_batch_1: M3\n"
            "## BERATER_OUTPUTS\n"
            "### modusEntscheidung\n"
            'last_berater: "_SDF_berater_modusEntscheidung (worker-sdf-c3-sb1)"\n',
            encoding="utf-8",
        )
        # Sanity: has_altmodisch_marker MUSS auf Prosa-only False sein
        if has_altmodisch_marker(read_manifest(str(bl_folder))):
            failures.append("Test-I FAIL: has_altmodisch_marker should be False (Prosa-Erwaehnung, kein echtes driver:-Feld)")
        findings = run_all_checks(str(bl_folder), _write_red_audit(tmp), 1)
        by_rule = {f[0]: f[1] for f in findings}
        if "R4" in by_rule:
            failures.append("Test-I FAIL: R4 should NOT fire (audit-fixture liefert TDD_red; RED muss von R5/R6 kommen)")
        if by_rule.get("R5") != "HIGH":
            failures.append(f"Test-I FAIL (NON-WEAKENING-2): R5 must stay HIGH (Prosa-only, kein echtes driver:-Feld), got {by_rule.get('R5')}")
        if by_rule.get("R6") != "HIGH":
            failures.append(f"Test-I FAIL (NON-WEAKENING-2): R6 must stay HIGH (Prosa-only, kein echtes driver:-Feld), got {by_rule.get('R6')}")
        rc, color = verdict_from_findings(findings)
        if color != "RED" or rc != 2:
            failures.append(f"Test-I FAIL (NON-WEAKENING-2): expected RED/exit-2 (Prosa-Erwaehnung downgradet NICHT), got exit {rc}/{color}")

    # ── Dogfood (AK-4): echte Manifeste BL-327 + BL-316 → verdict NICHT RED ──
    # read-only. Audit-Pfad script-relativ aufgeloest (real audit.jsonl enthaelt
    # TDD_red-Events → R4 false-fire-frei). Beide sind altmodische flat-node-BLs
    # mit driver: ALTMODISCH ohne patternLibrary/goldDefine → R5/R6 -> INFO.
    script_audit = Path(__file__).resolve().parent.parent / "audit" / "audit.jsonl"
    audit_arg = str(script_audit) if script_audit.exists() else None
    dogfood_backlog = Path("C:/Users/Administrator/Documents/OmniCommand/Backlog")
    dogfood_specs = [
        ("BL-327", "BL-327-parallel-params-dial-parallel-mode-nr-parallel-batches-default-1-off-single-wave"),
        ("BL-316", "BL-316-test-harness-worktree-faehig-echter-git-roundtrip-parallel-assertion"),
    ]
    for label, folder in dogfood_specs:
        bl_path = dogfood_backlog / folder
        if not (bl_path / "_manifest.md").exists():
            print(f"[SELF-TEST SKIP] Dogfood {label}: Manifest nicht gefunden ({bl_path})")
            continue
        findings = run_all_checks(str(bl_path), audit_arg, 1)
        rc, color = verdict_from_findings(findings)
        if rc not in (0, 1):
            sev_dump = ", ".join(f"{f[0]}={f[1]}" for f in findings)
            failures.append(f"Dogfood {label} FAIL: expected exit 0/1 (NICHT RED), got exit {rc}/{color} [{sev_dump}]")

    if failures:
        for f in failures:
            print(f"[SELF-TEST FAIL] {f}")
        return 1

    total = 8  # R1a+R1b+R2+R3+R5+R6+R7+R8 aus Test-A
    print(f"[SELF-TEST PASS] {total}/8 rules detected in Test-A; Test-B/C/D R1b-Logik OK, verdict=RED")
    print("[SELF-TEST PASS] BL-341: Test-E altmodisch R5/R6=INFO->exit0/1; "
          "Test-F NON-WEAKENING full-pipeline R5/R6=HIGH->exit2; "
          "Test-G bare-key patternLibrary/goldDefine -> kein Finding; "
          "Test-H R1a case-insensitive klein-c3 OK; "
          "Test-I NON-WEAKENING-2 Prosa-Erwaehnung 'driver: ALTMODISCH' downgradet NICHT (R5/R6=HIGH->exit2); "
          "Dogfood BL-327+BL-316 NICHT RED")
    return 0


def main(argv):
    p = argparse.ArgumentParser(description="BL-NEW-RCA-486 Process-Audit (Ring 2)")
    p.add_argument("--bl-folder", help="Path to BL-Folder with _manifest.md")
    p.add_argument("--round", type=int, default=1, help="Round number")
    p.add_argument("--audit-jsonl", default=".claude/audit/audit.jsonl")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--json", action="store_true", help="Output JSON statt human-readable")
    args = p.parse_args(argv[1:])

    if args.self_test:
        return self_test()

    if not args.bl_folder:
        print("[ERROR] --bl-folder required (or --self-test)", file=sys.stderr)
        return 1

    findings = run_all_checks(args.bl_folder, args.audit_jsonl, args.round)
    rc, color = verdict_from_findings(findings)

    if args.json:
        print(json.dumps({
            "bl_folder": args.bl_folder,
            "round": args.round,
            "verdict": color,
            "exit_code": rc,
            "findings": [{"rule": f[0], "severity": f[1], "msg": f[2]} for f in findings]
        }, indent=2))
    else:
        print(f"=== process_audit.py — {args.bl_folder} Round {args.round} ===")
        print(f"Verdict: {color}  (exit_code={rc})")
        if findings:
            print(f"\n{len(findings)} Findings:")
            for rule, sev, msg in findings:
                print(f"  [{sev}] {rule}: {msg}")
        else:
            print("  GREEN — alle Rules passed")

    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
