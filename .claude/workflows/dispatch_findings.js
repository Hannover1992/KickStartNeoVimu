export const meta = {
  name: 'dispatch_findings',
  description: 'BL-235 Asymptotic Findings Engine: deterministischer Findings-Motor. Loop-until-dry Extraktion (cap) -> semantisches Clustering (CORE/BORDER) -> Timeline-Gewicht -> Valenz/Pruning -> CORE-Destillat + BORDER-Anhang fuer Checkpoint A. Ersetzt die 1-Pass+dedup-0.85-Logik in _A_berater_findingsExtraction. 1-Step=1-agent + harte Caps => Mega-Worker strukturell unmoeglich (BL-222/FIX2-Lehre; AK-8 als Workflow NICHT in-Skill-Pseudocode).',
  phases: [
    { title: 'Extract', detail: 'asymptotische Runden bis DeltaCORE==0 (Hard-Cap)' },
    { title: 'Cluster', detail: 'cleancoder-Embedding -> Dichte -> CORE/BORDER' },
    { title: 'WeightPrune', detail: 'Timeline-Gewicht + Valenz-Matrix (K^2) + Pruning' },
    { title: 'Synthesize', detail: 'CORE-Destillat oben / BORDER-Anhang' },
  ],
}

// ── BL-228 F-MOTOR-ARGS-Lehre: das Workflow-Tool reicht args als JSON-STRING, nicht Objekt ──
let A = (typeof args !== 'undefined' && args) ? args : {}
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { A = {} } }
const BL_ID = A.bl_id || A.BL_ID || 'UNKNOWN'
const PILE_FILES = Array.isArray(A.pile_files) ? A.pile_files : []
const EXTRACT_CAP = Number.isInteger(A.extract_cap) ? A.extract_cap : 3   // OQ-5 Hard-Cap 3
const COSINE_THRESHOLD = typeof A.cosine_threshold === 'number' ? A.cosine_threshold : 0.78  // OQ-2

if (PILE_FILES.length === 0) {
  log('[dispatch_findings] WARN: keine pile_files -> No-Op (kein stiller Erfolg, lautes Signal).')
  return { findings_core: [], findings_border: [], terminated_reason: 'no_pile_files', rounds: 0 }
}

const EXTRACT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    findings: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      text: { type: 'string' },
      type: { type: 'string', enum: ['observation', 'hypothesis', 'burden', 'requirement', 'constraint', 'other'] },
      source: { type: 'string' }, line_start: { type: 'integer' },
      timeline_pos: { type: 'integer', description: 'globaler Pile-Sequenz-Index (OQ-4)' },
      user_emphasis: { type: 'boolean', description: 'AK-12: explizit betont (UNBEDINGT/...) -> CORE-Pin' },
    }, required: ['text', 'type', 'source', 'timeline_pos'] } },
    new_core_count: { type: 'integer', description: 'wie viele NEUE CORE-Kandidaten ggu. schon_gefunden' },
  }, required: ['findings', 'new_core_count'],
}

// ── Phase Extract: asymptotische Schleife (AK-1), Seed=Marker-Heuristik (OQ-5), Stop bei DeltaCORE==0 ──
phase('Extract')
let all = []
let rounds = 0
for (let r = 1; r <= EXTRACT_CAP; r++) {
  rounds = r
  const seen = all.map((f) => f.text)
  const res = await agent(
    `BL-235 Findings-Extraktion Runde ${r}/${EXTRACT_CAP} fuer ${BL_ID}.\n`
    + `LIES die Pile-Dateien: ${JSON.stringify(PILE_FILES)}.\n`
    + (r === 1
      ? `Runde 1 = Marker-Seed (OQ-5): extrahiere Findings ueber die Marker-Heuristik (observation/hypothesis/burden) + offensichtliche requirements/constraints.\n`
      : `SCHON GEFUNDEN (${seen.length}, NICHT wiederholen): ${JSON.stringify(seen).slice(0, 4000)}\n`
        + `Suche NUR NEUE Findings, die in den frueheren Runden uebersehen wurden (Rand/Border, implizite, Kreuzbezuege).\n`)
    + `Jedes Finding traegt timeline_pos = globaler Sequenz-Index (Datei-Reihenfolge in pile_files * 100000 + Zeile). `
    + `Setze user_emphasis=true bei expliziter Betonung (UNBEDINGT/wichtig/Kern) (AK-12). `
    + `new_core_count = Anzahl NEUER, nicht-trivialer Kern-Kandidaten dieser Runde.`,
    { label: `extract:r${r}`, phase: 'Extract', schema: EXTRACT_SCHEMA, model: 'opus' },
  )
  const fresh = (res && res.findings) ? res.findings : []
  all = all.concat(fresh)
  log(`[dispatch_findings] Runde ${r}: +${fresh.length} (new_core=${res && res.new_core_count}). total=${all.length}`)
  if (!res || (res.new_core_count || 0) === 0) {  // DeltaCORE==0 -> konvergiert
    log(`[dispatch_findings] Konvergenz nach Runde ${r} (DeltaCORE==0).`)
    break
  }
}

// ── Phase Cluster (AK-2, OQ-1 cleancoder-Embedding) + WeightPrune (AK-3/4/5) + Synthesize (AK-6) ──
phase('Cluster')
const DISTILL_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    findings_core: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      text: { type: 'string' }, cluster_id: { type: 'integer' }, weight: { type: 'number' },
      recurrence: { type: 'integer' }, sources: { type: 'array', items: { type: 'string' } },
    }, required: ['text', 'cluster_id', 'weight'] } },
    findings_border: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      text: { type: 'string' }, source: { type: 'string' }, demoted_reason: { type: 'string' },
    }, required: ['text'] } },
    pruned: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
      loser: { type: 'string' }, winner: { type: 'string' }, reason: { type: 'string' },
    }, required: ['loser', 'winner'] } },
    cluster_count: { type: 'integer' },
  }, required: ['findings_core', 'findings_border', 'cluster_count'],
}
const distilled = await agent(
  `BL-235 Findings-Destillation fuer ${BL_ID}. Eingabe: ${all.length} Roh-Findings (asymptotisch, ${rounds} Runden):\n`
  + `${JSON.stringify(all).slice(0, 12000)}\n\n`
  + `AUFGABE (in dieser Reihenfolge):\n`
  + `1. CLUSTER (AK-2, OQ-1): nutze die cleancoder-MCP \`generate_embedding\` (via ToolSearch) pro Finding-Text, `
  + `clustere nach Cosine >= ${COSINE_THRESHOLD}. CORE = Cluster mit >=2 Findings (Dichte-Mitte) ODER user_emphasis=true (AK-12 CORE-Pin); `
  + `BORDER = Singletons/Rand -> demoted (NICHT geloescht, AK-5).\n`
  + `2. GEWICHT (AK-3): weight = f(timeline_pos) * cluster_recurrence. recurrence = Cluster-Groesse. `
  + `Spaeteres timeline_pos => hoeheres Gewicht (OQ-4 later-wins).\n`
  + `3. VALENZ/PRUNING (AK-4/5, OQ-3 K^2): pro Cluster-Paar (NICHT N^2 Finding-Paar) bestimme REINFORCE|CONTRADICT. `
  + `Bei CONTRADICT gewinnt der Knoten mit hoechstem timeline-Gewicht; der Verlierer -> pruned (mit Begruendung).\n`
  + `4. OUTPUT (AK-6): findings_core (nach weight absteigend = Headline-faehig) + findings_border (Anhang) + pruned-Liste.`,
  { label: `distill:${BL_ID}`, phase: 'Cluster', schema: DISTILL_SCHEMA, model: 'opus' },
)

phase('Synthesize')
const core = (distilled && distilled.findings_core) ? distilled.findings_core : []
const border = (distilled && distilled.findings_border) ? distilled.findings_border : []
log(`[dispatch_findings] DONE ${BL_ID}: ${all.length} roh -> ${core.length} CORE + ${border.length} BORDER `
  + `(${distilled && distilled.cluster_count} Cluster, ${rounds} Runden, ${(distilled && distilled.pruned || []).length} gepruned).`)

return {
  bl_id: BL_ID,
  rounds,
  raw_count: all.length,
  findings_core: core,
  findings_border: border,
  pruned: (distilled && distilled.pruned) || [],
  cluster_count: (distilled && distilled.cluster_count) || 0,
  terminated_reason: 'converged',
}
