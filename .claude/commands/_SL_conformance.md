---
type: building-block
status: active
version: 1.0.0
created: 2026-05-04
feature: SemantischePatternLibrary
chain_position: standalone (Pre-Merge / Pre-PR Quality-Gate)
related: _SL_init, _Pre_PR_orchestrate
---

# /_SL_conformance — Conformance-Check Branch-Aenderungen vs. SemanticLibrary

**Status:** v1.0.0 (initial)
**Actor:** SEMANTIC-CONFORMANCE-CHECKER (Wellen-Pattern: 7 Sonnet-Drafter parallel + 1 Opus-Synthese)
**Zweck:** Prueft ob die Aenderungen im aktuellen feature-Branch gegen die in `{VAULT_ROOT}/Libraries/SemanticLibrary/` dokumentierten Konventionen verstossen. Diff gegen Vergleichsbasis (default `develop`), Blacklist der Branch-Files, Per-File-Klassifikation (PASS/INFO/WARN/VIOLATION), Master-Synthese mit Merge-Empfehlung (GREEN/YELLOW/RED) und automatischem Anhaengen der Findings als Parking-Lot-Items.

> **Frequenz:** PRO MERGE (vor PR-Erstellung). Standard-Quality-Gate vor `_Pre_PR_orchestrate`.

---

## Aufruf

```
/_SL_conformance [--vs BRANCH] [--scope PFAD] [--no-pl] [--ceiling MODEL]
```

| Parameter   | Pflicht | Default            | Beispiel                        |
|-------------|---------|--------------------|---------------------------------|
| `--vs`      | NEIN    | `develop`          | `--vs main`, `--vs release/v2`  |
| `--scope`   | NEIN    | `Sources/Backend/` | `--scope Sources/Frontend/`     |
| `--no-pl`   | NEIN    | false              | Findings nicht ins Parking-Lot anhaengen (nur Report) |
| `--ceiling` | NEIN    | `opus`             | Synthese-Modell (`sonnet`/`opus`) |

---

## VERTRAG

```
+======================================================================+
| VERTRAG: /_SL_conformance                                            |
+======================================================================+
| LIEST:                                                               |
|   {repo_root}/.claude/config/layers.yaml                            |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md              |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/naming-conventions.md  |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/domain-terms.md        |
|   git diff {vs_branch}...HEAD --name-only            (Blacklist)    |
|   git diff {vs_branch} -- {file}                     (pro Datei)    |
|                                                                      |
| SCHREIBT (Per Layer):                                                |
|   .claude/wissen/sl_conformance_{LAYER}.md           (W1, 7 Files)  |
|                                                                      |
| SCHREIBT (Synthese):                                                 |
|   .claude/wissen/sl_conformance_{FEATURE}_{DATUM}.md (Master-Report) |
|                                                                      |
| SCHREIBT (Parking-Lot, default an):                                  |
|   {VAULT}/.../6_PL/{bl_id}-parking-lot.md                          |
|     -> Sektion "## {DATUM} - Conformance Findings (SemanticLibrary)"|
|     -> CONF-N Items: must-fix vor Merge + Backlog                   |
|                                                                      |
| ACTOR: SEMANTIC-CONFORMANCE-CHECKER                                  |
| MODELL-TIER: sonnet drafter / opus ceiling (Drafter IMMER sonnet,    |
|              Memory-Regel)                                           |
|                                                                      |
| INVARIANTEN:                                                         |
|   INV-CONF-1: SemanticLibrary muss befuellt sein (sonst HiL Fehler) |
|   INV-CONF-2: Wellen-Pattern - 1 Drafter pro Layer parallel        |
|   INV-CONF-3: Drafter IMMER sonnet (Memory)                        |
|   INV-CONF-4: Synthese 1 Opus-Worker NACH allen Drafter-W1         |
|   INV-CONF-5: Default Vergleichsbasis = develop                    |
|   INV-CONF-6: Beabsichtigte Konventions-Erweiterungen NICHT als    |
|               Violation flaggen (Pruefung "konsistent mit Bestand?")|
|   INV-CONF-7: --no-pl unterdrueckt PL-Anhang (Report bleibt)       |
+======================================================================+
```

---

## Chain-Position

```
Branch-Arbeit fertig (commits da, Build/Tests gruen)
     |
     v
[/_SL_conformance]    <- DIESES COMMAND
     |
     +--> .claude/wissen/sl_conformance_*.md (7 Layer-Reports + 1 Master)
     +--> Parking-Lot CONF-N Items (default)
     +--> Merge-Empfehlung GREEN/YELLOW/RED
     |
     v
[Must-fix Items abarbeiten] (falls YELLOW/RED)
     |
     v
[/_Pre_PR_orchestrate] (Pattern-Battle-Test, Build, etc.)
     |
     v
[PR erstellen] (gh pr create - User-Freigabe Pflicht)
```

---

## Layer-Auflistung (BE-Default)

Die 9 Layer aus `.claude/config/layers.yaml`. Falls `_project/{LAYER}/` Dateien fehlen → Layer wird mit "limited reference" markiert, Pruefung baut nur auf `_global/`.

| Layer | path_globs | Anzahl Drafter |
|-------|-----------|----------------|
| BE-DOMAIN | Domain/{BO,Enums,Extensions} | 1 Drafter |
| BE-CORE | Application/Services + Domain/{Services,Providers} + Common/Constants | 1 Drafter |
| BE-CONT | WebApi/Controllers | 1 Drafter |
| BE-DTO | WebApi.DTOs | 1 Drafter |
| BE-MAP | {Application,Data,WebApi}/Mapping | 1 Drafter |
| BE-AUTH | WebApi/Authorization + PeAccessGuard | 1 Drafter (skip falls 0 Files) |
| BE-MID | WebApi/Filters | 1 Drafter (skip falls 0 Files) |
| BE-MIGRATION | Setup.Database/Structure + Setup.TestData/Data + Data.Entities | 1 Drafter |
| BE-TEST | *UnitTests + IntegrationTests | 1 Drafter |

> **Synthese-Welle:** 1 Opus-Worker (oder ceiling-Modell), `blocked_by` alle Drafter.

---

## Ablauf

### Phase 0: Voraussetzungen + Setup

```
1. Voraussetzungen pruefen:
   a. Aktueller Branch != vs_branch (sonst nichts zu pruefen)
   b. SemanticLibrary befuellt ({VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md existiert,
      _project/{LAYER}/naming-conventions.md existiert fuer mind. 1 Layer)
      → NICHT befuellt: STOPP mit Hinweis "Run /_SL_init zuerst"
   c. Git-Status sauber (uncommitted Changes erlaubt — werden mit-geprueft)

2. Blacklist bilden:
   git diff {vs_branch}...HEAD --name-only > /tmp/conf_blacklist_{FEATURE}.txt
   Filter auf {scope} (default Sources/Backend/)
   Frontend/E2E/Cypress raus (Backend-Only Scope)
   csproj/json/yml raus (kein Code)

3. Layer-Zuordnung:
   Pro Datei: erste matchende layers.yaml path_glob -> Layer
   "OTHER" Falls keine Zuordnung -> in BE-CORE-Drafter mit-prufen ODER skippen

4. Team erstellen:
   TeamCreate name="sl-conformance-{FEATURE}"
   Tasks: 1 pro Layer mit >=1 File (max 9 W1) + 1 W2-Synthese
   W2 blocked_by alle W1
```

### Phase 1: WELLE 1 — Drafter-Worker (Sonnet) PARALLEL

**Pro Layer 1 Sonnet-Worker.** Alle parallel via `run_in_background: true`.

Worker-Prompt-Vorlage:
```
[WORKER-MODE] Welle 1 {LAYER} Conformance-Check (Sonnet)

REPO: {repo_root}
Branch: {current_branch}. Vergleichsbasis: {vs_branch}.

DEINE {N} DATEIEN:
{file_list}

SEMANTIK-REGELN — LIES ZUERST:
1. {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md (KOMPLETT)
2. {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/naming-conventions.md
3. {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/domain-terms.md

PRO DATEI:
1. git diff {vs_branch} -- <file>
2. Read aktueller Stand (Working-Tree)
3. Pruefe gegen Regeln aus SemanticLibrary
4. Klassifiziere: PASS / INFO / WARN / VIOLATION
5. Bei Findings: Datei:Zeile + zitiere Regel + 1-2 Saetze Begruendung

NUANCE — beabsichtigte neue Konventionen:
- Wenn Branch ABSICHTLICH neue Konvention einfuehrt: NICHT als Violation
- Pruefe stattdessen: Konsistent mit Bestand?
- Subversive Brueche (z.B. ploetzlich englisches Naming wo Layer deutsch ist) WERDEN geflaggt

OUTPUT: .claude/wissen/sl_conformance_{LAYER}.md (Format: frontmatter + per-file Sections)

ABSCHLUSS:
1. TaskUpdate Task-ID auf status=completed
2. SendMessage team-lead 1-Satz-Bilanz: "{LAYER}: N Files | x PASS, y INFO, z WARN, w VIOLATION"
```

### Phase 2: Synthese-WELLE — Opus

NACH allen W1 Drafter completed:

```
[WORKER-MODE] Welle 2 Synthese (Opus)

LIES alle Layer-Reports:
.claude/wissen/sl_conformance_BE-*.md

SCHREIBE Master-Report:
.claude/wissen/sl_conformance_{FEATURE}_{DATUM}.md

INHALT:
- Executive Summary (Bilanz + Merge-Empfehlung GREEN/YELLOW/RED + 1 Satz)
- KRITISCH (must-fix vor Merge): Sammle alle WARN die echte Bugs sind, mit Datei:Zeile + Fix
- WARN (sollte nachgezogen werden, nicht-blockierend)
- INFO Beabsichtigte Konventions-Erweiterungen (NICHT-Violation)
- INFO Stilistische Beobachtungen (Cleanup-Kandidaten)
- Cross-Layer-Beobachtungen (Patterns die in mehreren Layern auftreten)
- Empfohlener Fix-Plan (Vor Merge / Nach Merge / Backlog)
- Methodik

ABSCHLUSS:
1. TaskUpdate Synthese-Task auf completed
2. SendMessage team-lead: Pfad + Empfehlung + Top-3 Must-Fix + Bilanz
```

### Phase 3: Parking-Lot Anhang (default an, --no-pl unterdruecken)

Team Lead (DU) NACH Synthese-Empfang:

```
1. Falls --no-pl gesetzt: SKIP, RETURN.
2. Lies Synthese-Master-Report.
3. Pro KRITISCH/WARN-Finding: Erstelle PL-Item-Block:
   - [ ] **CONF-N - {KAT}: {Kurzfassung}** (Conformance {DATUM})
     - Prioritaet: {KRITISCH/NORMAL/NIEDRIG}
     - Komplexitaet: {TRIVIAL/LOW/MITTEL/HOCH}
     - Datei: `{path}:{line}`
     - **Befund:** {Zusammenfassung}
     - **Fix:** {Vorschlag}
4. Schreibe Sektion "## {DATUM} - Conformance Findings (SemanticLibrary v{VERSION})"
   ueber "## Abgeschlossen" in {VAULT}/.../6_PL/{bl_id}-parking-lot.md.
5. Inkludiere Bilanz-Header + Quelle (Pfad zum Master-Report).
```

---

## Output-Struktur

```
.claude/wissen/
  sl_conformance_BE-DOMAIN.md         <- Drafter Output
  sl_conformance_BE-CORE.md
  sl_conformance_BE-CONT.md
  sl_conformance_BE-DTO.md
  sl_conformance_BE-MAP.md
  sl_conformance_BE-MIGRATION.md
  sl_conformance_BE-TEST.md
  sl_conformance_{FEATURE}_{DATUM}.md  <- Synthese Master-Report

{VAULT}/.../6_PL/{bl_id}-parking-lot.md
  ## {DATUM} - Conformance Findings (SemanticLibrary)
    > Quelle: {Pfad zum Master-Report}. Bilanz: ... PASS / ... WARN / ... INFO. Merge-Empfehlung: {GREEN|YELLOW|RED}.
    ### Must-fix vor Merge
    - [ ] CONF-1 - KRITISCH: ...
    - [ ] CONF-2 - WARN: ...
    ### Nach Merge / Backlog
    - [ ] CONF-N - INFO: ...
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| Diff vs vs_branch leer | STOPP "Branch hat keine Aenderungen vs {vs}" |
| SemanticLibrary leer | STOPP "Run /_SL_init zuerst" |
| Layer ohne Files in Diff | Layer-Worker SKIP (kein Spawn) |
| Layer ohne SemanticLibrary-Dateien | Worker prueft nur gegen `_global/`, markiert "limited reference" |
| Worker-Fehler / Timeout | TaskUpdate auf failed, Synthese ueberspringt diesen Layer mit Hinweis |
| Synthese-Fehler | Layer-Reports bleiben, Manifest-Vermerk "SYNTHESE_OFFEN" |
| Parking-Lot fehlt | --no-pl-Verhalten + WARN |

---

## Abgrenzung

```
/_SL_init        = SemanticLibrary EINMALIG befuellen (Bootstrap, Code-Scan)
/_SL_conformance = Branch GEGEN Bibliothek pruefen (laufendes Quality-Gate)  <- DIESE
/_PT_extract     = Einzelnes Pattern aus Code extrahieren
/_PT_update      = Pattern manuell registrieren/upgraden
/_Pre_PR_orchestrate = Pre-Merge-Battle-Test (Pattern-Promotion, Build, Tests)

Reihenfolge:
  Branch-Arbeit -> /_SL_conformance -> Fix Must-Fixes -> /_Pre_PR_orchestrate -> PR
```

---

## Memory-Regeln (DCSRE)

- Drafter IMMER sonnet (auch wenn ceiling=sonnet) — Memory feedback_a_pipeline_order
- Backend-Only Scope (default Sources/Backend/) — Memory feedback_backend_only_scope
- HiL=off Standard fuer DCSRE — autonom durchlaufen ohne Rueckfragen
- Niemals PR/git push autonom — Memory PR VERBOTEN
- Status-Display: Modelle + 1-Satz-Zustand bei Welle-Spawn

---

## Beispiel-Lauf (DCSRE-94, 2026-05-04)

```
/_SL_conformance --vs develop

→ Blacklist: 63 BE-Files
→ Team: sl-conformance-94
→ W1: 7 Sonnet-Drafter parallel (BE-DOMAIN/CORE/CONT/DTO/MAP/MIGRATION/TEST)
→ W2: 1 Opus-Synthese (blocked_by W1)
→ Bilanz: 54 PASS / 5 WARN / 21 INFO / 0 VIOLATION
→ Merge-Empfehlung: YELLOW (1 funktional kaputter Round-Trip)
→ PL-Anhang: 9 CONF-Items (3 must-fix + 6 backlog)
```
