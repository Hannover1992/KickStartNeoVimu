# /_arc42_orchestrate — arc42-Sichten-Renderer (Thin-Manager, Views auf Wahrheiten)

```yaml
status: active
version: 1.0.0
created: 2026-06-16
op: Arc42Render
phase: Meta
type: orchestration
chain_position: "terminale A-Phase (nach Gap/PL) ODER ad-hoc standalone {BL}"
team_based: true
feature_anchor: BL-378 (supersedes BL-305)
```

```
+======================================================================+
| /_arc42_orchestrate {BL} [--tier=auto|full|standard|light]           |
|                          [--mode=adhoc|organic]                      |
+======================================================================+
| ACTOR: TEAM LEAD (DU — reiner Orchestrator, INV-AO-CALLER)          |
| ZWECK: rendert die SCHON-gepflegten W{n}-Wahrheiten eines BL in     |
|        normierte arc42-Sichten + Mermaid. KEIN Wahrheits-Produzent  |
|        (Geschwister von /_presentation). Luecke = sichtbare offene  |
|        Frage (Backlink Gap-OQ / BLOCKED-PL).                        |
| OUTPUT: {WORKING_DIR}/arc42/NN_*.md  (file-isoliert) + 00_index.md  |
| FAN-OUT: 1 Sektion = 1 Berater = 1 Worker, PARALLEL (read-only ueber|
|          eingefrorenem Snapshot -> keine Inter-Sektions-Abhaengigkt,|
|          file-isoliert -> kein concurrent-write-Race). BL-330 gruen/|
|          gelb (Doku-Projektion), KEIN dispatch_implement-Build-Motor.|
+======================================================================+
```

## VERTRAG

```
WORKING_DIR = resolve_bl_path(BL_ID)         # INV-VAULT-9
ARC42_DIR   = {WORKING_DIR}/arc42/

LIEST (READ-ONLY, der Wahrheits-Snapshot):
  {WORKING_DIR}/_manifest.md  → A_PIPELINE_STATE (k_score, srs, modus, greenfield-Signal),
                                 BERATER_OUTPUTS.{dependencyAnalyzer, specParse, akExtraktion, plAggregation, domainBrief}
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md    (W{n}-Wahrheiten / Bausteine)
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md      (Schnittstellen, Komponenten, ADRs)
  {VAULT}/Backlog/{BL_SLUG}/4_K-Score/*           (Tier-Ableitung)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/*               (offene Fragen / OQ)
  {VAULT}/Backlog/{BL_SLUG}/6_PL/{BL}-parking-lot.md  (PL-Items, READY/BLOCKED)

SCHREIBT (NUR Orchestrator-Slot + Fan-In):
  {ARC42_DIR}/00_index.md   (Sektions-Links + Tier + Grounding-Coverage + Lint-Status)
  KEINE Sektionsdateien direkt (das machen die Berater, file-isoliert).
  KEINE Wahrheits-Edits, KEIN Manifest-State-Write (reine Render-Schicht).

RUFT (Berater via Worker-Spawn, INV-PM-5 — PARALLEL, file-isoliert) — ALLE 12 Sektionen (13 Berater, §8 gesplittet):
  _arc42_berater_einfuehrung    → 01_einfuehrung_ziele.md (§1, mindmap)
  _arc42_berater_randbedingungen→ 02_randbedingungen.md   (§2, Tabellen)
  _arc42_berater_kontext        → 03_kontext.md           (§3, flowchart)
  _arc42_berater_loesungsstrategie → 04_loesungsstrategie.md (§4, flowchart?)
  _arc42_berater_bausteinsicht  → 05_bausteinsicht.md     (§5, flowchart+subgraph/classDiagram)
  _arc42_berater_laufzeitsicht  → 06_laufzeitsicht.md     (§6, sequenceDiagram/stateDiagram-v2)
  _arc42_berater_verteilung     → 07_verteilung.md        (§7, flowchart+subgraph)
  _arc42_berater_querschnitt    → 08_querschnitt.md       (§8 allgemein, mindmap/flowchart)
  _arc42_berater_datenmodell    → 08_datenmodell.md       (§8 Datenmodell, erDiagram)
  _arc42_berater_entscheidungen → 09_entscheidungen.md    (§9, ADR-Tabelle)
  _arc42_berater_qualitaet      → 10_qualitaet.md         (§10, mindmap + Q42-Szenarien aus AKs)
  _arc42_berater_risiken        → 11_risiken.md           (§11, Tabelle aus BLOCKED-PL/OQ)
  _arc42_berater_glossar        → 12_glossar.md           (§12, Begriff/Definition aus SemanticLibrary)

RUFT (Gate):
  py -3 .claude/scripts/arc42_mermaid_lint.py {ARC42_DIR}/*.md   # AK-3, nach Fan-Out, vor Index
```

## INVARIANTEN

```
INV-ARC42-1 (Read-Only): arc42 ist eine VIEW-Schicht — liest Wahrheiten, schreibt NIE welche.
                         Kein Manifest-State-Write, keine Model/Spec/PL-Edits.
INV-ARC42-2 (File-isoliert): jeder Berater schreibt NUR seine eigene NN_*.md -> kein concurrent-write-Race;
                         Fan-Out daher echt parallel (read-only ueber eingefrorenem Snapshot).
INV-ARC42-3 (Luecke sichtbar): fehlende Wahrheit -> `> [ungegroundet: X] (siehe OQ-y / PL-z)`-Platzhalter,
                         NIE halluziniertes Grounding (W{n} code_verified). Index meldet Coverage.
INV-ARC42-4 (Lint-Gate): jede Sektionsdatei MUSS arc42_mermaid_lint.py bestehen (exit 0); FAIL -> im Index markiert.
INV-ARC42-5 (Proportionalitaet): Tier (FULL/STANDARD/LIGHT) steuert Sektions-Auswahl (Anti-Zeremonie, arc42-Imperativ).
INV-AO-CALLER: Lead laedt /_arc42_orchestrate SELBST (kein Mega-Agent-Delegieren).
INV-PM-5: Berater via Worker-Spawn (Agent), nie Lead-Direkt-Load.
INV-PM-1: opus-floor (Sichten-Abstraktion = kognitives Urteil).
INV-ARC42-6 (Mermaid-only): NUR reines Mermaid + Markdown — KEIN C4 (User-Direktive 2026-06-16).
            C4-Semantik (Context/Container/Component/Deployment) via flowchart+subgraph. arc42_mermaid_lint
            flaggt C4* als unbekannten Typ (Enforcement).
INV-ARC42-7 (Vehikel grün): arc42-Render ist read-only Projektion = GRÜNE Zone (BL-330) -> Sektions-Fan-Out
            laeuft als deterministischer Workflow (dispatch_arc42) ODER altmodisch-parallele Team-Member,
            geroutet via workflow_zones.vehicle_for. NICHT der verbotene dispatch_implement-Build-Motor.
```

## Tier-Matrix (Proportionalitaet)

| Tier | Sektionen | Wann (auto) |
|---|---|---|
| **LIGHT** | §3 Kontext (knapp), §5 Bausteinsicht Ebene-1 | k<25, M1/M2, trivial |
| **STANDARD** (Default) | §1, §3, §5, §6, §8-Datenmodell, §9, §10, §11, §12 | Normalfall pro BL |
| **FULL** | alle 12 (inkl. §2, §4, §7, §8-Querschnitt) | M3 / k>=25 / greenfield (`twin_ref=IS-NEW`) |

`auto`: greenfield ODER k_score>=25 ODER modus==M3 → FULL; k<25 ∧ (M1∨M2) → LIGHT; sonst STANDARD.
**ALLE 12 Sektionen implementiert** (13 Berater, §8 = Datenmodell + Querschnitt). Tier wählt die Teilmenge;
fehlende WAHRHEIT (nicht fehlende Sektion) → `[ungegroundet]`-Platzhalter im Sektions-File (NIE stiller Skip).

## ORCHESTRATOR-PSEUDOCODE

```
ENTRY (Lead, INV-AO-CALLER):
  BL_ID, tier=auto, mode=adhoc = parse_args()
  WORKING_DIR = resolve_bl_path(BL_ID); ARC42_DIR = {WORKING_DIR}/arc42/; mkdir -p ARC42_DIR

# — Stufe 1: Lifecycle (NESTED-AWARE) —
  parent = Read(_manifest).BDF_PIPELINE_STATE.active_team   # gesetzt wenn unter A Phase 5d o.ae.
  nested = (parent != null AND NOT parent.name.startswith("arc42-"))
  IF nested:
    own_team = parent.name   # Sub-Orchestrierung: Berater laufen im Parent-Team, KEIN eigenes TeamCreate/Delete
    Logge: "[arc42] nested unter Parent-Team {own_team} — kein eigenes Team-Lifecycle."
  ELSE:
    own_team = "arc42-{BL_ID}"
    TeamCreate team_id=own_team purpose="arc42-Sichten {BL_ID}"

# — Stufe 2: Snapshot + Tier —
  snap = read_truth_snapshot(WORKING_DIR)   # Model/Spec/K-Score/Gap/PL/AKs/depAnalyzer (READ-ONLY)
  IF tier=="auto": tier = derive_tier(snap.k_score, snap.modus, snap.greenfield)   # FULL/STANDARD/LIGHT
  sections = TIER_SECTIONS[tier]    # alle Tier-Sektionen implementiert (13 Berater, §1-§12)
  pending  = []                     # keine unimplementierten Sektionen mehr

# — Stufe 3: Fan-Out (PARALLEL, file-isoliert) — VEHIKEL-GEROUTET (BL-330/BL-378 INV-ARC42-7) —
  workflow_param = session_params.workflow ?? false   # {false,normal,fast}
  vehicle = workflow_zones.vehicle_for("dispatch_arc42", workflow_param)   # green -> "workflow" bei mode!=false
  IF vehicle == "workflow":
    # GRUEN (read-only Projektion, NON-BLOCKING): deterministischer Parallel-Doku-Workflow.
    # 1 Step = 1 agent, file-isoliert -> race-frei. Mega-Worker strukturell unmoeglich.
    Workflow(name="dispatch_arc42", args={bl_id: BL_ID, arc42_dir: ARC42_DIR, sections: sections})
  ELSE:
    # altmodisch (workflow=false ODER nested ohne Workflow): parallele Team-Member, file-isoliert, INV-PM-5.
    PARALLEL FOR s IN sections:
       Agent(team_name=own_team, model=opus,
             prompt="Lade Skill _arc42_berater_{s.name} und fuehre Vertrag aus mit args={BL_ID}. "
                    "Schreibe NUR {ARC42_DIR}/{s.file}. Read-only auf Wahrheiten. NUR Mermaid+Markdown (kein C4). "
                    "Fehlende Wahrheit -> ungegroundet-Platzhalter mit OQ/PL-Backlink. KEIN Sub-Spawn (W7).")
  # Fan-In-Barrier: erst NACH allen Sektionen (Workflow-Return ODER alle Member fertig), NICHT pro Sektion.

# — Stufe 4: Lint-Gate (INV-ARC42-4) —
  lint = Bash("py -3 .claude/scripts/arc42_mermaid_lint.py {ARC42_DIR}/*.md")   # exit 0 ok / 2 fail

# — Stufe 5: Fan-In Index (Orchestrator-Slot) —
  write {ARC42_DIR}/00_index.md:
     # arc42 — {BL_ID}  (Tier: {tier}, {mode})
     | Sektion | Datei | Grounding | Lint |  + Links
     pending: {pending}  (Phase-3 — noch nicht implementiert, NICHT uebersprungen-still)
     Coverage: {voll/teil/leer pro Sektion aus den Berater-Frontmattern}

# — Stufe 5b: Konsolidiertes all.md (BL-417, read-only Concat-Fan-In, INV-ARC42-1 gewahrt) —
  # Vereint die gerenderten NN_*.md (01..12) in numerischer Sektions-Reihenfolge zu EINER Lese-Ansicht.
  # Reine Projektion der SCHON ge-linteten Sichten — KEIN Re-Render, keine neuen Wahrheiten, idempotent,
  # BOM-frei/LF. 00_index.md bleibt Navigations-/Status-Ansicht; all.md ist die Durchlese-Ansicht (Koexistenz).
  Bash("py -3 .claude/scripts/arc42_consolidate.py --arc42-dir {ARC42_DIR}")   # schreibt {ARC42_DIR}/all.md
  # 00_index verlinkt auf all.md (AK-5). Lint lief in Stufe 4 auf die Sektionen; all.md = deren Concat.

# — Stufe 6: Lifecycle-Ende —
  IF NOT nested: TeamDelete team_id=own_team   # nested: Parent (A) raeumt sein Team selbst ab
  SendMessage/Log: "arc42 {tier}: {|sections|} Sichten -> {ARC42_DIR}, Lint={ok|fail}, pending={pending}"
```

## Zwei Modi (BL-378)
- **adhoc** (Default beim manuellen Aufruf): vor Story-Kickoff / vor Implementierung, nachdem A durch ist.
- **organic**: als terminale `/_A_orchestrate`-Phase (Inkrement-2-Wiring) — laeuft jeden A-Lauf mit, idempotent
  (Re-Run ueberschreibt Sektionsdateien, Backlink-Stabilitaet). A IST der Nach-Analyse-vor-Impl-Punkt.

## Verwandt
- `/_presentation` (Geschwister-Render-Schicht) · `_arc42_berater_{kontext,bausteinsicht,laufzeitsicht,datenmodell}` ·
  `arc42_mermaid_lint.py` (AK-3 Gate) · `_A_orchestrate` (Inkrement-2-Heimat als terminale Phase) ·
  BL-378 (supersedes BL-305) · BL-270 (Models als Views) · BL-330 (Vehikel: Doku=gruen/gelb) · arc42-Template v9.0-DE.
```
