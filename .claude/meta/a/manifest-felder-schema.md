---
name: A_PIPELINE_STATE Manifest-Felder Schema
description: Zentrale Schema-Doku fuer A-Pipeline-Manifest-Felder post-BL-142
type: schema
version: 1.0.0
date: 2026-04-26
related_bl: BL-142
status: NORMATIV
---

# A_PIPELINE_STATE — Manifest-Felder-Schema

## Zweck dieser Datei

Diese Datei ist die **alleinige normative Referenz** fuer welche Felder die
A-Pipeline ins Manifest schreibt und welche Caller sie konsumieren. Vor jeder
Aenderung am A-Output muss diese Datei aktualisiert werden. Vor jedem neuen
Caller, der A-Manifest-Felder liest, muss er hier eingetragen werden.

## Praemisse: A schreibt NUR Roh-Daten (INV-A-RAW-DATA)

A liefert kein Mode-Ranking, keine Empfehlung, keinen Trend, keine
Switch-Logik. Solche Bewertungen gehoeren zu SDF C3 (Mode-Decision) bzw. SC
(Forschungs-Trends). A ist ein Aggregator von Roh-Daten — nicht mehr.

## Pflicht-Felder (geschrieben von A nach BL-142)

A_PIPELINE_STATE-Block, Phase 4.2a (Metadaten-Aggregation):

| Feld | Typ | Quelle | Wertebereich |
|------|-----|--------|--------------|
| `aggregat_k_score` | int | K-Score-Datei (Mittel) | 0-100 |
| `aggregat_srs_score` | int | K-Score-Datei (Mittel SRS pro AK) | 0-100 |
| `aggregat_gap_percent` | int | Gap-Datei | 0-100 |
| `aggregat_model_maturity` | int | Model.md (Reife-Heuristik) | 0-100 |
| `aggregat_freiheitsgrade` | int | Spec.md (Anzahl Loesungswege) | 1-N |
| `aggregat_is_meta_command` | bool | Task-Klassifikation | true | false |
| `unreife_typ` | enum | Phase 4.1c Schwelle >= 2, INV-3 Default INTERN | EXTERN | INTERN |
| `last_sync_commit` | str | Phase 4.4 Git-Tracking | Git-Hash |
| `phase` | enum | Universal-Lifecycle Stufe 5 | INIT | RUNNING | COMPLETED | ABORTED |
| `entry_point` | str | Routing Phase 5 | BDF | IDF |
| `bl_id` | str | Backlog Phase 4.2b | BL-{N} |
| `team_name` | str | Universal-Lifecycle Stufe 2 | a-{NAME} |

**Anmerkung zu `aggregat_freiheitsgrade`:** Diese ist eine reine Anzahl, keine
Bewertung. Hohe Anzahl = viele moegliche Loesungswege im Spec. SDF C3 liest dies
als Mode-Entscheidungs-Eingang.

## Verbotene Felder (geloescht durch BL-142)

A schreibt diese Felder NICHT mehr:

| Feld | Status | Migrations-Hinweis |
|------|--------|--------------------|
| `recommendation` | GELOESCHT | Mode-Decision wandert vollstaendig nach SDF C3 |
| `mode` | GELOESCHT | Wie `recommendation` |
| `complexity_current` (in A_PIPELINE_STATE) | GELOESCHT | SC-internal-Feld bleibt; nur A's Schreib-Stelle entfaellt |
| `complexity_grob` | UNVERAENDERT | BDF-Batch-Konzept, NICHT Teil von BL-142 |
| `unreife_typ_kandidat` | UMBENANNT | Heisst jetzt `unreife_typ` ohne Suffix |
| `gap_percent` (in A_PIPELINE_STATE) | UMBENANNT | Heisst `aggregat_gap_percent` |
| `model_maturity` (in A_PIPELINE_STATE) | UMBENANNT | Heisst `aggregat_model_maturity` |
| `open_questions` | OPTIONAL | Bleibt erhalten als Hinweis-Feld; SDF C3 ignoriert es |
| `completion_signal` | UNVERAENDERT | Universal-Lifecycle, kein BL-142-Cleanup |

## Caller-Map (post-BL-142 Soll)

### A_PIPELINE_STATE-Schreib-Stelle

- `_A_orchestrate.md` Phase 4.2a (Metadaten-Aggregation)
- `_A_orchestrate.md` Phase 4.4 (Git-Tracking → `last_sync_commit`)
- `_A_orchestrate.md` Phase 5 (Routing → `entry_point`)

### A_PIPELINE_STATE-Lese-Stellen

| Caller | Liest | Zweck |
|--------|-------|-------|
| `_BDF_orchestrate.md` Phase 2 | `aggregat_k_score`, `aggregat_model_maturity` | Refine-Loop-Decision |
| `_SDF_orchestrate.md` Phase 1 (C3) | alle 6 `aggregat_*` + `unreife_typ` | Mode-Decision M1-M9 |
| `_IDF_orchestrate.md` Phase 1 INIT | `aggregat_*`, `bl_id`, `last_sync_commit` | State-Resume |
| `_backlog.md` BL-Item-Generation | alle Felder | BL-Frontmatter |

### Verbotene Lese-Caller

Diese Caller existieren post-BL-142 NICHT:

- `_SC_orchestrate.md` A-Guard (Z.506-520, 602-610) — geloescht (kein
  Mode-Vergleich mehr; SDF C3 ist alleinige Quelle)
- `_A_postRoute.md` — Datei geloescht (Doppelung 3 Routing/Dispatch)

## Verwandte Felder (NICHT A-Output, dokumentiert zur Abgrenzung)

Diese Felder existieren im Manifest, sind aber nicht von A geschrieben:

| Feld | Schreiber | Lebenszyklus |
|------|-----------|--------------|
| `complexity_current` (SC-Block) | `_SC_ergebnis.md` | Per SC-Zyklus |
| `complexity_trend` | `_SC_ergebnis.md` | Per SC-Zyklus |
| `complexity_switch_recommendation` | `_SC_ergebnis.md` | Per SC-Zyklus |
| `complexity_auto_tdd_pending` | `_SC_ergebnis.md` | Per SC-Zyklus |
| `complexity_grob` | `_BDF_batchPlan.md` | Per BDF-Batch |
| `tdd_alarm.recommendation` | `_TDD_orchestrate.md` | TDD-internal |
| `pruning_recommendation` | `_SDF_berater_validator.md` | SDF Phase 0.2 |
| `mode_switch_recommendation` | `_SC_qualityGate.md` | Per Gate 6 |
| `BERATER_OUTPUTS.*.pruning_recommendation` | SDF-Berater | SDF Phase 0 |

**Wichtig:** Trotz Namens-Aehnlichkeit haben `recommendation` (A's Output, in
BL-142 geloescht) und z.B. `tdd_alarm.recommendation` oder
`mode_switch_recommendation` **nichts miteinander zu tun**. Sie leben in
verschiedenen Manifest-Bloecken mit eigenen Schreibern und eigenen Konsumenten.
Verwechslung verursacht falsche Caller-Audits.

## Anchor-Konvention (BL-142 Spec v1.3)

Felder, die auf Spec/Model/K-Score zeigen, nutzen Anker statt Zeilennummern:

```yaml
spec_anchor:  { section: "## Phase A AK-A-1", ak_id: "AK-A-1" }
model_anchor: { tc_id: "TC-2", w_id: "W-03" }
```

Zeilennummern sind verboten (fragil bei Edits). Anchors zeigen auf
Markdown-Header oder explizite ID-Tokens.

## Regel "Pflicht-Werkstoff vs Optional-Hint"

Pflicht-Werkstoff = Felder, die SDF C3 ohne weitere Quellen lesen koennen muss.
Das sind die 6 `aggregat_*` + `unreife_typ` + `bl_id`. Diese 8 Felder muessen
immer gesetzt sein, wenn `phase = COMPLETED`.

Optional-Hint = `open_questions`, `entry_point`, `team_name` — duerfen leer
sein. SDF C3 darf hier `null` annehmen ohne Fehler.

## Verifikation post-Implementierung

Nach BL-142-Implementation:

- Datei `BL-142-Spec.md` v1.3 RF-A-RAW-DATA + INV-A-RAW-DATA erfuellt.
- Grep `git grep "A_PIPELINE_STATE.recommendation"` liefert leer.
- Grep `git grep "unreife_typ_kandidat"` liefert leer.
- Grep `git grep "complexity_current"` liefert nur `_SC_*`-Treffer.
- Grep `git grep "aggregat_"` liefert mindestens die in der Caller-Map
  dokumentierten Caller.
- A-Pipeline-Self-Smoke-Test auf BL-142 selbst gruen.

## Aenderungs-Protokoll

| Version | Datum | Aenderung |
|---------|-------|-----------|
| 1.0.0 | 2026-04-26 | Initial-Schema (BL-142 Phase 0 Pre-Flight) |
