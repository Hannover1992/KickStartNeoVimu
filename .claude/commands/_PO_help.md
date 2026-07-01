---
type: satellite
---

# PO-Pipeline - Hilfe & Uebersicht

Zeige die Uebersicht der Product-Owner-Pipeline (PO-Orchestrate) Commands.

## Aufruf

```
/_PO_help
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  PO-PIPELINE: Paper → Epic → User Story (9 Commands)                    ║
║                                                                           ║
║  TANDEM-ROLLEN:                                                           ║
║                                                                           ║
║  PO  (Product Owner)        = Nutzernutzen, Epic-Priorisierung,          ║
║                               User Stories, Value-Score                  ║
║  PE  (Principal Engineer)   = Forschungsvalidierung, theoretische        ║
║                               Machbarkeit, Paper-Evidenz                 ║
║  ARC (Architect)            = Code-nahe Machbarkeit, Constraints,        ║
║                               Architektur-Grenzen, techn. Schulden       ║
║  CXO (optional, Komplexitäts-/Budget-Manager)                            ║
║                               = Delivery-Priorisierung, Komplexitaet,    ║
║                               Wertschoepfung, Release-Planung            ║
║                                                                           ║
║  ═══ SETUP ═══                                                           ║
║                                                                           ║
║  /_PO_paperRead    Paper-Analyse & Insights-Extraktion                   ║
║                    → Paper(s) lesen, Schluessel-Insights extrahieren     ║
║                    → Themen-Cluster bilden (fuer Epic-Mapping)           ║
║                    → RAG: research_query fuer Kontext                    ║
║                                                                           ║
║  ═══ EPIC-PHASE ═══                                                      ║
║                                                                           ║
║  /_PO_epicExtraction   Epic-Extraktion (PO + PE Tandem)                  ║
║                        → PO: Nutzernutzen pro Insight bewertet           ║
║                        → PE: Theoretische Machbarkeit validiert          ║
║                        → Resultat: Priorisierte Epic-Liste               ║
║                                                                           ║
║  /_PO_archConstraints  Architekt-Constraints pro Epic                    ║
║                        → ARC: Technische Machbarkeit pro Epic            ║
║                        → ARC: Constraints + Architektur-Grenzen         ║
║                        → ARC: Technische Schulden & Risiken              ║
║                        → Output: Constrained Epic-Liste                  ║
║                                                                           ║
║  ═══ USER STORY PHASE ═══                                                ║
║                                                                           ║
║  /_PO_userStoryDraft   User Story Drafts                                 ║
║                        → PO: "Als [User] moechte ich [Feature]..."       ║
║                        → PE: Evidenz-Annotation (Zitate + Papers)        ║
║                        → ARC: Constraint-Annotation (techn. Grenzen)     ║
║                        → Akzeptanzkriterien aus Forschung ableiten       ║
║                                                                           ║
║  /_PO_valueScore       Value-Scoring + Priorisierung                     ║
║                        → PO: Business Value (1-10)                       ║
║                        → PE: Research Evidence Score (1-10)              ║
║                        → ARC: Complexity Score (1-10)                    ║
║                        → MoSCoW-Mapping + Release-Plan                   ║
║                                                                           ║
║  /_PO_dependencyMap    Story-Abhaengigkeiten kartieren                   ║
║                        → Constraints zwischen User Stories               ║
║                        → Blocker + Enabler identifizieren                ║
║                        → Dependency-Graph erstellen                      ║
║                                                                           ║
║  ═══ SYNTHESE ═══                                                        ║
║                                                                           ║
║  /_PO_synthesis        Finale Epic + User Story Synthese                 ║
║                        → Alle 3 Rollen: Konsens-Bildung                  ║
║                        → Finales Epic-Dokument + User-Story-Set          ║
║                        → Quality Gate: Alle Stories haben Evidenz        ║
║                                                                           ║
║  /_PO_obsidianSync     Obsidian Vault Sync                               ║
║                        → Epics als Obsidian-Notes (YAML-Frontmatter)     ║
║                        → User Stories als verlinkte Sub-Notes            ║
║                        → Tags: #epic #user-story #evidence #constraint   ║
║                        → Wikilinks zwischen abhaengigen Stories          ║
║                                                                           ║
║  ═══ ORCHESTRIERUNG ═══                                                  ║
║                                                                           ║
║  /_PO_orchestrate      Team Lead PO-Pipeline-Orchestrierung              ║
║                        → Spawnt 3 Rollen-Agents (PO, PE, ARC)           ║
║                        → Paper → Epic → Story → Obsidian                 ║
║                        → HiL-Pause nach Synthese                        ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  PIPELINE-FLOW:                                                           ║
║                                                                           ║
║  /_PO_paperRead                                                           ║
║       │                                                                   ║
║       ▼                                                                   ║
║  /_PO_epicExtraction  ◄── PO + PE TANDEM (parallel)                      ║
║       │                                                                   ║
║       ▼                                                                   ║
║  /_PO_archConstraints  ◄── ARC (constraints einarbeiten)                 ║
║       │                                                                   ║
║       ▼                                                                   ║
║  /_PO_userStoryDraft  ◄── PO primary, PE + ARC annotieren               ║
║       │                                                                   ║
║       ▼                                                                   ║
║  /_PO_valueScore + /_PO_dependencyMap  (parallel)                        ║
║       │                                                                   ║
║       ▼                                                                   ║
║  /_PO_synthesis  ◄── Alle 3 Rollen: finales Dokument                    ║
║       │                                                                   ║
║       ▼                                                                   ║
║  /_PO_obsidianSync  ◄── Vault Integration                                ║
║       │                                                                   ║
║       ▼                                                                   ║
║  HiL-PAUSE (User: ACCEPT / RETRY / ABORT)                                ║
║                                                                           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ROLLEN-DYNAMIK (Tandem-Prinzip):                                        ║
║                                                                           ║
║  PO:  "Welchen Wert schafft das fuer den Nutzer?"                        ║
║  PE:  "Was sagt die Forschung? Ist das theoretisch machbar?"             ║
║  ARC: "Was sind die technischen Grenzen und Constraints?"                ║
║                                                                           ║
║  Entscheidungsmatrix pro Epic/Story:                                     ║
║    PO_value >= 7 AND PE_evidence >= 6 AND ARC_complexity <= 7            ║
║    → IMPLEMENT (Epic wird zu User Stories)                               ║
║    PE_evidence < 4 → RESEARCH_FIRST (mehr Paper benoetigt)              ║
║    ARC_complexity > 8 → SPIKE (technisches Risiko zuerst)               ║
║    PO_value < 4 → PARK (kein Nutzernutzen erkennbar)                    ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

ARGUMENTS: $ARGUMENTS
