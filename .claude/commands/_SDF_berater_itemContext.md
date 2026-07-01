---
status: deprecated
version: 1.1
type: berater
parent: _SDF_orchestrate
model_tier: floor
actor: _SDF_PreBerater_orchestrate (C9b) — Schritt 2
sdf_quelle: Z930-1037
tc: TC2
feature: BL-124
batch_aware: true  # BL-140
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "Liste der PL-Items fuer Pre-Item-Berater"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.task_source", purpose: "Item-Typ-Bestimmung"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.itemContext_per_item", purpose: "Liste der itemContext-Outputs pro Item"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.itemContext.batch_summary", purpose: "Aggregat: total, blocked_count"}
---

# _SDF_berater_itemContext (C2)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_itemContext (C2)                              ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                 ║
║           DF_PIPELINE_STATE.task_source                              ║
║           BDF_BATCH_STATE.bl_items (fuer BL-Zweig)                  ║
║         {VAULT}/.../6_PL/{bl_id}-parking-lot.md (PL-Zweig)          ║
║         Vault-Frontmatter bl_vault_path                              ║
║           (blocked_by[], reifegrad, spec_link, title)               ║
║         Blocker-Vault-Items (blocked_by[] traversal)                 ║
║         Model-Header (.claude/models/{NAME}_Model.md TC-Headers)    ║
║  SCHREIBT: BERATER_OUTPUTS.itemContext                               ║
║            {item_id, item_type, blocked, tc_scope}                  ║
║            + _berater_outputs.md Frontmatter: last_update,          ║
║              last_berater="C2"                                       ║
║  SCHREIBT AUCH (OQ-4 Resolution, semantisch im Concern):            ║
║    PL-Zweig: {VAULT}/.../6_PL/{bl_id}-parking-lot.md: IN_ARBEIT    ║
║    BL-Zweig: Vault-Frontmatter.status="BLOCKED"|"IN_PROGRESS"       ║
║              _backlog_index.md Status-Spalte (BLOCKED|IN_PROGRESS)  ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                  ║
║                  {WORKING_DIR}/_manifest.md DF_PIPELINE_STATE direkt              ║
║                  Modus (BL-405: itemContext gibt KEINEN Modus vor)  ║
║  ACTOR: _SDF_PreBerater_orchestrate (C9b) — Schritt 2               ║
║  MODELL-TIER: floor (haiku) — TC2, SDF-Quelle Z930-1037             ║
║  INVARIANTEN: INV-2 (Write-Isolation), INV-6 (blocked=true →        ║
║               Alpha-Beta-Pruning: PreBerater ruft C3 NICHT auf),   ║
║               NFR-3 (Idempotenz: "[STATUS: IN_ARBEIT]" Guard),      ║
║               INV-MODUS-1 (BL-405: itemContext gibt KEINEN Modus    ║
║               vor; reifegrad routet upstream — C3 entscheidet allein║
║               aus k-score/srs/coverage)                             ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_itemContext, args="{NAME}")

Parameter:
  {NAME} — Feature-Name (z.B. "BL-124")

Vorbedingung:
  - _berater_outputs.md existiert (M1 GATE PASS)
  - item_id + cycle_nr in _berater_outputs.md Frontmatter gesetzt (C9b Init)
  - DF_PIPELINE_STATE.task_source bekannt ("pl" | "backlog")

Ausgabe:
  - BERATER_OUTPUTS.itemContext (4 Felder: item_id, item_type, blocked, tc_scope)
  - Exitcode: 0=OK, 1=PRUNED (blocked), 2=FAIL (harter Fehler)

Logging-Format (NFR-4):
  [C2_itemContext] ENTRY item_id={item_id} cycle_nr={cycle_nr}
  [C2_itemContext] EXIT duration={ms}ms status={OK|PRUNED|FAIL}
```

## Schritte (aus SDF Z930-1037 extrahiert, fuer Berater-Scope angepasst)

```
SCHRITT 0: Entry-Log + item_type bestimmen
  [C2_itemContext] ENTRY cycle_nr={cycle_nr} batch_size={len(DF_BATCH_STATE.batch_items)}
  item_type = DF_PIPELINE_STATE.task_source
    ("pl" → "PL", "backlog" → "BL", sonst → "direct")
  batch_items = DF_BATCH_STATE.batch_items  # BL-140: Batch-Aware

SCHRITT 1: FOR item IN batch_items (BL-140 Batch-Loop)
  item_id = item.id
  item_context_result = {}

SCHRITT 1a: PL-Zweig (wenn item_type == "PL")
  pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
  Lies pl_path → suche Item mit ID/Name = {item_id}
  IF pl_item nicht gefunden:
    Logge WARNUNG: "[C2] PL-Item '{item_id}' nicht gefunden"
    blocked = false; tc_scope = "ALL"
    → SCHRITT 3 (Output)
  ELSE:
    # Idempotenz-Guard (NFR-3)
    IF "[STATUS: IN_ARBEIT]" NOT IN pl_item.text:
      pl_path: Ersetze "[ ] {item_id}" mit "[ ] {item_id} [STATUS: IN_ARBEIT]"
    blocked = false  # PL-Items haben kein blocked_by-Konzept

SCHRITT 1b: BL-Zweig (wenn item_type == "BL")
  bl_batch_info = BDF_BATCH_STATE.bl_items.find(bl.id == item_id)
  bl_vault_path = bl_batch_info.vault_path ?? null
  bl_reifegrad  = bl_batch_info.reifegrad ?? "UNREIF"
  bl_frontmatter = Lies bl_vault_path → Frontmatter (YAML)

  # Blocker-Verifikation (SDF Z967-994, BL-113a-FIX-10)
  blocked_by_list = bl_frontmatter.blocked_by ?? []
  blocker_not_done = []
  FUER blocker_id IN blocked_by_list:
    blocker_path = finde Vault-Item mit id = blocker_id
    IF blocker_path == null:
      Logge WARNUNG: "[C2] Blocker {blocker_id} nicht gefunden — Guard skip"
      CONTINUE
    blocker_fm = Lies blocker_path → Frontmatter
    IF blocker_fm.status != "DONE":
      blocker_not_done.append({id: blocker_id, status: blocker_fm.status})

  IF len(blocker_not_done) > 0:
    # Alpha-Beta-Pruning Ausloeser (INV-6)
    Schreibe Vault-Frontmatter.status = "BLOCKED"
    Schreibe Vault-Frontmatter.blocked_reason = "Blockers: " + join(ids)
    Aktualisiere _backlog_index.md (Status: BLOCKED fuer {item_id})
    blocked = true
    → SCHRITT 3 (Output — exitcode PRUNED)

  ELSE:
    # Status-Transition IN_PROGRESS (SDF Z996-999)
    Schreibe Vault-Frontmatter.status = "IN_PROGRESS"
    Aktualisiere _backlog_index.md (Status: IN_PROGRESS)

    # BL-405 (INV-MODUS-1-Bereinigung): KEIN reifegrad-zu-Modus Mapping mehr.
    # itemContext gibt KEINEN Modus vor — der Modus wird AUSSCHLIESSLICH von C3
    # (_SDF_berater_modusEntscheidung) aus k-score/srs/coverage entschieden.
    # reifegrad routet bereits upstream (A/IDF/SDF), C3 braucht hier keinen Override.

    blocked = false

SCHRITT 2: TC-Selektion (SDF Z1020-1036)
  model_tcs = parse_tc_headers("{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md")
  matched_tcs = keyword_match(item_text, item_tags, model_tcs)
  IF matched_tcs.length == 0:
    tc_scope = "ALL"  # Degraded Mode
    Logge WARNUNG: "[C2] Kein TC-Match — lade gesamtes Model (degraded)"
  ELSE:
    tc_scope = expand_tc_dependencies(matched_tcs)
    Logge: "[C2] TC-Scope: {tc_scope}"

SCHRITT 3: Item-Output sammeln (BL-140 Batch-Loop)
  item_context_result = {
    item_id: {item_id},
    item_type: {item_type},        # BL | PL | direct
    blocked: {blocked},
    tc_scope: {tc_scope}
  }
  # BL-405: kein Modus-Feld mehr (INV-MODUS-1: C3 entscheidet Modus allein).
  BERATER_OUTPUTS.itemContext_per_item.append(item_context_result)

END_FOR  # Ende batch_items Loop

SCHRITT 4: Batch-Aggregat schreiben (BL-140)
  blocked_items = [i FOR i IN itemContext_per_item IF i.blocked == true]
  # BL-405: kein Modus-Aggregat mehr (itemContext gibt keinen Modus vor — INV-MODUS-1).
  BERATER_OUTPUTS.itemContext.batch_summary = {
    total: len(batch_items),
    blocked_count: len(blocked_items)
  }
  _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="C2"

SCHRITT 5: Exit-Log
  blocked_count = BERATER_OUTPUTS.itemContext.batch_summary.blocked_count
  [C2_itemContext] EXIT duration={ms}ms batch_total={len(batch_items)} blocked={blocked_count}
```

## Output an BERATER_OUTPUTS (BL-140 Batch-Aware)

```yaml
itemContext_per_item:
  - item_id: "BL-124"
    item_type: "BL"        # BL | PL | direct
    blocked: false         # true → Alpha-Beta-Pruning
    tc_scope: ["TC2", "TC5", "TC7"]
  - item_id: "BL-125"
    item_type: "BL"
    blocked: true
    tc_scope: []
itemContext:
  batch_summary:
    total: 2
    blocked_count: 1
```

> **BL-405 (INV-MODUS-1-Bereinigung):** itemContext liefert KEIN Modus-Feld mehr. Der frueher hier berechnete `reifegrad→Modus`-Pfad war Altschuld (verletzte INV-MODUS-1). Der Modus wird AUSSCHLIESSLICH von C3 (_SDF_berater_modusEntscheidung) aus k-score/srs/coverage entschieden; reifegrad routet upstream.

> **BL-303 (Flag-Provenance-Kette: PL -> itemContext -> subSkillPrompt -> Worker):** itemContext liest `test_correction_authorized` (bool) und `authorization_evidence` (string) aus dem PL-Frontmatter des jeweiligen Items und reicht sie in `sub_batches[].items[]` durch. Default: Feld fehlt = protektiv (kein Flag = kein autorisierter Test-Correction-Pfad). Diese Felder sind KEINE Modus-Felder (INV-MODUS-1 bleibt unberuehrt) — sie steuern ausschliesslich den Split-Trigger in SCHRITT 7 (_SDF_berater_modusEntscheidung: split_required=true -> M3-Pflicht) und den subSkillPrompt-Schalter in dispatch_implement.js (M2-_TDD_green-Pfad: Freigabe vs. protektiver Default). Der gruene Worker darf die autorisierte Test-Korrektur GENAU DANN durchfuehren wenn `test_correction_authorized: true` im Prompt erscheint; ohne Flag gilt der Default-Schutz (NOCH KEINE Autorisierung / GREEN_BLOCKED_TEST_CONFLICT).
>
> Felder in `sub_batches[].items[]`:
> - `test_correction_authorized`: bool (aus PL-Frontmatter, Default: Feld fehlt = false = protektiv)
> - `authorization_evidence`: string (Begruendung fuer den gruenen Worker, z.B. "FLIP:BL-303-finding-X — adjudiziert YYYY-MM-DD")

## Risiko-Hinweis

**HD01-OBS-1 (R4 LOW):** haiku-Tier evtl. zu niedrig bei vielen blocked_by-Eintraegen
(mehrere HTTP-Vault-Reads). AK-4 prueft nach Deployment; Tier-Upgrade zu sonnet ohne
Spec-Aenderung moeglich (ADR-D).
