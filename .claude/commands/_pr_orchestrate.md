---
name: _pr_orchestrate
status: active
version: 1.0.0
type: orchestration
op: PrInquiryCycle
phase: Meta
created: 2026-06-09
updated: 2026-06-09
chain_position: standalone
team_based: false
difficulty_scaling: false
feature_anchor: BL-296
related:
  - _pr_init
  - _pr_pull
  - _R_orchestrate
  - _pr_question_answer_sim
  - _pr_parkinglot_fill
  - _IDF_orchestrate
  - _pr_answer
---

# /_pr_orchestrate - PR-Inquiry-Pipeline Chain-Orchestrator (Team-Lead-Handschuh)

> **Rolle:** Verkettet die 7 Schritte der PR-Antwort-Pipeline deterministisch aus
> EINEM PR-Link. PR-Review ist eine Instanz des Inquiry-Cycle: jeder Reviewer-Kommentar
> = eine offene Frage, die simulierte Antwort = eine Hypothese (theory), die Maschinen-
> Implementierung = das Experiment, das die Hypothese am echten Code beweist (oder kippt).
> Dieser Orchestrator ist KEIN Fachlogik-Worker-Spawner — er LAEDT jeden Sub-Skill selbst
> via `Skill()` (INV-AO-CALLER). Alle Worker-Spawns leben INNERHALB der Sub-Skills.
>
> **REUSE-FIRST:** Die ganze Kette haengt bestehende Infra ein —
> `_pr_init`/`_pr_pull` (Azure/TFS-agnostischer Bootstrap+Fetch ueber `routing.json`),
> `_R_orchestrate` (Uncle-Bob-Urteil, UNVERAENDERT), `_IDF_orchestrate` (Maschinen-
> Implementierung, UNVERAENDERT). NEU verdrahtet sind nur die Seams: adversarial Steelman,
> Findings-Tripel, HiL-Param. Kein Greenfield.

---

```
+======================================================================+
| VERTRAG: /_pr_orchestrate v1.0.0 (BL-296)                            |
+======================================================================+
|                                                                       |
| LIEST:                                                                |
|   $ARGUMENTS = {link} [--hil=true|false] [--resume]                   |
|     {link} = Azure-DevOps- ODER TFS-PR-URL (einzige Pflicht-Eingabe)  |
|   .claude/meta/pr/active-pr.json                                      |
|     (Chain-State: prId, hil_mode, committer, chain_phase)             |
|   .claude/analysis/pr-{id}-state.json                                 |
|     (comments[].status, findings_tripel[] — Resume-Punkt)             |
|   .claude/analysis/pr-{id}-sim-answers.json                           |
|     (Existenz = answer_sim gelaufen)                                  |
|   .claude/review-{prId}-queue.md                                      |
|     (Existenz = pull gelaufen)                                        |
|   .claude/review/bob-monolog-*.md                                     |
|     (Existenz = R_orchestrate gelaufen)                               |
|                                                                       |
| SCHREIBT (NUR Chain-State, KEINE Fachdaten):                          |
|   .claude/meta/pr/active-pr.json                                      |
|     chain_phase: init|pull|reviewed|sim_done|hil_wait                 |
|                  |pl_filled|implemented|answered                      |
|   .claude/analysis/pr-{id}-state.json                                 |
|     (Phase-Stempel pro Seam — chain_phase + last_seam_at)             |
|                                                                       |
| RUFT (Sub-Skills via Skill(), INV-AO-CALLER — Team Lead SELBST):      |
|   Skill(_pr_init,                args='{link} [--hil]')   [NEU]        |
|   Skill(_pr_pull)                                         [REUSE fetch.ps1]
|   Skill(_R_orchestrate,          args='PR-{id} normal')   [UNVERAENDERT]
|   Skill(_pr_question_answer_sim)                          [NEU, CRUX]  |
|   Skill(_pr_parkinglot_fill)                              [NEU]        |
|   Skill(_IDF_orchestrate, args='{committer_bl} --pl-only --from=sdf_finish') [UNVERAENDERT]
|   Skill(_pr_answer)                                       [NEU]        |
|                                                                       |
| RUFT NICHT (verboten):                                                |
|   KEIN Agent(general-sonnet, prompt='orchestrate...') (Mega-Agent!)   |
|   KEIN Worker-Spawn im Chain-Orchestrator selbst                      |
|                                                                       |
| INVARIANTEN:                                                          |
|   INV-PR-ORC-1: Team Lead laedt jeden Sub-Skill via Skill() selbst.   |
|   INV-PR-ORC-2: HiL-Gate (AK8) — hil=true STOPP nach answer_sim.      |
|   INV-PR-ORC-3: Reihenfolge-Enforcement je Seam + Recovery-Hint.      |
|   INV-PR-ORC-4: KEINE internen Marker (DUC/Ring/PR2) im Output.       |
|   INV-PR-ORC-5: Azure-agnostisch — Kette laeuft nur aus {link}.       |
|   INV-PR-ORC-6: Re-Lauf 486 reproduziert 16 Antworten + #2-Flip.     |
+======================================================================+
```

---

```
+======================================================================+
| META-COMMAND: /_pr_orchestrate                                       |
+======================================================================+
|                                                                      |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)             |
| SUB-SKILLS (via Skill(), KEINE direkten Worker hier):              |
|   1. _pr_init               [NEU, sonnet]   PR-Kontext + Identitaet |
|   2. _pr_pull               [REUSE, sonnet] Kommentare -> Queue     |
|   3. _R_orchestrate         [UNVERAENDERT]  Uncle-Bob-Urteil        |
|   4. _pr_question_answer_sim[NEU, opus]     Hypothese + adversarial |
|   5. _pr_parkinglot_fill    [NEU, sonnet]   agree -> PL-Items       |
|   6. _IDF_orchestrate       [UNVERAENDERT]  Maschine implementiert  |
|   7. _pr_answer             [NEU, opus]     Endantwort am echten Code|
|                                                                      |
| ZWECK: Aus EINEM PR-Link autonome (oder HiL-pausierte) Erzeugung    |
|   von belastbaren, am echten Diff verankerten PR-Antworten.        |
|   PR-Reviewer = 3. Stakeholder. Jeder Kommentar = offene Frage.    |
|   Simulierte Antwort = Hypothese; IDF beweist sie am Code.         |
|                                                                      |
| PRINZIP: 1 Sub-Skill = 1 Schritt = dateibasierter Seam danach.    |
|   State lebt in Dateien (active-pr.json + pr-{id}-state.json),     |
|   nicht im Orchestrator-Kontext. Jeder Seam ist State-gepruft.    |
|   Worker-Spawns AUSSCHLIESSLICH innerhalb der Sub-Skills.         |
|                                                                      |
| CHAIN: init -> pull -> R_orchestrate -> answer_sim ->             |
|        [HiL-Gate] -> parkinglot_fill -> IDF -> answer             |
|                                                                      |
| ABGRENZUNG:                                                         |
|   NICHT _Post_PR_orchestrate (das ist die alte TFS-Gruppen-Logik) |
|   NICHT ein Worker selbst (kein Code, kein Fetch, keine REST hier) |
|   PR-Review = "Reviewer fragt, Hypothese antwortet, Code beweist" |
+======================================================================+
```

---

## CHAIN-POSITION

```
                {PR-Link}
                    |
                    v
   /_pr_orchestrate {link} [--hil] [--resume]   <== DU BIST HIER
                    |
   1. Skill(_pr_init)          --> active-pr.json {prId, committer, hil_mode}
                    |               + pr-{id}-state.json (leer)
   2. Skill(_pr_pull)          --> fetch.ps1 -> pr-{id}-raw.json
                    |               -> comments[] + review-{prId}-queue.md
   3. Skill(_R_orchestrate)    --> bob-monolog-{item}.md + PRAESENTATION
                    |               (UNVERAENDERT eingehaengt)
   4. Skill(_pr_question_answer_sim) --> sim-answers.json
                    |               + Findings-Tripel (PENDING)
                    |
        +===== HiL-GATE (AK8) =====+
        | hil=true  -> STOPP        |  User postet echte Antwort,
        |              (hil_wait)    |  ruft --resume
        | hil=false -> weiter        |
        +===========================+
                    |
   5. Skill(_pr_parkinglot_fill) --> PL-Items (Refutationen ausgelassen)
                    |
   6. Skill(_IDF_orchestrate)  --> Maschine implementiert, echte Commits
                    |               (UNVERAENDERT)
   7. Skill(_pr_answer)        --> pr-{id}-answers.md (readable)
                    |               + Findings-Tripel-Loop-Schluss
                    v
            {fertige Antworten — User pastet 1-by-1}
```

---

## Aufruf

```
/_pr_orchestrate {link} [--hil=true|false] [--resume]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|--------------|
| `{link}` | (PFLICHT) | Azure-DevOps- ODER TFS-PR-URL | Einzige Pflicht-Eingabe. PrId/Org/Project/Repo werden daraus extrahiert (`_pr_init`). |
| `--hil` | (siehe Aufloesung) | `true` \| `false` | Human-in-the-Loop. `true` = Stopp nach `answer_sim`, User postet echte Antwort. `false` = vollauto bis readable `.md`. |
| `--resume` | (aus) | Flag | Re-Entry nach HiL-Stopp ODER nach Abbruch. Liest `chain_phase` und macht ab dort weiter. |

**HiL-Aufloesung (Prioritaet, gesetzt von `_pr_init`, INV-PR-INIT-3):**
```
hil_mode = --hil-Argument  >  routing.json hil_mode  >  Default true
```
Persistiert in `active-pr.json.hil_mode` + `pr-{id}-state.json.hil_mode` (Single-Source der Chain).

**Beispiele:**
```
/_pr_orchestrate https://dev.azure.com/ITSGGMBH/AP0071.../_git/DCSRE/pullrequest/20
    -> hil_mode aus routing.json (Default true): autonom bis answer_sim, dann STOPP

/_pr_orchestrate https://tfs.itsg.de/.../pullrequest/18979 --hil=false
    -> vollauto bis .claude/review/pr-18979-answers.md (echte Commit-Hashes)

/_pr_orchestrate https://dev.azure.com/.../pullrequest/20 --resume
    -> nach HiL-Paste: parkinglot_fill -> IDF -> answer
```

---

## QUICK-START / VERIFIKATIONS-TESTCASE (INV-PR-ORC-6)

**DCSRE-486** ist das manuell gefahrene Referenz-Beispiel (Gold-Lauf 2026-06-08,
`pr-replies-dcsre486-wf.js` + `DCSRE-486-pr-replies-final-2026-06-08.md`). Ein Re-Lauf
der Kette MUSS:

1. die **16 Antworten** reproduzieren (gleiche DISPOSITION-Klassen, gleiche Commit-Anker),
2. die **#2-cancelEdit-Refutation** im adversarial Steelman-Check (PHASE 2 von
   `_pr_question_answer_sim`) als **REFINED** einfangen — die simulierte Refutation
   ("`cancelEdit` oeffnet nur den Confirm-Dialog") wird durch tiefes Code-Lesen praezisiert
   (`effect() -> resetValidators()` ist der reaktive Pfad), bleibt aber Refutation, KEIN Bug,
3. **KEINE internen Marker** (DUC/Ring/PR2/PR-Review) im finalen `.md` enthalten.

Schlaegt einer der 3 Punkte fehl, ist die Chain nicht regression-frei.

---

## VORAUSSETZUNGEN / OFFENE INFRA-PATCHES

Diese Kette setzt 4 kleine, gezielte Patches an bestehender Infra voraus (von den
Sub-Skill-Specs getragen, hier nur zur Vollstaendigkeit):

| # | Patch | Wo | Warum |
|---|-------|-----|-------|
| 1 | `INV-PL-WRITER-1` um 4. Writer `d) _pr_parkinglot_fill` ergaenzen | `_parking-lot.md` | sonst verletzt jeder PL-Append Single-Writer |
| 2 | `routing.json` neue Felder `hil_mode`, `pathPrefix`, `tfs_compat` | `.claude/meta/pr/routing.json` | HiL-Default + Azure-Agnostik |
| 3 | `fetch.ps1` `pathPrefix`-Parametrisierung statt hardcoded `/Sources/Backend/` | `fetch.ps1` | Azure-agnostischer Fetch |
| 4 | NEUE Vault-Root-Kategorie `{VAULT}/Findings/` anlegen | Vault | Findings-Tripel-Heimat (AK7) |

---

## ABLAUF (Pseudocode, Schritt-fuer-Schritt)

### SCHRITT 0 — Entry + Resume-Erkennung

```
[PR_ORC] entry-log: vault_root + $ARGUMENTS (link, --hil, --resume)

link        = parse_first_positional($ARGUMENTS)
resume_flag = "--resume" in $ARGUMENTS

# Resume-Erkennung (zwei Quellen, redundant):
IF resume_flag OR existiert(.claude/meta/pr/active-pr.json):
    state       = lies(active-pr.json)
    chain_phase = state.chain_phase     # init|pull|reviewed|sim_done|hil_wait|pl_filled|implemented|answered
    # Fallback bei fehlendem chain_phase: Datei-Existenz-Probe
    IF chain_phase == null:
        chain_phase = probe_phase_from_files()   # siehe Tabelle unten
    resume_ab = next_phase_after(chain_phase)
ELSE:
    chain_phase = "fresh"
    resume_ab   = "init"

Logge: "[PR_ORC] resume_ab={resume_ab} (chain_phase={chain_phase})"
```

**Datei-Existenz-Probe (Fallback wenn `chain_phase` fehlt):**

| Datei existiert | => chain_phase ist mindestens |
|-----------------|-------------------------------|
| `active-pr.json` | `init` |
| `review-{prId}-queue.md` | `pull` |
| `bob-monolog-*.md` | `reviewed` |
| `pr-{id}-sim-answers.json` | `sim_done` |
| PL-Items mit `source=pr_review` | `pl_filled` |
| `code_verified=true` in state.json | `implemented` |
| `pr-{id}-answers.md` | `answered` |

---

### SCHRITT 1 — _pr_init  [NEU, sonnet]  (AK1)

```
IF resume_ab in {pull, reviewed, sim_done, hil_wait, pl_filled, implemented, answered}:
    SKIP (init bereits gelaufen — active-pr.json vorhanden)
ELSE:
    Skill(_pr_init, args="{link} {--hil falls gesetzt}")
    # _pr_init: Link -> PrId/Org/Project/Repo, committer aus routing.json
    #          (auth.myDisplayName/credentialKey — NIE git config),
    #          hil_mode aufloesen, active-pr.json + pr-{id}-state.json (leer) anlegen.
    set_chain_phase("init")
```

**Seam:** `active-pr.json {prId, prUrl, platform, committer, hil_mode}` + `pr-{id}-state.json`
(Grundstruktur, `comments[]`+`findings_tripel[]` leer).

> Ab hier ist `{id}` = `prId` aus `active-pr.json` (Resolve-PrId). `hil_mode` ist gesetzt.

---

### SCHRITT 2 — _pr_pull  [REUSE fetch.ps1, sonnet]  (AK1)

```
IF resume_ab in {reviewed, sim_done, hil_wait, pl_filled, implemented, answered}:
    SKIP (Queue bereits vorhanden)
ELSE:
    Skill(_pr_pull)
    # _pr_pull: fetch.ps1 (parametrisiert, pathPrefix aus routing.json)
    #          -> pr-{id}-raw.json -> comments[] (1 Kommentar = 1 Frage)
    #          -> review-{prId}-queue.md im _R_orchestrate-Pflichtformat
    #             (## Item N / **Datei:** / **Zeilen:** / **Frage:** / **Code:**).
    set_chain_phase("pull")
```

**Seam:** `.claude/review-{prId}-queue.md` (dateibasiert — `_R_orchestrate` liest nur Dateien).

---

### SCHRITT 3 — _R_orchestrate  [UNVERAENDERT eingehaengt]  (AK2)

```
IF resume_ab in {sim_done, hil_wait, pl_filled, implemented, answered}:
    SKIP (bob-monolog vorhanden)
ELSE:
    Skill(_R_orchestrate, args="PR-{id} normal")
    # UNVERAENDERT: Uncle-Bob-Urteil pro Queue-Item (RAG + Bob-Monolog + Synthese).
    # Liefert code-gegruendetes Urteil je Kommentar BEVOR simuliert wird.
    set_chain_phase("reviewed")
```

**Seam:** `.claude/review/bob-monolog-{item}.md` + `PRAESENTATION-PR-{id}-*.md`.

> `_R_orchestrate` ist hier 1:1 das bestehende Code-Review-Skill — kein PR-spezifischer
> Glue-Code. Die `review-{prId}-queue.md` aus Schritt 2 ist exakt das Format, das es erwartet.

---

### SCHRITT 4 — _pr_question_answer_sim  [NEU, opus]  (AK3, DER CRUX)

```
# INV-PR-ORC-3 Seam-Gate VOR dem Aufruf:
IF NOT existiert(.claude/review/bob-monolog-*.md):
    BLOCK + Recovery-Hint:
      "[PR_ORC] answer_sim blockiert: bob-monolog fehlt.
       Rufe: /_R_orchestrate PR-{id} normal"
    STOPP

IF resume_ab in {pl_filled, implemented, answered}:
    SKIP (sim-answers.json vorhanden)
ELSE:
    Skill(_pr_question_answer_sim)
    # Pro Kommentar simulierte Antwort als Hypothese (theory):
    #   PHASE 1 DRAFT (sonnet parallel, 1 Agent/Comment) — DISPOSITION-Routing
    #   PHASE 2 ADVERSARIAL (opus, NUR refute|INFO|F4=LOW) — Steelman PFLICHT,
    #           Code TIEF lesen, Entscheid STABLE|FLIP|REFINED  <== faengt #2-Flip
    #   PHASE 3 POLISH/HUMANIFY (opus, einmal) — Dev-Ton, ECHTE Umlaute, keine Marker
    # Schreibt sim-answers.json + Findings-Tripel (flip_status=PENDING).
    set_chain_phase("sim_done")
```

**Seam:** `.claude/analysis/pr-{id}-sim-answers.json` + `{VAULT}/Findings/{id}/tripel-*.md` (PENDING).

---

### SCHRITT 5 — HiL-GATE  (AK8, INV-PR-ORC-2)

```
hil_mode = lies(active-pr.json).hil_mode

IF hil_mode == true AND chain_phase != reaching_resume_past_hil:
    set_chain_phase("hil_wait")
    Gib aus: die simulierten Antworten (frage + sim_answer pro Kommentar)
             + Findings-Tripel-Stand (PENDING).
    Markiere FLIP/REFINED explizit (z.B. "#2 cancelEdit: Refutation REFINED").
    STOPP mit Hinweis:
      "HiL aktiv. Lies die simulierten Antworten, poste die ECHTEN Antworten im PR,
       gib sie zurueck. Dann: /_pr_orchestrate {link} --resume
       -> parkinglot_fill -> IDF -> _pr_answer (nimmt deine echte Antwort als Basis,
          INV-PR-ANS-6)."
    RETURN   # Kette pausiert hier sauber

ELSE:   # hil_mode == false ODER --resume nach HiL-Paste
    weiter mit SCHRITT 6
```

> Das HiL-Gate sitzt AUSSCHLIESSLICH hier im Orchestrator — die Sub-Skills bleiben
> einzeln aufrufbar/testbar. `_pr_question_answer_sim` liest `hil_mode` nur informativ
> (gibt am Ende einen STOPP-Hinweis aus statt `parkinglot_fill` anzudeuten).

---

### SCHRITT 6 — _pr_parkinglot_fill  [NEU, sonnet]  (AK4)

```
# INV-PR-ORC-3 Seam-Gate:
IF NOT existiert(pr-{id}-sim-answers.json):
    BLOCK + Recovery-Hint:
      "[PR_ORC] parkinglot_fill blockiert: sim-answers.json fehlt.
       Rufe: /_pr_question_answer_sim"
    STOPP

IF resume_ab in {implemented, answered}:
    SKIP (PL-Items bereits angelegt)
ELSE:
    Skill(_pr_parkinglot_fill)
    # Filtert auf zustimmende Code-Kommentare (stance agree|partial, ODER FLIP refute->agree).
    # REFUTATIONEN (stance=refute, auch REFINED) erzeugen KEINE Items (AK4).
    # PL-Items IDF-kompatibel, source='pr_review', BL-Kontext = BL des Committers
    # (aus active-pr.json) — NICHT BL-296. APPEND-ONLY.
    set_chain_phase("pl_filled")
```

**Seam:** `{bl_slug}/6_PL/{bl_id}-parking-lot.md` (neue Items) + `parking_lot`-Ref in Findings-Tripel
+ `manifest.parking_lot_modified_since_last_idf=true`.

---

### SCHRITT 7 — _IDF_orchestrate  [UNVERAENDERT eingehaengt]  (AK5)

```
committer_bl = lies(active-pr.json).committer_bl_id   # BL des Committers, NICHT BL-296

IF resume_ab == answered:
    SKIP (IDF gelaufen, code_verified=true)
ELSE:
    Skill(_IDF_orchestrate, args="{committer_bl} --pl-only --from=sdf_finish")
    # UNVERAENDERT: Maschine implementiert die PL-Items, erzeugt echte Commits.
    # Flip-Erlaubnis (AK5): die Hypothese DARF beim echten Implementieren kippen.
    set_chain_phase("implemented")
```

**Seam:** echte Commits im Ziel-Repo + `code_verified` in den umgesetzten `comments[]`.

> `_IDF_orchestrate` liest die PL-Items als normale Backlog-Items — kein PR-Wissen noetig.
> `source='pr_review'`/`provenance='pr_review'` (von `_pr_parkinglot_fill` gesetzt) verhindert,
> dass `_IDF_berater_plBewertung` pessimistisch `srs=100`/`Bottleneck=SC` waehlt.

---

### SCHRITT 8 — _pr_answer  [NEU, opus]  (AK6 + AK7)

```
# INV-PR-ORC-3 Seam-Gate:
IF NOT code_verified_fuer_zustimm_items(pr-{id}-state.json):
    BLOCK + Recovery-Hint:
      "[PR_ORC] answer blockiert: code_verified=false (IDF nicht gelaufen /
       Item nicht umgesetzt). Rufe: /_IDF_orchestrate {committer_bl} --pl-only --from=sdf_finish"
    STOPP

Skill(_pr_answer)
# Finale Antworten am ECHTEN Code: git rev-parse Full-Hash + Get-CommitWebUrl (link.ps1)
#   -> [kurzhash](az-url). flip_status final (CONFIRMED|FLIPPED|REFINED) aus Code-Realitaet.
# Schreibt pr-{id}-answers.md (readable, humanifiziert, KEINE Marker)
#   + Findings-Tripel-Loop-Schluss (resulting_truth + commit_refs) -> AK7.
# Bei hil_mode=true: Basis ist die echte User-Antwort, _pr_answer ist Formatierungs-Hilfe
#   + Commit-Verankerung (INV-PR-ANS-6).
set_chain_phase("answered")
```

**Seam:** `.claude/review/pr-{id}-answers.md` (readable) + Findings-Tripel geschlossen.

---

### SCHRITT EXIT

```
Gib aus: .claude/review/pr-{id}-answers.md (readable, User pastet 1-by-1 in den PR).
Melde explizit jeden FLIP/REFINED:
    z.B. "#2 cancelEdit: Refutation REFINED durch adversarial-check
          (effect()->resetValidators() ist der reaktive Pfad, kein Bug)."
Logge: "[PR_ORC] exit chain_phase=answered, {N} Antworten, {R} Refutationen,
        {F} Flips/Refinements."
Exitcode 0.
```

---

## INVARIANTEN

1. **INV-PR-ORC-1 (INV-AO-CALLER):** Der Team Lead (DU) laedt JEDEN Sub-Skill selbst via
   `Skill()` — direkt nach diesem `Skill(_pr_orchestrate)`-Load. **VERBOTEN:** den
   Orchestrator oder einen Sub-Skill via `Agent(general-sonnet, prompt="orchestrate ...")`
   delegieren. Sonst wird der Sub-Agent zum Mega-Agent (interpretiert die
   `Skill(...)`-Stellen als Inline-Logik statt zu laden). Worker-Spawns leben
   AUSSCHLIESSLICH innerhalb der Sub-Skills (`answer_sim`/`answer`/`R_orchestrate`) —
   NIE im Chain-Orchestrator.

2. **INV-PR-ORC-2 (HiL-Gate, AK8):** Bei `hil_mode=true` STOPP nach
   `_pr_question_answer_sim` (`chain_phase=hil_wait`), gibt `frage+sim_answer` aus, wartet
   auf User-Paste. Re-Entry nur ueber `--resume` -> `parkinglot_fill -> IDF -> answer`.
   Bei `hil_mode=false` laeuft die Kette vollauto bis `pr-{id}-answers.md`. Das Gate sitzt
   AUSSCHLIESSLICH hier (nicht in den Sub-Skills — die bleiben einzeln testbar).

3. **INV-PR-ORC-3 (Reihenfolge-Enforcement je Seam):** `answer_sim` blockt ohne
   `bob-monolog`; `parkinglot_fill` blockt ohne `sim-answers.json`; `answer` blockt ohne
   IDF-`code_verified`. Jeder Block traegt einen **Recovery-Hint** (korrektive Enforcement —
   blocken UND den Weg zeigen, nicht nur blocken).

4. **INV-PR-ORC-4 (keine Marker):** NIE interne Marker (DUC/Ring/PR2/PR-Review/PL/IDF/SDF)
   im finalen Output. Der Reviewer sieht ausschliesslich Dev-Sprache mit ECHTEN Umlauten
   (AK-Verifikation 486). Die Inquiry-Cycle-Begriffe sind interne Modellierung, kein
   Output-Vokabular.

5. **INV-PR-ORC-5 (Azure-agnostisch):** Die ganze Chain laeuft nur aus `{link}`; KEINE
   TFS-Hardcodes. Platform-Aufloesung (Azure-DevOps vs. TFS) ist an `routing.json`
   delegiert (via `_pr_init`/`_pr_pull`). Der Orchestrator kennt keine REST-URLs.

6. **INV-PR-ORC-6 (Verifikation):** Ein Re-Lauf gegen DCSRE-486 muss die 16 Antworten
   reproduzieren UND den #2-cancelEdit-Flip im adversarial-check als REFINED einfangen
   (siehe QUICK-START). Regressions-Anker der Pipeline.

---

## REUSE-MAP (was wiederverwendet wird — kein Greenfield)

| Sub-Skill | Reuse aus bestehender Infra | NEU |
|-----------|------------------------------|-----|
| `_pr_init` | `routing.json` + `_common.ps1` (Get-AuthHeaders/Resolve-PrId), `active-pr.json`-Mechanismus | Link-Extraktion ersetzt `PrId=18979`-Hardcode aus `pr-init.md` |
| `_pr_pull` | `fetch.ps1` (Thread-Abruf), `raw.json`-Format, Queue-Format aus `_R_orchestrate.md` | `pathPrefix`-Parametrisierung; 1:1 Frage-Mapping |
| `_R_orchestrate` | **UNVERAENDERT** — Uncle-Bob-Pipeline | — (nur eingehaengt) |
| `_pr_question_answer_sim` | `bob-monolog`, PR-REPLY-GUIDELINES, `pr-replies-dcsre486-wf.js` (DISPOSITION-Enum, DRAFT_SCHEMA), `humanify`-Dev-Stil, `feedback_pr_replies_humanify.md` | adversarial Steelman-Check; Findings-Tripel |
| `_pr_parkinglot_fill` | `_parking-lot.md` (`resolve_write_path`/`get_next_pl_id`), IDF-Item-Format | 4. PL-Writer; `provenance='pr_review'` |
| `_IDF_orchestrate` | **UNVERAENDERT** — Maschinen-Implementierung | — (nur eingehaengt) |
| `_pr_answer` | `link.ps1`/`Get-CommitWebUrl`, PR-REPLY-GUIDELINES (normativ referenziert), `_answer.md` KURZFORM | Findings-Tripel-Loop-Schluss; `flip_status` final |
| `_pr_orchestrate` (dieses) | INV-AO-CALLER (CLAUDE.md), `pr-{id}-state.json`-Schema, VERTRAG-Box/CHAIN-POSITION-House-Style aus `_R_orchestrate`/`_A_postRoute` | HiL-Gate; deterministische 7-Seam-Verkettung |

> **Abgrenzung zu `_Post_PR_orchestrate`:** Das bestehende `_Post_PR_orchestrate` ist die
> aeltere TFS-Gruppen-orientierte PR-Review-Orchestrierung. `_pr_orchestrate` ist die
> BL-296-Inquiry-Cycle-Variante (1 Kommentar = 1 Frage, Findings-Tripel, HiL-Param,
> Azure-agnostisch). Sie ersetzt die `pr-*`-Einzel-Commands NICHT, sondern verkettet die
> neue `_pr_*`-Familie deterministisch.

---

## FEHLERFAELLE & RECOVERY

| Situation | Verhalten |
|-----------|-----------|
| `bob-monolog` fehlt bei Schritt 4 | BLOCK + Hint `/_R_orchestrate PR-{id} normal` |
| `sim-answers.json` fehlt bei Schritt 6 | BLOCK + Hint `/_pr_question_answer_sim` |
| `code_verified=false` bei Schritt 8 | BLOCK + Hint `/_IDF_orchestrate {committer_bl} --pl-only --from=sdf_finish` |
| Aktive `active-pr.json` mit ANDERER PrId | `_pr_init` warnt (kein-konkurrierender-Edit), nicht stumm ueberschreiben |
| `--resume` ohne vorhandenen Chain-State | Datei-Existenz-Probe (SCHRITT 0); wenn nichts gefunden -> behandeln wie `fresh` |
| HiL aktiv, User noch nicht zurueck | `chain_phase=hil_wait` bleibt; erneutes `--resume` vor Paste -> erneuter STOPP-Hinweis |

ARGUMENTS: $ARGUMENTS.
