#!/usr/bin/env python3
"""
guard_geist2_bdf_to_a.py — Geist G#2: BDF -> A (UNREIF-Triage)

PreToolUse-Hook auf Skill-Tool. Triggert wenn Skill(_A_orchestrate) geladen
wird. Prueft ob der adressierte BL den Status "UNREIF" (oder leer/DRAFT) hat
— die A-Pipeline ist die Triage-Stufe und darf NICHT auf reife BLs laufen.

Contract (Master-Analyse 2026-05-27, G#2):
  - BDF darf Skill(_A_orchestrate) NUR fuer UNREIF-BLs starten
  - Reife BLs (READY, SC-REIF, REIF, DONE) gehoeren zu IDF/SDF/Pre_PR

Reifegrad-Quellen (Reihenfolge):
  1. Vault-Knoten Frontmatter: {vault_root}/Backlog/BL-{NNN}-*.md (reifegrad: ...)
  2. _factory_manifest.md BL_LIFECYCLE_STATE.current_bl.reifegrad
  3. _manifest.md (legacy) BL_LIFECYCLE_STATE.current_bl.reifegrad

Mode:
  enforceProcess=true   -> BLOCK (continue=false) bei reifem BL
  enforceProcess=false  -> WARN (continue=true) — Default
  OMNI_ENFORCE_GEIST2_GUARD=1 -> erzwingt enforce=true (fuer pytest)

Konservativ:
  - BL-ID nicht extrahierbar -> continue=true (passthrough)
  - Vault-Knoten nicht gefunden -> continue=true (kein Reifegrad ableitbar)
  - Reifegrad unbekannt/leer -> continue=true (UNREIF-aequivalent, A erlaubt)
  - Skill != _A_orchestrate -> continue=true (passthrough)

Style-Reference: guard_modus_writer.py, guard_a_routing_target.py.
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

EXPECTED_SKILL = "_A_orchestrate"

# Reife-Status die A-Pipeline VERBIETEN (BL ist bereits durch A gelaufen)
REIFE_STATUSES_BLOCKED = {"READY", "SC-REIF", "REIF", "DONE"}

# Status die als UNREIF zaehlen (A-Pipeline erlaubt)
UNREIF_STATUSES_ALLOWED = {"", "UNREIF", "DRAFT", "INITIAL", "PROPOSED"}

# Test-Override ENV-Var
ENV_ENFORCE = "OMNI_ENFORCE_GEIST2_GUARD"
# Test-Override fuer Vault-Root (damit Tests einen Temp-Vault verwenden koennen)
ENV_VAULT_OVERRIDE = "OMNI_GEIST2_VAULT_ROOT"

# BL-ID Extraction aus args: "BL-XXX ..." oder "BL-XXX-slug ..."
BL_ID_PATTERN = re.compile(r"\bBL-(\d{1,4})(?:-[A-Za-z0-9_-]+)?\b")

# Reifegrad-Pattern (YAML-Frontmatter oder Manifest)
REIFEGRAD_PATTERN = re.compile(
    r"(?:^|\n)\s*reifegrad\s*:\s*[\"']?([A-Z][A-Z_-]*)[\"']?",
    re.IGNORECASE,
)


def _resolve_vault_root():
    """Resolves Vault-Root via resolve_vault_root.py (oder ENV-Override fuer Tests)."""
    override = os.environ.get(ENV_VAULT_OVERRIDE)
    if override:
        return Path(override)
    try:
        import subprocess
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
                    return Path(vault_root_str)
    except Exception:
        pass
    return None


def _resolve_session_params(vault_root):
    """Sucht _session_params.md im Vault-Root, sonst Fallback."""
    if vault_root is not None:
        candidate = vault_root / "_session_params.md"
        if candidate.exists():
            return candidate
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


def read_enforce_process(vault_root):
    """Liest enforceProcess aus _session_params.md.
    Test-Override: OMNI_ENFORCE_GEIST2_GUARD=1 erzwingt enforce=true.
    Default: False (WARN) wenn Datei fehlt oder unlesbar.
    """
    if os.environ.get(ENV_ENFORCE) == "1":
        return True
    try:
        params_file = _resolve_session_params(vault_root)
        if not params_file.exists():
            return False
        content = params_file.read_text(encoding="utf-8")
        m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
        if m:
            return m.group(1).strip().lower() == "true"
    except Exception:
        pass
    return False


def append_guard_log(violation_type, details, blocked):
    """Appendet Log-Eintrag in _guard_log.md (analog guard_modus_writer.py)."""
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def append_debug_log(msg):
    """Schreibt in .hook_debug.log bei unerwarteten Exceptions."""
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] guard_geist2_bdf_to_a: {msg}\n")
    except Exception:
        pass


def extract_bl_id(args):
    """Extrahiert BL-{NNN} aus Skill-args. Returns 'BL-NNN' oder None."""
    if not args or not isinstance(args, str):
        return None
    m = BL_ID_PATTERN.search(args)
    if not m:
        return None
    bl_num = m.group(1).zfill(3)
    return f"BL-{bl_num}"


def find_bl_vault_node(vault_root, bl_id):
    """Sucht Vault-Knoten {vault_root}/Backlog/BL-{NNN}-*.md.
    Returns Path oder None.
    """
    if vault_root is None or not bl_id:
        return None
    backlog_dir = vault_root / "Backlog"
    if not backlog_dir.is_dir():
        return None
    try:
        # Match BL-NNN-*.md (Top-Level-File, nicht Subfolder)
        matches = list(backlog_dir.glob(f"{bl_id}-*.md"))
        if matches:
            # Bevorzuge die kuerzeste (Top-Level statt evtl. Sub-Files)
            matches.sort(key=lambda p: len(str(p)))
            return matches[0]
    except Exception:
        pass
    return None


def read_reifegrad_from_node(node_path):
    """Liest reifegrad aus YAML-Frontmatter eines BL-Knotens.
    Returns Reifegrad-String (uppercase) oder None.
    """
    if not node_path or not node_path.is_file():
        return None
    try:
        # Nur Top-Bereich lesen (Frontmatter ist meist <50 Zeilen)
        with open(node_path, encoding="utf-8") as f:
            head = f.read(8192)
        m = REIFEGRAD_PATTERN.search(head)
        if m:
            return m.group(1).upper()
    except Exception:
        pass
    return None


def read_reifegrad_from_manifest(vault_root, bl_id):
    """Fallback: Liest reifegrad aus _factory_manifest.md/_manifest.md.
    Sucht current_bl-Block fuer das BL-ID. Returns String oder None.
    """
    if vault_root is None:
        return None
    candidates = [
        vault_root / "_factory_manifest.md",
        vault_root / "_manifest.md",
    ]
    for manifest in candidates:
        if not manifest.is_file():
            continue
        try:
            content = manifest.read_text(encoding="utf-8")
        except Exception:
            continue
        # Suche reifegrad-Eintrag innerhalb eines current_bl-Blocks mit BL-ID
        # einfacher Heuristik-Check: zeilenweise nahe der BL-ID nach reifegrad
        for match in re.finditer(rf"{re.escape(bl_id)}\b", content):
            # Lese ein Fenster von +/- 500 Zeichen um den Match
            start = max(0, match.start() - 500)
            end = min(len(content), match.end() + 500)
            window = content[start:end]
            r = REIFEGRAD_PATTERN.search(window)
            if r:
                return r.group(1).upper()
    return None


def classify_reifegrad(reifegrad):
    """Klassifiziert Reifegrad in UNREIF (A erlaubt), REIF (A blockiert), UNKNOWN.
    Returns 'UNREIF' | 'REIF' | 'UNKNOWN'.
    """
    if reifegrad is None:
        return "UNKNOWN"
    norm = reifegrad.upper().strip()
    if norm in UNREIF_STATUSES_ALLOWED:
        return "UNREIF"
    if norm in REIFE_STATUSES_BLOCKED:
        return "REIF"
    # Unbekannter Status -> konservativ als UNKNOWN (passthrough)
    return "UNKNOWN"


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
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({"continue": True}))
            return
        hook_data = json.loads(raw)

        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        # Nur Skill-Tool ist relevant
        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        if not isinstance(tool_input, dict):
            print(json.dumps({"continue": True}))
            return

        skill = tool_input.get("skill", "")
        # Skill-Name normalisieren (manchmal "plugin:skill", manchmal nur "_X")
        skill_norm = skill.split(":")[-1] if ":" in skill else skill

        if skill_norm != EXPECTED_SKILL:
            # Nicht dieser Geist
            print(json.dumps({"continue": True}))
            return

        args = tool_input.get("args", "")
        bl_id = extract_bl_id(args)

        if not bl_id:
            # Keine BL-ID extrahierbar -> konservativ passthrough
            # (Master-Analyse: konservatives Default statt aggressive Block)
            print(json.dumps({"continue": True}))
            return

        vault_root = _resolve_vault_root()
        node_path = find_bl_vault_node(vault_root, bl_id)
        reifegrad = read_reifegrad_from_node(node_path)

        if reifegrad is None:
            # Fallback: Manifest
            reifegrad = read_reifegrad_from_manifest(vault_root, bl_id)

        classification = classify_reifegrad(reifegrad)

        if classification in ("UNREIF", "UNKNOWN"):
            # A-Pipeline erlaubt
            print(json.dumps({"continue": True}))
            return

        # classification == "REIF" -> BLOCK oder WARN
        enforce = read_enforce_process(vault_root)
        details = (
            f"Skill(_A_orchestrate) fuer {bl_id} mit reifegrad={reifegrad} "
            f"(klassifiziert als REIF). A-Pipeline ist Triage-Stufe und nicht "
            f"fuer reife BLs vorgesehen — gehoert zu IDF/SDF/Pre_PR."
        )
        message = (
            f"[GUARD-VIOLATION] GEIST2_BDF_TO_A: {details} "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )

        append_guard_log("GEIST2_BDF_TO_A", details, enforce)

        if enforce:
            sys.stderr.write(
                f"[guard_geist2_bdf_to_a BLOCK] {bl_id} reifegrad={reifegrad}\n"
                f"  Fix: A-Pipeline ist fuer UNREIF-BLs. Route diesen BL via BDF "
                f"zu IDF (READY/SC-REIF/PLANNED) oder Pre_PR (DONE).\n"
            )
            print(json.dumps({"continue": False, "message": message}))
        else:
            sys.stderr.write(
                f"[guard_geist2_bdf_to_a WARN] {bl_id} reifegrad={reifegrad}\n"
                f"  enforceProcess=false, A-Pipeline laeuft trotzdem.\n"
            )
            print(json.dumps({"continue": True, "message": message}))

    except json.JSONDecodeError as e:
        append_debug_log(f"JSONDecodeError: {e}")
        print(json.dumps({"continue": True}))
    except Exception as e:
        append_debug_log(f"Unexpected error: {e}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
