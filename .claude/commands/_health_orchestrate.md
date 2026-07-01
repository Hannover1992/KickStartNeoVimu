---
status: active
version: 1.0.0
created: 2026-06-13
op: HealthOrchestrate
phase: Meta
type: orchestration
feature_anchor: BL-335
related: [resolve_format_version(BL-333), vault_lock(BL-334), _sanity_check, _D_kollaps]
---

# /_health_orchestrate — STATE-Format-Drift Scan + Heilung (Umbrella-Core)

**Zweck:** Das homoeostatische Dach (BL-322 EPIC) fuer die *Langzeit-Artefakte* des
Vaults. Es scannt die State-Artefakte (zuerst `_manifest.md`) auf **Format-Drift**
— ungestempelte / veraltete `format_version` — meldet die Befunde als Report und
heilt sie kontrolliert, gestaffelt nach Sicherheits-Klasse. Es vereint die bisher
verstreuten Wartungs-Scripts (manifest_slim, reconcile_backlog_index,
propagate_provenance, stamping, GC, ...) unter EINEM Dach und reduziert damit die
Scatter (BL-322 Design-Fork).

Es orchestriert das bereits gebaute Backend `health_orchestrate.py` (BL-335) ueber
die Member-Registry `health_registry.yaml`. Dieses Skill ist der Host: es loest das
Vehikel, ruft das Backend, liest den Report und fuehrt — nur im `heal`-Modus und nur
nach safety_class-Policy — die Heilung aus.

---

## Aufruf

```
/_health_orchestrate [--mode=report-only|dry-run|heal] [--vault=<pfad>]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|--------------|
| `--mode` | `report-only` | `report-only \| dry-run \| heal` | Tiefe des Eingriffs (siehe Modes-Tabelle) |
| `--vault` | auto-resolved | Pfad | Vault-Root; default ueber `resolve_format_version.resolve_vault_root` (Single Source VAULT_ROOT) |

**Beispiele:**
```
/_health_orchestrate                    → nur Scan + Report (read-only, IMMER safe)
/_health_orchestrate --mode=dry-run     → Report + Heil-Plan ANZEIGEN, NICHT ausfuehren
/_health_orchestrate --mode=heal        → Report + Heilung ausfuehren (safety_class-gated)
```

---

## VERTRAG

```
+======================================================================+
| COMMAND: /_health_orchestrate [--mode=...] [--vault=...]            |
+======================================================================+
|                                                                      |
| ACTOR: HEALTH-ORCHESTRATOR (Team Lead direkt)                       |
|                                                                      |
| DEFAULT-MODUS: report-only — read-only, IMMER safe (STRUKTURELL:    |
|   plan_heal() gibt bei report-only [] zurueck; OBERSTE Sicherheits- |
|   Invariante des Backends).                                         |
|                                                                      |
| LIEST:                                                               |
|   .claude/config/health_registry.yaml   (die 14 Member + safety)   |
|     -> Vault-First: {vault}/config/health_registry.yaml zuerst     |
|   {vault}/_manifest.md                   (Format-Drift-Scan-Ziel)  |
|   weitere bekannte State-Artefakte       (read-only, best-effort)  |
|                                                                      |
| SCHREIBT:                                                            |
|   report-only:  NICHTS (kein einziger Schreibzugriff)              |
|   dry-run:      NICHTS (Plan wird nur ANGEZEIGT, execute=False)    |
|   heal:         NUR via safety_class-Policy:                       |
|     - auto  -> Heiler schreibt direkt                              |
|     - lock  -> Heiler schreibt unter vault_lock zweck=health_heal  |
|                (BL-334; nur nach erfolgreichem acquire)            |
|     - hil   -> KEIN Auto-Write; wartet auf Mensch-Freigabe         |
|                                                                      |
| BACKEND: .claude/scripts/health_orchestrate.py                      |
|   API: load_health_registry, generate_health_report,              |
|        render_report_markdown, plan_heal(report, mode),           |
|        MODES, SAFETY_CLASSES, DEFAULT_MODE='report-only'          |
|   CLI: python3 .claude/scripts/health_orchestrate.py --mode=...    |
+======================================================================+
```

---

## Modes-Tabelle

| Mode | Was | Schreibt? |
|------|-----|-----------|
| `report-only` (DEFAULT) | Scan + Report. `plan_heal()` -> `[]` (strukturell, keine Action). Reine STATE-Diagnose. | NEIN — read-only, strukturell garantiert. |
| `dry-run` | Report + voller Heil-Plan, jeder Eintrag mit `execute=False`. Zeigt, was *geheilt wuerde*, fuehrt aber NICHTS aus. | NEIN — Plan wird nur angezeigt. |
| `heal` | Report + Plan + Ausfuehrung, safety_class-gegated (auto direkt / lock unter Lock / hil nur mit Freigabe). | JA, aber NUR nach Policy (siehe unten). |

Der `--mode`-Param ist die einzige Stellschraube fuer die Eingriffstiefe. Default
`report-only` ist read-only by-design — kein Bypass, keine versteckten Schreibpfade.

---

## Member-Dispatch-Flow

Der Orchestrator arbeitet die Registry-Member deterministisch ab. Das Backend
(`health_orchestrate.py`) traegt die Logik; der Host loest das Vehikel und routet.

```
1. SCAN
   load_health_registry()                  -> 14 Member {drift_typ, detector,
                                               healer, safety_class, status}
   generate_health_report(vault_root)       -> pro Artefakt: format_version_ist
                                               (read_format_version; ungestempelt=0)
                                               vs format_version_soll
                                               (resolve_format_version je Typ);
                                               daraus detected_drifts (closed vocab:
                                               missing_format_version | version_lag).
   Heal-Recommendations sind DRIFT-TYP-GEMATCHT: pro erkannter Drift NUR die Member,
   deren drift_typ passt (KEIN blanket-all; ein Heiler pro Drift).

2. REPORT
   render_report_markdown(report)           -> Mensch-lesbarer Markdown-Report
                                               (Artefakt-Tabelle IST/SOLL + Heal-
                                               Empfehlungen). Bei report-only ENDE.

3. PLAN  (nur mode != report-only)
   plan_heal(report, mode)                  -> dry-run: Eintraege execute=False
                                               heal: safety_class-Gating je Eintrag.

4. AUSFUEHRUNG  (nur mode == heal)
   Pro Plan-Eintrag nach safety_class (siehe Policy-Doku):
     auto -> Heiler-CLI direkt ausfuehren.
     lock -> vault_lock acquire (zweck=health_heal, BL-334) -> Heiler -> release.
     hil  -> NICHT ausfuehren; dem Owner zur Freigabe vorlegen.
   Unbekannte/fehlende safety_class -> fail-safe: needs_lock + needs_freigabe,
   execute=False (kein Auto-Eingriff).
```

### Die 14 Member (nach status gruppiert)

**13 wired** — verdrahtet auf gebaute Scripts (Scatter-Reduktion: Wartungs-Tools unter
ein Dach geholt). BL-338 (batch_PL3) hat die 4 vormals new_to_create-Member verdrahtet
und GC generalisiert (3 typ-spezifische gc_slim_general-Member):

| Member | drift_typ | safety_class | Heiler |
|--------|-----------|--------------|--------|
| `manifest_slim` | manifest_bloat | lock | `manifest_slim.py slim {bl_id}` |
| `reconcile_backlog_index` | index_split_brain | auto | `reconcile_backlog_index.py --apply --ts {DATUM}` |
| `validate_backlog_frontmatter` | frontmatter_schema | auto | (nur Report, healer=null) |
| `propagate_provenance_validate` | provenance_mismatch | auto | `propagate_provenance.py update ...` |
| `d_kollaps` | truth_bloat | hil | `/_D_kollaps {feature}` |
| `stamping_heiler` | missing_format_version | auto | `resolve_format_version.stamp_format_version_lines` |
| `backup_retention` | manifest_corpses | lock | `backup_retention.py prune {family} --keep=2` (find_backups/prune_backups) |
| `audit_log_rotation` | audit_log_bloat | auto | `audit_rotation.py --keep=2000` (rotate_audit/rotate_log) |
| `blueprint_sidecar_ttl` | sidecar_ttl | auto | `sidecar_ttl.py {bl_folder} --ttl-days=N` (find_sidecars/prune_sidecars) |
| `budget_watch` | binary_artifact_bloat | auto | (DETECTOR-ONLY, healer=null — `budget_watch.py {root}`) |
| `backlog_index_slim` | index_bloat | lock | `gc_slim_general.py slim {path} backlog_index` |
| `parking_lot_slim` | pl_bloat | lock | `gc_slim_general.py slim {path} parking_lot` |
| `model_slim` | model_bloat | lock | `gc_slim_general.py slim {path} model` |

**1 spec_only** — spezifiziert, noch nicht implementiert:

| Member | drift_typ | safety_class | Hinweis |
|--------|-----------|--------------|---------|
| `truth_migration` | truth_format_drift | hil | BL-309 (Truth-Migration), detector/healer noch null |

**0 new_to_create** — BL-338 (batch_PL3) hat die letzten 4 verdrahtet; alle bekannten
Slots tragen jetzt einen Detector (budget_watch ist DETECTOR-ONLY by-design).

`budget_watch` ist DETECTOR-ONLY (PL-338-7): binaere/grosse Artefakte (Screenshots,
PDFs, Presentations) sind BY-DESIGN gross — der Member weist ihre GROESSE im Report aus
und flaggt `over_budget` gegen gc_budgets, HEILT aber NICHTS (`healer: null`). Das ist
gewollt, kein fehlender Heiler; ein Auto-Slim auf Binaer-Artefakte waere falsch.

Member mit `status != wired` werden vom Report aufgefuehrt, erzeugen aber (mangels
detector/healer) noch keine ausfuehrbare Heal-Action — sie sind dokumentierte
Erweiterungs-Slots, keine erfundenen Heiler.

---

## Policy-Doku (safety_class — owner-owned, PL-335-4)

Die `safety_class` jedes Members ist konservativ gesetzt (BL-322 Design-Fork: im
Zweifel lieber NICHT automatisch eingreifen) und vollstaendig owner-owned — sie wird
in `health_registry.yaml` im `safety_class`-Feld parametrisiert und kann vom Owner
ueberschrieben werden. Es gibt KEINE im Skill verdrahtete Policy; die Config IST die
Policy.

| safety_class | Bedeutung | Mitglieder (Stand 2026-06-13) | Schreib-Mechanik im heal-Mode |
|--------------|-----------|-------------------------------|-------------------------------|
| `auto` | Sicher genug fuer direkte Ausfuehrung | reconcile_backlog_index (Index-Reconcile), validate_backlog_frontmatter (Frontmatter-Report), stamping_heiler (Stamping), propagate_provenance_validate (Provenance), audit_log_rotation, blueprint_sidecar_ttl, budget_watch | Heiler schreibt direkt (`execute=True`). |
| `lock` | Destruktiv genug fuer Quiescenz-Schutz | manifest_slim (Slim), backup_retention (Backup-Retention/GC), backlog_index_slim / parking_lot_slim / model_slim (gc_slim_general, typ-param. Auslager-Write) | NUR unter `vault_lock` (zweck=`health_heal`, BL-334). Caller `acquire` -> Heiler -> `release`. `execute=False` bis Lock haelt. |
| `hil` | Irreversibel / urteilsbeduerftig | d_kollaps (destruktiver Wahrheiten-Kollaps), truth_migration (BL-309) | KEIN Auto-Execute (`needs_freigabe=True`). Dem Owner zur Mensch-Freigabe vorlegen. |

Fail-safe: eine unbekannte oder fehlende safety_class wird vom Backend als
`needs_lock + needs_freigabe, execute=False` behandelt — also maximal vorsichtig, nie
Auto-Eingriff. Konservativ ist der Default-Bias; Lockerung ist eine bewusste
Owner-Entscheidung in der Config.

---

## Healer-Contract (detect → classify → heal|abort)

Jeder `/_health`-Heiler greift potenziell schreibend in ein Langzeit-Artefakt ein,
das eine andere (aeltere oder fremde) Format-Generation tragen kann als die Engine
erwartet — die Redeploy-Generations-Luecke aus INV-HEALTH-1. Damit kein Heiler ein
fremd-formatiertes Artefakt blind ueberschreibt oder an ihm crasht, erfuellt jeder
Heiler am Eingang einen festen 3-Schritt-Contract:

1. **DETECT** — Der Heiler liest die Format-Generation seines Inputs: die
   Top-Level-`format_version` via `resolve_format_version.read_format_version`.
   Fehlt der Stempel, ist die erkannte Generation `0` (Gen-0) — `read_format_version`
   gibt strukturell `0` zurueck, NIE einen Crash.
2. **CLASSIFY** — Der Heiler ordnet seinen Zustaendigkeits-Fall ein:
   - **zustaendig** (`ist == soll`): die Generation entspricht der Soll-Generation
     (`resolve_format_version` fuer den Artefakt-Typ).
   - **fremde / aeltere Generation ohne registrierte Migration** (`ist != soll`,
     `soll != None`): die Generation weicht ab und es gibt keinen Migrations-Pfad.
   - **Registry nicht aufloesbar** (`soll == None`): die Soll-Generation kann nicht
     ermittelt werden.
3. **HEAL|ABORT** — Der Heiler entscheidet je Fall:
   - zustaendig (`ist == soll`) → **heilen** (normaler Lauf).
   - ungestempelt / Gen-0 (`ist == 0`) → **PROCEED + WARN**: solange die Stempelung
     noch nicht universal gewired ist, sind ALLE Bestands-Artefakte Gen-0; ein hartes
     Abort darauf wuerde die Fabrik stallen. Darum proceedet der Heiler (Dual-Read;
     der lossless-verify-Gate schuetzt interim) und gibt eine Stempelungs-Empfehlung
     auf stderr aus, statt abzubrechen.
   - explizit gestempelte FREMDE Generation ohne Migration (`ist > 0`, `ist != soll`,
     `soll != None`) → **SAFE-ABORT**: klare Meldung mit {erkannte Generation,
     erwartete Generation, Migrations-Pfad}, KEIN destruktiver Write, KEIN
     Crash/Traceback — ein kontrollierter, lesbarer Abbruch. Das ist der echte
     "inkompatible Generation"-Fall.
   - `soll == None` → **PROCEED**: Dual-Read-Resilienz; eine fehlende Registry darf
     einen Heiler NIE crashen lassen, der Lauf geht weiter.

Strikter Abort auf ungestempelte ALT-STRUKTUR (der echte 1944-Schutz) ist Follow-up,
sobald die Stempelung universal gewired ist.

**Referenz-Beispiel:** `manifest_slim.py` Funktion `_assert_manifest_generation`
(BL-336, der erste gehaertete Heiler). Sie liest die Manifest-Generation aus dem
Frontmatter (`read_format_version` → DETECT), vergleicht `ist` gegen
`resolve_format_version("manifest")` (CLASSIFY) und entscheidet vor jedem
Manifest-Write: `soll is None` oder `ist == soll` → PROCEED; `ist == 0` (Gen-0) →
PROCEED + stderr-WARN; nur eine explizit gestempelte FREMDE Generation (`ist > 0`,
`ist != soll`) → SAFE-ABORT via `RuntimeError` mit Migrations-Hint (kein partieller
Byte-Write). Der Spezialfall ist die 1944-Klasse: ein 234KB-Manifest ungestempelt →
`ist == 0`, `soll == 1` → in der jetzigen Transition PROCEED + WARN (Stempelung noch
nicht universal); SAFE-ABORT trifft erst eine fremd gestempelte Generation. Gleiches
"kein destruktiver Write"-Prinzip wie der `require_quiescent`-Abbruch.

Damit kuenftige Heiler diesen Schutz nicht versehentlich auslassen, ist der Contract
als nummerierte Invariante festgeschrieben:

> **INV-HEALTH-2 (Healer-Contract):** Jeder `/_health`-Heiler MUSS am Eingang den
> 3-Schritt-Contract erfuellen — (1) DETECT die Format-Generation seines Inputs
> lesen (`read_format_version`; ungestempelt = Gen-0, nie Crash); (2) CLASSIFY
> zustaendig (`ist == soll`) | ungestempelt/Gen-0 (`ist == 0`) | explizit gestempelte
> FREMDE Generation ohne registrierte Migration (`ist > 0`, `ist != soll`) | Registry
> nicht aufloesbar (`soll == None`); (3) HEAL|ABORT — zustaendig → heilen;
> Gen-0 → PROCEED + stderr-WARN (Transition, da Stempelung noch nicht universal
> gewired); fremd gestempelte Generation ohne Migration → SAFE-ABORT (klare Meldung
> mit erkannter/erwarteter Generation + Migrations-Pfad, KEIN destruktiver Write,
> kein Crash); `soll == None` → PROCEED (Dual-Read-Resilienz). Strikter Abort auf
> ungestempelte ALT-STRUKTUR ist Follow-up, sobald die Stempelung universal gewired
> ist. Jeder NEUE Member erfuellt den Contract; Bestands-Member werden beim
> Verdrahten gehaertet. Wer einen Heiler ohne diese Generations-Pruefung verdrahtet,
> verletzt INV-HEALTH-2. [BL-336]

**Bezug zu BL-335 (Member-Registry-Vertrag):** Der Healer-Contract ist Teil des
Member-Vertrags in `health_registry.yaml`. Member mit `status: wired` SOLLTEN ihn
erfuellen (Bestands-Heiler werden beim Verdrahten gehaertet — `manifest_slim` ist der
erste); Member mit `status: new_to_create` MUESSEN ihn beim Bau ihres Detectors/Healers
von Anfang an erfuellen. So waechst der Generations-Schutz mit jedem neuen Member mit,
statt nachtraeglich nachgeruestet werden zu muessen.

**BL-338 (die 4 neu-verdrahteten + gc_slim_general):** Die in batch_PL3 verdrahteten
Heiler erfuellen INV-HEALTH-2 — sie operieren je auf ihrem EIGENEN Artefakt-Typ und
schreiben verlustfrei: `backup_retention` (prunt nur jenseits der keep_n juengsten, mit
MD5-vor-Prune-Verify gegen Out-of-Band-Tampering), `audit_rotation` (archiviert die
aeltesten Zeilen lossless mit MD5-Header, behaelt die guard-relevanten RECENT-Marker),
`sidecar_ttl` (archiviert ERST lossless DANN prunt, nur bei story_done + TTL). Die 3
`gc_slim_general`-Member uebernehmen das `manifest_slim.verify_split`-lossless-Gate
direkt (jede nicht-leere Original-Zeile in kept ODER archived) — derselbe MD5-Beweis wie
der Referenz-Heiler. `budget_watch` ist DETECTOR-ONLY und beruehrt nie ein Artefakt,
faellt also nicht unter den Schreib-Teil des Contracts (kein HEAL|ABORT noetig).

---

## Abgrenzung sanity vs health (PL-335-5)

`/_health_orchestrate` und die `_sanity_*`-Familie loesen ZWEI verschiedene Probleme
und duerfen NIE zu einem gemeinsamen Dach verschmolzen werden:

- **`_sanity_*` = PROZESS-Compliance.** `_sanity_check`, `_sanity_check_dynamic`,
  `_sanity_check_pre`, `_sanity_check_post`, `_sanity_process` auditieren, ob *die
  Pipeline sich an den Prozess haelt* (Skill-Vertraege, Invarianten, Step-Adherence,
  Manifest-Delta gegen erwartete Ausfuehrung). Frage: *Laeuft die Fabrik regelkonform?*
- **`/_health` = STATE-Format-Drift + Heilung.** Frage: *Sind die Langzeit-Artefakte
  format-aktuell und gesund?* (format_version-Stempel, Index-Split-Brain, Bloat,
  Provenance). Es prueft nicht den Prozess, sondern den *Zustand* der Artefakte ueber
  die Zeit, und heilt ihn.

Damit kuenftige Arbeit die beiden nicht versehentlich verschmilzt, ist die Trennung
als nummerierte Invariante festgeschrieben:

> **INV-HEALTH-SANITY-SEP:** `/_health_orchestrate` (STATE-Format-Drift + Heilung)
> und die `_sanity_*`-Familie (PROZESS-Compliance-Audit) bleiben strukturell
> getrennt. KEIN gemeinsames Dach, kein gemeinsamer Orchestrator, keine
> wechselseitigen Member. Ein Sanity-Skill darf KEINE State-Heilung ausloesen; ein
> Health-Member darf KEINEN Prozess-Compliance-Audit kapseln. Wer beide vereinen
> will, verletzt INV-HEALTH-SANITY-SEP. [BL-335 / PL-335-5]

---

## INV-HEALTH-1 — Redeploy-Self-Check

Ein Redeploy tauscht die **Engine** (Skills + Scripts + Infrastruktur), NICHT den
**State** (Vault-Artefakte). Daraus entsteht eine Generations-Luecke: die frische
Engine erwartet ein neues Artefakt-Format, der mitgewanderte Alt-Vault traegt es aber
noch nicht. Das ist Engine-Austausch am fahrenden Auto.

> **INV-HEALTH-1:** Nach JEDEM Redeploy MUSS `/_health_orchestrate` (zuerst
> `report-only`) gegen den Ziel-Vault laufen, gefolgt von der empfohlenen Heilung.
> Der Redeploy ist erst dann abgeschlossen, wenn der Health-Self-Check gruen ist
> (kein offener Format-Drift) oder die Heal-Empfehlungen ausgefuehrt wurden.

**Konkreter Praezedenz-Fall (Case 1944):** ein 234KB-Manifest ohne
`format_version`-Stempel. `/_health_orchestrate report-only` erkennt das
deterministisch — `read_format_version` liefert `ist == 0` (`_detect_drifts` ->
`missing_format_version`), gematcht auf den `stamping_heiler` (safety_class `auto`).
Der Report empfiehlt `{stamp, slim}` **OHNE Crash** (der Backend-Loader ist
Dual-Read-resilient, Gen-0-Pfad faengt ungestempelte Artefakte ab). Erst danach
heilt der `heal`-Mode: `stamping_heiler` (auto, direkt) und — falls Bloat — der
`manifest_slim` (lock, unter `vault_lock`).

**Forward-Verify (PL-335-6):** Diese Invariante ist dormant bis zum ersten echten
Live-Redeploy. Beim naechsten Redeploy ist zu verifizieren, dass der
`report-only`-Self-Check die Generations-Luecke crash-frei erkennt und korrekte
{stamp, slim}-Empfehlungen ausgibt — der retrospektive Beweis ist hier nicht
moeglich, er muss am Live-Lauf eingeloest werden.

---

## Placement-Matrix (Self-Check-Einbau-Punkte)

INV-HEALTH-1 ist der erste, harte Einbau-Punkt (Post-Redeploy), aber nicht der einzige.
`/_health_orchestrate report-only` ist read-only und IMMER safe — es laesst sich darum an
mehreren strategischen Naehten des Systems einbauen. Die Matrix listet die bekannten
Einbau-Punkte; sie ist ERWEITERBAR (ueber `/_health` an strategischen Stellen einbauen,
sobald neue Seams entstehen).

| Seam | Mode | mandatory / optional |
|------|------|----------------------|
| POST-REDEPLOY | report-only (min) → heal | **mandatory** (INV-HEALTH-1, via `guard_redeploy_health`) |
| PRE-230-WELLE | report-only → heal | **mandatory** sobald Wellen existieren (kranker State + Parallelitaet = multiplizierter Schaden) |
| PRE-BDF-CYCLE | report-only | optional (billig) |
| PERIODISCH | report-only | via Crown-Watchdog |
| MANUELL | beliebig | `/_health` on demand |

**POST-REDEPLOY** ist der gehaertete Pflicht-Punkt (siehe INV-HEALTH-1 oben). **PRE-230-WELLE**
wird mandatory, sobald die erste echte Welle existiert (Phase E der 230-Roadmap): paralleles
Schreiben auf einen format-driftigen Vault multipliziert den Schaden statt den Durchsatz, darum
muss der State VOR jeder Welle gesund sein (Gate-H-Kopplung). **PRE-BDF-CYCLE** und **PERIODISCH**
sind billige Vorsorge-Punkte (report-only kostet nichts), **MANUELL** ist der Owner-Direktzugriff.
