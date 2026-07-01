---
status: active
version: 1.0.0
created: 2026-03-12
op: FeatureFinish
phase: Verification
type: building-block
chain_position: pre-finish
team_based: false
---

# /_smoothing — Final-Verification vor Feature-Abschluss

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_smoothing                                               ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST — Vault-First (BL-050):                                       ║
║    $spec_input           (Pflicht: Spec-Text, Dateipfade, AK)       ║
║    PRIMAER: {VAULT}/.../Model/{FEATURE}_Model.md (Feature-Kontext)  ║
║      FALLBACK: .claude/models/{FEATURE}_Model.md                    ║
║    .claude/evidence/*.md                    (bestehende Evidence)    ║
║    PRIMAER: {VAULT}/.../Crumbs/{FEATURE}_crumbs.md (Kruemmel)      ║
║      FALLBACK: .claude/crumbs/{FEATURE}_crumbs.md                   ║
║    .claude/pileOfMud/*.md                   (Case Studies, optional) ║
║    {VAULT}/_manifest.md            (Feature-Name, Phase)    ║
║    git diff develop...HEAD --name-only      (geaenderte Dateien)    ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/analysis/SMOOTHING-{FEATURE}-{DATE}.md  (Report)         ║
║                                                                      ║
║  AUSGABEN:                                                           ║
║    Traceability Matrix (Spec-Feld → Code → DB → Test)               ║
║    AK-Coverage Report (welche AK in welchem Test)                    ║
║    Findings (Luecken, Abweichungen, Stille-Post-Verluste)           ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    NIE Code aendern (Verification-only)                              ║
║    NIE Tests aendern (nur pruefen ob sie da sind)                   ║
║    NIE Team spawnen (Solo-Command)                                   ║
║    IMMER User fragen wenn Spec unklar                               ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

```
+======================================================================+
| COMMAND: /_smoothing                                                  |
+======================================================================+
|                                                                      |
| ACTOR: DU (direkt, kein Worker-Spawn)                               |
|                                                                      |
| ZWECK: Stille-Post-Schutz — Feincheck ob das Gebaute mit dem       |
|   Geforderten uebereinstimmt. Nicht "ist der Code sauber?"          |
|   (das macht /_Pre_PR) sondern "haben wir das Richtige gebaut?"    |
|                                                                      |
| WANN:                                                                |
|   - NACH /_Pre_PR (Code ist sauber) und VOR /_finish               |
|   - NACH /_AC_orchestrate (Architektur ist korrekt)                 |
|   - Wenn ein Feature mehrere Sessions/Worktrees durchlaufen hat    |
|   - Wenn zwischen Spec und Implementierung viele Tage lagen        |
|   - IMMER wenn der User "smoothing" oder "final check" sagt        |
|                                                                      |
| PIPELINE-POSITION:                                                   |
|   /_I_orchestrate → /_DiffReduce → /_AC_orchestrate →              |
|   /_Pre_PR → **/_smoothing** → /_finish                            |
|                                                                      |
| ABGRENZUNG:                                                         |
|   /_Pre_PR        = "Ist der Code sauber?" (9 Quality Gates)       |
|   /_AC_orchestrate = "Ist die Architektur korrekt?"                 |
|   /_DiffReduce    = "Ist alles noetig? Aligned mit Spec?"          |
|   /_smoothing     = "Haben wir gebaut was gefordert wurde?"        |
|   /_finish        = "Feature sauber abschliessen"                   |
+======================================================================+
```

---

## Aufruf

```
/_smoothing [FEATURE] [--spec "text oder pfad"] [--ak "AK-Liste"]
```

**Parameter:**

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `FEATURE` | aus _manifest.md | z.B. "DCSRE-882" |
| `--spec` | (optional) | Spec-Text direkt oder Dateipfad. Kann auch im Chat nachgeliefert werden. |
| `--ak` | (optional) | Akzeptanzkriterien-Liste. Wenn nicht gegeben: aus Model/Spec extrahieren. |

**Beispiele:**
```
/_smoothing DCSRE-882
/_smoothing DCSRE-882 --spec "EM0012: Richtung E/A, IkEmpfaenger, DicPackageId"
/_smoothing   (Feature aus Manifest)
```

---

## ABLAUF (Solo — kein Worker-Spawn)

### Schritt 1: Kontext laden

Sammle alle verfuegbaren Informationen zum Feature:

```
1. _manifest.md → FEATURE-Name, Phase, Coverage
2. PRIMAER: {VAULT}/.../Model/{FEATURE}_Model.md → W{n} Wahrheiten, Ziel-Architektur
   FALLBACK: .claude/models/{FEATURE}_Model.md
3. .claude/evidence/*.md → bestehende Entscheidungen/Constraints
4. PRIMAER: {VAULT}/.../Crumbs/{FEATURE}_crumbs.md → gesammelte Kruemmel vom User
   FALLBACK: .claude/crumbs/{FEATURE}_crumbs.md
5. git diff develop...HEAD --name-only → geaenderte Dateien
```

Falls `--spec` gegeben: Spec-Text als primaere Quelle verwenden.
Falls NICHT gegeben: Spec aus Model + Crumbs + Evidence extrahieren.

**Wenn kein ausreichender Spec-Kontext vorhanden:**
→ User fragen: "Was waren die Anforderungen fuer {FEATURE}? (Felder, AK, Verhalten)"

### Schritt 2: Anforderungen extrahieren

Aus dem gesammelten Kontext extrahiere:

**2a. Daten-Anforderungen (Felder/Spalten):**
```
Fuer jedes geforderte Feld:
  - Name (aus Spec)
  - Typ (S=System, M=Manuell, optional)
  - Quelle (woher kommt der Wert?)
  - Erwartetes Mapping (wie heisst es im Code/DB?)
```

**2b. Akzeptanzkriterien (AK):**
```
Fuer jedes AK:
  - AK-ID (AK1, AK2, ...)
  - Beschreibung (Was muss gelten?)
  - Testbar? (Kann man einen Assert dafuer schreiben?)
```

**2c. Verhaltens-Anforderungen:**
```
  - Flows (z.B. SOAP-Abruf → SFTP-Download → S3-Upload → DB-Finalize)
  - Edge Cases (z.B. Duplikate, Fehler, Retry)
  - Konfiguration (z.B. IK aus Config statt hardcoded)
```

### Schritt 3: Traceability Matrix bauen

Fuer jede Daten-Anforderung pruefe die Kette:

```
SPEC-FELD → CODE (Entity/DTO/Mapping) → DB (Migration/TableDef) → TEST (Assert)
```

**Algorithmus:**
```
Fuer jedes Spec-Feld:
  1. Suche im Code: Entity-Property, DTO-Property, Mapping
     → Grep in geaenderten Dateien (git diff develop...HEAD)
  2. Suche in DB-Schema: TableDefinition, Migration
     → Grep nach Spaltenname in TableDefinitions/ und Migrations/
  3. Suche in Tests: Assert-Statement das dieses Feld prueft
     → Grep in IntegrationTests/ und UnitTests/
  4. Bewerte: COVERED | PARTIAL | MISSING | ABWEICHUNG
```

**Output-Format (Tabelle):**
```markdown
| Spec-Feld | Code (Entity) | DB (TableDef) | Test (Assert) | Status |
|-----------|---------------|---------------|---------------|--------|
| Richtung  | DicFileImportEntity.Richtung | ColumnNameRichtung | Assert.Equal(Eingang, ...) | ✅ COVERED |
| IkEmpfaenger | DicFileImportEntity.IkEmpfaenger | ColumnNameIkEmpfaenger | Assert.Equal(Expected, ...) | ✅ COVERED |
| LastUpdatedAt | LastModifiedAt | ColumnNameLastModifiedAt | — | ⚠️ ABWEICHUNG (Name) |
```

### Schritt 4: AK-Coverage pruefen

Fuer jedes Akzeptanzkriterium pruefe:

```
Fuer jedes AK:
  1. Gibt es einen Integration Test der dieses AK prueft?
     → Grep nach Assert-Statements die das AK-Verhalten testen
  2. Gibt es einen Unit Test dafuer?
  3. Ist das AK nur manuell testbar? (z.B. UI-Verhalten)
  4. Bewerte: INTEGRATION | UNIT | MANUAL | MISSING
```

**Output-Format:**
```markdown
| AK | Beschreibung | Integration Test | Unit Test | Status |
|----|-------------|-----------------|-----------|--------|
| AK1 | Richtung = Eingang | T3_MetaDaten_DbFields:239 | — | ✅ INTEGRATION |
| AK2 | IkEmpfaenger aus Config | T3_MetaDaten_DbFields:242 | — | ✅ INTEGRATION |
| AK3 | DicPackageId = DicFileId | T3_MetaDaten_DbFields:245 | — | ✅ INTEGRATION |
```

### Schritt 5: Findings & Stille-Post-Check

Pruefe auf typische Stille-Post-Verluste:

**SP-1: Naming-Drift**
Spec sagt "LastUpdatedAt" aber Code heisst "LastModifiedAt".
→ Ist das bewusst (Evidence vorhanden?) oder versehentlich?

**SP-2: Fehlende Felder**
Spec-Feld hat kein Gegenstueck im Code.
→ Vergessen oder bewusst ausgelassen (Evidence/Parking-Lot)?

**SP-3: Ueberschuessige Felder**
Code hat Felder die nicht in der Spec stehen.
→ Scope-Creep oder sinnvolle Ergaenzung?

**SP-4: Test-Luecken**
AK ohne Test-Abdeckung.
→ War das AK testbar? Wurde es vergessen?

**SP-5: Config vs. Hardcoded**
Spec sagt "konfigurierbar" aber Code hat Hardcoded-Wert.
→ Wurde eine DicImportConfiguration o.ae. erstellt?

**SP-6: Skip-Tests mit Feature-Bezug**
Tests mit `[Fact(Skip = "...")]` die auf dieses Feature verweisen.
→ Sind die Skips berechtigt? Gibt es ein Folge-Ticket?

### Schritt 6: Report schreiben

**Dateiname:** `SMOOTHING-{FEATURE}-{DATE}.md`
**Speicherort:** `.claude/analysis/`

```markdown
---
feature: '{FEATURE}'
date: {DATE}
status: PASS | FINDINGS | FAIL
spec_coverage: {N}/{M} Felder
ak_coverage: {N}/{M} AK
findings_count: {N}
---

# Smoothing Report: {FEATURE}

**Datum:** {DATE}
**Spec-Coverage:** {N}/{M} Felder abgedeckt
**AK-Coverage:** {N}/{M} Akzeptanzkriterien in Tests
**Findings:** {N} (davon {kritisch} kritisch)

---

## Traceability Matrix

{Tabelle aus Schritt 3}

## AK-Coverage

{Tabelle aus Schritt 4}

## Findings

{Findings aus Schritt 5, sortiert nach Severity}

## Fazit

{1-3 Saetze: Feature-Status, offene Punkte, Empfehlung}
```

### Schritt 7: Ergebnis ausgeben

```
✅ Smoothing Report: .claude/analysis/SMOOTHING-{FEATURE}-{DATE}.md

Spec-Coverage: {N}/{M} Felder ({%})
AK-Coverage:   {N}/{M} AK in Tests ({%})
Findings:      {N} ({kritisch} kritisch, {warn} Warnungen)

{Falls FINDINGS oder FAIL:}
⚠️ Offene Punkte:
  - {Finding 1}
  - {Finding 2}

{Falls PASS:}
✅ Feature ready fuer /_finish
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Kein Spec-Kontext vorhanden | User interaktiv fragen |
| Feature nicht ermittelbar | User nach Feature-Name fragen |
| Keine geaenderten Dateien (git diff leer) | Warnung, trotzdem mit vorhandenen Infos pruefen |
| Integration Tests nicht gefunden | AK-Status als MANUAL markieren, nicht als FAIL |
| Model nicht vorhanden | Ohne Model-Kontext arbeiten, Warnung |

---

## Case Study: DCSRE-882 MetaDaten

**Referenz-Durchlauf** (manuell durchgefuehrt am 2026-03-12):

**Input:** EM0012 Spec (10 Felder), Version1.cs, Integration Tests

**Traceability Matrix Ergebnis:**
```
10/10 Felder: COVERED
3 neue Felder (DCSRE-882): Richtung, IkEmpfaenger, DicPackageId
1 Naming-Abweichung: LastUpdatedAt → LastModifiedAt (pre-existing)
```

**AK-Coverage Ergebnis:**
```
4/4 AK: INTEGRATION (T2_MetaDaten_NewFields + T3_MetaDaten_DbFields)
AK1: Richtung = Eingang ← Assert.Equal(DicRichtung.Eingang, ...)
AK2: IkEmpfaenger aus Config ← Assert.Equal(ExpectedIkEmpfaenger, ...)
AK3: DicPackageId = DicFileId ← Assert.Equal(uploadedFileId.ToString(), ...)
AK4: Status = Abgerufen ← Assert.Equal(DicFileImportStatus.Abgerufen, ...)
```

**Manuelle E2E Validierung:**
```
7 DB-Rows (3 geseedet + 4 manuell hochgeladen)
SOAP + SFTP → DB: Alle Felder korrekt befuellt
FileName-Strip: RSN-Prefix korrekt entfernt
```

**Ergebnis:** PASS (10/10 Felder, 4/4 AK, 0 kritische Findings)
