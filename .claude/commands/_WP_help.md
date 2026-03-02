# Paper-Pipeline - Hilfe & Uebersicht

Zeige die Uebersicht der Paper-Pipeline (WritePaper) Commands.

## Aufruf

```
/_WP_help
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  PAPER-PIPELINE: RAG-basiertes akademisches Schreiben (19 Commands)    ║
║                                                                         ║
║  ═══ SETUP (Projekt + Session) ═══                                     ║
║                                                                         ║
║  /_WP_init        Projekt-Initialisierung                              ║
║                   → Projekt-Ordner, config/project.yaml, Quellen-Scan  ║
║                   → MCP: research_ingest (RAG-Ingest aller Quellen)    ║
║                                                                         ║
║  /_WP_session     Session Parameter Configuration                      ║
║                   → chapter_focus, writing_style, citation_density      ║
║                   → Persistiert in config/session.yaml                  ║
║                                                                         ║
║  /_WP_structure   Paper-Strukturextraktion                             ║
║                   → LaTeX-Struktur parsen, Kapitel-Hierarchie          ║
║                   → Sections + Subsections mit Platzhaltern erkennen   ║
║                                                                         ║
║  ═══ KNOWLEDGE (Kapitel-Wissen aufbauen) ═══                           ║
║                                                                         ║
║  /_WP_chapterModel  Chapter Knowledge Model                           ║
║                     → Pro Kapitel: Wissens-Modell aus RAG aufbauen     ║
║                     → Keywords, Konzepte, Quellen-Zuordnung            ║
║                     → MCP: research_query (RAG-Abfragen)               ║
║                                                                         ║
║  /_WP_chapterGap    Chapter Gap Analysis & Decision                    ║
║                     → IST vs SOLL pro Kapitel-Sektion                  ║
║                     → Entscheidung: WRITE (neu) oder AUTOREVISE        ║
║                     → MCP: research_gaps (Luecken-Analyse)             ║
║                                                                         ║
║  /_WP_assess        Chapter Knowledge Assessment                      ║
║                     → Bewertung: Genuegt das Wissen zum Schreiben?     ║
║                     → Coverage-Score pro Sektion                       ║
║                     → Trigger: /_WP_discovery bei Luecken              ║
║                                                                         ║
║  /_WP_research      RAG Source Ingestion                               ║
║                     → Neue Quellen in RAG ingestieren                  ║
║                     → MCP: research_ingest + research_query            ║
║                     → BibTeX-Extraktion + Chunk-Traceability           ║
║                                                                         ║
║  /_WP_discovery     Research Source Discovery                          ║
║                     → Fehlende Quellen identifizieren + beschaffen     ║
║                     → WebSearch fuer neue Paper/Quellen                ║
║                     → Trigger: /_WP_research fuer Ingest               ║
║                                                                         ║
║  ═══ WRITING (Kapitel schreiben) ═══                                   ║
║                                                                         ║
║  /_WP_write         Chapter Draft Writing                              ║
║                     → LaTeX-Draft pro Kapitel-Sektion                  ║
║                     → RAG-only: NUR aus ingestierten Quellen zitieren  ║
║                     → MCP: research_query_r2 (3-Collection Exclusion)  ║
║                                                                         ║
║  /_WP_visual        Visual Figure Generation & Review                  ║
║                     → Abbildungen, Diagramme, Tabellen erstellen       ║
║                     → TikZ, pgfplots, Mermaid → LaTeX-Integration     ║
║                     → Review: Passt Abbildung zum Text?                ║
║                                                                         ║
║  /_WP_review        Cross-Review & Scoring                             ║
║                     → Kapitel bewerten (Scoring-Rubrik)                ║
║                     → Cross-Referenzen zwischen Kapiteln pruefen       ║
║                     → Annotations fuer Verbesserungen                  ║
║                                                                         ║
║  /_WP_synthesis     Draft Synthesis & Consensus                        ║
║                     → Mehrere Drafts zusammenfuehren                   ║
║                     → Konsens-Bildung bei Widerspruechen               ║
║                     → Finaler Kapitel-Draft                            ║
║                                                                         ║
║  /_WP_chapterPDF    Chapter PDF Generation & Email Delivery            ║
║                     → final-draft.md -> LaTeX -> PDF kompilieren       ║
║                     → PDF per Email an User senden (Gmail SMTP)        ║
║                     → NON-BLOCKING: Pipeline stoppt nie wegen PDF      ║
║                                                                         ║
║  ═══ QUALITY (Qualitaetssicherung) ═══                                 ║
║                                                                         ║
║  /_WP_qualityGate   Chapter Quality Gate Orchestrator                  ║
║                     → 8 Quality Gates pro Kapitel                      ║
║                     → Citation-Check, Plagiarism, Style, Structure     ║
║                     → MCP: research_verify (Zitat-Verifikation)        ║
║                                                                         ║
║  /_WP_convergence   Quality Loop Convergence Controller                ║
║                     → INNER-Loop: Kapitel bis Threshold iterieren      ║
║                     → Stagnations-Erkennung + ABORT-Trigger            ║
║                     → Automatische Eskalation bei Nicht-Konvergenz     ║
║                                                                         ║
║  /_WP_autoGen       Gap-Driven Section Rewrite                         ║
║                     → Automatisches Rewrite schwacher Sektionen        ║
║                     → GAP-getrieben: NUR Sektionen unter Threshold     ║
║                     → MCP: research_query_r2 + mark_covered            ║
║                                                                         ║
║  ═══ META (Reflexion + Abschluss) ═══                                  ║
║                                                                         ║
║  /_WP_reflect       Kapitel Retrospektive & OUTER-Loop Controller      ║
║                     → Kapitel-Retrospektive: Was hat funktioniert?      ║
║                     → OUTER-Loop: Naechstes Kapitel waehlen            ║
║                     → MCP: research_mark_covered (Abschluss)           ║
║                                                                         ║
║  /_WP_finalize      Paper Finalization & Publication                   ║
║                     → Gesamt-Paper zusammenfuegen                      ║
║                     → Finale Quality Gates (Paper-Ebene)               ║
║                     → BibTeX konsolidieren, PDF generieren             ║
║                                                                         ║
║  ═══ ORCHESTRIERUNG (Meta-Command) ═══                                 ║
║                                                                         ║
║  /_WP_orchestrate   Team Lead Kapitel-Orchestrierung                   ║
║                     → Spawnt Worker, leitet durch alle Steps           ║
║                     → Setup → Knowledge → Write → Quality → PDF       ║
║                     → Email an User → Feedback → ACCEPT/RETRY/ABORT   ║
║                     → Bei ACCEPT: /_W_push_orchestrate + /_finish      ║
║                     → EIN Command fuer den gesamten Kapitel-Zyklus     ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  PIPELINE-FLOW (typischer Ablauf):                                     ║
║                                                                         ║
║  /_WP_init → /_WP_session → /_WP_structure                            ║
║       │                          │                                      ║
║       ▼                          ▼                                      ║
║  /_WP_research              Pro Kapitel:                                ║
║       │               ┌──────────────────────┐                          ║
║       ▼               │  /_WP_chapterModel   │                          ║
║  /_WP_discovery       │  /_WP_chapterGap     │                          ║
║  (bei Luecken)        │  /_WP_assess         │                          ║
║       │               │       │              │                          ║
║       └───────────────┤  /_WP_write          │                          ║
║                       │  /_WP_visual         │                          ║
║                       │  /_WP_review         │  INNER                   ║
║                       │  /_WP_synthesis      │  LOOP                    ║
║                       │  /_WP_qualityGate    │                          ║
║                       │  /_WP_convergence ◄──┘                          ║
║                       │       │ (nicht konvergiert)                      ║
║                       │       ▼                                         ║
║                       │  /_WP_autoGen                                   ║
║                       │       │                                         ║
║                       └───────┘ (zurueck zu write)                      ║
║                              │ (konvergiert)                            ║
║                              ▼                                          ║
║                       /_WP_chapterPDF (PDF + Email)                     ║
║                              │                                          ║
║                              ▼                                          ║
║                       /_WP_reflect ──▶ naechstes Kapitel               ║
║                              │ (alle Kapitel fertig)                    ║
║                              ▼                                          ║
║                       /_WP_finalize                                     ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  MCP-TOOLS (CleanCoder RAG):                                           ║
║                                                                         ║
║  research_ingest        Quellen in RAG aufnehmen (6-Stage Pipeline)    ║
║  research_query         Projekt-isolierte RAG-Abfrage                  ║
║  research_query_r2      3-Collection Exclusion (Round 2+)              ║
║  research_gaps          Quellen-Luecken analysieren                    ║
║  research_verify        Zitat-Verifikation gegen RAG                   ║
║  research_mark_covered  Geschriebenes als COVERED markieren            ║
║  research_add_exclusion Falsche Richtungen ausschliessen               ║
║  research_reset_collections  Collections zuruecksetzen                 ║
║                                                                         ║
║  3-COLLECTION-SYSTEM:                                                   ║
║    SOURCES   = Quellen (positiv, was wir zitieren koennen)             ║
║    COVERED   = Bereits Geschriebenes (soft penalty, Wiederholung)      ║
║    EXCLUSION = Falsche Richtungen (hard filter, ausgeschlossen)        ║
║                                                                         ║
║  ROUND 2+ LOGIK:                                                       ║
║    Query → SOURCES ∩ ¬EXCLUSION − COVERED_penalty                      ║
║    Vermeidet Wiederholung, schliesst falsche Richtungen aus            ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  ZWEI-LOOP-ARCHITEKTUR:                                                ║
║                                                                         ║
║  INNER-LOOP (pro Kapitel):                                             ║
║    write → visual → review → synthesis → qualityGate → convergence     ║
║    → [autoGen wenn nicht konvergiert] → zurueck zu write               ║
║    → [chapterPDF wenn konvergiert] → PDF + Email an User               ║
║    Abbruch: Max 5 Iterationen oder Konvergenz-Threshold erreicht       ║
║                                                                         ║
║  OUTER-LOOP (Paper-Ebene):                                             ║
║    reflect → naechstes Kapitel → INNER-LOOP → reflect → ...            ║
║    Reihenfolge: Kapitel-Abhaengigkeiten beachten                       ║
║    Abschluss: Alle Kapitel konvergiert → finalize                      ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  WISSENS-KOALESZENZ SCHNITTSTELLE:                                     ║
║                                                                         ║
║  WP nutzt ein EIGENES Wissenssystem (research_* MCP Tools):            ║
║    research_ingest, research_query, research_query_r2,                  ║
║    research_gaps, research_verify, research_mark_covered                ║
║  Dieses System arbeitet mit BibTeX, 3-Collection-Logik                 ║
║  (SOURCES/COVERED/EXCLUSION) und projekt-isolierten Queries.           ║
║                                                                         ║
║  Koexistenz mit globalem W-System (OPTIONAL):                          ║
║    /_W_fetch       Vault-Wissen als zusaetzliche Quellen (optional)    ║
║    /_W_push_global Paper-Ergebnisse global sichern (optional)          ║
║    global_knowledge Shared Collection als WP-Quelle (optional)         ║
║                                                                         ║
║  Warum 2 Systeme parallel?                                             ║
║    WP braucht BibTeX, Citations, COVERED/EXCLUSION — Features die      ║
║    das W-System nicht hat. Das W-System ist fuer SC/I optimiert.       ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `.claude/analysis/_manifest.md` falls vorhanden und zeige den WritePaper-Status:

```
AKTUELLER STAND WritePaper:
  Phase: {Phase aus Manifest}
  Naechster Schritt: {Command aus Manifest}
  Zyklen: {Anzahl}
  Model: v{Version}
```

ARGUMENTS: $ARGUMENTS
