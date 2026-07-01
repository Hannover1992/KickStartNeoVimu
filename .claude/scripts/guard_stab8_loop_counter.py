#!/usr/bin/env python3
"""
guard_stab8_loop_counter.py — Intra-Skill Stabilization Hook S#8

Schuetzt die BL-075 Anti-Zirkel-Counter im _manifest.md vor unauthorisierter
Manipulation durch Team Lead oder Sub-Agents:

  - BDF_PIPELINE_STATE.bdf_scan_iterations  (BL-075 T4, max 20)
  - BDF_PIPELINE_STATE.reifung_cycles       (BL-075 T2, max 3)
  - BDF_PIPELINE_STATE.bdf_bl_handoff_depth (BL-075 T2, max 2)

Geschuetzt sind zwei Klassen von Verletzungen:

  1) **Counter-Reset ohne Berechtigung**: Wenn N → 0 (oder N → kleinerer Wert)
     ohne legitimen Reset-Pfad geschrieben wird. Legitime Reset-Pfade lt.
     _BDF_orchestrate.md BL-075:
       * bdf_scan_iterations / reifung_cycles: Reset NUR nach einem
         erfolgreichen Item-Done-Block (Phase 5 Auto-Continue, ~Zeile 1248).
         Marker: `items_done` / `item_status: DONE` / `bdf_item_complete`
         im selben Edit-Hunk ODER bereits im aktuellen Manifest.
       * bdf_bl_handoff_depth: Reset NUR via Dekrement-Pfad (`-= 1`) der
         direkt nach Sub-BDF-Rueckkehr ausgefuehrt wird. Wenn N → N-1
         OK; aber N → 0 oder spruenge groesser 1 → Block.

  2) **Counter ueber Max** (Sabotage / Overflow-Trick): Ein Wert
     groesser als bdf_max_* (Defaults 20 / 3 / 2). Per Default werden die
     Caps streng durchgesetzt (kein Lese-Roundtrip zur Config noetig).

Pragmatik-Override: env `OMNI_COUNTER_RESET_OK=1` (manueller Vault-Cleanup).

enforceProcess=true (Default): BLOCKIERT (continue=false)
enforceProcess=false: NUR Warning (continue=true)

Style-Reference: guard_modus_writer.py (BL-165 AK-5).
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# ───── Counter-Spec (BL-075) ─────
COUNTER_LIMITS = {
    "bdf_scan_iterations": 20,    # BL-075 T4 (RF-BDF-034)
    "reifung_cycles": 3,          # BL-075 T2 (RF-BDF-032)
    "bdf_bl_handoff_depth": 2,    # BL-075 T2 INV-5
}

# Counter die ueber Item-Done-Block resettet werden duerfen (Phase 5)
ITEM_DONE_RESET_COUNTERS = {"bdf_scan_iterations", "reifung_cycles"}

# Counter mit explizitem Dekrement-Pfad (jede Stufe -= 1)
DECREMENT_ONLY_COUNTERS = {"bdf_bl_handoff_depth"}

# Marker die einen legitimen Item-Done-Block kennzeichnen
ITEM_DONE_MARKERS = [
    r"items_done\s*[:=]",
    r"item_status\s*[:=]\s*[\"']?DONE[\"']?",
    r"bdf_item_complete\s*[:=]\s*[\"']?true[\"']?",
    r"Anti-Zirkel\s+Zaehler\s+Reset\s+nach\s+erfolgreichem\s+Item",  # Phase 5 Log-Line
    r"BDF_PIPELINE_STATE\.items_done",
]

# Pattern zum Extrahieren der Counter-Werte aus Manifest-Content
def _counter_pattern(name: str) -> re.Pattern:
    # Matched z.B.:
    #   bdf_scan_iterations: 5
    #   BDF_PIPELINE_STATE.bdf_scan_iterations: 5
    #   bdf_scan_iterations = 5
    return re.compile(
        rf"(?:BDF_PIPELINE_STATE\.)?{re.escape(name)}\s*[:=]\s*([0-9]+)",
        re.MULTILINE,
    )


def _resolve_vault_session_params():
    """Vault-aware _session_params.md Pfad (wie guard_modus_writer.py)."""
    try:
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5,
                cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                vault_root_str = proc.stdout.strip()
                if vault_root_str:
                    return Path(vault_root_str) / "_session_params.md"
    except Exception:
        pass
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


SESSION_PARAMS_FILE = _resolve_vault_session_params()


def read_enforce_process() -> bool:
    """Test-Override OMNI_ENFORCE_LOOP_COUNTER_GUARD=1 erzwingt enforce=true."""
    if os.environ.get("OMNI_ENFORCE_LOOP_COUNTER_GUARD") == "1":
        return True
    try:
        if not SESSION_PARAMS_FILE.exists():
            return True
        content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
        if m:
            return m.group(1) == "true"
    except Exception:
        pass
    return True


def append_guard_log(violation_type: str, details: str, blocked: bool) -> None:
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def extract_counters(text: str) -> dict:
    """Extrahiert {counter_name: int_value} aus Text. Nur erste Vorkommen."""
    out = {}
    for name in COUNTER_LIMITS:
        m = _counter_pattern(name).search(text)
        if m:
            try:
                out[name] = int(m.group(1))
            except ValueError:
                pass
    return out


def has_item_done_marker(text: str) -> bool:
    for pat in ITEM_DONE_MARKERS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def read_current_manifest(file_path: str) -> str:
    """Liest aktuellen Manifest-Inhalt von Disk; '' wenn unmoeglich."""
    try:
        p = Path(file_path)
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return ""


def check_violations(
    file_path: str,
    new_content: str,
    tool_name: str,
) -> list:
    """
    Pruefen ob das Edit/Write Counter-Regeln verletzt.

    Vorgehen:
      - Edit: alter Wert kommt aus on-disk Manifest, neuer Wert aus new_content
      - Write: alter Wert kommt aus on-disk Manifest (vorher), neuer Wert aus
        new_content (komplett neu)
    """
    violations = []

    new_vals = extract_counters(new_content)
    # Wenn der Edit keinen Counter beruehrt → kein Violation
    if not new_vals:
        return violations

    # Aktuelle Werte aus File-State (falls vorhanden)
    disk_text = read_current_manifest(file_path)
    old_vals = extract_counters(disk_text)

    # Check 1: Counter > Max
    for name, new_val in new_vals.items():
        cap = COUNTER_LIMITS[name]
        if new_val > cap:
            violations.append(
                f"{name}={new_val} > max {cap} (Counter-Overflow / Sabotage)"
            )

    # Check 2: Counter-Reset ohne Berechtigung
    for name, new_val in new_vals.items():
        old_val = old_vals.get(name)
        if old_val is None:
            # Kein vorheriger Wert bekannt — nichts zu vergleichen.
            # Bei einem Write ohne Disk-State: nichts vom Reset-Pfad pruefbar.
            continue
        if new_val >= old_val:
            # Inkrement oder Gleichbleibend → OK
            continue

        # Hier: new_val < old_val (Regression)
        if name in ITEM_DONE_RESET_COUNTERS:
            # Reset NUR mit Item-Done-Marker erlaubt.
            # Marker kann im neuen Content selbst sein ODER bereits im
            # aktuellen Disk-State (z.B. Item-Done in Phase 5 vorher geschrieben).
            if has_item_done_marker(new_content) or has_item_done_marker(disk_text):
                continue
            violations.append(
                f"{name}: {old_val} → {new_val} (Reset ohne sichtbaren "
                f"Item-Done-Block) — Counter-Reset ohne Berechtigung"
            )
        elif name in DECREMENT_ONLY_COUNTERS:
            # Erlaubt: N → N-1 (Dekrement-Pfad).
            # Verboten: alles andere (N → 0 ausser N==1, N → N-2, ...).
            if new_val == old_val - 1:
                continue
            violations.append(
                f"{name}: {old_val} → {new_val} (kein korrekter "
                f"Dekrement-Pfad — erwartet {old_val - 1})"
            )
        else:
            violations.append(
                f"{name}: {old_val} → {new_val} (Reset nicht legitim)"
            )

    return violations


def main():
    # === Globaler Owner-Kill-Switch (BL-223): enforceProcess=false -> Guard aus ===
    import os as _os, json as _json
    if _os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(_json.dumps({"continue": True}))
        return
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sd = str(_P(__file__).parent.absolute())
        if _sd not in _sys.path:
            _sys.path.insert(0, _sd)
        from _enforce_gate import enforce_active
        if not enforce_active():
            print(_json.dumps({"continue": True}))
            return
    except Exception:
        pass
    try:
        hook_data = json.loads(sys.stdin.read())
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        if tool_name not in ("Edit", "Write"):
            print(json.dumps({"continue": True}))
            return

        file_path = ""
        new_content = ""
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "")
            new_content = tool_input.get("new_string", "") or tool_input.get("content", "")

        # Trigger NUR bei _manifest.md Edits
        if not file_path or "_manifest.md" not in file_path:
            print(json.dumps({"continue": True}))
            return

        # Pragmatik-Override
        if os.environ.get("OMNI_COUNTER_RESET_OK") == "1":
            print(json.dumps({"continue": True}))
            return

        violations = check_violations(file_path, new_content, tool_name)
        if not violations:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()
        violation_str = "; ".join(violations)
        message = (
            f"[GUARD-VIOLATION] STAB8_LOOP_COUNTER_GUARD (BL-075 T2/T4 Anti-Zirkel): "
            f"{violation_str}. "
            f"Schutz: bdf_scan_iterations (max {COUNTER_LIMITS['bdf_scan_iterations']}), "
            f"reifung_cycles (max {COUNTER_LIMITS['reifung_cycles']}), "
            f"bdf_bl_handoff_depth (max {COUNTER_LIMITS['bdf_bl_handoff_depth']}). "
            f"Reset von bdf_scan_iterations/reifung_cycles NUR mit Item-Done-Marker. "
            f"bdf_bl_handoff_depth NUR via Dekrement-Pfad (-= 1). "
            f"Override: OMNI_COUNTER_RESET_OK=1 fuer manuellen Vault-Cleanup. "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )
        print(json.dumps({
            "continue": not enforce,
            "message": message,
        }))
        append_guard_log("STAB8_LOOP_COUNTER_VIOLATION", violation_str, enforce)

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_stab8_loop_counter Error: {e}\n")
        except Exception:
            pass
        # Fail-open: bei Hook-Fehlern niemals den User blockieren.
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
