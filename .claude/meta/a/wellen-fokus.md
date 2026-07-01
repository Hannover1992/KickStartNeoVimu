# Wellen-Fokus-Bereiche (A-Pipeline)

Referenz fuer `/_A_orchestrate`. Wird in Phase 3 (Agent-Prompts) und Phase 4.1a (Puppet-Master) verwendet.

## Command-Komplexitaet und Wellen-Defaults

| Command | Komplex. | Input | Explor. | Synth. | Kreat. | Wellen (normal) | Begruendung |
|---------|----------|-------|---------|--------|--------|-----------------|-------------|
| /_W_fetch | HOCH | viel | ja | ja | ja | 5-3-1 | Vault 5-Stufen-Fallback + 7 RAG-Collections. Kartografie. |
| /_taskDefinition | HOCH | viel | ja | ja | ja | 5-3-1 | pileOfMud (Screenshots→Mermaid), 7 Crumbs-Kategorien. |
| /_model | HOCH | viel | ja | ja | ja | 5-3-1 | 5 Explorer kartografieren Codebase. Kern-Artefakt. |
| /_spec | MITTEL | mittel | nein | ja | ja | 3-1 | KEINE Codebase-Exploration. Input-Dateien → 8 Kategorien. |
| /_gap | HOCH | viel | ja | ja | ja | 5-3-1 | Cross-Reference SPEC×MODEL×Codebase. Circuit-Breaker. |
| /_SC_modelMaintain | MITTEL | mittel | nein | ja | ja | 1 solo | Synthese aus OBSERVE+ERGEBNIS. Keine Exploration noetig. |

**Legende:** HOCH = 5-3-1 (Explorer+Drafter+Synthese), MITTEL = 3-1 (Drafter+Synthese), NIEDRIG = 1 solo.

## /_model Fokus-Bereiche

### Explorer-Fokus
| Agent | Fokus |
|-------|-------|
| E01 | architektur |
| E02 | konfiguration |
| E03 | code-flow |
| E04 | externe-deps |
| E05 | dokumentation |

### Drafter-Fokus
| Agent | Fokus |
|-------|-------|
| D01 | validierung |
| D02 | zusammenhaenge |
| D03 | constraints |

## /_spec Fokus-Bereiche

### Drafter-Fokus
| Agent | Fokus |
|-------|-------|
| D01 | architektur |
| D02 | komponenten |
| D03 | qualitaet |

## /_W_fetch Fokus-Bereiche

### Explorer-Fokus
| Agent | Fokus |
|-------|-------|
| E01 | vault-navigation |
| E02 | rag-collections |
| E03 | domain-hash |
| E04 | keyword-extraktion |
| E05 | tag-index-matching |

### Drafter-Fokus
| Agent | Fokus |
|-------|-------|
| D01 | kartograph |
| D02 | filter |
| D03 | konsolidierer |

## /_taskDefinition Fokus-Bereiche

### Explorer-Fokus
| Agent | Fokus |
|-------|-------|
| E01 | diagramme |
| E02 | dokumente |
| E03 | bestehendes-wissen |
| E04 | screenshots-mermaid |
| E05 | anforderungen |

### Drafter-Fokus
| Agent | Fokus |
|-------|-------|
| D01 | diagramme |
| D02 | dokumente |
| D03 | bestehendes-wissen |

## /_gap Fokus-Bereiche

### Explorer-Fokus
| Agent | Fokus |
|-------|-------|
| E01 | backend-komponenten |
| E02 | frontend-komponenten |
| E03 | interfaces |
| E04 | datenmodell |
| E05 | nfr-konventionen |

### Drafter-Fokus
| Agent | Fokus |
|-------|-------|
| D01 | konsolidierung |
| D02 | priorisierung |
| D03 | risiko |

## Sequentielle Commands (KEINE Wellen)

| Command | Agents | Modell |
|---------|--------|--------|
| /_SC_modelMaintain | 1 | ceiling |
