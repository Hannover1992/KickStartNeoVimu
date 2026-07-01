# _arc42_berater_verteilung (arc42 §7 Verteilungssicht — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§7"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — relevante Infrastruktur-Aspekte fuer die Software-Verteilung waehlen = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §7 Verteilungssicht** als View: die **technische Infrastruktur**, auf der das System läuft
(Standorte/Umgebungen/Rechner/Container/Kanäle/Netztopologie) + die **Abbildung von Software-Bausteinen auf
diese Infrastruktur** (Infrastruktur Ebene 1, opt. Ebene 2). Quelle = Spec/Model-Deployment + Infra-/Redeploy-
Topologie. **Lücken-Detektor:** Software-Baustein ohne Infra-Zuordnung / Umgebung ohne Kanal = ungegroundet.

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.{specParse, dependencyAnalyzer}, A_PIPELINE_STATE
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Deployment/Infrastruktur/Umgebungen)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (Software-Bausteine fuer Infra-Mapping)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Cross-Ref)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/07_verteilung.md
    Frontmatter: {section_nr: 7, tier_min: full, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [flowchart]}
    Body: Infrastruktur Ebene-1 (Uebersichtsdiagramm + Begruendung + Qualitaets-/Leistungsmerkmale + Zuordnung Bausteine->Infra).

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten.

INVARIANTEN: INV-A42B-1 (NUR 07_verteilung.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat,
  ungegroundet -> `> [ungegroundet: X] (siehe OQ-x / PL-y)`) · INV-A42B-4 (Lint-konform) · INV-A42B-5 (W7).
```

## Mermaid-Form
```
flowchart TB
  subgraph PROD[Produktionsumgebung]
    APP[App-Server]
    DB[(Datenbank)]
    APP -->|SQL| DB
  end
  Client -->|HTTPS| APP
```
(`flowchart`+subgraph fuer Umgebungen/Kanaele: Knoten=Rechner/Container, subgraph=Umgebung — KEIN C4. Baustein->Infra-Mapping als Tabelle daneben.)

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/07_verteilung.md.
2. snap = read-only Spec(Deployment/Umgebungen) + Model(Bausteine) + Gap/PL.
3. Infrastruktur Ebene-1: Knoten (Umgebungen/Rechner/Container) + Kanaele + Begruendung + Qualitaetsmerkmale.
4. Zuordnung Software-Bausteine -> Infra (Tabelle). Fehlende Zuordnung/Umgebung -> ungegroundet + OQ/PL.
5. Schreibe + Self-Lint. SendMessage: "§7 Verteilung: {n} Infra-Knoten, {luecken} Zuordnungs-Luecken."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| keine Infrastruktur gegroundet | minimaler 1-Knoten-Stub + grounding_status=leer |
| Baustein ohne Infra-Zuordnung | Mapping-Tabelle `[ungegroundet] (OQ/PL)` |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_kontext` (§3.2 techn. Kontext) · `_arc42_berater_bausteinsicht` (§5) · arc42-Template §7 · BL-378.
```
