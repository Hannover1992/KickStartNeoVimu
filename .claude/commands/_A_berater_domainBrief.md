# _A_berater_domainBrief (A-Pipeline — Domain-Konsultation)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-08
op: Analyse
phase: "0.6"
chain_position: "nach findingsExtraction/findingsReview, VOR specParse/akExtraktion — Domain-Konsultation"
feature_anchor: BL-254 (DomainLibrary-Consumer @A) — Zwilling von _SDF_berater_patternBrief (@SDF/I)
model_tier: ceiling  # opus — semantischer Domaenen-Match (Konzept-Vergleich, nicht Struktur)
```

## Zweck (EIN Job)

**Konsultiere die DomainLibrary, BEVOR das Model/die AKs gebaut werden** — wiederverwenden statt
neu-erfinden, und **Dubletten vermeiden** (confirm-or-add-or-contradict). Das ist der **Zwilling von
`_SDF_berater_patternBrief`** (Pattern @SDF/I), nur für **Domänen-Wahrheiten @A**. Der I-Pfad macht das
schon für Patterns; diese Stage macht es für Domäne @Analyse-Zeit (BL-254).

> **Schluessel-Unterschied zu patternBrief (BL-254):** Pattern-Dedup = **struktureller** Match (Code-Form).
> Domain-Dedup = **semantischer** Match (Begriff/Konzept) — "ist `Selbstauskunft hat QDVTP+QDVS-Varianten`
> schon bekannt, oder neu?" ist ein Bedeutungs-Vergleich. Heute opus-Urteil; später der BL-287-Retriever.

## confirm-or-add-or-contradict (der Kern)

```
FOR jede Domaenen-Annahme aus den findings:
  match = semantischer Vergleich gegen DomainLibrary-Eintraege (Konzept/Begriff, nicht Naming)
  IF match (hohe Konfidenz):
    → CONFIRM: pattern_library.py lifecycle {DOM-id} --pfad 1 --scope domain   # usage++ + Provenance(dies BL)
      matched_domain.append({id, term, confidence})   # KEIN Doppel — wird NICHT als neue Wahrheit angelegt
  ELIF widerspricht einem Eintrag (gegenteilige Geschaeftsregel):
    → CONTRADICTION: contradictions.append({new, existing_id, note})  # Domaenen-Verstaendnis hat sich geaendert
  ELSE:
    → NEU: new_candidates.append({term, ...})  # geht als neue Domaenen-Wahrheit in die normale A-Pipeline
```

## VERTRAG

```
LIEST:
  {bl_folder}/_manifest.md → A_PIPELINE_STATE / BERATER_OUTPUTS.findingsExtraction (die Domaenen-Annahmen)
  {VAULT}/Libraries/DomainLibrary/_index.md   (read-only; Bestands-Domaenen-Wahrheiten)
  VAULT_ROOT via resolve_vault_root.py (ARCH-N8, Single Source)

RUFT (Reuse — NIE Counter-Logik duplizieren):
  pattern_library.py lifecycle {DOM-id} --pfad 1 --scope domain   # usage++ fuer CONFIRM-Treffer
  pattern_library.py rank_by_maturity(..., scope=domain)          # Reife-Sortierung (analog patternBrief R3)

SCHREIBT (NUR eigener Slot — Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS.domainBrief:
      matched_domain:  [{id, term, confidence}]        # bestaetigt (existieren schon — wiederverwenden, kein Doppel)
      new_candidates:  [{term, source_finding_id}]     # neu (kein Match → neue Domaenen-Wahrheit)
      contradictions:  [{new, existing_id, note}]      # Widerspruch → HiL/auflösen
      no_match: bool                                   # true wenn DomainLibrary leer/fehlt ODER 0 Treffer
      brief_summary: "Freitext, max 3 Saetze"
      domain_brief_logged: true
      domain_brief_at: {ISO8601}

  NICHT: DomainLibrary direkt editieren (nur via pattern_library.py), andere BERATER_OUTPUTS, A_PIPELINE_STATE.

INVARIANTEN:
  INV-DB-1 (Single-Writer): schreibt NUR BERATER_OUTPUTS.domainBrief (+ DomainLibrary-usage via Script-API).
  INV-DB-2 (NON-BLOCKING): leere/fehlende DomainLibrary → no_match=true, graceful skip, domain_brief_logged=true (kein Fehler).
  INV-DB-3 (Dedup-Pflicht): ein CONFIRM-Treffer wird NICHT als neue Domaenen-Wahrheit angelegt — confirm (usage++) statt Doppel (BL-254-Kern).
  INV-DB-4 (semantischer Match): Domain-Match ist Konzept-/Begriffs-Vergleich, NICHT Naming/Struktur — orthogonal zur PatternLibrary.
  INV-DB-5 (Reuse): Counter-Reifung NUR via pattern_library.py lifecycle (scope=domain) — keine duplizierte Counter-Logik.
  INV-DB-6 (Idempotenz): domain_brief_logged=true + cached output → SKIP_CACHED (Resume-aware).
```

## Aufruf

```
Skill(_A_berater_domainBrief, args="{BL_ID}")
```
Aufgerufen von `_A_orchestrate` (Phase 0.6, nach findingsReview, vor specParse). KEIN direkter User-Aufruf.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID)
   IDEMPOTENZ-GATE (INV-DB-6): IF domain_brief_logged==true AND cached domainBrief present: RETURN SKIP_CACHED

2. VAULT-ONLY (INV-PL-VAULT-1 analog): VAULT_ROOT = resolve_vault_root.py; vault_dl = {VAULT_ROOT}/Libraries/DomainLibrary
   IF NOT exists(vault_dl) OR _index leer (EMPTY_SEED):
     SCHREIBE domainBrief={no_match:true, matched_domain:[], new_candidates:[alle findings als neu], domain_brief_logged:true,
              brief_summary:"DomainLibrary leer/fehlt (EMPTY_SEED) — alle Domaenen-Annahmen sind neu."}; RETURN (INV-DB-2)

3. domain_findings = Domaenen-Annahmen aus BERATER_OUTPUTS.findingsExtraction (FACHLICH-relevante Findings)
   lib = rank_by_maturity(read DomainLibrary-Eintraege, scope=domain)   # Reife-sortiert (analog patternBrief R3)

4. FOR f IN domain_findings:   # confirm-or-add-or-contradict (der Kern)
     m = semantischer_match(f, lib)   # Konzept-Vergleich (opus-Urteil), nicht Naming
     IF m.confirm:        Bash("py pattern_library.py lifecycle {m.id} --pfad 1 --scope domain"); matched_domain.append({m.id, f.term, m.confidence})
     ELIF m.contradicts:  contradictions.append({new:f.term, existing_id:m.id, note:m.note})
     ELSE:                new_candidates.append({term:f.term, source_finding_id:f.id})

5. no_match = (|matched_domain|==0)
   Schreibe BERATER_OUTPUTS.domainBrief = {matched_domain, new_candidates, contradictions, no_match, brief_summary, domain_brief_logged:true, domain_brief_at:ISO}.
   SendMessage team-lead: "domainBrief: {matched_domain} bestaetigt (wiederverwendet) / {new_candidates} neu / {contradictions} Widersprueche"
```

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| DomainLibrary leer/fehlt (EMPTY_SEED) | no_match=true, alle Findings als new_candidates, domain_brief_logged=true (INV-DB-2) |
| 0 Domaenen-Findings | matched/new/contra=[], no_match=true |
| pattern_library.py lifecycle nicht erreichbar | matched trotzdem listen (WARN), usage++ nachholen bei Resume |
| Widerspruch erkannt | contradictions[] + Hinweis an Lead (HiL-Klaerung VOR Model-Bau) |

## Verwandt
- `_SDF_berater_patternBrief` (Zwilling, Pattern @SDF/I) · `_A_berater_findingsExtraction` (Eingabe) ·
  `_A_berater_specParse`/`akExtraktion` (Downstream — nutzen matched_domain für Reuse) ·
  `pattern_library.py` (lifecycle scope=domain) · `_PT_berater_materialize` (Producer der DomainLibrary, BL-256) ·
  BL-254 (DomainLibrary-Consumer) · BL-287 (späterer semantischer Retriever ersetzt den opus-Match)
```
