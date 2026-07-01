# POST-I REVIEW-Modus (--mode=review, v2.1)

**Quelle:** Extrahiert aus `_SC_orchestrate.md` v2.4 → v3.0 (Decomposition)
**Geladen von:** Team Lead bei Modus-Erkennung (--mode=review)

---

## Zweck

Post-Implementation SC-Zyklen (SC→I→SC) unterscheiden sich fundamental von Discovery-Zyklen:
- Code existiert bereits → kein SRS-Baseline noetig
- Findings sind Reparatur-Findings → gehoeren NICHT ins Haupt-Model
- Gates muessen auf Code-Quality kalibriert sein, nicht auf Wissens-Expansion

**Evidenz:** DCSRE-93 Cycles 5+6 waren inhaltlich wertvoll (IK-Bug, DTO-Kompatibilitaet),
aber hatten keine passende Pipeline-Struktur. Reparatur-Findings trieben ModelBloat.

---

## Aktivierung

```
/_SC_orchestrate {NAME} [difficulty] [ceiling] [floor] --mode=review
```

Inkompatibel mit: `-I` (INLINE), `--mode=analyse`

---

## Unterschiede zum Standard-Modus

| Aspekt | Standard (FULL/INLINE) | Review (Post-I) |
|--------|---------------------|-----------------|
| Gate 1 (Battle-Royale) | SRS-Tracking aktiv | SRS-Tracking DEAKTIVIERT |
| Gate 3 (Feature-Abschluss) | W{n} Coverage | Code-Quality Coverage |
| Gate 6 (Post-Impl-Check) | NICHT AKTIV | AKTIV (Reality-Check) |
| Findings-Pfad | Haupt-Model (models/) | Separater Pfad (post-impl/) |
| W{n}-Schreibziel | {NAME}_Model.md | {NAME}-REVIEW-PROTOKOLL.md |
| Max Zyklen | easy=3, normal=5, hard=8 | easy=2, normal=3, hard=5 |
| DONE-Bedingung | Feature-Coverage 90% | Alle Review-Items RESOLVED/DEFERRED |

---

## Gate 6: Post-Implementation-Reality-Check

Gate 6 ersetzt Gate 1 (Battle-Royale) im Review-Modus:

```markdown
## Gate 6: Post-Implementation-Reality-Check

### Code-Quality Pruefung

| Pruefung | Status | Details |
|----------|--------|---------|
| Tests vorhanden fuer alle Aenderungen | ok/fail | {N}/{M} Tests |
| Keine Regressions-Findings | ok/fail | {Details} |
| ADR-Konformitaet geprueft | ok/fail | {Abweichungen} |
| Model<->Code-Konsistenz | ok/fail | {Divergenzen} |

**Empfehlung:** {RESOLVED | REPARATUR NOETIG | DEFERRED}
```

---

## Separater Findings-Pfad

```
Standard: .claude/models/{NAME}_Model.md           → W{n} direkt
Review:   .claude/analysis/post-impl/{NAME}-REVIEW-PROTOKOLL.md → Reparatur-Findings
```

Verhindert semantischen ModelBloat durch kurzlebige Code-Quality-Findings.
Nur Findings die nach Review als "permanent relevant" bewertet werden,
werden manuell ins Haupt-Model uebernommen.

---

## Manifest-Flags (Review-Modus)

```yaml
SC_PIPELINE_STATE:
  modus: REVIEW
  sc_mode: REVIEW
  review_target: post-impl
  review_items_total: {N}
  review_items_resolved: {M}
  review_items_deferred: {K}
```
