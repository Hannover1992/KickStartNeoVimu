# /_worktree_parallel — Offizieller Parallel-Weg via Worktrees (BL-431 Capstone)

```yaml
status: active
version: 1.2.0
created: 2026-06-20
updated: 2026-06-26
op: Worktree-Parallel
phase: Meta
type: doctrine
chain_position: cross-cutting
bl_history:
  - BL-431: "ID-Schema + Registry + Handoff (1-stufig, root-gebunden)"
  - BL-351: "Tiefen-Agnostik: nested Mothership, Branch-Tiefe, Nesting-Cap, dynamischer cwd"
  - BL-490: "FF-safe-gegateter Lane->develop-Seam (INV-WT-FFSAFE) + guard_branch_force_develop + Reflog-Runbook"
```

## Zweck (projekt-unabhaengiger Engine-Kanon)

Diese Doktrin ist FESTER BESTANDTEIL von OmniCommand — sie lebt in der Engine (reist mit jedem
Redeploy), NICHT im projekt-gebundenen Agent-Memory. Analog `_vehikel.md`.

BL-431 liefert den OFFIZIELLEN Weg fuer BL-Level-Parallelitaet: mehrere Backlog-Items koennen
in getrennten Git-Worktrees auf dedizierten Lanes bearbeitet werden — SEQUENZIELL innerhalb
jeder Lane, DATEI-DISJUNKT zwischen den Lanes.

**Vorbedingung (INV-WORKTREE-PARALLEL — zwingende Sequenz):** Den Parallel-Mechanismus ZUERST
seriell auf einem Terminal bauen und nach develop mergen — ERST DANN Worktree-Split starten.
Die Parallel-Maschine muss existieren bevor parallel gearbeitet wird.

---

## Kernkonzepte

### Worktree-ID-Schema: WT-{N}

Jeder Worktree erhaelt eine eindeutige ID im Schema `WT-{N}` (N = Ganzzahl ab 1).

```python
# worktree_registry.py: assign_worktree_id(existing)
assign_worktree_id({"WT-1", "WT-2"})  # -> "WT-3"  (kollisionsfrei, deterministisch)
```

IDs sind monoton aufsteigend, nie wiederverwendet waehrend einer Registry-Sitzung.

### Persistente Registry

```
{vault_root}/_worktree_registry.md      (Markdown, single-writer-geschuetzt)
```

Registry-Eintraege (In-Memory: dict wt_id -> Eintrag):

| Feld | Typ | Bedeutung |
|---|---|---|
| `path` | str | Absoluter Pfad des Worktrees (eindeutig in Registry) |
| `branch` | str | Aktueller Branch im Worktree |
| `bl_id` | str | Zugeordnetes BL-Item |
| `base_sha` | str | Git-SHA beim Erstellungszeitpunkt |
| `lane` | str | Lane-Bezeichner (z.B. "A", "B") |
| `status` | str | "active" | "merged" | "idle" |
| `vault_root` | str | Pfad zum Vault-Root |

API: `registry_add`, `registry_lookup`, `registry_remove`, `registry_list`
(alle in `.claude/scripts/worktree_registry.py`, Lock-geschuetzt via `_REGISTRY_LOCK`).

### bl_parallel-Dial

```
bl_parallel ∈ {True, False}     default: False     (orthogonal zu parallel_mode)
```

- `False` (default): Serieller Modus — ein Worktree, eine Lane, ein BL nach dem anderen.
- `True`: Parallel-Modus — mehrere Worktrees aktiv, Lane-Disjunktheit erzwungen.

Gesetzt via `session_params_resolver` (BL-431 AK-4). Bypass-Felder -> ValueError.

---

## Lebenszyklus eines Worktrees

```
1. VERGABE:    assign_worktree_id(bestehende_ids)  -> wt_id = "WT-{N}"
               validate_worktree_path(pfad)         -> ok / vault_root_required
               registry_add(reg, wt_id, ...)        -> neue Registry

2. LANE BINDEN: Lane-Bezeichner (A/B/...) dem Worktree zuweisen.
                Jeder Worktree = exakt 1 Roadmap-Lane (BL-430 ROADMAP-ORDER).
                Lanes sind DATEI-DISJUNKT: kein gemeinsames Schreiben in dieselbe Datei.

3. BL BAUEN:   Vollstaendige I-Pipeline im Worktree (A->IDF->SDF->I->Post).
               SEQUENZIELL innerhalb der Lane (kein gleichzeitiges Schreiben in Lane-Dateien).
               INV-BUILD-GRAIN gilt (M2/M3 = Step-Kette, nie monolithisch).

4. HANDOFF:    handoff(wt_id, reg, merge_fn=..., lane=lane, open_items=[...])
               -> CLEAN:    merge_seam.py nach develop (BL-425), Status -> "merged".
               -> CONFLICT: PL-Item erstellen + Hold, kein Merge auf develop.
               pick_next_lane_item(lane, open_items, claimed) -> naechstes Lane-Item oder None.

5. WEITER:     Naechstes Lane-Item binden (pick_next_lane_item, Lane-Disjunktheit sicherstellen).
               Oder: Worktree idle wenn keine weiteren Items in Lane.
```

### Lane-Disjunktheit (Kern-Invariante)

- Zwei Lanes DUERFEN NIE dieselbe Datei gleichzeitig schreiben.
- Lane-Zuschnitt folgt ROADMAP-ORDER (BL-430): Lane A = Items {i, i+2, ...}, Lane B = {i+1, i+3, ...}
  oder nach expliziter Cluster-Logik.
- `pick_next_lane_item(lane, open_items, claimed_by_other)` erzwingt Disjunktheit:
  gibt nur Items zurueck die NICHT in `claimed_by_other` sind.

---

## Handoff: CLEAN vs. CONFLICT

```python
# merge_fn wird injiziert (Testbarkeit, BL-425 Reuse):
result = handoff(wt_id, reg, merge_fn=do_merge_or_conflict, lane="A", open_items=[...])

# CLEAN  -> result["merge_executed"] == True, result["registry"][wt_id]["status"] == "merged"
# CONFLICT -> result["hold"] == True, result["conflict"] == True, result["pl_created"] == True
```

Merge-Logik liegt in `merge_seam.py` (BL-425, wiederverwendet). BL-431 liefert nur
den ID+Registry+Handoff-Rahmen — das eigentliche Git-Merge-Kommando ist merge_seam-Verantwortung.

---

## FF-safe-gegateter Lane→develop-Seam (BL-490, INV-WT-FFSAFE)

**Der Near-Miss (C's BL-451-Lauf 2026-06-25, reflog-gerettet):** `git branch -f develop roadmap-c`
verwaiste fast A's Commit `7a3337e` — develop war zwischenzeitlich via roadmap-a avanciert, der
`-f` war **nicht FF-safe** und haette die develop-only-Commits verworfen. Wurzel: die
Lane→develop-Integration lief per ad-hoc `git branch -f` auf der GETEILTEN develop, ohne die
FF-Safety zu **gaten** (nur zu pruefen).

### Doktrin (zwingend)

- **NIE** `git branch -f develop ...` / `git update-ref refs/heads/develop ...` / `git push --force`
  (auch `--force-with-lease`) / `git branch -D develop` von Hand auf der GETEILTEN develop (oder main).
  Dieselbe Disziplin gilt fuer jeden geteilten Integrations-Branch.
- **Der erzwungene Pfad** ist das FF-safe-Gate in `merge_seam.py` (BL-490):

  ```
  py -3 .claude/scripts/merge_seam.py advance --ref develop --to <lane>
  ```

  Das Gate prueft `is_ff_safe(ref, new_tip)` (= `git merge-base --is-ancestor ref new_tip`):
  FF-safe → es bewegt develop; **non-FF → es VERWEIGERT** (exit 2, `status=refused`, `reason=non_ff`)
  mit dem Hinweis, einen echten Merge statt `-f` zu nutzen. develop wird bei Verweigerung NIE bewegt
  — kein Verwaisen mehr moeglich.
- Wenn das Gate verweigert (develop ist non-FF voraus), ist ein **echter Merge** noetig
  (lane → develop, CLEAN-gegated via `merge_seam.merge_exec`/temp-worktree) — kein Force.

### Guard (strukturelle Erzwingung)

`guard_branch_force_develop.py` (PreToolUse-Hook, matcher `Bash|PowerShell`) BLOCKIERT jeden
ad-hoc Force-Move/Delete/Force-Push der geteilten Branches develop/main auf der Tool-Ebene und
verweist auf das `merge_seam advance`-Gate. Force-Moves von Lane-/Backup-Branches (roadmap-*,
backup/*) und normales git bleiben erlaubt. Kill-Switch: `OMNI_ENFORCE_ALL_OFF=1`
(bzw. `enforceProcess: false`). Analog der INV-AO-CALLER-Guard-Linie.

### Reflog-Recovery-Runbook (falls doch ein Commit verwaist)

C's Rettung als Vorlage — ein force-verwaister Commit ist via reflog vollstaendig erholbar,
solange GC ihn nicht entfernt hat (Default ~90 Tage):

```
1. FINDEN:   git reflog --all                       # alle Ref-Bewegungen, der verwaiste SHA steht hier
             git fsck --lost-found --no-reflogs      # alternativ: dangling commits auflisten
2. PRUEFEN:  git show <verwaister-SHA>                # Inhalt verifizieren (richtiger Commit?)
             git merge-base --is-ancestor <SHA> develop && echo "schon drin" || echo "fehlt"
3. RETTEN:   # develop auschecken (oder temp-worktree) und den verwaisten Commit SAUBER zurueck-mergen:
             git merge <verwaister-SHA> --no-edit     # datei-disjunkt = CLEAN; sonst conflict_to_pl + Hold
4. RE-POINT: # develop steht jetzt FF-safe — kuenftige Avancen NUR via:
             py -3 .claude/scripts/merge_seam.py advance --ref develop --to <lane>
5. VERIFY:   git merge-base --is-ancestor <SHA> develop   # exit 0 = gerettet, reachable from develop
             git log --oneline develop | grep <SHA-kurz>
```

Force-Move-Dangler-Residue (der alte, force-ueberschriebene Tip) bleibt als unreachable Objekt
liegen bis zur naechsten GC — harmlos, kein Arbeitsverlust.

---

## Tiefen-Agnostik (BL-351)

BL-431 lieferte das **flache, 1-stufige + root-gebundene** Worktree-Geruest. BL-351 macht die
Maschinerie **tiefen-agnostisch**: identisches Verhalten bei Worktree-Tiefe 0 (main-Checkout),
Tiefe 1 (Feature-Worktree) und Tiefe N (geschachtelter Worktree). Die "Mothership = main-Checkout"-
Annahme (BL-431 W4) ist verworfen.

### Kern-Konzepte

#### nested Mothership

Ein Worktree-Spawn kann aus einem Worktree starten — der Caller ist SELBST eine Mothership.
`resolve_mothership_root()` (`worktree_aware_params.py`) loest den Mothership-Root zur Laufzeit
auf via git-worktree-Topologie-Walk gegen `Path.cwd()`. Statisches `_PROJECT_ROOT` als git-cwd-
Quelle ist **abgeloest**.

```python
# worktree_aware_params.py
from_path = resolve_mothership_root()   # dynamisch: Tiefe 0 -> Repo-Root, Tiefe N -> Mothership-Worktree
```

Fallback: Registry-Feld `is_mothership` (deterministischer Cache bei Walk-Mehrdeutigkeit /
detached HEAD). Bei Walk-Fehler: lautes Fail, KEIN stilles Fallback auf falschen Root (SA-1).

#### Branch-Tiefe: Anker = Feature-Branch der Mothership

Der Worktree-Split-Anker (base) ist der **aktuelle Feature-Branch des Mothership-Worktrees**,
nicht main. Ermittelt via `get_mothership_branch()` = `_git_current_branch(cwd=resolve_mothership_root())`.

```
Mothership auf roadmap-c  ->  nested Worktree Anker = roadmap-c  (NICHT main)
Mothership auf main       ->  Anker = main  (Tiefe-0-Kompatibilitaet)
```

Das Merge-Ziel im Handoff folgt derselben Semantik: `resolve_merge_target()` liefert den
Mothership-Feature-Branch (depth > 0) oder `develop` (depth = 0, Default). NICHT `merge_seam.merge_exec`
intern geaendert — der Aufrufer setzt `merge_target` Mothership-relativ (W15, SA-3).

#### Rekursive Tiefe + Nesting-Cap

`resolve_nesting_depth()` loest die Parent-Kette rekursiv auf (statt 1-stufig / flach).
Konstante `MAX_NESTING_DEPTH = 3` in `worktree_aware_params.py` setzt den harten Cap.
`check_nesting_depth_cap(depth)` wirft **RuntimeError / exit 1** bei Ueberschreitung —
KEIN stilles Stop (SA-2, QG-4).

```python
depth = resolve_nesting_depth()       # rekursiv: 0 / 1 / 2 / 3
check_nesting_depth_cap(depth)        # lautes hart-fail bei depth > 3
```

#### Gate-C-Shadow-cwd dynamisch

Der Gate-C-Shadow-Lauf spawnt mit `cwd = resolve_mothership_root()` statt statischem
`_PROJECT_ROOT`. Alle vier bekannten git-cwd-Aufrufstellen in `worktree_aware_params.py`
(Z89/Z123/Z142/Z238) nutzen den dynamischen Resolver (SA-4, AK-3/AK-4).

### Registry-Schema-Delta (BL-351, additiv)

Drei additive Felder — bestehende flache Eintraege bleiben OHNE Migration lesbar
(graceful-Default via `registry_lookup`):

| Feld | Typ | Default (legacy) | Bedeutung |
|---|---|---|---|
| `is_mothership` | bool | `true` | Ist dieser Worktree die aktive Mothership? |
| `parent_wt_id` | str \| None | `None` | WT-ID des Parent-Worktrees (null = kein Parent) |
| `nesting_depth` | int | `0` | Rekursive Schachtelungstiefe (0 = main-Checkout) |

INV-WORKTREE-2: Die Schema-Erweiterung ist additiv — alte Eintraege werden nie ungueltig.

### 3-Tiefen-Agnostik-Testharness (AK-11)

Parametrisierter Integrationstest: derselbe Funktionsaufruf (`resolve_mothership_root` +
Branch-Anker + Tiefe-Resolver) bei Tiefe 0 / 1 / N muss **strukturell aequivalente Antworten**
liefern (gleiche Resolver-Vertraege, jeweils tiefen-korrekte Werte). Gruen = Tiefen-Agnostik
bewiesen.

---

## Neue Invarianten (BL-351)

- **INV-WT-TIEFE (Tiefen-Agnostik — Kern):** Die Worktree-Maschinerie verhaelt sich identisch
  bei Tiefe 0 (main), Tiefe 1 (Feature-Worktree) und Tiefe N (geschachtelt). Mothership-Root,
  Branch-Anker und Merge-Ziel werden IMMER zur **Laufzeit** aufgeloest — niemals statisch
  import-zeit-gebunden an `_PROJECT_ROOT`.

- **INV-WT-NESTED (nested Mothership — Annahme verworfen):** Die Annahme "Mothership = main-
  Checkout" gilt NICHT mehr. Ein Worktree-Spawn MAY aus einem Worktree starten (Mothership
  selbst = Worktree). `resolve_mothership_root()` (`worktree_aware_params.py`) ist die EINZIGE
  kanonische Quelle des Mothership-Pfads. Jede Hardcode-Referenz auf `_PROJECT_ROOT` als git-
  cwd fuer Mothership-Operationen ist ein Defekt.

- **INV-WT-CAP (Nesting-Cap — hartes Fail):** Maximale Schachtelungstiefe = `MAX_NESTING_DEPTH = 3`.
  Ueberschreitung = **lautes hart-fail** (RuntimeError / exit 1 mit Cap-Begruendung). KEIN
  stilles Stop, KEIN Durchlauf. Cap ist als Modul-Konstante in `worktree_aware_params.py`
  zentral aenderbar.

- **INV-WT-ANKER (Branch-Anker Mothership-relativ):** Der Worktree-Split-Anker und das Handoff-
  Merge-Ziel sind IMMER Mothership-Feature-Branch-relativ. `develop` als Merge-Ziel gilt
  ausschliesslich bei depth = 0. Anker-Ermittlung: `get_mothership_branch()` =
  `_git_current_branch(cwd=resolve_mothership_root())`.

---

## OUT-OF-SCOPE (BL-431 Lieferumfang)

**EXPLIZIT NICHT im Lieferumfang von BL-431:**

| Out-of-Scope | Begruendung / Folge-BL |
|---|---|
| Simultane Multi-Engine-Concurrency (Lock fuer N>=2 gleichzeitige Schreiber) | Folge-BL (scharfer Lock erfordert separate Spezifikation) |
| Remote-Push / PR-Automation | Gehoert zu Post-Pipeline, nicht zum Worktree-Rahmen |
| INNERHALB-BL-Parallelitaet (parallele Steps IN einem BL) | BL-230 (Ausbau, deferiert per heal_optimize_first) |
| Automatisches Worktree-Pruning / GC | Separate Engine-Health-Massnahme |

BL-431 liefert: **ID-Schema + Registry-CRUD + validate_path + pick_next_lane_item + handoff + Doktrin**.
Echte gleichzeitige Concurrency (N >= 2 Lanes schreiben simultan ohne Koordinationsprotokoll) ist
ein SEPARATES Problem und absichtlich ausgeklammert.

---

## Aufruf

```python
from .claude.scripts.worktree_registry import (
    assign_worktree_id,
    registry_add, registry_lookup, registry_remove, registry_list,
    validate_worktree_path,
    pick_next_lane_item,
    handoff,
)
from .claude.scripts.worktree_aware_params import (
    resolve_mothership_root,        # BL-351: dynamischer Mothership-Pfad
    resolve_nesting_depth,          # BL-351: rekursive Tiefe-Aufloesung
    check_nesting_depth_cap,        # BL-351: lautes Fail bei depth > MAX_NESTING_DEPTH
    get_mothership_branch,          # BL-351: Feature-Branch der Mothership
    resolve_merge_target,           # BL-351: Mothership-relatives Merge-Ziel
)

# --- BL-351: Tiefen-agnostische Vorbedingungen ---
mothership_root = resolve_mothership_root()     # dynamisch; Tiefe 0 -> Repo-Root
depth = resolve_nesting_depth()                 # rekursiv
check_nesting_depth_cap(depth)                  # hart-fail bei depth > 3
anker_branch = get_mothership_branch()          # Feature-Branch, NICHT main
merge_target = resolve_merge_target(depth)      # develop bei depth=0, Feature-Branch sonst

# --- BL-431: ID + Registry ---
wt_id = assign_worktree_id(registry_list(reg))  # -> "WT-1" bei leerer Registry
check = validate_worktree_path("/pfad/OmniCommand-worktree-A")
reg = registry_add(
    reg, wt_id, path=..., branch=..., bl_id="BL-999",
    base_sha="abc123", lane="A", status="active", vault_root=...,
    # BL-351 additive Felder:
    is_mothership=False, parent_wt_id="WT-0", nesting_depth=depth,
)

# Nach BL-Done: Mothership-relatives Merge-Ziel uebergeben
result = handoff(wt_id, reg, merge_fn=my_merge_fn, lane="A", open_items=["BL-1000"],
                 merge_target=merge_target)  # BL-351: explizit, nicht hart develop
```

## Invarianten (Kurzfassung)

- **INV-WT-1:** Jede Worktree-ID ist eindeutig und wird nicht wiederverwendet.
- **INV-WT-2:** Jeder Pfad ist eindeutig in der Registry (registry_add wirft ValueError).
  Schema-Erweiterungen sind IMMER additiv — alte Eintraege bleiben ohne Migration lesbar.
- **INV-WT-3:** Lane-Disjunktheit ist strukturell erzwungen (pick_next_lane_item).
- **INV-WT-4:** bl_parallel=False ist der sichere Default (opt-in, kein Versehen).
- **INV-WT-5 (Sequenz-Vorbedingung):** Parallel-Mechanismus ZUERST seriell bauen + mergen,
  DANN Worktree-Split. Kein Split vor existierender Maschine.
- **INV-WT-TIEFE (Tiefen-Agnostik):** Identisches Verhalten bei Tiefe 0/1/N. Alle
  Mothership-Pfad-, Branch- und Tiefe-Aufloesungen IMMER zur Laufzeit via
  `resolve_mothership_root()` / `resolve_nesting_depth()` — niemals statisch _PROJECT_ROOT.
- **INV-WT-NESTED (nested Mothership):** "Mothership = main-Checkout"-Annahme verworfen.
  `resolve_mothership_root()` ist die EINZIGE kanonische Quelle. Jede Hardcode-Referenz
  auf `_PROJECT_ROOT` als git-cwd fuer Mothership-Operationen ist ein Defekt.
- **INV-WT-CAP (Nesting-Cap):** MAX_NESTING_DEPTH=3. Ueberschreitung = lautes hart-fail
  (RuntimeError / exit 1). Kein stiller Stop, kein Durchlauf.
- **INV-WT-ANKER (Branch-Anker):** Split-Anker + Merge-Ziel = Mothership-Feature-Branch.
  `develop` als Merge-Ziel nur bei depth=0. Anker via `get_mothership_branch()`.
- **INV-WT-FFSAFE (BL-490, Lane→develop nie ad-hoc force):** Die GETEILTE develop (und jeder
  geteilte Integrations-Branch) wird NIE per Hand force-bewegt/-geloescht/-gepusht. Avancen NUR
  ueber das FF-safe-Gate `merge_seam.py advance --ref develop --to <lane>` (non-FF → refuse,
  kein Verwaisen). Strukturell erzwungen durch `guard_branch_force_develop.py` (PreToolUse
  `Bash|PowerShell`). Reflog-Recovery-Runbook s.o.

## Verwandte

- `.claude/scripts/worktree_registry.py` — Registry-Implementierung (BL-431 batch_1); Schema-Delta (BL-351 batch_2)
- `.claude/scripts/worktree_aware_params.py` — Tiefen-agnostische Resolver (BL-351): `resolve_mothership_root`, `resolve_nesting_depth`, `check_nesting_depth_cap`, `get_mothership_branch`, `resolve_merge_target`
- `.claude/scripts/merge_seam.py` — Merge-Logik (BL-425, wiederverwendet via handoff); Aufrufer setzt merge_target Mothership-relativ (BL-351 AK-6); FF-safe-Gate `advance`/`is_ff_safe`/`advance_ref_ff_safe` (BL-490)
- `.claude/scripts/guard_branch_force_develop.py` — PreToolUse-Guard gegen ad-hoc Force-Move/-Delete/-Push der geteilten develop/main (BL-490, INV-WT-FFSAFE)
- `.claude/scripts/session_params_resolver.py` — bl_parallel-Param (BL-431 AK-4)
- CLAUDE.md INV-WORKTREE-PARALLEL — Sequenz-Vorbedingung (Kurzanker, laedt jede Session)
- BL-430 — Roadmap-Executor (Lane-Order-Quelle)
- BL-429 — 3-Wege-Routing (Vorbedingung zu BL-431)
- BL-351 — Tiefen-Agnostik (nested Mothership, Nesting-Cap, Branch-Anker, Gate-C-Shadow-cwd)

## cwd-Lockout Recovery (manuelle Worktrees, BL-471)

**Symptom:** Bei manuell angelegten Worktrees (oder einem relativen `cd` in einen Unterordner,
z.B. `cd .claude/scripts`) konnte vor BL-471 die GESAMTE Toolchain ausgesperrt werden
(cwd-Lockout). Wurzel: die PreToolUse/PostToolUse/Stop/Notification-Hook-Commands in
`.claude/settings.json` waren cwd-RELATIV formuliert (`py -3 .claude/scripts/<guard>.py`).
Der Hook-Shell-Prozess startet im aktuellen Arbeitsverzeichnis — sobald die cwd NICHT der
Worktree-Root war, loesten die relativen Pfade `.claude/scripts/...` ins Leere
(FileNotFound). Da diese Hooks load-bearing PreToolUse-Guards sind (das Immunsystem),
brach damit jeder Tool-Call ab: ein vollstaendiger Toolchain-Lockout.

**Recovery (manueller Sofort-Ausweg, falls man doch in den Lockout geraet):**
Session-Neustart im Worktree-Root — eine neue Session starten mit korrektem cwd
(dem Worktree-/Repo-Root, in dem `.claude/settings.json` liegt). Mit korrekter cwd
loesen auch cwd-relative Pfade wieder auf und die Hooks feuern normal.
Vgl. das Recovery-Memo [[feedback_cwd_lockout_recovery]] (NIE `cd` in `.claude/scripts`).

**Seit BL-471 strukturell behoben:** Alle 56 Hook-Commands in `.claude/settings.json`
sind jetzt `$CLAUDE_PROJECT_DIR`-ABSOLUT formuliert
(`py -3 "$CLAUDE_PROJECT_DIR/.claude/scripts/<guard>.py"`). `$CLAUDE_PROJECT_DIR` wird vom
Hook-Shell-Mechanismus auf den Projekt-/Worktree-Root expandiert — cwd-UNABHAENGIG.
Ein relativer `cd` in einen Unterordner kann die Hook-Pfad-Aufloesung damit NICHT mehr
brechen; der cwd-Lockout-Vektor ist geschlossen.
