export const meta = {
  name: 'dispatch_arc42',
  description: 'arc42-Sichten parallel rendern (read-only Views auf W{n}, file-isoliert) — gruene-Zone Doku-Workflow (BL-378/BL-330): 1 Step=1 agent, kein concurrent-write-Race, NUR reines Mermaid+Markdown (kein C4). NICHT der pre-Gate-D-verbotene dispatch_implement-Build-Motor (anderer Zweck: read-only Doku statt Code-Mutation).',
  phases: [
    { title: 'Render', detail: '1 agent pro arc42-Sektion, file-isoliert parallel ueber frozen Wahrheits-Snapshot' },
  ],
}

// args: { bl_id, arc42_dir, sections: [{ name, file, section_nr }] }
// Der Lead (_arc42_orchestrate) bestimmt sections (Tier-gefiltert) + den arc42_dir; dieser Workflow
// faechert sie file-isoliert auf. Lint-Gate + Fan-In-Index macht der Orchestrator NACH diesem Return.

phase('Render')

const sections = (args && args.sections) || []
if (sections.length === 0) {
  log('dispatch_arc42: keine Sektionen uebergeben — nichts zu rendern.')
  return { rendered: [], section_count: 0, ok_count: 0 }
}

log(`dispatch_arc42: ${sections.length} arc42-Sektionen parallel rendern (file-isoliert) fuer ${args.bl_id}`)

// PARALLEL: jede Sektion = 1 agent = 1 Berater-Load = 1 eigene Datei (file-isoliert -> race-frei).
// Mega-Worker strukturell unmoeglich (1 Step = 1 agent). opus-floor (haiku verboten).
const results = await parallel(sections.map((s) => () =>
  agent(
    `Lade Skill _arc42_berater_${s.name} und fuehre seinen Vertrag aus mit args="${args.bl_id}". `
    + `Schreibe AUSSCHLIESSLICH die Datei ${args.arc42_dir}/${s.file} (file-isoliert, READ-ONLY auf den `
    + `schon-gepflegten Wahrheiten Model/Spec/K-Score/Gap/PL). Fehlende Wahrheit -> Platzhalter `
    + `"> [ungegroundet: <was> ] (siehe OQ-y / PL-z)" mit Backlink, NIE halluziniertes Grounding. `
    + `NUR reines Mermaid + Markdown (KEIN C4). KEIN Sub-Agent-Spawn (W7).`,
    { label: `arc42:${s.name}`, phase: 'Render', model: 'opus' }
  )
))

const rendered = sections.map((s, i) => ({ section: s.name, file: s.file, ok: results[i] != null }))
const okCount = rendered.filter((r) => r.ok).length
log(`dispatch_arc42: ${okCount}/${sections.length} Sektionen gerendert (file-isoliert). Lint+Index folgt im Orchestrator.`)

return { rendered, section_count: sections.length, ok_count: okCount }
