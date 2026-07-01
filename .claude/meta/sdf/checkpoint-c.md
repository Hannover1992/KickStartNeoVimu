# Checkpoint C: HiL nach Finish (BL-042, AK-03-01)

Position: Nach Protokoll-Rollover, VOR TeamDelete.
Zweck: User kann Beobachtungen in Parking-Lot oder Manifest-Protokoll schreiben.

```
Lies GLOBAL_HIL aus {VAULT}/_session_params.md

IF GLOBAL_HIL == "off":
  # AK-03-02: Bei HiL=off wird Checkpoint C auto-skipped
  Logge: "[HiL-SKIP] Checkpoint C auto-skipped (HiL=off)"
  # Kein AskUserQuestion — direkt weiter

ELSE:
  # AK-03-03: HiL != off → User-Interaktion mit 3 Optionen
  AskUserQuestion:
    header: "Checkpoint C: Beobachtungen nach Finish"
    question: |
      Batch {NAME} abgeschlossen. Beobachtungen?
      (1) Enter/nichts → weiter ohne Aktion
      (2) "PL: {text}" → Finding als PL-Item schreiben
      (3) Freitext → Kommentar ins Manifest-Protokoll

  IF user_antwort == "" OR user_antwort == "nichts":
    # Option 1: Nichts passiert — Default
    Logge: "[CHECKPOINT-C] Keine Beobachtungen — weiter"

  ELIF user_antwort startswith "PL:":
    # Option 2: PL-Eintrag — Finding als PL-Item schreiben
    finding_text = user_antwort[3:].strip()
    pl_eintrag = "- [ ] OBSERVATION: {finding_text} (Quelle: Checkpoint C, Batch {NAME}, {Datum})"
    Append pl_eintrag an {VAULT}/_parking-lot.md
    Logge: "[CHECKPOINT-C] PL-Item geschrieben: {finding_text}"
    # SDF bleibt im Zyklus — neues PL-Item fliesst in naechsten BDF-Batch

  ELSE:
    # Option 3: Freitext → Kommentar ins Manifest-Protokoll
    kommentar = user_antwort
    Append "  Checkpoint-C-Kommentar: {kommentar}" an _manifest_protokoll.md
    Logge: "[CHECKPOINT-C] Kommentar ins Protokoll geschrieben"
```
