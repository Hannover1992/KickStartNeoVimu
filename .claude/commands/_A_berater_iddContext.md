---
status: active
version: 0.2.0
type: berater
parent: _A_orchestrate
phase: phase_2
model_tier: middle
created: 2026-04-25
updated: 2026-05-06
feature_anchor: BL-142
optional: true
changelog_0_2_0: |
  v0.2.0 (2026-05-06): Skelett -> produktiv.
    - git diff main...{parent_pr} parsen + per-File-Hunks aggregieren.
    - Markdown-Doc mit Frontmatter unter .claude/merge-instructions/.
    - Skip wenn parent_pr nicht reachable.
contract:
  reads:
    - {file: "git", path: "diff main...{parent_pr}", purpose: "PR-Aenderungen sammeln"}
    - {file: "git", path: "show {parent_pr_sha}", purpose: "Commit-Metadaten"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.derived_name", purpose: "Feature-Anker"}
    - {file: "_session_params.md", path: "PARENT_PR / GLOBAL_*", purpose: "PR-Referenz / HiL"}
  writes:
    - {file: ".claude/merge-instructions/{NAME}-idd-context.md", path: "Volltext (kondensierter PR-Diff)", purpose: "Inheritance-Doc fuer downstream"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.iddContext", purpose: "Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser iddContext)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.routing_target"}
  calls: []
---

# _A_berater_iddContext (Phase 2 in _A_orchestrate)

> **Zweck:** Inheritance-Document erzeugen aus parent-PR-Diff — NUR aktiv bei `--parent-pr`.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_iddContext                                      |
+======================================================================+
|  LIEST:                                                              |
|    git diff main...{parent_pr}                                       |
|    git show {parent_pr_sha}                                          |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      A_PIPELINE_STATE.derived_name                                   |
|    _session_params.md                                                |
|      PARENT_PR (Branch oder SHA)                                     |
|                                                                      |
|  SCHREIBT:                                                           |
|    .claude/merge-instructions/{NAME}-idd-context.md                  |
|      Frontmatter: feature, parent_pr, generated_at                   |
|      Body: kondensierter Diff (Files, Hunks, Begruendungen)         |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.iddContext = {                                  |
|        files_touched, hunks_total, parent_pr_sha                     |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser iddContext)                             |
|    A_PIPELINE_STATE.routing_target                                   |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 2 (NUR bei --parent-pr)                 |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Diff-Aggregation + Pfad-Listung + Hunk-Zaehlung,    |
|    keine Reasoning-Tiefe noetig.                                    |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-IDD-1: Output-Pfad fest .claude/merge-instructions/           |
|    INV-IDD-2: parent_pr_sha vollstaendig (kein gekuerzter SHA)       |
|    INV-IDD-3: Schreib-Isolation auf BERATER_OUTPUTS.iddContext       |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - PARENT_PR gesetzt (sonst Phase uebersprungen)                   |
|    - git ist verfuegbar, parent_pr Branch reachable                  |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - {NAME}-idd-context.md existiert                                 |
|    - BERATER_OUTPUTS.iddContext vollstaendig                         |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_iddContext, args="{NAME}")

Parameter:
  {NAME} - Feature-Name

Ausgabe:
  - .claude/merge-instructions/{NAME}-idd-context.md
  - BERATER_OUTPUTS.iddContext
  - Exitcode: 0=OK, 2=FAIL (PR nicht reachable / leer)

Logging-Format:
  [A_IDD] ENTRY parent_pr={ref}
  [A_IDD] EXIT duration={ms}ms files={n} hunks={k}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  iddContext:
    files_touched: 12
    hunks_total: 47
    parent_pr_sha: "abc1234..."
    last_berater: "iddContext"
```

## Logik (v0.2.0 produktiv)

```
SCHRITT 0: Entry + Vorbedingung
  NAME = args[0]
  Logge: "[A_IDD] ENTRY name={NAME}"

  # Parent-PR aus Session-Params
  session = Read("{VAULT}/_session_params.md") fallback Read(".claude/config/_session_params.md")
  parent_pr = session.PARENT_PR ?? args.get("parent_pr") ?? null

  IF parent_pr == null:
    Logge: "[A_IDD] SKIP — kein parent_pr konfiguriert (optional Phase)"
    EXIT 0

SCHRITT 1: parent_pr-Reachability + SHA aufloesen
  parent_pr_sha = bash("git rev-parse {parent_pr}").stdout.strip()
  IF parent_pr_sha == "" OR len(parent_pr_sha) < 40:
    Logge: "[A_IDD] FAIL — parent_pr={parent_pr} nicht reachable"
    EXIT 2

SCHRITT 2: Diff erzeugen (main...parent_pr)
  diff_output = bash("git diff main...{parent_pr_sha} --name-only").stdout
  files_touched = parse_lines(diff_output)
  IF |files_touched| == 0:
    Logge: "[A_IDD] FAIL — Diff leer (parent_pr identisch zu main?)"
    EXIT 2

  # Per-File Hunks aggregieren
  hunks_total = 0
  per_file_summary = {}
  FOR file IN files_touched:
    file_diff = bash("git diff main...{parent_pr_sha} -- {file}").stdout
    hunks = count_pattern(file_diff, r"^@@ ")
    hunks_total += hunks
    per_file_summary[file] = {
      hunks: hunks,
      lines_added: count_pattern(file_diff, r"^\+[^+]"),
      lines_removed: count_pattern(file_diff, r"^-[^-]")
    }

SCHRITT 3: Commit-Metadaten
  parent_pr_msg = bash("git show -s --format=%s {parent_pr_sha}").stdout.strip()
  parent_pr_author = bash("git show -s --format=%an {parent_pr_sha}").stdout.strip()
  parent_pr_date = bash("git show -s --format=%ai {parent_pr_sha}").stdout.strip()

SCHRITT 4: Inheritance-Doc schreiben (INV-IDD-1 fester Pfad)
  out_dir = ".claude/merge-instructions"
  bash("mkdir -p {out_dir}")
  out_path = "{out_dir}/{NAME}-idd-context.md"

  fm_yaml = render_yaml({
    type: "idd_context",
    feature: NAME,
    parent_pr: parent_pr,
    parent_pr_sha: parent_pr_sha,
    parent_pr_author: parent_pr_author,
    parent_pr_date: parent_pr_date,
    generated_at: ISO_NOW(),
    files_touched: |files_touched|,
    hunks_total: hunks_total
  })

  body = "# IDD-Context fuer {NAME}\n\n## Parent-PR\n{parent_pr_msg}\n\n## Geaenderte Dateien\n\n"
  FOR file, summary IN per_file_summary:
    body += "### {file}\n- Hunks: {summary.hunks}\n- Lines: +{summary.lines_added}/-{summary.lines_removed}\n\n"

  Write(out_path, "---\n{fm_yaml}\n---\n\n" + body)

SCHRITT 5: Output (INV-IDD-3 Schreib-Isolation)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.iddContext = {
    files_touched: |files_touched|,
    hunks_total: hunks_total,
    parent_pr_sha: parent_pr_sha,
    out_path: out_path,
    last_berater: "iddContext"
  })

SCHRITT 6: Exit
  Logge: "[A_IDD] EXIT files={|files_touched|} hunks={hunks_total}"
  EXIT 0
```

## Begruendung Modell-Tier

sonnet — Diff-Aggregation, Hunk-Zaehlung, Pfad-Listing. Kein Reasoning, das opus rechtfertigen wuerde.
