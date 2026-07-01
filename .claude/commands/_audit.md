---
status: active
version: 1.0.0
created: 2026-04-05
type: satellite
chain_position: standalone
depends_on: []
feeds_into: []
related:
  - _BDF_orchestrate
  - _SDF_orchestrate
---

# /_audit — Prozess-Audit & Compliance-Report

**Zweck:** Liest `.claude/audit/audit.jsonl` und prueft ob der Prozess eingehalten wurde. Pro BL-Item wird der Weg rekonstruiert und gegen die SOLL-Regeln geprueft.

## Aufruf

```
/_audit [--item=BL-NNN] [--session=YYYY-MM-DD] [--verbose] [--skill-load-replay]
```

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `--item` | alle | Nur ein bestimmtes BL-Item auswerten |
| `--session` | heute | Nur Events von einem bestimmten Datum |
| `--verbose` | false | Zeigt alle Events, nicht nur Violations |
| `--skill-load-replay` | false | **BL-159 PL-6-02:** Post-Hoc Replay — validiert `skill_loaded`-Events gegen erwartete Spawn-Pattern (Mega-Agent-Detection). Idempotent. Skip Compliance-Regeln R1-R9. |

---

## VERTRAG

```
LIEST:
  .claude/audit/audit.jsonl              (Audit-Log, JSONL)
  {VAULT}/_manifest.md          (aktueller State)
  {VAULT}/_backlog_index.md     (BL-Item Status)
  .claude/analysis/synthese/*-K_SCORE.md (K-Scores pro Item)
  .claude/analysis/synthese/*-GAP.md     (GAP pro Item)
  .claude/analysis/drafts/ProcessMap-COMPLETE.md (SOLL-Regeln)

SCHREIBT:
  .claude/audit/audit-report-{DATUM}.md  (Compliance-Report)

SCHREIBT NICHT:
  _manifest.md, _backlog_index.md, _parking-lot.md (read-only)
```

---

## Pseudocode

```
FUNCTION _audit(item_filter, session_filter, verbose, skill_load_replay):

  # ============================================================
  # SCHRITT 0: Mode-Switch — BL-159 PL-6-02 Skill-Load-Replay
  # ============================================================

  IF skill_load_replay == True:
    RETURN _audit_skill_load_replay(session_filter)
    # Skip Compliance-Regeln R1-R9 — Replay ist eigenstaendiger Pfad

  # ============================================================
  # SCHRITT 1: Audit-Log laden und filtern
  # ============================================================

  log_path = ".claude/audit/audit.jsonl"
  IF NOT EXISTS(log_path):
    LOGGE: "FEHLER: Kein Audit-Log gefunden. Wurde audit_hook.py aktiviert?"
    RETURN

  events = []
  FUER JEDE zeile IN log_path:
    entry = JSON_PARSE(zeile)
    IF session_filter AND entry.ts NOT STARTS_WITH session_filter:
      CONTINUE
    events.append(entry)

  IF events.length == 0:
    LOGGE: "Keine Events fuer Filter gefunden."
    RETURN

  LOGGE: "[AUDIT] {events.length} Events geladen"

  # ============================================================
  # SCHRITT 2: Events nach BL-Items gruppieren
  # ============================================================

  # Heuristik: Events gehoeren zum BL-Item das in ctx.feature steht
  # oder das im Skill-Args als --batch= referenziert wird
  items = {}  # {bl_id: [events]}

  FUER event IN events:
    bl_id = NULL

    # Aus ctx.feature ableiten
    IF event.ctx.feature:
      # Feature-Name → BL-ID via _backlog_index.md
      bl_id = lookup_bl_id(event.ctx.feature)

    # Aus Skill-Args ableiten
    IF bl_id == NULL AND event.event == "HANDOFF":
      match = regex("--batch=(\S+)", event.args)
      IF match:
        bl_id = match.group(1)

    IF bl_id == NULL:
      bl_id = "_GLOBAL"  # Events ohne Item-Zuordnung

    IF bl_id NOT IN items:
      items[bl_id] = []
    items[bl_id].append(event)

  # Filter auf bestimmtes Item
  IF item_filter:
    items = {k: v FOR k, v IN items.items() IF k == item_filter}

  LOGGE: "[AUDIT] {items.keys().length} Items erkannt: {items.keys()}"

  # ============================================================
  # SCHRITT 3: Pro Item — Prozess-Weg rekonstruieren
  # ============================================================

  report_items = []

  FUER bl_id, item_events IN items.items():
    IF bl_id == "_GLOBAL":
      CONTINUE

    item_report = {
      bl_id: bl_id,
      handoffs: [],
      state_writes: [],
      workers: [],
      violations: [],
      compliance: "PASS",
    }

    # K-Score und Modus lesen
    k_score = lese_k_score(bl_id)  # aus *-K_SCORE.md
    gap = lese_gap(bl_id)          # aus *-GAP.md

    # Events klassifizieren
    FUER event IN item_events:
      IF event.event == "HANDOFF":
        item_report.handoffs.append(event)
      ELIF event.event == "STATE_WRITE":
        item_report.state_writes.append(event)
      ELIF event.event == "WORKER_SPAWN":
        item_report.workers.append(event)

    # ============================================================
    # SCHRITT 4: SOLL-Regeln pruefen (Compliance-Check)
    # ============================================================

    # ─── REGEL R1: K>=34 MUSS durch SDF ───
    # Items mit K-Score >= 34 (MEDIUM) duerfen NICHT inline implementiert werden.
    # SOLL: BDF→SDF→(SC/I)→SDF→BDF
    # VIOLATION: Kein SDF-HANDOFF in Events
    IF k_score >= 34:
      sdf_handoffs = [h FOR h IN item_report.handoffs IF h.skill == "_SDF_orchestrate"]
      IF sdf_handoffs.length == 0:
        item_report.violations.append({
          "regel": "R1",
          "schwere": "HOCH",
          "beschreibung": "K={k_score} >= 34 aber KEIN SDF-Handoff. Item wurde inline implementiert.",
          "soll": "BDF → Skill(_SDF_orchestrate) → SC/I",
          "ist": "Direkte Edits ohne SDF",
        })

    # ─── REGEL R2: SC-REIF Items brauchen Modus-Entscheidung ───
    # SDF MUSS 7-Modus-Entscheidung treffen (M1-M9)
    # VIOLATION: SDF-HANDOFF vorhanden aber kein Modus in ctx
    sdf_events = [e FOR e IN item_events IF e.ctx.get("modus")]
    IF sdf_events.length == 0 AND k_score >= 34:
      item_report.violations.append({
        "regel": "R2",
        "schwere": "MITTEL",
        "beschreibung": "Kein Modus (M1-M9) in Audit-Events. SDF hat keine 7-Modus-Entscheidung getroffen.",
        "soll": "SDF Phase 2 Schritt 2.1: gewaehlter_modus setzen",
        "ist": "Kein Modus-Event",
      })

    # ─── REGEL R3: M5+ braucht SC-Handoff ───
    # Modi M4-M7 MUESSEN SC_orchestrate aufrufen
    modus_events = [e FOR e IN item_events IF e.ctx.get("modus") IN ["M4","M5","M6","M7"]]
    IF modus_events.length > 0:
      sc_handoffs = [h FOR h IN item_report.handoffs IF h.skill == "_SC_orchestrate"]
      IF sc_handoffs.length == 0:
        item_report.violations.append({
          "regel": "R3",
          "schwere": "HOCH",
          "beschreibung": "Modus {modus_events[0].ctx.modus} gewaehlt aber KEIN SC-Handoff.",
          "soll": "M4-M7 → Skill(_SC_orchestrate)",
          "ist": "SC uebersprungen",
        })

    # ─── REGEL R4: RECALIBRATE nach nicht-M1 ───
    # Nach jedem SC/I Handschuh-Rueckweg (nicht M1): modelMaintain + K_score
    modus = modus_events[0].ctx.modus IF modus_events.length > 0 ELSE NULL
    IF modus AND modus != "M1":
      recal_events = [h FOR h IN item_report.handoffs IF h.skill == "_SC_modelMaintain"]
      IF recal_events.length == 0:
        item_report.violations.append({
          "regel": "R4",
          "schwere": "MITTEL",
          "beschreibung": "Modus {modus} aber KEIN RECALIBRATE (modelMaintain).",
          "soll": "Schritt 2.2b: modelMaintain + K_score nach Handschuh-Rueckweg",
          "ist": "Kein Recalibrate-Event",
        })

    # ─── REGEL R5: GAP-Check nach Implementation ───
    # Nach I_orchestrate MUSS /_gap aufgerufen werden
    i_handoffs = [h FOR h IN item_report.handoffs IF h.skill == "_I_orchestrate"]
    IF i_handoffs.length > 0:
      gap_handoffs = [h FOR h IN item_report.handoffs IF h.skill == "_gap"]
      IF gap_handoffs.length == 0:
        item_report.violations.append({
          "regel": "R5",
          "schwere": "MITTEL",
          "beschreibung": "I_orchestrate aufgerufen aber KEIN GAP-Check danach.",
          "soll": "Schritt 2.4b: /_gap nach Implementation",
          "ist": "Kein GAP-Event nach I",
        })

    # ─── REGEL R6: Stage nach GAP=0% ───
    # Nach GAP=0% MUSS stage_orchestrate aufgerufen werden
    # (schwer zu pruefen ohne GAP-Wert im Event — DEFERRED)

    # ─── REGEL R7: Worker-Pflicht (INV-PM-1) ───
    # JEDE Code-Aenderung MUSS durch Worker, nicht TL direkt
    # Heuristik: Edit an .claude/commands/ ohne vorherigen I/SC-Handoff
    direct_edits = [e FOR e IN item_report.state_writes
                    IF "commands/" IN e.get("file", "")]
    IF direct_edits.length > 0 AND i_handoffs.length == 0:
      item_report.violations.append({
        "regel": "R7",
        "schwere": "HOCH",
        "beschreibung": "Direkte Edits an Commands ohne I_orchestrate-Handoff (INV-PM-1).",
        "soll": "Code-Aenderungen NUR durch Worker (I/SC Pipeline)",
        "ist": "{direct_edits.length} direkte Command-Edits",
      })

    # ─── REGEL R8: Puppet-Master (INV-PM-2) ───
    # Orchestrator-Wechsel NUR via Skill(), nie via Agent()
    agent_orchestrators = [w FOR w IN item_report.workers
                           IF w.get("command") IN ["_SDF_orchestrate", "_SC_orchestrate",
                                                    "_I_orchestrate", "_BDF_orchestrate"]]
    IF agent_orchestrators.length > 0:
      item_report.violations.append({
        "regel": "R8",
        "schwere": "KRITISCH",
        "beschreibung": "Orchestrator via Agent() statt Skill() aufgerufen (INV-PM-2).",
        "soll": "Skill(skill='...') fuer Orchestrator-Wechsel",
        "ist": "{agent_orchestrators.length} Agent()-Aufrufe fuer Orchestratoren",
      })

    # ─── REGEL R9: Vault-Write nach Synthese (BL-050 Vault-First DirectWrite) ───
    # Nach model/spec/gap Synthese MUSS vault_write erfolgt sein (DirectWrite).
    # Ersetzt alte R9 (Fire-Together Check) — _W_fireTogether ist OBSOLET (BL-050).
    synthese_skills = [h FOR h IN item_report.handoffs
                       IF h.skill IN ["_model", "_spec", "_gap"]]
    IF synthese_skills.length > 0:
      vault_writes = [h FOR h IN item_report.handoffs IF h.vault_write == True]
      IF vault_writes.length == 0:
        item_report.violations.append({
          "regel": "R9",
          "schwere": "NIEDRIG",
          "beschreibung": "Synthese ohne Vault-Write (BL-050 DirectWrite).",
          "soll": "vault_write == True nach jeder Synthese (DirectWrite in Vault)",
          "ist": "Kein vault_write Event gefunden",
        })

    # Compliance-Ergebnis
    IF item_report.violations.length > 0:
      max_schwere = max(v.schwere FOR v IN item_report.violations,
                        key={"KRITISCH":4,"HOCH":3,"MITTEL":2,"NIEDRIG":1})
      item_report.compliance = "FAIL ({max_schwere})"
    ELSE:
      item_report.compliance = "PASS"

    report_items.append(item_report)

  # ============================================================
  # SCHRITT 5: Report generieren
  # ============================================================

  datum = HEUTE
  report_path = ".claude/audit/audit-report-{datum}.md"

  report = """
---
type: audit-report
datum: {datum}
items_total: {report_items.length}
items_pass: {COUNT(r FOR r IN report_items IF r.compliance == "PASS")}
items_fail: {COUNT(r FOR r IN report_items IF "FAIL" IN r.compliance)}
violations_total: {SUM(r.violations.length FOR r IN report_items)}
---

# Audit-Report {datum}

## Zusammenfassung

| Metrik | Wert |
|--------|------|
| Items geprueft | {report_items.length} |
| PASS | {pass_count} |
| FAIL | {fail_count} |
| Violations gesamt | {total_violations} |
| Schwerstes | {max_schwere_global} |

## Pro Item

"""

  FUER item_report IN report_items:
    report += """
### {item_report.bl_id} — {item_report.compliance}

**Weg:** {item_report.handoffs als Pfad: skill1 → skill2 → ...}
**K-Score:** {k_score} | **Modus:** {modus} | **Handoffs:** {item_report.handoffs.length} | **Workers:** {item_report.workers.length}

"""

    IF item_report.violations.length > 0:
      report += "| Regel | Schwere | Beschreibung | SOLL | IST |\n"
      report += "|-------|---------|-------------|------|-----|\n"
      FUER v IN item_report.violations:
        report += "| {v.regel} | {v.schwere} | {v.beschreibung} | {v.soll} | {v.ist} |\n"

    ELIF verbose:
      report += "Keine Violations. Prozess korrekt eingehalten.\n"
      report += "\nEvents:\n"
      FUER event IN item_events:
        report += "- [{event.ts}] {event.event} {event.level} {event.skill ?? event.file ?? ''}\n"

  SCHREIBE report → report_path
  LOGGE: "[AUDIT] Report geschrieben: {report_path}"

  # ============================================================
  # SCHRITT 6: Zusammenfassung ausgeben
  # ============================================================

  Logge: ""
  Logge: "=== AUDIT REPORT {datum} ==="
  Logge: ""
  FUER item_report IN report_items:
    symbol = "PASS" IF item_report.compliance == "PASS" ELSE "FAIL"
    Logge: "  [{symbol}] {item_report.bl_id} — {item_report.handoffs.length} Handoffs, {item_report.violations.length} Violations"
    FUER v IN item_report.violations:
      Logge: "        [{v.schwere}] {v.regel}: {v.beschreibung}"

  Logge: ""
  Logge: "Items: {pass_count} PASS / {fail_count} FAIL"
  Logge: "Report: {report_path}"
  Logge: ""

  IF fail_count > 0:
    Logge: "EMPFEHLUNG: Items mit FAIL-Violations muessen nachgebessert werden."
    Logge: "  R1/R3/R7/R8 (HOCH/KRITISCH): Prozess wiederholen (SDF korrekt aufrufen)"
    Logge: "  R2/R4/R5 (MITTEL): Fehlende Schritte nachholen"
    Logge: "  R9 (NIEDRIG): Fire-Together Trigger ergaenzen"


# ============================================================
# Hilfsfunktionen
# ============================================================

FUNCTION lookup_bl_id(feature_name):
  # Sucht BL-ID in _backlog_index.md anhand des Feature-Namens
  Lies _backlog_index.md
  FUER zeile IN tabelle:
    IF feature_name IN zeile:
      RETURN zeile.bl_id  # z.B. "BL-025"
  RETURN NULL

FUNCTION lese_k_score(bl_id):
  # Liest K-Score aus der zugehoerigen K_SCORE.md
  # Sucht via _backlog_index.md → feature_name → *-K_SCORE.md
  feature = lookup_feature(bl_id)
  k_score_path = ".claude/analysis/synthese/{feature}-K_SCORE.md"
  IF EXISTS(k_score_path):
    content = LIES(k_score_path)
    match = regex(r'k_score\s*=?\s*(\d+\.?\d*)', content)
    IF match: RETURN float(match.group(1))
  RETURN 0

FUNCTION lese_gap(bl_id):
  feature = lookup_feature(bl_id)
  gap_path = ".claude/analysis/synthese/{feature}-GAP.md"
  IF EXISTS(gap_path):
    content = LIES(gap_path)
    match = regex(r'GAP\s*=?\s*(\d+\.?\d*)%', content)
    IF match: RETURN float(match.group(1))
  RETURN 100


# ============================================================
# BL-159 PL-6-02: Skill-Load Replay
# ============================================================
#
# Zweck: Idempotenter Post-Hoc Replay validiert ob alle
#        skill_loaded-Events via Skill()-Tool stammen.
#        Erkennt Mega-Agent-Verstoesse anhand load_method.
#
# Vorbedingung: audit_hook.py schreibt skill_loaded-Events
#               mit Feldern: worker_id, skill, load_method,
#               attempted_path, ts.
#               load_method IN {"skill", "read", "other"}.
# Idempotenz: liest NUR aus audit.jsonl, schreibt NICHT zurueck.
#             Report wird in audit-replay-report-{datum}.md geschrieben.

FUNCTION _audit_skill_load_replay(session_filter):

  log_path = ".claude/audit/audit.jsonl"
  IF NOT EXISTS(log_path):
    Logge: "[REPLAY] FEHLER: audit.jsonl nicht vorhanden (BL-159 AK-4 noch nicht aktiv?)"
    RETURN exit_code=2

  # Events laden + filtern
  events = []
  FUER zeile IN log_path:
    entry = JSON_PARSE(zeile)
    IF session_filter AND entry.ts NOT STARTS_WITH session_filter:
      CONTINUE
    IF entry.type IN ["skill_loaded", "SKILL_LOAD_VIOLATION", "WORKER_SPAWN"]:
      events.append(entry)

  IF events.length == 0:
    Logge: "[REPLAY] Keine skill_loaded-Events fuer Filter '{session_filter}'"
    RETURN exit_code=0

  Logge: "[REPLAY] {events.length} relevante Events geladen"

  # Worker-Index aufbauen
  workers = {}  # {worker_id: {spawn_ts, skill_loads: [], violations: []}}
  FUER e IN events:
    IF e.type == "WORKER_SPAWN":
      workers[e.worker_id] = {
        spawn_ts: e.ts,
        spawn_skill_expected: e.get("skill", "unknown"),
        skill_loads: [],
        violations: []
      }
    ELIF e.type == "skill_loaded":
      wid = e.get("worker_id", "_LEAD")
      IF wid NOT IN workers:
        workers[wid] = {spawn_ts: null, spawn_skill_expected: null,
                        skill_loads: [], violations: []}
      workers[wid].skill_loads.append({
        skill: e.skill,
        load_method: e.get("load_method", "other"),
        attempted_path: e.get("attempted_path"),
        ts: e.ts
      })
    ELIF e.type == "SKILL_LOAD_VIOLATION":
      wid = e.get("worker_id", "_LEAD")
      IF wid NOT IN workers:
        workers[wid] = {spawn_ts: null, spawn_skill_expected: null,
                        skill_loads: [], violations: []}
      workers[wid].violations.append({
        attempted_path: e.attempted_path,
        hook_action: e.get("hook_action", "block"),
        ts: e.ts
      })

  # Pro Worker pruefen
  pass_workers = []
  fail_workers = []
  FUER wid, w IN workers.items():
    # Regel: Falls Worker WORKER_SPAWN hat, MUSS er auch ein
    # passendes skill_loaded mit load_method="skill" haben.
    IF w.spawn_ts != null:
      valid_loads = [l FOR l IN w.skill_loads
                     IF l.load_method == "skill" AND l.ts > w.spawn_ts]
      IF valid_loads.length == 0:
        fail_workers.append({
          worker_id: wid,
          reason: "no_valid_skill_load",
          spawn_expected: w.spawn_skill_expected,
          actual_loads: w.skill_loads,
          violations: w.violations
        })
      ELSE:
        pass_workers.append(wid)
    ELSE:
      # Worker ohne SPAWN-Event = Lead-Frame oder Pre-Audit-Hook-Worker
      # → SKIP (kein Spawn-Vertrag zu pruefen)
      CONTINUE

    # Zusatz-Check: Hatte der Worker SKILL_LOAD_VIOLATION-Events?
    IF w.violations.length > 0 AND wid NOT IN [f.worker_id FOR f IN fail_workers]:
      fail_workers.append({
        worker_id: wid,
        reason: "violation_event_present",
        violations: w.violations
      })

  # Report schreiben
  datum = HEUTE
  report_path = ".claude/audit/audit-replay-report-{datum}.md"
  report = """
---
type: audit-skill-load-replay
datum: {datum}
session_filter: {session_filter}
workers_total: {workers.length}
workers_pass: {pass_workers.length}
workers_fail: {fail_workers.length}
exit_code: {0 IF fail_workers.length == 0 ELSE 1}
---

# Skill-Load Replay Report {datum}

## Zusammenfassung
| Metrik | Wert |
|--------|------|
| Worker erkannt | {workers.length} |
| PASS | {pass_workers.length} |
| FAIL | {fail_workers.length} |

## Violations
"""
  FUER f IN fail_workers:
    report += "- Worker {f.worker_id}: {f.reason}\n"
    FUER v IN f.get("violations", []):
      report += "  - {v.ts} BLOCK: {v.attempted_path} (hook_action={v.hook_action})\n"
    FUER l IN f.get("actual_loads", []):
      report += "  - {l.ts} load_method={l.load_method} skill={l.skill}\n"

  SCHREIBE report → report_path

  # Konsole
  Logge: ""
  Logge: "=== SKILL-LOAD REPLAY {datum} ==="
  Logge: "Workers: {pass_workers.length} PASS / {fail_workers.length} FAIL"
  FUER f IN fail_workers:
    Logge: "  [FAIL] {f.worker_id} — {f.reason}"
  Logge: "Report: {report_path}"

  IF fail_workers.length > 0:
    RETURN exit_code=1   # BLOCKER-Signal fuer Pre-PR Phase 4d / CI
  RETURN exit_code=0
```

---

## Regeln (9 Compliance-Checks)

| Regel | Schwere | Beschreibung | Referenz |
|-------|---------|-------------|----------|
| R1 | HOCH | K>=34 MUSS durch SDF | ProcessMap SDF-05 |
| R2 | MITTEL | Modus-Entscheidung (M1-M9) PFLICHT | SDF Phase 2.1 |
| R3 | HOCH | M4-M7 braucht SC-Handoff | INV-HW-1 |
| R4 | MITTEL | RECALIBRATE nach nicht-M1 | SDF 2.2b |
| R5 | MITTEL | GAP-Check nach Implementation | SDF 2.4b |
| R6 | NIEDRIG | Stage nach GAP=0% | SDF 2.4d (DEFERRED) |
| R7 | HOCH | Worker-Pflicht (kein TL-Code) | INV-PM-1 |
| R8 | KRITISCH | Orchestrator via Skill, nie Agent | INV-PM-2 |
| R9 | NIEDRIG | Fire-Together nach Synthese | BL-027 |

---

## Beispiel-Output

```
=== AUDIT REPORT 2026-04-05 ===

  [FAIL] BL-032 — 0 Handoffs, 3 Violations
        [HOCH] R1: K=34 >= 34 aber KEIN SDF-Handoff
        [HOCH] R7: Direkte Edits an Commands ohne I_orchestrate-Handoff
        [MITTEL] R2: Kein Modus in Audit-Events

  [FAIL] BL-027 — 0 Handoffs, 2 Violations
        [HOCH] R1: K=38 >= 34 aber KEIN SDF-Handoff
        [HOCH] R7: Direkte Edits an Commands ohne I_orchestrate-Handoff

  [PASS] BL-034 — 0 Handoffs, 0 Violations
  [PASS] BL-033 — 0 Handoffs, 0 Violations

Items: 2 PASS / 2 FAIL
Report: .claude/audit/audit-report-2026-04-05.md
```
