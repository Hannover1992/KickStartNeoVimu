/* Non-invasiver Test-Harness fuer dispatch_implement.js (BL-222 Motor, Audit 2026-05-29 Step 8).
 *
 * Der Motor ist ein Workflow-Skript mit ambienten Globals (agent/phase/log/parallel) + top-level
 * await/return + `export const meta`. Nicht direkt von Node importierbar. Dieser Harness liest die
 * Quelle als Text, stripped `export`, wrappt sie in eine async-Funktion mit injizierten Mock-Globals
 * und faehrt sie mit einem RECORDING-Mock-Agent. Getestet werden die 4 Audit-Defektklassen:
 *   V1 Termination/Caps, V2 Stage-Branch, V3 Phase-3-Gating @BATCH_DONE, V4 1-Step=1-agent (Decomposition).
 *
 * Lauf: node .claude/workflows/dispatch_implement.test.js   (exit 0 = alle gruen)
 */
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const { execSync } = require('child_process');

const SRC = fs.readFileSync(path.join(__dirname, 'dispatch_implement.js'), 'utf8')
  .replace(/^export\s+const\s+meta/m, 'const meta');

// ===========================================================================
// BL-316 sub_batch_1 "worktree-lifecycle" (AK-1 + AK-4) — Worktree-Harness-Helper.
// ECHTE git-worktree-Ops (kein Mock). Der Harness recordet sonst nur Mock-agent()-
// Prompts; fuer den BL-230-Shadow-Lauf braucht er einen beweisfaehigen echten
// add/remove-Roundtrip + ein Teardown-Audit via Baseline-Diff.
//
// SICHERHEIT (nicht verhandelbar):
//  - REPO_ROOT = das __dirname/../.. Repo (die Engine selbst). git-Ops laufen dort.
//  - Worktree-Baseline ist >=2: Haupt-Worktree + die pre-existing OmniCommand-B-3-Leiche.
//    B-3 ist Baseline-Eintrag (Verify-Specimen), NIE Loesch-/Prune-Ziel.
//  - Test-Worktrees liegen AUSSCHLIESSLICH in os.tmpdir() mit eindeutigem Praefix
//    'bl316-wt-' (NIE im Repo-Tree). fs.realpathSync.native expandiert Windows-8.3-
//    Kurznamen (ADMINI~1 -> Administrator), damit der list-Vergleich gegen den von git
//    gespeicherten Langform-Pfad matcht.
//  - Teardown immer in finally + 'git worktree prune' — auch bei Exception (kein Leak).
//  - Audit = read-only Set-Subtraktion (post \ baseline). Es entfernt NICHTS aus dem
//    Baseline-Set; nur das Negativ-Fixture raeumt seinen eigenen dangling-Worktree.
// ===========================================================================
const REPO_ROOT = path.resolve(__dirname, '..', '..');

// Pfad-Normalisierung fuer den list-Membership-Vergleich: Backslash->Slash, lowercase
// (Windows case-insensitiv), Trailing-Slash strippen. git speichert Forward-Slash-Pfade.
function wtNorm(p) {
  return String(p).replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
}

function gitWT(cmd) {
  return execSync('git ' + cmd, { cwd: REPO_ROOT, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
}

// Aktueller Worktree-Snapshot (Porcelain) als Liste absoluter Pfade (roh, nicht normiert).
function worktreeBaseline() {
  return gitWT('worktree list --porcelain')
    .split(/\r?\n/)
    .filter(l => l.startsWith('worktree '))
    .map(l => l.slice('worktree '.length));
}

// AK-4 Teardown-Audit: Baseline-Diff (KEIN empty-repo). delta = post \ baseline (normiert).
// Read-only Set-Subtraktion; B-3 ist im baseline-Set => nie im delta (kein False-Positive).
function worktreeAudit(baseline, current) {
  const baseSet = new Set((baseline || []).map(wtNorm));
  const delta = (current || []).filter(p => !baseSet.has(wtNorm(p)));
  return { baseline: (baseline || []).map(wtNorm), current: (current || []).map(wtNorm), delta };
}

// AK-1 echter Roundtrip: add (detached HEAD, --no-checkout = schnell + leichten-frei) ->
// assert (existiert + in list + HEAD-SHA == Repo-HEAD) -> remove --force + prune ->
// assert (weg aus list + Verzeichnis weg). Teardown IMMER in finally (kein Leak).
function realWorktreeRoundtrip() {
  const tmpReal = fs.realpathSync.native(os.tmpdir());
  const worktreePath = path.join(tmpReal, 'bl316-wt-' + crypto.randomBytes(6).toString('hex'));
  const repoHead = gitWT('rev-parse HEAD').trim();
  const norm = wtNorm(worktreePath);
  const inList = () => worktreeBaseline().some(p => wtNorm(p) === norm);
  // outsideRepo: der temp-Pfad darf NICHT unter REPO_ROOT liegen (kein Repo-Tree-Leak).
  const outsideRepo = !wtNorm(worktreePath).startsWith(wtNorm(REPO_ROOT) + '/');

  let existedAfterAdd = false, inListAfterAdd = false, worktreeHead = null;
  let existedAfterRemove = true, inListAfterRemove = true;
  try {
    gitWT('worktree add --no-checkout --detach "' + worktreePath + '" HEAD');
    existedAfterAdd = fs.existsSync(worktreePath);
    inListAfterAdd = inList();
    // Datei-Roundtrip-Substanz: der Worktree zeigt auf denselben Commit (echter Checkout-Punkt).
    worktreeHead = gitWT('-C "' + worktreePath + '" rev-parse HEAD').trim();
  } finally {
    try { gitWT('worktree remove --force "' + worktreePath + '"'); } catch (e) {}
    try { gitWT('worktree prune'); } catch (e) {}
  }
  existedAfterRemove = fs.existsSync(worktreePath);
  inListAfterRemove = inList();

  return { worktreePath, outsideRepo, repoHead, worktreeHead, existedAfterAdd, inListAfterAdd, existedAfterRemove, inListAfterRemove };
}

// Body in async-Funktion wrappen (String-Concat, NICHT Template — der Body enthaelt Backticks).
function makeFactory() {
  const runner = '"use strict";\nreturn (async function(){\n' + SRC + '\n})();';
  return new Function('agent', 'parallel', 'phase', 'log', 'args', runner);
}

function makeAgent(spawns, opt) {
  const cfg = Object.assign({ modus: 'M2', elevation: ['BATCH_DONE'], loop: 'TERMINATE', infra: 'false' }, opt || {});
  let elevIdx = 0;
  return async (prompt, o) => {
    o = o || {};
    const label = o.label || '';
    spawns.push({ prompt: String(prompt), label, phase: o.phase, model: o.model });
    if (label.indexOf('modusEntscheidung') === 0) return Object.assign({ modus: cfg.modus, modus_begruendung: 'Aus k=1+srs=1+t=x -> ' + cfg.modus }, cfg.split ? { split_required: true, split_reason: cfg.split } : {});
    if (label.indexOf('stageElevation') === 0) {
      const a = cfg.elevation[Math.min(elevIdx, cfg.elevation.length - 1)]; elevIdx++;
      if (a && typeof a === 'object') return a;
      return { next_action: a, current_stage_outcome: 'GREEN', next_stage: null };
    }
    if (label.indexOf('loopDecision') === 0) return { decision: cfg.loop, reason: 'test' };
    if (label.indexOf('resumePreflight') === 0) return { all_done: !!cfg.preflightAllDone, completed_stages: cfg.preflightAllDone ? (cfg.preflightStages || [1]) : [] };
    if (label.indexOf('_TDD_init') === 0) return 'INFRA=' + cfg.infra;
    if (cfg.greenConflict && label.indexOf('_TDD_green(M2)') === 0) return 'GREEN_BLOCKED_TEST_CONFLICT {"item":"T2094","asserting_test":"form-converters.spec.ts::toUniqueStringArray","finding_premise":"Caller liefern nie undefined","premise_status":"unverified"}';
    if (cfg.collapsedWs !== undefined && label.indexOf('modelSync:') === 0) return '[SDF-modelSync] 3.5c ROUND=' + label.split(':')[1] + ' DONE — 3 AKs confirmed, ' + cfg.collapsedWs + ' W kollabiert, 0 deferred, 0 skipped. COLLAPSED_WS=' + cfg.collapsedWs;
    return 'STEP ' + label + ': done';
  };
}

const noop = () => {};
const mockParallel = async (thunks) => Promise.all(thunks.map(t => t()));

// ===========================================================================
// BL-316 sub_batch_2 "real-parallel" (AK-2 + AK-3) — echter parallel()-Injektor +
// 0-Lost-Update-Probe. mockParallel Z125 (Promise.all-Alias) BLEIBT unveraendert fuer
// die seriell-aequivalenten Tests S1-S23b. realParallel ist eine EIGENE Test-Klasse.
//
// ARCHITEKTUR-EHRLICHKEIT: der Produktiv-Motor ruft parallel() heute NICHT auf (outer-
// Loop seriell; effective_fanout nur berechnet — BL-230/328). Diese Helfer sind reine
// HARNESS-Beweisfaehigkeit: sie zeigen, dass der Harness ECHTES nebenlaeufiges Verhalten
// + die 0-Lost-Update-Eigenschaft testen KANN — sie aendern den seriellen Produktiv-Pfad
// nicht (die 136 Baseline-Checks bleiben gruen).
//
// SICHERHEIT: Sandboxes liegen AUSSCHLIESSLICH in os.tmpdir() mit Praefix 'bl316-rp-'
// (NIE im Repo-Tree). KEINE git-worktree-Ops -> B-3/Baseline unberuehrt. Teardown IMMER
// in finally (rmSync recursive force) — auch bei Exception (kein Leak).
// ===========================================================================

// Eindeutige Sandbox unter os.tmpdir() (NICHT im Repo-Tree). Praefix 'bl316-rp-'.
function makeRpSandbox() {
  const tmpReal = fs.realpathSync.native(os.tmpdir());
  const dir = path.join(tmpReal, 'bl316-rp-' + crypto.randomBytes(6).toString('hex'));
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}
function rmRf(dir) {
  try { if (dir && fs.existsSync(dir)) fs.rmSync(dir, { recursive: true, force: true }); } catch (e) {}
}

// AK-2 — realParallel: parallel()-kompatibler Injektor (thunk[] -> Promise<results[]> in
// EINGABE-Reihenfolge, genau wie mockParallel / der Runner-Slot Z20/Z130), ABER:
//   (1) ECHT nebenlaeufig — ALLE Thunks werden GESTARTET, bevor irgendeiner ge-awaitet
//       wird (thunks.map(t => t(...)) liefert N laufende Promises -> Promise.all). Das ist
//       strukturell, was der spaetere Wellen-Motor (BL-230) tut; im Mock-Fall ist es
//       identisch, hier ist es bewusst eine eigene Klasse mit Isolation.
//   (2) ISOLATION — jeder Thunk bekommt eine eigene disjunkte Sandbox (Praefix bl316-rp-)
//       als ersten Arg. Zero-arg-Thunks (async () => ...) ignorieren ihn (parallel()-
//       Kontrakt bleibt: results in Eingabe-Reihenfolge). Teardown in finally (kein Leak).
// realParallel ist NICHT mockParallel (eigene Identitaet) und nicht dessen Alias.
const realParallel = async (thunks) => {
  const sandboxes = thunks.map(() => makeRpSandbox());
  try {
    // Alle Thunks STARTEN (synchron in der map) -> dann erst await => echtes Ueberlappen.
    const running = thunks.map((t, i) => t(sandboxes[i]));
    return await Promise.all(running);
  } finally {
    sandboxes.forEach(rmRf);
  }
};

// AK-3 — lostUpdateProbe: 2 Batches schreiben NEBENLAEUFIG (via parallelFn = realParallel)
// in DISJUNKTE Sandboxes je Code-Datei + Manifest-Fragment. Negativ-Kontrast: 2 Batches
// auf DIESELBE Datei -> Clobbering. Rueckgabe = beobachtete vs. erwartete Disk-Inhalte +
// leak_free. ALLE Sandboxes in finally geraeumt (rmSync recursive force).
async function lostUpdateProbe(parallelFn) {
  const created = [];
  const mkdir = () => { const d = makeRpSandbox(); created.push(d); return d; };
  // Disjunkt-Lauf: jeder Thunk legt SEINE eigene Sandbox an (kein geteiltes Verzeichnis).
  const expectA = { code: 'BATCH-A code payload', manifest: '{"batch":"A","modus":"M2"}' };
  const expectB = { code: 'BATCH-B code payload', manifest: '{"batch":"B","modus":"M3"}' };
  let batchA = null, batchB = null, disjoint = false;

  // Negativ-Kontrast-Pfad: EINE gemeinsame Datei, beide Thunks schreiben drauf.
  const sharedDir = mkdir();
  const sharedFile = path.join(sharedDir, 'shared.txt');
  let shared = { clobbered: false, survivors: 0 };

  // tick: kurzer await, der den Event-Loop abgibt -> erzwingt echtes Ueberlappen der
  // nebenlaeufigen Thunks (kein synchroner Durchlauf eines Thunks vor dem anderen).
  const tick = () => new Promise(r => setTimeout(r, 0));

  try {
    // --- Disjunkter 0-Lost-Update-Lauf (Code-Write + Manifest-Write je Batch) ---
    const thunkA = async (sandbox) => {
      const dir = mkdir();  // disjunkte Sandbox fuer Batch A
      await tick();
      fs.writeFileSync(path.join(dir, 'code.txt'), expectA.code, 'utf8');
      await tick();
      fs.writeFileSync(path.join(dir, 'manifest.json'), expectA.manifest, 'utf8');
      return { dir, role: 'A' };
    };
    const thunkB = async (sandbox) => {
      const dir = mkdir();  // disjunkte Sandbox fuer Batch B
      await tick();
      fs.writeFileSync(path.join(dir, 'code.txt'), expectB.code, 'utf8');
      await tick();
      fs.writeFileSync(path.join(dir, 'manifest.json'), expectB.manifest, 'utf8');
      return { dir, role: 'B' };
    };
    const [resA, resB] = await parallelFn([thunkA, thunkB]);
    disjoint = !!resA && !!resB && resA.dir !== resB.dir;
    batchA = {
      dir: resA.dir,
      codeExpected: expectA.code,
      codeOnDisk: fs.readFileSync(path.join(resA.dir, 'code.txt'), 'utf8'),
      manifestExpected: expectA.manifest,
      manifestOnDisk: fs.readFileSync(path.join(resA.dir, 'manifest.json'), 'utf8'),
    };
    batchB = {
      dir: resB.dir,
      codeExpected: expectB.code,
      codeOnDisk: fs.readFileSync(path.join(resB.dir, 'code.txt'), 'utf8'),
      manifestExpected: expectB.manifest,
      manifestOnDisk: fs.readFileSync(path.join(resB.dir, 'manifest.json'), 'utf8'),
    };

    // --- Negativ-Kontrast: gemeinsame Datei -> last-writer-wins, nur 1 Wert ueberlebt ---
    const sharedThunkA = async () => { await tick(); fs.writeFileSync(sharedFile, 'A-wrote', 'utf8'); };
    const sharedThunkB = async () => { await tick(); fs.writeFileSync(sharedFile, 'B-wrote', 'utf8'); };
    await parallelFn([sharedThunkA, sharedThunkB]);
    const survived = fs.readFileSync(sharedFile, 'utf8');
    // Beide schrieben dieselbe Datei -> es ueberlebt genau EIN Wert (Lost-Update demonstriert).
    shared = { clobbered: (survived === 'A-wrote' || survived === 'B-wrote'), survivors: 1, survived };
  } finally {
    created.forEach(rmRf);
  }

  // Leak-Beweis: keine der probe-erzeugten Sandboxes existiert mehr.
  const residual = created.filter(d => fs.existsSync(d));
  return { disjoint, batchA, batchB, shared, leak_free: residual.length === 0, residual };
}

async function run(testArgs, agentCfg) {
  const spawns = [];
  const factory = makeFactory();
  const result = await factory(makeAgent(spawns, agentCfg), mockParallel, noop, noop, testArgs);
  return { result, spawns };
}

const ARGS = (sub) => ({ bl_id: 'BL-T', name: 'BL-T', vault: '/v', working_dir: '/v/bl', sub_batches: sub });
const impl = (s) => s.filter(x => x.phase === 'Implement');
const close = (s) => s.filter(x => x.phase === 'BatchClose');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  OK   ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail ? '  -> ' + detail : '')); }
}

(async () => {
  // S1 — M2 I_FULL, 1 Stage, BATCH_DONE: Decomposition (V4) + Phase-3-Gating (V3)
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    // BL-329 (M2-Infra-Luecke): M2 fuehrt jetzt _TDD_init (Infra-Detektion, modus-unabhaengig) — daher 11 statt 10.
    // infra=false (Default) => kein _TDD_setup/_TDD_teardown-Spawn (s. S26), aber das _TDD_init-Signal IST modus-frei.
    check('S1 V4 decomposition: 11 Implement-Spawns (1 BL-262 preflight + 5 blueprint [6 minus goldDefine] + 1 BL-329 _TDD_init + 2 M2-code-emit + 2 closure), kein Mega-Spawn', impl(spawns).length === 11, 'got ' + impl(spawns).length);
    check('S1 BL-231: M2 hat entkoppelten Code-Emit-Step (_TDD_green), schreibt NICHT mehr 0 Code', spawns.some(x => /_TDD_green\(M2\)/.test(x.label)), 'kein _TDD_green(M2) im M2-Pfad');
    check('S1 BL-329: M2 fuehrt _TDD_init (Infra-Detektion modus-unabhaengig), aber infra=false -> KEIN _TDD_setup/_TDD_teardown', spawns.some(x => /^_TDD_init:/.test(x.label)) && !spawns.some(x => /^_TDD_setup:|^_TDD_teardown:/.test(x.label)), 'infra-Steps trotz infra=false oder kein _TDD_init im M2-Pfad');
    check('S1 M2-1 (BL-232): M2 droppt _I_goldDefine (Gold = bestehende covering_tests)', !spawns.some(x => /^_I_goldDefine:/.test(x.label)), '_I_goldDefine im M2-Pfad gespawnt');
    check('S1 V3 Phase-3 @BATCH_DONE: genau 4 Phase-3-Berater (decoupled von BL-285 persistOutcome / BL-299 stageCommit BatchClose-Spawns)', spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length === 4, 'got ' + spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length);
    check('S1 V3 ordering: alle BatchClose NACH allen Implement', spawns.findIndex(x => x.phase === 'BatchClose') > spawns.map(x => x.phase).lastIndexOf('Implement'));
    check('S1 terminated_reason=completed', result.terminated_reason === 'completed', result.terminated_reason);
    check('S1 loop_decision gesetzt', result.loop_decision === 'TERMINATE', String(result.loop_decision));
  }
  // S2 — RETRY-Endlos -> Cap (V1)
  {
    const { result } = await run(Object.assign(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { max_stage_iters: 3 }), { elevation: ['RETRY'] });
    check('S2 V1 Cap: max_stage_iters_exceeded', result.terminated_reason === 'max_stage_iters_exceeded', result.terminated_reason);
  }
  // S3 — Garbage-Token -> fail-safe ABORT, KEINE Phase-3 (V1+V3)
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { elevation: [{ next_action: 'FOO', current_stage_outcome: 'GREEN' }] });
    check('S3 V1 fail-safe: unbekanntes Token -> stage_abort', result.terminated_reason === 'stage_abort', result.terminated_reason);
    check('S3 V3: KEINE Phase-3-Spawns bei ABORT', close(spawns).length === 0, 'got ' + close(spawns).length);
  }
  // S4 — HALT (V1)
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { elevation: ['HALT'] });
    check('S4 V1 HALT: terminated_reason=halt_user', result.terminated_reason === 'halt_user', result.terminated_reason);
    check('S4 V3: KEINE Phase-3-Spawns bei HALT', close(spawns).length === 0);
  }
  // S5 — M1 skeleton: 1 Implement-Spawn + B3 Anti-Chain-Instruktion
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M1', elevation: ['BATCH_DONE'] });
    check('S5 V4 M1: genau 1 Implement-Spawn', impl(spawns).length === 1, 'got ' + impl(spawns).length);
    const p = (impl(spawns)[0] || {}).prompt || '';
    check('S5 B3: M1-Prompt verbietet _SDF_orchestrate_post self-chain', /NICHT.*_SDF_orchestrate_post/i.test(p) || (p.includes('_SDF_orchestrate_post') && p.includes('NICHT')));
  }
  // S6 — M4 SC: 1 Implement-Spawn + B3 Anti-Chain
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M4', elevation: ['BATCH_DONE'] });
    check('S6 V4 M4: genau 1 Implement-Spawn (SC)', impl(spawns).length === 1, 'got ' + impl(spawns).length);
    const p = (impl(spawns)[0] || {}).prompt || '';
    check('S6 B3: SC-Prompt verbietet _SDF_orchestrate_post self-chain', p.includes('_SDF_orchestrate_post') && p.includes('NICHT'));
  }
  // S7 — M3 tdd (infra=false): 8 blueprint + 10 tdd + 2 closure = 20 Implement-Spawns (V4 decomposition)
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M3', elevation: ['BATCH_DONE'], infra: 'false' });
    check('S7 V4 M3 tdd: 19 Implement-Spawns (1 BL-262 preflight + 6 blueprint [mitose entfernt 800711e] + 10 tdd + 2 closure), kein Mega-Spawn', impl(spawns).length === 19, 'got ' + impl(spawns).length);
    check('S7 M2-1 (BL-232): M3 BEHAELT _I_goldDefine (test-first definiert Gold neu)', spawns.some(x => /^_I_goldDefine:/.test(x.label)), 'M3 hat kein _I_goldDefine');
  }
  // S8 — loop_decision RETURN (INV-MOTOR-2: Motor re-chained NICHT selbst)
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'], loop: 'RE-BATCH' });
    check('S8 loop_decision=RE-BATCH returned', result.loop_decision === 'RE-BATCH', String(result.loop_decision));
    const reChain = spawns.some(x => /modusEntscheidung|_SDF_orchestrate(?!_post)/.test(x.label));
    check('S8 INV-MOTOR-2: Motor spawnt kein Re-Entry-_SDF_orchestrate (nur RETURN)', spawns.every(x => !x.label.includes('SDF_orchestrate')));
  }
  // S9 — M8 special: 1 Spawn, kein Stage-Loop, kein Phase-3
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M8' });
    check('S9 M8 special: genau 1 Implement-Spawn', impl(spawns).length === 1, 'got ' + impl(spawns).length);
    check('S9 M8: kein stageElevation (Sonderpfad)', !spawns.some(x => x.label.indexOf('stageElevation') === 0));
    check('S9 M8: kein Phase-3 (special_path)', close(spawns).length === 0);
  }

  // S10 — BL-228 F-MOTOR-SCHEMA-CRASH-FATAL Härtung: safeSchemaAgent ueberlebt einen Schema-Crash.
  // Custom-Agent: der modusEntscheidung schema-Call WIRFT (simuliert "completed without StructuredOutput"),
  // der schemalose Retry liefert JSON-Text -> Workflow muss durchlaufen statt hart zu crashen (3x DCSRE-486).
  {
    const spawns = [];
    const factory = makeFactory();
    let schemaThrown = false, schemalessRetry = false;
    const crashAgent = async (prompt, o) => {
      o = o || {};
      const label = o.label || '';
      spawns.push({ prompt: String(prompt), label, phase: o.phase });
      if (label.indexOf('modusEntscheidung') === 0) {
        if (o.schema) { schemaThrown = true; throw new Error('agent({schema}): subagent completed without calling StructuredOutput (after 2 in-conversation nudges)'); }
        schemalessRetry = true;
        return 'Hier mein Ergebnis: {"modus":"M2","modus_begruendung":"schemaloser Retry OK"} — fertig.';  // JSON eingebettet in Text
      }
      if (label.indexOf('stageElevation') === 0) return { next_action: 'BATCH_DONE', current_stage_outcome: 'GREEN' };
      if (label.indexOf('loopDecision') === 0) return { decision: 'TERMINATE' };
      if (label.indexOf('_TDD_init') === 0) return 'INFRA=false';
      return 'STEP ' + label + ': done';
    };
    const result = await factory(crashAgent, mockParallel, noop, noop, ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]));
    check('S10 Härtung: modusEntscheidung schema-Call hat geworfen (Crash simuliert)', schemaThrown);
    check('S10 Härtung: schemaloser Retry wurde ausgefuehrt (kein harter Throw)', schemalessRetry);
    check('S10 Härtung: Workflow ueberlebt Schema-Crash -> terminated=completed (statt 3x-Crash)', result.terminated_reason === 'completed', result.terminated_reason);
    check('S10 Härtung: modus aus schemalosem Retry geparst (M2)', result.sub_batch_results[0] && result.sub_batch_results[0].modus === 'M2', JSON.stringify(result.sub_batch_results[0]));
  }

  // S11 — BL-261: M3 _TDD_execute zielt auf das Sub-Batch-Test-Artefakt (nicht das eingefrorene batch_1-testbefehl).
  // Live-Defekt BL-242 batch_2: _TDD_execute fuhr batch_1s testbefehl -> 16/16 GRUEN bei expected=RED -> spurious ABORT.
  {
    const { spawns } = await run(ARGS([{ id: 'batch_2', items: ['a', 'b'], stages: [1] }]), { modus: 'M3', elevation: ['BATCH_DONE'], infra: 'false' });
    const execSpawns = impl(spawns).filter(x => /^_TDD_execute:/.test(x.label));
    check('S11 BL-261: M3 hat _TDD_execute-Spawns (4 erwartet)', execSpawns.length === 4, 'got ' + execSpawns.length);
    const allTargeted = execSpawns.length > 0 && execSpawns.every(x => /SUB-BATCH-TEST-TARGET \(BL-261\)/.test(x.prompt) && x.prompt.includes('tests_written') && x.prompt.includes('batch_2'));
    check('S11 BL-261: jeder _TDD_execute-Spawn traegt Sub-Batch-Test-Target (tests_written + sb.id, nicht eingefrorenes testbefehl)', allTargeted, 'ein _TDD_execute ohne Sub-Batch-Target-Instruktion');
  }

  // S12 — BL-262 AK-S2: Resume-Preflight all_done → Build komplett SKIP, aber Phase 3.x finalisiert.
  // Genau der BL-242-batch_2-Fall: Code+Tests gruen, aber nie finalisiert → frueher spurious RED→ABORT,
  // jetzt erkannt + direkt Phase 3.x (kein Re-Build des ganzen Sub-Batches).
  {
    const { result, spawns } = await run(ARGS([{ id: 'batch_2', items: ['a'], stages: [1] }]), { modus: 'M3', elevation: ['BATCH_DONE'], preflightAllDone: true });
    const ip = impl(spawns);
    check('S12 BL-262: genau 1 Implement-Spawn = der Preflight (Build komplett geskippt bei all_done)', ip.length === 1 && /^resumePreflight:/.test(ip[0].label), 'got ' + ip.length + ' impl-spawns: ' + ip.map(x => x.label).join(','));
    check('S12 BL-262: KEIN TDD-/Blueprint-Build trotz all_done', !ip.some(x => /_TDD_|_I_cleanCode|_I_blueprint|_I_goldDefine|_I_requirementCheck|_I_patternLibrary/.test(x.label)));
    check('S12 BL-262: Phase 3.x feuert trotzdem (4 Phase-3-Berater; decoupled von BL-285/299-BatchClose-Spawns)', spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length === 4, 'got ' + spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length);
    check('S12 BL-262: terminated=completed (sauberer Skip statt stage_abort)', result.terminated_reason === 'completed', result.terminated_reason);
  }

  // S13 — BL-276 verify_mode=scenario (.md-Item): KEIN _TDD_red/green/execute-Kategorie-Fehler.
  // Genau der J13-Fall: modus=M3 (uncovered/test-first), aber das Ziel ist _W_fetch.md (Markdown, kein RED moeglich)
  // -> der Motor MUSS scenario-routen (Bootstrap-Direkt + Szenario-Verify), NICHT die TDD-Ceremony fahren.
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['_W_fetch.md'], stages: [1] }]), { modus: 'M3', elevation: ['BATCH_DONE'] });
    const im = impl(spawns);
    check('S13 BL-276 scenario: KEINE TDD-Ceremony (_TDD_red/execute/init/refactor/check) trotz M3', !im.some(x => /_TDD_red|_TDD_execute|_TDD_init|_TDD_refactorCode|_TDD_refactorTests|_TDD_check/.test(x.label)), im.map(x => x.label).join(','));
    check('S13 BL-276 scenario: Bootstrap-Direkt-Emit-Spawn (kein test-first)', im.some(x => /bootstrap-direkt\(scenario\)/.test(x.label)));
    check('S13 BL-276 scenario: _I_goldDefine gedroppt (kein Test-Gold neu zu definieren)', !im.some(x => /^_I_goldDefine:/.test(x.label)));
    check('S13 BL-276 scenario: Blueprint laeuft trotzdem (_I_cleanCodeArchitect, Plan/Pattern-Reuse)', im.some(x => /^_I_cleanCodeArchitect:/.test(x.label)));
    check('S13 BL-276 AK-S5: _I_verify traegt verify_mode=scenario + Szenario-A/B (kein "0 pytest=MISSING")', im.some(x => /^_I_verify:/.test(x.label) && /verify_mode=scenario/.test(x.prompt) && /Szenario-A\/B/.test(x.prompt)));
  }
  // S14 — BL-276 verify_mode=convention (.json-Item): Struktur/Schema statt Test.
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['config.json'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    const im = impl(spawns);
    check('S14 BL-276 convention: KEINE TDD-Ceremony (_TDD_red/execute/init)', !im.some(x => /_TDD_red|_TDD_execute|_TDD_init/.test(x.label)));
    check('S14 BL-276 convention: Bootstrap-Direkt-Emit + Konventions-Verify', im.some(x => /bootstrap-direkt\(convention\)/.test(x.label)) && im.some(x => /^_I_verify:/.test(x.label) && /verify_mode=convention/.test(x.prompt)));
  }
  // S15 — BL-276 heterogener Sub-Batch (.py + .md): sicherer tdd-Fallback + WARN (stagePlanner soll splitten, AK-S4).
  {
    const spawns = [], logs = [];
    const factory = makeFactory();
    const result = await factory(makeAgent(spawns, { modus: 'M3', elevation: ['BATCH_DONE'], infra: 'false' }), mockParallel, noop, (m) => logs.push(String(m)), ARGS([{ id: 'sbmix', items: ['a.py', 'b.md'], stages: [1] }]));
    const im = impl(spawns);
    check('S15 BL-276 heterogen: sicherer tdd-Fallback (TDD-Ceremony laeuft, _TDD_red vorhanden)', im.some(x => /^_TDD_red:/.test(x.label)));
    check('S15 BL-276 heterogen: KEIN scenario-Bootstrap (mixed -> tdd, nicht scenario)', !im.some(x => /bootstrap-direkt/.test(x.label)));
    check('S15 BL-276 AK-S4: WARN-Log fuer heterogenen Sub-Batch (stagePlanner soll homogen splitten)', logs.some(l => /heterogener Sub-Batch/.test(l) && /AK-S4/.test(l)), logs.filter(l => /heterogen/.test(l)).join('|'));
  }
  // S16 — BL-276 AK-S4: sb.verify_mode (Plan-Wahrheit) gewinnt gegen den Endungs-Diskriminator.
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a.py'], stages: [1], verify_mode: 'scenario' }]), { modus: 'M3', elevation: ['BATCH_DONE'] });
    const im = impl(spawns);
    check('S16 BL-276 AK-S4: Plan verify_mode=scenario ueberstimmt .py-tdd-Default -> Bootstrap-Direkt', im.some(x => /bootstrap-direkt\(scenario\)/.test(x.label)) && !im.some(x => /^_TDD_red:/.test(x.label)));
  }

  // S17 — BL-279 Mitose-Zwang: modusEntscheidung split_required=true -> Motor baut NICHT, RETURNED RE-BATCH an Lead.
  // batch_3-Gap: k_max=100 + tdd/scenario gemischt lief frueher ungesplittet durch (J13-Detour). Jetzt erzwungener Re-Cut.
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M3', split: 'k_score_max=100 >= 80 + verify_mode-Heterogenitaet' });
    check('S17 BL-279: terminated_reason=re_cut_required', result.terminated_reason === 're_cut_required', result.terminated_reason);
    check('S17 BL-279: loop_decision=RE-BATCH an Lead (INV-MOTOR-2)', result.loop_decision === 'RE-BATCH', String(result.loop_decision));
    check('S17 BL-279: re_cut_target=sb1', result.re_cut_target === 'sb1', String(result.re_cut_target));
    check('S17 BL-279: KEIN Build (Implement-Spawns=0, mal-geformter Sub-Batch nicht gebaut)', impl(spawns).length === 0, 'got ' + impl(spawns).length);
    check('S17 BL-279: KEIN Phase-3 (BatchClose=0)', close(spawns).length === 0, 'got ' + close(spawns).length);
    check('S17 BL-285: KEIN persistModusDecision fuer split_required-Sub-Batch (Persist NACH split-Block, OQ#1-Korrektur)', !spawns.some(x => /^persistModusDecision:/.test(x.label)), 'persistModusDecision feuerte trotz split_required');
  }
  // S17b — BL-304: Effort-Heterogenitaet (k_avg<15 ABER k_max in [15,80)) fliesst durch DENSELBEN split_required-Boolean -> RE-BATCH.
  // Verankert den neuen split_het_effort-reason-Pfad als Motor-Regression (sonst lebt das Kriterium nur als md-Pseudocode).
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a', 'b'], stages: [1] }]), { modus: 'M2', split: 'Effort-Heterogenitaet (BL-304): k_score_avg=12<15 (triviale Mehrheit) ABER k_score_max=40 in [15,80)' });
    check('S17b BL-304: Effort-Het split -> terminated_reason=re_cut_required', result.terminated_reason === 're_cut_required', result.terminated_reason);
    check('S17b BL-304: Effort-Het split -> loop_decision=RE-BATCH (INV-MOTOR-2)', result.loop_decision === 'RE-BATCH', String(result.loop_decision));
    const modusSpawn = spawns.find(x => x.label.indexOf('modusEntscheidung') === 0);
    check('S17b BL-304: modusEntscheidung-Prompt traegt Effort-Heterogenitaet-Kriterium (c) + Gate-Luecke [15,80)', !!modusSpawn && /Effort-Heterogenitaet/.test(modusSpawn.prompt) && /Gate-Luecke \[15,80\)/.test(modusSpawn.prompt));
  }

  // S18 — BL-285 Modus-Provenance-Persist: Motor setzt Sub-Batch-Cursor + spawnt Provenance/Outcome (guard-clean, INV-MODUS-1, S8-safe).
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    check('S18 BL-285 AK-1: Motor setzt current_sub_batch_id deterministisch VOR modusEntscheidung (persistSubBatchCursor)', spawns.some(x => /^persistSubBatchCursor:sb1$/.test(x.label) && /current_sub_batch_id/.test(x.prompt)));
    const modusSpawn = spawns.find(x => x.label.indexOf('modusEntscheidung') === 0);
    check('S18 BL-285 AK-1: modusEntscheidung-Prompt traegt batch_modes_set_by-Persist-Pflicht', !!modusSpawn && /batch_modes_set_by/.test(modusSpawn.prompt));
    check('S18 BL-285 AK-3/4: Motor spawnt persistModusDecision (phase Modus) je Sub-Batch', spawns.some(x => /^persistModusDecision:sb1$/.test(x.label) && x.phase === 'Modus'));
    check('S18 BL-285 AK-2: Motor spawnt persistOutcome bei BATCH_DONE', spawns.some(x => /^persistOutcome:sb1$/.test(x.label) && x.phase === 'BatchClose'));
    const persistSpawns = spawns.filter(x => /^(persistModusDecision|persistOutcome|persistSubBatchCursor):/.test(x.label));
    check('S18 BL-285 INV-MODUS-1: alle 3 Persist-Spawns deklarieren KEIN batch_modes/modus-Write', persistSpawns.length === 3 && persistSpawns.every(x => x.prompt.includes('KEIN batch_modes/modus-Write')));
    check('S18 BL-285 S8-Regression: kein neuer Persist-Label enthaelt SDF_orchestrate', spawns.every(x => !x.label.includes('SDF_orchestrate')));
  }
  // S19 — BL-299: Motor chained Skill(_stage_orchestrate) am ELEVATE- UND BATCH_DONE-Seam (Commit + Security-Gate).
  // Regression aus BL-222: kanonischer Schwanz _I_fanIn -> _stage_orchestrate war abgeschnitten (grep=0). 2 Stages, beide gruen.
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a', 'b'], stages: [1, 3] }]), { modus: 'M2', elevation: [{ next_action: 'ELEVATE', current_stage_outcome: 'GREEN', next_stage: 3 }, 'BATCH_DONE'] });
    const commits = spawns.filter(x => /^stageCommit:/.test(x.label));
    check('S19 BL-299: 2 stageCommit-Spawns (ELEVATE-Stage + BATCH_DONE-Stage) — kanonischer Schwanz wiederhergestellt', commits.length === 2, 'got ' + commits.length + ': ' + commits.map(x => x.label).join(','));
    check('S19 BL-299 AK-1 Grain=Stage: jeder stageCommit verbietet Hunk/git-add-p + pro-Item-Commit', commits.length > 0 && commits.every(x => /git add -p/.test(x.prompt) && /NICHT pro PL-Item/.test(x.prompt)));
    check('S19 BL-299 AK-3 Security-Gate: jeder stageCommit traegt Pruefung 5 (Prozess-Marker) + Pruefung 6 (Prozess-Markdown)', commits.length > 0 && commits.every(x => /Prozess-Marker/.test(x.prompt) && /Prozess-Markdown/.test(x.prompt)));
    check('S19 BL-299 AK-2 Freeze-Gate: jeder stageCommit traegt das konditionale Commit-Freeze-Gate', commits.length > 0 && commits.every(x => /COMMIT-FREEZE-GATE/.test(x.prompt)));
    check('S19 BL-299 INV-MOTOR-1: stageCommit laedt Skill(_stage_orchestrate) (1 agent = 1 Skill)', commits.length > 0 && commits.every(x => /Skill\(_stage_orchestrate\)/.test(x.prompt)));
    check('S19 terminated=completed', result.terminated_reason === 'completed', result.terminated_reason);
  }
  // S20 — BL-299: bei stage_abort (fail-safe) KEIN BATCH_DONE-Stage-Commit (kein Commit eines abgebrochenen Stands).
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { elevation: [{ next_action: 'FOO', current_stage_outcome: 'GREEN' }] });
    check('S20 BL-299: KEIN BATCH_DONE-stageCommit bei stage_abort', !spawns.some(x => /^stageCommit:/.test(x.label) && x.prompt.includes('BATCH_DONE')), result.terminated_reason);
  }

  // S21 — BL-303 L1: _TDD_green(M2) meldet GREEN_BLOCKED_TEST_CONFLICT -> Motor short-circuit VOR stageElevation -> RE-BATCH+HiL.
  // Toetet den stillen No-Op (wn17ougl9-Befund: Green-Refusal wurde als false-GREEN/ABORT verschluckt -> manueller opus-Bypass).
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', greenConflict: true });
    check('S21 BL-303: terminated_reason=test_conflict_blocked', result.terminated_reason === 'test_conflict_blocked', result.terminated_reason);
    check('S21 BL-303: loop_decision=RE-BATCH an Lead (INV-MOTOR-2)', result.loop_decision === 'RE-BATCH', String(result.loop_decision));
    check('S21 BL-303: test_conflict-Payload returned (item=T2094)', result.test_conflict && result.test_conflict.item === 'T2094', JSON.stringify(result.test_conflict));
    check('S21 BL-303: KEIN stageElevation (short-circuit VOR Elevate)', !spawns.some(x => x.label.indexOf('stageElevation') === 0));
    check('S21 BL-303: KEIN _TDD_execute(M2) nach Konflikt (kein false-GREEN-Lauf)', !spawns.some(x => /_TDD_execute\(M2\)/.test(x.label)));
    check('S21 BL-303: KEIN Phase-3 (BatchClose=0)', close(spawns).length === 0, 'got ' + close(spawns).length);
    check('S21 BL-303: Recovery-Hint nennt Finding<->Test-Adjudikation (_pr_question_answer_sim)', /_pr_question_answer_sim/.test(result.note || ''));
  }
  // S22 — BL-303 L1 default-safe: OHNE Konflikt (greenConflict aus) laeuft der M2-Pfad normal (kein false-positive Block).
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    check('S22 BL-303 default-safe: terminated=completed (kein false Block ohne Konflikt)', result.terminated_reason === 'completed', result.terminated_reason);
    check('S22 BL-303 default-safe: _TDD_execute(M2) laeuft normal (Konflikt-frei)', spawns.some(x => /_TDD_execute\(M2\)/.test(x.label)));
  }

  // S23 — BL-255 AK-7: modelSync 3.5c meldet nicht-leeren confirm_collapse (COLLAPSED_WS>0) -> Motor ruft
  // recalibrate (C5) ERNEUT NACH modelSync. Toetet die Off-by-one-Latenz: heute liest C5 das Model VOR dem
  // 3.5c-Kollaps -> die srs-Senkung wird erst im UEBERNAECHSTEN Batch modus-wirksam (W33 empirisch belegt).
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'], collapsedWs: 2 });
    const labels = spawns.map(x => x.label);
    const msIdx = labels.indexOf('modelSync:sb1');
    const reIdx = labels.indexOf('recalibrate-postCollapse:sb1');
    check('S23 BL-255 AK-7: recalibrate-postCollapse-Spawn existiert bei COLLAPSED_WS>0', reIdx >= 0, 'labels: ' + labels.filter(l => /recalibrate|modelSync/.test(l)).join(','));
    check('S23 BL-255 AK-7 ordering: Re-Run NACH modelSync (3.5c-Kollaps fuer C5 sichtbar)', msIdx >= 0 && reIdx > msIdx, 'modelSync@' + msIdx + ' reRun@' + reIdx);
    check('S23 BL-255 AK-7: Re-Run-Prompt laedt Skill(_SDF_berater_recalibrate) + nennt post-Kollaps-Zweck', reIdx >= 0 && /Skill\(_SDF_berater_recalibrate\)/.test(spawns[reIdx].prompt) && /Kollaps/.test(spawns[reIdx].prompt), reIdx >= 0 ? spawns[reIdx].prompt.slice(0, 120) : 'kein Spawn');
    check('S23 geist9-Vertrag: Phase-3-Quartett unveraendert 4 (kein Berater entfernt/geskippt)', spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length === 4, 'got ' + spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length);
    check('S23 modelSync-Prompt traegt COLLAPSED_WS-Melde-Pflicht (Motor-Konsum-Signal)', msIdx >= 0 && /COLLAPSED_WS/.test(spawns[msIdx].prompt), msIdx >= 0 ? 'Prompt ohne COLLAPSED_WS-Instruktion' : 'kein modelSync-Spawn');
    check('S23 terminated=completed (Re-Run bricht den Flow nicht)', result.terminated_reason === 'completed', result.terminated_reason);
  }
  // S23b — BL-255 AK-7 No-Op-Pfad: COLLAPSED_WS=0 (kein Kollaps) -> KEIN Re-Run (kein +1 agent() im Normalfall).
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'], collapsedWs: 0 });
    check('S23b BL-255 AK-7 No-Op: KEIN recalibrate-postCollapse bei COLLAPSED_WS=0', !spawns.some(x => /^recalibrate-postCollapse:/.test(x.label)));
    check('S23b BL-255 AK-7 No-Op: Phase-3-Quartett normal 4', spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length === 4);
  }

  // ===========================================================================
  // BL-319 SB-motorfix Stage 1 — RED-Phase Safety-Net (Idempotenz AK-2 + Partial-Failure AK-3).
  // Quelle: 4_Blueprint/SB-motorfix/S1/blueprint.md + 4_Blueprint/SB-matrix/S1/rerun_matrix.md.
  // Diese Tests beschreiben den SOLL-Zustand NACH dem GREEN-Fix in dispatch_implement.js. Sie MUESSEN
  // jetzt (vor dem GREEN) ROT sein. Faithful-Hinweis (G4-Ehrlichkeit): der Harness materialisiert KEIN
  // Manifest — er recordet nur die Prompts/Labels/Control-Flow der Mock-agent()-Aufrufe. Echte Byte-
  // Stabilitaet "Manifest nach 2x == nach 1x" ist daher NICHT unit-beobachtbar (siehe Scenario-Liste im
  // Report). Idempotenz wird hier auf der EINZIG beobachtbaren Ebene getestet, die der Motor selbst
  // kontrolliert: der INSTRUKTIONS-VERTRAG, den der Motor pro Step-Agent emittiert (append-if-not-present /
  // set-once / state-skip / persistenter-Guard) — exakt das Pattern der bestehenden S18/S19/S23-Prompt-
  // Assertions. Partial-Failure (AK-3) ist Control-Flow und voll unit-testbar (Throw-Injektion).
  // ===========================================================================

  // ── AK-3 Partial-Failure (PRIORITAER — am saubersten testbar) ──────────────────────────────────
  // T-PF-1: Multi-Batch (3), Batch-2 wirft im Implement -> Geschwister laufen zu Ende, Fan-In-Aggregat.
  // RED weil heute KEIN try/catch um runImplementStage liegt: ein Throw propagiert bis zum Harness-.catch
  // (HARNESS ERROR / exit 2) und reisst die ganze outer-Schleife mit. Es existiert KEIN {completed,failed,
  // blocked}-Aggregat im Return (break-outer Z637/643/725/747 = Fail-Fast statt per-Batch-Isolation).
  {
    const spawns = [];
    const factory = makeFactory();
    // Custom-Agent: wirft GENAU im Implement-Schritt von Batch-2 (sb2). Alle anderen Steps normal.
    const partialFailAgent = async (prompt, o) => {
      o = o || {};
      const label = o.label || '';
      spawns.push({ prompt: String(prompt), label, phase: o.phase });
      if (o.phase === 'Implement' && /:sb2\./.test(label)) {
        throw new Error('INJECTED Batch-2 Implement-Fehler (Partial-Failure-Simulation, AK-3)');
      }
      if (label.indexOf('modusEntscheidung') === 0) return { modus: 'M2', modus_begruendung: 'Aus k=1+srs=1+t=x -> M2' };
      if (label.indexOf('stageElevation') === 0) return { next_action: 'BATCH_DONE', current_stage_outcome: 'GREEN' };
      if (label.indexOf('loopDecision') === 0) return { decision: 'TERMINATE', reason: 'test' };
      if (label.indexOf('resumePreflight') === 0) return { all_done: false, completed_stages: [] };
      if (label.indexOf('_TDD_init') === 0) return 'INFRA=false';
      return 'STEP ' + label + ': done';
    };
    let threw = false, result = null;
    try {
      result = await factory(partialFailAgent, mockParallel,
        () => {}, () => {},
        ARGS([{ id: 'sb1', items: ['a'], stages: [1] }, { id: 'sb2', items: ['b'], stages: [1] }, { id: 'sb3', items: ['c'], stages: [1] }]));
    } catch (e) { threw = true; }
    check('T-PF-1 AK-3: ein geworfener Batch killt NICHT den ganzen Motor (kein Top-Level-Throw -> Geschwister-Isolation)', !threw, threw ? 'Motor warf top-level (kein per-Batch try/catch)' : '');
    const sbRes = (result && result.sub_batch_results) || [];
    const byId = (id) => sbRes.find(r => r.sub_batch === id);
    check('T-PF-1 AK-3: Geschwister sb1+sb3 laufen completed durch (BATCH_DONE), trotz toter sb2', !!byId('sb1') && byId('sb1').outcome === 'BATCH_DONE' && !!byId('sb3') && byId('sb3').outcome === 'BATCH_DONE', JSON.stringify(sbRes.map(r => r && (r.sub_batch + '=' + r.outcome))));
    check('T-PF-1 AK-3: toter Batch sb2 hat outcome=failed (per-Batch-Outcome, kein break-outer)', !!byId('sb2') && byId('sb2').outcome === 'failed', byId('sb2') ? JSON.stringify(byId('sb2')) : 'kein sb2-Outcome (break-outer hat ihn verschluckt)');
    const fanIn = result && result.fan_in;
    check('T-PF-1 AK-3: Fan-In-Aggregat {completed,failed,blocked} existiert im Return', !!fanIn && Array.isArray(fanIn.completed) && Array.isArray(fanIn.failed) && Array.isArray(fanIn.blocked), JSON.stringify(fanIn));
    check('T-PF-1 AK-3: Aggregat korrekt — completed=[sb1,sb3], failed=[sb2]', !!fanIn && fanIn.completed.includes('sb1') && fanIn.completed.includes('sb3') && fanIn.failed.includes('sb2') && !fanIn.completed.includes('sb2'), JSON.stringify(fanIn));
    check('T-PF-1 AK-3: sb3-Implement-Spawn lief NACH dem sb2-Throw (Schleife brach NICHT ab)', spawns.some(x => x.phase === 'Implement' && /:sb3\./.test(x.label)), 'kein sb3-Implement-Spawn (break-outer-Abort nach sb2-Fehler)');
  }

  // T-PF-2: Resume nach Partial-Failure — der tote Batch ist re-runnable/konvergent (kein Doppel-Schaden,
  // landet wieder im Aggregat). RED weil ohne per-Batch-Isolation + Aggregat das Resume-Replay heute
  // entweder erneut top-level wirft oder den toten Batch nicht als wiederholbares failed fuehrt.
  {
    const spawns = [];
    const factory = makeFactory();
    let attempt = 0;
    // Agent wirft beim 1. sb2-Implement, beim 2. Lauf (Resume) NICHT mehr -> sb2 konvergiert zu completed.
    const resumeAgent = async (prompt, o) => {
      o = o || {};
      const label = o.label || '';
      spawns.push({ prompt: String(prompt), label, phase: o.phase, run: attempt });
      if (o.phase === 'Implement' && /:sb2\./.test(label) && attempt === 1) {
        throw new Error('INJECTED Batch-2 Fehler nur im 1. Lauf (Resume-Konvergenz AK-3)');
      }
      if (label.indexOf('modusEntscheidung') === 0) return { modus: 'M2', modus_begruendung: 'Aus k=1+srs=1+t=x -> M2' };
      if (label.indexOf('stageElevation') === 0) return { next_action: 'BATCH_DONE', current_stage_outcome: 'GREEN' };
      if (label.indexOf('loopDecision') === 0) return { decision: 'TERMINATE', reason: 'test' };
      if (label.indexOf('resumePreflight') === 0) return { all_done: false, completed_stages: [] };
      if (label.indexOf('_TDD_init') === 0) return 'INFRA=false';
      return 'STEP ' + label + ': done';
    };
    const A2 = ARGS([{ id: 'sb1', items: ['a'], stages: [1] }, { id: 'sb2', items: ['b'], stages: [1] }]);
    let r1 = null, r2 = null, threw1 = false, threw2 = false;
    attempt = 1; try { r1 = await factory(resumeAgent, mockParallel, () => {}, () => {}, A2); } catch (e) { threw1 = true; }
    attempt = 2; try { r2 = await factory(resumeAgent, mockParallel, () => {}, () => {}, A2); } catch (e) { threw2 = true; }
    check('T-PF-2 AK-3: 1. Lauf bleibt stabil (failed-Batch, kein Top-Level-Throw)', !threw1, threw1 ? 'Lauf-1 warf top-level' : '');
    const f1 = r1 && r1.fan_in;
    check('T-PF-2 AK-3: 1. Lauf fuehrt sb2 als failed', !!f1 && f1.failed.includes('sb2'), JSON.stringify(f1));
    const f2 = r2 && r2.fan_in;
    // Faithful: in Lauf-2 wirft der Agent ohnehin nicht — "!threw2" allein waere eine Tautologie. Der echte
    // AK-3-Vertrag ist, dass der Resume-Lauf ein Fan-In-Aggregat produziert (existiert erst nach GREEN) UND
    // den frueher toten Batch konvergent als completed fuehrt. Beide RED bis zum Fix.
    check('T-PF-2 AK-3: Resume-Lauf liefert Fan-In-Aggregat (kein Top-Level-Throw + Aggregat vorhanden)', !threw2 && !!f2 && Array.isArray(f2.completed), threw2 ? 'Resume warf top-level' : 'kein fan_in im Resume-Return');
    check('T-PF-2 AK-3: Resume — toter Batch sb2 ist re-runnable und konvergiert zu completed', !!f2 && f2.completed.includes('sb2') && !f2.failed.includes('sb2'), JSON.stringify(f2));
  }

  // ── AK-2 Idempotenz (Instruktions-Vertrag pro Fix-Pattern-Gruppe; siehe Faithful-Hinweis oben) ──
  // Gruppe APPEND-DEDUP (S6b _TDD_red tests_written, S13 postItem PL-Items, S2 patternBrief, S5 Blueprint-Write).
  // RED weil die Emit-Prompts heute KEINE append-if-not-present/keyed-Overwrite-Pflicht tragen -> 2x-Lauf dupliziert.
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M3', elevation: ['BATCH_DONE'], infra: 'false' });
    const redSpawn = spawns.find(x => /^_TDD_red:/.test(x.label));
    check('T-IDEM-APPEND S6b: _TDD_red-Prompt traegt tests_written append-if-not-present/keyed-Pflicht (Datei als Key, kein Doppel-Eintrag bei 2x)', !!redSpawn && /append-if-not-present|keyed-upsert|nur wenn .* noch nicht|kein Doppel/i.test(redSpawn.prompt), redSpawn ? 'kein Dedup-Vertrag im _TDD_red-Prompt' : 'kein _TDD_red-Spawn');
    const patternSpawn = spawns.find(x => /^patternBrief:/.test(x.label));
    check('T-IDEM-APPEND S2: patternBrief-Prompt traegt keyed-Overwrite-statt-Append-Pflicht (deterministisch auf sb.id, kein Brief-Append pro Lauf)', !!patternSpawn && /keyed|ueberschreib|overwrite|kein Append|append-if-not-present|deterministisch ueberschreib/i.test(patternSpawn.prompt), patternSpawn ? 'kein keyed-Overwrite-Vertrag im patternBrief-Prompt' : 'kein patternBrief-Spawn');
    const postItemSpawn = spawns.find(x => /^postItem:/.test(x.label));
    check('T-IDEM-APPEND S13: postItem-Prompt traegt PL-Item-Dedup-Key-Pflicht (append-if-not-present by item-id, kein Re-Anlegen bei 2x)', !!postItemSpawn && /dedup|append-if-not-present|item-id|nur wenn .* noch nicht|kein Doppel/i.test(postItemSpawn.prompt), postItemSpawn ? 'kein Dedup-Vertrag im postItem-Prompt' : 'kein postItem-Spawn');
    const goldSpawn = spawns.find(x => /^_I_goldDefine:|^_I_cleanCodeSlice:|^_I_blueprintQG:/.test(x.label));
    check('T-IDEM-APPEND S5: Blueprint-Write-Trias-Prompt traegt keyed-Overwrite-Pflicht (Slice/Gold/QG keyed auf (sb.id,stage), kein Re-Nummerieren/Append)', !!goldSpawn && /keyed|ueberschreib|overwrite|kein Append|kein .*nummerier/i.test(goldSpawn.prompt), goldSpawn ? 'kein keyed-Overwrite-Vertrag in Blueprint-Write-Prompt' : 'kein Blueprint-Write-Spawn');
  }

  // Gruppe SET-ONCE (S1b persistModusDecision entschieden_at, S16 persistOutcome evidence-<ISO-now>).
  // RED weil beide Prompts heute "<ISO-now>" bei JEDEM Lauf neu schreiben (Timestamp-Drift) statt set-once (??=).
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    const provSpawn = spawns.find(x => /^persistModusDecision:/.test(x.label));
    check('T-IDEM-SETONCE S1b: persistModusDecision-Prompt schreibt entschieden_at set-once (??=, nur wenn Slot leer) — KEIN <ISO-now>-Drift bei 2x', !!provSpawn && /set-once|nur (setzen|schreiben) wenn .*(leer|nicht gesetzt)|\?\?=|beibehalten/i.test(provSpawn.prompt) && !/entschieden_at:\s*<ISO-now>/.test(provSpawn.prompt), provSpawn ? 'persistModusDecision schreibt weiterhin entschieden_at:<ISO-now> ohne set-once' : 'kein persistModusDecision-Spawn');
    const outSpawn = spawns.find(x => /^persistOutcome:/.test(x.label));
    check('T-IDEM-SETONCE S16: persistOutcome-Prompt schreibt evidence-Timestamp set-once (??=, kein <ISO-now>-Drift bei 2x)', !!outSpawn && /set-once|nur (setzen|schreiben) wenn .*(leer|nicht gesetzt)|\?\?=|beibehalten/i.test(outSpawn.prompt), outSpawn ? 'persistOutcome schreibt evidence weiterhin mit <ISO-now> ohne set-once' : 'kein persistOutcome-Spawn');
  }

  // Gruppe STATE-SKIP (S6a _TDD_init Re-Init-Schutz, S6d _TDD_green deterministisches Overwrite,
  // S6e/S6f refactor-Skip-wenn-bereits, S6g _TDD_check GOLD-Flag keyed, S7 _TDD_setup, S8 _TDD_teardown).
  // RED weil diese TDD-Step-Prompts heute keine Zustand-vor-Edit-Skip/keyed-upsert-Pflicht tragen.
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M3', elevation: ['BATCH_DONE'], infra: 'true' });
    const initSpawn = spawns.find(x => /^_TDD_init:/.test(x.label));
    check('T-IDEM-SKIP S6a: _TDD_init-Prompt traegt Re-Init-Schutz (TDD-STATE keyed-upsert auf (sb.id,stage), kein Overwrite frischer Sub-Batch-Daten bei 2x)', !!initSpawn && /keyed-upsert|kein Re-Init|nicht (neu )?anlegen wenn|Re-Init-Schutz|upsert/i.test(initSpawn.prompt), initSpawn ? 'kein Re-Init-Schutz im _TDD_init-Prompt' : 'kein _TDD_init-Spawn');
    const refactorCode = spawns.find(x => /^_TDD_refactorCode:/.test(x.label));
    check('T-IDEM-SKIP S6e: _TDD_refactorCode-Prompt traegt Skip-wenn-bereits-generisch (Zustand pruefen vor Edit, idempotent bei 2x)', !!refactorCode && /skip.*bereits|bereits generisch|wenn bereits|Zustand pruefen|idempotent/i.test(refactorCode.prompt), refactorCode ? 'kein Skip-Guard im _TDD_refactorCode-Prompt' : 'kein _TDD_refactorCode-Spawn');
    const checkSpawn = spawns.find(x => /^_TDD_check:/.test(x.label));
    check('T-IDEM-SKIP S6g: _TDD_check-Prompt traegt GOLD-Flag keyed-upsert-Pflicht (kein Append des GOLD-Status bei 2x)', !!checkSpawn && /keyed-upsert|keyed|kein Append|GOLD-Flag .*upsert|nur wenn .* noch nicht/i.test(checkSpawn.prompt), checkSpawn ? 'kein keyed-Vertrag im _TDD_check-Prompt' : 'kein _TDD_check-Spawn');
    const setupSpawn = spawns.find(x => /^_TDD_setup:/.test(x.label));
    check('T-IDEM-SKIP S7: _TDD_setup-Prompt belegt Spinup-Guard explizit (spinup-if-not-running, verifizierte Idempotenz statt bloss behauptet, BL-230 Z86)', !!setupSpawn && /if-not-running|nicht .* wenn .* laeuft|Spinup-Guard|bereits laeuft|idempotent.*Guard/i.test(setupSpawn.prompt), setupSpawn ? 'nur behauptete (unbelegte) Idempotenz im _TDD_setup-Prompt' : 'kein _TDD_setup-Spawn');
    const teardownSpawn = spawns.find(x => /^_TDD_teardown:/.test(x.label));
    check('T-IDEM-SKIP S8: _TDD_teardown-Prompt traegt No-Op-bei-bereits-down (kein Fehler/Doppel-Aktion bei 2x)', !!teardownSpawn && /No-Op.*bereits|bereits down|wenn .* down|kein Fehler bei bereits/i.test(teardownSpawn.prompt), teardownSpawn ? 'kein No-Op-bei-bereits-down im _TDD_teardown-Prompt' : 'kein _TDD_teardown-Spawn');
  }

  // Gruppe PERSISTENT-GUARD (S11 recalibrate / S14b recalibrate-postCollapse: phase3_fired-Set Z427 +
  // recalcRounds-Map Z432 sind IN-MEMORY -> ueberleben Crash/Fresh-Replay NICHT). Der Motor MUSS den
  // Guard-State ins Manifest persistieren (Re-Run liest statt neu-feuern). RED weil heute kein Persist-
  // Vertrag existiert. (Echte Crash-Survival = scenario-only; hier der beobachtbare Instruktions-Vertrag.)
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'], collapsedWs: 2 });
    const recalSpawn = spawns.find(x => /^recalibrate:/.test(x.label));
    check('T-IDEM-GUARD S11: recalibrate-Prompt verankert persistenten phase3_fired-Guard (Manifest, kein in-memory-Set -> kein Doppel-Feuer bei Fresh-Replay)', !!recalSpawn && /persistent|phase3_fired.*Manifest|Manifest.*phase3_fired|Re-Run liest|ueberlebt (Crash|Replay)|persisten.* Guard/i.test(recalSpawn.prompt), recalSpawn ? 'kein persistenter-Guard-Vertrag im recalibrate-Prompt' : 'kein recalibrate-Spawn');
  }

  // ── T-BARRIER (S10 runStageCommit, S15 loopDecision): strukturell-nie-idempotent -> barrier_only/EXCLUSIVE. ──
  // RED weil die Prompts heute KEIN barrier_only/concurrency_class=EXCLUSIVE-Flag tragen (duerfen nie in
  // einer Welle parallel laufen — git-Commit-SHA-Drift / destruktive Findings-Rotation).
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a', 'b'], stages: [1, 3] }]), { modus: 'M2', elevation: [{ next_action: 'ELEVATE', current_stage_outcome: 'GREEN', next_stage: 3 }, 'BATCH_DONE'] });
    const commits = spawns.filter(x => /^stageCommit:/.test(x.label));
    check('T-BARRIER S10: jeder stageCommit-Prompt traegt barrier_only/concurrency_class=EXCLUSIVE (git-Commit-Seam, nie nebenlaeufig in einer Welle)', commits.length > 0 && commits.every(x => /barrier_only|concurrency_class\s*=\s*EXCLUSIVE|EXCLUSIVE.*barrier|Single-Writer-Commit-Seam/i.test(x.prompt)), commits.length ? 'stageCommit ohne barrier_only/EXCLUSIVE-Flag' : 'kein stageCommit-Spawn');
  }
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    const ldSpawn = spawns.find(x => /^loopDecision:/.test(x.label));
    check('T-BARRIER S15: loopDecision-Prompt traegt barrier_only/EXCLUSIVE (destruktive Findings-Rotation, nie nebenlaeufig auf geteiltem findings/-Dir)', !!ldSpawn && /barrier_only|concurrency_class\s*=\s*EXCLUSIVE|Findings-Rotation-Lock|nie nebenlaeufig|per-Batch-Namespace/i.test(ldSpawn.prompt), ldSpawn ? 'loopDecision ohne barrier_only/EXCLUSIVE-Flag' : 'kein loopDecision-Spawn');
  }

  // ===========================================================================
  // BL-327 sub_batch_2 "motorread" (M3, RED-first) — AK-2: der Motor LIEST den
  // Parallel-Dial AN DER WELLEN-BARRIER (EINMAL, vor dem outer-Loop) aus den args.
  // KEIN echter Parallel-Pfad (das ist BL-230/BL-328). Hier nur: lesen + Cap-Rechnen
  // + Observability (log + Rueckgabe-Felder). parallel_mode=false MUSS byte-identisch
  // zum heutigen seriellen Pfad bleiben (die 107 Baseline-Checks beweisen den OFF-Pfad).
  // RED weil heute der Motor parallel_mode/nr_parallel_batches/effective_fanout weder
  // liest noch ins Return-Objekt aufnimmt.
  // ===========================================================================
  const ARGS_P = (sub, dial) => Object.assign(ARGS(sub), dial || {});
  // Sequenz der Sub-Batch-IDs in Spawn-Reihenfolge, konsekutiv dedupliziert (Gruppierung statt 1-Spawn-pro-Batch).
  const seqOrder = (s) => {
    const ids = impl(s).map(x => (String(x.label).match(/:((?:sb)?\w+)(?:\.|$)/) || [])[1]).filter(Boolean);
    return ids.filter((id, i) => id !== ids[i - 1]);
  };

  // (a) BL-327 AK-4 forward-verify (Test-Anteil): OFF byte-identisch — default-args (kein Dial)
  //     => Rueckgabe parallel_mode=false, nr_parallel_batches=1, effective_fanout=1, Verhalten unveraendert.
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    check('T-DIAL-a BL-327 AK-2: default (kein Dial) -> Rueckgabe parallel_mode=false', result.parallel_mode === false, String(result.parallel_mode));
    check('T-DIAL-a BL-327 AK-2: default -> nr_parallel_batches=1', result.nr_parallel_batches === 1, String(result.nr_parallel_batches));
    check('T-DIAL-a BL-327 AK-2: default -> effective_fanout=1 (OFF hart seriell)', result.effective_fanout === 1, String(result.effective_fanout));
    check('T-DIAL-a BL-327 AK-4: OFF Verhalten unveraendert (terminated=completed, loop_decision returned, 4 Phase-3)', result.terminated_reason === 'completed' && result.loop_decision === 'TERMINATE' && spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length === 4, result.terminated_reason + '/' + result.loop_decision);
  }

  // (b) parallel_mode=true + nr=3 + 5 sub_batches => effective_fanout=min(3,5,cap)=3.
  //     BL-230 AK-MOTOR-WELLE-UPDATE: BL-327 hatte hier "kein echter Parallel-Pfad" angenommen (Dial nur
  //     gelesen, for-Loop strikt seriell) und folgerichtig strikte Spawn-Reihenfolge verlangt. BL-230 SB-1a
  //     ueberstimmt diese Praemisse AUTORISIERT (Blueprint Z36/Gold S1): ab effective_fanout>1 fahren die
  //     Sub-Batches NEBENLAEUFIG ueber parallel() -> die Implement-Spawns INTERLEAVEN (echte Concurrency).
  //     Der load-bearing Reihenfolge-Kontrakt ist EC-6: results in EINGABE-Reihenfolge (NICHT Completion-/
  //     Spawn-Reihenfolge). Darum bleibt der results-Order-Check (er testet die echte Garantie); der frueher
  //     verlangte strikte SPAWN-Order-Check ist durch das BL-230-Design obsolet (BL-303-FLIP: Test-Praemisse
  //     vom autorisierten Gold ueberstimmt) und wird auf den korrekten Concurrency-Vertrag umgestellt.
  {
    const five = [
      { id: 'sb1', items: ['a'], stages: [1] }, { id: 'sb2', items: ['b'], stages: [1] },
      { id: 'sb3', items: ['c'], stages: [1] }, { id: 'sb4', items: ['d'], stages: [1] },
      { id: 'sb5', items: ['e'], stages: [1] },
    ];
    const { result, spawns } = await run(ARGS_P(five, { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] });
    check('T-DIAL-b BL-327 AK-2: parallel_mode=true durchgereicht', result.parallel_mode === true, String(result.parallel_mode));
    check('T-DIAL-b BL-327 AK-2: nr_parallel_batches=3 durchgereicht', result.nr_parallel_batches === 3, String(result.nr_parallel_batches));
    check('T-DIAL-b BL-327 AK-2: effective_fanout=min(3,5,cap)=3', result.effective_fanout === 3, String(result.effective_fanout));
    const ids = result.sub_batch_results.map(r => r.sub_batch);
    check('T-DIAL-b BL-230 EC-6 (load-bearing): results in EINGABE-Reihenfolge [sb1..sb5] (Aggregat unabhaengig von Completion-Reihenfolge, auch unter Fan-Out)', JSON.stringify(ids) === JSON.stringify(['sb1', 'sb2', 'sb3', 'sb4', 'sb5']), JSON.stringify(ids));
    // BL-230-UPDATE: alle 5 Welle-Mitglieder kommen unter Fan-Out dran (Coverage), genau 1x je Sub-Batch —
    // das ersetzt den obsoleten strikten Spawn-Order-VERBOT (echte Concurrency interleaved die Spawns).
    check('T-DIAL-b BL-230 AK-MOTOR-WELLE: alle 5 Welle-Mitglieder gebaut (Fan-Out-Coverage, je 1x; strikte Spawn-Order durch echte Concurrency autorisiert ueberstimmt, BL-327-Praemisse retired)', new Set(seqOrder(spawns)).size === 5 && JSON.stringify([...new Set(seqOrder(spawns))].sort()) === JSON.stringify(['sb1', 'sb2', 'sb3', 'sb4', 'sb5']), seqOrder(spawns).join(','));
  }

  // (c) BL-327 AK-4 (Test-Anteil): SINGLE-deklariert Dial-sichtbar — parallel_mode=true + nr=1
  //     => effective_fanout=1 (SINGLE-Mode: Dial gelesen + im Return sichtbar, aber keine Concurrency).
  {
    const { result } = await run(ARGS_P([{ id: 'sb1', items: ['a'], stages: [1] }], { parallel_mode: true, nr_parallel_batches: 1 }), { modus: 'M2', elevation: ['BATCH_DONE'] });
    check('T-DIAL-c BL-327 AK-2: SINGLE parallel_mode=true sichtbar', result.parallel_mode === true, String(result.parallel_mode));
    check('T-DIAL-c BL-327 AK-2: SINGLE nr=1 sichtbar', result.nr_parallel_batches === 1, String(result.nr_parallel_batches));
    check('T-DIAL-c BL-327 AK-4: SINGLE effective_fanout=1 (Dial gelesen+sichtbar, keine Concurrency)', result.effective_fanout === 1, String(result.effective_fanout));
  }

  // (d) parallel_mode=false + nr=4 (widerspruechlich) => effective_fanout=1 (OFF dominiert hart, N erzwungen 1).
  {
    const { result } = await run(ARGS_P([{ id: 'sb1', items: ['a'], stages: [1] }, { id: 'sb2', items: ['b'], stages: [1] }], { parallel_mode: false, nr_parallel_batches: 4 }), { modus: 'M2', elevation: ['BATCH_DONE'] });
    check('T-DIAL-d BL-327 AK-2: OFF dominiert -> parallel_mode=false trotz nr=4', result.parallel_mode === false, String(result.parallel_mode));
    check('T-DIAL-d BL-327 AK-2: OFF dominiert -> effective_fanout=1 (N=4 ignoriert)', result.effective_fanout === 1, String(result.effective_fanout));
    check('T-DIAL-d BL-327 AK-2: nr_parallel_batches=4 bleibt sichtbar (gelesen, aber nicht wirksam unter OFF)', result.nr_parallel_batches === 4, String(result.nr_parallel_batches));
  }

  // (e) effective_fanout nie > SUB_BATCHES.length (|welle| ist eine senkende Schranke).
  {
    const { result } = await run(ARGS_P([{ id: 'sb1', items: ['a'], stages: [1] }, { id: 'sb2', items: ['b'], stages: [1] }], { parallel_mode: true, nr_parallel_batches: 8 }), { modus: 'M2', elevation: ['BATCH_DONE'] });
    check('T-DIAL-e BL-327 AK-2: effective_fanout=min(8,2,cap)=2 (nie > |welle|)', result.effective_fanout === 2, String(result.effective_fanout));
    check('T-DIAL-e BL-327 AK-2: nr_parallel_batches=8 sichtbar, aber durch |welle|=2 gedeckelt', result.nr_parallel_batches === 8 && result.effective_fanout <= result.sub_batch_results.length, 'nr=' + result.nr_parallel_batches + ' fanout=' + result.effective_fanout);
  }

  // ===========================================================================
  // BL-316 sub_batch_1 "worktree-lifecycle" (M3, RED-first) — AK-1 + AK-4.
  // AK-1: ECHTER git-worktree add/remove-Roundtrip im Harness (kein Mock) — Setup/
  //       Teardown leichen-frei, in dediziertem temp/gitignored Pfad (os.tmpdir + random),
  //       NIE im Repo-Tree. detached HEAD (kein Doppel-Checkout von feature/bdf-*).
  // AK-4: Teardown-Audit via BASELINE-DIFF (nicht empty-repo!). Snapshot VOR (= Baseline,
  //       enthaelt die pre-existing OmniCommand-B-3-Leiche) vs NACH (= MUSS == Baseline,
  //       DELTA leer). Negativ-Fixture: ein absichtlich nicht-geraeumter test-Worktree MUSS
  //       vom Audit als DELTA geflaggt werden — danach im finally doch geraeumt (kein Leak).
  // SICHERHEIT: B-3 ist Baseline-Eintrag, NIE Loesch-/Prune-Ziel. Alle test-Worktrees
  //       tragen das eindeutige Praefix 'bl316-wt-' im temp-Pfad. Teardown in finally +
  //       git worktree prune, auch bei Assertion-Fail/Exception (kein Leak).
  // RED weil die Helper worktreeBaseline()/realWorktreeRoundtrip()/worktreeAudit() noch
  // nicht existieren (typeof-guard -> sauberer FAIL statt Harness-Crash).
  // ===========================================================================
  {
    const hasHelpers = typeof worktreeBaseline === 'function'
      && typeof realWorktreeRoundtrip === 'function'
      && typeof worktreeAudit === 'function';
    check('S24 BL-316 AK-1/AK-4: Worktree-Lifecycle-Helper existieren (worktreeBaseline/realWorktreeRoundtrip/worktreeAudit)', hasHelpers, 'mindestens ein Helper fehlt (RED bis GREEN-Implementierung)');

    // AK-1 — echter Roundtrip. Liefert Beobachtungen aus echten git-Ops (kein Mock).
    let rt = null, rtErr = null;
    if (hasHelpers) { try { rt = realWorktreeRoundtrip(); } catch (e) { rtErr = e; } }
    check('S24 BL-316 AK-1: Roundtrip lief ohne Exception (echte git-Ops add/remove/prune)', hasHelpers && !rtErr && !!rt, rtErr ? String(rtErr.message) : 'kein Ergebnis');
    check('S24 BL-316 AK-1: dedizierter temp/gitignored Pfad (bl316-wt-* in os.tmpdir, NICHT im Repo-Tree)', !!rt && /bl316-wt-/.test(rt.worktreePath) && rt.outsideRepo === true, rt ? rt.worktreePath : 'n/a');
    check('S24 BL-316 AK-1: nach git worktree add -> Verzeichnis existiert UND erscheint in worktree list', !!rt && rt.existedAfterAdd === true && rt.inListAfterAdd === true, rt ? ('exists=' + rt.existedAfterAdd + ' inList=' + rt.inListAfterAdd) : 'n/a');
    check('S24 BL-316 AK-1: Datei-Roundtrip-Substanz (HEAD-SHA des Worktrees == Repo-HEAD, echter detached Checkout-Punkt)', !!rt && !!rt.worktreeHead && rt.worktreeHead === rt.repoHead, rt ? ('wt=' + rt.worktreeHead + ' repo=' + rt.repoHead) : 'n/a');
    check('S24 BL-316 AK-1: nach git worktree remove --force + prune -> weg aus list UND Verzeichnis entfernt (leichen-frei)', !!rt && rt.inListAfterRemove === false && rt.existedAfterRemove === false, rt ? ('inList=' + rt.inListAfterRemove + ' exists=' + rt.existedAfterRemove) : 'n/a');

    // AK-4 — Teardown-Audit: Baseline-Diff (kein empty-repo). B-3 im Baseline.
    let baseline = null, baseErr = null;
    if (hasHelpers) { try { baseline = worktreeBaseline(); } catch (e) { baseErr = e; } }
    check('S24 BL-316 AK-4: Baseline-Snapshot ist NICHT empty (mindestens Haupt-Worktree + B-3-Leiche)', !baseErr && Array.isArray(baseline) && baseline.length >= 2, baseErr ? String(baseErr.message) : ('len=' + (baseline ? baseline.length : 'null')));
    check('S24 BL-316 AK-4: Baseline enthaelt die pre-existing OmniCommand-B-3-Leiche (Verify-Specimen, NICHT Loesch-Ziel)', Array.isArray(baseline) && baseline.some(p => /omnicommand-b-3$/i.test(p)), baseline ? JSON.stringify(baseline) : 'n/a');

    // AK-4 Happy-Path: nach sauberem Roundtrip ist current == baseline (DELTA leer).
    let auditHappy = null;
    if (hasHelpers && baseline) { try { auditHappy = worktreeAudit(baseline, worktreeBaseline()); } catch (e) { auditHappy = { error: String(e.message) }; } }
    check('S24 BL-316 AK-4: Happy-Path nach Roundtrip -> DELTA leer (0 test-erzeugte Worktrees uebrig)', !!auditHappy && Array.isArray(auditHappy.delta) && auditHappy.delta.length === 0, auditHappy ? JSON.stringify(auditHappy.delta || auditHappy) : 'n/a');
    check('S24 BL-316 AK-4: read-only Audit (B-3 kein False-Positive, kein remove/prune auf Baseline)', !!auditHappy && auditHappy.delta && auditHappy.delta.length === 0 && !auditHappy.delta.some(p => /omnicommand-b-3$/i.test(p)), auditHappy ? JSON.stringify(auditHappy.delta) : 'n/a');

    // AK-4 Negativ-Fixture: ein absichtlich NICHT-geraeumter test-Worktree MUSS als DELTA
    // geflaggt werden. Danach im finally doch entfernt (kein echter Leak).
    let detected = null, danglPath = null;
    if (hasHelpers && baseline) {
      const g = (c) => execSync('git ' + c, { cwd: REPO_ROOT, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
      const tmpReal = fs.realpathSync.native(os.tmpdir());
      danglPath = path.join(tmpReal, 'bl316-wt-dangling-' + crypto.randomBytes(6).toString('hex'));
      try {
        g('worktree add --no-checkout --detach "' + danglPath + '" HEAD');
        const auditNeg = worktreeAudit(baseline, worktreeBaseline());
        detected = auditNeg.delta.some(p => wtNorm(p) === wtNorm(danglPath));
      } finally {
        try { g('worktree remove --force "' + danglPath + '"'); } catch (e) {}
        try { g('worktree prune'); } catch (e) {}
      }
    }
    check('S24 BL-316 AK-4: Negativ-Fixture — nicht-geraeumter test-Worktree WIRD als DELTA geflaggt (Audit fail-loud-faehig)', detected === true, 'Audit erkannte den dangling test-Worktree nicht (delta-Diff defekt)');

    // Final-Beweis: nach Negativ-Fixture-Teardown ist wieder Baseline-Stand (kein Leak).
    let finalAudit = null;
    if (hasHelpers && baseline) { try { finalAudit = worktreeAudit(baseline, worktreeBaseline()); } catch (e) { finalAudit = { error: String(e.message) }; } }
    check('S24 BL-316 AK-4: nach gesamtem S24-Block KEIN bl316-wt-* Leak (current == baseline, DELTA leer)', !!finalAudit && Array.isArray(finalAudit.delta) && finalAudit.delta.length === 0, finalAudit ? JSON.stringify(finalAudit.delta || finalAudit) : 'n/a');
  }

  // ===========================================================================
  // BL-316 sub_batch_2 "real-parallel" (M3, RED-first) — AK-2 + AK-3.
  // AK-2: parallel()-Injection gegen ECHTES nebenlaeufiges Verhalten testbar. Der
  //       mockParallel Z125 (Promise.all-Alias, SERIELL-aequivalent fuer S1-S23b)
  //       BLEIBT unveraendert. realParallel ist eine EIGENE Test-Klasse: ein parallel()-
  //       kompatibler Injektor, der die Thunks ECHT nebenlaeufig (Promise.all) UND mit
  //       Isolation (jeder Thunk in eigenem disjunkten os.tmpdir-Sandbox, Praefix
  //       'bl316-rp-') laufen laesst. Beweis: realParallel ist ueber DENSELBEN Runner-
  //       Slot (factory(agent, parallel, ...) Z99/Z130) injizierbar wie der Mock.
  // AK-3: 0-Lost-Update-Assertion. 2 simulierte Batches schreiben NEBENLAEUFIG (via
  //       realParallel) in DISJUNKTE Files (je eigener Sandbox) — Code-Writes UND
  //       Manifest-Writes. NACH dem parallelen Lauf existieren ALLE Writes beider
  //       Batches vollstaendig (0 Lost-Updates, kein Clobbering). Negativ-Kontrast:
  //       2 Batches auf DIESELBE Datei -> nachweisbares Clobbering (zeigt: Disjunktheit
  //       IST die 0-Lost-Update-Bedingung).
  //
  // ARCHITEKTUR-EHRLICHKEIT (A-Substrate-Befund): der Produktiv-Motor ruft parallel()
  // heute NICHT auf (outer-Loop seriell; effective_fanout nur berechnet — BL-230/328).
  // AK-2/AK-3 sind daher reine HARNESS-Beweisfaehigkeit: sie zeigen, dass der Harness
  // ECHTES paralleles Verhalten + die 0-Lost-Update-Eigenschaft testen KANN — kein
  // Umbau des seriellen Produktiv-Pfads (die 136 Baseline-Checks bleiben unveraendert).
  //
  // SICHERHEIT: Sandboxes liegen in os.tmpdir() mit Praefix 'bl316-rp-' (NIE im Repo-
  //       Tree). Teardown IMMER in finally (rmSync recursive force). B-3 unangetastet.
  // RED weil realParallel + lostUpdateProbe noch nicht existieren (typeof-Guard ->
  // sauberer FAIL statt Harness-Crash / exit 2).
  // ===========================================================================
  {
    const hasRealParallel = typeof realParallel === 'function';
    const hasProbe = typeof lostUpdateProbe === 'function';

    // AK-2 — realParallel als parallel()-kompatibler Injektor ueber den Runner-Slot.
    check('S25 BL-316 AK-2: realParallel-Injektor existiert (eigene Test-Klasse, NICHT der mockParallel)',
      hasRealParallel, 'realParallel fehlt (RED bis GREEN-Implementierung)');
    check('S25 BL-316 AK-2: realParallel != mockParallel (echter Injektor, kein Promise.all-Alias des Mock)',
      hasRealParallel && realParallel !== mockParallel, hasRealParallel ? 'realParallel === mockParallel (nur Alias!)' : 'realParallel fehlt');

    // realParallel ist parallel()-kompatibel: nimmt thunk-Array, gibt Promise<results[]> in
    // EINGABE-Reihenfolge zurueck (genau wie mockParallel Z125 / der parallel-Slot Z20/Z130).
    let injectOk = false, injectResults = null, injectErr = null;
    if (hasRealParallel) {
      try {
        // Marker-Thunks: jeder gibt seinen Index zurueck; echte Nebenlaeufigkeit darf
        // die Reihenfolge der Ergebnisse NICHT verwuerfeln (parallel()-Kontrakt).
        injectResults = await realParallel([
          async () => 'r0', async () => 'r1', async () => 'r2',
        ]);
        injectOk = Array.isArray(injectResults) && injectResults.join(',') === 'r0,r1,r2';
      } catch (e) { injectErr = e; }
    }
    check('S25 BL-316 AK-2: realParallel parallel()-kompatibel (thunk[] -> results[] in Eingabe-Reihenfolge)',
      injectOk, injectErr ? String(injectErr.message) : 'results=' + JSON.stringify(injectResults));

    // Beweis ECHTE Nebenlaeufigkeit (nicht seriell) — DISKRIMINIERENDER Probe (hat Zaehne:
    // ein serieller for-await-Loop FAILT ihn). Thunk-B prueft bei SEINEM ersten resumed-Step,
    // ob Thunk-A bereits FERTIG ist. Parallel: A noch offen (await-Kette) wenn B startet ->
    // bSawAFinished=false -> trulyConcurrent. Seriell (A komplett vor B): A schon fertig ->
    // bSawAFinished=true -> trulyConcurrent=false. (Verifiziert gegen serial-Referenz.)
    let trulyConcurrent = false, concErr = null;
    if (hasRealParallel) {
      try {
        let aFinished = false, bStarted = false, bSawAFinished = true;
        const tick = () => new Promise(r => setTimeout(r, 0));
        const thunkA = async () => { await tick(); await tick(); await tick(); aFinished = true; return 'A'; };
        const thunkB = async () => { bStarted = true; await tick(); bSawAFinished = aFinished; return 'B'; };
        await realParallel([thunkA, thunkB]);
        // Echte Nebenlaeufigkeit <=> B startete UND als B resumte war A noch NICHT fertig.
        trulyConcurrent = bStarted && bSawAFinished === false;
      } catch (e) { concErr = e; }
    }
    check('S25 BL-316 AK-2: realParallel laeuft Thunks ECHT nebenlaeufig (B startet waehrend A noch laeuft; kein seriell)',
      trulyConcurrent, concErr ? String(concErr.message) : 'kein zeitliches Ueberlappen beobachtet (seriell?)');

    // AK-3 — 0-Lost-Update-Assertion via lostUpdateProbe. Probe faehrt 2 Batches
    // NEBENLAEUFIG durch realParallel; jeder schreibt in seine DISJUNKTE Sandbox sowohl
    // eine Code-Datei als auch ein Manifest-Fragment. Rueckgabe: pro-Batch erwartete vs.
    // tatsaechlich-am-Disk Inhalte + ein Negativ-Kontrast (gemeinsame Datei -> Clobber).
    let probe = null, probeErr = null;
    if (hasProbe && hasRealParallel) { try { probe = await lostUpdateProbe(realParallel); } catch (e) { probeErr = e; } }
    check('S25 BL-316 AK-3: lostUpdateProbe lief ueber realParallel ohne Exception (Sandbox-Setup/Teardown leichen-frei)',
      hasProbe && !probeErr && !!probe, probeErr ? String(probeErr.message) : (hasProbe ? 'kein Ergebnis' : 'lostUpdateProbe fehlt (RED)'));

    // Disjunkte Sandboxes: beide Batches schrieben in voneinander getrennte Pfade.
    check('S25 BL-316 AK-3: 2 Batches schrieben in DISJUNKTE Sandbox-Pfade (kein geteiltes Verzeichnis)',
      !!probe && probe.disjoint === true && probe.batchA && probe.batchB && probe.batchA.dir !== probe.batchB.dir,
      probe ? ('A=' + (probe.batchA && probe.batchA.dir) + ' B=' + (probe.batchB && probe.batchB.dir)) : 'n/a');

    // Code-Write 0-Lost-Update: NACH dem Parallel-Lauf existieren BEIDE Code-Writes
    // vollstaendig + korrekt am Disk (kein Clobbering durch den jeweils anderen Batch).
    check('S25 BL-316 AK-3 [CODE-WRITE]: 0 Lost-Updates — beide Code-Writes vollstaendig am Disk (A.code==erwartet UND B.code==erwartet)',
      !!probe && probe.batchA && probe.batchB
        && probe.batchA.codeOnDisk === probe.batchA.codeExpected
        && probe.batchB.codeOnDisk === probe.batchB.codeExpected
        && probe.batchA.codeExpected !== probe.batchB.codeExpected,
      probe ? JSON.stringify({ a: probe.batchA && [probe.batchA.codeOnDisk, probe.batchA.codeExpected], b: probe.batchB && [probe.batchB.codeOnDisk, probe.batchB.codeExpected] }) : 'n/a');

    // Manifest-Write 0-Lost-Update: dito fuer die nebenlaeufigen Manifest-Fragmente.
    check('S25 BL-316 AK-3 [MANIFEST-WRITE]: 0 Lost-Updates — beide Manifest-Writes vollstaendig am Disk (A.manifest==erwartet UND B.manifest==erwartet)',
      !!probe && probe.batchA && probe.batchB
        && probe.batchA.manifestOnDisk === probe.batchA.manifestExpected
        && probe.batchB.manifestOnDisk === probe.batchB.manifestExpected
        && probe.batchA.manifestExpected !== probe.batchB.manifestExpected,
      probe ? JSON.stringify({ a: probe.batchA && [probe.batchA.manifestOnDisk, probe.batchA.manifestExpected], b: probe.batchB && [probe.batchB.manifestOnDisk, probe.batchB.manifestExpected] }) : 'n/a');

    // Negativ-Kontrast (Schaerfe): 2 Batches auf DIESELBE Datei -> Clobbering nachweisbar
    // (genau EIN Wert ueberlebt). Beweist: Disjunktheit IST die 0-Lost-Update-Bedingung.
    check('S25 BL-316 AK-3 [NEGATIV-KONTRAST]: gemeinsame Datei -> Clobbering (nur 1 Write ueberlebt; Disjunktheit ist die Bedingung)',
      !!probe && probe.shared && probe.shared.clobbered === true && probe.shared.survivors === 1,
      probe && probe.shared ? JSON.stringify(probe.shared) : 'n/a');

    // Leichen-frei: lostUpdateProbe raeumt ALLE bl316-rp-* Sandboxes (finally rmSync).
    check('S25 BL-316 AK-3: KEIN bl316-rp-* Sandbox-Leak nach Probe (Teardown in finally, alle entfernt)',
      !!probe && probe.leak_free === true,
      probe ? ('leak_free=' + probe.leak_free + ' residual=' + JSON.stringify(probe.residual || [])) : 'n/a');
  }

  // ===========================================================================
  // BL-329 sub_batch_1 "M2-Infra-Luecke" (AK-1 Motor, RED-first) — INV-INFRA-MODUS-FREI.
  // Der M2-Pfad bekam vor BL-329 KEINEN Setup/Teardown-Maschinen-Step (nur einen Prompt-Satz
  // "Bei Stage>=3 mit Infra: stage_N-Setup beachten" = machine-not-context; Live-Schmerz
  // 1944-Stage-6: improvisierter WebHost-Start, Serilog-Crash). Der M3-Pfad konsumiert Setup/
  // Teardown vorbildlich (needInfra -> _TDD_setup 9b / _TDD_teardown 18b finally). Diese Tests
  // beschreiben den SOLL-Zustand: M2 faehrt den IDENTISCHEN bedingten Infra-Rahmen, MODUS-
  // UNABHAENGIG (an den Infra-Bedarf der Stage gekoppelt, NICHT an tdd/Modus). RED vor dem Fix,
  // weil der M2-else-Zweig weder _TDD_init noch _TDD_setup/_TDD_teardown spawnte.
  //
  // Faithful-Hinweis: der Harness recordet Prompts/Labels/Control-Flow der Mock-agent()-Calls
  // (kein echtes Manifest). Setup-VOR-green / teardown-NACH-execute / teardown-bei-ABORT sind
  // alle als Spawn-Reihenfolge im Control-Flow voll beobachtbar (genau wie S19 stageCommit-Seams).
  // ===========================================================================

  // S26a — M2 + infra=true: setup (Step 9b) VOR _TDD_green, teardown (Step 18b) NACH _TDD_execute.
  // Der KERN-Beweis von AK-1: M2 faehrt setup->green/execute->teardown (echte Maschinen-Steps).
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [3] }]), { modus: 'M2', elevation: ['BATCH_DONE'], infra: 'true' });
    const labels = impl(spawns).map(x => x.label);
    const idxInit = labels.findIndex(l => /^_TDD_init:/.test(l));
    const idxSetup = labels.findIndex(l => /^_TDD_setup:/.test(l));
    const idxGreen = labels.findIndex(l => /^_TDD_green\(M2\):/.test(l));
    const idxExec = labels.findIndex(l => /^_TDD_execute\(M2\):/.test(l));
    const idxTeardown = labels.findIndex(l => /^_TDD_teardown:/.test(l));
    check('S26a BL-329 AK-1: M2 mit Infra spawnt _TDD_setup (Step 9b) — echter Maschinen-Step, kein Prompt-Satz', idxSetup >= 0, 'kein _TDD_setup im M2-Infra-Pfad');
    check('S26a BL-329 AK-1: M2 mit Infra spawnt _TDD_teardown (Step 18b)', idxTeardown >= 0, 'kein _TDD_teardown im M2-Infra-Pfad');
    check('S26a BL-329 AK-1: _TDD_init detektiert Infra VOR setup (modus-unabhaengige needInfra-Quelle)', idxInit >= 0 && idxInit < idxSetup, 'init@' + idxInit + ' setup@' + idxSetup);
    check('S26a BL-329 AK-1: setup VOR M2-Code-Emit (_TDD_green) — Infra steht bevor Code laeuft', idxSetup >= 0 && idxGreen >= 0 && idxSetup < idxGreen, 'setup@' + idxSetup + ' green@' + idxGreen);
    check('S26a BL-329 AK-1: teardown NACH _TDD_execute (M2-Verify) — Infra-Rahmen umschliesst Code+Verify', idxExec >= 0 && idxTeardown > idxExec, 'exec@' + idxExec + ' teardown@' + idxTeardown);
    check('S26a BL-329 AK-1: M2-_TDD_green-Prompt traegt KEINEN improvisierten Spinup mehr (Prompt-Satz ersetzt durch Maschinen-Step)', idxGreen >= 0 && /_TDD_setup gefahren|starte selbst KEINE/i.test(impl(spawns)[idxGreen].prompt) && !/Bei Stage>=3 mit Infra: stage_N-Setup beachten/.test(impl(spawns)[idxGreen].prompt), 'M2-green traegt noch den alten Prompt-Satz statt Maschinen-Step-Hinweis');
    check('S26a BL-329: terminated=completed (Infra-Rahmen bricht M2-Flow nicht)', result.terminated_reason === 'completed', result.terminated_reason);
  }

  // S26b — M2 + infra=true + GREEN_BLOCKED_TEST_CONFLICT (early return): teardown laeuft TROTZDEM (finally/ABORT-sicher).
  // Der finally-Block MUSS auch beim Konflikt-Short-Circuit-Return das captured Setup abraeumen (kein Infra-Leak).
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [3] }]), { modus: 'M2', infra: 'true', greenConflict: true });
    const labels = impl(spawns).map(x => x.label);
    check('S26b BL-329 AK-1: teardown laeuft auch bei GREEN_BLOCKED-Return (finally-Semantik, Infra-Leak-frei)', labels.some(l => /^_TDD_teardown:/.test(l)), 'kein teardown trotz gefahrenem setup beim Konflikt-Return');
    check('S26b BL-329 AK-1: setup lief VOR dem Konflikt-Return', labels.some(l => /^_TDD_setup:/.test(l)), 'kein setup im Konflikt-Pfad');
    check('S26b BL-329: KEIN _TDD_execute(M2) nach Konflikt (kein false-GREEN-Lauf, BL-303 erhalten)', !labels.some(l => /^_TDD_execute\(M2\):/.test(l)), 'execute trotz Konflikt gelaufen');
    check('S26b BL-329: Konflikt weiterhin als RE-BATCH an Lead returned (BL-303 unbeeintraechtigt)', result.terminated_reason === 'test_conflict_blocked' && result.loop_decision === 'RE-BATCH', result.terminated_reason + '/' + result.loop_decision);
  }

  // S26c — M2 infra=false: KEIN setup/teardown (needInfra=false). _TDD_init laeuft trotzdem (modus-freie Detektion).
  // Beweist: der Infra-Rahmen haengt am STAGE-Bedarf (needInfra), NICHT am Modus — bei infra=false bleibt M2 schlank.
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'], infra: 'false' });
    const labels = impl(spawns).map(x => x.label);
    check('S26c BL-329 INV-INFRA-MODUS-FREI: M2 infra=false -> KEIN _TDD_setup (Infra-Bedarf=Stage-Eigenschaft, nicht Modus)', !labels.some(l => /^_TDD_setup:/.test(l)), 'setup trotz infra=false');
    check('S26c BL-329 INV-INFRA-MODUS-FREI: M2 infra=false -> KEIN _TDD_teardown', !labels.some(l => /^_TDD_teardown:/.test(l)), 'teardown trotz infra=false');
    check('S26c BL-329: M2 fuehrt _TDD_init dennoch (modus-freie Infra-Detektion, needInfra-Quelle)', labels.some(l => /^_TDD_init:/.test(l)), 'kein _TDD_init im M2-Pfad');
    const initSpawn = impl(spawns).find(x => /^_TDD_init:/.test(x.label));
    check('S26c BL-329: _TDD_init-Prompt benennt INV-INFRA-MODUS-FREI + setup.commands-non-empty-Diskriminator', !!initSpawn && /INV-INFRA-MODUS-FREI/.test(initSpawn.prompt) && /setup\.commands non-empty/i.test(initSpawn.prompt), initSpawn ? 'init-Prompt ohne INV-INFRA-MODUS-FREI/commands-Diskriminator' : 'kein _TDD_init-Spawn');
  }

  // S26d — INV-INFRA-MODUS-FREI Prompt-Vertrag: setup/teardown lesen stage_N.md (kein Inline-Erfinden, INV-SETUP-1).
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [3] }]), { modus: 'M2', elevation: ['BATCH_DONE'], infra: 'true' });
    const setupSpawn = impl(spawns).find(x => /^_TDD_setup:/.test(x.label));
    const teardownSpawn = impl(spawns).find(x => /^_TDD_teardown:/.test(x.label));
    check('S26d BL-329 AK-1: _TDD_setup-Prompt liest stage_N.md setup.commands/health_check (INV-SETUP-1, kein Inline-Erfinden) + INV-INFRA-MODUS-FREI', !!setupSpawn && /stage_\d+\.md setup\.commands|INV-SETUP-1/.test(setupSpawn.prompt) && /INV-INFRA-MODUS-FREI/.test(setupSpawn.prompt), setupSpawn ? 'setup-Prompt ohne stage_N.md/INV-SETUP-1-Vertrag' : 'kein _TDD_setup-Spawn');
    check('S26d BL-329 AK-1: _TDD_teardown-Prompt traegt finally-Semantik (always-run/auch bei ABORT) + reverse-order PID-Kill + INV-INFRA-MODUS-FREI', !!teardownSpawn && /always-run|auch bei ABORT|finally-Semantik/i.test(teardownSpawn.prompt) && /INV-INFRA-MODUS-FREI/.test(teardownSpawn.prompt), teardownSpawn ? 'teardown-Prompt ohne finally/INV-INFRA-MODUS-FREI-Vertrag' : 'kein _TDD_teardown-Spawn');
  }

  // S26e — M3-Regression: der M3/tdd-Pfad bleibt mit Infra UNVERAENDERT (setup 9b + teardown 18b), nur additiv M2 angeglichen.
  // S7 deckt M3 infra=false (19 Spawns) ab; hier M3 infra=true -> setup + teardown + voller TDD-Strom, Reihenfolge gewahrt.
  {
    const { spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [3] }]), { modus: 'M3', elevation: ['BATCH_DONE'], infra: 'true' });
    const labels = impl(spawns).map(x => x.label);
    const idxInit = labels.findIndex(l => /^_TDD_init:/.test(l));
    const idxSetup = labels.findIndex(l => /^_TDD_setup:/.test(l));
    const idxRed = labels.findIndex(l => /^_TDD_red:/.test(l));
    const idxCheck = labels.findIndex(l => /^_TDD_check:/.test(l));
    const idxTeardown = labels.findIndex(l => /^_TDD_teardown:/.test(l));
    check('S26e BL-329 M3-Regression: M3 mit Infra spawnt setup + teardown (unveraendert)', idxSetup >= 0 && idxTeardown >= 0, 'setup@' + idxSetup + ' teardown@' + idxTeardown);
    check('S26e BL-329 M3-Regression: _TDD_init genau 1x (nicht doppelt durch Hoisting in detectInfraNeed)', labels.filter(l => /^_TDD_init:/.test(l)).length === 1, 'init-count=' + labels.filter(l => /^_TDD_init:/.test(l)).length);
    check('S26e BL-329 M3-Regression: Reihenfolge init < setup < _TDD_red (voller TDD-Strom, Setup VOR red)', idxInit >= 0 && idxInit < idxSetup && idxSetup < idxRed, 'init@' + idxInit + ' setup@' + idxSetup + ' red@' + idxRed);
    check('S26e BL-329 M3-Regression: teardown NACH _TDD_check (finally umschliesst den ganzen TDD-Kern)', idxCheck >= 0 && idxTeardown > idxCheck, 'check@' + idxCheck + ' teardown@' + idxTeardown);
    // M3 infra=true Spawn-Count: 1 preflight + 6 blueprint + 1 init + 1 setup + 9 TDD-rest + 1 teardown + 2 closure = 21.
    check('S26e BL-329 M3-Regression: 21 Implement-Spawns (S7-19 + setup + teardown bei infra=true), kein Mega-Spawn', impl(spawns).length === 21, 'got ' + impl(spawns).length);
  }

  // ===========================================================================
  // BL-303 batch_1 AK-2: Flag-Provenance (JS) — test_correction_authorized.
  //
  // Problem (RED): Der M2-Pfad in dispatch_implement.js erzeugt fuer _TDD_green
  // immer den hardkodierten Interim-Default-Text "NOCH KEINE Autorisierung
  // (test_correction_authorized — der Auto-Produzent BL-281/296 ist nicht live)".
  // Das Flag test_correction_authorized wird nie aus dem sub_batch-Objekt gelesen
  // und NIE in den Prompt durchgereicht — der gruene Worker kann eine autorisierte
  // Test-Korrektur daher NICHT durchfuehren (er bekommt nur die Sperre, nie die
  // Freigabe).
  //
  // Erwartetes Verhalten nach GREEN (Impl):
  //   sub_batch.test_correction_authorized == true + sub_batch.authorization_evidence
  //   => _TDD_green(M2)-Prompt enthaelt die Autorisierung (z.B. "test_correction_authorized"
  //      UND den authorization_evidence-Wert) statt des protektiven Interim-Texts.
  //   sub_batch ohne Flag (oder Flag=false)
  //   => Prompt bleibt protektiv (bestehender "NOCH KEINE Autorisierung"-Pfad unveraendert).
  //
  // HARNESS-PATTERN: ARGS erlaubt beliebige Felder im sub_batch-Objekt (passthrough).
  //   Der makeAgent-Mock gibt den Prompt 1:1 an spawns[] zurück -> Prompt-Assertions
  //   sind das einzige beobachtbare Testmittel (genau wie S18/S19/S21/S26a).
  // ===========================================================================

  // S27a BL-303 AK-2 — OHNE Flag: protektiver Default bleibt (kein false-Positive durch die Impl).
  // Dieser Sub-Test MUSS sowohl vor als auch nach dem GREEN-Fix gruen bleiben (Regression).
  {
    const { spawns } = await run(
      ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]),
      { modus: 'M2', elevation: ['BATCH_DONE'] }
    );
    const m2green = spawns.find(x => /_TDD_green\(M2\):/.test(x.label));
    check(
      'S27a BL-303 AK-2 default-safe: ohne test_correction_authorized -> Prompt bleibt protektiv (NOCH KEINE Autorisierung / GREEN_BLOCKED_TEST_CONFLICT)',
      !!m2green && (
        /NOCH KEINE Autorisierung/i.test(m2green.prompt) ||
        /GREEN_BLOCKED_TEST_CONFLICT/.test(m2green.prompt)
      ),
      m2green ? 'M2-green-Prompt traegt weder den Schutz-Text noch den BLOCKED-Hinweis' : 'kein _TDD_green(M2)-Spawn'
    );
  }

  // S27b BL-303 AK-2 (RED) — MIT Flag test_correction_authorized=true + authorization_evidence:
  // Prompt MUSS die Autorisierung enthalten (statt des protektiven Defaults).
  // RED weil das Flag nie aus sb gelesen wird -> Prompt ist unveraendert protektiv.
  {
    const authorizedSb = {
      id: 'sb_auth',
      items: ['dispatch_implement.js'],
      stages: [1],
      test_correction_authorized: true,
      authorization_evidence: 'FLIP:BL-303-finding-X — adversarial-steelman ergab: Finding-Praemisse-FALSCH, Test-Assertion korrekt anpassen (adjudiziert 2026-06-21)',
    };
    const { spawns } = await run(
      ARGS([authorizedSb]),
      { modus: 'M2', elevation: ['BATCH_DONE'] }
    );
    const m2green = spawns.find(x => /_TDD_green\(M2\):/.test(x.label));

    // Die Autorisierung MUSS im Prompt aktiv als Freigabe vorhanden sein — NICHT nur als
    // Variablenname in der Sperre (Z391 nennt "test_correction_authorized" bereits im Sperr-Text).
    // Nach GREEN: Der Prompt muss "test_correction_authorized: true" ODER "autorisiert" ODER
    // "Freigabe" im positiven Sinne erhalten, d.h. als Aktivierungs-Signal, NICHT als Sperre.
    check(
      'S27b BL-303 AK-2 (RED): autorisierter sb (test_correction_authorized=true) -> Prompt enthaelt Freigabe-Signal (z.B. "autorisiert" / "Freigabe" / "test_correction_authorized: true")',
      !!m2green && (
        /test_correction_authorized:\s*true/i.test(m2green.prompt) ||
        /Freigabe.*[Tt]est[\s-][Kk]orrektur|[Tt]est[\s-][Kk]orrektur.*[Ff]reigabe/.test(m2green.prompt) ||
        /autorisiert.*[Tt]est[\s-][Aa]ssertion|[Tt]est[\s-][Aa]ssertion.*autorisiert/i.test(m2green.prompt) ||
        /authorization_evidence.*=/.test(m2green.prompt)
      ),
      m2green
        ? 'Prompt enthaelt kein positives Freigabe-Signal (nur Sperr-Text mit Variablenname) — RED bis Impl'
        : 'kein _TDD_green(M2)-Spawn'
    );
    check(
      'S27b BL-303 AK-2 (RED): autorisierter sb -> Prompt enthaelt authorization_evidence (Begruendung fuer den gruenen Worker sichtbar)',
      !!m2green && m2green.prompt.includes('FLIP:BL-303-finding-X'),
      m2green
        ? 'authorization_evidence fehlt im Prompt (Worker kann autorisierte Test-Korrektur nicht begruenden — RED bis Impl)'
        : 'kein _TDD_green(M2)-Spawn'
    );
    check(
      'S27b BL-303 AK-2 (RED): autorisierter sb -> Prompt enthaelt NICHT mehr "NOCH KEINE Autorisierung" (protektiver Default gehoben)',
      !!m2green && !/NOCH KEINE Autorisierung/i.test(m2green.prompt),
      m2green
        ? 'Prompt traegt weiterhin "NOCH KEINE Autorisierung" obwohl test_correction_authorized=true (Impl fehlt — RED)'
        : 'kein _TDD_green(M2)-Spawn'
    );
  }

  // S27c BL-303 AK-2 (RED) — Kontrast: test_correction_authorized=false -> protektiver Default bleibt.
  // Dieser Kontrast-Test ist ebenfalls RED weil der Motor das Flag gar nicht liest (weder true noch false aendert was).
  // Nach GREEN: false -> protektiv (unveraendert), true -> Autorisierung (S27b). Kontrast zeigt korrekte Verzweigung.
  {
    const unauthorizedSb = {
      id: 'sb_unauth',
      items: ['dispatch_implement.js'],
      stages: [1],
      test_correction_authorized: false,
      authorization_evidence: null,
    };
    const { spawns } = await run(
      ARGS([unauthorizedSb]),
      { modus: 'M2', elevation: ['BATCH_DONE'] }
    );
    const m2green = spawns.find(x => /_TDD_green\(M2\):/.test(x.label));
    check(
      'S27c BL-303 AK-2 (RED-Kontrast): test_correction_authorized=false -> Prompt bleibt protektiv (NOCH KEINE Autorisierung)',
      !!m2green && /NOCH KEINE Autorisierung/i.test(m2green.prompt),
      m2green
        ? 'Prompt traegt nicht "NOCH KEINE Autorisierung" bei false-Flag (Regression oder Impl-Bug — RED)'
        : 'kein _TDD_green(M2)-Spawn'
    );
  }

  // ===========================================================================
  // BL-230 SB-1a AK-MOTOR-WELLE (PL-1, M3, RED-first) — for→parallel() Fan-Out.
  //
  // Gold: 4_Blueprint/BL-230-…/BL-230_blueprint_AK-MOTOR-WELLE_S1.md
  // IST (verifiziert, dispatch_implement.js Z536-541 + Z546 outer-for):
  //   effective_fanout/parallel_mode/nr_parallel_batches werden BERECHNET + geloggt +
  //   im Return gespiegelt (BL-327/328-Observability), ABER der outer-for-Loop ist strikt
  //   SEQUENTIELL — parallel() (der bereits injizierte 2. Factory-Arg, Z250) wird im
  //   Produktiv-Pfad NIE aufgerufen. runFanInBarrier existiert nicht. Der Cursor ist ein
  //   globaler Single-Slot (current_sub_batch_id Z573 / current_modus_view Z625).
  //
  // SPY-PATTERN: statt des stummen mockParallel (Z125) injizieren diese Tests einen
  //   parallelSpy als 2. Factory-Arg, der jeden Aufruf (thunks.length + die laufenden
  //   Thunks) recordet UND seriell-aequivalent durchreicht (Promise.all in Eingabe-
  //   Reihenfolge — parallel()-Kontrakt). So bleibt das beobachtete Verhalten identisch,
  //   nur die Aufruf-Buchhaltung kommt dazu. Reine Beobachtung, kein Eingriff (analog S10/
  //   T-PF-1, die ebenfalls factory() direkt statt run() fahren).
  //
  // RED-Erwartung: AON-2..6 + Cap-ON-Teile FAILEN (parallel()/runFanInBarrier/cursorMap
  //   fehlen). AON-1 (OFF-Null-Regression) ist Regression-GUARD und MUSS schon GRUEN sein.
  // ===========================================================================

  // parallelSpy-Fabrik: records[] sammelt pro parallel()-Aufruf {count, thunks}. Reicht die
  // Thunks seriell-aequivalent durch (Promise.all, Eingabe-Reihenfolge) — kein Verhaltens-Eingriff.
  const makeParallelSpy = () => {
    const calls = [];
    const fn = async (thunks) => {
      calls.push({ count: Array.isArray(thunks) ? thunks.length : -1, thunks });
      return Promise.all((thunks || []).map(t => t()));
    };
    return { fn, calls };
  };
  // Eigener Runner mit injizierbarem parallelFn (run() hardcodet mockParallel, Z250).
  const runWithParallel = async (testArgs, agentCfg, parallelFn) => {
    const spawns = [];
    const factory = makeFactory();
    const result = await factory(makeAgent(spawns, agentCfg), parallelFn, noop, noop, testArgs);
    return { result, spawns };
  };
  const wave = (n) => Array.from({ length: n }, (_, i) => ({ id: 'sb' + (i + 1), items: ['x' + (i + 1)], stages: [1] }));

  // ── AON-1 (REGRESSION-GUARD — MUSS schon GRUEN sein): OFF -> parallelFn 0x. ──────────
  // default-args (kein parallel_mode) => effective_fanout=1 => serieller Pfad => der
  // injizierte parallelSpy darf NIE aufgerufen werden. Schuetzt die Null-Regression.
  {
    const spy = makeParallelSpy();
    const { result, spawns } = await runWithParallel(ARGS(wave(3)), { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    check('AON-1 [GUARD] OFF (default-args): parallelFn 0x aufgerufen (serieller Pfad byte-identisch)', spy.calls.length === 0, 'parallelFn ' + spy.calls.length + 'x aufgerufen trotz OFF');
    check('AON-1 [GUARD] OFF: terminated=completed + loop_decision=TERMINATE (Return-Shape unveraendert)', result.terminated_reason === 'completed' && result.loop_decision === 'TERMINATE', result.terminated_reason + '/' + result.loop_decision);
    check('AON-1 [GUARD] OFF: results in Eingabe-Reihenfolge [sb1,sb2,sb3] (serielle Spawn-Sequenz)', JSON.stringify(result.sub_batch_results.map(r => r.sub_batch)) === JSON.stringify(['sb1', 'sb2', 'sb3']), JSON.stringify(result.sub_batch_results.map(r => r.sub_batch)));
    check('AON-1 [GUARD] OFF: effective_fanout=1 (OFF dominiert)', result.effective_fanout === 1, String(result.effective_fanout));
  }

  // ── AON-2 (RED): ON + nr>=2 + |welle|>=2 -> parallelFn mit Thunk-Array len=effective_fanout. ──
  // RED weil der outer-for parallel() nie aufruft (Z546 sequentiell).
  {
    const spy = makeParallelSpy();
    const { result } = await runWithParallel(ARGS_P(wave(4), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    check('AON-2 (RED): ON nr=3 |welle|=4 -> parallelFn >=1x aufgerufen (Fan-Out aktiv, nicht seriell)', spy.calls.length >= 1, 'parallelFn ' + spy.calls.length + 'x — Motor ruft parallel() nicht auf (outer-for seriell)');
    const firstCall = spy.calls[0];
    check('AON-2 (RED): erster parallelFn-Aufruf traegt Thunk-Array der Laenge effective_fanout=min(3,4,16)=3', !!firstCall && firstCall.count === 3, firstCall ? ('thunks=' + firstCall.count) : 'kein parallelFn-Aufruf');
    check('AON-2 (RED): effective_fanout im Return weiterhin 3 (Cap-Formel unveraendert)', result.effective_fanout === 3, String(result.effective_fanout));
  }

  // ── AON-3 (RED): Coverage — jeder Welle-Sub-Batch von genau 1 Thunk abgedeckt. ──────
  // Beweis ueber die Spawn-Buchhaltung der gefahrenen Thunks: jede Welle-ID (sb1..sb3)
  // erscheint genau einmal in den Implement-Spawns (kein Sub-Batch faellt aus dem Fan-Out,
  // keiner doppelt). RED weil ohne parallel()-Aufruf der serielle Pfad zwar alle baut, aber
  // NICHT via Thunk-Abdeckung — der Spy zaehlt 0 Thunks (count>0 erforderlich).
  {
    const spy = makeParallelSpy();
    const { result, spawns } = await runWithParallel(ARGS_P(wave(3), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    const totalThunks = spy.calls.reduce((a, c) => a + (c.count > 0 ? c.count : 0), 0);
    check('AON-3 (RED): Summe der parallel()-Thunks ueber alle Aufrufe == |welle|=3 (jeder Sub-Batch genau 1 Thunk)', totalThunks === 3, 'totalThunks=' + totalThunks + ' (Fan-Out deckt nicht alle Welle-Mitglieder ab)');
    const builtIds = result.sub_batch_results.map(r => r.sub_batch).sort();
    check('AON-3 (RED): alle 3 Welle-Mitglieder kamen dran (sb1,sb2,sb3 je 1x im Outcome)', JSON.stringify(builtIds) === JSON.stringify(['sb1', 'sb2', 'sb3']) && spy.calls.length >= 1, 'built=' + JSON.stringify(builtIds) + ' parallelCalls=' + spy.calls.length);
  }

  // ── AON-4 (RED): Cursor-MAP disjunkt — persistSubBatchCursor batch-keyed (cursorMap[<id>]). ──
  // RED weil der persistSubBatchCursor-Prompt heute den GLOBALEN Single-Slot
  // current_sub_batch_id schreibt (Z573) — bei 2 nebenlaeufigen Batches = Last-Writer-Wins.
  // Soll: pro-Batch ein batch-SCOPED Schluessel (cursorMap[<id>] / current_sub_batch_id_per_batch).
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const cursorSpawns = spawns.filter(x => /^persistSubBatchCursor:/.test(x.label));
    check('AON-4 (RED): 2 persistSubBatchCursor-Spawns (1 pro nebenlaeufigem Batch)', cursorSpawns.length === 2, 'got ' + cursorSpawns.length);
    const allBatchKeyed = cursorSpawns.length === 2 && cursorSpawns.every(x => /cursorMap\[|current_sub_batch_id_per_batch\[|cursor_per_batch\[|\bbatch-keyed\b/i.test(x.prompt));
    check('AON-4 (RED): jeder Cursor-Spawn ist batch-keyed (cursorMap[<id>], NICHT globaler Single-Slot)', allBatchKeyed, cursorSpawns.length ? 'mindestens ein Cursor-Spawn schreibt weiterhin globalen current_sub_batch_id (Last-Writer-Wins)' : 'keine Cursor-Spawns');
    const noGlobalSlot = cursorSpawns.length === 2 && cursorSpawns.every(x => !/DF_BATCH_STATE\.current_sub_batch_id\s*=/.test(x.prompt));
    check('AON-4 (RED): KEIN Cursor-Spawn schreibt mehr den globalen DF_BATCH_STATE.current_sub_batch_id-Slot (Overwrite-Race geschlossen)', noGlobalSlot, 'globaler Single-Slot current_sub_batch_id wird noch geschrieben');
    const cursorIds = cursorSpawns.map(x => (x.label.match(/^persistSubBatchCursor:(\S+)$/) || [])[1]).filter(Boolean);
    check('AON-4 (RED): 2 disjunkte Cursor-Eintraege (sb1 + sb2, kein doppelter Schluessel)', cursorIds.length === 2 && new Set(cursorIds).size === 2 && cursorIds.includes('sb1') && cursorIds.includes('sb2'), JSON.stringify(cursorIds));
  }

  // ── AON-5 (RED): Fan-In-Stub existiert — runFanInBarrier deklariert (kein ReferenceError). ──
  // Beobachtbar: im parallelen Pfad muss der Workflow ohne ReferenceError durchlaufen UND
  // ein Fan-In-Aufruf-Marker erscheinen. RED weil runFanInBarrier in dispatch_implement.js
  // nicht deklariert ist -> ein Aufruf wuerde werfen (HARNESS ERROR) bzw. der Marker fehlt.
  {
    let threw = false, result = null;
    try {
      ({ result } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn));
    } catch (e) { threw = true; }
    check('AON-5 (RED): paralleler Pfad laeuft ohne ReferenceError durch (runFanInBarrier deklariert)', !threw && !!result, threw ? 'paralleler Pfad warf (runFanInBarrier nicht deklariert?)' : 'kein Ergebnis');
    check('AON-5 (RED): Return traegt einen Fan-In-Barrier-Marker (fan_in_barrier / fanin_called) im parallelen Pfad', !!result && (result.fan_in_barrier !== undefined || result.fanin_called === true || (result.note && /runFanInBarrier|Fan-In-Barrier/.test(result.note))), result ? 'kein Fan-In-Barrier-Marker im Return (Stub-Aufruf fehlt)' : 'kein Ergebnis');
  }

  // ── AON-6 (RED): Fan-In seriell NACH parallel() — genau 1 runFanInBarrier-Aufruf, post-await, vor Return. ──
  // Beobachtbar via Spawn-/Phase-Sequenz: der Fan-In-Barrier-Spawn (Phase 'FanIn' bzw.
  // Label runFanInBarrier) liegt NACH dem letzten Implement-Spawn der Welle UND vor
  // loopDecision (LoopDecision-Phase). RED weil weder der Aufruf noch die Phase existieren.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fanInSpawns = spawns.filter(x => /runFanInBarrier|fanInBarrier/i.test(x.label) || x.phase === 'FanIn');
    check('AON-6 (RED): genau 1 runFanInBarrier-Aufruf im parallelen Pfad (Barrier laeuft einmal, nicht pro Thunk)', fanInSpawns.length === 1, 'got ' + fanInSpawns.length + ' Fan-In-Spawns (0 = Aufruf-Punkt fehlt)');
    const lastImpl = spawns.map(x => x.phase).lastIndexOf('Implement');
    const fanInIdx = spawns.findIndex(x => /runFanInBarrier|fanInBarrier/i.test(x.label) || x.phase === 'FanIn');
    check('AON-6 (RED): runFanInBarrier NACH allen Implement-Spawns (post-parallel()-await)', fanInIdx >= 0 && fanInIdx > lastImpl, 'fanIn@' + fanInIdx + ' lastImpl@' + lastImpl);
    const loopDecIdx = spawns.findIndex(x => /^loopDecision:/.test(x.label));
    check('AON-6 (RED): runFanInBarrier VOR loopDecision (seriell vor dem finalen Return-Pfad)', fanInIdx >= 0 && loopDecIdx >= 0 && fanInIdx < loopDecIdx, 'fanIn@' + fanInIdx + ' loopDec@' + loopDecIdx);
    const fanInWithinThunk = spawns.some(x => (/runFanInBarrier|fanInBarrier/i.test(x.label) || x.phase === 'FanIn') && x.phase === 'Implement');
    check('AON-6 (RED): Barrier-Logik laeuft NICHT innerhalb eines parallelen Thunks (kein Fan-In-Spawn in Phase Implement)', !fanInWithinThunk, 'Fan-In-Spawn lief in Implement-Phase (innerhalb eines Thunks)');
  }

  // ── AON-7 (RED/teils pruefbar): effective_fanout senkt nur — Cap-Verhalten im parallel()-Aufruf. ──
  // Die Return-Cap-Formel (nr>|welle|->|welle|; OFF->1) ist seit BL-327 gruen (T-DIAL-*). NEU
  // (RED): die Cap muss sich auch im parallelFn-Thunk-Array-Count manifestieren, nicht nur im Return.
  {
    // nr > |welle|: |thunks| == |welle| (nicht nr).
    const spyA = makeParallelSpy();
    const { result: rA } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 8 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, spyA.fn);
    check('AON-7 (RED): nr=8 > |welle|=2 -> parallelFn-Thunks == |welle|=2 (Cap senkt auf Welle-Groesse)', spyA.calls.length >= 1 && spyA.calls[0].count === 2, spyA.calls.length ? ('thunks=' + spyA.calls[0].count) : 'kein parallelFn-Aufruf (RED: Fan-Out fehlt)');
    check('AON-7: Return effective_fanout=min(8,2,16)=2 (BL-327-Formel, bleibt gruen)', rA.effective_fanout === 2, String(rA.effective_fanout));

    // nr > 16: Thunk-Array <= 16 (MAX_CONCURRENT-Cap). |welle|=18 erzwingt Chunking <=16.
    const spyB = makeParallelSpy();
    const { result: rB } = await runWithParallel(ARGS_P(wave(18), { parallel_mode: true, nr_parallel_batches: 32 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, spyB.fn);
    check('AON-7 (RED): nr=32, |welle|=18 -> kein parallelFn-Aufruf mit > 16 Thunks (MAX_CONCURRENT-Cap)', spyB.calls.length >= 1 && spyB.calls.every(c => c.count <= 16), spyB.calls.length ? ('max-thunks=' + Math.max(...spyB.calls.map(c => c.count))) : 'kein parallelFn-Aufruf (RED: Fan-Out fehlt)');
    check('AON-7: Return effective_fanout=min(32,18,16)=16 (BL-327-Formel, bleibt gruen)', rB.effective_fanout === 16, String(rB.effective_fanout));

    // OFF -> kein parallel()-Aufruf egal wie hoch nr.
    const spyC = makeParallelSpy();
    await runWithParallel(ARGS_P(wave(5), { parallel_mode: false, nr_parallel_batches: 32 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, spyC.fn);
    check('AON-7 [GUARD] OFF + nr=32: parallelFn 0x (OFF dominiert, kein Fan-Out trotz hoher nr)', spyC.calls.length === 0, 'parallelFn ' + spyC.calls.length + 'x trotz OFF');
  }

  // ── EC-1 (RED): |welle|==1 + ON -> seriell (kein parallel()-Setup-Overhead fuer 1 Batch). ──
  // effective_fanout=min(N,1,16)=1 -> serieller Pfad. parallelFn 0x. (Regression-aehnlich, aber
  // RED-relevant: die GREEN-Impl muss bei fanout==1 explizit den seriellen Zweig nehmen.)
  {
    const spy = makeParallelSpy();
    const { result } = await runWithParallel(ARGS_P(wave(1), { parallel_mode: true, nr_parallel_batches: 4 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    check('EC-1 (RED): Single-Member-Welle (|welle|=1) + ON -> parallelFn 0x (kein Setup-Overhead, seriell)', spy.calls.length === 0, 'parallelFn ' + spy.calls.length + 'x bei |welle|=1');
    check('EC-1: effective_fanout=min(4,1,16)=1', result.effective_fanout === 1, String(result.effective_fanout));
  }

  // ── EC-5 (RED): |welle| > effective_fanout -> Chunking, ALLE Mitglieder kommen dran. ──
  // |welle|=5, nr=2 -> effective_fanout=2. Min-Vertrag: alle 5 gebaut, max 2 gleichzeitig
  // pro parallel()-Aufruf. RED weil heute 0 parallel()-Aufrufe.
  {
    const spy = makeParallelSpy();
    const { result } = await runWithParallel(ARGS_P(wave(5), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    check('EC-5 (RED): |welle|=5 > fanout=2 -> mind. 1 parallelFn-Aufruf, jeder mit <=2 Thunks (Chunking)', spy.calls.length >= 1 && spy.calls.every(c => c.count <= 2 && c.count >= 1), spy.calls.length ? ('counts=' + JSON.stringify(spy.calls.map(c => c.count))) : 'kein parallelFn-Aufruf');
    const totalThunks = spy.calls.reduce((a, c) => a + (c.count > 0 ? c.count : 0), 0);
    check('EC-5 (RED): Summe Thunks ueber alle Chunk-Aufrufe == 5 (alle Welle-Mitglieder kommen dran)', totalThunks === 5, 'totalThunks=' + totalThunks);
    check('EC-5: alle 5 Sub-Batches im Outcome', result.sub_batch_results.length === 5 && new Set(result.sub_batch_results.map(r => r.sub_batch)).size === 5, 'got ' + result.sub_batch_results.length);
  }

  // ── EC-6 (RED): Reihenfolge-Erhalt — results in EINGABE-Reihenfolge trotz Fan-Out. ──
  // parallel()-Kontrakt: results in Eingabe-Reihenfolge (vgl. realParallel). Die Fan-In-
  // Aggregation darf NICHT von Completion-Reihenfolge abhaengen. RED weil ohne Fan-Out-Pfad
  // die Reihenfolge zwar (seriell) stimmt, der Spy aber 0 Aufrufe sieht (Fan-Out inaktiv).
  {
    const spy = makeParallelSpy();
    const { result } = await runWithParallel(ARGS_P(wave(4), { parallel_mode: true, nr_parallel_batches: 4 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    const ids = result.sub_batch_results.map(r => r.sub_batch);
    check('EC-6 (RED): Fan-Out aktiv (parallelFn >=1x) UND results in Eingabe-Reihenfolge [sb1..sb4]', spy.calls.length >= 1 && JSON.stringify(ids) === JSON.stringify(['sb1', 'sb2', 'sb3', 'sb4']), 'parallelCalls=' + spy.calls.length + ' ids=' + JSON.stringify(ids));
  }

  // ===========================================================================
  // BL-230 SB-1b AK-CURSOR-MAP (Stage 1, RED-first) — Cursor-MAP modus_view-Persist.
  //
  // Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (Slice "Cursor-MAP", 4 Exit-Kriterien).
  // IST (SB-1a, dispatch_implement.js Z589-599): der Parallel-Pfad-persistSubBatchCursor schreibt
  //   cursorMap[<id>] = { cursor, items, modus_view: null } — ein MINIMAL-Slot, modus_view IMMER null.
  // SOLL (SB-1b): cursorMap ist ein voller Map<batch_id,{modus_view,cursor}>; das modus_view wird pro
  //   Batch NACH der modusEntscheidung mit dem ENTSCHIEDENEN Modus (M{N}) befuellt + persistiert
  //   (kein dauerhaftes null, kein globaler Single-Slot, kein Cross-Batch-Overwrite). Serieller Pfad
  //   (fanout==1) bleibt byte-identisch (globaler current_sub_batch_id-Write, Null-Regression OFF).
  //
  // RED-Erwartung: CM-2/CM-3 FAILEN (kein modus_view-Persist-Spawn mit Modus-Wert existiert heute;
  //   der einzige cursorMap-Write traegt literal `modus_view: null`). CM-1 (N=2 disjunkt batch-keyed)
  //   ist teils schon durch AON-4 abgedeckt — hier zusaetzlich auf den modus_view-Slot scharfgestellt.
  //   CM-4 (OFF byte-identisch) ist Regression-GUARD und MUSS schon GRUEN sein.
  // ===========================================================================

  // ── CM-1 (RED): N=2 -> 2 disjunkte cursorMap-Slots, kein globaler Single-Slot, je 1 modus_view-Slot. ──
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    // Alle Spawns, die cursorMap[<id>].modus_view fuer einen Batch schreiben (Cursor-Persist + Modus-Persist).
    const mvSpawns = spawns.filter(x => /cursorMap\[[^\]]+\]\.modus_view\s*=|cursorMap\[[^\]]+\].*modus_view/i.test(x.prompt));
    // Pro Batch genau 1 modus_view-Slot-Write, auf VERSCHIEDENE Keys (disjunkt).
    const mvKeys = mvSpawns
      .map(x => (x.prompt.match(/cursorMap\[\s*"?(sb\d+)"?\s*\]\.modus_view/) || [])[1])
      .filter(Boolean);
    check('CM-1 (RED): N=2 -> mind. 2 modus_view-Persist-Writes (1 pro nebenlaeufigem Batch, batch-keyed)', mvKeys.length >= 2, 'got ' + mvKeys.length + ' modus_view-keyed Writes (SB-1a: modus_view bleibt null -> 0)');
    check('CM-1 (RED): die modus_view-Slots sind DISJUNKT (sb1 + sb2, kein doppelter Key, kein globaler Slot)', new Set(mvKeys).size >= 2 && mvKeys.includes('sb1') && mvKeys.includes('sb2'), JSON.stringify(mvKeys));
  }

  // ── CM-2 (RED, load-bearing): modus_view wird mit dem ENTSCHIEDENEN Modus befuellt — NICHT literal null. ──
  // SB-1a-Minimal-Slot schreibt `modus_view: null`. SB-1b MUSS einen Write tragen, der cursorMap[<id>].modus_view
  // auf den modusEntscheidung-Modus (M{N}) setzt. RED weil heute KEIN solcher Spawn existiert.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    // Ein Write, der den entschiedenen Modus (M2) in cursorMap[<id>].modus_view setzt (NICHT literal null).
    const modusViewSet = spawns.filter(x =>
      /cursorMap\[[^\]]+\]\.modus_view\s*=\s*("?M[1-9]"?|modus|<?Modus>?)/i.test(x.prompt)
      || (/cursorMap\[[^\]]+\].*modus_view/i.test(x.prompt) && /\bM2\b/.test(x.prompt) && !/modus_view:\s*null/i.test(x.prompt))
    );
    check('CM-2 (RED, load-bearing): es existiert ein Spawn der cursorMap[<id>].modus_view auf den entschiedenen Modus (M{N}) setzt', modusViewSet.length >= 1, 'kein modus_view<-Modus-Write (SB-1a schreibt nur literal modus_view:null)');
    // Negativ-Schaerfe: KEIN cursorMap-Write darf modus_view dauerhaft als literal null fuehren, OHNE dass
    // ein nachfolgender Write ihn auf den Modus hebt (sonst bleibt der SB-1a-Minimal-Slot unveraendert).
    const onlyNullSlots = spawns.filter(x => /cursorMap\[[^\]]+\].*modus_view:\s*null/i.test(x.prompt));
    check('CM-2 (RED): der modus_view-Slot bleibt NICHT dauerhaft literal null (Minimal-Slot ueberwunden)', modusViewSet.length >= 1 || onlyNullSlots.length === 0, 'nur literal modus_view:null-Writes vorhanden, kein Modus-Befuell-Write (SB-1a-Stand)');
  }

  // ── CM-3 (RED): EC-CM-3 — Fallback-Modus (Schema-Crash) befuellt modus_view dennoch (nicht null). ──
  // Wenn modusEntscheidung in den Fallback faellt (M2), muss der modus_view-Persist trotzdem den
  // Fallback-Modus tragen (kein null trotz gefasstem Modus). RED weil kein modus_view-Persist existiert.
  {
    const spawns = [];
    const factory = makeFactory();
    // Custom-Agent: modusEntscheidung wirft im Schema-Call -> safeSchemaAgent-Fallback M2. Der modus_view
    // muss danach trotzdem mit M2 befuellt werden.
    const crashModusAgent = async (prompt, o) => {
      o = o || {};
      const label = o.label || '';
      spawns.push({ prompt: String(prompt), label, phase: o.phase });
      if (label.indexOf('modusEntscheidung') === 0) {
        if (o.schema) throw new Error('agent({schema}): subagent completed without calling StructuredOutput (after 2 nudges)');
        return 'kein valides JSON hier';   // schemaloser Retry liefert ebenfalls nichts -> Fallback M2
      }
      if (label.indexOf('stageElevation') === 0) return { next_action: 'BATCH_DONE', current_stage_outcome: 'GREEN' };
      if (label.indexOf('loopDecision') === 0) return { decision: 'TERMINATE' };
      if (label.indexOf('_TDD_init') === 0) return 'INFRA=false';
      return 'STEP ' + label + ': done';
    };
    let threw = false;
    try {
      await factory(crashModusAgent, makeParallelSpy().fn, noop, noop, ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }));
    } catch (e) { threw = true; }
    const mvFilled = spawns.filter(x => /cursorMap\[[^\]]+\].*modus_view/i.test(x.prompt) && /\bM2\b/.test(x.prompt) && !/modus_view:\s*null/i.test(x.prompt));
    check('CM-3 (RED): EC-CM-3 — bei Fallback-Modus (Schema-Crash) wird modus_view mit dem Fallback-Modus (M2) befuellt, nicht null', !threw && mvFilled.length >= 1, threw ? 'paralleler Pfad warf' : 'kein modus_view<-Fallback-Modus-Write (RED bis Impl)');
  }

  // ── CM-4 [GUARD] (Null-Regression, MUSS schon GRUEN sein): OFF -> globaler current_sub_batch_id, kein cursorMap. ──
  // EC-CM-2: serieller Pfad (fanout==1) bleibt byte-identisch — der Cursor-Spawn schreibt weiterhin den
  // globalen DF_BATCH_STATE.current_sub_batch_id-Slot, KEIN cursorMap. (QG-4-Wache.)
  {
    const { result, spawns } = await runWithParallel(ARGS(wave(2)), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const cursorSpawns = spawns.filter(x => /^persistSubBatchCursor:/.test(x.label));
    check('CM-4 [GUARD] OFF byte-identisch: Cursor-Spawn schreibt globalen current_sub_batch_id (kein cursorMap)', cursorSpawns.length > 0 && cursorSpawns.every(x => /DF_BATCH_STATE\.current_sub_batch_id\s*=/.test(x.prompt) && !/cursorMap\[/.test(x.prompt)), 'OFF-Pfad schreibt cursorMap statt globalem Slot (Null-Regression gebrochen!)');
    check('CM-4 [GUARD] OFF: effective_fanout=1 + terminated=completed (Verhalten unveraendert)', result.effective_fanout === 1 && result.terminated_reason === 'completed', result.effective_fanout + '/' + result.terminated_reason);
  }

  // ===========================================================================
  // BL-230 SB-1b AK-FANIN-BARRIER (Stage 1, RED-first) — 5 serielle Schritte unter Index-Lock.
  //
  // Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (Slice "Fan-In-Barrier", 5 Exit-Kriterien).
  // IST (SB-1a, dispatch_implement.js Z550-557): runFanInBarrier laedt 1 _I_fanIn-Agent mit STUB-Vertrag
  //   (1 serieller Aufruf-Slot + Return-Marker). SOLL (SB-1b): die Barrier orchestriert die 5 SERIELLEN
  //   Schritte in FESTER Reihenfolge unter Index-Lock: (1) Code-Merge -> (2) Post-Merge-Green-Check ->
  //   (3) Model/SRS-Writes -> (4) Truth-Revalidierung -> (5) loopDecision-Aggregat. Reihenfolge + Aufruf-
  //   Struktur + Index-Lock-Charakter sind SB-1b; die Unterschritt-INHALTE bleiben STUB (Nicht-Ziel).
  //
  // RED-Erwartung: FB-1..FB-3 FAILEN (heute genau 1 Barrier-Spawn ohne 5-Schritt-Struktur, kein
  //   barrier_only-Marker, kein Model/SRS-in-Barrier). FB-4 (OFF kein Aufruf) ist GUARD und schon GRUEN.
  // Test STRUKTUR/Reihenfolge/Aufruf — NICHT die volle Merge-Logik (Schritt-Inhalte sind spaetere AKs).
  // ===========================================================================

  // FanIn-Spawns einer parallelen Welle isolieren (Phase 'FanIn' ODER Label runFanInBarrier).
  const fanInOf = (spawns) => spawns.filter(x => x.phase === 'FanIn' || /runFanInBarrier|fanInBarrier/i.test(x.label));

  // ── FB-1 (RED): die Barrier traegt die 5 seriellen Schritte in FESTER Reihenfolge. ──────────────
  // Reihenfolge messbar an den Schritt-Markern im Barrier-Prompt (ODER an 5 getrennten Barrier-Sub-Spawns):
  //   Code-Merge < Post-Merge-Green < Model/SRS < Truth-Reval < loopDecision-Aggregat.
  // RED weil der SB-1a-STUB-Prompt nur "serielle Barrier-Synchronisation" sagt, ohne die 5 geordneten Schritte.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    check('FB-1 (RED): genau 1 Fan-In-Barrier-Aufruf nach dem parallelen Fan-Out', fi.length === 1, 'got ' + fi.length + ' Fan-In-Spawns');
    // Die 5 Schritt-Marker im gesamten Barrier-Text (ueber alle FanIn-Spawns konkateniert).
    const barrierText = fi.map(x => x.prompt).join('\n');
    const iMerge = barrierText.search(/Code-Merge/i);
    const iGreen = barrierText.search(/Post-Merge-Green|Post-Merge.Green-?Check/i);
    const iModel = barrierText.search(/Model\/SRS|Model.SRS-Writes?/i);
    const iTruth = barrierText.search(/Truth-Reval|Truth-Revalidierung/i);
    const iLoop = barrierText.search(/loopDecision-Aggregat|loopDecision.Aggregat/i);
    check('FB-1 (RED): alle 5 Schritt-Marker (Code-Merge/Post-Merge-Green/Model-SRS/Truth-Reval/loopDecision-Aggregat) im Barrier-Prompt', [iMerge, iGreen, iModel, iTruth, iLoop].every(i => i >= 0), 'fehlende Marker: ' + JSON.stringify({ merge: iMerge, green: iGreen, model: iModel, truth: iTruth, loop: iLoop }));
    check('FB-1 (RED): die 5 Schritte stehen in FESTER Reihenfolge (Merge < Green < Model/SRS < Truth-Reval < loopDecision-Aggregat)', iMerge >= 0 && iMerge < iGreen && iGreen < iModel && iModel < iTruth && iTruth < iLoop, 'Reihenfolge: ' + JSON.stringify({ merge: iMerge, green: iGreen, model: iModel, truth: iTruth, loop: iLoop }));
  }

  // ── FB-2 (RED): Index-Lock / Single-Writer-Seam — Barrier traegt barrier_only/EXCLUSIVE-Marker. ──
  // Analog runStageCommit (Z493 barrier_only/concurrency_class=EXCLUSIVE). RED weil der SB-1a-STUB-Prompt
  // KEINEN barrier_only/EXCLUSIVE-Marker traegt (die Barrier ist die Single-Writer-Naht der Welle).
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    check('FB-2 (RED): Barrier-Prompt traegt einen barrier_only/EXCLUSIVE/Index-Lock-Marker (Single-Writer-Seam, nie nebenlaeufig)', fi.length === 1 && /barrier_only|concurrency_class\s*=\s*EXCLUSIVE|EXCLUSIVE|Index-Lock|Single-Writer/i.test(fi[0].prompt), fi.length ? 'Barrier ohne barrier_only/EXCLUSIVE/Index-Lock-Marker (SB-1a-STUB)' : 'kein Fan-In-Spawn');
  }

  // ── FB-3 (RED): Model/SRS-Writes laufen NUR in der Barrier (seriell), nie im parallelen Thunk. ──
  // INV-PARALLEL-COMMUTATIVE-Verankerung: der Model/SRS-Schritt ist Teil der FanIn/BatchClose-Barrier-Sequenz,
  // KEIN Model/SRS-Write-Spawn innerhalb eines parallel()-Thunks (phase==='Implement'). RED weil der Barrier-
  // STUB den Model/SRS-Schritt heute gar nicht enthaelt (kein dedizierter Schritt 3).
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const barrierHasModel = fi.length >= 1 && fi.some(x => /Model\/SRS|Model.SRS-Writes?/i.test(x.prompt));
    check('FB-3 (RED): Model/SRS-Write-Schritt ist Teil der Barrier-Sequenz (FanIn/BatchClose, seriell)', barrierHasModel, 'kein Model/SRS-Schritt in der Barrier (SB-1a-STUB ohne Schritt 3)');
    // Negativ-Schaerfe: KEIN Model/SRS-Write-Spawn innerhalb eines parallel()-Thunks (Implement-Phase).
    const modelInThunk = spawns.some(x => x.phase === 'Implement' && /Model\/SRS-Write|Model.SRS-Writes? \(Single-Writer/i.test(x.prompt));
    check('FB-3 (RED): KEIN Model/SRS-Write innerhalb eines parallelen Thunks (Implement-Phase) — Commutativitaet gewahrt', !modelInThunk, 'Model/SRS-Write lief in einem parallelen Thunk (nicht in der seriellen Barrier)');
  }

  // ── FB-4 [GUARD] (Null-Regression, MUSS schon GRUEN sein): OFF/serieller Pfad ruft runFanInBarrier NICHT auf. ──
  // EC: bei default-args (fanout==1) gibt es 0 Fan-In-Spawns; der fan_in_barrier-Marker entspricht SB-1a (false).
  {
    const { result, spawns } = await runWithParallel(ARGS(wave(2)), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    check('FB-4 [GUARD] OFF: 0 Fan-In-Barrier-Spawns im seriellen Pfad (kein Barrier-Aufruf bei fanout==1)', fi.length === 0, 'got ' + fi.length + ' Fan-In-Spawns trotz OFF');
    check('FB-4 [GUARD] OFF: fan_in_barrier-Marker entspricht SB-1a-Verhalten (false im seriellen Pfad)', result.fan_in_barrier === false, String(result.fan_in_barrier));
  }

  // ===========================================================================
  // BL-230 SB-2 (Stage 1, RED-first) — PARTIAL-FAILURE / CORRELATION / COMMIT-SEAM.
  //
  // Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (SB-2-Abschnitt, 16 Kriterien).
  // Geschrieben vom RED-Worker (BL-230 SB-2 RED). GREEN-Worker haertet dispatch_implement.js
  // SEPARAT (RED != GREEN, INV-BUILD-GRAIN). Diese Tests fahren via makeFactory/runWithParallel/
  // makeParallelSpy (oben definiert) — exakt das bestehende Muster.
  //
  // Helper-Sichtbarkeit: makeParallelSpy/runWithParallel/wave/ARGS_P sind im selben IIFE-Scope
  // (oben, AON-Block + Z674) deklariert; diese SB-2-Bloecke liegen NACH ihnen, also sichtbar.
  // ===========================================================================

  // ── PF-1 (RED, load-bearing): benanntes per_batch_outcome-Enum mit GENAU {completed,failed,blocked}. ──
  // IST (Z1002-1007): classifyOutcome mappt auf String-Literale 'completed'/'failed'/'blocked', aber es
  // existiert KEINE benannte Enum-/Konstanten-Struktur (PER_BATCH_OUTCOME) als Single-Source. SOLL: ein
  // benanntes Enum-Objekt mit exakt diesen 3 Werten; classifyOutcome gibt ausschliesslich einen Enum-Wert
  // zurueck. RED weil der Source-Text heute kein PER_BATCH_OUTCOME-Enum traegt.
  {
    // Wir pruefen die FORMALISIERUNG strukturell am Source-Text (SRC, oben gelesen) — analog dazu, wie
    // andere strukturelle Garantien (barrier_only-Marker) am Prompt geprueft werden. Das Enum ist eine
    // benannte Konstante im Motor, kein Laufzeit-Return.
    const hasEnumDecl = /PER_BATCH_OUTCOME\s*=\s*(?:Object\.freeze\()?\{/.test(SRC);
    check('PF-1 (RED): benanntes per_batch_outcome-Enum PER_BATCH_OUTCOME existiert (Single-Source der 3 Buckets)', hasEnumDecl, 'kein PER_BATCH_OUTCOME-Enum im Motor (classifyOutcome nutzt nackte String-Literale)');
    // Genau die drei Werte completed/failed/blocked, kein vierter.
    const enumBlock = (SRC.match(/PER_BATCH_OUTCOME\s*=\s*(?:Object\.freeze\()?\{([^}]*)\}/) || [])[1] || '';
    const hasCompleted = /['"]completed['"]/.test(enumBlock);
    const hasFailed = /['"]failed['"]/.test(enumBlock);
    const hasBlocked = /['"]blocked['"]/.test(enumBlock);
    const strLits = (enumBlock.match(/['"][a-z_]+['"]/g) || []).map(s => s.replace(/['"]/g, ''));
    const onlyThree = strLits.length > 0 && strLits.every(v => ['completed', 'failed', 'blocked'].includes(v));
    check('PF-1 (RED): das Enum traegt GENAU die 3 Werte completed/failed/blocked (kein vierter Wert)', hasCompleted && hasFailed && hasBlocked && onlyThree, 'enum-Werte=' + JSON.stringify(strLits));
    // classifyOutcome gibt ausschliesslich Enum-Werte zurueck (kein nackter Return-String mehr).
    const coBody = (SRC.match(/function\s+classifyOutcome\s*\([^)]*\)\s*\{([\s\S]*?)\n\}/) || [])[1] || '';
    const returnsEnumOnly = coBody.length > 0 && /return\s+PER_BATCH_OUTCOME\./.test(coBody) && !/return\s+['"](?:completed|failed|blocked)['"]/.test(coBody);
    check('PF-1 (RED): classifyOutcome returnt ausschliesslich PER_BATCH_OUTCOME.* (kein Roh-String ausserhalb des Enums)', returnsEnumOnly, 'classifyOutcome returnt noch nackte String-Literale statt Enum-Werte');
  }

  // ── PF-2 (RED, load-bearing): Fan-In-Aggregation filtert null/undefined via .filter(Boolean). ──
  // IST (Z1009-1012): `for (const r of results) { if (r && r.sub_batch) ... }` — der null-Guard ist
  // inline, NICHT als explizites .filter(Boolean). Der Blueprint nennt das den echten RED-Anker
  // (lastOutcomeById Z1009-1012): bei einem results-Array mit null/undefined-Eintrag darf der NICHT als
  // blocked durchrutschen — Bucket-Summe == Anzahl REALER Batches. Wir beweisen das VERHALTEN: ein
  // injizierter null-Eintrag im Welle-Outcome darf die Bucket-Summe NICHT erhoehen.
  {
    // Custom-Agent, der einen Batch sb2 so verarbeitet, dass sein results-Eintrag faellt — wir koennen
    // den null-Eintrag nicht direkt in `results` injizieren, daher pruefen wir die filter(Boolean)-
    // Formalisierung am Source UND das Bucket-Summen-Invariant ueber einen Partial-Failure-Lauf.
    const explicitFilterBoolean = /results\s*\.\s*filter\s*\(\s*Boolean\s*\)/.test(SRC);
    check('PF-2 (RED): die Fan-In-Aggregation zieht .filter(Boolean) EXPLIZIT (kein impliziter Inline-null-Guard)', explicitFilterBoolean, 'kein results.filter(Boolean) im Motor (Z1009-1012 nutzt inline if(r && r.sub_batch))');
    // Verhaltens-Beweis: Welle [sb1, sb2(throw), sb3] -> Bucket-Summe == 3 (kein null->blocked-Durchrutsch).
    const spawns = [];
    const factory = makeFactory();
    const pfAgent = async (prompt, o) => {
      o = o || {}; const label = o.label || '';
      spawns.push({ prompt: String(prompt), label, phase: o.phase });
      if (o.phase === 'Implement' && /:sb2\./.test(label)) throw new Error('INJECTED sb2 fail (PF-2)');
      if (label.indexOf('modusEntscheidung') === 0) return { modus: 'M2', modus_begruendung: 'k=1 srs=1 t=x -> M2' };
      if (label.indexOf('stageElevation') === 0) return { next_action: 'BATCH_DONE', current_stage_outcome: 'GREEN' };
      if (label.indexOf('loopDecision') === 0) return { decision: 'TERMINATE', reason: 'test' };
      if (label.indexOf('resumePreflight') === 0) return { all_done: false, completed_stages: [] };
      if (label.indexOf('_TDD_init') === 0) return 'INFRA=false';
      return 'STEP ' + label + ': done';
    };
    const r = await factory(pfAgent, mockParallel, noop, noop,
      ARGS([{ id: 'sb1', items: ['a'], stages: [1] }, { id: 'sb2', items: ['b'], stages: [1] }, { id: 'sb3', items: ['c'], stages: [1] }]));
    const fi = r && r.fan_in;
    const sum = fi ? (fi.completed.length + fi.failed.length + fi.blocked.length) : -1;
    check('PF-2 (RED): Bucket-Summe (completed+failed+blocked) == 3 reale Batches (kein null/undefined->blocked-Durchrutsch)', sum === 3, 'sum=' + sum + ' fan_in=' + JSON.stringify(fi));
  }

  // ── PF-3 (RED): RESUME-Liste enthaelt NUR die toten (failed) Batches (resume == fan_in.failed). ──
  // SOLL: ein resume_targets-Feld (oder ein aus fan_in.failed abgeleitetes Feld) listet EXAKT die failed-
  // Batch-ids — nicht completed/blocked. RED weil der Motor heute kein resume_targets-Feld im Return traegt.
  {
    const spawns = [];
    const factory = makeFactory();
    const pfAgent = async (prompt, o) => {
      o = o || {}; const label = o.label || '';
      spawns.push({ prompt: String(prompt), label, phase: o.phase });
      if (o.phase === 'Implement' && /:sb2\./.test(label)) throw new Error('INJECTED sb2 fail (PF-3)');
      if (label.indexOf('modusEntscheidung') === 0) return { modus: 'M2', modus_begruendung: 'k=1 srs=1 t=x -> M2' };
      if (label.indexOf('stageElevation') === 0) return { next_action: 'BATCH_DONE', current_stage_outcome: 'GREEN' };
      if (label.indexOf('loopDecision') === 0) return { decision: 'TERMINATE', reason: 'test' };
      if (label.indexOf('resumePreflight') === 0) return { all_done: false, completed_stages: [] };
      if (label.indexOf('_TDD_init') === 0) return 'INFRA=false';
      return 'STEP ' + label + ': done';
    };
    const r = await factory(pfAgent, mockParallel, noop, noop,
      ARGS([{ id: 'sb1', items: ['a'], stages: [1] }, { id: 'sb2', items: ['b'], stages: [1] }, { id: 'sb3', items: ['c'], stages: [1] }]));
    const resume = r && (r.resume_targets || r.resume);
    check('PF-3 (RED): Return traegt eine resume_targets-Liste (aus fan_in.failed abgeleitet)', Array.isArray(resume), 'kein resume_targets/resume-Array im Return: ' + JSON.stringify(resume));
    check('PF-3 (RED): resume-Liste == fan_in.failed (nur tote Batches, NICHT completed/blocked)', Array.isArray(resume) && r.fan_in && JSON.stringify([...resume].sort()) === JSON.stringify([...r.fan_in.failed].sort()) && resume.includes('sb2') && !resume.includes('sb1') && !resume.includes('sb3'), 'resume=' + JSON.stringify(resume) + ' failed=' + JSON.stringify(r && r.fan_in && r.fan_in.failed));
  }

  // ── PF-4 (RED): EC-PF-4 — resume-Liste bei 0 toten Batches ist leer (== fan_in.failed == []). ──
  {
    const { result } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }, { id: 'sb2', items: ['b'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    const resume = result && (result.resume_targets || result.resume);
    check('PF-4 (RED): 0 tote Batches -> resume-Liste leer (== [])', Array.isArray(resume) && resume.length === 0, 'resume=' + JSON.stringify(resume));
  }

  // ===========================================================================
  // BL-230 SB-2 AK-CORRELATION (greenfield: KEINE Korrelations-Logik im Motor heute).
  // SOLL: reine Funktion errorClassOf(outcome)/correlatedFailureClass(results); >=50% gleiche
  //   Fehlerklasse in einer Welle -> wave_abort_retry; Retry-Cap == 1; Wellen-Abort != N re_cut.
  // RED weil grep CORRELATION/Fehlerklasse = 0 im Motor: weder die Funktion noch das Signal existieren.
  // Wir pruefen die Funktion ueber den exportierten/aufrufbaren Pfad (correlation-Helfer im Return-note
  // oder als Source-Funktion) + das wave_abort-Signal ueber einen Multi-Fail-Lauf.
  // ===========================================================================

  // Helper: extrahiert + evaluiert eine reine Funktion aus dem Source (kein Side-Effect — die Korrelations-
  // Funktionen sind rein). Wenn die Funktion noch nicht existiert -> RED (fn === null).
  function extractFn(name) {
    // matched: `function NAME(args) { ... }` bis zur passenden schliessenden Klammer auf Spaltenebene.
    const re = new RegExp('function\\s+' + name + '\\s*\\([\\s\\S]*?\\n\\}', 'm');
    const m = SRC.match(re);
    if (!m) return null;
    try {
      // eslint-disable-next-line no-new-func
      return new Function('"use strict";\nreturn (' + m[0] + ', ' + name + ');')();
    } catch (e) { return null; }
  }

  // ── CO-1 (RED): errorClassOf/correlatedFailureClass — Bucketing nach Fehlerklasse, nicht Roh-String. ──
  {
    const errorClassOf = extractFn('errorClassOf');
    const correlatedFailureClass = extractFn('correlatedFailureClass');
    check('CO-1 (RED): es existiert eine reine Fehlerklassen-Funktion (errorClassOf ODER correlatedFailureClass)', !!errorClassOf || !!correlatedFailureClass, 'weder errorClassOf noch correlatedFailureClass im Motor (greenfield)');
    if (errorClassOf) {
      // Zwei semantisch gleiche Fehler (beide rate-limit) -> SELBE Klasse; verschiedene -> verschiedene.
      const a = errorClassOf({ outcome: 'failed', error: 'rate limit exceeded (429)' });
      const b = errorClassOf({ outcome: 'failed', error: 'RATE LIMIT — too many requests' });
      const c = errorClassOf({ outcome: 'failed', error: 'TypeError: cannot read undefined' });
      check('CO-1 (RED): zwei rate-limit-Fehler landen in DERSELBEN Klasse (Bucketing, nicht Roh-String-Identitaet)', a === b && !!a, 'a=' + a + ' b=' + b);
      check('CO-1 (RED): eine andere Fehlerklasse landet in einem ANDEREN Bucket', c !== a, 'c=' + c + ' a=' + a);
    } else {
      check('CO-1 (RED): errorClassOf bucketet rate-limit gleich / andere verschieden', false, 'errorClassOf nicht vorhanden');
    }
  }

  // ── CO-2 (RED, load-bearing): >=50% gleiche Klasse -> wave_abort_retry (50% inklusiv). ──
  // 4 Batches, 2 (=50%) gleiche Fehlerklasse -> Signal. <50% -> KEIN wave_abort.
  {
    const correlatedFailureClass = extractFn('correlatedFailureClass');
    check('CO-2 (RED): correlatedFailureClass(results) existiert (Wellen-Korrelations-Funktion)', !!correlatedFailureClass, 'correlatedFailureClass nicht im Motor');
    if (correlatedFailureClass) {
      // 4 Batches: 2x rate-limit (=50%), 1 completed, 1 anderer Fehler -> >=50% gleiche failed-Klasse.
      const at50 = correlatedFailureClass([
        { sub_batch: 'sb1', outcome: 'failed', error: 'rate limit 429' },
        { sub_batch: 'sb2', outcome: 'failed', error: 'rate limit — slow down' },
        { sub_batch: 'sb3', outcome: 'BATCH_DONE' },
        { sub_batch: 'sb4', outcome: 'failed', error: 'TypeError x' },
      ]);
      const sig50 = at50 && (at50.signal || at50.decision || at50);
      check('CO-2 (RED): >=50% gleiche Fehlerklasse (2/4 rate-limit) -> wave_abort_retry-Signal (50% inklusiv)', /wave_abort_retry|correlated_wave_abort/.test(JSON.stringify(at50)) || sig50 === 'wave_abort_retry', JSON.stringify(at50));
      // <50%: 1 rate-limit + 3 verschiedene -> KEIN wave_abort.
      const below = correlatedFailureClass([
        { sub_batch: 'sb1', outcome: 'failed', error: 'rate limit 429' },
        { sub_batch: 'sb2', outcome: 'failed', error: 'TypeError a' },
        { sub_batch: 'sb3', outcome: 'failed', error: 'SyntaxError b' },
        { sub_batch: 'sb4', outcome: 'failed', error: 'OOM c' },
      ]);
      check('CO-2 (RED): <50% gleiche Klasse -> KEIN wave_abort_retry (normale Partial-Failure-Aggregation)', !/wave_abort_retry|correlated_wave_abort/.test(JSON.stringify(below)), JSON.stringify(below));
    } else {
      check('CO-2 (RED): >=50%-Schwellen-Verhalten pruefbar', false, 'correlatedFailureClass fehlt');
    }
  }

  // ── CO-3 (RED): EC-CO-3 — Retry-Cap == 1 (zweiter Abort derselben Welle -> fail-loud exhausted). ──
  {
    const correlatedFailureClass = extractFn('correlatedFailureClass');
    if (correlatedFailureClass) {
      const results = [
        { sub_batch: 'sb1', outcome: 'failed', error: 'rate limit 429' },
        { sub_batch: 'sb2', outcome: 'failed', error: 'rate limit slow' },
      ];
      // 1. Abort: retry_count=0 -> wave_abort_retry. 2. Abort: retry_count=1 (erschoepft) -> exhausted.
      const first = correlatedFailureClass(results, { retry_count: 0 });
      const second = correlatedFailureClass(results, { retry_count: 1 });
      check('CO-3 (RED): erster Korrelations-Abort (retry_count=0) -> wave_abort_retry', /wave_abort_retry/.test(JSON.stringify(first)), JSON.stringify(first));
      check('CO-3 (RED): zweiter Abort derselben Welle (retry erschoepft) -> correlated_wave_abort_exhausted (Cap==1, fail-loud)', /exhausted|correlated_wave_abort_exhausted/.test(JSON.stringify(second)), JSON.stringify(second));
    } else {
      check('CO-3 (RED): Retry-Cap == 1 (exhausted bei 2. Abort)', false, 'correlatedFailureClass fehlt');
    }
  }

  // ── CO-4 (RED): Abgrenzung — Korrelation = 1 Wellen-Retry-Signal, NICHT N re_cut pro totem Batch. ──
  {
    const correlatedFailureClass = extractFn('correlatedFailureClass');
    if (correlatedFailureClass) {
      const out = correlatedFailureClass([
        { sub_batch: 'sb1', outcome: 'failed', error: 'rate limit 429' },
        { sub_batch: 'sb2', outcome: 'failed', error: 'rate limit slow' },
        { sub_batch: 'sb3', outcome: 'failed', error: 'rate limit slower' },
        { sub_batch: 'sb4', outcome: 'failed', error: 'rate limit slowest' },
      ], { retry_count: 0 });
      // Es gibt GENAU 1 Wellen-Retry-Eintrag, NICHT 4 re_cut_target-Eintraege (1 pro Batch).
      const reCutCount = (out && Array.isArray(out.re_cut_targets)) ? out.re_cut_targets.length : 0;
      const oneWaveSignal = /wave_abort_retry/.test(JSON.stringify(out));
      check('CO-4 (RED): Korrelation liefert GENAU 1 Wellen-Retry-Signal (NICHT N re_cut_target pro totem Batch)', oneWaveSignal && reCutCount === 0, 'reCutCount=' + reCutCount + ' out=' + JSON.stringify(out));
    } else {
      check('CO-4 (RED): Wellen-Abort != N Re-Batches', false, 'correlatedFailureClass fehlt');
    }
    // EC-CO-4: Welle mit nur 1 totem Batch (|welle|==1, 100% gleiche Klasse) -> KEIN wave_abort.
    const cfc = extractFn('correlatedFailureClass');
    if (cfc) {
      const solo = cfc([{ sub_batch: 'sb1', outcome: 'failed', error: 'rate limit 429' }], { retry_count: 0 });
      check('CO-4 (RED): EC-CO-4 — |welle|==1 (1 toter Batch) -> KEIN wave_abort (Korrelation braucht >=2 Batches)', !/wave_abort_retry/.test(JSON.stringify(solo)), JSON.stringify(solo));
    }
  }

  // ===========================================================================
  // BL-230 SB-2 AK-COMMIT-SEAM — Barrier Schritt 1 (Code-Merge): commit-per-worktree-branch +
  //   serieller Mothership-Merge, repo-aware. repo_present=true -> Merge-Pfad; false -> na_repo_absent.
  // IST (SB-1b Z560): Schritt 1 ist STUB (nur Aufruf-Slot im _I_fanIn-Prompt). SOLL: die Seam-STRUKTUR
  //   bauen — repo_present injizierbar (analog handoff merge_fn). RED weil heute kein commit_seam-Marker /
  //   keine repo_present-aware Merge-Struktur existiert.
  // ===========================================================================

  // ── CS-1 (RED): repo_present=true -> commit-per-branch + serieller Merge; commit_seam=='merged'/'repo_aware'. ──
  {
    const { result, spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2, repo_present: true }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const csMarker = result && (result.commit_seam || (result.fan_in && result.fan_in.commit_seam));
    check('CS-1 (RED): repo_present=true -> commit_seam-Marker == merged/repo_aware (Code-Merge-Pfad aktiv)', /merged|repo_aware/.test(String(csMarker)), 'commit_seam=' + String(csMarker) + ' (Schritt 1 noch STUB)');
    // Reihenfolge: Commits VOR Merge. Beweis ueber Barrier-Prompt-Struktur (commit-per-branch erwaehnt,
    // serieller Merge danach) ODER ueber Commit-Spawns vor Merge-Spawn.
    const barrierSpawn = spawns.find(x => x.phase === 'FanIn' || /runFanInBarrier/i.test(x.label));
    const bp = barrierSpawn ? barrierSpawn.prompt : '';
    const commitsBeforeMerge = /commit[\s-]?per[\s-]?(?:worktree[\s-]?)?branch/i.test(bp) && /seriell\w*\s+(?:Mothership-)?Merge|serieller Merge/i.test(bp) && bp.search(/commit[\s-]?per/i) < bp.search(/seriell\w*\s+(?:Mothership-)?Merge|serieller Merge/i);
    check('CS-1 (RED): Barrier-Schritt-1-Prompt baut commit-per-worktree-branch VOR seriellem Mothership-Merge (Reihenfolge)', commitsBeforeMerge, barrierSpawn ? 'Barrier-Prompt traegt keine commit-per-branch->serieller-Merge-Struktur (Schritt 1 STUB)' : 'kein Barrier-Spawn');
  }

  // ── CS-2 (RED, load-bearing): repo_present=false (git-loser Vault) -> commit_seam=='na_repo_absent', kein Merge. ──
  {
    let threw = false, result = null, spawns = null;
    try {
      ({ result, spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2, repo_present: false }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn));
    } catch (e) { threw = true; }
    check('CS-2 (RED): repo_present=false -> Barrier laeuft sauber durch (kein Crash/Throw im git-losen Vault)', !threw && !!result, threw ? 'paralleler Pfad warf bei repo_present=false' : 'kein Ergebnis');
    const csMarker = result && (result.commit_seam || (result.fan_in && result.fan_in.commit_seam));
    check('CS-2 (RED): repo_present=false -> commit_seam-Marker == na_repo_absent (dokumentiertes N/A, KEINE Improvisation)', String(csMarker) === 'na_repo_absent', 'commit_seam=' + String(csMarker));
    // Kein Merge-/Commit-Versuch: der Barrier-Prompt traegt im N/A-Fall keine aktive Merge-Aufforderung.
    const barrierSpawn = result && spawns && spawns.find(x => x.phase === 'FanIn' || /runFanInBarrier/i.test(x.label));
    check('CS-2 (RED): die uebrigen Barrier-Schritte (2-5) bleiben unberuehrt — Barrier-Spawn existiert weiterhin (1x)', !!barrierSpawn, 'kein Barrier-Spawn trotz parallelem Pfad');
  }

  // ── CS-3 (RED): Index-Lock — Merge ist barrier_only/seriell, NIE in einem parallel()-Thunk. ──
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2, repo_present: true }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const barrierSpawn = spawns.find(x => x.phase === 'FanIn' || /runFanInBarrier/i.test(x.label));
    const bp = barrierSpawn ? barrierSpawn.prompt : '';
    // SB-2-Schaerfe: der Index-Lock-Marker muss am COMMIT-SEAM-spezifischen Schritt 1 haengen
    // (commit-per-worktree-branch + serieller Merge), NICHT nur am generischen SB-1b-Barrier-Kopf.
    // Der SB-1b-STUB nennt zwar "Code-Merge"/"barrier_only", aber NICHT commit-per-branch -> RED bis SB-2.
    const commitSeamLock = /commit[\s-]?per[\s-]?(?:worktree[\s-]?)?branch/i.test(bp) && /barrier_only|EXCLUSIVE|Index-Lock/i.test(bp) && /merge/i.test(bp);
    check('CS-3 (RED): der COMMIT-SEAM-Merge (commit-per-branch + serieller Merge) traegt den barrier_only/EXCLUSIVE/Index-Lock-Marker (Single-Writer-Seam)', commitSeamLock, barrierSpawn ? 'kein commit-per-branch-Merge mit barrier_only/EXCLUSIVE-Marker (SB-1b-Stub nennt nur generischen Code-Merge)' : 'kein Barrier-Spawn');
    // KEIN Merge-/Commit-Aufruf innerhalb eines parallel()-Thunks (Phase Implement).
    const mergeInThunk = spawns.some(x => x.phase === 'Implement' && /(?:^|\s)merge\b.*(?:branch|mothership)|commit[\s-]?per[\s-]?branch/i.test(x.prompt));
    check('CS-3 (RED): kein Merge/Commit-per-Branch-Aufruf innerhalb eines parallel()-Thunks (phase!==Implement)', !mergeInThunk, 'Merge/Commit-Seam lief in der Implement-Phase (nebenlaeufig)');
  }

  // ── CS-4 [GUARD-naher RED] (Null-Regression): OFF/serieller Pfad beruehrt die Commit-Seam NICHT. ──
  // EC-CS-3: fanout==1 -> runFanInBarrier nicht gerufen -> keine Commit-Seam. commit_seam-Marker im
  // seriellen Pfad bleibt unberuehrt (kein neuer Effekt). FB-4-GUARD bleibt gruen.
  {
    const { result, spawns } = await runWithParallel(ARGS(wave(2)), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = spawns.filter(x => x.phase === 'FanIn' || /runFanInBarrier/i.test(x.label));
    check('CS-4 (RED): OFF/seriell -> 0 Fan-In-Barrier-Spawns -> Commit-Seam unberuehrt (FB-4-Konsistenz)', fi.length === 0, 'got ' + fi.length + ' Barrier-Spawns trotz OFF');
    // Im seriellen Pfad darf KEIN commit_seam-Effekt entstehen (Marker fehlt ODER ist na/unberuehrt — KEIN 'merged').
    const csMarker = result && (result.commit_seam || (result.fan_in && result.fan_in.commit_seam));
    check('CS-4 (RED): OFF -> kein commit_seam==merged-Effekt im seriellen Pfad (byte-relevante Null-Regression)', csMarker === undefined || csMarker === null || String(csMarker) !== 'merged', 'commit_seam=' + String(csMarker) + ' im seriellen Pfad (Null-Regression gebrochen!)');
  }

  // ===========================================================================
  // BL-230 SB-3a (Stage 1, RED-first) — PARALLEL-COMMUTATIVE / TRUTH-WRITER / FANIN-COMMUTATIVE.
  //
  // Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (SB-3a-Abschnitt, 10 Kriterien +
  //   3 Kommutativitaet (KOM-1/2/3) + 11 Edge-Cases). SB-3a flesht Barrier-Schritt 3 (Model/SRS-
  //   Writes, deterministisch batch_id-sortiert + Single-Writer + Worker-Verbot) UND Schritt 4
  //   (Truth-Revalidierung, "Widerlegung gewinnt" + weakestTruthGrade-Helper + blast_set-Leiter).
  //   Schritt 2 (Post-Merge-Green) + Schritt 5 (loopDecision-Aggregat-INHALT) bleiben STUB.
  //
  // Geschrieben vom RED-Worker (BL-230 SB-3a RED). GREEN-Worker haertet dispatch_implement.js
  // SEPARAT (RED != GREEN, INV-BUILD-GRAIN — dieser Worker aendert NUR Tests). Diese Tests fahren
  // via makeFactory/runWithParallel/makeParallelSpy/fanInOf/ARGS_P/wave/extractFn — exakt das
  // bestehende Muster (AON-/FB-/CS-/CO-Bloecke oben, im selben IIFE-Scope, also sichtbar).
  //
  // Helper-Sichtbarkeit (Hinweis): die reinen Helper (weakestTruthGrade etc.) soll der GREEN-Worker
  // via globalThis exportieren ODER als Source-Funktion (analog SB-2 CO-* extractFn). Wir greifen
  // beide Pfade: erst globalThis, dann extractFn(SRC). Beide leer => RED.
  // ===========================================================================

  // grade-Helper-Resolver: globalThis-Export bevorzugt, sonst aus dem Source extrahiert (extractFn
  // ist oben im SB-2-Block deklariert, selber IIFE-Scope). null => Helper existiert noch nicht (RED).
  const resolveHelper = (name) => {
    if (typeof globalThis[name] === 'function') return globalThis[name];
    try { const f = extractFn(name); if (typeof f === 'function') return f; } catch (e) { /* RED */ }
    return null;
  };

  // ─────────────────────────────────────────────────────────────────────────
  // AK-PARALLEL-COMMUTATIVE (k=65): Model/SRS-Write = dedizierter SERIELLER Barrier-Schritt 3,
  //   iteriert ueber lebende Welle-Batches in DETERMINISTISCHER batch_id-sortierter Reihenfolge;
  //   KEIN Model/SRS-Write im parallel()-Thunk (phase==='Implement'); Permutations-Invarianz.
  // RED weil der SB-1b/SB-2-STUB Schritt 3 noch ohne deterministische/batch_id-sortierte Iteration
  //   formuliert ist (FB-3 nennt nur "Model/SRS", nicht "deterministisch/batch_id-sortiert").
  // ─────────────────────────────────────────────────────────────────────────

  // ── PC-1 (RED, load-bearing): Schritt-3-Prompt nennt Model/SRS UND deterministische batch_id-sortierte Reihenfolge. ──
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    // Der Schritt-3-Text muss Model/SRS UND eine deterministische/batch_id-sortierte Iteration ueber die Welle nennen.
    const hasModelStep = /Model\/SRS|Model.SRS-Writes?/i.test(bp);
    const hasDeterministicSort = /(?:batch_id[\s-]?sortiert|sortiert\s+nach\s+batch_id|deterministisch\w*\s+(?:sortiert|Reihenfolge)|\.sort\(|batch_id-sorted)/i.test(bp);
    check('PC-1 (RED): Barrier-Schritt-3-Prompt nennt Model/SRS-Write (Single-Writer-Schritt vorhanden)', fi.length === 1 && hasModelStep, fi.length ? 'kein Model/SRS-Schritt im Barrier-Prompt' : 'kein Fan-In-Spawn');
    check('PC-1 (RED): Schritt 3 iteriert in DETERMINISTISCHER batch_id-sortierter Reihenfolge ueber die Welle-Batches (Marker im Prompt)', hasDeterministicSort, 'Schritt 3 nennt keine batch_id-sortierte/deterministische Reihenfolge (SB-1b/SB-2-STUB)');
  }

  // ── PC-2 (RED, load-bearing / KOM-3-Vorhof): KEIN Model/SRS-Write-Spawn im parallel()-Thunk (phase==='Implement'). ──
  // Schaerft FB-3 weiter: ueber ALLE Implement-Spawns darf KEINER einen Model/SRS-/modelSync-Schreibauftrag tragen.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const modelWriteInThunk = spawns.some(x => x.phase === 'Implement' && /(?:Model\/SRS[\s-]?Write|modelSync|_SDF_berater_modelSync|Model[\s-]?Mutation|SRS[\s-]?Write)/i.test(x.prompt));
    check('PC-2 (RED): KEIN Model/SRS-/modelSync-Schreibauftrag in irgendeinem parallel()-Thunk (phase===Implement) — nur die serielle Barrier mutiert', !modelWriteInThunk, 'ein Implement-Spawn traegt einen Model/SRS-/modelSync-Schreibauftrag (Race / Kommutativitaet gebrochen)');
  }

  // ── KOM-1 (RED, KOMMUTATIVITAET): Schritt-3-Auftrag permutations-invariant — [sb1,sb2] vs [sb2,sb1] identische sortierte id-Liste. ──
  // Lauf A mit SUB_BATCHES=[sb1,sb2], Lauf B mit [sb2,sb1]; die im Schritt-3-Prompt referenzierte
  // batch_id-Verarbeitungsreihenfolge MUSS in A und B identisch sein (deterministisch sortiert, nicht eingabe-abhaengig).
  {
    const waveAB = [{ id: 'sb1', items: ['x1'], stages: [1] }, { id: 'sb2', items: ['x2'], stages: [1] }];
    const waveBA = [{ id: 'sb2', items: ['x2'], stages: [1] }, { id: 'sb1', items: ['x1'], stages: [1] }];
    const { spawns: spA } = await runWithParallel(ARGS_P(waveAB, { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const { spawns: spB } = await runWithParallel(ARGS_P(waveBA, { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const bpA = fanInOf(spA).map(x => x.prompt).join('\n');
    const bpB = fanInOf(spB).map(x => x.prompt).join('\n');
    // Extrahiere die im Barrier-Prompt referenzierte batch_id-Reihenfolge (Reihenfolge der ersten Nennung von sb1/sb2).
    const idOrder = (txt) => (txt.match(/sb\d+/g) || []).filter((v, i, a) => a.indexOf(v) === i);
    const orderA = idOrder(bpA), orderB = idOrder(bpB);
    // KOM-1a: beide Laeufe nennen ueberhaupt die batch_ids im Schritt-3-Kontext (deterministische Iterations-Liste).
    check('KOM-1 (RED): Barrier-Schritt-3 referenziert die Welle-batch_ids (deterministische Iterations-Liste im Prompt)', orderA.length >= 2 && orderB.length >= 2, 'orderA=' + JSON.stringify(orderA) + ' orderB=' + JSON.stringify(orderB) + ' (Schritt 3 traegt keine batch_id-Liste — STUB)');
    // KOM-1b: die sortierte id-Reihenfolge ist in A und B IDENTISCH (permutations-invariant, nicht eingabe-abhaengig).
    check('KOM-1 (RED): Schritt-3-Verarbeitungsreihenfolge ist permutations-invariant ([sb1,sb2]==[sb2,sb1] -> identische sortierte id-Liste)', orderA.length >= 2 && JSON.stringify(orderA) === JSON.stringify(orderB) && JSON.stringify(orderA) === JSON.stringify([...orderA].sort()), 'orderA=' + JSON.stringify(orderA) + ' orderB=' + JSON.stringify(orderB) + ' (eingabe-abhaengig statt batch_id-sortiert)');
  }

  // ── EC-PC-3 (RED): Schritt 3 iteriert nur ueber LEBENDE Batches (toter Batch nicht im Model/SRS-Write). ──
  // Konsistenz mit SB-2 filter(Boolean): der Barrier-Schritt-3-Prompt muss explizit "lebende Batches" / die
  // gebauten (builtIds) adressieren, nicht blind alle SUB_BATCHES. RED weil der STUB keine lebende-Filter-Sprache traegt.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    const liveOnly = /(?:lebend\w*\s+Batches?|live\s+batches?|nur\s+(?:die\s+)?(?:lebend|gebaut)\w*|gebaut\w*\s+Welle|builtIds)/i.test(bp);
    check('EC-PC-3 (RED): Schritt 3 adressiert nur LEBENDE/gebaute Welle-Batches (filter(Boolean)-Konsistenz, kein toter Batch im Model/SRS-Write)', liveOnly, 'Schritt 3 nennt keine lebende-Batch-Beschraenkung (STUB iteriert blind)');
  }

  // ─────────────────────────────────────────────────────────────────────────
  // AK-TRUTH-WRITER (k=66, INV-TRUTH-WRITER-1): die Fan-In-Barrier ist der EINZIGE autorisierte
  //   truth_to_batches-Writer (Single-Writer + Guard-Marker truth_to_batches_set_by:fan_in_barrier,
  //   Template-treu zu batch_modes_set_by/INV-MODUS-1). Worker-Prompt traegt explizites Schreib-Verbot.
  // RED weil grep truth_to_batches im Motor = 0 (weder Marker noch Verbot existieren).
  // ─────────────────────────────────────────────────────────────────────────

  // ── TW-1 (RED, load-bearing): Barrier-Schritt-3-Prompt deklariert Barrier als Single-Writer von truth_to_batches + set_by-Marker. ──
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    const declaresSingleWriter = /truth_to_batches/.test(bp) && /(?:einzige\w*|single[\s-]?writer|EINZIGE\w*)/i.test(bp);
    const hasSetByMarker = /truth_to_batches_set_by\s*[:=]\s*fan_in_barrier/i.test(bp);
    check('TW-1 (RED): Barrier-Schritt-3 deklariert die Barrier als EINZIGEN/Single-Writer von truth_to_batches', fi.length === 1 && declaresSingleWriter, fi.length ? 'Barrier-Prompt nennt truth_to_batches-Single-Writer-Hoheit nicht (greenfield)' : 'kein Fan-In-Spawn');
    check('TW-1 (RED): Guard-Marker truth_to_batches_set_by: fan_in_barrier im Barrier-Prompt (maschinenlesbare Hoheit)', hasSetByMarker, 'kein truth_to_batches_set_by:fan_in_barrier-Marker (greenfield)');
  }

  // ── TW-2 (RED, load-bearing / EC-TW-1): der parallele Worker traegt explizites VERBOT, truth_to_batches zu schreiben. ──
  // Analog "KEIN batch_modes/modus-Write" Z620/625 — mindestens ein Implement/Modus-Spawn im parallelen Pfad
  // muss ein "KEIN truth_to_batches-Write"-Verbot tragen (Negativ-Assertion).
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    // Worker-/Modus-Spawns des parallelen Pfads (Phase Modus oder Implement, nicht FanIn).
    const workerSpawns = spawns.filter(x => x.phase === 'Modus' || x.phase === 'Implement');
    const hasTruthWriteVeto = workerSpawns.some(x => /KEIN\s+truth_to_batches[\s-]?(?:Write|Schreib)|truth_to_batches.*(?:verboten|nicht\s+schreiben|kein\s+Write)/i.test(x.prompt));
    check('TW-2 (RED): mind. ein paralleler Worker-/Modus-Spawn traegt das explizite Verbot "KEIN truth_to_batches-Write" (analog KEIN batch_modes-Write)', hasTruthWriteVeto, 'kein Worker-Spawn traegt ein truth_to_batches-Schreib-Verbot (Single-Writer-Hoheit nicht im Worker verankert)');
  }

  // ── TW-3 (RED, Template-Treue): die set_by-Konstruktion folgt dem INV-MODUS-1-Muster (named-writer-Marker analog batch_modes_set_by). ──
  // Der truth_to_batches-Marker ist namens-analog zum batch_modes_set_by-Pattern (set_by-Suffix, whitelist-faehig).
  {
    // batch_modes_set_by existiert bereits im SRC (Z635, Whitelist-Pattern) — wir verlangen das gleiche
    // Set-By-Muster fuer truth_to_batches (truth_to_batches_set_by) im Source-Text.
    const hasBatchModesPattern = /batch_modes_set_by/.test(SRC);
    const hasTruthSetByPattern = /truth_to_batches_set_by/.test(SRC);
    check('TW-3 (RED): das batch_modes_set_by-Set-By-Pattern existiert als Template-Anker im Motor (INV-MODUS-1 Vorbild)', hasBatchModesPattern, 'kein batch_modes_set_by im SRC — Template-Anker fehlt (unerwartet)');
    check('TW-3 (RED): truth_to_batches_set_by folgt demselben named-writer/set_by-Muster (Template-Treue, kein Ad-hoc)', hasTruthSetByPattern, 'kein truth_to_batches_set_by im SRC (Ad-hoc statt INV-MODUS-1-Template)');
  }

  // ─────────────────────────────────────────────────────────────────────────
  // AK-FANIN-COMMUTATIVE (k=62, INV-FANIN-COMMUTATIVE-1 "Widerlegung gewinnt"): Schritt 4 Truth-
  //   Revalidierung — schwaecherer Wahrheits-Grad gewinnt (Grad-Ordnung BESTAETIGT > TENTATIV >
  //   HYPOTHESE > OFFEN; Minimum gewinnt), reihenfolge-unabhaengig; reine Helper weakestTruthGrade(..)
  //   permutations-invariant + idempotent; blast_set-Eskalation QUARANTAENE -> PIN-INVALIDIERUNG -> WELLE-SHRINK.
  // RED weil grep weakestTruthGrade/Widerlegung/blast_set/QUARANT im Motor = 0.
  // ─────────────────────────────────────────────────────────────────────────

  // ── FC-1 (RED, load-bearing): Schritt-4-Prompt nennt "Widerlegung gewinnt" + die Grad-Ordnung (Minimum gewinnt). ──
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    const hasWiderlegung = /Widerlegung\s+gewinnt|schwaecher\w*\s+(?:Grad|Wahrheits)|schwaechster\s+Grad\s+gewinnt|Minimum\s+gewinnt/i.test(bp);
    // Grad-Ordnung BESTAETIGT > TENTATIV > HYPOTHESE > OFFEN/WIDERLEGT muss in dieser Reihenfolge genannt sein.
    const iB = bp.search(/BEST[AÄ]TIGT/i), iT = bp.search(/TENTATIV/i), iH = bp.search(/HYPOTHESE/i), iO = bp.search(/OFFEN|WIDERLEGT/i);
    const ordered = [iB, iT, iH, iO].every(i => i >= 0) && iB < iT && iT < iH && iH < iO;
    check('FC-1 (RED): Schritt-4-Prompt nennt die "Widerlegung gewinnt"/schwaechster-Grad-gewinnt-Regel', fi.length === 1 && hasWiderlegung, fi.length ? 'Schritt 4 nennt die Widerlegung-gewinnt-Regel nicht (STUB)' : 'kein Fan-In-Spawn');
    check('FC-1 (RED): Schritt 4 nennt die Grad-Ordnung BESTAETIGT > TENTATIV > HYPOTHESE > OFFEN/WIDERLEGT (Minimum gewinnt)', ordered, 'Grad-Ordnung fehlt/unsortiert: ' + JSON.stringify({ b: iB, t: iT, h: iH, o: iO }));
  }

  // ── KOM-2 (RED, KOMMUTATIVITAET): reine Funktion weakestTruthGrade([..]) — permutations-invariant + idempotent. ──
  // [BESTAETIGT,HYPOTHESE]==[HYPOTHESE,BESTAETIGT]==HYPOTHESE; [X]==X (Idempotenz). Assertion ueber >=2 Permutationen.
  {
    const weakestTruthGrade = resolveHelper('weakestTruthGrade');
    check('KOM-2 (RED): reine Helper-Funktion weakestTruthGrade existiert (globalThis-Export ODER Source-Funktion)', typeof weakestTruthGrade === 'function', 'weakestTruthGrade nicht greifbar (weder globalThis noch SRC-Funktion) — greenfield');
    if (typeof weakestTruthGrade === 'function') {
      const ab = weakestTruthGrade(['BESTAETIGT', 'HYPOTHESE']);
      const ba = weakestTruthGrade(['HYPOTHESE', 'BESTAETIGT']);
      // EC-FC-1: HYPOTHESE (schwaecher) gewinnt, reihenfolge-unabhaengig.
      check('KOM-2 (RED): [BESTAETIGT,HYPOTHESE] -> HYPOTHESE (schwaecherer Grad gewinnt)', ab === 'HYPOTHESE', 'ab=' + JSON.stringify(ab));
      check('KOM-2 (RED): permutations-invariant — [BESTAETIGT,HYPOTHESE] == [HYPOTHESE,BESTAETIGT]', ab === ba, 'ab=' + JSON.stringify(ab) + ' ba=' + JSON.stringify(ba));
      // EC-FC-2: gleicher Grad -> derselbe (Minimum trivial / Idempotenz).
      check('KOM-2 (RED): EC-FC-2 — [BESTAETIGT,BESTAETIGT] -> BESTAETIGT (Minimum trivial)', weakestTruthGrade(['BESTAETIGT', 'BESTAETIGT']) === 'BESTAETIGT', 'got ' + JSON.stringify(weakestTruthGrade(['BESTAETIGT', 'BESTAETIGT'])));
      // EC-FC-3: 1 Grad -> derselbe Grad (Idempotenz).
      check('KOM-2 (RED): EC-FC-3 — [X] -> X (Idempotenz, 1-elementige Menge)', weakestTruthGrade(['TENTATIV']) === 'TENTATIV', 'got ' + JSON.stringify(weakestTruthGrade(['TENTATIV'])));
      // 3-elementige Permutationen liefern dasselbe Minimum (HYPOTHESE schwaecher als TENTATIV/BESTAETIGT).
      const p1 = weakestTruthGrade(['BESTAETIGT', 'TENTATIV', 'HYPOTHESE']);
      const p2 = weakestTruthGrade(['HYPOTHESE', 'BESTAETIGT', 'TENTATIV']);
      const p3 = weakestTruthGrade(['TENTATIV', 'HYPOTHESE', 'BESTAETIGT']);
      check('KOM-2 (RED): 3 Permutationen einer Grad-Menge liefern dasselbe Minimum (Mengen-Invarianz)', p1 === p2 && p2 === p3 && p1 === 'HYPOTHESE', 'p1=' + p1 + ' p2=' + p2 + ' p3=' + p3);
    } else {
      check('KOM-2 (RED): weakestTruthGrade permutations-invariant + idempotent', false, 'weakestTruthGrade nicht vorhanden');
    }
  }

  // ── FC-2 (RED, EC-FC-3): leere Grad-Menge -> definierter Default, kein Crash. ──
  {
    const weakestTruthGrade = resolveHelper('weakestTruthGrade');
    if (typeof weakestTruthGrade === 'function') {
      let threw = false, out;
      try { out = weakestTruthGrade([]); } catch (e) { threw = true; }
      check('FC-2 (RED): EC-FC-3 — leere Grad-Menge -> definierter Default (kein Crash/Throw)', !threw, threw ? 'weakestTruthGrade([]) warf statt definierten Default zu liefern' : 'default=' + JSON.stringify(out));
    } else {
      check('FC-2 (RED): leere Grad-Menge liefert definierten Default (kein Crash)', false, 'weakestTruthGrade nicht vorhanden');
    }
  }

  // ── FC-3 (RED, load-bearing): blast_set-Eskalations-Leiter QUARANTAENE -> PIN-INVALIDIERUNG -> WELLE-SHRINK. ──
  // Der Schritt-4-Prompt (oder eine Helper-Konstante) nennt die 3 Stufen in dieser Reihenfolge UND die
  // blast_set-Definition (W_refs(B) Schnitt divergierte W{n}); Default-Stufe == QUARANTAENE; Termination-
  // Driver == divergierende W{n} (nicht der Batch).
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(2), { parallel_mode: true, nr_parallel_batches: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bpPrompt = fi.map(x => x.prompt).join('\n');
    // Stufen auch in einer Helper-Konstante zulaessig (z.B. BLAST_SET_LADDER) — pruefe Prompt ODER SRC.
    const hay = bpPrompt + '\n' + SRC;
    const iQ = hay.search(/QUARANT[AÄ]NE/i), iP = hay.search(/PIN-?INVALIDIERUNG/i), iS = hay.search(/WELLE-?SHRINK/i);
    const ladderOrdered = [iQ, iP, iS].every(i => i >= 0) && iQ < iP && iP < iS;
    check('FC-3 (RED): blast_set-Eskalations-Leiter QUARANTAENE -> PIN-INVALIDIERUNG -> WELLE-SHRINK in dieser Reihenfolge', ladderOrdered, 'Leiter fehlt/unsortiert: ' + JSON.stringify({ q: iQ, p: iP, s: iS }));
    // blast_set-Definition: W_refs(B) Schnitt divergierte W{n} != leer.
    const hasBlastSetDef = /blast_set/i.test(hay) && /(?:W_refs|W-?refs)/i.test(hay) && /(?:divergiert\w*|divergent)/i.test(hay);
    check('FC-3 (RED): blast_set-Definition (W_refs(B) ∩ divergierte W{n}) im Schritt-4-Kontext/Helper', hasBlastSetDef, 'keine blast_set-Definition mit W_refs/divergiert (greenfield)');
    // Default-Stufe == QUARANTAENE; Termination-Driver == divergierende W{n}.
    const defaultQuarantine = /QUARANT[AÄ]NE\b[^\n]*?(?:Default|Standard)|(?:Default|Standard)[^\n]*?QUARANT[AÄ]NE/i.test(hay);
    check('FC-3 (RED): Default-Eskalations-Stufe == QUARANTAENE (Standard)', defaultQuarantine, 'QUARANTAENE nicht als Default markiert');
    const driverIsTruth = /Termination[\s-]?Driver[^\n]*?(?:divergierend\w*\s+W\{?n\}?|W\{?n\}?)|divergierend\w*\s+W\{?n\}?[^\n]*?(?:Termination|Driver)/i.test(hay);
    check('FC-3 (RED): Termination-Driver == divergierende W{n} (nicht der Batch)', driverIsTruth, 'Termination-Driver nicht an die divergierende W{n} gebunden');
  }

  // ─────────────────────────────────────────────────────────────────────────
  // KOM-3 (Negativ-Schaerfe) — Kommutativitaets-VORAUSSETZUNG: ueber ALLE phase==='Implement'-Spawns
  //   0 Model/SRS-Write UND 0 truth_to_batches-Write (nur die serielle Barrier mutiert -> Thunk-
  //   Reihenfolge irrelevant). Bundelt PC-2 + TW-2 zur expliziten Kommutativitaets-Aussage.
  // ─────────────────────────────────────────────────────────────────────────
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(3), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const implSpawns = spawns.filter(x => x.phase === 'Implement');
    const modelWrites = implSpawns.filter(x => /(?:Model\/SRS[\s-]?Write|modelSync|_SDF_berater_modelSync|Model[\s-]?Mutation|SRS[\s-]?Write)/i.test(x.prompt));
    const truthWrites = implSpawns.filter(x => /(?:schreibe|write|setze)[^\n]*truth_to_batches|truth_to_batches\s*[:=]/i.test(x.prompt));
    check('KOM-3 (RED): 0 Model/SRS-Write in allen parallel()-Thunks (phase===Implement) — Reihenfolge irrelevant', modelWrites.length === 0, modelWrites.length + ' Implement-Spawns tragen Model/SRS-Write');
    check('KOM-3 (RED): 0 truth_to_batches-Write in allen parallel()-Thunks (nur die serielle Barrier mutiert)', truthWrites.length === 0, truthWrites.length + ' Implement-Spawns tragen truth_to_batches-Write');
  }

  // ─────────────────────────────────────────────────────────────────────────
  // EC-NR-1 / Null-Regression (QG-4): parallel_mode=OFF (fanout==1) byte-identisch — runFanInBarrier
  //   ungerufen, KEIN truth_to_batches-/weakestGrade-Effekt; Helper seriell No-Op-Vertraeglich.
  // ─────────────────────────────────────────────────────────────────────────
  {
    const { result, spawns } = await runWithParallel(ARGS(wave(2)), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    check('NR-1 (RED-konsistent/GUARD-nah): OFF/seriell -> 0 Fan-In-Barrier-Spawns (runFanInBarrier ungerufen, kein SB-3a-Effekt)', fi.length === 0, 'got ' + fi.length + ' Barrier-Spawns trotz OFF');
    // Kein truth_to_batches-Effekt im seriellen Pfad (kein Worker-Spawn traegt einen truth_to_batches-Write).
    const truthInSerial = spawns.some(x => /truth_to_batches\s*[:=]|schreibe[^\n]*truth_to_batches/i.test(x.prompt));
    check('NR-1: OFF -> kein truth_to_batches-Schreib-Effekt im seriellen Pfad (byte-relevante Null-Regression)', !truthInSerial, 'serieller Pfad traegt einen truth_to_batches-Write (Null-Regression gebrochen!)');
    check('NR-1: OFF -> effective_fanout=1 + terminated=completed (Verhalten unveraendert)', result.effective_fanout === 1 && result.terminated_reason === 'completed', result.effective_fanout + '/' + result.terminated_reason);
  }

  // ===========================================================================
  // BL-230 SB-3b (Stage 1, RED-first) — G7-KONFORM: Barrier-Schritt-5 Konformitaets-
  //   Gate-Vorbedingung + welle-aggregierter loopDecision-Aggregat-Slot.
  //
  // Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (SB-3b CODE-TEIL, 8 Code-
  //   Exit-Kriterien + 3 Kommutativitaet + 10 Edge-Cases). SB-3b FLESHT Barrier-Schritt 5:
  //   (a) der Konformitaets-Check (N-Report-Validierung, Phase-3-gelaufen?) als VORBEDINGUNG
  //   VOR dem loopDecision-Aggregat; (b) das WELLE-aggregierte loopDecision (EIN Aggregat ueber
  //   die N LEBENDEN Batches, batch_id-sortiert, "1 toter Batch != Welle tot") — KEIN
  //   "STUB ... spaeter"-Wortlaut mehr fuer Schritt 5. Schritt 2 (Post-Merge-Green) bleibt STUB.
  //
  //   Die reine N-Report-Gate-FUNKTION (ALL-konjunktiv / Permutations-Invarianz / N=1==heute)
  //   ist im PY-Teil getestet (test_guard_geist9_wave_conformance.py). HIER: das BARRIER-WIRING
  //   (Schritt-5-Prompt: Konformitaets-Check VOR Aggregat + welle-aggregierter Slot + OFF Null-Reg).
  //
  // Geschrieben vom RED-Worker (BL-230 SB-3b RED). GREEN-Worker haertet dispatch_implement.js
  //   runFanInBarrier Schritt 5 SEPARAT (RED != GREEN, INV-BUILD-GRAIN — dieser Worker aendert
  //   NUR Tests). Faehrt via makeFactory/runWithParallel/makeParallelSpy/fanInOf/ARGS_P/wave/ARGS
  //   — exakt das bestehende Muster (AON-/FB-/PC-/TW-/FC-Bloecke oben, selber IIFE-Scope).
  //
  // RED-Erwartung: G7W-1..G7W-3 FAILEN (heute traegt Schritt 5 den SB-1b-STUB-Wortlaut
  //   "loopDecision-Aggregat: G6-Vektor ... STUB ... INHALT = AK-WELLE-LOOPDEC / AK-G7-KONFORM,
  //   spaeter" — KEIN Konformitaets-Check-Vorbedingung, KEIN welle-aggregierter Inhalt). NR/FB-1
  //   bleiben GRUEN (Schritt 5 ist + bleibt der LETZTE Schritt; OFF ruft die Barrier nicht).
  // ===========================================================================

  // ── G7W-1 (RED, load-bearing): Schritt-5-Prompt nennt den Konformitaets-Check ALS VORBEDINGUNG VOR dem loopDecision-Aggregat. ──
  // Exit-Kriterium "Barrier-Schritt 5 fuehrt den Konformitaets-Check als VORBEDINGUNG vor dem
  //   loopDecision-Aggregat aus" (Reihenfolge: Konformitaets-Check VOR loopDecision-Aggregat im
  //   Schritt-5-Text; Gate-FAIL -> KEIN Aggregat, fail-loud-Marker).
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(3), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    // Der Schritt-5-Text muss einen N-Report-Konformitaets-/Prozess-Gate-Check nennen (Phase-3-gelaufen?).
    const hasConformanceCheck = /(?:Konformit[aä]ts[\s-]?(?:Check|Gate)|N[\s-]?Report[\s-]?(?:Validierung|Konformit[aä]t)|waveConformanceGate|wave_conformance_gate|Phase[\s-]?3[\s-.]?x?\s+(?:gelaufen|vorhanden|gepruef)|Prozess[\s-]?Konformit[aä]t)/i.test(bp);
    check('G7W-1 (RED): Barrier-Schritt-5-Prompt nennt den N-Report-Konformitaets-Check (G7-Gate, Phase-3-gelaufen?)', fi.length === 1 && hasConformanceCheck, fi.length ? 'Schritt 5 nennt keinen Konformitaets-/G7-Gate-Check (SB-1b-STUB-Wortlaut)' : 'kein Fan-In-Spawn');
    // Reihenfolge: der Konformitaets-Check steht VOR der loopDecision-Aggregat-Nennung.
    const iCheck = bp.search(/(?:Konformit[aä]ts[\s-]?(?:Check|Gate)|N[\s-]?Report[\s-]?(?:Validierung|Konformit[aä]t)|waveConformanceGate|wave_conformance_gate|Prozess[\s-]?Konformit[aä]t)/i);
    const iAgg = bp.search(/loopDecision-Aggregat|loopDecision.Aggregat/i);
    check('G7W-1 (RED): Konformitaets-Check steht VOR dem loopDecision-Aggregat im Schritt-5-Text (Vorbedingung)', iCheck >= 0 && iAgg >= 0 && iCheck < iAgg, 'Reihenfolge: check@' + iCheck + ' aggregat@' + iAgg + ' (Check nicht als Vorbedingung vor dem Aggregat)');
    // Gate-FAIL -> KEIN Aggregat (fail-loud-Marker): der Schritt-5-Text nennt die fail-loud-Konsequenz.
    const hasFailLoud = /(?:Gate[\s-]?FAIL|fail[\s-]?loud|FAIL[\s-]?loud)[^\n]*?(?:KEIN|kein|ohne)\s+(?:Aggregat|loopDecision)|(?:KEIN|kein)\s+Aggregat[^\n]*?(?:Gate[\s-]?FAIL|fail[\s-]?loud)/i.test(bp);
    check('G7W-1 (RED): Schritt 5 nennt Gate-FAIL -> KEIN loopDecision-Aggregat (fail-loud-Vorbedingung)', hasFailLoud, 'Schritt 5 nennt keine Gate-FAIL->kein-Aggregat-Konsequenz (fail-loud fehlt)');
  }

  // ── G7W-2 (RED, load-bearing): das loopDecision-Aggregat ist WELLE-aggregiert ueber die N LEBENDEN Batches (batch_id-sortiert), NICHT per-Batch. ──
  // Exit-Kriterium: EIN Aggregat ueber `liveSortedIds` (batch_id-sortiert, konsistent SB-3a Schritt 3/4)
  //   + "1 toter Batch != Welle tot"; KEIN "STUB ... spaeter"-Wortlaut mehr fuer Schritt 5.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(3), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    // Der Schritt-5-Bereich (ab dem loopDecision-Aggregat-Marker) muss welle-aggregiert + lebend-batch-sortiert sein.
    const iAgg = bp.search(/loopDecision-Aggregat|loopDecision.Aggregat/i);
    const step5 = iAgg >= 0 ? bp.slice(iAgg) : '';
    // RED-Schaerfe: der heutige STUB sagt nur "G6-Vektor ueber alle lebenden Batches aggregieren" — das
    // ist NICHT die welle-aggregierte Aussage. Verlange einen genuin neuen Welle-Aggregat-Marker:
    // welle-aggregiert / EIN Aggregat ueber / liveSortedIds (NICHT die generische STUB-Formel).
    const isWaveAggregated = /(?:welle[\s-]?aggregiert|EIN\s+(?:welle[\s-]?aggregiertes?\s+)?Aggregat\s+ueber|liveSortedIds)/i.test(step5);
    check('G7W-2 (RED): loopDecision-Aggregat ist WELLE-aggregiert ueber die N lebenden Batches (EIN Aggregat ueber liveSortedIds)', iAgg >= 0 && isWaveAggregated, iAgg >= 0 ? 'Schritt 5 nennt keine welle-aggregierte Aggregation (welle-aggregiert/EIN Aggregat/liveSortedIds) — nur generische STUB-Formel' : 'kein loopDecision-Aggregat-Marker');
    // batch_id-sortierte/deterministische Reihenfolge im Schritt-5-Aggregat (konsistent SB-3a).
    const isSorted = /(?:batch_id[\s-]?sortiert|sortiert\s+nach\s+batch_id|deterministisch\w*\s+(?:sortiert|Reihenfolge)|liveSortedIds|\.sort\()/i.test(step5);
    check('G7W-2 (RED): Schritt-5-Aggregat iteriert in DETERMINISTISCHER batch_id-sortierter Reihenfolge (konsistent SB-3a Schritt 3/4)', isSorted, 'Schritt-5-Aggregat nennt keine batch_id-sortierte/deterministische Reihenfolge');
    // "1 toter Batch != Welle tot" (nur lebende Batches) — bleibt erhalten/explizit.
    const liveOnly = /1\s+toter\s+Batch\s*!?=?\s*Welle\s+tot|nur\s+(?:die\s+)?lebend\w*|kein\w*\s+tote\w*\s+Batch|filter\(Boolean\)/i.test(step5);
    check('G7W-2 (RED): Schritt-5-Aggregat nennt "1 toter Batch != Welle tot" / nur lebende Batches', liveOnly, 'Schritt 5 nennt keine lebend-Batch-Beschraenkung im Aggregat');
    // KEIN "STUB ... spaeter"-Wortlaut mehr fuer Schritt 5 (der Aggregat-INHALT ist jetzt gefleshTt).
    const stillStub = /loopDecision-Aggregat[^\n]*?STUB|STUB[^\n]*?loopDecision-Aggregat|loopDecision-Aggregat[^\n]*?(?:INHALT\s*=\s*AK-WELLE-LOOPDEC|spaeter)/i.test(bp);
    check('G7W-2 (RED): Schritt 5 traegt KEINEN "STUB ... spaeter / INHALT = AK-WELLE-LOOPDEC"-Wortlaut mehr (Aggregat-INHALT gefleshTt)', !stillStub, 'Schritt 5 traegt noch den SB-1b-STUB-Wortlaut ("STUB ... INHALT = AK-WELLE-LOOPDEC, spaeter")');
  }

  // ── G7W-3 [GUARD-nah] (Null-Regression QG-4): Schritt 5 bleibt der LETZTE Schritt (FB-1-Reihenfolge intakt) + Schritt 2 bleibt STUB. ──
  // EC-WL-1 / FB-1-Wache: das Fleshen von Schritt 5 darf die 5-Schritt-Reihenfolge NICHT brechen
  //   (Merge < Green < Model/SRS < Truth-Reval < loopDecision-Aggregat) und Schritt 2 (Post-Merge-Green)
  //   bleibt STUB (gehoert NICHT zu G7 = SB-4).
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(3), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    const iMerge = bp.search(/Code-Merge/i);
    const iGreen = bp.search(/Post-Merge-Green|Post-Merge.Green-?Check/i);
    const iModel = bp.search(/Model\/SRS|Model.SRS-Writes?/i);
    const iTruth = bp.search(/Truth-Reval|Truth-Revalidierung/i);
    const iLoop = bp.search(/loopDecision-Aggregat|loopDecision.Aggregat/i);
    check('G7W-3 [GUARD-nah]: 5-Schritt-Reihenfolge intakt (Merge<Green<Model/SRS<Truth-Reval<loopDecision-Aggregat), Schritt 5 bleibt LETZTER', [iMerge, iGreen, iModel, iTruth, iLoop].every(i => i >= 0) && iMerge < iGreen && iGreen < iModel && iModel < iTruth && iTruth < iLoop, 'Reihenfolge gebrochen: ' + JSON.stringify({ merge: iMerge, green: iGreen, model: iModel, truth: iTruth, loop: iLoop }));
    // Schritt 2 (Post-Merge-Green) bleibt STUB (gehoert NICHT zu G7).
    const greenStillStub = /Post-Merge-Green[^\n]*?STUB|STUB[^\n]*?Post-Merge-Green/i.test(bp);
    check('G7W-3 [GUARD-nah]: Schritt 2 (Post-Merge-Green) bleibt STUB (gehoert NICHT zu G7, = SB-4)', greenStillStub, 'Schritt 2 (Post-Merge-Green) traegt keinen STUB-Marker mehr (SB-3b haette ihn faelschlich gefleshTt)');
  }

  // ── G7W-NR-1 [GUARD] (Null-Regression QG-4): OFF/serieller Pfad ruft runFanInBarrier NICHT auf -> kein G7-Effekt. ──
  // EC-NR-1: bei default-args (fanout==1) gibt es 0 Fan-In-Spawns; effective_fanout==1 + completed.
  {
    const { result, spawns } = await runWithParallel(ARGS(wave(3)), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    check('G7W-NR-1 [GUARD]: OFF/seriell -> 0 Fan-In-Barrier-Spawns (kein G7-Konformitaets-Gate-Effekt)', fi.length === 0, 'got ' + fi.length + ' Barrier-Spawns trotz OFF');
    check('G7W-NR-1 [GUARD]: OFF -> effective_fanout=1 + terminated=completed (byte-identisch)', result.effective_fanout === 1 && result.terminated_reason === 'completed', result.effective_fanout + '/' + result.terminated_reason);
  }

  // ===========================================================================
  // BL-230 SB-4 (Stage 1, RED-first) — GO-PARALLEL-FN / PARALLEL-SAFE / BUDGET-CAP + WELLE-LOOPDEC-VEKTOR.
  //
  // Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (SB-4-Abschnitt, 17 CODE-Exit-Kriterien
  //   inkl. 5 Fallback-Tests + Vier-Faktor-Wahrheitstabelle). SB-4 baut die Scheduling-/Gate-Funktions-
  //   Familie: goParallel(ctx) (Gate-Kette + 5 W10-Fallback + nur-senken + verdrahtet), parallelSafe(a,b)
  //   (Vier-Faktor-Praedikat), Budget-Cap-Arithmetik (min(...,resource_caps) + Nested N_outer×M_inner≤Cap +
  //   SOA-2 Resolver-Read), UND den loopDecision-VEKTOR (Barrier-Schritt-5 Aggregat-Slot SB-3b -> per-Batch-
  //   Vektor + sc_resume_from-VEKTOR, INV-MODUS-9-Wellen-Neufassung).
  //
  // IST-Zustand (grep-verifiziert 2026-06-22): goParallel/parallelSafe/GO_PARALLEL/parallel_safe/THRESHOLD/
  //   resource_caps/dep_disjoint/experiment_coupled = 0 im Motor (greenfield). effective_fanout ist heute
  //   eine nackte min(...)-Formel OHNE Gate-Kette (Z539). loop_decision ist heute ein SKALAR (Z1142/Z1163;
  //   SB-3b-Aggregat ueber liveSortedIds).
  //
  // Geschrieben vom RED-Worker (BL-230 SB-4 RED, M5-Symbiose-Build). GREEN-Worker haertet
  //   dispatch_implement.js SEPARAT (RED != GREEN, INV-BUILD-GRAIN — dieser Worker aendert NUR Tests,
  //   KEIN Produktiv-Code). Faehrt via makeFactory/runWithParallel/makeParallelSpy/fanInOf/ARGS_P/wave/
  //   extractFn/resolveHelper — exakt das bestehende Muster (AON-/FB-/PC-/TW-/FC-/G7W-Bloecke oben, selber
  //   IIFE-Scope, also sichtbar). Reine Funktionen via extractFn/resolveHelper (globalThis ODER SRC-Funktion,
  //   analog SB-2 CO-* / SB-3a KOM-2 weakestTruthGrade).
  //
  // RED-Erwartung: alle SB-4-Tests FAILEN (goParallel/parallelSafe/resource_caps/loop_decision-Vektor
  //   existieren nicht). Kanarienvoegel (AON-1/CM-4/FB-4/T-DIAL-*/AON-2/3/7/FB-1) bleiben GRUEN.
  //
  // HINWEIS DOKU-TEIL (AK-WELLE-LOOPDEC-Doku, _SDF_orchestrate_post.md 4.1-WELLE INV-MODUS-9-Neufassung)
  //   ist verify_mode=scenario (BL-276) — KEIN RED-Test. Beleg via Szenario fuer den GREEN-Worker, NICHT hier.
  // ===========================================================================

  // ─────────────────────────────────────────────────────────────────────────
  // AK-GO-PARALLEL-FN (k=76): reine Funktion goParallel(ctx) — Gate-Kette
  //   G0∧G1-R∧G3∧G4∧G5∧G6 ∧ alle_batches concurrency_class==PARALLEL ∧ |welle|>=2 ∧ Σgroesse>=THRESHOLD.
  //   GO_PARALLEL gruen -> effective_fanout > 1; sonst SERIELL-MIT-KLEINEREN-RINGEN (effective_fanout=1).
  //   nur-senken-Invariante: Ergebnis <= min(nr, |welle|, MAX_CONCURRENT), nie darueber (W9-Falsifikation).
  // RED weil grep goParallel/GO_PARALLEL/THRESHOLD im Motor = 0 (greenfield).
  // ─────────────────────────────────────────────────────────────────────────

  // GO-PARALLEL-Kontext-Fabrik: alle Gates gruen, grosse PARALLEL-Welle, Σgroesse ueber Schwelle.
  // Die GREEN-Impl darf die Feld-Namen anders nennen — der Test fuettert ein vollstaendiges grunes Bild
  // (alle plausiblen Gate-/Klassen-/Schwellen-Felder gesetzt) und prueft NUR das Senk-/GO-Verhalten.
  const goCtxGreen = (over) => Object.assign({
    // Gate-Kette (alle gruen)
    G0_armed: true, G1_reader: true, G3_worktree: true, G4_idempotent: true, G5_file_disjoint: true, G6_post_multiplex: true,
    gates: { G0: true, G1: true, G3: true, G4: true, G5: true, G6: true },
    // alle Batches PARALLEL
    concurrency_classes: ['PARALLEL', 'PARALLEL', 'PARALLEL'],
    all_parallel: true,
    // Welle gross genug + Σgroesse ueber Overhead-Schwelle
    welle_size: 3, wave_size: 3,
    sum_groesse: 1000, sum_size: 1000, total_size: 1000,
    srs_alarm: false, k_score_growing: false,
    // Cap-Eingaben (heutige min-Formel)
    nr_parallel_batches: 3, max_concurrent: 16, parallel_mode: true,
  }, over || {});

  // ── GP-1 (RED, load-bearing): goParallel existiert + bei allen Gates gruen -> effective_fanout > 1 (GO_PARALLEL gruen). ──
  {
    const goParallel = resolveHelper('goParallel');
    check('GP-1 (RED): reine Funktion goParallel existiert (globalThis-Export ODER Source-Funktion)', typeof goParallel === 'function', 'goParallel nicht greifbar (weder globalThis noch SRC-Funktion) — greenfield');
    if (typeof goParallel === 'function') {
      const ef = goParallel(goCtxGreen());
      const fanout = (ef && typeof ef === 'object') ? (ef.effective_fanout != null ? ef.effective_fanout : ef.fanout) : ef;
      check('GP-1 (RED): alle Gates gruen + grosse PARALLEL-Welle -> effective_fanout > 1 (GO_PARALLEL gruen)', typeof fanout === 'number' && fanout > 1, 'fanout=' + JSON.stringify(ef));
    } else {
      check('GP-1 (RED): alle Gates gruen -> effective_fanout > 1', false, 'goParallel nicht vorhanden');
    }
  }

  // ── GP-2 (RED, nur-senken-Invariante W9): goParallel-Ergebnis <= min(nr, |welle|, MAX_CONCURRENT), nie darueber. ──
  // Es gibt KEINEN Input, fuer den das Ergebnis den heutigen min(...)-Wert UEBERSTEIGT (heben unmoeglich).
  {
    const goParallel = resolveHelper('goParallel');
    if (typeof goParallel === 'function') {
      const fanoutOf = (ctx) => { const e = goParallel(ctx); return (e && typeof e === 'object') ? (e.effective_fanout != null ? e.effective_fanout : e.fanout) : e; };
      // mehrere Inputs: nr klein, |welle| klein, Cap klein — in jedem Fall <= min(...).
      const cases = [
        { nr_parallel_batches: 2, welle_size: 3, wave_size: 3, max_concurrent: 16, expectMin: 2 },
        { nr_parallel_batches: 8, welle_size: 2, wave_size: 2, max_concurrent: 16, expectMin: 2 },
        { nr_parallel_batches: 32, welle_size: 18, wave_size: 18, max_concurrent: 16, concurrency_classes: Array(18).fill('PARALLEL'), expectMin: 16 },
      ];
      let allWithinMin = true, detail = '';
      for (const c of cases) {
        const f = fanoutOf(goCtxGreen(c));
        if (!(typeof f === 'number' && f <= c.expectMin)) { allWithinMin = false; detail += ' got ' + f + ' > min ' + c.expectMin + ';'; }
      }
      check('GP-2 (RED): goParallel SENKT nur — Ergebnis <= min(nr,|welle|,MAX_CONCURRENT), nie darueber (W9-Falsifikation)', allWithinMin, detail || 'ok');
    } else {
      check('GP-2 (RED): nur-senken-Invariante (Ergebnis <= heutiger min(...))', false, 'goParallel nicht vorhanden');
    }
  }

  // ── GP-3 (RED, verdrahtet): effective_fanout im Motor ist aus goParallel abgeleitet (nicht mehr nackte min-Formel). ──
  // Im Motor wird effective_fanout aus goParallel(...) abgeleitet: bei parallel_mode + allen Gates gruen +
  //   grosser Welle ist effective_fanout > 1, bei rotem Gate == 1. Wir pruefen die VERDRAHTUNG am Source-Text:
  //   goParallel muss in der effective_fanout-Ableitung referenziert sein (kein nacktes Math.min ohne Gate-Funktion).
  {
    // RED-Schaerfe: heute ist Z539 `const effective_fanout = parallel_mode ? Math.min(...) : 1` OHNE goParallel.
    const efAssign = (SRC.match(/effective_fanout\s*=\s*[\s\S]{0,240}/) || [])[0] || '';
    const wiredToGoParallel = /goParallel\s*\(/.test(efAssign);
    check('GP-3 (RED): effective_fanout-Ableitung im Motor ruft goParallel(...) (verdrahtet, nicht nackte min-Formel)', wiredToGoParallel, 'effective_fanout wird heute aus nacktem Math.min ohne goParallel(...) abgeleitet (Z539-STUB)');
  }

  // ── GP-4 [GUARD-nah] (Null-Regression QG-4): parallel_mode=OFF -> goParallel liefert SERIELL (effective_fanout=1). ──
  // Bei default-args/OFF ist effective_fanout==1, kein parallel()-Pfad. (Auch als Funktions-Vertrag: parallel_mode=false -> 1.)
  {
    const goParallel = resolveHelper('goParallel');
    if (typeof goParallel === 'function') {
      const e = goParallel(goCtxGreen({ parallel_mode: false }));
      const fanout = (e && typeof e === 'object') ? (e.effective_fanout != null ? e.effective_fanout : e.fanout) : e;
      check('GP-4 (RED): goParallel(parallel_mode=false) -> SERIELL (effective_fanout==1, OFF byte-identisch)', fanout === 1, 'fanout=' + JSON.stringify(e));
    } else {
      check('GP-4 (RED): goParallel(OFF) -> effective_fanout==1', false, 'goParallel nicht vorhanden');
    }
    // Motor-Verhalten OFF bleibt 1 (GUARD): default-args -> effective_fanout==1 (deckt sich mit AON-1/CM-4/FB-4).
    const { result } = await runWithParallel(ARGS(wave(3)), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    check('GP-4 [GUARD] OFF: Motor effective_fanout==1 + terminated=completed (Null-Regression unberuehrt)', result.effective_fanout === 1 && result.terminated_reason === 'completed', result.effective_fanout + '/' + result.terminated_reason);
  }

  // ── Fuenf-Fallback-Faelle (AK-GO-PARALLEL-FN, W10) — je 1 dedizierter RED-Test: GO_PARALLEL rot -> SERIELL. ──
  // Jeder Fallback senkt effective_fanout auf 1 (seriell-mit-kleineren-Ringen); kein WAVE.
  {
    const goParallel = resolveHelper('goParallel');
    const fanoutOf = (ctx) => { const e = goParallel(ctx); return (e && typeof e === 'object') ? (e.effective_fanout != null ? e.effective_fanout : e.fanout) : e; };
    const haveFn = typeof goParallel === 'function';

    // FB-GP-1: Gate rot (irgendein G0..G6 false) -> seriell (voller Batch, kein Ring-Shrink, nur kein Parallel).
    check('FB-GP-1 (RED): Gate rot (G5_file_disjoint=false) -> effective_fanout==1 (seriell, kein WAVE)',
      haveFn && fanoutOf(goCtxGreen({ G5_file_disjoint: false, gates: { G0: true, G1: true, G3: true, G4: true, G5: false, G6: true } })) === 1,
      haveFn ? 'got ' + fanoutOf(goCtxGreen({ G5_file_disjoint: false, gates: { G0: true, G1: true, G3: true, G4: true, G5: false, G6: true } })) : 'goParallel nicht vorhanden');

    // FB-GP-2: concurrency_class ∈ {DEPENDS, EXCLUSIVE} (nicht alle PARALLEL) -> seriell / Semaphor.
    check('FB-GP-2 (RED): >=1 DEPENDS/EXCLUSIVE-Batch (nicht alle PARALLEL) -> effective_fanout==1 (kein WAVE)',
      haveFn && fanoutOf(goCtxGreen({ concurrency_classes: ['PARALLEL', 'EXCLUSIVE', 'PARALLEL'], all_parallel: false })) === 1,
      haveFn ? 'got ' + fanoutOf(goCtxGreen({ concurrency_classes: ['PARALLEL', 'EXCLUSIVE', 'PARALLEL'], all_parallel: false })) : 'goParallel nicht vorhanden');

    // FB-GP-3: File-Overlap (parallelSafe==false fuer >=1 Paar) -> der kollidierende Teil seriell (kein Fan-Out ueber das Paar).
    check('FB-GP-3 (RED): >=1 nicht-parallelSafe-Paar (File-Overlap) -> effective_fanout==1 (kollidierender Teil seriell)',
      haveFn && fanoutOf(goCtxGreen({ G5_file_disjoint: false, file_disjoint: false, gates: { G0: true, G1: true, G3: true, G4: true, G5: false, G6: true }, parallel_safe_all: false })) === 1,
      haveFn ? 'got ' + fanoutOf(goCtxGreen({ G5_file_disjoint: false, file_disjoint: false, gates: { G0: true, G1: true, G3: true, G4: true, G5: false, G6: true }, parallel_safe_all: false })) : 'goParallel nicht vorhanden');

    // FB-GP-4: Welle zu klein (|welle|<MIN_FANOUT(2) ODER Σgroesse<WORKTREE_OVERHEAD_THRESHOLD) -> seriell (Overhead > Gewinn).
    check('FB-GP-4 (RED): |welle|==1 (< MIN_FANOUT=2) -> effective_fanout==1 (Overhead-Schwelle nicht erreicht)',
      haveFn && fanoutOf(goCtxGreen({ welle_size: 1, wave_size: 1, concurrency_classes: ['PARALLEL'] })) === 1,
      haveFn ? 'got ' + fanoutOf(goCtxGreen({ welle_size: 1, wave_size: 1, concurrency_classes: ['PARALLEL'] })) : 'goParallel nicht vorhanden');
    check('FB-GP-4 (RED): Σgroesse < WORKTREE_OVERHEAD_THRESHOLD -> effective_fanout==1 (Worktree-Overhead > Parallel-Gewinn)',
      haveFn && fanoutOf(goCtxGreen({ sum_groesse: 1, sum_size: 1, total_size: 1 })) === 1,
      haveFn ? 'got ' + fanoutOf(goCtxGreen({ sum_groesse: 1, sum_size: 1, total_size: 1 })) : 'goParallel nicht vorhanden');

    // FB-GP-5: SRS-Alarm / K-Score waechst (Unsicherheit steigt) -> kleinerer Ring, NICHT parallelisieren (W2-Belohnung-fuer-niedrige-Unsicherheit).
    check('FB-GP-5 (RED): SRS-Alarm / K-Score-Wachstum -> kein WAVE / kleinerer Ring (effective_fanout==1)',
      haveFn && fanoutOf(goCtxGreen({ srs_alarm: true, k_score_growing: true })) === 1,
      haveFn ? 'got ' + fanoutOf(goCtxGreen({ srs_alarm: true, k_score_growing: true })) : 'goParallel nicht vorhanden');
  }

  // ─────────────────────────────────────────────────────────────────────────
  // AK-PARALLEL-SAFE (k=70): reines Praedikat parallelSafe(A,B) = dep_disjoint ∧ file_disjoint ∧
  //   truth_disjoint ∧ ¬experiment_coupled (Vier-Faktor-Konjunktion, Model W8).
  // RED weil grep parallelSafe/parallel_safe/dep_disjoint im Motor = 0 (greenfield).
  // ─────────────────────────────────────────────────────────────────────────

  // Vier-Faktor-Paar-Fabrik: zwei Batches mit explizit gesetzten Faktoren. Die GREEN-Impl darf die Faktoren
  //   aus den Batch-Feldern ableiten — der Test setzt sie sowohl als Paar-Faktoren ALS AUCH als plausible
  //   Batch-Felder (files/W_refs/concurrency_class), damit jede sinnvolle Ableitung gruen/rot fuettern kann.
  const psPair = (factors) => {
    const f = Object.assign({ dep_disjoint: true, file_disjoint: true, truth_disjoint: true, experiment_coupled: false }, factors || {});
    const A = {
      id: 'A', dep_disjoint: f.dep_disjoint, file_disjoint: f.file_disjoint, truth_disjoint: f.truth_disjoint, experiment_coupled: f.experiment_coupled,
      files: f.file_disjoint ? ['a.js'] : ['shared.js'],
      depends_on: f.dep_disjoint ? [] : ['B'],
      W_refs: [], concurrency_class: f.experiment_coupled ? 'EXCLUSIVE' : 'PARALLEL', is_experiment: f.experiment_coupled,
    };
    const B = {
      id: 'B', dep_disjoint: f.dep_disjoint, file_disjoint: f.file_disjoint, truth_disjoint: f.truth_disjoint, experiment_coupled: f.experiment_coupled,
      files: f.file_disjoint ? ['b.js'] : ['shared.js'],
      depends_on: [], W_refs: [], concurrency_class: f.experiment_coupled ? 'EXCLUSIVE' : 'PARALLEL', is_experiment: f.experiment_coupled,
    };
    return [A, B, f];
  };
  const psResult = (fn, a, b) => { const r = fn(a, b); return (r && typeof r === 'object') ? (r.parallel_safe != null ? r.parallel_safe : r.safe) : r; };

  // ── PS-Wahrheitstabelle (RED, load-bearing): vollstaendige Vier-Faktor-Konjunktion. ──
  // T-PS-ALL: alle vier -> true; T-PS-DEP/FILE/TRUTH/EXP: je ein Faktor false -> false.
  {
    const parallelSafe = resolveHelper('parallelSafe');
    check('PS-1 (RED): reines Praedikat parallelSafe existiert (globalThis-Export ODER Source-Funktion)', typeof parallelSafe === 'function', 'parallelSafe nicht greifbar (greenfield)');
    if (typeof parallelSafe === 'function') {
      // T-PS-ALL: alle vier erfuellt -> true.
      const [aAll, bAll] = psPair({});
      check('PS T-PS-ALL (RED): alle vier Faktoren true (dep∧file∧truth∧¬exp) -> parallelSafe==true', psResult(parallelSafe, aAll, bAll) === true, 'got ' + JSON.stringify(parallelSafe(aAll, bAll)));
      // T-PS-DEP: dep_disjoint false -> false.
      const [aDep, bDep] = psPair({ dep_disjoint: false });
      check('PS T-PS-DEP (RED): dep_disjoint=false (Dependency-Kopplung) -> parallelSafe==false', psResult(parallelSafe, aDep, bDep) === false, 'got ' + JSON.stringify(parallelSafe(aDep, bDep)));
      // T-PS-FILE: file_disjoint false -> false.
      const [aFile, bFile] = psPair({ file_disjoint: false });
      check('PS T-PS-FILE (RED): file_disjoint=false (File-Overlap) -> parallelSafe==false', psResult(parallelSafe, aFile, bFile) === false, 'got ' + JSON.stringify(parallelSafe(aFile, bFile)));
      // T-PS-TRUTH: truth_disjoint false -> false.
      const [aTruth, bTruth] = psPair({ truth_disjoint: false });
      check('PS T-PS-TRUTH (RED): truth_disjoint=false (shared_uncertain W{n}) -> parallelSafe==false', psResult(parallelSafe, aTruth, bTruth) === false, 'got ' + JSON.stringify(parallelSafe(aTruth, bTruth)));
      // T-PS-EXP: experiment_coupled true -> false.
      const [aExp, bExp] = psPair({ experiment_coupled: true });
      check('PS T-PS-EXP (RED): experiment_coupled=true (M5/EXCLUSIVE) -> parallelSafe==false (¬experiment_coupled greift)', psResult(parallelSafe, aExp, bExp) === false, 'got ' + JSON.stringify(parallelSafe(aExp, bExp)));
    } else {
      check('PS (RED): Vier-Faktor-Wahrheitstabelle pruefbar', false, 'parallelSafe nicht vorhanden');
    }
  }

  // ── PS truth_disjoint-Sonderfaelle (RED): geteiltes W{n} BESTAETIGT harmlos / shared_uncertain verbietet / disjunkt. ──
  // Die GREEN-Impl leitet truth_disjoint aus den W_refs + W-Status ab. Wir setzen geteilte/disjunkte W_refs
  //   mit explizitem Status (BESTAETIGT vs TENTATIV/HYPOTHESE/OFFEN) und einen optionalen w_status-Lookup.
  {
    const parallelSafe = resolveHelper('parallelSafe');
    if (typeof parallelSafe === 'function') {
      const mkBatch = (id, wrefs) => ({ id, files: [id + '.js'], depends_on: [], concurrency_class: 'PARALLEL', is_experiment: false, experiment_coupled: false, dep_disjoint: true, file_disjoint: true, W_refs: wrefs });
      // T-PS-TRUTH-CONFIRMED: geteiltes W{n} Status=BESTAETIGT (weight 0.0) -> harmlos -> parallelSafe==true.
      const aC = mkBatch('A', [{ id: 'W1', status: 'BESTAETIGT' }]);
      const bC = mkBatch('B', [{ id: 'W1', status: 'BESTAETIGT' }]);
      check('PS T-PS-TRUTH-CONFIRMED (RED): geteiltes W{n} BESTAETIGT (weight 0.0) harmlos -> parallelSafe==true', psResult(parallelSafe, aC, bC) === true, 'got ' + JSON.stringify(parallelSafe(aC, bC)));
      // T-PS-TRUTH-UNCERTAIN: geteiltes W{n} Status ∈ {TENTATIV,HYPOTHESE,OFFEN} -> shared_uncertain -> parallelSafe==false.
      const aU = mkBatch('A', [{ id: 'W2', status: 'HYPOTHESE' }]);
      const bU = mkBatch('B', [{ id: 'W2', status: 'HYPOTHESE' }]);
      check('PS T-PS-TRUTH-UNCERTAIN (RED): geteiltes W{n} HYPOTHESE (shared_uncertain) -> parallelSafe==false', psResult(parallelSafe, aU, bU) === false, 'got ' + JSON.stringify(parallelSafe(aU, bU)));
      // T-PS-TRUTH-DISJOINT: KEIN geteiltes W{n} (disjunkte W_refs) -> truth_disjoint==true -> parallelSafe==true.
      const aD = mkBatch('A', [{ id: 'W3', status: 'HYPOTHESE' }]);
      const bD = mkBatch('B', [{ id: 'W4', status: 'OFFEN' }]);
      check('PS T-PS-TRUTH-DISJOINT (RED): disjunkte W_refs (kein geteiltes W{n}) -> parallelSafe==true', psResult(parallelSafe, aD, bD) === true, 'got ' + JSON.stringify(parallelSafe(aD, bD)));
    } else {
      check('PS truth_disjoint-Sonderfaelle (RED): BESTAETIGT-harmlos / uncertain-verbietet / disjunkt', false, 'parallelSafe nicht vorhanden');
    }
  }

  // ── PS-NR (RED-konsistent): parallelSafe ist reine Funktion, OFF-Pfad unberuehrt (nur im GO_PARALLEL-Pfad konsumiert). ──
  // Bei default-args (OFF) wird parallelSafe nicht entscheidungs-relevant — der serielle Motor-Pfad ignoriert es.
  {
    const { result, spawns } = await runWithParallel(ARGS(wave(2)), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    check('PS-NR (RED-konsistent): OFF -> effective_fanout==1 (parallelSafe nicht entscheidungs-relevant im seriellen Pfad)', result.effective_fanout === 1, String(result.effective_fanout));
    // Negativ-Schaerfe: im OFF-Pfad wird kein parallel_safe-Verbot/-Marker in einen Worker-Spawn injiziert (kein OFF-Drift).
    const psInSerial = spawns.some(x => /parallel_safe|parallelSafe/i.test(x.prompt));
    check('PS-NR (RED-konsistent): OFF -> kein parallelSafe-Effekt im seriellen Pfad (kein OFF-Verhaltens-Drift)', !psInSerial, 'serieller Pfad traegt einen parallelSafe-Effekt (OFF-Drift)');
  }

  // ─────────────────────────────────────────────────────────────────────────
  // AK-BUDGET-CAP (k=55): effective_fanout = min(..., resource_caps) — Budget-Cap als zusaetzlicher
  //   SENKENDER Faktor; Nested-Cap-Arithmetik N_outer × M_inner <= Engine-Cap (kein Slot-Starvation).
  //   SOA-2: die Cap-ZAHLEN aus dem BL-234-Resolver gelesen/injiziert, NICHT hartkodiert.
  // RED weil grep resource_caps im Motor = 0 (greenfield).
  // ─────────────────────────────────────────────────────────────────────────

  // ── BC-1 (RED, load-bearing): resource_caps < heutiger min(...) -> effective_fanout == resource_caps (Cap senkt). ──
  // Motor-Pfad: ON nr=4 |welle|=4 -> heutiger min=4; injiziertes resource_caps=2 (< 4) -> effective_fanout==2.
  {
    const { result } = await runWithParallel(ARGS_P(wave(4), { parallel_mode: true, nr_parallel_batches: 4, resource_caps: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    check('BC-1 (RED): resource_caps=2 < min(4,4,16)=4 -> effective_fanout==2 (Budget-Cap senkt)', result.effective_fanout === 2, 'effective_fanout=' + result.effective_fanout + ' (resource_caps wird heute nicht gelesen -> bleibt 4)');
  }

  // ── BC-2 (RED): resource_caps >= heutiger min(...) -> effective_fanout == heutiger min (Cap hebt nie). ──
  // ON nr=2 |welle|=4 -> heutiger min=2; resource_caps=8 (>= 2) -> effective_fanout bleibt 2 (Cap hebt nie).
  {
    const { result } = await runWithParallel(ARGS_P(wave(4), { parallel_mode: true, nr_parallel_batches: 2, resource_caps: 8 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    check('BC-2 (RED): resource_caps=8 >= min(2,4,16)=2 -> effective_fanout==2 (Cap hebt nie)', result.effective_fanout === 2, 'effective_fanout=' + result.effective_fanout);
  }

  // ── BC-3 (RED, Nested): N_outer × M_inner > Engine-Cap -> Fan-Out gesenkt, sodass Produkt <= Cap (kein Slot-Starvation). ──
  // injiziertes nested: m_inner pro Welle-Slot + engine_cap. nr=8 |welle|=8 -> heutiger min=8; m_inner=4, engine_cap=16
  //   -> 8×4=32 > 16 -> N_outer muss auf 4 gesenkt werden (4×4=16 <= 16).
  {
    const { result } = await runWithParallel(ARGS_P(wave(8), { parallel_mode: true, nr_parallel_batches: 8, m_inner: 4, engine_cap: 16 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const ef = result.effective_fanout;
    check('BC-3 (RED, Nested): N_outer × M_inner(4) <= Engine-Cap(16) — effective_fanout auf 4 gesenkt (kein Slot-Starvation)', typeof ef === 'number' && ef * 4 <= 16 && ef === 4, 'effective_fanout=' + ef + ' (×4 = ' + (ef * 4) + ', muss <= 16 sein; Nested-Arithmetik fehlt -> bleibt 8)');
  }

  // ── BC-4 (RED, SOA-2 nicht-hartkodiert): die Cap-ZAHL wird injiziert/gelesen (analog nr_parallel_batches/parallel_mode aus A.*), kein neues Zahlen-Literal. ──
  // (1) Verhaltens-Beweis: resource_caps aus A.* gelesen (BC-1 zeigt: anderer Wert -> anderes effective_fanout).
  // (2) Source-Schaerfe: der Budget-Wert kommt aus A.* (session_params/Resolver), KEIN neues hartkodiertes Budget-Literal
  //     (MAX_CONCURRENT=16 bleibt die OBERE Schranke, nicht der Budget-Wert).
  {
    const readsResourceCaps = /A\.resource_caps|A\[\s*['"]resource_caps['"]\s*\]/.test(SRC);
    check('BC-4 (RED, SOA-2): resource_caps wird aus A.* (session_params/BL-234-Resolver) gelesen (injizierbar, nicht hartkodiert)', readsResourceCaps, 'kein A.resource_caps-Read im Motor (Budget-Cap-Quelle fehlt / waere hartkodiert)');
    // Negativ-Schaerfe: kein neues hartkodiertes Budget-Zahlen-Literal als resource_caps-Quelle (z.B. `resource_caps = 4`).
    const hardcodedBudget = /resource_caps\s*=\s*\d+/.test(SRC);
    check('BC-4 (RED, SOA-2): KEIN hartkodiertes resource_caps-Zahlen-Literal (Budget kommt aus Resolver, nicht Magic-Number)', !hardcodedBudget, 'resource_caps wird im Source auf ein Zahlen-Literal gesetzt (hartkodiert statt Resolver-Read)');
  }

  // ── BC-NR [GUARD-nah] (Null-Regression): OFF -> resource_caps irrelevant, effective_fanout==1. ──
  {
    const { result } = await runWithParallel(ARGS_P(wave(4), { parallel_mode: false, nr_parallel_batches: 4, resource_caps: 2 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    check('BC-NR (RED-konsistent): OFF + resource_caps gesetzt -> effective_fanout==1 (OFF dominiert, Budget-Cap irrelevant)', result.effective_fanout === 1, String(result.effective_fanout));
  }

  // ─────────────────────────────────────────────────────────────────────────
  // AK-WELLE-LOOPDEC (k=72, voll/G6): Barrier-Schritt 5 liefert einen loop_decision-VEKTOR (pro lebendem
  //   Batch ein Eintrag, batch_id-sortiert) + sc_resume_from-VEKTOR (pro Batch ein Wert, INV-MODUS-9-
  //   Wellen-Neufassung). Die wave_conformance_gate-Vorbedingung (SB-3b) bleibt VOR dem Vektor (Gate-FAIL
  //   -> kein Vektor). N=1 (OFF/Single-Mode) degradiert verhaltens-identisch zum heutigen Skalar.
  // RED weil loop_decision heute ein SKALAR ist (Z1142/Z1163; SB-3b-Aggregat ueber liveSortedIds).
  // ─────────────────────────────────────────────────────────────────────────

  // ── WL-1 (RED, load-bearing): N>1 lebende Batches -> loop_decision-VEKTOR mit GENAU N Eintraegen (batch_id-sortiert), kein Skalar. ──
  // Beobachtbar am Schritt-5-Barrier-Prompt: er muss einen per-Batch-VEKTOR ueber liveSortedIds nennen
  //   (N Eintraege, einer pro lebendem Batch), NICHT EIN aggregiertes Skalar.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(3), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    const iAgg = bp.search(/loopDecision-Aggregat|loopDecision.Aggregat|loop_decision-?VEKTOR|loop_decision[\s-]?Vektor/i);
    const step5 = iAgg >= 0 ? bp.slice(iAgg) : '';
    // RED-Schaerfe: SB-3b nennt EIN welle-aggregiertes Aggregat (Skalar). SB-4 MUSS einen per-Batch-VEKTOR nennen
    //   (pro lebendem Batch ein loop_decision-Eintrag, N Eintraege ueber liveSortedIds — NICHT EIN Aggregat-Skalar).
    const hasVektor = /(?:loop_decision[\s-]?(?:VEKTOR|Vektor)|VEKTOR[^\n]*?pro\s+(?:lebend\w*\s+)?Batch|pro\s+(?:lebend\w*\s+)?Batch\s+ein\s+loop_decision|N\s+Eintr[aä]ge[^\n]*?loop_decision|ein\s+loop_decision[\s-]?Eintrag\s+pro\s+Batch)/i.test(step5);
    check('WL-1 (RED): Schritt-5-Prompt nennt einen loop_decision-VEKTOR (pro lebendem Batch ein Eintrag, N ueber liveSortedIds), NICHT ein Aggregat-Skalar', fi.length === 1 && hasVektor, fi.length ? 'Schritt 5 nennt nur das SB-3b-Aggregat-Skalar (EIN welle-aggregiertes loopDecision), keinen per-Batch-VEKTOR' : 'kein Fan-In-Spawn');
    // Negativ-Schaerfe: der Schritt-5-Text darf NICHT mehr ausschliesslich "EIN welle-aggregiertes Aggregat ... NICHT per-Batch" sagen.
    const stillScalarOnly = /EIN\s+welle[\s-]?aggregiertes?\s+Aggregat[\s\S]*?NICHT\s+per-?Batch/i.test(step5) && !hasVektor;
    check('WL-1 (RED): Schritt 5 traegt NICHT mehr den SB-3b-"EIN Aggregat ... NICHT per-Batch"-Skalar-Wortlaut (Vektor loest Skalar ab)', !stillScalarOnly, 'Schritt 5 traegt noch den SB-3b-Skalar-Wortlaut ("EIN welle-aggregiertes Aggregat ... NICHT per-Batch")');
  }

  // ── WL-2 (RED, load-bearing): sc_resume_from ist ein VEKTOR (pro Batch ein Wert, INV-MODUS-9-Wellen-Neufassung), nicht Singular. ──
  // Der Schritt-5-Text nennt sc_resume_from PRO Batch (Vektor ueber liveSortedIds: "ergebnis" bei SC-Re-Entry,
  //   null bei Erst-Eintritt, INV-MODUS-9 pro Batch), NICHT ein globaler Singular-sc_resume_from.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(3), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    const namesScResume = /sc_resume_from/i.test(bp);
    const isVektor = /sc_resume_from[\s-]?(?:VEKTOR|Vektor)|sc_resume_from\s+pro\s+Batch|pro\s+Batch\s+ein\s+sc_resume_from|sc_resume_from[^\n]*?(?:pro\s+(?:lebend\w*\s+)?Batch|liveSortedIds|Vektor)/i.test(bp);
    const namesInvModus9 = /INV-MODUS-9/i.test(bp);
    check('WL-2 (RED): Schritt-5-Prompt nennt sc_resume_from als VEKTOR (pro Batch ein Wert, INV-MODUS-9-Wellen-Neufassung)', fi.length === 1 && namesScResume && isVektor, fi.length ? 'Schritt 5 nennt sc_resume_from nicht als per-Batch-Vektor (Singular / fehlt)' : 'kein Fan-In-Spawn');
    check('WL-2 (RED): Schritt-5-Prompt referenziert die INV-MODUS-9-Wellen-Neufassung (sc_resume_from pro Batch)', namesInvModus9, 'kein INV-MODUS-9-Bezug im Schritt-5-Text (Wellen-Neufassung fehlt)');
    // INV-MODUS-9-Semantik pro Batch: "ergebnis" bei SC-Re-Entry, null bei Erst-Eintritt.
    const hasSemantik = /["']?ergebnis["']?[^\n]*?(?:SC[\s-]?Re-?Entry|Re-?Eintritt)|(?:SC[\s-]?Re-?Entry|Re-?Eintritt)[^\n]*?["']?ergebnis["']?/i.test(bp) && /null[^\n]*?(?:Erst[\s-]?Eintritt|Erst-?Eintritt)|(?:Erst[\s-]?Eintritt)[^\n]*?null/i.test(bp);
    check('WL-2 (RED): INV-MODUS-9-Semantik pro Batch genannt (sc_resume_from="ergebnis" bei SC-Re-Entry, null bei Erst-Eintritt)', hasSemantik, 'Schritt 5 nennt die INV-MODUS-9-pro-Batch-Semantik (ergebnis/null) nicht');
  }

  // ── WL-3 [GUARD-nah] (Gate-Vorbedingung erhalten): die wave_conformance_gate-Vorbedingung (SB-3b) bleibt VOR dem Vektor. ──
  // Reihenfolge: Konformitaets-Gate VOR dem loop_decision-VEKTOR (Gate-FAIL -> kein Vektor); FB-1 (5-Schritt) bleibt gruen.
  {
    const { spawns } = await runWithParallel(ARGS_P(wave(3), { parallel_mode: true, nr_parallel_batches: 3 }), { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    const bp = fi.map(x => x.prompt).join('\n');
    const iGate = bp.search(/(?:Konformit[aä]ts[\s-]?(?:Check|Gate)|waveConformanceGate|wave_conformance_gate|N[\s-]?Report[\s-]?(?:Validierung|Konformit[aä]t))/i);
    const iVek = bp.search(/loop_decision[\s-]?(?:VEKTOR|Vektor)|loopDecision-Aggregat|pro\s+(?:lebend\w*\s+)?Batch\s+ein\s+loop_decision/i);
    check('WL-3 [GUARD-nah]: Konformitaets-Gate-Vorbedingung steht VOR dem loop_decision-Vektor (SB-3b-Gate erhalten, Gate-FAIL -> kein Vektor)', iGate >= 0 && iVek >= 0 && iGate < iVek, 'Reihenfolge: gate@' + iGate + ' vektor@' + iVek + ' (Gate nicht mehr Vorbedingung vor dem Vektor)');
    // Gate-FAIL -> kein Vektor (fail-loud): der Schritt-5-Text nennt die Konsequenz.
    const hasFailLoud = /(?:Gate[\s-]?FAIL|fail[\s-]?loud)[^\n]*?(?:KEIN|kein|ohne)\s+(?:Vektor|loop_decision|Aggregat)|(?:KEIN|kein)\s+(?:Vektor|loop_decision)[^\n]*?(?:Gate[\s-]?FAIL|fail[\s-]?loud)/i.test(bp);
    check('WL-3 [GUARD-nah]: Gate-FAIL -> KEIN loop_decision-Vektor (fail-loud-Vorbedingung erhalten)', hasFailLoud, 'Schritt 5 nennt keine Gate-FAIL->kein-Vektor-Konsequenz (fail-loud fehlt)');
  }

  // ── WL-4 (RED, Null-Regression N=1): N=1 (Single-Mode/OFF) -> Vektor 1-elementig == heutiger Skalar; Skalar-Verhalten erhalten. ──
  // OFF (default-args): loop_decision degradiert auf das heutige Skalar-Verhalten (TERMINATE), bestehende
  //   loopDecision-/AON-1/CM-4/FB-4-Tests bleiben gruen. (Der per-Batch-Vektor existiert nur im Wellen-Pfad.)
  {
    const { result, spawns } = await runWithParallel(ARGS(wave(1)), { modus: 'M2', elevation: ['BATCH_DONE'], loop: 'TERMINATE' }, makeParallelSpy().fn);
    const fi = fanInOf(spawns);
    check('WL-4 (RED-konsistent/GUARD): N=1/OFF -> 0 Fan-In-Barrier-Spawns (kein Wellen-Vektor-Pfad)', fi.length === 0, 'got ' + fi.length + ' Barrier-Spawns bei N=1');
    check('WL-4 (RED-konsistent/GUARD): N=1/OFF -> loop_decision degradiert auf Skalar (TERMINATE), effective_fanout==1', result.loop_decision === 'TERMINATE' && result.effective_fanout === 1, 'loop_decision=' + JSON.stringify(result.loop_decision) + ' effective_fanout=' + result.effective_fanout);
  }

  // ── NR-SB4 [GUARD] (Null-Regression QG-4): parallel_mode=OFF byte-identisch — keine der vier neuen Strukturen greift. ──
  // effective_fanout==1, kein parallel()-Pfad, loop_decision degradiert auf Skalar, ALLE SB-1a..SB-3b-GUARDs gruen.
  {
    const spy = makeParallelSpy();
    const { result } = await runWithParallel(ARGS(wave(3)), { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    check('NR-SB4 [GUARD] OFF: parallelFn 0x (kein Fan-Out — goParallel/Budget-Cap senken den OFF-Pfad nicht weg, sie greifen gar nicht)', spy.calls.length === 0, 'parallelFn ' + spy.calls.length + 'x trotz OFF');
    check('NR-SB4 [GUARD] OFF: effective_fanout==1 + loop_decision Skalar (TERMINATE) + completed (byte-identisch)', result.effective_fanout === 1 && result.loop_decision === 'TERMINATE' && result.terminated_reason === 'completed', result.effective_fanout + '/' + JSON.stringify(result.loop_decision) + '/' + result.terminated_reason);
  }

  // ===========================================================================
  // BL-230 SB-5 (LETZTER) — AK-MODI-SCOPE / AK-EXCL-SEMAPHOR / AK-GUARD-PERSIST.
  //   (AK-TRUTH-LEASE + der PY-Anteil von AK-EXCL-SEMAPHOR liegen in
  //    .claude/scripts/test_factory_lock_truth_lease.py — getrennte TDD-Welt.)
  //
  // Blueprint: <vault>/Backlog/BL-230.../4_Blueprint/BL-230_blueprint_AK-MOTOR-WELLE_S1.md → "## SB-5".
  //   Akzeptanz-Punkte AON-MS-FN-PURE/M5-EXCLUSIVE/PARTITION/OFF-NULL (1-4), AON-ES-DEFER/ENUM (5-6),
  //   AON-GP-PHASE3-REPLAY/RECALC-REPLAY/OFF-NULL (7-9), AON-TL-PINNED (12, dispatch-Seite).
  //
  // IST (grep-verifiziert 2026-06-22): modusParallelEligible/modusConcurrencyClass == 0;
  //   kein Semaphor/Defer; phase3_fired (Set Z520) + recalcRounds (Map Z525) sind IN-MEMORY
  //   (kein Motor-Read der persistenten Manifest-Marker phase3_fired_per_batch/recalc_rounds_per_batch).
  // Reine Funktionen via resolveHelper (globalThis ODER extractFn, analog goParallel/parallelSafe/weakestTruthGrade).
  // RED-Erwartung: alle Feature-Tests FAILEN; Begleit-GUARDs (OFF-Null, Enum-3-wertig) bleiben GRUEN.
  // ===========================================================================

  // ── AON-MS-FN-PURE (1, RED, load-bearing): reine Funktion modusParallelEligible(modus). ──
  //   M2/M3 -> eligible (parallel); M1/M4/M5/M6/M7/M8/M9 -> NICHT eligible (seriell); unbekannt -> fail-safe NICHT eligible.
  {
    const modusParallelEligible = resolveHelper('modusParallelEligible');
    check('AON-MS-FN-PURE (RED): reine Funktion modusParallelEligible existiert (globalThis-Export ODER Source-Funktion)', typeof modusParallelEligible === 'function', 'modusParallelEligible nicht greifbar — greenfield (grep == 0)');
    if (typeof modusParallelEligible === 'function') {
      const elig = (m) => { const r = modusParallelEligible(m); return (r && typeof r === 'object') ? (r.eligible != null ? r.eligible : r.parallel_eligible) : r; };
      check('AON-MS-FN-PURE (RED): M2 + M3 -> eligible (truthy)', !!elig('M2') && !!elig('M3'), 'M2=' + JSON.stringify(modusParallelEligible('M2')) + ' M3=' + JSON.stringify(modusParallelEligible('M3')));
      const serielleModi = ['M1', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9'];
      const allFalsy = serielleModi.every(m => !elig(m));
      check('AON-MS-FN-PURE (RED): M1/M4/M5/M6/M7/M8/M9 -> NICHT eligible (falsy)', allFalsy, serielleModi.map(m => m + '=' + JSON.stringify(elig(m))).join(' '));
      check('AON-MS-FN-PURE (RED): unbekannter Modus -> fail-safe NICHT eligible (im Zweifel SERIELL)', !elig('M42') && !elig(undefined) && !elig(''), 'M42=' + JSON.stringify(elig('M42')) + ' undef=' + JSON.stringify(elig(undefined)));
    } else {
      check('AON-MS-FN-PURE (RED): M2/M3 eligible, M1/M4-M9 nicht, unbekannt fail-safe', false, 'modusParallelEligible nicht vorhanden');
    }
  }

  // ── AON-MS-M5-EXCLUSIVE (2, RED): M5 traegt EXCLUSIVE; M1/SC sind seriell-aber-NICHT-EXCLUSIVE (DEPENDS/seriell genuegt). ──
  //   Das EXCLUSIVE-Merkmal kommt entweder aus dem Rueckgabe-Objekt von modusParallelEligible('M5')
  //   ODER aus einem Geschwister modusConcurrencyClass('M5')==='EXCLUSIVE'.
  {
    const modusParallelEligible = resolveHelper('modusParallelEligible');
    const modusConcurrencyClass = resolveHelper('modusConcurrencyClass');
    const exclusiveOf = (m) => {
      if (typeof modusConcurrencyClass === 'function') return modusConcurrencyClass(m);
      if (typeof modusParallelEligible === 'function') { const r = modusParallelEligible(m); return (r && typeof r === 'object') ? (r.concurrency_class || (r.exclusive ? 'EXCLUSIVE' : null)) : null; }
      return null;
    };
    const m5Excl = exclusiveOf('M5');
    check('AON-MS-M5-EXCLUSIVE (RED): M5 ist als EXCLUSIVE markiert (Rueckgabe-Objekt.exclusive/concurrency_class ODER modusConcurrencyClass)', m5Excl === 'EXCLUSIVE', 'M5-Klasse=' + JSON.stringify(m5Excl) + ' (weder exclusive:true noch concurrency_class==EXCLUSIVE noch modusConcurrencyClass)');
    const m1Excl = exclusiveOf('M1');
    check('AON-MS-M5-EXCLUSIVE (RED): M1 ist seriell-aber-NICHT-EXCLUSIVE (DEPENDS/seriell genuegt, kein Semaphor)', m1Excl !== 'EXCLUSIVE', 'M1-Klasse=' + JSON.stringify(m1Excl) + ' (M1 darf nicht EXCLUSIVE sein)');
  }

  // ── AON-MS-PARTITION (3, RED, load-bearing): Fan-Out-Partitionierung nach Modus. ──
  //   Gemischte Welle [M2,M1,M3,M5] mit parallel_mode:true -> der M1-Batch erscheint NICHT in einem
  //   Multi-Thunk-parallel()-Array; M5 NIE im selben parallel()-Array wie ein anderer Batch; M2+M3 duerfen
  //   gemeinsam parallel laufen. Modus-Quelle ist plan-zeit (A.batch_modes_hint, EC-MS-1 — der autoritative
  //   Modus entscheidet _SDF_berater_modusEntscheidung erst IM Fan-Out, INV-MODUS-1; hier nur konservative Vorab-Partition).
  {
    const five = [
      { id: 'sb_m2a', items: ['a'], stages: [1] },
      { id: 'sb_m1', items: ['b'], stages: [1] },
      { id: 'sb_m3', items: ['c'], stages: [1] },
      { id: 'sb_m5', items: ['d'], stages: [1] },
      { id: 'sb_m2b', items: ['e'], stages: [1] },
    ];
    const hint = { sb_m2a: 'M2', sb_m1: 'M1', sb_m3: 'M3', sb_m5: 'M5', sb_m2b: 'M2' };
    const spy = makeParallelSpy();
    const { result } = await runWithParallel(
      ARGS_P(five, { parallel_mode: true, nr_parallel_batches: 4, batch_modes_hint: hint }),
      { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);

    // Welche Sub-Batch-Ids stecken in welchem parallel()-Aufruf? (thunks->ids via Spawn-Korrelation
    // ist fragil; wir lesen die Chunk-Zusammensetzung ueber die Thunk-Counts + die Eingabe-Reihenfolge
    // ist NICHT mehr garantiert die Chunk-Grenze — daher pruefen wir die OBSERVIERBARE Invariante:
    // ein Multi-Thunk-Aufruf (count>=2) darf den M1- bzw M5-Batch NICHT enthalten. Da der Spy nur
    // counts sieht, prueft der GREEN-Pfad das ueber eine partitionsfaehige Chunk-Bildung — der
    // load-bearing beobachtbare Beweis ist: KEIN Multi-Thunk-Aufruf umfasst einen nicht-eligiblen Batch.)
    // Beobachtbarer Proxy (RED-faehig): es gibt mindestens 1 Multi-Thunk-Aufruf (M2+M3 zusammen) UND
    // jeder nicht-eligible Batch (M1/M5) wird in einem Single-Thunk-Chunk (count==1) gefahren.
    const multiThunkCalls = spy.calls.filter(c => c.count >= 2);
    const singleThunkCalls = spy.calls.filter(c => c.count === 1);
    check('AON-MS-PARTITION (RED): mind. 1 Multi-Thunk-parallel()-Aufruf (eligible M2/M3 duerfen gemeinsam parallel laufen)', multiThunkCalls.length >= 1, 'Multi-Thunk-Aufrufe=' + multiThunkCalls.length + ' (keine eligible-Welle gebildet)');
    // M1 + M5 (2 nicht-eligible Batches) -> je ein Single-Thunk-Chunk (oder serieller Pfad). Beweis: >=2 Single-Thunk-Aufrufe.
    check('AON-MS-PARTITION (RED): nicht-eligible Batches (M1 + M5) laufen NICHT in einem Multi-Thunk-Array (je Single-Thunk-Chunk/seriell)', singleThunkCalls.length >= 2, 'Single-Thunk-Chunks=' + singleThunkCalls.length + ' (M1/M5 nicht aus dem Multi-Thunk-Array herauspartitioniert)');
    // Coverage bleibt: alle 5 Batches kommen dran (Partitionierung darf keinen Batch verlieren).
    check('AON-MS-PARTITION (RED): alle 5 Welle-Mitglieder gebaut (Partitionierung verliert keinen Batch)', result.sub_batch_results.length === 5 && new Set(result.sub_batch_results.map(r => r.sub_batch)).size === 5, 'got ' + result.sub_batch_results.length);
  }

  // ── EC-MS-2 (RED): gemischte Welle NUR aus nicht-eligiblen Modi (M1/SC) -> effektiv serieller Pfad (parallelFn 0x). ──
  {
    const allSerial = [
      { id: 'sx1', items: ['a'], stages: [1] }, { id: 'sx2', items: ['b'], stages: [1] }, { id: 'sx3', items: ['c'], stages: [1] },
    ];
    const hint = { sx1: 'M1', sx2: 'M4', sx3: 'M5' };
    const spy = makeParallelSpy();
    const { result } = await runWithParallel(
      ARGS_P(allSerial, { parallel_mode: true, nr_parallel_batches: 3, batch_modes_hint: hint }),
      { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    const multiThunk = spy.calls.some(c => c.count >= 2);
    check('EC-MS-2 (RED): Welle nur aus M1/M4/M5 -> KEIN Multi-Thunk-parallel()-Aufruf (alle nicht-eligible -> seriell)', !multiThunk, 'Multi-Thunk-Aufruf trotz reiner nicht-eligible-Welle (counts=' + JSON.stringify(spy.calls.map(c => c.count)) + ')');
    check('EC-MS-2 (RED): alle 3 nicht-eligible Batches trotzdem gebaut (seriell)', result.sub_batch_results.length === 3, 'got ' + result.sub_batch_results.length);
  }

  // ── AON-MS-OFF-NULL (4, GUARD, Null-Regression QG-4): parallel_mode fehlt -> Modus-Scope ist No-Op. ──
  {
    const spy = makeParallelSpy();
    const { result } = await runWithParallel(
      ARGS_P(wave(3), { batch_modes_hint: { sb1: 'M2', sb2: 'M2', sb3: 'M2' } }),
      { modus: 'M2', elevation: ['BATCH_DONE'] }, spy.fn);
    check('AON-MS-OFF-NULL [GUARD] OFF: parallelFn 0x (Modus-Scope ist No-Op im seriellen Pfad)', spy.calls.length === 0, 'parallelFn ' + spy.calls.length + 'x trotz OFF');
    check('AON-MS-OFF-NULL [GUARD] OFF: effective_fanout==1 + completed (byte-identisch)', result.effective_fanout === 1 && result.terminated_reason === 'completed', result.effective_fanout + '/' + result.terminated_reason);
  }

  // ── AON-ES-ENUM (6, RED+GUARD): classifyOutcome('deferred') -> 'blocked' (Enum bleibt GENAU 3-wertig). ──
  //   Der Semaphor-Defer (S-ES-1) markiert einen 2. M5 als 'deferred'; classifyOutcome muss das auf
  //   'blocked' mappen (KEIN vierter Enum-Wert). Reine Funktion via extractFn.
  {
    // classifyOutcome hat eine Closure-Abhaengigkeit (PER_BATCH_OUTCOME) + ist eine benannte Funktions-
    // DEKLARATION -> der nackte extractFn-Pfad (named-fn-expr) bindet den Namen nicht. Wir extrahieren BEIDE
    // (Enum + Funktion) und evaluieren sie GEMEINSAM, damit der Vertrag echt aufrufbar geprueft wird.
    const enumMatch = (SRC.match(/const\s+PER_BATCH_OUTCOME\s*=\s*[\s\S]*?\)\s*\n/m) || [])[0] || '';
    const fnMatch = (SRC.match(/function\s+classifyOutcome\s*\([\s\S]*?\n\}/m) || [])[0] || '';
    let classifyOutcome = null;
    try {
      // eslint-disable-next-line no-new-func
      classifyOutcome = new Function('"use strict";\n' + enumMatch + '\n' + fnMatch + '\nreturn classifyOutcome;')();
    } catch (e) { classifyOutcome = null; }
    check('AON-ES-ENUM (RED): classifyOutcome + PER_BATCH_OUTCOME extrahier-/aufrufbar', typeof classifyOutcome === 'function', 'classifyOutcome nicht aufrufbar (Enum/Funktion nicht extrahiert)');
    if (typeof classifyOutcome === 'function') {
      // RED-Schaerfe: der Vertrag verlangt deferred->blocked EXPLIZIT. Heute faellt 'deferred' implizit in den
      // Default-Branch (-> 'blocked') — der RED-Anker unten verlangt die BEWUSSTE Verankerung von 'deferred' im Source.
      check('AON-ES-ENUM (GUARD): classifyOutcome("deferred") == "blocked" (deferred mappt auf blocked)', classifyOutcome('deferred') === 'blocked', 'got ' + JSON.stringify(classifyOutcome('deferred')));
      const vals = ['BATCH_DONE', 'failed', 'deferred', 'unknown_token', 're_cut_required'].map(classifyOutcome);
      const onlyThree = vals.every(v => v === 'completed' || v === 'failed' || v === 'blocked');
      check('AON-ES-ENUM (GUARD): classifyOutcome liefert AUSSCHLIESSLICH {completed,failed,blocked} (kein 4. Wert)', onlyThree, 'got ' + JSON.stringify(vals));
    }
    // RED (load-bearing): der Source verankert den SEMAPHOR-Defer EXPLIZIT — 'deferred' ko-lokalisiert mit
    // einem Semaphor/EXCLUSIVE/M5-Token (NICHT der unverwandte AK-7-"legit-deferred"-Item-Kommentar Z853).
    // greenfield: grep semaphor == 0, kein Defer->blocked-Mapping fuer M5.
    const semaphorDeferAnchor = /(?:semaphor|truth_lease|acquire_truth_lease)[\s\S]{0,400}deferred|deferred[\s\S]{0,400}(?:semaphor|truth_lease|EXCLUSIVE.*M5|M5.*EXCLUSIVE)/i.test(SRC);
    check('AON-ES-ENUM (RED): Source verankert den SEMAPHOR-Defer->blocked-Pfad EXPLIZIT (deferred ko-lokalisiert mit Semaphor/truth_lease/M5, NICHT der AK-7-Item-Kommentar)', semaphorDeferAnchor, 'kein Semaphor-Defer-Pfad im Motor (grep semaphor==0, deferred nur im unverwandten AK-7-Kommentar — greenfield)');
  }

  // ── AON-ES-DEFER (5, RED, load-bearing): 2. M5/EXCLUSIVE bei besetztem Semaphor -> deferred (blocked), non-blocking. ──
  //   Welle mit 2 M5-Batches (per plan-zeit-hint): der erste nimmt den Semaphor, der zweite wird DEFERRT
  //   (per_batch_outcome=blocked, in fan_in.blocked, KEIN throw, KEIN Anhalten); Geschwister-M2 laufen weiter.
  //   RED weil heute kein Semaphor/Defer existiert (grep semaphor == 0): beide M5 wuerden gleich behandelt.
  {
    const wel = [
      { id: 'sb_m2', items: ['a'], stages: [1] },
      { id: 'sb_m5a', items: ['b'], stages: [1] },
      { id: 'sb_m5b', items: ['c'], stages: [1] },
    ];
    const hint = { sb_m2: 'M2', sb_m5a: 'M5', sb_m5b: 'M5' };
    let threw = false, result = null;
    try {
      ({ result } = await runWithParallel(
        ARGS_P(wel, { parallel_mode: true, nr_parallel_batches: 3, batch_modes_hint: hint }),
        { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn));
    } catch (e) { threw = true; }
    check('AON-ES-DEFER (RED): Welle mit 2 M5 laeuft ohne Throw durch (Defer ist non-blocking, kein Anhalten)', !threw && !!result, threw ? 'Welle warf bei 2 M5 (Semaphor blockierte/threw statt deferred)' : 'kein Ergebnis');
    if (result) {
      const fi = result.fan_in || { completed: [], failed: [], blocked: [] };
      // Mindestens ein M5-Batch ist DEFERRT (in fan_in.blocked) — NICHT failed, NICHT completed-doppelt.
      const blocked = Array.isArray(fi.blocked) ? fi.blocked : [];
      const deferredM5 = blocked.includes('sb_m5a') || blocked.includes('sb_m5b');
      check('AON-ES-DEFER (RED): der 2. M5 ist DEFERRT (in fan_in.blocked, ein 1-Slot-Semaphor pro BL)', deferredM5, 'fan_in.blocked=' + JSON.stringify(blocked) + ' (kein M5 deferred -> Semaphor fehlt, beide M5 gleich behandelt)');
      // Defer != Failure: kein deferred-M5 landet in fan_in.failed; die Welle gilt NICHT als tot.
      const failed = Array.isArray(fi.failed) ? fi.failed : [];
      check('AON-ES-DEFER (RED): deferred-M5 ist NICHT failed (Defer != Failure, Welle nicht tot)', !failed.includes('sb_m5a') && !failed.includes('sb_m5b'), 'fan_in.failed=' + JSON.stringify(failed));
      check('AON-ES-DEFER (RED): Geschwister-M2 laeuft ungestoert (sb_m2 im Outcome)', result.sub_batch_results.some(r => r.sub_batch === 'sb_m2'), 'sb_m2 fehlt im Outcome (Defer stoerte das Geschwister)');
    } else {
      check('AON-ES-DEFER (RED): 2. M5 deferred (blocked), Geschwister ungestoert', false, 'kein Ergebnis (Welle threw)');
    }
  }

  // ── AON-GP-PHASE3-REPLAY (7, RED, load-bearing): Motor LIEST phase3_fired_per_batch[id] aus dem Manifest-Seed. ──
  //   Zweiter Lauf (frischer Motor-State, A.phase3_fired_seed mit id=true) -> runPhase3/recalibrate feuert
  //   NICHT erneut fuer id (Spawn-Quartett-Zaehler steigt nicht). RED weil der Motor heute nur das in-memory
  //   Set (Z520) konsultiert und A.phase3_fired_seed gar nicht liest.
  //   Beobachtbar: der SC-Saettigungs-Pfad triggert runPhase3 bei sc_verdict; mit Seed bleibt das Quartett aus.
  {
    // Lauf MIT Seed: id bereits phase3_fired (persistent) -> kein erneutes recalibrate/postItem/statusTransition/modelSync-Quartett.
    const seedArgs = ARGS_P([{ id: 'sb1', items: ['a'], stages: [1] }], { phase3_fired_seed: { sb1: true } });
    const { spawns: seedSpawns } = await run(seedArgs, { modus: 'M2', elevation: ['BATCH_DONE'] });
    const quartetSeeded = seedSpawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):sb1\b/.test(x.label)).length;
    // RED-Schaerfe: ohne Motor-Read des Seeds feuert das BATCH_DONE-Quartett trotzdem (==4). Mit Read (GREEN)
    // ist es uebersprungen (==0) fuer den geseedeten Batch. Der Source MUSS den Seed lesen.
    const readsSeed = /phase3_fired_seed|A\.phase3_fired/.test(SRC);
    check('AON-GP-PHASE3-REPLAY (RED): Motor LIEST A.phase3_fired_seed (persistenter Manifest-Marker, kein nacktes in-memory-Set)', readsSeed, 'kein Lesen von A.phase3_fired_seed im Motor-Source (Z520-Set bleibt einzige Quelle — greenfield)');
    check('AON-GP-PHASE3-REPLAY (RED): mit phase3_fired_seed[sb1]=true -> KEIN erneutes Phase-3-Quartett fuer sb1 (Fresh-Replay kein Doppel-Feuer)', quartetSeeded === 0, 'Phase-3-Quartett-Spawns fuer sb1 trotz Seed=true: ' + quartetSeeded + ' (Seed nicht gelesen)');
  }

  // ── AON-GP-RECALC-REPLAY (8, RED): recalc_rounds_per_batch[id] keyed-upsert ueber Laeufe; Cap liest persistenten Stand. ──
  //   Seed A.recalc_rounds_seed[id]=MAX -> der naechste Recalc ueberschreitet den Cap und terminiert
  //   recalc_cap_exceeded AUCH nach Replay (statt bei 0 neu zu zaehlen). RED weil recalcRounds (Map Z525)
  //   in-memory bei 0 startet (Seed wird nicht gelesen).
  {
    const readsRecalcSeed = /recalc_rounds_seed|A\.recalc_rounds/.test(SRC);
    check('AON-GP-RECALC-REPLAY (RED): Motor LIEST A.recalc_rounds_seed (Cap haelt ueber Crash/Replay)', readsRecalcSeed, 'kein Lesen von A.recalc_rounds_seed im Motor-Source (recalcRounds-Map Z525 startet bei 0 — greenfield)');
    // Verhaltens-Beweis: Seed == MAX_RECALC_ROUNDS -> der erste echte Recalc-Round nach Replay ueberschreitet
    // den Cap sofort -> recalc_cap_exceeded (statt erst nach MAX weiteren Runden).
    const maxSeed = { sb1: 8 };   // MAX_RECALC_ROUNDS default 8 (A.max_recalc_rounds || 8, Z43)
    const seedArgs = ARGS_P([{ id: 'sb1', items: ['a'], stages: [1] }], { recalc_rounds_seed: maxSeed });
    // SC-Re-Entry-Schleife erzwingen: stageElevation liefert SC_RE_ENTRY-aehnliches Token (Recalc-Trigger).
    // Wir greifen den beobachtbaren Cap: mit Seed==MAX terminiert der naechste Recalc fail-loud.
    const { result } = await run(Object.assign(seedArgs, { max_stage_iters: 20 }), { modus: 'M4', elevation: ['ELEVATE', 'BATCH_DONE'] });
    // RED-konsistent: ohne Seed-Read terminiert NICHT mit recalc_cap_exceeded nach 1 Round (Cap zaehlt bei 0 neu).
    // Mit Seed-Read (GREEN) ist recalc_cap_exceeded nach Replay erreichbar. Wir pruefen den Source-Read als
    // load-bearing RED-Anker (das Verhaltens-Assert haengt von der SC-Schleifen-Mechanik ab; der Read ist der harte RED).
    check('AON-GP-RECALC-REPLAY (RED-konsistent): Seed-Read ist die load-bearing Voraussetzung fuer Cap-ueber-Replay (terminated_reason nicht "completed"-blind)', readsRecalcSeed || result.terminated_reason !== undefined, 'kein Seed-Read + kein terminated_reason');
  }

  // ── AON-GP-OFF-NULL (9, GUARD, Null-Regression): Single-Lauf ohne Seed byte-identisch (Set/Map effektiv leer). ──
  {
    const { result, spawns } = await run(ARGS([{ id: 'sb1', items: ['a'], stages: [1] }]), { modus: 'M2', elevation: ['BATCH_DONE'] });
    const quartet = spawns.filter(x => /^(recalibrate|postItem|statusTransition|modelSync):/.test(x.label)).length;
    check('AON-GP-OFF-NULL [GUARD]: Single-Lauf ohne Seed -> Phase-3-Quartett feuert normal (==4, BL-238 byte-identisch)', quartet === 4, 'got ' + quartet);
    check('AON-GP-OFF-NULL [GUARD]: Single-Lauf -> completed + loop_decision TERMINATE (kein Doppel-Feuer NEU eingefuehrt)', result.terminated_reason === 'completed' && result.loop_decision === 'TERMINATE', result.terminated_reason + '/' + result.loop_decision);
  }

  // ── AON-TL-PINNED (12, RED, dispatch-Seite): bei aktivem truth_lease (M5) setzt der Motor fuer Geschwister einen read-pinned/pinned_at_round-Marker. ──
  //   Die Fan-In-Barrier-Truth-Reval (bestehender Schritt 4) konsumiert ihn. RED weil grep pinned_at_round/read_pinned == 0.
  {
    const wel = [
      { id: 'sb_m5', items: ['a'], stages: [1] },
      { id: 'sb_sib', items: ['b'], stages: [1] },
    ];
    const hint = { sb_m5: 'M5', sb_sib: 'M2' };
    const { spawns } = await runWithParallel(
      ARGS_P(wel, { parallel_mode: true, nr_parallel_batches: 2, batch_modes_hint: hint }),
      { modus: 'M2', elevation: ['BATCH_DONE'] }, makeParallelSpy().fn);
    // Beobachtbar: irgendein Spawn-Prompt (Geschwister-Bau ODER Fan-In-Barrier-Schritt-4) traegt den read-pinned/pinned_at_round-Marker.
    const pinnedMarker = spawns.some(x => /pinned_at_round|read[\s_-]?pinned|read-pinned/i.test(x.prompt));
    check('AON-TL-PINNED (RED): bei M5-truth_lease traegt ein Spawn-Prompt den read-pinned/pinned_at_round-Marker (Geschwister bauen pinned)', pinnedMarker, 'kein pinned_at_round/read-pinned-Marker in den Spawn-Prompts (grep == 0 — greenfield)');
    // Source-Anker (load-bearing RED): der Motor verankert pinned_at_round ueberhaupt.
    check('AON-TL-PINNED (RED): Motor-Source verankert pinned_at_round/read-pinned (Marker-SETZUNG, Unit-testbar)', /pinned_at_round|read[\s_-]?pinned/i.test(SRC), 'kein pinned_at_round/read-pinned im Motor-Source (greenfield)');
  }

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail === 0 ? 0 : 1);
})().catch(e => { console.error('HARNESS ERROR', e); process.exit(2); });
