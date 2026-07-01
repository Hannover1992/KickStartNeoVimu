# Session-Parameter — DEFAULT (deployable via /_redeploy)
#
# Diese Datei ist die SOURCE-OF-TRUTH fuer Default-Session-Parameter.
# Sie wird durch /_redeploy in alle Ziel-Projekte verteilt (CONFIG_WHITELIST).
# Per-Projekt-Aktualisierungen erfolgen in {VAULT}/_session_params.md
# (NICHT-deployable, BLACKLIST in /_redeploy).
#
# Stand: 2026-05-07 (User-Direktive: small_dark_factory als Standard-Modus,
#                     HiL=on, easy difficulty, sonnet ceiling / haiku floor)

**HiL:** on
**difficulty:** easy
**ceiling:** sonnet
**floor:** haiku
**slicing:** false
**tdd:** true
**tdd_stages:** [1,3,6]
**prePr:** report
**pr:** false
**enforceProcess:** false
**dark_factory_max_cycles_override:** 5
**task_source:** backlog
**pattern_scan_threshold:** 5
**dark_factory:** false
**GLOBAL_MODUS:** small_dark_factory
**sdf:** true
**merge:** true
**lane:**

## Erwarteter Default-Lauf (Beschreibung Operator)

Bei diesen Defaults bearbeitet der Standard-Pfad **1 Backlog-Item ohne parallele Wellen-Worker**:

1. `/_backlog {NAME}` — Item aufnehmen (intake oder create)
2. `/_A_orchestrate` — Fresh-Modus, Wissensbasis bauen (Model + Spec + K-Score + Gap)
3. `/_IDF_orchestrate` — Dekomposition Spec → AKs → PL-Items (per Cluster)
4. `/_SDF_orchestrate` — SDF C3 modusEntscheidung waehlt M1-M9 je nach K-Score:
   - M1-M3 → `Skill(_I_orchestrate)` Implementation (Standard)
   - M4-M6 → `Skill(_SC_orchestrate)` SC-Symbiose
   - M7 → SC reine Analyse
   - M8 → PR-Review (nur wenn pr=true)
   - M9 → WP-Research

**difficulty=easy** = 1 Worker pro Welle (statt 5-3-1 normal oder 9-5-1 hard).
**GLOBAL_MODUS=small_dark_factory** = SDF-direkt (BDF-Outer-Loop nur wenn explizit aufgerufen).
**HiL=on** = User-Checkpoints aktiv (Findings + AK-Review + Post-SDF Beobachtungen).
