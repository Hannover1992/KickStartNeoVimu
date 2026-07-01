---
status: active
version: 1.0
type: berater
parent: _SDF_PostBerater_orchestrate
model_tier: floor
actor: C9c — Phase 2 (nach C12 garbageCollection)
feature: BL-124
sdf_quelle: BL-124-ARCHITECT-S4.md Z112-201
tc: TC9
batch_aware: true
wired_in: _PostBatch_orchestrate
---

# _SDF_berater_stateMaintain (C13)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_stateMaintain (C13)                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:   {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded) (alle Pfad-Felder + alle Bloecke)             ║
║           _session_params.md (resume_point, aktive Feature-Felder)  ║
║           BERATER_OUTPUTS.garbageCollection.violations_found         ║
║             (als Eingangs-Hints fuer gezielte Pruefung)             ║
║  SCHREIBT: BERATER_OUTPUTS.stateMaintain                             ║
║              {integrity_pass, violations[], auto_corrected[]}        ║
║  SCHREIBT ZUSAETZLICH (Auto-Corrections):                            ║
║    {WORKING_DIR}/_manifest.md — Duplikat-Felder entfernen (letzter Wert gewinnt), ║
║      Orphan-Refs → nur im violations[]-Log, KEIN Auto-Remove        ║
║    _guard_log.md — APPEND kritische Violations (HARD-Level)         ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   ║
║                  I_PIPELINE_STATE Signal-Felder (ADR-F)             ║
║  INVARIANTEN:                                                        ║
║    INV-2: Write-Isolation (nur eigene BERATER_OUTPUTS-Sub-Felder)   ║
║    INV-FACTORY-1: kein HiL                                           ║
║    Auto-Correct NUR bei eindeutig (Duplikat letzter Wert gewinnt)   ║
║    Orphan-Ref → violations[], KEIN Auto-Remove (Eskalations-Pfad)   ║
║    integrity_pass=true wenn keine HARD-Violations                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_stateMaintain)
Kein Argument — liest {WORKING_DIR}/_manifest.md + _session_params.md direkt.
Ausgabe: BERATER_OUTPUTS.stateMaintain (3 Felder)
Exitcode: 0=integrity_pass=true, 1=SOFT-Violations, 2=HARD-Violations
```

## Schritte (Pseudo-Code)

### Schritt 1: CROSS_REFERENCE_CHECK

```
1.1 Pfad-Felder sammeln
    Alle Felder in {WORKING_DIR}/_manifest.md die Dateipfade enthalten:
    spec_path, model_path, gap_path, vault_path, crumbs_path, log_path, 
    task_md_path, blueprint_path, protokoll_path
    
1.2 Existenz pruefen fuer jeden Pfad
    cross_ref_violations[] = []
    FUER field IN path_fields:
      Lese {WORKING_DIR}/_manifest.md, Wert aus field
      IF value ist nicht leer:
        path = value
        IF file_exists(path) == false:
          cross_ref_violations[].append({
            field: field,
            path: path,
            level: "SOFT",
            action: "Orphan-Ref"
          })

1.3 Sammeln
    violations[].extend(cross_ref_violations[])
```

### Schritt 2: DUPLIKAT_CHECK

```
2.1 Jeder Block parsen
    dup_check_violations[] = []
    auto_corrected[] = []
    FUER block IN {WORKING_DIR}/_manifest.md:
      block_fields = {}
      FUER line IN block.lines:
        IF line.contains("=") OR line.contains(":"):
          field_name = line.split("=|:")[0].strip()
          field_value = line.split("=|:")[1].strip()
          
          IF field_name IN block_fields:
            # Duplikat gefunden
            old_value = block_fields[field_name]
            auto_corrected[].append({
              block: block.name,
              field: field_name,
              kept: field_value,  # letzter Wert gewinnt
              removed: old_value
            })
            # Entferne alte Zeile aus {WORKING_DIR}/_manifest.md
            {WORKING_DIR}/_manifest.md.remove_line(line_number_of_old_value)
          ELSE:
            block_fields[field_name] = field_value

2.2 Schreiben falls Korrektionen noetig
    IF len(auto_corrected[]) > 0:
      Schreibe {WORKING_DIR}/_manifest.md (doppelte Zeilen entfernt)
```

### Schritt 3: TIMESTAMP_PLAUSIBILITAET

```
3.1 Timestamp-Felder pruefen
    timestamp_fields = [current_stage_completed, last_append, 
                        deferred_date, resumed_at]
    timestamp_violations[] = []
    
3.2 Jeden Timestamp validieren
    FUER field IN timestamp_fields:
      Lese Wert aus {WORKING_DIR}/_manifest.md oder _session_params.md
      IF value ist nicht leer:
        timestamp = parse(value)
        now = datetime.now()
        IF timestamp > now:
          timestamp_violations[].append({
            field: field,
            value: value,
            level: "SOFT",
            detail: "Zeitstempel in Zukunft"
          })

3.3 Sammeln
    violations[].extend(timestamp_violations[])
```

### Schritt 4: RESUME_POINTER_CHECK

```
4.1 Resume-Point lesen
    resume_point = _session_params.md.get("resume_point")
    IF resume_point ist leer:
      EXIT diesen Schritt (SOFT-OK)
    
4.2 Ziel-Block pruefen
    resume_violations[] = []
    # resume_point Format: "BLOCK_NAME" oder "BLOCK_NAME.FIELD"
    target_block = resume_point.split(".")[0]
    
    block_exists = false
    FUER block IN {WORKING_DIR}/_manifest.md:
      IF block.name == target_block:
        block_exists = true
        BREAK
    
    IF block_exists == false:
      resume_violations[].append({
        field: "resume_point",
        value: resume_point,
        level: "HARD",
        detail: f"Resume-Ziel '{target_block}' existiert nicht in {WORKING_DIR}/_manifest.md"
      })

4.3 Sammeln
    violations[].extend(resume_violations[])
```

### Schritt 5: HARD_VIOLATION_ESCALATION

```
5.1 HARD-Violations filtern
    hard_violations[] = [v for v in violations[] if v.level == "HARD"]
    
5.2 In _guard_log.md schreiben (APPEND)
    IF len(hard_violations[]) > 0:
      log_block = f"""## C13 StateMaintain {ISO_TIMESTAMP}
      
[C13_stateMaintain] HARD Violations erkannt:
"""
      FUER violation IN hard_violations[]:
        log_block += f"- {violation.field}: {violation.detail}\n"
      
      _guard_log.md.append(log_block)
```

### Schritt 6: integrity_pass Berechnung

```
6.1 Ergebnis festlegen
    hard_violations[] = [v for v in violations[] if v.level == "HARD"]
    integrity_pass = (len(hard_violations[]) == 0)
```

### Schritt 7: OUTPUT_YAML

```
7.1 BERATER_OUTPUTS.stateMaintain schreiben
    _berater_outputs.md aktualisieren:
    
    BERATER_OUTPUTS:
      stateMaintain:
        integrity_pass: {integrity_pass}
        violations: {violations[]}  # List of dicts
        auto_corrected: {auto_corrected[]}  # List of dicts

7.2 Exitcode setzen
    IF integrity_pass == true:
      EXIT 0
    ELSE IF any(v.level == "HARD" for v in violations[]):
      EXIT 2
    ELSE:  # SOFT-Violations nur
      EXIT 1
```

## Output-YAML Beispiel

```yaml
BERATER_OUTPUTS:
  stateMaintain:
    integrity_pass: true
    violations:
      - field: "crumbs_path"
        level: "SOFT"
        detail: "Pfad nicht gefunden"
      - field: "last_append"
        level: "SOFT"
        detail: "Zeitstempel in Zukunft"
    auto_corrected:
      - block: "A_PIPELINE_STATE"
        field: "phase"
        kept: "IN_PROGRESS"
        removed: "PENDING"
```

## Tier-Begruendung (floor/haiku)

Mechanische Operationen ohne Intelligenz:
- Cross-Reference-Check: Datei-Existenz-Tests (Dateisystem-Abfrage)
- Duplikat-Check: String-Vergleich + Parsing (deterministisch)
- Timestamp-Check: Zeitvergleiche (arithmetisch)
- Resume-Pointer-Check: Block-Lookup (Lookup-Tabelle)
- Alle Entscheidungen regelbasiert, keine ML/Reasoning nötig
→ **floor/haiku gerechtfertigt**

## Invarianten-Einhaltung

- **INV-2:** Schreibt AUSSCHLIESSLICH in `BERATER_OUTPUTS.stateMaintain`
- **INV-FACTORY-1:** Kein `AskUserQuestion`, kein HiL
- **ADR-F:** Schreibt NICHT in `I_PIPELINE_STATE` Signal-Felder
- **Auto-Correct:** NUR bei Duplikaten (letzter Wert gewinnt); Orphan-Refs gehen NUR in violations[], kein Auto-Remove
- **Eskalation:** HARD-Violations → `_guard_log.md` APPEND, Pipeline LAEUFT WEITER (SOFT-Degradation)

## Integration in C9c PostBerater-Orchestrate

**Position:** Phase 2 (nach C12 garbageCollection, vor C3 sdfHub)

```
orchestrator returns →
  Phase 1: Skill(_SDF_berater_garbageCollection)   ← C12
  Phase 2: Skill(_SDF_berater_stateMaintain)        ← C13 **HIER**
  Phase 3: # BL-140 DELETED: _SDF_berater_sdfHub (C4) redundant. Hub-Loop in executionDispatch SCHRITT 2.
  ...
```

**Trigger:** Automatisch nach C12, kein Opt-In-Flag

**Abbruch-Regel:** HARD-Violations → enforcement_level=WARN in C9c, Pipeline LAEUFT WEITER

## format_version-Stamping-Disziplin (BL-333, B2 — Follow zu B1)

> **Lead = `_A_berater_stateMaintain.md` (B1).** Diese SDF-Variante ist der SDF-seitige Manifest-Writer und folgt 1:1 derselben Stamp-Disziplin (PT-GEN-LeadFollow).

Das `_manifest.md` ist Typ `manifest` in der Registry `.claude/config/format_versions.yaml`. Da dieser Berater `{WORKING_DIR}/_manifest.md` schreibt (Auto-Corrections / Duplikat-Entfernung), gilt:

- **Top-Level-Stamp (additiv, idempotent):** `format_version: {N}` im Frontmatter; Wert via `resolve_format_version("manifest")` (kein Literal); vorhanden -> kein Duplikat.
- **Dual-Read-Gen-0:** Manifest ohne Stempel == Generation-0 (NIE Crash); Loader `None` -> Stamp weglassen statt brechen.
- **Rein additiv:** kein Re-Format/Umbenennen bestehender Frontmatter-Felder. Die Auto-Correction (Duplikat-Entfernung) darf den `format_version:`-Stempel NICHT als Duplikat fehl-interpretieren.

Vertrags-Spiegel der Lane-A-Logik in `resolve_format_version.py` (`stamp_format_version_lines`, `read_format_version`). Details siehe B1.

## Siehe auch

- `_SDF_berater_garbageCollection.md` (C12, Vorgänger in Phase 1)
- `_SDF_PostBerater_orchestrate.md` (C9c, Aufrufer)
- `_berater_outputs.md` (Contract, Ausgabe-Format)
- `_A_berater_stateMaintain.md` (B1, format_version-Stamp-Lead — BL-333)
- `BL-124-ARCHITECT-S4.md` (Design-Quelle)
