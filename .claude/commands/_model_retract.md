---
type: building-block
status: active
version: 1.0.0
created: 2026-05-06
op: Correction
phase: ad-hoc
type_role: retractor
related: _model, _spec, _K_score, _IDF_berater_modelSync, _PT_promoteFromPL, _SL_promoteFromPL
chain_position: ad-hoc (User-Trigger)
model_tier: opus
---

# /_model_retract — Korrektur-Flow fuer falsche W{n} / AK{n} / Library-Eintraege

**Status:** v1.0.0 (initial — Korrektur-Command, kein Pipeline-Hook)
**Actor:** RETRACTOR
**Zweck:** Wenn ein Akzeptanzkriterium (`AK{n}`), eine Wahrheit (`W{n}`), oder ein bereits promovierter Library-Eintrag sich als falsch herausstellt ("doch keine Validierung — AK7 war ein Missverstaendnis"), markiert dieser Command alle betroffenen Stellen als `DEPRECATED` mit Reason + Datum, **ohne zu loeschen**. Triggert anschliessend `_K_score` Re-Computation und Library-Markierung.

> **Architektur-Invariante (BL-103, ARCH):** APPEND-ONLY. Wahrheiten/AKs werden NIE geloescht — auch nicht bei Falsch-Entscheidungen. DEPRECATED ist der einzige Rueckweg. Audit-Trail bleibt vollstaendig erhalten.

> **Abgrenzung zu modelSync:** modelSync ist **append-only Promotion** (PL → Model). DIESER Command ist **append-only Markierung** (Model → DEPRECATED). Beide sind irreversibel.

---

## Aufruf

```
/_model_retract {ID} --reason "{Begruendung}" [--cascade] [--dry-run]
```

| Parameter | Pflicht | Format | Beispiel |
|-----------|---------|--------|----------|
| `ID` | JA | `W{n}`, `AK{n}`, `RF{n}`, `PL-{n}` | `W7`, `AK12`, `RF3`, `PL-25` |
| `--reason` | JA | Freitext mit Evidenz | `"AK7 widerspruecht User-Direktive 2026-05-06: doch keine Validierung gewuenscht"` |
| `--cascade` | NEIN | Flag | Markiert auch transitiv abhaengige Items (Library-Eintraege) |
| `--dry-run` | NEIN | Flag | Zeigt was passieren wuerde, schreibt nichts |

**Reason ist PFLICHTFELD.** Ohne Begruendung kein Retract — Evidenz-Pflicht (W222, BL-103 AK-C-6).

---

## VERTRAG

```
+======================================================================+
| VERTRAG: /_model_retract                                             |
+======================================================================+
| LIEST:                                                                |
|   {bl_folder}/2_Model/{NAME}_Model.md     (W{n}-Liste)               |
|   {bl_folder}/3_Spec/{NAME}_Spec.md       (AK/RF-Liste)              |
|   {bl_folder}/6_PL/{bl_id}-parking-lot.md (PL-Items)                 |
|   {bl_folder}/4_K_Score/{NAME}_KScore.md  (vorheriger Score)         |
|   {bl_folder}/2_Model/_modelSync_log_*.md (Audit-Trail)              |
|   .claude/analysis/_manifest.md           (BERATER_OUTPUTS)          |
|   {VAULT}/Libraries/PatternLibrary/_project/{LAYER}/*.md (cascade)   |
|   {VAULT}/Libraries/SemanticLibrary/_project/{LAYER}/*.md (cascade)  |
|                                                                       |
| SCHREIBT:                                                             |
|   {bl_folder}/2_Model/{NAME}_Model.md                                |
|     -> W{n}-Block: status: deprecated, deprecated_reason, deprecated_at |
|   {bl_folder}/3_Spec/{NAME}_Spec.md                                  |
|     -> AK{n}/RF{n}: ~~strikethrough~~ + DEPRECATED-Block             |
|   {bl_folder}/6_PL/{bl_id}-parking-lot.md                            |
|     -> Item: retracted-marker + Reason                               |
|   {bl_folder}/2_Model/_retract_log_{DATE}.md                         |
|     -> Append-Only Audit-Log (was, warum, wann, von wem)             |
|   {bl_folder}/4_K_Score/{NAME}_KScore.md                             |
|     -> Re-Computed Score (via _K_score Skill-Aufruf)                 |
|                                                                       |
| SCHREIBT (bei --cascade):                                             |
|   {VAULT}/Libraries/PatternLibrary/_project/{LAYER}/{name}.md        |
|     -> frontmatter.status = "deprecated"                              |
|     -> frontmatter.deprecated_reason mit Source-Verweis              |
|   {VAULT}/Libraries/SemanticLibrary/_project/{LAYER}/*.md            |
|     -> Eintrag: ~~strikethrough~~ + RETRACTED-Annotation             |
|                                                                       |
| BERATER_OUTPUTS.retract:                                              |
|   id_retracted:           string  (W7, AK12, ...)                    |
|   reason:                 string                                      |
|   cascaded_items:         list[{path, id}]                           |
|   k_score_old:            int                                         |
|   k_score_new:            int                                         |
|   k_score_delta:          int                                         |
|   files_modified:         list[path]                                  |
|   log_path:               string                                      |
|   exit_code:              0 OK | 2 ABORT (id not found / no reason)  |
|                                                                       |
| ACTOR: RETRACTOR                                                      |
| MODELL-TIER: opus (Klassifikation + Cascade-Analyse)                  |
+======================================================================+
```

---

## INVARIANTEN

| INV | Beschreibung |
|-----|-------------|
| INV-RT-1 | **REASON-PFLICHT** — `--reason` ist PFLICHTFELD (BLOCKER wenn fehlt). Keine Retracts ohne Evidenz. |
| INV-RT-2 | **APPEND-ONLY** — KEINE Loeschung. Items werden mit `status: deprecated` markiert, Original-Text bleibt (durchgestrichen). |
| INV-RT-3 | **IRREVERSIBLE** — Einmal DEPRECATED, kann NICHT zurueck zu `active`. Wenn Item doch wieder gelten soll: neues W{n+k} schreiben (Re-Promotion). |
| INV-RT-4 | **AUDIT-TRAIL** — `_retract_log_{DATE}.md` enthaelt vollstaendige Begruendung + Diff. |
| INV-RT-5 | **CASCADE-OPTIONAL** — `--cascade` markiert auch Vault-Library-Eintraege. Default: NUR Model/Spec/PL im Projekt. Cascade ist explizit (User entscheidet). |
| INV-RT-6 | **K-SCORE-RECOMPUTE** — Nach Retract IMMER `_K_score` triggern (sofern es noch existiert). Score-Delta wird in BERATER_OUTPUTS protokolliert. |
| INV-RT-7 | **ID-MUST-EXIST** — Wenn ID (W7, AK12 etc.) nicht in den Files existiert: ABBRUCH mit Liste verfuegbarer IDs. Kein blindes Schreiben. |
| INV-RT-8 | **CONFLICT-DETECT** — Bei Cascade: wenn Library-Eintrag bereits `deprecated` ist mit ANDEREM Reason: WARN + NICHT ueberschreiben. |

---

## CHAIN-POSITION

```
User merkt: "AK7 war doch falsch"
     │
     ▼
[/_model_retract AK7 --reason "..."]   ← DIESER COMMAND
     │
     ├──► Spec.md AK7 ~~deprecated~~
     ├──► Model.md W{n} (abhaengig von AK7) deprecated
     ├──► PL.md Item-Marker retracted
     ├──► K_Score recomputed (--reason im Manifest)
     │
     ▼  (--cascade optional)
PatternLibrary/SemanticLibrary
   marker: deprecated
     │
     ▼
NACH Retract: User kann re-promoten via neuer SDF-Run
   (modelSync schreibt neue W{n+k} mit korrekter Definition)
```

---

## ABLAUF

### Phase 1: Validierung + Pfad-Resolution

```python
# INV-RT-1: Reason-Check
if not args.reason:
  raise BLOCKER("--reason ist PFLICHTFELD. Kein Retract ohne Evidenz (BL-103 AK-C-6).")

# Pfade aufloesen
paths = read_manifest_paths()
bl_folder = paths.bl_folder
vault_root = paths.vault_root

model_path  = f"{bl_folder}/2_Model/{NAME}_Model.md"
spec_path   = f"{bl_folder}/3_Spec/{NAME}_Spec.md"
pl_path     = f"{bl_folder}/6_PL/{bl_id}-parking-lot.md"
score_path  = f"{bl_folder}/4_K_Score/{NAME}_KScore.md"
log_path    = f"{bl_folder}/2_Model/_retract_log_{DATE}.md"
```

### Phase 2: ID-Lookup (INV-RT-7)

```python
id_type = classify_id(args.ID)  # "W" | "AK" | "RF" | "PL"

found_locations = []
if id_type == "W":
  hit = grep_w_block(model_path, args.ID)
  if hit: found_locations.append(("model", model_path, hit))
elif id_type in ("AK", "RF"):
  hit = grep_ak_block(spec_path, args.ID)
  if hit: found_locations.append(("spec", spec_path, hit))
elif id_type == "PL":
  hit = grep_pl_item(pl_path, args.ID)
  if hit: found_locations.append(("pl", pl_path, hit))

if not found_locations:
  available = list_all_ids_in_files()
  raise ABORT(f"ID {args.ID} nicht gefunden. Verfuegbare IDs: {available[:20]}...")

Logge: f"[retract] found {args.ID} in {[loc[0] for loc in found_locations]}"
```

### Phase 3: Cascade-Analyse (Cross-References finden)

Wenn AK retracted wird, sind alle abgeleiteten W{n} betroffen. modelSync-Logs liefern die Trace-Map:

```python
cascaded = []

# 3.1 Model.md: welche W{n} verweisen auf retracted ID?
for w_block in parse_w_blocks(model_path):
  if w_block.references(args.ID):
    cascaded.append(("model", model_path, w_block))

# 3.2 modelSync-Logs: welche W{n} wurden aus der retracted PL-Item-Quelle promoviert?
for sync_log in glob(f"{bl_folder}/2_Model/_modelSync_log_*.md"):
  for entry in parse_log(sync_log):
    if entry.source.contains(args.ID):
      cascaded.append(("model-sync-derived", sync_log, entry))

# 3.3 PL: welche Items haben synced-to-model auf den retracted W{n}?
for pl_item in parse_pl(pl_path):
  if pl_item.has_marker("synced-to-model") and pl_item.derived_w == args.ID:
    cascaded.append(("pl-marker", pl_path, pl_item))

# 3.4 (NUR --cascade) Vault-Library-Eintraege
if args.cascade:
  # Pattern-Library
  for pt_log in glob(f"{bl_folder}/2_Model/_ptPromote_log_*.md"):
    for entry in parse_log(pt_log):
      if entry.source.contains(args.ID):
        pt_path = entry.target_path  # in Library
        cascaded.append(("pt-library", pt_path, entry))

  # Semantic-Library
  for sl_log in glob(f"{bl_folder}/2_Model/_slPromote_log_*.md"):
    for entry in parse_log(sl_log):
      if entry.source.contains(args.ID):
        sl_path = entry.target_path  # in Library
        cascaded.append(("sl-library", sl_path, entry))

Logge: f"[retract] cascade analysis: {len(cascaded)} dependent items found"
```

### Phase 4: Dry-Run-Pfad

```python
if args.dry_run:
  print_summary(args.ID, found_locations, cascaded, args.reason)
  return  # KEINE Schreibungen
```

### Phase 5: Markierungen schreiben (INV-RT-2, -4)

**5.1 Primaeres Item — Model.md (Beispiel W7):**

```markdown
<!-- VOR Retract -->
### W7: Hospiz-Kooperationen werden mit MaxLength(10) validiert
Source: BL-XX-PL-3 (2026-04-30)

<!-- NACH Retract -->
### ~~W7: Hospiz-Kooperationen werden mit MaxLength(10) validiert~~ [DEPRECATED]
Source: BL-XX-PL-3 (2026-04-30)

> **DEPRECATED am {DATE}** — _model_retract
>
> **Reason:** {reason}
>
> Diese Wahrheit gilt nicht mehr. Statt Loeschen: Strikethrough +
> Audit-Trail (BL-103 AK-C-6, APPEND-ONLY). Falls korrekte Variante
> wieder benoetigt: neues W{n+k} schreiben (modelSync naechste Runde).
```

**5.2 Spec.md (AK{n}):**

```markdown
<!-- VOR -->
### AK7: System validiert Hospiz-Kooperationen mit MaxLength(10)
- Severity: BLOCKER
- ...

<!-- NACH -->
### ~~AK7: System validiert Hospiz-Kooperationen mit MaxLength(10)~~ [DEPRECATED am {DATE}]
- ~~Severity: BLOCKER~~
- ...

> **DEPRECATED am {DATE}** — _model_retract  Reason: {reason}
```

**5.3 PL-Items (Marker):**

```markdown
- [x] **PL-3** Validator MaxLength fuer KooperationHospiz   synced-to-model: 2026-04-30   **retracted: 2026-05-06** ({reason-short})
```

**5.4 Audit-Log schreiben:**

```markdown
# Retract-Log {DATE}

## Retract: {ID}

**Datum:** {ISO}
**Reason:** {reason}
**Initiator:** /_model_retract (User-Trigger)

### Primaeres Item
- **Datei:** {model_path}
- **Vorher:** {original_text}
- **Nachher:** [DEPRECATED] markiert

### Cascade-Items ({N})
- model: {paths}
- pl-marker: {paths}
- {falls --cascade} pt-library: {paths}
- {falls --cascade} sl-library: {paths}

### K-Score Vorher/Nachher
- Vorher: {old_k_score}
- Nachher: {new_k_score} (Delta: {delta})
```

### Phase 6: K-Score Re-Compute (INV-RT-6)

```python
old_k_score = read_k_score(score_path)

if Skill_available("_K_score"):
  Logge: "[retract] triggering K-Score re-computation"
  Skill(skill="_K_score", args=NAME)
  new_k_score = read_k_score(score_path)  # frisch
  delta = new_k_score - old_k_score
else:
  Logge: "[retract] _K_score not available — skipping re-compute (NON-BLOCKING)"
  new_k_score = old_k_score
  delta = 0
```

### Phase 7: Cascade auf Vault-Libraries (INV-RT-5, -8)

```python
if args.cascade:
  for kind, lib_path, entry in cascaded:
    if kind not in ("pt-library", "sl-library"):
      continue

    # Conflict-Detect (INV-RT-8)
    existing_status = read_frontmatter(lib_path).get("status")
    existing_reason = read_frontmatter(lib_path).get("deprecated_reason")
    if existing_status == "deprecated" and existing_reason and existing_reason != args.reason:
      Logge: f"[retract] WARN: {lib_path} already deprecated with different reason — SKIP"
      continue

    # Schreibe deprecation
    if kind == "pt-library":
      update_frontmatter(lib_path, {
        "status": "deprecated",
        "deprecated_reason": f"Retracted via /_model_retract: {args.reason} (Source: {args.ID})",
        "deprecated_at": DATE,
        "replacement_pattern": "keiner",
      })
    elif kind == "sl-library":
      # SemanticLibrary: Strikethrough-Annotation
      annotate_in_file(lib_path, entry.term, f"~~{entry.term}~~ [RETRACTED {DATE}: {args.reason}]")

    Logge: f"[retract] cascaded to library: {lib_path}"
```

### Phase 8: Output schreiben

```python
manifest_update("BERATER_OUTPUTS.retract", {
  id_retracted: args.ID,
  reason: args.reason,
  cascaded_items: [{path, id} for ... in cascaded],
  k_score_old: old_k_score,
  k_score_new: new_k_score,
  k_score_delta: delta,
  files_modified: [model_path, spec_path, pl_path, score_path, log_path] + cascade_paths,
  log_path: log_path,
  exit_code: 0,
})

Logge: f"[retract] DONE — {args.ID} marked deprecated, {len(cascaded)} items cascaded, K-Score {old_k_score}→{new_k_score}"
```

---

## QUICK-START

```bash
# Beispiel: AK7 war doch falsch (User-Direktive 2026-05-06)
/_model_retract AK7 --reason "User-Direktive 2026-05-06: keine Validierung gewuenscht, MaxLength-Constraint entfaellt. Siehe PR-Comment Jochen."

# Mit Cascade auf Library (markiert auch promoted Pattern als deprecated)
/_model_retract AK7 --reason "..." --cascade

# Dry-Run zum Testen
/_model_retract W7 --reason "..." --dry-run

# Mehrere IDs nacheinander (nicht batch — bewusst eine nach der anderen mit Begruendung)
/_model_retract W7 --reason "..."
/_model_retract W8 --reason "..."
```

---

## ABGRENZUNG

| Command | Was es macht |
|---------|--------------|
| `_IDF_berater_modelSync` | PL → Model/Spec PROMOTE (append-only neue Items) |
| `_PT_promoteFromPL` / `_SL_promoteFromPL` | PL → Library PROMOTE |
| `/_model_retract` (DIESER) | Model/Spec/PL/Library RETRACT (append-only deprecated-Markierung) |
| `_K_score` | Score-Berechnung (wird von DIESEM aufgerufen) |

**Symmetrie:** Promote (vorwaerts) ↔ Retract (rueckwaerts). Beide append-only. Beide audit-trail-vollstaendig.

---

## WIE OFT BRAUCH ICH DAS?

Selten. Retract ist ein Korrektur-Mechanismus — wenn die Pipeline gut laeuft, brauchst du es nie. Typische Trigger:
- PR-Reviewer sagt "AK{n} war ein Missverstaendnis"
- User erkennt nach Implementation: "Das war doch nicht was ich wollte"
- Bug-Report: "Pattern X funktioniert nicht — sollte deprecated"

Wenn du oft Retract brauchst → A-/IDF-Pipeline produziert zu viele falsche AK/W-Promotions. Dann lieber stromaufwaerts fixen (modelSync Stabilitaets-Kriterien strenger).

---

ARGUMENTS: $ARGUMENTS
