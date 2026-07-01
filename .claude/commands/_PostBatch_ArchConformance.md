---
type: berater
feature: ArchitektonischePatternLibrary
bl_item: BL-154
ak_ref: "AK-3-1, AK-3-2, AK-6-2, AK-6-3"
chain_position: "nach _T_orchestrate-Run-1, VOR _PostBatch_PatternConformance"
status: active
version: 1.0.0
created: 2026-05-01
---

# _PostBatch_ArchConformance (BL-154)

**Zweck:** Architektonische Conformance-Pruefung auf Batch-Ebene — vollstaendiger
unstaged Diff aller im Batch angefassten Dateien gegen ARCH-VERTRAG-Blöcke und
PatternLibrary-Grenzen. Schreibt `arch_dirty` Flag. Laeuft VOR `_PostBatch_PatternConformance`.

**Analog zu:** `_PostBatch_PatternConformance` (BL-153) — gleiche Thin-Wrapper-Struktur.

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _PostBatch_ArchConformance (BL-154, AK-3-1, AK-6-2, AK-6-3)║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {WORKING_DIR}/_manifest.md → DF_BATCH_STATE.batch_current        ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_index.md                  ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_project/{LAYER}/*.md      ║
║    VAULT_ROOT via: resolve_vault_root.py (ARCH-N8, Single Source)   ║
║    _session_params.md → GLOBAL_HIL                                   ║
║    Git unstaged diff (vollstaendiger Batch-Diff)                     ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {WORKING_DIR}/_manifest.md:                                       ║
║      ARCH_CONFORMANCE_STATE.arch_dirty: true|false                   ║
║      ARCH_CONFORMANCE_STATE.blocker_count: {N}                       ║
║      ARCH_CONFORMANCE_STATE.warn_count: {N}                          ║
║      ARCH_CONFORMANCE_STATE.apply_happened: true|false               ║
║      ARCH_CONFORMANCE_STATE.hil_mode: off|on                         ║
║      ARCH_CONFORMANCE_STATE.escalation_queued: true|false            ║
║      ARCH_CONFORMANCE_STATE.coupling_warnings_count: {N}             ║
║        (BL-154-PL-29, ARCH-K3 — Coupling-Score-Check)               ║
║      ARCHITECT_ESCALATION_QUEUE: [{finding_id, datei, pattern_id,   ║
║        severity, beschreibung, suggested_berater, queued_at,         ║
║        auto_fixable_class}]                                          ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    PATTERN_CONFORMANCE_STATE.* (das ist _PostBatch_PatternConformance)║
║    DF_BATCH_STATE.* (read-only)                                      ║
║                                                                      ║
║  MODELL-TIER: floor (haiku) — Pattern-Lookup + Diff-Analyse          ║
║  INVARIANTEN:                                                        ║
║    INV-ARCH-1: Laeuft IMMER VOR _PostBatch_PatternConformance        ║
║    INV-ARCH-2: HiL binaer — NUR off (Auto-Apply) ODER on (Report)   ║
║    INV-ARCH-3: arch_dirty=true NUR wenn Apply-Lauf stattfand ODER   ║
║                nicht-fixierbare BLOCKER gefunden                     ║
║    INV-ARCH-4: NON-BLOCKING bei leerer PatternLibrary (EMPTY_SEED)  ║
║    INV-ARCH-5: auto_fixable_class PFLICHT in Queue-Eintraegen        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
Skill(_PostBatch_ArchConformance, args="--scope unstaged --batch {ID}")
```

Wird von `_PostBatch_orchestrate` (SCHRITT 1.3) aufgerufen.

---

## HiL-Semantik (AK-6-3, analog AK-E-3 BL-153)

**Genau 2 Modi — kein whenBlocker-Modus:**

| HiL | BLOCKER (auto-fixable) | BLOCKER (nicht auto-fixable) | WARN | INFO |
|-----|------------------------|------------------------------|------|------|
| `off` (Default) | Auto-Apply | Eskalation-Queue (ARCH-7) | PL-Park | Ignoriert |
| `on` | Report + `/_question "Apply / Park / Skip?"` | Report + `/_question` | Report + `/_question` | Report |

---

## Ablauf

### Schritt 0: PatternLibrary verfuegbar? (INV-ARCH-4)

```
# ARCH-N9: VAULT_ROOT via resolve_vault_root.py (Single Source of Truth)
IF {VAULT_ROOT}/Libraries/PatternLibrary/_index.md NICHT vorhanden OR leer (EMPTY_SEED):
  Logge: "[ArchConformance] PatternLibrary leer — NON-BLOCKING Skip (EMPTY_SEED)"
  Schreibe ARCH_CONFORMANCE_STATE:
    arch_dirty: false
    blocker_count: 0
    warn_count: 0
    apply_happened: false
    hil_mode: {hil_mode}
    escalation_queued: false
    note: "PatternLibrary leer (EMPTY_SEED) — ArchConformance-Check uebersprungen"
  → RETURN (kein Fehler)
```

### Schritt 1: Diff laden

```
# Vollstaendiger unstaged Diff (alle Batch-Dateien)
dateien = git_unstaged_files()
Logge: "[ArchConformance] Scope=unstaged: {|dateien|} Dateien im Batch-Diff"
```

### Schritt 2: Architektonische Pattern + ARCH-VERTRAG-Lookup

```
# Nur architektonische Patterns aus PatternLibrary laden
arch_patterns = lies {VAULT_ROOT}/Libraries/PatternLibrary/_project/{LAYER}/*.md
filter: status != DEPRECATED, category IN ["architecture", "structure", "layer"]

# ARCH-VERTRAG-Block aus Worker-Prompts (W22, W30):
# Pruefen ob Diff-Dateien ARCH-VERTRAG-Block enthalten und einhalten
arch_vertrag_findings = pruefe_arch_vertrag_einhaltung(dateien)

findings = []
FÜR jede datei in dateien:
  FÜR jedes pattern in arch_patterns:
    IF datei-Inhalt verletzt pattern.boundary_rules ODER
       datei-Inhalt enthaelt pattern.anti_pattern:
      findings.append({
        datei: datei,
        pattern_id: pattern.id,
        severity: pattern.severity,
        beschreibung: "{violation_text}",
        auto_fixable: (pattern.frontmatter.auto_fixable ?? false),
        auto_fixable_class: (pattern.frontmatter.auto_fixable_class ?? "risky")
        # INV-ARCH-5: auto_fixable_class PFLICHT (trivial|risky|architect_required)
      })

# ARCH-VERTRAG-Findings hinzufuegen
findings += arch_vertrag_findings
```

### Schritt 3: HiL-Entscheidung + Apply (AK-6-3)

```
hil_mode = lies _session_params.md → GLOBAL_HIL ?? "off"
blocker_findings = [f for f in findings IF f.severity == "BLOCKER"]
warn_findings    = [f for f in findings IF f.severity == "WARN"]
apply_happened   = false

IF hil_mode == "off":
  FÜR jedes finding in blocker_findings:
    IF finding.auto_fixable AND finding.auto_fixable_class == "trivial":
      wende_fix_an(finding)
      apply_happened = true
      Logge: "[ArchConformance] Auto-Apply BLOCKER (trivial): {finding.pattern_id} in {finding.datei}"
    ELIF finding.auto_fixable AND finding.auto_fixable_class == "risky":
      Schreibe PL-Item: "[ArchConformance] RISKY-BLOCKER {finding.pattern_id}: {finding.beschreibung}"
      Logge: "[ArchConformance] Risky-BLOCKER → PL-Item (kein Auto-Apply)"
    ELSE:
      Logge: "[ArchConformance] BLOCKER nicht auto-fixbar (class={finding.auto_fixable_class}): {finding.pattern_id}"
  FÜR jedes finding in warn_findings:
    Schreibe PL-Item: "[ArchConformance] WARN {finding.pattern_id}: {finding.beschreibung}"

ELIF hil_mode == "on":
  FÜR jede finding-Gruppe (gruppiert nach severity):
    AskUserQuestion:
      "ArchConformance {finding.severity}: {finding.pattern_id} in {finding.datei}
       {finding.beschreibung}
       [Apply] Auto-korrigieren
       [Park]  Als PL-Item parken
       [Skip]  Ueberspringen (Evidenz-Pflicht)"
    IF user_choice == "Apply":
      wende_fix_an(finding)
      apply_happened = true
    ELIF user_choice == "Park":
      Schreibe PL-Item: "[ArchConformance] {finding.severity} parkiert: {finding.beschreibung}"
```

### Schritt 3.5: Architekten-Eskalation (ARCH-7, INV-ARCH-5)

```
# Alle nicht-auto-fixbaren BLOCKER (HiL=off) → ARCHITECT_ESCALATION_QUEUE
verbleibende_nicht_fixierbar = [f for f in blocker_findings IF NOT f.auto_fixable AND hil_mode == "off"]

IF |verbleibende_nicht_fixierbar| > 0:
  FÜR jedes finding in verbleibende_nicht_fixierbar:
    ARCHITECT_ESCALATION_QUEUE.append({
      finding_id: "{finding.pattern_id}@{finding.datei}",
      datei: finding.datei,
      pattern_id: finding.pattern_id,
      severity: finding.severity,
      beschreibung: finding.beschreibung,
      suggested_berater: "_I_cleanCodeArchitect --mode impact-check",
      queued_at: {ISO8601},
      auto_fixable_class: finding.auto_fixable_class  # INV-ARCH-5: PFLICHT
    })
  escalation_queued = true
  Logge: "[ArchConformance] ARCHITECT_ESCALATION_QUEUE: {|verbleibende_nicht_fixierbar|} Findings eskaliert"
ELSE:
  escalation_queued = false
```

### Schritt 3.7: Coupling-Score-Check (BL-154-PL-29, ARCH-K3, V5)

> **Zweck:** Pattern das strukturelle Kopplung propagiert (k_kopplung-Einfluss nachweisbar)
> wird automatisch als DEPRECATED-Kandidat markiert und mit Warnung versehen.
> Schwellwert: Pattern-Frontmatter `k_kopplung_impact >= 70` ODER
> `propagates_coupling: true` ODER Verletzungs-Muster in >= 2 Dateien des Batch-Diffs.

```
# Coupling-Score-Check (BL-154-PL-29, ARCH-K3)
coupling_warnings = []

FÜR jedes pattern in arch_patterns:
  pattern_fm = lies_frontmatter(pattern.path)

  # Signal 1: Frontmatter k_kopplung_impact explizit hoch
  IF pattern_fm.k_kopplung_impact != null AND pattern_fm.k_kopplung_impact >= 70:
    coupling_warnings.append({
      pattern_id: pattern.id,
      signal: "k_kopplung_impact={pattern_fm.k_kopplung_impact} >= 70",
      recommended_action: "DEPRECATED-Kandidat pruefen"
    })
    Logge: "[CouplingCheck] {pattern.id}: k_kopplung_impact={pattern_fm.k_kopplung_impact} — DEPRECATED-Kandidat"

  # Signal 2: propagates_coupling Flag gesetzt
  ELIF pattern_fm.propagates_coupling == true:
    coupling_warnings.append({
      pattern_id: pattern.id,
      signal: "propagates_coupling=true",
      recommended_action: "boundary_notes ergaenzen + DEPRECATED-Kandidat pruefen"
    })
    Logge: "[CouplingCheck] {pattern.id}: propagates_coupling=true — Warnung"

  # Signal 3: Pattern verletzt in >= 2 Batch-Dateien (Kopplung wird verbreitet)
  ELSE:
    violations_in_batch = [f for f in findings IF f.pattern_id == pattern.id]
    IF |violations_in_batch| >= 2:
      coupling_warnings.append({
        pattern_id: pattern.id,
        signal: "Verletzung in {|violations_in_batch|} Batch-Dateien",
        recommended_action: "Pattern-Reichweite pruefen"
      })
      Logge: "[CouplingCheck] {pattern.id}: Verletzungen in {|violations_in_batch|} Dateien — Kopplungs-Signal"

IF |coupling_warnings| > 0:
  # In ARCH_CONFORMANCE_STATE schreiben (nicht auto-fixbar — immer Parking-Lot)
  FÜR jedes warn IN coupling_warnings:
    Schreibe PL-Item: "[ArchConformance-CouplingCheck] {warn.pattern_id}: {warn.signal}. Empfehlung: {warn.recommended_action}"
    Logge: "[CouplingCheck] PL-Item erstellt fuer {warn.pattern_id}"
  Schreibe ARCH_CONFORMANCE_STATE.coupling_warnings_count = |coupling_warnings|
ELSE:
  Logge: "[CouplingCheck] Kein Kopplungs-Problem festgestellt"
  Schreibe ARCH_CONFORMANCE_STATE.coupling_warnings_count = 0
```

### Schritt 4: arch_dirty Flag setzen (AK-3-1, INV-ARCH-3)

```
# INV-ARCH-3: arch_dirty=true wenn Apply-Lauf stattfand ODER nicht-fixierbare BLOCKER
arch_dirty = apply_happened OR (escalation_queued AND |verbleibende_nicht_fixierbar| > 0)

Logge: "[ArchConformance] apply_happened={apply_happened}, escalation_queued={escalation_queued} → arch_dirty={arch_dirty}"
```

### Schritt 5: Output schreiben

```
verbleibende_blocker = [f for f in blocker_findings IF NOT f.auto_fixable AND hil_mode == "off"]
blocker_count = |verbleibende_blocker|

Schreibe {WORKING_DIR}/_manifest.md ARCH_CONFORMANCE_STATE:
  arch_dirty: {arch_dirty}
  blocker_count: {blocker_count}
  warn_count: {|warn_findings|}
  apply_happened: {apply_happened}
  hil_mode: {hil_mode}
  escalation_queued: {escalation_queued}
  findings_total: {|findings|}
  batch_id: {batch_current}

Schreibe {WORKING_DIR}/_manifest.md ARCHITECT_ESCALATION_QUEUE = ARCHITECT_ESCALATION_QUEUE

Logge: "[ArchConformance] DONE — arch_dirty={arch_dirty} BLOCKER={blocker_count} WARN={|warn_findings|} escalation_queued={escalation_queued}"
```
