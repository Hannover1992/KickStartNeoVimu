#!/usr/bin/env python3
"""Tests fuer BL-365 AK-4: N=1-Fast-Path-Bypass in guard_a_idf_handoff.py
und guard_idf_sdf_handoff.py.

Wenn der Marker `idf_bypass_reason: "N=1_fastpath_BL-365"` im Manifest steht,
ist der Fast-Path legitim: ein einzelnes PL-Item fliesst direkt (A->SDF ohne
vollstaendigen IDF-Lauf). Die Guards duerfen diesen Pfad NICHT blocken.

RED-Ring 1 (guard_a_idf_handoff): Bypass mit Marker -> KEIN Block.
RED-Ring 2 (guard_a_idf_handoff): ohne Marker -> Block bleibt (kein Loch).
RED-Ring 3 (guard_idf_sdf_handoff): Bypass mit Marker -> KEIN Block.
RED-Ring 4 (guard_idf_sdf_handoff): ohne Marker -> Block bleibt (kein Loch).
RED-Ring 5 (Loch-Schutz): Marker mit falschem Wert -> kein Bypass.

RED-Begruendung: Beide Guards kennen idf_bypass_reason noch nicht -> sie blocken
auch den legitimen N=1-Fast-Path (exit 2 statt exit 0). Tests FAILEN im RED-State.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_A_IDF = SCRIPT_DIR / "guard_a_idf_handoff.py"
GUARD_IDF_SDF = SCRIPT_DIR / "guard_idf_sdf_handoff.py"

# Kanonischer Bypass-Marker (AK-4 BL-365)
BYPASS_MARKER = 'N=1_fastpath_BL-365'


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _run_guard_skill_load(guard_path, skill_name, audit_lines, extra_env=None):
    """Simuliert einen Skill-Load-Event (kein Edit/Write) fuer guard_a_idf_handoff.
    Enforcement-Punkt fuer guard_a_idf_handoff ist der IDF-Eintritt (enforce-AFTER-write,
    BL-350 AK-2): tool_name='mcp__claude_ai__execute_skill' mit skill_name im tool_input."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    ) as sp:
        sp.write("**enforceProcess:** true\n")
        sp_path = sp.name

    env = os.environ.copy()
    env["OMNI_A_IDF_HANDOFF_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    if extra_env:
        env.update(extra_env)

    event = {
        "tool_name": "mcp__claude_ai__execute_skill",
        "tool_input": {"skill_name": skill_name},
    }
    proc = subprocess.run(
        [sys.executable, str(guard_path)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


def _run_guard_manifest_write(guard_path, manifest_text, audit_lines,
                               audit_env_key="OMNI_A_IDF_HANDOFF_AUDIT", enforce=True):
    """Simuliert einen Edit/Write-Event auf ein _manifest.md fuer beide Guards.
    Schreibt synthetische manifest- + audit- + session_params-Dateien und gibt
    das Guard-Verdikt zurueck."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_manifest.md", delete=False, encoding="utf-8"
    ) as mf:
        mf.write(manifest_text)
        manifest_path = mf.name
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    ) as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp_path = sp.name

    env = os.environ.copy()
    env[audit_env_key] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path

    event = {
        "tool_name": "Edit",
        "tool_input": {"file_path": manifest_path, "new_string": manifest_text},
    }
    proc = subprocess.run(
        [sys.executable, str(guard_path)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )
    Path(manifest_path).unlink(missing_ok=True)
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


# ---------------------------------------------------------------------------
# RED-Ring 1: guard_a_idf_handoff + Bypass-Marker -> KEIN Block
# ---------------------------------------------------------------------------

def test_guard_a_idf_bypass_marker_allows_idf_load():
    """RED-Ring 1 (BL-365 AK-4): guard_a_idf_handoff blockt den Skill-Load
    _IDF_orchestrate, wenn kein _A_postRoute nach _A_orchestrate im Audit steht.
    AK-4-Soll: Wenn der Manifest-State den Marker
    `idf_bypass_reason: "N=1_fastpath_BL-365"` enthaelt, ist der IDF-Eintritt
    legitim (N=1-Fast-Path) -> KEIN Block (exit 0, continue=True).

    RED-Begruendung: Guard kennt idf_bypass_reason noch nicht -> gibt exit 2
    (Block) statt exit 0. Test FAILT im RED-State.

    Enforcement-Punkt: Skill-Load _IDF_orchestrate (enforce-AFTER-write,
    guard_a_idf_handoff Trigger A, BL-350 AK-2). Audit enthaelt _A_orchestrate
    OHNE _A_postRoute (das ist der Bypass-Kontext den der Marker legitimiert).
    """
    # Audit: _A_orchestrate lief, kein _A_postRoute (N=1-Fast-Path umgeht postRoute)
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"},
        # Kein _A_postRoute — N=1-Fast-Path braucht den postRoute-Seam nicht
    ]
    # Manifest enthaelt den Bypass-Marker (wird ueber OMNI_A_IDF_BYPASS_MANIFEST
    # oder als State-Context bereitgestellt; der Guard soll den Audit-State lesen)
    # Technisch: wir schreiben den Marker als zusaetzlichen Audit-Eintrag,
    # da der Guard Manifest-Inhalt beim Skill-Load-Trigger nicht direkt liest.
    # AK-4-Spec: Guard liest idf_bypass_reason aus dem letzten Manifest-State-
    # Audit-Eintrag (oder Env OMNI_IDF_BYPASS_REASON fuer Test-Override).
    env_extra = {"OMNI_IDF_BYPASS_REASON": BYPASS_MARKER}
    proc, r = _run_guard_skill_load(
        guard_path=GUARD_A_IDF,
        skill_name="_IDF_orchestrate",
        audit_lines=audit,
        extra_env=env_extra,
    )
    assert proc.returncode == 0, (
        f"BL-365 AK-4: Skill-Load _IDF_orchestrate MIT Bypass-Marker "
        f"'{BYPASS_MARKER}' -> KEIN Block erwartet (exit 0), war exit {proc.returncode}. "
        f"Guard kennt idf_bypass_reason noch nicht (RED-State)."
    )
    assert r.get("continue") is True, (
        f"BL-365 AK-4: N=1-Fast-Path mit Marker '{BYPASS_MARKER}' -> "
        f"continue=True erwartet (Guard soll Fast-Path durchlassen)."
    )


# ---------------------------------------------------------------------------
# RED-Ring 2: guard_a_idf_handoff OHNE Marker -> Block bleibt (kein Loch)
# ---------------------------------------------------------------------------

def test_guard_a_idf_without_bypass_marker_still_blocks():
    """RED-Ring 2 (BL-365 AK-4 Loch-Schutz): guard_a_idf_handoff blockt
    weiterhin den IDF-Eintritt ohne _A_postRoute, wenn der Bypass-Marker FEHLT.

    Prueft: das neue Bypass-Feature oeffnet kein Loch fuer normale Faelle.
    Normaler Block-Pfad (INV-A-GUARD-1) muss unveraendert funktionieren.

    PASS im RED-State erwartet (Guard blockt bereits korrekt ohne Marker).
    Bleibt PASS nach GREEN-Implementierung (Regression-Schutz).
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_A_orchestrate"},
        # kein _A_postRoute, kein Bypass-Marker -> normaler Block-Pfad
    ]
    # KEIN OMNI_IDF_BYPASS_REASON gesetzt
    proc, r = _run_guard_skill_load(
        guard_path=GUARD_A_IDF,
        skill_name="_IDF_orchestrate",
        audit_lines=audit,
    )
    assert proc.returncode == 2, (
        f"BL-365 AK-4 Loch-Schutz: Kein Bypass-Marker -> normaler BLOCK erwartet "
        f"(exit 2), war exit {proc.returncode}. "
        f"Das Bypass-Feature darf kein Loch fuer normale Faelle oeffnen."
    )
    assert r.get("continue") is not True, (
        "Ohne Bypass-Marker darf der Guard NICHT 'continue=True' liefern "
        "(normaler Block-Pfad INV-A-GUARD-1 muss unveraendert funktionieren)."
    )


# ---------------------------------------------------------------------------
# RED-Ring 3: guard_idf_sdf_handoff + Bypass-Marker -> KEIN Block
# ---------------------------------------------------------------------------

def test_guard_idf_sdf_bypass_marker_allows_idf_done_write():
    """RED-Ring 3 (BL-365 AK-4): guard_idf_sdf_handoff blockt den Write
    idf_status=IDF_DONE + routing_target=SDF, wenn kein _SDF_orchestrate nach
    _IDF_orchestrate im Audit steht.
    AK-4-Soll: Wenn der Manifest-Write den Marker
    `idf_bypass_reason: "N=1_fastpath_BL-365"` enthaelt, ist das IDF-Ende
    legitim (N=1-Fast-Path umgeht den normalen IDF-Lauf) -> KEIN Block
    (exit 0, continue=True).

    RED-Begruendung: Guard kennt idf_bypass_reason noch nicht -> gibt exit 2
    (Block) statt exit 0. Test FAILT im RED-State.
    """
    manifest = (
        "IDF_PIPELINE_STATE:\n"
        f'  idf_status: "IDF_DONE"\n'
        f'  routing_target: "SDF"\n'
        f'  idf_bypass_reason: "{BYPASS_MARKER}"\n'
    )
    # Audit: _IDF_orchestrate lief, kein _SDF_orchestrate (N=1-Fast-Path)
    audit = [{"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"}]
    proc, r = _run_guard_manifest_write(
        guard_path=GUARD_IDF_SDF,
        manifest_text=manifest,
        audit_lines=audit,
        audit_env_key="OMNI_IDF_SDF_HANDOFF_AUDIT",
        enforce=True,
    )
    assert proc.returncode == 0, (
        f"BL-365 AK-4: IDF-Ende-Write MIT Bypass-Marker '{BYPASS_MARKER}' "
        f"-> KEIN Block erwartet (exit 0), war exit {proc.returncode}. "
        f"Guard kennt idf_bypass_reason noch nicht (RED-State)."
    )
    assert r.get("continue") is True, (
        f"BL-365 AK-4: N=1-Fast-Path mit Marker '{BYPASS_MARKER}' -> "
        f"continue=True erwartet (Guard soll Fast-Path durchlassen)."
    )


# ---------------------------------------------------------------------------
# RED-Ring 4: guard_idf_sdf_handoff OHNE Marker -> Block bleibt (kein Loch)
# ---------------------------------------------------------------------------

def test_guard_idf_sdf_without_bypass_marker_still_blocks():
    """RED-Ring 4 (BL-365 AK-4 Loch-Schutz): guard_idf_sdf_handoff blockt
    weiterhin das IDF-Ende-Signal ohne _SDF_orchestrate-Handoff, wenn der
    Bypass-Marker FEHLT.

    Prueft: das neue Bypass-Feature oeffnet kein Loch fuer normale Faelle.
    Normaler Block-Pfad (BL-313 AK-1) muss unveraendert funktionieren.

    PASS im RED-State erwartet (Guard blockt bereits korrekt ohne Marker).
    Bleibt PASS nach GREEN-Implementierung (Regression-Schutz).
    """
    manifest = (
        "IDF_PIPELINE_STATE:\n"
        '  idf_status: "IDF_DONE"\n'
        '  routing_target: "SDF"\n'
        # KEIN idf_bypass_reason -> normaler Block-Pfad
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"}]
    proc, r = _run_guard_manifest_write(
        guard_path=GUARD_IDF_SDF,
        manifest_text=manifest,
        audit_lines=audit,
        audit_env_key="OMNI_IDF_SDF_HANDOFF_AUDIT",
        enforce=True,
    )
    assert proc.returncode == 2, (
        f"BL-365 AK-4 Loch-Schutz: Kein Bypass-Marker -> normaler BLOCK erwartet "
        f"(exit 2), war exit {proc.returncode}. "
        f"Das Bypass-Feature darf kein Loch fuer normale Faelle oeffnen."
    )
    assert r.get("continue") is not True, (
        "Ohne Bypass-Marker darf der Guard NICHT 'continue=True' liefern "
        "(normaler Block-Pfad BL-313 AK-1 muss unveraendert funktionieren)."
    )


# ---------------------------------------------------------------------------
# RED-Ring 5: Loch-Schutz — falscher Marker-Wert -> kein Bypass
# ---------------------------------------------------------------------------

def test_guard_idf_sdf_wrong_marker_value_still_blocks():
    """RED-Ring 5 (BL-365 AK-4 Loch-Schutz — falscher Wert): Der Bypass
    funktioniert NUR mit dem exakten kanonischen Marker-Wert
    'N=1_fastpath_BL-365'. Ein anderer Wert (z.B. 'N=1_fastpath' ohne BL-ID,
    oder 'bypass', oder ein leerer String) darf KEINEN Bypass ausloesen.

    Prueft: Kein generisches 'idf_bypass_reason: anything' als Bypass.
    Guard muss den Wert exakt pruefen (nicht nur das Feld).

    RED-Begruendung: Wenn der Guard noch gar keine Bypass-Logik hat (RED-State),
    blockt er korrekterweise -> PASS im RED-State. Dieser Test ist primarer
    Regression-Schutz fuer nach GREEN: falscher Wert -> weiterhin Block.
    """
    manifest = (
        "IDF_PIPELINE_STATE:\n"
        '  idf_status: "IDF_DONE"\n'
        '  routing_target: "SDF"\n'
        '  idf_bypass_reason: "N=1_fastpath"\n'  # falscher Wert (kein BL-365)
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"}]
    proc, r = _run_guard_manifest_write(
        guard_path=GUARD_IDF_SDF,
        manifest_text=manifest,
        audit_lines=audit,
        audit_env_key="OMNI_IDF_SDF_HANDOFF_AUDIT",
        enforce=True,
    )
    assert proc.returncode == 2, (
        f"BL-365 AK-4 Loch-Schutz: Falscher Marker-Wert 'N=1_fastpath' (ohne BL-365) "
        f"-> normaler BLOCK erwartet (exit 2), war exit {proc.returncode}. "
        f"Guard darf NUR den exakten Wert '{BYPASS_MARKER}' als Bypass akzeptieren."
    )
    assert r.get("continue") is not True, (
        f"Falscher Marker-Wert 'N=1_fastpath' darf KEINEN Bypass ausloesen. "
        f"Nur exakter Wert '{BYPASS_MARKER}' ist gueltig."
    )


if __name__ == "__main__":
    tests = [
        test_guard_a_idf_bypass_marker_allows_idf_load,
        test_guard_a_idf_without_bypass_marker_still_blocks,
        test_guard_idf_sdf_bypass_marker_allows_idf_done_write,
        test_guard_idf_sdf_without_bypass_marker_still_blocks,
        test_guard_idf_sdf_wrong_marker_value_still_blocks,
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
