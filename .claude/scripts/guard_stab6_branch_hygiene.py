#!/usr/bin/env python3
"""
Claude Code Hook — Branch-Hygiene Guard (Stab S#6, BL-194).

PreToolUse-Hook fuer Skill(_BDF_orchestrate) und Skill(_SDF_orchestrate),
sofern der Aufruf mit `--batch=` Argument erfolgt (Batch-Start).

Hintergrund (RCA DCSRE-486):
  Multi-Worktree-Drift: Uncommitted Changes vor neuem Batch-Start fuehren
  zu Cross-Batch-Code-Mixing. DCSRE-486 hatte das mehrfach.

Pruefungs-Logik (via `git status --porcelain`):
  - 0..N modified files (N=WARN_THRESHOLD, default 5): continue=true (sauber genug)
  - > WARN_THRESHOLD modified files UND kein Batch-Marker in einem der
    modifizierten _manifest.md Dateien: WARN (continue=true mit Message)
  - > BLOCK_THRESHOLD modified files (default 20): BLOCK
    "Branch nicht sauber — moegliche Cross-Batch-Drift"

Batch-Marker (Heuristik):
  Eine modifizierte _manifest.md zaehlt als "laufender Batch" wenn sie
  einen `DF_BATCH_STATE`-Block enthaelt. Dann ist der Drift legitime
  Batch-Fortsetzung, nicht Cross-Batch-Drift.

Override (Reihenfolge):
  1. Env-Var `OMNI_BRANCH_HYGIENE_SKIP=1` -> skip (continue=true)
  2. `_session_params.md` Zeile `branch_hygiene: skip` -> skip
  3. `_session_params.md` Zeile `**enforceProcess:** false` -> WARN-only

Test-Override:
  - `OMNI_ENFORCE_STAB6_GUARD=1` erzwingt enforce=true (fuer pytest)
  - `OMNI_STAB6_GIT_STATUS` setzt simulierten git status --porcelain Output
  - `OMNI_STAB6_BATCH_MARKER` setzt simulierten Batch-Marker-Check (0/1)

Pattern: guard_modus_writer.py (Style) + process_audit_stop_hook.py
(subprocess git status). Master-Analyse:
.claude/output/Enforce_Refactor_Master_Analyse_2026-05-27.md (Schicht 2/3).
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

# Skills die dieser Guard ueberwacht
TARGET_SKILLS = {"_BDF_orchestrate", "_SDF_orchestrate"}

# Threshold-Defaults (override via env OMNI_STAB6_WARN/_BLOCK)
WARN_THRESHOLD = int(os.environ.get("OMNI_STAB6_WARN", "5"))
BLOCK_THRESHOLD = int(os.environ.get("OMNI_STAB6_BLOCK", "20"))

# Batch-Argument: --batch=foo / --batch foo / --batch="foo"
BATCH_ARG_PATTERN = re.compile(r"--batch(?:\s*=\s*|\s+)[\"']?[^\s\"']+", re.IGNORECASE)

# Manifest-Pfad-Match in `git status --porcelain` Zeilen
# Format: ' M path/to/_manifest.md' / 'MM path/...' / '?? path/...'
MANIFEST_LINE_PATTERN = re.compile(r"^\s*[\?MARCDU!]{1,2}\s+(.+_manifest\.md)\s*$")

# Batch-Marker in _manifest.md (laufender Batch-Block vorhanden)
BATCH_MARKER_PATTERN = re.compile(
    r"##\s*DF_BATCH_STATE"
    r"|^\s*DF_BATCH_STATE\s*[:=]"
    r"|^\s*batch_id\s*[:=]\s*[\"']?[A-Za-z0-9_\-]+"
    r"|^\s*current_batch\s*[:=]\s*[\"']?[A-Za-z0-9_\-]+",
    re.MULTILINE,
)


def _resolve_vault_session_params() -> Path:
    """Vault-Root via resolve_vault_root.py finden, sonst lokaler Fallback."""
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


def _read_session_params() -> str:
    """Liest _session_params.md vollstaendig. Leer bei Fehler.

    Test-Override: OMNI_STAB6_SESSION_PARAMS (Pfad).
    """
    override = os.environ.get("OMNI_STAB6_SESSION_PARAMS")
    target = Path(override) if override else SESSION_PARAMS_FILE
    try:
        if target.exists():
            return target.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


def session_says_skip() -> bool:
    """True wenn _session_params.md `branch_hygiene: skip` enthaelt."""
    content = _read_session_params()
    if not content:
        return False
    return bool(re.search(
        r"(?m)^\s*\*?\*?branch_hygiene\*?\*?\s*[:=]\s*[\"']?skip[\"']?",
        content,
        re.IGNORECASE,
    ))


def read_enforce_process() -> bool:
    """Liest enforceProcess aus _session_params.md.

    Default true (BLOCKIERT). enforceProcess=false -> WARN-only.
    Test-Override: OMNI_ENFORCE_STAB6_GUARD=1 erzwingt true; =0 erzwingt false.
    """
    val = os.environ.get("OMNI_ENFORCE_STAB6_GUARD")
    if val == "1":
        return True
    if val == "0":
        return False
    content = _read_session_params()
    if not content:
        return True
    m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
    if m:
        return m.group(1).lower() == "true"
    return True


def env_says_skip() -> bool:
    return os.environ.get("OMNI_BRANCH_HYGIENE_SKIP") == "1"


def append_guard_log(skill: str, severity: str, details: str) -> None:
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = (
            f"- [{timestamp}] **STAB6_BRANCH_HYGIENE** [{severity}]: "
            f"Skill({skill}) — {details}\n"
        )
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def append_debug_log(msg: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] guard_stab6_branch_hygiene: {msg}\n")
    except Exception:
        pass


def has_batch_arg(args: str) -> bool:
    if not args:
        return False
    return bool(BATCH_ARG_PATTERN.search(args))


def run_git_status() -> str:
    """Liefert `git status --porcelain` Output.

    Test-Override: OMNI_STAB6_GIT_STATUS setzt simulierten Output (multi-line).
    Bei git-Fehlern: leere Zeichenkette (= sauber).
    """
    sim = os.environ.get("OMNI_STAB6_GIT_STATUS")
    if sim is not None:
        return sim
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(ROOT_DIR), timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout or ""
    except Exception as e:
        append_debug_log(f"git status failed: {e}")
    return ""


def count_modified_files(porcelain: str) -> int:
    """Anzahl Zeilen mit Aenderungs-Status (modified/added/renamed/untracked).

    Wir zaehlen ALLE Zeilen — auch untracked (??), weil neue Files Drift sind.
    """
    if not porcelain:
        return 0
    return sum(1 for line in porcelain.splitlines() if line.strip())


def has_batch_marker_in_modified_manifests(porcelain: str) -> bool:
    """Sucht in modifizierten _manifest.md Dateien nach DF_BATCH_STATE-Block.

    Test-Override: OMNI_STAB6_BATCH_MARKER=1 erzwingt true; =0 erzwingt false.
    """
    val = os.environ.get("OMNI_STAB6_BATCH_MARKER")
    if val == "1":
        return True
    if val == "0":
        return False

    if not porcelain:
        return False

    manifest_paths = []
    for line in porcelain.splitlines():
        m = MANIFEST_LINE_PATTERN.match(line)
        if m:
            manifest_paths.append(m.group(1).strip())

    for rel_path in manifest_paths:
        candidate = ROOT_DIR / rel_path
        if not candidate.exists():
            # absoluter Pfad als Fallback
            candidate = Path(rel_path)
        try:
            if candidate.is_file():
                content = candidate.read_text(encoding="utf-8", errors="replace")
                if BATCH_MARKER_PATTERN.search(content):
                    return True
        except Exception:
            continue
    return False


def evaluate_hygiene(porcelain: str) -> tuple[str, int, bool]:
    """Returns: (severity, modified_count, has_marker)

    severity ∈ {OK, WARN, BLOCK}
    """
    count = count_modified_files(porcelain)
    marker = has_batch_marker_in_modified_manifests(porcelain)

    if count > BLOCK_THRESHOLD:
        return "BLOCK", count, marker
    if count > WARN_THRESHOLD and not marker:
        return "WARN", count, marker
    return "OK", count, marker


def build_block_message(skill: str, count: int) -> str:
    return (
        f"[STAB6_BRANCH_HYGIENE BLOCK] Skill({skill}): "
        f"{count} modified files in git status (Threshold {BLOCK_THRESHOLD}). "
        f"Branch nicht sauber — moegliche Cross-Batch-Drift (RCA DCSRE-486). "
        f"Aktion: git status pruefen, Cross-Batch-Aenderungen committen oder "
        f"stashen, dann Batch erneut starten. "
        f"Override: env OMNI_BRANCH_HYGIENE_SKIP=1 oder "
        f"_session_params.md `branch_hygiene: skip`."
    )


def build_warn_message(skill: str, count: int) -> str:
    return (
        f"[STAB6_BRANCH_HYGIENE WARN] Skill({skill}): "
        f"{count} modified files in git status, kein DF_BATCH_STATE-Marker. "
        f"Empfehlung: Branch-Hygiene pruefen vor Batch-Start. "
        f"Override: OMNI_BRANCH_HYGIENE_SKIP=1 oder branch_hygiene: skip."
    )


def main() -> None:
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
        raw = sys.stdin.read()
        hook_data = json.loads(raw) if raw.strip() else {}
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        # Nur Skill-Tool relevant
        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        if not isinstance(tool_input, dict):
            print(json.dumps({"continue": True}))
            return

        skill = tool_input.get("skill", "") or ""
        if skill not in TARGET_SKILLS:
            print(json.dumps({"continue": True}))
            return

        args = tool_input.get("args", "") or ""
        if not has_batch_arg(args):
            # Skill ohne --batch-Argument ist nicht Batch-Start
            print(json.dumps({"continue": True}))
            return

        # Override-Checks (in dieser Reihenfolge)
        if env_says_skip():
            print(json.dumps({"continue": True}))
            return
        if session_says_skip():
            print(json.dumps({"continue": True}))
            return

        porcelain = run_git_status()
        severity, count, marker = evaluate_hygiene(porcelain)

        if severity == "OK":
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()

        if severity == "BLOCK" and enforce:
            details = f"{count} modified files (Threshold {BLOCK_THRESHOLD})"
            append_guard_log(skill, "BLOCKED", details)
            sys.stderr.write(
                f"[guard_stab6_branch_hygiene BLOCK] Skill({skill}) "
                f"count={count} marker={marker}\n"
            )
            print(json.dumps({
                "continue": False,
                "message": build_block_message(skill, count),
            }))
            return

        # WARN-Pfad (auch BLOCK bei enforce=false wird zu WARN degradiert)
        warn_severity = "WARNED" if severity == "WARN" else "BLOCK_DOWNGRADED_WARN"
        details = f"{count} modified files, batch_marker={marker}"
        append_guard_log(skill, warn_severity, details)
        sys.stderr.write(
            f"[guard_stab6_branch_hygiene WARN] Skill({skill}) "
            f"count={count} marker={marker}\n"
        )
        print(json.dumps({
            "continue": True,
            "message": build_warn_message(skill, count),
        }))

    except json.JSONDecodeError as e:
        append_debug_log(f"JSONDecodeError: {e}")
        print(json.dumps({"continue": True}))
    except Exception as e:
        append_debug_log(f"Unexpected error: {e}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
