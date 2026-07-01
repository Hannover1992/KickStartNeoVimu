---
status: active
version: 0.1.0
type: berater
parent: _A_orchestrate
phase: phase_5a
model_tier: ceiling
created: 2026-05-23
feature_anchor: BL-197
optional: false
changelog_0_1_0: |
  v0.1.0 (2026-05-23): Initial — BL-197 A-Pipeline absorbiert Forward-PL-Generierung.
    - Kopiert und angepasst aus _IDF_berater_specParse.md (INV-NS-1: IDF unveraendert).
    - parent: _A_orchestrate statt _IDF_orchestrate.
    - BERATER_OUTPUTS-Slot: A_PIPELINE_STATE-Namespace.
    - Phase 5a (nach Phase 4g gap, vor Phase 5b akExtraktion).
contract:
  reads:
    - {file: "{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md", path: "Volltext (Vault-First)", purpose: "Spec-Sektionen, AKs, RFs extrahieren"}
    - {file: ".claude/specs/{NAME}_Spec.md", path: "Lokal-Fallback", purpose: "Legacy"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.derived_name / bl_id / bl_slug", purpose: "Feature-Anker"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.specParse", purpose: "Sections + AK-Liste + RF-Liste"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser specParse)"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md", path: "(read-only)"}
  calls: []
---

# _A_berater_specParse (Phase 5a in _A_orchestrate)

> **Zweck:** Spec parsen: Sections, AKs, RFs strukturiert extrahieren — als Vorbereitung fuer Phase 5b (akExtraktion) in der A-Pipeline.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_specParse                                       |
+======================================================================+
|  LIEST:                                                              |
|    {VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md (Volltext)        |
|    .claude/specs/{NAME}_Spec.md (Lokal-Fallback)                    |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver)      |
|      A_PIPELINE_STATE.derived_name / bl_id / bl_slug                |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                        |
|      BERATER_OUTPUTS.specParse = {                                   |
|        sections[], aks[], rfs[],                                     |
|        sections_count, aks_count, rfs_count,                         |
|        spec_path, status                                             |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser specParse)                              |
|    A_PIPELINE_STATE.* (read-only hier)                               |
|    Spec selbst (read-only)                                           |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 5a (nach Phase 4g gap)                  |
|                                                                      |
|  MODELL-TIER: opus                                                   |
|    Begruendung: Volltext-Spec-Parse + Section-Klassifikation        |
|    + AK/RF-Identifikation. Sonnet uebersieht subtile RFs.           |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-SP-1: Jede AK traegt eindeutige ID (AK-{n} oder {bl}-AK-{n}) |
|    INV-SP-2: Jede RF traegt eindeutige ID                            |
|    INV-SP-3: Schreib-Isolation auf BERATER_OUTPUTS.specParse         |
|    INV-A-ORDER-5: Phase 5a MUSS nach Phase 4g (gap) laufen          |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - Spec existiert (Vault-First, sonst Lokal-Fallback)              |
|    - A_PIPELINE_STATE.gap.status = DONE                              |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.specParse vollstaendig                          |
|    - aks_count > 0 (sonst EXIT 2)                                    |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_specParse, args="{NAME}")

Parameter:
  {NAME} - Feature-Name (aus A_PIPELINE_STATE.derived_name)

Ausgabe:
  - BERATER_OUTPUTS.specParse (sections, aks, rfs + counts)
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [A_SPEC] ENTRY name={NAME}
  [A_SPEC] EXIT duration={ms}ms sections={n} aks={k} rfs={m}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  specParse:
    sections:
      - {id: "S-1", title: "Ziel", line_start: 12}
    aks:
      - {id: "AK-1", title: "...", refs: ["S-1"], line_start: 25, line_end: 40}
    rfs:
      - {id: "RF-1", title: "...", refs: ["AK-1"]}
    sections_count: 7
    aks_count: 10
    rfs_count: 5
    spec_path: "{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md"
    status: DONE
    last_berater: "specParse"
```

## Logik (v0.1.0)

```
SCHRITT 0: Entry-Log + Spec-Pfad (Vault-First)
  NAME = args[0]
  Logge: "[A_SPEC] ENTRY name={NAME}"

  manifest = Read({WORKING_DIR}/_manifest.md)
  bl_id   = manifest.A_PIPELINE_STATE.bl_id ?? NAME
  bl_slug = manifest.A_PIPELINE_STATE.derived_name ?? NAME

  spec_path = "{VAULT}/Backlog/{bl_slug}/3_Spec/{NAME}_Spec.md"
  IF NOT exists(spec_path):
    spec_path = ".claude/specs/{NAME}_Spec.md"
  IF NOT exists(spec_path):
    Logge: "[A_SPEC] FAIL — Spec nicht gefunden: {spec_path}"
    EXIT 2

  Logge: "[A_SPEC] spec_path={spec_path}"

SCHRITT 1: Section-Extraktion (Volltext lesen)
  spec_text = Read(spec_path)
  sections = []
  section_counter = 0
  FOR jede Zeile i in spec_text:
    IF line matches "^## " (Markdown H2):
      section_counter += 1
      sections.append({
        id: "S-{section_counter}",
        title: strip_prefix(line, "## "),
        line_start: i
      })
  # line_end = naechste Section line_start - 1 (oder EOF)
  FOR j in range(|sections| - 1):
    sections[j].line_end = sections[j+1].line_start - 1
  IF |sections| > 0:
    sections[-1].line_end = count_lines(spec_text)

SCHRITT 2: AK-Extraktion (Pattern "### AK-{n}" oder "AK-{n} —")
  aks = []
  ak_counter = 0
  FOR jede Zeile i in spec_text:
    IF line matches "^### AK-\d+" OR "^AK-\d+":
      ak_counter += 1
      ak_id  = extract_pattern(line, r"AK-\d+")
      ak_title = strip_prefix(line, "### AK-") ?? strip_prefix(line, "AK-")
      ak_title = split(ak_title, " —")[1] if " —" in ak_title else ak_title
      # Zuordnung zu Section: letzte Section mit line_start <= i
      parent_section = max(s FOR s in sections IF s.line_start <= i, key=s.line_start)
      aks.append({
        id: ak_id,
        title: ak_title.strip(),
        refs: [parent_section.id] if parent_section else [],
        line_start: i
      })
  # line_end pro AK: naechste AK line_start - 1 (oder naechste Section)
  FOR j in range(|aks| - 1):
    aks[j].line_end = aks[j+1].line_start - 1
  IF |aks| > 0:
    aks[-1].line_end = count_lines(spec_text)

SCHRITT 3: RF-Extraktion (Pattern "RF-{n}" in Text)
  rfs = []
  rf_counter = 0
  FOR jede Zeile i in spec_text:
    IF line matches "RF-\d+":
      rf_id = extract_pattern(line, r"RF-\d+")
      IF rf_id NOT IN [rf.id FOR rf in rfs]:
        rf_counter += 1
        # Zuordnung: pruefen welche AK diese Zeile enthaelt
        parent_ak = max(a FOR a in aks IF a.line_start <= i AND a.line_end >= i, key=a.line_start)
        rfs.append({
          id: rf_id,
          title: strip_line(line).strip(),
          refs: [parent_ak.id] if parent_ak else []
        })

SCHRITT 4: Synthese + Dedup (INV-SP-1/INV-SP-2)
  # AKs dedup nach id
  seen_ak_ids = {}
  aks_deduped = []
  FOR ak in aks:
    IF ak.id NOT IN seen_ak_ids:
      seen_ak_ids[ak.id] = true
      aks_deduped.append(ak)

  # RFs dedup nach id
  seen_rf_ids = {}
  rfs_deduped = []
  FOR rf in rfs:
    IF rf.id NOT IN seen_rf_ids:
      seen_rf_ids[rf.id] = true
      rfs_deduped.append(rf)

  aks = aks_deduped
  rfs = rfs_deduped

SCHRITT 5: Output schreiben (INV-SP-3 Schreib-Isolation)
  output = {
    sections:       sections,
    aks:            aks,
    rfs:            rfs,
    sections_count: |sections|,
    aks_count:      |aks|,
    rfs_count:      |rfs|,
    spec_path:      spec_path,
    status:         "DONE",
    last_berater:   "specParse"
  }
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.specParse = output)

SCHRITT 6: Exit
  exitcode = |aks| > 0 ? 0 : 2
  Logge: "[A_SPEC] EXIT sections={|sections|} aks={|aks|} rfs={|rfs|}"
  EXIT exitcode
```

## ADR-Truth-Node-Materialisierung (Producer-Erweiterung, BL-382 AK-2/AK-3 — additiv)

> **Zweck (ADR-Producer):** Trifft die Spec-Arbeit eine **signifikante Architektur-Entscheidung**,
> materialisiert specParse **zur Entscheidungs-Zeit** einen `type: adr`-Truth-Node (6 Nygard-Felder +
> drei explizite Graph-Kanten) im Model/Vault — explizit-vor-implizit. KEIN neuer Berater, KEINE neue
> A-Phase (B-1 adjudiziert). Strukturelle Schwester des BL-380-QDSA-Producers (`_taskDefinition` Schritt 1.5)
> und des `quality_scenario`-Subtyps. Schema-Kanon: `manifest-schema.md` Sektion L; Validator:
> `quality_model_wform.py` (`_is_adr`/`check_adr_block`). Konsument: `_arc42_berater_entscheidungen` (§9).

**Warum hier (W-PROD-1 / A2-Adjudikation, B-1):** `_A_berater_specParse` parst schon heute den Spec-Volltext
und erzeugt die `ADR-*`-Eintraege, die der §9-Berater liest (VERTRAG-Beleg). Es ist der natuerliche
Producer-Sitz fuer den ADR-Knoten. Eine **neue dedizierte A-Phase** waere riskanter (zusaetzliche
Phase-Skip-Flaeche → INV-MODUS-2-Exposition) — exakt das BL-380-W-QDSA-1-Muster, das die QDSA-Mechanik
additiv in `_taskDefinition` (Phase 0.6) statt in eine neue Phase legte. Pflege/Re-Materialize laeuft
downstream via `_SDF_berater_modelMaintain` / `_SC_modelMaintain` (nicht in diesem Berater).

**WANN materialisieren (Materialize-Schwelle, AK-4 / batch_PL4 — B-2 adjudiziert, FINAL):** Nygards
Doktrin „dokumentiere die Entscheidungen, **die nicht offensichtlich sind**" (Nygard 2011) wird hier
*berechenbar* statt Freihand-Bauchgefuehl. Eine Entscheidung ist **materialisierungs-pflichtig** (ein
`type: adr`-Knoten MUSS entstehen) gdw. **mindestens eine** der drei Bedingungen erfuellt ist (Spec-B-2-
Kombi-Regel `a OR b OR c` — disjunktiv, nicht konjunktiv):

1. **(a) k_score-Schwelle (Struktur-Risiko, Quelle `_K_score.md`):** Der betroffene Baustein/die AK
   ueberschreitet die **HIGH**-Schwelle des K-Scores. `_K_score.md` klassifiziert (`--mode pl_item`,
   Rueckgabe `{k_score: N}`): `LOW = [0,33]`, `MEDIUM = (33,66]`, **`HIGH = (66,100]`**. **Schwelle =
   k_score > 66 (HIGH-Band).** Hoher k_score bedeutet teuer-zu-aendern + hoch-gekoppelt + fragil — exakt
   Nygards „signifikant/teuer/riskant". Die Schwellen-ZAHL ist die kanonische K-Score-HIGH-Grenze (kein
   neuer Magic-Wert; bei Verschiebung der K-Score-Baender folgt die ADR-Schwelle automatisch). **`_K_score.md`
   bleibt Single-Source der Zahl — dieser Berater liest sie, fixiert sie NICHT redundant.**
2. **(b) Risiko-Klasse (Thread-B-Taxonomie):** Die Entscheidung gehoert einer der vier Risiko-Klassen an —
   **Omission** (etwas Notwendiges weggelassen), **Commission** (etwas Falsches getan), **Realization**
   (Umsetzungs-/Technologie-Risiko), **Managerial** (Prozess-/Organisations-Risiko). Risiko-behaftet ⇒
   materialisierungs-pflichtig, auch wenn der k_score-Baustein (noch) nicht HIGH ist (z.B. eine fruehe
   Technologie-Wahl mit Realization-Risiko, deren Baustein erst spaeter hoch-gekoppelt wird).
3. **(c) expliziter Materialize-Override (Berater/HiL-Flag, reines Bool ohne Modus-Semantik):** Ein Berater
   oder HiL kann eine Entscheidung explizit als materialisierungs-pflichtig markieren, auch unter beiden
   Schwellen — faengt die wichtige-aber-strukturell-unauffaellige Entscheidung (false-negative-Schutz). **Der
   Override ist STRENG ADDITIV: er kann die Materialize-Pflicht nur OEFFNEN, NIE schliessen/unterdruecken**
   (W-THR-2). Es gibt keinen Pfad, eine schwellen-pflichtige Entscheidung per Override aus der
   Materialisierung herauszunehmen.

**Anti-Zeremonie (die Kehrseite der Schwelle):** Eine **offensichtliche/triviale** Entscheidung (k_score
LOW/MEDIUM, keine Risiko-Klasse, kein Override) materialisiert **bewusst KEINEN** ADR-Knoten — Nygards
„nicht die offensichtlichen" wirkt in BEIDE Richtungen. Die Schwelle schuetzt vor ADR-Inflation (jede
triviale Wahl als Zeremonie-ADR ⇒ Signal-Rausch-Kollaps, niemand liest sie mehr).

**Goodhart-Guard (W-THR-3, AK-4 — Schwelle-traegt-Begruendung):** Die Schwelle ist **Trigger, NICHT Ziel.**
Goodhart: „when a measure becomes a target, it ceases to be a good measure." Damit der k_score-Schwellenwert
nicht zum Selbstzweck degeneriert (Knoten emittiert, nur weil eine Zahl gerissen wurde, mit Pseudo-Inhalt),
gilt: (i) der emittierte Knoten traegt seine **inhaltliche** `adr.begruendung` — WARUM diese Wahl, fachlich,
nicht „weil k_score=72". Das Schwelle-Reissen oeffnet die Pflicht, **ersetzt aber die Begruendung NIE**;
`adr.begruendung` ist strukturell erzwungenes Pflichtfeld (Validator, AK-6). (ii) Die **Schwell-Entscheidung
selbst** traegt ihre Ableitung sichtbar — `begruendung`/`konsequenzen` halten fest, *warum* diese Entscheidung
signifikant ist (welche Bedingung a/b/c griff), nicht nur *dass* eine Metrik riss. Das ist der direkte
**Spiegel des BL-380-W-GH-1-Prinzips**: dort traegt das `quality_scenario`-`response_measure.method` die
Mess-METHODE (gegen Metrik-Gaming des `threshold`); hier traegt der ADR-Knoten seine `begruendung` (gegen
Schwellen-Gaming des `k_score`). Der **strukturelle Anteil** dieses Guards ist der bereits gebaute Validator
(`begruendung`-Pflichtfeld); dieser WANN-Absatz ist der **doktrinaere Anteil** (markdown_uncoverable).

**WIE materialisieren (Emit-Schritt, AK-2):** Pro materialisierungs-pflichtiger Entscheidung emittiert
specParse EINEN Gold-Form-`### W-ADR-{n}`-Knoten in den Model-Vault (`{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md`),
der die BL-243-Gold-Form-Basis (`text/Status/source/Quelle/Edge zu`) traegt UND einen `adr:`-Block mit den
**6 Nygard-Feldern**. ID-Format `{BL-SLUG}.ADR-{n}` (BL-309-lokales Praefix, W-DOM-4 — identisch zum `ADR-*`-Token,
das §9 heute heuristisch sucht). Der emittierte Knoten MUSS `quality_model_wform.py`-gold sein (6 Felder praesent,
`adr.status` IN ADR-Enum).

```yaml
### W-ADR-{n} · {atomarer Entscheidungs-Titel}
- **text:** {einzeiliger Satz: diese Entscheidung wurde getroffen}
- **Status:** {Gold-Form epistemisch: BESTAETIGT/TENTATIV/...}   # orthogonal zu adr.status (AK-5)
- **source:** {INTERN/EXTERN-Provenienz}
- **Quelle:** [[{Vault-Anker}]]
- **Edge zu:** {>=1 W{n}/Source-Ref}
- **type:** adr
- **id:** {BL-SLUG}.ADR-{n}
- **adr:**
    - entscheidung: {Was wurde beschlossen}
    - problem_kontext: {Welches Problem / welcher Kontext zwang die Wahl}
    - alternativen:
        - option: {verworfene Wahl}
          abgelehnt_weil: {Grund}
    - begruendung: {Warum diese Wahl — Pflicht nicht-leer, Goodhart-Guard}
    - konsequenzen: {positive + negative Folgen}
    - status: vorgeschlagen | akzeptiert | superseded | konflikt-offen   # ADR-Enum (AK-5)
    - betrifft_baustein: ["{baustein-ref}" | "[ungegroundet: baustein?]"]
    - superseded_by: {BL-SLUG}.ADR-{m}     # optional, nur bei Abloesung
    - abhaengig_von: ["{BL-SLUG}.ADR-{k}"]  # optional, nur bei Abhaengigkeit
```

**Die drei expliziten Graph-Kanten (AK-3 — Felder, KEINE Prosa, BL-287-Doktrin):** Der emittierte `adr:`-Block
traegt drei explizite Kanten-Felder (NICHT Prosa-Erwaehnung im Fliesstext):

1. **`betrifft_baustein[]`** — Liste von Kanten nach UNTEN auf arc42-§5-Bausteinsicht/Komponenten-Knoten.
   **Default-Pflicht mit Luecken-Marker-Fallback (B-3):** Hat eine fruehe (vor-Bausteinsicht-)Entscheidung
   noch keinen identifizierbaren Baustein, emittiert specParse `betrifft_baustein: ["[ungegroundet: baustein?]"]`
   — die Kante wird NICHT hart abgelehnt und NICHT still weggelassen (loest die W-DOM-5/W-EDGE-1-Spannung ohne
   Optional-machen).
2. **`superseded_by`** — gerichtete ADR→ADR-Ersetzungs-Kante, ID-Form `{BL-SLUG}.ADR-{m}`. Nur gesetzt, wenn
   diese Entscheidung eine frueheren abloest. Loest ADR-2 eine ADR-1 ab, MUSS der Producer im selben Schritt
   **atomar** `ADR-1.status = superseded` UND `ADR-1.superseded_by = {BL-SLUG}.ADR-2` setzen (kein verwaister
   "akzeptiert-aber-ersetzt"-Zustand; der abgeloeste Knoten bleibt verlustfrei im Vault — Historie). Liegt der
   abzuloesende ADR in einem fremden, nicht-schreibbaren BL-Vault, wird das als Cross-BL-Pflege-Bedarf markiert
   (nicht still verschluckt). *Zyklus-Guard + ein-aktiver-Kopf-Invariante = AK-7 (eigener Batch).*
3. **`abhaengig_von[]`** — Liste gerichteter ADR→ADR-Abhaengigkeits-Kanten (ID-Form `{BL-SLUG}.ADR-{k}`),
   getrennt von `superseded_by`: Abhaengigkeit = "baut auf", superseded = "ersetzt". Nur gesetzt bei Vorhandensein
   einer solchen Beziehung, sonst leer/absent.

`superseded_by` und `abhaengig_von` sind bei vorhandener Beziehung Pflicht, sonst absent/leer. `betrifft_baustein`
ist Default-Pflicht (Marker erlaubt). Das ID-Format-Schema ist `{BL-SLUG}.ADR-{n}`; die maschinelle
ID-Format-Pruefung + Kanten-Praesenz-Check im Validator ist AK-3-code-coverable (eigener additiver Validator-Schritt,
sofern gebaut — bricht die 16/16 NICHT).

**INV-MODUS-1/5 (hart, strukturell):** Weder der emittierte `adr:`-Block noch `adr.status` noch der
Materialize-Override-Trigger (c) DUERFEN eines der Verbotsfelder tragen: `recommended_modus`, `sdf_mode`,
`sdf_mode_hint`, `expected_sdf_mode`, `mode_recommendation`. Der ADR-Knoten ist **Input/Truth, KEIN
Modus-Setzer** — specParse setzt NIE den Modus (das ist SDF Phase 1.1 alleinige Hoheit, INV-MODUS-1). Der
Materialize-Trigger ist ein reines Bool/Flag ohne Modus-Semantik (W-THR-2). Der Pre-Write-Hook
(`guard_modus_writer.py`, BL-382-erweitert auf den verschachtelten `adr:`-Block, AK-11) BLOCKT einen
Verbotskey auch nested unter `adr:` — kein Naming-Bypass.

**Scope-Hinweis (markdown_uncoverable):** Diese Producer-Doktrin ist eine Skill-Doc-Erweiterung (WO/WIE-Doktrin) —
**forward-verify per echtem A-Lauf** (T-12). Die ERGEBNIS-Knoten sind code-coverable (Validator, AK-1/AK-5/AK-6),
die Producer-Integration + Schwellen-Trigger-Logik (a/b/c) selbst nicht. Die Materialize-Schwelle (k_score>66-HIGH
ODER Risiko-Klasse ODER Override + Goodhart-Guard) = AK-4 (batch_PL4, **oben verdrahtet**); der STRUKTURELLE
Goodhart-Anteil (`begruendung`-Pflichtfeld) ist der schon gebaute Validator (AK-6), dieser Berater traegt den
DOKTRINAEREN Anteil. Zyklus-Guard = AK-7; Konflikt-Stufe-1 = AK-8; §9-Konsum-Vertrag (Primaer-Lese-Pfad +
Misch-Render) = `_arc42_berater_entscheidungen` (AK-9/10).

## migration_disposition-Pflicht-Metadatum (BL-333, B4 — WARN-Haken, non-blocking)

> **Spiegel der Lane-A-WARN-Logik** (`resolve_format_version.check_migration_disposition`). Prosa-Disziplin, kein Hard-Block.

Beim Parsen/Anlegen der Spec-Frontmatter traegt jede Spec ein Pflicht-Metadatum `migration_disposition`, das festhaelt, wie sich die Aenderung zu Bestands-Artefakten verhaelt:

- **Wertebereich:** `retroaktiv` (wirkt auf bestehende Artefakte rueckwirkend) | `forward-compat-only` (nur neue Artefakte, Bestand bleibt Gen-0) | `hybrid` (beides).
- **Pruef-Haken (fehlt -> WARN):** Fehlt `migration_disposition`, erzeugt der Validator eine WARN-Zeile (`check_migration_disposition`) — **non-blocking**, eskaliert NIE zu exit!=0. Die REQUIRED-Pflichtfelder (`id/title/status/reifegrad/created`) bleiben unberuehrt.
- **Follow-Spiegel:** IDF Phase 3.5 (`_IDF_berater_validator.md`, B5) wendet denselben WARN-Haken mit identischer WARN-vs-Block-Semantik an.

## Begruendung Modell-Tier

opus — Volltext-Spec mit subtilen Anforderungen. Latente RFs koennen versteckt sein in Prosa-Saetzen. Wellen-Pattern erfordert Synthese-Tiefe.
