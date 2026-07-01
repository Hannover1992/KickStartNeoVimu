---
type: satellite
---

# Debloat-System - Hilfe & Uebersicht

Zeige die Uebersicht der Debloat (/_D_*) Commands.

## Aufruf

```
/_D_help
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  DEBLOAT-SYSTEM v1.0 (4 Commands)                                       ║
║                                                                           ║
║  Problem: Models wachsen unkontrolliert (Beobachtungen akkumulieren).    ║
║  Loesung: Separation Blueprint ↔ Protokoll + Wahrheiten-Kollaps.        ║
║                                                                           ║
║  Fackel-Analogie:                                                         ║
║    FALSCH: "Fackel brennt, ist warm, leuchtet roetlich" (Beobachtung)   ║
║    RICHTIG: "Thermisch→Schwellenwert→Kerosin+Luft→Energie" (Mechanismus)║
║                                                                           ║
║  ═══ EINSTIEGSPUNKT (User-triggered, jederzeit aufrufbar) ═══            ║
║                                                                           ║
║  /_D_orchestrate {FEATURE} [--hard]                                      ║
║  ┌──────────────────────────────────────────────────────────────────┐    ║
║  │  Debloat-Orchestrator — Standalone, kein Team noetig.            │    ║
║  │  Prueft Trigger-Schwellen und spawnt kurzlebige Agents.          │    ║
║  │                                                                  │    ║
║  │  TRIGGER-CHECK (automatisch):                                    │    ║
║  │    <500 Zeilen  → kein Debloat noetig, meldet Status             │    ║
║  │    >=500 Zeilen → SOFT-Trigger: fragt User (HiL)                │    ║
║  │    >=700 Zeilen → HARD-Trigger: Debloat verpflichtend           │    ║
║  │    --hard Flag  → forciert Debloat unabhaengig von Zeilen        │    ║
║  │                                                                  │    ║
║  │  Interne Chain (bei Trigger):                                    │    ║
║  │    1. /_D_separate  → Protokoll-Datei anlegen (falls fehlt)     │    ║
║  │    2. /_D_kollaps   → Wahrheiten-Kollaps (5 Phasen)             │    ║
║  │                                                                  │    ║
║  │  Beispiele:                                                      │    ║
║  │    /_D_orchestrate OmniCommand    → OmniCommand_Model.md pruefen│    ║
║  │    /_D_orchestrate DCSRE-93       → anderes Projekt debloaten   │    ║
║  │    /_D_orchestrate ModelBloat --hard  → forciert Debloat        │    ║
║  └──────────────────────────────────────────────────────────────────┘    ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ═══ COMMAND-KETTE (n-1 / n / n+1 Vertraege) ═══                        ║
║                                                                           ║
║  ┌─────────────────────────────────────────────────────────────────┐     ║
║  │                                                                 │     ║
║  │   /_D_separate {FEATURE}                                        │     ║
║  │   Actor: SEPARATOR                                               │     ║
║  │   → Erstellt {FEATURE}_Protokoll.md (Wahrheiten-Protokoll)     │     ║
║  │   → Klassifiziert W{n}: Beobachtung → Protokoll                │     ║
║  │                         Mechanismus → bleibt im Model           │     ║
║  │   → Entscheidungsbaum: "Warum/Wie?" = Mechanismus               │     ║
║  │                        "Was beobachtet?" = Beobachtung          │     ║
║  │   → LIEST:    {FEATURE}_Model.md, Protokoll_Template.md        │     ║
║  │   → SCHREIBT: {FEATURE}_Protokoll.md (NEU oder geprueft)       │     ║
║  │                          │                                      │     ║
║  │                          ▼                                      │     ║
║  │   /_D_kollaps {FEATURE} [--dry-run] [--scan-only]              │     ║
║  │   Actor: KOLLAPS-EXECUTOR                                        │     ║
║  │   → 5-Phasen Wahrheiten-Kollaps                                 │     ║
║  │   → P1: Kandidaten identifizieren (OFFEN/BESTAETIGT, Conf>0.65)│     ║
║  │   → P2: Cluster bilden (thematische Gruppen)                   │     ║
║  │   → P3: Kollaps (Cluster → kompaktes Mermaid im Model)         │     ║
║  │   → P4: INTEGRATED-Marking (W{n} im Protokoll archivieren)     │     ║
║  │   → P5: Qualitaets-Check (Model <500 Zeilen? Mechan. erhalten?)│     ║
║  │   → HiL bei Confidence <0.85 (W07: User bestaetigt Kollaps)   │     ║
║  │   → --dry-run: zeigt Plan, schreibt NICHTS                     │     ║
║  │   → --scan-only: nur P1+P2 (SOFT-Trigger Analyse)              │     ║
║  │   → LIEST:    {FEATURE}_Protokoll.md, {FEATURE}_Model.md       │     ║
║  │   → SCHREIBT: {FEATURE}_Model.md (Mermaid-Updates, bereinigt)  │     ║
║  │              {FEATURE}_Protokoll.md (W{n} als INTEGRATED)      │     ║
║  │                                                                 │     ║
║  └─────────────────────────────────────────────────────────────────┘     ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ═══ MIGRATIONS-COMMAND (Legacy-Models) ═══                              ║
║                                                                           ║
║  /_D_migrate {FEATURE} [--dry-run] [--interactive]                       ║
║  ┌──────────────────────────────────────────────────────────────────┐    ║
║  │  Konvertiert grosses Legacy-Model in Separation-Format.          │    ║
║  │  Fuer bestehende Models (z.B. OmniCommand 63K, 1556 Zeilen).   │    ║
║  │                                                                  │    ║
║  │  7-Phasen-Ablauf:                                                │    ║
║  │    1. Analyse       → W{n} zaehlen + klassifizieren             │    ║
║  │    2. HiL-Check     → User bestaetigt Migration                 │    ║
║  │    3. Backup        → Model_pre_migrate_{DATUM}.md erstellen    │    ║
║  │    4. Separate      → _D_separate intern aufrufen               │    ║
║  │    5. Kollaps       → _D_kollaps intern aufrufen                │    ║
║  │    6. Validation    → <500 Zeilen? Mechanismen erhalten?        │    ║
║  │    7. Summary       → Vorher/Nachher Vergleich                  │    ║
║  │                                                                  │    ║
║  │  Flags:                                                          │    ║
║  │    --dry-run        → zeigt Analyse, kein Schreiben             │    ║
║  │    --interactive    → User entscheidet pro W{n}                 │    ║
║  │                                                                  │    ║
║  │  Activation-Gate (5 Kriterien, W13):                            │    ║
║  │    Model >500 Zeilen, >30% Beobachtungs-W{n},                  │    ║
║  │    Team-Lead Signoff, Backup vorhanden, Tests gruен             │    ║
║  └──────────────────────────────────────────────────────────────────┘    ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ═══ PIPELINE-INTEGRATION ═══                                            ║
║                                                                           ║
║  _SC_modelMaintain v2.4:                                                 ║
║    SOFT-Trigger (>=500 Zeilen): empfiehlt /_D_orchestrate (HiL)         ║
║    HARD-Trigger (>=700 Zeilen): verpflichtend, blockiert Post-Cycle      ║
║                                                                           ║
║  _I_orchestrate v2.1:                                                    ║
║    Debloat-Hook nach codeSystem-Stufe:                                   ║
║    Falls Model >500 Zeilen → schlaegt /_D_orchestrate vor               ║
║                                                                           ║
║  WP-Pipeline:                                                            ║
║    TODO (EC-F offen, externe Klaerung noetig)                           ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ═══ DATEIEN & FORMATE ═══                                               ║
║                                                                           ║
║  {FEATURE}_Model.md     Blueprint (Mermaid, Mechanismen, <500 Zeilen)   ║
║  {FEATURE}_Protokoll.md Wahrheiten-Protokoll (append-only, W{n}-Bloecke)║
║                                                                           ║
║  Protokoll W{n}-Block:                                                   ║
║    ### W{N}: {Titel}                                                     ║
║    Status: OFFEN | BESTAETIGT | INTEGRATED | WIDERLEGT                  ║
║    Confidence: 0.0-1.0                                                   ║
║    Cluster: {thematische Gruppe}                                          ║
║                                                                           ║
║  Template: .claude/templates/Protokoll_Template.md                       ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ═══ MECHANISMEN ═══                                                     ║
║                                                                           ║
║  Dual-Stufen-Trigger:  SOFT(>=500Z, HiL) / HARD(>=700Z, verpflichtend) ║
║  Dual-Track-Kollaps:   Track 1 (manuelle Tags, Default)                 ║
║                         Track 2 (NLP-Analyse, Enhancement)               ║
║  Confidence-Schwellen: 0.65 minimal (P1), 0.85 auto-kollaps (P3/W07)   ║
║  W{n}-Lebenszyklus:    OFFEN → BESTAETIGT → INTEGRATED → ARCHIVIERT    ║
║                         OFFEN → WIDERLEGT  → ARCHIVIERT                  ║
║  Backup-Strategie:     {FEATURE}_Model_pre_migrate_{DATUM}.md           ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ═══ QUICK-START ═══                                                     ║
║                                                                           ║
║  Model pruenfen:                                                          ║
║    /_D_orchestrate {FEATURE}        → prueft + debloatet automatisch    ║
║                                                                           ║
║  Analyse ohne Aenderung:                                                 ║
║    /_D_kollaps {FEATURE} --dry-run  → zeigt Kollaps-Plan                ║
║                                                                           ║
║  Legacy-Model migrieren:                                                 ║
║    /_D_migrate {FEATURE} --dry-run  → Analyse zuerst                    ║
║    /_D_migrate {FEATURE}            → vollstaendige Migration            ║
║                                                                           ║
║  Nur Protokoll anlegen:                                                   ║
║    /_D_separate {FEATURE}           → erstellt Protokoll-Datei           ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```
