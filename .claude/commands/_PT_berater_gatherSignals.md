# _PT_berater_gatherSignals (Pattern-Extraction Stage 1)

```yaml
type: berater
status: draft
version: 0.2.0
created: 2026-06-02
updated: 2026-06-20
op: PatternExtraction
phase: "1"
chain_position: "erste Stage in _PT_orchestrate — vor clustering"
feature_anchor: BL-237 (Anschluss 3: Buendelung der verstreuten Signale) + BL-427 (commit_sweep 5. Signal-Quelle)
model_tier: middle  # sonnet — Multi-Quellen-Scan + Normalisierung
```

## Zweck (EIN Job)

**Sammle ALLE Pattern-Lernsignale eines BL an EINEM Ort.** Heute sind sie verstreut (BL-237-Befund):
das Nervensystem schreibt an vier getrennte Stellen, niemand erntet sie zusammen. Diese Stage buendelt
sie in eine normalisierte Signal-Liste — die Grundlage fuer Clustering/Forensik/Materialisierung.

> **Single Unit of Work (/_help P-10):** liest vier Quellen, normalisiert, schreibt EINEN Slot, stirbt.
> Kein Clustern (→ Stage 2), kein Klassifizieren (→ Stage 5), kein Schreiben in Libraries.

## Die 5 Signal-Quellen (heute verstreut)

| Quelle | Signal-Typ | Bedeutung |
|---|---|---|
| `{bl_folder}/6_PL/{bl_id}-parking-lot.md` | **PL-Items** (inkl. `[PatternConformance]`, `[PT-Kandidat]`, `PL_DRIFT-*`, `HOLD-*`, `CONF-N`) | Geparkte Erkenntnisse = der Haupt-Lernstrom |
| `_manifest.md` → `s{N}_pt_signal: KEIN_PATTERN` + `s{N}_pt_signal_slices` | **Consult-Gap** | „hier wurde ein Pattern gebraucht, aber keins gefunden" |
| `_manifest.md` → `PATTERN_CONFORMANCE_STATE` + `ARCHITECT_ESCALATION_QUEUE` | **Conformance-Verletzung** | „Code hielt sich nicht ans Pattern" (WARN/BLOCKER) |
| `.claude/wissen/pattern-usage.log` (falls vorhanden) | **Nutzungs-Events** (USED/VERIFIED/BROKEN/KEIN_PATTERN) | die ungenutzte Reifungs-Nahrung (BL-237: laeuft heute kaum) |
| `git log` (Ticket/Branch-Filter, NUR bei `--ticket`/`--branch`-Args) | **reviewed_change** | abgenommene Kollegen-Idiome / Erfolgs-Schritte (abgenommener Code = Truth-Quelle, gleichrangig zur Parking-Lot) |

## VERTRAG

```
LIEST:
  {bl_folder}/6_PL/{bl_id}-parking-lot.md
  {bl_folder}/_manifest.md
    s{N}_pt_signal / s{N}_pt_signal_slices / s{N}_pt_signal_at  (alle N)
    PATTERN_CONFORMANCE_STATE.{blocker_count,warn_count,findings_total}
    ARCHITECT_ESCALATION_QUEUE[]
  .claude/wissen/pattern-usage.log         (Graceful: fehlt oft — dann leer)
  WORKING_DIR via resolve_bl_path.py
  git log / git show                       (NUR bei --ticket / --branch-Args; sonst nicht aufgerufen)

SCHREIBT (NUR eigener Slot — INV-PTO-4 Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.gatherSignals:
      signals: [{
        id,                # stabile Signal-ID (z.B. PL-FE-F6, CONF-3, KEIN_PATTERN@s3, USAGE-BROKEN@PT-DOM-005, COMMIT-abc1234)
        source,            # parking_lot | kein_pattern | conformance | usage_log | commit_sweep
        signal_type,       # finding | gap | violation | revert | usage | reviewed_change
        raw_ref,           # Datei:Zeile / PL-Item-ID / Pattern-ID / vollstaendiger Commit-Hash
        text,              # 1-2 Saetze Roh-Inhalt (fuer A-Pipeline-Harvest spaeter)
        file_refs: [],     # betroffene Code-Dateien (falls erkennbar)
        pattern_id_hint,   # referenziertes Pattern (falls Conformance/Usage) oder null
        timestamp          # falls bekannt (fuer Stage 3 Time-Axis)
      }]
      counts: {parking_lot, kein_pattern, conformance, usage_log, commit_sweep, total}
      status: DONE | EMPTY

  NICHT: Libraries/* , andere BERATER_OUTPUTS_PT-Slots, DF_BATCH_STATE.

INVARIANTEN:
  INV-GS-1: NUR sammeln + normalisieren — KEINE Bewertung/Klassifikation (das ist Stage 5).
  INV-GS-2: Roh-Text erhalten (kein Glaetten) — die A-Pipeline-findingsExtraction harvestet ihn spaeter (BL-237 raw_source).
  INV-GS-3: Graceful — fehlende Quelle (z.B. keine pattern-usage.log) → counts=0, kein Fehler.
  INV-GS-4: Dedup nach raw_ref (dasselbe PL-Item nicht doppelt, wenn es in 6_PL UND Conformance-State steht).
  INV-GS-5: commit_sweep NUR aktiv wenn --ticket oder --branch Arg uebergeben; ohne diese Args → commit_sweep=0, reiner PL-Modus (Abwaertskompatibilitaet garantiert).
```

## Aufruf

```
Skill(_PT_berater_gatherSignals, args="{BL_ID}")
Skill(_PT_berater_gatherSignals, args="{BL_ID} --ticket={PRÄFIX}")
Skill(_PT_berater_gatherSignals, args="{BL_ID} --ticket={PRÄFIX} --author={substr}")
Skill(_PT_berater_gatherSignals, args="{BL_ID} --branch={range}")
```
Aufgerufen von `_PT_orchestrate` Stage 1 (Worker-Spawn). KEIN direkter User-Aufruf.
Optionale Args `--ticket`, `--author`, `--branch` aktivieren ausschliesslich Quelle E (commit_sweep) — ohne sie unveraendertes Verhalten.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID); bl_folder = WORKING_DIR
   IDEMPOTENZ: IF BERATER_OUTPUTS_PT.gatherSignals.status == DONE: RETURN (Resume-SKIP)

2. Quelle A — Parking-Lot:
   pl = Read({bl_folder}/6_PL/{bl_id}-parking-lot.md)
   FOR item IN parse_pl_items(pl):
     signal_type = classify_raw(item):           # NUR Grob-Typ, keine 3-Achsen (das ist Stage 5)
       "[PatternConformance]"/CONF- → violation
       "PL_DRIFT-"/"HOLD-"          → finding (Revert-Verdacht → Stage 3/4 verfeinern)
       "[PT-Kandidat]"              → finding (pattern-wuerdig-Vorsignal)
       sonst                        → finding
     signals.append(normalize(item, source="parking_lot", signal_type, raw_ref=item.id, text=item.kurz))

3. Quelle B — KEIN_PATTERN-Gaps:
   FOR N WHERE manifest.s{N}_pt_signal == "KEIN_PATTERN":
     signals.append({id:"KEIN_PATTERN@s{N}", source:"kein_pattern", signal_type:"gap",
                     raw_ref:manifest.s{N}_pt_signal_slices, text:"Consult-Gap Stufe {N}",
                     timestamp:manifest.s{N}_pt_signal_at})

4. Quelle C — Conformance-Verletzungen:
   FOR f IN manifest.ARCHITECT_ESCALATION_QUEUE + parse PATTERN_CONFORMANCE_STATE:
     signals.append({id:"CONF-{f.finding_id}", source:"conformance", signal_type:"violation",
                     raw_ref:f.datei, text:f.beschreibung, pattern_id_hint:f.pattern_id,
                     file_refs:[f.datei]})

5. Quelle D — pattern-usage.log (Graceful):
   IF exists(.claude/wissen/pattern-usage.log):
     FOR line IN log WHERE status IN [BROKEN, VERIFIED, KEIN_PATTERN, CONFIDENCE_DOWNGRADE]:
       signals.append({id:"USAGE-{status}@{pattern_id}", source:"usage_log",
                       signal_type:(status==BROKEN?"revert":"usage"),
                       raw_ref:pattern_id, pattern_id_hint:pattern_id, timestamp:line.date})
   ELSE: LOG "[gatherSignals] keine pattern-usage.log — 0 Usage-Signale (BL-237: laeuft heute kaum)"

5b. Quelle E — commit_sweep (NUR bei --ticket oder --branch-Arg; INV-GS-5):
   IF args enthält --ticket ODER --branch:
     ticket  = args["--ticket"]   # optional (Freitext-Praefixfilter fuer --grep)
     author  = args["--author"]   # optional
     b_range = args["--branch"]   # optional (z.B. "main..HEAD")

     git_cmd = ["git", "log", "--all", "--no-merges", "--pretty=format:%H"]
     IF ticket: git_cmd += ["--grep", ticket]
     IF author: git_cmd += ["--author", author]
     IF b_range: git_cmd += [b_range]  # Branch-Range ersetzt --all

     hashes = run(git_cmd)
     FOR full_hash IN hashes:
       show_out = run("git show --no-merges --stat {full_hash}")   # Commit-Msg + Stat-Zeilen
       diff_ctx = run("git show --no-merges -U3 {full_hash}")      # Diff-Kontext (Rohdaten)
       commit_msg  = extract_first_paragraph(show_out)
       changed_files = extract_stat_files(show_out)
       hash7 = full_hash[:7]
       # INV-GS-1: NUR sammeln; Revert-Bewertung = Stage 3 timeAxis
       # INV-GS-2: Roh-Text erhalten (commit_msg + diff_ctx unbearbeitet)
       signals.append({
         id:             "COMMIT-{hash7}",
         source:         "commit_sweep",
         signal_type:    "reviewed_change",
         raw_ref:        full_hash,
         text:           commit_msg + "\n---\n" + diff_ctx,   # roh, ungekuerzt
         file_refs:      changed_files,
         pattern_id_hint: null,
         timestamp:      extract_commit_date(show_out)
       })
   ELSE:
     counts.commit_sweep = 0
     LOG "[gatherSignals] kein --ticket/--branch — commit_sweep uebersprungen (INV-GS-5)"

6. Dedup nach raw_ref (INV-GS-4). counts berechnen.

7. Schreibe BERATER_OUTPUTS_PT.gatherSignals = {signals, counts, status: (signals?DONE:EMPTY)}
   SendMessage team-lead: "gatherSignals: {total} Signale ({parking_lot} PL / {kein_pattern} Gap / {conformance} Verletzung / {usage_log} Usage / {commit_sweep} Commits)"
```

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| 6_PL fehlt | counts.parking_lot=0, weiter mit anderen Quellen |
| keine s{N}_pt_signal | counts.kein_pattern=0 |
| PATTERN_CONFORMANCE_STATE fehlt | counts.conformance=0 |
| pattern-usage.log fehlt (Normalfall heute) | counts.usage_log=0 + LOG-Hinweis (BL-237-Befund) |
| kein --ticket/--branch Arg | counts.commit_sweep=0, reiner PL-Modus (Abwaertskompatibilitaet) |
| --ticket gesetzt, aber 0 Treffer | counts.commit_sweep=0 + LOG-Hinweis, kein Fehler |
| git nicht verfuegbar / kein Repo | counts.commit_sweep=0 + LOG-Warnung, weiter mit anderen Quellen |
| ALLE leer | status=EMPTY, SendMessage "keine Signale — nichts zu ernten" |

## Verwandt
- `_PT_orchestrate` (Stage 1 Caller) · `_PT_berater_clustering` (Stage 2, konsumiert .gatherSignals)
- BL-237 Abschnitt „Fehlersignal = Parking-Lot" + „Buendelung" (Anschluss 3)
- BL-427 commit_sweep als 5. Signal-Quelle (abgenommener Code = gleichrangige Truth-Quelle)
- `_PT_berater_timeAxis` (Stage 3) — Revert-Bewertung der commit_sweep-Signale (INV-GS-1: hier nur sammeln)
