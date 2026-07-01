# _arc42_berater_randbedingungen (arc42 §2 Randbedingungen — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§2"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — relevante Constraints von Rauschen trennen = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §2 Randbedingungen** als View: Vorgaben, die Entwurf/Implementierung/Prozess einschränken —
**technisch / organisatorisch / politisch** (einfache Tabellen mit Erläuterung). Quelle = Spec-Constraints +
Projekt-Konventionen (CLAUDE.md/Invarianten) + session_params. Keine Mermaid (reine Tabelle).

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.specParse, A_PIPELINE_STATE
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Constraints/Vorgaben)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (technische Randbedingungen)
  Projekt-Konventionen (z.B. CLAUDE.md-Invarianten, Namens-/Doku-Konventionen) — read-only
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Cross-Ref)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/02_randbedingungen.md
    Frontmatter: {section_nr: 2, tier_min: full, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: []}
    Body: 3 Tabellen (technisch | organisatorisch | politisch), je Randbedingung + Erlaeuterung.

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten.

INVARIANTEN: INV-A42B-1 (NUR 02_randbedingungen.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat) ·
  INV-A42B-4 (Lint-konform, hier i.d.R. keine Diagramme) · INV-A42B-5 (W7).
```

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/02_randbedingungen.md.
2. snap = read-only Spec(Constraints) + Model + Projekt-Konventionen + Gap/PL.
3. Klassifiziere Constraints -> technisch / organisatorisch / politisch. Je Eintrag: Randbedingung + Erlaeuterung + model_ref.
4. Vermutete-aber-ungegroundete Randbedingung -> `[ungegroundet] (OQ/PL)` statt erfinden.
5. Schreibe 3 Tabellen. SendMessage: "§2 Randbedingungen: {n} Constraints ({t}/{o}/{p})."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| keine Constraints gegroundet | leere Tabellen + Hinweis "keine Randbedingungen gegroundet", grounding_status=leer |
| Constraint vermutet, nicht belegt | `[ungegroundet] (OQ/PL)` |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_loesungsstrategie` (§4, respektiert Constraints) · arc42-Template §2 · BL-378.
```
