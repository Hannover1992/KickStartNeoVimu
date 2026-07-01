---
status: active
version: 0.1.0
type: satellite
op: PRInquiry
phase: init
model_tier: sonnet
created: 2026-06-09
feature_anchor: BL-296
related:
  - _pr_pull
  - _pr_question_answer_sim
  - _pr_parkinglot_fill
  - _pr_answer
  - _pr_orchestrate
reuses:
  - .claude/meta/pr/routing.json
  - .claude/scripts/pr/_common.ps1  (Resolve-PrId, Get-StateFile, Get-AuthHeaders)
  - .claude/meta/pr/active-pr.json  (Konflikt-Check + Schreib-Ziel)
changelog_0_1_0: |
  v0.1.0 (2026-06-09): Initial — BL-296 PR-Inquiry-Pipeline.
    Ersetzt pr-init.md Hardcode (PrId=18979, fester DCSRE-Skript-Pfad) durch
    Link-Extraktion + routing.json-Abstraktion. INV-PR-INIT-1..5.
---

# /_pr_init — PR-Kontext-Bootstrap (BL-296)

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_pr_init                                                  ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    $ARGUMENTS = {link} [--hil=true|false]                           ║
║      Azure-DevOps-URL: dev.azure.com/{org}/{proj}/_git/{repo}/       ║
║                        pullrequest/{id}                              ║
║      TFS-URL:          tfs.itsg.de/.../pullrequest/{id}             ║
║    .claude/meta/pr/routing.json                                      ║
║      (platform, organization, project, repository,                  ║
║       urls.api/web, apiVersion, auth.credentialKey,                 ║
║       auth.myDisplayName, auth.myTfsId, paths.stateDir,             ║
║       NEU: hil_mode, pathPrefix, tfs_compat)                        ║
║      — via dot-source _common.ps1 (Reuse: $Routing-Objekt)          ║
║    .claude/meta/pr/active-pr.json                                    ║
║      (Konflikt-Check — INV-PR-INIT-5)                               ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/meta/pr/active-pr.json                                    ║
║      {prId, prUrl, platform, branchRef, committer, hil_mode,        ║
║       fetchedAt, chain_phase:"init"}                                 ║
║    .claude/analysis/pr-{id}-state.json                               ║
║      Grundstruktur: {pr_id, pr_link, platform, branch_ref,          ║
║        committer_id, hil_mode, created_at,                          ║
║        comments:[], findings_tripel:[]}                              ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    Kommentare / Threads (→ _pr_pull)                                 ║
║    review-{prId}-queue.md (→ _pr_pull)                              ║
║    Jede andere Datei ausser active-pr.json + pr-{id}-state.json     ║
║                                                                      ║
║  ACTOR: Team Lead (sonnet) — reines Satellite, kein Worker-Spawn    ║
║                                                                      ║
║  MODELL-TIER: sonnet                                                 ║
║    Begruendung: Reine Konfig-Aufloesung + JSON-Schreiben,            ║
║    kein semantisches Urteilen noetig.                                ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    INV-PR-INIT-1: PrId IMMER aus {link} extrahieren — NIE hardcoden ║
║    INV-PR-INIT-2: Committer aus routing.json, NIE git config         ║
║    INV-PR-INIT-3: hil_mode: --hil-Arg > routing.json > Default true  ║
║    INV-PR-INIT-4: Schreibt NICHTS ausser active-pr.json + state.json ║
║    INV-PR-INIT-5: Aktive PR mit anderer PrId → User warnen, STOPP   ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf-Interface

```
/_pr_init {link} [--hil=true|false]
```

**Parameter:**

| Parameter | Pflicht | Default | Beschreibung |
|-----------|---------|---------|-------------|
| `{link}` | JA | — | Vollstaendige Azure-DevOps- oder TFS-PR-URL |
| `--hil` | NEIN | routing.json hil_mode > `true` | Human-in-the-Loop-Modus der Chain |

**Beispiele:**

```
/_pr_init https://dev.azure.com/ITSGGMBH/AP0071%20Daten%20Clearing%20Stelle%20Pflege/_git/DCSRE/pullrequest/20
/_pr_init https://dev.azure.com/ITSGGMBH/.../pullrequest/21 --hil=false
/_pr_init https://tfs.itsg.de/tfs/DefaultCollection/Projekt/_git/Repo/pullrequest/4711
```

**hil_mode-Semantik (AK8 — Vollbeschreibung in _pr_orchestrate):**

| Wert | Verhalten |
|------|-----------|
| `true` (Default) | Chain stoppt nach answer_sim; User pastet echte Antwort zurueck |
| `false` | Vollauto bis readable .md (pr-{id}-answers.md) |

**Logging-Format:**

```
[PR_INIT] ENTRY link={link} hil_arg={true|false|unset}
[PR_INIT] prId={id} platform={azure-devops|tfs} org={org} project={project} repo={repo}
[PR_INIT] committer={displayName} credentialKey={key}
[PR_INIT] hil_mode={true|false} (source: arg|routing|default)
[PR_INIT] WROTE active-pr.json + pr-{id}-state.json
[PR_INIT] EXIT duration={ms}ms status=OK
```

---

## REUSE-INFRASTRUKTUR (kein Greenfield)

**Wiederverwendet aus bestehender TFS-Familie:**

- **`.claude/scripts/pr/_common.ps1`** — `$Routing`-Objekt (bereits geladen von allen PR-Scripts via dot-source), `Resolve-PrId`, `Get-StateFile`, `Get-AuthHeaders`, `Get-PrWebUrl`. `_pr_init` erweitert das active-pr.json-Format, das `Resolve-PrId` und `Get-ActivePrId` danach lesen.
- **`.claude/meta/pr/routing.json`** — bestehende Auth-Abstraktion (`credentialKey`, `urls.*`, `apiVersion`). `_pr_init` benoetigt KEINE neuen Felder wenn `auth.myDisplayName` + `auth.myTfsId` vorhanden; fuegt `hil_mode`, `pathPrefix`, `tfs_compat` NUR als optionale Felder hinzu (WARN wenn fehlend, Defaults greifen).
- **`.claude/meta/pr/active-pr.json`** — bereits vorhanden (pr-20 Beispiel). `_pr_init` schreibt das Format weiter, ERWEITERT um `committer`, `hil_mode`, `chain_phase` (additive, kein Breaking Change fuer bestehende Scripts die nur `prId` lesen).

**NEU (Seam, nicht bestehend):**

- `.claude/analysis/pr-{id}-state.json` — Grundstruktur mit `comments:[]` + `findings_tripel:[]` (BL-296-Erweiterung des state.json-Formats). Kompatibel zur bestehenden pr-20-state.json-Struktur.
- `auth.myDisplayName` + `auth.myTfsId` in routing.json (neue Felder, WARN wenn fehlend).

---

## ABLAUF (Pseudocode)

```
SCHRITT 0: Entry-Log
  Logge: "[PR_INIT] ENTRY link={$ARGUMENTS[0]} hil_arg={...}"
  args    = Parse($ARGUMENTS)
  link    = args[0]          # Pflicht — Fehler wenn leer
  hil_arg = args["--hil"]   # optional, null wenn nicht gesetzt

SCHRITT 1: PR-Link parsen (INV-PR-INIT-1)
  # PrId = letztes Segment nach '/pullrequest/'
  match = Regex.Match(link, r'/pullrequest/(\d+)')
  IF NOT match:
    Logge: "[PR_INIT] FAIL — kein /pullrequest/{id} Segment im Link"
    EXIT 1

  prId = int(match.group(1))

  # Platform + Org/Project/Repo aus URL-Struktur
  IF link enthält "dev.azure.com":
    platform = "azure-devops"
    # dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}
    urlParts = link nach "dev.azure.com/" aufteilen
    org      = urlParts[0]
    project  = urlParts[1]         # URL-decoded
    repo     = urlParts[3]         # nach _git/
  ELSE IF link enthält "tfs." ODER "tfs_compat-Indiz":
    platform = "tfs"
    # tfs.{host}/tfs/{collection}/{project}/_git/{repo}/pullrequest/{id}
    # oder tfs.{host}/{project}/_git/{repo}/pullrequest/{id}
    org/project/repo aus URL-Segment-Analyse (adaptiv)
  ELSE:
    platform = "unknown"
    WARN: "[PR_INIT] WARN — Unbekannte Plattform, Defaults aus routing.json"
    org/project/repo = routing.json-Werte als Fallback

  Logge: "[PR_INIT] prId={prId} platform={platform} org={org} project={project} repo={repo}"

SCHRITT 2: routing.json laden (REUSE: _common.ps1-Mechanismus nachbilden)
  # Claude-Logik (kein PowerShell-Exec hier — reines Satellite)
  routing = Read(".claude/meta/pr/routing.json")
  IF routing fehlt:
    WARN: "[PR_INIT] WARN — routing.json nicht gefunden, Defaults greifen"
    routing = { platform:"azure-devops", auth:{credentialKey:"TFS_ITSG_PAT",
                myDisplayName:"Patryk Krzyzanski", myTfsId:"ITSG\\Patryk.Krzyzanski"},
                hil_mode: null, pathPrefix: "", tfs_compat: false }

  # Committer aus routing.json — INV-PR-INIT-2 (NIE git config)
  committer = {
    displayName:  routing.auth.myDisplayName ?? "Patryk Krzyzanski",
    tfsId:        routing.auth.myTfsId       ?? "ITSG\\Patryk.Krzyzanski",
    credentialKey: routing.auth.credentialKey ?? "TFS_ITSG_PAT"
  }

  IF committer.displayName FEHLT IN routing.json:
    WARN: "[PR_INIT] WARN — routing.json.auth.myDisplayName fehlt; Default 'Patryk Krzyzanski'"
    HINT: "Bitte routing.json um auth.myDisplayName ergaenzen (TFS-Display-Name fuer Reviewer-Matching)"

SCHRITT 3: hil_mode aufloesen (INV-PR-INIT-3)
  hil_mode_source = "default"
  hil_mode        = true                   # Default

  IF routing.hil_mode != null:
    hil_mode        = routing.hil_mode
    hil_mode_source = "routing"

  IF hil_arg != null:
    hil_mode        = hil_arg              # --hil-Arg gewinnt
    hil_mode_source = "arg"

  Logge: "[PR_INIT] hil_mode={hil_mode} (source: {hil_mode_source})"

SCHRITT 4: Konflikt-Check active-pr.json (INV-PR-INIT-5)
  IF active-pr.json existiert:
    existing = Read(".claude/meta/pr/active-pr.json")
    IF existing.prId != null AND existing.prId != prId:
      WARN: "[PR_INIT] WARN — Aktive PR {existing.prId} laeuft noch."
      Ausgabe: "Aktive PR #{existing.prId} ist offen. Vor dem Start von #{prId} bitte"
               "die laufende PR abschliessen (/_pr_answer) oder active-pr.json manuell"
               "loeschen. Kein-konkurrierender-Edit-Regel verletzt."
      EXIT 1   # STOPP — nicht stumm ueberschreiben
    # Gleiche PrId → Re-Init (Resume-freundlich), warnen + fortfahren
    IF existing.prId == prId:
      WARN: "[PR_INIT] WARN — PR #{prId} bereits initialisiert (Re-Init)"

SCHRITT 5: active-pr.json schreiben
  active_pr = {
    "prId":       prId,
    "prUrl":      link,
    "platform":   platform,
    "branchRef":  "",           # noch unbekannt — _pr_pull fuellt aus fetch.ps1-Output
    "committer":  {
      "displayName":  committer.displayName,
      "tfsId":        committer.tfsId,
      "credentialKey": committer.credentialKey
    },
    "hil_mode":   hil_mode,
    "fetchedAt":  ISO8601-Timestamp,
    "chain_phase": "init"
  }
  Write(".claude/meta/pr/active-pr.json", active_pr)

SCHRITT 6: pr-{id}-state.json Grundstruktur schreiben
  state = {
    "pr_id":        prId,
    "pr_link":      link,
    "platform":     platform,
    "branch_ref":   "",             # nach _pr_pull bekannt
    "committer_id": committer.tfsId,
    "hil_mode":     hil_mode,
    "created_at":   ISO8601-Timestamp,
    "comments":     [],             # gefuellt durch _pr_pull
    "findings_tripel": []           # gefuellt durch _pr_question_answer_sim
  }
  stateFile = ".claude/analysis/pr-{prId}-state.json"
  # Wenn Datei bereits existiert: NICHT ueberschreiben (Resume-Schutz) — nur wenn Schritt 4 Re-Init erkannt
  # Bei echtem Erst-Init: Write
  IF stateFile existiert UND existing.prId == prId:
    WARN: "[PR_INIT] WARN — state.json bereits vorhanden (Re-Init), bestehendes state.json bleibt"
  ELSE:
    Write(stateFile, state)

SCHRITT 7: Exit-Log + Naechster-Schritt-Hinweis
  Logge: "[PR_INIT] WROTE active-pr.json + pr-{prId}-state.json"
  Logge: "[PR_INIT] EXIT duration={ms}ms status=OK"

  Ausgabe:
    "PR-Kontext gesetzt (PrId={prId}, hil={hil_mode})."
    "Naechster Schritt: /_pr_pull"
  EXIT 0
```

---

## Output-Schema

**active-pr.json (nach _pr_init):**

```json
{
  "prId": 21,
  "prUrl": "https://dev.azure.com/ITSGGMBH/.../pullrequest/21",
  "platform": "azure-devops",
  "branchRef": "",
  "committer": {
    "displayName": "Patryk Krzyzanski",
    "tfsId": "ITSG\\Patryk.Krzyzanski",
    "credentialKey": "TFS_ITSG_PAT"
  },
  "hil_mode": true,
  "fetchedAt": "2026-06-09T10:00:00Z",
  "chain_phase": "init"
}
```

**pr-{id}-state.json Grundstruktur (nach _pr_init):**

```json
{
  "pr_id": 21,
  "pr_link": "https://dev.azure.com/ITSGGMBH/.../pullrequest/21",
  "platform": "azure-devops",
  "branch_ref": "",
  "committer_id": "ITSG\\Patryk.Krzyzanski",
  "hil_mode": true,
  "created_at": "2026-06-09T10:00:00Z",
  "comments": [],
  "findings_tripel": []
}
```

---

## INVARIANTEN

**INV-PR-INIT-1 — PrId immer aus {link} extrahieren**

NIE PrId hardcoden. Immer letztes Segment nach `/pullrequest/` parsen — gilt fuer Azure-DevOps-URLs und TFS-URLs gleichermassen. Behebt den Hardcode aus dem alten `pr-init.md` (PrId=18979, fester DCSRE-Skript-Pfad).

```
Korrekt:   prId = Regex('/pullrequest/(\d+)', link).group(1)
Verboten:  prId = 18979   # NIEMALS
```

**INV-PR-INIT-2 — Committer aus routing.json, NIE git config**

`auth.myDisplayName` und `auth.myTfsId` aus routing.json sind die einzige Quelle. `git config user.email` ist falsch — Reviewer-Matching in TFS/Azure braucht den TFS-Display-Namen, nicht die Git-Email.

**INV-PR-INIT-3 — hil_mode-Aufloesung (Prioritaetskette)**

```
Prioritaet: --hil-Arg > routing.json.hil_mode > Default true

Beispiele:
  /_pr_init {link} --hil=false   → hil_mode=false  (arg gewinnt)
  /_pr_init {link}               → routing.json.hil_mode falls gesetzt, sonst true
  routing.json fehlt hil_mode    → Default true
```

`hil_mode` wird in BEIDE Ausgabedateien (active-pr.json + pr-{id}-state.json) geschrieben und ist Single-Source fuer die gesamte Chain.

**INV-PR-INIT-4 — Schreibt NICHTS ausser active-pr.json + pr-{id}-state.json**

Kein Fetch, keine Kommentare, keine review-Queue, kein Manifest-Edit. Klare Trennung zu `_pr_pull` (AK1-Aufteilung). Der einzige Zweck ist Kontext-Bootstrap.

**INV-PR-INIT-5 — Aktive PR mit anderer PrId → User warnen, STOPP**

Wenn `active-pr.json` existiert und `prId` einer anderen PR enthaelt: User explizit warnen (kein stilles Ueberschreiben). Verweis auf kein-konkurrierender-Edit-Regel. EXIT 1.

Ausnahme: gleiche PrId = Re-Init (z.B. nach Fehler) → WARN + fortfahren. state.json bei Re-Init NICHT ueberschreiben (Resume-Schutz — bestehende `comments[]`/`findings_tripel[]` bleiben erhalten).

---

## Routing-Erweiterungen (NEU, optional in routing.json)

```json
{
  "auth": {
    "myDisplayName": "Patryk Krzyzanski",
    "myTfsId":       "ITSG\\Patryk.Krzyzanski"
  },
  "hil_mode":   true,
  "pathPrefix": "/Sources/Backend/",
  "tfs_compat": false
}
```

- `auth.myDisplayName` / `auth.myTfsId` — PFLICHT fuer INV-PR-INIT-2; WARN bei Fehlen, Defaults greifen
- `hil_mode` — optionaler Organisations-Default (INV-PR-INIT-3)
- `pathPrefix` — fuer `_pr_pull` (fetch.ps1-Parametrisierung, kein Belang fuer `_pr_init`)
- `tfs_compat` — fuer `_pr_pull` (API-URL-Routing, kein Belang fuer `_pr_init`)

---

## Chain-Position

```
+------------------------------------------------------------------+
| PR-Inquiry-Pipeline (BL-296)                                     |
|                                                                  |
| [1] /_pr_init      ← DU BIST HIER                               |
|      |                                                           |
|      v                                                           |
| [2] /_pr_pull      → fetch.ps1 (parametrisiert) → queue.md      |
|      |                                                           |
|      v                                                           |
| [3] /_R_orchestrate  → bob-monolog (UNVERAENDERT eingehaengt)    |
|      |                                                           |
|      v                                                           |
| [4] /_pr_question_answer_sim  → sim-answers + Findings-Tripel   |
|      |                                                           |
|      v  (HiL-Gate: hil=true → STOPP; hil=false → weiter)       |
|      |                                                           |
|      v                                                           |
| [5] /_pr_parkinglot_fill  → PL-Items (agree/FLIP only)          |
|      |                                                           |
|      v                                                           |
| [6] /_IDF_orchestrate  → Implementierung                        |
|      |                                                           |
|      v                                                           |
| [7] /_pr_answer    → readable .md + Loop-Schluss (AK7)         |
+------------------------------------------------------------------+
```

`_pr_init` erzeugt den Kontext-Anker (active-pr.json) den alle nachfolgenden Skills via `Resolve-PrId` (_common.ps1) lesen. Kein Schritt nach `_pr_init` fragt nochmals nach dem Link.
