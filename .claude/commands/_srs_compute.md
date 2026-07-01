---
status: active
version: 1.0.0
type: skill
created: 2026-05-24
feature: BL-205
ak_implements: [AK-3]
contract:
  reads:
    - {file: "{MODEL_PATH}", purpose: "W{n}-Status aus Model.md lesen (OFFEN/TENTATIV/HYPOTHESE/BESTAETIGT/...)"}
    - {file: "{ITEM_CONTEXT}", purpose: "model_refs des Items (AK, PL, Batch)"}
  writes:
    - {output: "srs_result", purpose: "{srs, flag, breakdown} — kein File-Write, nur In-Memory-Return"}
  not_writes:
    - recommended_modus
    - sdf_mode
    - mode_recommendation
---

# _srs_compute (BL-205 AK-3)

Compute SRS (Epistemik-Score) fuer ein Item (AK, PL-Item oder Batch).

## Aufruf-Interface

```
Skill(_srs_compute, args="--item={ak_id|pl_id|batch_id} --model={path}")
```

## SRS-Formel (BL-205 S-2, kanonisch)

```python
srs_weight = {
    # Sichere Knoten (srs_weight = 0.0):
    "BESTAETIGT":         0.0,
    "BESTAETIGT-DB":      0.0,
    "STABLE":             0.0,
    "AKTIV (BESTAETIGT)": 0.0,
    "RESOLVED":           0.0,
    "RESOLVED-DB":        0.0,
    "CLOSED":             0.0,
    # Unsichere Knoten (srs_weight = 1.0):
    "TENTATIV":           1.0,
    "HYPOTHESE":          1.0,
    "OFFEN":              1.0,
    "experiment_provable": 1.0,  # NEU [BL-239 AK-1/AK-9]: nur experimentell schliessbare Wahrheit.
                                 # Default 1.0 = volle Unsicherheits-Gewichtung wie OFFEN (OQ-2-Default,
                                 # revisierbar). Die KATEGORIE (nicht die SRS-Hoehe) triggert M5 — siehe
                                 # _SDF_berater_modusEntscheidung SCHRITT 4.5 (AK-2).
    # RETRACTED: ausgeschlossen (zaehlt NICHT im Nenner)
}

def compute_srs(item, model_path):
    w_refs = resolve_truth_refs(item, model_path)
    w_refs_active = [w for w in w_refs if w.status != "RETRACTED"]

    if len(w_refs_active) == 0:
        return {"srs": 100, "flag": "no_truth_refs", "breakdown": [], "srs_source": "srs_compute"}

    unsicher_sum = sum(srs_weight[w.status] for w in w_refs_active)
    srs = round((unsicher_sum / len(w_refs_active)) * 100, 1)

    return {
        "srs": srs,
        "flag": None,
        "breakdown": [{"id": w.id, "status": w.status, "weight": srs_weight[w.status]} for w in w_refs_active],
        "srs_source": "srs_compute"   # NEU [BL-239 AK-6]: Provenance — dieser srs ist ENGINE-DERIVED.
                                      # Nur engine-derived srs darf das SC-Gate (modusEntscheidung srs>=60)
                                      # treiben; hand-authored srs (BL-Frontmatter/manuell) ist Anzeige-only.
    }
```

## Bewertungs-Basis: PL↔W-Referenz, ak_ref optional (BL-312 AK-7, Klarstellung)

Die SRS-Bewertung beruht AUSSCHLIESSLICH auf der **PL↔W-Referenz** (`model_refs` / W{n}-status —
siehe `srs_weight`-Tabelle oben). Ein **`ak_ref` ist ein OPTIONALER Zusatz-Anker, KEINE
Bewertungs-Voraussetzung**: SRS wird NIE durch ein fehlendes AK gegated. Ein late Item OHNE AK,
aber MIT `model_refs` (ggf. nachtraeglich via **W_fetch-light** geknuepft — siehe
`scripts/w_fetch_light.py`, `match_item_to_model`), bekommt ein vollwertiges srs aus den W{n}-Stati.
Nur ein Item OHNE jede Truth-Ref faellt in `no_truth_refs` (srs=100, INV-SRS-3) — und das ist dann
KORREKT (echtes Unbekanntes), nicht ein AK-Mangel. (Diese Klarstellung ist additiv und aendert weder
Formel noch Contract — sie dokumentiert das bereits AK-freie Verhalten; siehe `test_srs_compute.py::TestComputeSrsEdgeCases::test_akfree_evaluation`.) [BL-312 AK-7]

## Intern/Extern-Routing (AK-3, BL-205 S-4)

```
W{n}.source bestimmt Routing:

INTERN (SC klaerbar):
  - "Repo: ..."       | "Crumbs: ..."    | "Assays: ..."   | "W_fetch: ..."

EXTERN (WP erforderlich):
  - "Wiki: ..."        | "URL: https://..." | andere Story-ID
  - "Stakeholder: ..." | "Industry-Standard: ..."

Routing-Signal (Output-Feld, kein Modus-Vorschlag):
  unsicher_intern_count = count(w for w in w_refs_active if w.source ist INTERN AND srs_weight[w.status] == 1.0)
  unsicher_extern_count = count(w for w in w_refs_active if w.source ist EXTERN AND srs_weight[w.status] == 1.0)

Hinweis fuer SDF Phase 1.1 (KEIN Modus-Vorschlag):
  IF unsicher_extern_count > 0:  bottleneck_signal = "WP"
  ELIF unsicher_intern_count > 0: bottleneck_signal = "SC"
  ELSE:                           bottleneck_signal = null
```

## Invarianten

- INV-SRS-1: `srs_weight`-Dict ist ABGESCHLOSSEN — Status-Werte ausserhalb der Tabelle → FAIL
- INV-SRS-2: RETRACTED zaehlt NIE im Nenner
- INV-SRS-3: `no_truth_refs` → srs=100 (pessimistisch, kein Fallback auf Heuristik)
- INV-SRS-4: Routing-Signal ist BEOBACHTUNG, KEINE Modus-Empfehlung (INV-MODUS-5)
- INV-SRS-5 [BL-239 AK-6 Guard]: srs aus `_srs_compute` traegt `srs_source="srs_compute"` (engine-derived).
  Hand-authored srs-Werte (BL-Frontmatter / manuell gesetztes metric_per_batch ohne Pipeline-Herkunft)
  sind NICHT engine-derived und duerfen das SC-Gate (modusEntscheidung srs>=60) NICHT treiben — nur
  Anzeige. Default bei FEHLENDEM `srs_source`: trusted (non-breaking fuer Legacy); explizit
  `srs_source="hand_authored"` → untrusted. Genuine Unsicherheit signalisiert der Mensch ueber den
  `experiment_provable`-Status (kategorie-basiert, vertrauenswuerdig), NICHT ueber eine rohe srs-Zahl.
- INV-SRS-6 [BL-255 AK-4 Guard, 2026-06-10]: Anti-False-Certainty STATUS-Guard (orthogonal zum
  Zahlen-Guard INV-SRS-5). Ein Status-Write auf BESTAETIGT / "AKTIV (BESTAETIGT)" (am W{n}; analog
  AK-Status `confirmed` in 3_Spec) OHNE whitelisted `confirmed_by` + Pflicht-Evidenz wird GEBLOCKT.
  confirmed_by-Whitelist (SINGLE-SOURCE — DIESE Liste, keine Kopien; Konsumenten wie
  `_SC_modelMaintain` und kuenftig BL-251 referenzieren hierher):
    - `abnahme_verdikt` — NEU BL-255: VERIFIED-Verdikt aus `_I_verify` (verify_mode tdd|scenario|convention)
    - `experiment`      — bestehend: experiment-derived (SC-Pfad)
    - `user_hil`        — bestehend: explizite User-Bestaetigung
  Pflicht-Evidenz fuer `abnahme_verdikt`: `verify_ref` (Pfad zum verify_report) + `confirmed_at` (ISO).
  BL-239 AK-6 / BL-251 AK-S3 bleiben AKTIV — Whitelist-ERWEITERUNG, keine Deaktivierung (NFR-3).
  0-Formel-Diffs: `srs_weight`-Dict + SRS-Formel UNVERAENDERT (NFR-4, INV-SRS-1 intakt).

### BL-251-Schnittstellen-Constraint (BL-255 AK-9, 2026-06-10)

- **Single-Source:** BL-251 (Eingangs-Seite, Anti-False-Certainty-Guard) und BL-255 (Ausgangs-Seite,
  Confirm-Kollaps) nutzen DIESELBE `confirmed_by`-Whitelist — die Liste in INV-SRS-6 oben.
  KEINE zweite Liste anlegen (Convention-Verify: Whitelist existiert genau 1x im System).
- **Roll-out-Ordering:** BL-255 wird VOR oder ZUSAMMEN mit BL-251 ausgerollt — Eingangs-Seite ohne
  Ausgangs-Seite verschaerft die srs-Inflation (Einbahn-Verschaerfung, W27).
- **Uebergangs-Sichtbarkeit:** Bis BL-251's AK→W-Pflicht (jede AK >= 1 W-Ref) greift, macht AK-8
  (`_SDF_berater_recalibrate` R3 `no_truth_refs_count`) ref-lose AKs/PL-Items als `no_truth_refs`
  SICHTBAR statt sie zu kollabieren. INV-SRS-3 bleibt: `no_truth_refs` → srs=100.

## Aufruf-Kontext

Dieser Skill wird von folgenden Konsumenten aufgerufen:
- `_K_score` (per-AK srs_pro_ak Berechnung)
- `_IDF_berater_metricPlanner` (per-Batch SRS-Aggregation)
- `_SDF_berater_modusEntscheidung` (Phase 1.1, als Daten-Input)
- `_IDF_berater_plBewertung` (Phase 3.8a, SRS-Refresh pro PL-Item — BL-203 AK-2)
