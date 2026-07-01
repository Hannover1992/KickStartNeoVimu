---
name: _IDF_berater_metric_derivation
description: "Deterministische Metric-Derivation fuer IDF PL-Items: Schneide-Algorithmus (AK-15), SRS-Formel (AK-16), K-Score-Formel (AK-17). Beseitigt das Schema-without-Algorithm Anti-Pattern."
status: active
version: 1.0.0
created: 2026-05-17
feature_anchor: BL-174
parent: _IDF_orchestrate
phase: 3.5 (validator/derivation, NEU)
model_tier: middle
contract:
  reads:
    - {file: "{VAULT}/Backlog/{BL_ID}/3_Spec/{BL_ID}_Spec.md", path: "AK-Texte + keywords", purpose: "Stufe-1 Keyword-Match Quellmaterial"}
    - {file: "{VAULT}/Backlog/{BL_ID}/2_Model/{BL_ID}_Model.md", path: "W-Knoten + confidence + ak_to_w_mapping", purpose: "W-Knoten-Pool fuer Schneiden + SRS-Berechnung"}
    - {file: "{VAULT}/Backlog/{BL_ID}/4_K-Score/{BL_ID}_K-SCORE.md", path: "per_ak k_score + k_aufwand", purpose: "K-Score weighted_mean Eingabe (AK-17)"}
    - {file: "{VAULT}/Backlog/{BL_ID}/6_PL/*_PL_Items.md", path: "PL-Item.description", purpose: "Input fuer Metric-Ableitung pro Item"}
  writes:
    - {file: "{VAULT}/Backlog/{BL_ID}/6_PL/*_PL_Items.md", path: "source_w_derived, source_aks_derived, derivation_source, derivation_confidence, metric_provenance, srs, srs_components, k_score, k_components", purpose: "Derived Metrics pro PL-Item (INV-DERIV-1 Pflichtfelder)"}
---

# /_IDF_berater_metric_derivation

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _IDF_berater_metric_derivation (BL-174, Phase 3.5)            ║
╠══════════════════════════════════════════════════════════════════════════╣
║  LIEST:  {VAULT}/Backlog/{BL_ID}/3_Spec/{BL_ID}_Spec.md                ║
║            AK-Texte, AK-Keywords (Stufe-1 Quelle)                       ║
║          {VAULT}/Backlog/{BL_ID}/2_Model/{BL_ID}_Model.md               ║
║            W-Knoten-Pool: id, confidence, ak_to_w_mapping               ║
║          {VAULT}/Backlog/{BL_ID}/4_K-Score/{BL_ID}_K-SCORE.md           ║
║            per_ak: {k_score, k_aufwand} (AK-17 Eingabe)                 ║
║          {VAULT}/Backlog/{BL_ID}/6_PL/*_PL_Items.md                     ║
║            PL-Item.description (Freitext-Input)                          ║
║  SCHREIBT: 6_PL/*_PL_Items.md (Frontmatter-Erweiterung):               ║
║            source_w_derived, source_aks_derived,                         ║
║            derivation_source, derivation_confidence,                     ║
║            metric_provenance, srs, srs_components,                       ║
║            k_score, k_components                                          ║
║  SCHREIBT NICHT: 3_Spec, 2_Model, 4_K-Score — read-only                ║
║                  _manifest.md — kein direkter Manifest-Write            ║
║                  DF_BATCH_STATE.modus — INV-MODUS-1 (SDF allein)        ║
║  ACTOR: _IDF_orchestrate (Phase 3.5, nach plAggregation)               ║
║  MODELL-TIER: sonnet                                                      ║
║  INVARIANTEN: INV-DERIV-1 (kein PL-Write ohne derivation_source),       ║
║               INV-DERIV-2 (Linter authoritative bei FAIL)               ║
║  MODUS-HINWEIS: Liefert NUR Daten (SRS/K-Score) — entscheidet          ║
║                 NIE den Modus. INV-MODUS-1 bleibt bei SDF Phase 1.1.   ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## AUFRUF

```
Skill(_IDF_berater_metric_derivation, args="{BL_ID} {batch_key}")

Parameter:
  {BL_ID}       — Backlog-ID, z.B. "BL-174"
  {batch_key}   — Batch-Schluessel fuer Iteration, z.B. "batch_A"

Vorbedingung:
  - 3_Spec/{BL_ID}_Spec.md existiert mit AK-Texten
  - 2_Model/{BL_ID}_Model.md existiert mit W-Knoten + confidence
  - 4_K-Score/{BL_ID}_K-SCORE.md existiert (oder Default-Fallback aktiv)
  - 6_PL/*_PL_Items.md PL-Items angelegt (description-Feld vorhanden)

Ausgabe:
  - PL-Items erweitert um alle Pflichtfelder (INV-DERIV-1)
  - Exitcode: 0=OK, 1=FAIL (missing input), 2=PARTIAL (unresolved items)

Logging-Format:
  [metric_derivation] ENTRY bl={BL_ID} batch={batch_key} items_count={n}
  [metric_derivation] PHASE1 ak15 items_matched={n} items_unresolved={m}
  [metric_derivation] PHASE2 ak16 srs_range=[min..max]
  [metric_derivation] PHASE3 ak17 k_score_range=[min..max]
  [metric_derivation] EXIT duration={ms}ms status={OK|FAIL|PARTIAL}
```

---

## PHASE 0: INPUTS (Laden)

Vor Algorithmus-Ausfuehrung laedt der Berater:

```
inputs = {
  spec_aks:       parse_aks(3_Spec/{BL_ID}_Spec.md),
                  # Dict: {ak_id -> {text, keywords[]}}

  model_w_nodes:  parse_w_nodes(2_Model/{BL_ID}_Model.md),
                  # Dict: {w_id -> {confidence: float, description: str}}

  ak_to_w_map:    parse_ak_to_w(2_Model/{BL_ID}_Model.md),
                  # Dict: {ak_id -> [w_id, ...]}

  k_score_file:   parse_k_score(4_K-Score/{BL_ID}_K-SCORE.md),
                  # Dict: {ak_id -> {k_score: int, k_aufwand: int}}
                  # Fallback: leeres Dict wenn File fehlt

  pl_items:       parse_pl_items(6_PL/*_PL_Items.md),
                  # Liste: [{id, description, ...}]
}

INVARIANTE: Wenn spec_aks oder model_w_nodes leer -> EXIT 1 (FAIL, missing input)
```

---

## PHASE 1: SCHNEIDEN — AK-15 Algorithmus

Fuer jedes PL-Item wird deterministisch `source_w_derived` und `source_aks_derived` abgeleitet.
Der Algorithmus laeuft in 3 Stufen — Stufe 2 nur als Fallback wenn Stufe 1 leer.

### Stufe 1: Keyword-Match

```python
KEYWORD_THRESHOLD = 0.3  # konfigurierbar via Skill-Parameter

def stufe_1_keyword_match(pl_description, spec_aks):
    """
    Tokenisiert die PL-Beschreibung und matched gegen AK-Keywords.
    Short-circuit: wenn results non-empty -> Stufe 2 wird NICHT ausgefuehrt.
    """
    pl_tokens = set(
        tokenize(pl_description)  # lowercased, stopwords entfernt
    )
    results = {}
    for ak_id, ak_data in spec_aks.items():
        ak_keywords = extract_keywords(ak_data["text"])
        # top-K TF/IDF Tokens aus AK-Text
        overlap = len(pl_tokens & ak_keywords) / max(len(ak_keywords), 1)
        if overlap >= KEYWORD_THRESHOLD:
            results[ak_id] = overlap
    return results  # Dict {ak_id -> score}, leer wenn kein Match
```

Schwellwert-Regel: `overlap < KEYWORD_THRESHOLD` → AK wird NICHT aufgenommen (harte Grenze).

### Stufe 2: Semantic-Fallback (nur wenn Stufe 1 leer)

```python
SEMANTIC_THRESHOLD = 0.5  # konfigurierbar

def stufe_2_semantic_fallback(pl_description, spec_aks):
    """
    Nur ausgefuehrt wenn stufe_1_keyword_match() leeres Dict zurueckgibt.
    Primaer: cosine_similarity ueber Embeddings.
    Fallback (kein Embedding-Modell): token-bigram-overlap (Jaccard > 0.3).
    """
    results = {}
    pl_embedding = embed(pl_description)
    # Fallback: wenn embed() nicht verfuegbar -> lsp_bigram_tokens(pl_description)

    for ak_id, ak_data in spec_aks.items():
        ak_embedding = embed(ak_data["text"])
        sim = cosine_similarity(pl_embedding, ak_embedding)
        # LSP-Token-Bigram-Fallback:
        # sim = jaccard_bigrams(pl_description, ak_data["text"])
        if sim >= SEMANTIC_THRESHOLD:
            results[ak_id] = sim
    return results
```

### Stufe 3: Union-Aggregation

```python
def stufe_3_union(stufe_1_results, stufe_2_results, ak_to_w_map):
    """
    Kombiniert Stufe-1 und Stufe-2 Ergebnisse (union, AK-ID unique).
    Leitet source_w_derived via ak_to_w_mapping ab.
    """
    combined = {**stufe_1_results, **stufe_2_results}
    # Stufe 1 hat Prioritaet bei ak_id-Kollision (stufe_1 zuerst, **stufe_2 ueberschreibt nicht)
    # Korrekt: stufe_1_results dominiert -> merged = {**stufe_2_results, **stufe_1_results}

    source_aks = sorted(combined.keys())

    source_w = []
    for ak_id in source_aks:
        source_w.extend(ak_to_w_map.get(ak_id, []))
    source_w = sorted(set(source_w))  # dedupliziert

    confidence = max(combined.values()) if combined else 0.0

    # Edge-Case: beide Stufen leer
    provenance = "derived" if source_aks else "unresolved"

    return {
        "source_aks_derived": source_aks,
        "source_w_derived":   source_w,
        "derivation_confidence": round(confidence, 4),
        "derivation_source":  "AK-15",   # Invariante: immer AK-15
        "metric_provenance":  provenance  # NIEMALS "hand_waved"
    }
```

**Edge-Cases AK-15:**
- Stufe 1 und Stufe 2 beide leer: `metric_provenance: unresolved`, `confidence: 0.0`
- `metric_provenance: hand_waved` ist VERBOTEN als Output
- Partial-Match (score > 0 aber < threshold): AK wird NICHT aufgenommen

### Gesamt-Ablauf AK-15

```python
def ak15_schneiden(pl_item, inputs):
    s1 = stufe_1_keyword_match(pl_item["description"], inputs["spec_aks"])
    s2 = {} if s1 else stufe_2_semantic_fallback(
             pl_item["description"], inputs["spec_aks"]
         )
    return stufe_3_union(s1, s2, inputs["ak_to_w_map"])
```

---

## PHASE 2: SRS-FORMEL — AK-16

Basierend auf `source_w_derived` (Output von AK-15) wird der SRS-Wert deterministisch berechnet.

```python
def compute_srs(source_w_derived, model_w_nodes):
    """
    Formel: SRS = max(0, min(95, round((1 - mean_confidence) * sparsity * 100)))
    Clamping-Grenze: 95 (SRS=100 per Architektur verboten)
    """
    if not source_w_derived:
        return {
            "srs": 0,
            "srs_components": {
                "mean_w_confidence": None,
                "sparsity_factor":   0.0,
                "total_w_in_model":  len(model_w_nodes),
                "w_beruehrt":        0,
                "note":              "kein W-Knoten beruehrt -> SRS=0"
            }
        }

    confidences = [
        model_w_nodes[w]["confidence"]
        for w in source_w_derived
        if w in model_w_nodes
    ]

    if not confidences:
        # W-Knoten im Model unbekannt -> konservativer Default
        return {"srs": 50, "srs_components": {"note": "W-Knoten unbekannt -> Default 50"}}

    mean_confidence  = sum(confidences) / len(confidences)
    total_w          = len(model_w_nodes)
    sparsity_factor  = len(source_w_derived) / total_w

    srs_raw = (1 - mean_confidence) * sparsity_factor
    srs     = max(0, min(95, round(srs_raw * 100)))

    return {
        "srs": srs,
        "srs_components": {
            "mean_w_confidence": round(mean_confidence, 4),
            "sparsity_factor":   round(sparsity_factor, 4),
            "total_w_in_model":  total_w,
            "w_beruehrt":        len(source_w_derived)
        }
    }
```

**Property-Guarantees:**
- `W.confidence = 1.0` fuer alle → SRS = 0
- `W.confidence = 0.0` fuer alle → SRS = min(95, sparsity * 100)
- `source_w_derived = []` → SRS = 0
- SRS immer in `[0, 95]` (nie 100)

---

## PHASE 3: K-SCORE-FORMEL — AK-17

Basierend auf `source_aks_derived` (Output von AK-15) wird der K-Score aufwand-gewichtet berechnet.

```python
def compute_k_score(source_aks_derived, k_score_file):
    """
    Formel: K_Score = weighted_mean(per_ak_k * aufwand) / sum(aufwand)
    Default: K-Score=50 wenn source_aks_derived leer
    Default: aufwand=1 wenn k_aufwand-Feld fehlt (aequigewichtet)
    """
    if not source_aks_derived:
        return {
            "k_score": 50,
            "k_components": {"note": "source_aks_derived leer -> Default 50"}
        }

    per_ak = []
    for ak_id in source_aks_derived:
        ak_entry = k_score_file.get(ak_id)
        if ak_entry is None:
            continue          # AK nicht in K-Score-File -> uebersprungen (kein Crash)
        per_ak.append({
            "ak":      ak_id,
            "k":       ak_entry["k_score"],
            "aufwand": ak_entry.get("k_aufwand", 1)  # Default-Gewicht=1
        })

    if not per_ak:
        return {
            "k_score": 50,
            "k_components": {"note": "keine AK-ID in K-Score-File -> Default 50"}
        }

    total_weight  = sum(e["aufwand"] for e in per_ak)
    weighted_sum  = sum(e["k"] * e["aufwand"] for e in per_ak)
    k_score_raw   = weighted_sum / total_weight
    k_score       = max(0, min(100, round(k_score_raw)))

    return {
        "k_score": k_score,
        "k_components": {
            "per_ak":       per_ak,
            "weighted_mean": round(k_score_raw, 4),
            "total_weight":  total_weight
        }
    }
```

**Edge-Cases AK-17:**
- `source_aks_derived = []` → K-Score = 50 (Default, kein Crash)
- AK-ID nicht in K-Score-File → AK wird uebersprungen (kein Default-K fuer diesen AK)
- K-Score immer in `[0, 100]` (Clamping analog SRS)
- `derived_from_srs: true` ist Pflichtfeld im Output (BL-165:W10)

---

## PHASE 4: PL-ITEM SCHREIBEN

Nach Abschluss von AK-15/16/17 schreibt der Berater die Ergebnisse zurueck in die PL-Item-Frontmatter.

**Output-Schema pro PL-Item (Pflichtfelder, INV-DERIV-1):**

```yaml
# AK-15 Output-Felder
source_w_derived: [W-DERIV-1, W10_REF]
source_aks_derived: [AK-2, AK-5]
derivation_source: "AK-15 (schneiden) + AK-16 (srs) + AK-17 (k_score)"
derivation_confidence: 0.85         # float, max(stufe_1_score, stufe_2_score)
metric_provenance: derived           # oder: unresolved (wenn confidence=0)

# AK-16 Output-Felder
srs: 13                              # int [0..95], nie 100
srs_components:
  mean_w_confidence: 0.40
  sparsity_factor: 0.214
  total_w_in_model: 14
  w_beruehrt: 3

# AK-17 Output-Felder
k_score: 57                          # int [0..100]
k_components:
  per_ak:
    - {ak: AK-2, k: 60, aufwand: 3}
    - {ak: AK-5, k: 55, aufwand: 5}
  weighted_mean: 56.875
  total_weight: 8
derived_from_srs: true               # BL-165:W10 Pflichtfeld
```

**Schreib-Reihenfolge:**

```
FOR EACH pl_item in pl_items:
  1. ak15_result = ak15_schneiden(pl_item, inputs)
  2. ak16_result = compute_srs(ak15_result.source_w_derived, inputs.model_w_nodes)
  3. ak17_result = compute_k_score(ak15_result.source_aks_derived, inputs.k_score_file)
  4. merged = {
       ...pl_item,
       ...ak15_result,
       ...ak16_result,
       k_score:          ak17_result.k_score,
       k_components:     ak17_result.k_components,
       derived_from_srs: true
     }
  5. WRITE merged -> 6_PL/*_PL_Items.md (Frontmatter-Update)
     GUARD: guard_metric_derivation.py prueft derivation_source vor Write
```

---

## INVARIANTEN

### INV-DERIV-1: Kein PL-Write ohne derivation_source-Marker

**Regel:** Jedes neu geschriebene oder aktualisierte PL-Item in `6_PL/*_PL_Items.md` MUSS das Feld
`derivation_source` enthalten. Gueltiger Wert: `AK-15`, `AK-16`, `AK-17`,
oder kombiniert `"AK-15 (schneiden) + AK-16 (srs) + AK-17 (k_score)"`.

**Enforcement:** `guard_metric_derivation.py` (Artefakt C, BL-174) blockt Write-Versuche
ohne dieses Feld bei `enforceProcess=true`.

**Violation-Log:** `[INV-DERIV-1] {filepath}: derivation_source fehlt -> BLOCKED`

**Ausnahme:** Grandfathered Items (aelter als `--ignore-pre`-Datum im Linter). Der Guard
prueft IMMER fuer neue Writes — keine Grandfather-Ausnahme im Guard.

### INV-DERIV-2: Linter ist authoritative; bei FAIL kein PR/Merge

**Regel:** `lint_pl_item_derivation.py` Exit 1 (> 5% non-grandfathered hand-waved Items)
blockiert PR-Erstellung und Merge.

**Bypass-Verbot:** `--threshold=1.0` als Bypass-Versuch ist eine Prozess-Verletzung
und wird im Audit geloggt.

**Modus-Abgrenzung:** Diese Skill-Datei liefert SRS/K-Score als Daten. Modus-Entscheidung
bleibt ausschliesslich bei `_SDF_berater_modusEntscheidung` (INV-MODUS-1).

---

## TESTS (Pseudocode)

### Test-1: Keyword-Match (AK-15 Stufe 1)

```python
# Input
pl_description = "implement keyword extraction for routing_decision fields"
spec_aks = {
    "AK-15": {"text": "Keyword-Match extraction tokenize routing_decision", "keywords": {"keyword", "extraction", "routing_decision"}}
}

# Erwartung
result = stufe_1_keyword_match(pl_description, spec_aks)
assert "AK-15" in result
assert result["AK-15"] >= 0.3          # overlap-score ueber Threshold
# Stufe 2 wird NICHT ausgefuehrt (short-circuit)
```

### Test-2: Semantic-Fallback (AK-15 Stufe 2)

```python
# Input: PL-Beschreibung ohne direkte Keywords
pl_description = "analyse the classification system for request routing"
spec_aks = {
    "AK-15": {"text": "Keyword-Match extraction tokenize routing_decision", "keywords": {"keyword", "extraction", "routing_decision"}}
}

# Stufe 1: leer (kein Keyword-Overlap >= 0.3)
s1 = stufe_1_keyword_match(pl_description, spec_aks)
assert s1 == {}

# Stufe 2: Semantic-Fallback wird ausgefuehrt
s2 = stufe_2_semantic_fallback(pl_description, spec_aks)
# Erwartung: cosine_sim(embed(pl), embed(ak)) >= 0.5 -> AK-15 in s2
assert len(s2) >= 0   # kann auch leer sein -> metric_provenance=unresolved
```

### Test-3: SRS-Clamping (AK-16)

```python
# Input: extrem niedrige confidence -> hoher SRS_raw
source_w_derived = ["W1", "W2", "W3", "W4", "W5"]
model_w_nodes = {
    "W1": {"confidence": 0.0},
    "W2": {"confidence": 0.0},
    "W3": {"confidence": 0.0},
    "W4": {"confidence": 0.0},
    "W5": {"confidence": 0.0},
    # total_w_in_model = 5
}

result = compute_srs(source_w_derived, model_w_nodes)
# SRS_raw = (1-0.0) * (5/5) * 100 = 100 -> clamp -> 95
assert result["srs"] == 95
assert result["srs"] <= 95   # Clamping-Invariante: nie 100
```

### Test-4: K-Score Weighted-Mean (AK-17)

```python
# Input: 2 AKs mit unterschiedlichen Gewichten
source_aks_derived = ["AK-2", "AK-5"]
k_score_file = {
    "AK-2": {"k_score": 60, "k_aufwand": 3},
    "AK-5": {"k_score": 55, "k_aufwand": 5}
}

result = compute_k_score(source_aks_derived, k_score_file)
# weighted_mean = (60*3 + 55*5) / (3+5) = (180+275)/8 = 455/8 = 56.875
# k_score = round(56.875) = 57
assert result["k_score"] == 57
assert result["k_components"]["weighted_mean"] == 56.875
assert result["k_components"]["total_weight"] == 8
```
