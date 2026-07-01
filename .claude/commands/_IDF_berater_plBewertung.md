---
status: active
version: 1.0.0
created: 2026-05-24
feature: BL-203
ak_implements: [AK-1, AK-5, AK-11]
bl_312_ak9: "Re-Bewertungs-Ausnahme — Items in BERATER_OUTPUTS.loopCheck.affected_pl_items (W-state-change, stale srs) werden trotz Idempotenz-SKIP SRS-re-bewertet (SRS-only, K deferred AK-10/BL-311). Selektion macht _IDF_berater_loopCheck SCHRITT 2.7."
type: berater
phase: "3.8"
chain_position: after-modelSync-3.7-before-dependencyAnalyzer-4
model_tier: middle
contract:
  reads:
    - {file: "{bl_folder}/6_PL/*.md", purpose: "PL-Items (provenance, w_refs, id)"}
    - {file: "{bl_folder}/2_Model/*.md", purpose: "W{n}-Status (BESTAETIGT/TENTATIV/HYPOTHESE/OFFEN)"}
    - {file: "_manifest.md", purpose: "session_param.bottleneck_srs_threshold, DF_BATCH_STATE"}
    - {file: "_manifest.md", path: "BERATER_OUTPUTS.loopCheck.affected_pl_items", purpose: "BL-312 AK-9: W-state-change-betroffene Items → SRS-Re-Bewertung trotz Idempotenz-SKIP (SRS-only)"}
  writes:
    - {output: "DF_BATCH_STATE.per_pl_evaluation", purpose: "Pro-PL-Vektor {srs, k_score, bottleneck, bottleneck_route}"}
    - {output: "DF_BATCH_STATE.plBewertung_done", purpose: "Idempotenz-Flag"}
    - {output: "BERATER_OUTPUTS.plBewertung", purpose: "Status + Statistik"}
  not_writes:
    - modus
    - recommended_modus
    - sdf_mode
    - sdf_mode_hint
    - mode_recommendation
    - expected_sdf_mode
---

# _IDF_berater_plBewertung (Phase 3.8)

Mehrstufige PL-Bewertung: SRS-Refresh → Bottleneck-Filter → K-Score-Refresh → Intern/Extern-Klassifikation.
Schreibt `DF_BATCH_STATE.per_pl_evaluation` als Pro-PL-Vektor.

## IDF Phase 3.8 = ERST+EINZIG-SRS-Rechner (BL-312 AK-1, additiv)

IDF Phase 3.8 plBewertung ist der **EINE, erste SRS-Bewertungs-Ort** fuer JEDES PL-Item — egal
welcher Entry (Erst-Eintrag, Trickle/Entry-3, late Self-Raised-PL). **Idempotent:** Items, die
bereits ein `per_pl_evaluation[pl.id].srs` tragen, werden NICHT neu gerechnet; nur Items OHNE srs
werden bewertet — so deckt EIN Aufruf auch nachgereichte Items ab, ohne fertige zu ueberschreiben.

**AK-9 Re-Bewertungs-Ausnahme (BL-312, additiv):** Items in `BERATER_OUTPUTS.loopCheck.affected_pl_items`
sind eine **gezielte Ausnahme** vom Idempotenz-SKIP — sie tragen zwar ein srs, dieses ist aber STALE,
weil ein referenziertes W{n} seinen Zustand gewechselt hat (SC bestaetigt/widerlegt/neu, modelSync 3.7
Reverse-Naht). Genau diese Items werden im FULL_LOOP_WITH_REVERSE **SRS-re-bewertet** (Single-Computation
bleibt an EINEM Ort — die Aenderung lebt, wo sie passiert). Nicht-betroffene Items mit srs bleiben
unangetastet (kein Voll-Recompute). **K-Re-Bewertung DEFERRED** (AK-10/BL-311 — NUR SRS). Die
`affected_pl_items`-Selektion macht `_IDF_berater_loopCheck` (SCHRITT 2.7, INV-IDF-LOOP-8); 3.8 RECHNET,
loopCheck DETEKTIERT nur.

Fuer ein **late Item OHNE w_refs** gilt die Reihenfolge **ERST anknuepfen, DANN rechnen**:
`scripts/w_fetch_light.py::match_item_to_model(item_text, model_w_nodes)` knuepft das Item an die
Model-W{n}-Knoten → die zurueckgegebenen w_refs werden gesetzt → **DANN** `_srs_compute`. Ohne diese
Vor-Anknuepfung liefe das Item in den `no_truth_refs`-Kollaps (srs=100) trotz vorhandenem Model-Bezug.
Liefert W_fetch-light KEINEN Treffer (kein Anker), bleibt `no_truth_refs`/srs=100 — und das ist dann
KORREKT (echtes Unbekanntes).

**KEIN K-Recompute** in diesem Schritt: K-Migration ist DEFERRED (AK-10 / BL-311 — erst Pin der
Code-K-Skala). Der K-Score bleibt vorerst A-4k-Quelle (Phase 3.8c bleibt unveraendert; diese AK-1-Note
betrifft NUR den SRS-Pfad). [BL-312 AK-1]

## INVARIANTEN

- INV-MODUS-1: Schreibt NIEMALS `modus` — bottleneck_route ist BEOBACHTUNG (INV-SRS-4), kein Modus-Vorschlag
- INV-MODUS-5: Alle verbotenen Felder (recommended_modus, sdf_mode, ...) in contract.not_writes
- INV-SRS-3: no_truth_refs → srs=100 (pessimistisch)
- INV-SRS-4: bottleneck_route ist Signal, kein Modus-Vorschlag
- INV-BC-1: PLs ohne provenance-Feld → srs=100, no_truth_refs (Backward-Compat, AK-11)

## Ablauf

### Schritt 0: Idempotenz-Gate

```python
# [plBewertung] ENTRY
LOG "[plBewertung] Phase 3.8 gestartet"

IF DF_BATCH_STATE.plBewertung_done == true:
  LOG "[plBewertung] IDEMPOTENZ-GATE — bereits ausgefuehrt, SKIP"
  RETURN exitcode=0
```

### Schritt 1: PL-Items laden

```python
bl_folder = resolve_bl_folder()  # via vault-routing.json
pl_items   = Read(f"{bl_folder}/6_PL/*.md")
model_path = f"{bl_folder}/2_Model/{NAME}_Model.md"

LOG "[plBewertung] {len(pl_items)} PL-Items geladen aus {bl_folder}/6_PL/"
```

### Schritt 2: Bottleneck-Schwelle lesen

```python
threshold = session_param.bottleneck_srs_threshold ?? 60
LOG "[plBewertung] bottleneck_srs_threshold={threshold}"
```

### Schritt 3: Pro-PL-Bewertung (Phase 3.8a → 3.8d)

```python
per_pl_evaluation = {}

# AK-9 (BL-312): W-state-change-betroffene Items werden trotz vorhandenem srs re-bewertet (SRS-only).
affected_pl_items = Read(_manifest.md).BERATER_OUTPUTS.loopCheck.affected_pl_items ?? []

FOR pl IN pl_items:

  # ── Idempotenz (BL-312 AK-1): bereits bewertete Items NICHT neu rechnen ──
  # AK-9-Ausnahme: affected_pl_items (stale durch W-state-change) werden SRS-re-bewertet.
  IF per_pl_evaluation.get(pl.id, {}).get("srs") is not None AND pl.id NOT IN affected_pl_items:
    LOG f"[plBewertung] {pl.id}: srs bereits vorhanden → SKIP (idempotent, deckt Trickle/Entry-3)"
    CONTINUE
  IF pl.id IN affected_pl_items:
    LOG f"[plBewertung] {pl.id}: in affected_pl_items (W-state-change) → SRS-RE-BEWERTUNG (AK-9, SRS-only; K deferred)"

  # ── Phase 3.8a-pre: W_fetch-light fuer late Items OHNE w_refs (BL-312 AK-1) ──
  # ERST anknuepfen, DANN rechnen — sonst no_truth_refs-Kollaps (srs=100) trotz Model-Bezug.
  # PFLASTER 2026-06-26 (SRS-MANUAL-PROVENANCE, siehe Vault _parking-lot): manual/None AUCH
  #   anknuepfen — ein Seed-Item das einer Model-Entitaet entspricht (z.B. VersorgungsvertragId)
  #   bekommt so echte w_refs statt no_truth_refs-Kollaps. War: ... AND provenance not in (None,"manual").
  IF pl.w_refs is empty:
    model_w_nodes = load_w_nodes(model_path)   # [{id, status, title}]
    light_refs = w_fetch_light.match_item_to_model(pl.item_text, model_w_nodes)  # threshold=0.5
    IF light_refs:
      pl.w_refs = light_refs   # geknuepft (source="W_fetch-light")
      LOG f"[plBewertung] {pl.id}: W_fetch-light knuepfte {len(light_refs)} w_ref(s) → kein no_truth_refs-Kollaps"
    # kein Treffer → w_refs bleibt leer → no_truth_refs/srs=100 ist KORREKT (echtes Unbekanntes)

  # ── Phase 3.8a: SRS-Refresh ─────────────────────────────────────────
  # AK-11 Backward-Compat: PLs ohne provenance → SRS=100 (no_truth_refs)
  # PFLASTER 2026-06-26 (SRS-MANUAL-PROVENANCE): srs=100 wird jetzt auf TATSAECHLICHE
  #   Ungegroundetheit gegated (w_refs leer NACH dem Anknuepfungs-Versuch oben), NICHT mehr aufs
  #   provenance-Label. Seed-Item mit Model-Treffer -> echtes srs_compute -> M1/M2-light statt SC/M7;
  #   genuin ungegroundet (kein Treffer) -> weiterhin srs=100 (pessimistisch, korrekt).
  #   Proper-fix (Trivial/Seed-Klassifikation + truth_srs.py BL-384): siehe Vault _parking-lot.
  IF pl.w_refs is empty:
    srs_result = {"srs": 100, "flag": "no_truth_refs", "breakdown": []}
    LOG f"[plBewertung] {pl.id}: w_refs leer nach Anknuepfung → SRS=100 (no_truth_refs)"
  ELSE:
    srs_result = Skill(_srs_compute, args=f"--item={pl.id} --model={model_path}")
    LOG f"[plBewertung] {pl.id}: srs_compute → srs={srs_result.srs}, flag={srs_result.flag}"

  pl.srs     = srs_result.srs
  pl.srs_flag = srs_result.flag

  # ── Phase 3.8b: Bottleneck-Filter ───────────────────────────────────
  IF pl.srs >= threshold OR pl.srs_flag == "no_truth_refs":
    pl.bottleneck = True
    LOG f"[plBewertung] {pl.id}: BOTTLENECK (srs={pl.srs} >= {threshold} OR no_truth_refs)"
  ELSE:
    pl.bottleneck = False

  # ── Phase 3.8c: K-Score-Refresh (NUR wenn NOT bottleneck) ───────────
  IF NOT pl.bottleneck:
    k_result   = Skill(_K_score, args=f"--mode=pl_item --pl={pl.id}")
    pl.k_score = k_result.k_score
    LOG f"[plBewertung] {pl.id}: K-Score={pl.k_score}"
  ELSE:
    pl.k_score = None  # Kein K-Score wenn Wahrheit unklar (Bottleneck)

  # ── Phase 3.8d: Intern/Extern-Klassifikation (NUR wenn bottleneck) ──
  # AK-5: W{n}.source bestimmt Routing-Signal (INV-SRS-4: KEIN Modus-Vorschlag)
  IF pl.bottleneck:
    INTERN_SOURCES   = ["Repo:", "Crumbs:", "Assays:", "W_fetch:"]
    UNSICHER_STATUSES = ["TENTATIV", "HYPOTHESE", "OFFEN"]

    w_refs = resolve_truth_refs(pl, model_path)

    extern_count = count(w for w in w_refs
                         if w.status in UNSICHER_STATUSES
                         AND NOT any(w.source.startswith(s) for s in INTERN_SOURCES))

    intern_count = count(w for w in w_refs
                         if w.status in UNSICHER_STATUSES
                         AND any(w.source.startswith(s) for s in INTERN_SOURCES))

    IF extern_count > 0:
      pl.bottleneck_route = "WP"   # Externe Unsicherheit → WP-Skill (M9)
    ELSE:
      pl.bottleneck_route = "SC"   # Interne Unsicherheit oder kein W-Bezug → SC (M5/6)

    LOG f"[plBewertung] {pl.id}: bottleneck_route={pl.bottleneck_route} (intern={intern_count}, extern={extern_count})"
  ELSE:
    pl.bottleneck_route = None

  # ── Vektor zusammensetzen ────────────────────────────────────────────
  per_pl_evaluation[pl.id] = {
    "srs":             pl.srs,
    "srs_flag":        pl.srs_flag,
    "k_score":         pl.k_score,
    "bottleneck":      pl.bottleneck,
    "bottleneck_route": pl.bottleneck_route,
    "evaluated_at":    today()
  }
```

### Schritt 4: Output schreiben

```python
Write(_manifest.md → DF_BATCH_STATE.per_pl_evaluation = per_pl_evaluation)
Write(_manifest.md → DF_BATCH_STATE.plBewertung_done  = true)

items_bottleneck    = count(pl for pl in per_pl_evaluation.values() if pl.bottleneck)
items_k_score_avail = count(pl for pl in per_pl_evaluation.values() if pl.k_score is not None)

Write(BERATER_OUTPUTS.plBewertung = {
  "status":             "DONE",
  "items_evaluated":    len(pl_items),
  "items_bottleneck":   items_bottleneck,
  "items_k_score_avail": items_k_score_avail,
  "threshold_used":     threshold
})

LOG f"[plBewertung] DONE — {len(pl_items)} Items: {items_bottleneck} Bottleneck, {items_k_score_avail} mit K-Score"
```

## Aufruf-Kontext

Dieser Berater wird aufgerufen von:
- `_IDF_orchestrate` Phase 3.8 (nach Phase 3.7 modelSync, vor Phase 4 dependencyAnalyzer)

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| PL-Item ohne `provenance`-Feld | srs=100, flag=no_truth_refs (AK-11 Guard) |
| `_srs_compute` Fehler | LOG WARN + srs=100, no_truth_refs (pessimistisch) |
| `_K_score --mode=pl_item` nicht verfuegbar | k_score=null, Bottleneck-Route weiterhin berechnet |
| Keine PL-Items in 6_PL/ | per_pl_evaluation={}, DONE (kein Fehler) |
| Model-Datei nicht lesbar | w_refs=[] → intern_count=0, extern_count=0 → route="SC" |

## Downstream-Integrationen

- **Phase 4 dependencyAnalyzer**: liest `per_pl_evaluation[pl_id].k_score` fuer Dep-Gewichtung
  - Bottleneck-PLs (k_score=null) erhalten niedrigere Dep-Prioritaet
- **Phase 7.6 metricPlanner**: aggregiert `per_pl_evaluation` pro Sub-Batch
  - `srs_max` = MAX(srs fuer alle PL in Batch)
  - `k_score_avg` = AVG(k_score fuer PL mit k_score != null)
