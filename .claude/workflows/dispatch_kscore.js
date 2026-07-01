export const meta = {
  name: 'dispatch_kscore',
  description: 'K-Score v3 Dispatch-Motor (BL-311 batch_3): deterministischer JS-Workflow fuer mehrstufige K-Score-Berechnung. '
    + 'Stage 0 PLAN (walker_plan[] via safeSchemaAgent) -> Stage 1 WALKERS (N Items -> N agent(), parallel(), read-only) -> '
    + 'Barrier -> Stage 2 TOPOLOGY (kscore_v3_topology.py) -> Stage 3 SCORING (kscore_v3_scoring.py) -> Stage 4 PERSIST (kscore_v3_persist.py). '
    + 'AK-15 Solo-Pfad-Weiche: bei item_count < n_schwelle UND kein k_verdacht -> frueh return {terminated_reason: \'solo_path_2.0\'}. '
    + 'INV-MOTOR-1-analog: 1 Stage = 1 agent(). Mega-Walker strukturell unmoeglich.',
  phases: [
    { title: 'Plan' },
    { title: 'Walkers' },
    { title: 'Topology' },
    { title: 'Scoring' },
    { title: 'Persist' },
  ],
}

// ===========================================================================
// ARGS (vom Lead/Pre-SDF uebergeben — Workflow-Skript hat KEINEN FS-Zugriff,
// daher reicht Caller alle Pfade + PL-Items herein):
//   {
//     bl_id,         // BL-ID
//     name,          // Feature-Name
//     vault,         // Vault-Root-Pfad
//     working_dir,   // BL-Folder-Pfad
//     pl_items,      // array[{id, title, ziel_symbole, ziel_dateien, pl_draft_text}]
//     n_schwelle,    // AK-15 Solo-Pfad-Weiche (Default: 3)
//     k_verdacht,    // AK-15 Solo-Pfad-Weiche (Default: false)
//     session_params // weights, OP_MULT-Overrides, PATTERN_DISCOUNT-Overrides (BL-273, optional)
//   }
// RETURN: { walker_outputs, topology, scores, persist_path, terminated_reason, agent_spawns }
// ===========================================================================
let A = (typeof args !== 'undefined' && args) ? args : {}
// Defensive (BL-228-Lehre): manche Caller reichen args als JSON-STRING statt
// Objekt (Workflow-Tool-Stringify-Falle) -> A.pl_items waere undefined.
// Parse defensiv, damit der Motor sowohl Objekt- als auch String-args akzeptiert.
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
const BL = A.bl_id || A.name || '<bl>'
const NAME = A.name || A.bl_id || '<name>'
const VAULT = A.vault || ''
const WD = A.working_dir || A.vault || ''
const PL_ITEMS = Array.isArray(A.pl_items) ? A.pl_items : []
const N_SCHWELLE = (typeof A.n_schwelle === 'number') ? A.n_schwelle : 3
const K_VERDACHT = A.k_verdacht === true || A.k_verdacht === 'true'
const SESSION_PARAMS = A.session_params || {}

const CTX = `BL=${BL} name=${NAME} vault=${VAULT} working_dir=${WD}`
const PATHS = `Vault-Root=${VAULT}  Per-BL-Folder=${WD}  (IMMER absolute Pfade, NIE das Literal "bl_folder")`
const SCRIPTS = `${VAULT ? VAULT + '/' : ''}OmniCommand/scripts`

// ===========================================================================
// AK-15: Solo-Pfad-Weiche (VOR Stage 0) — frueh return wenn kein v3-Full noetig.
// should_use_v3_full(item_count, k_verdacht, n_schwelle) aus kscore_v3_persist.py.
// ===========================================================================
const use_v3_full = K_VERDACHT || (PL_ITEMS.length >= N_SCHWELLE)
if (!use_v3_full) {
  log(`[dispatch_kscore] Solo-Pfad (Schema 2.0) — item_count=${PL_ITEMS.length} < n_schwelle=${N_SCHWELLE}, kein k_verdacht`)
  log(`[dispatch_kscore] Trickle: _K_score.md Solo-Pfad nutzen (kein v3-Full-Workflow noetig)`)
  return {
    walker_outputs: [],
    topology: null,
    scores: null,
    persist_path: null,
    terminated_reason: 'solo_path_2.0',
    agent_spawns: 0,
    note: 'Trickle: _K_score.md Solo-Pfad nutzen',
  }
}

log(`[dispatch_kscore] START — ${BL} | item_count=${PL_ITEMS.length} | v3_full=true (k_verdacht=${K_VERDACHT}, n_schwelle=${N_SCHWELLE})`)

// ===========================================================================
// safeSchemaAgent — Schema-erzwungene Calls mit Fallback (BL-228 F-MOTOR-SCHEMA-CRASH-FATAL)
// ===========================================================================
function extractJson(text) {
  if (!text) return null
  const m = String(text).match(/\{[\s\S]*\}/)
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
    log(`[dispatch_kscore] WARN schema-agent ${opts.label} crashed (${String(e && e.message || e).slice(0, 90)}) — schemaloser Retry (F-MOTOR-SCHEMA-CRASH Haertung)`)
    const keys = Object.keys(schemaObj.properties || {}).join(', ')
    const raw = await agent(
      prompt + `\n\nWICHTIG: Gib AUSSCHLIESSLICH ein einziges valides JSON-Objekt zurueck mit den Feldern {${keys}}. KEIN Fliesstext, KEIN Markdown, KEINE Code-Fences — nur das rohe JSON.`,
      opts
    )
    if (isSessionLimit(raw)) {
      throw new Error('SESSION_LIMIT: Plan-Agent traf das Account-/Session-Limit. Motor pausiert GRACEFUL — spaeter resumen.')
    }
    const parsed = extractJson(raw)
    if (parsed) { log(`[dispatch_kscore] schemaloser Retry OK fuer ${opts.label}`); return parsed }
    log(`[dispatch_kscore] WARN ${opts.label}: Retry-Parse fehlgeschlagen -> sicherer Fallback ${JSON.stringify(fallback)}`)
    return fallback
  }
}

// ===========================================================================
// PLAN_SCHEMA — Stage 0 Output-Struktur (strukturiert, Fehler-sicher downstream)
// ===========================================================================
const PLAN_SCHEMA = {
  type: 'object',
  properties: {
    walker_plan: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          item_id:       { type: 'string' },
          title:         { type: 'string' },
          ziel_symbole:  { type: 'array', items: { type: 'string' } },
          ziel_dateien:  { type: 'array', items: { type: 'string' } },
          pl_draft_text: { type: 'string' },
        },
        required: ['item_id', 'ziel_symbole', 'ziel_dateien'],
      },
    },
    item_count: { type: 'integer' },
  },
  required: ['walker_plan', 'item_count'],
}

// ===========================================================================
// walkerPrompt — Read-only-Prompt fuer 1 Item = 1 Walker (AK-3, read-only-Disziplin)
// ===========================================================================
function walkerPrompt(item) {
  return `Du bist ein read-only K-Score-v3-Walker fuer Item "${item.item_id}" (${item.title || ''}).
STRIKT READ-ONLY: kein Write, kein Edit, kein File-Create. Nur lesen + ableiten.
Kontext: ${CTX}
Pfade: ${PATHS}
Ziel-Symbole: ${JSON.stringify(item.ziel_symbole || [])}.
Ziel-Dateien: ${JSON.stringify(item.ziel_dateien || [])}.

Erhebe den Rohdaten-Vektor (Achsen 1-6) fuer item_id="${item.item_id}":
- Achse 1 (Scope/Groesse): LOC, zyklomatik, kognitiv, datei_anzahl, layer_anzahl
  (Script via kscore_v3_axes.axis1_scope — rufe Python-Script auf ODER schaetze mit Marker source="heuristik")
- Achse 2 (Operation-Typ): klassifiziere ADD/EXTEND/MODIFY/DELETE/MOVE aus pl_draft_text + Code-Kontext.
  Wende OP_MULT an (aus kscore_v3_axes.OP_MULT). Evidence PFLICHT.
- Achse 3 (Kopplung): Ca/Ce/Instability, fan_in, call_tiefe, cross_layer (LSP-bevorzugt, INV-K2).
  Bei lsp_available=false: evidence MUSS "[LSP-MISS]" tragen.
- Achse 4 (Kohaesion/SRP): srp_defizit, lcom (via kscore_v3_axes.axis4_cohesion).
- Achse 5 (OCP): ocp_vorhanden, erweiterungspunkte (via kscore_v3_axes.axis5_ocp).
- Achse 6 (Lokalitaet): streuung_klasse, streuung_faktor (via kscore_v3_axes.axis6_locality).

pl_draft_text: ${item.pl_draft_text || '(kein draft_text vorhanden)'}

OUTPUT: Gib AUSSCHLIESSLICH ein JSON-Objekt zurueck:
{
  "item_id": "${item.item_id}",
  "dateien": [...],
  "symbole": [...],
  "achse1_scope": {...},
  "achse2_operation": {...},
  "achse3_coupling": {...},
  "achse4_cohesion": {...},
  "achse5_ocp": {...},
  "achse6_locality": {...},
  "evidence_per_axis": "..."
}
INV-MOTOR-1-analog: STIRBST nach diesem einen Walker-Schritt. KEINE Folge-Spawns.`
}

// ===========================================================================
// MAIN — FLAT-SEQUENCE: Stage 0 -> parallel(Stage 1) -> Barrier -> 2 -> 3 -> 4
// ===========================================================================
let agent_spawns = 0

// ── Stage 0 PLAN ────────────────────────────────────────────────────────────
log(`[dispatch_kscore] Stage 0 PLAN — erzeuge walker_plan[] fuer ${PL_ITEMS.length} Items`)
const planPrompt = `Du bist der K-Score-v3-Planer fuer ${BL}.
Kontext: ${CTX}
Pfade: ${PATHS}
PL-Items (${PL_ITEMS.length} Stueck): ${JSON.stringify(PL_ITEMS)}

Aufgabe: Erstelle einen walker_plan[] — einen Eintrag PRO PL-Item.
Fuelle je Item: item_id, title, ziel_symbole (Symbole/Klassen die analysiert werden sollen),
ziel_dateien (Dateipfade die relevant sind), pl_draft_text (Kurzfassung des Aenderungsvorhabens).
Fehlende Felder aus pl_draft_text + Kontext ableiten.

Gib AUSSCHLIESSLICH das JSON-Objekt mit walker_plan[] und item_count zurueck.`

const planResult = await safeSchemaAgent(
  planPrompt,
  { label: 'stage0:plan', phase: 'Plan', model: 'sonnet' },
  PLAN_SCHEMA,
  { walker_plan: [], item_count: 0 }
)
agent_spawns += 1

const walker_plan = Array.isArray(planResult && planResult.walker_plan) ? planResult.walker_plan : []

// Fehler-Guard: kein walker_plan -> frueh return
if (!walker_plan || walker_plan.length === 0) {
  log(`[dispatch_kscore] WARN Stage 0: leerer walker_plan (item_count=0) -> terminated_reason=no_walker_plan`)
  return {
    walker_outputs: [],
    topology: null,
    scores: null,
    persist_path: null,
    terminated_reason: 'no_walker_plan',
    agent_spawns,
  }
}
log(`[dispatch_kscore] Stage 0 DONE — walker_plan.length=${walker_plan.length}`)

// ── Stage 1 WALKERS (parallel, read-only) ───────────────────────────────────
log(`[dispatch_kscore] Stage 1 WALKERS — ${walker_plan.length} Items -> ${walker_plan.length} agent()-Calls (parallel, read-only)`)
const walker_outputs_raw = await parallel(
  walker_plan.map(item =>
    agent(walkerPrompt(item), { label: `walker:${item.item_id}`, phase: 'Walkers', model: 'sonnet' })
  )
)
agent_spawns += walker_plan.length

// Barrier: alle Walker-Outputs gesammelt. Parse JSON aus jedem Walker-Return.
const walker_outputs = walker_outputs_raw.map((raw, idx) => {
  const parsed = extractJson(String(raw || ''))
  if (parsed) return parsed
  // Fallback: Rohtext mit item_id aus Plan
  log(`[dispatch_kscore] WARN Walker ${walker_plan[idx] && walker_plan[idx].item_id}: JSON-Parse fehlgeschlagen — Rohtext als Fallback`)
  return { item_id: (walker_plan[idx] && walker_plan[idx].item_id) || `item_${idx}`, _raw: String(raw || '').slice(0, 500) }
})
log(`[dispatch_kscore] Stage 1 DONE (Barrier) — ${walker_outputs.length} Walker-Outputs gesammelt`)

// ── Stage 2 TOPOLOGY ────────────────────────────────────────────────────────
log(`[dispatch_kscore] Stage 2 TOPOLOGY — kscore_v3_topology.py`)
const walker_outputs_clean = walker_outputs.filter(w => w && !w._raw)
const topology_raw = await agent(
  `Kontext: ${CTX}
Pfade: ${PATHS}

Fuehre Stage 2 Topologie-Analyse aus. Rufe kscore_v3_topology.build_overlap_graph + contention_per_item auf:

  py -3 -c "import json,sys; sys.path.insert(0, '${WD}'.replace('/Backlog/', '/scripts/').replace('\\\\Backlog\\\\', '\\\\scripts\\\\')); ` +
  `from kscore_v3_topology import build_overlap_graph, contention_per_item; ` +
  `wo=json.loads(sys.argv[1]); ` +
  `print(json.dumps({'graph': build_overlap_graph(wo), 'contention': contention_per_item(wo)}))" ` +
  `'${JSON.stringify(walker_outputs_clean).replace(/'/g, "'\\''")}'

Alternativ: Importiere direkt aus .claude/scripts/kscore_v3_topology.py (py -3 .claude/scripts/kscore_v3_topology.py).
Die walker_outputs sind: ${JSON.stringify(walker_outputs_clean)}

Gib das JSON-Resultat zurueck: {"graph": {...}, "contention": {...}}`,
  { label: 'stage2:topology', phase: 'Topology', model: 'sonnet' }
)
agent_spawns += 1
const topology = extractJson(String(topology_raw || '')) || { graph: {}, contention: {} }
log(`[dispatch_kscore] Stage 2 DONE — topology.graph keys=${Object.keys(topology.graph || {}).length}`)

// ── Stage 3 SCORING ─────────────────────────────────────────────────────────
log(`[dispatch_kscore] Stage 3 SCORING — kscore_v3_scoring.py`)
const scores_raw = await agent(
  `Kontext: ${CTX}
Pfade: ${PATHS}

Fuehre Stage 3 Scoring aus. Rufe kscore_v3_scoring.score_item + aggregate auf:

Fuer jedes Item in walker_outputs: score_item(achse1, achse2, achse3, achse4, achse5, achse6, contention_score, pattern_status, truth_grade, weights?)
Dann aggregate(scored_items) fuer den Batch-Gesamtscore.

Script-Pfad: .claude/scripts/kscore_v3_scoring.py
  py -3 -c "import json,sys; from kscore_v3_scoring import score_item, aggregate; ..."

Walker-Outputs: ${JSON.stringify(walker_outputs_clean)}
Contention (aus Stage 2): ${JSON.stringify(topology.contention || {})}
Session-Params (weights/Overrides): ${JSON.stringify(SESSION_PARAMS)}

Gib das JSON-Resultat zurueck: {"scored_items": [...], "aggregate": {...}}`,
  { label: 'stage3:scoring', phase: 'Scoring', model: 'sonnet' }
)
agent_spawns += 1
const scores = extractJson(String(scores_raw || '')) || { scored_items: [], aggregate: {} }
log(`[dispatch_kscore] Stage 3 DONE — scored_items=${Array.isArray(scores.scored_items) ? scores.scored_items.length : 0}`)

// ── Stage 4 PERSIST ─────────────────────────────────────────────────────────
log(`[dispatch_kscore] Stage 4 PERSIST — kscore_v3_persist.py`)
const persist_raw = await agent(
  `Kontext: ${CTX}
Pfade: ${PATHS}

Fuehre Stage 4 Persistierung aus. Rufe kscore_v3_persist.write_schema_3 auf:

  py -3 -c "import json,sys; from kscore_v3_persist import write_schema_3; ..."

Input fuer write_schema_3:
- bl_id: "${BL}"
- working_dir: "${WD}"
- walker_outputs: ${JSON.stringify(walker_outputs_clean)}
- topology: ${JSON.stringify(topology)}
- scores: ${JSON.stringify(scores)}
- session_params: ${JSON.stringify(SESSION_PARAMS)}

Script-Pfad: .claude/scripts/kscore_v3_persist.py
Schreibe das Schema-3-Dokument in den BL-Folder (${WD}).

Gib zurueck: {"persist_path": "<absoluter Pfad zur geschriebenen Datei>", "status": "ok"}`,
  { label: 'stage4:persist', phase: 'Persist', model: 'sonnet' }
)
agent_spawns += 1
const persist_result = extractJson(String(persist_raw || '')) || { persist_path: null, status: 'unknown' }
const persist_path = persist_result.persist_path || null
log(`[dispatch_kscore] Stage 4 DONE — persist_path=${persist_path}`)

// ── RETURN ───────────────────────────────────────────────────────────────────
log(`[dispatch_kscore] COMPLETE — BL=${BL} | walker_outputs=${walker_outputs.length} | agent_spawns=${agent_spawns}`)
return {
  walker_outputs,
  topology,
  scores,
  persist_path,
  terminated_reason: 'completed',
  agent_spawns,
}
