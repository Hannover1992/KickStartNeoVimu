---
type: satellite
---

# TDD-Pipeline - Hilfe & Uebersicht

Zeige die Uebersicht der TDD-Pipeline (/_TDD_*) Commands.

## Aufruf

```
/_TDD_help
```

---

## Updates 2026-05-19 (BL-173/174/175 Cross-Cutting)

**Deprecation-Hinweis (BL-169, 2026-05-09):**
- TDD-Pipeline ist in die I-Pipeline integriert — `/_TDD_orchestrate` wird von `/_I_orchestrate` als
  Playbook-Wechsel gesteuert. Kein eigenstaendiger Aufruf vorgesehen.
- Aktivierung weiterhin via `/_param tdd=true` (unterstuetzt BL-174 Per-BL-Override)

**Manifest-Routing (BL-173):**
- TDD-State (`TDD-STATE.md`) liegt im `{bl_folder}/` — kein Eintrag in `_factory_manifest.md`
- `{vault}/_factory_manifest.md` behaelt ausschliesslich BDF+GLOBAL_*-Bloecke
- Helper: `manifest_reader.read_bl_block(bl_id, ...)` liest TDD-State aus BL-Ordner

**Session-Params Per-BL (BL-174):**
- 3-Stufen-Inheritance: BL-Override → Vault-Default → Framework-Default
- `/_param tdd=true --bl-id=BL-XXX` aktiviert TDD nur fuer dieses BL
- Resolver: `session_params_resolver.resolve_param("tdd", bl_id="BL-XXX")`

**BDF Factory-Lock (BL-175):**
- `acquire/release/heartbeat` via `factory_lock.py`
- TTL+Heartbeat, kein fcntl, eigenes `_factory_lock.md`
- Race-Condition-safe fuer 5-10 parallele BDFs

(siehe `/_help` TEIL 8c, BL-173/174/175 Spec-Dateien)

---

## POSITION IN DER PIPELINE-REISE (3er-Doppel-Sicht, NEU 2026-05-24)

> **Cross-Reference:** Vollstaendige Reise + Geister-Tabelle: `/_help` TEIL 10
> Methodik: `.claude/INSTRUCTION_full_scan_2026-05-24.md`

**Wo sitzen die TDD-Sub-Skills?**

Nach BL-169 (2026-05-09) sind die TDD-Skills KEINE eigene Pipeline mehr —
sie sind **Steps 9-18 INNERHALB der I-Pipeline** (`/_I_orchestrate`).

```
/_I_orchestrate Steps 9-18 (pro Stage, nur wenn --tdd=true):
   9   _TDD_init           (HiL-Wizard, 1x pro Stage)
   10  _TDD_red             (Failing Test schreiben)
   9b  _TDD_setup           (Container/DB-Spinup, BL-NEW-53)
   11  _TDD_execute + monitor (RED-Assert + Healthcheck-Monitoring BL-NEW-62)
   12  _TDD_green           (minimaler Code)
   13  _TDD_execute + monitor (GREEN-Assert)
   14  _TDD_refactorCode    (Opus-Pflicht, Pattern-Konsultation)
   15  _TDD_execute + monitor (GREEN-Stay)
   16  _TDD_refactorTests   (Tests spezifischer)
   17  _TDD_execute + monitor (GREEN-Stay)
   18b _TDD_teardown        (Container/Process-Cleanup, BL-NEW-53)
   18  _TDD_check           (GOLD-Check)
```

**3er-Doppel-Fenster pro TDD-Step:**

Pro TDD-Step ist [N-1] der vorherige TDD-Step (oder Blueprint Step 8 fuer Step 9),
[N+1] der naechste TDD-Step (oder Closure Step 19 fuer Step 18).

**Beispiel (Step 12 _TDD_green):**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `_TDD_execute` (Step 11)         | RED-Assert-Result + TDD-STATE.md state |
| [N  ]    | `_TDD_green` (Step 12)           | LIEST + SCHREIBT (minimaler Code) |
| [N+1]    | `_TDD_execute` (Step 13)         | Was wird gelesen (GREEN-Assert)? |

**Geister-Beteiligung:**

- **Intra-Geister:** Pro Step ein Mini-Handover (TDD-STATE.md ist das Vehikel)
- **Setup/Execute-Trennung (BL-NEW-52):** Pflicht bei Stage 3+ — `_TDD_init` macht Setup (Docker/DB), `_TDD_execute` NUR `dotnet test`
- **Worker-Tier (BL-NEW-51):** sonnet/opus PFLICHT — haiku VERBOTEN (Stuck-Risiko bei Polling/Recovery)

**Status nach BL-169:**

- `/_TDD_orchestrate` ist **DEPRECATED** (alter Top-Level-Orchestrator)
- TDD-Sub-Skills (`_TDD_init`, `_TDD_red`, `_TDD_green`, `_TDD_refactorCode`, `_TDD_refactorTests`, `_TDD_execute`, `_TDD_check`, `_TDD_setup`, `_TDD_teardown`, `_TDD_monitor`) bleiben aktiv
- Kein eigenstaendiger Aufruf — IMMER via `/_I_orchestrate --tdd=true`

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  TDD-PIPELINE v1.0 (7 Commands + 1 Playbook)                          ║
║                                                                         ║
║  Uncle Bob Red-Green-Refactor in der I-Pipeline.                        ║
║  Playbook: /_TDD_orchestrate (von I_orchestrate gesteuert).            ║
║  Kein eigenstaendiger Aufruf — immer Teil des Stufen-Loops.            ║
║                                                                         ║
║  Aktivierung: /_param tdd=true                                         ║
║  Stufen-Filter: /_param tdd_stages=[1,3,5]  (Default: alle)           ║
║                                                                         ║
║  ═══ TDD-ZYKLUS (pro Stufe, pro Slice) ═══                            ║
║                                                                         ║
║  /_TDD_orchestrate (PLAYBOOK — kein eigenstaendiger Aufruf)            ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Wird von /_I_orchestrate als Playbook-Wechsel geladen.          │   ║
║  │  Steuert TDD fuer EINE Stufe: Ring-Planung + 8a-8i + QG.        │   ║
║  │                                                                   │   ║
║  │  Schritt 7a: TDD_INSTRUCTIONS.md befuellen                       │   ║
║  │    → testbefehl, mock_scope, infrastruktur aus stage_{N}.md      │   ║
║  │                                                                   │   ║
║  │  Schritt 7b: Ring-Planung (pro Slice)                            │   ║
║  │    → Konzentrische Ringe, Gold, Kanarienvoegel                   │   ║
║  │    → SCHREIBT: TDD-STATE.md                                      │   ║
║  │                                                                   │   ║
║  │  Schritt 8: TDD-Zyklus (Innerer Loop)                           │   ║
║  │  ┌──────────────────────────────────────────────────────────┐    │   ║
║  │  │                                                          │    │   ║
║  │  │  8a. /_TDD_red           Failing Test schreiben          │    │   ║
║  │  │      ↓                                                   │    │   ║
║  │  │  8b. /_TDD_execute       MUSS rot sein                   │    │   ║
║  │  │      ↓ (Backtrack → 8a bei Failure)                      │    │   ║
║  │  │  8c. /_TDD_green         Minimaler Code fuer GREEN       │    │   ║
║  │  │      ↓                                                   │    │   ║
║  │  │  8d. /_TDD_execute       MUSS gruen sein                 │    │   ║
║  │  │      ↓ (Backtrack → 8c bei Failure)                      │    │   ║
║  │  │  8e. /_TDD_refactorCode  Code refaktorisieren            │    │   ║
║  │  │      ↓                                                   │    │   ║
║  │  │  8f. /_TDD_execute       Nach Refactor gruen?            │    │   ║
║  │  │      ↓ (Backtrack → 8e bei Failure)                      │    │   ║
║  │  │  8g. /_TDD_refactorTests Tests refaktorisieren           │    │   ║
║  │  │      ↓                                                   │    │   ║
║  │  │  8h. /_TDD_execute       Nach Test-Refactor gruen?       │    │   ║
║  │  │      ↓ (Backtrack → 8g bei Failure)                      │    │   ║
║  │  │  8i. /_TDD_check         GOLD erreicht?                  │    │   ║
║  │  │      → NOT_YET: zurueck zu 8a (naechster Ring)           │    │   ║
║  │  │      → GOLD_REACHED: Slice DONE                          │    │   ║
║  │  │                                                          │    │   ║
║  │  └──────────────────────────────────────────────────────────┘    │   ║
║  │                                                                   │   ║
║  │  Schritt 9:  /_I_verify (pro Slice)                              │   ║
║  │  Schritt 10: /_I_fanIn  (NUR bei slicing=true)                   │   ║
║  │  Schritt 11: Stufen-QG (Kanarienvogel-Check)                    │   ║
║  │                                                                   │   ║
║  │  → Rueckkehr an /_I_orchestrate                                  │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
║  ═══ COMMAND-DETAILS ═══                                               ║
║                                                                         ║
║  /_TDD_red                                                             ║
║  │  Schritt 8a: Failing Test schreiben (1 Test pro Ring)               ║
║  │  Actor: TDD-CODER. Liest TDD-STATE.md, schreibt NEUEN Test.        ║
║  │  Test MUSS fehlschlagen (Red). KEIN Production-Code.                ║
║  │                                                                      ║
║  /_TDD_execute                                                         ║
║  │  Schritt 8b/8d/8f/8h: Test-Suite ausfuehren                        ║
║  │  Erwartet RED oder GREEN je nach Phase.                             ║
║  │  Bei unerwartetem Ergebnis: Backtrack (max 3x pro Schritt).        ║
║  │                                                                      ║
║  /_TDD_green                                                           ║
║  │  Schritt 8c: Minimaler Code fuer GREEN                             ║
║  │  So wenig Code wie moeglich, damit der Test gruen wird.             ║
║  │  KEINE Generalisierung, KEINE "Verbesserungen".                     ║
║  │                                                                      ║
║  /_TDD_refactorCode                                                    ║
║  │  Schritt 8e: Code generischer machen                               ║
║  │  Duplikate entfernen, Patterns anwenden. Tests muessen gruen bleiben.║
║  │                                                                      ║
║  /_TDD_refactorTests                                                   ║
║  │  Schritt 8g: Tests spezifischer machen                             ║
║  │  Test-Klarheit, Duplikate, Naming. Tests muessen gruen bleiben.     ║
║  │                                                                      ║
║  /_TDD_check                                                           ║
║  │  Schritt 8i: GOLD erreicht?                                        ║
║  │  Prueft Gold-Kriterien (aus Ring-Planung). GOLD → Slice DONE.       ║
║  │  NOT_YET → naechster Ring (zurueck zu 8a).                          ║
║                                                                         ║
║  ═══ BACKTRACK-MAP ═══                                                 ║
║                                                                         ║
║  ┌──────────────────────┬──────────┬────────────────────────┐          ║
║  │ Schritt              │ Erwartet │ Bei Failure → zurueck  │          ║
║  ├──────────────────────┼──────────┼────────────────────────┤          ║
║  │ 8b: execute(RED)     │ ROT      │ → 8a: red              │          ║
║  │ 8d: execute(GREEN)   │ GRUEN    │ → 8c: green            │          ║
║  │ 8f: execute(GREEN)   │ GRUEN    │ → 8e: refactorCode     │          ║
║  │ 8h: execute(GREEN)   │ GRUEN    │ → 8g: refactorTests    │          ║
║  └──────────────────────┴──────────┴────────────────────────┘          ║
║                                                                         ║
║  MAX_BACKTRACK_PER_STEP = 3                                            ║
║  Bei Erschoepfung + HiL=off + Stufe<=2: Auto-SKIP Ring                ║
║  Bei Erschoepfung + HiL=off + Stufe>=3: Alarm → I_orchestrate         ║
║                                                                         ║
║  ═══ SYMBIOSE MIT I-PIPELINE ═══                                      ║
║                                                                         ║
║  I_orchestrate steuert den aeusseren Stufen-Loop:                      ║
║    Stufe N: Blueprint → [TDD → verify → fanIn → QG] → Stufe N+1      ║
║                                                                         ║
║  TDD_orchestrate steuert den inneren TDD-Zyklus:                      ║
║    Pro Slice: Ring-Planung → [red→exec→green→exec→refactor...→check]  ║
║                                                                         ║
║  Manifest-Uebergabe:                                                   ║
║    I_PIPELINE_STATE.phase = "TDD" (Eingang)                            ║
║    I_PIPELINE_STATE.phase = "POST_TDD" (Ausgang)                       ║
║                                                                         ║
║  Bei slicing=false:                                                    ║
║    Slices sequentiell im gleichen Branch (kein Worktree)               ║
║    TDD laeuft identisch — nur kein fanOut/fanIn                        ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann zeige den aktuellen TDD-Status aus `{WORKING_DIR}/_manifest.md` falls vorhanden  (per-Story, BL-155 AK-1)
(Felder: I_PIPELINE_STATE.phase, current_stage, tdd_pipeline_mode, tdd_alarm).

ARGUMENTS: $ARGUMENTS
