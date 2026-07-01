# _arc42_berater_querschnitt (arc42 §8 Querschnittliche Konzepte — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: "arc42/§8-Querschnitt"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378
model_tier: ceiling  # opus — NUR die wichtigsten Querschnitts-Konzepte waehlen (Anti-Zeremonie) = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §8 Querschnittliche Konzepte** als View: übergreifende, prinzipielle Regelungen, die an
mehreren Bausteinen relevant sind — z.B. Domänenmodell (→ verweist auf §8-Datenmodell/ERD), Patterns,
Safety/Security & AuthZ, Persistence, Logging/Tracing, Error-Handling, Business-Rules. **NUR die wichtigsten**
(Template-Imperativ: "auf keinen Fall alle Themen"). Quelle = PatternLibrary + SemanticLibrary + crosscutting W{n}.

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.{specParse, domainBrief}, A_PIPELINE_STATE
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md + 3_Spec/*_Spec.md   (querschnittliche W{n}/Regelungen)
  {VAULT}/Libraries/PatternLibrary/_index.md + SemanticLibrary/_index.md   (read-only; Bestands-Konzepte)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — Cross-Ref)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/08_querschnitt.md
    Frontmatter: {section_nr: 8, tier_min: full, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: [mindmap|flowchart]}
    Body: mindmap (Konzept-Ueberblick) + je wichtigem Konzept ein Level-2-Abschnitt (kurz, opt. flowchart).
          Verweist fuer das Domaenen-Datenmodell auf `08_datenmodell.md` (kein Doppel).

SCHREIBT NICHT: andere arc42/-Sektionen (inkl. 08_datenmodell.md — das ist _arc42_berater_datenmodell), Manifest-State, Wahrheiten.

INVARIANTEN: INV-A42B-1 (NUR 08_querschnitt.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat) ·
  INV-A42B-4 (Lint-konform) · INV-A42B-5 (W7). INV-A42B-PROP (NUR wichtigste Konzepte, Anti-Zeremonie).
```

## Mermaid-Form (Konzept-Überblick)
```
mindmap
  root((Querschnitt))
    Security
      AuthZ
    Persistence
    Logging
    Error-Handling
```

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/08_querschnitt.md.
2. snap = read-only Model/Spec(querschnittliche Regelungen) + PatternLibrary + SemanticLibrary + domainBrief + Gap/PL.
3. Waehle NUR die wichtigsten Konzepte fuer DIESEN BL (nicht alle). Je Konzept: kurzer Level-2-Abschnitt + model_ref.
4. mindmap-Ueberblick. Domaenen-Datenmodell -> Verweis auf 08_datenmodell.md. Ungegroundetes Konzept -> Platzhalter + OQ/PL.
5. Schreibe + Self-Lint. SendMessage: "§8 Querschnitt: {n} Konzepte (wichtigste)."
```

## Graceful Degradation / Lücke = sichtbare Frage
| Situation | Verhalten |
|---|---|
| keine querschnittlichen Konzepte relevant | knapper Stub + Verweis auf §8-Datenmodell, grounding_status=teil |
| Konzept vermutet, nicht belegt | Level-2-Abschnitt mit `[ungegroundet] (OQ/PL)` |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_datenmodell` (§8-Datenmodell, Schwester) · `_A_berater_domainBrief` · PatternLibrary/SemanticLibrary · arc42-Template §8 · BL-378.
```
