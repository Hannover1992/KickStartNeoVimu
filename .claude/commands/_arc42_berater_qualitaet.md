# _arc42_berater_qualitaet (arc42 §10 Qualitätsanforderungen — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§10"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — Qualitaetsbaum strukturieren + Szenarien aus AKs ableiten = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §10 Qualitätsanforderungen** als View: **10.1 Qualitätsbaum** (Quality Attribute Utility
Tree, mindmap, ISO-25010) + **10.2 Qualitätsszenarien** (Q42: Source/Stimulus/Artifact/Environment/
Response + Response-Measure). **Schlüssel-Quelle (BL-380 AK-5/W-CON-1): echte `quality_scenario`-Truth-Nodes**
(Model, `type: quality_scenario`) — die 6 iSAQB-Felder + `response_measure.{metric,threshold,method}`
maschinenlesbar, NICHT AK-Freitext. **Fallback (kein Node vorhanden): AK = Q42 1:1** (Rückwärts-Kompatibilität,
INV-A42B-AK-Legacy-Weg). Quelle = Model(quality_scenario) > SRS + akExtraktion.

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.{specParse, akExtraktion}, A_PIPELINE_STATE (srs)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (PRIMAER: quality_scenario-Nodes, type=quality_scenario [BL-380 AK-5/W-CON-1])
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Fallback: AKs = Q42-Szenarien wenn kein Node)
  {VAULT}/Backlog/{BL_SLUG}/4_K-Score/*          (per-AK Metriken; metric_component-Endpunkt-Werte)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Szenario ohne testbares Kriterium)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/10_qualitaet.md
    Frontmatter: {section_nr: 10, tier_min: standard, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [mindmap]}
    Body: 10.1 Qualitaetsbaum (mindmap, ISO-25010-Achsen) + 10.2 Szenarien-Tabelle
      (Source|Stimulus|Environment|Response|Metrik/Schwelle|Endpunkt), PRIMAER aus quality_scenario-Nodes
      (maschinenlesbar), Fallback 1:1 aus AKs.

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten.

INVARIANTEN: INV-A42B-1 (NUR 10_qualitaet.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat) ·
  INV-A42B-4 (Lint-konform) · INV-A42B-5 (W7). INV-A42B-AK (BL-380-NEUFASSUNG W-CON-1): PRIMAER sind echte
  `quality_scenario`-Nodes die Szenario-Quelle; KEIN §10-Inhalt aus AK-Freitext wenn Nodes vorhanden sind.
  Nur wenn GAR KEIN Node existiert -> Legacy-Fallback AK = Q42 1:1 (Rueckwaerts-Kompatibilitaet).
```

## Mermaid-Form (10.1 Qualitätsbaum)
```
mindmap
  root((Qualität))
    Wartbarkeit
      Modularität
      Testbarkeit
    Zuverlässigkeit
      Fehlertoleranz
    Performance-Effizienz
```

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/10_qualitaet.md.
2. snap = read-only Model(quality_scenario-Nodes) + AKs + SRS + K-Score + Gap/PL.
3. 10.1 Qualitaetsbaum (mindmap, ISO-25010-Achsen aus quality_goals/SRS/Top-AKs).
4. 10.2 Szenarien-Tabelle — QUELLE-Routing (BL-380 W-CON-1):
   IF >=1 `quality_scenario`-Node im Model:
     pro Node eine Zeile aus `scenario.{source, stimulus, environment, response,
     response_measure.{metric, threshold}}` + Endpunkt (`endpoint_type`/`endpoint_ref`),
     maschinenlesbar. KEINE Zeile aus AK-Freitext, solange Nodes vorhanden sind.
   ELSE (kein Node): Legacy-Fallback je AK ein Q42-Szenario (Source/Stimulus/Metrik aus AK).
5. Node/AK ohne testbare metric/threshold -> Zeile `[ungegroundet: messbar?] (OQ/PL)`.
6. Schreibe + Self-Lint. SendMessage: "§10 Qualitaet: {n} Szenarien ({quelle: nodes|AK-fallback}), {luecken} ohne Kriterium."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| `quality_scenario`-Nodes vorhanden | 10.2 aus Nodes (maschinenlesbar); AK-Freitext NICHT genutzt (W-CON-1) |
| kein Node vorhanden | Fallback AK = Q42 1:1 (Rückwärts-Kompatibilität) |
| Node/AK ohne messbares Kriterium | Q42-Szenario-Zeile `[ungegroundet: Metrik?] (OQ/PL)` |
| keine AKs/Nodes gegroundet | nur Qualitaetsbaum-Stub, grounding_status=teil |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_einfuehrung` (§1.2 Top-Qualitaetsziele) · `_arc42_berater_laufzeitsicht` (§6, Szenarien dynamisch) · arc42-Template §10 (Q42) · BL-378.
```
