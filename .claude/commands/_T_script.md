---
name: _T_script
description: Fuehrt NUR die Tests EINER Stage aus (stage1..stage6) — optional gefiltert auf die testSearch-relevanten Tests (der Mix)
type: satellite
---

# /_T_script — gezielter Stage-Test-Runner (der Mix)

**Zweck:** Eine einfache Moeglichkeit, **wirklich nur** die Tests einer bestimmten Stage
auszufuehren — und zwar **nur die, die fuer die aktuelle Arbeit relevant sind**. Nicht die
ganze Suite. Gedacht zum „nebenbei laufen lassen" (eigene kleine Skripte).

**Der Mix (2 Quellen):**
1. **Stage-`testbefehl`-Template** (`.claude/meta/implementation/stage_{N}.md`) — das *WIE*
   (Unit=1, Integration=3, E2E=6). Traegt einen Platzhalter `<FQN>`/`<TestName>` (.NET) bzw.
   `<SPEC>` (Cypress/FE).
2. **testSearch-relevante Tests** — das *WELCHE* (= `coverage_map.covering_tests` aus dem
   I_orchestrate/IDF-testSearch, IDF Phase 7.7). Werden ins Template substituiert → **genau
   diese** Tests laufen.

## Aufruf

```
/_T_script <stage> [<stage>...] [--tests=A,B] [--tests-file=F] [--setup] [--teardown] [--dry-run]
```
Der Lead fuehrt dazu aus (im jeweiligen Projekt-Worktree, wo `stage_{N}.md` projekt-korrekt ist):
```
py .claude/scripts/t_script.py <stage> [flags]
```

| Arg/Flag | Wirkung |
|---|---|
| `<stage>` | `1`..`6` oder `stage1`..`stage6` (mehrere moeglich) |
| `--tests=A,B` | relevante Test-Namen/FQN/Spec — substituiert in den `<...>`-Platzhalter (= nur diese) |
| `--tests-file=F` | dieselben, 1 pro Zeile (`#`=Kommentar) — dorthin schreibt der testSearch die covering_tests |
| `--setup` / `--teardown` | Infra hoch/runter (Docker/Healthchecks aus `stage_{N}.md.setup/teardown`) — default AUS |
| `--dry-run` | nur den Plan zeigen, nichts ausfuehren |
| `--meta-dir=DIR` | abweichendes Stage-Meta-Verzeichnis (default `.claude/meta/implementation`) |

## Beispiele

```
py .claude/scripts/t_script.py 3                              # ganze stage-3 Integration-Suite
py .claude/scripts/t_script.py 3 --tests=QdvtpBearbeitenTest  # NUR dieser relevante Integration-Test (Mix)
py .claude/scripts/t_script.py 6 --tests-file=relevant.txt --setup --teardown   # FE-E2E: nur relevante Specs + Infra
py .claude/scripts/t_script.py 1 3 --dry-run                  # Plan fuer Unit + Integration
```

## Hinweise

- **Projekt-Config:** der `testbefehl` je Stage lebt in `stage_{N}.md` (projekt-typ-spezifisch).
  FE-Projekt → stage-6-`testbefehl` = scoped Cypress-Lauf (Platzhalter `<SPEC>`); BE → `dotnet test
  --filter "FullyQualifiedName~<TestName>"`. `t_script.py` ist projekt-agnostisch: es faehrt, was
  dort steht. Hat der `testbefehl` keinen Platzhalter, aber `--tests` ist gesetzt → WARN + ganzer
  Stage-Lauf (nicht substituierbar).
- **Nur-Tests by default:** ohne `--setup/--teardown` laeuft **ausschliesslich** der `testbefehl`
  (kein Docker-Spinup) — fuer den Fall, dass die Umgebung schon laeuft (z.B. lokaler Branch :5443).
- **Encoding-robust:** liest `stage_{N}.md` mit `errors="replace"` (BL-278), schneidet Reminder-
  `#`-Kommentare im `testbefehl` ab (BL-275/-243-Lauf).
- **Stage-Resolution via `resolve_vault_stage` (BL-392 AK-CONSUMER-REWRITE):** `t_script.py` liest
  die Stage NICHT mehr per Direkt-`open(stage_N.md)`, sondern ueber den kanonischen
  `resolve_vault_stage`-Resolver (Dual-Read). Ist die Stage in den Vault migriert
  (`{VAULT}/Stage/stage_N_<name>/`), kommt der `testbefehl` aus dem `execute`-Slice und
  `--setup`/`--teardown` aus den `setup`/`teardown`-Slices (je 1 Concern-Slice, single unit of
  work). Ist sie NICHT migriert, faellt der Resolver auf den Legacy-Monolith im `--meta-dir`
  zurueck und `t_script` liest dessen Rohtext mit dem bisherigen Parser — **byte-identisch zum
  heutigen Verhalten** (inkl. In-Quote-`#`-Abschnitt). `--meta-dir` zeigt damit weiter auf das
  Legacy-Verzeichnis (default `.claude/meta/implementation`).
- Implementierung + Tests: `.claude/scripts/t_script.py` (Unit-Tests inkl. BL-392-Resolver-Routing, TDD).

ARGUMENTS: $ARGUMENTS
