# /_wellen_guard — Guard-Command fuer Wellen-Enforcement

```yaml
status: active
version: 1.0.0
created: 2026-04-03
op: Guard
phase: Pre-Pipeline
type: enforcement
chain_position: guard
```

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_wellen_guard                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  INPUT:                                                              ║
║    $command  — Pipeline-Command der ausgefuehrt werden soll          ║
║    $difficulty — easy | normal | hard                                ║
║                                                                      ║
║  LIEST:                                                              ║
║    {WORKING_DIR}/_manifest.md  (A_PIPELINE_STATE, DF_PIPELINE_STATE — per-Story, BL-155 AK-1)║
║    .claude/analysis/_guard_log.md (bisherige Violations)             ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/analysis/_guard_log.md (bei Violation: APPEND)            ║
║                                                                      ║
║  OUTPUT:                                                             ║
║    PASS — Command darf ausgefuehrt werden                            ║
║    WARN — Violation erkannt, geloggt, Warnung an Team Lead           ║
║    BLOCK — Kritische Violation, Command wird NICHT ausgefuehrt       ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Logik

```
EINGABE: command, difficulty

# ═══ GUARD 1: Wellen-Enforcement (CS7-F01, CS7-F02) ═══
IF difficulty IN [normal, hard]:
  IF command IN [_W_fetch, _taskDefinition, _model, _spec, _gap, _K_score]:
    # Diese Commands MUESSEN mit Wellen-Pattern ausgefuehrt werden
    ERWARTUNG:
      IF difficulty == normal:
        N_explorer = 5, N_drafter = 3, N_synthese = 1  → Total = 9
      ELIF difficulty == hard:
        N_explorer = 9, N_drafter = 5, N_synthese = 1  → Total = 15

    # Pruefe: Wird ein einzelner Agent fuer den gesamten Command gespawnt?
    IF agent_count == 1 AND command.wellen == true:
      VIOLATION: "[WELLEN-VIOLATION] {command} bei difficulty={difficulty} hat nur 1 Agent statt {expected_total}"
      → Log ins _guard_log.md
      → WARNUNG an Team Lead (kein Block, aber SICHTBAR)
      → Empfehlung: "Spawne {N_explorer} Explorer + {N_drafter} Drafter + 1 Synthese"

ELIF difficulty == "easy":
  # Bei easy: 1 Agent ist ERLAUBT — kein Wellen-Pattern noetig
  PASS

# ═══ GUARD 2: Mega-Agent-Erkennung (DCSRE-98, CS7-F01) ═══
IF agent_prompt CONTAINS mehr als 1 Pipeline-Command:
  VIOLATION: "[MEGA-AGENT] Agent-Prompt enthaelt {N} Pipeline-Commands: {list}"
  → Log ins _guard_log.md
  → BLOCK: "Jeder Pipeline-Command braucht eigenen Agent (W7, DCSRE-98)"

# ═══ GUARD 3: BDF-Bypass-Erkennung (CS6-F06) ═══
IF context CONTAINS "BDF" OR "BigDarkFactory":
  IF agent_prompt CONTAINS Pipeline-Command WITHOUT "_SDF_orchestrate":
    VIOLATION: "[BDF-BYPASS] BDF→Agent() direkt statt BDF→SDF"
    → Log ins _guard_log.md
    → BLOCK: "BDF MUSS ueber SDF routen (BDF→SDF→SC/I)"

# ═══ GUARD 4: Violation-Schwelle (STUCKED-Promotion) ═══
IF count_violations_today(_guard_log.md) >= 3:
  WARNUNG: "[GUARD-ALARM] 3+ Violations heute — Context-Druck-Eskalation moeglich"
  → Empfehlung: "Session beenden, frisch starten, oder HiL=manual setzen"

# Kein Verstoss
RETURN PASS
```

---

## Aufruf-Beispiele

```
# VOR jedem Pipeline-Schritt:
/_wellen_guard _model normal
→ Prueft: Wird _model mit Wellen-Pattern ausgefuehrt?

/_wellen_guard _spec easy
→ PASS (easy braucht keine Wellen)

/_wellen_guard _gap normal
→ Prueft: Werden 5+3+1 Agents gespawnt?
```

---

## Integration

Dieser Guard wird aufgerufen:
1. **Automatisch** via Claude Code Hooks (settings.json Pre-Hook auf Agent/TaskCreate)
2. **Manuell** vom Team Lead VOR jedem Pipeline-Schritt in _A_orchestrate Phase 4.1a
3. **Von BDF** beim SCANNING um BDF→SDF Routing zu verifizieren

Die Hook-Scripts (guard_agent_prompt_validator.py, guard_wellen_reminder.py) implementieren
Guards 1-3 technisch. Dieser Command dokumentiert die Semantik und dient als Referenz.
