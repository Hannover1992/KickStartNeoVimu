export const meta = {
  name: 'dispatch_model_drift',
  description: 'BL-236 MVP: deterministischer Model-Drift-Motor (AK-1/2/3). Parst Model-W-Knoten mit Code-Ankern (Datei:Zeile aus _W_fetch) -> verifiziert pro Knoten den Claim gegen current develop-Code -> truth_grade {code_verified|vault_hypothesis|code_contradicted}. Erweitert _model-finish Phase-2.5 (Datei-EXISTENZ -> WERT-Drift, code>vault). 1-Step=1-agent + harte Caps => Mega-Worker strukturell unmoeglich.',
  phases: [
    { title: 'Parse', detail: 'verankerte W-Knoten aus dem Model extrahieren' },
    { title: 'Verify', detail: 'pro Knoten: Code am Anker lesen -> truth_grade + Drift' },
    { title: 'Report', detail: 'Drift-Bilanz + code_contradicted-Liste' },
  ],
}

// ── BL-228 F-MOTOR-ARGS-Lehre: args kommt als JSON-STRING, nicht Objekt ──
let A = (typeof args !== 'undefined' && args) ? args : {}
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
const BL_ID = A.bl_id || A.BL_ID || 'UNKNOWN'
const MODEL_PATH = A.model_path || A.model || null
const VERIFY_CAP = Number.isInteger(A.verify_cap) ? A.verify_cap : 60   // Sicherheits-Cap Knoten-Anzahl

if (!MODEL_PATH) {
  log('[dispatch_model_drift] WARN: kein model_path -> No-Op (lautes Signal, kein stiller Erfolg).')
  return { bl_id: BL_ID, truth_graded: [], drift_count: 0, terminated_reason: 'no_model_path' }
}

const PARSE_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    anchored_knots: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      w_id: { type: 'string' },
      claim: { type: 'string', description: 'die zu pruefende Model-Aussage (1 Satz)' },
      file: { type: 'string', description: 'Code-Anker Datei (relativ zum Repo)' },
      line_start: { type: 'integer' },
      line_end: { type: 'integer' },
      prior_grade: { type: 'string', description: 'bestehender verifikation_status falls vorhanden (BESTAETIGT/REFUTED/...)' },
    }, required: ['w_id', 'claim', 'file'] } },
    unanchored_count: { type: 'integer', description: 'W-Knoten OHNE Code-Anker (=> vault_hypothesis-Kandidaten)' },
  }, required: ['anchored_knots', 'unanchored_count'],
}

const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    w_id: { type: 'string' },
    truth_grade: { type: 'string', enum: ['code_verified', 'vault_hypothesis', 'code_contradicted'] },
    evidence: { type: 'string', description: 'Datei:Zeile + was der Code real sagt' },
    drift_detail: { type: 'string', description: 'bei code_contradicted: wie weicht Claim vom Code ab (z.B. Enum 6->1)' },
  }, required: ['w_id', 'truth_grade', 'evidence'],
}

// ── Phase Parse (AK-3: Anker als Drift-Check-Punkt) ──
phase('Parse')
const parsed = await agent(
  `BL-236 Drift-Parse fuer ${BL_ID}. LIES das Model: ${MODEL_PATH}.\n`
  + `Extrahiere ALLE W-Knoten, die einen Code-Anker tragen (source_node / EDGES-PFLICHT Datei:Zeile, vom _W_fetch). `
  + `Pro Knoten: w_id, claim (die pruefbare 1-Satz-Aussage), file, line_start, ggf line_end, prior_grade (bestehender verifikation_status). `
  + `unanchored_count = Anzahl W-Knoten OHNE Code-Anker (das sind vault_hypothesis per Definition, AK-1).`,
  { label: `parse:${BL_ID}`, phase: 'Parse', schema: PARSE_SCHEMA, model: 'opus' },
)
const knots = (parsed && parsed.anchored_knots) ? parsed.anchored_knots.slice(0, VERIFY_CAP) : []
log(`[dispatch_model_drift] ${knots.length} verankerte Knoten (+${parsed && parsed.unanchored_count} unverankert=vault_hypothesis).`)

// ── Phase Verify (AK-2: Wert-Drift Code>Vault, pro Knoten 1 agent = kein Mega-Worker) ──
phase('Verify')
const verified = await pipeline(
  knots,
  (k) => agent(
    `BL-236 Drift-Verify Knoten ${k.w_id} (${BL_ID}).\n`
    + `MODEL-CLAIM: "${k.claim}"\n`
    + `CODE-ANKER: ${k.file}:${k.line_start || '?'}${k.line_end ? '-' + k.line_end : ''}.\n`
    + `LIES den AKTUELLEN Code an diesem Anker (Read/Grep gegen develop-HEAD). ENTSCHEIDE truth_grade (AK-1, code>vault):\n`
    + `- code_verified: der Code BESTAETIGT den Claim (Wert/Verhalten stimmt ueberein).\n`
    + `- code_contradicted: der Code WIDERSPRICHT dem Claim (Wert-Drift, z.B. Claim sagt Enum hat 6 Werte, Code hat 1) -> drift_detail PFLICHT.\n`
    + `- vault_hypothesis: der Anker existiert nicht mehr / Code unentscheidbar -> Claim ist unbestaetigte Vault-Annahme.\n`
    + `evidence = Datei:Zeile + was der Code REAL sagt. Code gewinnt gegen Vault (die abgenommene Wahrheit ist der Code).`,
    { label: `verify:${k.w_id}`, phase: 'Verify', schema: VERIFY_SCHEMA, model: 'opus' },
  ),
)

phase('Report')
const graded = verified.filter(Boolean)
const contradicted = graded.filter((g) => g.truth_grade === 'code_contradicted')
const hypothesis = graded.filter((g) => g.truth_grade === 'vault_hypothesis')
log(`[dispatch_model_drift] DONE ${BL_ID}: ${graded.length} geprueft -> `
  + `${graded.filter((g) => g.truth_grade === 'code_verified').length} code_verified, `
  + `${contradicted.length} code_contradicted (DRIFT!), ${hypothesis.length} vault_hypothesis.`)

return {
  bl_id: BL_ID,
  model_path: MODEL_PATH,
  truth_graded: graded,
  drift_count: contradicted.length,
  drifted: contradicted,
  hypotheses: hypothesis,
  unanchored_count: (parsed && parsed.unanchored_count) || 0,
  terminated_reason: 'verified',
}
