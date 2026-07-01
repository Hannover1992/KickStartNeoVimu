---
type: satellite
status: active
version: 1.0.0
created: 2026-05-06
op: Self-Healing-Audit
phase: Meta
chain_position: standalone
---

# /_sanity_check — Schweizer-Uhrmacher Self-Healing Audit

**Zweck:** Zweistufiger Pipeline-Audit. Findet Drift-Patterns, Skelett-Code,
veraltete Pfade, semantische Inkonsistenzen — kategorisiert sie und repariert
selbsttaetig (Self-Healing). Geboren aus 3-Wellen-Iteration 2026-05-06 wo der
gleiche Audit drei Mal noetig war weil V1+V2 immer mehr Drift entdeckten.

---

## Aufruf

```
/_sanity_check [scope=full|orchestrator|worker] [welle=N]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `scope` | full | `full \| orchestrator \| worker` | Welche Stufe(n) |
| `welle` | auto | 1, 2, 3, ... | Welche V-Welle (auto=naechste freie) |

**Beispiele:**
```
/_sanity_check                       → V{N+1}, beide Stufen
/_sanity_check scope=orchestrator    → nur Stufe 1 (Pipeline-Walk)
/_sanity_check scope=worker          → nur Stufe 2 (Worker-Walk)
/_sanity_check welle=4               → forciert V4
```

---

## VERTRAG

```
+======================================================================+
| COMMAND: /_sanity_check                                              |
+======================================================================+
|                                                                      |
| ACTOR: SCHWEIZER-UHRMEISTER (Team Lead direkt)                       |
|                                                                      |
| LIEST:                                                               |
|   .claude/commands/*.md                  (alle Commands + Berater)   |
|   .claude/scripts/*.py                   (Pfad-Resolver, Hooks)      |
|   .claude/config/vault-routing.json      (Routing-Konfiguration)     |
|   .claude/config/layers.yaml             (Layer-Definitionen)        |
|   {META}/architekturKonventionen/  (Vault-Schema, Invarianten) |
|   .claude/output/Audit_SanityCheck_*.md  (Vorgaenger-Wellen)         |
|                                                                      |
| SCHREIBT:                                                            |
|   .claude/output/Audit_SanityCheck_V{N}_{DATE}.md  (NEUE Datei!)    |
|     -> NICHT vorherige V-Datei aendern (Audit-Trail-Erhalt)         |
|   {VAULT}/Backlog/{slug}/6_PL/{bl_id}-parking-lot.md  (PL-Items)    |
|   {VAULT}/Backlog/BL-{NNN}-{slug}.md          (NEUE Backlog-Items)  |
|   .claude/commands/*.md                       (Easy-Fixes inline)   |
|                                                                      |
| FINDINGS-KATEGORIEN (Self-Healing-Aktionen):                         |
|   🟢 EASY-FIX    : <20 LOC, mechanisch, reversibel → INLINE-Fix    |
|   🟡 PL-ITEM     : kontextspezifisch              → parking-lot.md  |
|   🔴 BL-ITEM     : systematisch, mehrere Files    → /_backlog erzeugen|
|   🔵 NOTE        : Verstaendnis-Hinweis           → nur Audit-Datei |
|                                                                      |
| INVARIANTEN:                                                         |
|   INV-SC-1: Vorherige V-Audit-Dateien werden NIE veraendert         |
|   INV-SC-2: Jeder Befund hat Kategorie + Begruendung + Action       |
|   INV-SC-3: NICHT "heilig schwoeren" - jede Behauptung ist Grep-    |
|             verifiziert (Lesson aus V1: "Verifizierung > Schwur")   |
|   INV-SC-4: Drift-Pattern in MEHREREN Greps suchen (Lesson V2:      |
|             {VAULT} ≠ {DCS_VAULT} ≠ /home/uczen/...)               |
|   INV-SC-5: Mass-Replace nur bei semantischer Eindeutigkeit         |
|             (Lesson V3: sed war zu schnell, Architektur-Frage      |
|             {VAULT} vs {WORKING_DIR} blieb offen)                   |
|   INV-SC-6: Ehrlich was unklar ist — keine "95%-Compliance"-Zahlen  |
|             ohne Verifikation                                        |
+======================================================================+
```

---

## METHODIK: 2 Stufen, je mit Sliding Window N-1/N/N+1

### Stufe 1: Orchestrator-Ebene (Pipeline-Walk)

**Sicht:** Team Lead. Was sieht er? Was liest er? Was schreibt er?
Welche Handschuhe wechselt er wann? Welche Pipeline-Uebergaben?

**Pfad (chronologisch durch eine Story):**

```
1. /_backlog              (Intake: Voice/Text → BL-Item)
2. /_BDF_orchestrate      (Outer Loop, Dispatcher)
3. /_A_orchestrate        (Wissensbasis-Bauer, 9 Berater)
4. /_IDF_orchestrate      (Dekomposition, 14 Berater)
5. /_SDF_orchestrate      (Batch-Worker, 12+ Berater)
6. /_SC_orchestrate       (Forschungszyklus, 5 Berater)
7. /_SDF (Hub-Return)     (Handschuh-Wechsel SC → I)
8. /_I_orchestrate        (Implementation, 6 Berater)
9. /_TDD_orchestrate      (TDD-Stufen-Schleife)
10. /_SDF Post-Batch      (Phase 3: PT/SL-Promote, batchEnde)
```

**Sliding Window pro Schritt:**
- N-1: Vorgaenger (was kommt rein?)
- N:   Aktueller Orchestrator
- N+1: Nachfolger (was geht raus?)

**Pro Window pruefen:**
- Vertrag-Konsistenz (LIEST von N-1 = SCHREIBT-Output von N-1)
- Handschuh-Wechsel-Pattern (Skill() vs Agent() — INV-PM-2)
- State-Uebergabe (Manifest-Felder konsistent zwischen Pipelines)
- Pfad-Konsistenz ({VAULT} / {WORKING_DIR} / {VAULT_ROOT})
- Anti-Pattern (Worker spawnt Code, BDF spawnt Workers, etc.)

### Stufe 2: Worker-Ebene (Atomarer Single-Unit-of-Work-Walk)

**Sicht:** Einzelner kurzlebiger Worker. Was bekommt er als Prompt?
Was liest er? Was schreibt er? Wie stirbt er?

**Cluster (chronologisch durch Worker-Familien):**

```
A. A-Pipeline-Berater (9 Worker)         → /_A_berater_*.md
B. IDF-Pipeline-Berater (14 Worker)      → /_IDF_berater_*.md
C. SDF-Pipeline-Berater (12+ Worker)     → /_SDF_berater_*.md
D. SC-Pipeline-Berater (5 Worker)        → /_SC_berater_*.md + Cycle-Cmds
E. I-Pipeline-Berater (6 Worker)         → /_I_berater_*.md + Sub-Cmds
F. TDD-Atomic-Steps (8 Worker, 8a-8i)    → /_TDD_*.md
G. PT/SL-Promote (3 Worker)              → /_PT_promoteFromPL etc.
```

**Sliding Window pro Cluster:**
- N-1: Vorgaenger-Berater
- N:   Aktueller Berater
- N+1: Nachfolger-Berater

**Pro Worker pruefen (Single-Unit-of-Work-Property):**
- Stateless: keine Member-Variablen, kein Cache zwischen Aufrufen
- Schreib-Isolation: nur eigener BERATER_OUTPUTS-Slot
- W7-Konformitaet: spawnt KEINE Sub-Agents
- Vault-Pfad-Konsistenz: liest/schreibt aus den richtigen Vault-Pfaden
- Frontmatter-Vertrag stimmt mit Pseudocode ueberein
- Vault-Driven-Development: per-Story-Daten (`{WORKING_DIR}/`) vs.
  global-cross-Story (`{VAULT}/`) richtig unterschieden

---

## DRIFT-PATTERNS (Pflicht-Greps)

Aus Lessons V1-V3: **Eine Drift kommt in vielen Varianten.**
Bei jeder Welle ALLE folgenden Greps durchfuehren:

### Vault-Pfad-Drift (Mehrere Varianten!)
```bash
grep -rn "{VAULT}/OmniCommand/Backlog/"     .claude/commands/   # V1-Hauptpattern
grep -rn "{DCS_VAULT}/OmniCommand/Backlog/" .claude/commands/   # V2-Variante
grep -rn "/home/uczen/Documents/"           .claude/commands/   # V3-Variante (Linux)
grep -rn "C:/Users/.*Documents/OmniCommand" .claude/commands/   # Windows hardcoded
grep -rn "0_BL/{bl_id}-frontmatter"         .claude/commands/   # Phantom-Folder
```

### Skelett-/TODO-Drift
```bash
grep -rn "## Logik (TBD)"                 .claude/commands/
grep -rn "Status v0\.[01]\.0:.* Skelett"  .claude/commands/
grep -rn "^Geplant:"                       .claude/commands/
grep -rn "Logik kommt"                     .claude/commands/
grep -rln "version: 0\.0\.[0-9]" .claude/commands/_*berater*.md
```

### Semantik-Mismatch (BL-151)
```bash
# Berater die per-Story-State lesen aber globalen Manifest haben
for f in .claude/commands/_*berater*.md; do
  if grep -q "{VAULT}/_manifest.md" "$f" && \
     grep -qE "(A|IDF|SDF|SC|I)_PIPELINE_STATE|DF_BATCH_STATE" "$f"; then
    echo "MISMATCH: $f"
  fi
done
```

### vault-routing.json Konsistenz
```bash
# Folder-Schema mit numerischen Prefixes (BL-151 Convention)?
grep '"ordner":' .claude/config/vault-routing.json | grep -v '_'
# Wenn Treffer: subfolder_structure inkonsistent zur Vault-Realitaet
```

### Orchestrator-Resume-Registrierungs-Drift (BL-362)
Statischer Lint der Orchestrator-Skill-DEFINITIONEN (Resume-Registrierungs-Vollstaendigkeit) —
faengt die 7.7-Klasse: eine Phase mit Resume-Einstiegspunkt (`resume_phase IN [...,"X"]`), die NICHT
in der `resolve_resume_phase`-Whitelist + Resume-Tabelle registriert ist -> stiller
Resume-from-scratch-Bug (~2 Wochen unentdeckt bei Phase 7.7 TEST_SEARCH). Mechanismus-bewusst
(whitelist / state_dispatch / factory_state / idempotent_berater); Logik im getesteten Script,
nicht hier inline.
```bash
py -3 .claude/scripts/orchestrator_phase_registration.py .claude/commands/_*orchestrate.md
```
Interpretation:
- `[DRIFT]` (exit 1) = HARTE Registrierungs-Luecke (7.7-Gap oder broken-whitelist: Guards ohne
  resolve_resume_phase) -> EASY-FIX/BL-ITEM: Phase in ALLEN Registrierungs-Flaechen nachtragen.
- `[WARN]` (exit 0) = unklassifiziertes Resume (schwaches Signal, generischer --resume-Marker) ->
  NOTE / Auditor-Urteil: Checker-Vokabular erweitern ODER Resume des Orchestrators unterspezifiziert.
- `[OK]` / `[CLASSIFIED]` / `[N/A]` = sauber, keine Aktion.
Heimat = HIER (statischer Engine-Definitions-Audit), NICHT `/_health` (INV-HEALTH-SANITY-SEP:
Health = State-Format-Drift, ein Health-Member darf KEINEN Prozess-/Definitions-Audit kapseln).

---

## ABLAUF (10 Schritte)

```
SCHRITT 0: Welle ermitteln + Audit-Datei vorbereiten
  N = max([V-Nummer in .claude/output/Audit_SanityCheck_V*]) + 1
  audit_path = .claude/output/Audit_SanityCheck_V{N}_{DATE}.md
  Schreibe Header: Vorgaenger, Predecessor-Lessons, Methodik

SCHRITT 1: Vorgaenger-Welle lesen
  IF V > 1:
    Lies V{N-1} Audit-Datei
    Extrahiere "Was hat V{N-1} uebersehen?"-Sektion
    Lese die Lessons-Learned als Pflicht-Pattern fuer V{N}

SCHRITT 2: Drift-Pattern-Greps (alle Varianten!)
  Fuehre ALLE Greps aus DRIFT-PATTERNS-Sektion durch
  + den Orchestrator-Resume-Registrierungs-Checker (BL-362) ausfuehren
    (py -3 .claude/scripts/orchestrator_phase_registration.py .claude/commands/_*orchestrate.md);
    [DRIFT]=harte Luecke (fixen), [WARN]=schwaches Signal (NOTE/Urteil).
  Erwartung: V{N+1} entdeckt IMMER neue Patterns die V{N} uebersehen hat
  Fuer jeden Treffer: Datei + Zeile + Kontext

SCHRITT 3: Stufe 1 - Orchestrator-Walk (sliding window)
  FOR pos = 1..10 (Backlog → SDF Post-Batch):
    lade(N-1, N, N+1)
    pruefe Vertrag-Konsistenz
    pruefe Handschuh-Wechsel
    pruefe Pfad-Variablen
    notiere Befunde mit Kategorie

SCHRITT 4: Stufe 2 - Worker-Walk (sliding window)
  FOR cluster = A..G:
    FOR pos = 1..|cluster|:
      lade(N-1, N, N+1) — Worker
      pruefe Stateless-Property
      pruefe Schreib-Isolation
      pruefe W7-Konformitaet
      pruefe Vault-Pfad-Semantik (per-Story vs global)
      pruefe Frontmatter-Vertrag vs Pseudocode

SCHRITT 5: Findings kategorisieren
  Pro Befund:
    🟢 EASY-FIX  → wenn <20 LOC + mechanisch + reversibel
    🟡 PL-ITEM   → wenn kontextspezifisch, Reflektion noetig
    🔴 BL-ITEM   → wenn systematisch, betrifft >2 Files
    🔵 NOTE      → wenn nur Verstaendnis-Hinweis

SCHRITT 6: Self-Healing Aktionen ausfuehren
  Easy-Fixes:
    Edit-Tool inline. NICHT batchen — pro Fix einzeln verifizieren.
    Re-Grep nach jedem Fix: hat sich Drift wirklich reduziert?

  PL-Items:
    Append in {VAULT}/Backlog/{slug}/6_PL/{bl_id}-parking-lot.md
    Format: "- [ ] OBSERVATION: {text} (Quelle: SanityCheck V{N}, {Datum})"

  BL-Items:
    Skill(_backlog, args="{titel} --mode=create")
    Reifegrad: meist SC-REIF (mechanisch + Tests-noetig)

SCHRITT 7: Verifikation (Pflicht!)
  Re-Grep ALLER Drift-Patterns: 0 Matches?
  Wenn nicht 0: Fehler dokumentieren, NICHT als gefixt markieren
  INV-SC-3: Verifizierung > Schwur

SCHRITT 8: Lessons Learned dokumentieren
  Was hat V{N} gefunden was V{N-1} uebersehen hat?
  Welche neuen Drift-Patterns sind aufgetaucht?
  Welche Pattern-Variante existiert die in DRIFT-PATTERNS fehlt?
  → DRIFT-PATTERNS-Sektion DIESES Files erweitern (falls noetig)

SCHRITT 9: Audit-V{N} abschliessen
  Bilanz-Tabelle: V{N-1} vs V{N}
  Verbleibende offene Items
  Empfehlung fuer V{N+1} (was noch zu pruefen waere)

SCHRITT 10: Status-Bericht (kompakt)
  Bilanz-Tabelle an User
  Hinweis auf Audit-Datei
  Ehrliche Selbst-Einschaetzung: was wurde NICHT geprueft?
```

---

## SELF-HEALING-PRINZIPIEN

**Ehrlich statt heroisch:**
- "Verifiziert" nur wenn Grep es bestaetigt
- "Compliance ~X%" nur mit konkreter Metrik
- "Komplett gefixt" nur wenn ALLE Pattern-Varianten 0 Matches geben
- Wenn unsicher: explizit als 🔵 NOTE markieren

**Iterativ statt einmal:**
- V1 hat IMMER blinde Flecken (Erfahrung 2026-05-06)
- V2 findet Varianten die V1 uebersehen hat
- V3 findet noch tiefere Drift-Klassen
- Stop-Kriterium: 2 aufeinanderfolgende Wellen finden NICHTS Neues

**Mechanisch + manuell kombinieren:**
- Greps fuer Pattern-Suche (mechanisch, breit)
- Manueller Walk fuer Semantik-Pruefung (Schweizer Uhrmacher)
- sed nur bei semantischer Eindeutigkeit (Lesson V3: Hammer war zu grob)

**Audit-Trail bewahren:**
- V1-Audit NIE ueberschreiben
- V{N+1} ist NEUE Datei mit Verweis auf V{N}
- Lessons-Learned-Section bewahrt das gelernte Wissen

---

## INTEGRATION

**Aufrufer (idiomatisch):**
- Manuell durch User: `/_sanity_check`
- Vor PR: in Pre-PR-Pipeline einklinken (TBD)
- Nach groesseren Refactorings: empfohlen
- Wenn Skepsis: User sagt "fang nochmal an" → V{N+1}

**Verwandte Commands:**
- `/_help` — System-Uebersicht (Vault-Driven-Development)
- `/_assay` — Reflektiver Mini-Essay (komplementaer)
- `/_R_orchestrate` — Code-Review Pipeline (Uncle Bob, fuer einzelne Code-Stellen)
- `/_branch_health` — Branch-Hygiene Guard
- `/_DiffReduce` — Diff-Reduktion (Daseinsberechtigung pro Aenderung)

---

## ANTI-PATTERN (PFLICHT vermeiden)

**❌ "Heilig schwoeren" ohne Verifikation:**
```
VERBOTEN: "Compliance ~95%, alle gefixt"
RICHTIG : "Grep X gibt 0 Matches. Grep Y gibt 1 (Doku-Beispiel, OK)."
```

**❌ Mass-Replace ohne Semantik-Pruefung:**
```
VERBOTEN: sed -i 's|/home/uczen/.../X|{VAULT}/X|g' (V3-Lesson)
RICHTIG : Pro Datei pruefen ob {VAULT} oder {WORKING_DIR} korrekt ist
```

**❌ Ein Grep-Pattern als Pruefung:**
```
VERBOTEN: grep "{VAULT}/OmniCommand/Backlog/" → "alles gefixt"
RICHTIG : ALLE Drift-Pattern-Varianten greppen (V1-Lesson)
```

**❌ "Ist nur Doku" als Ausrede:**
```
VERBOTEN: "TBD-Marker sind nur Doku, ignoriert"
RICHTIG : Pro TBD pruefen ob Laufzeit-Flag (legitim) oder Skelett-Code (Bug)
```

---

## QUICK-START

```
# Erste Welle
/_sanity_check

# → erstellt Audit_SanityCheck_V1_{DATE}.md
# → 10 Orchestrators + 60+ Berater walked
# → findet Drift-Pattern, kategorisiert, fixed Easy-Fixes
# → erstellt PL-Items + BL-Items
# → meldet ehrliche Bilanz

# Wenn User skeptisch: V2
/_sanity_check

# → liest V1, sucht was V1 uebersehen hat
# → findet IMMER neue Pattern-Varianten
# → erweitert DRIFT-PATTERNS-Liste (selbst-lernend)

# Stop-Kriterium: zwei Wellen ohne neue Funde
```

---

## CHANGELOG

### v1.0.0 (2026-05-06) — Initial
- Geboren aus 3-Wellen-Iteration der Pipeline-Audit-Session
- Lessons V1-V3 in INVARIANTEN + ANTI-PATTERN integriert
- 2-Stufen-Methodik (Orchestrator + Worker)
- Self-Healing-Aktionen (Easy-Fix / PL / BL / NOTE)
- Drift-Pattern-Liste mit Versions-Erweiterung
- Audit-Trail-Erhalt (V{N+1} ist neue Datei)

---

ARGUMENTS: $ARGUMENTS
