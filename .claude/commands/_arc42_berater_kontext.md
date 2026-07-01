# _arc42_berater_kontext (arc42 §3 Kontextabgrenzung — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§3"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — Systemgrenze ziehen + relevante Nachbarn waehlen = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §3 Kontextabgrenzung** als View auf die schon-gepflegten Wahrheiten: das System als **Blackbox**
gegen alle Kommunikationspartner (Nachbarsysteme + Benutzerrollen), externe Schnittstellen, Verantwortlichkeit/scope
— **3.1 fachlich** (Kommunikationsbeziehungen, fachliche Ein-/Ausgaben) + **3.2 technisch** (Kanäle, Mapping
fachlich→technisch). **Lücken-Detektor:** ein Daten-/Schnittstellen-Element OHNE eingehende Kante = sichtbares
Waisen-Attribut → markierte offene Frage (DCSRE-14-F2-Klasse: "DAS-Kennzeichen ohne Quelle").

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.dependencyAnalyzer (file_index/externe Kanten = Nachbarsysteme),
                              BERATER_OUTPUTS.specParse (Schnittstellen), A_PIPELINE_STATE
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (Systemgrenze, Verantwortung — W{n})
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (externe fachl./techn. Schnittstellen, Kanäle)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/*  + 6_PL/*    (OQ + BLOCKED-PL — fuer Luecken-Cross-Ref)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/03_kontext.md
    Frontmatter: {section_nr: 3, tier_min: light, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [flowchart]}
    Body: 3.1 Fachlicher Kontext (Diagramm + Tabelle: Kommunikationsbeziehung|Eingabe|Ausgabe) +
          3.2 Technischer Kontext (Kanal/Protokoll + Mapping fachl.→techn.)

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten (Model/Spec/PL), {bl}/_manifest.md.

INVARIANTEN:
  INV-A42B-1 (File-Single-Writer): NUR 03_kontext.md.
  INV-A42B-2 (Read-Only): keine Wahrheits-/Manifest-Edits.
  INV-A42B-3 (kein Halluzinat): gegroundete Aussage traegt model_refs; fehlt eine Wahrheit ->
             `> [ungegroundet: <was>] (siehe OQ-x / PL-y)` — NIE erfundenes Grounding.
  INV-A42B-4 (Lint-konform): jeder ```mermaid-Block besteht arc42_mermaid_lint.py.
  INV-A42B-5 (W7): kein Sub-Spawn.
```

## Mermaid-Form
```
flowchart LR
  Admin[Administrator] -->|fachl. Eingabe| SYS[(System)]
  SYS -->|Ausgabe| Nachbar1[Nachbarsystem 1]
  QuelleX -. "[ungegroundet: Quelle?] (PL-y)" .-> SYS
```
(System als EINE Blackbox; Nachbarn + Rollen als Knoten; ungegroundete Eingangs-Quelle als gestrichelte
Kante mit OQ/PL-Backlink. Reines Mermaid `flowchart` — KEIN C4.)

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/03_kontext.md
2. snap = read-only Model/Spec/depAnalyzer/Gap/PL.
3. partner = externe Nachbarn + Benutzerrollen (aus depAnalyzer externe Kanten + Spec-Schnittstellen).
4. FOR jede fachl. Ein-/Ausgabe: groundbar gegen Spec/Model? -> model_refs; sonst ungegroundet-Platzhalter + OQ/PL-Backlink.
5. Schreibe 03_kontext.md (3.1 + 3.2 + Mermaid). grounding_status = voll(0 Luecken)|teil|leer.
6. Self-Lint (arc42_mermaid_lint.py ziel). SendMessage team-lead: "§3 Kontext: {partner} Partner, {luecken} Luecken (OQ/PL-verlinkt)."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| Schnittstelle ohne Quelle (F2-Klasse) | gestrichelter Knoten + `[ungegroundet: Quelle?] (siehe OQ/PL)` |
| keine Nachbarsysteme gegroundet | minimaler Blackbox-Kontext + grounding_status=leer |
| Rolle ohne Zugriffs-Kante (F7-Klasse) | Akteur ohne Kante = sichtbares "kein Zugriff?" |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_datenmodell` (§8, teilt F2-Quellen-Luecke) ·
`arc42_mermaid_lint.py` · arc42-Template §3 · BL-378.
```
