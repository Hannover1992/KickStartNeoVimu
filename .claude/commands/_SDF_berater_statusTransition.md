---
status: active
version: 1.2
type: berater
parent: _SDF_orchestrate
model_tier: floor
actor: _SDF_orchestrate — Phase 3, SCHRITT 3.3 (BL-140)
sdf_quelle: Z1725-1800
tc: TC7
feature: BL-124
batch_aware: true
---

# _SDF_berater_statusTransition (C7)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_statusTransition (C7) — BL-140: Batch-Level  ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                 ║
║           DF_PIPELINE_STATE.task_source                              ║
║           DF_PIPELINE_STATE.batch_done (fuer Idempotenz)            ║
║         DF_BATCH_STATE.batch_items[] (alle Items im Batch)          ║
║         DF_BATCH_STATE.item_done[] (welche Items als DONE markiert) ║
║         BERATER_OUTPUTS.postBatch_aggregate.gap_ready (Aufruf-Bed.) ║
║         {VAULT}/.../6_PL/{bl_id}-parking-lot.md (PL-Zweig)          ║
║         Vault-Frontmatter bl_item.vault_path (BL-Zweig)              ║
║         Vault-Frontmatter parent_epic (fuer Epic-Kaskade)           ║
║         Vault-Frontmatter parent_fm.children[] (Kaskade-Pruefung)   ║
║  SCHREIBT: BERATER_OUTPUTS.statusTransition_batch                    ║
║            {transitions[], epic_cascades[], batch_complete}         ║
║            + _berater_outputs.md Frontmatter: last_update,          ║
║              last_berater="C7"                                       ║
║  SCHREIBT AUCH (OQ-4 Resolution, Domain: Batch abschliessen):       ║
║    PL-Zweig: {VAULT}/.../6_PL/{bl_id}-parking-lot.md: DONE          ║
║              fuer JEDEN Item in batch_items WHERE id IN item_done   ║
║              Markierung via pl_item_marker.mark_pl_done (AK-4, BL-435)  ║
║              + Read-Back-Verify pl_item_is_done (exitcode=2 bei Mismatch)║
║              (AK-3 BL-428: end_art aus item.end_art ?? "done",      ║
║               ENUM-Fallback "done"; 4 Werte: done/deferred/         ║
║               PO-question/rolled-up)                                ║
║              + commit_ref=<git rev-parse HEAD> am PL-Item-FM        ║
║                (BL-271 batch_2 Auto-Pop, abwaertskompat: kein Hash  ║
║                 -> Feld weglassen, kein Crash; KEIN Freitext)       ║
║    BL-Zweig: Vault-Frontmatter.status="DONE" + done_date            ║
║              _backlog_index.md via update_index_row() aus           ║
║              bl_index_updater.py (AK-2 BL-428: line-anchored,      ║
║              verhindert BL-364/BL-3640-Kollision)                   ║
║              READ-BACK nach Write: Node-FM.status==DONE UND         ║
║              index_row_has_done()==True (AK-1 BL-428);              ║
║              bei Mismatch → RETURN exitcode=2 (kein optimist.report)║
║    Epic-Kaskade: Vault-Frontmatter.status="DONE" fuer parent_epics  ║
║                  _backlog_index.md via update_index_row() (AK-2)    ║
║    DF_PIPELINE_STATE.batch_done APPEND alle verarbeiteten item_ids  ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                  ║
║                  {VAULT}/.../6_PL/{bl_id}-pl.md APPEND (C6-Domain)  ║
║  ACTOR: _SDF_orchestrate — Phase 3, SCHRITT 3.3 (BL-140)           ║
║  MODELL-TIER: floor — TC7, SDF-Quelle Z1725-1800                    ║
║  INVARIANTEN: INV-2 (Write-Isolation), INV-6 (batch leer oder       ║
║               item_done leer → SKIP), NFR-3 (Idempotenz: Items in   ║
║               item_done; IDEMPOTENZ-GUARD skipt bereits-DONE Items  ║
║               AK-5 BL-428), ADR-F (I_PIPELINE_STATE Signal-Felder  ║
║               unveraendert), AK-1 exitcode=2 bei Read-Back-Mismatch ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_statusTransition, args="{NAME}")

Parameter:
  {NAME}  — Feature-Name

Vorbedingung:
  - BERATER_OUTPUTS.postBatch_aggregate.gap_ready = true (SDF Phase 3 prueft vor Aufruf)
  - DF_BATCH_STATE.batch_items[] befuellt
  - DF_BATCH_STATE.item_done[] befuellt (welche Items wirklich DONE sind)
  - bl_item.vault_path im DF_BATCH_STATE vorhanden (fuer BL-Zweig)

Ausgabe:
  - BERATER_OUTPUTS.statusTransition_batch (3 Felder)
  - Exitcode: 0=OK, 1=SKIP (item_done leer), 2=FAIL (Vault-Pfad fehlt ODER Read-Back-Mismatch AK-1 BL-428)

Logging-Format (NFR-4):
  [C7_statusTransition] ENTRY batch_count={batch_count} done_count={done_count} cycle_nr={cycle_nr}
  [C7_statusTransition] EXIT duration={ms}ms status={OK|SKIP|FAIL}
```

## Schritte (BL-140: Batch-Level — iteriert ueber alle Items im Batch)

```
SCHRITT 0: Entry-Log + Skip-Guard (INV-6)
  batch_items = DF_BATCH_STATE.batch_items[]
  item_done = DF_BATCH_STATE.item_done[]
  [C7_statusTransition] ENTRY batch_count={batch_items.length} done_count={item_done.length} cycle_nr={cycle_nr}
  transitions = []
  epic_cascades = []

  IF item_done.length == 0:
    Logge: "[C7] SKIP: item_done leer (INV-6)"
    BERATER_OUTPUTS.statusTransition_batch = { transitions: [], epic_cascades: [], batch_complete: false }
    _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="C7"
    [C7_statusTransition] EXIT status=SKIP
    → RETURN exitcode=1

SCHRITT 1: FOR item IN batch_items WHERE item.id IN item_done (BL-140: Batch-Iteration)

  SCHRITT 1 (PRE): IDEMPOTENZ-GUARD (AK-5, BL-428)
    # Wenn item bereits DONE auf Disk — Skip, kein Doppel-Write
    node_status = lies Node-FM.status fuer item.id   # Vault-Frontmatter
    # PL-Zweig: format-agnostischer Check via Helper (AK-4, BL-435 DoD-9)
    # pl_item_is_done erkennt kanonisch-done UND alle 5 Alt-Formate — kein Format-Raten
    from pl_item_marker import pl_item_is_done
    _pre_pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
    pl_already_done = pl_item_is_done(Lese(_pre_pl_path), item.id) IF item.item_type == "PL" ELSE False
    IF node_status == "DONE" OR pl_already_done:
      Logge: "[C7] IDEMPOTENZ-GUARD: {item.id} bereits DONE auf Disk — Skip"
      transitions.append({ id: item.id, type: item.item_type, transition: "ALREADY_DONE" })
      CONTINUE  # naechstes item

  SCHRITT 1a: PL-Zweig (wenn item.item_type == "PL")
    # AK-3 (BL-428): end_art-Parameter mit ENUM-Validierung + Fallback
    END_ART_ENUM = ["done", "deferred", "PO-question", "rolled-up"]
    end_art = item.end_art ?? "done"
    IF end_art NOT IN END_ART_ENUM:
      Logge WARNUNG: "[C7] end_art '{end_art}' unbekannt — Fallback auf 'done'"
      end_art = "done"

    # IN_ARBEIT → DONE Transition via pl_item_marker.py (AK-4, BL-435)
    # Kein Format-Raten mehr — Helper deckt 6 Formate (kanonisch + 5 Alt) atomar ab.
    from pl_item_marker import mark_pl_done, pl_item_is_done
    pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
    pl_content = Lese(pl_path)
    pl_content_updated = mark_pl_done(pl_content, item.id)
    Schreibe(pl_path, pl_content_updated)

    # Read-Back-Verify (AK-4, BL-435 + AK-1 BL-428 Muster)
    pl_content_readback = Lese(pl_path)
    IF NOT pl_item_is_done(pl_content_readback, item.id):
      Logge FEHLER: "[C7] PL READ-BACK FEHLER: {item.id} nicht als done erkannt nach mark_pl_done — exitcode=2"
      → RETURN exitcode=2
    Logge: "[C7] PL-Item {item.id}: mark_pl_done + Read-Back OK (pl_item_marker, BL-435)"
    transitions.append({ id: item.id, type: "PL", transition: "IN_ARBEIT→DONE" })
    Logge: "[C7] PL-Item {item.id}: IN_ARBEIT → DONE (end_art={end_art})"

    # BL-271 batch_2: commit_ref-Auto-Population (am [x]-Setz-Punkt, abwaertskompatibel)
    # GROUNDING (2026-06-14): es gibt KEIN Manifest-Feld `code_verified_against`.
    # Die maschinell-bekannte, VERIFIZIERTE Commit-Quelle ist der aktuelle HEAD
    # nach dem (durch die Stage-Loop/_I_verify bestaetigten) Batch-Commit — exakt
    # die Quelle, die _I_verify (Z442) + _A_berater_gitTracking (head_sha) nutzen.
    # KEIN Freitext: der Hash kommt aus `git rev-parse HEAD`, nicht aus item.text.
    verified_sha = bash("git rev-parse HEAD").stdout.strip()   # Mothership-cwd
    IF verified_sha != "" AND len(verified_sha) >= 7:           # plausibler Hash (vgl. pl_learning_schema.is_plausible_commit_ref)
      Setze PL-Item-Frontmatter.commit_ref = verified_sha (in pl_path, fuer item.id)
      Logge: "[C7] PL-Item {item.id}: commit_ref={verified_sha[:8]} (auto, BL-271)"
    ELSE:
      # Abwaertskompatibel: kein verifizierter Hash verfuegbar -> Feld WEGLASSEN,
      # KEIN Crash, KEIN Platzhalter. Das Item bleibt valide (INV-PL-LEARN-1).
      Logge: "[C7] PL-Item {item.id}: commit_ref weggelassen (kein HEAD-Hash, BL-271 abwaertskompat)"

  SCHRITT 1b: BL-Zweig (wenn item.item_type == "BL")
    # IN_PROGRESS → DONE (SDF Z1739-1748, RF-SDF-008, AK-08, INV-3)
    bl_batch_info = DF_BATCH_STATE.batch_items.find(b.id == item.id)
    bl_vault_path = bl_batch_info.vault_path ?? null
    IF bl_vault_path == null:
      Logge FEHLER: "[C7] FAIL: bl_vault_path nicht gefunden fuer {item.id}"
      → RETURN exitcode=2

    Schreibe Vault-Frontmatter.status = "DONE" (bl_vault_path)
    Schreibe Vault-Frontmatter.done_date = {Datum}

    # AK-2 (BL-428): update_index_row() statt Freitext — line-anchored, verhindert BL-364/BL-3640-Kollision
    # AK-3 (BL-428): end_art fuer BL-Zweig analog PL-Zweig
    end_art_bl = item.end_art ?? "done"
    IF end_art_bl NOT IN END_ART_ENUM: end_art_bl = "done"
    from bl_index_updater import update_index_row, index_row_has_done
    index_path = "{VAULT}/_backlog_index.md"
    index_content = Lese(index_path)
    index_content_updated = update_index_row(index_content, item.id, "DONE", end_art_bl)
    Schreibe(index_path, index_content_updated)

    # SCHRITT 1b-POST: READ-BACK-Block (AK-1, BL-428) — kein optimistic-report
    node_fm_reread = Lies bl_vault_path → Frontmatter   # erneut lesen
    index_reread = Lese(index_path)
    readback_node_ok = (node_fm_reread.status == "DONE")
    readback_index_ok = index_row_has_done(index_reread, item.id)
    IF NOT readback_node_ok OR NOT readback_index_ok:
      Logge FEHLER: "[C7] READ-BACK FEHLER: node_ok={readback_node_ok} index_ok={readback_index_ok} fuer {item.id}"
      → RETURN exitcode=2
    Logge: "[C7] READ-BACK OK: {item.id} DONE in Node-FM={readback_node_ok} + Index={readback_index_ok}"

    transitions.append({ id: item.id, type: "BL", transition: "IN_PROGRESS→DONE" })
    Logge: "[C7] BL-Item {item.id}: IN_PROGRESS → DONE (done_date={Datum}, end_art={end_art_bl})"

    # Epic-Kaskade Tiefe-1 (SDF Z1751-1786, BL-113a-FIX-9)
    bl_frontmatter = Lies bl_vault_path → Frontmatter (erneut, fuer parent_epic)
    parent_id = bl_frontmatter.parent_epic ?? null

    IF parent_id != null:
      parent_path = finde Vault-Item mit id = parent_id
      IF parent_path != null:
        parent_fm = Lies parent_path → Frontmatter
        parent_children = parent_fm.children ?? []
        IF len(parent_children) > 0:
          all_done = true
          FUER child_id IN parent_children:
            child_path = finde Vault-Item mit id = child_id
            IF child_path == null:
              Logge WARNUNG: "[C7] EPIC-KASKADE: Child {child_id} nicht gefunden — Kaskade skip"
              all_done = false; BREAK
            child_fm = Lies child_path → Frontmatter
            IF child_fm.status != "DONE":
              all_done = false; BREAK
          IF all_done:
            Schreibe parent_fm.status = "DONE" (parent_path)
            Schreibe parent_fm.done_date = {Datum}
            # AK-2 (BL-428): update_index_row() fuer Epic-Kaskade
            epic_index_content = Lese(index_path)
            epic_index_updated = update_index_row(epic_index_content, parent_id, "DONE", "rolled-up")
            Schreibe(index_path, epic_index_updated)
            epic_cascades.append(parent_id)
            Logge: "[C7] EPIC-KASKADE: Parent-Epic {parent_id} → DONE (alle Kinder DONE)"
          ELSE:
            Logge: "[C7] EPIC-KASKADE: Parent {parent_id} bleibt IN_PROGRESS (Kinder offen)"
        ELSE:
          Logge WARNUNG: "[C7] EPIC-KASKADE: Parent {parent_id} kein children-Feld"
      ELSE:
        Logge WARNUNG: "[C7] EPIC-KASKADE: Parent-Vault-Item {parent_id} nicht gefunden"

  SCHRITT 1c: DF_PIPELINE_STATE.batch_done aktualisieren
    DF_PIPELINE_STATE.batch_done APPEND {item.id}
    Aktualisiere Manifest

# END FOR

SCHRITT 2: Output in BERATER_OUTPUTS.statusTransition_batch schreiben
  batch_complete = (transitions.length == item_done.length)
  BERATER_OUTPUTS.statusTransition_batch = {
    transitions: {transitions},          # [{id, type, transition}] fuer jeden verarbeiteten Item
    epic_cascades: {epic_cascades},      # [parent_id, ...] ausgeloeste Kaskaden
    batch_complete: {batch_complete}     # true wenn alle item_done verarbeitet
  }
  _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="C7"

SCHRITT 3: Exit-Log
  [C7_statusTransition] EXIT duration={ms}ms status=OK
```

## Output an BERATER_OUTPUTS.statusTransition_batch

```yaml
statusTransition_batch:
  transitions:                     # Liste aller verarbeiteten Items
    - id: "PL-4"
      type: "PL"
      transition: "IN_ARBEIT→DONE"
    - id: "BL-140"
      type: "BL"
      transition: "IN_PROGRESS→DONE"
  epic_cascades: ["BL-113"]        # parent_ids wo Kaskade ausgeloest wurde (leer wenn keine)
  batch_complete: true             # true wenn alle item_done verarbeitet
```

## Abgrenzung

- C7 schreibt `{VAULT}/.../6_PL/{bl_id}-parking-lot.md [x]` (Abschluss-Domain).
- AK-4 BL-428: C7 ist ALLEINIGER Writer der PL-[x]-Markierung. _SDF_berater_batchEnde DELEGIERT (nur frontmatter-Update, kein [x]-Write).
- C6 schreibt `{VAULT}/.../6_PL/{bl_id}-parking-lot.md APPEND` bei Regression (Regressions-Guard-Domain).
- ADR-F: `I_PIPELINE_STATE`-Signal-Felder (needs_tdd, handschuh_wechsel_pending) bleiben unveraendert — C9c-Domain.
