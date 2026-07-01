# /_vehikel — Vehikel-Doktrin: Team vs Workflow (BL-330 Zonen-Routing)

```yaml
status: active
version: 1.0.0
created: 2026-06-12
op: Vehikel
phase: Meta
type: doctrine
chain_position: cross-cutting
```

## Zweck (projekt-unabhaengiger Engine-Kanon)

Diese Doktrin ist FESTER BESTANDTEIL von OmniCommand — sie lebt in der Engine (reist mit jedem
Redeploy), NICHT im projekt-gebundenen Agent-Memory. User-Direktive 2026-06-12: "so ist das in den
Prozess selbst gebaut."

OmniCommand faehrt JEDE dispatchbare Aktivitaet mit genau EINEM von zwei Vehikeln. Der Team Lead
wechselt ABWECHSELND zwischen beiden im selben Lauf (verallgemeinerter Handschuh-Wechsel — erweitert
das BDF<->SDF-Puppet-Master-Muster um Team<->Workflow):

| Zone | Vehikel | Mechanik |
|---|---|---|
| **rot + gelb** (kognitiv: Diskretion, Interpretation, Urteil) | **benanntes TEAM** | `TeamCreate` (Team MIT Namen) -> `Agent(name=..., team_name=...)` benannte Member -> `TaskCreate` mit `blockedBy` = Task-DAG (Dependencies) -> `SendMessage` Member-Koordination -> Lead trackt via TaskList/TaskGet/TaskUpdate |
| **gruen** (hart-deterministisch: festes I/O, kein Urteils-Seam) | **WORKFLOW** | deterministischer Motor, fire-and-collect |

**Router:** `py -3 .claude/scripts/workflow_zones.py vehicle --activity={X} --mode={workflow-Param}`
-> `workflow` | `advisory` | `worker`. Die Registry (`ZONE_REGISTRY`) ist die maschinenlesbare
Determinismus-Karte (Quelle: BL-330-Klassifikation, 104 Komponenten / 6 Schichten).

## Warum (User-Empirie, 2026-06-12 — die Begruendung IST Teil des Kanons)

1. **Teams sind bewaehrt** — gute Erfahrung seit der Vor-Opus-4.8-Aera; die gesamte
   Berater-Architektur (teamSetup-Klasse, BERATER_OUTPUTS-Trennung, Phase-Separation) ist darauf
   gebaut. Das ist kein Experiment, sondern der gewachsene, validierte Kern.
2. **Workflows sind real schneller** — fuer deterministische Ketten entfaellt "das Zwischending"
   (Interpretations-Schicht): stabiler UND schneller bei festem I/O.
3. **Der Kern-Grund fuer Team-bei-kognitiv: gegenseitige Sichtbarkeit faengt false-GREEN.**
   Benannte Member SEHEN einander und einander Claims — "GREEN bei TDD? GREEN bei einer
   MIGRATION? Kannst du dir abschminken." Ein Member mit Kontext erkennt, dass ein GREEN auf
   einem Ziel-Artefakt ohne RED-Pfad (Migration, Markdown) bedeutungslos ist, und sagt es.
   Ein Workflow kennt nur das Outcome-Label und winkt durch. Belege: BL-312 (Dilution),
   BL-334 (parallel-Key), BL-341 (Prosa-Marker) — alle test-gruen-aber-falsch, alle NUR durch
   Dialog/Behavior-Review gefangen; 30-Iter-Burn Fable-as-Workflow an TDD-auf-Migration.

## Der 3-Modi-Dial (`workflow`-Param, BL-174-Resolver)

```
workflow ∈ {false, normal, fast}     default: "false"     (Aliase: true/on->normal, off->false)
  false  = ALLES altmodisch (benannte Teams)   — Verhalten wie vor BL-330, byte-identisch
  normal = gruene Zone als Workflow            ; gelb + rot als Team
  fast   = gruen als Workflow, gelb advisory   ; rot IMMER Team
           (advisory = Workflow rechnet/scannt/scored, benannter Member/Lead bestaetigt das Urteil)
```

## Invarianten

- **INV-VEHIKEL-1 (Router-Pflicht):** Vor jedem Dispatch einer Aktivitaet konsultiert der Lead
  `vehicle_for(activity, workflow_mode)`. gruen->Workflow, gelb->advisory, rot->Team-Member.
- **INV-VEHIKEL-2 (rot-nie-Workflow):** Die rote Zone (C3-modusEntscheidung, TDD-Kern
  _TDD_red/green/refactorCode/refactorTests/check, goldDefine, cleanCodeSlice, cleanCodeArchitect,
  _I_verify, modelSync-Wahrheit, batchPlan-Adjudikation, specParse-Intent, sc_verdict) laeuft in
  KEINEM Modus als Workflow — strukturell erzwungen (`resolve_vehicle` rot-Kurzschluss; kein
  cognitive/all-Modus im Enum; unbekannte Aktivitaet -> rot fail-safe).
- **INV-VEHIKEL-3 (Team heisst Team):** "altmodisch" bedeutet NICHT Lead-direkt oder ein
  anonymer Einzel-Worker. Es bedeutet: benanntes Team + benannte Member + Task-DAG mit
  Dependencies + SendMessage-Koordination. Mehrere interdependente kognitive Schritte = EIN Team
  mit DAG, nicht N unkoordinierte Spawns. (Die gegenseitige Sichtbarkeit ist der Punkt — sie ist
  der false-GREEN-Faenger.)
- **INV-VEHIKEL-4 (eine Stellschraube):** Der `workflow`-Param ist der EINZIGE Schaltweg.
  Bypass-Felder (`force_workflow`, `ultracode_force`, `workflow_zone_override`,
  `motor_zone_force`) -> ValueError im Resolver. Ultracode-/Auto-Workflow-Reflex bleibt abgelehnt:
  jeder Workflow-Einsatz ist eine Zonen-Entscheidung per Karte, nie ein Default.
- **INV-VEHIKEL-5 (Selbst-Konsistenz):** Auch BEIM BAUEN von OmniCommand selbst gilt die Karte —
  der rote Bau-Kern (TDD auf Engine-Code) laeuft als Team, gruene Verifikation/Klassifikation
  (read-only Survey) darf als Workflow laufen. Praezedenz: der BL-330-Dial wurde selbst so gebaut.
- **INV-VEHIKEL-6 (Ketten-Granularitaet — die Dispatch-Einheit ist die KETTE, nicht der Step):**
  Ein Workflow lohnt nur ueber eine ZUSAMMENHAENGENDE gleich-Vehikel-Kette (amortisiert
  Engine-Setup, gewinnt Determinismus-/Idempotenz-/Parallel-Garantien). Eine EINZELNE gruene
  Aktivitaet, eingebettet in kognitive (rote/gelbe) Schritte, laeuft INLINE — der Team-Member
  fuehrt den deterministischen Tool-/CLI-Call selbst aus. KEIN Workflow-Setup fuer 1 Step
  (Overhead ohne Gewinn). Faustregel: Workflow ab Kette >=2-3 konsekutiver gruener/advisory
  Schritte; Lead bestimmt die Kette aus der REIHENFOLGE der Pipeline (nicht aus der Aktivitaets-
  MENGE). Konsequenz: der Build-Inner-Loop (TDD/Architekt/Gold) ist rot-dominant mit ISOLIERTEN
  gruenen Steps (TDD_setup/teardown) -> Team-inline, kein Workflow. Konkrete Ketten-Daten unten.

## INV-VEHIKEL-6 Daten-Anhang: Workflow-faehige Ketten je Pipeline (2x chain-map-verifiziert + korrigiert 2026-06-12)

Quelle: `workflow_zones.py` ZONE_REGISTRY (live via `vehicle`-CLI). Kette = max. konsekutiver Run mit
`vehicle != worker` (len>=2) entlang des LINEAREN Ausfuehrungs-Pfads.

> **WICHTIG — 2-Lauf-Korrektur:** Der 1. Lauf (`ketten-karte`) meldete max **len-3**. Das war ein
> MESS-ARTEFAKT: ~40 deterministische Berater waren NICHT in der Registry und fielen auf den
> Fail-Safe-RED (`workflow_zones.py` zone_of unbekannt->red), der korrekt-gruene Ketten kuenstlich
> zerhackt. Der 2. Lauf (`ketten-recheck-unregistriert`) klassifizierte sie nach + die Registry wurde
> vervollstaendigt. Untenstehende Werte sind die KORRIGIERTEN.

| Pipeline | Laengste Kette | Steps |
|---|---|---|
| **SDF Pre-Plan** | **len=7** | resumeGuard->validator->dependencyAnalyzer->sequencePlanner->batchPlanner->itemContext->analyse |
| **SDF Post-Bookkeeping** | **len=7** | stageElevation->post_sc_pl_resync->batchEnde->garbageCollection->stateMaintain->loopDecision->orphan_scan (modelSync = isolierte rote Insel) |
| **IDF-Start** | **len=5** | loopCheck->teamSetup->init->resumeGuard->validator |
| IDF-Organisation | len=4 | bottleneckTrigger->dependencyAnalyzer->clustering->sequencePlanner |
| **A-Ende** | **len=4** | plAggregation->metadatenAggregation->gitTracking->stateMaintain |
| Closure/PostBatch | len=1 | KEINE Kette — gruene Lock/Fan-In-Spine motor-INTERN |

**REGEL INV-VEHIKEL-6b (Registry ist Pflicht):** ZONE_REGISTRY ist NICHT optional fuer deterministische
Berater. Jeder green/yellow-Berater MUSS explizit (lowercased key) eingetragen werden — sonst zerhackt der
Fail-Safe (rot-Default) korrekt-gruene Ketten und blockiert Workflow-Faehigkeit im normal-Modus. Die
rot-Invariante bleibt absichtlich fail-safe-getragen, ABER die echten Seams (modusEntscheidung, modelSync,
plBewertung, specParse, TDD-Kern, _I_verify, Wissensbau model/spec/taskDefinition/domainBrief/findingsReview/
dispatch_findings) werden ZUSAETZLICH EXPLIZIT rot eingetragen — damit rot dokumentiert statt zufaellig ist.

**Muster (bestaetigt + geschaerft):** Determinismus sitzt an den Pipeline-RAENDERN (Setup/Plan/Aggregations-/
Bookkeeping-Schwaenze = lange gruene Ketten), die roten Seams sind ISOLIERTE INSELN in der Mitte
(C3-modusEntscheidung, modelSync/Truth, plBewertung/Saettigung, batchPlan, TDD-Kern, A-Wissensbau).
Hoechste Gruen-Dichte: **SDF** (zwei len-7-Schwaenze), NICHT A — der User-Riecher 'A gruenlicher' ist wahr
nur an den A-RAENDERN (Front len-2, Schwanz len-4, Terminal A_postRoute), die A-Mitte bleibt korrekt rot.

## Aufruf

```
# Zone einer Aktivitaet:
py -3 .claude/scripts/workflow_zones.py zone --activity=_TDD_red

# Vehikel-Entscheid (Modus aus Session-Params aufloesen, dann routen):
py -3 .claude/scripts/session_params_resolver.py resolve --param=workflow --bl-id={BL_ID}
py -3 .claude/scripts/workflow_zones.py vehicle --activity={X} --mode={resolved}

# Gesamte Registry:
py -3 .claude/scripts/workflow_zones.py dump
```

## Verbote (Anti-Pattern)

- Eine rote Aktivitaet "weil eilig" als Workflow fahren — strukturell geblockt, nicht verhandeln.
- Eine gelbe advisory-Rechnung autonom das Urteil SCHREIBEN lassen (advisory heisst: Member/Lead
  bestaetigt; der eine eingebettete Seam ist load-bearing — BL-312-Mechanismus).
- Kognitive Mehr-Schritt-Arbeit als unkoordinierte Einzel-Spawns statt benanntem Team + DAG.
- Die Registry per Prosa "ueberstimmen" — Zonen-Aenderung = Edit in `workflow_zones.py`
  (test-gedeckt, behavior-reviewed), nie ad-hoc im Kopf.
- Ein urteils-tragender NEUER Guard, der vom `guard_`-Praefix gruen erbt: MUSS explizit als
  `red` in die Registry (Registry-Lookup schlaegt Praefix-Regel).

## Verwandte

- `.claude/scripts/workflow_zones.py` — die maschinenlesbare Karte (Registry + Resolver, 51 Tests
  mit `test_workflow_zones.py` + `test_session_params_resolver.py`)
- `.claude/scripts/session_params_resolver.py` — der `workflow`-Param (3-Stufen-Inheritance)
- Vault `Konzepte/Determinismus-Karte_Zonen-Dial_BL-330_2026-06-12.md` — die menschenlesbare
  Voll-Karte (104 Komponenten, Flow-Projektion, Risiken; projekt-Vault, nicht Engine)
- CLAUDE.md INV-VEHIKEL-Familie — Kurzanker, laedt jede Session
- Langfristige Heimat der Voll-Karte: der /_help-Rewrite (BL-330 AK-1-Restschritt)
