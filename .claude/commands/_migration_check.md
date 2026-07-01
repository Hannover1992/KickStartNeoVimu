---
type: satellite
status: active
version: 1.0.0
created: 2026-06-21
op: Migration-Readiness-Check
phase: Meta
chain_position: standalone
bl: BL-253
lane: LANE-C
---

# /_migration_check — Pre-Migration Readiness Gate

**Zweck:** Prueft ob der aktuelle Worktree zwischen abgeschlossenen BLs sicher
auf eine andere Maschine migriert werden kann (SSH-Server <-> Laptop). Aggregiert
5 Checks zu einem READY/NOT_READY-Verdict. Einzusetzen VOR jedem Maschinen-Wechsel
und nach jedem BL->DONE als Abschluss-Checkpoint.

Gebaut in BL-253 (Workflow-Resilienz: Maschinen-Interruption + Resume-Fragilitaet).

---

## Aufruf

```
/_migration_check
```

Das Command ist ein Hinweis-Skill ohne Parameter. Der eigentliche Check laeuft ueber
das CLI-Script:

```bash
py -3 .claude/scripts/migration_readiness.py --repo . --json
```

| Flag | Default | Beschreibung |
|------|---------|-------------|
| `--repo PATH` | `.` | Repo-Pfad (Worktree-Root) |
| `--vault-root PATH` | auto (resolve_vault_root) | Vault-Pfad-Override |
| `--json` | human-output | JSON-only auf stdout |

**Exit-Codes:**
- `0` = READY — Maschinen-Wechsel sicher
- `1` = NOT_READY — mindestens 1 blockender Check rot

**Beispiele:**
```bash
# Standard: prueft . als Repo, Vault via resolve_vault_root
py -3 .claude/scripts/migration_readiness.py --repo . --json

# Mit explizitem Vault-Pfad
py -3 .claude/scripts/migration_readiness.py \
  --repo C:/Users/hanno/RiderProjects/OmniCommand-wtC \
  --vault-root "C:/Users/hanno/Documents/Work/Wissen/Berechtigung/OmniCommand/OmniCommand" \
  --json

# Human-lesbarer Output (ohne --json)
py -3 .claude/scripts/migration_readiness.py --repo .
```

---

## VERTRAG

```
+=======================================================================+
| COMMAND: /_migration_check                                            |
+=======================================================================+
|                                                                       |
| ACTOR: Team Lead / Architekt (manuell vor Maschinen-Wechsel)         |
|                                                                       |
| LIEST:                                                                |
|   .claude/scripts/migration_readiness.py  (Check-Implementierung)    |
|   git status --porcelain          (C1 + C4: uncommitted + untracked) |
|   git rev-list @{u}..HEAD         (C2: unpushed Commits)             |
|   lane_develop_sync.ahead_behind  (C3: Lane-Divergenz, DRY-Reuse)    |
|   {vault_root}/.git               (C5: Vault-Versionierungs-Status)  |
|                                                                       |
| SCHREIBT: NICHTS (read-only gate)                                     |
|                                                                       |
| INVARIANTEN:                                                          |
|   INV-MC-1: Kein Push/Commit durch dieses Tool — reine Pruefung      |
|   INV-MC-2: AK-S2 (Commit/Push-Disziplin) ist Standing-Rule —       |
|             muss MANUELL eingehalten werden (Tool prueft nur Zustand) |
|   INV-MC-3: C5 (Vault) ist teil-gated: Vault ohne .git ist WARN,    |
|             kein hartes Fail (AK-VAULT-VERSIONIERUNG = GATED bis     |
|             Owner-Entscheid git-init vs Obsidian-Sync, PL-253-09)    |
|   INV-MC-4: Produkt-Heuristik in C4 = .py-Dateien; .md-Dateien      |
|             (Doku, Backlog) werden ignoriert                          |
+=======================================================================+
```

---

## Die 5 Checks (C1-C5)

### C1 — Uncommitted Working-Tree

**Was:** `git status --porcelain` — zaehlt alle Zeilen (modified, staged, untracked).

**GREEN wenn:** count == 0 (leerer Output). Harte 0-Schwelle, keine WARN-Thresholds.

**Bedeutung:** Kein Work-in-Progress verloren beim Wechsel. Vor Migration immer
committen oder stashen.

**Typische Ursache fuer RED:** laufende BL-Arbeit noch nicht committed. Fix: commit
+ push oder explizit stashen (Stash geht bei Maschinen-Wechsel verloren — lieber committen).

---

### C2 — Unpushed Commits

**Was:** `git rev-list --count @{u}..HEAD` — Commits die lokal existieren, aber
noch nicht beim Remote (origin) liegen.

**GREEN wenn:** ahead_of_remote == 0.

**Sonderfall:** Kein Upstream konfiguriert -> `no_upstream`-Marker, wird als RED
behandelt (kein stiller Crash).

**Bedeutung:** Auch committed Code ist verloren wenn er nicht gepusht ist und die
Maschine nicht mehr erreichbar ist. Ein Commit ohne Push ist kein Checkpoint.

**Fix:** `git push` (oder `git push -u origin <branch>` wenn noch kein Upstream).

---

### C3 — Lane-Divergenz ggue. develop

**Was:** Nutzt `lane_develop_sync.ahead_behind()` + `develop_sync_action()` (DRY-Reuse,
kein Re-Implement). Prueft ob die aktuelle Lane mit develop in-sync ist.

**GREEN wenn:** `develop_sync_action(ahead, behind) == "in-sync"`.

**Moegliche Aktionen:**
- `in-sync` — GREEN, kein Handlungsbedarf
- `merge` — Lane ahead (eigene Commits, develop kannte sie nicht) → erst mergen/PR
- `pull-first` — develop hat neue Commits, Lane ist hinterher → erst pullen
- `diverged` — beide Seiten haben Commits → Abstimmung noetig

**Bedeutung:** Auf der neuen Maschine muss der gleiche Branch + State vorhanden sein.
Wenn Lane und develop divergiert sind, muss das vor dem Wechsel aufgeloest werden.

---

### C4 — Untracked Produkt-Dateien

**Was:** `git status --porcelain` `??`-Zeilen, gefiltert auf `.py`-Endung.

**GREEN wenn:** keine untracked `.py`-Dateien (leere untracked_products-Liste).

**Heuristik:** `.py`-Dateien = Produkt-Code (Scripts, Tests). `.md`, `.json`, etc.
werden ignoriert (Doku/Config ohne Laufzeit-Bedeutung). Regression-Fixture:
`build_retrieval_index.py` (BL-242) wuerde hier gefangen.

**Bedeutung:** Untracked Produkt-Code existiert weder im Repo noch beim Remote —
er geht beim Maschinen-Wechsel verloren. Solcher Code muss erst committed + gepusht werden.

**Fix:** `git add <datei> && git commit -m "..." && git push`.

---

### C5 — Vault-Sync-Status (teil-gated)

**Was:** Prueft ob `{vault_root}/.git` existiert und ob der Vault sauber ist.

**Drei Zustaende:**
- `vault_not_versioned` — kein `.git` im Vault → `warn=True, blocking=False`
  (Migration wird NICHT geblockt, aber Vault-Content geht verloren wenn Sync fehlt)
- `clean` — Vault git-versioniert + sauber → GREEN
- `dirty` — Vault git-versioniert + unsaved Changes → RED, `blocking=True`

**HINWEIS — GATED (PL-253-09):** Der Vault (`Documents/OmniCommand`) ist aktuell
NICHT git-versioniert. Owner-Entscheid steht aus:
- Option A: `git init` im Vault-Root (250+ .md, .gitignore-Strategie, Remote-Wahl)
- Option B: Obsidian-Sync als Versionierungs-Ersatz verifizieren/dokumentieren

Bis zum Entscheid liefert C5 `vault_not_versioned` als WARN (nicht blockend).
Der Vault-Inhalt liegt dabei in der Verantwortung des Owners (manuelles Backup/Sync
vor Wechsel empfohlen).

**Bedeutung:** Vault-Inhalte (Backlog, Spec, PL, Model) beschreiben den Zustand aller
BLs. Ohne Versionierung oder Sync koennen geplante/laufende BL-Beschreibungen verloren gehen.

---

## Commit/Push-Disziplin an BL-Grenzen (AK-S2 — Standing Rule)

**Regel: 1 BL-Abschluss = 1 Migrations-Checkpoint.**

Wenn ein BL auf DONE gesetzt wird, MUESSEN folgende 3 Schritte ausgefuehrt werden —
in dieser Reihenfolge — bevor die Maschine gewechselt wird:

```
SCHRITT 1: Repo commit + push
  git add <relevante-Dateien>
  git commit -m "BL-{NNN}: {Titel} (DONE)"
  git push

SCHRITT 2: Vault commit/sync
  IF Vault git-versioniert:
    cd {vault_root}
    git add .
    git commit -m "BL-{NNN}: Backlog-Update (DONE)"
    git push
  ELSE (Obsidian-Sync):
    Sicherstellen dass Obsidian-Sync alle Aenderungen uebertragen hat
    (BL-Spec, Model, PL-Items, BL-Frontmatter-Status-Update)

SCHRITT 3: Readiness pruefen
  py -3 .claude/scripts/migration_readiness.py --repo . --json
  → exit 0 = alle 3 Schritte erfolgreich abgeschlossen
  → exit 1 = noch offen, vor Wechsel beheben
```

**Warum nach JEDEM BL?** Ein BL-Abschluss ohne Push-Checkpoint erzeugt stille
Luecken: auf der neuen Maschine fehlen die letzten Commits, der Vault ist out-of-sync,
oder untracked Produkt-Code ist verloren. Resume wird fragil (BL-253-Wurzel-Problem).

**Nicht gueltig:** „Ich pushe erst am Ende des Tages." Jedes BL->DONE ist ein
semantischer Checkpoint — nicht nur ein zeitlicher.

---

## Repo <-> Vault-Konsistenz (AK-S4 — Standing Rule)

**Regel: Kein BL-Produkt-Code lokal-untracked.**

Jede `.py`-Datei die zu einem BL-Ergebnis gehoert MUSS committed + gepusht sein
bevor das BL auf DONE gesetzt wird. C4 des Readiness-Checks erzwingt das maschinell.

**Warum .py und nicht .md?** `.py`-Dateien sind Laufzeit-Artefakte (Scripts, Tests,
Guards). Eine fehlende `.py` bricht andere Scripts oder laesst Tests verschwinden.
`.md`-Dateien (Doku, Daten) sind via Vault separat synchronisiert.

**Gilt auch fuer Test-Dateien:** `test_*.py` sind ebenfalls Produkt — RED-Worker-Output
ist genau so commit-pflichtig wie der GREEN-Worker-Output.

---

## Vollstaendige JSON-Ausgabe (Referenz)

```json
{
  "migration_ready": true,
  "verdict": "READY",
  "checks": {
    "c1": {"green": true, "count": 0},
    "c2": {"green": true, "ahead_of_remote": 0},
    "c3": {"green": true, "action": "in-sync"},
    "c4": {"green": true, "untracked_products": []},
    "c5": {
      "status": "vault_not_versioned",
      "green": false,
      "warn": true,
      "blocking": false
    }
  },
  "red_checks": []
}
```

**Anmerkung C5:** Im obigen Beispiel ist C5 `green=false` (Vault nicht versioniert),
aber `blocking=false` → daher `migration_ready=true` und `red_checks=[]`. Das ist
das erwartete Verhalten solange AK-VAULT-VERSIONIERUNG (PL-253-09) noch GATED ist.

**NOT_READY Beispiel (C1 + C4 rot):**
```json
{
  "migration_ready": false,
  "verdict": "NOT_READY",
  "checks": {
    "c1": {"green": false, "count": 3},
    "c4": {"green": false, "untracked_products": [".claude/scripts/new_feature.py"]}
  },
  "red_checks": ["c1", "c4"]
}
```

---

## Ablauf (typischer BL-Abschluss-Flow)

```
SCHRITT 0: BL-Implementierung abgeschlossen (alle AKs GREEN)

SCHRITT 1: Repo-Commit + Push
  git add .claude/scripts/<neue-dateien>.py
  git commit -m "BL-{NNN}: {Titel} DONE"
  git push
  → pruefe: C1 = 0 uncommitted, C2 = 0 unpushed

SCHRITT 2: Vault synchronisieren
  Backlog-Frontmatter BL-{NNN} status -> DONE updaten
  Obsidian-Sync abwarten ODER git commit/push im Vault

SCHRITT 3: Readiness-Gate ausfuehren
  py -3 .claude/scripts/migration_readiness.py --repo . --json
  → exit 0 = Checkpoint sauber, Maschinen-Wechsel erlaubt
  → exit 1 = Beheben (red_checks lesen, C1/C2/C3/C4 fixen)

SCHRITT 4: BL-Abschluss im Backlog dokumentieren (/_finish)
  Erst NACH exit 0 vom Readiness-Check.
```

---

## Integration

**Aufrufer (idiomatisch):**
- Manuell vor jedem Maschinen-Wechsel (SSH <-> Laptop)
- Als Pflicht-Schritt nach `/_finish` (BL->DONE)
- Im Pre-PR Check (`/_Pre_PR`) — verhindert unveroeffentlichten Produkt-Code

**Verwandte Commands:**
- `/_finish` — BL-Abschluss-Flow (enthaelt Hinweis auf diesen Check)
- `/_branch_health` — Branch-Hygiene (komplementaer: Repo-Health)
- `/_sanity_check` — Engine-Definitionen-Audit (orthogonal: prueft Skills, nicht State)
- `/_stage_sanity_check` — Stage-Level-Check (Scope: Stage-Konsistenz, nicht Migration)

**Script-Verwandtschaft:**
- `.claude/scripts/migration_readiness.py` — Implementierung (BL-253 batch_1)
- `.claude/scripts/lane_develop_sync.py` — C3 DRY-Reuse (ahead_behind / develop_sync_action)
- `.claude/scripts/resolve_vault_root.py` — Vault-Pfad-Resolver (C5 + CLI-Default)

---

## ANTI-PATTERN (PFLICHT vermeiden)

**Maschinen-Wechsel ohne Check:**
```
VERBOTEN: Laptop aufklappen, weiterarbeiten -> "fehlt was? schauen wir"
RICHTIG : exit 0 aus migration_readiness.py ist die Eintrittsbedingung
```

**Commit ohne Push als Checkpoint:**
```
VERBOTEN: "ist committed, das reicht"
RICHTIG : C2 prueft push — committed != gepusht; exit 1 solange ahead_of_remote > 0
```

**Vault als "nur Doku" ignorieren:**
```
VERBOTEN: Nur Repo pushen, Vault-Sync vergessen
RICHTIG : BL-Spec + Model + PL sind BL-Content — verloren = kein Resume moeglich
```

**Exit-Code ignorieren:**
```
VERBOTEN: JSON lesen, "sieht OK aus" — Script-Output ignorieren
RICHTIG : exit $? als Gate — exit 0 = READY, exit 1 = NOT_READY (blocking=false-Felder korrekt)
```

---

## CHANGELOG

### v1.0.0 (2026-06-21) — Initial (BL-253 batch_2 AK-DOKU-PUSH-DISZIPLIN)
- Command-Skill fuer migration_readiness.py (BL-253 batch_1)
- 5 Checks (C1-C5) erklaert + Commit/Push-Disziplin (AK-S2) als Standing-Rule
- Repo<->Vault-Konsistenz (AK-S4) dokumentiert
- AK-VAULT-VERSIONIERUNG (C5 GATED, PL-253-09) hingewiesen
- Vollstaendige JSON-Shape-Referenz + NOT_READY-Beispiel

---

ARGUMENTS: $ARGUMENTS
