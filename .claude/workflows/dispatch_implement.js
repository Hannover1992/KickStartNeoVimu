export const meta = {
  name: 'dispatch_implement',
  description: 'Deterministischer Dispatch-Motor (BL-222 + FIX2/BL-210): SDF Implement-Inner-Loop als Workflow. Pro Sub-Batch: modusEntscheidung -> patternBrief -> Stage-Loop[FLAT-SEQUENCE je 1 agent/Sub-Skill -> stageElevation -> Branch] -> Phase 3.x NUR @BATCH_DONE -> loopDecision -> Loop. Engine erzwingt 1-Step=1-agent => Mega-Worker strukturell unmoeglich. Lead startet, Engine konsumiert Signale deterministisch (kein Lead-vergisst-Phase-3).',
  phases: [
    { title: 'Modus' },
    { title: 'PatternBrief' },
    { title: 'Implement' },
    { title: 'Elevate' },
    { title: 'BatchClose' },
    { title: 'LoopDecision' },
  ],
}

// ===========================================================================
// ARGS (vom Lead/Pre-SDF uebergeben — Workflow-Skript hat KEINEN FS-Zugriff,
// daher liest Pre-SDF den Plan aus dem Manifest und reicht ihn hier herein):
//   {
//     bl_id, name, vault, working_dir,
//     difficulty, ceiling, floor,
//     sub_batches: [ { id, items: [..], stages: [1,3,6], coverage_stages?: [1,3] } ],
//        // stages = geplante Test-Stufen; coverage_stages (L4/BL-232, OPTIONAL) = die aus der
//        // coverage_map (IDF Phase 7.7) abgeleiteten Stufen-mit-Tests. Pre-SDF befuellt es aus
//        // DF_BATCH_STATE.coverage_per_batch[sb.id].stages_with_tests; fehlt es -> Fallback stages.
//     max_subbatch_rounds, max_stage_iters                       // optionale Caps
//   }
// RETURN: { sub_batch_results: [...], terminated_reason, agent_spawns }
// ===========================================================================
let A = (typeof args !== 'undefined' && args) ? args : {}
// Defensive (2026-05-30 BL-226-Lauf): manche Caller reichen args als JSON-STRING statt
// Objekt (Workflow-Tool-Stringify-Falle) -> A.sub_batches waere undefined -> no_sub_batches.
// Parse defensiv, damit der Motor sowohl Objekt- als auch String-args akzeptiert.
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
const BL = A.bl_id || A.name || '<bl>'
const NAME = A.name || A.bl_id || '<name>'
const VAULT = A.vault || ''
const WD = A.working_dir || A.vault || ''
const DIFF = A.difficulty || 'normal'
const CEIL = A.ceiling || 'opus'
const FLOOR = A.floor || 'sonnet'
const SUB_BATCHES = Array.isArray(A.sub_batches) ? A.sub_batches : []
const MAX_SUBBATCH_ROUNDS = A.max_subbatch_rounds || 12   // Outer-Loop-Cap
const MAX_STAGE_ITERS = A.max_stage_iters || 15           // Inner-Loop-Cap (C-B3: harter Lead-Iterations-Cap)
const MAX_RECALC_ROUNDS = A.max_recalc_rounds || 8        // BL-238 AK-9: Cross-Round-Recalc-Cap (SC-Saettigungs-runPhase3 pro Sub-Batch)

const CTX = `BL=${BL} name=${NAME} vault=${VAULT} working_dir=${WD}`
const PATHS = `Vault-Root=${VAULT}  Per-BL-Manifest=${WD}/_manifest.md  (IMMER absolute Pfade, NIE das Literal "bl_folder")`

// FLAT-SEQUENCE (verbatim _I_orchestrate.md Z53-89). Jeder Eintrag = 1 agent() = 1 Sub-Skill-Load.
// Bedingte Steps (setup/teardown/monitor) werden im Stage-Loop modus-/stage-abhaengig eingewoben.
// BL-231/BL-232 (2026-05-30): _I_testSearch ENTFERNT — Test-Coverage wird jetzt zu PLAN-Zeit in
// IDF Phase 7.7 (_IDF_berater_testSearch) ermittelt (coverage_map, entscheidet Modus + Stages).
// Die Implement-Worker LESEN die persistierte coverage_map (covering_tests) statt neu zu suchen.
// BL-238 MOTOR-FIX (2026-06-03, RCA B-2-Stall): _I_mitose ENTFERNT. Kanonisch ist Step 8
// "_I_mitose + _I_fanOut" ein PAAR (Worktree erzeugen + befuellen, _I_orchestrate.md Z28). Der Motor
// nahm nur _I_mitose und droppte _I_fanOut -> _I_mitose erzeugte einen Git-Worktree (z.B.
// OmniCommand-BL-238_B-2), den nichts befuellte/aktivierte -> dangling. Die Post-mitose-Steps (TDD/verify)
// liefen ins Leere (kein Handover-State) -> stageElevation RED -> stage_abort (B-2 2x identisch).
// Der Motor laeuft SEQUENTIELL (fanout=1, Batch-as-Slice/slicing=false) -> Worktree-Isolation (fuer
// PARALLELE Slices gedacht) ist hier weder noetig noch korrekt. Code-Emit erfolgt via _TDD_green im
// Mothership; Closure (_I_verify/_I_fanIn, graceful ohne Worktree) schreibt das Handover. Darum: kein
// _I_mitose im sequentiellen Motor. (B-1 lief nur DESHALB durch, weil sein dangling Worktree zufaellig
// harmlos blieb + Code im Mothership landete; B-2 stiess auf die Worktree-Verwirrung.)
const BLUEPRINT_STEPS = [
  '_I_cleanCodeArchitect', '_I_requirementCheck', '_I_patternLibrary',
  '_I_goldDefine', '_I_blueprintQG', '_I_cleanCodeSlice',
]
// BL-319 AK-2 (Idempotenz-Vertrag fuer die Blueprint-Write-Trias): die Steps, die Slice/Gold/QG-Artefakte
// SCHREIBEN, muessen keyed-Overwrite auf (sb.id,stage) statt blind-append fahren — sonst re-nummeriert ein
// 2x-Lauf die Slices oder haengt einen zweiten Gold/QG-Block an. Rein additive Prompt-Haertung.
const BLUEPRINT_IDEM_EXTRA = {
  '_I_cleanCodeSlice': 'BL-319 AK-2 KEYED-OVERWRITE (Idempotenz): schreibe die Slice-Artefakte keyed auf (Sub-Batch,Stage) — '
    + 'KEIN Re-Nummerieren und KEIN Append eines zweiten Slice-Satzes bei 2x-Lauf; bestehende Slices fuer diesen (sb.id,stage) ueberschreiben statt duplizieren.',
  '_I_goldDefine': 'BL-319 AK-2 KEYED-OVERWRITE (Idempotenz): schreibe die Gold-Definition keyed auf (Sub-Batch,Stage) — '
    + 'kein Append/Re-Nummerieren bei 2x-Lauf, bestehende Gold-Definition fuer diesen Slot ueberschreiben statt duplizieren.',
  '_I_blueprintQG': 'BL-319 AK-2 KEYED-OVERWRITE (Idempotenz): schreibe das Blueprint-QG-Verdikt keyed auf (Sub-Batch,Stage) — '
    + 'kein Append eines zweiten QG-Blocks bei 2x-Lauf, bestehendes Verdikt fuer diesen Slot ueberschreiben statt duplizieren.',
}
// TDD-Strom (Steps 9-18). _TDD_setup (9b) + _TDD_teardown (18b) sind BEDINGT
// (stage_N.infrastruktur != none) — der TDD-init-Agent meldet zurueck ob Infra noetig ist.
const TDD_CORE = [
  '_TDD_init', '_TDD_red', '_TDD_execute', '_TDD_green', '_TDD_execute',
  '_TDD_refactorCode', '_TDD_execute', '_TDD_refactorTests', '_TDD_execute', '_TDD_check',
]
// BL-319 AK-2 (Idempotenz-Vertrag pro TDD-Step): additive Instruktion an den jeweiligen Step-Agent,
// damit ein 2x-Lauf (Resume/Replay) keinen Doppel-Eintrag / kein Drift / keine destruktive Re-Aktion
// erzeugt. Rein additive Prompt-Haertung — keine Control-Flow-Aenderung. Wird in der TDD_CORE-Schleife
// als `extra` eingewoben (Step-Label -> Instruktion).
const TDD_IDEM_EXTRA = {
  '_TDD_red': 'BL-319 AK-2 APPEND-DEDUP (Idempotenz): trage neue Test-Dateien in TDD-STATE.tests_written append-if-not-present ein — '
    + 'Datei-Pfad als Key, keyed-upsert; ein bei 2x-Lauf bereits enthaltener tests_written-Eintrag wird NICHT erneut angehaengt (kein Doppel-Eintrag). '
    + 'Nur wenn die Datei noch nicht gelistet ist: anhaengen.',
  '_TDD_refactorCode': 'BL-319 AK-2 SKIP-WENN-BEREITS (Idempotenz): pruefe ZUERST den Zustand der Zieldatei — wenn der Code bereits generisch/refactored ist '
    + '(die geplante Generalisierung schon umgesetzt), SKIP den Refactor (No-Op, idempotent bei 2x-Lauf) statt ihn erneut anzuwenden. Zustand pruefen vor Edit.',
  '_TDD_check': 'BL-319 AK-2 GOLD-FLAG KEYED-UPSERT (Idempotenz): schreibe das GOLD-Erreicht-Flag keyed-upsert auf (' /* sb.id/stage werden im Aufrufer ergaenzt */
    + 'Sub-Batch,Stage) — nur wenn der GOLD-Status fuer diesen Slot noch nicht gesetzt ist (kein Append des GOLD-Status bei 2x-Lauf).',
}
const CLOSURE_STEPS = ['_I_verify', '_I_fanIn']

// Modus -> wie der Implement-Step ausgefuehrt wird.
//   I-Strom (M1/M2/M3): FLAT-SEQUENCE als Einzel-agents (Mega-Worker unmoeglich).
//   SC (M4-M7): 1 agent laedt Skill(_SC_orchestrate) — SC ist selbst Orchestrator mit eigener
//               Loop (verdict-ehrlich: hier ruht Mega-Worker-Schutz auf SC-INV-PM + Hooks, NICHT
//               auf der Step-Zerlegung). M8/M9 sind Sonderpfade ausserhalb des Implement-Kerns.
function modusFamily(m) {
  if (m === 'M1') return 'I_SKELETON'
  if (m === 'M2' || m === 'M3') return 'I_FULL'
  if (m === 'M4' || m === 'M5' || m === 'M6' || m === 'M7') return 'SC'
  return 'SPECIAL' // M8/M9
}

// BL-276: verify_mode-Taxonomie. Diskriminator = "kann das Ziel-Artefakt einen automatisierten RED-Zustand
// annehmen?" — NICHT Sprach-naiv, sondern Datei-/Artefakt-Faehigkeit zum RED. Quelle der Wahrheit ist der Plan
// (sb.verify_mode, von IDF Phase 7.7 / _SDF_berater_stagePlanner gesetzt, AK-S4); der Motor leitet nur als
// Fallback aus den Ziel-Datei-Endungen ab (forward-compat fuer Pre-BL-276-Plaene). Den Vault-Meta-Override
// (stage_N.md / meta-overrides, AK-S7) liest der Plan-Producer ein — der agnostische Motor hartkodiert NUR
// den generischen RED-Faehigkeits-Default (kein projekt-spezifisches Mapping).
const VERIFY_MODE_BY_EXT = {
  // tdd = automatisierter RED moeglich (Test-Harness schlaegt ohne Impl fehl)
  '.py':'tdd', '.cs':'tdd', '.ts':'tdd', '.tsx':'tdd', '.js':'tdd', '.jsx':'tdd', '.java':'tdd',
  '.go':'tdd', '.rb':'tdd', '.php':'tdd', '.kt':'tdd', '.rs':'tdd', '.cpp':'tdd', '.c':'tdd',
  // scenario = Doku/Prosa, kein failing-test-RED -> Bootstrap-Direkt + Szenario-A/B-Verify
  '.md':'scenario', '.txt':'scenario', '.rst':'scenario', '.adoc':'scenario',
  // convention = strukturiert, Schema/Lint-/Struktur-Check statt Test
  '.json':'convention', '.yaml':'convention', '.yml':'convention', '.toml':'convention',
  '.xml':'convention', '.ini':'convention', '.cfg':'convention', '.csv':'convention',
}
function extOf(p) { const s = String(p); const i = s.lastIndexOf('.'); return i < 0 ? '' : s.slice(i).toLowerCase() }
function deriveVerifyMode(sb) {
  // 1) Plan-Wahrheit gewinnt (stagePlanner/IDF Phase 7.7, AK-S4) — homogen pro Sub-Batch erwartet.
  if (sb && typeof sb.verify_mode === 'string' && ['tdd','scenario','convention'].includes(sb.verify_mode)) {
    return { mode: sb.verify_mode, source: 'plan' }
  }
  // 2) Fallback-Diskriminator aus den Ziel-Datei-Endungen der Items (forward-compat).
  const items = Array.isArray(sb && sb.items) ? sb.items : []
  const modes = items.map(it => VERIFY_MODE_BY_EXT[extOf(it)]).filter(Boolean)
  if (modes.length === 0) return { mode: 'tdd', source: 'default' }  // unbekannt -> bestehendes Verhalten
  const uniq = Array.from(new Set(modes))
  if (uniq.length === 1) return { mode: uniq[0], source: 'derived' }
  // 3) Heterogen (J12 .py + J13 .md im selben Sub-Batch = der BL-276-Anlassfall): tdd-Pfad fahren (sicher fuer
  //    die tdd-Items), aber sichtbar machen — stagePlanner SOLL nach verify_mode homogen splitten (AK-S4).
  return { mode: 'tdd', source: 'mixed', mixed: uniq }
}

function subSkillPrompt(skill, sb, stage, extra) {
  return `Lade als ERSTE Aktion Skill(${skill}) und fuehre AUSSCHLIESSLICH diesen einen Pipeline-Schritt aus `
    + `(INV-SPAWN: 1 Worker = 1 Phase, danach STIRBST du — KEINE Folge-Spawns, KEIN Self-Assign weiterer Steps).\n`
    + `Kontext: ${CTX} | Sub-Batch=${sb.id} items=${JSON.stringify(sb.items)} Stage=${stage}.\n`
    + `Pfade: ${PATHS}.\n`
    + (extra ? extra + '\n' : '')
    + `Gib am Ende eine kompakte Status-Zeile zurueck: "STEP ${skill} stage=${stage}: <done|partial|failed> — <1 Satz>".`
}

const DECISION_NOTE = 'Reiner Decision-Berater (INV-STAGE-ELEV-5 / loopDecision): NUR Manifest lesen+schreiben, KEIN Skill() weiter, KEIN Code.'

const MODUS_SCHEMA = {
  type: 'object',
  properties: {
    modus: { type: 'string', enum: ['M1','M2','M3','M4','M5','M6','M7','M8','M9'] },
    modus_begruendung: { type: 'string' },
    // BL-279 Mitose-Zwang: true wenn der Sub-Batch re-cut MUSS (k_max >= hard_threshold ODER verify_mode-
    // Heterogenitaet). Der Motor baut dann NICHT, sondern RETURNED loop_decision=RE-BATCH an den Lead (INV-MOTOR-2).
    split_required: { type: ['boolean','null'] },
    split_reason: { type: ['string','null'] },
  },
  required: ['modus', 'modus_begruendung'],
}
const ELEV_SCHEMA = {
  type: 'object',
  properties: {
    next_action: { type: 'string', enum: ['ELEVATE','BATCH_DONE','RETRY','ABORT','HALT'] },
    current_stage_outcome: { type: 'string', enum: ['GREEN','PARTIAL','RED','PAUSED'] },
    next_stage: { type: ['integer','null'] },
    rationale: { type: 'string' },
  },
  required: ['next_action', 'current_stage_outcome'],
}
const LOOP_SCHEMA = {
  type: 'object',
  properties: {
    decision: { type: 'string', enum: ['ROLLBACK','TERMINATE','SOFT-REPRIO','RE-BATCH'] },
    reason: { type: 'string' },
  },
  required: ['decision'],
}
// BL-262 AK-S2: Resume-Preflight — erkennt einen gebauten-aber-nicht-finalisierten Sub-Batch (BL-242-batch_2-Fall:
// Code+Tests gruen, aber Phase-3.x/completed_sub_batches nie gelaufen → der TDD-Loop kann kein RED erzeugen → spurious
// stage_abort, ganzer Sub-Batch neu, ~4M Token). all_done=true → Build SKIP, direkt Phase 3.x (Finalisierung).
const PREFLIGHT_SCHEMA = {
  type: 'object',
  properties: {
    all_done: { type: 'boolean' },
    completed_stages: { type: 'array', items: { type: 'integer' } },
    note: { type: 'string' },
  },
  required: ['all_done'],
}

// ── BL-228 F-MOTOR-SCHEMA-CRASH-FATAL Härtung (2026-05-30, DCSRE-486 Round-18 Live-Crash 3×) ──
// Die schema-erzwungenen Decision-Agenten (modusEntscheidung/stageElevation/loopDecision) werfen einen
// HARTEN Workflow-Throw "agent({schema}): subagent completed without calling StructuredOutput (after 2
// nudges)", sobald der Sub-Agent kein StructuredOutput emittiert — Session-Limit, Non-Compliance, oder
// Schema-Mismatch. Das machte den ganzen Motor 3× unbenutzbar. safeSchemaAgent fängt das ab:
//   1. Normaler schema-erzwungener Call (Happy-Path unveraendert).
//   2. Bei Throw: schemaloser Retry mit explizitem JSON-Auftrag + Parse (haelt den haeufigen Non-
//      Compliance-Fall ab, ohne den Workflow zu killen).
//   3. Session-Limit erkannt → klares SESSION_LIMIT-Signal (graceful, resumebar) statt kryptischem Crash.
//   4. Doppel-Fehler → sicherer Fallback (kein faken: ABORT/TERMINATE/M2-degraded mit Begruendung).
function extractJson(text) {
  if (!text) return null
  const m = String(text).match(/\{[\s\S]*\}/)   // erstes JSON-Objekt
  if (!m) return null
  try { return JSON.parse(m[0]) } catch (e) { return null }
}
function isSessionLimit(text) {
  return /session limit|hit your (usage|session|account) limit|resets \d|rate.?limit/i.test(String(text || ''))
}
async function safeSchemaAgent(prompt, opts, schemaObj, fallback) {
  try {
    return await agent(prompt, Object.assign({}, opts, { schema: schemaObj }))
  } catch (e) {
    log(`[dispatch_implement] WARN schema-agent ${opts.label} crashed (${String(e && e.message || e).slice(0, 90)}) — schemaloser Retry (F-MOTOR-SCHEMA-CRASH Härtung)`)
    const keys = Object.keys(schemaObj.properties || {}).join(', ')
    const raw = await agent(prompt + `\n\nWICHTIG: Gib AUSSCHLIESSLICH ein einziges valides JSON-Objekt zurueck mit den Feldern {${keys}}. KEIN Fliesstext, KEIN Markdown, KEINE Code-Fences — nur das rohe JSON.`, opts)
    if (isSessionLimit(raw)) {
      throw new Error('SESSION_LIMIT: Decision-Agent traf das Account-/Session-Limit. Motor pausiert GRACEFUL — spaeter resumen (modusEntscheidung/patternBrief sind idempotent gegen das Manifest, kein Daten-Verlust).')
    }
    const parsed = extractJson(raw)
    if (parsed) { log(`[dispatch_implement] schemaloser Retry OK fuer ${opts.label}`); return parsed }
    log(`[dispatch_implement] WARN ${opts.label}: Retry-Parse fehlgeschlagen → sicherer Fallback ${JSON.stringify(fallback)}`)
    return fallback
  }
}

// BL-303 L1 (Consumer-Wiring): erkennt den unautorisierten Gruen-Schutz-Konflikt im _TDD_green-Return.
// Heute (vor L1) wurde ein Green-Agent-Refusal still verschluckt -> downstream als GREEN (false BATCH_DONE)
// ODER als RED (fail-safe ABORT) fehlgelesen = der tote Pfad (wn17ougl9-Befund). parseTestConflict macht
// das Signal maschinenlesbar, damit der Motor es VOR stageElevation deterministisch konsumiert.
function parseTestConflict(text) {
  const s = String(text || '')
  if (!/GREEN_BLOCKED_TEST_CONFLICT/.test(s)) return null
  const j = extractJson(s)
  return (j && (j.item || j.asserting_test || j.finding_premise)) ? j : { item: '(unspezifiziert)', note: 'Marker ohne strukturiertes JSON' }
}

// ── BL-329 (M2-Infra-Luecke, Motor-AK-1) — INV-INFRA-MODUS-FREI ────────────────────────────────
// Ob eine Stage Infra braucht, ist eine STAGE-Eigenschaft (stage_N.md setup./teardown./health_check),
// NICHT eine Modus-Eigenschaft. tdd=true/false steuert die Red/Refactor-Ceremony — NICHT ob
// Container/WebHost hochfahren. Vor BL-329 lebte der Infra-Konsum NUR im M3/tdd-Zweig (vorbildlich):
// _TDD_init -> needInfra -> _TDD_setup (9b) + _TDD_teardown (18b, finally). Der M2-Zweig hatte KEINEN
// Maschinen-Step — nur einen Prompt-Satz ("Bei Stage>=3 mit Infra: stage_N-Setup beachten") =
// machine-not-context woertlich (Live-Schmerz 1944-Stage-6: improvisierter WebHost-Start, Serilog-Crash).
// Diese drei Helper heben Infra-Detektion + Setup/Teardown auf die MODUS-UNABHAENGIGE Ebene (gemeinsam
// fuer M2 + M3). _TDD_setup/_TDD_teardown sind selbst-guardend (INV-SETUP-6 / INV-TEARDOWN-5 Auto-SKIP
// bei infrastruktur=none + leere commands), aber der Motor entscheidet aus dem _TDD_init-INFRA-Signal,
// ob ueberhaupt ein Setup/Teardown-Worker gespawnt wird (1 agent = 1 Step, INV-MOTOR-1).

// Infra-Bedarf der Stage detektieren (1 agent = _TDD_init). Quelle des needInfra-Signals fuer BEIDE
// I_FULL-Modi (M2 + M3, non-scenario). Gibt true zurueck, wenn die geplante Stage Infra braucht.
async function detectInfraNeed(sb, stage) {
  const initRes = await agent(subSkillPrompt('_TDD_init', sb, stage,
    'Melde am Ende explizit: "INFRA=true" wenn stage_' + stage + '.infrastruktur != none (Container/DB/WebHost-Spinup noetig) '
    + 'ODER stage_' + stage + '.setup.commands non-empty, sonst "INFRA=false". '
    + 'INV-INFRA-MODUS-FREI (BL-329): dieser Infra-Bedarf ist eine STAGE-Eigenschaft, MODUS-UNABHAENGIG (gilt auch fuer M2/tdd=false).\n'
    + 'BL-319 AK-2 RE-INIT-SCHUTZ (Idempotenz): TDD-STATE-Eintraege keyed-upsert auf (' + JSON.stringify(sb.id) + ',Stage ' + stage + ') schreiben — '
    + 'einen bereits vorhandenen Sub-Batch-Slot NICHT neu anlegen und NICHT mit frischen Defaults ueberschreiben (kein Overwrite frischer Sub-Batch-Daten bei 2x-Lauf). '
    + 'Existiert der Slot bereits: bestehende Werte beibehalten (upsert), nur fehlende Felder ergaenzen.'),
    { label: `_TDD_init:${sb.id}.s${stage}`, phase: 'Implement' })
  return /INFRA\s*=\s*true/i.test(initRes || '')
}

// Step 9b: _TDD_setup (1x pro Stage, idempotent). MODUS-UNABHAENGIG (BL-329 INV-INFRA-MODUS-FREI).
//
// BL-486 C-FIX (DoD-6) — ACQUIRE-VOR-SPINUP-ENFORCEMENT (verdrahtet):
// VOR dem Container/DB/WebHost-Spinup unten MUSS der Setup-Step die unteilbaren Stage-Ressourcen
// via guard_stage_acquire_enforce.enforce_stage_acquire(resource_ids, worker_id=..., timeout=...)
// acquiren. Rueckgabe False (HALT, Timeout/belegte unteilbare Ressource) => KEIN Spinup (return);
// nur bei True (alle Ressourcen acquiriert) darf der eigentliche Spinup laufen. Der Teardown am
// Stage-Ende (Step 18b runInfraTeardown) gibt die Ressourcen ueber den bei acquire registrierten
// teardown_callback (resource_allocator.register_teardown_hook) wieder frei. Substrat:
// .claude/scripts/guard_stage_acquire_enforce.py (Python, via pytest geprueft); der Setup-Worker
// ruft es als thin subprocess/Funktions-Call BEFORE dem Spinup auf (acquire-before-spinup-Gate).
async function runInfraSetup(sb, stage) {
  await agent(subSkillPrompt('_TDD_setup', sb, stage,
    'Container/DB/WebHost-Spinup (BL-NEW-53). Lies stage_' + stage + '.md setup.commands + health_check und fuehre sie aus '
    + '(INV-SETUP-1: NUR Commands aus stage_N.md, keine eigenen erfinden). INV-INFRA-MODUS-FREI (BL-329): laeuft modus-unabhaengig (auch M2).\n'
    + 'BL-486 C-FIX (DoD-6) ACQUIRE-VOR-SPINUP: BEVOR du Container/DB/WebHost spinupst, acquire die unteilbaren '
    + 'Stage-Ressourcen via guard_stage_acquire_enforce.enforce_stage_acquire(...) (resource_allocator.acquire_all-Retry). '
    + 'Liefert es False (HALT/Timeout, Ressource belegt): KEIN Spinup — halten/warten statt blind starten. Nur bei True spinup.\n'
    + 'BL-319 AK-2 SPINUP-GUARD (verifizierte Idempotenz, BL-230 Z86): spinup-if-not-running — pruefe ZUERST ob Container/DB/WebHost '
    + 'BEREITS laeuft (docker ps / Port-Probe / Health-Check); wenn bereits laeuft: KEIN zweiter Spinup, nur den laufenden Stand verifiziert wiederverwenden. '
    + 'Die Idempotenz ist VERIFIZIERT (Running-State geprueft), nicht bloss behauptet.'),
    { label: `_TDD_setup:${sb.id}.s${stage}`, phase: 'Implement' })
}

// Step 18b: _TDD_teardown — finally-Semantik (auch bei ABORT), best-effort (BL-NEW-53).
// MODUS-UNABHAENGIG (BL-329 INV-INFRA-MODUS-FREI): laeuft fuer jeden Modus, der Setup gefahren hat.
async function runInfraTeardown(sb, stage) {
  await agent(subSkillPrompt('_TDD_teardown', sb, stage,
    'Container/Process-Cleanup, always-run (auch bei ABORT), best-effort (INV-TEARDOWN-3 finally-Semantik). '
    + 'Kille captured PIDs + stoppe Container aus TDD-STATE.setup_artifacts (INV-TEARDOWN-2 reverse-order). INV-INFRA-MODUS-FREI (BL-329).\n'
    + 'BL-319 AK-2 NO-OP-BEI-BEREITS-DOWN (Idempotenz): pruefe ZUERST ob Container/Process bereits down ist; wenn bereits down: '
    + 'sauberer No-Op (kein Fehler, keine Doppel-Aktion bei 2x-Lauf) statt eines fehlschlagenden Stop/Remove auf nicht-existentem Ziel.'),
    { label: `_TDD_teardown:${sb.id}.s${stage}`, phase: 'Implement' })
}

// Eine Stage komplett fahren: FLAT-SEQUENCE als Einzel-agents (sequentiell, je 1 Sub-Skill).
async function runImplementStage(sb, stage, modus, fam) {
  const tdd = (modus === 'M3' || modus === 'M6')
  if (fam === 'I_SKELETON') {
    // M1: 1 deterministischer Step — _I_orchestrate --scope=skeleton (Bare-Minimum-Subset, BL-174/BL-212).
    await agent(subSkillPrompt('_I_orchestrate', sb, stage,
      'Argumente: --worker-mode --scope=skeleton --batch=' + sb.items.join(',') + ' --stage=' + stage + ' --tdd=false --vault=' + VAULT
      + '\nWICHTIG (B3 / INV-MODUS-7 Neufassung): chaine NICHT Skill(_SDF_orchestrate_post) — der Motor ruft Phase 3.x NUR @BATCH_DONE selbst. Ein Self-Chain hier = Doppel-Phase-3.x.'),
      { label: `M1-skeleton:${sb.id}.s${stage}`, phase: 'Implement', model: 'sonnet' })
    return
  }
  if (fam === 'SC') {
    // M4-M7: 1 agent = voller SC-Orchestrator (eigene Loop). Argumente je Modus.
    let scArgs = `${NAME} ${DIFF} ${CEIL} ${FLOOR} --batch=${sb.items.join(',')} --vault=${VAULT}`
    if (modus === 'M4') scArgs = `${NAME} ${DIFF} ${CEIL} ${FLOOR} -I --batch=${sb.items.join(',')} --vault=${VAULT}`
    if (modus === 'M7') scArgs = `${NAME} ${DIFF} ${CEIL} ${FLOOR} --mode=analyse --batch=${sb.items.join(',')} --vault=${VAULT}`
    const scRes = await agent(subSkillPrompt('_SC_orchestrate', sb, stage, 'Argumente: ' + scArgs
      + (modus === 'M6' ? '\nHINWEIS M6: _session_params.tdd=true ist gesetzt (TDD aktiv).' : '')
      + '\nWICHTIG (B3 / INV-MODUS-7 Neufassung): chaine NICHT Skill(_SDF_orchestrate_post) — der Motor ruft Phase 3.x NUR @BATCH_DONE selbst. Ein Self-Chain hier = Doppel-Phase-3.x.'
      + '\nBL-238 AK-7: melde am Ende explizit den geschriebenen SC_PIPELINE_STATE.sc_verdict-Wert '
      + '(SATURATED_READY_FOR_IMPL | EXPERIMENT_OPEN | ABORT) — der Motor liest ihn fuer den runPhase3-Trigger (AK-1).'),
      { label: `${modus}-SC:${sb.id}.s${stage}`, phase: 'Implement' })
    // BL-238 AK-1: sc_verdict aus dem SC-Return extrahieren (Producer _SC_orchestrate.md schrieb ihn
    // in SC_PIPELINE_STATE am Phase-5-Exit). Konsumiert wird er in der Hauptschleife (Branch NEBEN BATCH_DONE).
    const scVerdict = /\bSATURATED_READY_FOR_IMPL\b/.test(scRes || '') ? 'SATURATED_READY_FOR_IMPL'
      : /\bEXPERIMENT_OPEN\b/.test(scRes || '') ? 'EXPERIMENT_OPEN'
      : /\bABORT\b/.test(scRes || '') ? 'ABORT'
      : null
    return { sc_verdict: scVerdict }
  }
  // I_FULL (M2/M3): Blueprint -> [TDD wenn tdd] -> Closure, je 1 agent pro Sub-Skill.
  // M2-1 (BL-232): _I_goldDefine ist fuer M2 redundant — der "Gold-Standard" sind die BESTEHENDEN
  // covering_tests aus der coverage_map (IDF Phase 7.7, batch_coverage_verdict=covered). Nur M3
  // (test-first/greenfield, uncovered) definiert Gold neu. Blueprint bleibt sonst voll (User-Direktive
  // 2026-05-30: "wir aendern Code, klar brauchen wir Blueprint" — nur goldDefine faellt fuer M2).
  // BL-276 verify_mode-Weiche: scenario/convention-Artefakte (Markdown/Config) koennen KEINEN automatisierten
  // RED annehmen -> _TDD_red/green/execute waere ein Kategorie-Fehler (J13: _W_fetch.md durch red/green gezwungen,
  // "0 pytest = MISSING"-Fehlalarm 18:23). Statt dessen: Bootstrap-Direkt-Edit + Szenario-/Konventions-Verify.
  const vm = deriveVerifyMode(sb)
  if (vm.source === 'mixed') log(`[dispatch_implement] WARN heterogener Sub-Batch ${sb.id} (verify_mode ${JSON.stringify(vm.mixed)}) — tdd-Pfad gefahren; _SDF_berater_stagePlanner SOLL nach verify_mode homogen splitten (BL-276 AK-S4).`)
  const isScenarioMode = (vm.mode === 'scenario' || vm.mode === 'convention')
  // _I_goldDefine faellt fuer M2 (covering_tests = Gold) UND scenario/convention (kein Test-Gold neu zu definieren).
  const blueprintSteps = (modus === 'M2' || isScenarioMode)
    ? BLUEPRINT_STEPS.filter(s => s !== '_I_goldDefine')
    : BLUEPRINT_STEPS
  for (const sk of blueprintSteps) {
    await agent(subSkillPrompt(sk, sb, stage, BLUEPRINT_IDEM_EXTRA[sk] || ''), { label: `${sk}:${sb.id}.s${stage}`, phase: 'Implement' })
  }
  if (isScenarioMode) {
    // BL-276 Bootstrap-Direkt-Emit: Ziel-Artefakt direkt editieren (kein test-first); Verify folgt in der Closure.
    log(`[dispatch_implement] verify_mode=${vm.mode} (${vm.source}) fuer ${sb.id} -> Bootstrap-Direkt + ${vm.mode === 'scenario' ? 'Szenario-A/B' : 'Konventions'}-Verify (kein _TDD_red/green, BL-276)`)
    await agent(subSkillPrompt('_TDD_green', sb, stage,
      `BL-276 BOOTSTRAP-DIREKT-EMIT (verify_mode=${vm.mode}): Editiere die Ziel-Artefakte direkt gemaess Blueprint/Slice. `
      + `Das Ziel ist ${vm.mode === 'scenario' ? 'eine Doku/Markdown-Datei (kein automatisierter RED-Zustand moeglich)' : 'eine Config/strukturierte Datei (Schema/Struktur statt Test)'} — `
      + `schreibe KEINEN Failing-Test und fahre KEIN _TDD_red/execute (waere ein Kategorie-Fehler, BL-276). Setze die geplante Aenderung praezise um.`),
      { label: `bootstrap-direkt(${vm.mode}):${sb.id}.s${stage}`, phase: 'Implement' })
  } else {
    // I_FULL non-scenario (M2 + M3): BL-329 INV-INFRA-MODUS-FREI — der Infra-Bedarf ist eine STAGE-
    // Eigenschaft, modus-unabhaengig. _TDD_init detektiert ihn EINMAL (gemeinsame needInfra-Quelle fuer
    // M2 + M3). Vor BL-329 lief _TDD_init nur im tdd-Zweig -> M2 bekam nie ein needInfra-Signal und nie
    // Setup/Teardown (nur einen Prompt-Satz; machine-not-context, 1944-Stage-6-Schmerz). Jetzt klammern
    // setup (Step 9b) VOR und teardown (Step 18b, finally/ABORT-sicher) NACH dem modus-spezifischen Kern.
    const needInfra = await detectInfraNeed(sb, stage)
    // Step 9b: _TDD_setup — modus-unabhaengig, sobald die Stage Infra braucht (Container/DB/WebHost-Spinup).
    if (needInfra) await runInfraSetup(sb, stage)
    try {
      if (tdd) {
        // M3/M6: voller TDD-Strom. _TDD_init schon gefahren (detectInfraNeed) -> TDD_CORE ab _TDD_red.
        for (const sk of TDD_CORE.slice(1)) {  // _TDD_init schon gefahren (detectInfraNeed, oben)
          let extra = TDD_IDEM_EXTRA[sk] || ''
          if (sk === '_TDD_execute') {
            // BL-261 (Wurzel-Fix): _TDD_execute MUSS die Test-Artefakte des AKTUELLEN Sub-Batches fahren — NICHT
            // nur das stage-eingefrorene testbefehl (das oft nur batch_1s Datei trifft). Live-Defekt BL-242 batch_2:
            // _TDD_execute fuhr batch_1s Suite -> 16/16 GRUEN bei expected=RED -> spurious RED->ABORT (4M Token).
            extra = `SUB-BATCH-TEST-TARGET (BL-261): Fahre die Test-Artefakte des AKTUELLEN Sub-Batches "${sb.id}" `
              + `— die Dateien aus TDD-STATE.tests_written[].datei, die _TDD_red gerade fuer Sub-Batch "${sb.id}" `
              + `geschrieben hat (Konvention test_{name}_batch{N}.py). Fahre NICHT NUR das stage-eingefrorene testbefehl `
              + `(das trifft oft nur batch_1s Datei und liefert ein False-Negative bei spaeteren Sub-Batches). `
              + `Bei Python/pytest IST diese Sub-Batch-Test-Datei das Test-Ziel (= "FQN" im Sinne BL-NEW-54): bei leerer `
              + `.NET-fqn_list NICHT EXIT-FAIL, sondern das Ziel aus tests_written ableiten und fahren. ZUSAETZLICH die `
              + `Test-Dateien der frueheren Sub-Batches als Kanarienvogel (Regressions-Schutz) mitlaufen lassen.`
            if (needInfra) extra += `\n_TDD_monitor laeuft PARALLEL (BL-NEW-62): beobachte Docker/Parallelism/FQN-Match waehrend der Test-Ausfuehrung.`
          }
          await agent(subSkillPrompt(sk, sb, stage, extra),
            { label: `${sk}:${sb.id}.s${stage}`, phase: 'Implement' })
        }
      } else {
        // M2 (BL-231 Decoupling): emit_code ist ENTKOPPELT von test_first — M2 schreibt Code OHNE Test-First-Ceremony.
        // Wurzel-Fix (nicht nur M2-Flicken): tdd steuert NUR die Red/Refactor-Ceremony, NICHT mehr OB Code entsteht.
        // M2 = Refactor/bekannter Fix; die BESTEHENDEN Tests sind die GREEN-Referenz (_SDF_berater_modusEntscheidung Z516).
        // BL-329: Infra-Setup ist hier OBEN als echter Maschinen-Step (runInfraSetup) gefahren — KEIN Prompt-Satz mehr.
        const m2TestCorrectionAuthorized = sb.test_correction_authorized === true
        const m2TestCorrectionExtra = m2TestCorrectionAuthorized
          ? ('BL-303 TEST-KORREKTUR FREIGABE (test_correction_authorized: true): '
            + 'Dieses Sub-Batch traegt eine autorisierte Test-Assertion-Korrektur. '
            + 'authorization_evidence = ' + (sb.authorization_evidence || '(kein evidence-Text)') + '. '
            + 'Du DARFST die autorisierte Test-Korrektur durchfuehren — '
            + 'der korrigierte Test IST das neue RED dieser Iteration (BL-303). '
            + 'Fuehre AUSSCHLIESSLICH die explizit autorisierte Aenderung durch (kein Scope-Creep). ')
          : ('BL-303 GRUEN-SCHUTZ (Interim-Default, HiL-Fallback): Aendere/entferne KEINE bestehende gruene Test-Assertion. '
            + 'In diesem Build gibt es NOCH KEINE Autorisierung (test_correction_authorized — der Auto-Produzent BL-281/296 ist nicht live). '
            + 'Wuerde deine geplante Aenderung eine bestehende gruene Test-Assertion beruehren, fuehre sie NICHT aus und schreibe AUCH KEINEN Code: '
            + 'melde am Ende EXAKT "GREEN_BLOCKED_TEST_CONFLICT" gefolgt von einem JSON {item, asserting_test, finding_premise, premise_status:"unverified"} (AK-4, KEIN stilles No-Op). '
            + 'Reiner Produktiv-Code OHNE Beruehrung einer bestehenden Assertion: normal weiter.')
        const m2green = await agent(subSkillPrompt('_TDD_green', sb, stage,
          'M2-CODE-EMIT (BL-231, entkoppelt von TDD-Ceremony): Schreibe realen Produktiv-Code/Refactor in die Zieldateien '
          + '(setze die geplante Aenderung aus Blueprint/Slice um). Die BESTEHENDEN Tests sind die GREEN-Referenz — '
          + 'schreibe KEINE neuen Tests (kein red-first), kein Scope-Creep.\n'
          + 'BL-329 INV-INFRA-MODUS-FREI: ein etwaiges Infra-Setup (Container/WebHost) ist BEREITS via _TDD_setup gefahren '
          + '(modus-unabhaengiger Maschinen-Step, KEIN improvisierter Spinup hier) — nutze die laufende Infra, starte selbst KEINE.\n'
          + m2TestCorrectionExtra),
          { label: `_TDD_green(M2):${sb.id}.s${stage}`, phase: 'Implement' })
        const m2conflict = parseTestConflict(m2green)
        if (m2conflict) {
          log(`[dispatch_implement] ${sb.id}.s${stage}: BL-303 GREEN_BLOCKED_TEST_CONFLICT — kein Code/Test-Edit, Short-Circuit VOR _TDD_execute/Closure -> RE-BATCH+HiL an Lead (kein false-GREEN/ABORT).`)
          // BL-329: RETURN aus der try -> der finally-Block fuehrt teardown auch hier aus (Infra-Leak-frei,
          // auch bei Konflikt-Short-Circuit). closure wird wie zuvor uebersprungen (return verlaesst die Funktion).
          return { test_conflict: m2conflict }
        }
        await agent(subSkillPrompt('_TDD_execute', sb, stage,
          'Verifiziere dass die bestehenden Tests nach der M2-Code-Aenderung GREEN bleiben. '
          + 'L4 (BL-232): fuehre GEZIELT die in DF_BATCH_STATE.coverage_per_batch[' + JSON.stringify(sb.id) + ']'
          + '.covering_tests fuer Stage ' + stage + ' gelisteten Tests aus (von IDF Phase 7.7 persistiert) — '
          + 'nicht blind die Voll-Suite. Fehlt die coverage_map (Pre-7.7-Story): Fallback auf relevante Test-Klassen der Zieldateien.'),
          { label: `_TDD_execute(M2):${sb.id}.s${stage}`, phase: 'Implement' })
      }
    } finally {
      // Step 18b: _TDD_teardown — finally-Semantik (auch bei ABORT/Throw/RETURN), best-effort (BL-NEW-53).
      // BL-329 INV-INFRA-MODUS-FREI: laeuft fuer M2 + M3 gleichermassen, sobald Setup gefahren wurde.
      if (needInfra) await runInfraTeardown(sb, stage)
    }
  }
  // Closure. _I_verify ehrt verify_mode (BL-276 AK-S5): scenario/convention NICHT als "0 pytest = MISSING/RED" werten.
  const verifyExtra = isScenarioMode
    ? `BL-276 verify_mode=${vm.mode}: das Ziel ist ein ${vm.mode === 'scenario' ? 'Doku/Markdown' : 'Config/strukturiertes'}-Artefakt OHNE automatisierten RED-Zustand. `
      + `Belege die Korrektheit ueber ${vm.mode === 'scenario' ? 'einen isolierten Szenario-A/B-Durchlauf (A=geaenderter Pfad greift, B=Counterfactual/Gegenfall)' : 'Struktur-/Schema-/Lint-Assertions (valides Format, Pflicht-Felder, Konvention)'} und SETZE das Green-Haekchen (stage_status=done). `
      + `Die Abwesenheit von pytest/dotnet-Tests ist KEIN MISSING/RED fuer dieses Artefakt (BL-276 AK-S5/S6).`
    : ''
  for (const sk of CLOSURE_STEPS) {
    await agent(subSkillPrompt(sk, sb, stage, sk === '_I_verify' ? verifyExtra : ''),
      { label: `${sk}:${sb.id}.s${stage}`, phase: 'Implement' })
  }
}

// Phase 3.x Berater-Bundle — NUR im BATCH_DONE-Pfad (C5). Jeder ist ein eigener agent/Skill-Load.
// (BL-255 AK-7, 2026-06-10: 3.5c-Kollaps für C5 sichtbar — Off-by-one-Fix.) modelSync 3.5c kollabiert
// AK-Confirms + getragene W{n} ERST in Phase 3.5 — der recalibrate-Lauf davor liest also pre-Kollaps-
// W-Status (stale srs; die Senkung wurde erst im UEBERNAECHSTEN Batch modus-wirksam, W33 empirisch).
// KEIN Order-Swap: modelSync LIEST per Vertrag BERATER_OUTPUTS.recalibrate + postBatch der AKTUELLEN
// Round (Promote-Stabilitaets-Kriterien) — Swap wuerde ihm Stale-Inputs der Vorrunde geben. Stattdessen
// bedingter C5-Re-Run NACH modelSync, NUR wenn 3.5c einen nicht-leeren confirm_collapse meldet
// (COLLAPSED_WS>0): +1 agent() im Kollaps-Fall, 0 Kosten im No-Op-Fall. Kein Berater entfernt/geskippt
// (geist9-Quartett intakt); metric_per_batch ist danach post-Kollaps-frisch fuer Re-Modus (PT-CMD-017).
function parseCollapsedWs(text) {
  const m = String(text || '').match(/COLLAPSED_WS\s*=\s*(\d+)/i)
  return m ? parseInt(m[1], 10) : 0
}
async function runPhase3(sb) {
  await agent(`Lade Skill(_SDF_berater_recalibrate) und fuehre Phase 3.1 (K-Score-Update) fuer Sub-Batch ${sb.id} aus. ${CTX}. ${PATHS}\n`
    + `BL-319 AK-2 PERSISTENTER PHASE3-GUARD (Idempotenz): verankere den phase3_fired-Guard fuer ${JSON.stringify(sb.id)} PERSISTENT im Manifest `
    + `(DF_BATCH_STATE.phase3_fired_per_batch[${JSON.stringify(sb.id)}]=true) — NICHT als fluechtiges in-memory-Set. Ein Fresh-Replay/Crash-Resume liest den persistenten Guard `
    + `aus dem Manifest und feuert Phase 3.x NICHT erneut (kein Doppel-Feuer); der Guard ueberlebt Crash/Replay.`,
    { label: `recalibrate:${sb.id}`, phase: 'BatchClose' })
  await agent(`Lade Skill(_SDF_berater_postItem) und fuehre Phase 3.2 (GAP-Check) fuer Sub-Batch ${sb.id} aus. ${CTX}. ${PATHS}\n`
    + `BL-319 AK-2 PL-ITEM-DEDUP (Idempotenz): neue PL-Items append-if-not-present mit item-id als Dedup-Key — `
    + `ein bei 2x-Lauf bereits angelegtes PL-Item (gleiche item-id / gleicher Gap-Fingerprint) wird NICHT erneut angelegt (kein Doppel-Eintrag). `
    + `Nur wenn die item-id noch nicht im Parking-Lot existiert: anlegen.`,
    { label: `postItem:${sb.id}`, phase: 'BatchClose' })
  await agent(`Lade Skill(_SDF_berater_statusTransition) und fuehre Phase 3.3 (DONE-Markierung) fuer Sub-Batch ${sb.id} aus. ${CTX}. ${PATHS}\n`
    + `IDEMPOTENT (B3, Audit 2026-05-29): completed_sub_batches.append("${sb.id}") NUR wenn "${sb.id}" noch NICHT enthalten — Schutz gegen Doppel-Phase-3.x (falls ein I/SC-Worker doch _SDF_orchestrate_post self-chained).`,
    { label: `statusTransition:${sb.id}`, phase: 'BatchClose' })
  const msRes = await agent(`Lade Skill(_SDF_berater_modelSync) und fuehre Phase 3.5 (Round-Erkenntnisse -> Model.md/Spec.md, INV-MODUS-6 Persistenz VOR naechster Round) fuer Sub-Batch ${sb.id} aus. ${CTX}. ${PATHS}\n`
    + `BL-255 AK-7 MELDE-PFLICHT: melde am Ende explizit "COLLAPSED_WS=<n>" (confirm_collapse.collapsed_ws aus SCHRITT 3.5c; 0 bei No-Op/keinem verify-Verdikt) — der Motor konsumiert es fuer den bedingten C5-Re-Run.`,
    { label: `modelSync:${sb.id}`, phase: 'BatchClose' })
  const collapsedWs = parseCollapsedWs(msRes)
  if (collapsedWs > 0) {
    log(`[dispatch_implement] ${sb.id}: 3.5c confirm_collapse nicht-leer (COLLAPSED_WS=${collapsedWs}) -> recalibrate-Re-Run, damit der srs-Drop SOFORT modus-wirksam wird (BL-255 AK-7, Off-by-one-Fix).`)
    await agent(`Lade Skill(_SDF_berater_recalibrate) und fuehre Phase 3.1 (K-Score-Update) fuer Sub-Batch ${sb.id} ERNEUT aus — `
      + `Re-Run NACH modelSync 3.5c (BL-255 AK-7): der soeben gelaufene Confirm-Kollaps hat ${collapsedWs} W{n} auf AKTIV (BESTAETIGT) `
      + `transitioniert; recompute srs/k_score auf dem POST-Kollaps-W-Status (BESTAETIGT-Familie -> srs_weight 0.0) und versiegele `
      + `metric_per_batch[${JSON.stringify(sb.id)}] frisch (INV-METRIC-1). Idempotenter Recompute, kein anderer Scope (INV-RECOMPUTE-SCOPE-1). ${CTX}. ${PATHS}`,
      { label: `recalibrate-postCollapse:${sb.id}`, phase: 'BatchClose' })
  }
}

// BL-299 (Regression aus BL-222 Refactor-Truncation): Der Motor hatte KEINEN Commit-/Security-Gate-Step.
// Der kanonische Pipeline-Schwanz _I_fanIn -> _stage_orchestrate war beim BL-222-Motor-Refactor abgeschnitten
// (CLOSURE_STEPS endet bei _I_fanIn; grep _stage_orchestrate im Motor = 0). Das Anti-Leak-Security-Gate
// (Phase 2.3/2.4) lief nur im Skill-Pfad (_SDF_orchestrate_post 3.3.5) -> Commit + Gate hingen an manueller
// Lead-Disziplin (BL-NEW-40-Leak-Klasse; Live 486: 6 gepushte Commits mit internem Prozess-Zeug). Dieser
// Helper spiegelt den Skill-Pfad in den Motor — gerufen an ZWEI Seams: ELEVATE (jede gruene Zwischen-Stage,
// AK-7 Partial-Batch) + BATCH_DONE (finaler Commit nach runPhase3).
// INV-MOTOR-1: 1 agent() laedt Skill(_stage_orchestrate) (analog SC-Fall — eigener Skill mit eigenen Workern,
// kein Mega-Worker). Der Motor hat keinen FS-Zugriff -> Freeze-Read (AK-2) + Security-Gate (AK-3) delegiert.
async function runStageCommit(sb, stage, isBatchDone) {
  await agent(
    `Lade als ERSTE Aktion Skill(_stage_orchestrate) und fuehre AUSSCHLIESSLICH diesen einen Commit-/Security-Gate-Schritt aus `
    + `(INV-SPAWN: 1 Worker = 1 Phase, danach STIRBST du — KEINE Folge-Spawns, KEIN Self-Assign weiterer Pipeline-Schritte).\n`
    + `Kontext: ${CTX} | Sub-Batch=${sb.id} items=${JSON.stringify(sb.items)} Stage=${stage} ${isBatchDone ? '(BATCH_DONE — letzte Stage)' : '(ELEVATE — gruene Zwischen-Stage)'}.\n`
    + `Pfade: ${PATHS}.\n`
    + `BL-319 AK-2 BARRIER (barrier_only / concurrency_class = EXCLUSIVE): dieser Commit-Schritt ist ein Single-Writer-Commit-Seam — `
    + `er darf NIE nebenlaeufig in einer Welle mit anderen Steps laufen (git-Commit-SHA-Drift / verschraenkte Index-Stages). barrier_only=true, exklusiv.\n`
    + `GRAIN (BL-299 AK-1): committe den GRUENEN Zwischenstand dieser Test-Stage als GENAU EINEN kohaerenten Commit `
    + `ueber GANZE Dateien — NICHT Hunk-Level (kein \`git add -p\`), NICHT pro PL-Item (mehrere Items teilen sich dieselben Dateien).\n`
    + `MODUS: dark_factory (autonom, kein HiL) — Security-Verstoesse autonom korrigieren.\n`
    + `AK-2 COMMIT-FREEZE-GATE (KONDITIONAL): Lies das Manifest auf ein aktives Commit-/PR-/Push-Verbot (z.B. "KEIN develop-Push ohne Freigabe"). `
    + `Bei aktivem Freeze: KEINEN Commit, sondern sauberer Handover ("STAGE_COMMIT stage=${stage}: frozen — kein Commit, Handover"). Nie unbedingt committen.\n`
    + `AK-3 SECURITY-GATE (PFLICHT, deterministisch): fahre Phase 2.3 Pruefung 5 (Prozess-Marker BDF/SDF/IDF/BL-NNN/PR-Review/_X_orchestrate) `
    + `+ Phase 2.4/Pruefung 6 (Prozess-Markdown unter 4_Blueprint/6_PL/2_Model/3_Spec/5_Gap/Crumbs/...) — schliesst die BL-NEW-40-Leak-Klasse strukturell.\n`
    + `Gib am Ende zurueck: "STAGE_COMMIT stage=${stage}: <committed sha=...|frozen-handover|gate-fail> — <1 Satz>".`,
    { label: `stageCommit:${sb.id}.s${stage}`, phase: 'BatchClose' })
}

// ===========================================================================
// HAUPTSCHLEIFE — Lead-getriebene Loop, jetzt deterministisch in der Engine.
// ===========================================================================
const results = []
let terminated_reason = 'completed'

if (SUB_BATCHES.length === 0) {
  log('[dispatch_implement] WARN: keine sub_batches in args — nichts zu tun (Pre-SDF muss Plan liefern).')
  return { sub_batch_results: [], terminated_reason: 'no_sub_batches', agent_spawns: 0 }
}

let outerRounds = 0
// BL-238 AK-1 (PT-CMD-007): Idempotenz-Guard fuer den SC-Saettigungs-Trigger. Verhindert
// Doppel-runPhase3 pro Sub-Batch bei Resume/2x-Replay (analog statusTransition-Idempotenz :236).
// BL-230 SB-5 (AK-GUARD-PERSIST, S-GP-1/EC-GP-1/EC-GP-2): das Set startet NICHT mehr nackt-leer,
// sondern wird aus dem PERSISTENTEN Manifest-Marker A.phase3_fired_seed geseedet (vom Pre-SDF aus
// DF_BATCH_STATE.phase3_fired_per_batch[id] gereicht — der Motor hat keinen FS-Zugriff, EC-GP-1).
// Fresh-Replay/Crash-Resume liest den persistenten Marker -> runPhase3 feuert NICHT erneut fuer einen
// bereits ge-feuerten Sub-Batch (kein Doppel-Quartett). EC-GP-2: DERSELBE Key (phase3_fired_per_batch[id])
// wie der Berater-Write in runPhase3 (Z452, BL-319 AK-2) — kein zweiter, divergenter Marker.
// S-GP-3 (Null-Regression OFF): fehlt der Seed -> leeres Set (byte-identisch zum heutigen Single-Lauf).
const phase3_fired = new Set()
{
  const seed = (A.phase3_fired_seed && typeof A.phase3_fired_seed === 'object') ? A.phase3_fired_seed : {}
  for (const id of Object.keys(seed)) { if (seed[id] === true) phase3_fired.add(id) }
}
// BL-238 AK-9: Cross-Round-Recalc-Zaehler PRO Sub-Batch (ueber phase3_fired-Idempotenz hinaus).
// phase3_fired blockt nur das ZWEITE Feuer pro Sub-Batch; recalcRounds zaehlt die REALEN
// SC-Saettigungs-Recalc-Runden, damit eine endlos saettigende SC-Schleife am MAX_RECALC_ROUNDS-Cap
// fail-loud terminiert statt unbegrenzt runPhase3 zu triggern (PT-CMD-011 fail-loud).
// BL-230 SB-5 (AK-GUARD-PERSIST, S-GP-2/EC-GP-3): keyed-upsert-Seed aus dem PERSISTENTEN Manifest-Marker
// A.recalc_rounds_seed (DF_BATCH_STATE.recalc_rounds_per_batch[id]) — der MAX_RECALC_ROUNDS-Cap liest den
// ECHTEN bisherigen Count (statt bei 0 neu zu zaehlen), sodass ein Crash-Replay-Pendel den Cap NICHT umgeht
// (recalc_cap_exceeded haelt ueber Resume). S-GP-3 (Null-Regression OFF): fehlt der Seed -> leere Map.
const recalcRounds = new Map()
{
  const seed = (A.recalc_rounds_seed && typeof A.recalc_rounds_seed === 'object') ? A.recalc_rounds_seed : {}
  for (const id of Object.keys(seed)) { const n = parseInt(seed[id], 10); if (Number.isInteger(n) && n > 0) recalcRounds.set(id, n) }
}

// ===========================================================================
// BL-327 sub_batch_2 "motorread" (AK-2): WELLEN-BARRIER-Dial-Read. EINMAL hier,
// VOR dem outer-Loop (NICHT pro Iteration) — exakt der Lese-Zeitpunkt aus der
// BL-230-Roadmap §5 ("NUR an der Wellen-Grenze"). Reines LESEN + CAP-RECHNEN +
// OBSERVABILITY. KEIN echter Parallel-Ausfuehrungspfad: effective_fanout wird
// hier NICHT zum Spawnen benutzt, der for-Loop unten bleibt strikt sequentiell
// (das ist BL-230/BL-328, NICHT dieses Item). parallel_mode=false => alles bleibt
// byte-identisch zum heutigen seriellen Pfad (Null-Risiko-Fallback/Kill-Switch).
const MAX_CONCURRENT = 16   // harte obere Schranke (Caps duerfen nur SENKEN, nie heben)
const parallel_mode = A.parallel_mode === true   // default false (Master-Schalter; fehlt => OFF)
const nr_parallel_batches = (Number.isInteger(A.nr_parallel_batches) && A.nr_parallel_batches >= 1) ? A.nr_parallel_batches : 1   // default 1
// BL-230 SB-4 (AK-BUDGET-CAP, SOA-2): die Budget-/Nesting-Caps werden aus A.* (session_params/BL-234-Resolver)
// GELESEN, NICHT hartkodiert (MAX_CONCURRENT=16 bleibt die OBERE Schranke, nicht der Budget-Wert). Fehlen sie ->
// kein Budget-Cap-Effekt (Resolver liefert nichts -> heutiges min(...)-Verhalten). Caps duerfen nur SENKEN (W9).
const resource_caps = (Number.isInteger(A.resource_caps) && A.resource_caps >= 1) ? A.resource_caps : null   // injiziert/gelesen, kein Magic-Number
const m_inner = (Number.isInteger(A.m_inner) && A.m_inner >= 1) ? A.m_inner : null        // Nested: Inner-Slots pro Welle-Slot
const engine_cap = (Number.isInteger(A.engine_cap) && A.engine_cap >= 1) ? A.engine_cap : MAX_CONCURRENT
// BL-230 SB-4 (AK-GO-PARALLEL-FN): effective_fanout-Ableitung ruft goParallel(...) (Gate-Kette + 5 Fallbaecke +
// nur-senken), NICHT mehr eine nackte Math.min-Formel. goParallel senkt auf SERIELL (1) bei jedem roten Gate /
// Fallback; bei GO_PARALLEL gruen liefert es min(nr,|welle|,MAX_CONCURRENT). DANACH senken die Budget-/Nested-Caps.
let effective_fanout = goParallel({
  parallel_mode, nr_parallel_batches, max_concurrent: MAX_CONCURRENT,
  welle_size: SUB_BATCHES.length, wave_size: SUB_BATCHES.length,
  // Σgroesse: heute keine echte Groessen-Telemetrie im Motor -> Welle-Laenge als sichere Untergrenze (>=2 passt Schwelle).
  sum_groesse: SUB_BATCHES.length, sum_size: SUB_BATCHES.length, total_size: SUB_BATCHES.length,
  gates: A.gates, concurrency_classes: A.concurrency_classes, all_parallel: A.all_parallel,
  parallel_safe_all: A.parallel_safe_all, file_disjoint: A.file_disjoint,
  srs_alarm: A.srs_alarm, k_score_growing: A.k_score_growing,
}).effective_fanout
// AK-BUDGET-CAP: Budget-Cap (resource_caps) senkt weiter (min); Nested N_outer × M_inner <= engine_cap.
if (effective_fanout > 1 && resource_caps != null) effective_fanout = Math.min(effective_fanout, resource_caps)
if (effective_fanout > 1 && m_inner != null) effective_fanout = Math.min(effective_fanout, Math.floor(engine_cap / m_inner))
if (!(effective_fanout >= 1)) effective_fanout = 1
// BL-230 SB-2 (AK-COMMIT-SEAM): Repo-Anwesenheit injizierbar (analog handoff merge_fn in worktree_registry.py).
// repo_present=true (.git da) -> Code-Merge-Pfad in der Barrier (commit-per-branch + serieller Mothership-Merge).
// repo_present=false (git-loser Vault, T9/SOA-3) -> dokumentiertes N/A (commit_seam='na_repo_absent'), KEIN Merge.
const repo_present = A.repo_present === true   // default false (git-loser Vault = sicherer Default; kein blinder git-Call)
log(`[dispatch_implement] dial: parallel_mode=${parallel_mode} nr=${nr_parallel_batches} effective_fanout=${effective_fanout}`
  + ` (Lese-Zeitpunkt=Wellen-Barrier, EINMAL vor dem outer-Loop; KEIN echter Parallel-Pfad — for-Loop bleibt sequentiell, BL-327)`)
// ===========================================================================

// BL-230 AK-FANIN-BARRIER (SB-1b): Fan-In-Barrier als 5-Schritt-STRUKTUR unter Index-Lock. SB-1a etablierte nur
// die serielle Aufruf-Stelle (1x NACH await parallel(...), VOR loopDecision). SB-1b baut die ORCHESTRIERUNG der 5
// SERIELLEN Schritte in FESTER Reihenfolge: (1) Code-Merge -> (2) Post-Merge-Green-Check -> (3) Model/SRS-Writes ->
// (4) Truth-Revalidierung -> (5) loopDecision-Aggregat. Reihenfolge + Aufruf-Struktur + Index-Lock-Charakter sind
// SB-1b; die Unterschritt-INHALTE bleiben STUB (Code-Merge=COMMIT-SEAM / Truth-Reval=FANIN-COMMUTATIVE / etc. =
// spaetere AKs). Analog runStageCommit (Z493): barrier_only / concurrency_class=EXCLUSIVE / Index-Lock — Single-
// Writer-Seam der Welle, NIE nebenlaeufig. 1 agent = 1 Step (INV-MOTOR-1 / INV-SPAWN).
async function runFanInBarrier(builtIds) {
  // BL-230 SB-3a (AK-PARALLEL-COMMUTATIVE / KOM-1): die Welle-Batch-Ids DETERMINISTISCH (batch_id-sortiert)
  // ordnen — das Minimum/die Sortierung einer Menge ist permutations-invariant. Lauf [sb1,sb2] und [sb2,sb1]
  // ergeben dieselbe sortierte Liste -> Schritt-3-Verarbeitungs-Reihenfolge ist eingabe-UNABHAENGIG (kommutativ).
  // Die gesamte Barrier referenziert AUSSCHLIESSLICH diese sortierte Liste (auch der Einstiegs-Satz), damit die
  // ERSTE batch_id-Nennung im Prompt bereits sortiert ist (KOM-1 idOrder liest die erste Nennung).
  const liveSortedIds = (Array.isArray(builtIds) ? builtIds.slice() : []).filter(Boolean).sort()
  // BL-230 SB-2 (AK-COMMIT-SEAM): Schritt 1 (Code-Merge) ist repo-aware. repo_present=true -> echter
  // Merge-Pfad (commit-per-worktree-branch + serieller Mothership-Merge, Single-Writer/barrier_only).
  // repo_present=false (git-loser Vault, T9/SOA-3) -> dokumentiertes N/A, KEIN Merge/Commit (keine Improvisation).
  const commit_seam = repo_present ? 'merged' : 'na_repo_absent'
  const step1 = repo_present
    ? `  1. Code-Merge (AK-COMMIT-SEAM, repo_present=true) — INDEX-LOCK / barrier_only=true / concurrency_class = EXCLUSIVE (Single-Writer-Commit-Seam): `
      + `erzeuge je nebenlaeufig gebautem Worktree-Branch GENAU EINEN Commit (commit-per-worktree-branch) UND fuehre DANACH `
      + `einen serieller Mothership-Merge dieser Branch-Commits aus (Commits VOR Merge; der Merge laeuft SERIELL, 1x, NIE `
      + `nebenlaeufig in einem parallel()-Thunk). commit_seam='merged'. (Post-Merge-Green/Truth-Reval bleiben Schritt 2/4 STUB.)\n`
    : `  1. Code-Merge (AK-COMMIT-SEAM, repo_present=false / git-loser Vault, T9/SOA-3) — dokumentiertes N/A: `
      + `KEIN commit-per-worktree-branch, KEIN serieller Mothership-Merge (keine Improvisation, kein git-Call). `
      + `commit_seam='na_repo_absent'. Die uebrigen Barrier-Schritte (2-5) laufen UNBERUEHRT weiter.\n`
  await agent(`Lade als ERSTE Aktion Skill(_I_fanIn) und fuehre AUSSCHLIESSLICH den Fan-In-Barrier-Schritt fuer die `
    + `soeben NEBENLAEUFIG gebaute Welle (lebende/gebaute Batches, builtIds DETERMINISTISCH batch_id-sortiert: ${JSON.stringify(liveSortedIds)}) aus (INV-SPAWN: 1 Worker = 1 Phase, danach STIRBST du). ${CTX}. ${PATHS}\n`
    + `BL-230 AK-FANIN-BARRIER (SB-1b) — INDEX-LOCK / SINGLE-WRITER-SEAM (barrier_only=true, concurrency_class = EXCLUSIVE): `
    + `diese Barrier ist die EINZIGE serielle Naht der Welle (1x nach dem parallel()-Fan-Out, VOR loopDecision). Sie darf `
    + `NIE nebenlaeufig in einem parallel()-Thunk laufen (Single-Writer-Truth-Mutation, Index-Stage-Drift) — Index-Lock, exklusiv.\n`
    + `Fuehre die folgenden 5 SERIELLEN SCHRITTE in EXAKT dieser FESTEN Reihenfolge aus (geordnete Barrier-Sequenz):\n`
    + step1
    + `  2. Post-Merge-Green-Check: Build + Unit-Suite NACH dem Merge gegen den verschmolzenen Stand (STUB SB-1b: nur Aufruf-Slot; INHALT = SOA-1 U1-Backstop, spaeter).\n`
    + `  3. Model/SRS-Writes (AK-PARALLEL-COMMUTATIVE + AK-TRUTH-WRITER, SB-3a): Single-Writer Model/SRS-Mutation NUR HIER in der Barrier (seriell, NIE im parallelen Thunk — INV-PARALLEL-COMMUTATIVE). `
    + `Iteriere als dedizierter serieller Schritt ueber die LEBENDEN/gebauten Welle-Batches in DETERMINISTISCHER batch_id-sortierter Reihenfolge `
    + `(sortiert nach batch_id, .sort()) — die Verarbeitungs-Reihenfolge ist permutations-invariant (zwei Permutationen der Welle -> identischer Model/SRS-Endzustand). `
    + `Sortierte lebende Batch-Liste (Schritt-3-Iterations-Reihenfolge): ${JSON.stringify(liveSortedIds)} — adressiere NUR diese lebenden builtIds, KEINEN toten Batch (filter(Boolean)-Konsistenz, SB-2).\n`
    + `     AK-TRUTH-WRITER (INV-TRUTH-WRITER-1): diese Fan-In-Barrier ist der EINZIGE/Single-Writer von truth_to_batches (Single-Writer-Invariant, analog batch_modes_set_by/INV-MODUS-1). `
    + `Setze den Guard-Marker truth_to_batches_set_by: fan_in_barrier (maschinenlesbare Hoheit, whitelist-faehiges named-writer/set_by-Muster). `
    + `KEINE andere Stelle (kein paralleler Worker) darf truth_to_batches schreiben — KEIN truth_to_batches-Write ausserhalb dieser Barrier.\n`
    + `  4. Truth-Revalidierung (AK-FANIN-COMMUTATIVE / INV-FANIN-COMMUTATIVE-1, SB-3a): built_on_stale_truth-Reval der Welle gegen den frisch verschmolzenen Truth-Stand. `
    + `Regel "Widerlegung gewinnt": mutieren zwei Batches dasselbe W{n} gegenlaeufig, setzt sich der SCHWAECHERE Wahrheits-Grad durch (Minimum gewinnt), reihenfolge-unabhaengig (das Minimum einer Menge ist permutations-invariant — vgl. Helper weakestTruthGrade). `
    + `Grad-Ordnung (stark -> schwach, Minimum gewinnt): BESTÄTIGT > TENTATIV > HYPOTHESE > OFFEN/WIDERLEGT.\n`
    + `     blast_set-Eskalations-Leiter (§11b): blast_set = {B | W_refs(B) ∩ divergierte W{n} != leer} (Batches, deren W_refs die divergierte W{n} schneiden). `
    + `Eskalations-Stufen in dieser Reihenfolge: QUARANTÄNE (Default/Standard) -> PIN-INVALIDIERUNG -> WELLE-SHRINK. `
    + `Termination-Driver == die divergierende W{n} (NICHT der Batch — Sub-Agenten sind nicht suspendierbar; revalidieren statt pausieren).\n`
    + `  5. wave_conformance_gate (Konformitaets-Gate, Vorbedingung) + loopDecision-Aggregat (AK-G7-KONFORM + AK-WELLE-LOOPDEC, SB-3b): fuehre ZUERST als VORBEDINGUNG den N-Report-Konformitaets-Check / das G7-Gate aus `
    + `(Prozess-Konformitaet: ist pro lebendem Batch Phase-3.x gelaufen? — N-Report-Validierung via waveConformanceGate/wave_conformance_gate ueber die gemergte Per-Batch-Trace-Inventur, `
    + `pro batch_id ein Befund: alle 4 Phase-3.x-Outputs recalibrate/postItem/statusTransition/modelSync vorhanden, modelSync:SKIP nur mit reason). `
    + `ALL-konjunktiv: Verletzung in IRGENDEINEM der N lebenden Reports -> Gate-FAIL (fail-loud), nenne die divergente(n) batch_id(s) -> KEIN loopDecision-Aggregat / KEIN loop_decision-VEKTOR (Gate-FAIL -> kein Vektor, fail-loud-Vorbedingung). `
    + `NUR bei Gate-GRUEN (ALLE N konform): bilde DANN das loopDecision-Aggregat als loop_decision-VEKTOR (AK-WELLE-LOOPDEC, SB-4): PRO lebendem Batch EIN loop_decision-Eintrag — `
    + `N Eintraege ueber liveSortedIds (ein loop_decision-Eintrag pro Batch, NICHT ein einzelnes welle-aggregiertes Skalar), `
    + `in DETERMINISTISCHER batch_id-sortierter Reihenfolge (sortiert nach batch_id, .sort(), liveSortedIds — konsistent mit SB-3a Schritt 3/4). `
    + `1 toter Batch != Welle tot: der Vektor enthaelt NUR die lebenden Batches (filter(Boolean)-Konsistenz). `
    + `INV-MODUS-9-Wellen-Neufassung (AK-WELLE-LOOPDEC, SB-4): zusaetzlich zum loop_decision-VEKTOR fuehre einen sc_resume_from-VEKTOR (pro Batch ein sc_resume_from-Wert ueber liveSortedIds, NICHT ein globaler Singular). `
    + `INV-MODUS-9-Semantik PRO Batch: sc_resume_from="ergebnis" bei SC-Re-Entry des Batches, sc_resume_from=null bei Erst-Eintritt des Batches. `
    + `Sortierte lebende Batch-Liste (Vektor-Reihenfolge, ein loop_decision + ein sc_resume_from pro Batch): ${JSON.stringify(liveSortedIds)}.\n`
    + `STUB-VERTRAG (BL-230): Schritt 1 (Code-Merge) ist SB-2-AK-COMMIT-SEAM (repo-aware-Struktur, oben); Schritt 3+4 sind SB-3a-gefleshtes INHALT (oben); Schritt 5 ist SB-3b/SB-4-gefleshtes INHALT (Konformitaets-Gate SB-3b + loop_decision-VEKTOR + sc_resume_from-VEKTOR SB-4, oben). `
    + `Schritt 2 (Post-Merge-Green) bleibt STUB fuer die genannte spaetere AK (SOA-1 U1-Backstop) — gehoert NICHT zu G7.`,
    { label: `runFanInBarrier:${BL}`, phase: 'FanIn' })
  return { fan_in_barrier: true, commit_seam }
}

// BL-230 AK-MOTOR-WELLE (AON-1..7 / EC-1/5/6): die Per-Sub-Batch-Verarbeitung als FUNKTION extrahiert, damit
// BEIDE Pfade sie nutzen — der serielle for-Loop (effective_fanout==1, BYTE-IDENTISCH/Null-Regression OFF) UND
// der parallel()-Fan-Out (effective_fanout>1, Chunks via parallel()-Thunk-Array). Rueckgabe = Control-Signal
// { ctl: 'continue'|'break'|'return', value? }: 'continue'=naechster Sub-Batch, 'break'=Outer-Loop terminieren
// (HALT/ABORT/Cap = bewusste fail-safe-Entscheidung), 'return'=ganzer Workflow returnt sofort (split/test-conflict).
// Im Parallel-Pfad werden 'break'/'return'-Signale NACH dem Fan-In am Driver konsumiert (1 toter Batch != Welle tot).
async function processSubBatch(sb) {
  // BL-319 AK-3 (Partial-Failure-Semantik): per-Batch try/catch-Isolation. Ein im Build (runImplementStage)
  // oder einem Decision-Agent geworfener Fehler beendet NUR diesen Sub-Batch (Outcome=failed), NICHT die ganze
  // outer-Schleife — die Geschwister laufen zu Ende (Voraussetzung BL-230: 1 toter Batch != Welle tot). Die
  // INTENTIONALEN Terminierungen (HALT/ABORT/recalc_cap/sc_verdict_abort + bottom-break) bleiben break-outer
  // (sie sind kein geworfener Fehler, sondern bewusste fail-safe-Entscheidungen) — nur der THROW wird isoliert.
  // null-statt-throw-Konvention (BL-315): der gefangene Fehler -> failed-Outcome, KEIN Top-Level-Throw.
  try {
  // L4 (BL-232): Stages aus coverage_map.stages_with_tests (Pre-SDF-befuellt) bevorzugen — die
  // Coverage entscheidet WELCHE Stufen laufen. Fallback: geplante stages, dann [1] (min Unit).
  const planned = (Array.isArray(sb.coverage_stages) && sb.coverage_stages.length)
    ? sb.coverage_stages.slice()
    : (Array.isArray(sb.stages) && sb.stages.length ? sb.stages.slice() : [1])

  // --- Phase 1.1: modusEntscheidung PRO SUB-BATCH (INV-MODUS-1/4: alleinige Modus-Quelle) ---
  phase('Modus')
  // BL-285 AK-1 (Wurzel der leeren batch_modes, OQ#3 sauberer Hebel): der Motor setzt den Sub-Batch-Cursor
  // DETERMINISTISCH ins Manifest, BEVOR C3 spawnt. Ohne current_sub_batch_id faellt _SDF_berater_modusEntscheidung
  // in den Single-Batch-ELSE-Pfad (Vertrag Z200-219) und persistiert batch_modes[id] NIE pro Sub-Batch
  // (DCSRE-486 'grep batch_modes = 0'). Guard-clean (current_sub_batch_id/_items matchen NICHT MODUS_FIELD_PATTERN).
  // BL-230 AK-MOTOR-WELLE (AON-4): im Parallel-Pfad (effective_fanout>1) schreiben 2 nebenlaeufige Batches
  // sonst denselben globalen Single-Slot current_sub_batch_id (Last-Writer-Wins). Darum batch-KEYED:
  // cursorMap[<id>]={modus_view,cursor} statt des globalen Slots. Im seriellen Pfad (fanout==1) bleibt der
  // globale current_sub_batch_id-Write BYTE-IDENTISCH (Kompat, Null-Regression OFF).
  if (effective_fanout > 1) {
    await agent(`Persistiere AUSSCHLIESSLICH cursorMap[${JSON.stringify(sb.id)}] = { cursor: ${JSON.stringify(sb.id)}, items: ${JSON.stringify(sb.items)}, modus_view: null } ins Vault-Manifest (batch-keyed Cursor-MAP, AON-4). `
      + `INV-2 Write-Isolation: NUR dieser eine batch-keyed Eintrag (cursorMap[${JSON.stringify(sb.id)}]), KEIN globaler DF_BATCH_STATE.current_sub_batch_id-Slot (2 nebenlaeufige Batches wuerden ihn Last-Writer-Wins ueberschreiben), `
      + `KEIN Code, KEIN batch_modes/modus-Write (das macht gleich _SDF_berater_modusEntscheidung — INV-MODUS-1).\n`
      + `BL-230 SB-3a AK-TRUTH-WRITER (INV-TRUTH-WRITER-1): KEIN truth_to_batches-Write — der parallele Worker darf truth_to_batches NIEMALS schreiben (truth_to_batches ist verboten im Worker). EINZIGER autorisierter truth_to_batches-Writer ist die serielle Fan-In-Barrier (truth_to_batches_set_by: fan_in_barrier), analog dem "KEIN batch_modes-Write"-Verbot. ${PATHS}`,
      { label: `persistSubBatchCursor:${sb.id}`, phase: 'Modus', model: 'sonnet' })
  } else {
    await agent(`Persistiere AUSSCHLIESSLICH DF_BATCH_STATE.current_sub_batch_id = ${JSON.stringify(sb.id)} und `
      + `DF_BATCH_STATE.current_sub_batch_items = ${JSON.stringify(sb.items)} ins Vault-Manifest. INV-2 Write-Isolation: `
      + `NUR diese zwei Felder, KEIN Code, KEIN batch_modes/modus-Write (das macht gleich _SDF_berater_modusEntscheidung — INV-MODUS-1). ${PATHS}`,
      { label: `persistSubBatchCursor:${sb.id}`, phase: 'Modus', model: 'sonnet' })
  }
  const modusOut = await safeSchemaAgent(
    `Lade Skill(_SDF_berater_modusEntscheidung) und entscheide den Execution-Modus (M1..M9) fuer Sub-Batch ${sb.id} `
    + `(items=${JSON.stringify(sb.items)}) anhand des AKTUELLEN Vault-State. ${CTX}. ${PATHS}\n`
    + `INV-MODUS-1: DU bist die EINZIGE Modus-Quelle. INV-MODUS-3: schreibe modus_begruendung im Format `
    + `"Aus k_score=X + srs=Y + batch_type=Z -> M{N}".\n`
    + `BL-285 AK-1 PERSIST-PFLICHT: der Motor hat current_sub_batch_id=${JSON.stringify(sb.id)} bereits gesetzt — `
    + `schreibe AUTORITATIV DF_BATCH_STATE.batch_modes[${JSON.stringify(sb.id)}]=<Modus> + modus_begruendung_per_batch[${JSON.stringify(sb.id)}]=<Begruendung> `
    + `+ Guard-Marker batch_modes_set_by: _SDF_berater_modusEntscheidung (guard_modus_writer Whitelist; DU bist der EINZIGE batch_modes-Writer).\n`
    + `BL-279/BL-304 (SCHRITT 7 Mitose-Zwang): setze split_required=true + split_reason, wenn der Sub-Batch re-cut `
    + `gehoert — (a) k_score_max >= hard_threshold (Default 80, kein normalization_artifact) ODER (b) verify_mode-`
    + `Heterogenitaet (coverage_per_batch[${JSON.stringify(sb.id)}].verify_mode_heterogeneous == true, tdd + `
    + `scenario/convention gemischt) ODER (c) Effort-Heterogenitaet (BL-304): items_count>1 UND k_score_avg < het_floor `
    + `(Default 15) UND k_score_max in [het_floor, hard_threshold) — die Gate-Luecke [15,80), wo triviale Items sonst `
    + `nach M2 mitgerissen werden statt M1-MULTI. Sonst split_required=false. ${DECISION_NOTE}`,
    { label: `modusEntscheidung:${sb.id}`, phase: 'Modus' }, MODUS_SCHEMA,
    { modus: 'M2', modus_begruendung: 'FALLBACK (Schema-Crash-Haertung): Decision-Agent lieferte nach schemalosem Retry kein valides JSON -> Default M2 (code-with-test, sicherster Modus: schreibt Code + laeuft bestehende Tests, kein Greenfield-Risiko).' })
  const modus = (modusOut && modusOut.modus) || 'M2'
  const fam = modusFamily(modus)
  log(`[dispatch_implement] Sub-Batch ${sb.id}: modus=${modus} (${fam}) — ${(modusOut && modusOut.modus_begruendung) || ''}`)

  // BL-230 AK-CURSOR-MAP (SB-1b): das modus_view des batch-keyed cursorMap-Slots wird NACH der modusEntscheidung mit
  // dem ENTSCHIEDENEN Modus (M{N}) befuellt + persistiert — KEIN dauerhaftes literal null mehr (SB-1a-Minimal-Slot
  // ueberwunden). NUR im Parallel-Pfad (effective_fanout>1, batch-keyed disjunkt); der serielle Pfad bleibt byte-
  // identisch (globaler current_sub_batch_id-Write, kein cursorMap — CM-4/EC-CM-2 Null-Regression OFF). INV-MODUS-1:
  // das ist die motor-owned cursorMap-Beobachtung des Modus, KEIN autoritativer batch_modes-Write (den macht C3).
  // CM-3 (EC-CM-3): bei Schema-Crash-Fallback ist modus='M2' (safeSchemaAgent-Default) -> modus_view wird mit M2
  // befuellt, nie null. Batch-keyed disjunkt: cursorMap[<diese-id>], kein globaler Slot, kein Cross-Batch-Overwrite.
  if (effective_fanout > 1) {
    await agent(`Persistiere AUSSCHLIESSLICH cursorMap[${JSON.stringify(sb.id)}].modus_view = ${JSON.stringify(modus)} ins Vault-Manifest `
      + `(batch-keyed Cursor-MAP modus_view-Befuellung NACH modusEntscheidung, AK-CURSOR-MAP SB-1b — der entschiedene Modus ${modus} ersetzt den SB-1a-Minimal-Slot mit leerem modus_view). `
      + `INV-2 Write-Isolation: NUR dieser eine batch-keyed modus_view-Slot (cursorMap[${JSON.stringify(sb.id)}].modus_view), KEIN globaler DF_BATCH_STATE.current_sub_batch_id-Slot, `
      + `KEIN anderer cursorMap-Key (disjunkt — 2 nebenlaeufige Batches schreiben VERSCHIEDENE Keys, kein Cross-Batch-Overwrite), KEIN Code, `
      + `KEIN batch_modes/modus-Write (autoritativ ist batch_modes[${JSON.stringify(sb.id)}] aus _SDF_berater_modusEntscheidung — INV-MODUS-1). ${PATHS}`,
      { label: `persistCursorModusView:${sb.id}`, phase: 'Modus', model: 'sonnet' })
  }

  // BL-279 Mitose-Enforcement: aus dem frueheren non-blocking "Wunsch" wird ein Zwang. Setzt modusEntscheidung
  // split_required (k_max >= hard_threshold ODER verify_mode-Heterogenitaet), baut der Motor den mal-geformten
  // Sub-Batch NICHT, sondern RETURNED loop_decision=RE-BATCH an den Lead (INV-MOTOR-2 — Re-Cut macht der Lead via
  // IDF-Re-Cluster). Schliesst den batch_3-Gap (k_max=100 + tdd/scenario gemischt, lief ungesplittet → J13-Detour).
  if (modusOut && modusOut.split_required) {
    terminated_reason = 're_cut_required'
    log(`[dispatch_implement] BL-279 SPLIT-ZWANG: Sub-Batch ${sb.id} muss re-cut werden (${modusOut.split_reason || 'k_max/verify_mode'}) — Build uebersprungen, RE-BATCH an Lead (INV-MOTOR-2).`)
    results.push({ sub_batch: sb.id, modus, outcome: 're_cut_required', split_reason: (modusOut.split_reason || null) })
    return { ctl: 'return', value: {
      bl_id: BL,
      sub_batch_results: results,
      terminated_reason,
      loop_decision: 'RE-BATCH',
      re_cut_target: sb.id,
      note: 'BL-279: modusEntscheidung split_required -> Motor RETURNED RE-BATCH (kein Build des mal-geformten Sub-Batches). Lead schneidet via IDF-Re-Cut homogen neu (INV-MOTOR-2).',
    } }
  }

  // BL-285 AK-3/AK-4 Provenance-Persist (Motor-owned, guard-clean; NACH split_required-Block platziert, OQ#1-Korrektur:
  // feuert NICHT fuer einen sofort als RE-BATCH verworfenen Sub-Batch). DCSRE-486: Motor entscheidet korrekt im Flow,
  // aber Aussenansicht zeigt 3 Werte (hint=M2 / stale 'M2-skeleton' / echt) -> wiederholte Fehldiagnose + Motor-Bypass.
  // INV-MODUS-1: schreibt NICHT batch_modes/modus (das macht C3), NUR Beobachtungs-Felder. OQ#4-Korrektur: schreibt in
  // ein MOTOR-OWNED Feld (current_modus_view) statt den orchestrator-owned I_PIPELINE_STATE-Header zu mutieren.
  const modusBegr = (modusOut && modusOut.modus_begruendung) || ''
  await agent(`Persistiere BL-285-Provenance fuer Sub-Batch ${sb.id} ins Vault-Manifest — INV-2 Write-Isolation, KEIN Code, `
    + `KEIN batch_modes/modus-Write (das macht ausschliesslich _SDF_berater_modusEntscheidung — INV-MODUS-1).\n`
    + `1) DF_BATCH_STATE.modus_provenance_per_batch[${JSON.stringify(sb.id)}] = { modus: ${JSON.stringify(modus)}, begruendung: ${JSON.stringify(modusBegr)}, modus_set_by: "dispatch_implement->_SDF_berater_modusEntscheidung", entschieden_at } (Beobachtungs-Spiegel, KEIN autoritativer batch_modes-Slot).\n`
    + `   BL-319 AK-2 SET-ONCE (Idempotenz): entschieden_at NUR setzen wenn der Slot noch leer/nicht gesetzt ist (entschieden_at ??= ISO-now) — bei 2x-Lauf den bestehenden Timestamp BEIBEHALTEN (kein <ISO-now>-Drift, keine Neu-Datierung).\n`
    + `2) AK-3/AK-4 (motor-owned, KEIN I_PIPELINE_STATE-Mutieren): DF_BATCH_STATE.current_modus_view = { sub_batch: ${JSON.stringify(sb.id)}, modus: ${JSON.stringify(modus)}, note: "autoritativ ist batch_modes[id] aus _SDF_berater_modusEntscheidung (INV-MODUS-1); modus_hint ist nur die IDF-W7-Vorhersage" }. ${PATHS}`,
    { label: `persistModusDecision:${sb.id}`, phase: 'Modus', model: 'sonnet' })

  if (fam === 'SPECIAL') {
    // M8 (PR-Review) / M9 (WP) — Sonderpfad: 1 agent, kein Stage-Loop. (Implement-Kern uebersprungen.)
    await agent(`Lade Skill(${modus === 'M8' ? '_T_orchestrate' : '_WP_orchestrate'}) und fuehre den ${modus}-Sonderpfad fuer ${sb.id} aus. ${CTX}. ${PATHS}`,
      { label: `${modus}-special:${sb.id}`, phase: 'Implement' })
    results.push({ sub_batch: sb.id, modus, outcome: 'special_path' })
    return { ctl: 'continue' }
  }

  // --- Phase 1.5: patternBrief ---
  phase('PatternBrief')
  await agent(`Lade Skill(_SDF_berater_patternBrief) und erstelle den Pattern-Brief fuer Sub-Batch ${sb.id} (Pattern-Lookup vor Dispatch). ${CTX}. ${PATHS}\n`
    + `BL-319 AK-2 KEYED-OVERWRITE-STATT-APPEND (Idempotenz): schreibe den Pattern-Brief deterministisch keyed auf sub_batch=${JSON.stringify(sb.id)} (keyed-Overwrite) — `
    + `KEIN Append eines neuen Brief-Blocks pro Lauf. Ein bestehender Brief fuer ${JSON.stringify(sb.id)} wird ueberschrieben, nicht dupliziert (kein Doppel-Brief bei 2x-Lauf).`,
    { label: `patternBrief:${sb.id}`, phase: 'PatternBrief' })

  // --- Stage-Inner-Loop (deterministisch, C-B1 frische Decision je Iteration, C-B3 harter Cap) ---
  const completed = []
  let current_stage = planned[0]
  let stageIters = 0
  let batchOutcome = 'unknown'
  let sc_verdict = null          // BL-238 AK-1: zuletzt gelesenes SC-Saettigungs-Verdikt (fam==='SC')
  let subBatchCtl = null         // BL-230 AK-MOTOR-WELLE: break-outer-Aequivalent aus der Stage-Loop (am Driver konsumiert)

  // --- BL-262 AK-S2: Resume-Preflight (gebauter-aber-nicht-finalisierter Sub-Batch) ---
  // Liest den MIGRIERBAREN Vault-Cursor (completed_stages_per_batch, AK-S1) + prueft die Sub-Batch-Tests
  // READ-ONLY. all_done → Build SKIP, batchOutcome=BATCH_DONE, current_stage=null → die while-Loop wird
  // uebersprungen und der bestehende `if (batchOutcome === 'BATCH_DONE') runPhase3` (unten) finalisiert.
  // KEIN .claude-Journal-Abhaengigkeit (AK-S4): der Cursor lebt im committed Vault-Manifest.
  // NUR I_FULL (M2/M3 — die teuren Build-Modi, wo Re-Build des ganzen Sub-Batches schmerzt). M1-Skeleton
  // (I_SKELETON) ist atomar+winzig (1 Step) → kein Preflight noetig.
  if (fam === 'I_FULL') {
    phase('Implement')
    const pf = await safeSchemaAgent(
      `PREFLIGHT (READ-ONLY — KEIN Build, KEIN Code-Edit, KEIN TDD-STATE-Write) fuer Sub-Batch ${sb.id} `
      + `(geplante Stages=${JSON.stringify(planned)}). ${CTX}. ${PATHS}\n`
      + `1) Lies DF_BATCH_STATE.completed_stages_per_batch[${JSON.stringify(sb.id)}] (Vault-Cursor, AK-S1) — bereits abgeschlossene Stages.\n`
      + `2) Pruefe READ-ONLY ob die Test-Artefakte dieses Sub-Batches (TDD-STATE.tests_written ODER Konvention `
      + `test_{name}_batch{N}.py) fuer die geplanten Stages EXISTIEREN und GRUEN sind — fuehre NUR die Tests aus (py -3 -m pytest / dotnet test), schreibe NICHTS.\n`
      + `Melde all_done=true NUR wenn fuer ALLE geplanten Stages Code+Tests existieren UND gruen sind (→ Build wird `
      + `uebersprungen, direkt Phase 3.x finalisiert). Sonst all_done=false (normaler Bau). completed_stages = bereits gruene Stages.`,
      { label: `resumePreflight:${sb.id}`, phase: 'Implement' }, PREFLIGHT_SCHEMA,
      { all_done: false, completed_stages: [] })   // Fallback (Schema-Crash): nichts done → sicherer Normal-Bau
    const preDone = (pf && Array.isArray(pf.completed_stages)) ? pf.completed_stages.filter(s => planned.includes(s)) : []
    for (const s of preDone) if (!completed.includes(s)) completed.push(s)
    if (pf && pf.all_done && completed.length >= planned.length) {
      log(`[dispatch_implement] ${sb.id}: PREFLIGHT all_done — Stages ${JSON.stringify(completed)} schon gebaut+gruen → SKIP Build, direkt Phase 3.x (BL-262 AK-S2, BL-242-Unblock; kein spurious RED→ABORT).`)
      batchOutcome = 'BATCH_DONE'
      current_stage = null
    } else if (completed.length > 0) {
      current_stage = planned.find(s => !completed.includes(s)) ?? null   // Resume ab erster offener Stage (AK-S1 Cursor)
      if (current_stage === null) { batchOutcome = 'BATCH_DONE' }         // Cursor voll, aber all_done=false → trotzdem finalisieren
      log(`[dispatch_implement] ${sb.id}: PREFLIGHT partial — Stages ${JSON.stringify(completed)} schon gruen, Resume ab Stage=${current_stage} (BL-262 AK-S1 Cursor).`)
    }
  }

  while (current_stage !== null && current_stage !== undefined) {
    stageIters++
    if (stageIters > MAX_STAGE_ITERS) {
      batchOutcome = 'ABORT_max_stage_iters'
      terminated_reason = 'max_stage_iters_exceeded'
      log(`[dispatch_implement] HARD-CAP: Sub-Batch ${sb.id} > ${MAX_STAGE_ITERS} Stage-Iterationen — fail-safe ABORT (C-B3).`)
      break
    }

    // 1) Implement (FLAT-SEQUENCE je 1 agent) — der Implement-Step fuer current_stage
    phase('Implement')
    const implRes = await runImplementStage(sb, current_stage, modus, fam)
    // BL-238 AK-1: SC-Stage liefert das SC_PIPELINE_STATE.sc_verdict-Signal (Producer AK-7) zurueck.
    if (fam === 'SC' && implRes && implRes.sc_verdict) sc_verdict = implRes.sc_verdict

    // BL-303 L1 (Consumer-Wiring): _TDD_green meldete einen unautorisierten Test-Konflikt (Gruen-Schutz). NICHT still
    // weiterlaufen (heute als false-GREEN BATCH_DONE oder fail-safe RED ABORT verschluckt) — Motor short-circuit VOR
    // stageElevation, RETURNED an den Lead (INV-MOTOR-2, Spiegel des split_required-Blocks). Auto-Build-Bounded-Entscheid
    // 2026-06-10: HiL-Fallback ist der SICHERE Default — der Motor setzt KEIN test_correction_authorized (der Auto-
    // Produzent _pr_question_answer_sim/FLIP lebt in BL-281/296). Der Lead adjudiziert Finding vs Test.
    if (implRes && implRes.test_conflict) {
      terminated_reason = 'test_conflict_blocked'
      results.push({ sub_batch: sb.id, modus, outcome: 'green_blocked_test_conflict', test_conflict: implRes.test_conflict })
      log(`[dispatch_implement] ${sb.id}: TEST-CONFLICT-BLOCKED — RE-BATCH an Lead + HiL-Adjudikation (BL-303 L1, kein false-GREEN/ABORT).`)
      return { ctl: 'return', value: {
        bl_id: BL,
        sub_batch_results: results,
        terminated_reason,
        loop_decision: 'RE-BATCH',
        re_cut_target: sb.id,
        test_conflict: implRes.test_conflict,
        note: 'BL-303 L1: _TDD_green meldete unautorisierten Test-Konflikt (Gruen-Schutz). Motor baute NICHT weiter (kein false-GREEN/ABORT). LEAD-RECOVERY: Finding<->Test-Adjudikation (adversarial Steelman _pr_question_answer_sim, BL-281/296) — Finding gewinnt (FLIP) -> setze test_correction_authorized+authorization_evidence am PL-Item + re-dispatch; Test gewinnt (STABLE) -> Finding wird REFUTATION, Item schliessen. HiL-Fallback, da Auto-Produzent (BL-281/296) noch nicht live.',
      } }
    }

    // 2) stageElevation — reiner Decision-Berater, liefert next_action + outcome
    phase('Elevate')
    const elev = await safeSchemaAgent(
      `Lade Skill(_SDF_berater_stageElevation) und entscheide nach Stage ${current_stage} (Sub-Batch ${sb.id}, geplante Stages=${JSON.stringify(planned)}, `
      + `bereits abgeschlossen=${JSON.stringify(completed)}) ueber next_action. ${CTX}. ${PATHS}\n`
      + `Enum next_action ∈ {ELEVATE,BATCH_DONE,RETRY,ABORT,HALT}, current_stage_outcome ∈ {GREEN,PARTIAL,RED,PAUSED}. `
      + `RETRY-Limit 2 (INV-STAGE-ELEV-3). ${DECISION_NOTE}`,
      { label: `stageElevation:${sb.id}.s${current_stage}`, phase: 'Elevate' }, ELEV_SCHEMA,
      { next_action: 'ABORT', current_stage_outcome: 'RED', rationale: 'FALLBACK (Schema-Crash-Haertung): Decision nach Retry unlesbar -> fail-safe ABORT (kein Faken eines GREEN/BATCH_DONE).' })

    const action = (elev && elev.next_action) || 'ABORT'
    log(`[dispatch_implement] ${sb.id} stage=${current_stage} outcome=${elev && elev.current_stage_outcome} -> ${action}`)

    // 3) Branch (C5: Phase 3.x NUR bei BATCH_DONE; C2 fail-safe DEFAULT -> ABORT)
    if (action === 'ELEVATE') {
      completed.push(current_stage)
      // BL-262 AK-S1: Stage-Cursor in den COMMITTED Vault persistieren (migrierbar, NICHT .claude-Journal/JS-Variable) —
      // bei Maschinen-Tod zwischen Stages resumed der Preflight ab der naechsten offenen Stage statt am Sub-Batch-Anfang.
      await agent(`Persistiere AUSSCHLIESSLICH das Feld DF_BATCH_STATE.completed_stages_per_batch[${JSON.stringify(sb.id)}] = ${JSON.stringify(completed)} `
        + `ins Vault-Manifest. INV-2 Write-Isolation: NUR dieses eine Feld (??= bei Resume nicht reset), KEIN Code, KEIN Modus, kein anderes State-Feld. ${PATHS}`,
        { label: `persistStageCursor:${sb.id}.s${current_stage}`, phase: 'Implement', model: 'sonnet' })
      // BL-299 AK-1 ELEVATE-Seam: normierter, gate-gepruefter Commit des GRUENEN Zwischenstands (Grain=Test-Stage).
      // AK-7: sichert ein 9/11-GREEN, das bei legit-deferred Items nie BATCH_DONE erreicht. Freeze-Gate (AK-2) im Worker.
      await runStageCommit(sb, current_stage, false)
      current_stage = (elev && (elev.next_stage !== null && elev.next_stage !== undefined))
        ? elev.next_stage
        : (planned.find(s => !completed.includes(s)) ?? null)   // C-B1: frisch ermittelt, kein stale state
      continue
    }
    if (action === 'RETRY') {
      // current_stage bleibt — gleiche Stage erneut (Berater fuehrt retry_counts, Cap zusaetzlich oben)
      continue
    }
    if (action === 'BATCH_DONE') {
      completed.push(current_stage)
      current_stage = null
      batchOutcome = 'BATCH_DONE'
      break
    }
    if (action === 'HALT') {
      batchOutcome = 'HALT'
      terminated_reason = 'halt_user'   // SDF_HALT_USER — echter Case (nicht still TERMINATE)
      current_stage = null
      subBatchCtl = 'break'   // break outer -> Outer-Loop terminieren (am Driver konsumiert)
      break
    }
    // ABORT + alles Unbekannte -> fail-safe (C2)
    batchOutcome = 'ABORT'
    terminated_reason = 'stage_abort'
    current_stage = null
    subBatchCtl = 'break'   // break outer -> Outer-Loop terminieren (am Driver konsumiert)
    break
  }
  if (subBatchCtl === 'break') {
    // HALT/ABORT in der Stage-Loop = bewusste fail-safe-Terminierung -> Outer-Loop beenden (break outer-Aequivalent;
    // KEIN results.push hier — byte-identisch zum Original, das via break outer den Bottom-Push uebersprang).
    return { ctl: 'break' }
  }

  // --- BL-238 AK-1: SC-Saettigungs-Branch — runPhase3-Trigger NEBEN (nicht IN) dem BATCH_DONE-Tor ---
  // Producer (AK-7, _SC_orchestrate.md) schreibt SC_PIPELINE_STATE.sc_verdict am Phase-5-Exit; der Motor
  // muenden eine SC-Saettigung deterministisch in runPhase3 — sonst endet sie heute im fail-safe-ABORT.
  // Zweiter Eintrittspunkt in runPhase3 (INV-MOTOR-1: runPhase3-Body :230-241 unveraendert / Kanarienvogel).
  if (fam === 'SC' && sc_verdict) {
    phase('BatchClose')
    if (sc_verdict === 'SATURATED_READY_FOR_IMPL' || sc_verdict === 'EXPERIMENT_OPEN') {
      // BL-238 AK-9: Cross-Round-Recalc-Cap. Zaehle die REALE Recalc-Runde PRO Sub-Batch und
      // terminiere fail-loud, sobald MAX_RECALC_ROUNDS ueberschritten ist — sonst kann eine
      // wieder und wieder saettigende SC-Schleife unbegrenzt runPhase3 triggern (PT-CMD-011).
      const priorRecalc = recalcRounds.get(sb.id) || 0
      recalcRounds.set(sb.id, priorRecalc + 1)
      if (priorRecalc + 1 > MAX_RECALC_ROUNDS) {
        batchOutcome = 'ABORT'
        terminated_reason = 'recalc_cap_exceeded'
        log(`[dispatch_implement] HARD-CAP: ${sb.id} > ${MAX_RECALC_ROUNDS} Recalc-Rounds (recalcRounds=${priorRecalc + 1}) — fail-loud TERMINATE (BL-238 AK-9, terminated_reason='recalc_cap_exceeded').`)
        results.push({ sub_batch: sb.id, modus, outcome: batchOutcome, completed_stages: completed, sc_verdict, recalc_rounds: priorRecalc + 1 })
        return { ctl: 'break' }
      }
      // Saettigung -> runPhase3 genau 1x (PT-CMD-007 Idempotenz: kein Doppel-Feuer bei 2x-Replay).
      if (!phase3_fired.has(sb.id)) {
        phase3_fired.add(sb.id)   // sc_verdict_consumed — recalc done, Trigger idempotent
        log(`[dispatch_implement] ${sb.id}: sc_verdict=${sc_verdict} -> runPhase3 (NEBEN BATCH_DONE, BL-238 AK-1, recalcRounds=${priorRecalc + 1}/${MAX_RECALC_ROUNDS})`)
        await runPhase3(sb)
      } else {
        log(`[dispatch_implement] ${sb.id}: sc_verdict=${sc_verdict} bereits konsumiert (phase3_fired) — kein Doppel-runPhase3 (PT-CMD-007).`)
      }

      // ── BL-238 AK-4 (Re-Entry re-modus, dispatch_implement.js) ──────────────────────────────
      // PIPELINE-POSITION (PT-CMD-010): A_SC_I-Chain SC -> recalc(runPhase3) -> RE-MODUS -> I_FULL|M5.
      // Nach runPhase3 (AK-2/B-2 hat metric_per_batch[sb.id] frisch versiegelt — INV-METRIC-1) ruft der
      // Motor _SDF_berater_modusEntscheidung ERNEUT auf (re-decide statt re-derive, INV-MODUS-1: der Motor
      // erfindet KEINEN Modus, er fragt den EINZIGEN Modus-Berater erneut). PT-GEN-LeadFollow: gespiegelt
      // vom Erst-Call (:297-303), gleiche MODUS_SCHEMA/Fallback-Konvention. INV-MOTOR-1: 1 agent=1 Berater.
      // PT-CMD-017 (DAG AK-2 -> AK-4): der Re-Entry liest den recalc'ten metric_per_batch-Slot, der ERST
      // durch runPhase3 (oben) frisch ist — Reihenfolge maschinen-erzwungen (runPhase3 steht VOR diesem Call).
      const reModusOut = await safeSchemaAgent(
        `Lade Skill(_SDF_berater_modusEntscheidung) und entscheide den Execution-Modus (M1..M9) fuer Sub-Batch ${sb.id} `
        + `(items=${JSON.stringify(sb.items)}) anhand des AKTUELLEN Vault-State NACH Recalc — lies metric_per_batch[${JSON.stringify(sb.id)}].srs_max `
        + `PRIMAER (INV-METRIC-1, frisch versiegelt durch den soeben gelaufenen Recalc/runPhase3). ${CTX}. ${PATHS}\n`
        + `INV-MODUS-1: DU bist die EINZIGE Modus-Quelle (Re-Decide, kein Motor-Modus). INV-MODUS-3: schreibe modus_begruendung im Format `
        + `"Aus k_score=X + srs=Y + batch_type=Z -> M{N}". Niedrige recalc'te srs_max (< SC_GATE) -> I-Familie (M2/M3); hoch+experiment -> erneut M5. ${DECISION_NOTE}`,
        { label: `re-modusEntscheidung:${sb.id}`, phase: 'BatchClose' }, MODUS_SCHEMA,
        { modus: modus, modus_begruendung: 'FALLBACK (Re-Entry Schema-Crash-Haertung): Re-Decide-Agent lieferte kein valides JSON -> behalte den Erst-Modus (kein Faken eines Modus-Wechsels).' })
      const re_modus = (reModusOut && reModusOut.modus) || modus
      const re_fam = modusFamily(re_modus)
      log(`[dispatch_implement] ${sb.id}: RE-MODUS NACH Recalc = ${re_modus} (${re_fam}) — ${(reModusOut && reModusOut.modus_begruendung) || ''}`)

      // ── BL-238 AK-3 (A_SC_I Motor-Branch, dispatch_implement.js) ────────────────────────────
      // Verzweigung auf modusFamily(re_modus): I-Familie => A_SC_I-Vollzug (runImplementStage 'I_FULL',
      // PT-GEN-LeadFollow vom regulaeren M2/M3-Dispatch :339); weiterhin SC => erneute SC-Runde via
      // Loop-Re-Entry, GEDECKELT durch recalcRounds/MAX_RECALC_ROUNDS (AK-9/B-2 — derselbe Zaehler oben,
      // kein ungedeckelter Pendel-Loop). Outcome an den Lead via results.push (INV-MOTOR-2, kein Engine-Schluck).
      if (re_fam === 'I_FULL' || re_fam === 'I_SKELETON') {
        // A_SC_I-Vollzug: SC saettigte -> recalc senkte SRS -> re-modus M2/M3 -> jetzt I implementieren.
        await runImplementStage(sb, current_stage, re_modus, 'I_FULL')
        batchOutcome = 'A_SC_I_DONE'
        results.push({ sub_batch: sb.id, modus, re_modus, a_sc_i: 'I_FULL', outcome: batchOutcome, completed_stages: completed, sc_verdict, recalc_rounds: priorRecalc + 1 })
        return { ctl: 'continue' }   // weiter mit naechstem Sub-Batch (A_SC_I vollzogen)
      }
      if (modusFamily(re_modus) === 'SC') {
        // re-modus weiterhin SC (hohe recalc'te SRS + experiment-offen): erneute SC-Runde. Der recalcRounds-Cap
        // (AK-9) ist die Schranke — der naechste outer-Durchlauf zaehlt denselben recalcRounds.get(sb.id) hoch
        // und terminiert fail-loud bei > MAX_RECALC_ROUNDS (kein ungedeckelter M5<->re-modus-Pendel).
        batchOutcome = 'SC_RE_ENTRY'
        results.push({ sub_batch: sb.id, modus, re_modus, a_sc_i: 'SC_RE_ENTRY', outcome: batchOutcome, completed_stages: completed, sc_verdict, recalc_rounds: priorRecalc + 1 })
        return { ctl: 'continue' }   // erneute SC-Runde im naechsten outer-Durchlauf (AK-9 recalcRounds-gedeckelt)
      }

      batchOutcome = (batchOutcome === 'BATCH_DONE') ? batchOutcome : 'SC_RECALC_DONE'
      results.push({ sub_batch: sb.id, modus, re_modus, outcome: batchOutcome, completed_stages: completed, sc_verdict })
      return { ctl: 'continue' }   // weiter mit naechstem Sub-Batch (kein ABORT)
    }
    if (sc_verdict === 'ABORT') {
      // sc_verdict==ABORT -> bestehender fail-safe-Pfad: kein runPhase3, Outer-Loop beenden wie HEAD 24bbf75
      // (Kanarienvogel :351-355 — kein Verhaltens-Change). break outer.
      batchOutcome = 'ABORT'
      terminated_reason = 'sc_verdict_abort'
      results.push({ sub_batch: sb.id, modus, outcome: batchOutcome, completed_stages: completed, sc_verdict })
      return { ctl: 'break' }
    }
  }

  // --- Phase 3.x NUR bei sauberem BATCH_DONE (C5) ---
  if (batchOutcome === 'BATCH_DONE') {
    phase('BatchClose')
    // BL-230 SB-5 (AK-GUARD-PERSIST, S-GP-1/AON-GP-PHASE3-REPLAY): das Phase-3-Quartett ist idempotent ueber
    // Laeufe. Hat der persistente Manifest-Marker phase3_fired_per_batch[id] (via A.phase3_fired_seed geseedet)
    // diesen Sub-Batch bereits als ge-feuert markiert, ueberspringt der Motor bei Fresh-Replay das ZWEITE
    // runPhase3 (kein Doppel-recalibrate/postItem/statusTransition/modelSync-Quartett). EC-GP-2: derselbe Key
    // wie der SC-Saettigungs-Guard (phase3_fired). S-GP-3 (Null-Regression OFF): ohne Seed ist phase3_fired
    // leer -> das Quartett feuert normal (==4, BL-238 byte-identisch), DANACH ist der Marker gesetzt.
    if (!phase3_fired.has(sb.id)) {
      phase3_fired.add(sb.id)
      await runPhase3(sb)
    } else {
      log(`[dispatch_implement] ${sb.id}: BATCH_DONE phase3_fired (persistenter Seed A.phase3_fired_seed) — kein erneutes Phase-3-Quartett (AK-GUARD-PERSIST, Fresh-Replay kein Doppel-Feuer).`)
    }
    // BL-285 AK-2 Outcome+GREEN-Beleg-Persist (Motor-owned, guard-clean). batchOutcome lebte bisher nur im
    // Workflow-Return (in-memory) -> hier ins Manifest spiegeln. OQ#2-Korrektur: GREEN-Beleg = letzter Suite-Status
    // + Timestamp (NICHT ein test_results_hash, den der Agent ohne stabiles Artefakt erfinden wuerde).
    await agent(`Persistiere BL-285-AK-2-Outcome fuer Sub-Batch ${sb.id} ins Vault-Manifest — INV-2 Write-Isolation, KEIN Code, `
      + `KEIN batch_modes/modus-Write (INV-MODUS-1).\n`
      + `1) DF_BATCH_STATE.modus_outcome_per_batch[${JSON.stringify(sb.id)}] = "BATCH_DONE".\n`
      + `2) DF_BATCH_STATE.green_verified_per_batch[${JSON.stringify(sb.id)}] = { verified: true, evidence: <letzter _TDD_execute/_I_verify Suite-Status als kurzer Text>, evidence_at, mode: <tdd|scenario|convention> } — der zuletzt beobachtete Verify-Status (KEIN erfundener Hash).\n`
      + `   BL-319 AK-2 SET-ONCE (Idempotenz): den evidence-Timestamp (evidence_at ??= ISO-now) NUR setzen wenn der Slot noch leer/nicht gesetzt ist — bei 2x-Lauf den bestehenden Timestamp BEIBEHALTEN (kein <ISO-now>-Drift). ${PATHS}`,
      { label: `persistOutcome:${sb.id}`, phase: 'BatchClose', model: 'sonnet' })
    // BL-299 AK-1 BATCH_DONE-Seam: normierter, gate-gepruefter Produkt-Commit der LETZTEN Stage NACH runPhase3
    // (faengt auch die von Phase 3.x + persistOutcome geschriebenen Vault-/PL-Updates). Heilt den verwaisten
    // Vertrag von _SDF_berater_batchEnde ('stage_orchestrate wurde BEREITS aufgerufen') — jetzt traegt der Motor ihn.
    await runStageCommit(sb, (completed.length ? completed[completed.length - 1] : 'final'), true)
  }
  results.push({ sub_batch: sb.id, modus, outcome: batchOutcome, completed_stages: completed })
  if (batchOutcome !== 'BATCH_DONE') return { ctl: 'break' }  // Abbruch/Halt -> Outer-Loop beenden
  return { ctl: 'continue' }
  } catch (sbErr) {
    // BL-319 AK-3: ein geworfener Fehler (Build-Crash, Decision-Agent-Throw) isoliert auf DIESEN Sub-Batch.
    // Geschwister laufen weiter (continue, KEIN break outer). Outcome=failed mit Fehler-Text, re-runnable beim
    // Resume (T-PF-2: derselbe Sub-Batch konvergiert im naechsten Lauf zu completed). Idempotent gegen results:
    // ein evtl. schon gepushtes Teil-Outcome desselben Sub-Batches ueberschreiben wir nicht — wir HAENGEN das
    // failed-Outcome an (der juengste Eintrag pro Sub-Batch ist im Fan-In-Aggregat der maszgebliche, s.u.).
    const errMsg = String((sbErr && sbErr.message) || sbErr).slice(0, 200)
    log(`[dispatch_implement] AK-3 PARTIAL-FAILURE: Sub-Batch ${sb.id} warf (${errMsg}) — isoliert als outcome=failed, Geschwister laufen weiter (kein break outer, BL-319).`)
    results.push({ sub_batch: sb.id, outcome: 'failed', error: errMsg })
    return { ctl: 'continue' }
  }
}

// ===========================================================================
// HAUPTSCHLEIFE-DRIVER (BL-230 AK-MOTOR-WELLE): zwei Pfade ueber DIESELBE processSubBatch-Funktion.
//   effective_fanout==1 -> SERIELLER for-Loop (OFF byte-identisch, Null-Regression QG-4).
//   effective_fanout>1  -> parallel()-Fan-Out in Chunks von effective_fanout (Thunk-Array, NEBENLAEUFIG),
//                          results in EINGABE-Reihenfolge; runFanInBarrier GENAU 1x SERIELL nach den Chunks.
// Partial-Failure (BL-319 AK-3): processSubBatch wirft NIE (try/catch intern -> failed-Outcome) — auch im
// Parallel-Pfad ist 1 toter Batch != Welle tot.
// ===========================================================================
let fan_in_barrier_marker = false
let commit_seam_marker     // BL-230 SB-2 AK-COMMIT-SEAM: undefined im seriellen Pfad (CS-4 Null-Regression)
if (effective_fanout > 1) {
  // PARALLEL-PFAD: Chunks der Welle, jeder Chunk via parallel()-Thunk-Array nebenlaeufig.
  // BL-230 SB-5 (AK-MODI-SCOPE, S-MS-2/AON-MS-PARTITION): die Plan-Zeit-Modus-Quelle (A.batch_modes_hint,
  // EC-MS-1 — KONSERVATIV, der autoritative Modus entscheidet _SDF_berater_modusEntscheidung erst IM Fan-Out,
  // INV-MODUS-1). modusOf(sb) liefert den HINT (fehlt -> '' -> fail-safe NICHT eligible -> seriell).
  const batch_modes_hint = (A.batch_modes_hint && typeof A.batch_modes_hint === 'object') ? A.batch_modes_hint : {}
  const modusHintOf = (sb) => String(batch_modes_hint[sb.id] || sb.modus_hint || '').toUpperCase().trim()
  // BL-230 SB-5 (AK-EXCL-SEMAPHOR, S-ES-1/EC-ES-1/EC-ES-2): EIN 1-Slot-EXCLUSIVE-Semaphor PRO BL. Das IST die
  // truth_lease (EC-ES-2: 1 Lease-Slot = 1 EXCLUSIVE-Slot/BL; physisch factory_lock.truth_lease — hier der Motor-
  // Seitige In-Lauf-Spiegel der Belegung). Der erste M5/EXCLUSIVE-Batch belegt ihn; ein zweiter M5 bei besetztem
  // Slot wird DEFERRT (outcome='deferred' -> classifyOutcome -> blocked), NON-BLOCKING (kein Throw, kein Anhalten
  // der Welle). Geschwister bauen read-pinned (pinned_at_round-Marker, S-TL-2/AON-TL-PINNED).
  let exclusive_semaphor_held = false   // 1-Slot-Semaphor (== truth_lease) pro BL — Defer-bei-besetzt (S-ES-1)
  let truth_lease_round = 0             // pinned_at_round-Marker-Quelle fuer read-pinned Geschwister (S-TL-2)
  // Eine Welle "neben einem M5" baut read-pinned: setze den pinned_at_round-Marker fuer ein Geschwister, das
  // nebenlaeufig zu einem aktiven truth_lease (M5) gebaut wird. INV-MOTOR-1: 1 agent = 1 Step.
  async function pinSiblingReadPinned(sb, round) {
    await agent(`Baue Sub-Batch ${sb.id} READ-PINNED (BL-230 SB-5 AK-TRUTH-LEASE, S-TL-2): nebenlaeufig zu diesem Batch haelt ein M5-Batch die `
      + `truth_lease (klaert unsicheres W{n}). Lies AUSSCHLIESSLICH den EINGEFRORENEN Truth-Snapshot (pinned_at_round=${round}, read-pinned), `
      + `NICHT den live mutierenden — die Fan-In-Barrier-Truth-Revalidierung (Schritt 4) revalidiert deinen pinned_at_round=${round}-Stand `
      + `gegen den frisch verschmolzenen Truth-Stand (built_on_stale_truth-Reval). ${CTX}. ${PATHS}`,
      { label: `pinReadPinned:${sb.id}`, phase: 'Modus', model: 'sonnet' })
  }
  outerParallel:
  for (let i = 0; i < SUB_BATCHES.length; i += effective_fanout) {
    if (outerRounds > MAX_SUBBATCH_ROUNDS) {   // Cap-Check VOR dem Chunk (analog seriell: erst pruefen, dann verarbeiten)
      terminated_reason = 'max_subbatch_rounds_exceeded'
      log(`[dispatch_implement] HARD-CAP: > ${MAX_SUBBATCH_ROUNDS} Sub-Batch-Rounds — fail-safe TERMINATE.`)
      break
    }
    const chunk = SUB_BATCHES.slice(i, i + effective_fanout)   // <= effective_fanout (AON-7-Cap respektiert via Chunk-Groesse)
    outerRounds += chunk.length
    // BL-230 SB-5 (AK-MODI-SCOPE, EC-MS-1): die Modus-Scope-Partitionierung greift NUR, wenn eine Plan-Zeit-
    // Modus-Quelle (A.batch_modes_hint) UEBERHAUPT vorhanden ist. Fehlt sie KOMPLETT (kein hint), bleibt der
    // Fan-Out BYTE-IDENTISCH zum SB-1a-Verhalten (ganzer Chunk in EINEM parallel()-Array, AON-2/AON-3/AON-7).
    // Der konservativ-NICHT-eligible-Default (EC-MS-1) gilt PRO Batch, wenn der hint-MAP existiert aber einen
    // Batch nicht nennt — NICHT als globaler Serialisierungs-Hebel ohne jede Modus-Information.
    const hasHintSource = Object.keys(batch_modes_hint).length > 0
    if (!hasHintSource) {
      const grpSignals = await parallel(chunk.map(sb => () => processSubBatch(sb)))
      for (const sig of grpSignals) {
        if (sig && sig.ctl === 'return') {
          const fb = await runFanInBarrier(SUB_BATCHES.map(s => s.id))
          return Object.assign({}, sig.value, { fan_in_barrier: true, commit_seam: fb && fb.commit_seam })
        }
      }
      if (grpSignals.some(sig => sig && sig.ctl === 'break')) break outerParallel
      continue
    }
    // BL-230 SB-5 (AK-MODI-SCOPE S-MS-2 + AK-EXCL-SEMAPHOR S-ES-1): Chunk-Partitionierung nach Modus-Eligibility.
    //   eligibleGroup  = nur PARALLEL-Modi (M2/M3) -> EIN gemeinsames parallel()-Thunk-Array (Multi-Thunk erlaubt).
    //   serialSingles  = nicht-eligible (M1/M4-M7/M8/M9 + fehlender Hint) -> je EIN Single-Thunk-parallel()-Aufruf
    //                    (NIE nebenlaeufig mit anderen). M5/EXCLUSIVE durchlaeuft zusaetzlich den Semaphor (Defer).
    const eligibleGroup = []
    const serialSingles = []
    const deferredHere = []
    const signals = []
    for (const sb of chunk) {
      const cls = modusConcurrencyClass(modusHintOf(sb))
      if (cls === 'EXCLUSIVE') {
        // M5/EXCLUSIVE -> 1-Slot-Semaphor (== truth_lease, EC-ES-2). acquire-or-defer, non-blocking.
        if (exclusive_semaphor_held) {
          // 2. M5 bei besetztem Slot -> DEFERRT (blocked, KEIN Throw, KEIN Anhalten — S-ES-1/AON-ES-DEFER).
          log(`[dispatch_implement] AK-EXCL-SEMAPHOR: ${sb.id} (M5/EXCLUSIVE) bei besetztem 1-Slot-Semaphor (== truth_lease) -> deferred (blocked, non-blocking, kein Throw).`)
          results.push({ sub_batch: sb.id, modus: 'M5', outcome: 'deferred', deferred_reason: 'exclusive_semaphor_held (truth_lease besetzt, EC-ES-2)' })
          deferredHere.push(sb.id)
        } else {
          // 1. M5 belegt den Semaphor (== truth_lease genommen). Geschwister bauen read-pinned (S-TL-2).
          exclusive_semaphor_held = true
          truth_lease_round += 1
          serialSingles.push(sb)   // M5 selbst seriell (EXCLUSIVE, NIE im Multi-Thunk-Array)
        }
      } else if (cls === 'PARALLEL') {
        eligibleGroup.push(sb)
      } else {
        serialSingles.push(sb)     // M1/M4/M6/M7/M8/M9 + fehlender Hint -> seriell (Single-Thunk)
      }
    }
    // S-TL-2 (AON-TL-PINNED): haelt ein M5 im Lauf die truth_lease, bauen die Geschwister (eligible + serielle
    // Nicht-M5) read-pinned (pinned_at_round-Marker). Marker-SETZUNG ist Motor-Seite + Unit-testbar.
    if (exclusive_semaphor_held && truth_lease_round > 0) {
      for (const sb of eligibleGroup) await pinSiblingReadPinned(sb, truth_lease_round)
      for (const sb of serialSingles) { if (modusConcurrencyClass(modusHintOf(sb)) !== 'EXCLUSIVE') await pinSiblingReadPinned(sb, truth_lease_round) }
    }
    // eligible M2/M3 -> EIN parallel()-Aufruf (Multi-Thunk wenn >=2; Single-Thunk wenn ==1; gar nicht wenn leer).
    if (eligibleGroup.length > 0) {
      const grpSignals = await parallel(eligibleGroup.map(sb => () => processSubBatch(sb)))
      for (const s of grpSignals) signals.push(s)
    }
    // nicht-eligible -> je EIN Single-Thunk-parallel()-Aufruf (count==1, NIE nebenlaeufig mit anderen).
    for (const sb of serialSingles) {
      const [s] = await parallel([() => processSubBatch(sb)])
      signals.push(s)
      // M5 baut fertig -> Semaphor (== truth_lease) wieder frei fuer einen Folge-M5 in der naechsten Welle.
      if (modusConcurrencyClass(modusHintOf(sb)) === 'EXCLUSIVE') exclusive_semaphor_held = false
    }
    for (const sig of signals) {
      if (sig && sig.ctl === 'return') {
        // split_required / test_conflict: ganzer Workflow returnt sofort — aber ERST nach Fan-In der laufenden Welle.
        const fb = await runFanInBarrier(SUB_BATCHES.map(s => s.id))
        return Object.assign({}, sig.value, { fan_in_barrier: true, commit_seam: fb && fb.commit_seam })
      }
    }
    // 'break'-Signal (HALT/ABORT/Cap) terminiert die Outer-Schleife NACH dem Chunk (Geschwister im Chunk liefen zu Ende).
    if (signals.some(sig => sig && sig.ctl === 'break')) break outerParallel
  }
  // Fan-In-Barrier GENAU 1x SERIELL, NACH dem letzten parallel()-await, VOR loopDecision (AON-6).
  const fb = await runFanInBarrier(SUB_BATCHES.map(s => s.id))
  fan_in_barrier_marker = true
  commit_seam_marker = fb && fb.commit_seam   // BL-230 SB-2: 'merged' (repo da) / 'na_repo_absent' (git-los)
} else {
  // SERIELLER PFAD (OFF / fanout==1): byte-identisch zum bisherigen Verhalten — kein parallel()-Aufruf (AON-1/EC-1-GUARD).
  for (const sb of SUB_BATCHES) {
    outerRounds++
    if (outerRounds > MAX_SUBBATCH_ROUNDS) {
      terminated_reason = 'max_subbatch_rounds_exceeded'
      log(`[dispatch_implement] HARD-CAP: > ${MAX_SUBBATCH_ROUNDS} Sub-Batch-Rounds — fail-safe TERMINATE.`)
      break
    }
    const sig = await processSubBatch(sb)
    if (sig && sig.ctl === 'return') return sig.value
    if (sig && sig.ctl === 'break') break
    // 'continue' (oder kein Signal) -> naechster Sub-Batch
  }
}

// --- BL-319 AK-3: Fan-In-Aggregation ueber ALLE Sub-Batch-Outcomes ---
// Statt break-outer-Fail-Fast aggregiert der Motor am Fan-In jeden Sub-Batch in genau einen Bucket
// {completed, failed, blocked}. Ein toter Batch (outcome=failed) beendet NUR sich selbst — er erscheint
// hier als failed, die Geschwister als completed. Diese Aggregations-Regel ist der Input fuer die
// BL-230-A-Pipeline (parallele Welle: 1 toter Batch != Welle tot). Klassifikation pro Sub-Batch nach
// dem JUENGSTEN results-Eintrag (Resume/Re-Entry: der letzte Outcome ist der maszgebliche).
// BL-230 SB-2 (AK-PARTIAL-FAILURE): das per_batch_outcome-Enum als BENANNTE Single-Source der drei
// Klassifikations-Buckets. GENAU 3 Werte {completed, failed, blocked} — kein vierter, kein Roh-String
// ausserhalb des Enums. classifyOutcome mappt AUSSCHLIESSLICH auf diese Enum-Werte.
const PER_BATCH_OUTCOME = Object.freeze({ COMPLETED: 'completed', FAILED: 'failed', BLOCKED: 'blocked' })
function classifyOutcome(o) {
  const COMPLETED = ['BATCH_DONE', 'A_SC_I_DONE', 'SC_RECALC_DONE', 'special_path']
  const FAILED = ['failed', 'ABORT', 'ABORT_max_stage_iters', 'stage_abort', 'recalc_cap_exceeded', 'sc_verdict_abort']
  // BL-230 SB-5 (AK-EXCL-SEMAPHOR, S-ES-2/AON-ES-ENUM): der M5-EXCLUSIVE-Semaphor (== truth_lease, EC-ES-2)
  // markiert einen 2. M5 bei besetztem 1-Slot-Semaphor als 'deferred' (non-blocking Defer, KEIN Throw). Das
  // mappt EXPLIZIT auf den BLOCKED-Bucket — Defer != Failure (Welle nicht tot, deferred-Batch landet in
  // fan_in.blocked + Resume-Liste). KEIN vierter Enum-Wert: das Enum bleibt GENAU 3-wertig {completed,failed,blocked}.
  const BLOCKED_EXPLICIT = ['deferred']   // semaphor/truth_lease-deferred M5 (EXCLUSIVE-Slot besetzt) -> blocked
  if (COMPLETED.includes(o)) return PER_BATCH_OUTCOME.COMPLETED
  if (FAILED.includes(o)) return PER_BATCH_OUTCOME.FAILED
  if (BLOCKED_EXPLICIT.includes(o)) return PER_BATCH_OUTCOME.BLOCKED
  return PER_BATCH_OUTCOME.BLOCKED   // re_cut_required / green_blocked_test_conflict / HALT / SC_RE_ENTRY / unbekannt
}
// BL-230 SB-2 (AK-CORRELATION): reine Funktion — klassifiziert die FEHLERKLASSE eines failed-Outcomes
// ueber den error-Text (Bucketing nach Klasse, NICHT Roh-String-Identitaet). Erweiterbar (keine
// erschoepfende Taxonomie — SB-2 baut nur den Mechanismus). Self-contained (eval-faehig, kein Closure-Bezug).
function errorClassOf(outcome) {
  const txt = String((outcome && (outcome.error || outcome.outcome)) || '').toLowerCase()
  if (/rate.?limit|429|too many requests|slow down|session.?limit/.test(txt)) return 'rate_limit'
  if (/typeerror/.test(txt)) return 'type_error'
  if (/syntaxerror/.test(txt)) return 'syntax_error'
  if (/oom|out of memory|heap/.test(txt)) return 'oom'
  if (/timeout|timed out|etimedout/.test(txt)) return 'timeout'
  if (!txt) return 'unknown'
  return 'other:' + txt.slice(0, 24)
}
// BL-230 SB-2 (AK-CORRELATION): reine Funktion ueber die Welle-results. >=50% der Batches mit GLEICHER
// Fehlerklasse (50% inklusiv) -> Signal 'wave_abort_retry' (Wellen-Abort + EIN Retry der GANZEN Welle,
// NICHT N einzelne re_cut). Retry-Cap == 1: ein zweiter Korrelations-Abort derselben Welle (retry_count>=1)
// terminiert fail-loud ('correlated_wave_abort_exhausted'). Korrelation braucht >=2 Batches (|welle|==1 -> kein Abort).
// Self-contained (eval-faehig im Test-Harness, kein Closure-Bezug auf errorClassOf — Klassifikation inline).
function correlatedFailureClass(results, opts) {
  const retry_count = (opts && Number.isInteger(opts.retry_count)) ? opts.retry_count : 0
  const classOf = (outcome) => {
    const txt = String((outcome && (outcome.error || outcome.outcome)) || '').toLowerCase()
    if (/rate.?limit|429|too many requests|slow down|session.?limit/.test(txt)) return 'rate_limit'
    if (/typeerror/.test(txt)) return 'type_error'
    if (/syntaxerror/.test(txt)) return 'syntax_error'
    if (/oom|out of memory|heap/.test(txt)) return 'oom'
    if (/timeout|timed out|etimedout/.test(txt)) return 'timeout'
    if (!txt) return 'unknown'
    return 'other:' + txt.slice(0, 24)
  }
  const real = (results || []).filter(Boolean)
  const total = real.length
  const failed = real.filter(r => String(r.outcome) === 'failed')
  const counts = {}
  for (const f of failed) { const c = classOf(f); counts[c] = (counts[c] || 0) + 1 }
  let topClass = null, topCount = 0
  for (const c of Object.keys(counts)) { if (counts[c] > topCount) { topCount = counts[c]; topClass = c } }
  // Korrelation braucht >=2 Batches in der Welle (1 toter Batch == normaler Partial-Failure, kein Wellen-Abort).
  const correlated = total >= 2 && topCount >= 1 && (topCount / total) >= 0.5
  if (!correlated) {
    return { signal: null, correlated: false, dominant_class: topClass, dominant_count: topCount, total }
  }
  if (retry_count >= 1) {
    // Retry-Cap erschoepft -> fail-loud, KEIN dritter Lauf.
    return { signal: 'correlated_wave_abort_exhausted', terminated_reason: 'correlated_wave_abort_exhausted', correlated: true, dominant_class: topClass, retry_count }
  }
  // Erster Korrelations-Abort: GENAU 1 Wellen-Retry-Signal (NICHT N re_cut_target pro totem Batch).
  return { signal: 'wave_abort_retry', terminated_reason: 'correlated_wave_abort', correlated: true, dominant_class: topClass, retry_count, re_cut_targets: [] }
}
// BL-230 SB-3a (AK-FANIN-COMMUTATIVE / INV-FANIN-COMMUTATIVE-1, KOM-2): reine Funktion "Widerlegung gewinnt".
// Bei gegenlaeufiger W{n}-Mutation gewinnt der SCHWAECHERE Wahrheits-Grad (Minimum der Grad-Ordnung). Das Minimum
// einer Menge ist permutations-invariant -> reihenfolge-unabhaengig + idempotent. Grad-Ordnung (stark -> schwach):
// BESTAETIGT > TENTATIV > HYPOTHESE > OFFEN/WIDERLEGT (OFFEN == WIDERLEGT, beide schwaechster Grad). Leere Menge ->
// definierter Default ('OFFEN', kein Crash). Self-contained (eval-faehig im Test-Harness via extractFn, kein
// Closure-Bezug); top-level function mit schliessender Klammer auf Spaltenebene (extractFn-Regex /function ...\n}/).
function weakestTruthGrade(grades) {
  // Rang: kleiner = schwaecher (gewinnt). OFFEN und WIDERLEGT teilen den schwaechsten Rang 0.
  const RANK = { 'WIDERLEGT': 0, 'OFFEN': 0, 'HYPOTHESE': 1, 'TENTATIV': 2, 'BESTAETIGT': 3 }
  const DEFAULT_GRADE = 'OFFEN'   // leere Menge -> definierter Default (kein Crash), schwaechster Grad
  const list = Array.isArray(grades) ? grades.filter(g => typeof g === 'string') : []
  if (list.length === 0) return DEFAULT_GRADE
  let weakest = null, weakestRank = Infinity
  for (const g of list) {
    const key = String(g).toUpperCase().trim()
    const r = (key in RANK) ? RANK[key] : 0   // unbekannter Grad -> schwaechster Rang (fail-safe "Widerlegung gewinnt")
    if (r < weakestRank) { weakestRank = r; weakest = key }
  }
  return weakest
}
// BL-230 SB-4 (AK-PARALLEL-SAFE, k=70): reines Vier-Faktor-Praedikat parallelSafe(A,B) =
//   dep_disjoint ∧ file_disjoint ∧ truth_disjoint ∧ ¬experiment_coupled (Model W8). Reine Funktion,
//   state-frei, eval-faehig (extractFn-Regex /function ...\n}/, schliessende Klammer auf Spaltenebene).
//   truth_disjoint: geteiltes BESTAETIGT-W{n} ist harmlos (weight 0.0); ein geteiltes UNSICHERES W{n}
//   (TENTATIV/HYPOTHESE/OFFEN/WIDERLEGT, shared_uncertain) verbietet Parallelitaet. Disjunkte W_refs => sicher.
function parallelSafe(A, B) {
  const a = A || {}, b = B || {}
  // dep_disjoint: explizites Faktor-Feld ODER abgeleitet aus depends_on (keine wechselseitige Kante).
  const depDisjoint = (a.dep_disjoint != null || b.dep_disjoint != null)
    ? (a.dep_disjoint !== false && b.dep_disjoint !== false)
    : !(((a.depends_on || []).indexOf(b.id) >= 0) || ((b.depends_on || []).indexOf(a.id) >= 0))
  // file_disjoint: explizites Faktor-Feld ODER abgeleitet aus files-Schnitt (kein geteilter Pfad).
  const fa = Array.isArray(a.files) ? a.files : [], fb = Array.isArray(b.files) ? b.files : []
  const fileDisjoint = (a.file_disjoint != null || b.file_disjoint != null)
    ? (a.file_disjoint !== false && b.file_disjoint !== false)
    : !fa.some(f => fb.indexOf(f) >= 0)
  // experiment_coupled: M5/EXCLUSIVE-Kopplung (¬experiment_coupled greift) — explizit ODER aus concurrency_class.
  const expCoupled = (a.experiment_coupled === true || b.experiment_coupled === true
    || a.is_experiment === true || b.is_experiment === true
    || a.concurrency_class === 'EXCLUSIVE' || b.concurrency_class === 'EXCLUSIVE')
  // truth_disjoint: aus W_refs ableiten — geteiltes W{n} mit UNSICHEREM Status => shared_uncertain => verboten;
  // geteiltes W{n} BESTAETIGT (weight 0.0) => harmlos; explizites truth_disjoint-Faktor-Feld hat Vorrang.
  let truthDisjoint
  if (a.truth_disjoint != null || b.truth_disjoint != null) {
    truthDisjoint = (a.truth_disjoint !== false && b.truth_disjoint !== false)
  } else {
    const refsA = Array.isArray(a.W_refs) ? a.W_refs : [], refsB = Array.isArray(b.W_refs) ? b.W_refs : []
    const statusOf = (w) => String((w && (w.status || w.grade)) || 'OFFEN').toUpperCase().trim()
    const idOf = (w) => (w && (w.id || w.W || w)) // String oder {id,status}
    let sharedUncertain = false
    for (const wa of refsA) {
      for (const wb of refsB) {
        if (idOf(wa) === idOf(wb)) {
          // geteiltes W{n}: BESTAETIGT harmlos, alles andere (TENTATIV/HYPOTHESE/OFFEN/WIDERLEGT) verbietet.
          if (statusOf(wa) !== 'BESTAETIGT' || statusOf(wb) !== 'BESTAETIGT') sharedUncertain = true
        }
      }
    }
    truthDisjoint = !sharedUncertain
  }
  const safe = depDisjoint && fileDisjoint && truthDisjoint && !expCoupled
  return { parallel_safe: safe, safe, dep_disjoint: depDisjoint, file_disjoint: fileDisjoint, truth_disjoint: truthDisjoint, experiment_coupled: expCoupled }
}
// BL-230 SB-4 (AK-GO-PARALLEL-FN, k=76): reine Funktion goParallel(ctx) — die Gate-Kette + 5 W10-Fallbaecke,
//   NUR-SENKEN-Invariante (W9). GO_PARALLEL-Bedingung = G0∧G1-R∧G3∧G4∧G5∧G6 ∧ alle Batches PARALLEL ∧
//   |welle|>=MIN_FANOUT(2) ∧ Σgroesse>=WORKTREE_OVERHEAD_THRESHOLD ∧ kein parallel_safe-Verstoss ∧ kein SRS-Alarm.
//   Gruen -> effective_fanout = min(nr, |welle|, MAX_CONCURRENT) (NIE darueber). Jeder der 5 Fallbaecke
//   (Gate-rot / DEPENDS-EXCLUSIVE / File-Overlap-nicht-parallelSafe / Welle-zu-klein / SRS-Alarm) -> SERIELL (1).
//   Reine Funktion, state-frei, eval-faehig (extractFn). parallel_mode=false => hart 1 (OFF dominiert).
function goParallel(ctx) {
  const c = ctx || {}
  const MIN_FANOUT = 2                        // Overhead-Schwelle: < 2 Batches lohnt kein Worktree-Fan-Out
  const WORKTREE_OVERHEAD_THRESHOLD = 2       // Σgroesse-Mindestmasse (Worktree-Overhead > Parallel-Gewinn darunter)
  const MAX_CONCURRENT_CAP = (Number.isInteger(c.max_concurrent) && c.max_concurrent >= 1) ? c.max_concurrent : 16
  const SERIELL = { effective_fanout: 1, go_parallel: false }
  // OFF dominiert: parallel_mode=false -> hart seriell (Null-Regression QG-4, byte-identisch).
  if (c.parallel_mode !== true) return SERIELL
  // Gate-Kette G0..G6 (alle gruen erforderlich) — gates-Map ODER Einzel-Flags.
  const g = c.gates || {}
  const gateGreen = (key, flag) => (g[key] !== false) && (flag !== false)
  const gatesOk = gateGreen('G0', c.G0_armed) && gateGreen('G1', c.G1_reader) && gateGreen('G3', c.G3_worktree)
    && gateGreen('G4', c.G4_idempotent) && gateGreen('G5', c.G5_file_disjoint) && gateGreen('G6', c.G6_post_multiplex)
  if (!gatesOk) return SERIELL                                              // Fallback 1: Gate rot
  // alle Batches concurrency_class==PARALLEL (kein DEPENDS/EXCLUSIVE).
  const classes = Array.isArray(c.concurrency_classes) ? c.concurrency_classes : []
  const allParallel = (c.all_parallel !== false) && classes.every(k => k === 'PARALLEL')
  if (!allParallel) return SERIELL                                         // Fallback 2: DEPENDS/EXCLUSIVE
  // parallel_safe ueber alle Paare (File-Overlap / shared_uncertain) — Aggregat-Flag parallel_safe_all.
  if (c.parallel_safe_all === false || c.file_disjoint === false) return SERIELL   // Fallback 3: nicht-parallelSafe-Paar
  // Welle-Groesse: |welle|>=MIN_FANOUT UND Σgroesse>=THRESHOLD.
  const welle = (c.welle_size != null) ? c.welle_size : (c.wave_size != null ? c.wave_size : classes.length)
  const sum = (c.sum_groesse != null) ? c.sum_groesse : (c.sum_size != null ? c.sum_size : (c.total_size != null ? c.total_size : 0))
  if (!(welle >= MIN_FANOUT) || !(sum >= WORKTREE_OVERHEAD_THRESHOLD)) return SERIELL   // Fallback 4: Welle zu klein
  // SRS-Alarm / K-Score waechst (Unsicherheit steigt) -> kleinerer Ring, NICHT parallelisieren (W2).
  if (c.srs_alarm === true || c.k_score_growing === true) return SERIELL   // Fallback 5: SRS-Alarm
  // GO_PARALLEL gruen: NUR-SENKEN-Invariante (W9) — min(nr, |welle|, MAX_CONCURRENT). Heben unmoeglich.
  const nr = (Number.isInteger(c.nr_parallel_batches) && c.nr_parallel_batches >= 1) ? c.nr_parallel_batches : 1
  const ef = Math.min(nr, welle, MAX_CONCURRENT_CAP)
  return { effective_fanout: Math.max(1, ef), go_parallel: ef > 1 }
}
// BL-230 SB-5 (AK-MODI-SCOPE, k=63, S-MS-1/AON-MS-FN-PURE/M5-EXCLUSIVE): reine, state-freie Funktionen,
// die pro Execution-Modus (M1..M9) die Parallel-Eligibility klassifizieren. KEIN State, eval-faehig
// (extractFn/globalThis-Export analog goParallel/parallelSafe). Die Fan-Out-Partitionierung nutzt sie, damit
// M1/M4-M7/M5/M8-M9 NIE nebenlaeufig mit anderen Batches laufen (INV-MODUS-Scope auf Plan-Zeit-Ebene).
//   M2/M3 (I-Familie code-with-test / tdd)        -> eligible (parallel)
//   M1     (Skelett, Dependency-Vorbedingung)     -> NICHT eligible (seriell, DEPENDS)
//   M4/M5/M6/M7 (SC-Familie)                       -> NICHT eligible (seriell); M5 zusaetzlich EXCLUSIVE (Semaphor)
//   M8/M9  (SPECIAL-Familie)                       -> NICHT eligible (kein Implement-Kern)
//   unbekannt/fehlend                              -> fail-safe NICHT eligible (im Zweifel SERIELL, vgl. goParallel)
function modusConcurrencyClass(modus) {
  const m = String(modus || '').toUpperCase().trim()
  if (m === 'M5') return 'EXCLUSIVE'                              // M5 klaert unsicheres W{n} -> 1-Slot-Semaphor (== truth_lease, EC-ES-2)
  if (m === 'M2' || m === 'M3') return 'PARALLEL'                 // I-Familie: parallel-faehig
  if (m === 'M1' || m === 'M4' || m === 'M6' || m === 'M7') return 'DEPENDS'   // seriell, aber NICHT EXCLUSIVE (kein Semaphor)
  return 'SERIAL'                                                 // M8/M9 SPECIAL + unbekannt -> fail-safe seriell
}
function modusParallelEligible(modus) {
  const cls = modusConcurrencyClass(modus)
  return { eligible: cls === 'PARALLEL', parallel_eligible: cls === 'PARALLEL', concurrency_class: cls, exclusive: cls === 'EXCLUSIVE' }
}
// BL-230 SB-2 (AK-CORRELATION): die beiden Korrelations-Funktionen sind REIN + projekt-/state-frei.
// Export auf globalThis, damit sie aufrufbar/testbar sind, ohne den Motor (ambiente Globals, top-level
// await) als Modul importieren zu muessen (analog dem Test-Harness, der den Motor als Text laedt + ausfuehrt).
// BL-230 SB-3a: weakestTruthGrade analog mit-exportiert (KOM-2 resolveHelper greift globalThis bevorzugt).
// BL-230 SB-4: goParallel + parallelSafe analog mit-exportiert (GP-/PS-resolveHelper greift globalThis bevorzugt).
// BL-230 SB-5: modusParallelEligible + modusConcurrencyClass analog mit-exportiert (MS-resolveHelper greift globalThis bevorzugt).
try { globalThis.errorClassOf = errorClassOf; globalThis.correlatedFailureClass = correlatedFailureClass; globalThis.weakestTruthGrade = weakestTruthGrade; globalThis.goParallel = goParallel; globalThis.parallelSafe = parallelSafe; globalThis.modusParallelEligible = modusParallelEligible; globalThis.modusConcurrencyClass = modusConcurrencyClass } catch (e) {}
// BL-230 SB-2 (AK-PARTIAL-FAILURE): tote/leere results-Eintraege EXPLIZIT via .filter(Boolean) ziehen,
// damit ein null/undefined-Eintrag NICHT als 'blocked' durchrutscht (Bucket-Summe == reale Batches).
const realResults = results.filter(Boolean)
const lastOutcomeById = new Map()
for (const r of realResults) { if (r && r.sub_batch) lastOutcomeById.set(r.sub_batch, r.outcome) }
const fan_in = { completed: [], failed: [], blocked: [] }
for (const [id, outcome] of lastOutcomeById) fan_in[classifyOutcome(outcome)].push(id)
// BL-230 SB-2 (AK-PARTIAL-FAILURE): RESUME-Liste = NUR die toten (failed) Batches (1 toter Batch != Welle tot).
const resume_targets = fan_in.failed.slice()

// --- Phase 4: loopDecision (Story-Level) — entscheidet ROLLBACK/TERMINATE/SOFT-REPRIO/RE-BATCH ---
phase('LoopDecision')
let loopDecision = null
if (terminated_reason === 'completed') {
  const ld = await safeSchemaAgent(
    `Lade Skill(_SDF_berater_loopDecision) und entscheide auf Story-Level: decision ∈ {ROLLBACK,TERMINATE,SOFT-REPRIO,RE-BATCH}. `
    + `${CTX}. ${PATHS}\n`
    + `BL-319 AK-2 BARRIER (barrier_only / concurrency_class = EXCLUSIVE): loopDecision fuehrt eine destruktive Findings-Rotation auf dem geteilten findings/-Dir aus `
    + `und darf NIE nebenlaeufig laufen (Findings-Rotation-Lock; ohne per-Batch-Namespace wuerden parallele Wellen sich das findings/-Dir zerschiessen). barrier_only=true, exklusiv.\n`
    + `Reihenfolge: neue PL-Items->ROLLBACK; alle Items DONE->TERMINATE; K-Drift>30%->SOFT-REPRIO; sonst RE-BATCH. ${DECISION_NOTE}`,
    { label: `loopDecision:${BL}`, phase: 'LoopDecision' }, LOOP_SCHEMA,
    { decision: 'TERMINATE', reason: 'FALLBACK (Schema-Crash-Haertung): Loop-Decision nach Retry unlesbar -> sicheres TERMINATE (kein blindes RE-BATCH/ROLLBACK).' })
  loopDecision = (ld && ld.decision) || 'TERMINATE'
  log(`[dispatch_implement] loopDecision=${loopDecision} — ${(ld && ld.reason) || ''}`)
}

return {
  bl_id: BL,
  sub_batch_results: results,
  fan_in,                        // BL-319 AK-3: {completed, failed, blocked} — Aggregat fuer BL-230-A-Pipeline (1 toter Batch != Welle tot)
  resume_targets,                // BL-230 SB-2 AK-PARTIAL-FAILURE: == fan_in.failed (nur tote Batches re-runnable)
  commit_seam: commit_seam_marker,   // BL-230 SB-2 AK-COMMIT-SEAM: 'merged'/'na_repo_absent' im parallelen Pfad; undefined seriell (CS-4 Null-Regression)
  terminated_reason,
  loop_decision: loopDecision,   // Lead chaint danach: ROLLBACK/SOFT-REPRIO -> IDF; RE-BATCH -> erneut; TERMINATE -> fertig
  // BL-327 sub_batch_2 (AK-2): Dial-Read an der Wellen-Barrier sichtbar im Return (Observability).
  // effective_fanout wurde GELESEN/BERECHNET/BEOBACHTET, NICHT zum parallelen Spawnen benutzt (kein echter Pfad).
  parallel_mode,
  nr_parallel_batches,
  effective_fanout,
  // BL-230 AK-MOTOR-WELLE (AON-5): Fan-In-Barrier-Marker — true wenn der parallele Fan-Out-Pfad lief
  // (effective_fanout>1) und runFanInBarrier 1x SERIELL nach dem letzten parallel()-await aufgerufen wurde.
  fan_in_barrier: fan_in_barrier_marker,
  note: 'BL-230 AK-MOTOR-WELLE: for->parallel() Fan-Out aktiv (effective_fanout>1 -> Chunks via parallel(); fanout==1 -> serieller Pfad byte-identisch). Fan-In-Barrier (runFanInBarrier) 1x seriell nach den Chunks. Phase 3.x NUR bei BATCH_DONE (C5). modus ausschliesslich von modusEntscheidung (INV-MODUS-1). Caps aktiv (C-B3).',
}
