# _arc42_berater_einfuehrung (arc42 §1 Einführung & Ziele — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§1"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — Top-Qualitaetsziele auswaehlen + treibende Kraefte = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §1 Einführung & Ziele** als View: **1.1 Aufgabenstellung** (fachliche Aufgabe + treibende
Kräfte, knapp), **1.2 Qualitätsziele** (Top-3..5 nach ISO-25010, tabellarisch nach Priorität), **1.3
Stakeholder** (Rolle/Erwartung). Quelle = taskDefinition (`quality_goals[]`, BL-380 AK-4) + SRS/Top-AKs
+ BL/Spec. **Lücken-Detektor:** Qualitätsziel ohne `quality_scenario`-Node = ungegroundet (BL-380 W-CON-2).

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → A_PIPELINE_STATE (k_score, srs), BERATER_OUTPUTS.{specParse, akExtraktion}
  {VAULT}/Task.md / 1_Task/*_Task.md             (fachliche Aufgabe + treibende Kraefte + quality_goals[] [BL-380 AK-4])
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (quality_scenario-Nodes: type=quality_scenario + qualitaetsziel_ref [BL-380 AK-5/W-CON-2])
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Qualitaetsziele, Stakeholder)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Cross-Ref)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/01_einfuehrung_ziele.md
    Frontmatter: {section_nr: 1, tier_min: standard, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [mindmap]}
    Body: 1.1 Aufgabenstellung (kurz) · 1.2 Qualitaetsziele (Tabelle Ziel|ISO-Kategorie|Szenario|Prio; opt. mindmap-Baum) · 1.3 Stakeholder (Tabelle Rolle|Erwartung)

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten.

INVARIANTEN: INV-A42B-1 (NUR 01_einfuehrung_ziele.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat,
  ungegroundet -> `> [ungegroundet: X] (siehe OQ-x / PL-y)`) · INV-A42B-4 (Lint-konform) · INV-A42B-5 (W7).
```

## Mermaid-Form (optional, 1.2 Qualitätsbaum)
```
mindmap
  root((Qualität))
    Wartbarkeit
      Änderbarkeit
    Zuverlässigkeit
    Benutzbarkeit
```

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/01_einfuehrung_ziele.md.
2. snap = read-only taskDefinition (quality_goals[]) + SRS/AKs + Spec(Qualitaetsziele/Stakeholder)
   + Model(quality_scenario-Nodes) + Gap/PL.
3. 1.1 Aufgabe + treibende Kraefte (aus taskDef). 1.2 Top-3..5 Qualitaetsziele bestimmen (Regel unten),
   ISO-25010, tabellarisch nach Prioritaet.
4. Pro Top-Ziel: kante auf >=1 `quality_scenario`-Node (Model, qualitaetsziel_ref zeigt auf dieses Ziel).
   Node vorhanden -> Szenario-Spalte traegt Node-id + response_measure.{metric,threshold} (maschinenlesbar).
   KEIN Node -> `[ungegroundet: Szenario? (OQ/PL)]` (gegen echte Node-Existenz pruefbar, BL-380 W-CON-2).
   Graceful Degradation: gar keine quality_scenario-Nodes im Vault -> Fallback auf AK-Freitext-Szenario
   (Rueckwaerts-Kompatibilitaet, kein Breaking-Change).
5. 1.3 Stakeholder-Tabelle (aus Spec/BL; fehlend -> Platzhalter).
6. Schreibe + Self-Lint. SendMessage: "§1 Einfuehrung: {n} Top-Ziele, {g} szenario-gegroundet, {luecken} ungegroundet."
```

## Top-3..5-Bestimmung + Proportionalitaet (BL-380 AK-2 / W-PROP-1, W-PROP-2)
**Deterministische "Top"-Ordnung (strikte Prioritaet, KEIN Misch-Gewicht):**
```
(1) arc42-§1.2-Prioritaet (explizite quality_goals[].priority_rank aus taskDefinition / §1.2) GEWINNT.
(2) Sonst SRS-Ranking      (ak_details[AK].srs_pro_ak hoch = epistemisch unsicher = hoher Klaerungs-Hebel).
(3) Sonst K-Score-Ranking  (ak_details[AK].k_score_pro_ak hoch = strukturelles Risiko).
Bei Gleichstand in Stufe N -> naechste Stufe konsultieren (W-PROP-2-Adjudikation, Spec Sec 0).
```
**Proportionalitaets-Cap (W-PROP-1, gegen ISO-25010-Achsen-Explosion):** Fuer JEDES der Top-3..5
Qualitaetsziele existiert >=1 `quality_scenario`-Node — NICHT pro ISO-25010-Achse, nur die fuer
DIESES System kritischen Achsen. Schranke: Gesamtanzahl Szenarien <= 5 × Anzahl-Top-Ziele.
Proportional, nicht exhaustiv. (Produktion der Nodes = A-Pipeline; dieser Berater ist read-only View
und macht die Top-Auswahl + prueft die Kante — er schreibt keine Nodes, INV-A42B-2.)

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| Top-Ziel ohne `quality_scenario`-Node (Node fehlt) | `[ungegroundet: Szenario? (OQ/PL)]` (gegen echte Node-Existenz, W-CON-2) |
| gar keine quality_scenario-Nodes im Vault | Fallback: AK-Freitext-Szenario (Rückwärts-Kompatibilität, kein Breaking-Change) |
| keine Stakeholder gegroundet | Stakeholder-Tabelle leer + grounding_status=teil |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_qualitaet` (§10 vertieft 1.2) · `arc42_mermaid_lint.py` · arc42-Template §1 · BL-378.
```
