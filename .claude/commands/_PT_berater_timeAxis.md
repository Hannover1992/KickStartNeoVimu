# _PT_berater_timeAxis (Pattern-Extraction Stage 3)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-02
op: PatternExtraction
phase: "3"
chain_position: "dritte Stage in _PT_orchestrate — nach clustering, vor contradiction"
feature_anchor: BL-237 (AK-CTX-PTO-3: git+PL-Timestamp-Korrelation, Reverts roh)
model_tier: middle  # sonnet — git-History-Lesen + temporale Korrelation
```

## Zweck (EIN Job)

**Lege die Zeitachse: ordne die Signale temporal und markiere Reverts roh.** Aus der git-History wird die
zeitliche Reihenfolge gebaut + Revert-Kandidaten (zurueckgebaute Aenderungen) roh erkannt; das wird mit den
PL-Timestamps der Signale korreliert. Wichtig (486-Lehre): das Pattern-Gold liegt in PL-Vorgaengen
(`PL_DRIFT-*`/`HOLD-*`), **NICHT** in git-revert-Commits — beide Achsen werden hier nur roh nebeneinander
gelegt, die Deutung (das WARUM) macht Stage 6 (forensic).

> **Single Unit of Work (/_help P-10):** liest git-History + PL-Timestamps, baut Timeline + reverts_raw,
> schreibt EINEN eigenen Slot (.timeAxis), stirbt. Keine Widerspruchs-Isolierung (→ Stage 4), keine
> Hypothesen (→ Stage 6), kein Library-Write.

## VERTRAG

```
LIEST:
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.gatherSignals.signals[]    (Signal-Timestamps + raw_ref fuer Korrelation)
    BERATER_OUTPUTS_PT.clustering.clusters[]       (Kompass — welche Cluster zeitlich zu ordnen sind)
  git log --since={since}/git diff (via Bash)      (temporale Ordnung + Revert-Kandidaten roh)
  WORKING_DIR via resolve_bl_path.py

SCHREIBT (NUR eigener Slot — INV-PTO-4 Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.timeAxis:
      timeline: [{
        seq,               # 0-basierter temporaler Index (aufsteigend)
        ref,               # commit_sha | PL-Item-ID
        kind,              # commit | pl_event
        timestamp,
        related_signal_ids # [signal.id, ...] — korrelierte Signale (via timestamp/raw_ref)
      }]
      reverts_raw: [{
        revert_ref,        # commit_sha des Revert-Kandidaten
        reverted_ref,      # vermuteter urspruenglicher commit (roh, ohne Deutung)
        source,            # git_revert_commit | pl_drift | pl_hold
        related_signal_ids
      }]
      counts: {timeline_entries, reverts_git, reverts_pl}
      status: DONE | EMPTY

  NICHT: Libraries/* , andere BERATER_OUTPUTS_PT-Slots, DF_BATCH_STATE.

INVARIANTEN:
  INV-TA-1 (Single-Writer): schreibt NUR BERATER_OUTPUTS_PT.timeAxis.
  INV-TA-2 (roh, keine Deutung): reverts_raw enthaelt NUR das DASS (zurueckgebaut?), nicht das WARUM (→ Stage 6).
  INV-TA-3 (PL-Gold-Prioritaet): PL_DRIFT-/HOLD-Vorgaenge werden als reverts_raw mit source=pl_* erfasst — NICHT mit git-revert-Commits verwechselt (486-Lehre: Gold sitzt im PL, nicht im git-revert).
  INV-TA-4 (Graceful): keine git-History / leere clustering → timeline=[], reverts_raw=[], status=EMPTY.
```

## Aufruf

```
Skill(_PT_berater_timeAxis, args="{BL_ID} [--since={git-ref}]")
```
Aufgerufen von `_PT_orchestrate` Stage 3 (Worker-Spawn). KEIN direkter User-Aufruf.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID); bl_folder = WORKING_DIR
   IDEMPOTENZ: IF BERATER_OUTPUTS_PT.timeAxis.status == DONE: RETURN (Resume-SKIP)

2. signals = .gatherSignals.signals[]; clusters = .clustering.clusters[]
   IF beide leer: SCHREIBE timeAxis={timeline:[], reverts_raw:[], status:EMPTY}; RETURN (INV-TA-4)

3. git-Achse:
   commits = Bash("git log --pretty=... [--since={since}]")
   FOR c IN commits: timeline.append({seq, ref:c.sha, kind:commit, timestamp:c.date, related_signal_ids: match_by_ts(c.date, signals)})
   reverts_git = Bash("git log --grep='^Revert'") → reverts_raw.append({source:git_revert_commit, ...})  # roh (INV-TA-2)

4. PL-Achse (INV-TA-3 — Gold-Prioritaet):
   FOR s IN signals WHERE s.raw_ref MATCHES PL_DRIFT-/HOLD-:
     reverts_raw.append({revert_ref:s.id, source:(PL_DRIFT? pl_drift : pl_hold), related_signal_ids:[s.id]})
     timeline.append({seq, ref:s.id, kind:pl_event, timestamp:s.timestamp, related_signal_ids:[s.id]})

5. timeline nach timestamp sortieren, seq neu vergeben. counts berechnen.

6. Schreibe BERATER_OUTPUTS_PT.timeAxis = {timeline, reverts_raw, counts, status: DONE}.
   SendMessage team-lead: "timeAxis: {timeline_entries} Timeline-Eintraege, {reverts_git} git-Reverts + {reverts_pl} PL-Reverts (roh, ohne Deutung)"
```

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| kein git-Repo / leere History | timeline aus PL-Events allein; reverts_git=0 |
| keine PL_DRIFT/HOLD-Signale | reverts_pl=0, nur git-Achse |
| alles leer | status=EMPTY, SendMessage "keine temporalen Daten" |

## Verwandt
- `_PT_berater_clustering` (Stage 2, liefert .clustering) · `_PT_berater_contradiction` (Stage 4, konsumiert .timeAxis) ·
  `_PT_berater_forensic` (Stage 6, deutet reverts_raw) · BL-237 Time-Axis + Revert-Detection (Anschluss 5)
