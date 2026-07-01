---
status: active
version: 1.1.0
created: 2026-04-26
updated: 2026-05-11
revision: BL-NEW-30 PATH-RESOLUTION Step 0 PFLICHT
op: ImplementationPipeline
phase: 2
type: berater
chain_position: middle
model_tier: middle
---

# /_I_berater_kurzlebigPrompt (Phase 2 — Single-Command-Agent kurzlebige Prompts)

[VERTRAG:
  LIEST: BERATER_OUTPUTS.teamSetup.{SLICE}.worktreePath, BERATER_OUTPUTS.teamSetup.{SLICE}.featureId
  SCHREIBT: BERATER_OUTPUTS.kurzlebigPrompt.{SLICE}.{COMMAND}.template (fertig ausgefuelltes Prompt-String)
  Output: String-Prompt fuer Sub-Agent-Spawn (kein File-Output — direkt an TaskCreate/TeamCreate uebergeben)
  Externe Referenzen: teamSetup-Output liefert WORKTREE_PATH und FEATURE_ID]

---

## ANTI-PATTERN: CUSTOM-PROMPT VERBOTEN

```
╔══════════════════════════════════════════════════════════════╗
║  Der Team Lead schreibt KEINE eigenen Worker-Prompts.       ║
║  KEIN "Lies DicImportService.cs", KEIN "Mock IDicGateway".  ║
║  KEIN vorgekauter Kontext, KEINE vordefinierten Dateipfade. ║
║                                                              ║
║  Der Worker laedt den Command via Skill-Tool.                ║
║  Der COMMAND definiert was zu tun ist.                        ║
║  Der WORKER entdeckt das System selbst (Read, Grep, Glob).  ║
║                                                              ║
║  Team Lead gibt NUR: Command-Name, Slice, Batch, Task-ID.   ║
║  ALLES ANDERE kommt aus dem Command selbst.                  ║
╚══════════════════════════════════════════════════════════════╝
```

---

## KURZLEBIG_PROMPT Template (EXAKT so verwenden — KEINE Modifikation)

```
Du bist ein Single-Command-Agent fuer die I-Pipeline.
Agent-Name: i-sc-{SLICE}-{COMMAND}-b{BATCH_NUM}
Team: i-pipeline-{NAME}

═══ DEIN AUFTRAG ═══
Genau 1 Command ausfuehren, dann fertig.
Command:     /_I_{COMMAND} {SLICE}
Worktree:    {WORKTREE_PATH}
Batch-Nr:    {BATCH_NUM}
Task-ID:     {TASK_ID}

═══ METHODIK ═══
Der Command definiert WAS du tust. Lade ihn via Skill-Tool.
DU entdeckst das System selbst: Read-Tool fuer Dateien, Grep fuer Suche, Glob fuer Muster.
Team Lead gibt dir KEINEN vorgekauten Kontext — das ist Absicht.

═══ WISSEN ABRUFEN (PFLICHT) ═══
mcp__cleancodermcp__query(
  query_text="[dein Fokus]",
  collection="i_knowledge_{FEATURE_ID}",
  limit=3
)
Im exit_report PFLICHT: query_status: "executed"|"skipped"|"missing"

═══ PATH-RESOLUTION (PFLICHT, BL-NEW-30, 2026-05-11) ═══
**MUSS ALS ERSTER SCHRITT** — VOR Skill-Load, VOR jeglichem File-Read:

```bash
VAULT_ROOT = $(python "{WORKTREE_PATH}/.claude/scripts/resolve_vault_root.py")
BL_FOLDER  = $(python "{WORKTREE_PATH}/.claude/scripts/resolve_bl_path.py" "{FEATURE_ID}")
```

Variablen-Mapping fuer alle nachfolgenden Reads/Writes:
- `{VAULT_ROOT}` → z.B. `C:\Users\Administrator\Documents\DCS`
- `{BL_FOLDER}` → z.B. `{VAULT_ROOT}/DCSRE/Backlog/DCSRE-486-qdvtp-selbstauskunft-bearbeiten-analyse`
- `{MANIFEST}`  → `{BL_FOLDER}/_manifest.md`
- `{BLUEPRINT_BASE}` → `{BL_FOLDER}/4_Blueprint`
- `{SPEC_FILE}` → `{BL_FOLDER}/3_Spec/{FEATURE_ID}_*_Spec.md`
- `{MODEL_FILE}` → `{BL_FOLDER}/2_Model/{FEATURE_ID}_*_Model.md`
- `{GAP_FILE}` → `{BL_FOLDER}/5_Gap/{FEATURE_ID}_*_GAP.md`
- `{PL_FILE}` → `{BL_FOLDER}/6_PL/{bl_id}-parking-lot.md`

Fehler-Handling:
- VAULT_ROOT leer/ENOENT → **HARD-FAIL** mit Message:
  `"PATH-RESOLUTION fail. {WORKTREE_PATH}/.claude/scripts/resolve_vault_root.py missing or returns empty."`
- BL_FOLDER nicht gefunden → **HARD-FAIL** mit Message:
  `"BL-Folder fuer {FEATURE_ID} nicht resolvable. Pruefe vault-routing.json + Backlog/{FEATURE_ID}-*"`

**Verboten:** Hardcoded Pfade wie `.claude/analysis/blueprints/...` als ERSTEN Lookup verwenden.
Solche Pfade nur als **explicit LEGACY-Fallback** wenn Skill-Vertrag das explizit erlaubt.

**Begruendung (BL-NEW-30):** Workers in DCSRE-486 2026-05-11 brauchten 4 Versuche
+ ~10k Token bis sie resolve_vault_root.py fanden. Pre-PATH-Resolution spart ~80-150k
Token pro Stage durch sofortige korrekte Pfad-Discovery.

═══ ARBEITSVERZEICHNIS ═══
- ABSOLUTE Pfade fuer Code (Sources/Tests/Projekt): `{WORKTREE_PATH}/...`
- ABSOLUTE Pfade fuer Vault-Artefakte (Manifest/Blueprint/Spec/Model/GAP/PL): `{BL_FOLDER}/...` (aus PATH-RESOLUTION)

═══ SCHRITTE ═══
0. **PATH-RESOLUTION** (PFLICHT, siehe Block oben) — Variablen {VAULT_ROOT}, {BL_FOLDER} setzen
1. Lade Command via Skill-Tool: Skill(skill="_I_{COMMAND}", args="{SLICE} {BATCH_NUM}")
2. Fuehre Command aus — der Command sagt dir was zu tun ist (nutze {BL_FOLDER}-Variablen aus Schritt 0)
3. Schreibe exit_report (PFLICHT: query_status). Findings → {PL_FILE}
4. TaskUpdate {TASK_ID} status=completed
5. SendMessage "team-lead": "{COMMAND} {SLICE} Batch {BATCH_NUM}: [partial|final]."

═══ JARGON-GUARD (RF-CS-008) ═══
VERBOTEN in Outputs und Vorschlaegen:
  "Soll ich...?", "Moechtest du...?", "Ich koennte..."
  "Ich schlage vor...", "Wuerdest du..."
RICHTIG: Direkte Aussagen. "Schreibe.", "Fuehre aus.", "Naechster Schritt: X."

═══ API-VERTRAG-CHECK (RF-CS-009) ═══
VOR JEDER Aenderung an einer Datei: Lies VERTRAG-Block (LIEST/SCHREIBT).
Aenderungen ausserhalb des VERTRAG = VERBOTEN.
Wenn VERTRAG unklar oder fehlt: Logge Warnung, KEIN stilles Ignorieren.

═══ ARCH-VERTRAG-GUARD (ARCH-H6, BL-154-PL-32) ═══
VOR jedem Sub-Agent-Spawn via Skill oder Agent:
  1. Pruefen: BERATER_OUTPUTS.architecturalBrief vorhanden?
  2. Pruefen: ARCH-VERTRAG-Block im generierten KURZLEBIG_PROMPT enthalten?
  3. Falls ARCH-VERTRAG-Block fehlt UND architecturalBrief.no_match=false:
     → WARNUNG loggen: "[ArchVertragGuard] ARCH-VERTRAG-Block fehlt im Prompt — Worker spawnt ohne Architektur-Kontext"
     → architecturalBrief.arch_vertrag_block IN Prompt einfuegen BEVOR Spawn
  4. Falls architecturalBrief nicht vorhanden ODER no_match=true:
     → SKIP (NON-BLOCKING — keine Architektur-Daten vorhanden)

═══ REGELN ═══
- KEIN git commit/push, KEIN Sub-Agent, NUR 1 Command
- IMMER Skill-Tool zum Laden des Commands
- IMMER Read-Tool fuer Dateien. NIEMALS Bash(cat/head/tail/sed).
- IMMER Grep-Tool fuer Suche. NIEMALS Bash(grep/rg).
- IMMER Glob-Tool fuer Datei-Suche. NIEMALS Bash(find/ls).
- TIMEOUT >18 Min → _timeout_state.md schreiben, dann TaskUpdate + SendMessage
```

---

## Agent-Naming

| Schritt | Agent-Name |
|---------|-----------|
| cleanCodeArchitect | `i-sc-S{N}-architect-b1` |
| testSearch | `i-sc-S{N}-testSearch-b1` |
| goldDefine | `i-sc-S{N}-goldDefine-b1` |
| patternLibrary | `i-sc-S{N}-patternLib-b1` |
| blueprintQG | `i-sc-S{N}-blueprintQG-b1` |
| cleanCodeSlice | `i-sc-{SLICE}-cleanCode-b1` |
| tddRed/Green/etc. | `i-sc-{SLICE}-tddRed-i{N}` |
| verify | `i-sc-{SLICE}-verify-b1` |
| fanIn | `i-sc-{SLICE}-fanIn-b1` |

---

## INVARIANTEN

- I-1: KEIN Custom-Prompt. Nur Template-Variablen befuellen.
- I-2: WORKTREE_PATH und FEATURE_ID kommen aus Phase-1-Output (teamSetup).
- I-3: BATCH_NUM und TASK_ID kommen aus Phase-3-Steuerung (Team Lead).
- I-4: Template-Struktur unveraenderlich — keine Abschnitte hinzufuegen oder entfernen.
- I-5: Agent-Name folgt exakt der Naming-Tabelle — kein freies Benennen.

---

## ARCH-37: KURZLEBIG_PROMPT und Stateless-Spannung

> **Dokumentiert (ARCH-37, BL-153):** KURZLEBIG_PROMPT uebertraegt polier_kontext
> (Pattern-Direktiven) an Sub-Agents. Diese "Injektion" verletzt konzeptuell das
> Stateless-Prinzip: Agents sollten ihren Kontext selbst aus Vault/Command laden.

### Mechanismus-Erklaerung

```
KURZLEBIG_PROMPT injiziert polier_kontext in den Agent-Spawn-Prompt.
Der Agent liest: polier_kontext = lies KURZLEBIG_PROMPT → polier_kontext ?? null

Warum KEIN reines Stateless-Pattern:
- Der Agent koennte polier_kontext auch aus dem Manifest lesen (Vault-Pull-Pattern).
- KURZLEBIG_PROMPT ist ein Push-Mechanismus (Team Lead schreibt, Agent liest passiv).
- Vorteil: Kein extra Vault-Lookup im Agent noetig, Context-Budget gespart.
- Nachteil: Agent-Behavior haengt von Prompt-Inhalt ab, nicht nur vom Command.
```

### Akzeptierter Trade-off (ARCH-37-Entscheidung)

```
AKZEPTIERT: KURZLEBIG_PROMPT-Push als pragmatischer Mechanismus fuer polier_kontext.

Begründung:
1. polier_kontext ist READ-ONLY im Agent — kein State-Write via KURZLEBIG_PROMPT.
2. NON-BLOCKING-Design: polier_kontext=null = normaler Lauf ohne Pattern-Direktive.
3. Vault-Pull-Alternative wuerde refactorCode + refactorTests zu extra Manifest-Reads
   zwingen — mehr Komplexitaet als der aktuelle Push-Ansatz.

Marker fuer zukuenftigen Review:
  KURZLEBIG_STATELESS_REVIEW: wenn Vault-Pull-Infrastruktur verfuegbar → polier_kontext
  als BERATER_OUTPUTS.polierKontext ins Manifest schreiben + Agents lesen von dort.
  Trigger: Wenn KURZLEBIG_PROMPT mehr als 2 Felder uebermittelt → Refactor-Signal.
```

### Symmetrie-Invariante (ARCH-33-Konsequenz)

```
REGEL: Wenn Team Lead polier_kontext in EINEN Refactor-Agent injiziert
       MUSS es auch in den anderen injiziert werden.
refactorCode erhält polier_kontext ↔ refactorTests erhält polier_kontext (PFLICHT-Symmetrie)
Cross-Check via Schritt 0.6 in beiden Commands (ARCH-33).
```
