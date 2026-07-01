# _arc42_berater_loesungsstrategie (arc42 §4 Lösungsstrategie — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§4"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — die zentralen Eckpfeiler-Entscheidungen destillieren = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §4 Lösungsstrategie** als View — **KURZ**: die grundlegenden Entscheidungen, die Entwurf +
Implementierung prägen: Technologieentscheidungen · Top-Level-Zerlegung (prägendes Muster) · wie die
wichtigsten Qualitätsziele erreicht werden · relevante organisatorische Entscheidungen. Quelle = Model/Spec-
Kern-Entscheidungen. Verweist auf §5/§8/§9 statt zu duplizieren.

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.{specParse, domainBrief}, A_PIPELINE_STATE (k_score)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (Top-Level-Zerlegung, praegende Muster — W{n})
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Technologie-/Architektur-Entscheidungen)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Cross-Ref)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/04_loesungsstrategie.md
    Frontmatter: {section_nr: 4, tier_min: full, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [flowchart?]}
    Body: kurzer Ueberblick (Technologie · Top-Level-Zerlegung · Qualitaets-Erreichung · org. Entscheidungen),
          Verweis auf §5/§8/§9. KEINE Redundanz.

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten.

INVARIANTEN: INV-A42B-1 (NUR 04_loesungsstrategie.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat) ·
  INV-A42B-4 (Lint-konform) · INV-A42B-5 (W7). INV-A42B-KURZ: bewusst knapp — Eckpfeiler, keine Detail-Duplikation.
```

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/04_loesungsstrategie.md.
2. snap = read-only Model(Zerlegung/Muster) + Spec(Technologie/Entscheidungen) + domainBrief + Gap/PL.
3. Destilliere die 3-5 zentralen Entscheidungen + WARUM (knapp). Verweise fuer Details auf §5/§8/§9.
4. Entscheidung vermutet, nicht belegt -> ungegroundet + OQ/PL.
5. Schreibe (kurz). SendMessage: "§4 Loesungsstrategie: {n} Eckpfeiler-Entscheidungen."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| keine Kern-Entscheidungen gegroundet | knapper Stub + grounding_status=leer |
| Entscheidung offen/konfliktär | Verweis auf §9-ADR `[ungegroundet: Entscheidung offen] (OQ/PL)` |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_bausteinsicht` (§5) · `_arc42_berater_entscheidungen` (§9) · arc42-Template §4 · BL-378.
```
