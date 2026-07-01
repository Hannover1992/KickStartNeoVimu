---
type: building-block
---

# /_PT_update

**Status:** v1.0 (Initial — W245 KERN-BLOCKER teilweise geloest)
**Actor:** PATTERN-REGISTRAR
**Zweck:** Entwickler findet Pattern bei Review/Abnahme/Beobachtung → einspeisen als DRAFT in Pattern Library

---

## Aufruf

```
/_PT_update {pattern-name} {cluster} [beschreibung]
/_PT_update --from-pl-feedback   # (ARCH-21, BL-153) PL-Feedback-Loop Modus
```

| Parameter | Pflicht | Format | Beispiel |
|-----------|---------|--------|----------|
| pattern-name | NEIN bei --from-pl-feedback | kebab-case | `vertrag-block`, `kurzlebig-prompt` |
| cluster | NEIN bei --from-pl-feedback | Layer-Kuerzel aus _pl-index.md 2.3 | `cmd`, `test`, `be-cont`, `fe-comp`, `arch` |
| beschreibung | NEIN | Freitext (wird interaktiv abgefragt falls leer) | "VERTRAG-Block Pattern fuer Commands" |
| --from-pl-feedback | NEIN | Flag | Scannt PL-Items mit [PatternConformance]-Prefix und updated Pattern-Confidence |

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_PT_update {pattern-name} {cluster} [beschreibung]  |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. Libraries/PatternLibrary/_index.md                       |
|       → Duplikat-Check: existiert Pattern bereits?             |
|       → Layer-Routing: Cluster validieren                      |
|    2. User-Input: pattern-name, cluster, beschreibung          |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    3. Libraries/PatternLibrary/_generic/*.md                   |
|       → Aktueller Library-Stand fuer Kontext                   |
|    4. Aktueller Code-Kontext (falls Pattern aus Code stammt)   |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md |
|       → Neue Pattern-Datei, status: draft (W258)               |
|    2. .claude/wissen/pattern-usage.log                         |
|       → APPEND: Datum, Pattern-Name, Kontext, Quelle           |
|    3. Libraries/PatternLibrary/_index.md                       |
|       → Neuen Pattern-Link hinzufuegen                         |
|                                                                |
|  ACTOR: PATTERN-REGISTRAR                                      |
|    Nimmt Pattern-Kandidaten entgegen und persistiert sie        |
|    als DRAFT in der Pattern Library. Kein Battle-Test,          |
|    kein Promotion — nur Registrierung.                          |
|                                                                |
+===============================================================+
```

---

## Chain-Position

```
[Mensch findet Pattern] → [/_PT_update] → [/_Pre_PR_orchestrate Battle-Test]
       KANDIDAT               DRAFT                PROMOTED
    (mental, nicht           (persistiert,         (battle-tested,
     persistiert)            Blueprint-Kandidat)    W257)

/_SC_implement 1.5g PT-TRIGGER-CHECK:
  RED-Klassifikation + Custom-Implementation
  → PT-Trigger: /_PT_update ausfuehren (W246)
```

**Prev:** Mensch findet Pattern (Review, Abnahme, Code-Beobachtung) ODER _SC_implement 1.5g PT-Trigger
**Next:** /_Pre_PR_orchestrate (Battle-Test fuer PROMOTION, W257)

---

## Status-Schema (W258 Pattern-Maturity-System)

| Status | Beschreibung | Gesetzt durch | Persistiert? |
|--------|-------------|---------------|-------------|
| KANDIDAT | Mentale Notiz: Mensch erkennt wiederkehrendes Muster | Mensch (Review/Abnahme) | NEIN (nur im Kopf) |
| DRAFT | /_PT_update hat Pattern registriert. Sofort als Blueprint-Kandidat verfuegbar. | /_PT_update | JA (Libraries/PatternLibrary/_project/{LAYER}/{name}.md) |
| PROMOTED | /_Pre_PR_orchestrate Battle-Test bestanden. Alle Gates PASS. | /_Pre_PR_orchestrate (W257) | JA (status update) |
| MATURE | Mehrfach in Production genutzt, eigene Usage-Bounds bekannt. | /_PT_extract (W254) | JA (status update + bounds) |

### Transition-Matrix (RF-PT7, W258)

**Normatives SPEC-Artefakt: Jede Transition hat genau 1 verantwortlichen Mechanismus.**
**Scope:** Code/Command-Patterns JA, Model-Patterns NEIN (AC-PT7-4).

| Transition | Trigger-Bedingung | Mechanismus | Graceful |
|------------|------------------|-------------|---------|
| KANDIDAT → DRAFT | Mensch findet Pattern bei Review/Beobachtung/SC-ORANGE | `/_PT_update` oder `/_PT_extract` | Immer moeglich |
| DRAFT → PROMOTED | Pattern ueberlebt _Pre_PR_orchestrate Phase 4c (ALLE 9 Gates PASS) | `_Pre_PR_orchestrate` setzt `battle_test: passed` | Phase 4c nicht implementiert → DRAFT bleibt DRAFT |
| PROMOTED → MATURE | >= 3 erfolgreiche Anwendungen ueber >= 2 Features (aus pattern-usage.log) | `/_PT_update` Update-Modus setzt status: mature + bounds | pattern-usage.log fehlt → PROMOTED bleibt |
| Jede → DEPRECATED | Evidenz-Pflicht (W222): Pattern funktioniert nicht mehr | Manuell via `/_PT_update`, deprecated_reason Pflichtfeld (AC-PT7-6) | Mensch muss Evidenz liefern |

**Frontmatter-Schema-Varianten pro Status (AC-PT7-3):**

DRAFT (Standard, von /_PT_update gesetzt):
```yaml
status: draft
battle_test: pending
```

PROMOTED (nach Battle-Test, von _Pre_PR_orchestrate gesetzt):
```yaml
status: promoted
battle_test: passed
promoted_at: "{YYYY-MM-DD}"
```

MATURE (nach >= 3 Anwendungen ueber >= 2 Features):
```yaml
status: mature
battle_test: passed
bounds:
  min_usage_count: {N}
  max_reuse_score: {0.0-1.0}
  typical_features: ["{feature1}", "{feature2}"]
```

DEPRECATED (manuell, Evidenz-Pflicht):
```yaml
status: deprecated
deprecated_reason: "{Freitext mit Evidenz-Referenz}"
deprecated_at: "{YYYY-MM-DD}"
replacement_pattern: "{P-ID oder 'keiner'}"
```

**Invarianten:**
- KANDIDAT wird NICHT persistiert (nur im Kopf des Entwicklers)
- DRAFT ist sofort als Blueprint-Kandidat verfuegbar fuer _I_patternLibrary (AC-PT7-5)
- DEPRECATED ist IMMER manuell — kein Auto-DEPRECATED durch System (AC-PT7-6)

### APPEND-ONLY Regel (BL-103, AK-C-6, BL-153)

**Status-Transitionen sind irreversibel — kein Rollback:**

| Regel | Beschreibung |
|-------|-------------|
| Kein Status-Rollback | PROVEN → experimental verboten. DEPRECATED → PROVEN verboten. |
| Kein Hard-Delete | Pattern-Knoten werden NIE geloescht. Stattdessen: status=DEPRECATED. |
| DEPRECATED mit Evidenz | `deprecated_reason` ist PFLICHTFELD wenn status=DEPRECATED (BLOCKER). |
| Widerspruch/0-Vorkommen | Kein Auto-DEPRECATED — IMMER manuell mit Evidenz-Referenz (AC-PT7-6). |

```yaml
# Korrekt: DEPRECATED mit Evidenz (Pflicht)
status: deprecated
deprecated_reason: "Abgeloest durch neues Pattern PT-X. Kein Vorkommen seit B-12."
deprecated_at: "2026-04-30"
replacement_pattern: "PT-GEN-NachfolgerName"  # oder "keiner"

# VERBOTEN: Status-Rollback
# status: experimental  # nach PROVEN — VERBOTEN
```

### Trigger-Inventur (RF-PT5, W255)

**7 Trigger-Punkte fuer PT-Commands systemweit (ADR-PL-008: nur _SC_implement 1.5g darf PT-Commands direkt aufrufen):**

| # | Trigger-Punkt | Trigger-Bedingung | Aktion | Typ | Status |
|---|--------------|-------------------|--------|-----|--------|
| 1 | `_SC_implement` 1.5g | RED-Klassifikation + _PT_extract.md existiert | `/_PT_extract` direkt aufrufen | Direkt | aktiv |
| 2 | `_SC_orchestrate` Step 7a | FULL/INLINE + Pattern-Kandidat + _PT_extract.md existiert | Task fuer `/_PT_extract` erzeugen | Task | aktiv |
| 3 | `_I_patternLibrary` | `[KEIN PATTERN GEFUNDEN]` bei MCP-Query | Manifest s{N}_pt_signal: KEIN_PATTERN + pattern-usage.log | Signal | offen (RF-PIL2) |
| 4 | `_SC_implement` 1.5g | Jede Farbe (GRAY/ORANGE/RED) | pattern-usage.log APPEND | Log | aktiv |
| 5 | `_I_verify` | Pattern erfolgreich verifiziert | pattern-usage.log VERIFIED Signal | Signal | offen |
| 6 | `_R_evidence` | pattern_evolution Typ | Hinweis auf /_PT_update (HiL, kein Auto-Aufruf) | Signal | offen |
| 7 | `_Pre_PR_orchestrate` | Phase 4c nach FAN_IN | Battle-Test Auswertung | Signal | offen |

**Invariante (ADR-PL-008):** KEIN Command ausser `_SC_implement 1.5g` darf PT-Commands direkt aufrufen. Alle anderen Trigger-Punkte erzeugen nur Signale (Manifest-Felder, pattern-usage.log).

**Graceful Degradation:** Falls PT-Command nicht existiert → SKIP (kein Fehler-Abbruch). Manifest-Vermerk: `PT_SKIP_W245_OFFEN`.

---

## Schritte

### Schritt 0: Parameter validieren

```
1. pattern-name vorhanden?
   → NEIN: AskUserQuestion "Pattern-Name (kebab-case)?"
   → JA: Weiter

2. cluster vorhanden?
   → NEIN: AskUserQuestion "Cluster/Layer? (cmd, test, be-cont, be-core, fe-comp, ...)"
   → JA: Weiter

3. beschreibung vorhanden?
   → NEIN: AskUserQuestion "Kurze Beschreibung des Patterns?"
   → JA: Weiter
```

### Schritt 1: Duplikat-Check

```
1. Lies Libraries/PatternLibrary/_index.md
2. Grep nach {pattern-name} (case-insensitive)
3. Falls TREFFER:
   → WARNUNG: "Pattern '{pattern-name}' existiert bereits in _index.md."
   → Frage User: "Update-Modus? (j=bestehenden Eintrag ergaenzen / n=abbrechen)"
   → Bei NEIN: STOP (kein Duplikat anlegen)
   → Bei JA: Bestehende Datei lesen und ergaenzen statt neu erstellen
4. Falls KEIN TREFFER: Weiter (neues Pattern)
```

### Schritt 2: Pattern-Datei erstellen

Erstelle `Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md`:

```markdown
---
id: P-{CLUSTER-UPPER}-{NAME-UPPER}
status: draft
date_added: {YYYY-MM-DD}
added_by: /_PT_update
cluster: {cluster}
battle_test: pending
source: {review|abnahme|beobachtung|pt-trigger}
---

# {Pattern-Name (Title Case)}

## Zweck

{beschreibung}

## Wann anwenden

- [ ] Trigger-Bedingung 1 (vom User/Entwickler auszufuellen)
- [ ] Trigger-Bedingung 2

## Beispiel

{Konkretes Code/Command-Beispiel falls verfuegbar, sonst Platzhalter}

## Nicht anwenden wenn

- [ ] Anti-Pattern-Bedingung (vom User/Entwickler auszufuellen)

## Referenzen

- Erstellt von: /_PT_update
- Datum: {YYYY-MM-DD}
- Cluster: {cluster}
- W{n}-Bezug: {falls bekannt, sonst "keiner"}
```

**Verzeichnis-Erstellung:**
Falls `Libraries/PatternLibrary/_project/{LAYER}/` nicht existiert → `mkdir -p Libraries/PatternLibrary/_project/{LAYER}/`

### Schritt 3: pattern-usage.log aktualisieren

```
Datei: .claude/wissen/pattern-usage.log
Falls nicht vorhanden: Erstellen mit Header-Zeile.

Format:
  {YYYY-MM-DD} | {pattern-id} | {pattern-name} | {cluster} | DRAFT | {quelle}

Beispiel:
  2026-03-07 | P-CMD-VERTRAG-BLOCK | vertrag-block | cmd | DRAFT | review
```

### Schritt 3.5: Referenz-Update bei VERIFIED (RF-MAT3, AC-MAT3-2)

```
1. Lies .claude/wissen/pattern-usage.log
   Suche: Eintrag mit {pattern-id} und Status VERIFIED
   → NICHT vorhanden oder pattern-usage.log fehlt: SKIP (Graceful Degradation)
   → VERIFIED-Eintrag gefunden: Weiter

2. Lies Pattern-Datei (Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md)
   Suche: Sektion "## Referenzen"

3. Extrahiere Code-Pfad aus VERIFIED-Eintrag in pattern-usage.log
   Format: {DATUM} | {pattern-id} | ... | VERIFIED | {feature}

4. Fuege Referenz hinzu in "## Referenzen":
   - Verifiziert in: {feature} ({code-context-file}, {DATUM})

5. Schwelle: >= 1 VERIFIED-Eintrag → Referenz-Befuellung PFLICHT (AC-MAT3-3)
   Referenz-Feld DARF NICHT dauerhaft leer bleiben nach VERIFIED-Nutzung (AC-MAT3-1)
```

### Schritt 4: _index.md aktualisieren

```
1. Lies Libraries/PatternLibrary/_index.md
2. Finde Sektion oder Table für neue Pattern-Einträge
3. Fuege neuen Eintrag hinzu:
   | `_project/{LAYER}/{pattern-name}.md` | {beschreibung} | P-{LAYER}-{NAME} (DRAFT) | v1.0 |
4. Falls Konsumenten-Sektion existiert:
   → Pruefe ob /_PT_update bereits als Schreiber gelistet ist
   → Falls NEIN: Hinzufuegen (Graceful: nur wenn Sektion erkennbar)
```

### Schritt 4b: PL-Feedback Loop (--from-pl-feedback Modus, ARCH-21, BL-153)

> **Einschub-Strategie (INV-EINSCHUB):** Nur wenn `--from-pl-feedback` Flag gesetzt.
> NON-BLOCKING — leere PL-Item-Liste oder kein PatternConformance-Item → SKIP.
> Konsumiert `[PatternConformance]`-getaggte PL-Items aus Parking-Lot und updated
> Pattern-Frontmatter.confidence basierend auf WARN-Frequenz (AK-C-2, AK-C-3, BL-153).

```
IF "--from-pl-feedback" NOT IN args:
  SKIP (normaler Registrierungs-Pfad → weiter zu Schritt 5)

# Schritt 4b.1: PatternConformance PL-Items scannen
pl_feedback_items = []
FUER pl_item IN lies_parking_lot():
  IF "[PatternConformance]" IN pl_item.text OR pl_item.tags enthaelt "pattern-conformance":
    pl_feedback_items.append(pl_item)

IF |pl_feedback_items| == 0:
  Logge: "[PT-PL-Feedback] Keine [PatternConformance]-Items gefunden — SKIP (NON-BLOCKING)"
  RETURN

Logge: "[PT-PL-Feedback] {|pl_feedback_items|} PatternConformance-Items gefunden"

# Schritt 4b.2: Pro Pattern Confidence-Frequenz berechnen (AK-C-2: 1×medium, 2×high)
pattern_warn_counts = {}
FUER item IN pl_feedback_items:
  pattern_ids = extrahiere_pattern_ids(item.text)  # grep nach P-*-* oder PT-GEN-* IDs
  FUER pid IN pattern_ids:
    pattern_warn_counts[pid] = (pattern_warn_counts.get(pid) OR 0) + 1

# Schritt 4b.3: Confidence updaten basierend auf WARN-Frequenz (S1 QUICKFIX 2026-05-01)
# WARNs sind Pattern-VERLETZUNGEN — d.h. Pattern wurde erwartet, aber Code hielt sich nicht daran.
# Vision V6 (BL-153 Audit): "User parkt PL-Items, das ist Lernimpuls fuer Pattern-Anpassung"
# Mehr WARNs => Pattern problematisch / unklar / falsch angewandt => confidence SENKEN, nicht heben.
# FRUEHERER BUG (vor S1-Quickfix): warn_count>=2 → high. Das war invertiert.
# Confidence-UPGRADE soll NUR ueber positive Signale erfolgen (Battle-Test PROMOTED via _Pre_PR_orchestrate,
# usage_count via _PT_extract MATURE-Promotion). PL-Feedback-Loop kann ausschliesslich DOWNGRADEN.
FUER pid, warn_count IN pattern_warn_counts.items():
  pattern_path = finde_pattern_datei(pid)  # aus Libraries/PatternLibrary/
  IF pattern_path IS NULL: CONTINUE

  pattern_fm = lies_frontmatter(pattern_path)
  old_confidence = pattern_fm.confidence ?? "low"

  # Confidence-Downgrade-Stufung (AK-C-2 reinterpretiert nach S1-Audit, BL-153)
  IF warn_count >= 2:
    new_confidence = "low"   # Pattern wird wiederholt verletzt → review noetig, ggf. DEPRECATED-Kandidat
  ELIF warn_count == 1:
    # 1 WARN ist Hinweis. Confidence bleibt mindestens auf "low", aber kein Upgrade.
    # NUR Downgrade wenn aktuell ueber "low" (Hinweis dass Pattern nicht mehr universell gilt).
    IF model_rank(old_confidence) > model_rank("low"):
      new_confidence = "low"
    ELSE:
      CONTINUE  # bereits low, kein weiteres Downgrade
  ELSE:
    CONTINUE

  # NUR schreiben wenn echtes DOWNGRADE (kein Upgrade durch PL-Feedback erlaubt)
  IF model_rank(new_confidence) < model_rank(old_confidence):
    Schreibe frontmatter.confidence = new_confidence IN pattern_path
    Schreibe frontmatter.confidence_updated_at = "{DATUM}" IN pattern_path
    Schreibe frontmatter.warn_count = warn_count IN pattern_path
    Logge: "[PT-PL-Feedback] {pid}: confidence {old_confidence} → {new_confidence} (WARN-Count: {warn_count}) — DOWNGRADE wegen Pattern-Verletzungen"
    pattern-usage.log APPEND: "{DATUM} | {pid} | - | - | CONFIDENCE_DOWNGRADE | pt-pl-feedback"

Logge: "[PT-PL-Feedback] DONE — {|pattern_warn_counts|} Patterns geprueft, Confidence-Updates gespeichert"
```

### Schritt 5: User-Feedback

```
Ausgabe:
  "Pattern '{pattern-name}' als DRAFT in {cluster}/ gespeichert."
  "  Datei: Libraries/PatternLibrary/_project/{LAYER}/{pattern-name}.md"
  "  Status: DRAFT (W258 Maturity-System)"
  "  Naechster Schritt: Battle-Test via /_Pre_PR_orchestrate fuer PROMOTION."
  "  pattern-usage.log: Eintrag hinzugefuegt."
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| Libraries/PatternLibrary/_index.md existiert nicht | Pattern-Datei trotzdem erstellen. WARNUNG: "_index.md nicht gefunden, Pattern nur als Datei gespeichert." pattern-usage.log Eintrag schreiben. |
| Libraries/PatternLibrary/_generic/ existiert nicht | Kein Blocker. /_PT_update braucht nur _index.md fuer Duplikat-Check. |
| Libraries/PatternLibrary/_project/{LAYER}/ Verzeichnis fehlt | mkdir -p erstellen. |
| pattern-usage.log existiert nicht | Erstellen mit Header: `# Pattern Usage Log` + `# Format: DATUM \| PATTERN-ID \| NAME \| CLUSTER \| STATUS \| QUELLE` |

---

## Qualitaetskriterien

- VERTRAG-Block vorhanden (LIEST/SCHREIBT Sektionen)
- Status-Schema KANDIDAT/DRAFT/PROMOTED/MATURE dokumentiert (W258)
- Duplikat-Check gegen _pl-index.md als Guard
- Pattern-Datei-Format mit Frontmatter (id, status, cluster, battle_test)
- Schritte klar und ausfuehrbar (0-5)
- Graceful Degradation fuer fehlende Dateien/Verzeichnisse
- pattern-usage.log Eintrag fuer Audit-Trail (W250)

---

## Abgrenzung

```
/_PT_update      = Pattern REGISTRIEREN (KANDIDAT → DRAFT, einzeln, inline)
/_PT_init        = Pattern Library INITIALISIEREN (Template-Setup, W252)
/_PT_extract     = Pattern EXTRAHIEREN aus Code-Kontext (1 Command, kein Orchestrator)

Nur /_PT_update ist inline/leichtgewichtig.
/_PT_init erfordert Orchestrierung. /_PT_extract = 1 Command, kein Orchestrator.
```

---

## Architektonischer Pattern-Lifecycle (BL-154, AK-4-1..AK-4-5)

> ⚠ **SINGLE-SOURCE-VERWEIS (BL-237 AK-COUNTER-0 / C-2, 2026-06-02):** Die folgende Pfad-1/2/3/5-Logik ist
> AUSFUEHRBAR materialisiert in **`.claude/scripts/pattern_library.py`** (`lifecycle(pid, pfad, scope, **ctx)`,
> CLI `py pattern_library.py lifecycle {pid} --pfad N --scope arch|domain|factoring|semantic`). Der Block
> unten ist die SPEC/Referenz, NICHT der Ausfuehrungs-Ort. **VERBOTEN: `subprocess(_PT_update.md ...)`** —
> Markdown ist physisch nicht aufrufbar (das war der „Kabel-ins-Leere"-Bug). EIN parametrisierter Counter-Kern,
> kein zweites Modell, keine `--*-lifecycle`-Klone. Schwellen 5/10/3 + Feldnamen leben in `pattern_library.py`
> (`THRESH_ACTIVE/PROVEN/DEPRECATE`); dieser Doc-Block muss feld-/schwellen-deckungsgleich bleiben (Diff = 0).

> **Scope:** Gilt NUR fuer architektonische Patterns (scope: architectural, BL-154).
> Semantische Patterns (BL-153, scope: semantic) nutzen weiterhin confidence-Mechanismus.
> Unterscheidung via Frontmatter: `scope: architectural` vs. `scope: semantic`.

### Aufruf --arch-lifecycle

```
/_PT_update --arch-lifecycle {pattern-id} {pfad} [parameter]
```

| Pfad | Trigger | Pflichtparameter |
|------|---------|-----------------|
| pfad-1 | Pattern gefunden und angewandt | `--pattern-id PT-{LAYER}-{NR}` |
| pfad-2 | Pattern passt nicht | `--pattern-id` + `--broken-context "{context}"` + `--broken-reason "{reason}"` |
| pfad-3 | Aehnliches Pattern → Abwandlung | `--source-id PT-{LAYER}-{NR}` + `--new-name {kebab-name}` |
| pfad-4 | Kein Pattern → Neuer Knoten | Wie normaler `/_PT_update`-Aufruf + `--scope architectural` |
| pfad-5 | Suche > 3 Attempts → STOP | `--layer {LAYER}` + `--context "{kontext}"` |

### 5-Pfade-Verifikationstabelle (BL-154-PL-33, ARCH-H7)

> **Zweck (PL-33):** Jeder Pfad hat deterministisch UNTERSCHIEDLICHES Verhalten im Output.
> Pruefbar via `/_PT_update --arch-lifecycle {pattern-id} pfad-N` — Output muss GENAU
> die unten beschriebenen Signale emittieren. Kein Pfad darf das Output eines anderen ergeben.

| Pfad | Pfad-Identifier | Manifest-Aktion | pattern-usage.log Signal | pattern.md Mutation | Return-Signal |
|------|----------------|-----------------|--------------------------|---------------------|---------------|
| **Pfad-1** | `usage++` | `frontmatter.usage_count = N+1`, ggf. `status_promoted_at` | `USED` | usage_count++, last_used, ggf. status-Upgrade | `{usage_count: N+1, new_status: ...}` |
| **Pfad-2** | `broken++` | `frontmatter.broken_count = M+1`, ggf. `status = deprecated` | `BROKEN` oder `AUTO_DEPRECATED` | broken_count++, boundary_notes APPEND, broken_locations APPEND, ggf. deprecated | `{broken_count: M+1, auto_deprecated: true|false}` |
| **Pfad-3** | `derived` | Neues Pattern in `_project/{LAYER}/{new_name}.md`, `source_fm.variants APPEND` | `DERIVED` | new pattern erstellt, source.variants++ | `{new_id: PT-..., derived_from: source_id}` |
| **Pfad-4** | `new_node` | Neue Pattern-Datei in `_project/{LAYER}/{name}.md`, `_index.md APPEND` | — (kein Log, via Schritt 3 oben) | neue Datei, status=experimental | `{created: Libraries/PatternLibrary/...}` |
| **Pfad-5** | `stop` | pattern-usage.log APPEND, Parking-Lot Notiz | `STOP` | KEINE Mutation | `{no_pattern_found: true}` |

**Invariante (PL-33):** Pfad-1 und Pfad-2 duerfen NIE in demselben Aufruf gleichzeitig aktiv sein.
Pfad-5 mutiert KEINE Pattern-Datei (read-only, pure STOP-Signal).

---

### Pfad-1: Pattern angewandt → usage_count++ (AK-4-1, W12, W24)

```
/_PT_update --arch-lifecycle {pattern-id} pfad-1
```

```
# Pfad-1 Ablauf (BL-154 AK-4-1)
pattern_path = finde_arch_pattern_datei(pattern_id)
IF pattern_path IS NULL:
  Logge WARNUNG: "[Pfad-1] Pattern {pattern_id} nicht gefunden — SKIP"
  RETURN

# usage_count erhoehen (Strichliste)
pattern_fm = lies_frontmatter(pattern_path)
old_count = pattern_fm.usage_count ?? 0
new_count = old_count + 1
Schreibe frontmatter.usage_count = new_count IN pattern_path
Schreibe frontmatter.last_used = "{YYYY-MM-DD}" IN pattern_path

# Status-Upgrade pruefen (W25, W26)
# Schwellwerte: experimental→active bei 5, active→PROVEN bei 10
old_status = pattern_fm.status ?? "experimental"
new_status = old_status
IF old_status == "experimental" AND new_count >= 5:
  new_status = "active"
  Logge: "[Pfad-1] {pattern_id}: experimental → active (usage_count={new_count})"
ELIF old_status == "active" AND new_count >= 10:
  new_status = "PROVEN"
  Logge: "[Pfad-1] {pattern_id}: active → PROVEN (usage_count={new_count})"

IF new_status != old_status:
  Schreibe frontmatter.status = new_status IN pattern_path
  Schreibe frontmatter.status_promoted_at = "{YYYY-MM-DD}" IN pattern_path

# ApplicationTrail (W4, AK-7-3): Erstellung bei PROVEN, APPEND bei bestehendem Trail
IF new_status == "PROVEN" AND old_status != "PROVEN":
  # Neu-PROVEN: ApplicationTrail_{ID}.md erstellen (AK-7-3)
  trail_path = "Libraries/PatternLibrary/_project/{pattern_fm.layer}/ApplicationTrail_{pattern_id}.md"
  IF NOT exists(trail_path):
    schreibe(trail_path, {
      frontmatter: {id: pattern_id, pattern_layer: pattern_fm.layer, promoted_at: heute_iso8601},
      inhalt: "# ApplicationTrail — {pattern_id}\n\n## Anwendungs-Historie\n\n| Datum | Kontext | Pfad | Slice |\n|-------|---------|------|-------|\n| {DATUM} | Promotion zu PROVEN | pfad-1 | — |"
    })
    Schreibe frontmatter.hard_reference = trail_path IN pattern_path
    Logge: "[Pfad-1 AK-7-3] ApplicationTrail erstellt: {trail_path}"
  ELSE:
    APPEND IN trail_path: "{DATUM} | Pfad-1 Anwendung | PROVEN | —"
ELIF pattern_fm.hard_reference IS NOT NULL:
  # Bestehender Trail: APPEND
  trail_path = finde_trail_datei(pattern_fm.hard_reference)
  IF trail_path NOT NULL:
    APPEND IN trail_path: "{YYYY-MM-DD} | pfad-1 | {kontext-falls-vorhanden}"

# pattern-usage.log APPEND
pattern-usage.log APPEND:
  "{DATUM} | {pattern_id} | {pattern_fm.title ?? pattern_id} | {pattern_fm.layer} | USED | pfad-1"

Logge: "[Pfad-1] {pattern_id}: usage_count {old_count} → {new_count}, status={new_status}"
```

**APPEND-ONLY-Regel (BL-103):** usage_count wird NUR inkrementiert, nie reduziert.
Status-Upgrade ist IRREVERSIBEL (experimental → active → PROVEN, kein Rollback).

---

### Pfad-2: Pattern passt nicht → broken_count++ + boundary_notes (AK-4-2, AK-4-3, W13)

```
/_PT_update --arch-lifecycle {pattern-id} pfad-2 --broken-context "..." --broken-reason "..."
```

```
# Pfad-2 Ablauf (BL-154 AK-4-2 + AK-4-3)
pattern_path = finde_arch_pattern_datei(pattern_id)
IF pattern_path IS NULL:
  Logge WARNUNG: "[Pfad-2] Pattern {pattern_id} nicht gefunden — SKIP"
  RETURN

pattern_fm = lies_frontmatter(pattern_path)

# boundary_notes APPEND (W13 — Pattern stirbt langsam durch Beweise)
broken_note = "broken in {broken_context}: {broken_reason}"
old_notes = pattern_fm.boundary_notes ?? []
new_notes = old_notes + [broken_note]
Schreibe frontmatter.boundary_notes = new_notes IN pattern_path

# broken_locations APPEND (BL-154-PL-34, ARCH-H8): Strukturierte Bruchstellen-Dokumentation
# Jeder Pfad-2-Aufruf fuegt einen Eintrag mit file, class, reason, date hinzu
broken_location_entry = {
  file: broken_context,              # Datei-Pfad wo Pattern gebrochen
  class: (extrahiere_klasse(broken_context) ?? null),  # Optional: Klassenname
  reason: broken_reason,             # Freitext-Begruendung
  date: "{YYYY-MM-DD}"
}
old_locations = pattern_fm.broken_locations ?? []
new_locations = old_locations + [broken_location_entry]
Schreibe frontmatter.broken_locations = new_locations IN pattern_path
Logge: "[Pfad-2] broken_locations: {|new_locations|} Eintraege (PL-34)"

# broken_count erhoehen
old_broken = pattern_fm.broken_count ?? 0
new_broken = old_broken + 1
Schreibe frontmatter.broken_count = new_broken IN pattern_path

# Deprecated-Schwelle pruefen (AK-4-3, W13: Schwellwert = 3)
# KRITISCH: broken_count >= 3 → automatisch DEPRECATED (APPEND-ONLY, IRREVERSIBEL)
IF new_broken >= 3:
  old_status = pattern_fm.status ?? "experimental"
  IF old_status != "deprecated":
    Schreibe frontmatter.status = "deprecated" IN pattern_path
    Schreibe frontmatter.deprecated_reason = (
      "Auto-DEPRECATED: broken_count={new_broken} >= 3. "
      "Letzte broken_note: {broken_note}. "
      "Alle boundary_notes: {new_notes}"
    ) IN pattern_path
    Schreibe frontmatter.deprecated_at = "{YYYY-MM-DD}" IN pattern_path
    Schreibe frontmatter.replacement_pattern = "keiner"  # Placeholder — User kann ersetzen
    Logge: "[Pfad-2] {pattern_id}: DEPRECATED (broken_count={new_broken} >= 3)"
    pattern-usage.log APPEND:
      "{DATUM} | {pattern_id} | {pattern_fm.title ?? pattern_id} | {pattern_fm.layer} | AUTO_DEPRECATED | broken_count={new_broken}"
ELSE:
  Logge: "[Pfad-2] {pattern_id}: broken_count {old_broken} → {new_broken}. Schwelle 3 nicht erreicht."
  pattern-usage.log APPEND:
    "{DATUM} | {pattern_id} | {pattern_fm.title ?? pattern_id} | {pattern_fm.layer} | BROKEN | broken_count={new_broken}"
```

**Invarianten Pfad-2:**
- `boundary_notes` ist APPEND-ONLY — bestehende Notizen werden NICHT geloescht
- `broken_count >= 3` loest automatisches DEPRECATED aus (kein HiL-Gate)
- DEPRECATED-Status ist IRREVERSIBEL (APPEND-ONLY-Regel)
- `replacement_pattern` bleibt "keiner" bis User manuell ersetzt

---

### Pfad-3: Abwandlung → derived_from + variants Backlink (AK-4-4, W14)

```
/_PT_update --arch-lifecycle pfad-3 --source-id {PT-LAYER-NR} --new-name {kebab-name} [beschreibung]
```

```
# Pfad-3 Ablauf (BL-154 AK-4-4)
source_path = finde_arch_pattern_datei(source_id)
IF source_path IS NULL:
  Logge WARNUNG: "[Pfad-3] Quell-Pattern {source_id} nicht gefunden. Abbruch."
  RETURN

source_fm = lies_frontmatter(source_path)
source_layer = source_fm.layer ?? "BE-UNKNOWN"

# Neuen Knoten erstellen (analog Schritt 0-4 oben, mit Erweiterungen)
new_pattern_id = generiere_naechste_id(source_layer)  # z.B. PT-CORE-007
new_pattern_path = Libraries/PatternLibrary/_project/{source_layer}/{new_name}.md

# Frontmatter des Abwandlungs-Knotens
Erstelle {new_pattern_path} mit Frontmatter:
  id: {new_pattern_id}
  type: pattern
  scope: architectural
  layer: {source_layer}
  status: experimental          # Abwandlung startet immer experimental (W14)
  usage_count: 0
  applies_to: "{beschreibung}"
  severity: {source_fm.severity ?? "RECOMMENDED"}
  min_scope: "{source_fm.min_scope ?? TBD}"   # Erbt Ausgangswerte, Worker praezisiert
  max_scope: "{source_fm.max_scope ?? TBD}"
  boundary_notes: []
  broken_count: 0
  derived_from: "{source_id}"   # PFLICHT-Backlink auf Ursprungs-Pattern (AK-4-4)
  variants: []
  date_added: "{YYYY-MM-DD}"
  added_by: /_PT_update --arch-lifecycle pfad-3

# Backlink im Original-Pattern setzen (variants Liste)
old_variants = source_fm.variants ?? []
new_variants = old_variants + [{new_pattern_id}]
Schreibe frontmatter.variants = new_variants IN source_path
Logge: "[Pfad-3] {source_id}.variants erhalten Backlink → {new_pattern_id}"

# _index.md aktualisieren (analog Schritt 4)
APPEND IN Libraries/PatternLibrary/_index.md:
  | `_project/{source_layer}/{new_name}.md` | {beschreibung} | {new_pattern_id} (EXPERIMENTAL, derived_from: {source_id}) | v1.0 |

# pattern-usage.log
pattern-usage.log APPEND:
  "{DATUM} | {new_pattern_id} | {new_name} | {source_layer} | DERIVED | source={source_id}"

Logge: "[Pfad-3] Abwandlung {new_pattern_id} erstellt. derived_from={source_id}. variants-Backlink gesetzt."
```

---

### Pfad-4: Kein Pattern → Neuer Knoten (AK-1-3, W3)

```
# Pfad-4 = Standard-Aufruf von /_PT_update mit --scope architectural
/_PT_update {pattern-name} {layer} {beschreibung} --scope architectural
```

```
# Pfad-4 erstellt neuen Knoten mit architektonischem Frontmatter-Schema (W3, AK-1-3)
# Unterschied zum Standard-Aufruf: ERWEITERTES Frontmatter (BL-154-spezifische Felder)

Frontmatter-Schema fuer Pfad-4 (architektonisch, W3):
  id: PT-{LAYER}-{NR:03d}          # z.B. PT-CORE-001
  type: pattern
  scope: architectural              # NEU vs. semantisch
  layer: BE-{LAYER}                 # z.B. BE-CORE, BE-CONT
  status: experimental              # IMMER experimental bei Neuerstellung
  usage_count: 0
  applies_to: "{Kontext-Beschreibung}"
  severity: MANDATORY|RECOMMENDED|OPTIONAL
  min_scope: "{Wann Overkill — Worker befuellt}"
  max_scope: "{Wann Pattern nicht mehr traegt — Worker befuellt}"
  boundary_notes: []
  broken_count: 0
  derived_from: null                # kein Ursprung (original)
  variants: []
  seed: false                       # nur true wenn aus Bootstrap
  date_added: "{YYYY-MM-DD}"
  added_by: /_PT_update pfad-4
```

**Pfad-4 Invarianten:**
- `status: experimental` ist PFLICHT bei Neuerstellung (nie direct active/PROVEN)
- `usage_count: 0` bei Neuerstellung (Strichliste startet leer)
- `derived_from: null` markiert Original (nicht Abwandlung)

---

### Pfad-5: Stop-Mechanismus — 3 Attempts, dann STOP (AK-4-5, W33, W34)

```
/_PT_update --arch-lifecycle pfad-5 --layer {LAYER} --context "{kontext}"
```

> **Zweck (W33):** Verhindert Endlosschleifen bei Pattern-Suche. Worker darf max. 3
> Lookup-Versuche machen. Beim 4. Versuch → STOP, dokumentiere, Ticket.

```
# Pfad-5 Ablauf (BL-154 AK-4-5, W33, W34)
# Aufgerufen von Worker nach 3 erfolglosen Lookup-Versuchen

# no_pattern_found dokumentieren (W34: Feedback-Schleife)
Logge: "[Pfad-5] STOP: 3 Suche-Versuche erschoepft fuer Layer={layer}, Kontext={context}"

# pattern-usage.log
pattern-usage.log APPEND:
  "{DATUM} | NO_PATTERN | - | {layer} | STOP | context={context}"

# Parking-Lot Notiz (W34: User entscheidet ob neuer Knoten noetig)
pl_eintrag = {
  typ: "[ArchPL] Pfad-5 STOP",
  layer: layer,
  context: context,
  datum: "{YYYY-MM-DD}",
  hinweis: "3 Suche-Versuche erschoepft. Entscheidung: neuer Pattern-Knoten via Pfad-4 ODER genuiner Einzel-Case (kein Pattern)."
}
Logge: "[Pfad-5] Parking-Lot-Notiz: {pl_eintrag}"

# Output fuer aufrufer (stop_signal)
RETURN:
  no_pattern_found: true
  layer: {layer}
  context: {context}
  recommendation: "Pfad-4 (neuer Knoten) ODER Einzel-Case (User-Entscheidung)"
```

**Stop-Mechanismus Invarianten (W33):**
- Max 3 Attempts = strikt (nicht "ungefaehr 3")
- Beim 4. Versuch IMMER STOP — kein weiterer Lookup
- Worker-Prompt muss Zaehler selbst tracken (Stateless-System)
- ARCH-VERTRAG-Block im Worker-Prompt enthalt `max_search_attempts: 3`

---

### Architektonisches Frontmatter-Schema (Referenz, W3)

Vollstaendiges Schema fuer architektonische Pattern-Knoten (BL-154, AK-1-3):

```yaml
# Pflichtfelder (alle MUESSEN vorhanden sein):
id: PT-{LAYER}-{NR:03d}            # z.B. PT-CORE-001
type: pattern
scope: architectural               # unterscheidet von semantic (BL-153)
layer: BE-{LAYER}                  # z.B. BE-CORE, BE-CONT
status: experimental|active|PROVEN|DEPRECATED
usage_count: 0                     # Strichliste — incrementiert durch Pfad-1
applies_to: "{Kontext-Beschreibung}"
severity: MANDATORY|RECOMMENDED|OPTIONAL

# Neue Felder (BL-154-spezifisch, kein Aequivalent in BL-153):
min_scope: "{Wann Anwendung Overkill}"     # z.B. "Klasse < 20 LOC"
max_scope: "{Wann Pattern nicht mehr traegt}"  # z.B. "Klasse > 5 Dependencies"
boundary_notes: []                 # Liste broken-Notizen (befuellt durch Pfad-2)
broken_count: 0                    # Incrementiert durch Pfad-2
broken_locations: []               # BL-154-PL-34 ARCH-H8: Strukturierte Bruchstellen
                                   # Format: [{file, class, reason, date}]
                                   # Jeder Pfad-2-Aufruf APPENDED einen Eintrag (APPEND-ONLY)

# Optionale Felder:
derived_from: null                 # PT-{LAYER}-{NR} bei Abwandlungen (Pfad-3)
variants: []                       # Backlinks auf Abwandlungen
hard_reference: null               # Optionaler Verweis auf ApplicationTrail_{ID}.md
seed: false                        # true = Bootstrap-Ursprung (_PT_arch_init)
last_used: null                    # Datum letzter Anwendung (Pfad-1)
status_promoted_at: null           # Datum letzter Status-Promotion
```

**Status-Lifecycle (BL-154, ADR-4 — UNTERSCHIED zu BL-153):**

| Status | Trigger | Mechanismus |
|--------|---------|-------------|
| `experimental` | Neuerstellung (Pfad-4) oder Abwandlung (Pfad-3) | `/_PT_update` / `/_PT_extract` |
| `active` | `usage_count >= 5` | Pfad-1 Auto-Upgrade |
| `PROVEN` | `usage_count >= 10` | Pfad-1 Auto-Upgrade |
| `deprecated` | `broken_count >= 3` (auto) ODER User-Entscheidung | Pfad-2 Auto / manuell |

**KRITISCH: BL-154 vs. BL-153 Unterschied:**
- BL-153 (semantisch): `draft/promoted/mature/deprecated` + `confidence`
- BL-154 (architektonisch): `experimental/active/PROVEN/deprecated` + `usage_count`
- Unterscheidung via Frontmatter `scope: architectural`

---

## Siehe auch

- [[_SC_implement]] - Schritt 1.5g: PT-TRIGGER-CHECK (Trigger fuer /_PT_update)
- [[_pattern-library]] - Bestehender Pattern-Katalog
- [[_pl-index]] - Pattern Library Index (Routing + Konsumenten)
- [[_Pre_PR_orchestrate]] - Battle-Test Gate fuer PROMOTION (W257)

---

ARGUMENTS: $ARGUMENTS
