---
status: active
version: 1.0.0
created: 2026-06-14
op: Crown2Orchestrate
phase: Meta
type: orchestration
model_tier: opus
floor_model: opus
feature_anchor: BL-252
parent_epic: BL-322
related:
  - deviation_signals(BL-252-AK-1)
  - crown2_dedupe(BL-252-AK-4)
  - _backlog
  - _crown
  - _sanity_check_dynamic
  - _disciplinary_report(BL-324)
---

# /_crown2_orchestrate — System-Health-Deviation-Observer (Crown-2)

**Zweck:** Die ZWEITE Crown neben dem Worker-Watchdog [[_crown]] (Crown-1). Sie ist
der **Deviation-Observer-Kern** des OmniCommand-Architekten: sie liest die rohen
SOLL↔IST-Abweichungs-Signale (aus `deviation_signals.py`, AK-1), **clustert** sie,
**adjudiziert** opus-seitig welche eine echte Abweichung sind (vs erwartetes
Rauschen / dokumentierte Escape-Hatch), **dedupet** gegen den Bestands-Backlog und
**generiert** pro NEUEM echten Cluster EIN fertig-ausformuliertes Backlog-Item via
[[_backlog]] — statt eines Pflasters.

Damit **automatisiert** sie die Architekt-1-Pflicht (Anti-Pflaster): „Sobald ein
ad-hoc Pflaster gelegt wird, MUSS im selben Flow ein proper-fix Backlog-Item
entstehen" wird hier zum periodisch laufbaren System-Reflex statt zur manuellen
Lead-Disziplin. (Genau das tat der Lead in der BL-320-Session manuell:
`acquire_bl`-2-Owner-Race = echte Abweichung → [[BL-344]].)

**Crown-2 ist NUR die Urteils-Schicht.** Sie sammelt NICHT (das ist AK-1, rein), sie
baut den BL-Writer NICHT neu (das ist [[_backlog]], single-writer). Sie ruft beide
auf.

---

## Aufruf

```
/_crown2_orchestrate [--mode=report-only|generate] [--since=<ISO-ts>] [--vault=<pfad>]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|--------------|
| `--mode` | `report-only` | `report-only \| generate` | report-only = NUR anzeigen (read-only, IMMER safe). generate = BLs via /_backlog erzeugen (nach Dedupe). |
| `--since` | `null` | ISO-Timestamp | Nur Audit-Events ab diesem Zeitpunkt sammeln (Inkrement-Lauf; lexikographisch ISO-8601). |
| `--vault` | auto-resolved | Pfad | Vault-Root; default cwd-stabil via `crown2_dedupe._resolve_vault_root` / `deviation_signals._resolve_vault_root`. |

**Beispiele:**
```
/_crown2_orchestrate                       → Sammeln + Clustern + Adjudizieren + Draft-BLs ANZEIGEN (NICHTS geschrieben)
/_crown2_orchestrate --since=2026-06-01    → nur Signale ab 2026-06-01 betrachten
/_crown2_orchestrate --mode=generate       → echte, nicht-deduplizierte Cluster als BLs erzeugen
```

---

## VERTRAG

```
+======================================================================+
| COMMAND: /_crown2_orchestrate [--mode=...] [--since=...] [--vault=...]|
+======================================================================+
|                                                                      |
| ACTOR: CROWN-2 ORCHESTRATOR (Team Lead direkt, floor=opus)          |
|                                                                      |
| DEFAULT-MODUS: report-only — read-only, IMMER safe (STRUKTURELL:    |
|   Phase 5 ruft /_backlog NUR bei --mode=generate; ein Auto-BL-      |
|   Generator darf den Backlog NICHT zuspammen). Analog /_health.     |
|                                                                      |
| LIEST:                                                               |
|   deviation_signals.collect_deviation_signals(vault,audit,since)   |
|     -> rohe Anomalie-Signale (guard_block/hard_gate_block/          |
|        contract_violation/rollback/stale_lock_reclaim/process_bypass|
|        /counter_drift/status_drift/...). REINER Input, kein Urteil. |
|   crown2_dedupe.load_existing_bls(vault, open_only=True)           |
|     -> Bestands-BL-Korpus (Index-Zeile + Node-Body) fuer Dedupe.   |
|   Vision/Design-SOLL-Kontext (CLAUDE.md ## Architekt-Pflicht,       |
|     INV-*-Familien, dokumentierte Escape-Hatches) — fuer Phase 3.   |
|                                                                      |
| SCHREIBT:                                                            |
|   report-only:  NICHTS (kein einziger Schreibzugriff)              |
|   generate:     pro NEUEM echten Cluster ein BL — AUSSCHLIESSLICH   |
|     via Skill(_backlog, ...) (single-writer). Crown-2 schreibt     |
|     NIE direkt in Vault/Index/Manifest.                            |
|   audit.jsonl: CROWN2_RUN-Event (clusters/genuine/deduped/generated)|
|                                                                      |
| RUFT:                                                                |
|   deviation_signals.collect_deviation_signals(...)  (AK-1 Sammler)  |
|   crown2_dedupe.cluster_signature_from_cluster(...)  (AK-4 Signatur)|
|   crown2_dedupe.cluster_already_tracked(...)        (AK-4 Match)    |
|   Skill(_backlog, args="{TITLE}")                   (AK-3, nur gen) |
|                                                                      |
| INVARIANTEN:                                                         |
|   INV-CROWN2-1: report-only ist DEFAULT — KEIN /_backlog-Aufruf,   |
|     KEIN Schreibzugriff ohne explizites --mode=generate.           |
|   INV-CROWN2-2: KEIN Urteil im Sammler — die Adjudikation          |
|     (genuine vs noise) lebt NUR hier (Phase 3), nie in AK-1.       |
|   INV-CROWN2-3: KONSERVATIV adjudizieren — nur hoch-konfidente      |
|     echte Abweichungen werden BL-wuerdig. Dokumentierte Escape-     |
|     Hatches sind KEINE Abweichung (ENFORCEMENT_BYPASS/GUARD_WARN/   |
|     MOTOR_OVERRIDE — by-design-Soften, kein SOLL-Bruch).           |
|   INV-CROWN2-4: Dedupe VOR Generierung — pro echtem Cluster gegen   |
|     Bestands-Backlog pruefen (crown2_dedupe). Treffer -> SKIP.     |
|   INV-CROWN2-5: BLs NUR via /_backlog (single-writer). Crown-2 baut |
|     den Writer NICHT nach.                                          |
|   INV-CROWN2-6: floor=opus — die Adjudikation (Phase 3) ist        |
|     rote Zone (SOLL↔IST-Urteil), NIE Workflow, NIE haiku/sonnet.   |
╚======================================================================╝
```

---

## PHASEN-VERTRAG

### Phase 1 — COLLECT (mechanisch, AK-1)

```
sigs = deviation_signals.collect_deviation_signals(
          vault_root=VAULT, audit_path=AUDIT, since=SINCE)
```

`sigs` = list[{source, kind, evidence, severity_hint, first_seen}] — rohe
Kandidaten. KEIN Urteil. Bei leerer Quelle -> [] (robust).

**Vier Quellen (BL-324 AK-4 schliesst den Lern-Loop):** Neben den drei Maschinen-
Quellen (audit.jsonl, Manifest-Counter, Index↔Frontmatter-Status) ist
`disciplinary_report.jsonl` (die Lead-SELBST-Reports des Feldjaegers,
[[_disciplinary_report]]) jetzt der 4. Crown-2-Signal-Strom (`source="disciplinary"`,
`kind="lead_deviation_<class>"`, severity `was_correct→low` sonst `medium`).
Damit pickt Crown-2s collect + Adjudikation (Phase 3) + gated Generierung (Phase 5)
die wiederkehrenden Lead-Abweichungen **automatisch** auf — der Lern-Loop
(Lead-Selbst-Reports → Crown-2-Adjudikation → gated Härtungs-BL) schliesst sich,
statt dass die Reports nur im Feldjaeger-Aggregat haengen bleiben. Audit-Strom +
Lead-Selbst-Strom → EIN Observer.

Aufruf-Skizze (read-only Subprocess, utf-8-sicher):
```
py -3 -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); \
  from deviation_signals import collect_deviation_signals as c; \
  import json; print(json.dumps(c(since=SINCE), ensure_ascii=False))"
```
(oder die Funktion via Glob/Read des Moduls; der Sammler ist rein.)

### Phase 2 — CLUSTER (deterministisch-vorbereitend)

Signale zu **Deviations-Clustern** gruppieren — ein Cluster = ein kohaerentes
SOLL↔IST-Thema. Gruppier-Achsen:
- **kind** (z.B. alle `guard_block`),
- **source** (audit / manifest / index),
- **evidence-Aehnlichkeit** (gleicher Guard/Hook/Datei/Symbol-Name in `evidence`).

Pro Cluster eine **Signatur** ableiten:
```
sig = crown2_dedupe.cluster_signature_from_cluster(cluster)
      # -> {"kind": ..., "terms": [Schluessel-Evidence-Terme]}
```
Beispiel-Cluster: „N×`guard_block` Typ geist9 auf loopDecision", „counter_drift
Δ=5", „M×`stale_lock_reclaim` unter Last auf acquire_bl".

### Phase 3 — ADJUDIKATION (opus-Urteil, DER KERN, INV-CROWN2-2/3/6)

Pro Cluster SOLL↔IST urteilen: **echte Abweichung (BL-wuerdig)** vs
**erwartet/Rauschen**. KONSERVATIV — im Zweifel als Rauschen werten (lieber eine
echte Abweichung im naechsten Lauf erneut sehen als den Backlog mit Spekulation
zuspammen).

**NICHT als Abweichung werten (dokumentierte Escape-Hatches / by-design):**
- `ENFORCEMENT_BYPASS` / `enforceProcess=false` — der dokumentierte Owner-Hatch
  (Guards nicht gegen eigene Umbau-Arbeit; [[_hook_workaround]]).
- `GUARD_WARN` (severity low) — Warn-kein-Block ist die *gewollte* nicht-blockende
  Klasse, kein SOLL-Bruch.
- `MOTOR_OVERRIDE` (severity low) — dokumentierte Motor-Soften.
- `LOCK_STALE_RECLAIM` bei *einzelnem* Vorfall nach legitimem Crash/Timeout —
  erwarteter Recovery-Pfad. ABER: **gehaeuft unter Gleichzeitigkeit** (Muster) =
  echte Abweichung (das war [[BL-344]] — false-stale-Reclaim als Race).
- Single-Vorkommen ohne Muster bei low/medium severity — Rauschen.

**Als echte Abweichung werten (BL-wuerdig):**
- `GEIST5_CONTRACT_VIOLATION`, `HARD_GATE_BLOCK`, `WORKER_RUNAWAY`,
  `PROCESS_BYPASS_DETECTED_*` — strukturelle SOLL-Bruch-Klassen.
- `counter_drift` / `status_drift` — Single-Writer-/Konsistenz-Bruch (Index↔Manifest
  ↔Frontmatter divergiert).
- Jedes **gehaeufte** Muster (N×gleicher kind+Signatur unter Last) das auf einen
  Korrektheits-/Konkurrenz-Defekt zeigt.

Nutze den Vision/Design-SOLL-Kontext (CLAUDE.md ## Architekt-Pflicht + INV-Familien)
als Massstab. Output pro Cluster: `verdict ∈ {genuine, noise}` + `begruendung`.

### Phase 4 — DEDUPE (mechanisch, AK-4, INV-CROWN2-4)

Pro **genuine** Cluster gegen den Bestands-Backlog pruefen:
```
existing = crown2_dedupe.load_existing_bls(vault_root=VAULT, open_only=True)
match    = crown2_dedupe.cluster_already_tracked(sig, existing)
IF match (BL-ID):  cluster.disposition = "deduped" (SKIP, kein Duplikat)
ELSE:              cluster.disposition = "new"     (-> Phase 5)
```
`cluster_already_tracked` ist konservativ: ohne verlaessliche Schluessel-Terme ODER
unter der Term-Treffer-Schwelle -> KEIN match -> Item wird (im generate-Modus)
erzeugt, nicht verschluckt.

### Phase 5 — GENERIEREN (AK-3, NUR bei --mode=generate, INV-CROWN2-1/5)

```
IF mode != "generate":
  -> NICHTS schreiben. Draft-BLs nur als Report anzeigen (Phase 6). RETURN.

FUER jeden Cluster MIT disposition=="new":
  TITLE = praeziser, ein-Zeiler-Titel der Abweichung (BL-344/345-Stil)
  Skill(_backlog, args="{TITLE}")      # single-writer erzeugt counter-bump + Node + Index
  # danach: den generierten BL-Node mit dem Crown-2-Body fuellen (Schema unten),
  # priority=hoch, parent_epic=BL-322 (bei Engine-Health), type=bug/task.
```
Das generierte BL trifft das **BL-344/345-Schema**:
```
Frontmatter: id, title, type(bug|task), version, created, updated, status=DRAFT,
  reifegrad, ledger:work, priority: hoch, parent_epic: "BL-322",
  needs_a_pipeline: false, raw_source: "<Crown-2-Lauf {ISO} + Signal-Belege>",
  dependencies, vault_knoten_id
Body:
  # {bl_id}: {Kurz-Titel}
  ## Quelle / Fund-Kontext   (Crown-2-Lauf + welche Signale, severity, Anzahl)
  ## Kern / Problem          (die SOLL↔IST-Abweichung praezise)
  ## Vermutete Wurzel        (aus evidence abgeleitet)
  ## Belege                  (Signal-evidence-Auszuege, Audit-Event-Namen)
  ## AK-Seeds                (Fix-Skizze: AK-1..N)
  ## Abgrenzung + Cross-Links ([[...]]: ≠ verwandte BLs, parent [[BL-322]])
```

### Phase 6 — OUTPUT (immer)

Report (an Lead, und CROWN2_RUN-Audit-Event):
```
Cluster gesamt:     {N}
  genuine:          {G}   (echte Abweichung laut Adjudikation)
  noise:            {N-G} (erwartet/Escape-Hatch/Single-Vorkommen)
genuine deduped:    {D}   (bereits durch Bestands-BL abgedeckt -> SKIP)
generated/proposed: {G-D} ({mode=generate: erzeugte BL-IDs | report-only: Draft-Titel})
```
Pro Cluster eine Zeile: kind · Signatur-Terme · verdict · begruendung ·
disposition (noise / deduped→BL-XXX / new→{erzeugt BL-YYY | proposed}).

---

## AK-6 — Abgrenzung (was Crown-2 NICHT ist)

- **≠ [[_sanity_check_dynamic]]** — der beobachtet eine *laufende* Pipeline auf
  **Prozess-Compliance** (Live-Audit eines Laufs). Crown-2 ist *post-hoc* +
  *quer ueber alle Laeufe*: SOLL↔IST-Abweichungs-Cluster aus dem Audit-Aggregat →
  Backlog-Items. Kein Live-Beobachter eines Einzel-Laufs.
- **≠ [[_sanity_check]] (BL-228, one-shot)** — der ist ein einmaliger Self-Healing-
  Audit. Crown-2 ist der *wiederkehrende* Deviation-Reflex (periodisch laufbar,
  z.B. als Cron oder am BDF-Cycle-Rand).
- **≠ [[_disciplinary_report]] (BL-324, Feldjaeger)** — der trackt **Lead-Abweichungen**
  (der Mensch/Architekt weicht vom Prozess ab) als Lernsignal. Das ist eine
  *Teilmenge* der Crown-2-Abweichungen (Lead-getrieben). Crown-2 ist breiter:
  System-weite SOLL↔IST-Drift (Guards, Locks, Counter, Status, Contracts).
- **≠ [[_crown]] (Crown-1)** — der ist der *Worker-Watchdog* (lebt-noch-Check je
  Spawn, Cron-Heartbeat). Crown-2 ist die *zweite Crown daneben* — sie stoert
  Crown-1 nicht, teilt nur den „Crown"-Namen (Waechter-Prinzip).

---

## AK-5 — Trigger + Dual-Crown-Koordination

Crown-2 ist der **wiederkehrende** Deviation-Reflex (größeres Zeitfenster als Crown-1s
per-Worker-Watchdog). Drei Auslöse-Wege, alle im **report-only**-Default:

- **Periodischer Cron (primär):** ein wiederkehrender `CronCreate`-Schedule (größeres
  Intervall, z.B. stündlich/täglich) ruft `/_crown2_orchestrate --mode=report-only`.
  **Eigener Cron-ID-Namespace** (`crown2-observer-*`), getrennt von Crown-1s
  per-Worker-Watchdog-IDs (`crown-watchdog-{worker}`). Autonome Fires sind
  **report-only** (kein Auto-Write — der periodische Reflex beobachtet + meldet, er
  generiert NICHT von selbst BLs; `--generate` ist eine bewusste Owner/Lead-Aktivierung).
- **Am BDF-Cycle-Rand / Item-Ende mit Zoom-out:** nicht nur 1 Worker (das ist Crown-1),
  sondern das System-Aggregat über den größeren Abschnitt — als optionaler Einhang-Punkt
  (billig, weil report-only).
- **Manuell:** `/_crown2_orchestrate` on demand (Owner-Direktzugriff).

> **INV-CROWN2-7 (Dual-Crown-Koordination):** Crown-1 ([[_crown]]) = **one-shot
> per-Worker-Watchdog** (mechanisch, „lebt der Worker noch?", haiku, Cron-ID
> `crown-watchdog-{worker}`, `CronDelete` bei Self-Report). Crown-2 = **wiederkehrender
> System-Observer** (Urteil „läuft das System as-designed?", opus, Cron-ID
> `crown2-observer-*`). Sie laufen NEBENEINANDER, teilen **keinen** Cron-ID-Namespace,
> **keinen** State, **keinen** Scope (Crown-1: ein Worker; Crown-2: Audit-/State-Aggregat)
> — und stören sich nicht. Wer beide auf denselben Cron-ID/Scope legt, verletzt INV-CROWN2-7.

**Aktivierung = bewusster operativer Schritt, KEIN Auto-Self-Schedule:** Dieses Skill
erzeugt beim Load KEINEN Cron von selbst (das wäre ein unerwünschter persistenter
Seiteneffekt). Die Live-Cron-Erzeugung (`CronCreate` mit dem `crown2-observer`-Namespace,
report-only-Aufruf) ist ein bewusster Owner/Lead-Schritt, wenn der periodische Reflex
scharf geschaltet werden soll. Bis dahin ist Crown-2 manuell + am Cycle-Rand nutzbar.

---

## SELBST-KONSISTENZ (BL-330 Vehikel-Doktrin)

- **Phase 1 (COLLECT)** + **Phase 4 (DEDUPE)** sind **gruen/deterministisch** —
  reine Funktions-Aufrufe (`deviation_signals` + `crown2_dedupe`), workflow-faehig.
- **Phase 3 (ADJUDIKATION)** ist **rot** — SOLL↔IST-Urteil, GREEN-Klarheit-Klasse;
  NIE Workflow, floor=opus (INV-CROWN2-6). Genau die Member-gegenseitige-
  Sichtbarkeits-Klasse, die ein Workflow durchwinken wuerde.
- **Phase 5 (GENERIEREN)** delegiert an [[_backlog]] (single-writer) — Crown-2
  faellt das *ob*-Urteil (rot), der Writer macht das *wie* (deterministisch).

---

## Changelog

### v1.1.0 (2026-06-14) — BL-252 batch_3: AK-5 Trigger + Dual-Crown-Koordination
- AK-5-Sektion: periodischer Cron (`crown2-observer-*`-Namespace, report-only-Fires) +
  BDF-Cycle-Rand-Einhang + manuell. INV-CROWN2-7 (Dual-Crown-Trennung: getrennte
  Cron-IDs/State/Scopes zu Crown-1, kein Stören). Aktivierung = bewusster Owner-Schritt,
  KEIN Auto-Self-Schedule beim Load (kein persistenter Seiteneffekt). BL-252 build-komplett.

### v1.0.0 (2026-06-14) — BL-252 batch_2: Crown-2-Orchestrator-Kern
- 6-Phasen-Vertrag: COLLECT(AK-1) → CLUSTER → ADJUDIKATION(opus, Kern) →
  DEDUPE(AK-4) → GENERIEREN(AK-3, gated) → OUTPUT.
- `--mode=report-only` (DEFAULT, read-only safe) vs `--mode=generate` (gated).
- Adjudikation konservativ + Escape-Hatch-Liste (ENFORCEMENT_BYPASS/GUARD_WARN/
  MOTOR_OVERRIDE/single-LOCK_STALE_RECLAIM NICHT als Abweichung).
- Dedupe via `crown2_dedupe.py` (cluster_already_tracked + load_existing_bls).
- Generierte BLs treffen BL-344/345-Schema (priority=hoch, parent_epic=BL-322).
- INV-CROWN2-1..6 + AK-6-Abgrenzung (≠ sanity_dynamic / sanity_check / _disciplinary
  / Crown-1).
