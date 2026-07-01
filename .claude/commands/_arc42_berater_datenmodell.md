# _arc42_berater_datenmodell (arc42 §8 Datenmodell/ERD — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§8-Datenmodell"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — Domaenen-Entitaeten + Beziehungen modellieren = Urteil
```

## Zweck (EIN Job)
Rendere den **Datenmodell-Ausschnitt von arc42 §8 Querschnittliche Konzepte** (Domain Data Models) als
**Entity-Relationship-Diagramm**: die Domänen-Entitäten + Attribute + Beziehungen (Kardinalitäten). View auf
die schon-gepflegten Domänen-Wahrheiten. **Lücken-Detektor:** ein Attribut OHNE Quell-Beziehung = Waisen-Feld
(DCSRE-14-F2: DAS-Kennzeichen) bzw. ein Attribut OHNE Schreib-Pfad = ungeklärter Befüll-Prozess (F4).

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.domainBrief (matched_domain — Domaenen-Wahrheiten), specParse, akExtraktion
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (Entitaeten, Felder, Beziehungen — W{n})
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Entity-Erweiterung, Feld-Herkunft/Mapping)
  {VAULT}/Libraries/DomainLibrary/_index.md      (read-only; bekannte Domaenen-Begriffe)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Quell-/Befüll-Luecken)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/08_datenmodell.md
    Frontmatter: {section_nr: 8, tier_min: standard, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [erDiagram]}
    Body: erDiagram (Entitaeten + Attribute + Beziehungen) + Tabelle Feld|Herkunft|Befüll-Pfad (Spalten-Herkunft).

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten, DomainLibrary.

INVARIANTEN: INV-A42B-1 (NUR 08_datenmodell.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat,
  ungegroundet -> `> [ungegroundet: X] (siehe OQ-x / PL-y)`) · INV-A42B-4 (Lint-konform) · INV-A42B-5 (W7).
```

## Mermaid-Form
```
erDiagram
  PFLEGEEINRICHTUNG ||--o{ VERTRAG : hat
  PFLEGEEINRICHTUNG {
    string pe_id
    string das_kennzeichen "ungegroundet: Quelle? (OQ-DM-4 / PL-AK-06)"
    date   freigabedatum   "ungegroundet: Befüll-Workflow? (PL-AK-04)"
  }
```
(`erDiagram`: Entitaeten + Kardinalitaeten. Waisen-Attribut/ohne-Schreib-Pfad als Feld mit ungegroundet-Kommentar
+ OQ/PL-Backlink in der Herkunfts-Tabelle. Lint laesst ER-Kardinalitaet `||--o{` korrekt durch — no-false-RED.)

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/08_datenmodell.md.
2. snap = read-only Model(Entitaeten/Felder) + Spec(Erweiterung/Mapping) + domainBrief + DomainLibrary + Gap/PL.
3. entitaeten = Domaenen-Entitaeten + Attribute + Beziehungen (Kardinalitaeten aus Model/Spec).
4. FOR jedes Attribut: Quelle gegroundet (Import/Join/berechnet)? -> Herkunfts-Tabelle + model_refs;
   sonst Waisen (F2) -> ungegroundet + OQ/PL. Befuell-Pfad gegroundet? sonst (F4) -> ungegroundet + OQ/PL.
5. Schreibe erDiagram + Herkunfts-Tabelle Feld|Herkunft|Befüll-Pfad. grounding_status setzen.
6. Self-Lint. SendMessage: "§8 Datenmodell: {entitaeten} Entitaeten, {luecken} Waisen-/Befüll-Luecken (OQ/PL)."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| Attribut ohne Quelle (F2) | Feld + `"ungegroundet: Quelle? (OQ/PL)"` in ERD + Herkunfts-Tabelle |
| Attribut ohne Befüll-Pfad (F4) | Herkunfts-Tabelle Befüll-Pfad = `[ungegroundet] (PL-y)` |
| DomainLibrary leer / kein Domänenmodell | minimales ERD aus Spec-Entitäten, grounding_status=teil/leer |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_kontext` (§3, teilt F2-Quellen-Luecke) · `_arc42_berater_laufzeitsicht` (§6, teilt F4-Befüll-Luecke) ·
`_A_berater_domainBrief` (Domaenen-Wahrheiten-Quelle) · `arc42_mermaid_lint.py` · arc42-Template §8 · BL-378.
```
