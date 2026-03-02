# /_I_fanIn

**Status:** v1.0
**Actor:** MOTHERSHIP-OPERATOR
**Zweck:** Worktree-Ergebnisse einsammeln, Merge begleiten, Status verwalten

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_fanIn {SLICE_NAME}                               |
+===============================================================+
|                                                                |
|  LIEST:                                                        |
|    1. Worktree .claude/ (User gibt Pfad an):                  |
|       - synthese/{NAME}-ATOMIC-{SLICE}.md                     |
|       - synthese/{NAME}-INTEGRATION-{SLICE}.md                |
|       - synthese/{NAME}-SYSTEM-{SLICE}.md                     |
|       - synthese/{NAME}-VERIFY-{SLICE}.md (falls vorhanden)   |
|       - plans/{NAME}-{SLICE}-PLAN.md                          |
|       - _parking-lot.md (Eintraege aus Worktree)              |
|       - patterns/_pattern-library.md (neue Patterns)          |
|    2. Mothership .claude/:                                     |
|       - _manifest.md → FanOut-Status, bisherige Merges        |
|       - ARCHITECT.md → Abhaengigkeitsgraph                    |
|       - _parking-lot.md (bestehende Eintraege)                |
|       - patterns/_pattern-library.md (bestehende Patterns)    |
|                                                                |
|  PHASE 1 - ARTEFAKT-SYNC (.claude/ Worktree → Mothership):    |
|    Kopiert:                                                    |
|      - Synthese-Dateien: 1:1 (ATOMIC, INTEGRATION, SYSTEM,   |
|        VERIFY falls vorhanden)                                 |
|      - PLAN.md: 1:1                                           |
|      - Parking-Lot: APPEND (neue Eintraege anfuegen)          |
|      - Pattern Library: MERGE (neue Patterns hinzufuegen)     |
|    Kopiert NICHT:                                              |
|      - Manifest (wird in Phase 5 neu gebaut)                  |
|      - CURRENT_SLICE.md (Worktree-spezifisch)                |
|      - commands/, agents/ (identisch zum Mothership)          |
|                                                                |
|  PHASE 2 - GIT MERGE (User macht selbst):                     |
|    AUSGABE: "Bitte jetzt git merge durchfuehren:"             |
|    AUSGABE: "  git merge feature/DCSRE-881_{SLICE}"           |
|    AUSGABE: "Konflikte? Melde Anzahl und betroffene Dateien." |
|    → Wartet auf User-Bericht                                  |
|    → Protokolliert Konflikte + Aufloesung                     |
|                                                                |
|  PHASE 3 - BUILD-VALIDIERUNG:                                  |
|    AUSGABE: "Bitte ausfuehren:"                               |
|    AUSGABE: "  dotnet clean && dotnet build"                   |
|    → Wartet auf User-Bericht (0 Errors? Warnings?)            |
|                                                                |
|  PHASE 4 - TEST-VALIDIERUNG (gestuft):                         |
|    Stufe 1: Unit Tests des gemergten Slices                   |
|      AUSGABE: "Bitte Slice-spezifische Unit Tests starten"    |
|      → Wartet auf Ergebnis                                    |
|    Stufe 2: Integration Tests des gemergten Slices            |
|      AUSGABE: "Bitte Slice-spezifische ITs starten"           |
|      → Wartet auf Ergebnis                                    |
|    Stufe 3: NUR wenn Stufe 1+2 gruen:                         |
|      AUSGABE: "Bitte ALLE Integration Tests starten"          |
|      AUSGABE: "(Ressourcen-intensiv, du kuemmerst dich)"      |
|      → Wartet auf Ergebnis                                    |
|                                                                |
|  PHASE 5 - STATUS-UPDATE:                                      |
|    SCHREIBT in Mothership .claude/:                            |
|      _manifest.md:                                            |
|        - Slice als GEMERGED markieren                         |
|        - Test-Ergebnisse protokollieren                       |
|        - Merge-Konflikte protokollieren                       |
|      ARCHITECT.md:                                             |
|        - Dependency-Graph: Slice als DONE                     |
|        - Blockierte Slices pruefen                            |
|                                                                |
|  PHASE 6 - NAECHSTE SCHRITTE:                                  |
|    PRUEFT:                                                     |
|      - Hat dieser Merge Slices entblockt?                     |
|      - Sind ALLE Slices gemerged? → Feature KOMPLETT          |
|    AUSGABE:                                                    |
|      A) "{SLICE_X} ist jetzt entblockt → /_I_fanOut Welle 2" |
|      B) "Alle Slices gemerged → Feature KOMPLETT"             |
|      C) "Noch {N} Worktrees aktiv, warte auf Abschluss"      |
|                                                                |
|  PIPELINE:                                                     |
|    [Worktree DONE] → [/_I_fanIn] → [/_I_fanOut Welle 2]      |
|                        oder → [Feature KOMPLETT]               |
|                                                                |
|  WICHTIG: FanIn fuehrt KEIN Git aus!                           |
|  User merged selbst. FanIn BERÄT + VALIDIERT + AKTUALISIERT.  |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**MOTHERSHIP-OPERATOR:** Sammelt Worktree-Ergebnisse ein, begleitet Merge, verwaltet Status.

**TUT:** .claude/ Artefakte kopieren, Merge begleiten (Anweisungen geben), Build+Tests
validieren lassen, Manifest updaten, entblockte Slices identifizieren.

**NICHT:** Git-Befehle ausfuehren, Code schreiben, Tests starten (User macht das).

**Eskalation:** Bei Merge-Konflikten die nicht aufloesbar sind → /_SC_observe

---

## Schritt 0: Slice identifizieren

```
Falls {SLICE_NAME} angegeben:
  → Diesen Slice verarbeiten
Falls NICHT angegeben:
  → Lies Manifest → Welche Worktrees sind als AKTIV markiert?
  → AUSGABE: "Welcher Slice ist fertig?"
  → Frage User nach Slice-Name und Worktree-Pfad
```

---

## Schritt 1: Artefakt-Sync (Phase 1)

```
1. User gibt Worktree-Pfad an
2. Lies Worktree .claude/:
   - Pruefe: Existiert SYSTEM-{SLICE}.md mit status=final?
     → Falls ja: Slice ist komplett (alle 3 Test-Ebenen durch)
     → Falls nein: Pruefe INTEGRATION/ATOMIC Status
     → Warnung falls Slice nicht vollstaendig abgeschlossen
3. Kopiere Artefakte nach Mothership:

   | Quelle (Worktree) | Ziel (Mothership) | Strategie |
   |--------------------|-------------------|-----------|
   | synthese/{NAME}-ATOMIC-{SLICE}.md | synthese/ | 1:1 kopieren |
   | synthese/{NAME}-INTEGRATION-{SLICE}.md | synthese/ | 1:1 kopieren |
   | synthese/{NAME}-SYSTEM-{SLICE}.md | synthese/ | 1:1 kopieren |
   | synthese/{NAME}-VERIFY-{SLICE}.md | synthese/ | 1:1 (falls vorhanden) |
   | plans/{NAME}-{SLICE}-PLAN.md | plans/ | 1:1 kopieren |
   | _parking-lot.md | _parking-lot.md | APPEND neue Eintraege |
   | _pattern-library.md | _pattern-library.md | MERGE neue Patterns |

4. AUSGABE: "{N} Artefakte von Worktree nach Mothership kopiert"
```

---

## Schritt 2: Git Merge begleiten (Phase 2)

```
AUSGABE:
  "Artefakte synchronisiert. Bitte jetzt den Git-Merge durchfuehren:"
  ""
  "  cd {MOTHERSHIP_PFAD}"
  "  git merge feature/DCSRE-881_{SLICE_NAME}"
  ""
  "Melde mir:"
  "  - Anzahl Konflikte"
  "  - Betroffene Dateien"
  "  - Wie aufgeloest"

→ Wartet auf User-Bericht
→ Protokolliert in Merge-Log
```

---

## Schritt 3: Build + Tests (Phase 3+4)

### Gestufte Validierung:

```
STUFE 1: Build
  AUSGABE: "Bitte: dotnet clean && dotnet build"
  → Erwartet: 0 Errors
  → Falls Errors: Zusammen debuggen

STUFE 2: Unit Tests (Slice-spezifisch)
  AUSGABE: "Bitte Unit Tests fuer {SLICE} starten"
  → Erwartet: Alle gruen
  → Falls rot: Regression identifizieren

STUFE 3: Integration Tests (Slice-spezifisch)
  AUSGABE: "Bitte Integration Tests fuer {SLICE} starten"
  AUSGABE: "Nur die Tests die zum Slice gehoeren"
  → Erwartet: Alle gruen

STUFE 4: ALLE Integration Tests (nur wenn Stufe 1-3 gruen)
  AUSGABE: "Slice-Tests gruen. Bitte ALLE Integration Tests starten."
  AUSGABE: "(Ressourcen-intensiv - du kuemmerst dich darum)"
  → Wartet auf Ergebnis
  → Bei gruen: Weiter zu Phase 5
  → Bei rot: Regression zwischen Slices! Zusammen analysieren.
```

---

## Schritt 4: Status-Update (Phase 5)

### Manifest aktualisieren

```markdown
## Slice-Status nach FanIn

| Slice | Status | Merge-Datum | Konflikte | Tests |
|-------|--------|-------------|-----------|-------|
| S1S2_DBSchema | GEMERGED | 2026-02-06 | 3 (aufgeloest) | 848 PASS |
| S4_S3Key | GEMERGED | 2026-02-05 | 0 | 812 PASS |
| S6_Locking | GEMERGED | 2026-02-06 | (mit S1S2) | (mit S1S2) |
| S5_Retry | OFFEN | - | - | - |
```

### Abhaengigkeiten pruefen

```
Lies ARCHITECT.md → Dependency-Graph
Fuer jeden OFFENEN Slice:
  - Sind alle Blocker jetzt GEMERGED?
  → Falls ja: Slice ist ENTBLOCKT
  → AUSGABE: "{SLICE} ist jetzt frei! Naechste Welle moeglich."
```

---

## Schritt 5: Naechste Schritte (Phase 6)

```
Falls entblockte Slices:
  AUSGABE: "Entblockt: {SLICE_LIST}"
  AUSGABE: "Fuer neue Welle: /_I_mitose + /_I_fanOut"
  AUSGABE: "Oder direkt im Mothership: /_I_cleanCodeSlice {SLICE}"

Falls ALLE Slices GEMERGED:
  AUSGABE: "ALLE Slices gemerged. Feature CODE-KOMPLETT."
  AUSGABE: "Gesamt: {N} Unit Tests, {N} ITs, {N} STs - alle gruen"
  AUSGABE: "Naechster Schritt: /_I_verify global (SPEC ↔ Test Mapping)"
  AUSGABE: "Danach: /_gap Re-Eval → /_model finish → Pre-PR"

Falls noch aktive Worktrees:
  AUSGABE: "Noch {N} Worktrees aktiv: {LISTE}"
  AUSGABE: "Warte auf Abschluss, dann erneut /_I_fanIn"
```

---

## Qualitaetskriterien

- Artefakte vollstaendig kopiert (keine verlorenen Synthese-Dateien)
- Parking-Lot: APPEND, nicht ueberschreiben
- Pattern Library: MERGE, nicht ueberschreiben
- Manifest korrekt aktualisiert (Slice-Status, Test-Ergebnisse)
- Dependency-Graph geprueft (entblockte Slices erkannt)
- User hat klare Anweisungen was als naechstes zu tun ist
- Kein Git ausgefuehrt (User macht alles selbst)
- Gestufte Test-Validierung (nicht alles auf einmal)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_fanIn abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
