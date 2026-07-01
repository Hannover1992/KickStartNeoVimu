# _arc42_berater_risiken (arc42 §11 Risiken & technische Schulden — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§11"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — Risiko-Priorisierung + Massnahmen-Vorschlag = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §11 Risiken & technische Schulden** als View: nach Priorität geordnete Liste der erkannten
Architektur-Risiken / technischen Schulden, mit vorgeschlagenen Maßnahmen. **Schlüssel-Mapping: BLOCKED-PL-
Items + OQ = die priorisierte Risiko-Liste** (DCSRE-14: die 9 BLOCKED-AKs sind 1:1 die Risiken). Quelle = PL
(BLOCKED) + K-Fragilität + Gap-OQ.

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.plAggregation, A_PIPELINE_STATE (k_fragilitaet)
  {VAULT}/Backlog/{BL_SLUG}/6_PL/{BL}-parking-lot.md   (PL-Items, READY/BLOCKED = Risiken/Schulden)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/*                    (offene Fragen = Risiko-Treiber)
  {VAULT}/Backlog/{BL_SLUG}/4_K-Score/*                (k_fragilitaet pro AK)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/11_risiken.md
    Frontmatter: {section_nr: 11, tier_min: standard, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: []}
    Body: Tabelle nach Prio (Risiko/Schuld | Treiber (PL/OQ) | Maßnahme). BLOCKED-PL + offene OQ zuerst.

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten, PL (read-only!).

INVARIANTEN: INV-A42B-1 (NUR 11_risiken.md) · INV-A42B-2 (Read-Only — PL wird NUR gelesen) · INV-A42B-3 (model_refs / kein Halluzinat) ·
  INV-A42B-4 (Lint-konform, i.d.R. keine Diagramme) · INV-A42B-5 (W7).
```

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/11_risiken.md.
2. snap = read-only PL(BLOCKED + READY) + Gap-OQ + K-Fragilitaet.
3. Sammle Risiken: BLOCKED-PL-Items (hoechste Prio) + offene OQ + hohe k_fragilitaet-AKs. Ordne nach Prio.
4. Je Risiko: Treiber (Backlink PL-Item/OQ) + vorgeschlagene Massnahme. KEINE erfundenen Risiken (nur gegroundet).
5. Schreibe Tabelle. SendMessage: "§11 Risiken: {n} ({blocked} aus BLOCKED-PL, {oq} aus offenen OQ)."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| 0 BLOCKED, 0 OQ | "keine offenen Architektur-Risiken erkannt" + ggf. k_fragilitaet-Hinweise, grounding_status=voll |
| PL fehlt | aus Gap-OQ + k_fragilitaet ableiten, grounding_status=teil |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_entscheidungen` (§9, offene Entscheidungen = Risiken) · alle Berater (deren ungegroundet-Platzhalter speisen die OQ/PL-Risiken) · arc42-Template §11 · BL-378.
```
