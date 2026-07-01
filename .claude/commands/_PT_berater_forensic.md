# _PT_berater_forensic (Pattern-Extraction Stage 6)

```yaml
type: berater
status: active
version: 1.1.0
created: 2026-06-02
updated: 2026-06-08
op: PatternExtraction
phase: "6"
chain_position: "sechste Stage in _PT_orchestrate — nach classify, vor materialize"
feature_anchor: BL-237 (Revert-Forensik — 3 Hypothesen, pfad-2-Vokabular) + BL-257 (Factoring-Evidenz, positiv)
model_tier: ceiling  # opus — Hypothesen-Bildung (das WARUM hinter dem Revert)
```

## Zweck (EIN Job)

**Deute jeden Revert mit 3 Hypothesen.** Stage 4 (contradiction) lieferte das DASS — welche Signale
zurueckgebaut/contested sind. Diese Stage liefert das **WARUM**: pro Revert genau 3 Hypothesen, warum das
Pattern nicht hielt. Das ist die Forensik-Achse (BL-237 AK-5). Das Verdikt wird im **pfad-2-Vokabular**
formuliert (der `broken++`-Pfad von `_PT_update`/`pattern_library.py lifecycle`), damit Stage 7 es direkt
in die Counter-Mechanik einspeisen kann.

**+ BL-257 (Factoring-Evidenz, die POSITIVE Seite derselben git-Forensik):** für jedes `classify.factoring`-
Signal liefert diese Stage zusätzlich die git-diff-Evidenz der **Transformation** (vorher→nachher:
extract/inline/declarativize/dedup/move — welcher Commit, welche Datei:Zeile vorher/nachher). Kein Revert —
Stage 7 materialisiert daraus den FactoringLibrary-Eintrag mit echtem Commit-Anker als Provenance.

> **Single Unit of Work (/_help P-10):** liest .contradiction + .timeAxis + Code-Anker, bildet je Revert
> 3 Hypothesen, schreibt EINEN eigenen Slot (.forensic), stirbt. Keine Materialisierung (→ Stage 7),
> kein Library-Write.

## Die 3 Hypothesen (pro Revert)

| Hypothese | Bedeutung | Konsequenz fuer Stage 7 |
|---|---|---|
| **H1: Pattern falsch** (`pattern_wrong`) | das Pattern selbst war fehlerhaft / Anti-Pattern | pfad-2 broken++ → Richtung DEPRECATE |
| **H2: falsch verwendet** (`pattern_misused`) | Pattern ok, aber im Kontext falsch angewendet | KEIN broken++ am Pattern; boundary_note ergaenzen |
| **H3: Beschreibung falsch** (`pattern_misdescribed`) | Pattern ok, aber Doku/Grenzen irrefuehrend | boundary_note/Beschreibung korrigieren, kein broken++ |

## pfad-2-Vokabular (verbindlich — boundary_note)

`boundary_note` muss exakt im Vokabular des `lifecycle --pfad-2`-Pfades formuliert sein (BL-154
`_PT_update` Counter-Schema), damit Stage 7 es ohne Uebersetzung in `pattern_library.py lifecycle`
einspeisen kann. Kein Freitext-Jargon — die Felder spiegeln das broken/boundary-Schema.

**Konkretes Format-Mapping (code-grounded, K-4 — `.claude/scripts/pattern_library.py:427-430`):**
Der pfad-2-Pfad schreibt `boundary_notes` und `broken_locations` in GENAU diesem Schema. `boundary_note`
MUSS verbatim diesem Format folgen (sonst muesste Stage-7-Materialize uebersetzen — INV-FOR-3 verboten):

```
# pattern_library.py lifecycle pfad-2 (Z.427 / Z.429):
boundary_notes  APPEND:  f"broken in {ctx}: {reason}"           # ctx=broken_context, reason=broken_reason
broken_locations APPEND: {"file": ctx, "reason": reason, "date": today}

# forensic boundary_note (Stage 6) ist EXAKT dieser String — kein Freitext:
boundary_note = f"broken in {broken_context}: {broken_reason}"
# + die strukturierten Anker, die Stage 7 1:1 als lifecycle --broken-context / --broken-reason durchreicht:
broken_context = <betroffene Datei/Modul-Anker>     # -> broken_locations[].file
broken_reason  = <Kurz-Begruendung der leading_hypothesis>   # -> broken_locations[].reason
```

So liest Stage 7 `boundary_note` (bzw. `broken_context`/`broken_reason`) und ruft
`pattern_library.py lifecycle {pid} --pfad 2 --scope semantic --broken-context {ctx} --broken-reason {reason}`
OHNE Uebersetzung. Bei `lifecycle_hint == "boundary-only"` (leading != pattern_wrong) wird KEIN
`broken++` ausgeloest — nur die `boundary_note` als Grenz-Doku am Pattern hinterlegt (H2/H3).

## VERTRAG

```
LIEST:
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.contradiction.items[]       (die contested/reverted Items — das DASS)
    BERATER_OUTPUTS_PT.timeAxis.reverts_raw[]      (Revert-Anker fuer Code-Bezug)
    BERATER_OUTPUTS_PT.classify.*                  (Achsen-Kontext; classify.factoring[] = die zu belegenden Transformationen, BL-257)
  git diff {reverted_ref}..{revert_ref} (via Bash) (Code-Evidenz fuer Hypothesen-Bildung)
  WORKING_DIR via resolve_bl_path.py

SCHREIBT (NUR eigener Slot — INV-PTO-4 Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.forensic:
      verdicts: [{
        verdict_id, contradiction_id, pattern_id_hint,
        hypotheses: [
          {h: "pattern_wrong",       plausibility, evidence},
          {h: "pattern_misused",     plausibility, evidence},
          {h: "pattern_misdescribed", plausibility, evidence}
        ],
        leading_hypothesis,   # die plausibelste der 3 (deterministisch: hoechste plausibility, Tie → H2>H3>H1 konservativ)
        boundary_note,        # VERBATIM f"broken in {broken_context}: {broken_reason}" (pattern_library.py:427) — fuer Stage 7, kein Freitext
        broken_context,       # -> broken_locations[].file (pattern_library.py:429) — betroffener Datei/Modul-Anker
        broken_reason,        # -> broken_locations[].reason — Kurz-Begruendung der leading_hypothesis
        lifecycle_hint        # pfad-2-broken (nur bei leading=pattern_wrong) | boundary-only (sonst)
      }]
      factoring_evidence: [{   # BL-257: positive git-diff-Evidenz pro classify.factoring-Signal
        signal_id, transform_kind,    # extract|inline|declarativize|dedup|move
        before_anchor, after_anchor,  # Datei:Zeile vorher / nachher
        commit, diff_stat             # Commit-Hash (Provenance) + +/- Zeilen
      }]
      counts: {verdicts, broken_candidates, boundary_only, factoring_evidence}
      status: DONE | EMPTY

  NICHT: Libraries/* , andere BERATER_OUTPUTS_PT-Slots, pattern_library.py-Aufruf (das ist Stage 7).

INVARIANTEN:
  INV-FOR-1 (Single-Writer): schreibt NUR BERATER_OUTPUTS_PT.forensic.
  INV-FOR-2 (3-Hypothesen-Pflicht): jeder Revert bekommt GENAU 3 Hypothesen (pattern_wrong/misused/misdescribed) — keine fehlt.
  INV-FOR-3 (pfad-2-Vokabular): boundary_note ist im lifecycle-pfad-2-Schema (BL-154) formuliert — kein Freitext-Jargon.
  INV-FOR-4 (keine Materialisierung): forensic stellt NUR Hypothesen + lifecycle_hint bereit — der Counter-Write ist Stage 7.
  INV-FOR-5 (Graceful): keine reverts/contradiction → verdicts=[], status=EMPTY (factoring_evidence kann trotzdem gefuellt sein).
  INV-FOR-6 (Factoring-Evidenz, BL-257): pro classify.factoring-Signal eine git-diff-belegte Transformation (FORWARD-Diff, kein Revert) mit Commit-Anker — POSITIVE Seite der git-Forensik, getrennt von den Revert-verdicts.
```

## Aufruf

```
Skill(_PT_berater_forensic, args="{BL_ID}")
```
Aufgerufen von `_PT_orchestrate` Stage 6 (Worker-Spawn). KEIN direkter User-Aufruf.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID); bl_folder = WORKING_DIR
   IDEMPOTENZ: IF BERATER_OUTPUTS_PT.forensic.status == DONE: RETURN (Resume-SKIP)

2. contested = .contradiction.items[]; reverts = .timeAxis.reverts_raw[]
   IF contested == [] AND reverts == []: SCHREIBE forensic={verdicts:[], status:EMPTY}; RETURN (INV-FOR-5)

3. FOR item IN contested:
     diff = Bash("git diff {reverted_ref}..{revert_ref}")  (falls Code-Anker vorhanden)
     # INV-FOR-2: GENAU 3 Hypothesen, je mit plausibility + Code-Evidenz
     hypotheses = [
       {h:pattern_wrong,       plausibility: assess(diff, anti_pattern_signal), evidence:...},
       {h:pattern_misused,     plausibility: assess(diff, misuse_signal),       evidence:...},
       {h:pattern_misdescribed, plausibility: assess(diff, doc_mismatch),        evidence:...}
     ]
     leading = argmax(plausibility)  # Tie konservativ: misused > misdescribed > wrong (kein vorschnelles broken++)
     # INV-FOR-3 (K-4): boundary_note VERBATIM im pfad-2-Format (pattern_library.py:427), kein Freitext:
     broken_context = code_anchor(item)            # betroffene Datei/Modul -> broken_locations[].file
     broken_reason  = short_reason(leading, item)  # Kurz-Begruendung -> broken_locations[].reason
     boundary_note  = f"broken in {broken_context}: {broken_reason}"   # == pattern_library.py:427 verbatim
     lifecycle_hint = (leading==pattern_wrong) ? "pfad-2-broken" : "boundary-only"
     verdicts.append({..., boundary_note, broken_context, broken_reason, lifecycle_hint})

3b. BL-257 Factoring-Evidenz (positiv, getrennt von Reverts): FOR signal IN .classify.factoring:
     fdiff = Bash("git show {commit_of(signal)} -- {file_of(signal)}")  # FORWARD-Diff der Refactoring-Bewegung (KEIN Revert)
     transform_kind = classify_transform(fdiff)   # extract|inline|declarativize|dedup|move
     factoring_evidence.append({signal_id, transform_kind, before_anchor, after_anchor, commit, diff_stat})

4. counts berechnen. Schreibe BERATER_OUTPUTS_PT.forensic = {verdicts, factoring_evidence, counts, status: DONE}.
   SendMessage team-lead: "forensic: {verdicts} Verdikte ({broken_candidates} broken-Kandidaten / {boundary_only} boundary-only) — je 3 Hypothesen, pfad-2-Vokabular"
```

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| Revert ohne Code-Anker | Hypothesen aus Signal-Text allein (plausibility niedriger) |
| keine Reverts | verdicts=[], status=EMPTY |
| alle 3 Hypothesen gleich plausibel | Tie-Break konservativ misused>misdescribed>wrong (kein vorschnelles broken++) |

## Verwandt
- `_PT_berater_contradiction` (Stage 4, liefert das DASS) · `_PT_berater_timeAxis` (Stage 3) ·
  `_PT_berater_materialize` (Stage 7, konsumiert lifecycle_hint+boundary_note) ·
  `_PT_update` (BL-154 Counter-Schema pfad-2) · BL-237 3-Hypothesen-Forensik (Anschluss 5 / AK-5)
