# _arc42_berater_entscheidungen (arc42 §9 Architekturentscheidungen — View auf Wahrheiten)

```yaml
type: berater
status: active
version: 1.1.0   # BL-382 AK-9/AK-10: adr-Truth-Node-Primaer-Lese-Pfad + Graceful Degradation + Misch-Render + Konflikt-Stufe-2-Urteil
created: 2026-06-16
op: Arc42Render
phase: "arc42/§9"
chain_position: "Fan-Out-Worker von /_arc42_orchestrate (file-isoliert, parallel)"
feature_anchor: BL-378  # Konsum-Vertrag erweitert durch BL-382 (AK-9/AK-10)
model_tier: ceiling  # opus — Tragweite/Risiko einer Entscheidung einschaetzen + Konflikt-Stufe-2-Urteil = Urteil
```

## Zweck (EIN Job)
Rendere **arc42 §9 Architekturentscheidungen** als View: wichtige/teure/riskante Entscheidungen inkl.
Begründung, **nach Tragweite geordnet** (ADR-Form / Tabelle). **Schlüssel-Quelle (BL-382 AK-9/W-CON-1):
echte `adr`-Truth-Nodes** (Model, `### W-ADR-{n}` mit `type: adr`) — die 6 Nygard-Felder
(`adr.{entscheidung, problem_kontext, alternativen, begruendung, konsequenzen, status}`) + die drei
expliziten Graph-Kanten (`betrifft_baustein[]` / `superseded_by` / `abhaengig_von[]`) maschinenlesbar,
ID-adressierbar via `{BL-SLUG}.ADR-{n}` — NICHT heuristisch aus Spec-Text rekonstruiert. **Graceful
Degradation (BL-382 AK-10): kein ADR-Node vorhanden -> Legacy-Spec-`ADR-*`-Heuristik als Fallback**
(Rückwärts-Kompatibilität, kein Hard-Cut alter BLs); gemischt -> Misch-Render MIT Herkunfts-Kennzeichnung
pro Eintrag. **Lücken-Detektor:** widersprüchliche/offene Entscheidung = offener ADR
(DCSRE-14-F3-Klasse: Default-Filter 526 vs Mockup); fehlende Wahrheit -> `[ungegroundet: ...]`.

## VERTRAG

```
LIEST (READ-ONLY):
  {bl_folder}/_manifest.md → BERATER_OUTPUTS.specParse, A_PIPELINE_STATE (k_score)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/*_Model.md   (PRIMAER: adr-Nodes, `### W-ADR-{n}` type=adr [BL-382 AK-9/W-CON-1])
  {VAULT}/Backlog/{BL_SLUG}/3_Spec/*_Spec.md     (Fallback: ADR-* / Architektur-Entscheidungen wenn kein Node)
  {VAULT}/Backlog/{BL_SLUG}/5_Gap/* + 6_PL/*     (OQ + BLOCKED-PL — offene/konfliktäre Entscheidungen)

SCHREIBT (NUR diese eine Datei — File-Single-Writer):
  {bl_folder}/arc42/09_entscheidungen.md
    Frontmatter: {section_nr: 9, tier_min: standard, grounding_status: voll|teil|leer, model_refs: [...], mermaid_types: []}
    Body: ADR-Tabelle/Liste nach Tragweite (ID | Entscheidung | Alternativen | Begruendung | Konsequenzen |
      Status: entschieden|offen|konflikt | betrifft_baustein | Herkunft: truth-node|spec-heuristik),
      PRIMAER aus `adr`-Nodes (maschinenlesbar), Fallback aus Spec-Heuristik, gemischt -> Misch-Render
      mit Herkunfts-Kennzeichnung pro Zeile.

SCHREIBT NICHT: andere arc42/-Sektionen, Manifest-State, Wahrheiten. INSBESONDERE NICHT: ADR-Truth-Nodes,
  adr.status (auch nicht konflikt-offen — der Render FLAGGT nur, der Producer/modelMaintain schreibt; INV-A42B-2).

INVARIANTEN: INV-A42B-1 (NUR 09_entscheidungen.md) · INV-A42B-2 (Read-Only) · INV-A42B-3 (model_refs / kein Halluzinat) ·
  INV-A42B-4 (Lint-konform, i.d.R. keine Diagramme) · INV-A42B-5 (W7). INV-A42B-AK (BL-382-NEUFASSUNG W-CON-1):
  PRIMAER sind echte `adr`-Nodes die Entscheidungs-Quelle; KEINE §9-Zeile aus Spec-Heuristik solange Nodes
  vorhanden sind. Nur wenn GAR KEIN Node existiert -> Legacy-Fallback Spec-`ADR-*`-Heuristik 1:1
  (Rueckwaerts-Kompatibilitaet). Gemischt -> Misch-Render mit Pflicht-Herkunfts-Kennzeichnung pro Eintrag
  (kein stiller Teil-Render, W-CON-2).
```

## Ablauf
```
1. WORKING_DIR = resolve_bl_path(BL_ID); ziel = {WORKING_DIR}/arc42/09_entscheidungen.md.
2. snap = read-only Model(adr-Nodes: `### W-ADR-{n}` type=adr) + Spec(ADR-* — nur Fallback) + K-Score + Gap/PL.
3. QUELLE-Routing (BL-382 W-CON-1/AK-9 — Primaer-Lese-Pfad):
   IF >=1 `adr`-Node im Model (`type: adr`):
     pro Node EINE Tabellen-Zeile, befuellt MASCHINENLESBAR aus den Node-Feldern (NICHT Spec-Heuristik):
       ID            <- node.id ({BL-SLUG}.ADR-{n}, maschinen-referenzierbar fuer BL-383-Downstream)
       Entscheidung  <- adr.entscheidung
       Alternativen  <- adr.alternativen[] ({option} abgelehnt_weil {grund})
       Begruendung   <- adr.begruendung
       Konsequenzen  <- adr.konsequenzen
       Status        <- adr.status (vorgeschlagen|akzeptiert|superseded|konflikt-offen — DAS ADR-Enum,
                        NICHT der Gold-Form-`Status:`; beide orthogonal, W-VAL-3)
       betrifft_baustein <- adr.betrifft_baustein[] (Kante nach UNTEN §5)
       Herkunft      <- `truth-node`  (Pflicht-Kennzeichnung, AK-10)
     KEINE Zeile aus Spec-`ADR-*`-Heuristik, solange Nodes vorhanden sind (INV-A42B-AK).
   ELSE (kein Node): Legacy-Fallback — Spec-`ADR-*` + Model-Kern-Entscheidungen + K-Score(riskante)
     heuristisch sammeln (ALT-Verhalten 1:1), jede Zeile Herkunft=`spec-heuristik`.
4. Ordne nach Tragweite (superseded ans Ende; aktive/konfliktaere zuerst). Superseded-Knoten bleiben
   sichtbar (Historie verlustfrei) — mit Status=superseded + Verweis auf `superseded_by`-Nachfolger.
5. KONFLIKT-Stufe-2-Urteil (BL-382 AK-8/AK-10 — DEINE Render-Zeit-Pflicht, ceiling-tier):
   Die Stufe-1-Kandidaten (zwei nicht-superseded `akzeptiert`-ADRs gleicher `betrifft_baustein` +
   UNTERSCHIEDLICHER `entscheidung`) liefert der deterministische Vorfilter
   `detect_adr_conflicts(parse_w_blocks(model_content))` (quality_model_wform.py) ->
   [{baustein, adr_ids:[a,b], entscheidungen:[ea,eb]}, ...]. Pro Kandidat URTEILE (opus): widersprechen
   sich ea/eb am gemeinsamen Baustein INHALTLICH?
     JA  -> flagge beide Zeilen Status=`konflikt-offen` + `[konflikt: {adr_a} vs {adr_b} @ {baustein}] (OQ/PL)`.
            (Du SCHREIBST adr.status NICHT in den Vault — INV-A42B-2; du flaggst nur die View. Die
             Persistenz von adr.status=konflikt-offen ist Producer/modelMaintain-Sache.)
     NEIN -> beide bleiben `akzeptiert` (konservativ, KEIN false-positive-Flag, SOA-2).
6. Weitere Luecken: Widerspruch/offen ohne Beschluss bzw. fehlendes Pflicht-Feld -> Status=konflikt/offen +
   `[ungegroundet: welche?] (OQ/PL)` (bestehender Luecken-Detektor, INV-A42B-3).
7. Schreibe ADR-Tabelle + Self-Lint (i.d.R. keine Diagramme, INV-A42B-4).
   SendMessage: "§9 Entscheidungen: {n} ADRs ({quelle: nodes|spec-fallback|misch}), {offen} offen/konflikt."
```

## Graceful Degradation / Lücke = sichtbare Frage (BL-382 AK-10 / W-CON-2)
| Situation | Verhalten |
|---|---|
| `adr`-Nodes vorhanden | §9 PRIMAER aus Nodes (maschinenlesbar); Spec-`ADR-*`-Heuristik NICHT genutzt (W-CON-1, INV-A42B-AK); jede Zeile Herkunft=`truth-node` |
| GAR KEIN `adr`-Node im Vault | voller Fallback: Spec-`ADR-*`-Heuristik 1:1 (Rückwärts-Kompatibilität, kein Hard-Cut alter BLs); jede Zeile Herkunft=`spec-heuristik` |
| GEMISCHT (einzelne als Node, Rest nur Spec) | Misch-Render: gegroundete Zeilen aus Truth-Node, Rest aus Heuristik — **jede Zeile trägt Herkunfts-Markierung** (`truth-node` vs `spec-heuristik`); KEIN stiller Teil-Render (W-CON-2) |
| Stufe-1-Konflikt-Kandidat, Stufe-2-Urteil JA (Widerspruch) | beide Zeilen Status=`konflikt-offen` + `[konflikt: {a} vs {b} @ {baustein}] (OQ/PL)` (View-Flag, kein Vault-Write, INV-A42B-2) |
| Stufe-1-Kandidat, Stufe-2-Urteil NEIN | beide bleiben `akzeptiert` (konservativ, kein false-positive, SOA-2) |
| widersprüchliche Entscheidung (F3) / fehlendes Pflicht-Feld | ADR Status=konflikt/offen + `[ungegroundet: welche?] (OQ/PL)` |
| keine Entscheidungen gegroundet (Node noch Spec) | leere ADR-Liste + grounding_status=leer |

## Verwandt
`/_arc42_orchestrate` (Caller) · `_arc42_berater_loesungsstrategie` (§4, strategische Entscheidungen) ·
`_A_berater_specParse` (ADR-Truth-Node-Producer, BL-382 AK-2) · `quality_model_wform.py`
(`detect_adr_conflicts` Stufe-1-Vorfilter + `check_adr_superseded_chains`, BL-382 AK-7/AK-8) ·
`manifest-schema.md` Sektion L (ADR-Node-Schema-Kanon) · arc42-Template §9 · BL-378 / BL-382.
```
