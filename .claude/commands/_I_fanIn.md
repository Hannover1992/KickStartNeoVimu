---
type: building-block
---

# /_I_fanIn

**Status:** v2.0 (Z2: 5-Phasen + 3-Kategorien selektive Tests + Modul-Register + Sub-Blueprint Aggregation)
**Actor:** MOTHERSHIP-OPERATOR
**Zweck:** Worktree-Ergebnisse einsammeln, Sub-Blueprints aggregieren, Merge begleiten, Status verwalten

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_fanIn {SLICE_NAME}                               |
+===============================================================+
|                                                                |
|  LIEST:                                                        |
|    1. Worktree (User gibt Pfad an) — PRIMAER: Vault/Worktree: |
|       PRIMAER: {VAULT}/.../Implementation/{NAME}-ATOMIC-{SLICE}.md |
|         FALLBACK: .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md |
|       PRIMAER: {VAULT}/.../Implementation/{NAME}-INTEGRATION-{SLICE}.md |
|         FALLBACK: .claude/analysis/synthese/{NAME}-INTEGRATION-{SLICE}.md |
|       PRIMAER: {VAULT}/.../Implementation/{NAME}-SYSTEM-{SLICE}.md |
|         FALLBACK: .claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md |
|       PRIMAER: {VAULT}/.../Implementation/{NAME}-VERIFY-{SLICE}.md (falls vorhanden) |
|         FALLBACK: .claude/analysis/synthese/{NAME}-VERIFY-{SLICE}.md |
|       - plans/{NAME}-{SLICE}-PLAN.md                          |
|       - _parking-lot.md (Eintraege aus Worktree)              |
|       - patterns/_pattern-library.md (neue Patterns)          |
|       - analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md     |
|         → Sub-Blueprint aus Worktree (falls vorhanden)        |
|    2. Mothership .claude/:                                     |
|       - _manifest.md → FanOut-Status, bisherige Merges        |
|       PRIMAER: {VAULT}/.../Blueprint/{NAME}-ARCHITECT.md      |
|         FALLBACK: .claude/analysis/synthese/{NAME}-ARCHITECT.md |
|         → Abhaengigkeitsgraph                                  |
|       - _parking-lot.md (bestehende Eintraege)                |
|       - patterns/_pattern-library.md (bestehende Patterns)    |
|                                                                |
|  PHASE 1 - ARTEFAKT-SYNC (Vault/Worktree → Mothership):       |
|    Kopiert:                                                    |
|      - Synthese-Dateien: 1:1 (ATOMIC, INTEGRATION, SYSTEM,   |
|        VERIFY falls vorhanden)                                 |
|      - PLAN.md: 1:1                                           |
|      - Parking-Lot: APPEND (neue Eintraege anfuegen)          |
|      - Pattern Library: MERGE (neue Patterns hinzufuegen)     |
|    Kopiert (zusaetzlich, Sub-Blueprint-Aggregation):           |
|      - analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md     |
|        → Status auf approved setzen nach QG PASS              |
|        → Zurueck ins Mothership kopieren                      |
|        → Graceful Degradation: Falls kein Sub-Blueprint → SKIP|
|    Liest (zusaetzlich, Modul-Register):                        |
|      - {WORKTREE}/.claude/analysis/blueprints/{FEATURE}/S2/module-register.md |
|        → Rolle (shared/primary), Konflikt-Risiko pro Modul    |
|        → Graceful Degradation: Falls kein Register → SKIP     |
|    Kopiert NICHT:                                              |
|      - Manifest (wird in Phase 4 neu gebaut)                  |
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
|  PHASE 3 - BUILD + SELEKTIVE TESTS (3-Kategorien):             |
|    3.1 Build:                                                  |
|      AUSGABE: "dotnet clean && dotnet build"                   |
|      → 0 Errors erwartet                                      |
|    3.2 Selektive Tests (3-Kategorien-Schema):                  |
|      Kategorie 1 (betroffen): Tests des gemergten Slices      |
|        → PFLICHT ausfuehren, MUESSEN gruen sein               |
|      Kategorie 2 (anzupassen): Tests mit Interface-Aenderung  |
|        → PFLICHT ausfuehren, duerfen angepasst werden         |
|      Kategorie 3 (Kanarienvogel): Regressionstests            |
|        → PFLICHT ausfuehren, DUERFEN NICHT geaendert werden   |
|        → Bei Bruch: Regression erkannt → Eskalation           |
|    3.3 VERBOTEN: Kein Gesamt-Test-Run (RF-TEST-003)            |
|      Nur selektive 3-Kategorien-Tests (betroffen/anzupassen/   |
|      Kanarienvogel). Gesamt-Run ist ressourcen-ineffizient.    |
|                                                                |
|  PHASE 4 - STATUS-UPDATE:                                      |
|    SCHREIBT in Mothership .claude/:                            |
|      _manifest.md:                                            |
|        - Slice als GEMERGED markieren                         |
|        - Test-Ergebnisse (3-Kategorien) protokollieren        |
|        - Merge-Konflikte protokollieren                       |
|      ARCHITECT.md:                                             |
|        - Dependency-Graph: Slice als DONE                     |
|        - Blockierte Slices pruefen                            |
|                                                                |
|  PHASE 5 - NAECHSTE SCHRITTE:                                  |
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

## Schritt 1b: Sub-Blueprint aggregieren (Stufen-Modus)

Falls `{WORKTREE}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md` existiert:

```
1. Lese sub-{NR}.md aus Worktree
2. Pruefe Exit-Kriterien: Sind alle in "## Exit-Kriterien" erfuellt?
3. Falls JA: Setze status: approved im Frontmatter
4. Falls NEIN: Setze status: partial (mit Begruendung in Kommentar)
5. Kopiere zurueck:
   Ziel: .claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
6. Graceful Degradation: Falls kein Sub-Blueprint → SKIP
   (FanIn funktioniert wie bisher ohne Sub-Blueprint)
```

---

## Schritt 1c: Ueberlappungs-Erkennung (VOR Git Merge, NUR Stufe 2)

Falls `stufe == 2`:

```
1. Lies blueprints/{FEATURE}/S2/module-register.md (falls vorhanden)
2. Pruefe fuer jede Datei mit Rolle=shared:
   a) Identifiziere welche bereits gemergten Slices dasselbe Modul beruehrt haben
   b) Falls nur aktueller Slice → kein Konflikt, weiter
   c) Falls mehrere Slices dieselbe Datei beruehrt haben:
      - Identische Hunks in allen Slices → harmlos (kein Merge-Konflikt erwartet)
      - Verschiedene Hunks an gleicher Stelle → semantischer Konflikt:
        AUSGABE: "UEBERLAPPUNGS-KONFLIKT: {DATEI} in Slices {S1,S2} verschieden geaendert → Manuelle Review empfohlen"
      - Falls Konflikt-Risiko=hoch (Interface-Aenderung):
        AUSGABE: "ESKALATION: {DATEI} hat Konflikt-Risiko HOCH."
        AUSGABE: "  Empfehlung: git diff {MERGED_BRANCH}..{CURRENT_BRANCH} -- {DATEI}"
3. Zusammenfassung:
   AUSGABE: "Ueberlappungs-Check: {N} shared Module, {N} Warnungen, {N} Eskalationen"
4. Graceful Degradation:
   - Kein Modul-Register vorhanden → Schritt ueberspringen
   - Stufe != 2 → Schritt ueberspringen
   - Erster Slice-Merge (kein bereits gemergter Slice) → SKIP (nichts zu vergleichen)
```

WICHTIG: Dieser Schritt fuehrt KEIN Git aus. Er analysiert das Modul-Register und gibt
dem User VORWARNUNGEN vor dem manuellen Git Merge.

---

## Schritt 1c.1: Region-Lock Retirement-Netz (merge-Hunk-Verify, AK-R4 / BL-247)

Der DETERMINISTISCHE, zeilen-praezise Unterbau von Schritt 1c. Schritt 1c (Modul-Register-
Heuristik) ist die GROBE Vorwarnung; 1c.1 ist der exakte Half-Open-Zeilen-Range-Check
(-1 = ganze Datei) = das **Retirement-Netz** hinter dem OPTIMISTISCHEN Plan-Zeit-
Region-Claim (`stage_resource_registry.acquire_region`, BL-342-Suitability plant Wellen
optimistisch; der Fan-In faengt die Fehlprognose pessimistisch). Optimistic->Pessimistic-Kette.

Falls MEHR ALS EIN Slice/Worker in DIESE Fan-In-Welle einfliesst (Parallel-Execution):

```
1. Sammle die TATSAECHLICH beruehrten Hunks je Worker je Datei aus den Slice-Diffs
   (git diff je Worktree-Branch --unified=0 -> Hunk-Header @@ -a,b +c,d @@ -> (start, start+len)):
     worker_hunks = {worker_id: {datei: [(start, end), ...]}}   # half-open, end=-1 = ganze Datei
2. Deterministischer Check (machine-not-context: Logik in srr.fan_in_hunk_verify, kurzlebiger Worker):
     conflicts = py -3 -c "import json,sys,stage_resource_registry as s; \
                 print(json.dumps(s.fan_in_hunk_verify(json.load(sys.stdin))))"  < worker_hunks.json
3. conflicts == [] -> Region-Claims haben gehalten (sauberer Merge) -> weiter zu Schritt 2.
   conflicts != [] -> ECHTE Cross-Worker-Hunk-Kollision, die der Plan-Claim VERFEHLTE:
     AUSGABE: "REGION-LOCK RETIREMENT-NETZ: {file} Hunks {worker_a}{range_a} vs {worker_b}{range_b}
               ueberlappen -> Suitability-Misprediction (BL-342). Manuelle Merge-Review PFLICHT."
     -> Eskalation (Schritt-1c-Semantik). Telemetrie-Signal fuer den Misprediction-Detektor
        (BL-358, deferred) — jede gefangene Kollision schaerft die Plan-Zeit-Vorhersage.
4. Graceful Degradation: Single-Slice (slicing=false) / erster Merge / kein Diff -> SKIP
   (kein Cross-Worker-Hunk vorhanden; identisch zur 1c-SKIP-Semantik).
```

LIVE-Validierung dieses Pfades unter einer echten Parallel-Welle = Gate-C/E (Region-Lock
execution path). Die Verify-LOGIK selbst ist deterministisch + unit-getestet
(`test_fan_in_hunk_verify.py`, BL-247 AK-R4/R5) — KEIN blinder Concurrency-Code.

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

## Schritt 3: Build + Selektive Tests (Phase 3 — 3-Kategorien-Schema)

### 3.1 Build

```
AUSGABE: "Bitte: dotnet clean && dotnet build"
→ Erwartet: 0 Errors
→ Falls Errors: Zusammen debuggen
```

### 3.2 Selektive Tests (3-Kategorien-Schema)

```
Die 3 Kategorien bestimmen WAS getestet wird und WIE mit Ergebnissen umgegangen wird:

KATEGORIE 1 — BETROFFEN (direkt betroffene Tests):
  Tests die zum gemergten Slice gehoeren.
  AUSGABE: "Bitte Slice-spezifische Unit + Integration Tests starten"
  → PFLICHT ausfuehren
  → MUESSEN alle gruen sein
  → Falls rot: Implementierungsfehler im Slice → fixen

KATEGORIE 2 — ANZUPASSEN (Interface-Aenderungen):
  Tests anderer Slices die von Interface-Aenderungen betroffen sind.
  → Falls Sub-Blueprint vorhanden: Lese "## Test-Inventar" Sektion
    → Dort stehen explizit die anzupassenden Tests
  → Falls kein Sub-Blueprint: Heuristik — Tests die gleiche Entities/Interfaces nutzen
  AUSGABE: "Bitte anzupassende Tests starten: {LISTE}"
  → DUERFEN angepasst werden (Interface-Aenderung erwartet)
  → Bei Anpassung: Dokumentiere was und warum in FANIN-{SLICE}.md

KATEGORIE 3 — KANARIENVOGEL (Regressionstests):
  Ausgewaehlte Tests die NICHT zum Slice gehoeren, aber Regressionen aufdecken.
  → Falls Sub-Blueprint vorhanden: Lese "## Test-Inventar" Sektion
    → Dort stehen explizit die Kanarienvogel-Tests
  → Falls kein Sub-Blueprint: Mindestens 5 Tests aus angrenzenden Modulen
  AUSGABE: "Bitte Kanarienvogel-Tests starten: {LISTE}"
  → DUERFEN NICHT geaendert werden (read-only!)
  → Bei Bruch: REGRESSION erkannt!
    → AUSGABE: "KANARIENVOGEL-BRUCH: {TEST_NAME} — Regression durch Merge!"
    → Eskalation an User: Merge hat unerwartete Seiteneffekte
```

### 3.3 KEIN Gesamt-Test-Run (RF-TEST-003)

```
VERBOTEN: Gesamt-Test-Run nach Fan-In.
Nur die 3 Kategorien aus 3.2 werden ausgefuehrt (betroffen + anzupassen + Kanarienvogel).
Ergebnis-Protokoll trennt die 3 Test-Sets explizit:

  Betroffen:     {N}/{M} PASS
  Anzupassen:    {N}/{M} PASS (angepasste Tests dokumentiert)
  Kanarienvogel: {N}/{M} PASS (read-only, keine Aenderungen)

→ Alle 3 Kategorien gruen: Weiter zu Phase 4
→ Kanarienvogel rot: REGRESSION → Eskalation
→ Betroffen/Anzupassen rot: Implementierungsfehler → fixen
```

---

## Schritt 4: Status-Update (Phase 4)

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

## Schritt 5: Naechste Schritte (Phase 5)

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
- 3-Kategorien selektive Tests angewendet (betroffen/anzupassen/Kanarienvogel)
- Kanarienvogel-Tests read-only — Bruch = Regression → Eskalation
- Sub-Blueprints aggregiert und Status auf approved/partial gesetzt
- Modul-Register gelesen (falls vorhanden, Graceful Degradation)
- Ueberlappungs-Check VOR Git Merge durchgefuehrt (Stufe 2, falls Register vorhanden)
- 5-Phasen-Ablauf eingehalten (nicht 6)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_fanIn abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
