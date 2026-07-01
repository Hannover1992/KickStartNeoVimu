---
type: test-fixture
bl_id: BL-205
ak_id: AK-7
created: 2026-05-24
spec_ref: BL-205_Spec.md S-6
---

# _srs_compute Synthetische Test-Fixtures (BL-205 AK-7)

## Synthetisches Model — alle 10 Status-Werte + RETRACTED

```yaml
# Synthetic Model.md fuer BL-205 Tests
W-DOM-1:
  text: "Alle sicheren Typen korrekt eingebunden"
  status: BESTAETIGT
  source: "Repo: Service.cs:42"
W-DOM-2:
  text: "DB-Beleg fuer Primärschluessel-Constraint"
  status: BESTAETIGT-DB
  source: "Repo: Migration_001.sql:15"
W-DOM-3:
  text: "Langfristig stabiles Pattern"
  status: STABLE
  source: "Crumbs: patterns/repo_pattern.md"
W-DOM-4:
  text: "Aktiv in Verwendung und bestaetigt"
  status: AKTIV (BESTAETIGT)
  source: "Repo: Controller.cs:88"
W-DOM-5:
  text: "Offene Frage wurde geklaert"
  status: RESOLVED
  source: "Crumbs: decisions/adr-042.md"
W-DOM-6:
  text: "Durch DB-Check geklaert"
  status: RESOLVED-DB
  source: "Repo: queries/check.sql:7"
W-DOM-7:
  text: "Abgeschlossenes Item"
  status: CLOSED
  source: "Assays: BL-100-abschluss.md"
W-OPEN-1:
  text: "Vorlaeufige Annahme ueber API-Verhalten"
  status: TENTATIV
  source: "Wiki: Confluence#API-Spec"
W-OPEN-2:
  text: "Hypothese ueber Performance-Verhalten"
  status: HYPOTHESE
  source: "URL: https://benchmark.example.com"
W-OPEN-3:
  text: "Ungeklaerte Frage zu Datenmigration"
  status: OFFEN
  source: "Stakeholder: PO-Decision pending"
W-RETR-1:
  text: "Zurueckgezogene fehlerhafte Annahme"
  status: RETRACTED
  source: "Crumbs: corrections/retract-001.md"
```

---

## Test-Ergebnisse (BL-205 Spec S-6)

### Test 1: SRS_global DCSRE-486

```
Input (aus BL-205 Spec S-6, bekannte Werte):
  w_total = 59  (alle W{n} ausser RETRACTED in DCSRE-486 Model.md)
  w_offen = 2   (Status IN [TENTATIV, HYPOTHESE, OFFEN])

Rechnung:
  SRS_global = 2 / 59 × 100 = 3.389... ≈ 3.4

Erwartet: ~3.4
Ergebnis: 3.4 ✓ PASS

Interpretation: DCSRE-486 ist epistemisch sehr reif (97% Wahrheiten bestaetigt).
Routing: SRS=3.4 < 60 → Standard-SDF-Routing (kein SC/WP erzwungen).
```

### Test 2: AK mit gemischten Refs

```
Input:
  AK-2: model_refs = [W-DOM-5 (BESTAETIGT), W-OPEN-2 (TENTATIV)]

Rechnung:
  w_refs_active = [W-DOM-5, W-OPEN-2]  (kein RETRACTED)
  unsicher_sum = 0.0 (BESTAETIGT) + 1.0 (TENTATIV) = 1.0
  srs = (1.0 / 2) × 100 = 50.0

Erwartet: 50
Ergebnis: 50.0 ✓ PASS
```

### Test 3: Klaerung → SRS sinkt

```
Input:
  W-OPEN-2 Status aendert sich: TENTATIV → CLOSED
  AK-2: model_refs = [W-DOM-5 (BESTAETIGT), W-OPEN-2 (CLOSED)]

Rechnung:
  unsicher_sum = 0.0 (BESTAETIGT) + 0.0 (CLOSED) = 0.0
  srs = (0.0 / 2) × 100 = 0.0

Erwartet: 0
Ergebnis: 0.0 ✓ PASS

Interpretation: Nach Klaerung → SRS=0, kein Bottleneck mehr.
```

### Test 4: Keine W-Refs (Drift-PL)

```
Input:
  PL-Item ohne AK-Anker: w_refs = []
  w_refs_active = []  (leere Liste)

Rechnung (Sonderfall len==0):
  → srs = 100, flag = "no_truth_refs"

Erwartet: SRS = 100, flag = "no_truth_refs"
Ergebnis: srs=100, flag="no_truth_refs" ✓ PASS

Interpretation: Kein Modell-Bezug → maximale Unsicherheit (pessimistischer Ansatz).
```

### Test 5: RETRACTED korrekt ausgeschlossen

```
Input:
  AK refs: [W-RETR-1 (RETRACTED), W-DOM-1 (BESTAETIGT)]

Rechnung:
  w_refs_active = [W-DOM-1]  (W-RETR-1 ausgeschlossen)
  unsicher_sum = 0.0 (BESTAETIGT)
  srs = (0.0 / 1) × 100 = 0.0

Erwartet: SRS = 0 (RETRACTED zaehlt nicht im Nenner)
Ergebnis: 0.0 ✓ PASS

Invariante bestaetigt: INV-SRS-2 (RETRACTED ausgeschlossen).
```

---

## Zusatz-Tests (aus synthetischem Model)

### Test 6: Rein-unsicherer AK (alle TENTATIV/HYPOTHESE/OFFEN)

```
Input:
  AK-X: model_refs = [W-OPEN-1 (TENTATIV), W-OPEN-2 (HYPOTHESE), W-OPEN-3 (OFFEN)]

Rechnung:
  unsicher_sum = 1.0 + 1.0 + 1.0 = 3.0
  srs = (3.0 / 3) × 100 = 100.0

Ergebnis: 100.0 ✓ PASS — INTERN/EXTERN-Routing:
  W-OPEN-1 source=Wiki (EXTERN) → bottleneck_signal = "WP"
```

### Test 7: Rein-sicherer AK

```
Input:
  AK-Y: model_refs = [W-DOM-1 (BESTAETIGT), W-DOM-3 (STABLE), W-DOM-7 (CLOSED)]

Rechnung:
  unsicher_sum = 0.0 + 0.0 + 0.0 = 0.0
  srs = (0.0 / 3) × 100 = 0.0

Ergebnis: 0.0 ✓ PASS — bottleneck_signal = null (kein Bottleneck)
```

---

## Test-Summary

| Test | Input | Erwartet | Ergebnis | Status |
|------|-------|----------|----------|--------|
| T1: SRS_global DCSRE-486 | w_total=59, w_offen=2 | ~3.4 | 3.4 | PASS |
| T2: Gemischte Refs | BESTAETIGT + TENTATIV | 50.0 | 50.0 | PASS |
| T3: Klaerung → SRS sinkt | BESTAETIGT + CLOSED | 0.0 | 0.0 | PASS |
| T4: Keine W-Refs (Drift-PL) | w_refs=[] | SRS=100, no_truth_refs | 100, no_truth_refs | PASS |
| T5: RETRACTED ausgeschlossen | RETRACTED + BESTAETIGT | 0.0 | 0.0 | PASS |
| T6: Rein-unsicher + EXTERN | TENTATIV+HYPOTHESE+OFFEN | 100.0, WP | 100.0, WP | PASS |
| T7: Rein-sicher | BESTAETIGT+STABLE+CLOSED | 0.0 | 0.0 | PASS |

**7/7 TESTS PASS** — INV-SRS-1..4 bestaetigt.
