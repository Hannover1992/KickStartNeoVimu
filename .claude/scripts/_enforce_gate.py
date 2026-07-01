#!/usr/bin/env python3
"""_enforce_gate.py — GLOBALER Owner-Kill-Switch fuer ALLE Guards (BL-210, 2026-05-28).

KERN: `enforceProcess` in `_session_params.md` koppelt ALLE Hooks. Steht dort
`false`, liefert `enforce_active()` False — und jeder Guard, der den Gate ganz
oben in main() aufruft, early-outed zu `{"continue": True}`. EIN Schalter (via
/_param), der das gesamte Enforcement-Immunsystem deaktiviert.

Warum noetig (BL-210 Audit): mehrere Guards lasen `enforceProcess` GAR NICHT
(geist7b/10/11/7c/9b default-true; param_writer/hook_prep bewusst entkoppelt) —
ein Owner der `enforceProcess=false` setzte, wurde trotzdem geblockt. Das
verletzt die Owner-Souveraenitaet ("Prozess darf nie unnoetig stallen").

Default: True (fail-safe — fehlt der Param, bleibt Enforcement an).
Notbremse: OMNI_ENFORCE_ALL_OFF=1 (env) erzwingt global off.
Test-Override: OMNI_SESSION_PARAMS=<pfad> zeigt auf eine spezifische Datei.

BOOTSTRAP-HINWEIS (revidiert B4, Audit 2026-05-29): Die zwei SOUVERAENITAETS-Guards
(param_writer_identity, hook_prep_owner_only) haengen BEWUSST NICHT mehr an diesem
file-basierten Gate — sonst koennte ein Sub-Agent via _session_params.md-Write
(enforceProcess:false) seinen EIGENEN Waechter abschalten (agent-erreichbarer
Self-Unlock = Generalschluessel). Sie honorieren NUR die agent-UNERREICHBARE
OMNI_ENFORCE_ALL_OFF-Env-Notbremse + ihre eigenen Env-Hatches (OMNI_PARAM_WRITER_OFF/
OMNI_HOOK_PREP_OFF). Alle uebrigen (Routing-)Guards koppeln an enforceProcess via
diesen Gate. enforceProcess selbst ist jetzt ein geschuetztes Param-Feld
(guard_param_writer_identity SESSION_PARAM_PATTERN) — nur /_param darf es schreiben.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

_BL_CTX_TTL = 5.0  # Sekunden — Cross-Prozess-Cache (temp-file) fuer den BL-Kontext.


def _vault_root():
    try:
        r = SCRIPT_DIR / "resolve_vault_root.py"
        if r.is_file():
            p = subprocess.run([sys.executable, str(r)], capture_output=True,
                               text=True, timeout=5, cwd=str(ROOT_DIR))
            if p.returncode == 0 and p.stdout.strip():
                return Path(p.stdout.strip())
    except Exception:
        pass
    return ROOT_DIR / ".claude" / "analysis"


def _bl_session_params_path():
    """BL-234 AK-1: Pfad zu {bl_folder}/_session_params.md fuer den aktuellen Kontext.

    Cross-Prozess-gecached (temp-file, key=CWD, TTL=5s) — jeder PreToolUse-Guard ist
    ein EIGENER Prozess, ein Modul-Cache greift nicht. Vermeidet einen current_context-
    Subprozess bei JEDEM geguardeten Tool-Call (486-Perf: current_context spawnt intern
    resolve_vault_root + resolve_bl_path).

    Overrides: OMNI_BL_SESSION_PARAMS=<pfad> (Test/cheap) ODER "-" (explizit kein
    BL-Kontext). Rueckgabe None => kein BL-Kontext => additiver 486-safe Fallback auf
    den Umbrella-Vault.
    """
    override = os.environ.get("OMNI_BL_SESSION_PARAMS")
    if override:
        return None if override == "-" else Path(override)
    # Unter pytest ohne expliziten Override: kein BL-Kontext (haelt Bestands-Gate-Tests stabil).
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return None

    cwd = os.getcwd()
    cache_key = hashlib.sha1(cwd.encode("utf-8", "replace")).hexdigest()[:16]
    cache_file = Path(tempfile.gettempdir()) / f"omni_blctx_{cache_key}.json"
    try:
        if cache_file.is_file() and (time.time() - cache_file.stat().st_mtime) < _BL_CTX_TTL:
            bf = json.loads(cache_file.read_text(encoding="utf-8")).get("bl_folder")
            return (Path(bf) / "_session_params.md") if bf else None
    except Exception:
        pass

    bl_folder = None
    try:
        cc = SCRIPT_DIR / "current_context.py"
        if cc.is_file():
            p = subprocess.run([sys.executable, str(cc), "--format=json"],
                               capture_output=True, text=True, timeout=5, cwd=str(ROOT_DIR))
            if p.returncode == 0 and p.stdout.strip():
                bl_folder = json.loads(p.stdout.strip()).get("bl_folder")
    except Exception:
        bl_folder = None
    try:
        cache_file.write_text(json.dumps({"bl_folder": bl_folder, "cwd": cwd}), encoding="utf-8")
    except Exception:
        pass
    return (Path(bl_folder) / "_session_params.md") if bl_folder else None


def enforce_active(default=True):
    """True wenn Enforcement aktiv ist. False => Guard soll durchlassen."""
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        return False
    # Test-Affordance: unter pytest NICHT kurzschliessen, damit Guard-Tests ihre
    # Block-Logik pruefen koennen (sonst maskiert enforceProcess=false im Repo alle
    # Block-Erwartungen). Explizite Gate-Tests setzen OMNI_SESSION_PARAMS ODER
    # OMNI_BL_SESSION_PARAMS und umgehen diese Ausnahme.
    if (os.environ.get("PYTEST_CURRENT_TEST")
            and not os.environ.get("OMNI_SESSION_PARAMS")
            and not os.environ.get("OMNI_BL_SESSION_PARAMS")):
        return True
    candidates = []
    # BL-234 AK-1: per-BL Override ganz oben (additiv; kein BL-File => unveraendert = 486-safe).
    # Die 2 Souveraenitaets-Guards (param_writer/hook_prep) nutzen diesen Gate NICHT
    # (Bootstrap-Hinweis oben) -> kein agent-erreichbarer Self-Unlock ueber die BL-Schicht.
    bl_sp = _bl_session_params_path()
    if bl_sp is not None:
        candidates.append(bl_sp)
    sp_override = os.environ.get("OMNI_SESSION_PARAMS")
    if sp_override:
        candidates.append(Path(sp_override))
    candidates.append(_vault_root() / "_session_params.md")
    candidates.append(ROOT_DIR / ".claude" / "analysis" / "_session_params.md")
    for sp in candidates:
        try:
            if sp.is_file():
                content = sp.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
                if m:
                    return m.group(1).strip().lower() == "true"
        except Exception:
            continue
    return default


if __name__ == "__main__":
    print(f"enforce_active() = {enforce_active()}")
