---
type: berater
feature: SemantischePatternLibrary
bl_item: BL-153
ak_ref: "AK-A-3, AK-E-3, AK-E-6"
chain_position: "nach _T_orchestrate-Run-1, vor _stage_orchestrate"
status: active
version: 1.0.0
created: 2026-04-30
---

# _PostBatch_PatternConformance (M-4)

**Zweck:** Ausfuehrliche Pattern-Konformanz-Pruefung auf Batch-Ebene — vollstaendiger
unstaged Diff aller im Batch angefassten Dateien. Scope: gesamter Batch (nicht nur letzter Slice).
Laeuft VOR `_stage_orchestrate` (Reihenfolge-Invariante AK-A-3).

**Scope-Modi:**
- `--scope unstaged`: Vollstaendiger unstaged Diff (Batch-Ebene, Standard)
- `--scope slice --slice {SLICE_NAME}`: Nur Slice-Dateien (Quick Gate fuer _TDD_orchestrate AK-A-2)

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _PostBatch_PatternConformance (M-4, AK-A-3, AK-E-3, AK-E-6)║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {WORKING_DIR}/_manifest.md → DF_BATCH_STATE.batch_current        ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_index.md                  ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_generic/*.md              ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_project/{LAYER}/*.md      ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_index.md (ARCH-10)       ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_global/*.md (IMMER)      ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/*.md     ║
║    VAULT_ROOT via: resolve_vault_root.py (ARCH-N8, Single Source)   ║
║    _session_params.md → GLOBAL_HIL                                  ║
║    Git unstaged diff (--scope unstaged) ODER Slice-Dateien         ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {WORKING_DIR}/_manifest.md:                                      ║
║      PATTERN_CONFORMANCE_STATE.blocker_count: {N}                   ║
║      PATTERN_CONFORMANCE_STATE.warn_count: {N}                      ║
║      PATTERN_CONFORMANCE_STATE.info_count: {N}                      ║
║      PATTERN_CONFORMANCE_STATE.tests_dirty: true|false              ║
║      PATTERN_CONFORMANCE_STATE.apply_happened: true|false           ║
║      PATTERN_CONFORMANCE_STATE.hil_mode: off|on                     ║
║      PATTERN_CONFORMANCE_STATE.scope: unstaged|slice                ║
║      PATTERN_CONFORMANCE_STATE.escalation_queued: true|false        ║
║      ARCHITECT_ESCALATION_QUEUE: [{finding_id, datei, pattern_id,   ║
║        severity, beschreibung, suggested_berater, queued_at}]       ║
║                                                                      ║
║  SCHREIBT (POST-B, BL-237 AK-CTX-R2 + AK-3 — ADDITIV, separat):     ║
║    {VAULT}/.claude/wissen/pattern-usage.log (APPEND, R2):           ║
║      Pro Conformance-PASS-mit-Match EIN CONFORMANCE_PASS-Signal     ║
║      (Signal-Pfad, ADR-PL-008). NUR bei hartem Relevanz-Gate:       ║
║      applies_to-Match UND Kern-Symbol im Diff. "kein finding"       ║
║      -> NIE usage++ (Asymmetrie-Schutz C-6, K-4).                   ║
║    POST-B-Orchestrierung (AK-3): (a) add_arch Golden-Capture,       ║
║      (b) drain_usage_log 1x (R6b, idempotent), (c) Revert->R4.      ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    DF_BATCH_STATE.* (read-only)                                     ║
║    stage_gate_status (nur _stage_orchestrate schreibt das)          ║
║    PATTERN_CONFORMANCE_STATE / ARCHITECT_ESCALATION_QUEUE bleiben   ║
║      BIT-STABIL — POST-B aendert die POST-A-SCHREIBT-Sektion NICHT  ║
║      (AK-3 additiv, F10, K-3-Canary).                               ║
║                                                                      ║
║  MODELL-TIER: floor (haiku) — Pattern-Index-Lookup + Diff-Analyse   ║
║    (POST-B-Golden-Capture-Worthiness: bei Tier-Konflikt Split nach  ║
║     _PostBatch_PatternLearning.md, W-2/§8 — KEIN POST-A-Override)   ║
║  INVARIANTEN:                                                        ║
║    INV-A3-1: Laeuft IMMER VOR _stage_orchestrate (Reihenfolge)      ║
║    INV-E3-1: HiL binaer — NUR off (Auto-Apply) ODER on (Report+Frage)║
║    INV-E6-1: tests_dirty=true NUR wenn Apply-Lauf stattfand         ║
║    INV-E6-2: Nur WARN/INFO → tests_dirty=false (kein zweiter T-Run) ║
║    INV-B2-1: NON-BLOCKING bei leerer PatternLibrary (Graceful Skip) ║
║    INV-A7-1: Nicht-auto-fixbare BLOCKER → ARCHITECT_ESCALATION_QUEUE║
║      (ARCH-7, BL-153) — kein Hard-Stop, Architekten-Analyse statt  ║
║      Pipeline-Abbruch (Aufrufer entscheidet via escalation_queued)  ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
Skill(_PostBatch_PatternConformance, args="--scope {unstaged|slice} --batch {ID} [--slice {SLICE_NAME}]")
```

Wird von `_PostBatch_orchestrate` (SCHRITT 1.5) und `_TDD_orchestrate` (Quick Gate AK-A-2) aufgerufen.

---

## HiL-Semantik (AK-E-3)

**Genau 2 Modi — kein whenBlocker-Modus:**

| HiL | BLOCKER (auto-fixable) | BLOCKER (nicht auto-fixable) | WARN | INFO |
|-----|------------------------|------------------------------|------|------|
| `off` (Default) | Auto-Apply | Eskalation-Queue (ARCH-7) | PL-Park | Ignoriert |
| `on` | Report + `/_question "Apply / Park / Skip?"` | Report + `/_question` | Report + `/_question` | Report |

- **Auto-Apply (HiL=off):** Berater korrigiert die Verletzung direkt (wenn automatisch korrigierbar).
  Bei nicht-auto-korigierbarem BLOCKER → `ARCHITECT_ESCALATION_QUEUE` befuellen → Aufrufer ruft `_I_cleanCodeArchitect --mode impact-check` (ARCH-7, kein Hard-Stop).
- **Report + Frage (HiL=on):** Pro Finding-Gruppe: AskUserQuestion mit 3 Optionen (Apply/Park/Skip).
- **Kein `whenBlocker`-Modus:** Ein Modus der nur bei BLOCKERn fragt existiert NICHT (AK-E-3 explizit ausgeschlossen).

---

## Ablauf

### Schritt 0: PatternLibrary verfuegbar? (INV-B2-1)

```
# ARCH-N9: VAULT_ROOT via resolve_vault_root.py (Single Source of Truth)
IF {VAULT_ROOT}/Libraries/PatternLibrary/_index.md NICHT vorhanden OR leer (EMPTY_SEED):
  Logge: "[PatternConformance] PatternLibrary leer — NON-BLOCKING Skip"
  Schreibe PATTERN_CONFORMANCE_STATE:
    blocker_count: 0
    warn_count: 0
    tests_dirty: false
    apply_happened: false
    scope: {scope}
    note: "PatternLibrary leer (EMPTY_SEED) — Conformance-Check uebersprungen"
  → RETURN (kein Fehler)
```

### Schritt 1: Diff laden

```
IF scope == "unstaged":
  # Vollstaendiger unstaged Diff (alle Batch-Dateien)
  dateien = git_unstaged_files()
  Logge: "[PatternConformance] Scope=unstaged: {|dateien|} Dateien im Batch-Diff"

ELIF scope == "slice":
  # Slice-Ebene (nur Slice-Dateien, AK-A-2 Quick Gate)
  dateien = slice_files(SLICE_NAME)
  Logge: "[PatternConformance] Scope=slice/{SLICE_NAME}: {|dateien|} Dateien"
```

### Schritt 2: Pattern + Semantic Lookup + Matching (ARCH-10)

```
# Alle vier Libraries laden (BL-237 batch_C4 F8: 4 rule_source — pattern|semantic|domain|factoring)
patterns = lies {VAULT_ROOT}/Libraries/PatternLibrary/_generic/*.md +
           {VAULT_ROOT}/Libraries/PatternLibrary/_project/{LAYER}/*.md
semantics = lies {VAULT_ROOT}/Libraries/SemanticLibrary/_global/*.md +
            {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/*.md
# BL-237 batch_C4 F8 (4-rule_source): DomainLibrary + FactoringLibrary (greenfield-tolerant —
# fehlender Ordner -> leere Liste, KEIN Abbruch; F5 greenfield, AK-7 legt sie an).
domains = lies {VAULT_ROOT}/Libraries/DomainLibrary/_generic/*.md +
          {VAULT_ROOT}/Libraries/DomainLibrary/_project/{LAYER}/*.md   # leer falls greenfield
factorings = lies {VAULT_ROOT}/Libraries/FactoringLibrary/_generic/*.md +
             {VAULT_ROOT}/Libraries/FactoringLibrary/_project/{LAYER}/*.md  # leer falls greenfield
filter: status != DEPRECATED, severity IN [BLOCKER, WARN, INFO]

# BL-237 batch_C4 F8/F9 (Anti-Overclaim, K-4): Domain-/Factoring-Regeln sind fachliche/Business-
# Invarianten — oft NICHT statisch grep-bar. Default-Severity = INFO (NICHT BLOCKER), damit eine
# nicht-statisch-verifizierbare fachliche Regel die Stage NICHT faelschlich stoppt. INFO ist via
# der vorhandenen Klasse (:154 Filter / :199 INFO->ignoriert / INV-E6-2) bereits non-blocking —
# KEINE neue Mechanik. Eine Domain-/Factoring-Regel MUSS severity:INFO sein, wenn nicht explizit
# ein statisch verifizierbarer Anker (anti_pattern-Regex) eine hoehere severity rechtfertigt.
domain_default_severity   = "INFO"   # Anti-Overclaim (F9/K-4)
factoring_default_severity = "INFO"  # Anti-Overclaim (F9/K-4)

# Vereinte Knoten-Liste — 4 rule_source (jedes Element behaelt source: "pattern"|"semantic"|"domain"|"factoring")
all_rules = [{...p, source: "pattern"}   for p in patterns] +
            [{...s, source: "semantic"}  for s in semantics] +
            [{...d, source: "domain",    severity: (d.severity ?? domain_default_severity)}    for d in domains] +
            [{...f, source: "factoring", severity: (f.severity ?? factoring_default_severity)} for f in factorings]

findings = []
FÜR jede datei in dateien:
  FÜR jedes rule in all_rules:
    IF datei-Inhalt verletzt rule.boundary_rules ODER
       datei-Inhalt enthaelt rule.anti_pattern:
      findings.append({
        datei: datei,
        rule_id: rule.id,
        rule_source: rule.source,         # "pattern" | "semantic" | "domain" | "factoring" (ARCH-10, BL-237 F8)
        severity: rule.severity,          # domain/factoring default INFO (F9/K-4 Anti-Overclaim)
        beschreibung: "{violation_text}",
        auto_fixable: (rule.frontmatter.auto_fixable ?? false),
        auto_fixable_class: (rule.frontmatter.auto_fixable_class ?? "risky")  # ARCH-22: trivial|risky|architect_required
      })
```

### Schritt 3: HiL-Entscheidung + Apply (AK-E-3)

```
hil_mode = lies _session_params.md → GLOBAL_HIL ?? "off"
blocker_findings = [f for f in findings IF f.severity == "BLOCKER"]
warn_findings    = [f for f in findings IF f.severity == "WARN"]
apply_happened   = false

IF hil_mode == "off":
  # Auto-Apply basierend auf auto_fixable_class (ARCH-22, BL-153)
  FÜR jedes finding in blocker_findings:
    IF finding.auto_fixable AND finding.auto_fixable_class == "trivial":
      wende_fix_an(finding)
      apply_happened = true
      Logge: "[PatternConformance] Auto-Apply BLOCKER (trivial): {finding.pattern_id} in {finding.datei}"
    ELIF finding.auto_fixable AND finding.auto_fixable_class == "risky":
      Schreibe PL-Item: "[PatternConformance] RISKY-BLOCKER {finding.pattern_id}: {finding.beschreibung}"
      Logge: "[PatternConformance] Risky-BLOCKER → PL-Item (kein Auto-Apply): {finding.pattern_id}"
    ELSE:
      Logge: "[PatternConformance] BLOCKER nicht auto-fixbar (class={finding.auto_fixable_class}): {finding.pattern_id}"
  # WARN → PL-Item parken (unabhaengig von auto_fixable_class)
  FÜR jedes finding in warn_findings:
    Schreibe PL-Item: "[PatternConformance] WARN {finding.pattern_id}: {finding.beschreibung}"
  # INFO → ignoriert (non-blocking). BL-237 F8/F9/K-4: Domain-/Factoring-Regeln laufen
  #   per Default hier durch (severity:INFO) → Anti-Overclaim: eine fachliche/Business-Invariante,
  #   die nicht statisch grep-bar ist, stoppt die Stage NIE faelschlich (kein BLOCKER).

ELIF hil_mode == "on":
  FÜR jede finding-Gruppe (gruppiert nach severity):
    AskUserQuestion:
      "PatternConformance {finding.severity}: {finding.pattern_id} in {finding.datei}
       {finding.beschreibung}
       [Apply] Auto-korrigieren
       [Park]  Als PL-Item parken
       [Skip]  Ueberspringen (Evidenz-Pflicht)"
    IF user_choice == "Apply":
      wende_fix_an(finding)
      apply_happened = true
    ELIF user_choice == "Park":
      Schreibe PL-Item: "[PatternConformance] {finding.severity} parkiert: {finding.beschreibung}"
```

### Schritt 3.5: Architekten-Eskalation (ARCH-7, BL-153, INV-A7-1)

```
# Alle nicht-auto-fixbaren BLOCKER (HiL=off) → ARCHITECT_ESCALATION_QUEUE
verbleibende_nicht_fixierbar = [f for f in blocker_findings IF NOT f.auto_fixable AND hil_mode == "off"]

IF |verbleibende_nicht_fixierbar| > 0:
  FÜR jedes finding in verbleibende_nicht_fixierbar:
    ARCHITECT_ESCALATION_QUEUE.append({
      finding_id: "{finding.pattern_id}@{finding.datei}",
      datei: finding.datei,
      pattern_id: finding.pattern_id,
      rule_source: finding.rule_source,              # ARCH-29: PFLICHT — "pattern" | "semantic" | "domain" | "factoring" (BL-237 F8 4-rule_source)
      severity: finding.severity,
      beschreibung: finding.beschreibung,
      suggested_berater: "_I_cleanCodeArchitect --mode impact-check",
      queued_at: {ISO8601},
      auto_fixable_class: finding.auto_fixable_class  # PL-20: PFLICHT (BL-154 AK-6-2)
    })
  escalation_queued = true
  Logge: "[PatternConformance] ARCHITECT_ESCALATION_QUEUE: {|verbleibende_nicht_fixierbar|} Findings eskaliert — kein Hard-Stop (ARCH-7)"

  # PL-21: needs_human Verdict → [NEEDS_HUMAN]-präfixierter PL-Item (BL-154 AK-6-3)
  FÜR jedes finding in verbleibende_nicht_fixierbar:
    IF finding.auto_fixable_class == "architect_required":
      Schreibe PL-Item: "[NEEDS_HUMAN] PatternConformance BLOCKER {finding.pattern_id} in {finding.datei}: {finding.beschreibung} — architect_required, kein Auto-Fix moeglich"
      Logge: "[PatternConformance] [NEEDS_HUMAN] PL-Item fuer architect_required-Finding: {finding.pattern_id}"
ELSE:
  escalation_queued = false
  Logge: "[PatternConformance] Kein Eskalations-Bedarf (escalation_queued=false)"
```

### Schritt 4: tests_dirty Flag setzen (AK-E-6, INV-E6-1/E6-2)

```
# INV-E6-1: tests_dirty=true NUR wenn Apply-Lauf stattfand
# INV-E6-2: Nur WARN/INFO (kein Apply) → tests_dirty=false
tests_dirty = apply_happened  # Bool: true iff Apply-Lauf

Logge: "[PatternConformance] apply_happened={apply_happened} → tests_dirty={tests_dirty}"
```

### Schritt 5: Output schreiben

```
# Verbleibende nicht-fixierte BLOCKER zaehlen
verbleibende_blocker = [f for f in blocker_findings IF NOT f.auto_fixable AND hil_mode == "off"]
blocker_count = |verbleibende_blocker|

Schreibe {WORKING_DIR}/_manifest.md PATTERN_CONFORMANCE_STATE:
  blocker_count: {blocker_count}
  warn_count: {|warn_findings| - parkierte}
  info_count: {|findings| - blocker - warn}
  tests_dirty: {tests_dirty}
  apply_happened: {apply_happened}
  hil_mode: {hil_mode}
  scope: {scope}
  findings_total: {|findings|}
  batch_id: {batch_current}
  escalation_queued: {escalation_queued}

Schreibe {WORKING_DIR}/_manifest.md ARCHITECT_ESCALATION_QUEUE = ARCHITECT_ESCALATION_QUEUE  # leer wenn escalation_queued=false

Logge: "[PatternConformance] DONE — BLOCKER={blocker_count} WARN={warn_count} tests_dirty={tests_dirty} escalation_queued={escalation_queued}"
```

---

## Schritt 6: POST-B Reifungs-Feed (BL-237 AK-CTX-R2 + AK-3 — ADDITIV, POST-A bit-stabil)

> **ADDITIV (F10, K-3):** Diese Sektion laeuft NACH Schritt 5 und beruehrt die POST-A-SCHREIBT-Sektion
> (`PATTERN_CONFORMANCE_STATE` + `ARCHITECT_ESCALATION_QUEUE`) NICHT. Sie schreibt ausschliesslich in
> `pattern-usage.log` (Signal-Pfad, ADR-PL-008) bzw. ruft die autorisierten Script-Funktionen.

### Schritt 6a: R2 Conformance-PASS → usage++-Signal (Relevanz-Gate + Asymmetrie-Schutz C-6)

```
# R2 (AK-CTX-R2, K-4): EIN CONFORMANCE_PASS-Signal NUR bei HARTEM Relevanz-Gate.
# ASYMMETRIE-SCHUTZ (C-6, K-4): "kein finding" ist NIE ein usage++-Signal.
#   Nur ein AKTIVER PASS-mit-Match darf appenden — die blosse Abwesenheit einer Verletzung NICHT.

FÜR jedes rule in all_rules (aus Schritt 2):
  # Hartes Relevanz-Gate: BEIDE Bedingungen muessen gelten
  applies_to_match = (rule.frontmatter.applies_to matcht eine der Batch-Dateien/Layer)
  kern_symbol_im_diff = (ein Kern-Symbol des Patterns kommt im unstaged Diff der gematchten Datei vor)

  IF applies_to_match AND kern_symbol_im_diff
     AND rule NICHT in findings (= kein Verstoss = aktiver PASS-mit-Match):
    Bash: py -3 .claude/scripts/pattern_library.py append-usage \
          --signal CONFORMANCE_PASS --pattern-id {rule.id} --scope {rule.scope} \
          --commit-sha {git rev-parse HEAD} --file-anchor {gematchte Datei} \
          --note "CONFORMANCE_PASS via _PostBatch_PatternConformance (batch={batch_id})"
    Logge: "[PatternConformance/R2] CONFORMANCE_PASS-Signal: {rule.id} (applies_to-Match + Kern-Symbol im Diff)"
  ELSE:
    # KEIN Signal. Insbesondere: kein finding + KEIN Match => NIE usage++ (Asymmetrie C-6).
    KEIN append_usage.
```

**INVARIANTE (ADR-PL-008, AK-CTX-R2):** R2 ruft `lifecycle()` NICHT direkt — nur `append_usage`
(Signal). Den `usage++` macht der Drain (R6b). **Asymmetrie (C-6, K-4):** "kein finding" darf NIE
als `usage++` gewertet werden; nur ein aktiver PASS-mit-`applies_to`-Match UND Kern-Symbol-im-Diff
appendet ein Signal.

### Schritt 6b: AK-3 POST-B-Orchestrierung (a)/(b)/(c) — additiv

```
# (a) Golden-Capture neu als-relevant erkannter Patterns (W-POSTB-2) via add_arch.
#     add_arch schreibt das VOLLE Counter-Frontmatter ab Geburt (usage_count:0 etc.).
#     WORTHINESS-EXTRACT (is_pattern_worthy) ist batch_C5 (known-pending) — hier add_arch DIREKT.
FÜR jedes als golden bewertete neue Pattern:
  Bash: py -3 .claude/scripts/pattern_library.py add --arch --layer {LAYER} --name "{name}" \
        --description "{desc}"   # Reuse add_arch (F4); KEIN Eingriff in den Counter-Kern.

# (b) Counter-Vorschub GENAU 1x via Drain R6b (idempotent, K-1):
#     Der Drain konsumiert ALLE seit dem letzten Lauf neuen Signale (VERIFIED/CONFORMANCE_PASS/REVERT)
#     und ruft den Sink (lifecycle). Zweimal drainen == einmal usage++ (processed-Cursor).
Bash: py -3 .claude/scripts/pattern_library.py drain
Logge: "[PatternConformance/AK-3] drain_usage_log: usage_pp={usage_pp} broken_pp={broken_pp} (idempotent)"

# (c) Revert -> Forensik via R4 (W-POSTB-4): fuer jeden git-Revert-Kandidaten im Batch-Diff
#     greift das konservative Anti-False-Positive-Gate VOR dem irreversiblen pfad-2/auto-deprecate@3.
FÜR jeden Pattern-Anwendungs-Commit der im Batch revertet wurde:
  detect_and_emit_revert(pattern_id, candidate, applied_commit_sha, applied_file_anchor)
  # gated=True => KEIN broken++ (kein commit_sha/file_anchor-Doppel-Match). emitted=True => REVERT-Signal,
  # broken++ macht erst der Drain (R6b). auto-deprecate@3 bleibt IRREVERSIBEL + hinter EINEM Konsumenten.
```

**Heimat-Eskalation (W-2, §8):** Bleibt POST-B additiv hier, SOLANGE kein POST-A-Vertragsbruch.
Bei `model_tier`-Konflikt (POST-A=floor/haiku vs. Golden-Capture-Worthiness braucht opus) → Split nach
`_PostBatch_PatternLearning.md` (erlaubte Eskalation, KEIN POST-A-Override, KEIN Architektur-Re-Entwurf).

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| PatternLibrary leer (EMPTY_SEED) | NON-BLOCKING Skip (INV-B2-1), blocker_count=0, tests_dirty=false |
| Git-Diff nicht lesbar | WARNUNG + Fallback: alle angefassten Dateien aus DF_BATCH_STATE |
| Slice-Name unbekannt | WARNUNG + Fallback: --scope unstaged |
| Pattern-Datei nicht lesbar | WARNUNG + SKIP fuer dieses Pattern |
| auto_fixable=false + HiL=off | ARCHITECT_ESCALATION_QUEUE befuellen + escalation_queued=true → Aufrufer ruft _I_cleanCodeArchitect (ARCH-7, kein Hard-Stop) |
| Leere findings Liste | PASS sofort, tests_dirty=false, blocker_count=0 |

---

## Verwandt

- `_PostBatch_orchestrate` SCHRITT 1.5 — Aufrufer fuer Batch-Scope
- `_TDD_orchestrate` Schritt 8i+ — Aufrufer fuer Slice-Scope (Quick Gate, AK-A-2)
- `{VAULT_ROOT}/Libraries/PatternLibrary/_generic/frontmatter-schema.md` — Pflichtfelder-Schema

---

## bestimme_auto_fixability (Hilfsfunktion, AK-D-3, BL-153 + ARCH-T4)

```
FUNKTION bestimme_auto_fixability(pattern, finding):
  # 3-stufige Klassifikation: Frontmatter-Flag → Pattern-Typ-Heuristik → Default
  # Liefert: {auto_fixable: bool, auto_fixable_class: "trivial"|"risky"|"architect_required"}

  # Stufe 1: Frontmatter explizit (hoechste Prioritaet)
  IF pattern.frontmatter.auto_fixable != null:
    flag  = pattern.frontmatter.auto_fixable
    klasse = pattern.frontmatter.auto_fixable_class ?? (flag ? "trivial" : "risky")
    RETURN {auto_fixable: flag, auto_fixable_class: klasse}

  # Stufe 2: Pattern-Typ-Heuristik (ARCH-T4, BL-153 3. Audit)
  pattern_type = pattern.frontmatter.pattern_type ?? infer_type(pattern)

  # Trivial = additiv ohne Symbol-Rename, kein Refactor
  IF pattern_type IN ["doc-typo", "comment-format", "import-order",
                      "trailing-newline", "frontmatter-field-add",
                      "missing-vertrag-block"]:
    RETURN {auto_fixable: true, auto_fixable_class: "trivial"}

  # Risky = mechanisch moeglich aber Symbol-rename → Test-Suite-Risiko
  IF pattern_type IN ["class-naming", "method-naming", "constant-rename",
                      "namespace-rename", "file-rename"]:
    RETURN {auto_fixable: true, auto_fixable_class: "risky"}

  # Architect-required = strukturelle Aenderung
  IF pattern_type IN ["controller-structure", "base-class-change",
                      "layer-violation", "logic-refactor"]:
    RETURN {auto_fixable: false, auto_fixable_class: "architect_required"}

  # Stufe 3: Konservativer Default
  RETURN {auto_fixable: false, auto_fixable_class: "risky"}
```

---

## wende_fix_an (Apply-Mechanik, ARCH-T1, BL-153 3. Audit)

```
FUNKTION wende_fix_an(finding) -> {applied: bool, edits: [...], rollback_diff: str}:
  # Apply trivial Auto-Fix via Edit-Tool. PFLICHT: Pre-/Post-State + Rollback-Diff.

  # PRE-Check: Datei + Region lesen, alten Stand sichern
  pre_state = Read(finding.datei, region=finding.zeile_start..finding.zeile_end)
  rollback_anchor = git_diff_capture(finding.datei)  # vor Edit

  # Apply-Strategie pro Pattern-Type
  SWITCH finding.pattern_type:
    "doc-typo", "comment-format":
      # Wort-Ersetzung in Kommentar/Doku (Edit-Tool old_string→new_string)
      Edit(file=finding.datei, old_string=finding.violation_text,
           new_string=finding.suggested_text)

    "trailing-newline":
      # Datei-Ende auf \n normalisieren (Bash: ensure trailing newline)
      Bash("[[ -z $(tail -c1 {finding.datei}) ]] || echo >> {finding.datei}")

    "frontmatter-field-add":
      # Pflichtfeld mit Default einfuegen (vor closing ---)
      Edit(file=finding.datei,
           old_string="^---\n",
           new_string="---\n{finding.field}: {finding.default_value}\n",
           replace_all=false)

    "import-order":
      # Imports sortieren (sprach-spezifisch — delegiert an Linter)
      Bash("ruff check --select=I --fix {finding.datei}")  # Beispiel Python

    "missing-vertrag-block":
      # VERTRAG-Block-Stub einfuegen (Template-basiert)
      Edit(file=finding.datei,
           old_string=finding.insert_anchor,
           new_string=finding.vertrag_template + "\n" + finding.insert_anchor)

    DEFAULT:
      # Nicht-trivial → SKIP (sollte nie hier landen wenn class==trivial)
      Logge FEHLER: "[wende_fix_an] Unbekannter Pattern-Type: {finding.pattern_type} — SKIP"
      RETURN {applied: false, edits: [], rollback_diff: ""}

  # POST-Check: Edit erfolgreich?
  post_state = Read(finding.datei, region=finding.zeile_start..finding.zeile_end)
  IF post_state == pre_state:
    Logge WARN: "[wende_fix_an] Edit hat nichts geaendert: {finding.pattern_id}"
    RETURN {applied: false, edits: [], rollback_diff: ""}

  # Audit-Log + Rollback-Diff fuer Recovery
  rollback_diff = git_diff_since(rollback_anchor, finding.datei)
  audit_log_append({type: "AUTO_FIX_APPLIED", pattern: finding.pattern_id,
                    datei: finding.datei, class: "trivial", diff: rollback_diff})

  RETURN {applied: true, edits: [{file, old, new}], rollback_diff: rollback_diff}
```

**INV-AUTO-FIX-1 (ARCH-T1):** `wende_fix_an` MUSS NUR fuer `auto_fixable_class == "trivial"`-Findings aufgerufen werden. Risky/architect_required → PL-Item bzw. ARCHITECT_ESCALATION_QUEUE.

**INV-AUTO-FIX-2:** Jeder Apply MUSS `rollback_diff` produzieren (audit_log + git-Recovery).

**INV-AUTO-FIX-3:** Pre-State == Post-State → Edit hat nichts gemacht → applied=false (kein false-positive im Audit-Log).

## Helper-Funktionen (ARCH-U1)

**INV-AUTO-FIX-4 (NEU):** Alle Helper sind hier als ausfuehrbare Funktionen definiert — kein Pseudo-Code mehr.

```
FUNKTION infer_type(pattern):
  """Heuristik via Pattern-Frontmatter-Felder — leitet Fix-Typ ab."""
  IF pattern.frontmatter.applies_to enthaelt "comment" OR "doc": RETURN "doc-typo"
  IF pattern.frontmatter.applies_to enthaelt "naming": RETURN "class-naming"
  IF pattern.frontmatter.applies_to enthaelt "frontmatter": RETURN "frontmatter-field-add"
  IF pattern.frontmatter.applies_to enthaelt "import": RETURN "import-order"
  IF pattern.frontmatter.applies_to enthaelt "vertrag": RETURN "missing-vertrag-block"
  RETURN "unknown"

FUNKTION git_diff_capture(file):
  """Pre-State snapshot: aktueller HEAD + Diff vor Edit."""
  result = Bash("git diff HEAD -- {file}")
  RETURN {anchor_sha: Bash("git rev-parse HEAD").stdout.strip(), pre_diff: result.stdout}

FUNKTION git_diff_since(anchor, file):
  """Post-State diff seit Snapshot — fuer Rollback-Nachweis."""
  RETURN Bash("git diff {anchor.anchor_sha} -- {file}").stdout

FUNKTION audit_log_append(entry):
  """Append JSON-Lines Eintrag nach .claude/output/auto_fix_audit.log."""
  log_path = ".claude/output/auto_fix_audit.log"
  Bash("echo '{json.dumps(entry)}' >> {log_path}")
```
