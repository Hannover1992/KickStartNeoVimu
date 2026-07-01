---
name: _pr_answer
status: active
version: 1.0.0
type: orchestration
op: PrInquiry
phase: AK6
created: 2026-06-09
updated: 2026-06-09
feature_anchor: BL-296
chain_position: pr-inquiry-cycle (Schritt 7/7, nach _IDF_orchestrate)
difficulty_scaling: true
team_based: true
tier: opus
related:
  - _pr_init
  - _pr_pull
  - _R_orchestrate
  - _pr_question_answer_sim
  - _pr_parkinglot_fill
  - _IDF_orchestrate
  - _pr_orchestrate
  - _answer
---

# /_pr_answer — Finale PR-Antworten am ECHTEN Code (AK6 + AK7-Loop-Schluss)

> **Stelle in der Inquiry-Kette:** `init -> pull -> R_orchestrate -> answer_sim -> [HiL-Gate] -> parkinglot_fill -> IDF -> **answer**`
> Dies ist der **letzte** Schritt. Die Maschine (IDF) hat implementiert; hier wird die *simulierte* Antwort (Hypothese/theory)
> durch die **verankerte Endantwort** mit **echten Commit-Hashes** ersetzt, der `flip_status` final gesetzt
> (CONFIRMED/FLIPPED/REFINED) und der Inquiry-Loop geschlossen (`resulting_truth`). Output ist eine **lesbare `.md`**,
> die der User 1-by-1 in den PR pastet. **KEINE internen Marker** (DUC/Ring/PR2/PL/IDF/SDF) im Output.

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_pr_answer                                          [AK6 + AK7] ║
╠══════════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                                    ║
║    .claude/analysis/pr-{id}-state.json                                     ║
║        (comments[], Commits der Gruppen NACH IDF, branch_ref, code_verified)║
║    .claude/analysis/pr-{id}-sim-answers.json                              ║
║        (sim_answer_text, stance, disp, parking_lot_id, flip_status)       ║
║    {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md                        ║
║        (Findings-Tripel; resulting_truth leer, flip_status=PENDING)       ║
║    git log / git show / git rev-parse  (echte Commit-Hashes im Ziel-Repo) ║
║    .claude/meta/pr/routing.json + active-pr.json                          ║
║        (Get-CommitWebUrl-Kontext: Org/Project/Repo/branchRef, hil_mode)   ║
║    _R_orchestrate PR-REPLY-GUIDELINES (Z. 875-913, NORMATIVE Referenz)    ║
║                                                                            ║
║  SCHREIBT:                                                                 ║
║    .claude/review/pr-{id}-answers.md       (readable, User pastet 1-by-1) ║
║    {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md                        ║
║        (resulting_truth + flip_status final + commit_refs — Loop-Schluss) ║
║    {VAULT}/Findings/_pr_findings_index.md  (Index-Status fortschreiben)   ║
║    .claude/analysis/pr-{id}-state.json                                     ║
║        (comments[].status='answered', final_reply, code_verified=true)    ║
║                                                                            ║
║  RUFT (REUSE-FIRST, kein Neubau):                                          ║
║    link.ps1 / Get-CommitWebUrl  (aus _common.ps1) — Commit-URL-Generierung║
║    git rev-parse / git show / git log  — Full-Hash + Commit-Existenz      ║
║    agent(model={ceiling/opus}, role=pr-{id}-synthese-answer)  OPTIONAL    ║
║        (Polish/Humanify nur bei >~6 Kommentaren; sonst Team-Lead inline)  ║
║                                                                            ║
║  RUFT NICHT:                                                               ║
║    KEIN Code-Schreiben/-Aendern  (Antwort-Synthese only)                  ║
║    KEIN _IDF_orchestrate / _SDF_ / Worker-Spawn fuer Implementierung      ║
║    KEIN Agent(general-sonnet, prompt='orchestrate...')  (INV-AO-CALLER)   ║
║                                                                            ║
║  INVARIANTEN: INV-PR-ANS-1 .. INV-PR-ANS-6 (siehe unten)                  ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Zweck (AK6 + AK7)

`_pr_answer` ist der **Loop-Schluss** der PR-Inquiry-Pipeline (BL-296). Jeder PR-Kommentar war eine offene Frage;
`_pr_question_answer_sim` hat dazu eine **Hypothese** (simulierte Antwort, `theory`-Grad) erzeugt; `_IDF_orchestrate`
hat sie als **Experiment** implementiert. `_pr_answer` liest jetzt die **Code-Realitaet** (echte Commit-Hashes) und
verwandelt jede Hypothese in eine **verankerte Endantwort**:

1. **Doing-Antworten** (disp=done): "Umgesetzt in [hash](url)" — nur mit echtem Commit (INV-PR-ANS-1).
2. **Abweichungs-Antworten** (stance=refute/REFINED): VERSTAENDNIS + BEGRUENDUNG + EVIDENCE-VERWEIS (INV-PR-ANS-2).
3. **Scope-Antworten** (out-of-scope): explizite Scope-Benennung + Parking-Lot-Verweis.

Dabei wird der `flip_status` **final** aus der Code-Realitaet gesetzt — eine sim-Refutation, die der echte Code als
Bug entlarvt, **FLIPPT** (Typ #2 cancelEdit, Live 2026-06-08). Der Inquiry-Loop schliesst, indem `resulting_truth`
(1-Satz-Endurteil ueber den realen Code) in das Findings-Tripel geschrieben wird (AK7).

**Output:** eine humanifizierte, lesbare `.md` ohne jeden internen Marker, die der User Kommentar-fuer-Kommentar
in den PR kopiert.

---

## REUSE-FIRST — was wiederverwendet wird (kein Greenfield)

| Bestehende Infra | Was genutzt wird | NEU / Patch |
|---|---|---|
| `link.ps1` (`.claude/scripts/pr/link.ps1`) | `prResponseMarkdown`-Logik (`"Umgesetzt in:\n- [shortHash](url)"`) + Browser-Open als Output-Vorlage; nutzt bereits `git rev-parse` fuer Full-Hash | unveraendert genutzt |
| `Get-CommitWebUrl` (`_common.ps1`, Z. 60-68) | Commit-URL-Generierung `{WebBaseUrl}/commit/{Hash}?refName=refs%2Fheads%2F{branch}` — **Branch-Param erzeugt das `%2F`-Encoding** | unveraendert genutzt (Azure-agnostisch via routing.json) |
| `Resolve-PrId` / `Get-StateFile` (`_common.ps1`) | PrId aus `active-pr.json`, State-Pfad `pr-{id}-state.json` | unveraendert genutzt |
| `sync.ps1` IsMyResponse-Mechanismus | `lastComment.author == myDisplayName` → pruefen ob Antwort schon gepostet (disp=*-already-replied) | unveraendert referenziert |
| `_R_orchestrate` PR-REPLY-GUIDELINES (Z. 875-913) | Doing-Regel / Abweichungs-Regel (3 Pflicht-Elemente) / Scope-Regel — **NORMATIV referenziert, NICHT kopiert** (House-Style "Referenz-Verweis") | referenziert |
| `_answer.md` KURZFORM-Konzept | copy-paste-fertiger, jargon-freier Dev-Ton fuer die readable `.md` | referenziert |
| `_pr_question_answer_sim` Findings-Tripel | Tripel existiert bereits (PENDING); `_pr_answer` fuellt NUR die 4. Position (`resulting_truth`) + `flip_status` final + `commit_refs` | erweitert, nicht ersetzt |
| `_pr_parkinglot_fill` `parking_lot_id` | aus `sim-answers.json` gelesen → Scope-Antwort verweist darauf | referenziert |

**NEUE Seams (klar markiert):**
- **`resulting_truth`-Fuellung + `flip_status`-Finalisierung** im Findings-Tripel = der eigentliche **Loop-Schluss (AK7)**.
  Vorher legt `_pr_question_answer_sim` das Tripel mit `flip_status=PENDING` an; `_pr_answer` ist der **einzige** Writer von `resulting_truth`.
- **`pr-{id}-answers.md`** im _answer.md-KURZFORM-Stil mit einer **`OFFEN / VOR MERGE PRUEFEN`**-Sektion (Refutationen + E2E + Squash-Caveat).
- **HiL-Switch (INV-PR-ANS-6):** bei `hil_mode=true` ist die Basis die **echte, vom User gepastete** Reviewer-Antwort, nicht die `sim_answer` — `_pr_answer` ist dann reine Formatierungs-Hilfe + Commit-Verankerung.

---

## Aufruf

```
/_pr_answer                        # nutzt active-pr.json (Resolve-PrId)
/_pr_answer PR-{id}                # explizite PrId
/_pr_answer PR-{id} --no-polish    # Polish-Agent unterdruecken (Team-Lead inline)
```

`$ARGUMENTS` = `[PR-{id}] [--no-polish]`. Ohne PrId → `Resolve-PrId` aus `active-pr.json`.

**Vorbedingung (Seam):** `_IDF_orchestrate {committer_bl} --pl-only --from=sdf_finish` ist gelaufen; die echten
Commits stehen im Ziel-Repo; `state.json` traegt `code_verified`-Markierung pro zustimmen-Item. Wird `_pr_answer`
ueblicherweise vom Chain-Orchestrator `/_pr_orchestrate` (SCHRITT 8) geladen, ist aber standalone aufrufbar.

**QUICK-START Test-Oracle (AK-Verifikation 486):** Re-Lauf gegen DCSRE-486 muss die **16 Antworten** reproduzieren
und den **#2 cancelEdit**-Eintrag als `flip_status=REFINED` (Refutation haelt, aber praeziser: `effect() -> resetValidators()`
ist der reaktive Pfad) ausweisen — KEIN `FLIPPED`, KEINE Marker im Output. Referenz-Oracle:
`DCSRE-486-pr-replies-final-2026-06-08.md`.

---

## Ablauf (Schritt-fuer-Schritt)

### SCHRITT 0 — Entry-Log + Reihenfolge-Gate (INV-PR-ANS-5)

```
[PR_ANS] entry — vault_root, args, PrId (Resolve-PrId aus active-pr.json)
audit-log: skill=_pr_answer, pr_id, phase=AK6, started_at

GATE (INV-PR-ANS-5): fuer JEDES Item mit stance IN {agree, partial} (also ein "zustimmen"-Item):
    IF state.comments[i].code_verified == false:
        BLOCK mit Recovery-Hint:
          "[PR_ANS] BLOCK: Item #{n} ({thread_id}) zugestimmt, aber code_verified=false.
           IDF hat dieses Item nicht umgesetzt. Recovery:
             /_IDF_orchestrate {committer_bl_id} --pl-only --from=sdf_finish
           danach: /_pr_answer PR-{id} erneut."
        exit 1
    # Refutationen (stance=refute) brauchen KEIN code_verified — sie haben keinen Commit.
```
> Korrektive Enforcement: der Block traegt den Recovery-Pfad, blockt nicht nur (feedback_corrective_enforcement).

### SCHRITT 1 — Echte Commit-Hashes aufloesen (REUSE: link.ps1 / Get-CommitWebUrl)

```
FOR jede Gruppe/jedes umgesetzte Item in state.json.comments[] (disp=done|verify, code_verified=true):
    shortHash = state.comments[i].commit_shorthash   # aus IDF/state.json
    fullHash  = git rev-parse {shortHash}              # Full-40-Hash (INV-PR-ANS-1)
    IF NICHT aufloesbar:
        markiere Item als AUSSTEHEND (kein Commit) — KEINE "wurde erledigt"-Behauptung
        continue
    branch = active-pr.json.branchRef   (z.B. feature/{branch})
    url = Get-CommitWebUrl -Hash {fullHash} -Branch {branch}
        # → {WebBaseUrl}/commit/{fullHash}?refName=refs%2Fheads%2F{branch}  (Azure/TFS aus routing.json)
    commit_link[i] = "[{shortHash}]({url})"
```
> Praktisch genuegt `link.ps1 -PrId {id} -GroupNr {n} -NoBrowser` (liefert fertiges `prResponseMarkdown` + JSON
> mit `commitUrl` pro Commit). Team-Lead nutzt das JSON-Feld direkt — **kein Neubau der URL-Logik**.

### SCHRITT 2 — Pro Kommentar die Endantwort + flip_status final bauen

```
FOR jeden Comment c (sim-answers.json + state.json + Findings-Tripel):

  (a) disp == done  (umgesetzt):
        → DOING-Antwort (PR-REPLY-GUIDELINES Doing-Regel, INV-PR-ANS-1):
          Kurz, was geaendert wurde + "Umgesetzt in {commit_link[c]}".
          flip_status_final = CONFIRMED  (Hypothese 'Fix noetig' durch Code bestaetigt)

  (b) disp == verify  (sollte umgesetzt sein — am Code pruefen):
        → Repo-Code an file:line lesen (Read-Tool). EHRLICH:
          umgesetzt → Doing-Antwort + commit_link; flip_status_final = CONFIRMED
          NICHT umgesetzt → AUSSTEHEND markieren (needs_work), NICHT beschoenigen;
                            (sollte SCHRITT-0-Gate schon gefangen haben)

  (c) stance == refute  (Refutation aus answer_sim):
        → ABWEICHUNGS-Antwort (PR-REPLY-GUIDELINES, 3 Pflicht-Elemente, INV-PR-ANS-2):
            1. VERSTAENDNIS: "Ich verstehe, dass {Reviewer-Punkt}."
            2. BEGRUENDUNG : "Wir weichen ab, weil {technische Begruendung}."
            3. EVIDENCE    : "Siehe {Code-Stelle file:line / Architektur-Entscheidung}."
          KEIN Commit-Link.
          flip_status_final aus Code-Realitaet (INV-PR-ANS-4):
            Code zeigt: Reviewer hatte recht / echter Bug  → FLIPPED  (Typ #2)
            Refutation haelt, aber praeziser nach Code-Check → REFINED  (z.B. #2 cancelEdit)
            Refutation unveraendert bestaetigt              → CONFIRMED (war REFINED-Kandidat, blieb stabil)

  (d) out-of-scope (Code-Kommentar → Parking-Lot, parking_lot_id gesetzt):
        → SCOPE-Antwort (PR-REPLY-GUIDELINES Scope-Regel):
          "Ausserhalb Scope dieses PRs. Eingetragen als {parking_lot_id} und wird separat verfolgt."
          flip_status_final = CONFIRMED  (zustimmen, aber separat)

  (e) disp == *-already-replied  (sync.ps1 IsMyResponse=true):
        → DISPOSITION done-already-replied: keine neue Antwort noetig; im Output als
          "(bereits beantwortet)" markieren, nicht erneut posten.

  IF hil_mode == true (INV-PR-ANS-6):
      Basis ist die ECHTE vom User gepastete Reviewer-Antwort (state.comments[c].user_pasted_reply),
      NICHT sim_answer_text. _pr_answer formatiert + verankert nur (Commit-Links, Struktur).
```

### SCHRITT 3 — Humanify / Polish (optional opus-Pass)

```
IF count(comments) > ~6  AND  NICHT --no-polish:
    agent(model={ceiling/opus}, role=pr-{id}-synthese-answer):
        Input: alle Roh-Antworten aus SCHRITT 2
        Aufgabe: variierte Opener ueber alle N, Dev-Kollegen-Ton, ECHTE Umlaute (ae/oe/ue VERBOTEN
                 im Freitext; Code-Bezeichner in Backticks bleiben ASCII), 2-4 Saetze pro Antwort,
                 KEINE internen Marker (INV-PR-ANS-3), Refutationen respektvoll.
        Humanify-Norm: feedback_pr_replies_humanify.md (MEMORY) + _answer.md KURZFORM-Stil.
ELSE:
    Team-Lead humanifiziert inline (gleiche Regeln).
```
> Konsistent zu `_pr_question_answer_sim` Phase 3 (Polish/Humanify opus). Hier kleiner, weil der Steelman-Check
> schon in answer_sim lag — `_pr_answer` poliert nur die finale Verankerung.

### SCHRITT 4 — readable `.md` schreiben (`pr-{id}-answers.md`)

```
schreibe .claude/review/pr-{id}-answers.md  (NEUER Seam, _answer.md-KURZFORM-Stil):

  # PR-{id} — Antworten (copy-paste 1-by-1)

  ### #N — {datei} — {kurzthema}
  > {Reviewer-Zitat woertlich, @-Mentions gestrippt}
  **Antwort:** {humanifizierte Antwort + echte Commit-Links bei disp=done}

  ... (ein Block pro Kommentar, in PR-Thread-Reihenfolge) ...

  ---
  ## OFFEN / VOR MERGE PRUEFEN
  - Refutationen (kein Commit, brauchen evtl. Reviewer-Diskussion): #X, #Y
  - E2E / manuelle Verifikation noch offen: {Items mit needs_work}
  - **Squash-Merge-Caveat:** Bei Squash-Merge zeigen die verlinkten Branch-Commit-Hashes
    nach dem Merge ggf. ins Leere — vor Merge posten ODER nach Merge auf den Squash-Commit umlenken.
```
> **AK-Verifikation 486:** KEINE internen Marker (DUC/Ring/PR2/PL/IDF/SDF). Reviewer sieht nur Dev-Sprache.

### SCHRITT 5 — Findings-Tripel-Loop-Schluss (AK7) + State

```
FOR jeden Comment c:
    update {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md:
        resulting_truth: "{1-Satz Endurteil — was der Code NACH IDF tatsaechlich zeigt}"
        flip_status:     {flip_status_final aus SCHRITT 2}   # CONFIRMED|FLIPPED|REFINED
        flip_reason:     {nur bei FLIPPED/REFINED — was der Code-Verify ergab}
        code_verified:   true
        commit_refs:     [{fullHash}, ...]   # echte 40-Hashes
        final_answer_ref: ".claude/review/pr-{id}-answers.md#N"
    # INV-PR-ANS-4: NIE Tripel ohne flip_status-Update ueberschreiben.

update {VAULT}/Findings/_pr_findings_index.md  (Status PENDING → CLOSED pro Tripel)

update .claude/analysis/pr-{id}-state.json:
    comments[c].status      = "answered"
    comments[c].final_reply = {humanifizierte Endantwort}
    comments[c].code_verified = true
```
> **Beispiel #2 cancelEdit:** `frage='kein markAllAsTouched'` → `sim_answer='Refutation: cancelEdit oeffnet nur Confirm-Dialog'`
> → `resulting_truth='effect()->resetValidators() ist der reaktive Pfad; Refutation praezisiert, kein Bug'`
> → `flip_status=REFINED`, `parking_lot=null`. Loop geschlossen.

### SCHRITT EXIT

```
[PR_ANS] exit — pr-{id}-answers.md geschrieben, {N} Antworten, {F} FLIP/REFINED, {A} ausstehend.
Ausgabe an User:
  - pr-{id}-answers.md ist fertig — bitte 1-by-1 in den PR kopieren.
  - Bei FLIP/REFINED explizit melden (z.B. "#2 cancelEdit: Refutation REFINED durch Code-Verify").
  - OFFEN-Sektion durchsehen (Refutationen + E2E + Squash-Caveat).
Exitcode 0.
```

---

## INVARIANTEN

1. **INV-PR-ANS-1 (Doing-Regel):** NIE "wurde erledigt" ohne echten Commit-Hash. Commit-Format `[kurzhash](az-url)`
   via `git rev-parse` (Full-Hash) + `Get-CommitWebUrl`. Kein Commit → **AUSSTEHEND** markieren, nicht behaupten.
   (REUSE: `link.ps1` `prResponseMarkdown`-Logik.)
2. **INV-PR-ANS-2 (Abweichungs-Regel):** Refutationen folgen den **3 Pflicht-Elementen** — VERSTAENDNIS + BEGRUENDUNG
   + EVIDENCE-VERWEIS. Normativ aus `_R_orchestrate` PR-REPLY-GUIDELINES (Z. 893-905), **referenziert, nicht dupliziert**.
3. **INV-PR-ANS-3 (Keine Marker / Humanify):** NIE interne Marker (DUC/Ring/PR2/PL/IDF/SDF) im Output (AK-Verifikation 486).
   ECHTE Umlaute im Freitext (ae/oe/ue VERBOTEN; Code-Bezeichner in Backticks ASCII), Dev-Kollegen-Ton wie `_answer.md` KURZFORM,
   variierte Opener ueber alle N.
4. **INV-PR-ANS-4 (flip_status final):** `flip_status` wird **nach echtem Code-Check** gesetzt
   (CONFIRMED = Hypothese bestaetigt, FLIPPED = durch Code gekippt, REFINED = praezisiert). Loop-Schluss `frage → resulting_truth`.
   NIE Findings-Tripel nach IDF ohne `flip_status`-Update ueberschreiben. `flip_reason` PFLICHT bei FLIPPED/REFINED.
5. **INV-PR-ANS-5 (Reihenfolge-Enforcement):** BLOCK wenn `code_verified=false` fuer ein zustimmen-Item (IDF nicht gelaufen
   / Item nicht umgesetzt). Block traegt Recovery-Hint (`/_IDF_orchestrate ... --from=sdf_finish`). Squash-Merge-Caveat
   in den Output-Hinweis-Block.
6. **INV-PR-ANS-6 (HiL):** Bei `hil_mode=true` ist die Basis die **echte vom User gepastete** Reviewer-Antwort
   (nicht `sim_answer`); `_pr_answer` ist dann Formatierungs-Hilfe + Commit-Verankerung. `hil_mode` aus `active-pr.json`
   (Single-Source der Chain, von `_pr_init` gesetzt — Parameters>Memory).

**Zusatz (Architektur-konform):**
- **INV-AO-CALLER (CLAUDE.md):** `_pr_answer` spawnt nur den OPTIONALEN Humanify-Worker (`role=pr-{id}-synthese-answer`)
  via `agent(...)` — NIE einen Orchestrator-Sub-Agent. Kein `Agent(general-sonnet, prompt='orchestrate...')`.
- **Analysis-only:** `_pr_answer` schreibt NIE Code. Code-Fixes sind ausschliesslich in `_IDF_orchestrate` entstanden
  (konsistent zur `_R_orchestrate`-Invariante "NIE Code schreiben").

---

## Daten-Schema-Bezug (Findings-Tripel, AK7)

`_pr_answer` fuellt die **letzten** Felder des Lebenszyklus
(`_pr_question_answer_sim` legt PENDING an → `_pr_parkinglot_fill` traegt `parking_lot` nach → **`_pr_answer` schliesst**):

```yaml
# {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md  (von _pr_answer gefuellte Felder)
resulting_truth: "{1-Satz Endurteil — Code-Realitaet NACH IDF}"   # <- NEU, Loop-Schluss
flip_status: "CONFIRMED | FLIPPED | REFINED"                       # <- final (war PENDING)
flip_reason: "{nur FLIPPED/REFINED — was der Code-Verify ergab}"
code_verified: true                                               # <- nach git-Check
commit_refs: ["{full-hash}", ...]                                 # <- echte 40-Hashes
final_answer_ref: ".claude/review/pr-{id}-answers.md#N"
```

Die 4 AK7-Kern-Tripel-Felder sind `{frage, sim_answer, parking_lot|resulting_truth, flip_status}`:
`parking_lot` (bei agree-Items) und `resulting_truth` (finale Wahrheit ueber alle Items) teilen sich die 3. Position.

---

## CHAIN-POSITION

```
_pr_init  ->  _pr_pull  ->  _R_orchestrate  ->  _pr_question_answer_sim
                                                        |
                                                  [HiL-Gate, im _pr_orchestrate]
                                                        |
                              _pr_parkinglot_fill  ->  _IDF_orchestrate  ->  [ _pr_answer ]  ← DU BIST HIER
                                                                                   |
                                              pr-{id}-answers.md (readable) + Findings-Tripel (Loop geschlossen)
                                                                                   |
                                                              User pastet 1-by-1 in den PR
```

**Naechster Schritt:** keiner (Kette zu Ende). Bei `hil_mode=false` hat der User die fertigen Antworten;
bei `hil_mode=true` war die Basis die echte User-Antwort (INV-PR-ANS-6) und `_pr_answer` lief als Re-Entry nach `--resume`.

---
ARGUMENTS: $ARGUMENTS
