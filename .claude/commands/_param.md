# /_param - Globale Session-Parameter setzen

```yaml
status: active
version: 1.2.0
created: 2026-02-28
updated: 2026-03-08
type: satellite
chain_position: standalone
team_based: false
```

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_param                                                    ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {VAULT}/_session_params.md  (aktuelle Werte)            ║
║    {VAULT}/_manifest.md        (State, GLOBAL_* Felder)    ║
║    {VAULT}/_manifest_protokoll.md  (optional: historische  ║
║                                              Session-Logs)           ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {VAULT}/_session_params.md  (PRIMAER: 7 Parameter)      ║
║    {VAULT}/_manifest.md        (SEKUNDAER: State Einzeiler)║
║    SCHREIBT NICHT: _manifest_protokoll.md  (Pattern A: reiner State)║
║                                                                      ║
║  ACTOR: DU (die ausfuehrende Claude-Instanz, KEIN Team)            ║
╚══════════════════════════════════════════════════════════════════════╝
```

### OWNERSHIP-SCHEMA (BL-159 AK-5-ERW)

**INV-OWNER-1:** Worker darf NUR `_owner=worker` oder `_owner=system` Parameter schreiben. Parameter mit `_owner=user` Inline-Suffix in `_session_params.md` sind fuer Worker GESPERRT. Versuch wird durch `guard_session_params_protection.py` als `PARAM_MUTATION_BLOCKED` geblockt und in `audit.jsonl` geloggt.

**INV-OWNER-2:** Implizite Kopplungen (z.B. `dark_factory=true` → `hil=off`) sind VERBOTEN wenn das Ziel-Feld `_owner=user` traegt — OHNE explizite HiL-Bestaetigung des Users. Worker MUSS HiL-Pause einlegen und User-Confirm einholen.

**Ownership-Klassen:**
| Klasse | Wert | Bedeutung |
|--------|------|-----------|
| `user` | `_owner: user` | Nur User oder Team-Lead darf diesen Parameter setzen |
| `worker` | `_owner: worker` | Worker darf setzen, User-Override hat Vorrang |
| `system` | `_owner: system` oder kein Marker | Pipeline-interne Parameter (z.B. `dark_factory`) |

**Guard-Enforcement:**
- `OMNI_ENFORCE_PARAM_GUARD=1` + `OMNI_AGENT_NAME=*-worker` → Block bei `_owner=user` Parametern
- Audit-Event: `PARAM_MUTATION_BLOCKED` in `.claude/audit/audit.jsonl` (Felder: event, ts, param_name, attempted_value, blocker)

---

### KOPPLUNGS-VERBOT (BL-159 AK-5b)

Erweiterung des VERTRAG-Blocks. Verbietet implizite Kopplungen, die in der Kopplungs-Matrix (siehe unten) nicht explizit dokumentiert sind. Worker, Reviewer und User koennen so erkennen, welche Mehrfach-Mutationen erlaubt sind.

Aktuelles Kopplungs-Inventar: `.claude/scripts/param_coupling_inventory.py` (Mode: `scan` oder `verify`).

**INVARIANTEN:**

**INV-COUP-1: Implizite Param-Kopplungen verboten ohne HiL-Bestaetigung**
Implizite Kopplungen (Parameter A setzt implizit Parameter B) sind VERBOTEN ohne explizite User-HiL-Bestaetigung, wenn:
- Parameter B `_owner=user` traegt, ODER
- die Kopplung A→B nicht in der Kopplungs-Matrix unten dokumentiert ist.
Worker darf nur Kopplungen ausfuehren, die in der Matrix mit Klasse HOCH oder niedriger vermerkt sind (KRITISCH-Klasse immer HiL-pflichtig).

**INV-COUP-2: dark_factory=true darf hil NICHT automatisch aendern (wenn User-owned)**
`dark_factory=true` DARF `hil` NICHT setzen, wenn `hil` mit `_owner=user` Marker in `_session_params.md` geschuetzt ist. Beispiel-Verbot: User hat `hil=phase` gesetzt → `dark_factory=true` belasst `hil=phase` — Worker muss HiL-Pause einlegen und User-Confirm einholen. Ohne `_owner=user`-Marker: Kopplung erlaubt (Matrix-Klasse KRITISCH, aber ungeblockt).

**INV-COUP-3: Nur Validations erlaubt — keine Werte-Mutationen**
Erlaubt sind ausschliesslich explizite Validations zwischen Parametern (z.B. `ceiling >= floor` Pruefung). Verboten sind alle Werte-Mutationen die einen anderen Parameter als Seiteneffekt aendern, ohne dass diese Kopplung in der Matrix dokumentiert ist:
- Kein automatisches `tdd=false` bei `dark_factory=true` (Tests opt-in, unabhaengig von BDF).
- Kein automatisches `enforceProcess=false` bei `dark_factory=true` (Guards bleiben aktiv).
- Kein automatisches `prePr=execute` bei `dark_factory=true` (Pre-PR bleibt im aktuellen Modus).
- Jede neue Kopplung MUSS zuerst in der Kopplungs-Matrix dokumentiert werden.

**INV-COUP-4: COUPLING_BLOCKED Audit-Event bei erkannter impliziter Kopplung**
Bei erkannter impliziter Kopplung ausserhalb der Whitelist: AbortException + Audit-Event `COUPLING_BLOCKED` in `.claude/audit/audit.jsonl`. Felder: `event`, `ts`, `param_source`, `param_target`, `attempted_value`, `blocker`, `reason`. Ergaenzend: `PARAM_MUTATION_BLOCKED` via `guard_session_params_protection.py` bei `_owner=user`-Verletzungen (INV-OWNER-1).

**Audit-Trail-Pflicht (INV-COUP-4 Ergaenzung):**
Wenn `/_param` mehrere Parameter atomic mutiert (z.B. `dark_factory=true` → hil + GLOBAL_MODUS), MUSS jeder Side-Effekt einzeln im `_manifest.md` Audit-Trail logged sein (Schritt 3 Z162-164).


---

## Aufruf

```
/_param [difficulty=WERT] [ceiling=WERT] [floor=WERT] [hil=WERT] [slicing=WERT] [tdd=WERT] [tdd_stages=WERT] [prePr=WERT] [bdf=WERT] [dark_factory=WERT] [pr_review_mode=WERT] [pr_create_at_end=WERT] [pr=WERT] [enforceProcess=WERT] [parallel_mode=WERT] [nr_parallel_batches=WERT] [motor_production_ready=WERT] [lane=WERT] [merge=WERT] [bl_parallel=WERT]
/_param show
/_param reset
```

| Parameter | Werte | Beschreibung |
|-----------|-------|-------------|
| `difficulty` | easy, normal, hard | Globale Schwierigkeit (ueberschreibt lokale Defaults) |
| `ceiling` | haiku, sonnet, opus | Hoechstes erlaubtes Modell fuer alle Orchestratoren |
| `floor` | haiku, sonnet | Niedrigstes Modell fuer Exploration-Wellen |
| `hil` | off, cycle, phase, manual | Human-in-the-Loop Modus (siehe HiL-Semantik) |
| `slicing` | true, false | **(BL-NEW-29, 2026-05-11)** Steuert Sub-Slicing innerhalb eines Batches. **Default: false** (Batch-as-Slice — 1 Batch = 1 Slice, mitose/fanOut/fanIn AUTO-SKIP via Single-Slice-Logik). Bei `true`: Legacy Multi-Slice-Modus mit parallelen Worktrees (Forward-Compat, derzeit nicht produktions-bereit). Blueprint-Phase (Architect/cleanCodeSlice) laeuft IMMER — slicing steuert nur ob mehrere Sub-Slices produziert werden. TDD wird NICHT deaktiviert (separat via tdd-Parameter). |
| `tdd` | true, false | Aktiviert TDD-Zyklus in der I-Pipeline (Default: false). Unabhaengig von slicing — bei slicing=false UND tdd=true laeuft TDD als Single-Slice ohne Worktrees. |
| `tdd_stages` | [1,2,3,4,5,6,7] | Welche Stufen TDD/Test-Verifikation durchlaufen (Default: alle). Beispiel: `tdd_stages=[1,3]` fuer nur Stufe 1 und 3. **Stufen-Uebersicht:** 1=Unit, 2=Module, 3=Integration (Docker, Filter PFLICHT), 4=System, 5=Frontend-only, 6=Controller-E2E (PowerShell-Script gegen laufende API), 7=User-Journey (Browser via Playwright MCP — `Skill(_user_journey)`, setzt laufendes FE+BE+DB voraus). |
| `prePr` | report, execute | Pre-PR Modus (Default: report). report=readonly Scan + Presentation + interaktive Diskussion, KEINE Auto-Fixes. execute=aktuelles Verhalten mit Auto-Fixes. |
| `bdf` | true, false | **BDF-Toggle** (PL-S2-06/S2-08, 2026-05-16): Bei true setzt GLOBAL_MODUS=big_dark_factory OHNE hil-Mutation. Saubere Trennung: BDF-Aktivierung und HiL sind orthogonal. Konsumenten: `_BDF_orchestrate` liest `bdf` statt `dark_factory`. (Default: false) |
| `dark_factory` | true, false | **DEPRECATED (PL-S2-06, 2026-05-16) — in 1 Sanity-Cycle entfernt.** Backward-Compat-Alias fuer `bdf=true hil=off` (beide werden gesetzt). Nutze stattdessen `bdf=true hil=off` separat. Kombinations-Parameter (BL-159 PL-AK5b-05): Bei true setzt GLOBAL_MODUS=big_dark_factory UND hil=off. User-Override via `_owner=user` Marker blockiert hil-Mutation (OWNERSHIP-GUARD). |
| `pr_review_mode` | true, false | **PR-Review-Modus** (PL-S2-05, 2026-05-16): Bei true aktiviert M8 in SDF (NUR Analyse + Bewertung, KEINE Implementierung). Aktiviert `/_git_analyse` Phase in A_orchestrate. Ersetzt den ueberladenen `pr`-Parameter. (Default: false) |
| `pr_create_at_end` | true, false | **PR-Create-Toggle** (PL-S2-05, 2026-05-16): Bei true erstellt Workflow am Ende automatisch einen PR. Default: derived from `bdf=true` (bei BDF-Lauf automatisch true). Unabhaengig von `pr_review_mode`. |
| `pr` | true, false | **ALIAS fuer `pr_review_mode`** (PL-S2-05, 2026-05-16). Backward-Compat — nutze `pr_review_mode` fuer Klarheit. **WARNING: `pr`-Param-Name ist ueberladen (Review vs Create). Neue Namen `pr_review_mode` und `pr_create_at_end` sind semantisch klarer.** |
| `enforceProcess` | true, false | Guard-Enforcement (BL-023): Bei true BLOCKIEREN Guards Violations (Mega-Agent, BDF-Bypass, Orchestrator-via-Agent, Wellen-Fehler). Bei false nur WARNUNG — Ausnahme-Modus wenn Prozess nicht korrekt funktioniert. (Default: true) |
| `pattern_scan_threshold` | Integer >= 1 | Minimum-Vorkommnisse fuer Pattern-Kandidat in `_PT_arch_init` und M2-Walk (AK-C-5, BL-153). Default=5. Kein Hardcode in Commands — IMMER aus _session_params.md lesen. |
| `parallel_mode` | true, false | **Parallel-Dial Master-Schalter (BL-327, 2026-06-12).** **Default: false** = heutiger serieller Pfad BYTE-IDENTISCH (Null-Risiko-Fallback + Kill-Switch). Bei true greift der Single/Wave-Pfad (BL-328/BL-230). Drei Betriebszustaende OFF→SINGLE→WAVE (siehe `nr_parallel_batches`). Lese-Zeitpunkt motorseitig NUR an der Wellen-Barrier; Kill-Switch (true→false) laesst laufende Welle auslaufen. **Kombi-Regel:** parallel_mode=false ERZWINGT nr_parallel_batches=1 (Resolver-Clamp). |
| `nr_parallel_batches` | Integer >= 1 | **Wellen-Breite wenn parallel_mode=true (BL-327, 2026-06-12).** **Default: 1.** **N=1 = SINGLE-MODE** (voller Fan-Out/Fan-In-Pfad inkl. Worktree, aber genau 1 Batch pro Welle = Mechanik-Probe OHNE Concurrency). **N≥2 = WAVE** (echte Parallelitaet, erst hinter den Gates A–C). N<1 ist invalid (ValueError). Bei parallel_mode=false wird N zwangsweise auf 1 normalisiert. effective_fanout=min(N,\|welle\|,caps) ist motorseitig (kann nur SENKEN, nie heben). **Verbotene Bypass-Felder** (analog INV-MODUS-5, kein zweiter Schreibweg am Dial vorbei): `force_parallel`, `wave_override`, `parallel_override`, `nr_parallel_override` — eine Params-Quelle mit einem dieser Felder wird vom Resolver mit ValueError geblockt. |
| `motor_production_ready` | true, false | **Motor-Produktions-Lock / Gate-D-Schwelle (BL-373, 2026-06-16).** Steuert, ob der `dispatch_implement`-Motor im SDF-OUTER-LOOP ueberhaupt erlaubt ist. **Default: false** = Motor VERBOTEN → altmodischer Lead-driven Multi-Sub-Batch-Pfad (vor Gate-D der einzige korrekte Pfad, [[feedback_motor_erst_nach_stabilisierung]]). Erst NACH Gate-D vom Architekten auf `true` (zusammen mit `workflow!=false`); dann gilt `motor_allowed = gate_d_passed AND vehicle_for(dispatch_implement,workflow)==workflow`. Der Motor ist strukturell green (deterministisch), dieser Flag ist der ZUSAETZLICHE temporale Vertrauens-Lock. _owner=user. |
| `lane` | A, B, C (frei) \| (leer) | **Roadmap-Lane-Marker (BL-442 W14, INV-WT-DIAL).** Markiert, **welche Lane dieser Worktree/Lauf ist** — die Lane nimmt ihr naechstes BL aus IHRER Queue (kollisionsfrei, respektiert HOLD + owned-by-other-lane) via `roadmap_status --respect-lanes --lane={X}` + `lane_plan.next_bl_for_lane`. **Default: leer** (= kein Lane-Override, serieller Single-Lane-Standard). Pro Worktree EINMAL setzen (`/_param lane=A`), wird in `_session_params.md` abgelegt. Kann auch aus dem Branch `roadmap-{x}` abgeleitet werden. Zentrale Verteilung: `{vault}/Konzepte/Multi-Lane-Verteilung_*.md`. _owner=user. |
| `merge` | true, false | **Merge-Seam-Toggle (BL-425).** Bei `true` (Default) macht der BL-Abschluss (Post-SDF TERMINATE) automatisch den develop-Resync via `lane_develop_sync` + `merge_seam` (CLEAN→ff, CONFLICT/DIRTY→PL+Hold). Begleit-Params: `merge_target` (Default `develop`), `merge_timing` (Default `per_bl`). So arbeitet das naechste BL auf frisch-synchronisiertem Stand. _owner=user. |
| `bl_parallel` | true, false | **BL-Parallel-Dial (BL-431, INV-WT-DIAL).** Orthogonal zu `parallel_mode` (das steuert Fanout INNERHALB eines Batches). `bl_parallel` steuert, ob **mehrere BL-Items parallel** ueber Worktrees bearbeitet werden (1 Worktree = 1 Lane). **Default: false.** Kein Bypass-Feld (`force_bl_parallel` → ValueError). Vorbedingung INV-WT-SEQUENZ: Parallel-Maschine erst seriell bauen + nach develop mergen, DANN Split. _owner=user. |
| `show` | — | Zeigt aktuelle globale Parameter |
| `reset` | — | Entfernt alle GLOBAL_* Felder (zurueck zu lokalen Defaults) |

**HiL-Semantik:**

| Wert | Bedeutung | Wann wird User gefragt? |
|------|-----------|------------------------|
| `off` | Vollautomatisch, kein HiL | Nie (Dark Factory Modus) |
| `cycle` | Nach jedem Zyklus/Stufe | Standard — nach SC-Zyklus, nach I-Pipeline-Stufe |
| `phase` | Nach jeder Phase | Feinere Granularitaet — nach jeder Pipeline-Phase |
| `manual` | Nur auf explizite Anforderung | Nur wenn Orchestrator auf Blocker trifft |

**Beispiele:**
```
/_param difficulty=hard ceiling=opus floor=sonnet    → Volle Kraft
/_param difficulty=normal ceiling=sonnet floor=haiku  → Standard
/_param ceiling=sonnet                                → Nur ceiling aendern
/_param hil=off                                       → Dark Factory (vollautomatisch)
/_param hil=cycle ceiling=sonnet                      → Standard HiL + Sonnet-Cap
/_param tdd=true                                      → TDD aktivieren (unabh. von slicing)
/_param tdd=true tdd_stages=[1,3]                     → TDD nur fuer Stufe 1 und 3
/_param show                                          → Aktuellen Stand zeigen
/_param reset                                         → Globale Parameter entfernen
```

---

## Modell-Hierarchie

```
Opus(3) > Sonnet(2) > Haiku(1)
```

**Validierung:** ceiling >= floor (sonst Fehler).
**Capping-Formel (von Orchestratoren angewandt):**
```
effektiv_ceiling = min(lokal_ceiling, GLOBAL_CEILING)
effektiv_floor   = max(lokal_floor, GLOBAL_FLOOR)
effektiv_difficulty = GLOBAL_DIFFICULTY (falls gesetzt, ueberschreibt lokal)
```

---

## Schritte

### Schritt 1: Argumente parsen

Parse `$ARGUMENTS` nach key=value Paaren:
- `difficulty=X` → validiere X in {easy, normal, hard}
- `ceiling=X` → validiere X in {haiku, sonnet, opus}
- `floor=X` → validiere X in {haiku, sonnet}
- `hil=X` → validiere X in {off, cycle, phase, manual}
- `tdd=X` → validiere X in {true, false}. KEIN Auto-Toggle (BL-148): Auto-TDD-Override existiert nicht, daher kein tdd_user_locked-Schutz noetig.
- `tdd_stages=X` → validiere X als Subset von [1,2,3,4,5] (z.B. [1,3,5])
  - **WARNING (RF-02):** Falls tdd_stages=[] (leere Liste) UND tdd=true:
    Logge: "WARNING: tdd_stages ist leer aber tdd=true. Keine Stufe wird ausgefuehrt. Setze tdd_stages=[1,2,3,4,5] oder tdd=false."
- `prePr=X` → validiere X in {report, execute}
- `bdf=X` → validiere X in {true, false}; bei true: setze GLOBAL_MODUS=big_dark_factory OHNE hil-Mutation. Kein OWNERSHIP-GUARD erforderlich (keine hil-Kopplung).
- `pr_review_mode=X` → validiere X in {true, false}. Alias-Behandlung: `pr=true` wird als `pr_review_mode=true` gewertet (Backward-Compat).
- `pr_create_at_end=X` → validiere X in {true, false}. Default: bei `bdf=true` automatisch true, sonst false (ableitbar, kein expliziter Wert notwendig).
- `pr=X` → Backward-Compat-Alias fuer `pr_review_mode`. Setze intern `pr_review_mode=X`.
- `dark_factory=X` → validiere X in {true, false}; **DEPRECATED (PL-S2-06)** — behandle als `bdf=X hil=off` Kombi. Bei true: **OWNERSHIP-GUARD** (BL-159 PL-AK5b-01):
    ```
    session_params = lies("{VAULT}/_session_params.md")
    hil_owner_marker = session_params.match(r'^\*\*_hil_owner:\*\*\s*user') OR
                       session_params.match(r'^\*\*_owner:\*\*\s*user')
    IF hil_owner_marker AND args.dark_factory == "true":
      HiL-Pause: "BLOCKED: dark_factory=true wuerde hil=off setzen, aber _owner=user fuer hil registriert.
                  W12 (User-Set sakrosankt) — bestaetige Override oder ABBRUCH."
      IF user_confirm != "force": ABBRUCH "OWNERSHIP_GUARD: dark_factory blocked"
    setze hil=off + GLOBAL_MODUS=big_dark_factory  # nur wenn nicht geblockt
    ```
  Begruendung: Pflaster fuer Kopplungs-Bypass (W15 code-grounded). Sub-Items PL-AK5ERW-01..03 (vollstaendiges _owner-Schema) bleiben DEFERRED bis OQ-2 resolved.
- `enforceProcess=X` → validiere X in {true, false}. Bei true: Guards BLOCKIEREN Violations. Bei false: Guards nur WARNING (Ausnahme-Modus). Default: true.
- `motor_production_ready=X` → validiere X in {true, false}. **BL-373 (2026-06-16):** Gate-D-Schwelle fuer den `dispatch_implement`-Motor. Default: false (Motor verboten vor Gate-D → altmodischer Pfad). _owner=user. Erst NACH Gate-D auf true. Wird vom `_SDF_orchestrate` OUTER-LOOP Vehikel-Gate gelesen (`motor_allowed = gate_d_passed AND vehicle_for(dispatch_implement,workflow)==workflow`).
- `show` → springe zu Schritt 4
- `reset` → springe zu Schritt 5
- Keine Argumente → zeige aktuellen Stand (wie `show`)

### Schritt 2: Validierung

Falls sowohl ceiling als auch floor angegeben (oder einer gesetzt + anderer aus Manifest):
```
Hierarchie-Werte: opus=3, sonnet=2, haiku=1
IF ceiling_wert < floor_wert:
  FEHLER: "ceiling ({ceiling}) darf nicht unter floor ({floor}) liegen."
  ABBRUCH.
```

### Schritt 3: In _session_params.md schreiben

Lies `{VAULT}/_session_params.md`.
Ueberschreibe die gesamte Datei mit genau diesem Format (7 Zeilen + Header):

```
# Session-Parameter
**HiL:** {hil_wert}
**difficulty:** {difficulty_wert}
**ceiling:** {ceiling_wert}
**floor:** {floor_wert}
**slicing:** {slicing_wert}
**tdd:** {tdd_wert}
**tdd_stages:** {tdd_stages_wert}
**prePr:** {prePr_wert}
```

Nicht angegebene Parameter behalten ihren aktuellen Wert.

**Zusaetzlich:** Aktualisiere auch `{VAULT}/_manifest.md` (Audit-Trail):
- Setze/aktualisiere `**GLOBAL_DIFFICULTY:**`, `**GLOBAL_CEILING:**`, `**GLOBAL_FLOOR:**`, `**GLOBAL_HIL:**`, `**GLOBAL_SLICING:**`
- Bei `bdf=true`: setze `**GLOBAL_MODUS:**` auf `big_dark_factory` (OHNE hil-Mutation)
- Bei `dark_factory=true` (DEPRECATED): setze `**GLOBAL_MODUS:**` auf `big_dark_factory` UND hil=off (Kombi-Alias-Verhalten)
- Falls Feld existiert: ueberschreiben. Falls nicht: nach PUSH_STATUS einfuegen.

### Schritt 4: Show (Anzeige)

Lies `{VAULT}/_session_params.md` und zeige:
```
Globale Parameter:
  GLOBAL_DIFFICULTY: {wert | "nicht gesetzt (lokale Defaults)"}
  GLOBAL_CEILING:    {wert | "nicht gesetzt (lokale Defaults)"}
  GLOBAL_FLOOR:      {wert | "nicht gesetzt (lokale Defaults)"}
  GLOBAL_HIL:        {wert | "nicht gesetzt (Default: cycle)"}

Effektive Wirkung auf Orchestratoren:
  Explorer:  {floor}
  Drafter:   {middle}
  Synthese:  {ceiling}
  HiL-Modus: {hil_wert} → {beschreibung}
```

**HiL-Beschreibungen fuer Show:**
- `off` → "Vollautomatisch, keine HiL-Pausen"
- `cycle` → "HiL nach jedem Zyklus/Stufe (Standard)"
- `phase` → "HiL nach jeder Phase (feingranular)"
- `manual` → "HiL nur bei Blockern (minimal)"

### Schritt 5: Reset

Ueberschreibe `{VAULT}/_session_params.md` mit Defaults:
```
# Session-Parameter
**HiL:** cycle
**difficulty:** normal
**ceiling:** sonnet
**floor:** haiku
**slicing:** true
**tdd:** false
**tdd_stages:** [1,2,3,4,5]
**prePr:** report
**pattern_scan_threshold:** 5
```
Entferne alle `**GLOBAL_*:**` Zeilen aus dem Manifest (Audit-Trail bereinigen).
Melde: "Globale Parameter zurueckgesetzt. Orchestratoren nutzen Defaults."

---

## BL-174 BL-Scope Erweiterung

**Version:** 1.3.0 (BL-174, 2026-05-19) — Per-BL Session-Params mit 3-Stufen-Inheritance.

### Neues Flag: --bl-id=BL-{NNN}

```
/_param hil=phase --bl-id=BL-174          → schreibt in {BL_FOLDER}/_session_params.md
/_param ceiling=opus                        → schreibt in {VAULT}/_session_defaults.md (Standard)
/_param show --bl-id=BL-174               → zeigt resolved Params fuer BL-174 (alle 3 Stufen)
/_param difficulty=hard --bl-id=BL-174    → BL-174-spezifischer Override
```

### Inheritance-Reihenfolge (INV-PARAM-RESOLVE-2)

```
1. {BL_FOLDER}/_session_params.md    (hoechste Prioritaet — per-BL Override)
2. {VAULT}/_session_defaults.md      (mittlere Prioritaet — Vault-weite Defaults)
3. Framework-Defaults (in Code)      (niedrigste Prioritaet — Fallback)
```

Resolver: `.claude/scripts/session_params_resolver.py`

```
py -3 session_params_resolver.py resolve --param=hil --bl-id=BL-174
py -3 session_params_resolver.py resolve-all --bl-id=BL-174
```

### Default-Logik ohne Flag

- Falls `current_context.py` aktiven BL erkannt hat → automatisch BL-Scope
- Sonst → Vault-Default (`{VAULT}/_session_defaults.md`)
- Keine Flag = kein BL-Scope-Override (Vault/Framework-Fallback)

### BL-spezifische _session_params.md — Pfad und Format

Pfad: `{VAULT}/Backlog/BL-{NNN}-{slug}/_session_params.md`

```markdown
---
bl_id: BL-{NNN}
scope: per-bl
updated: 'YYYY-MM-DD'
---

# Session-Params Override: BL-{NNN}

**hil:** phase _owner: user
**difficulty:** hard _owner: user
```

Oder als Markdown-Tabelle:

```markdown
| Parameter | Wert | Owner |
|-----------|------|-------|
| hil | phase | user |
| difficulty | hard | user |
```

### Guard-Enforcement (unveraendert, BL-159)

`guard_session_params_protection.py` blockt Worker-Writes sowohl auf
`{BL_FOLDER}/_session_params.md` als auch auf `{VAULT}/_session_defaults.md`.
Whitelist bleibt: `/_param`, `/_backlog`.

### Backward-Compat (BL-174 AK-6)

- Bestehende `{VAULT}/_session_params.md` bleibt unberuehrt (Legacy-Fallback)
- BL-172 Worktree-Namespace-Files bleiben parallel aktiv
- Kein Breaking Change

---

## Orchestrator-Integration

Alle Orchestratoren lesen Parameter beim Start aus `{VAULT}/_session_params.md` (NICHT aus dem Manifest — das Manifest ist zu gross fuer Worker-Kontext).

Ab BL-174: Orchestratoren SOLLEN `session_params_resolver.resolve_all_params(bl_id=current_bl_id)` nutzen statt direktem File-Read — dann greift die 3-Stufen-Inheritance automatisch.

**Anwendungsformel (von Orchestratoren angewandt):**
```
params = lies("{VAULT}/_session_params.md")
difficulty = params.difficulty    # easy | normal | hard
ceiling    = params.ceiling       # opus | sonnet | haiku
floor      = params.floor         # opus | sonnet | haiku
hil        = params.HiL           # off | cycle | phase | manual
tdd        = params.tdd           # true | false (Default: false)
tdd_stages = params.tdd_stages    # [1,2,3,4,5] (Default: alle)
prePr      = params.prePr         # report | execute (Default: report)
```

**HiL-Entscheidungslogik:**
```
off     → [kein HiL]   (nur Blocker)
manual  → [nur Blocker] (semantisch "User will manuell steuern")
cycle   → [nach Zyklus] (SC: nach SC-Cycle, I: nach Stufe, WP: nach Kapitel)
phase   → [nach Phase]  (SC: nach observe/hypothese/..., I: nach codeAtomic/codeSystem/...)
```

**Sicherheitsnetz:** Auch bei `hil=off` werden BLOCKER-HiL-Punkte NICHT uebersprungen:
- Entity-Readiness BLOCKED → immer HiL
- Gate FAIL (nicht CONDITIONAL) → immer HiL
- Irrecoverable Errors → immer HiL

---

## Tests (BL-159 AK-5b)

### I-AK5b-02: Positiv-Pfad — dark_factory=true ohne User-gesetztes hil [PL-AK5b-08]

**Setup:**
- `_session_params.md` enthaelt KEIN `_owner: user` und KEIN `_hil_owner: user` fuer `hil`.
- Aktueller Wert: `hil: cycle` (Default) oder anderer non-user-owned Wert.

**Aktion:**
```
/_param dark_factory=true
```

**Erwartetes Verhalten:**
- KEINE HiL-Pause (OWNERSHIP-GUARD nicht ausgeloest mangels `_owner=user` Marker).
- `_session_params.md` wird aktualisiert: `hil: off`.
- `_manifest.md` wird aktualisiert: `GLOBAL_MODUS: big_dark_factory`.
- Beide Mutationen erfolgen atomar im selben `/_param`-Aufruf.

**Verifikation:**
- `_session_params.md`: `**HiL:** off` (overridden von dark_factory).
- `_manifest.md`: `**GLOBAL_MODUS:** big_dark_factory` (gesetzt oder ueberschrieben).
- Audit-Trail: Beide Mutationen logged als Konsequenz EINES `/_param dark_factory=true`-Aufrufs.

**Negativ-Pendant:** Siehe I-AK5b-01 (PL-AK5b-07) — User-gesetztes hil=phase → HiL-Pause erwartet (separate Test-Datei, derzeit deferred).

---

## Kopplungs-Matrix (BL-159 AK-5b)

Dokumentiert alle impliziten Parameter-Kopplungen, die `/_param` auf einmal mutiert. Quelle der Wahrheit fuer Worker, Reviewer und User — welche Side-Effekte sind erlaubt, welche verboten.

| Parameter A | Parameter B | Condition | Direction | Kopplungs-Klasse | Beschreibung |
|-------------|-------------|-----------|-----------|------------------|--------------|
| `dark_factory=true` | `hil=off` | Immer (ausser OWNERSHIP-GUARD-Block via `_owner=user`-Marker, Schritt 1 Z115) | hart, gerichtet (A → B) | KRITISCH | Setzt hil zwangs-off. Side-Effekt nur via `_owner=user`-Marker blockierbar (W12 sakrosankt). |
| `dark_factory=true` | `GLOBAL_MODUS=big_dark_factory` | Immer (geht ueber OWNERSHIP-GUARD hinweg — Modus-Set blockiert nicht) | hart, gerichtet (A → B) | HOCH | Schreibt `**GLOBAL_MODUS:** big_dark_factory` ins Manifest (Schritt 3 Z163). |

**OQ-3 (self): RESOLVED** — Matrix dokumentiert die zwei harten Kopplungen, die `/_param dark_factory=true` ausloest. Direction ist immer `A → B` (Source-Param treibt Target-Param). Klasse KRITISCH/HOCH differenziert: KRITISCH = User-Override moeglich (OWNERSHIP-GUARD), HOCH = unkonditional (Modus-Setzung).

---

## BL-176 User-Override Re-Prioritization (AK-7, 2026-05-19)

**Version:** 1.4.0 (BL-176 AK-7, 2026-05-19) — Manuelle BL-Reihenfolge-Overrides.

### Neues Flag: `priority_override`

```
/_param priority_override --bl-id=BL-XXX KRITISCH
/_param priority_override --bl-id=BL-XXX HOCH
/_param priority_override --bl-id=BL-XXX MITTEL
/_param priority_override --bl-id=BL-XXX NIEDRIG
```

**Wirkung:** Schreibt `manual_priority: KRITISCH` in das BL-Frontmatter (1_Task/*.md oder direkt in BL-Ordner-Frontmatter). `_BDF_berater_blSequencePlanner` liest diesen Wert als Priority-Tiebreak-Override.

### Neues Frontmatter-Feld: `manual_sequence_override`

```yaml
# In BL-Frontmatter (1_Task/BL-NNN_Task.md):
manual_sequence_override: 3   # Position-Hint im Sequence-Index (0-basiert)
```

**Wirkung:** `_BDF_berater_blSequencePlanner` verschiebt das BL auf Position N in der topologischen Reihenfolge — NUR wenn dadurch kein Dependency-Zyklus entsteht.

### Quality-Check (INV-PARAM-OVERRIDE-1)

```
IF manual_sequence_override gesetzt:
  pruefe: BL an Position N nicht vor seinen Dependency-BLs
  IF Cycle-Check FAIL:
    Logge: "WARNING: manual_sequence_override fuer {bl_id} verletzt Dep-Constraint — ignoriert"
    # Override wird NICHT angewendet — Sequence-Planner entscheidet korrekte Position
  ELSE:
    Override anwenden (Position-Hint einhalten)
```

**Invariante INV-PARAM-OVERRIDE-1:** Override respektiert Cycle-Constraints. Kein Override kann ein blocked BL (BL mit offenen, unerfuellten Dependencies) vorreihen.

### Aufruf-Beispiele

```
/_param priority_override --bl-id=BL-177 KRITISCH    → BL-177 erhaelt hoechste Prioritaet
/_param priority_override --bl-id=BL-178 HOCH        → BL-178 wird vor MITTEL/NIEDRIG gereiht
/_param show --bl-id=BL-177                          → Zeigt resolved Priority + Override-Status
```

### Schreib-Logik

```
1. Lies BL-Frontmatter: {vault_root}/Backlog/BL-{NNN}-*/1_Task/*.md
2. Setze/aktualisiere: manual_priority: {WERT}
3. Logge: "BL-{NNN} manual_priority auf {WERT} gesetzt (BL-176 AK-7)"
4. Audit-Event: PRIORITY_OVERRIDE in .claude/audit/audit.jsonl
   Felder: event, ts, bl_id, old_priority, new_priority, actor=user
```

---

## Impact-Analyse — dark_factory caller (BL-159 AK-5b)

Vollstaendige Inventur aller `/_param dark_factory=true`-Aufrufer im OmniCommand-Repository (27 Commands gescannt).

**Direkte Caller (1):**
- `_BDF_orchestrate.md:312` — Big Dark Factory Meta-Orchestrator setzt `dark_factory=true` als Default-Eintritts-Condition.

**Eigenstaendige GLOBAL_MODUS-Setter (1, kein _param-call):**
- `_SDF_orchestrate.md:308` — Small Dark Factory setzt `GLOBAL_MODUS=big_dark_factory` direkt im Manifest, ohne `/_param`-Indirektion. Diese Setzung umgeht die Kopplungs-Matrix oben (kein Coupling-Test ausloesbar).

**Weitere indirekte Caller (0):**
- 27 Commands gescannt (alle `.claude/commands/*.md`). Keine weiteren direkten `dark_factory=true`-Aufrufe.

**Folge:**
- Kopplungs-Verbot (siehe VERTRAG unten) gilt fuer alle Worker auf `_BDF_orchestrate`-Pfad.
- SDF-Direkt-Setter bleibt Out-of-Scope fuer PL-AK5b-Kopplungs-Tests; sollte als separates Item dokumentiert werden (Sub-Item-Kandidat ausserhalb dieses Batches).

---
