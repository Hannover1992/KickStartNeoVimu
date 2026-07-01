# /_finish - Feature-Abschluss & Cleanup

```yaml
status: active
version: 1.3.0
created: 2026-02-21
updated: 2026-03-30
op: FeatureFinish
phase: Cleanup
type: satellite
chain_position: final
team_based: false
```

---

```
+======================================================================+
| COMMAND: /_finish [NAME]                                              |
+======================================================================+
|                                                                        |
| ACTOR: DU (die ausfuehrende Claude-Instanz, KEIN Team, KEIN Worker)  |
|                                                                        |
| ZWECK: Feature sauber abschliessen. Offene Items verarbeiten,         |
|        .claude/* konsistent machen, bereit fuer naechstes Feature.    |
|                                                                        |
| TYP: Einfacher Command — KEIN Orchestrator, kein Team, kein Worker.   |
|      Du fuehrst alle 4 Schritte SELBST aus.                           |
|                                                                        |
| AUFRUF:                                                                |
|   /_finish [NAME]                                                     |
|   NAME ist optional — wenn nicht angegeben, aus _manifest.md lesen.   |
|                                                                        |
| KEIN HiL fuer den Abschluss selbst — aber HiL fuer offene Items!    |
|                                                                        |
| LIEST:                                                                 |
|   {VAULT}/_manifest.md                (Phase, Coverage, SRS)          |
|   {VAULT}/_parking-lot.md             (offene [ ] Items)              |
|   {VAULT}/Task.md                     (offene ECs/TCs)                |
|   {VAULT}/.../Model/{NAME}_Model.md  (offene W{n}, BL-045)            |
|     FALLBACK: .claude/models/{NAME}_Model.md                          |
|                                                                        |
| SCHREIBT:                                                              |
|   {VAULT}/_manifest.md                (PHASE=READY)                   |
|   {VAULT}/_parking-lot.md             (Items aktualisiert)            |
|   {VAULT}/Task.md                     (ECs als erledigt/verworfen)    |
|   {VAULT}/.../Model/{NAME}_Model.md  (W{n} als erledigt/verworfen)   |
|     FALLBACK: .claude/models/{NAME}_Model.md                          |
|                                                                        |
| MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):                       |
|   Pattern A: Reiner State-Write — kein Protokoll-Eintrag              |
|   SCHREIBT STATE: PHASE=READY (Einzeiler)                             |
|   SCHREIBT NICHT: _manifest_protokoll.md                              |
|   (PUSH_STATUS Guard liest _manifest.md State — unveraendert W10)    |
+======================================================================+
```

---

## Schritt 0: PUSH_STATUS Guard

**Zweck:** Verhindert Feature-Abschluss ohne abgeschlossenen Wissens-Push (F04-Guard, W158).

```
1. Pruefe ob --skip-push-guard Flag gesetzt:
   → JA: Guard uebersprungen (bewusste Ausnahme). Logge im Manifest.
   → NEIN: Weitermachen

2. Lies {VAULT}/_manifest.md
3. Suche "PUSH_STATUS:" Zeile im Manifest

4. PUSH_STATUS == "COMPLETED"? (exakte Gleichheitspruefung, kein Substring-Match)
   Suche: Zeile die mit "PUSH_STATUS:" beginnt, gefolgt von " COMPLETED" (Prefix-Match)
   KORREKT: "PUSH_STATUS: COMPLETED" → Guard bestanden → WEITER zu Schritt 1
   FALSE POSITIVE vermeiden: "PUSH_STATUS: NOT COMPLETED" → kein Match (prueft NICHT ob "COMPLETED" irgendwo enthalten ist)
   → NEIN / nicht vorhanden:
     FEHLER: "PUSH_STATUS nicht COMPLETED."
     "        BL-050 Vault-First: Synthese-Artefakte (Model, Spec, Gap,"
     "        SC-Pipeline) werden DIREKT in Vault geschrieben."
     "        Push ist nur noch noetig fuer RAG-Ingest + lokale Artefakte."
     "        Option A: /_W_push_temp auto  (RAG-Ingest + verbleibende)"
     "        Option B: --skip-push-guard   (reine Vault-First-Features)"
     "        Danach: /_finish erneut aufrufen"
     → Zeige letzten PUSH_STATUS-Wert (falls vorhanden)
     → ABBRUCH
```

**Hintergrund (W158, aktualisiert BL-050):** Bei Vault-First-Features
liegen Synthese-Artefakte bereits im Vault. Push ist primaer fuer
RAG-Ingest und lokale Artefakte (.claude/) relevant.
Bei reinen Vault-First-Features kann `--skip-push-guard` verwendet werden.

---

## Schritt 1: Status-Check

Lies folgende Dateien und zaehle offene Items:

### 1.1 Manifest lesen

```
Lies {VAULT}/_manifest.md
Extrahiere:
  - NAME (falls nicht als Parameter gegeben)
  - PHASE
  - COVERAGE
  - SRS-SCORE
  - STAGNATION
```

### 1.2 Parking-Lot lesen

```
Lies {VAULT}/_parking-lot.md
Zaehle:
  - [ ] Items (offen)
  - [x] Items (erledigt)
  - [~] Items (verworfen)
Sammle alle [ ] Items als Liste.
```

### 1.3 Task.md lesen

```
Lies {VAULT}/Task.md (falls vorhanden)
Zaehle:
  - Offene ECs (Erfolgskriterien ohne ✅)
  - Offene TCs (Test Cases ohne ✅)
Sammle alle offenen ECs/TCs als Liste.
```

### 1.4 Model lesen

```
Lies .claude/models/{NAME}_Model.md (falls vorhanden)
Zaehle:
  - W{n} mit Status AKTIV oder ZUR_PRUEFUNG
  - W{n} mit Status BESTAETIGT (bereits erledigt)
  - W{n} mit Status WIDERLEGT (bereits verworfen)
Sammle alle AKTIV/ZUR_PRUEFUNG W{n} als Liste.
```

### 1.5 Report

```
AUSGABE:
  "═══════════════════════════════════════════════════════
   /_finish Status-Check: {NAME}
   ═══════════════════════════════════════════════════════

   Feature: {NAME}
   Phase: {PHASE}
   Coverage: {COVERAGE}
   SRS-Score: {SRS-SCORE}

   Offene Items:
     Parking-Lot:  {N} offene [ ] Items
     Task.md:      {M} offene ECs/TCs
     Model W{n}:   {K} AKTIV/ZUR_PRUEFUNG

   Gesamt: {N+M+K} offene Items
   ═══════════════════════════════════════════════════════"
```

Falls 0 offene Items → Springe zu Schritt 3.

---

## Schritt 2.0: Dark Factory Guard

**PFLASTER 2026-06-11 (BL-295 AK-5, Live-Bug DCSRE-1944):** Ob die offenen Items autonom geparkt
werden (kein AskUserQuestion) oder per HiL abgefragt werden, entscheidet AUSSCHLIESSLICH der
`hil`-Param (Session-Params via BL-174-Resolver). `GLOBAL_MODUS` ist KEIN HiL-Proxy mehr
(PL-S2-06: BDF/Modus und HiL sind ORTHOGONAL). Der alte `OR GLOBAL_MODUS IN [...]`-Disjunkt
koppelte das Auto-Park an den Modus — entfernt; `hil=off` ist die einzige Quelle (deckt
small_dark_factory UND big_dark_factory ueber den hil-Param ab).

```
hil_param = resolve(hil)   # off | cycle | phase | manual
             # BL-174: py -3 .claude/scripts/session_params_resolver.py resolve --param=hil --bl-id={BL_ID}
             # Fallback {VAULT}/_session_params.md **HiL:**

IF hil_param == "off":
  # Dark Factory Modus: Offene Items automatisch PARKEN (nicht loeschen)
  # Items bleiben als [ ] in _parking-lot.md (unveraendert)
  N = Anzahl offener [ ] Items aus Schritt 1
  Logge: "Dark Factory Guard: {N} offene Items automatisch GEPARKT (hil=off)"
  → Springe zu Schritt 3 (KEIN AskUserQuestion)
# ALT (BUG, ersetzt): IF GLOBAL_HIL == "off" OR GLOBAL_MODUS IN ["small_dark_factory", "big_dark_factory"]
# -> GLOBAL_MODUS war HiL-Proxy (Orthogonalitaets-Verletzung PL-S2-06).
```

---

## Schritt 2: Offene Items verarbeiten (HiL)

### 2.1 Batch-Entscheidung

Falls <= 5 offene Items: Frage EINZELN (ein AskUserQuestion pro Item).
Falls > 5 offene Items: Frage GRUPPIERT (AskUserQuestion mit multiSelect).

### 2.2 Einzeln fragen (<=5 Items)

Pro offenem Item:

```
AskUserQuestion:
  header: "Offenes Item"
  question: "Offenes Item: {ITEM_BESCHREIBUNG}

    Quelle: {parking-lot | Task.md EC | Model W{n}}

    Was soll damit passieren?"

  options:
    - label: "PARKEN"
      description: "In _parking-lot.md belassen/eintragen fuer spaeter"
    - label: "DISCARD"
      description: "Verwerfen — als [~] markieren mit Grund"
    - label: "ERLEDIGT"
      description: "Als [x] markieren (bereits umgesetzt)"
  multiSelect: false
```

### 2.3 Gruppiert fragen (>5 Items)

```
AskUserQuestion:
  header: "Offene Items"
  question: "Es gibt {N} offene Items. Welche sollen GEPARKT werden?
    (Nicht ausgewaehlte werden als DISCARD markiert)

    Items:
    {NUMMERIERTE_LISTE}"

  options:
    - label: "Alle PARKEN"
      description: "Alle offenen Items fuer spaeter parken"
    - label: "Alle DISCARD"
      description: "Alle offenen Items verwerfen"
    - label: "Einzeln entscheiden"
      description: "Jedes Item einzeln durchgehen"
  multiSelect: false
```

Bei "Einzeln entscheiden" → Wechsle zu 2.2 (einzeln fragen).

### 2.4 Entscheidungen umsetzen

Pro Item basierend auf User-Entscheidung:

**PARKEN:**
- Falls aus parking-lot: [ ] belassen
- Falls aus Task.md: Neuen Eintrag in _parking-lot.md:
  `- [ ] [aus Task.md EC] {BESCHREIBUNG}`
- Falls aus Model: Neuen Eintrag in _parking-lot.md:
  `- [ ] [aus Model W{n}] {BESCHREIBUNG}`

**DISCARD:**
- Falls aus parking-lot: `[ ]` → `[~]` mit Grund "Feature-Ende, verworfen"
- Falls aus Task.md: EC als "VERWORFEN" markieren
- Falls aus Model: W{n} Status auf ELIMINIERT setzen

**ERLEDIGT:**
- Falls aus parking-lot: `[ ]` → `[x]`
- Falls aus Task.md: EC als ✅ markieren
- Falls aus Model: W{n} Status auf BESTAETIGT setzen

---

## Schritt 3: .claude/* Konsistenz-Check

### 3.1 Models pruefen (BL-045 Vault-First)

```
# PRIMAER: Vault-Pfade scannen (BL-045)
Vault-Root via vault-routing.json (5-stufig)
BL_SLUG = aus _backlog_index.md oder Manifest

Fuer jede Datei in {VAULT}/Backlog/{BL_SLUG}/Model/*.md:
  - Hat sync-Block? (Obsidian Sync Metadaten)
  - Ist finalisiert? (status: final im Frontmatter)
  - Hat Vault-Frontmatter? (type, feature, bl-item, tags)

# FALLBACK (Legacy): .claude/models/*.md
Fuer jede Datei in .claude/models/*.md:
  - Hat sync-Block? (Obsidian Sync Metadaten)
  - Ist finalisiert? (status: final im Frontmatter)
```

### 3.2 Synthese pruefen (BL-045 Vault-First)

```
# PRIMAER: Vault-Pfade scannen (BL-045)
Fuer jeden Typ in [Spec, Gap, K-Score]:
  Fuer jede Datei in {VAULT}/Backlog/{BL_SLUG}/{Typ}/*.md:
    - Hat Frontmatter? (YAML-Block am Anfang)
    - Ist Status gesetzt? (final/partial/draft)
    - Hat Vault-Frontmatter? (type, feature, bl-item, tags)

# FALLBACK (Legacy): .claude/analysis/synthese/
Fuer jede Datei in .claude/analysis/synthese/{NAME}-*.md:
  - Hat Frontmatter? (YAML-Block am Anfang)
  - Ist Status gesetzt? (final/partial/draft)
```

### 3.3 Manifest-Phase pruefen

```
Passt PHASE zum aktuellen Stand?
  - Alle Items verarbeitet → PHASE sollte DONE oder READY sein
  - Post-Cycle durchlaufen → PHASE sollte nicht mehr "SC-CYCLE" sein
```

### 3.4 Stale Teams pruefen

```
Pruefe ob aktive Teams existieren:
  ls ~/.claude/teams/
Gibt es Teams die zu {NAME} gehoeren und noch aktiv sind?
  - sc-{name}/*
  - wp-{name}/*
  - i-pipeline-{name}/*
Falls ja: Melde als Inkonsistenz.
```

### 3.5 Report

```
AUSGABE:
  "{M} Inkonsistenzen gefunden:"
  - {LISTE_DER_INKONSISTENZEN}

  ODER:
  "Alles sauber — keine Inkonsistenzen."
```

Falls Inkonsistenzen: Team Lead behebt sie automatisch (Frontmatter ergaenzen,
Phase korrigieren). Bei stale Teams: Melde dem User.

### 3.6 Backup-Verzeichnisse bereinigen (Cleanup-Hook, CaseStudy MV-2d)

.backup_{DATE}/ Verzeichnisse sind obsolet sobald git die Aenderungen hat:

```
BACKUP_DIRS = Glob(".claude/commands/.backup_*/")

IF COUNT(BACKUP_DIRS) == 0:
  → SKIP (keine Backup-Verzeichnisse vorhanden)

IF COUNT(BACKUP_DIRS) > 10:
  → HiL: "{COUNT} Backup-Verzeichnisse gefunden. Loeschen? (j/n)"

Fuer jedes DIR in BACKUP_DIRS:
  DATEIEN = Glob(DIR + "/*")
  Loesche DIR rekursiv
  Log: "Geloescht: {DIR} ({COUNT(DATEIEN)} Dateien)"

Log: "Backup-Cleanup: {COUNT(BACKUP_DIRS)} Verzeichnisse entfernt"
Log: "Hinweis: Geloeschte Dateien erscheinen in 'git status' als deleted."
```

**Sicherheit:** 0 Risiko — alle Dateien sind git-tracked (verifiziert: .backup_20260206/
mit 6 Dateien, kein .gitignore-Eintrag). Loeschung ist auf Dateisystem-Ebene, git
commit erfolgt durch User separat.

---

## Schritt 3.7: PL→Pre-PR Selbstlern-Loop Guard (RF-CS-013)

**Zweck:** Scanne abgeschlossene PL-Items → finde Muster die Pre-PR haette erkennen muessen → `/_PrePR_Update_Meta` automatisch ausfuehren.

```
# ═══ GUARD: PL→Pre-PR Selbstlern-Loop (RF-CS-013, Selbstlernende Metadaten) ═══
# NON-BLOCKING: FAIL von _PrePR_Update_Meta blockiert NICHT den Abschluss

1. Lies {VAULT}/_parking-lot.md
   Sammle alle [x] DONE Items (abgeschlossen im aktuellen Feature-Kontext)
   → N_DONE = Anzahl [x] Items

2. Falls N_DONE == 0:
   → SKIP (kein Lernpotential, Guard ueberspringen)

3. Pro [x] Item: Klassifiziere den Fix-Typ:

   FORM/SYNTAX:
     Indikatoren: Umlaute, Encoding, Naming, Cleanup, Logging,
                  Formatierung, Konstanten, XML-Doc, Magic Strings
     → Liste: FORM_ITEMS

   ARCHITEKTUR:
     Indikatoren: Pattern, Datenfluss, Controller-Logik, Interface,
                  DI, Schicht-Verletzung, Abhaengigkeit
     → Liste: ARCH_ITEMS

   CODE-FIX (kein Learning noetig):
     Indikatoren: Bug, Logik-Fehler, Null-Check, Exception, Test-Fix
     → Liste: CODE_ITEMS (ignorieren)

4. Falls COUNT(FORM_ITEMS) > 0:
   Logge: "[SELBSTLERN] {COUNT(FORM_ITEMS)} PL-Items zeigen Pre-PR Metadaten-Luecken"
   Logge: "  Items: {KOMMA_LISTE_KURZTITEL}"
   Fuehre aus: Skill(skill="_PrePR_Update_Meta")
   → Bei Fehler: Logge "[SELBSTLERN] _PrePR_Update_Meta fehlgeschlagen — nicht blockierend"
   → Weiter (NON-BLOCKING)

5. Falls COUNT(ARCH_ITEMS) > 0:
   Logge: "[SELBSTLERN] {COUNT(ARCH_ITEMS)} PL-Items zeigen Pattern Library Luecken"
   Logge: "  (Pattern Library Guard handelt das separat — Guard 2)"
   → Kein automatischer Trigger hier

6. Falls COUNT(FORM_ITEMS) == 0 AND COUNT(ARCH_ITEMS) == 0:
   Logge: "[SELBSTLERN] Keine Metadaten-Luecken erkannt (nur CODE-FIX Items)"
```

**Hintergrund (RF-CS-013):** Das System lernt NICHT aus wiederholten Fehlern wenn PL-Items nie ausgewertet werden. Dieser Guard schliesst den Lern-Loop: Projekt → PL-Items → Guard → Metadaten-Update → naechstes Projekt profitiert.

---

## Schritt 3.8: Pattern Library Validation (Selbstlernende Metadaten)

> **INV-EINSCHUB (AK-F-4, AK-F-7, BL-153): M-5 Einschub-Marker**
> Dieser Schritt 3.8 ist ein INV-EINSCHUB nach dem bestehenden Schritt 3.7 —
> bestehende Schritte werden NICHT veraendert.
>
> **AK-F-7 (BL-153): KEIN automatischer `_PT_extract --parking-lot-walk` Hook hier.**
> Die M1-Walk-Pattern-Extraktion ist MANUELL: Nach Feature-Abschluss kann der User
> `/_PT_extract --parking-lot-walk` explizit aufrufen um neue Patterns aus dem
> Parking-Lot zu extrahieren. Automatischer Hook ist verboten (INV-D4).

**Zweck:** Pruefe ob Patterns waehrend dieser Feature-Implementierung validiert wurden. Hat sich ein Pattern bewaehrt? Grenzen dokumentieren, battle-tested Patterns promoten.

```
# ═══ GUARD: Pattern Library Validation (Selbstlernende Metadaten) ═══
# Pruefe ob Patterns waehrend dieser Feature-Implementierung validiert wurden
#
# Scan-Logik:
#   1. Lies Libraries/PatternLibrary/_index.md (Vault-basiert, BL-153)
#      IF Libraries/PatternLibrary/ nicht existiert → SKIP (Pattern Library nicht initialisiert)
#      LEGACY: .claude/patterns/ wird nicht mehr verwendet (Vault-Migration BL-153)
#   2. Finde Patterns mit status: "dirty" oder "unbattle-tested"
#   3. Pro Pattern:
#      - Wurde es in diesem Feature verwendet? (Suche in Commit-Diff oder Manifest)
#      - Wenn JA und erfolgreich → status: "battle-tested" vorschlagen
#      - Wenn JA und gescheitert → Pattern-Grenzen dokumentieren
#      - Wenn NEIN → status bleibt (kein Urteil moeglich)
#   4. Katalog erstellen:
#      Logge: "[PATTERN-VALIDATION] {N} Patterns geprueft, {M} battle-tested, {K} Grenzen gefunden"
#   5. Bei HiL=on: AskUserQuestion mit Katalog fuer finale Entscheidung
#      Bei HiL=off: Auto-accept (battle-tested Patterns automatisch promoten)
#
# NON-BLOCKING: Guard blockiert NICHT den Abschluss
```

**Hintergrund:** Ein Pattern wird "dirty" markiert wenn es erstmalig eingesetzt wird, aber nie wieder validiert. Dieser Guard schliesst die Luecke: nach jedem Feature wird geprueft ob sich das Pattern bewaehrt hat — oder ob Grenzen (Minima/Maxima) aus Evidenzen zu dokumentieren sind.

---

## Schritt 4: Bereit fuer naechstes Feature

### 4.1 Manifest updaten

```
Aktualisiere {VAULT}/_manifest.md:
  PHASE: READY
  NAECHSTER_SCHRITT: (leer)
  VORHERIGES FEATURE: {NAME} (ABGESCHLOSSEN, SRS {SRS}, {ZYKLEN} Zyklen, {DATUM})
```

### 4.2 Parking-Lot aktualisieren

```
Falls neue Items aus Schritt 2 hinzugefuegt wurden:
  Sauber in _parking-lot.md eintragen mit Quelle und Datum.
```

### 4.3 User informieren

```
AUSGABE:
  "═══════════════════════════════════════════════════════
   Feature '{NAME}' abgeschlossen.
   ═══════════════════════════════════════════════════════

   Geparkt:    {N} Items fuer spaeter
   Verworfen:  {M} Items
   Erledigt:   {K} Items (nachtraeglich)

   Naechste Optionen:
   - /_A_orchestrate {NEUES_FEATURE}  → neues Feature analysieren
   - /_SC_orchestrate {NAME}          → Forschung vertiefen
   - Parking-Lot Item aufgreifen      → offene Items bearbeiten

   ═══════════════════════════════════════════════════════"
```

---

## QUICK-START

Wenn User sagt "Feature abschliessen" oder "/_finish":

```
1. Lies _manifest.md → NAME, Phase, Coverage
2. Zaehle offene Items (parking-lot + Task.md + Model)
3. Frage User pro Item: PARKEN / DISCARD / ERLEDIGT
4. Pruefe .claude/* Konsistenz
5. Manifest: PHASE=READY
6. Melde User: "Feature fertig, naechste Optionen"
```

---

ARGUMENTS: $ARGUMENTS
