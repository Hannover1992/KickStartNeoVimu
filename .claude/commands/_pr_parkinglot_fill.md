---
name: _pr_parkinglot_fill
status: active
version: 1.0.0
type: satellite
op: PR-Inquiry-Pipeline
created: 2026-06-09
feature_anchor: BL-296
chain_position: step-5-of-7
related:
  - _pr_init
  - _pr_pull
  - _pr_question_answer_sim
  - _pr_answer
  - _pr_orchestrate
  - _parking-lot
  - _IDF_orchestrate
---

# /_pr_parkinglot_fill — PR-Inquiry AK4: Parking-Lot-Fueller

```
+======================================================================+
|  VERTRAG: /_pr_parkinglot_fill (AK4 — Satellite, kein Worker-Spawn) |
|  BL-296 | INV-PR-PL-1..7 | INV-PL-WRITER-1 (d)                     |
+======================================================================+
|  ACTOR: TEAM LEAD (DU — direkt, kein Agent-Delegate).               |
|  Satellite: KEIN Worker-Spawn, reine Datei-Transformation.          |
|                                                                      |
|  LIEST:                                                              |
|    .claude/analysis/pr-{id}-sim-answers.json                        |
|      (stance, disp, flip_status pro Comment — Filterquelle)         |
|    .claude/analysis/pr-{id}-state.json                              |
|      (comment-Texte, original_comment_text, reviewer)               |
|    .claude/meta/pr/active-pr.json                                   |
|      (committer-BL-Kontext: PR-BL-ID des Committers, NICHT BL-296)  |
|    {vault}/vault-routing.json + _current_context.md                 |
|      (Schreibweg-Aufloesung, identisch _parking-lot.md Entry-3)     |
|    {vault}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md           |
|      (Existenz-Check + get_next_pl_id — APPEND-ONLY Basis)          |
|                                                                      |
|  SCHREIBT:                                                           |
|    {vault}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md           |
|      APPEND-ONLY, neue PL-Items (source='pr_review',               |
|      entry_point='/_pr_parkinglot_fill')                            |
|    {bl_slug}/_manifest.md                                           |
|      DF_BATCH_STATE.parking_lot_modified_since_last_idf = true      |
|    {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md                 |
|      parking_lot_item-Ref nachtragen (parking_lot-Feld in Tripel)  |
|    .claude/analysis/pr-{id}-sim-answers.json                        |
|      parking_lot_id pro Comment zurueck (Rueck-Ref)                 |
|                                                                      |
|  RUFT: (keine — reines Satellite)                                   |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-PR-PL-1: NIE Refutationen ins PL (stance==refute → SKIP)    |
|    INV-PR-PL-2: source/entry_point PFLICHT (4. Writer INV-PL-W-1)  |
|    INV-PR-PL-3: IDF-kompatibles Item-Format (id/status/blocked_by) |
|    INV-PR-PL-4: provenance='pr_review' → verhindert srs=100-Bias   |
|    INV-PR-PL-5: APPEND-ONLY — bestehende Items NIE ueberschreiben  |
|    INV-PR-PL-6: BL-Kontext = Committer-BL, NICHT BL-296           |
|    INV-PR-PL-7: NIE modus/recommended_modus/sdf_mode-Felder        |
+======================================================================+
```

---

## Zweck

AK4 der PR-Inquiry-Pipeline (BL-296): Liest die sim-answers aus `_pr_question_answer_sim`, filtert auf zustimmende Code-Kommentare (stance `agree` | `partial`) sowie FLIPs (`refute→agree`), und erzeugt IDF-kompatible Parking-Lot-Items im Backlog des Committers.

Refutationen — auch REFINED — erzeugen KEINE PL-Items. Sie landen im Findings-Tripel mit `parking_lot=null` und gehen direkt als Erklaerung in `_pr_answer`.

Reuse-First: nutzt `resolve_write_path` / `get_next_pl_id` / `write_pl_item` EXAKT aus `_parking-lot.md` (v3.0.0 BL-201). Kein Neubau der PL-Infrastruktur.

---

## Aufruf

```
/_pr_parkinglot_fill
/_pr_parkinglot_fill [--pr-id=NNN]    (optional Override, sonst aus active-pr.json)
```

**Parameter:**

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `--pr-id` | aus active-pr.json | Override PrId (Sonderfall, Normalfall automatisch) |

**Beispiele:**
```
/_pr_parkinglot_fill
/_pr_parkinglot_fill --pr-id=18979
```

**Voraussetzung (Reihenfolge-Enforcement):**
- `.claude/analysis/pr-{id}-sim-answers.json` muss existieren (sonst BLOCK)
- Recovery-Hint bei Fehlen: `"Rufe /_pr_question_answer_sim"`

**Typischer Kontext in der Chain:**
```
_pr_question_answer_sim  →  [HiL-Gate wenn hil_mode=true]  →  _pr_parkinglot_fill  →  _IDF_orchestrate
```

---

## REUSE-FIRST — Wiederverwendete Infra

**Aus `_parking-lot.md` (v3.0.0, BL-201) — EXAKT uebernommen:**
- `resolve_write_path(bl_id)` → `{vault}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md`
- `get_next_pl_id(write_path, bl_id)` → `PL-{bl_id}-{NNN:03d}`
- `write_pl_item(...)` → APPEND-ONLY Semantik
- Manifest-Flag: `DF_BATCH_STATE.parking_lot_modified_since_last_idf = true`
- INV-PL-WRITER-1: Single-Writer-Disziplin (dieser Skill ist 4. Writer `d`)

**Aus `_pr_question_answer_sim` (BL-296, AK3):**
- `pr-{id}-sim-answers.json` als Filterquelle (stance/disp/flip_status)
- Findings-Tripel-Schema (`{VAULT}/Findings/{pr_id}/tripel-{comment_id}.md`) — nachtragen `parking_lot`-Feld

**Aus `_IDF_berater_validator` (Phase 3.5) + `_IDF_berater_plBewertung` (Phase 3.8):**
- PL-Item-Format-Anforderungen (IDF-kompatibel): id-Pattern, status-Enum, int k_score/srs

**NEU (kein Vorgaenger):**
- Filter-Logik `stance IN {agree, partial} OR flip_status==FLIP` (AK4-spezifisch)
- `source='pr_review'` + `provenance='pr_review'` (neue Herkunfts-Markierung)
- `entry_point='/_pr_parkinglot_fill'` als 4. erlaubter Writer (INV-PL-WRITER-1 Ergaenzung noetig)
- Rueck-Schreiben der `parking_lot_id` in sim-answers.json + Tripel

---

## Ablauf (Schritt-fuer-Schritt)

```
SCHRITT 0  [PR_PL] ENTRY
  - entry-log: "[PR_PL] START vault_root={vault} pr_id={pr_id}"
  - Resolve PrId: aus --pr-id-Arg ODER active-pr.json.prId
  - GATE: sim-answers.json existiert?
      NEIN → BLOCK "[PR_PL] BLOCK: sim-answers.json nicht gefunden.
                     Recovery: /_pr_question_answer_sim"
      JA  → weiter

SCHRITT 1  BL-KONTEXT + SCHREIBWEG
  - Lese active-pr.json: committer_bl_id (INV-PR-PL-6: Committer-BL, NICHT BL-296)
  - resolve_bl_slug(committer_bl_id)   [identisch _parking-lot.md Schreibweg-Logik]
  - resolve_write_path:
      {vault}/Backlog/{bl_slug}/6_PL/{committer_bl_id}-parking-lot.md
  - Datei-Existenz-Check: falls nicht vorhanden → anlegen (Header "# Parking Lot: {bl_id}")
  - log: "[PR_PL] Schreibziel: {write_path}"

SCHRITT 2  FILTER + ID-VERGABE (pro Comment in sim-answers.json)
  FOR comment IN sim_answers:
    IF comment.stance == "refute"
       AND comment.flip_status != "FLIP":
      → log "[PR_PL] skip refute thread_id={comment.question_id}"
      → CONTINUE  (INV-PR-PL-1: keine PL-Items fuer Refutationen)

    # stance IN {agree, partial} ODER flip_status == "FLIP" → PL-Item
    pl_id = get_next_pl_id(write_path, committer_bl_id)
      # PL-{bl_id}-{NNN:03d}, count aus bestehenden Items in write_path
    log "[PR_PL] item {pl_id} ← thread {comment.question_id} (stance={comment.stance})"

SCHRITT 3  PL-ITEM BAUEN

  FRONTMATTER (INV-PR-PL-3: IDF-kompatibel, INV-PR-PL-4: provenance):
  ---
  pl_item_id: "{pl_id}"                        # PL-{bl_id}-{NNN:03d}
  title: "{Kurztitel aus question_id + Datei/Thema}"
  status: open                                  # IN {open,done,blocked,in_progress}
  blocked_by: []
  source: pr_review                             # INV-PR-PL-2
  entry_point: /_pr_parkinglot_fill             # INV-PR-PL-2
  provenance: pr_review                         # INV-PR-PL-4: verhindert srs=100-Bias
  k_score: {int 0..100}                         # Heuristik: agree+KRITISCH=75; agree+WARN=50;
                                                #   partial=40; FLIP=60. NIE LOW/MED/HIGH
  srs: {int 0..100}                             # Default 50; hoeher wenn needs_work=true (70)
  layer_hint: "{aus comment.file: Domain/App/Infra}" # optional
  flip_status: "{comment.flip_status}"          # STABLE|FLIP|REFINED (bei FLIP explizit)
  created: "{YYYY-MM-DD}"
  # INV-PR-PL-7: KEINE modus/recommended_modus/sdf_mode/mode_recommendation-Felder
  ---

  BODY:
  ### {pl_id}: {Titel}

  - **source_aks:** [pr-comment-{thread_id}]
  - **k_score:** {int}
  - **srs:** {int}
  - **suggested_mode:** M2   # Normalfall codebasiert; M3 nur wenn needs_work=true+unbekannte Pfade
  - **Beschreibung:** {original_comment_text (woertlich, @-Mentions gestrippt)} — {sim_answer Fix-Plan}
  - **Acceptance Criteria:**
    - [ ] {abgeleitetes AC aus Fix-Plan, min. 1}
  - **pr_context:**
    - pr_id: {pr_id}
    - pr_author: {comment.reviewer_name}
    - comment_id: {comment.question_id}
    - sim_answer_ref: .claude/analysis/pr-{id}-sim-answers.json#{n}
    - flip_status: {comment.flip_status}
    - stance_original: {comment.stance}   # "FLIP" bedeutet: war refute, kippte zu agree

SCHRITT 4  APPEND
  append_to_file(write_path, pl_item_formatted)   # INV-PR-PL-5: APPEND-ONLY
  # Bestehende Items NIE ueberschreiben — count vorher, append danach

SCHRITT 5  RUECK-REFERENZEN
  - sim-answers.json: comment.parking_lot_id = pl_id  (zurueckschreiben)
  - {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md:
      parking_lot: "{pl_id}"   # im Frontmatter nachtragen
      # Bei Refutation (SKIP): parking_lot bleibt "null" (korrekt, AK4)

SCHRITT 6  MANIFEST-FLAG
  set_manifest_flag(bl_slug=bl_slug,
                    key="parking_lot_modified_since_last_idf",
                    value=true)
  # → triggert IDF FULL_LOOP_WITH_REVERSE beim naechsten /_IDF_orchestrate-Lauf

SCHRITT EXIT
  Zaehle: M = Anzahl angelegter PL-Items, R = Anzahl uebersprungener Refutationen
  log "[PR_PL] DONE: {M} PL-Items angelegt, {R} Refutationen uebersprungen."
  ausgabe: "M PL-Items angelegt (R Refutationen uebersprungen).
            Naechster Schritt: /_IDF_orchestrate {committer_bl_id} --pl-only --from=sdf_finish"
  Exitcode 0
```

---

## INV-PR-PL-Familie (nummeriert)

```
INV-PR-PL-1 (AK4, load-bearing):
  NIE Refutationen ins Parking-Lot.
  Regel: IF stance==refute AND flip_status != "FLIP" → SKIP (kein PL-Item).
  Nur stance IN {agree, partial} ODER flip_status=="FLIP" (refute→agree-Kipper) → PL-Item.
  REFINED bleibt refute → kein PL-Item (Refutation haelt, nur praezisiert).
  Begruendung: Refutationen sind keine Fix-Auftraege. Sie gehen als Erklaerung in _pr_answer.

INV-PR-PL-2 (Single-Writer-Ergaenzung):
  source='pr_review' + entry_point='/_pr_parkinglot_fill' PFLICHT in jedem Item-Frontmatter.
  _pr_parkinglot_fill ist 4. erlaubter Writer (d) in INV-PL-WRITER-1.
  PATCH ERFORDERLICH: _parking-lot.md INV-PL-WRITER-1 um Writer 'd) _pr_parkinglot_fill
  (BL-296 AK4 — PR-Review-Findings)' ergaenzen. Solange nicht gepatcht: konventionell dokumentiert.

INV-PR-PL-3 (IDF-Kompatibilitaet):
  PL-Item-Format EXAKT nach _IDF_berater_validator Phase 3.5-Anforderungen:
  - id: matcht "PL-{BL-ID}-{NNN}" (filename_id_pattern)
  - status: IN {open, done, blocked, in_progress}
  - blocked_by: Liste (auch leer: [])
  - k_score: int 0..100 (NIEMALS LOW/MED/HIGH)
  - srs: int 0..100 (NIEMALS LOW/MED/HIGH)
  IDF-Validator wuerde bei Formatverletzung BLOCK ausloesen.

INV-PR-PL-4 (provenance-Anti-Bias):
  provenance='pr_review' PFLICHT.
  Verhindert, dass _IDF_berater_plBewertung pessimistisch srs=100 + Bottleneck=SC setzt.
  PR-Findings sind codebasiert (echter Diff-Anker), nicht spekulativ.

INV-PR-PL-5 (APPEND-ONLY):
  Bestehende PL-Items in {bl_id}-parking-lot.md NIE ueberschreiben oder loeschen.
  Gilt analog INV-PLA-1 + INV-PL-WRITER-1.
  Konsequenz: get_next_pl_id MUSS count VOR dem Append bestimmen (race-safe bei
  Single-Writer).

INV-PR-PL-6 (BL-Kontext-Quelle):
  BL-Kontext = committer_bl_id aus active-pr.json.committer.bl_id
  (= die BL, an der der Committer gerade arbeitet).
  NICHT BL-296 (= die BL des PR-Inquiry-Pipeline-Designs selbst).
  resolve_bl_slug laeuft auf committer_bl_id.

INV-PR-PL-7 (INV-MODUS-5-Einhaltung):
  Frontmatter und Body enthalten NIEMALS:
    modus, recommended_modus, sdf_mode, sdf_mode_hint,
    expected_sdf_mode, mode_recommendation
  Diese Felder sind Pre-Write-Hook-blockiert (INV-MODUS-5, BL-165).
  suggested_mode ist ERLAUBT (anderer Namespace, kein SDF-Modus-Feld).
```

---

## k_score / srs Heuristik (lightweight, ohne AK-Pipeline)

```
Quelle: comment.schweregrad (aus bob-monolog) + comment.needs_work + flip_status

k_score (Komplexitaet der Aenderung, 0..100):
  KRITISCH + agree      → 75
  WARN + agree          → 50
  INFO + agree (selten) → 30
  partial               → 40
  FLIP (refute→agree)   → 60   (war strittig, Aufwand unklar)

srs (Spec-Reife / Unsicherheit, 0..100):
  needs_work=true       → 70   (IDF muss noch pruefen ob wirklich noetig)
  needs_work=false      → 40   (klar — Code ist nicht umgesetzt)
  flip_status=FLIP      → 65   (war Refutation, Scope kann unklar sein)
  Default               → 50

suggested_mode:
  srs < 55              → M2   (covered, klare Anforderung)
  srs >= 55             → M3   (uncovered, Exploration noetig)
```

---

## Findings-Tripel Rueck-Update

Nach SCHRITT 5 hat jedes Tripel-File fuer agree/partial/FLIP-Items:

```yaml
# {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md — Ausschnitt nach parkinglot_fill
parking_lot: "PL-{bl_id}-{NNN}"   # gesetzt von _pr_parkinglot_fill
flip_status: "FLIP"                 # (Beispiel: war Refutation, kippte)
# resulting_truth: ""              # noch leer — wird von _pr_answer gefuellt
```

Fuer Refutationen (SKIP):
```yaml
parking_lot: null                   # Refutation → kein PL-Item (AK4, INV-PR-PL-1)
```

---

## Output-Regeln (AK-Verifikation 486)

```
NIE interne Marker im Output:
  VERBOTEN: DUC / Ring / PR2 / PL / IDF / SDF / "PR-Inquiry" als Label in
            sim_answer-Text oder PL-Item-Body (Dev-Kollegen-Ton).
  ERLAUBT:  pr_context-Block (intern, Maschinen-Konsum), pl_item_id, pr_id als ID.

PL-Item-Titel und Beschreibung = Dev-Sprache:
  VERBOTEN: "Laut PR-Inquiry-Pipeline...", "IDF-Kandidat", "Parking-Lot-Item"
  ERLAUBT:  "markAllAsTouched fehlt in cancelEdit-Flow", "resetValidators() Pfad pruefen"
```

---

## Seam-Protokoll (Chain-Position)

```
Eingang (liest):
  .claude/analysis/pr-{id}-sim-answers.json
    ← erzeugt von _pr_question_answer_sim (AK3)
    Gate: Existenz-Check in SCHRITT 0

Ausgang (schreibt):
  {vault}/.../6_PL/{bl_id}-parking-lot.md  (APPEND)
    → gelesen von _IDF_orchestrate --pl-only --from=sdf_finish (AK5)
  DF_BATCH_STATE.parking_lot_modified_since_last_idf=true
    → triggert IDF FULL_LOOP_WITH_REVERSE (_IDF_berater_loopCheck Phase A)
  pr-{id}-sim-answers.json (parking_lot_id pro Item)
    → gelesen von _pr_answer (AK6) fuer Loop-Schluss
  {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md (parking_lot-Feld)
    → Loop-Schluss AK7 in _pr_answer
```

---

## Offene Infra-Patches (klein, chirurgisch)

```
PATCH-1 (PFLICHT vor erstem Live-Lauf):
  _parking-lot.md INV-PL-WRITER-1 ergaenzen:
    d) _pr_parkinglot_fill (BL-296 AK4 — PR-Review-Findings, source='pr_review')
  Ohne diesen Patch verletzt jeder Aufruf formal den Single-Writer-Vertrag.

PATCH-2 (PFLICHT):
  routing.json neue Felder: hil_mode, pathPrefix, tfs_compat
  (Benoetigt von _pr_init/_pr_pull, nicht direkt von _pr_parkinglot_fill —
   aber Teil der gemeinsamen Infra-Erweiterung BL-296.)

PATCH-3 (EMPFOHLEN):
  active-pr.json-Schema: committer.bl_id explizit als Pflichtfeld dokumentieren
  (aktuell implizit in committer-Objekt).
```

---

## Beispiel-Durchlauf (DCSRE-486 Verifikation)

```
Input sim-answers.json (Auszug, 4 Comments):
  #1: stance=agree,   disp=done,   flip_status=STABLE  → PL-Item (agree)
  #2: stance=refute,  disp=refute, flip_status=REFINED  → SKIP (Refutation, auch REFINED)
  #3: stance=partial, disp=verify, flip_status=STABLE  → PL-Item (partial)
  #4: stance=agree,   disp=done,   flip_status=FLIP    → PL-Item (war refute, kippte)

Ergebnis:
  [PR_PL] skip refute thread_id=ThreadId-2 (flip_status=REFINED)
  [PR_PL] item PL-DCSRE-486-007 ← thread ThreadId-1 (stance=agree)
  [PR_PL] item PL-DCSRE-486-008 ← thread ThreadId-3 (stance=partial)
  [PR_PL] item PL-DCSRE-486-009 ← thread ThreadId-4 (stance=agree, FLIP)
  [PR_PL] DONE: 3 PL-Items angelegt, 1 Refutationen uebersprungen.
  Naechster Schritt: /_IDF_orchestrate DCSRE-486 --pl-only --from=sdf_finish

tripel-ThreadId-2.md: parking_lot=null   (Refutation, REFINED, kein Item — korrekt AK4)
tripel-ThreadId-4.md: parking_lot=PL-DCSRE-486-009, flip_status=FLIP
```

---

## Tier

```
tier: sonnet   (Satellite — reine Datei-Transformation, kein Worker-Spawn,
                 kein Reasoning-intensiver Analyse-Schritt)
```
