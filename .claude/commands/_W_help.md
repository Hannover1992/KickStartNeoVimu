# Wissens-Koaleszenz - Hilfe & Uebersicht

Zeige die Uebersicht der Wissens-Koaleszenz (/_W_*) Commands.

## Aufruf

```
/_W_help
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  WISSENS-KOALESZENZ (5 Commands + 1 Referenz)                          ║
║                                                                         ║
║  Wissen lebt in ZWEI Quellen: Obsidian Vault (Langzeit) + RAG (Such).  ║
║  Features holen Wissen (Dual-Source), arbeiten damit, pushen es zurueck║
║  "Standing on the shoulders of giants."                                ║
║                                                                         ║
║  ═══ KREISLAUF (Dual-Source: Vault + RAG) ═══                          ║
║                                                                         ║
║       Vault (readonly)         RAG global_knowledge (readonly)         ║
║           │                                │                            ║
║           └────────────────────────────────┘                            ║
║                       │ /_W_fetch (HOLEN, Dual-Source)                 ║
║                       ▼                                                 ║
║       .claude/ (Arbeitsbereich)        RAG local_knowledge_* (temp)    ║
║           │                                │                            ║
║           │  Feature-Arbeit                │ /_W_push_temp (TEMP)      ║
║           │  /_model, /_SC_*               │ (feature-isoliert)         ║
║           │  /_I_*, /_WP_*                 │                            ║
║           │                                │                            ║
║           └────────▼───────────────────────┘                            ║
║               Feature-ENDE                                              ║
║                    │                                                    ║
║           /_W_push_global (Quality Gate)                                ║
║                    │                                                    ║
║       ┌────────────┴─────────────┐                                      ║
║       ▼                          ▼                                      ║
║  /_W_modelSplit            RAG global_knowledge                         ║
║  (thematisch splitten)     (verified knowledge)                         ║
║       │                                                                 ║
║       ▼                                                                 ║
║  /_W_obsidianSync                                                         ║
║  (Synthese TRANSPORTIEREN)                                              ║
║       │                                                                 ║
║       ▼                                                                 ║
║    Vault (readonly)                                                     ║
║                                                                         ║
║  ═══ COMMANDS ═══                                                      ║
║                                                                         ║
║  /_W_fetch {THEMA|FEATURE} [easy|normal|hard]                          ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  WISSEN HOLEN (Feature-START, Dual-Source, Wellen-Architektur)   │   ║
║  │  Actor: KNOWLEDGE-SCOUT                                          │   ║
║  │  → 3-Wellen-Architektur (v3.0):                                 │   ║
║  │    Welle 1: Haiku kartographiert (Vault + RAG, breit)           │   ║
║  │    Welle 2: Sonnet filtert (Relevanz, Dedup, Gruppierung)       │   ║
║  │    Welle 3: Opus entscheidet (Auswahl, Konsolidierung)          │   ║
║  │  → Schwierigkeitsstufen: easy (1 Welle), normal (3), hard (3+)  │   ║
║  │  → Dual-Mode: Solo (sequentiell) + Worker (orchestriert)        │   ║
║  │  → Auto-Accept bei easy (Score >= 0.5, kein User-Input)         │   ║
║  │  → Manifest-Integration: SYSTEM-MODEL + SCHWIERIGKEIT lesen     │   ║
║  │  → Plattform-agnostisch: Linux (cp, md5sum) + Windows (PS)     │   ║
║  │  SCHREIBT: models/*.md, wissen/*.md, _manifest.md               │   ║
║  │  Status: v3.0 (Wellen-Architektur + Schwierigkeitsstufen)       │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║         Feature-Arbeit (/_taskDefinition → /_model → ...)              ║
║                          │                                              ║
║                          ▼                                              ║
║  /_W_sync_orchestrate {FEATURE} [easy|normal|hard] [--co-work]         ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  SYNC ORCHESTRIEREN (prozessbegleitend, thin wrapper)            │   ║
║  │  Actor: SYNC-ORCHESTRATOR                                        │   ║
║  │  → Thin wrapper ueber /_W_obsidianSync                          │   ║
║  │  → Liest SC_PIPELINE_STATE aus Manifest (Zyklus N, Dateien)     │   ║
║  │  → Delegiert Sync an /_W_obsidianSync {easy|normal|hard}        │   ║
║  │  → --co-work: G-COWORK Guard schreibt co-created-with +         │   ║
║  │    cycle-cluster Frontmatter (Hebb-Prinzip, Zyklus-Cluster)     │   ║
║  │  → Manifest: Sync-Log aktualisieren                             │   ║
║  │  → Aufruf: SC §3.3a (parallel), W_push_orchestrate Step 5      │   ║
║  │  SCHREIBT: Vault-Dateien (via obsidianSync) + co-work Frontm.  │   ║
║  │  Status: v1.0 (NEU 2026-02-24)                                  │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_W_push_temp {DOCUMENT|auto}                                          ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  TEMP PUSHEN (waehrend Feature, feature-isoliert)                │   ║
║  │  Actor: KNOWLEDGE-PUSHER                                         │   ║
║  │  → Dokument validieren (erlaubte Ordner, .md)                   │   ║
║  │  → Collection: local_knowledge_{feature_id}                     │   ║
║  │  → MCP: create_collection + ingest                              │   ║
║  │  → KEIN Quality Gate (schnell, temporaer)                       │   ║
║  │  → Manifest: "## RAG Push Status" (Status: PUSHED)              │   ║
║  │  SCHREIBT: RAG local_knowledge_*, _manifest.md                  │   ║
║  │  Status: v2.0 (auto-Modus, Manifest-Tracking)                   │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║         Feature-Arbeit (weitere Cycles, /_SC_*, /_I_*)                 ║
║                          │                                              ║
║                          ▼                                              ║
║  /_W_push_global {DOCUMENT}                                             ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  GLOBAL PUSHEN (Feature-ENDE, Quality Gate)                      │   ║
║  │  Actor: KNOWLEDGE-GATEKEEPER                                     │   ║
║  │  → Quality Gate: W{n}-Status pruefen (BESTAETIGT/WIDERLEGT)     │   ║
║  │  → User-Approval bei kritischen Faellen                         │   ║
║  │  → RAG Push: global_knowledge (PFLICHT)                         │   ║
║  │  → Vault Push: mit Frontmatter (OPTIONAL)                       │   ║
║  │  → Manifest: "## Quality Gate Log" + "## RAG Push Status"       │   ║
║  │  SCHREIBT: RAG global_knowledge, Vault (optional), _manifest.md │   ║
║  │  Status: v1.0 (Dual-Push, Quality Gate)                         │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_W_modelSplit {NAME}                                                  ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  WISSEN ABLEGEN (Feature-ENDE)                                   │   ║
║  │  Actor: KNOWLEDGE-ENGINEER                                       │   ║
║  │  → Feature-Model lesen, Themen identifizieren                   │   ║
║  │  → THEMATISCH (wiederverwendbar) vs FEATURE (kontextgebunden)   │   ║
║  │  → Vault-Check: Existiert schon ein thematisches Model?         │   ║
║  │  → NEU erstellen oder MERGE in bestehendes Vault-Model          │   ║
║  │  → Feature-Model archivieren (readonly, Referenzen)             │   ║
║  │  SCHREIBT: {THEMA}_Model.md im Vault, Feature-Model archiviert │   ║
║  │  VORAUSSETZUNG: /_model finish abgeschlossen                    │   ║
║  │  Status: v1.0 (Placeholder — Vertrag definiert)                 │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_W_obsidianSync {FEATURE} [easy|normal|hard]                          ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  SYNTHESE TRANSPORTIEREN (.claude/ -> Vault)                     │   ║
║  │  Actor: SYNC-OPERATOR                                            │   ║
║  │  → PROZESSBEGLEITEND (v2.0 SOLL): Sync waehrend Feature         │   ║
║  │  → Schwierigkeitsstufen:                                        │   ║
║  │    easy: Delta-Sync (nur geaenderte, paralleler Worker)         │   ║
║  │    normal: Vollstaendig + Frontmatter + Wiki-Links              │   ║
║  │    hard: Alles + Chain-Erkennung + Mermaid (Feature-Ende)       │   ║
║  │  → MD5-Hash-Tracking (Delta-Sync Basis)                         │   ║
║  │  → YAML-Frontmatter + Obsidian Wiki-Links                      │   ║
║  │  → Feature-Note als Master-Hub                                   │   ║
║  │  → Manifest: Sync-Tabelle aktualisieren                        │   ║
║  │  SCHREIBT: Vault-Dateien, Feature-Note, _manifest.md           │   ║
║  │  Status: v1.0 (Standalone, Feature-Ende)                        │   ║
║  │  SOLL v2.0: Prozessbegleitend + Linux-Support + Dual-Mode      │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  /_obsidianHelp                                                         ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  REFERENZ (Tag-Taxonomie, Graph-Farben, Setup)                   │   ║
║  │  → Tag-Registry: type/, topic/, op/, chain/                     │   ║
║  │  → Graph-Farben: Rot=Model, Blau=Synthese, Gruen=Wissen, ...   │   ║
║  │  → Vault-Setup + Konfiguration                                  │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  ═══ SCHWIERIGKEITSSTUFEN (v3.0) ═══                                   ║
║                                                                         ║
║  | Stufe  | W_fetch              | W_obsidianSync          | Trigger  | ║
║  |--------|----------------------|-------------------------|----------|  ║
║  | easy   | 1 Welle (Auto-Scan)  | Delta-Sync (parallel)   | Auto     | ║
║  | normal | 3 Wellen (H+S+O)     | Voll-Sync + Frontmatter | 1x/Cycle | ║
║  | hard   | 3 Wellen (mehr Agts) | Alles + Chain + Mermaid  | Manuell  | ║
║                                                                         ║
║  Ceiling-Hierarchie: Sub-Prozess darf NIE hoehere Stufe als Parent.    ║
║  Easy SC-Zyklus -> max easy Sync/Fetch.                                ║
║  Normal SC-Zyklus -> max normal Sync/Fetch.                            ║
║  Hard -> separat, manuell (volle Ressourcen).                          ║
║  Schwierigkeit wird top-down ueber Manifest vererbt                    ║
║  (SYSTEM-MODEL + SCHWIERIGKEIT aus _manifest.md).                      ║
║  Regeln: R-CEIL-1 bis R-CEIL-6 (siehe WissensKoaleszenz_Model.md).    ║
║                                                                         ║
║  Model-Zuordnung (bei Wellen):                                         ║
║    floor  = Haiku  (Kartographierung, guenstig)                        ║
║    middle = Sonnet (Filterung, praezise)                               ║
║    ceiling = Opus  (Entscheidung, Qualitaet)                           ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  ABGRENZUNG: Wer macht was?                                            ║
║                                                                         ║
║  /_W_fetch       = Wissen HOLEN (Vault + RAG → .claude/, START)        ║
║  /_W_push_temp   = Temp PUSHEN (.claude/ → RAG local, waehrend)        ║
║  /_W_push_global = Global PUSHEN (.claude/ → RAG global + Vault, ENDE) ║
║  /_W_modelSplit  = Wissen ABLEGEN (Model thematisch splitten, ENDE)    ║
║  /_W_obsidianSync  = Synthese TRANSPORTIEREN (.claude/ → Vault, jederzeit)║
║  /_W_sync_orchestrate = Sync ORCHESTRIEREN (thin wrapper, prozessbegl.) ║
║  /_knowledge     = Wissen ERSTELLEN (Deep-Dive, waehrend Feature)      ║
║                                                                         ║
║  Model vs Wissen:                                                      ║
║    Model  = Technisch, W{n}, "Wie funktioniert es BEI UNS?"           ║
║    Wissen = Erklaerend, Feynman, "Was IST es?"                         ║
║    BEIDE leben im Vault UND in RAG global_knowledge (readonly).        ║
║                                                                         ║
║  RAG Collections:                                                      ║
║    local_knowledge_{feature_id} = Feature-isoliert, temporaer          ║
║    global_knowledge             = Eine Collection, verifiziert, global ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  PIPELINE-POSITION:                                                    ║
║                                                                         ║
║  Feature-START:                                                        ║
║    [/_W_fetch] → /_taskDefinition → /_spec → /_model → ...            ║
║    (Erst Vault + RAG durchsuchen, DANN Model bauen)                    ║
║                                                                         ║
║  Feature-WAEHREND (nach Cycles):                                       ║
║    ... → /_SC_observe → [/_W_push_temp auto] → ...                    ║
║    (Models, OBSERVE, ERGEBNIS temporaer ins RAG pushen)                ║
║                                                                         ║
║  Feature-ENDE:                                                         ║
║    ... → /_model finish → [/_W_push_global {MODELS}] →                ║
║    [/_W_modelSplit] → [/_W_obsidianSync hard] → /_retrospektive → PR  ║
║    (Quality Gate, dann global pushen, dann Vault sync)                 ║
║                                                                         ║
║  PROZESSBEGLEITEND (v3.0, easy/normal Sync als paralleler Worker):     ║
║    Nach Model-Update: /_W_sync_orchestrate easy (parallel)            ║
║    Nach Ergebnis: /_W_sync_orchestrate easy/normal --co-work (parallel)║
║    Nach W_push_temp: /_W_sync_orchestrate easy (parallel)             ║
║    (Statt direktem /_W_obsidianSync — DRY via sync_orchestrate)       ║
║    /_W_push_temp (nach jedem Cycle, Models/OBSERVE pushen)            ║
║    /_knowledge (parallel, blockiert NICHT)                             ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  VAULT-KONFIGURATION (plattform-agnostisch, v3.0):                     ║
║                                                                         ║
║  Reihenfolge (4-stufig, wie W_fetch v3.0):                             ║
║    1. Environment: $OBSIDIAN_VAULT_PATH                                ║
║    2. Fallback: Manifest "## Obsidian Sync" VAULT-Wert                 ║
║    3. Default Linux: /home/uczen/Documents/DCS                         ║
║    4. Default Windows: C:\Users\Administrator\Documents\DCS            ║
║                                                                         ║
║  Vault-Inhalt:                                                         ║
║    *_Model.md     Thematische Models (readonly, aus modelSplit)        ║
║    *_Wissen.md    Wissens-Dokumente (readonly, aus /_knowledge)        ║
║    {FEATURE}.md   Feature-Notes (Master-Hub, Wiki-Links)              ║
║    _Tag-Index.md  Thematischer Index aller Dokumente                  ║
║    _parking-lot.md  Geparkte Items (global)                           ║
║    Synthese-Docs  OBSERVE, HYPOTHESEN, ERGEBNIS, etc.                 ║
║                                                                         ║
║  PARKING LOT (#4): GELOEST (Dual-Source implementiert)                 ║
║    → /_W_fetch v3.0: Wellen + Schwierigkeitsstufen + Dual-Source    ║
║    → /_W_push_temp v2.1: Feature-isolierter RAG Push                 ║
║    → /_W_push_global v1.0: Quality Gate + Dual-Push                  ║
║    → Status: GELOEST + ERWEITERT (WK Redesign, 2026-02-20)          ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  MANIFEST-INTEGRATION (GAP-008):                                       ║
║                                                                         ║
║  Die Commands erstellen/aktualisieren folgende Manifest-Sektionen:     ║
║                                                                         ║
║  ## Wissens-Basis (via /_W_fetch)                                      ║
║  **DATUM:** {DATUM}                                                    ║
║  **SUCHE:** {N} Themen, {M} Dokumente gefunden                         ║
║  **QUELLEN:** Vault ({V} Hits), RAG ({R} Hits), BOTH ({B} Hits)       ║
║                                                                         ║
║  | Dokument | Typ | Source | Score | Aktion |                         ║
║  |----------|-----|--------|-------|--------|                         ║
║  | Model.md | model | BOTH | 0.87 | Kopiert → .claude/models/ |       ║
║  | Episode.txt | - | RAG:global | 0.82 | Referenz (RAG-only) |        ║
║                                                                         ║
║  ---                                                                   ║
║                                                                         ║
║  ## RAG Push Status                                                    ║
║  **Collection:** mixed (local + global)                                ║
║  **Letzter Push:** {DATUM}                                             ║
║                                                                         ║
║  | Dokument | Collection | Chunks | Datum | Status |                  ║
║  |----------|-----------|--------|-------|--------|                  ║
║  | models/Model.md | local_knowledge_feature | 12 | 2026-02-14 | PUSHED | ║
║  | models/Model.md | global_knowledge | 12 | 2026-02-15 | GLOBAL |   ║
║  | wissen/Wissen.md | global_knowledge | 8 | 2026-02-15 | GLOBAL |   ║
║                                                                         ║
║  ---                                                                   ║
║                                                                         ║
║  ## Quality Gate Log                                                   ║
║  **Feature:** {FEATURE_NAME}                                           ║
║  **Letztes Gate:** {DATUM}                                             ║
║                                                                         ║
║  | Dokument | W{n} Status | Gate-Ergebnis | Datum |                   ║
║  |----------|-------------|---------------|-------|                   ║
║  | models/Model.md | 5B / 0W / 2P / 1O | PASS | 2026-02-15 |         ║
║  | wissen/Wissen.md | 0B / 0W / 0P / 0O | PASS (User) | 2026-02-15 | ║
║                                                                         ║
║  Legende: B=BESTAETIGT, W=WIDERLEGT, P=ZUR_PRUEFUNG, O=OFFEN          ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `.claude/analysis/_manifest.md` falls vorhanden und zeige den Wissens-Koaleszenz-Status:

```
WISSENS-KOALESZENZ STATUS:
  Feature: {NAME aus Manifest}
  Vault: {Primary Vault Pfad oder "$OBSIDIAN_VAULT_PATH"}

  W_fetch (Dual-Source):
    Letzter Einsatz: {Datum aus "## Wissens-Basis" oder "noch nie"}
    Vault-Hits: {V}
    RAG-Hits: {R}
    BOTH-Hits: {B}

  RAG Push Status:
    local_knowledge_{feature_id}: {N} Dokumente gepusht
    global_knowledge: {M} Dokumente gepusht
    Letzter Push: {Datum aus "## RAG Push Status"}

  Quality Gate:
    Letztes Gate: {Datum aus "## Quality Gate Log"}
    Dokumente geprueft: {K}
    PASS: {P}
    REJECT: {R}

  Obsidian Sync:
    Letzter Sync: {Datum aus "## Obsidian Sync"}
    Synced Docs: {Anzahl}
```

ARGUMENTS: $ARGUMENTS
