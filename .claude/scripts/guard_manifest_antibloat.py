#!/usr/bin/env python3
"""guard_manifest_antibloat.py — BL-229 AK-D: Anti-Bloat-Enforcement (Root-Cause-Fix).

Die ROOT CAUSE des Manifest-Bloats (703 KB / 13k Zeilen bei 486): jeder Berater/jede Round
HAENGT einen NEUEN round-suffixed State-Block an (`## DF_BATCH_STATE (Round 17 ...)`,
`## BERATER_OUTPUTS_plBewertung_round15`) statt den EINEN bare-canonical Block (`## DF_BATCH_STATE`)
zu UEBERSCHREIBEN. Lineares Wachstum ∝ (Berater × Runden).

Die `## MANIFEST_BLOAT_PREVENTION (Konvention 2026-05-13)` scheiterte, weil sie nur PROSA war.
Konvention ohne Guard = wirkungslos. Dieser Guard erzwingt INV-POINTER-2: KEINE neuen
round-suffixed State-Bloecke im Manifest — 1 bare-canonical pro State-Familie (overwrite) ODER
Pointer. Round-Historie gehoert in die Report-Datei (AK-C), NICHT ins Manifest.

WICHTIG (Live-Driver 2026-05-31): der Exact-Match-Reader (`^## X$`) ist KORREKT (bare-canonical =
live, suffixed = audit-ignore, Methode A). Der Bug ist die FEHLENDE Enforcement — die dieser Guard
liefert. Reader NICHT auf newest-wins umstellen.

Pure Kern (`check_antibloat`) ist test-bar ohne IO. Hook-Wrapper (`main`) ist PreToolUse Edit/Write
auf `_manifest.md`. Registrierung in settings.json = bewusster Forward-Schritt (Quiescenz +
stab9-Kompat-Review), NICHT mid-konkurrierender-Arbeit scharfschalten.
"""
import json
import os
import re
import sys
from pathlib import Path

FAMILY_KEYWORDS = ("BERATER_OUTPUTS", "PIPELINE_STATE", "BATCH_STATE",
                   "PHASE_3_STATE", "FINAL_SUMMARY", "POST_SDF")
_ROUND_PAREN = re.compile(r"\(\s*Round\s*\d", re.IGNORECASE)
_ROUND_SUFFIX = re.compile(r"_round\d", re.IGNORECASE)


def _is_suffixed_state_header(header: str) -> bool:
    """True wenn der `## ...`-Header ein round-suffixed State-Familien-Block ist."""
    if not any(k in header for k in FAMILY_KEYWORDS):
        return False
    return bool(_ROUND_PAREN.search(header) or _ROUND_SUFFIX.search(header))


def count_suffixed_state_blocks(content: str) -> int:
    """Anzahl round-suffixed State-Familien-Bloecke (`## X (Round N)` / `## X_roundN`)."""
    n = 0
    for line in content.splitlines():
        if line.startswith("## ") and _is_suffixed_state_header(line):
            n += 1
    return n


def check_antibloat(old_content: str, new_content: str):
    """Reine Entscheidung: -> (allow: bool, reason: str).

    BLOCK wenn der Write die Anzahl round-suffixed State-Bloecke ERHOEHT (= Append statt
    bare-canonical-Overwrite). Reine Overwrites / bare-canonical-Writes / Loeschungen sind erlaubt.
    """
    old_n = count_suffixed_state_blocks(old_content or "")
    new_n = count_suffixed_state_blocks(new_content or "")
    if new_n > old_n:
        return False, (
            f"[ANTI-BLOAT BL-229 AK-D] Write fuegt {new_n - old_n} round-suffixed State-Block(s) "
            f"an (jetzt {new_n}, vorher {old_n}) statt den bare-canonical Block zu ueberschreiben "
            f"(INV-POINTER-2). Schreibe `## {{FAMILY}}` (ohne (Round N)/_roundN) = overwrite; "
            f"Round-Historie gehoert in die Report-Datei (AK-C), nicht ins Manifest."
        )
    return True, ""


def main():
    # Default disarmed: nur aktiv wenn explizit eingeschaltet (Forward-Enforcement-Gate).
    if os.environ.get("OMNI_MANIFEST_ANTIBLOAT", "off") == "off":
        print(json.dumps({"continue": True}))
        return
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except Exception:
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    path = ti.get("file_path", "") or ti.get("path", "")
    if "_manifest.md" not in str(path):
        print(json.dumps({"continue": True}))
        return

    try:
        old = Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).exists() else ""
    except Exception:
        old = ""
    # Write -> content; Edit -> new_string (Teil-Edit, additiv pruefbar via Vorher+Ersetzung)
    if "content" in ti:
        new = ti.get("content", "")
    else:
        new = old.replace(ti.get("old_string", "\0nope\0"), ti.get("new_string", "")) \
            if ti.get("old_string") else old + ti.get("new_string", "")

    allow, reason = check_antibloat(old, new)
    if allow:
        print(json.dumps({"continue": True}))
    else:
        print(json.dumps({"continue": False, "message": reason}))


if __name__ == "__main__":
    main()
