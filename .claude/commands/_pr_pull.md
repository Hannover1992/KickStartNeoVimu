---
name: _pr_pull
status: active
version: 1.0.0
type: satellite
op: PrInquiry
created: 2026-06-09
feature_anchor: BL-296
related:
  - _pr_init
  - _pr_question_answer_sim
  - _R_orchestrate
  - _pr_orchestrate
tier: sonnet
---

# /_pr_pull

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_pr_pull                                                  ║
╠══════════════════════════════════════════════════════════════════════╣
║  ZWECK:                                                              ║
║    AK1: Holt PR-Kommentare/Threads via parametrisiertem fetch.ps1,  ║
║    normiert auf kanonisches comments[]-Schema (1 Kommentar = 1      ║
║    Frage), schreibt review-{prId}-queue.md im _R_orchestrate-Format ║
║    (dateibasierter Seam). KEIN Neubau der REST-/Auth-Schicht.       ║
║                                                                      ║
║  LIEST:                                                              ║
║    .claude/meta/pr/active-pr.json      (PrId, prUrl, platform)      ║
║    .claude/meta/pr/routing.json        (platform, pathPrefix,        ║
║                                         tfs_compat, urls.api)       ║
║    .claude/analysis/pr-{id}-raw.json   (fetch.ps1-Output, nach      ║
║                                         SCHRITT 2)                  ║
║    Echter Repo-Code via Read-Tool      (Code-Anker pro Queue-Item)  ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/analysis/pr-{id}-raw.json   (via fetch.ps1)              ║
║    .claude/analysis/pr-{id}-state.json (comments[]-Normierung)      ║
║    .claude/review-{prId}-queue.md      (Queue fuer _R_orchestrate)  ║
║                                                                      ║
║  RUFT:                                                               ║
║    fetch.ps1 -PrId {id} -PathPrefix {aus routing.json}             ║
║              (KEIN Neubau; parametrisiert statt hardcoded)          ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    INV-PR-PULL-1: NIE hardcodierter Skript-Pfad oder PrId           ║
║    INV-PR-PULL-2: 1 aktiver Comment = GENAU 1 Queue-Item            ║
║    INV-PR-PULL-3: Queue-Datei PHYSISCH schreiben VOR _R_orchestrate ║
║    INV-PR-PULL-4: Filter status==active AND threadContext!=null      ║
║    INV-PR-PULL-5: NIE Reviewer-Content paraphrasieren               ║
║    INV-PR-PULL-6: disposition_owed (active ∧ last_word=reviewer) =   ║
║                   primaeres Work-Set + Einstiegspunkt; nur owed an   ║
║                   _R_orchestrate/answer_sim. last_word = Author des  ║
║                   LETZTEN Thread-Kommentars (nicht is_my_response)   ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_pr_pull
```

Keine eigenen Argumente — PrId und Plattform kommen ausschliesslich aus
`.claude/meta/pr/active-pr.json` (gesetzt von `/_pr_init`).

**Voraussetzung:**

`/_pr_init {link}` muss zuvor gelaufen sein. Falls `active-pr.json` fehlt:

```
[PR_PULL] FEHLER: active-pr.json nicht gefunden.
Recovery: Rufe /_pr_init {link} auf.
```

**Position in der Chain:**

```
/_pr_init  →  /_pr_pull  →  /_R_orchestrate PR-{id} normal  →  /_pr_question_answer_sim  →  ...
```

---

## Reuse-Karte (KEIN Greenfield)

| Komponente | Quelle | Was wiederverwendet wird |
|------------|--------|--------------------------|
| `fetch.ps1` | `{DCSRE}/.claude/scripts/pr/fetch.ps1` | REST-Threads-Abruf (GET pullRequests/{id}/threads), Filter status=active + threadContext, raw.json-Erzeugung — NUR parametrisiert (NEU: -PathPrefix statt hardcoded '/Sources/Backend/') |
| `_common.ps1` | `{DCSRE}/.claude/scripts/pr/_common.ps1` | `Get-AuthHeaders`, `Resolve-PrId`, `Get-StateFile`, `Get-ThreadsApiUrl` (abstrakt, Azure/TFS-agnostisch) — dot-source, kein Neubau |
| `pr-{id}-raw.json` | fetch.ps1-Output | Kanonisches Comment-Datenformat (ThreadId, TfsStatus, File, Line, Author, Content, IsMyResponse) — 1:1 uebernommen als Mapping-Quelle |
| Queue-Format | `_R_orchestrate.md` Zeilen 751-806 | `## Item N:` / `**Datei:**` / `**Zeilen:**` / `**Frage:**` / `**Code:**` — EXAKT dieses Format wird produziert (Seam-Kompatiblitaet) |
| `active-pr.json` + `Resolve-PrId` | `_pr_init` | `OverridePrId > active-pr.json` — gelesen, nie geschrieben in diesem Skill |

**NEUE Seams (nicht in bestehender Infra):**

- `pr-{id}-state.json comments[]` — Normierungs-Schema (id/thread_id/file/line/text/reviewer_name/is_my_response/status)
- `review-{prId}-queue.md` — physische Queue-Datei als dateibasierter Seam zu `_R_orchestrate`
- `-PathPrefix`-Parametrisierung in fetch.ps1 (minimaler Eingriff, Zeile mit hardcoded '/Sources/Backend/' ersetzen)

---

## Ablauf

### SCHRITT 0 — Entry-Log + Resolve-PrId

```
[PR_PULL] Start. Lese active-pr.json ...
PrId={id}, platform={azure-devops|tfs_compat}, prUrl={url}

Falls active-pr.json fehlt oder leer:
  → FEHLER + Recovery-Hint (siehe Aufruf-Sektion oben)
  → Exitcode 1
```

Resolve-PrId-Mechanismus (aus `_common.ps1`):

```
Prioritaet: OverridePrId-Arg > active-pr.json.prId > einzige pr-{id}-state.json
```

### SCHRITT 1 — Platform-Routing

```
Lese routing.json:
  platform   = routing.json.platform          ("azure-devops" | "tfs_compat")
  pathPrefix = routing.json.pathPrefix        (leer = kein Stripping, INV-PR-PULL-1)
  apiBase    = routing.json.urls.api

Get-ThreadsApiUrl (aus _common.ps1) ist bereits abstrakt:
  Azure:      {apiBase}/{org}/{project}/_apis/git/repositories/{repo}/pullRequests/{id}/threads
  TFS-compat: {apiBase}/{collection}/{project}/_apis/git/repositories/{repo}/pullRequests/{id}/threads

→ KEIN manuelles URL-Bauen; _common.ps1 kapselt die Differenz.
```

### SCHRITT 2 — fetch.ps1 ausfuehren

```powershell
# Skript-Pfad aus routing.json.paths.scriptsDir (kein Hardcode, INV-PR-PULL-1)
$scriptDir = (Get-Content .claude/meta/pr/routing.json | ConvertFrom-Json).paths.scriptsDir
& "$scriptDir\fetch.ps1" -PrId $prId -PathPrefix $pathPrefix

# Ergebnis: .claude/analysis/pr-{id}-raw.json
# Exitcode 0 = OK; 1 = Auth-Fehler; 2 = PR nicht gefunden
```

Bei Exitcode != 0:

```
[PR_PULL] WARN: fetch.ps1 Exitcode={n}.
  0 → OK
  1 → Auth-Fehler: credential-Key in routing.json pruefen (auth.credentialKey)
  2 → PR nicht gefunden: PrId pruefen in active-pr.json
Exitcode 1 (WARN, kein Hard-Fail wenn raw.json bereits existiert)
```

### SCHRITT 3 — raw.json normieren → comments[]

Lese `.claude/analysis/pr-{id}-raw.json`.

**Filter (INV-PR-PULL-4):**

```
Behalte nur Comments wo:
  TfsStatus == "active"
  UND threadContext != null   (threadContext = Datei/Zeilen-Anker)
  UND Content nicht leer

NICHT herausfiltern: IsMyResponse == true
  → Diese bleiben in der Queue, werden aber als disposition_owed=false markiert (s. Triage)
```

**Antwort-geschuldet-Triage (INV-PR-PULL-6 — der Einstiegspunkt):**

Der primäre Work-Set ist NICHT "alle aktiven Threads", sondern die, **bei denen WIR nicht das
letzte Wort haben** (= eine Antwort ist geschuldet). Pro Thread berechnen:

```
# "letztes Wort" = Author des LETZTEN Kommentars im Thread (nicht "habe ich irgendwann geantwortet").
# Quelle: das letzte Element in thread.comments[] (chronologisch). IsMyResponse ist nur ein
# Fallback-Signal, NICHT die Wahrheit — der Reviewer kann NACH meiner Antwort ERNEUT kommentiert
# haben (dann habe ich NICHT das letzte Wort, obwohl IsMyResponse irgendwann true war).
last_comment   = thread.comments[-1]                       # letzter Kommentar im Thread
last_word      = (last_comment.Author.displayName == committer.displayName) ? "committer" : "reviewer"
disposition_owed = (TfsStatus == "active") AND (last_word == "reviewer")

# committer.displayName kommt aus active-pr.json (gesetzt von _pr_init, auth.myDisplayName).
```

Klassen:
- **`disposition_owed = true`** (active ∧ last_word=reviewer): **Antwort geschuldet → PRIMÄRES Work-Set,
  zuerst in der Queue.** Nur DIESE bekommen in `_pr_question_answer_sim` eine sim-Antwort.
- **`disposition_owed = false`, last_word=committer** (wir haben zuletzt geantwortet): getrackt, aber
  KEINE neue sim-Antwort (Disposition `already-answered` im Findings-Tripel).
- **status != active** (resolved/closed): getrackt als `resolved`, kein Inquiry-Cycle.

**Normierung pro Comment:**

```json
{
  "id": "{ThreadId}",
  "thread_id": "{ThreadId}",
  "file": "{threadContext.filePath}",
  "line": {threadContext.rightFileStart.line},
  "text": "{Content — @-Mentions gestrippt, SONST WOERTLICH, INV-PR-PULL-5}",
  "reviewer_name": "{Author.displayName}",
  "is_my_response": {IsMyResponse},
  "last_word": "committer|reviewer",
  "disposition_owed": true,
  "status": "pending"
}
```

`last_word` + `disposition_owed` werden pro Thread nach der Triage (INV-PR-PULL-6) gesetzt —
sie steuern, welche Items `_pr_question_answer_sim` tatsächlich beantwortet (nur `disposition_owed=true`).

**@-Mention-Stripping:**

```
Content.replace(/@\w[\w.]*/, "").trim()
→ "@Patryk.Krzyzanski bitte korrigieren" → "bitte korrigieren"
→ Inhalt SONST UNVERAENDERT (INV-PR-PULL-5)
```

Schreibe Ergebnis in `.claude/analysis/pr-{id}-state.json` Feld `comments[]`
(MERGE, nicht Overwrite — bestehende Felder bleiben erhalten).

### SCHRITT 4 — Queue bauen (owed zuerst)

**Reihenfolge:** zuerst alle `disposition_owed=true` (das Primär-Work-Set = der Einstiegspunkt),
dann — getrennt unter `## TRACKED (nicht im Inquiry-Cycle)` — die non-owed (already-answered/resolved)
nur als 1-Zeilen-Referenz (ThreadId + Grund), OHNE Code-Anker. Nur die owed-Items gehen an
`_R_orchestrate` + `_pr_question_answer_sim`.

Pro **owed** Comment aus `comments[]` (disposition_owed=true):

```
## Item {N}: {ThreadId}-{AuthorKurz}
```

wobei `AuthorKurz` = erster Nachname oder letztes Segment aus `reviewer_name`
(z.B. "Muster" aus "Max Muster", "Krzyzanski" aus "Patryk.Krzyzanski").

**Pflicht-Felder pro Queue-Item (exakt _R_orchestrate-Format, Zeilen 755-766):**

```markdown
## Item {N}: {ThreadId}-{AuthorKurz}

**Datei:** {file}
**Zeilen:** {line-10}-{line+10}
**Frage:** {text}

```{sprache}
{Code-Snippet ca. 50 Zeilen via Read-Tool, zentriert um line}
```
```

**Optionales Feld:**

```markdown
**Uncle Bob Focus:** {nur setzen wenn Reviewer-Kommentar eindeutig auf Clean-Code-Prinzip zeigt}
```

**Code-Anker via Read-Tool:**

```
offset = max(0, line - 25)
limit  = 50
Lese {file} mit offset={offset}, limit={limit}
→ Snippet als Code-Block (Sprache aus Dateiendung ableiten: .cs→csharp, .ts→typescript, usw.)
Falls Datei nicht lesbar (Pfad fehlt, Permission):
  → Code-Block leer lassen mit Kommentar "// Datei nicht lesbar: {file}"
  → Kein Hard-Fail (WARN + weiter)
```

**Queue-Datei-Header:**

```markdown
# Review Queue -- PR-{id} (PENDING)

<!-- Erzeugt von /_pr_pull {datum} | {OWED} geschuldet / {TRACKED} getrackt von {N} aktiv | platform={platform} -->
```

### SCHRITT 5 — Queue-Datei schreiben

Schreibe `.claude/review-{prId}-queue.md` (INV-PR-PULL-3 — physisch schreiben
VOR jedem Aufruf von `_R_orchestrate`; _R_orchestrate liest ausschliesslich Dateien).

Falls Datei bereits existiert: UEBERSCHREIBEN (frischer Pull ersetzt alte Queue).

### SCHRITT 6 — Exit-Log

```
[PR_PULL] {N} Kommentare normiert → .claude/analysis/pr-{id}-state.json (comments[])
[PR_PULL] Queue geschrieben: .claude/review-{prId}-queue.md ({N} Items)
[PR_PULL] Naechster Schritt: /_R_orchestrate PR-{id} normal
Exitcode 0
```

Bei N == 0 (keine aktiven Kommentare):

```
[PR_PULL] WARN: 0 aktive Kommentare in pr-{id}-raw.json (alle gefiltert oder PR leer).
[PR_PULL] Queue NICHT geschrieben (kein _R_orchestrate-Input verfuegbar).
Exitcode 1
```

---

## Invarianten

**INV-PR-PULL-1 — Kein Hardcode (Azure-Agnostizitaet)**

NIE PrId, Skript-Pfad oder API-URL hardcodieren. Alle Werte kommen aus:
- `active-pr.json` (PrId, platform)
- `routing.json` (pathPrefix, urls.api, paths.scriptsDir)
- `_common.ps1` Get-ThreadsApiUrl (API-URL-Abstraktion)

Verletzt: alter pr-init.md-Hardcode (`PrId=18979`, fester DCSRE-Pfad) — NICHT wiederholen.

**INV-PR-PULL-2 — 1:1 Mapping**

1 aktiver Comment = GENAU 1 Queue-Item. KEINE Gruppierung nach Theme oder Datei
(anders als `pr-planning.md`). BL-296 braucht 1:1 Frage-Mapping fuer
den Inquiry-Cycle (jeder Kommentar = eigene Hypothese).

**INV-PR-PULL-3 — Physischer Seam**

`.claude/review-{prId}-queue.md` MUSS physisch auf Disk existieren BEVOR
`_R_orchestrate` gerufen wird. `_R_orchestrate` liest nur Dateien (kein
Input-Injection). Dieses Skill ist der einzige Produzent der Queue-Datei
in der BL-296-Chain.

**INV-PR-PULL-4 — Filter-Semantik**

Nur `status==active AND threadContext!=null` in die Queue. Kommentare ohne
Code-Anker (threadContext==null, z.B. allgemeine PR-Beschreibungs-Kommentare)
werden NICHT in den Inquiry-Cycle aufgenommen (kein Code-Anker, kein Code-Review).
`IsMyResponse==true` bleibt IN der Queue (nicht herausfiltern) — DISPOSITION
`done-already-replied` wird spaeter von `_pr_question_answer_sim` gesetzt.

**INV-PR-PULL-5 — Content unveraendert**

`**Frage:**` traegt den Reviewer-Content WOERTLICH (nach @-Mention-Stripping).
Keine Paraphrasierung, keine Kuerzung, keine Umformulierung.
Der exakte Wortlaut ist Input des Inquiry-Cycle.

**INV-PR-PULL-6 — Antwort-geschuldet-Triage (der Einstiegspunkt)**

Das primaere Work-Set ist `disposition_owed = (status==active) AND (last_word=="reviewer")` —
die Threads, bei denen WIR nicht das letzte Wort haben (Antwort geschuldet). Sie stehen ZUERST in
der Queue und sind die EINZIGEN, die an `_R_orchestrate` + `_pr_question_answer_sim` gehen.
`last_word` = Author des **letzten** Thread-Kommentars (chronologisch `thread.comments[-1]`), NICHT
`IsMyResponse` (das wäre falsch, wenn der Reviewer NACH meiner Antwort erneut kommentiert hat — dann
habe ich NICHT das letzte Wort, obwohl IsMyResponse irgendwann true war). `committer.displayName` aus
`active-pr.json`. Non-owed (last_word=committer = bereits beantwortet) + resolved werden als 1-Zeilen-
Referenz unter `## TRACKED` gefuehrt (kein Inquiry-Cycle, kein Code-Anker). Begruendung: der Reviewer
will dort eine Antwort, wo er zuletzt geschrieben hat — genau das ist der gute Start-Punkt.

---

## Fehlerbehandlung

| Fehler | Aktion |
|--------|--------|
| `active-pr.json` fehlt | FEHLER + Recovery-Hint `/_pr_init {link}`, Exitcode 1 |
| `routing.json` fehlt | WARN + Defaults verwenden (pathPrefix='', platform='tfs_compat'), Exitcode 0 mit WARN |
| fetch.ps1 Exitcode 1 (Auth) | FEHLER, Hinweis auf `auth.credentialKey` in routing.json, Exitcode 1 |
| fetch.ps1 Exitcode 2 (PR nicht gefunden) | FEHLER, PrId-Check-Hinweis, Exitcode 1 |
| Repo-Datei nicht lesbar (Code-Anker) | WARN, leerer Code-Block, Queue-Item trotzdem schreiben |
| 0 aktive Kommentare nach Filter | WARN + keine Queue, Exitcode 1 |
| pr-{id}-state.json fehlt | Neu anlegen (Grundstruktur), kein Fehler |

---

## Beispiele

```
/_pr_pull
```

Typische Ausgabe nach erfolgreichem Lauf (16 Kommentare, DCSRE-486):

```
[PR_PULL] Start. PrId=486, platform=tfs_compat
[PR_PULL] fetch.ps1 abgeschlossen → pr-486-raw.json (23 Threads gelesen)
[PR_PULL] Filter: 16 aktiv + threadContext, 7 uebersprungen (status!=active oder threadContext=null)
[PR_PULL] 16 Kommentare normiert → pr-486-state.json (comments[])
[PR_PULL] Queue geschrieben: .claude/review-486-queue.md (16 Items)
[PR_PULL] Naechster Schritt: /_R_orchestrate PR-486 normal
```

ARGUMENTS: $ARGUMENTS
