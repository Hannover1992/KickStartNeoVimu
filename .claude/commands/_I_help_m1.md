---
type: satellite
status: active
version: 1.0.0
created: 2026-05-10
related_bl: BL-174
companion_skill: _I_help (vollstaendige I-Pipeline)
---

# /_I_help_m1 — M1 Skelett-Modus Hilfe

Zeige Uebersicht und Vertrag des **M1-Skelett-Modus** im I-Pipeline-Subset.
Companion zu `/_I_help` (volle I-Pipeline). M1 ist die kondensierte Variante fuer
**triviale, templated Aufgaben** mit 1:1-Sister-Pattern.

## Aufruf

```
/_I_help_m1
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
+=========================================================================+
|  M1 SKELETT-MODUS (BL-174 reaktiviert 2026-05-10)                       |
|                                                                         |
|  M1 = Bare-Minimum I-Pipeline-Subset fuer triviale, templated Aufgaben |
|  Beispiel: Konstanten-Klasse 1:1-aequivalent zur Schwester-Story        |
|  (z.B. ValidationConstantsQDVTP <- ValidationConstantsQDVS)             |
|                                                                         |
|  ───────────────────────────────────────────────────────────────────    |
|  KONFORMITAET-vs-GESCHWINDIGKEIT BALANCE                                |
|  ───────────────────────────────────────────────────────────────────    |
|                                                                         |
|  Gegen Vollpipeline (M2/M3):                                            |
|    ~6× weniger Tokens   (~80k vs ~500k)                                 |
|    ~6× schneller        (~5-10min vs ~60min)                            |
|    1 Worker-Spawn statt 10+                                             |
|                                                                         |
|  Konformitaets-Erhalt:                                                  |
|    INV-PM-1 ABSOLUT — Worker-Spawn pflicht (kein Lead-inline-commit)    |
|    Vault-Schreib-Trail erhalten                                         |
|    Sister-Story-Coherence durch 3 Pflicht-Lookups                       |
|                                                                         |
+=========================================================================+
```

---

## TRIGGER-CRITERIA (4 UND-Verknuepft)

M1 wird ausschliesslich getriggert wenn ALLE 4 Bedingungen matchen
(siehe `_SDF_berater_modusEntscheidung.md` SCHRITT 1.5):

```
+=========================================================================+
|  M1-TRIGGER (BL-174):                                                   |
|                                                                         |
|    items_count        == 1                                              |
|  ∧ stages_for_batch   == [1]            (nur Stage 1 Unit)              |
|  ∧ layers_for_batch   ⊆  ["BE-CORE"]    (nur Konstanten/Enums)          |
|  ∧ has_template       == true           (1:1-Sister-Pattern verfuegbar) |
|                                                                         |
|  Falls einer FAIL → Eskalation zu M2 (volle Pipeline)                   |
+=========================================================================+
```

**Begruendung 4-fach UND:** Restriktiv preventiert Pragmatismus-Falle (DCSRE-1430-Risiko).
"Sind nur die einfachsten Aufgaben vorgesehen" (User-Direktive 2026-05-10).

---

## VERHALTENS-VERTRAG (Volles Bild)

```
+=========================================================================+
| Aspekt                | M1-Verhalten                                    |
+-----------------------+-------------------------------------------------+
| Team-Setup            | NEIN (--worker-mode → SKIP TeamCreate/Delete,   |
|                       |       nutze sc-{NAME})                          |
|                       |                                                 |
| Worker-Spawn          | JA — IMMER (INV-PM-1 ABSOLUT)                   |
|                       |                                                 |
| Worker-Anzahl         | 1 Worker (Variante 1, sequenziell)              |
|                       |   2-Worker-Tier-Mix verworfen                   |
|                       |   (Haiku-Trust noch nicht etabliert)            |
|                       |                                                 |
| Worker-Tier           | sonnet                                          |
|                       |   NICHT haiku (User-Trust-Signal)               |
|                       |   NICHT opus (kein Reasoning noetig)            |
|                       |                                                 |
| Skill-Aufruf          | Skill(_I_orchestrate, args=                     |
|                       |   "{NAME} --worker-mode --scope=skeleton        |
|                       |    --batch={AK} --stage=1 --tdd=false")         |
|                       |                                                 |
| Pflicht-Steps (4)     | 1. _I_architecturalLibrary  (architect)         |
|                       | 2. _I_patternLibrary        (architectural pat) |
|                       | 3. semanticLibrary lookup   (naming/semantic)   |
|                       | 4. _I_codeAtomic            (bare-min impl)     |
|                       |                                                 |
| Skip-Steps            | _I_requirementCheck                             |
|                       | _I_testSearch                                   |
|                       | _I_goldDefine                                   |
|                       | _I_blueprintQG                                  |
|                       | Stufen-Loop S1..S5 (nur Stage 1)                |
|                       | _I_mitose / _I_fanOut / _I_fanIn                |
|                       | TDD-Phase (kein Test-Bedarf bei Konstanten)     |
|                       |                                                 |
| Sequential vs Parallel| sequenziell innerhalb 1 Worker                  |
|                       |   3 Lookups parallel = Overhead nicht wert      |
|                       |   bei ~30LOC trivial                            |
|                       |                                                 |
| Vault-Schreib-Trail   | PFLICHT                                         |
|                       |   BERATER_OUTPUTS pro Step                      |
|                       |   Audit-Spawn-Eintrag                           |
|                       |                                                 |
| HiL-Verhalten         | unveraendert (=phase / cycle / off)             |
|                       |   Kein M1-Sonder-HiL                            |
|                       |                                                 |
| TDD                   | NEIN — tdd_flag=false                           |
|                       |   BE-CORE Konstanten haben keine Logik          |
|                       |                                                 |
| Pipeline-Route        | A_I (gleich wie M2/M3) + scope_mode="skeleton"  |
|                       |                                                 |
| Zeit/Token-Budget     | ~5-10min, ~80k tokens                           |
|                       |   6× billiger als Vollpipeline                  |
+-----------------------+-------------------------------------------------+
```

---

## END-TO-END-FLUSS (Beispiel: ValidationConstantsQDVTP)

```
+=========================================================================+
|  SDF Phase 1.1 (modusEntscheidung)                                      |
|    SCHRITT 1.5: M1-Check → 4-UND TRUE                                   |
|    → gewaehlter_modus="M1"                                              |
|    SCHRITT 9 SWITCH:                                                    |
|      pipeline_route = "A_I"                                             |
|      sc_mode        = null                                              |
|      scope_mode     = "skeleton"        ← NEU BL-174                    |
|      tdd_flag       = false                                             |
|                                                                         |
|  SDF Phase 2 Dispatch:                                                  |
|    Skill(_I_orchestrate, args=                                          |
|      "DCSRE-486 --worker-mode --scope=skeleton                          |
|       --batch=AK-CTX-2 --stage=1 --tdd=false")                          |
|                                                                         |
|  I_orchestrate Worker (1 Worker, sonnet):                               |
|    Step 1: architecturalLibrary lookup                                  |
|              → Layer=BE-CORE, ARCH-VERTRAG-Block A1                     |
|              → "ValidationConstantsQDVTP 1:1 Schwester                  |
|                 zu ValidationConstantsQDVS.cs"                          |
|    Step 2: patternLibrary lookup                                        |
|              → PT-CORE-Constants Pattern (falls vorhanden)              |
|              → MinMax-Boundaries fuer Konstanten-Files                  |
|    Step 3: semanticLibrary lookup                                       |
|              → Naming-Konvention QDVS→QDVTP                             |
|              → Namespace-Mapping                                        |
|    Step 4: codeAtomic                                                   |
|              → ValidationConstantsQDVTP.cs schreiben (~30 LOC)          |
|              → BERATER_OUTPUTS persistieren                             |
|              → Vault-Write Audit-Spawn                                  |
|                                                                         |
|  SDF Phase 3 (recalibrate / postBatch / statusTransition / modelSync)   |
|    unveraendert wie bei M2/M3                                           |
|                                                                         |
|  → batch_X DONE, naechster Batch (oft M2/M3 mit voller Pipeline)        |
+=========================================================================+
```

---

## VERGLEICH MATRIX (M1 vs M2/M3)

```
+========================+============+============+============+
| Aspekt                 | M1         | M2         | M3         |
+========================+============+============+============+
| Worker-Mode-Flag       | true       | false      | false      |
| Scope-Mode             | skeleton   | full       | full       |
| TDD                    | nein       | nein       | JA         |
| Stufen-Loop S1..S5     | SKIP       | komplett   | komplett   |
| Blueprint-Phase        | nur 3      | komplett   | komplett   |
| testSearch             | SKIP       | aktiv      | aktiv      |
| goldDefine             | SKIP       | aktiv      | aktiv      |
| blueprintQG            | SKIP       | aktiv      | aktiv      |
| mitose / fanOut/fanIn  | SKIP       | bei sliced | bei sliced |
| Tier (typisch)         | sonnet     | sonnet     | opus/sonnet|
| Token-Budget           | ~80k       | ~300-500k  | ~500k-800k |
| Wall-Clock             | 5-10min    | 30-60min   | 45-90min   |
+========================+============+============+============+
```

---

## INVARIANTEN

| ID | Invariante | Bedeutung |
|----|-----------|-----------|
| INV-MODUS-9 | M1-Strict-Trigger | 4-UND-Bedingungen: items=1 ∧ stages=[1] ∧ Layer⊆BE-CORE ∧ has_template=true |
| INV-PM-1 | Worker-Pflicht ABSOLUT auch bei M1 | Lead-Self-Inline NICHT zulaessig (User-Direktive 2026-05-10) |
| INV-PROCESS-STRICT | M2/M3 unveraendert strict | M1-Lockerung kompensiert durch M2/M3-Knochenhart |
| BL-174 SWITCH-Eintrag | M1 in modusEntscheidung Schritt 9 | scope_mode="skeleton" + worker_mode-Pfad in I_orchestrate |

---

## OFFENE FOLGE-PATCHES (Stand 2026-05-10)

| ID | Status | Beschreibung |
|----|--------|-------------|
| F2 | offen (PL/BL) | architecturalBrief-Vertrag muss `confidence` + `sister_story_link` Felder schreiben — sonst kann `has_template=true` strukturell nie erreicht werden |
| F3 | DONE 2026-05-10 | modusEntscheidung Skill SCHRITT 9 SWITCH M1-Eintrag + Schritt 1.5 Begruendungs-Template |
| F3-Folge | offen | `_I_orchestrate.md` muss `--scope=skeleton` Argument erkennen + Step-Subset-Routing implementieren (sonst laeuft Worker volle Pipeline trotz Flag) |

---

## REFERENZEN

| Quelle | Bedeutung |
|--------|-----------|
| BL-174 | M1 Reaktivierung 2026-05-10 (User-Direktive) |
| `_SDF_berater_modusEntscheidung.md` SCHRITT 1.5 | M1-Trigger-Logik |
| `_SDF_berater_modusEntscheidung.md` SCHRITT 9 SWITCH | M1 Pipeline-Mapping |
| `_I_orchestrate.md` Z381+391 | --worker-mode Flag (existiert) |
| `_I_help.md` | Vollstaendige I-Pipeline (Companion) |
| Audit_Dynamic_Live_DCSRE-486_2026-05-10.md | Live-Run Validierung F1-F3 |
| User-Direktive 2026-05-10 | "Handschuh-Wechsel und immer I_orchestrate. Bare-Minimum mit 3-4 Pflicht-Steps. Variante 1 (1-Worker). Sonnet, kein Haiku-Trust." |

---

*M1 ist die schmaler Pfad — schnell aber NICHT slordig. Konformitaet bleibt durch Worker-Pflicht
und 3-Lookup-Subset gewahrt. Geschwindigkeit kommt durch Skip von Quality-Gates die bei BE-CORE-
Konstanten ohnehin keine Wertschoepfung haben.*
