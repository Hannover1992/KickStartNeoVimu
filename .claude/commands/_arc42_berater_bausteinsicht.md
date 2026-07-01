# _arc42_berater_bausteinsicht (arc42 §5 Bausteinsicht — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§5"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — Whitebox-Schnitt + Relevanz-vor-Vollstaendigkeit = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §5 Bausteinsicht** ("Grundrissplan") als View: die **statische Zerlegung** des Systems in
Bausteine (Module/Komponenten/Klassen/Schichten) + deren Abhängigkeiten, als **Whitebox/Blackbox** über
**Ebene 1→2→3** (Relevanz vor Vollständigkeit — nur wichtige/riskante/komplexe Bausteine zoomen).
**Lücken-Detektor:** eine Owner-/Modul-Grenze macht "wer baut das?" sichtbar (DCSRE-14-F5-Klasse:
DCSRE-3806-Datenmodell-Erweiterung).

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.dependencyAnalyzer (layers/file_index = Zerlegung + Abhaengigkeiten),
                              BERATER_OUTPUTS.specParse (Komponenten/Sektionen), A_PIPELINE_STATE
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (W{n}-Bausteine, Verantwortungen)
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Komponenten, Schnittstellen)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Owner-/Boundary-Luecken)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/05_bausteinsicht.md
    Frontmatter: {section_nr: 5, tier_min: light, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [flowchart|classDiagram]}
    Body: Ebene-1 Whitebox (Uebersichtsdiagramm + Begruendung der Zerlegung + Blackbox-Tabelle Name|Verantwortung
          + wichtige Schnittstellen). Ebene-2/3 NUR fuer relevante Bausteine (Tier FULL).

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten.

INVARIANTEN: INV-A42B-1 (NUR 05_bausteinsicht.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat,
  ungegroundet -> `> [ungegroundet: X] (siehe OQ-x / PL-y)`) · INV-A42B-4 (Lint-konform) · INV-A42B-5 (W7).
  INV-A42B-PROP (Proportionalitaet): LIGHT = nur Ebene-1; tiefere Ebenen nur FULL.
```

## Mermaid-Form
```
flowchart TB
  subgraph SYS[Whitebox System]
    A[Baustein A] --> B[Baustein B]
    A --> C[Baustein C]
  end
  subgraph EXT[DCSRE-3806 - Owner?]
    D["[ungegroundet: wer baut Datenmodell-Erweiterung?] (PL-y)"]
  end
  B -.-> D
```
(Whitebox als subgraph; Owner-/Modul-Grenze als eigener subgraph → F5 sichtbar. `classDiagram` fuer feinere
statische Struktur. Reines Mermaid — KEIN C4.)

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/05_bausteinsicht.md; tier aus Spawn-Args.
2. snap = read-only depAnalyzer(layers/file_index) + Model(Bausteine) + Spec(Komponenten) + Gap/PL.
3. Ebene-1 Whitebox: Bausteine + Abhaengigkeiten + Begruendung. Blackbox-Tabelle Name|Verantwortung (aus W{n}).
4. Owner-/Boundary-Luecke (z.B. fremder Epic baut Teil) -> eigener subgraph + ungegroundet + OQ/PL-Backlink.
5. (FULL) Ebene-2/3 nur fuer wichtige/riskante Bausteine (Relevanz vor Vollstaendigkeit).
6. Schreibe + Self-Lint. SendMessage: "§5 Bausteinsicht: {n} Bausteine, {luecken} Owner/Boundary-Luecken."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| Baustein ohne Owner / fremder Epic (F5) | eigener subgraph "Owner?" + `[ungegroundet] (PL-y)` |
| Zerlegung nicht gegroundet | Ebene-1-Stub + grounding_status=leer |
| trivialer BL (LIGHT) | nur Ebene-1, keine tiefere Zerlegung (INV-A42B-PROP) |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_kontext` (§3) · `_arc42_berater_laufzeitsicht` (§6, dynamisch zu dieser statischen Sicht) ·
`arc42_mermaid_lint.py` · arc42-Template §5 · BL-378.
```
