# ImplementationHandOff Template (W99)

**Quelle:** Extrahiert aus `_SC_orchestrate.md` v2.4 → v3.0 (Decomposition)
**Geladen von:** Team Lead in Phase 3.4 POST-CYCLE (nach DONE/FORCE-Decision)

**Zweck:** SC→I Uebergabe-Vertrag. Team Lead erstellt dieses Dokument direkt.

---

## Ziel-Pfad

```
{VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HANDOFF.md
```

(BL-151 + PL-D Decision 2026-05-07; vorher: `.claude/analysis/synthese/{NAME}-HANDOFF.md`)

---

## Template

```markdown
---
type: handoff
feature: {NAME}
date: {YYYY-MM-DD}
cycles: {C}
sc_status: {DONE|FORCE}
srs_final: {score}
---

# ImplementationHandOff: {NAME}

## 1. LOESCHEN (Prototypen-Artefakte, untracked files)
- {Liste der Dateien die VOR I-Pipeline bereinigt werden muessen}
- Untracked files aus `git status` die nicht produktiv sind

## 2. BEHALTEN (produktive Dateien + Status)
- {Datei}: {Status} (AKTIV / ZUR_PRUEFUNG / FERTIG)

## 3. OFFENE AUFGABEN (W{n} AKTIV + ZUR_PRUEFUNG)
| # | W{n} | Beschreibung | Prioritaet |
|---|------|-------------|-----------|
| 1 | W{x} | {kurz} | HOCH/MITTEL/NIEDRIG |

## 4. ARCHITEKTUR-ENTSCHEIDUNGEN (ADR-Zusammenfassung)
- ADR {v}: {Entscheidung} (Status: BESTAETIGT/OFFEN)

## 5. KRITISCHE HINWEISE
- Externe Abhaengigkeiten: {Liste}
- Risiken: {Liste}
- Scope-Einschraenkungen: {was ist RAUS}

## 6. SRS-TREND (EC-2, W180-B)
| Zyklus | Score | Trend | Diff |
|--------|-------|-------|------|
| 1      | {srs_zyklus_1} | -    | -    |
| {C}    | {srs_final}    | ↓/↑  | {diff_percent}% |

Quelle: Manifest `sc_final_srs` pro Zyklus (OBSERVE{N}-Frontmatter).
Interpretation: {z.B. "Substantielle Reduktion", "Stagnation", "Komplexitaets-Anstieg"}

## 7. DISCOVERY-GAPS (EC-2, W180-B)
Topics mit unzureichender RAG-Abdeckung (< 3 Chunks) oder offenen W{n}:
| Topic | W{n} | Status | Chunks | Empfehlung |
|-------|------|--------|--------|------------|
| {topic_1} | W{x} | ZUR_PRUEFUNG | {n} | I-Phase vertiefen |
| {topic_2} | W{y} | AKTIV        | 0   | Grundlagen fehlen |

Quelle: `w_register where status IN (AKTIV, ZUR_PRUEFUNG)` + RAG gap-Analyse.
Leer wenn alle kritischen W{n} BESTAETIGT: `- (keine offenen Gaps)`

## 8. ADR-RATIONALE (EC-2, W180-B)
Architektur-Entscheidungen mit vollstaendiger Begruendung fuer I-Agenten:
| ADR | Entscheidung | Begruendung | Kontext | Status |
|-----|-------------|-------------|---------|--------|
| ADR-{v} | {Was entschieden} | {Warum} | W{n}-Referenz | BESTAETIGT/OFFEN |

Quelle: Model.md ADR-Sektion + W{n}-Notizen.
Zweck: I-Agenten verstehen das WARUM hinter Architektur-Entscheidungen.
```

---

## Pflicht-Sektionen (Minimum fuer Gate C6)

4 Pflicht-Sektionen: LOESCHEN, BEHALTEN, OFFENE AUFGABEN, ARCHITEKTUR
4 Optional-Erwartet: KRITISCHE HINWEISE, SRS-TREND, DISCOVERY-GAPS, ADR-RATIONALE

DONE_TIMESTAMP wird nach HANDOFF gesetzt (genutzt von /_W_push_orchestrate CHECK 1).
