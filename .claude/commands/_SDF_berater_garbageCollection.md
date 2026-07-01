---
status: active
version: 1.0
type: berater
parent: _SDF_PostBerater_orchestrate
model_tier: floor
actor: C9c — Phase 1 (erster Aufruf nach Orchestrator-Return)
feature: BL-124
sdf_quelle: BL-124-ARCHITECT-S4.md Z26-108
tc: TC8
batch_aware: true
wired_in: _PostBatch_orchestrate
---

# _SDF_berater_garbageCollection (C12)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_garbageCollection (C12)                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:   {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded) (alle Bloecke)                                ║
║           {VAULT}/.../6_PL/{bl_id}-parking-lot.md (Status + Datum)  ║
║           _session_params.md (obsolete Felder-Pruefung)              ║
║           _backlog_index.md (READ-ONLY, INV-3)                       ║
║           _manifest_protokoll.md (Frontmatter: append_count,        ║
║             last_append fuer Prepend-Koordination)                   ║
║  SCHREIBT: BERATER_OUTPUTS.garbageCollection                         ║
║              {status, files_scrubbed, bytes_archived, violations}    ║
║  SCHREIBT ZUSAETZLICH (Scrub-Writes):                                ║
║    {WORKING_DIR}/_manifest.md — entfernt *_PREV/*_ARCHIVED/*_COMPLETED-Bloecke,   ║
║      A_PIPELINE_STATE phase=COMPLETED/DEFERRED>7d → auslagern       ║
║    {VAULT}/.../6_PL/{bl_id}-parking-lot.md — [x]>30d → archivieren  ║
║    _session_params.md — obsolete Felder entfernen (Regeln s.u.)      ║
║    _manifest_protokoll.md — W18 Prepend: append_count++,            ║
║      last_append=ISO, Datum-Block mit archivierten Items             ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   ║
║                  _backlog_index.md (INV-3 append-only)              ║
║  INVARIANTEN:                                                        ║
║    INV-3: _backlog_index.md niemals schreiben                        ║
║    W18: Protokoll-Prepend (append_count++ + last_append + Block)     ║
║    INV-FACTORY-1: kein HiL, kein AskUserQuestion                    ║
║    SKIP-Bedingung: kein Bloat erkannt → gc.status="SKIP", kein Write ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_garbageCollection)
Kein Argument — scannt immer alle State-Dateien.
Ausgabe: BERATER_OUTPUTS.garbageCollection (4 Felder + status)
Exitcode: 0=OK|SKIP, 1=PARTIAL (einzelne Writes fehlgeschlagen), 2=FAIL
```

## Schritte (Pseudo-Code)

### Schritt 1: MANIFEST_SCAN

```
1.1 Bloecke mit Suffix *_PREV | *_ARCHIVED | *_COMPLETED sammeln
    candidates[] = []
    FUER jeder Block in {WORKING_DIR}/_manifest.md:
      IF Block-Name endet mit _PREV | _ARCHIVED | _COMPLETED:
        candidates[].append({name, content_lines, byte_count})

1.2 A_PIPELINE_STATE Bloecke pruefen
    IF existiert A_PIPELINE_STATE:
      phase = A_PIPELINE_STATE.phase
      IF phase == "COMPLETED":
        candidates[].append(A_PIPELINE_STATE)
      ELSE IF phase == "DEFERRED":
        deferred_date = A_PIPELINE_STATE.deferred_date
        age_days = (now - parse(deferred_date)).days
        IF age_days > 7:
          candidates[].append(A_PIPELINE_STATE)

1.3 Early-Exit wenn keine Kandidaten
    IF candidates[] ist leer:
      gc.status = "SKIP"
      gc.files_scrubbed = []
      gc.bytes_archived = 0
      gc.violations_found = 0
      Schreibe BERATER_OUTPUTS.garbageCollection
      EXIT 0
```

### Schritt 2: PARKING_LOT_SCAN

```
2.1 [x]-Items mit Datum-Suffix parsieren
    pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
    pl_archive[] = []
    FUER jede Zeile in pl_path:
      IF Zeile startet mit "[x]":
        Extrahiere Datum aus "(DONE: YYYY-MM-DD)" Suffix
        age_days = (now - parse(datum)).days
        IF age_days > 30:
          pl_archive[].append({zeile, datum, age_days})

2.2 Alte Items sammeln
    archive_count = len(pl_archive[])
```

### Schritt 3: SESSION_PARAMS_SCAN

```
3.1 tdd_user_locked pruefen
    obsolete_candidates[] = []
    IF _session_params.md.tdd_user_locked == true:
      IF kein aktiver TDD-Override in Manifest vorhanden:
        obsolete_candidates[].append("tdd_user_locked=true")

3.2 HASH_CACHE_BEGIN/END-Block pruefen
    IF existiert HASH_CACHE_BEGIN-Block:
      feature_in_block = Extrahiere Feature-Namen aus Block
      IF feature_in_block NOT IN batch_items[]:
        obsolete_candidates[].append("HASH_CACHE_BEGIN...END ({feature})")

3.3 Obsolete sammeln
    obsolete_count = len(obsolete_candidates[])
```

### Schritt 4: SCRUB_WRITES (nur wenn Arbeit noetig)

```
4.1 Entscheide ob Schreiben noetig
    total_work = len(candidates[]) + len(pl_archive[]) + len(obsolete_candidates[])
    IF total_work == 0:
      gc.status = "SKIP"
      EXIT 0

4.2 {WORKING_DIR}/_manifest.md scrubben
    bytes_removed = 0
    files_scrubbed = []
    FUER jeden candidate IN candidates[]:
      Entferne Block aus {WORKING_DIR}/_manifest.md
      bytes_removed += candidate.byte_count
    IF bytes_removed > 0:
      Schreibe {WORKING_DIR}/_manifest.md
      files_scrubbed[].append("{WORKING_DIR}/_manifest.md")

4.3 Vault-PL archivieren ({VAULT}/.../6_PL/{bl_id}-parking-lot.md)
    IF len(pl_archive[]) > 0:
      # Erstelle Archive-Section am Dateiende
      archive_section = "## Archiv\n\n"
      FUER item IN pl_archive[]:
        archive_section += "- " + item.zeile + " (archiviert " + today + ")\n"
      Append archive_section zu pl_path
      files_scrubbed[].append(pl_path)

4.4 _session_params.md bereinigen
    IF len(obsolete_candidates[]) > 0:
      FUER field IN obsolete_candidates[]:
        Entferne Zeile/Feld aus _session_params.md
      Schreibe _session_params.md
      files_scrubbed[].append("_session_params.md")

4.5 _manifest_protokoll.md W18 Prepend
    protokoll_fm = Lies _manifest_protokoll.md Frontmatter
    append_count_neu = protokoll_fm.append_count + 1
    last_append_neu = now.isoformat()
    
    # Konstruiere neuen Block fuer Prepend
    new_block = f"""
## Garbage Collection [{today}]

Archivierte Items:
"""
    FUER candidate IN candidates[]:
      new_block += f"- {candidate.name}\n"
    FUER item IN pl_archive[]:
      new_block += f"- {item.zeile} (age {item.age_days}d)\n"
    
    # Prepend (nicht Append!): Nach Frontmatter + Leerzeile
    old_content = Lies _manifest_protokoll.md
    frontmatter_end = Index "---" (zweite Vorkommen)
    protokoll_inhalt = old_content[frontmatter_end:].lstrip()
    
    new_content = frontmatter_with_updated_metadata + "\n\n" + new_block + protokoll_inhalt
    Schreibe _manifest_protokoll.md mit new_content
    
    # Aktualisiere Frontmatter
    _manifest_protokoll.md.append_count = append_count_neu
    _manifest_protokoll.md.last_append = last_append_neu
    
    files_scrubbed[].append("_manifest_protokoll.md")
```

### Schritt 5: OUTPUT_YAML

```
5.1 Berechne Metriken
    violations_found = Zaehle alle Orphan-Refs oder fehlerhafte Referenzen
                       (Falls vorhanden — sonst 0)

5.2 Schreibe BERAUER_OUTPUTS.garbageCollection
    gc.status = "OK"  (wenn total_work > 0 und alles OK)
    gc.files_scrubbed = files_scrubbed[]
    gc.bytes_archived = bytes_removed
    gc.violations_found = violations_found

5.3 Schreibe Frontmatter von _berater_outputs.md
    last_update = now.isoformat()
    last_berater = "C12"

5.4 Exit-Code
    IF alles OK: EXIT 0
    IF einzelne Writes fehlgeschlagen: EXIT 1
    IF fataler Fehler: EXIT 2
```

## Output-YAML Beispiel

```yaml
BERATER_OUTPUTS:
  garbageCollection:
    status: OK
    files_scrubbed: [{WORKING_DIR}/_manifest.md, _manifest_protokoll.md, "{VAULT}/.../6_PL/{bl_id}-parking-lot.md"]
    bytes_archived: 4200
    violations_found: 0
```

## Idempotenz-Eigenschaft

**2x Aufruf der gleichen {WORKING_DIR}/_manifest.md → 2. Mal liefert SKIP:**

Beim 1. Aufruf:
- candidates[] = [A_PIPELINE_STATE_PREV, MY_FEATURE_ARCHIVED, ...]
- SCRUB_WRITES entfernt diese
- gc.status = "OK"

Beim 2. Aufruf (auf schon gesauberte Datei):
- candidates[] = [] (keine *_PREV/*_ARCHIVED Bloecke mehr)
- pl_archive[] = [] (alle Items <30d)
- obsolete_candidates[] = []
- total_work = 0
- gc.status = "SKIP"
- EXIT 0 (keine Schreibvorgaenge)

## Ziel-Metrik

`{WORKING_DIR}/_manifest.md` ≤ 150 LOC pure State (nach GC-Lauf).
Baseline: 110 LOC nach manueller Reorg 2026-04-18.

## Muster-Anwendung

**Pattern-Zuordnung:**
- **P1 KURZLEBIG_PROMPT:** C12 Agent spawnt, scrubbt, stirbt
- **P2 VERTRAG-Block:** Obige ASCII-Box
- **P3 Pattern-B-Lite:** Schreibt nur BERAUER_OUTPUTS.garbageCollection
- **P4 Alpha-Beta-Pruning:** candidates[] leer → SKIP, EXIT 0
- **P11 INV-FACTORY-1:** kein HiL, kein AskUserQuestion
- **P12 Return-Guard-Pattern (KERN):** Auto-Trigger nach Orchestrator-Return, idempotent
- **P13 W18-Prepend-Pattern (KERN):** _manifest_protokoll.md Prepend, append_count++
