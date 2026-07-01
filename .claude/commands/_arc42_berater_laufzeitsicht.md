# _arc42_berater_laufzeitsicht (arc42 §6 Laufzeitsicht — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§6"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — architekturrelevante Szenarien auswaehlen = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §6 Laufzeitsicht** als View: konkrete **Abläufe/Szenarien** zwischen Bausteinen (wichtige
Features, Interaktionen an externen Schnittstellen, Betrieb/Admin, Fehler/Ausnahmen). **Auswahlkriterium =
Architekturrelevanz**, NICHT alle Abläufe. **Lücken-Detektor:** ein Feld/Feature OHNE Befüll-/Ablauf-Sequenz
= fehlendes Szenario (DCSRE-14-F4-Klasse: Freigabedatum/Quarantänegrund ohne Workflow); ein Status-Vokabular-
Konflikt = undefinierte Übergänge im Zustandsautomaten (F1-Klasse).

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.akExtraktion (AKs = Q42-Szenarien!), specParse, A_PIPELINE_STATE
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Abläufe, Interaktionen)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (beteiligte Bausteine — Konsistenz zu §5)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — fehlende Workflows/Szenarien)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/06_laufzeitsicht.md
    Frontmatter: {section_nr: 6, tier_min: standard, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [sequenceDiagram|stateDiagram-v2]}
    Body: pro architekturrelevantem Szenario ein Abschnitt (Mermaid + kurze Erlaeuterung der Besonderheiten).

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten.

INVARIANTEN: INV-A42B-1 (NUR 06_laufzeitsicht.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat) ·
  INV-A42B-4 (Lint-konform) · INV-A42B-5 (W7). INV-A42B-AK: AKs sind die primaere Szenario-Quelle (AK = Q42-Szenario 1:1).
```

## Mermaid-Form
```
sequenceDiagram
  participant U as Nutzer
  participant SYS as System
  participant VV as VV-Quelle
  U->>SYS: Anfrage Übersicht
  SYS->>VV: Live-Join (1:n GroupJoin)
  VV-->>SYS: Treffer (Orphan-Fallback bei 0)
  SYS-->>U: Liste
  Note over SYS: [ungegroundet: Befüll-Workflow Freigabedatum?] (siehe OQ-DM-2 / PL-AK-04)
```
(`sequenceDiagram` fuer Interaktionen; `stateDiagram-v2` fuer Status-Lebenszyklen — undefinierte Uebergaenge =
F1-Vokabular-Konflikt sichtbar.)

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/06_laufzeitsicht.md.
2. snap = read-only AKs + Spec(Abläufe) + Model(Bausteine) + Gap/PL.
3. szenarien = architekturrelevante Abläufe aus AKs/Spec (NICHT alle — Relevanz). Je Szenario: Akteure + Sequenz.
4. Feld/Feature ohne Befuell-Sequenz (F4) -> Note/Platzhalter `[ungegroundet: Workflow?] (OQ/PL)`.
   Status-Vokabular-Konflikt (F1) -> stateDiagram mit markierten undefinierten Uebergaengen.
5. Schreibe + Self-Lint. SendMessage: "§6 Laufzeit: {n} Szenarien, {luecken} fehlende Workflows (OQ/PL)."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| Feld ohne Befüll-Prozess (F4) | Note im Szenario + `[ungegroundet: Workflow?] (OQ-DM-2 / PL-y)` |
| Status-Vokabular-Konflikt (F1) | stateDiagram mit markiert-undefinierten Übergängen |
| keine architekturrelevanten Abläufe | grounding_status=leer, Hinweis "keine relevanten Laufzeit-Szenarien gegroundet" |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_bausteinsicht` (§5, statisch) · `_arc42_berater_datenmodell` (§8) ·
`arc42_mermaid_lint.py` · arc42-Template §6 · BL-378.
```
