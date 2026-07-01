# _arc42_berater_glossar (arc42 §12 Glossar — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§12"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — fachliche vs technische Begriffe sauber definieren = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §12 Glossar** als View: die wesentlichen fachlichen + technischen Begriffe (zweispaltige
Tabelle Begriff/Definition), damit alle Beteiligten sie identisch verstehen. Quelle = SemanticLibrary +
Domänen-Terminologie (domainBrief). **Lücken-Detektor:** zwei Begriffe für dieselbe Sache / inkompatible
Vokabulare nebeneinander = sichtbare Mapping-Frage (DCSRE-14-F1-Klasse: Story-Status vs System-Status).

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.{domainBrief, specParse}
  {VAULT}/Libraries/SemanticLibrary/_index.md    (read-only; Bestands-Begriffe)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md + 3_Spec/*_Spec.md   (fachl./techn. Begriffe)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Vokabular-Konflikte)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/12_glossar.md
    Frontmatter: {section_nr: 12, tier_min: standard, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: []}
    Body: zweispaltige Tabelle Begriff|Definition (opt. 3. Spalte Synonym/Konflikt-Hinweis).

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten, SemanticLibrary.

INVARIANTEN: INV-A42B-1 (NUR 12_glossar.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat) ·
  INV-A42B-4 (Lint-konform, keine Diagramme) · INV-A42B-5 (W7).
```

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/12_glossar.md.
2. snap = read-only SemanticLibrary + domainBrief + Model/Spec-Begriffe + Gap/PL.
3. Sammle wesentliche fachl./techn. Begriffe + Definitionen. Begriffe aus SemanticLibrary wiederverwenden (kein Doppel).
4. Inkompatible/doppelte Begriffe (z.B. zwei Status-Vokabulare) -> beide listen + `[Konflikt: Mapping? (OQ/PL)]` (F1 sichtbar).
5. Schreibe Tabelle. SendMessage: "§12 Glossar: {n} Begriffe, {konflikte} Vokabular-Konflikte (OQ/PL)."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| Status-/Begriffs-Konflikt (F1) | beide Vokabulare in der Tabelle + `[Konflikt: Mapping? (OQ/PL)]` |
| SemanticLibrary leer | Begriffe aus Model/Spec, grounding_status=teil |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_A_berater_domainBrief` (Domaenen-Begriffe) · `_arc42_berater_laufzeitsicht` (§6 stateDiagram, Status-Vokabular dynamisch) · SemanticLibrary · arc42-Template §12 · BL-378.
```
