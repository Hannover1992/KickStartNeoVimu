#!/usr/bin/env python3
"""
Geist-Hook G#9: I/SC → Post-SDF Phase 3 (Batch-Ende).

Contract: vor Skill(_SDF_berater_loopDecision) oder Skill(_PostBatch_orchestrate)
muessen 4 Berater-Outputs im Manifest existieren:
  - BERATER_OUTPUTS.recalibrate*    (Phase 3.1)
  - BERATER_OUTPUTS.postItem*       (Phase 3.2)
  - BERATER_OUTPUTS.statusTransition*  (Phase 3.3)
  - BERATER_OUTPUTS.modelSync*      (Phase 3.5) — bei SKIP: modelSync_skip_reason Pflicht

Ersetzt veralteten guard_post_gap_sequence.py (BL-037 alt).

enforceProcess Toggle via _session_params.md oder OMNI_ENFORCE_GEIST9_GUARD=1.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

TRIGGER_SKILLS = {"_SDF_berater_loopDecision", "_PostBatch_orchestrate"}

REQUIRED_BERATER = [
    ("recalibrate", r"BERATER_OUTPUTS[._]\w*recalibrate\w*"),
    ("postItem",    r"BERATER_OUTPUTS[._]\w*postItem\w*"),
    ("statusTransition", r"BERATER_OUTPUTS[._]\w*statusTransition\w*"),
    ("modelSync",   r"BERATER_OUTPUTS[._]\w*modelSync\w*"),
]


def resolve_vault_root():
    try:
        import subprocess
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run([sys.executable, str(resolver)], capture_output=True, text=True, timeout=5, cwd=str(ROOT_DIR))
            if proc.returncode == 0 and proc.stdout.strip():
                return Path(proc.stdout.strip())
    except Exception:
        pass
    return ROOT_DIR


def read_enforce_process():
    if os.environ.get("OMNI_ENFORCE_GEIST9_GUARD") == "1":
        return True
    sp = resolve_vault_root() / "_session_params.md"
    try:
        if sp.exists():
            content = sp.read_text(encoding="utf-8")
            m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
            if m:
                return m.group(1) == "true"
    except Exception:
        pass
    return False


def _dual_read(manifest_text, manifest_path):
    """BL-229 AK-F (2026-06-10): widen die LESE-Quelle auf den ausgelagerten Inhalt.

    Nach dem State-vs-Report-Split (BL-229) liegen fruehere-Round-Berater-Outputs
    in _manifest_history_*.md (AK-C) bzw. 6_PL/BERATER_OUTPUTS/*.md (AK-B Pointer).
    Ohne Dual-Read wuerden die 4 Phase-3-Pflicht-Outputs faelschlich als missing
    gelten -> Guard blockt (False-Negative, Stall). INV-POINTER-1: inhaltlich
    identisch egal inline/pointer/offloaded; Inline-Lesung bleibt 1:1 erhalten.
    """
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from _dual_read_manifest import dual_read_text
        return dual_read_text(manifest_text, manifest_path=manifest_path)
    except Exception:
        return manifest_text


def read_manifest():
    test_path = os.environ.get("OMNI_GEIST9_MANIFEST")
    if test_path and Path(test_path).exists():
        p = Path(test_path)
        return _dual_read(p.read_text(encoding="utf-8"), p)
    # Per-BL-folder-aware Resolution (BL-RCA-Round17): bl_manifest_path zuerst,
    # dann factory/legacy/vault-Fallback. Fixt flat-vault-Annahme.
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from _manifest_resolver import read_active_manifest
        content, _path = read_active_manifest(SCRIPT_DIR, ROOT_DIR, vault_root=resolve_vault_root())
        if content:
            return _dual_read(content, _path)
    except Exception:
        pass
    # Harter Fallback (alte Logik)
    vault = resolve_vault_root()
    for name in ["_factory_manifest.md", "_manifest.md"]:
        p = vault / name
        if p.exists():
            try:
                return _dual_read(p.read_text(encoding="utf-8", errors="replace"), p)
            except Exception:
                pass
    return ""


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **GEIST9_POST_SDF_CONTRACT** [{action}]: {msg}\n")
    except Exception:
        pass


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
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") != "Skill":
        print(json.dumps({"continue": True}))
        return

    tool_input = event.get("tool_input", {}) or {}
    skill_name = tool_input.get("skill", "")
    if skill_name not in TRIGGER_SKILLS:
        print(json.dumps({"continue": True}))
        return

    manifest = read_manifest()
    if not manifest:
        print(json.dumps({"continue": True}))
        return

    missing = []
    for label, pattern in REQUIRED_BERATER:
        if not re.search(pattern, manifest, re.IGNORECASE):
            missing.append(label)

    # Special: modelSync SKIP ohne reason
    has_modelsync_skip = re.search(r"phase_3_5_modelSync\s*:\s*SKIP|modelSync\s*:\s*SKIP", manifest)
    has_skip_reason = re.search(r"modelSync_skip_reason\s*:|skip_reason\s*:", manifest)
    if has_modelsync_skip and not has_skip_reason and "modelSync" in missing:
        missing.append("modelSync_skip_reason")
    elif has_modelsync_skip and has_skip_reason and "modelSync" in missing:
        # SKIP mit reason: legitimer Skip — entferne modelSync aus missing
        missing.remove("modelSync")

    if not missing:
        print(json.dumps({"continue": True}))
        return

    enforce = read_enforce_process()
    msg = f"[GUARD-VIOLATION] GEIST9_POST_SDF_CONTRACT: Skill({skill_name}) requires BERATER_OUTPUTS: missing {missing}"
    append_guard_log(msg, enforce)
    print(json.dumps({
        "continue": not enforce,
        "message": msg + (" BLOCKED (enforceProcess=true)." if enforce else " WARNED.")
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_geist9 ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
