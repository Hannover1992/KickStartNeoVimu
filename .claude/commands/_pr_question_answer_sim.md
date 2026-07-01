---
name: _pr_question_answer_sim
status: active
version: 1.0.0
type: orchestration
op: PrInquirySim
created: 2026-06-09
updated: 2026-06-09
feature_anchor: BL-296
chain_position: 4-of-7 (init -> pull -> R_orchestrate -> [SIM] -> [HiL-Gate] -> parkinglot_fill -> IDF -> answer)
team_based: true
difficulty_scaling: true
related:
  - _pr_init
  - _pr_pull
  - _R_orchestrate        # liefert bob-monolog-{item}.md (Grundlage)
  - _pr_parkinglot_fill   # naechster Schritt (Seam: sim-answers.json)
  - _pr_answer            # finaler Loop-Schluss (resulting_truth)
  - _pr_orchestrate       # Chain-Orchestrator (HiL-Gate sitzt DORT)
  - _parking-lot          # PL-Item-Schema (von _pr_parkinglot_fill konsumiert)
  - _answer               # KURZFORM-Dev-Stil-Anker (Humanify)
---

# /_pr_question_answer_sim - PR-Inquiry: Simulierte Antwort + Adversarial Steelman (AK3)

> PR-Review = Instanz des Inquiry-Cycle. Jeder Reviewer-Kommentar = offene Frage.
> Die simulierte Antwort ist eine **Hypothese** (theory), kein fertiges Urteil — sie kann
> spaeter am echten Code FLIPPEN. Dieser Schritt erzeugt die Hypothese und haertet sie:
> jede Refutation muss erst durch einen **adversarial Steelman-Check** (sonst rutscht ein
> #2-cancelEdit-Fall als "STABLE" durch, obwohl der reaktive Pfad ihn praezisiert/kippt).

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_pr_question_answer_sim                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                                         ║
║    .claude/analysis/pr-{id}-state.json                                          ║
║        (comments[] mit text/file/line/reviewer_name — von _pr_pull)            ║
║    .claude/review/bob-monolog-{item}.md     [PRIMAERGRUNDLAGE, von _R_orch]     ║
║        (schweregrad KRITISCH|WARN|INFO, F1 Problem, F3 Fix-Plan,                ║
║         F4 RAG-Kongruenz, F5 Klarsprache)                                       ║
║    .claude/review/PRAESENTATION-PR-{id}-*.md   (optional, Rang+Querverweise)    ║
║    Echter Repo-Code an File+Line (Read-Tool)                                    ║
║        — im Adversarial-Check TIEF, nicht nur RAG-Chunks (SP-FIX-10-analog)     ║
║    .claude/meta/pr/active-pr.json           (hil_mode, branchRef, committer)    ║
║    MEMORY feedback_pr_replies_humanify.md   (normative Humanify-Spec)           ║
║                                                                                 ║
║  SCHREIBT:                                                                      ║
║    .claude/analysis/pr-{id}-state.json                                          ║
║        (sim_answers in comments[]: disp, sim_answer_text, stance,               ║
║         flip_status, flip_reason, needs_work, grounded, commit_links)           ║
║    .claude/analysis/pr-{id}-sim-answers.json   [SCHEMA additionalProperties:false]║
║        ([{n, question_id, question, disp, sim_answer_text, stance,              ║
║          flip_status, flip_reason, needs_work, grounded, adversarial_result}])  ║
║    {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md   [NEUE Vault-Root, AK7]      ║
║        (flip_status=PENDING, parking_lot=null, resulting_truth='')              ║
║    {VAULT}/Findings/_pr_findings_index.md      (Index, analog _backlog_index)   ║
║                                                                                 ║
║  RUFT (Worker-Spawns NUR hier, nie im Chain-Orchestrator — INV-AO-CALLER):      ║
║    agent(model={middle/sonnet}, role=pr-{id}-{cid}-sim)        — PHASE 1 Draft  ║
║    agent(model={ceiling/opus},  role=pr-{id}-{cid}-adversarial)— PHASE 2 nur    ║
║                                                  refute ∨ INFO ∨ F4=LOW         ║
║    agent(model={ceiling/opus},  role=pr-{id}-synthese-polish)  — PHASE 3 1x     ║
║                                                                                 ║
║  INVARIANTEN:                                                                   ║
║    INV-PR-SIM-1  Refutation NIE ohne adversarial Steelman-Check (load-bearing)  ║
║    INV-PR-SIM-2  NIE interne Marker (DUC/Ring/PR2/PL/IDF/SDF) im Output         ║
║    INV-PR-SIM-3  Humanify-Pflicht (ECHTE Umlaute, 2-4 Saetze, Opener variiert)  ║
║    INV-PR-SIM-4  NIE Code schreiben/aendern (Analysis+Simulation only)          ║
║    INV-PR-SIM-5  flip_status-Semantik STABLE|FLIP/FLIPPED|REFINED               ║
║    INV-PR-SIM-6  Reihenfolge-Gate: blockt ohne bob-monolog-{item}.md            ║
║    INV-PR-SIM-7  Commit-Grounding bei disp=done/verify (Full-Hash, ehrlich)     ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

```
+================================================================================+
| META-COMMAND: /_pr_question_answer_sim   (Schritt 4 der PR-Inquiry-Kette)       |
+================================================================================+
|                                                                                |
| ACTOR : TEAM LEAD (DU — die ausfuehrende Claude-Instanz)                        |
| WORKER: 3 Phasen (KURZLEBIG_PROMPT, 1 Agent = 1 Aufgabe = stirbt danach):       |
|   PHASE 1 Draft       : middle/sonnet, PARALLEL, 1 Agent / Kommentar           |
|   PHASE 2 Adversarial : ceiling/opus, NUR Refutations-/INFO-/F4-LOW-Kandidaten |
|   PHASE 3 Polish       : ceiling/opus, EINMAL ueber alle Drafts (Humanify)      |
|                                                                                |
| PRINZIP: Der Team Lead spawnt — interpretiert die agent()-Stellen NICHT inline  |
|          (INV-AO-CALLER, kein Mega-Worker).                                     |
| INQUIRY: Reviewer-Kommentar = Frage. sim_answer = Hypothese. IDF (spaeter) =    |
|          Experiment. Hier wird die Hypothese erzeugt + adversarial gehaertet.   |
+================================================================================+
```

---

## Aufruf

```
/_pr_question_answer_sim
/_pr_question_answer_sim PR-486          # explizite PrId (sonst aus active-pr.json)
```

- Kein Pflicht-Argument: PrId wird via `active-pr.json` (Resolve-PrId) aufgeloest.
- Wird normal vom Chain-Orchestrator `_pr_orchestrate` (SCHRITT 4) geladen, ist aber
  **einzeln aufrufbar/testbar** (das HiL-Gate sitzt bewusst NICHT hier, sondern im
  Orchestrator — dieser Skill liest `hil_mode` nur informativ fuer den Exit-Hinweis).
- `$ARGUMENTS` = `[PR-{id}]` (optionaler PrId-Override).

### QUICK-START Testcase (DCSRE-486, AK-Verifikation)

Re-Lauf gegen DCSRE-486 (manuell gefahrenes Gold-Beispiel) muss die 16 Antworten
reproduzieren UND den **#2 cancelEdit**-Fall im adversarial-check fangen:
- Reviewer-Frage: "kein `markAllAsTouched`".
- Draft (sonnet): Refutation — "`cancelEdit` oeffnet nur den Confirm-Dialog".
- Adversarial (opus): liest `effect()` -> `resetValidators()` TIEF -> Entscheid **REFINED**
  (Refutation haelt, aber praeziser: der reaktive Pfad ist der Grund, kein echter Bug).
- Erwartung: `flip_status=REFINED`, `flip_reason` gesetzt, KEINE internen Marker im Text.

---

## Reuse-First (kein Greenfield — was hier wiederverwendet wird)

| Quelle (bestehend)                              | Wiederverwendung hier                                               |
|-------------------------------------------------|---------------------------------------------------------------------|
| `_R_orchestrate` -> `bob-monolog-{item}.md`     | **Primaergrundlage** je Kommentar: F1 Problem, F3 Fix-Plan, F4 RAG-Kongruenz, schweregrad. PHASE 1 leitet daraus die DISPOSITION ab. |
| `_R_orchestrate` PR-REPLY-GUIDELINES (Z. 875-913)| Format-Vorlage fuer `sim_answer` (Doing/Abweichung/Scope) — **per Referenz**, kein Copy-Paste. |
| `pr-replies-dcsre486-wf.js` (Gold-Lauf 06-08)   | 1:1 Strukturvorbild: DISPOSITION-Enum, DRAFT_SCHEMA (`additionalProperties:false`), Phase Draft(sonnet parallel)+Polish(opus), `git show`/`git rev-parse`-Grounding. |
| `pr-replies-humanify-wf.js` + `feedback_pr_replies_humanify.md` (MEMORY) | Humanify-House-Style: ECHTE Umlaute, 2-4 Saetze, Opener variieren, keine Marker. |
| `_answer.md` KURZFORM-Konzept                   | Dev-Stil-Anker (copy-paste-fertig, kein Jargon).                    |
| `active-pr.json` / `pr-{id}-state.json`         | Chain-State-Backbone (von `_pr_init`/`_pr_pull` gesetzt), hier ERWEITERT um `sim_answers` (nicht ersetzt). |
| `_R_orchestrate` SP-FIX-10 (Primaerquelle direkt lesen) | im Adversarial-Check: Code **TIEF** direkt lesen statt nur RAG-Chunks. |
| `_R_orchestrate` KURZLEBIG_PROMPT + floor/middle/ceiling-Routing | House-Style der Worker-Spawns (1 Agent = 1 Aufgabe). |

### NEUE Seams (von BL-296 erzeugt — klar markiert)

- **NEU:** `.claude/analysis/pr-{id}-sim-answers.json` (schema-validierter Draft-Output, der
  Uebergabe-Seam zu `_pr_parkinglot_fill`).
- **NEU:** `{VAULT}/Findings/{pr_id}/tripel-{comment_id}.md` + `_pr_findings_index.md`
  (neue Vault-Root-Kategorie `Findings/`, AK7 — schliesst den Inquiry-Loop).
- **NEU:** Der **adversarial Steelman-Check** als Pflicht-Phase vor jeder Refutation (AK3,
  INV-PR-SIM-1 — der eigentliche CRUX dieses Skills).

---

## Ablauf (Schritt-fuer-Schritt)

### SCHRITT 0 — Entry + Reihenfolge-Gate (INV-PR-SIM-6)

```
[PR_SIM] entry-log: vault_root + $ARGUMENTS
Resolve-PrId aus active-pr.json (OverridePrId > active-pr.json > einzige state.json)
Lade active-pr.json -> hil_mode, branchRef, committer
Lade pr-{id}-state.json -> comments[]

GATE (INV-PR-SIM-6):
  FOR jeden aktiven comment c in comments[]:
    erwarte .claude/review/bob-monolog-{item(c)}.md
  IF irgendein bob-monolog fehlt:
    BLOCK + Recovery-Hint:
      "[PR_SIM] BLOCK: bob-monolog-{item} fehlt. _R_orchestrate noch nicht (vollstaendig)
       gelaufen. Rufe: /_R_orchestrate PR-{id} normal"
    Exitcode 1
```

> Korrektive Enforcement: der Block STALLT die Kette nicht — er nennt den Recovery-Befehl.

### PHASE 1 — DRAFT (middle/sonnet, PARALLEL, 1 Agent / Kommentar)

Pro aktivem Kommentar **ein** kurzlebiger Agent. Worker liest `bob-monolog-{item}.md`
und den `comments[]`-Eintrag, leitet die DISPOSITION ab und schreibt einen Draft.

**DISPOSITION-Routing (aus `schweregrad` des bob-monolog):**

| schweregrad | Default-Stance        | DISPOSITION-Tendenz                          |
|-------------|-----------------------|----------------------------------------------|
| KRITISCH    | agree + Fix-Plan      | `done` (umgesetzt) ODER `verify`             |
| WARN        | agree ODER begruendete Abweichung | `done` / `verify` / begruendet `refute` |
| INFO        | refute-Kandidat       | `refute` (Steelman-pflichtig, INV-PR-SIM-1)  |

**5 DISPOSITION-Klassen** (aus dem Gold-Lauf, 1:1):
`done | refute | verify | status | done-already-replied | refute-already-replied`
(`*-already-replied` = `is_my_response=true` im comments[]-Eintrag.)

```
[WORKER-MODE] PHASE 1 Draft — pr-{id}-{cid}-sim   (model: middle/sonnet)
Agent-Name: pr-{id}-{comment_id}-sim   Team: pr-{id}   Task-ID: {TASK_ID}

LIES:
- bob-monolog-{item}.md   (F1 Problem, F3 Fix-Plan, F4 RAG-Kongruenz, F5, schweregrad)
- comments[]-Eintrag      (text = Reviewer-Frage WOERTLICH, file, line, reviewer_name,
                           is_my_response)
- bei disp IN {done, verify}: echten Repo-Code an file:line (Read-Tool) lesen
  + `git show {hash}` / `git rev-parse {hash}` fuer Commit-Grounding (Full-Hash)

ENTSCHEIDE:
1. stance ∈ {agree, partial, refute}   (Default aus schweregrad-Tabelle)
2. disp   ∈ {done, refute, verify, status, done-already-replied, refute-already-replied}
3. sim_answer_text: bei agree -> Zustimmung + Fix-Plan (Text, KEIN Code);
                    bei refute -> Refutation (noch DRAFT — wird in PHASE 2 gehaertet)
4. bei disp=done/verify: commit_links = [kurzhash] (INV-PR-SIM-7); Full-Hash via rev-parse
5. bei disp=verify: Code ehrlich pruefen — umgesetzt? Sonst needs_work=true
   (NICHT beschoenigen — INV-PR-SIM-7)

REGELN:
- KEIN Code aendern, NUR analysieren+simulieren (INV-PR-SIM-4)
- KEINE internen Marker (INV-PR-SIM-2)
- KEIN Sub-Agent, KEIN Task-Tool

SCHREIBE (Rueckgabe an Team Lead, Schema):
  {n, question_id, question, disp, sim_answer_text, stance, commit_links,
   needs_work, grounded}

ABSCHLUSS:
TaskUpdate {TASK_ID} status=completed
SendMessage an "team-lead": "Draft {cid}: stance={stance} disp={disp}
   {needs_adversarial? '-> ADVERSARIAL' : ''}"
```

Team Lead sammelt alle Drafts. **Markiere fuer PHASE 2** jeden Draft mit
`stance=refute` ∨ `schweregrad=INFO` ∨ `F4=LOW` (RAG-Kongruenz niedrig).

### PHASE 2 — ADVERSARIAL STEELMAN (ceiling/opus, NUR markierte Drafts) — DER CRUX (INV-PR-SIM-1)

> **NIE** eine Refutation ausgeben ohne diesen Check. Ohne ihn rutscht der #2-cancelEdit-Fall
> als "STABLE" durch, obwohl der reaktive Pfad ihn praezisiert/kippt.

```
[WORKER-MODE] PHASE 2 Adversarial — pr-{id}-{cid}-adversarial   (model: ceiling/opus)
Agent-Name: pr-{id}-{comment_id}-adversarial   Team: pr-{id}   Task-ID: {TASK_ID}

EINGABE: der Draft (stance=refute ∨ INFO ∨ F4=LOW) + Reviewer-Frage + file:line

DREI PFLICHT-SCHRITTE:
(1) STEELMAN: Formuliere die REVIEWER-Position so STARK wie moeglich.
    "Wenn der Reviewer recht haette — was waere das staerkste Argument?"
(2) CODE TIEF LESEN (Read-Tool, SP-FIX-10-analog): nicht nur die genannte Zeile —
    verfolge den reaktiven/indirekten Pfad. (#2-Beispiel: effect() -> resetValidators()
    ist der eigentliche Pfad, nicht der oberflaechliche cancelEdit-Handler.)
(3) ENTSCHEID + flip_reason (PFLICHT bei FLIP/REFINED):
    - STABLE   : Refutation haelt unveraendert -> bleibt refute
    - FLIP     : Reviewer hat recht, Hypothese kippt zu agree -> stance=agree
                 (PL-Kandidat, flip_reason PFLICHT)
    - REFINED  : Refutation haelt, ABER praeziser formuliert (kein "echter Bug",
                 sondern "praezisere Refutation" — #2-Typ; flip_reason PFLICHT)

REGELN:
- KEIN Code aendern (INV-PR-SIM-4). KEINE internen Marker (INV-PR-SIM-2).

SCHREIBE (Rueckgabe): {cid, adversarial_result: {steelman, code_path_read,
   entscheid: STABLE|FLIP|REFINED, flip_reason}}

ABSCHLUSS:
TaskUpdate {TASK_ID} status=completed
SendMessage an "team-lead": "Adversarial {cid}: {entscheid} — {flip_reason 1 Satz}"
```

Team Lead merged `adversarial_result` in jeden betroffenen Draft:
- `FLIP`    -> `stance=agree`, `flip_status=FLIP`
- `REFINED` -> `stance=refute` (bleibt), `flip_status=REFINED`
- `STABLE`  -> `stance=refute` (bleibt), `flip_status=STABLE`
- Drafts ohne PHASE 2 (agree/partial, kein INFO/F4-LOW): `flip_status=PENDING` bzw.
  bei klaren agree-done-Items kein Flip-Risiko (`flip_status` bleibt `PENDING` bis IDF).

### PHASE 3 — POLISH / HUMANIFY (ceiling/opus, EINMAL ueber alle Drafts) — INV-PR-SIM-2/3

```
[WORKER-MODE] PHASE 3 Polish — pr-{id}-synthese-polish   (model: ceiling/opus)
Agent-Name: pr-{id}-synthese-polish   Team: pr-{id}   Task-ID: {TASK_ID}

EINGABE: alle gemergten Drafts (mit adversarial_result wo vorhanden)
KONTEXT : MEMORY feedback_pr_replies_humanify.md + _answer.md KURZFORM-Stil

HUMANIFY-REGELN (INV-PR-SIM-3):
- ECHTE Umlaute im Freitext (ae/oe/ue VERBOTEN; Code-Bezeichner in `Backticks`, ASCII)
- 2-4 Saetze pro Antwort, Dev-Kollegen-Ton (kein KI-/Tool-/Prozess-Jargon)
- Opener ueber ALLE N variieren (nicht jede Antwort startet gleich)
- Refutationen respektvoll formulieren (VERSTAENDNIS + BEGRUENDUNG + EVIDENCE-Andeutung,
  PR-REPLY-GUIDELINES per Referenz)
- KEINE internen Marker (DUC/Ring/PR2/PL/IDF/SDF) — INV-PR-SIM-2

SCHREIBE (Rueckgabe): finalMarkdown je Kommentar + flagged-Liste (alle needs_work=true)

ABSCHLUSS:
TaskUpdate {TASK_ID} status=completed
SendMessage an "team-lead": "Polish fertig: N Antworten, {len(flagged)} flagged"
```

### SCHRITT N — Persistenz (sim-answers.json + state.json + Findings-Tripel)

```
1. .claude/analysis/pr-{id}-sim-answers.json schreiben (SCHEMA, additionalProperties:false):
   [{ n, question_id, question, disp, sim_answer_text, stance,
      flip_status, flip_reason, needs_work, grounded, adversarial_result }]

2. pr-{id}-state.json: pro comment c die sim_answers nachtragen:
   comments[c].sim_answer = {disp, sim_answer_text, stance, flip_status, flip_reason,
                             needs_work, grounded, commit_links}

3. {VAULT}/Findings/{pr_id}/tripel-{comment_id}.md  (sim-Stadium, AK7):
   ---
   finding_id: "FND-{pr_id}-{comment_id}"
   pr_id: "{pr_id}"
   comment_id: "{ThreadId}"        # = question_id
   reviewer: "{Author}"
   file: "{File}"
   line: {Line}
   # --- DIE 4 TRIPEL-FELDER (AK7) ---
   frage: "{Reviewer-Kommentar WOERTLICH}"     # Input des Inquiry-Cycle
   sim_answer: "{simulierte Antwort, theory-Grad — inkl. adversarial-Entscheid}"
   parking_lot: null               # null hier; gesetzt von _pr_parkinglot_fill
   resulting_truth: ""             # leer hier; gefuellt von _pr_answer (nach IDF)
   flip_status: "PENDING | STABLE | REFINED | FLIP"
   # --- Provenance/Loop ---
   stance: "agree | refute | partial"
   disp: "done | refute | verify | status | done-already-replied | refute-already-replied"
   flip_reason: "{nur bei FLIP/REFINED}"
   code_verified: false
   commit_refs: []
   sim_answer_ref: ".claude/analysis/pr-{id}-sim-answers.json#{n}"
   final_answer_ref: ".claude/review/pr-{id}-answers.md#N"   # spaeter
   created: "2026-06-09"
   ---

4. {VAULT}/Findings/_pr_findings_index.md  (Index, analog _backlog_index.md):
   APPEND-Zeile je Tripel: | FND-{pr_id}-{cid} | {reviewer} | {file}:{line} |
                            {stance} | {flip_status} | tripel-{cid}.md |
```

### SCHRITT EXIT

```
hil_mode == true:
  STOPP. Gib frage + sim_answer je Kommentar lesbar aus (+ FLIP/REFINED explizit melden,
  z.B. "#2 cancelEdit: Refutation REFINED — effect() -> resetValidators() ist der
  reaktive Pfad").
  Hinweis: "HiL=true. Das HiL-Gate im Chain-Orchestrator stoppt hier — User postet die
  echten Antworten und gibt sie zurueck. (Single-Skill-Lauf: naechster Schritt manuell.)"

hil_mode == false:
  "N sim_answers erzeugt ({M} Refutationen adversarial gehaertet, {K} FLIP/REFINED).
   Naechster Schritt: /_pr_parkinglot_fill"

Exitcode 0.   ARGUMENTS: $ARGUMENTS
```

---

## INVARIANTEN (nummeriert)

**INV-PR-SIM-1 (load-bearing, AK3):** NIE eine `sim_answer` ausgeben ohne adversarial
Steelman-Check, wenn `stance=refute` ∨ `schweregrad=INFO` ∨ `F4=LOW`. Ohne den Check rutscht
der #2-cancelEdit-Fall als STABLE durch. Steelman = Reviewer-Position MAXIMAL stark machen +
Code TIEF direkt lesen (reaktiver/indirekter Pfad) + Entscheid (STABLE|FLIP|REFINED) loggen.

**INV-PR-SIM-2:** NIE interne Marker (DUC/Ring/PR2/PL/IDF/SDF/PR-Review) im
`sim_answer`-Output. Der Reviewer sieht reinen Dev-Kollegen-Ton (AK-Verifikation 486).

**INV-PR-SIM-3:** Humanify-Pflicht — ECHTE Umlaute im Freitext (`ae`/`oe`/`ue` VERBOTEN;
Code-Bezeichner in Backticks bleiben ASCII), 2-4 Saetze, Opener ueber alle N variieren, kein
KI-/Tool-/Prozess-Jargon (KURZFORM-Stil aus `_answer.md`).

**INV-PR-SIM-4:** NIE Code schreiben oder aendern (Analysis + Simulation only). Fix-Plaene
sind Text, keine Edits. Code-Fixes entstehen spaeter via `_IDF_orchestrate`.

**INV-PR-SIM-5:** `flip_status`-Semantik:
- `STABLE`  — Refutation haelt unveraendert.
- `FLIP`/`FLIPPED` — kippte zu agree (PL-Kandidat).
- `REFINED` — Refutation bleibt, aber praeziser (wie #2: nicht "echter Bug", sondern
  "praezisere Refutation").
- `PENDING` — sim-Stadium, Flip-Entscheid steht noch aus (agree-Items vor IDF).

`flip_reason` ist PFLICHT bei `FLIP` und `REFINED`.

**INV-PR-SIM-6:** Reihenfolge-Enforcement — blockt ohne `bob-monolog-{item}.md` (je aktivem
Kommentar). Recovery-Hint im Block: `"Rufe /_R_orchestrate PR-{id} normal"`.

**INV-PR-SIM-7:** Commit-Grounding bei `disp=done`/`disp=verify` — `[kurzhash](az-url)` via
`git rev-parse` (Full-Hash). `needs_work=true` setzen wenn `disp=verify` UND der Code NICHT
umgesetzt ist (NICHT beschoenigen — ehrliche `grounded`-Flag).

---

## Modell-Routing (House-Style, difficulty_scaling)

| Phase            | Tier            | Begruendung                                            |
|------------------|-----------------|--------------------------------------------------------|
| PHASE 1 Draft    | middle / sonnet | Breite, parallel — 1 Agent / Kommentar.                |
| PHASE 2 Adversarial | ceiling / opus | Tiefe Code-Verfolgung + Steelman — der teure, aber load-bearing Schritt; NUR fuer markierte Drafts. |
| PHASE 3 Polish   | ceiling / opus  | Konsistenter Dev-Ton + Opener-Variation ueber alle N.  |

`model`-Param ist Alias (bump-safe) und gewinnt gegen Agent-Def; NIE downgraden,
NIE `haiku` fuer mehrstufige Worker (Berater-Worker mind. sonnet).

---

## CHAIN-POSITION

```
_pr_init  ->  _pr_pull  ->  _R_orchestrate  ->  [ _pr_question_answer_sim ]  ->  [HiL-Gate]
   (AK1)       (AK1)          (AK2)                      (AK3 — HIER)            (im _pr_orchestrate)
                                                                                      |
                                                                                      v
                                          _pr_parkinglot_fill  ->  _IDF_orchestrate  ->  _pr_answer
                                                 (AK4)                  (AK5)               (AK6+AK7)
```

**Seam-Protokoll (datei-basiert, kein Input-Injection):**
- LIEST `bob-monolog-*.md` (von `_R_orchestrate`).
- SCHREIBT `pr-{id}-sim-answers.json` -> `_pr_parkinglot_fill` LIEST diese (filtert refute).
- SCHREIBT `Findings/{pr_id}/tripel-{cid}.md` (PENDING) -> `_pr_parkinglot_fill` traegt
  `parking_lot` nach -> `_pr_answer` fuellt `resulting_truth` + `flip_status` final
  (Loop-Schluss, AK7).
