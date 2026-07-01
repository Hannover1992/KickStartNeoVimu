---
type: satellite
---

# A-Pipeline - Tiefen-Narrative (Assay-Format)

Zeige Assay-tiefe Phase-Essays der A-Pipeline post-BL-142.

## Aufruf

```
/_A_help_extended
```

---

## EINE METAPHER VORAUS

Stell dir A als **Steuerberater vor, der Roh-Daten sammelt** — bevor irgendjemand
ein Konto eroeffnet, eine Investition taetigt oder eine Steuererklaerung
einreicht. Der Steuerberater entscheidet NICHTS ueber dein Geld; er sammelt nur
Belege, ordnet sie, beschriftet sie, legt sie in der richtigen Akte ab. Wer dann
investiert (IDF), wer das Tempo bestimmt (SDF), wer die Steuererklaerung schreibt
(I) — das ist nicht seine Aufgabe.

A ist genau das: ein Materialsammler mit fester Akten-Ordnung, der seine Arbeit
**vor** der eigentlichen Entscheidungs-Maschinerie verrichtet. Kein Mode, kein
Routing-Detail, keine PL-Items — nur Wissensbasis und eine reife BL-Item-Huelle.

Die Daseinsberechtigung von A ist die **Anti-Stille-Post-Garantie**: Wenn IDF
und SDF spaeter Entscheidungen treffen, lesen sie kanonisierte Artefakte
(Task/Model/Spec/K-Score/Gap), nicht Heresay. So bleiben Begruendungs-Ketten
intakt — selbst wenn Tage zwischen A und SDF liegen.

---

## PHASE 0.0 — Cleanup + TeamCreate

**Was die Phase tut:** Raeumt verwaiste Vorgaenger-Teams auf (Stale-Detection
>24h), startet ein neues Team mit Naming `a-{NAME}` (z.B. `a-BL-142`).

**Daseins-Berechtigung:** Ohne Cleanup haengen Tasks aus abgebrochenen Sessions
in Limbo. Ohne klares Naming kann ein Beobachter nicht erkennen, welche Schicht
gerade arbeitet — IDF und SDF haben eigene Praefixe (idf-, sdf-).

**Inputs:** `active_team` aus state, Stale-Schwelle 24h.
**Outputs:** Frischer Team-Kontext mit `a-{NAME}` als Praefix.
**Konsumenten:** Alle nachfolgenden Phasen lesen aus diesem Team-Kontext.

**Drei Beispiele:**
1. Vorgaenger `a-BL-141` ist >24h alt → Cleanup, neues Team `a-BL-142`.
2. Aktueller Task ist Resync auf bestehendem Team → kein Cleanup, gleicher
   Team-Name.
3. Nachfolger soll IDF sein → Naming-Wechsel zu `idf-BL-142` erst dort, A
   bleibt `a-BL-142`.

---

## PHASE 0.1 — Modus-Erkennung (fresh / resync)

**Was die Phase tut:** Berater liest Manifest und Backlog-Eintrag, klassifiziert:
fresh (kein bestehender BL-Eintrag) vs resync (BL-Eintrag existiert, soll
aktualisiert werden). Steuert die Tasks fuer Phase 0.15.

**Daseins-Berechtigung:** Fresh und resync verlangen unterschiedliche Tasks. Bei
fresh muessen Findings extrahiert, Task definiert, Model neu gebaut werden. Bei
resync reicht haeufig ein Update einzelner Artefakte. Ohne diese Klassifikation
wird entweder zu viel oder zu wenig getan.

**Inputs:** Backlog-Eintrag (existiert? reifegrad?), Manifest-State.
**Outputs:** `mode = fresh | resync`, geladen in Team-State.
**Konsumenten:** Phase 0.15 Tasks-Generator.

**Drei Beispiele:**
1. Neue Aufgabe → fresh → volle Pipeline 0.0–5.
2. BL-142 wurde teilweise bearbeitet, soll aufgefrischt werden → resync → nur
   Phasen 3a–5 wiederholen.
3. BL-Item ist FRISCH, aber Wissensbasis fehlt → fresh ueberlagert resync.

---

## PHASE 0.15 — Tasks + Dependencies vorab

**Was die Phase tut:** Erstellt alle Tasks fuer den Run (mit
Dependency-Graph) im Voraus. Tasks sind Einheiten, die Workers spaeter
abarbeiten.

**Daseins-Berechtigung:** Vorab-Erstellung erlaubt parallele Worker-Spawns mit
sauberen Dependencies. Ohne Vorab-Plan muesste der Team Lead jede Task einzeln
erfinden — Race Conditions, Doppelt-Ausfuehrungen, fehlende Reihenfolge waeren
die Folge.

**Inputs:** Mode aus Phase 0.1, BL-ID, Parameter (name, pr, --parent-pr).
**Outputs:** Task-Liste mit Dependencies (`depends_on`).
**Konsumenten:** Phase 5 (Phasen-Ausfuehrung).

**Drei Beispiele:**
1. fresh + name=auto → Task Phase 0.2 + 0.5 ohne Dependency, dann Kette.
2. fresh ohne name=auto → Phase 0.2 entfaellt, Phase 0.5 ist Start.
3. resync → Tasks 3a–5 mit Dependencies, fruehere Phasen entfallen.

---

## PHASE 0.2 — Discovery (optional name=auto)

**Was die Phase tut:** Wenn der User keine BL-ID kennt, scannt Discovery den
Parking-Lot und schlaegt das naechste reife Item vor.

**Daseins-Berechtigung:** Bei langlaufenden Projekten ist die naechste Aufgabe
nicht immer offensichtlich. Discovery delegiert die Auswahl an einen Berater,
der Backlog-Status, Reifegrad und Routing-Hints liest.

**Inputs:** `_parking-lot.md`, Backlog-Status.
**Outputs:** Empfohlene BL-ID + Begruendung.
**Konsumenten:** Phase 0.5 (Findings-Extraktion uebernimmt diese ID).

**Drei Beispiele:**
1. Parking-Lot hat 3 reife Items → Discovery waehlt das mit hoechstem K-Score.
2. Parking-Lot leer → Discovery meldet `no_candidate`, Pipeline bricht ab.
3. User uebergab BL-142 explizit → Phase 0.2 entfaellt komplett.

---

## PHASE 0.5 — Findings-Extraktion (Wellen 3D+1S Opus)

**Was die Phase tut:** Liest pileOfMud / User-Notes / Vault-Hints, extrahiert
Findings in 3 Discovery-Wellen + 1 Synthese-Welle (alle Opus). Ergebnis: ein
Findings-Block, der spaeter zu Task.md wird.

**Daseins-Berechtigung:** Findings sind die **Roh-Beobachtungen**, nicht die
Aufgabe selbst. Die Trennung Findings → Task verhindert, dass Annahmen aus
fluechtigen User-Texten direkt zu Aufgaben mutieren. Drei Wellen erzwingen
Mehrfachprueefung; eine Synthese-Welle macht den Konsens explizit.

**Inputs:** pileOfMud, User-Hints, Vault.
**Outputs:** Findings-Liste (zur HiL-Pruefung in 0.5.2).
**Konsumenten:** Phase 0.5.2 (Review), Phase 0.6 (taskDefinition).

**Drei Beispiele:**
1. User schreibt "Mir faellt auf, dass Modul X stark mit Y koppelt." →
   Finding: Coupling-Vermutung, kein Auftrag.
2. Drei Wellen widersprechen sich → Synthese markiert Dissens, HiL entscheidet.
3. Ein Finding wiederholt sich in allen 3 Wellen → hohe Konfidenz, geht
   ungeprueft in Task.

---

## PHASE 0.5.2 — HiL Findings Review

**Was die Phase tut:** User schaut auf die Findings, akzeptiert / streicht /
ergaenzt. Berater dokumentiert Entscheidungen.

**Daseins-Berechtigung:** Findings sind LLM-Output. Ein Mensch muss sie sehen,
bevor sie zu einer Aufgabe werden. Diese Phase ist die einzige verpflichtende
HiL-Stelle in A.

**Inputs:** Findings aus 0.5.
**Outputs:** Kuratierte Findings-Liste (akzeptiert / gestrichen / neu).
**Konsumenten:** Phase 0.6.

**Drei Beispiele:**
1. User streicht 2 von 5 Findings → nur 3 wandern weiter.
2. User fuegt eine eigene Beobachtung hinzu → 6 Findings.
3. User akzeptiert alle → unveraendert.

---

## PHASE 0.6 — /_taskDefinition

**Was die Phase tut:** Verdichtet kuratierte Findings + Kruemmel aus pileOfMud
zu **Task.md** — der einzigen kanonisierten Auftrags-Beschreibung.

**Daseins-Berechtigung:** Task.md ist der **Stille-Post-Stopper**. Ab hier liest
jede Phase nur noch Task.md, nicht mehr User-Notes. Wer wissen will "was wollte
der User wirklich?", findet die Antwort dort — oder nirgends.

**Inputs:** Findings (kuratiert), pileOfMud.
**Outputs:** `Task.md` mit Aufgabe + Kruemmel.
**Konsumenten:** /_W_fetch (3a), /_model (3b), /_spec (3c).

**Drei Beispiele:**
1. Findings → 3 klare Punkte → Task.md mit 3 Acceptance-Krumel.
2. Findings sind diffus → Task.md markiert "TBD: Scope unklar" und HiL erneut.
3. Kruemmel widerspricht Finding → Task.md notiert Konflikt, Task-Owner muss
   waehlen.

---

## PHASE 1.5 — Git-Analyse (optional pr=true)

**Was die Phase tut:** Wenn `pr=true`, ruft `/_git_analyse` Git-Status, offene
PRs, Branch-Diffs, vergangene PR-Reviews ab.

**Daseins-Berechtigung:** Bei PR-Aufgaben ist Git-State Teil der Wissensbasis.
Ohne Snapshot waere unklar, was schon committed ist und was noch offen.

**Inputs:** Git-Repo, optional Branch-Name.
**Outputs:** Git-Snapshot in `.claude/git-state/`.
**Konsumenten:** Phase 2 (IDD-Context), spaeter SDF/I.

**Drei Beispiele:**
1. PR-Review-Aufgabe → pr=true → /_git_analyse holt PR-Kommentare, Branch-Diff.
2. Reine Spec-Aufgabe → pr=false → Phase 1.5 entfaellt.
3. PR offen, aber lokal noch ungepushte Commits → /_git_analyse markiert Drift.

---

## PHASE 2 — IDD-Context (optional --parent-pr)

**Was die Phase tut:** Wenn `--parent-pr` gesetzt, sammelt der Berater
Information ueber den Eltern-PR (Sub-Item-Beziehung) und mappt diese in die
Wissensbasis.

**Daseins-Berechtigung:** Sub-Items eines IDD-Decompositions brauchen
Eltern-Kontext (Sibling-Items, Eltern-Spec, gemeinsame Constraints). Ohne diesen
Kontext driftet das Sub-Item.

**Inputs:** Parent-PR-ID, Git-State.
**Outputs:** IDD-Context-Block.
**Konsumenten:** Phase 3a /_W_fetch.

**Drei Beispiele:**
1. BL-142 ist Sub-Item von BL-130 → Phase 2 zieht BL-130-Spec.
2. Standalone-Aufgabe → --parent-pr fehlt → Phase 2 entfaellt.
3. IDD-Context widerspricht Task → Berater markiert Konflikt, HiL.

---

## PHASE 3a — /_W_fetch (liest Task.md als Anker)

**Was die Phase tut:** Holt Wissen aus RAG / Vault, das fuer Task.md relevant
ist. Liefert thematisch sortierte Wissens-Bloecke.

**Daseins-Berechtigung:** Wissen, das schon im Vault liegt (frueheres
Model-Split, Pattern, Cases), darf nicht erneut hergeleitet werden. Reuse spart
Zyklen und stabilisiert Begriffe.

**Inputs:** Task.md, Vault, RAG.
**Outputs:** `.claude/wissen/{theme}.md` Snippets.
**Konsumenten:** Phase 3b /_model.

**Drei Beispiele:**
1. Task betrifft Auth → /_W_fetch zieht Auth-Pattern aus Vault.
2. Vault hat nichts → /_W_fetch meldet leer, Model startet aus Roh.
3. Vault hat Widerspruch zu Task → /_W_fetch markiert, Model muss adressieren.

---

## PHASE 3b — /_model

**Was die Phase tut:** Baut **Model.md** mit W{n}-Knoten in 3 Wellen
(Exploration / Draft / Synthese).

**Daseins-Berechtigung:** Model ist die **mentale Karte** — was sind die Akteure,
was die Beziehungen, welche Constraints? Ohne Model gibt es keinen Anker fuer
Spec.

**Inputs:** Task.md, /_W_fetch-Snippets.
**Outputs:** `Model.md` mit W{n} + TC{n}.
**Konsumenten:** Phase 3c /_spec, Phase 3d /_K_score.

**Drei Beispiele:**
1. Aufgabe einfach → Model klein (5 W{n}, 2 TC).
2. Aufgabe komplex → Model gross, Split bei >15 W{n}.
3. Model bleibt unklar → /_K_score wird mahnen, eventuell HiL.

---

## PHASE 3c — /_spec

**Was die Phase tut:** Schreibt **Spec.md** — Ziel-Architektur, Phasen,
Akzeptanzkriterien (AKs).

**Daseins-Berechtigung:** Spec ist das **Soll-Bild** — was soll am Ende stehen?
Sie zerlegt die Aufgabe in AKs (AK-A-1, AK-B-1, ...) mit Anchors, die spaeter
von K-Score, IDF und SDF konsumiert werden.

**Inputs:** Task.md, Model.md.
**Outputs:** `Spec.md` mit Phase-Sektionen + AKs + Anchors.
**Konsumenten:** Phase 3d /_K_score, IDF Phase 2 SPEC_PARSE.

**Drei Beispiele:**
1. Aufgabe = neuer Endpoint → Spec mit AK-API, AK-Storage, AK-Auth.
2. Aufgabe = Refactoring → Spec mit AKs pro Modul.
3. Spec hat AK ohne Anchor → /_K_score lehnt ab, zwingt zur Korrektur.

---

## PHASE 3d — /_K_score (Pro-AK)

**Was die Phase tut:** Bewertet pro AK die Karten-Reife: `k_score`, `srs_pro_ak`,
`spec_anchor`, `model_refs`, `rf_refs`.

**Daseins-Berechtigung:** Pro-AK-Granularitaet erlaubt IDF spaeter, AKs
zielgerichtet in PL-Items zu gruppieren. Aggregat-K-Scores allein sind zu grob,
weil ein einzelner unklarer AK die ganze Pipeline bremst.

**Inputs:** Spec.md, Model.md.
**Outputs:** `K-SCORE.md` + Aggregat-Felder fuer Phase 4.2a.
**Konsumenten:** Phase 4.2a Metadaten-Aggregation, IDF Phase 3.1.

**Drei Beispiele:**
1. AK-A-1 hat hohen K-Score, klare Anchors → IDF kann direkt PL-Item bauen.
2. AK-A-2 K-Score niedrig → IDF wird AK-A-2 als unreif markieren.
3. AK ohne model_refs → /_K_score wirft Warnung, Spec-Korrektur empfohlen.

---

## PHASE 3e — /_gap

**Was die Phase tut:** Vergleicht IST (Code) vs SOLL (Spec) und schreibt
**Gap.md** mit Delta-Beschreibung.

**Daseins-Berechtigung:** Ohne Gap weiss man nicht, wie viel Arbeit eigentlich
ansteht. Gap ist die **Aufwands-Metrik** fuer SDF-Mode-Entscheidung.

**Inputs:** Spec.md, Code (via Grep/Read).
**Outputs:** `Gap.md` mit gap_percent.
**Konsumenten:** Phase 4.2a, SDF C3 modusEntscheidung.

**Drei Beispiele:**
1. Gap = 80% → SDF wird hartem Modus zuneigen (M3+).
2. Gap = 20% → SDF kann leichtem Modus tendieren (M1/M2).
3. Gap unbestimmbar (kein Code-Anker) → Gap.md markiert "TBD".

---

## PHASE 4.2a — Metadaten-Aggregation (Single-Responsibility)

**Was die Phase tut:** Aggregiert pro-AK-Werte zu 6 BL-Item-Feldern:

- `aggregat_k_score` (Mittel)
- `aggregat_srs_score` (Mittel)
- `aggregat_gap_percent` (aus /_gap)
- `aggregat_model_maturity` (Model.md Reife)
- `aggregat_freiheitsgrade` (wie viele Wege?)
- `aggregat_is_meta_command` (Boolean)

**Daseins-Berechtigung:** Diese 6 Felder sind die **Eingangs-Vektoren fuer SDF
C3**. Ohne explizite Aggregation muesste SDF in fremden Dateien herumlesen — das
verletzt Single-Responsibility. Phase 4.2a war frueher unter dem Namen
`COMPLEXITY_STATE init` versteckt; post-BL-142 ist sie explizit.

**Inputs:** K-Score-Map, Gap.md, Model.md.
**Outputs:** 6 Felder im BL-Item-Frontmatter (Phase 4.2b schreibt).
**Konsumenten:** Phase 4.2b, SDF C3.

**Drei Beispiele:**
1. Alle AKs reif → aggregat_k_score hoch, SDF kann M1/M2.
2. Ein AK mit niedrigem K-Score zieht Mittel runter → SDF erwaegt M3+.
3. is_meta_command=true → SDF nimmt Meta-Modus.

---

## PHASE 4.2b — /_backlog (BL-Item-Huelle)

**Was die Phase tut:** Schreibt das BL-Item-Frontmatter:

- `reifegrad: REIF`
- `ak_anchors: [...]`
- `srs_per_ak: {...}`
- `k_score_per_ak: {...}`
- 6 Aggregat-Felder

**Daseins-Berechtigung:** Das BL-Item ist der **zentrale Vertrags-Knoten**
zwischen A und IDF/SDF. Es enthaelt alles, was die naechste Schicht braucht — in
einem einzigen, kanonisierten Dokument.

**Inputs:** Aggregate aus 4.2a, K-Score-Map, Spec-Anchors.
**Outputs:** `BL-{ID}.md` mit reifegrad=REIF.
**Konsumenten:** /_A_postRoute (Phase 4.3a), IDF /_IDF_orchestrate.

**Drei Beispiele:**
1. BL-142 erstmals erstellt → REIF, alle Felder gefuellt.
2. BL-142 Resync → Felder aktualisiert, reifegrad bleibt REIF.
3. /_K_score scheiterte → reifegrad bleibt FRISCH, BL-Item wird nicht
   freigegeben.

---

## PHASE 4.3a — Routing 2-Path Binary

**Was die Phase tut:** Liest `big_dark_factory`-Flag aus Task.md / Spec.md.
Routet zu BDF (true) oder IDF (false).

**Daseins-Berechtigung:** Detail-Routing (welche Slices? welcher Mode?) ist
**nicht A's Aufgabe**. A entscheidet nur die binaere Frage: Standardflow (IDF)
oder Multi-PL-Item-Refactor-Flow (BDF). Alles weitere wird in IDF/SDF
verfeinert.

**Inputs:** BL-Item-Frontmatter, Task-Hint.
**Outputs:** Routing-Entscheidung + naechster Command.
**Konsumenten:** /_BDF_orchestrate oder /_IDF_orchestrate.

**Drei Beispiele:**
1. big_dark_factory=true (z.B. groesseres Refactoring) → BDF.
2. big_dark_factory=false (Standard) → IDF.
3. Flag fehlt → Default IDF, Berater notiert.

---

## PHASE 4.4 — State-Maintain (Pattern B Rollover)

**Was die Phase tut:** Aktualisiert den Manifest-State: A_PIPELINE_STATE,
markiert Routing-Ergebnis, rollt Pattern B um.

**Daseins-Berechtigung:** State ist der **Rolltreppen-Mechanismus** zwischen
Schichten. Ohne sauberen Rollover wuerde IDF/BDF nicht wissen, dass A fertig ist
und welche Artefakte sie lesen sollen.

**Inputs:** Phasen-Ergebnisse.
**Outputs:** Manifest-State-Update.
**Konsumenten:** /_A_postRoute, IDF/BDF.

**Drei Beispiele:**
1. Erfolgs-Pfad → A_PIPELINE_STATE = "ready_for_idf".
2. Routing zu BDF → State markiert "ready_for_bdf".
3. Abbruch (HiL ABORT) → State markiert "halted", BL-Item bleibt FRISCH.

---

## PHASE 5 — Git-Tracking (last_sync_commit)

**Was die Phase tut:** Notiert den letzten Commit-Hash, gegen den A gelaufen ist.

**Daseins-Berechtigung:** Bei spaeteren Resync-Laeufen weiss A, ob sich das Repo
seitdem veraendert hat. Ohne `last_sync_commit` waere jeder Resync ein
Voll-Lauf.

**Inputs:** Git HEAD.
**Outputs:** `last_sync_commit` im Manifest.
**Konsumenten:** Naechster A-Lauf (Mode-Erkennung 0.1).

**Drei Beispiele:**
1. Frischer Run → Commit gespeichert.
2. Resync 2 Tage spaeter → Commit-Hash diff zeigt 5 Aenderungen, Resync laeuft
   nur ueber diese.
3. Repo unveraendert → Resync entfaellt, alte Artefakte bleiben gueltig.

---

## PHASE 0.0X — TeamDelete

**Was die Phase tut:** Loescht das `a-{NAME}` Team, setzt `active_team=null`.

**Daseins-Berechtigung:** Lifecycle-Klammer. Ohne TeamDelete bleibt das Team
"hot" und Stale-Detection kommt nicht an. Sauberer Abschluss = sauberer Start
des naechsten Orchestrators.

**Inputs:** Aktuelles Team.
**Outputs:** active_team=null.
**Konsumenten:** Naechster Orchestrator (IDF/BDF).

**Drei Beispiele:**
1. Erfolgs-Abschluss → TeamDelete sofort.
2. Abbruch → TeamDelete trotzdem (Lifecycle-Pflicht).
3. Vorheriges Team noch aktiv → Cleanup hat es schon entsorgt.

---

## DATENTRAEGER-KETTE (visualisiert)

```
A./_K_score (Phase 3d)
  ├─ pro AK: k_score
  ├─ pro AK: srs_pro_ak
  ├─ pro AK: spec_anchor
  ├─ pro AK: model_refs
  └─ pro AK: rf_refs
       │
       ▼
A./_backlog (Phase 4.2b)
  ├─ reifegrad: REIF
  ├─ ak_anchors: [...]
  ├─ srs_per_ak: {...}
  ├─ k_score_per_ak: {...}
  └─ 6 Aggregat-Felder
       │
       ▼
IDF Phase 3.1 (AK-Extraktion)
  └─ ak_metadata pro AK
       │
       ▼
IDF Phase 3.2 (PL-Aggregation)
  └─ k_score_pl, srs_pl, model_refs union, layer
       │
       ▼
IDF Phase 5 (Cluster-Aggregate Hint)
       │
       ▼
IDF Phase 7 (BATCH_PLAN — autoritativ)
  └─ Batch-Aggregat + EXTERN/INTERN-Scan
       │
       ▼
SDF C3 (modusEntscheidung)
  └─ M1-M9
```

---

## ANTI-STILLE-POST-PRINZIP

A laeuft, BL-Item entsteht, Stunden vergehen, IDF startet. Wenn IDF nun User-Notes
laesen wuerde, waere Stille Post unvermeidbar — Notes drueften gestrichen,
ergaenzt, missverstanden sein. **Loesung:** IDF liest ausschliesslich
kanonisierte Artefakte (Task.md, Spec.md, K-Score, BL-Frontmatter). A's einziger
Job ist, diese Artefakte korrekt zu erzeugen. Jede Phase 0.0–5 dient diesem
Ziel.

---

## DISCOVERY VS FINDINGS (orthogonal)

Discovery (Phase 0.2) findet **was bearbeitet werden soll** (BL-ID).
Findings (Phase 0.5) finden **was an dieser Aufgabe beobachtbar ist**
(Roh-Daten). Beide sind orthogonal: Discovery kann entfallen (User uebergibt
ID), Findings nicht (sie gehoeren zu jeder Aufgabe). Verwechslung der beiden
fuehrt zu schlechten Aufgaben oder fehlender Wissensbasis.

---

## MODUS FRESH VS RESYNC

Fresh = Wissensbasis von Null. Resync = Wissensbasis aktualisieren. Resync
spart Zeit, aber nur wenn Anchors stabil bleiben. Wenn Spec.md AKs umbenennt,
muss A im Zweifel fresh laufen — sonst werden alte K-Scores fuer alte AKs
mitgefuehrt.

---

## IDD-MODUS + PARENT-PR

IDD = Intermediate Decomposition Decomposition. Eltern-PR (`--parent-pr`) liefert
Sibling-Constraints, ein Sub-Item ist nicht standalone. A's Phase 2 importiert
diesen Kontext, damit IDF spaeter weiss, dass das BL-Item Teil eines groesseren
Plans ist.

---

## METADATEN-AGGREGATION SINGLE-RESPONSIBILITY

Phase 4.2a hatte historisch keinen eigenen Namen — sie war "der Init-Block fuer
COMPLEXITY_STATE". Mit BL-142 wird sie explizit, weil sie eine eigene Aufgabe
hat: Aggregation. Vorher war diese Logik in SDF; das war eine Schichten-Verletzung
(SDF las pro-AK-Werte). Jetzt liefert A genau das, was SDF konsumiert — Single-
Responsibility durchgesetzt.

---

## BL-ITEM ALS ZENTRALER VERTRAGS-KNOTEN

Das BL-Item-Frontmatter ist die **API zwischen Schichten**. IDF und SDF lesen es
wie eine Schnittstellen-Definition. Wenn Schicht-Code etwas Neues braucht, kommt
es ins Frontmatter; wenn etwas obsolet wird, fliegt es raus. Diese
Kontrakt-Disziplin ist das Mittel gegen Schichten-Verschmelzung.

---

## 2-PATH-BINARY-ROUTING

A entscheidet **nicht** zwischen 9 Modi (das ist SDF C3). A entscheidet **nicht**
zwischen 5 Decomposition-Strategien (das ist IDF). A entscheidet eine binaere
Frage: BDF oder IDF. Diese Reduktion verhindert Schichten-Vermischung. Routing-
Detail bleibt eine Schicht tiefer.

---

## MINI-THESE

A ist **kein Macher**, sondern ein **Karten-Kartograph**. Die naechsten Schichten
machen — aber nur, wenn A vorher saubere Karten geliefert hat. Sauber heisst:
kanonisiert, anchored, aggregat-fertig. Weniger waere Stille Post; mehr waere
Schichten-Vermischung. A's Disziplin ist, **genau diese Mitte** zu halten.

---

ARGUMENTS: $ARGUMENTS
