---
type: building-block
---

# /_I_verify

**Status:** v1.0
**Actor:** VERIFIER
**Zweck:** SPEC ↔ Test Mapping - Tests sind die Wahrheit, nicht der Code

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_verify {SLICE_NAME|global}                      |
+===============================================================+
|                                                                |
|  KERN-PRINZIP:                                                 |
|    Tests lesen = Stufe 1 (Wahrheit)                            |
|    Code lesen  = Stufe 2 (nur bei Unklarheit)                  |
|    Tests sind leichter zu lesen als Code.                      |
|    Tests enthalten Beispiel-Daten und echte Szenarien.         |
|    Tests SIND die Dokumentation der Implementierung.           |
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. {VAULT}/_manifest.md                            |
|    2. .claude/CURRENT_SLICE.md (falls Mitose-Worktree)        |
|    3. PRIMAER: {VAULT}/.../Spec/{NAME}_Spec.md                 |
|       FALLBACK: .claude/specs/{NAME}_Spec.md                   |
|       → SOLL: AKs, Prozessschritte, Interfaces, Komponenten   |
|    4. {VAULT}/Task.md                                          |
|       → Akzeptanzkriterien                                     |
|                                                                |
|  LIEST (Input) - PER SLICE (BL-050 Vault-First PRIMAER/FALLBACK): |
|    5. PRIMAER: {VAULT}/.../Blueprint/{NAME}-{SLICE}-PLAN.md   |
|       FALLBACK: .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md  |
|       → Geplante Test-Liste                                    |
|    6. PRIMAER: {VAULT}/.../Implementation/{NAME}-ATOMIC-{SLICE}.md |
|       FALLBACK: .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md |
|       → Unit Test Ergebnisse                                   |
|    7. PRIMAER: {VAULT}/.../Implementation/{NAME}-INTEGRATION-{SLICE}.md |
|       FALLBACK: .claude/analysis/synthese/{NAME}-INTEGRATION-{SLICE}.md |
|       → Integration Test Ergebnisse                            |
|    8. PRIMAER: {VAULT}/.../Implementation/{NAME}-SYSTEM-{SLICE}.md |
|       FALLBACK: .claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md |
|       → System Test Ergebnisse                                 |
|                                                                |
|  LIEST (Input) - DIE WAHRHEIT (Stufe 1):                      |
|    9. Codebase: *Tests*.cs (Unit Tests)                        |
|   10. Codebase: *IntegrationTests*.cs (Integration Tests)      |
|   11. Codebase: *E2E*.cs / *.feature (System/E2E Tests)       |
|       → Test-Methoden, Assertions, Beispiel-Strings            |
|       → DAS ist die Dokumentation des Codes                    |
|                                                                |
|  LIEST (Input) - NUR BEI UNKLARHEIT (Stufe 2):                |
|   12. Codebase: Production Code                                |
|       → Nur wenn Test-Bedeutung unklar                         |
|                                                                |
|  LIEST (Input) - GLOBAL MODUS:                                 |
|   13. Alle VERIFY-{SLICE}.md (vorherige Slice-Verifikationen)  |
|   14. .claude/analysis/synthese/{NAME}-ARCHITECT.md            |
|       → Slice-Liste + Abhaengigkeiten                          |
|   15. .claude/evidence/*.md (optional)               |
|       → constraint-Evidence = intentionale Abweichung von      |
|         Standard-Pattern (kein FALSE GAP melden)               |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. Per-Slice:                                               |
|       PRIMAER:  {VAULT}/Backlog/{BL_SLUG}/Implementation/{NAME}-VERIFY-{SLICE}.md |
|       FALLBACK: .claude/analysis/synthese/{NAME}-VERIFY-{SLICE}.md |
|       Global:                                                  |
|       PRIMAER:  {VAULT}/Backlog/{BL_SLUG}/Implementation/{NAME}-VERIFY.md |
|       FALLBACK: .claude/analysis/synthese/{NAME}-VERIFY.md     |
|    2. {VAULT}/_manifest.md (aktualisieren)            |
|                                                                |
|  MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):               |
|    Pattern B: State-Write + Protokoll-Rollover                 |
|    SCHREIBT STATE: i_core_result YAML-Block (aktueller         |
|      I-Lauf), verify_status                                    |
|    SCHREIBT PROTOKOLL: Aeltere i_core_result Bloecke           |
|      (Prepend → _manifest_protokoll.md)                        |
|                                                                |
|  SCHREIBT (Output) - OPTIONAL:                                 |
|    {VAULT}/_parking-lot.md (APPEND - entdeckte Test-Luecken)   |
|    {VAULT}/.claude/wissen/pattern-usage.log (APPEND, R1):      |
|      Pro VERIFIED-Pattern EIN VERIFIED-Signal (Signal-Pfad,    |
|      BL-237 AK-CTX-R1, ADR-PL-008). KEIN lifecycle-Direkt-Call.|
|                                                                |
|  PIPELINE:                                                     |
|    Per Slice:                                                  |
|    [/_I_codeSystem] → [/_I_verify] → [SLICE VERIFIZIERT]      |
|                                                                |
|    Global (nach allen Slices):                                 |
|    [Alle Slices DONE] → [/_I_verify global] →                  |
|    [/_gap normal] → [/_model finish] → [Pre-PR]               |
|                                                                |
|  BEZIEHUNG ZU /_gap:                                           |
|    /_gap     = GAP-Code (SPEC vs Code/Model)                   |
|    /_I_verify = GAP-Test (SPEC vs Tests)                       |
|    BEIDE zusammen = vollstaendiges Bild                        |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**VERIFIER:** Mappt SPEC auf Tests. Entdeckt Test-Luecken auf allen Ebenen.

**TUT:** SPEC-Items extrahieren, Test-Dateien lesen (3 Schichten),
bidirektionales Mapping erstellen, Luecken identifizieren, Coverage quantifizieren.

**NICHT:** Code schreiben, Tests schreiben, Model updaten.
Code lesen NUR bei Unklarheit (Stufe 2).

**Eskalation:** Bei Coverage < 60% → Warnung. Bei fehlenden AK-Tests → Blocker.

---

## Zwei Modi

| Modus | Wann | Scope | Output |
|-------|------|-------|--------|
| **Slice** | Nach /_I_codeSystem | 1 Slice | VERIFY-{SLICE}.md |
| **Global** | Nach allen Slices | Gesamtes Feature | VERIFY.md |

---

## Schritt 0: Manifest + Modus

```
1. Lies _manifest.md → NAME, aktuelle Phase

2. Falls {SLICE_NAME} angegeben UND != "global":
   → Slice-Modus
   → Pruefe: SYSTEM-{SLICE}.md existiert mit status=final
   → Falls nicht: ABBRUCH "/_I_codeSystem {SLICE} muss zuerst abgeschlossen sein"

3. Falls "global":
   → Global-Modus
   → Pruefe: Alle Slices in ARCHITECT.md haben SYSTEM-*.md mit status=final
   → Falls nicht alle: WARNUNG "Slices {X,Y} noch nicht abgeschlossen"
   → Falls VERIFY-{SLICE}.md fuer abgeschlossene Slices vorhanden:
     → Nutze als Input (nicht nochmal Slice-Verify ausfuehren)

4. Falls CURRENT_SLICE.md existiert:
   → Slice-Modus mit Slice aus CURRENT_SLICE.md
```

---

## Schritt 0.5: verify_mode-Weiche (BL-276 AK-S5) — TDD ist nicht fuer jedes Artefakt das Werkzeug

```
# verify_mode stammt aus der Plan-/Stage-Datei (IDF Phase 7.7 testSearch:
# coverage_per_batch[sb].verify_mode) bzw. der Motor (dispatch_implement) reicht ihn im Worker-Prompt durch.
# Diskriminator: "kann das Ziel-Artefakt einen automatisierten RED-Zustand annehmen?". Fuer scenario/convention-
# Artefakte ist "0 pytest = MISSING/RED" ein FALSCH-Negativ — genau der J13-Fehlalarm 18:23 (_W_fetch.md als
# BLOCKED gewertet, weil ein Doku-Edit kein failing-test hat).
verify_mode = coverage_per_batch[current_sub_batch].verify_mode
            ?? worker_prompt.verify_mode          # der Motor reicht es im Prompt durch
            ?? "tdd"                                # Default: bestehendes Test-Discovery-Verhalten

IF verify_mode IN ["scenario", "convention"]:
  # KEIN Test-Discovery-MISSING. Belege ueber den artefakt-passenden Verify:
  #   scenario   → isolierter Szenario-A/B-Durchlauf (A = geaenderter Pfad greift, B = Counterfactual/Gegenfall).
  #                Halten beide das erwartete Verhalten → VERIFIED. (Formalisiert die J13-Szenario-Verify; deckt
  #                sich mit der bootstrap_direkt_szenario_verify-Methode dieser ganzen Session.)
  #   convention → Struktur-/Schema-/Lint-Assertions (valides Format, Pflicht-Felder, Konvention) → VERIFIED.
  Fuehre den {scenario|convention}-Verify gegen die Ziel-Datei(en) aus.
  Schreibe VERIFY-Report: coverage_kind="{verify_mode}", verdict=VERIFIED|GAP (NIE MISSING-wegen-0-Tests),
    begruendung="{Szenario-A/B-Ergebnis | Struktur-Assertion-Ergebnis}".
  → RETURN — die Schritte 1-4 (SPEC-Dekomposition + Test-Discovery) sind tdd-spezifisch und werden fuer
    dieses Artefakt NICHT gefahren (kein "kein Test gefunden = BLOCKED").

# verify_mode == "tdd" → weiter mit Schritt 1 + Schritt 2 (Test-Discovery) wie bisher.
```

---

## Schritt 1: SPEC-Dekomposition

```
Lies specs/{NAME}_Spec.md + Task.md und extrahiere ALLE verifizierbaren Items:

SPEC-ITEMS Tabelle aufbauen:

| ID | Typ | Beschreibung | Erwartete Schicht | Quelle |
|------|------|-------------|-------------------|--------|
| AK1 | Akzeptanzkriterium | {aus Task.md} | System | Task.md |
| P01 | Prozessschritt | {aus Spec §2} | Integration | Spec §2 |
| I01 | Interface | {aus Spec §3} | Integration | Spec §3 |
| D01 | DB-Schema | {aus Spec §5} | Unit+IT | Spec §5 |
| S01 | Security/Config | {aus Spec §9} | Unit+IT | Spec §9 |

SCHICHT-ZUORDNUNG (Erwartung):
  AKs                → primaer System/E2E Tests
  Prozessschritte    → primaer Integration Tests
  Interfaces         → Integration Tests
  Business Logic     → Unit Tests
  DB-Schema          → Unit + Integration Tests
  Security/Config    → alle Schichten moeglich
```

---

## Schritt 2: Test-Discovery (DIE WAHRHEIT)

### Stufe 1: Tests lesen (IMMER zuerst)

```
SCHICHT 1 - Unit Tests:
  Glob: Sources/Backend/**/*Tests*/**/*.cs (NICHT *IntegrationTests*)
  Fuer jeden relevanten Test:
    → Test-Methode Name (beschreibt Szenario)
    → Assertions (beschreibt Erwartung)
    → Arrange-Daten (Beispiel-Strings, Konfigurationswerte)
    → Mocks (zeigt Abhaengigkeiten und Boundaries)

SCHICHT 2 - Integration Tests:
  Glob: Sources/Backend/**/*IntegrationTests*/**/*.cs
  Fuer jeden relevanten Test:
    → Test-Setup (zeigt echte Infrastruktur)
    → HTTP-Calls / DB-Queries (zeigt echte Boundaries)
    → Beispiel-Daten (zeigt echte Szenarien)
    → Container-Setup (zeigt echte Umgebung)

SCHICHT 3 - System/E2E Tests:
  Glob: Sources/**/*E2E*/**/*.cs + Sources/**/*.feature
  Fuer jeden relevanten Test:
    → User Flow (Given/When/Then)
    → End-to-End Szenarien
```

### Stufe 2: Code lesen (NUR BEI UNKLARHEIT)

```
Falls ein Test nicht eindeutig einem SPEC-Item zuordenbar:
  → Production Code lesen um Kontext zu verstehen
  → DOKUMENTIERE im Report warum Stufe 2 noetig war
  → Ziel: Test-Bedeutung klaeren, NICHT Code analysieren
```

---

## Schritt 3: Bidirektionales Mapping

### Richtung 1: SPEC → Tests (Backward Verification)

```
Fuer JEDES SPEC-Item aus Schritt 1:
  → Finde Tests die dieses Item abdecken
  → Pruefe: Ist die erwartete Schicht abgedeckt?
  → Klassifiziere:

    COVERED:  Mindestens 1 Test in erwarteter Schicht
    PARTIAL:  Tests vorhanden, aber nicht in erwarteter Schicht
              (z.B. AK nur per Unit Test, kein System Test)
    MISSING:  Kein Test fuer dieses SPEC-Item
```

### Richtung 2: Tests → SPEC (Forward Verification)

```
Fuer JEDEN gefundenen Test:
  → Welchem SPEC-Item dient er?
  → Klassifiziere:

    MAPPED:  Test dient einem SPEC-Item (Primaer-Zweck)
    GUARD:   Regressions-Schutz (kein direktes SPEC-Item, aber wertvoll)
    ORPHAN:  Test ohne erkennbaren SPEC-Bezug (Waste?)
```

---

## Schritt 4: Coverage + Luecken

```
COVERAGE-MATRIX aufbauen:

| SPEC-Item | Beschreibung | Unit | Integration | System | Status |
|-----------|-------------|------|-------------|--------|--------|
| AK1 | {Beschr.} | - | IT3 | - | PARTIAL |
| P01 | {Beschr.} | - | IT1 | - | COVERED |
| D01 | {Beschr.} | T8,T9 | - | - | COVERED |

METRIKEN berechnen:
  SPEC-Items gesamt: {N}
  COVERED: {N} ({%})
  PARTIAL: {N} ({%})
  MISSING: {N} ({%})

  Tests gesamt: {N}
  MAPPED: {N} ({%})
  GUARD: {N} ({%})
  ORPHAN: {N} ({%})

GAP-TEST ITEMS (entdeckte Luecken):
  GT-01: {SPEC-Item} hat keinen {Schicht} Test → Empfehlung
  GT-02: ...

BLOCKER identifizieren:
  AK ohne JEDEN Test = BLOCKER fuer Pre-PR
  Kritischer Prozessschritt ohne IT = BLOCKER
```

---

## Schritt 5: VERIFY Report schreiben

### Per-Slice Output

Pfad: `.claude/analysis/synthese/{NAME}-VERIFY-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: verify
pipeline: implementation
status: final
spec_items_total: {N}
covered: {N}
partial: {N}
missing: {N}
coverage_percent: {N}
tests_mapped: {N}
tests_orphan: {N}
blocker: {N}
last_updated: {YYYY-MM-DD}
---

# Verify: {NAME} - {SLICE_NAME}

**Coverage:** {covered}/{total} ({%}) | **Partial:** {N} | **Missing:** {N}
**Tests:** {mapped} mapped, {orphan} orphan, {guard} guard
**Blocker:** {N}

## SPEC → Test Mapping

| SPEC-Item | Beschreibung | Unit | IT | System | Status |
|-----------|-------------|------|------|--------|--------|
| AK1 | ... | T1 | IT3 | - | PARTIAL |
| P01 | ... | - | IT1 | - | COVERED |

## Test → SPEC Mapping

| Test | Datei:Zeile | SPEC-Item | Typ |
|------|-------------|-----------|-----|
| SendFileAsync_Happy | Adapter:45 | P01, AK2 | MAPPED |
| RetryAsync_Transient | Adapter:123 | S01 | MAPPED |
| OldLegacyTest | Legacy:89 | - | GUARD |

## GAP-Test Items

| # | SPEC-Item | Fehlende Schicht | Empfehlung | Prio |
|---|-----------|------------------|------------|------|
| GT-01 | AK1 | System | E2E fuer Gesamtflow | HOCH |

## Zusammenfassung

{3-5 Saetze: Was gut abgedeckt, wo Luecken, Empfehlung}
```

### Global Output

Pfad: `.claude/analysis/synthese/{NAME}-VERIFY.md`

```markdown
---
name: {NAME}
phase: verify-global
pipeline: implementation
status: final
slices_verified: {N}
spec_items_total: {N}
covered: {N}
partial: {N}
missing: {N}
coverage_percent: {N}
blocker: {N}
last_updated: {YYYY-MM-DD}
---

# Verify Global: {NAME}

**Slices:** {N}/{N} verifiziert | **Coverage:** {%} | **Blocker:** {N}

## Slice-Uebersicht

| Slice | Items | Covered | Partial | Missing | Coverage |
|-------|-------|---------|---------|---------|----------|
| {S1} | {N} | {N} | {N} | {N} | {%} |
| **GESAMT** | **{N}** | **{N}** | **{N}** | **{N}** | **{%}** |

## Cross-Slice Analyse

{Ueberschneidungen, gemeinsame Tests, Luecken die nur global sichtbar sind}

## GAP-Test Gesamtliste

| # | Slice | SPEC-Item | Fehlende Schicht | Prio |
|---|-------|-----------|------------------|------|

## Blocker (MUSS vor Pre-PR)

{AKs ohne Tests, kritische Prozessschritte ohne Verification}

## Naechster Schritt

Falls BLOCKER > 0:
  → Zurueck zu /_I_codeAtomic / codeIntegration / codeSystem
Falls Coverage > 80% und BLOCKER = 0:
  → /_gap {NAME} normal (GAP-Code Re-Eval)
  → /_model {NAME} finish
  → Pre-PR
```

---

## Schritt 5.5: VERIFIED → pattern-usage.log Signal (BL-237 AK-CTX-R1, Signal-Pfad)

**Zweck (Counter-Feed R1):** Wenn die Verifikation ein Pattern als **erfolgreich angewandt**
bestaetigt (das SPEC→Test-Mapping deckt einen Pattern-bezogenen AK PASS ab), appendet `_I_verify`
EIN `VERIFIED`-Signal in `pattern-usage.log`. Das ist die Schreib-Seite des Reifungs-Loops
(`usage_count`): der Drain (R6b) hebt daraus spaeter idempotent den Counter.

**INVARIANTE (ADR-PL-008, BL-237 AK-CTX-R1 — Signal-Pfad, KEIN Direkt-Call):**
`_I_verify` ruft **NIEMALS** `pattern_library.lifecycle()` direkt auf und mutiert den Counter NICHT.
Es appendet ausschliesslich ein `VERIFIED`-Signal in den Log. Den `lifecycle --pfad 1`-Call macht
der EINE autorisierte Drain (`drain_usage_log`, R6b). Schreib-Vorbild: `_I_patternLibrary.md:339-343`
(KEIN_PATTERN-APPEND, gleiche Datei).

```
# NUR wenn ein Pattern nachweislich verifiziert wurde (PASS auf Pattern-bezogenem AK):
FÜR jedes pattern_id mit VERIFIED-Mapping-Status:
  Bash: py -3 .claude/scripts/pattern_library.py append-usage \
        --signal VERIFIED --pattern-id {pattern_id} --scope {arch|semantic} \
        --commit-sha {git rev-parse HEAD} --file-anchor {verifizierte Datei} \
        --note "VERIFIED via _I_verify ({SLICE})"
  # append_usage ist vault-resolved + append-lock-gated (R6a). KEIN lifecycle-Direkt-Call.
```

**Negativ-Klausel (explizit):** Ohne verifiziertes Pattern wird KEIN Signal geschrieben (kein
pauschales VERIFIED). Ein bloss bestandener Test ohne Pattern-Bezug ist KEIN `usage++`-Signal.

---

## Schritt 6: Manifest + Naechste Schritte

```
Manifest aktualisieren:
  PHASE: _I_verify {SLICE|global}
  VERIFY-COVERAGE: {%}
  GAP-TEST-ITEMS: {N}
  BLOCKER: {N}

Naechster Schritt:
  Falls Slice-Modus + Mitose-Worktree:
    → "WORKTREE VERIFIZIERT. Bereit fuer /_I_fanIn"

  Falls Slice-Modus + weitere Slices:
    → "/_I_codeAtomic {NEXT}" oder "/_I_verify {NEXT}" je nach Status

  Falls Slice-Modus + letzter Slice:
    → "/_I_verify global empfohlen"

  Falls Global-Modus + Blocker:
    → Blocker auflisten, zurueck in Pipeline

  Falls Global-Modus + kein Blocker:
    → "/_gap {NAME} normal (GAP-Code Re-Eval)"
    → "/_model {NAME} finish"
    → "Pre-PR wenn beides gruen"
```

---

## Beziehung zu /_gap (GAP-Code vs GAP-Test)

```
         SPEC (SOLL)
        /            \
       /              \
  /_gap              /_I_verify
  (GAP-Code)         (GAP-Test)
      |                   |
      v                   v
   CODE               TESTS
  "Stimmt der Code    "Sind alle SPEC-Items
   mit SPEC ueberein?" durch Tests belegt?"

/_gap     liest CODE und MODEL → findet Code-Luecken
/_I_verify liest TESTS         → findet Test-Luecken

BEIDE zusammen = vollstaendiges Bild vor Pre-PR
```

---

## Qualitaetskriterien

- Tests IMMER zuerst lesen (Stufe 1), Code NUR bei Unklarheit (Stufe 2)
- JEDES AK aus Task.md muss im Mapping erscheinen
- Bidirektional: SPEC→Tests UND Tests→SPEC
- Orphan-Tests dokumentieren (nicht loeschen, aber kennzeichnen)
- Guard-Tests als wertvoll anerkennen (Regressions-Schutz)
- Coverage quantifizierbar (Prozent, nicht subjektiv)
- Blocker klar definiert (AK ohne jeden Test = Blocker)
- Parking-Lot fuer entdeckte Luecken nutzen (APPEND)
- Manifest nach Verify aktuell
- KEINE Code-Aenderungen, KEINE Tests schreiben (nur analysieren)

---

## INV-PROCESS-STRICT-2 (Refactor-Form-Carve-Out) — BL-404

**Schwester-Invariante zu INV-PROCESS-STRICT (BL-174, No-Test-Tuning).** Gilt ausschliesslich
im Refactor-Kontext (`batch_type == "refactor"`, M2). Guard: `guard_test_tuning_detector.py` (AK-5, batch_2).

### Diskriminator (Kern-Trennkriterium)

Eine Test-Aenderung ist **legitim-Form (Kat. B / Form-gekoppelt)** ⟺ sie passt eine
FORM-Erwartung (Schwellwert / Name / Struktur / alte-Klassen-Instanziierung) bei
**nachweislich unveraendertem Verhalten** an.

Sie ist **verbotenes Korrektheits-Tuning (Kat. A / Korrektheits-Failure)**, sobald sie eine
VERHALTENS-Assertion (Output / State / Protokoll-Text / Error-Code / Object-Type-Vertrag /
Operations-Reihenfolge / Exception-Art) aufweicht.

**Konservativitaets-Regel — im Zweifel: Korrektheit (Kat. A) — Code fixen, Test unangetastet.**

### Vokabular-Tabelle

| Kategorie | Token-Set | Erlaubt im Refactor |
|-----------|-----------|---------------------|
| **Kat. A — Korrektheit (VERBOTEN zu aendern)** | `Output`, `State`, `Protokoll-Text`, `Error-Code`, `Object-Type-Vertrag`, `Operations-Reihenfolge`, `Exception-Art` | NEIN — Code fixen |
| **Kat. B — Form-gekoppelt (legitim, beweis-pflichtig)** | `alte-Klassen-Instanziierung`, `Schwellwert`, `umbenannter Symbol`, `reorganisierte Struktur` | JA — mit Einzelmeldung |

### Per-Failure-Einzelmeldung (AK-3 — nie still, nie gebuendelt)

Jede Kat.-B-Anpassung MUSS einzeln dokumentiert werden. **Gebundelte oder stille Anpassung
ist verboten.** Report-Eintrag pro Failure (Pflichtfelder):

| Feld | Inhalt |
|------|--------|
| `Test-Name` | Vollstaendiger Testname |
| `alte Form-Erwartung` | Alter Wert / alter Klassen-Name / alte Struktur |
| `neue Form-Erwartung` | Neuer Wert / neuer Klassen-Name / neue Struktur |
| `Begruendung` | "Verhalten unveraendert weil X" |

### AK-7 Diskriminator-Semantik-Review (BL-404) — markdown_uncoverable Review-Gate

**AK-7 Diskriminator-Semantik-Review (BL-404):** Kat-A ∩ Kat-B = ∅ (disjunkt), Trennkriterium
konservativ (im Zweifel Korrektheit), W2/W3-abgedeckt.

**Reviewer-Verdikt:** Die Vokabular-Listen sind disjunkt — kein Token erscheint in beiden
Kategorien. Kat.-A-Liste (7 Token: Output, State, Protokoll-Text, Error-Code, Object-Type-Vertrag,
Operations-Reihenfolge, Exception-Art) deckt alle Verhaltens-Marker aus W2 ab. Kat.-B-Liste
(4 Token: alte-Klassen-Instanziierung, Schwellwert, umbenannter Symbol, reorganisierte Struktur)
deckt alle Form-Marker aus W2 ab. Konservativitaets-Regel "im Zweifel → Kat. A (Korrektheit)"
ist load-bearing verankert (Schritt 2 der 3-Fragen-Checkliste: unklar → wie Kat. A behandeln).
**Keine Luecke / Ueberschneidung gefunden. Verdikt: PASS.**

### AK-6 Heuristik-Grenze-Disclaimer (BL-404) — Reviewer-Pflicht, kein false-GREEN-Versteck

**Guard-Referenz:** `guard_test_tuning_detector.py` (BL-404 AK-5, PreToolUse-Hook).

**Heuristik-Grenze:** Der Guard ist **heuristisch (Vokabular-basiert)** — er ersetzt NICHT das
Reviewer-Urteil zur "Verhalten unverändert"-Frage (Schritt 2 des Diskriminators). Er verschiebt
die Beweis-Last (Kat.-A-Verdacht → Stop/Report), aber **faengt nicht jeden Umgehungsversuch**:
ein Token-getarntes Behavior-Tuning (Assertion mit Form-Vokabular umgeschrieben, z. B.
`OldClass`-Referenz statt Output-Wert geaendert, aber implizit Verhalten aufgeweicht) **kann
durchrutschen**. Diese Restluecke ist strukturell nicht mechanisch schliessbar
(markdown_uncoverable, BL-314). **Konsequenz: Der Reviewer bleibt Pflicht** — Guard-PASS ≠
inhaltliche Freigabe fuer Kat.-B. Jede Kat.-B-Anpassung erfordert das menschliche Urteil
"Verhalten nachweislich unverändert" (Schritt 2, W3).

---

## Twin-Diff Pflicht-Gate (BL-308)

**Zweck:** Deterministisches Referenz-Konformanz-Gate, das VOR BATCH_DONE prueft, ob eine
Implementierung gegen ihre Referenz-(Twin-)Datei konform ist — wenn das Item ein `twin_ref`-Signal
traegt (`IS-IDENTICAL` oder `IS-ADAPTED`). Faengt stille Drift frueh; kein nachgelagertes Audit noetig.

### AK-1 Verifier-Branch — twin_diff_gate konsultieren

`_I_verify` konsultiert **vor dem BATCH_DONE-Signal** die Funktion `twin_diff_gate` aus
`.claude/scripts/twin_diff.py`:

```python
from twin_diff import twin_diff_gate, conformance_diff, twin_path

gate_result = twin_diff_gate(
    actual=actual_anchors,       # Anker der Implementierung
    reference=reference_anchors, # Anker der Twin-Datei
    twin_available=twin_available,
)
# gate_result: { 'pass': bool, 'deviations': list, 'verdict': 'PASS'|'FAIL'|'SKIPPED' }
```

**Verzweigung nach `item.twin_ref`:**

| twin_ref-Wert | Twin-Sub-Achse | Bemerkung |
|---|---|---|
| `IS-IDENTICAL` | FEUERT | Anker-Mengen-Diff gegen Twin; kein Rest-Delta erlaubt |
| `IS-ADAPTED` | FEUERT | Abweichungen muessen in `{bl}/Twin/deviations.md` deklariert sein |
| `IS-NEW` | SKIP | Kein Twin vorhanden; kein Befund-Block |
| `null` / fehlend | SKIP | Proportionalitaet — twin-loser Pfad unveraendert |

Bei `verdict=FAIL` (undeklariete Abweichung): BATCH_DONE wird blockiert; der Befund
(`twin_conflict`) wird analog dem BL-303-L1-`test_conflict`-Kanal an den Motor
(`dispatch_implement.js`) zurueckgegeben → `loop_decision: 'RE-BATCH'`.

### AK-2 Verdikt-Matrix

**Verdikt-Matrix** (twin_diff_gate-Ergebnis in Abhaengigkeit von conformant x twin_available):

| conformant (Diff-Ergebnis) | twin_available | twin_ref | Verdikt |
|---|---|---|---|
| true | true | IS-IDENTICAL / IS-ADAPTED | PASS (GREEN) |
| false | true | IS-IDENTICAL | FAIL (BLOCK) |
| false + deklariert | true | IS-ADAPTED | PASS (deklarierte Deviation) |
| false + nicht deklariert | true | IS-ADAPTED | FAIL (UNDECLARED_DEVIATION, BLOCK) |
| — | false | beliebig | graceful PASS (SKIPPED) |

Die Funktion `twin_diff_gate(actual, reference, twin_available)` gibt zurueck:
`{ 'pass': bool, 'deviations': list, 'verdict': 'PASS'|'FAIL'|'SKIPPED' }`.

### AK-6 Proportionalitaet — graceful PASS bei twin_available=false

Wenn `twin_available=false` (IS-NEW / null / fehlend), liefert `twin_diff_gate` sofort einen
**graceful** PASS ohne Anker-Vergleich — kein Block, kein zusaetzlicher Step, keine veraenderte
Laufzeit gegenueber dem Pre-BL-308-Pfad:

```python
# aus twin_diff.py twin_diff_gate():
if not twin_available:
    return { "pass": True, "deviations": [], "verdict": "PASS" }  # graceful
```

twin_available=false bedeutet: das Item hat keinen Twin → Gate greift nicht (Proportionalitaet, AK-6).

### AK-12 twin_conformance STATE-Block

Der Twin-Befund wird als **eigener, paralleler** `twin_conformance`-STATE-Block neben
`i_core_result` im Manifest gefuehrt — NICHT als Ueberschreibung des Coverage-/Test-Verdikts
(Orthogonalitaet: `i_core_result.verdict` VERIFIED|GAP bleibt unveraendert).

```yaml
twin_conformance:
  twin_ref: IS-IDENTICAL|IS-ADAPTED|IS-NEW
  anchors:
    - { anchor: <id>, classification: PASS|UNDECLARED_DEVIATION|DECLARED_DEVIATION }
  verdict: GREEN|BLOCK|SKIPPED
```

Felder: `twin_ref` (Wert aus Plan-/PL-Item), `anchors` (pro geprueftem Anker mit
Klassifikation), `verdict` (Aggregat: jede UNDECLARED_DEVIATION → BLOCK).
Kein freier Prosa-Marker; maschinenlesbar fuer den Motor.

Deklarierte IS-ADAPTED-Abweichungen werden in `{bl}/Twin/deviations.md` auditierbar
gespeichert (5 Pflicht-Felder: anchor, expected, actual, begruendung, p12_backlink).
Der Ordner-Typ `{bl}/Twin/` ist analog `Crumbs/`, `2_Model/` (Per-BL-Folder-Konvention, AK-13).
Pfad-Bildung: `twin_path(bl_folder)` aus `.claude/scripts/twin_diff.py` (gibt `{bl_folder}/Twin/`).

### AK-14 Abgrenzung: Konformanz vs Korrektheit vs Audit

**Twin-Diff prueft Referenz-Konformanz** (diese konkrete Twin-Datei), NICHT abstrakte
Library-Patterns. Drei Dimensionen sind klar getrennt:

| Dimension | Werkzeug | Was wird geprueft |
|---|---|---|
| **Konformanz** (Twin-Diff) | `twin_diff_gate` (BL-308) | Konkrete Referenz-Datei: Anker-Mengen-Identitaet gegen die Twin-Datei (modulo Substitutions-Map) |
| **Korrektheit** (TDD-Tests) | `/_I_codeAtomic` → `pytest` / `dotnet test` | Verhaltens-Assertions: Output, State, Protokoll-Text, Error-Code — ob der Code das Richtige tut |
| **Pattern-Conformance** | `_PostBatch_PatternConformance` / `_SL_conformance` | Abstrakte Library-Patterns (andere Dimension: Pattern vs Datei) |
| **Nachgelagertes Audit** | `/_R_orchestrate` | Post-hoc manuell — wird durch das Gate ersetzt, nicht erganzt |

Korrektheit (TDD) und Konformanz (Twin-Diff) sind orthogonal: ein Test kann GREEN (korrekt)
sein und trotzdem einen Twin-BLOCK erzeugen (Struktur-Drift). Das Gate ordnet sich als
billige Stufe UNTER E2E in die Test-Pyramide ein (P-08) — kein E2E-Ersatz.
Kein Code-Pfad-Re-Use von `_PostBatch_PatternConformance`-Verdikt-Logik.

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_verify abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
