#!/usr/bin/env python3
"""
guard_vault_write_lock.py — Vault-Write-Seam-Durchsetzung (BL-334 sub_batch_2, AK-2).

HookGuard-Mirror #5 (Spiegel von guard_idf_sdf_handoff.py). PreToolUse-Hook auf
JEDEM Edit/Write. Durchsetzungs-Schicht ueber dem vault_lock-Primitiv (SB1):
ist ein FREMDES non-stale vault-Heal-Lock aktiv und das Ziel liegt UNTER
{vault_root}, wird der Write abgelehnt (INV-VAULT-LOCK-5) — die fremde Session
wird gestallt bis der Heiler released.

HOECHSTE VORSICHT — fail-open ist HEILIG: dieser Hook laeuft auf JEDEM Edit/Write.
Ein Bug darf NIEMALS den Vault zumauern. try/except umschliesst die GESAMTE Logik,
default exit 0 (continue:true). KEIN modus/batch_modes/Manifest. Self-Defeating-
Schutz wie alle Mirror-Guards.

Entscheidungs-Matrix (Spec 2.2 / INV-VAULT-LOCK-5):
  1. Kill-Switch (OMNI_ENFORCE_ALL_OFF=1 | OMNI_VAULT_WRITE_LOCK_OFF=1)  -> PASS
  2. tool_name nicht in {Edit, Write}                                    -> PASS
  3. file_path NICHT unter {vault_root}-Praefix (Engine-Repo, OQ-4)      -> PASS
  4. kein/stale vault-Lock (vault_lock.is_locked()==None, INV-LOCK-2)    -> PASS
  5. Lock-holder == eigene worker-id (OQ-7, self-Heiler darf schreiben)  -> PASS
  6. fremdes non-stale Lock:
       enforce=true  -> BLOCK (exit 2) + Recovery-Hint (holder + zweck)
       enforce=false -> WARN  (exit 0, continue:true) + Hint im message
  7. JEDE Exception (vault_lock-Import, JSON-Parse, vault_root-Fehler)   -> fail-open PASS

vault_root-Aufloesung: VAULT_ROOT-env (factory_lock-Default
C:/Users/Administrator/Documents/OmniCommand), abs + case-insensitive (Windows).
self-Identitaet: OMNI_WORKER_ID (Fallback OMNI_SESSION_ID).
enforce: OMNI_SESSION_PARAMS (Default true; enforceProcess:false -> WARN) — Spiegel
von guard_idf_sdf_handoff.read_enforce. Kill-Switch/Local-Off: OMNI_ENFORCE_ALL_OFF /
OMNI_VAULT_WRITE_LOCK_OFF.

Template/Blaupause: guard_idf_sdf_handoff.py. DIP-Analogon: der Guard kennt NUR
_vault.lock-State (via vault_lock-Primitiv) + eigene worker-id, NICHT die Heil-interne
Logik (BL-335).
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

# factory_lock-Default-Vault (gespiegelt) — falls VAULT_ROOT-env fehlt.
DEFAULT_VAULT_ROOT = "C:/Users/Administrator/Documents/OmniCommand"


def read_enforce():
    """enforceProcess aus OMNI_SESSION_PARAMS (Test) oder Default true. BLOCK ist
    Default am Write-Seam (Spiegel guard_idf_sdf_handoff); enforceProcess:false -> WARN."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    if sp and Path(sp).exists():
        try:
            txt = Path(sp).read_text(encoding="utf-8", errors="replace")
            if re.search(r"enforceProcess\s*:?\*?\*?\s*false", txt, re.IGNORECASE):
                return False
        except Exception:
            pass
    return True


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **VAULT_WRITE_LOCK** [{action}]: {msg}\n")
    except Exception:
        pass


def _norm(p):
    """Absolut + case-insensitive (Windows) normalisiert, fuer Praefix-Match."""
    return os.path.normcase(os.path.abspath(str(p)))


def _resolve_vault_root():
    """VAULT_ROOT-env oder factory_lock-Default. None wenn nicht aufloesbar."""
    root = os.environ.get("VAULT_ROOT", DEFAULT_VAULT_ROOT)
    if not root:
        return None
    return Path(root)


def _self_worker_id():
    """Eigene Identitaet aus env (OQ-7). None wenn nicht gesetzt."""
    return os.environ.get("OMNI_WORKER_ID") or os.environ.get("OMNI_SESSION_ID")


def main():
    # === 1. Kill-Switches (BL-210 global Owner-Kill + lokal) -> PASS ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    if os.environ.get("OMNI_VAULT_WRITE_LOCK_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    # === stdin-Event lesen (fail-open bei kaputtem Input) ===
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    # === 2. Nur Edit/Write am Write-Seam ===
    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    fp = ti.get("file_path", "")
    if not fp:
        # kein Ziel-Pfad -> nichts zu pruefen -> fail-open PASS
        print(json.dumps({"continue": True}))
        return

    # === 3. vault_root-Aufloesung + Praefix-Match (OQ-4) ===
    vault_root = _resolve_vault_root()
    if vault_root is None:
        # vault_root nicht ermittelbar -> fail-open PASS
        print(json.dumps({"continue": True}))
        return

    target_norm = _norm(fp)
    vault_norm = _norm(vault_root)
    # Praefix-Match: Ziel liegt unter vault_root? (mit Separator-Grenze gegen
    # Praefix-Kollisionen wie .../OmniCommandX vs .../OmniCommand).
    if not (target_norm == vault_norm or target_norm.startswith(vault_norm + os.sep)):
        # Engine-Repo / Nicht-Vault-Pfad -> PASS (kein Vault-Write)
        print(json.dumps({"continue": True}))
        return

    # === 4. vault-Lock-State lesen (via SB1-Primitiv) ===
    try:
        import vault_lock  # lokaler Import: Fehler -> fail-open im Top-except
        lock = vault_lock.is_locked(vault_root=vault_root)
    except Exception:
        # vault_lock-Import/Read-Fehler -> fail-open PASS
        print(json.dumps({"continue": True}))
        return

    if not lock:
        # kein/stale Heal-Lock (INV-LOCK-2) -> PASS
        print(json.dumps({"continue": True}))
        return

    # === 5. self-Holder? (OQ-7) -> PASS (der Heiler selbst darf schreiben) ===
    holder = lock.get("holder", "")
    self_id = _self_worker_id()
    if self_id and holder == self_id:
        print(json.dumps({"continue": True}))
        return

    # === 6. fremdes non-stale vault-Lock -> BLOCK (enforce) / WARN ===
    enforce = read_enforce()
    zweck = lock.get("purpose", "") or "?"
    ts = lock.get("acquired_at", "?")
    msg = (
        f"[GUARD-VIOLATION] VAULT_WRITE_LOCK: {Path(fp).name} liegt im Vault, "
        f"aber ein fremdes Heal-Lock ist aktiv (holder={holder}, zweck={zweck}, "
        f"acquired={ts}). -> Vault wird gerade geheilt; warte bis release oder "
        f"retry nach Lock-Frei. "
        + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (enforceProcess=false Opt-out).")
    )
    append_guard_log(
        f"Vault-Write {Path(fp).name} bei fremdem Lock (holder={holder}, zweck={zweck})",
        enforce,
    )
    print(json.dumps({"continue": not enforce, "message": msg}))
    if enforce:
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # fail-open ist HEILIG: jeder unerwartete Fehler -> PASS, niemals zumauern.
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_vault_write_lock ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
