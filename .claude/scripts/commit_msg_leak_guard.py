#!/usr/bin/env python3
"""
commit_msg_leak_guard.py — git commit-msg-Hook gegen internen Prozess-Info-Leak (BL-295 AK-2).

Defense-in-depth: der `_stage_orchestrate` Phase-2.3 Security-Gate laeuft NUR im Skill-Pfad.
Dieser git commit-msg-Hook faengt den Leak auch bei MANUELLEN Commits (= BL-295-Symptom:
486-Commits mit `(PR-Review Duc PR2-DUC-X)` raw gepusht).

git commit-msg-Konvention: argv[1] = Pfad zur Commit-Message-Datei. Wir lesen sie (utf-8),
delegieren an die KANONISCHE Pattern-Quelle `leak_patterns.scan_message()` (AK-3, geteilt mit
dem Phase-2.3-Gate — kein Drift) und rejecten bei Treffer HART.

Security-Gate (anders als Prozess-Guards): HARD reject (sys.exit(1)) bei Leak — KEIN
enforce=false-WARN-Bypass. Begruendung: ein Leak ist nach dem Push irreversibel.

Kill-Switch (Owner-Override): OMNI_COMMIT_MSG_GUARD_OFF=1 -> exit 0 sofort.

Robustheit: Bei einem FEHLER DER EIGENEN GUARD-LOGIK (z.B. Datei nicht lesbar, unerwarteter
Scan-Fehler) blockieren wir den User-Commit NICHT (defensiv exit 0 + Warn auf stderr). Ein
Guard-Bug darf legitime Commits nicht verhindern. Bei einem ECHTEN Leak-Treffer dagegen:
exit 1. So scheitert der Guard "offen" nur bei eigenem Defekt, nicht beim Schutzfall.
"""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()

# Import-robust: leak_patterns liegt im selben Verzeichnis (kann als Hook von ueberall
# aufgerufen werden -> SCRIPT_DIR explizit auf sys.path).
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def main(argv):
    # Kill-Switch zuerst — Owner-Override vor jeder Logik.
    if os.environ.get("OMNI_COMMIT_MSG_GUARD_OFF") == "1":
        return 0

    if len(argv) < 2:
        # Ohne Message-File-Pfad nichts zu pruefen -> Commit nicht blockieren.
        sys.stderr.write(
            "[COMMIT-MSG-LEAK] WARN: kein Message-File-Pfad (argv[1]) — uebersprungen.\n"
        )
        return 0

    msg_path = Path(argv[1])

    try:
        from leak_patterns import scan_message
    except Exception as e:  # Import-Defekt = eigener Guard-Bug -> nicht blockieren.
        sys.stderr.write(
            f"[COMMIT-MSG-LEAK] WARN: leak_patterns nicht importierbar ({e}) — "
            f"Commit nicht blockiert (Guard-Bug, kein Schutzfall).\n"
        )
        return 0

    try:
        text = msg_path.read_text(encoding="utf-8")
    except Exception as e:  # Datei nicht lesbar = eigener Guard-Bug -> nicht blockieren.
        sys.stderr.write(
            f"[COMMIT-MSG-LEAK] WARN: Message-File nicht lesbar ({e}) — "
            f"Commit nicht blockiert (Guard-Bug, kein Schutzfall).\n"
        )
        return 0

    try:
        treffer = scan_message(text)
    except Exception as e:  # Scan-Fehler = eigener Guard-Bug -> nicht blockieren.
        sys.stderr.write(
            f"[COMMIT-MSG-LEAK] WARN: scan_message-Fehler ({e}) — "
            f"Commit nicht blockiert (Guard-Bug, kein Schutzfall).\n"
        )
        return 0

    if not treffer:
        return 0  # sauber -> accept

    # ECHTER Leak -> HARD reject.
    ids = ", ".join(sorted({t.pattern_id for t in treffer}))
    matches = ", ".join(t.match for t in treffer)
    sys.stderr.write(
        f"[COMMIT-MSG-LEAK] Interne Prozess-Info in Commit-Message: "
        f"{ids} (Treffer: {matches}).\n"
        f"  -> FIX: nur fachlichen Inhalt behalten "
        f"(FALSCH: '... (PR-Review Gr.2)'  RICHTIG: '...').\n"
        f"  Owner-Override (nur bewusst): OMNI_COMMIT_MSG_GUARD_OFF=1.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
