# /_W_atom_migration_orchestrator — Wahrheits-Atomisierungs-Migration (Thin-Invoker)

```yaml
status: active
version: 1.0.0
created: 2026-06-16
op: TruthMigration
phase: Meta
type: orchestration
chain_position: meta
feature_anchor: BL-386 / BL-309
model_tier: sonnet
related:
  - truth_schema
  - truth_resolver
  - truth_normalize
  - truth_atomizer
  - truth_atomize_batch
  - truth_backref_index
  - truth_dedup
  - truth_id_allocator
  - truth_lifecycle
  - truth_srs
  - truth_graph
  - truth_ripple
  - truth_readiness_report
  - truth_migrate_orchestrator
```

---

## Zweck

Model-basiert → wahrheits-basiert: jedes Model wird in **atomare Wahrheiten** (1 Wahrheit = 1 Datei)
zerlegt, das Model wird zur **generierten Index-View** (Rebuildability-LAW). Dieser Befehl ist ein
**Thin-Invoker** auf die DETERMINISTISCHEN Python-Tools (`truth_*`) — er re-implementiert KEINE Logik
als Pseudocode (das waere genau die Drift, die `truth_resolver` ersetzt hat).

**Doktrin:** read-only by default; der irreversible Cutover-Write ist **GEFENCED** (frische Session +
Backup, Vault nicht git, zero-error one-shot — BL-364). Voll: `{vault}/Konzepte/Truth-Migration-Runbook_2026-06-16.md`.

---

## Aufruf

```
/_W_atom_migration_orchestrator [mode=global|pilot|bl:{ticket}] [--check(default)|--write]

mode=global   ganzer Korpus (Vault-Backlog + Repo-Meta-Models)
mode=bl:{id}  ein BL/Ticket
mode=pilot    erste ready-Einheiten (Pilot-Trio)
--check       read-only Readiness/Report (DEFAULT)
--write       GEFENCED: nur in frischer Session + nach Backup + nach bewiesenem Pilot-Rollback
--normalize   BL-398: Stage 2 (truth_normalize) VOR atomize einhaengen (DRY-RUN, content-faithful-guarded)
```

---

## VERTRAG

```
LIEST:  {vault}/Backlog/**/2_Model/*.md + .claude/models/*.md  (Model-Kandidaten via census.is_candidate)
        {bl_folder}/{6_PL,3_Spec,4_K-Score}/*  (Referenzier-Surfaces fuer Inverse-Index R1)
SCHREIBT (read-only Pfad): .claude/output/*.json  (Readiness/Report inkl. QUARANTAENE-Manifest BL-395:
        per-Model + Gruende {truth_count_loss | low_byte_coverage | range_collapse | schema_error | roundtrip_fail})
SCHREIBT (--write, GEFENCED): {bl_folder}/2_Model/truths/{local_id}.md + {vault}/_meta/truth_alias_map.json
        + Model.md->View-Swap + {bl_folder}/2_Model/_legacy/*.pre_truth.md   (Cutover, Phase C)
RUFT (Python, deterministisch):
   truth_readiness_report.py   Pre-Flight GO/NO-GO (Capstone)   ← ZUERST
   truth_migrate_orchestrator.py  Spine: discover -> [normalize(Stage 2, --normalize) -> atomize ->
                                  census-gate -> roundtrip-gate -> apply_backrefs(R1)] -> dedup(R4)
                                  + referenced_by-Coverage
```

---

## Pipeline (was der Spine pro Einheit komponiert)

**5-Stage-Sequenz (BL-398):** `Stage 1 discover -> Stage 2 normalize -> Stage 3 atomize -> Stage 4 loss-gates/backrefs -> Stage 5 cutover`.

```
discover(Models)  [STAGE 1] -> FAN-OUT (parallel --jobs):
  normalize (truth_normalize, STAGE 2, BL-398, --normalize/DRY-RUN, content-faithful-guarded):
           driftendes Model (Bullet/Bold/bare/Table/Range) -> kanonische ### W{n}-HEADING-Form
           GENAU DANN wenn content-faithful (census-gleiche W-Def-Menge + 0 Content-Verlust).
           Laeuft auf einer KOPIE im _legacy-Scope (NIE in-place am Quell-Model -> DRY-RUN-Erhalt),
           Backup .pre_normalize.md (DISJUNKT zu Stage-5 .pre_truth.md, byte-identischer Rollback).
           Wirkung: Stage 3 sieht das normalisierte HEADING-Substrat -> format_hint=="HEADING" (schlank)
           statt SEGMENT-Verbatim-Fallback (Slimming, DoD-W.3 stage2_heading_gain). Nicht-faithful
           (z.B. No-W-Def-Prosa) -> Model UNANGETASTET, Stage 3 faellt auf SEGMENT (Quarantaene intakt).
  atomize  (truth_atomizer, STAGE 3: HEADING-Parse + Range-Member-Atomisierung (BL-391 A) + Roundtrip-Beweis
           + content_hash + lifecycle(R2) + keywords(R3) + Forward-Edges)
  -> LOSS-GATES (BL-395, ALLE muessen gruen sein, sonst Model -> QUARANTAENE, KEIN Write):
       (1) census-W-DEFINITIONEN >= atomisierte knots  [Truth-Count-Loss; census zaehlt Definitionen am
           Zeilenanfang Heading/Bullet/Tabelle/bare/Bold/yaml -> bricht den frueheren HEADING-Lockstep]
       (2) Byte-Coverage: generierte View >= 50% Quell-Body  [Content-Loss-FLOOR; BL-384 View-Rekonstruktion]
           + BL-396 v1 ✅ content-faithful Router (`_content_preserved`, Whitespace-norm-Gleichheit): ein
           HEADING-Model bleibt HEADING NUR wenn die View KEINEN Real-Content droppt (Preamble vor 1. W-Heading);
           sonst -> byte-identischer SEGMENT-Pfad. Der 0.5-Floor ist Backstop; der Router ist der scharfe Gate
           (Real-Korpus: content-loss=0 unter allen 215 ready). v2 offen = Slimming (Preamble-als-View-Knoten).
       (3) Range-Kollaps == 0  [### W16-W19 -> merged Blob; BL-391 B Span-Signal]
       (+) roundtrip-gate (parse(alt)==parse(View)) + schema-gate (0 ERROR)
  -> apply_backrefs (truth_backref_index R1: referenced_by[] aus PL/Spec/K-Score/edges)
KORPUS: dedup_stats(R4) + Graph + SRS + QUARANTAENE-Manifest (quarantine_reasons je nicht-ready Model)
        -> readiness_report GO/NO-GO  (GO nur wenn JEDE Einheit ready = alle Gates gruen)
[B2 DONE = Recovery, 51e37d0/a5a5a7e]: Segment-Modell atomisiert die quarantaenierten Nicht-HEADING-Models
        verlustfrei (Bullet/Tabelle/yaml, View==Source byte-identisch, _verbatim-Body) -> 54 recovert ->
        215/223 ready; 8 genuine no-W-def bleiben quarantaeniert by-design.
[--write, Phase C/gefenced]: write truths/ NUR fuer ready-Models (QUARANTAENE ausgeschlossen — _process_one
        blockt physisch) -> cutover_model B2-aware (SEGMENT=build_segment_view byte-Gate / HEADING=parse-Gate,
        refuse-gate==quarantine_reasons) -> alias-map -> Model->View-Cutover -> --rollback byte-identisch (74e0c52)
```

---

## INVARIANTEN

```
INV-MIG-WRITE-FENCE: --write NUR in frischer Session + nach Vault-Backup + nach bewiesenem
                     Pilot-Rollback (INV-MIG-11). Aus geladenem/Marathon-Kontext: read-only.
INV-MIG-NO-SILENT-LOSS (BL-395 GEHAERTET): DREI unabhaengige Loss-Gates blocken den Write — der census==
                     atomizer-HEADING-Cross-Check ALLEIN war lockstep-blind (beide unterzaehlten Nicht-
                     HEADING-Formate identisch auf 0 -> 41 Models/1208 Truths still als ready durchgewunken).
                     (1) census zaehlt W-DEFINITIONEN >= knots, (2) Byte-Coverage View>=50% Quell-Body,
                     (3) Range-Kollaps==0. Verletzung einer -> QUARANTAENE.
                     BL-396 v1 ✅ (`7528a47`): content-faithful Router (Whitespace-norm-Gleichheit) faengt den
                     HEADING-Preamble-Verlust, den der 50%-Floor durchliess -> Preamble-Models gehen byte-identisch
                     auf SEGMENT. Real-Korpus content-loss=0 unter allen 215 ready. v2 offen = Slimming-Enrichment.
INV-MIG-QUARANTINE (BL-395): die Quarantaene ist ein DETERMINISTISCHER Maschinen-Output (quarantine_reasons),
                     KEIN Lead-Augenmass. Cutover-Write-Scope = ready-Set; Quarantaene ausgeschlossen bis B2
                     sie verlustfrei recovert. Per-Model-Override VERBOTEN (vernichtete sonst bestaetigte Wahrheiten).
INV-MIG-PILOT-FIRST: Wellen erst NACH Pilot-Trio mit byte-identischem Rollback-Beweis.
INV-MIG-ACTIVE-EXCL: aktive BLs aus jeder Welle exkludiert (per-BL Aktivitaets-Check).
INV-MIG-DCS-LAST: DCS-Vault zuletzt (Quiescenz + 2 gruene Runs).
INV-MIG-VIEW-LAW: Model.md ist generierte View; jede abgeleitete Sicht (K-Score/SRS/Gap/arc42)
                  muss aus den Wahrheiten rebuildbar sein, sonst Bug (Rebuildability-LAW, BL-384).
INV-MIG-NORMALIZE (BL-398, Stage 2): die Vorab-Normalisierung ist content-faithful-GUARDED — kein Persist
                  ohne census-gleiche W-Def-Menge + 0 Content-Verlust (CUTOVER-SAFE-1-Analogon). Sie laeuft
                  auf einer KOPIE (DRY-RUN: Quell-Model byte-identisch), Backup .pre_normalize.md (DISJUNKT zu
                  Stage-5 .pre_truth.md). Nicht-faithful -> Model unangetastet, Stage 3 SEGMENT-Pfad. normalize=
                  False (Default) -> Verhalten UNVERAENDERT (Regressionsschutz, read-only-first erhalten).
INV-MIG-THIN: dieser Befehl ruft die Python-Tools; er re-implementiert keine Logik als Pseudocode.
INV-MIG-GATE (BL-309 Gate-Strasse): vor JEDEM `--write` MUSS `truth_gate_check.py` exit 0 liefern
                  (10 Gates gruen) — als deterministischer MASCHINEN-Beweis, nicht Lead-Augenmass. Ein
                  rotes Gate = NO-GO, kein Write. Die Gate-Strasse ist read-only (Write-Pfad auf temp).
```

---

## Pre-Flight: die GATE-STRASSE (immer zuerst, read-only, Schritt fuer Schritt)

DER kanonische Vor-Cutover-Prozess = `truth_gate_check.py` (10 Gates, Maschinen-GO/NO-GO, NICHT Lead-Augenmass).
READ-ONLY gegen den Quell-Vault; die Write-Pfad-Gates (Cutover INV-MIG-11 + disk-rebuild BL-384) laufen auf
TEMP-Kopien. exit 0 = EXTRACTION-GO. Vor JEDEM `--write` zu fahren + per-Gate gruen zu sehen:

```
py -3 .claude/scripts/truth_gate_check.py --vault {VAULT} --repo-models .claude/models --jobs 6 --out {report}.json

  Gate  1 discovery_dedup_inv_mig_10   cross-root-Dedup, 0 ID-Kollisionen
  Gate  2 roundtrip_inv_mig_2_3        ready-Set roundtrippt (SEGMENT byte- / HEADING parse-identisch)
  Gate  3 completeness_census_bl395a   census-W-Def <= knots
  Gate  4 content_preservation ...     BL-395(b)+BL-396: content-loss==0 (SEGMENT byte- / HEADING content-gleich)
  Gate  5 range_collapse_bl391         0 merged Range-Bloecke
  Gate  6 schema_clean                 0 ERROR in ready-Truths
  Gate  7 quarantine_determinism       ready+quarantine==total, jede Quarantaene mit Gruenden (Maschinen-Output)
  Gate  8 cutover_safety_inv_mig_11    ready->verlustfreier Swap; quarantine->REFUSED; Rollback byte-identisch (temp)
  Gate  9 disk_rebuild_bl384           ready-Truths rekonstruieren die View aus DEN DATEIEN byte/parse-identisch
  Gate 10 dedup_soundness_r4           Dup-Gruppen = genuine alias-kollabierbare Cross-File-Kopien

  Stand 2026-06-17f (OmniCommand-Pilot, self-tested): **10/10 Gates PASS, EXTRACTION-GO=True**, 215/223 ready,
  content-loss=0, 8 genuine quarant. (truth_readiness_report bleibt als aggregierter Report-Companion.)
  GO-fuer-`--write`=False NUR wegen (1) Owner-Scope-out der 8 + (2) frische Session (BL-364). ⛔ DCS LIVE -> Pilot zuerst.
```

Status: read-only Spine + Capstone + 3-dim Loss-Gate (BL-395) + QUARANTAENE-Manifest + B2-Recovery + B2-aware
cutover_model (74e0c52) + content-faithful Router (BL-396 v1, 7528a47) LIVE (OmniCommand-Pilot 215/223 ready,
**content-loss=0**, 8 genuine quarantaeniert). Cutover-MECHANIK bewiesen (Real-Korpus: 215/215 disk-rebuild
identisch, 8/8 REFUSED). Migration jetzt EHRLICH verlustfrei. Offen: BL-396 v2 (Slimming-Enrichment), BL-387
(Konsumenten via Resolver), BL-388 (Ripple), BL-389 (Such-Index). Frische-Session-`--write` (Runbook) erst nach
Owner-Scope-out der 8 — und NIE in DCS/DCSRE solange der Motor dort laeuft (quiescenz-gated, BL-393).

**Cutover-Treiber:** `truth_pilot_cutover.py` (DRY-RUN default, INV-MIG-GATE intern, Owner-Scope-out der 8 +
`_legacy`-Rollback, `--limit` Pilot-Trio, `--confirm` Pflicht). Orchestrator-`--write` bleibt read-only-Fence;
DER Treiber ist der EINE gegatete Write-Pfad. **Turnkey-Runbook (frische Session):**
`{vault}/Konzepte/Truth-Migration-Runbook_2026-06-16.md` — Backup → Gate-Strasse 10/10 → Dry-Run-Plan →
Pilot-Trio `--limit 3 --confirm` → Rollback-Beweis → Welle → DCS zuletzt. Pilot-Dry-Run: 214 Write-Scope / 9 exkl.
