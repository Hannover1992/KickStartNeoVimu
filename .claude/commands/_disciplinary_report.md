---
status: active
version: 1.0.0
created: 2026-06-14
op: DisciplinaryReport
phase: Meta
type: orchestration
model_tier: opus
floor_model: opus
feature_anchor: BL-324
parent_epic: BL-322
related:
  - disciplinary_report(BL-324-AK-1/2)
  - deviation_signals(BL-252-AK-1)
  - _crown2_orchestrate(BL-252)
  - _backlog
  - _sanity_check
---

# /_disciplinary_report — Feldjaeger (Lead-Abweichungs-Capture)

**Zweck:** Der **Feldjaeger**. Wenn der Lead/Architekt BEWUSST gegen oder
AUSSERHALB des designten Prozesses handelt — improvisiert, overrided, defert
ohne Prozess-Pfad, **faengt was die Maschine uebersah**, leakt ueber eine
Tier-/Zonen-Grenze, schliesst eine Foresight-Luecke — dann MUSS diese Abweichung
**SICHTBAR** werden. Die Abweichung darf RICHTIG sein (`was_correct=true`), aber
jede Abweichung ist das Signal dafuer, **was die Maschine noch nicht selbst kann**.

> **Flexibilitaet ist erlaubt; Stille ist es nicht.**

**NICHT-punitiv.** Dies ist ein **Lern-Strom**, kein Straf-Register. Jeder Eintrag
ist ein Datenpunkt fuer die Maschinen-Selbstgenuegsamkeit ([[feedback_machine_not_context]]):
jede Lead-Intervention im Produktions-Flow ist eine Selbst-Genuegsamkeits-Luecke,
die irgendwann in die Maschine wandern soll.

BL-324 ist die **LEAD-Abweichungs-Teilmenge** von Crown-2 ([[_crown2_orchestrate]],
[[BL-252]]). Crown-2 beobachtet die system-weite SOLL↔IST-Drift (Guards, Locks,
Counter, Status, Contracts); der Feldjaeger meldet die **Lead-getriebenen**
Abweichungen, die kein Audit-Event hinterlassen (Urteils-Calls).

---

## Aufruf

```
/_disciplinary_report                  → eine Lead-Abweichung interaktiv/strukturiert melden (append)
/_disciplinary_report --aggregate      → Aggregations-View nach deviation_class (read-only)
```

| Parameter | Default | Beschreibung |
|-----------|---------|--------------|
| (kein) | Capture | Der Lead fuellt das Schema und meldet EINE Abweichung (`append_report`). |
| `--aggregate` | — | Read-only Aggregat nach Klasse (`{class: {count, was_correct_count, entries}}`). |
| `--report-path` | cwd-stabiler Default | Ziel-jsonl. Default: `.claude/audit/disciplinary_report.jsonl` (via `disciplinary_report._default_report_path`, cwd-stabil). |

---

## VERTRAG

```
+======================================================================+
| COMMAND: /_disciplinary_report [--aggregate] [--report-path=...]     |
+======================================================================+
|                                                                      |
| ACTOR: FELDJAEGER (Team Lead direkt, floor=opus)                    |
|        NICHT-punitiv: Lern-Strom, kein Straf-Register.              |
|                                                                      |
| LIEST (--aggregate):                                                 |
|   disciplinary_report.aggregate_by_class(report_path)              |
|     -> {class: {count, was_correct_count, entries[]}}, read-only.  |
|                                                                      |
| SCHREIBT (Capture):                                                  |
|   disciplinary_report.append_report(entry, report_path)            |
|     -> validiert Pflichtfelder + deviation_class, appended EINE     |
|        JSONL-Zeile an disciplinary_report.jsonl (append-only,       |
|        robust: Schema-Reject ODER OS-Fehler -> False, kein Crash). |
|                                                                      |
| SCHEMA (REQUIRED_FIELDS + auto-ts):                                  |
|   deviation_class     ∈ DEVIATION_CLASSES (5 belegte Klassen)      |
|   kontext             WO/WANN (Session, BL, Phase, Seam)            |
|   lead_reasoning      WARUM der Lead so handelte (der Urteils-Call) |
|   machine_should_have was die MASCHINE haette tun/fangen sollen    |
|   learning_signal     die abgeleitete Lehre (-> oft proper-fix-BL) |
|   was_correct (bool)  war die Abweichung im Ergebnis richtig?      |
|   proposed_hardening  Fix-Skizze (was die Maschine lernen muss)    |
|   ts                  auto-gestempelt (ISO-8601 Z), wenn fehlend   |
|                                                                      |
| DEVIATION_CLASSES (5, belegt):                                       |
|   bewusster_override            Lead overrided Schritt bewusst      |
|   improvisation_ohne_prozesspfad kein Prozess-Pfad existiert        |
|   machine_missed_catch          Lead faengt was Maschine uebersah   |
|   tier_leak                     Leak ueber Tier-/Zonen-Grenze       |
|   foresight_luecke              Lead schliesst Vorausschau-Luecke   |
|                                                                      |
| INVARIANTEN:                                                         |
|   INV-DR-1: NICHT-punitiv — Lern-Strom, kein Straf-Register.        |
|     was_correct=true ist haeufig + erwuenscht (richtige Abweichung  |
|     bleibt meldepflichtig: die Stille ist der Fehler, nicht die     |
|     Abweichung).                                                    |
|   INV-DR-2: Schema-Pflicht — fehlt EIN Pflichtfeld oder ist die     |
|     deviation_class unbekannt -> append_report rejected (False).   |
|   INV-DR-3: append-only, cwd-stabil (BL-336), utf-8-sicher          |
|     (a96eb1c stdout+stderr-Fang). KEIN Ueberschreiben.             |
|   INV-DR-4: KRUECKE, nicht Ziel — die Lead-Selbstmeldung ist die    |
|     Uebergangs-Form. Das ZIEL ist Maschinen-Hook-Detektion (ueber   |
|     deviation_signals, batch_2). Lead-Selbstmeldung ist WIEDER     |
|     "Agent macht's, nicht Maschine" ([[feedback_machine_not_context]]).|
|   INV-DR-5b (AK-4, GEBAUT): disciplinary_report.jsonl ist die 4.    |
|     Crown-2-Signal-Quelle (deviation_signals._scan_disciplinary_    |
|     reports -> source="disciplinary"). Lead-Selbst-Reports fliessen |
|     so automatisch in Crown-2-Adjudikation + gated Haertungs-BL —   |
|     der Lern-Loop schliesst sich (nicht nur Aggregat, sondern       |
|     Reports -> Crown-2 -> proper-fix-BL-Kandidat).                 |
|   INV-DR-5: REUSE, nicht duplizieren — der Lern-Loop (Abweichung    |
|     -> proper-fix-BL) lebt in Crown-2 + /_backlog (single-writer). |
|     Dieser Feldjaeger SAMMELT nur; er generiert KEINE BLs selbst.  |
|   INV-DR-6: floor=opus — die deviation_class-Zuordnung +            |
|     learning_signal-Ableitung sind ein Urteils-Call (rote Zone).   |
╚======================================================================╝
```

---

## PHASEN-VERTRAG

### A) Capture (Default — Lead meldet eine Abweichung)

1. Der Lead fuellt das **Schema** (alle `REQUIRED_FIELDS`) zur konkreten
   Abweichung. Die `deviation_class`-Zuordnung ist ein Urteils-Call (floor=opus,
   INV-DR-6) — bei mehreren passenden Klassen die DOMINANTE waehlen + im
   `kontext`/`learning_signal` die Mehrfach-Natur notieren.
2. Append via:
   ```
   py -3 -c "import sys; sys.path.insert(0, r'.claude/scripts'); \
     from disciplinary_report import append_report; \
     print(append_report({ ...schema-dict... }))"
   ```
   (oder die Funktion direkt importieren). `True` = appended, `False` =
   Schema-Reject (Pflichtfeld fehlt / unbekannte Klasse) — dann korrigieren.
3. **NICHT-punitiv-Ton** (INV-DR-1): die Meldung ist eine Beobachtung, kein
   Vorwurf. `was_correct=true` ist der Normalfall — eine korrekte Abweichung
   bleibt meldepflichtig, weil die Stille der Fehler ist, nicht die Abweichung.

### B) Aggregate (`--aggregate` — read-only)

```
py -3 .claude/scripts/disciplinary_report.py --aggregate [--report-path=...]
```
Zeigt pro `deviation_class`: `count`, `was_correct_count`. Das ist der Strom,
den Crown-2 / der Architekt liest, um wiederkehrende Lead-Abweichungs-Muster zu
proper-fix-BLs zu verdichten (ueber [[_backlog]], NICHT hier).

---

## Abgrenzung (was der Feldjaeger NICHT ist)

- **≠ [[_sanity_check]] (Prozess-Compliance):** der prueft, ob ein Lauf dem
  designten Prozess FOLGTE (Static/Self-Healing-Audit). Der Feldjaeger trackt
  die FAELLE, in denen der Lead bewusst davon ABWICH — und WARUM. Compliance
  misst Treue; der Feldjaeger misst die begruendete Untreue als Lernsignal.
- **≠ [[_crown2_orchestrate]] (Crown-2, system-weit):** Crown-2 beobachtet die
  SOLL↔IST-Drift ueber ALLE Laeufe (Guards/Locks/Counter/Status/Contracts aus
  `deviation_signals`) und generiert proper-fix-BLs. Der Feldjaeger ist die
  **Lead-Teilmenge**: die Urteils-Calls, die kein Audit-Event hinterlassen.
  Er speist in Crown-2 ein; er baut den Generator NICHT nach (INV-DR-5).
- **≠ [[deviation_signals]] (Maschinen-Detektion):** das ist der read-only
  Sammler der AUDIT-sichtbaren Abweichungen (MOTOR_OVERRIDE/PARAM_MUTATION_BLOCKED/
  PROCESS_BYPASS_*/guard_blocks). Der Feldjaeger deckt die **nicht-audit-
  detektierbaren** Lead-Selbstmeldungen ab. **AK-4-Wiring (GEBAUT):**
  `deviation_signals._scan_disciplinary_reports` liest jetzt diese Feldjaeger-jsonl
  als **4. Quelle** (`source="disciplinary"`, `kind="lead_deviation_<class>"`) —
  damit speisen die Lead-Selbst-Reports automatisch in Crown-2s Adjudikation +
  gated Härtungs-BL-Generierung. Der Lern-Loop (Lead-Selbst-Report →
  Crown-2 → proper-fix-BL) schliesst sich; der Feldjaeger SAMMELT weiterhin nur
  (kein Urteil, kein BL-Writer hier — INV-DR-5).

> **KRUECKE, nicht Ziel (INV-DR-4):** Die Lead-Selbstmeldung ist eine
> Uebergangs-Krucke. Das ZIEL ist die **Maschinen-Hook-Detektion** (batch_2 ueber
> [[deviation_signals]]): die Abweichung soll die Maschine selbst erkennen, nicht
> der Lead per Hand melden. Denn Lead-Selbstmeldung ist WIEDER "Agent macht's,
> nicht Maschine" ([[feedback_machine_not_context]]) — genau das Anti-Pattern, das
> BL-324 langfristig aufloesen, nicht zementieren soll. Solange die Hook-Detektion
> nicht steht, faengt der Feldjaeger das Signal, das sonst still verschwaende.

---

## AK-5 — Retro-Seed (Demonstration, KEIN Live-Prod-Write)

Die ad-hoc-Abweichungen DIESER Heal-Session sind der natuerliche erste
Report-Strom — Beweis, dass die Gaps-im-Flow genau der Strom sind, den der
Feldjaeger faengt. **Demonstration im Schema, NICHT in eine echte Prod-jsonl
geschrieben** (das waere operativ; die Belege leben hier als Doku):

```jsonl
{"deviation_class":"machine_missed_catch","kontext":"BL-344 acquire_bl TOCTOU-Fang in der BL-320-Promotion-Mutex-Session","lead_reasoning":"Race zwischen rmtree-Reclaim und remkdir manuell erkannt; ein zweiter Owner konnte den frisch reclaimten Lock gewinnen","machine_should_have":"einen Concurrency-Forward-Verify-Guard fuer die acquire/reclaim-Naht haben","learning_signal":"Race-Klassen brauchen einen Forward-Verify-Companion (vgl. Forward-Verification-Pattern) -> BL-344","was_correct":true,"proposed_hardening":"_process_lock um die acquire/reclaim-Entscheidung serialisieren (BL-344 AK-3) + Race-B remkdir-FileExistsError zu sauberem False statt Crash","ts":"2026-06-13T00:00:00Z"}
{"deviation_class":"machine_missed_catch","kontext":"deviation_signals.py __main__ live-Lauf auf Windows trotz 100% gruener Tests","lead_reasoning":"die gruenen Tests deckten den __main__-CLI-Pfad nicht ab; der live-Lauf crashte mit UnicodeEncodeError (cp1252-stdout)","machine_should_have":"den __main__/CLI-Pfad als Behavior-Review-Pflicht haben, nicht nur die importierten Funktionen testen","learning_signal":"Behavior-Review > Test-Green: RUN das CLI; gruene Funktions-Tests beweisen den Prozess-Pfad nicht (a96eb1c)","was_correct":true,"proposed_hardening":"stdout+stderr.reconfigure(utf-8) im __main__ als Standard-Praeludium fuer alle read-only-CLIs","ts":"2026-06-13T00:00:00Z"}
{"deviation_class":"foresight_luecke","kontext":"test-Module mit blossem sys.exit am Modul-Ende crashten den pytest-Bulk-Lauf","lead_reasoning":"ein top-level sys.exit/Seiteneffekt beim Import bricht die gesamte pytest-Collection ab, nicht nur das eine Modul","machine_should_have":"eine Lint-/Guard-Regel gegen import-time-Seiteneffekte in test_*.py haben","learning_signal":"Test-Hygiene-Invariante: kein top-level sys.exit/IO in test-Modulen -> BL-345","was_correct":true,"proposed_hardening":"Guard/Lint: test_*.py duerfen keine import-time sys.exit/Netz/Datei-Seiteneffekte haben (nur unter __main__) -> BL-345","ts":"2026-06-13T00:00:00Z"}
```

Lese-Interpretation: 3 Eintraege, davon 2× `machine_missed_catch` + 1×
`foresight_luecke`, alle `was_correct=true`. Genau das illustriert INV-DR-1
(richtige Abweichungen sind der Normalfall + bleiben meldepflichtig) und INV-DR-4
(jedes dieser Signale ist eine Maschinen-Selbstgenuegsamkeits-Luecke, die in einen
proper-fix-BL fliesst: BL-344, die a96eb1c-Lehre, BL-345).

---

## SELBST-KONSISTENZ (BL-330 Vehikel-Doktrin)

- **B) Aggregate** ist **gruen/deterministisch** — reiner read-only Funktions-
  Aufruf (`aggregate_by_class`), workflow-faehig.
- **A) Capture** ist **rot** — die `deviation_class`-Zuordnung + `learning_signal`-
  Ableitung sind ein SOLL↔IST-Urteils-Call (GREEN-Klarheit-Klasse), floor=opus
  (INV-DR-6), NIE Workflow. Das `append_report`-Schreiben selbst ist deterministisch,
  aber das WAS-melde-ich-Urteil davor ist rot.

---

## Changelog

### v1.0.0 (2026-06-14) — BL-324 batch_1: Feldjaeger-Kern
- `disciplinary_report.py` (M3, 17 Tests gruen, beide cwds): `DEVIATION_CLASSES`
  (5 belegte Klassen) + `REQUIRED_FIELDS`/`REPORT_FIELDS` + `append_report`
  (validiert + append-only, robust) + `aggregate_by_class` (read-only, robust gg.
  kaputte/leere/fehlende Datei). cwd-stabil (BL-336), __main__ utf-8-sicher
  stdout+stderr (a96eb1c).
- Skill-Vertrag: Capture (append) + `--aggregate` (read-only). NICHT-punitiv-Ton.
- INV-DR-1..6 (Lern-Strom / Schema-Pflicht / append-only-cwd-stabil-utf8 /
  Kruecke-nicht-Ziel / REUSE-Crown-2+deviation_signals / floor=opus).
- Abgrenzung ≠ _sanity_check / ≠ Crown-2 (Lead-Teilmenge) / ≠ deviation_signals
  (nicht-audit-detektierbare Lead-Selbstmeldung). Kruecke→Hook-Ziel-Doktrin.
- AK-5 Retro-Seed: 3 Demo-Eintraege dieser Heal-Session (Doku, KEIN Prod-Write).
