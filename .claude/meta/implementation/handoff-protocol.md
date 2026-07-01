# HANDOFF-Konsumption Protokoll (EC-6, W181, W180-D)

**Quelle:** Extrahiert aus `_I_orchestrate.md` v3.2 → v3.3 (Decomposition)
**Geladen von:** Team Lead in Schritt 0.4

**Zweck:** Explizite Konsumption des HANDOFF.md aus dem SC-Zyklus. Verhindert W181 (informeller Zugang) und W180-D (Konsumptions-Luecke). Stellt sicher dass alle Worker denselben strukturierten Kontext erhalten.

**Wann:** Nach Entity-Check CLEAR (Schritt 0.3), VOR Manifest-Init (Schritt 0.5).

---

## 0.4a: HANDOFF.md vorhanden?

```
handoff_path = "{VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HANDOFF.md"  # BL-151 + PL-D 2026-05-07

Falls NICHT vorhanden:
  → Logge: "HANDOFF.md nicht gefunden — HANDOFF-Konsumption SKIP."
  → handoff_consumed = false
  → Warnung in Manifest: handoff_warning = "HANDOFF.md nicht vorhanden (kein SC-Vorzyklus?)"
  → Weiter mit Schritt 0.5 (keine Blockierung — optional)
```

---

## 0.4b: HANDOFF.md lesen

```
Lies HANDOFF.md komplett:
  → YAML-Frontmatter (Version, Datum, Ersteller)
  → Markdown-Sektionen 1-8:
    Pflicht (4): [LOESCHEN], [BEHALTEN], [OFFENE AUFGABEN], [ARCHITEKTUR]
    Optional-Erwartet (4): [KRITISCHE HINWEISE], [SRS-TREND], [DISCOVERY-GAPS], [ADR-RATIONALE]
```

---

## 0.4c: Pflicht-Sektionen pruefen

```
pflicht_sektionen = ["[LOESCHEN]", "[BEHALTEN]", "[OFFENE AUFGABEN]", "[ARCHITEKTUR]"]
fehlende = [s fuer s in pflicht_sektionen wenn s NICHT in HANDOFF.md]

Falls fehlende nicht leer:
  i_gate_response:
    i_decision: reject_needs_more_sc
    handoff_completeness: MISSING
    rejection_reason: "Pflicht-Sektionen fehlen: {fehlende}"
    approved_by: "i-orchestrate-agent"
    approved_at: {jetzt ISO8601}
  Manifest updaten
  AUSGABE: "HANDOFF-Konsumption FEHLGESCHLAGEN: Pflicht-Sektionen fehlen: {fehlende}"
  → HARD STOP
```

---

## 0.4d: Strukturierte Daten extrahieren

```
handoff_context = {
  source_file: handoff_path,
  extracted_at: {jetzt ISO8601},
  sections: {
    loeschen:               extrahiere_sektion("[LOESCHEN]"),
    behalten:               extrahiere_sektion("[BEHALTEN]"),
    offene_aufgaben:        extrahiere_offene_aufgaben("[OFFENE AUFGABEN]"),
    architektur_constraints: extrahiere_liste("[ARCHITEKTUR]"),
    kritische_hinweise:     extrahiere_sektion("[KRITISCHE HINWEISE]") oder null,
    srs_trend:              extrahiere_srs_tabelle("[SRS-TREND]") oder null,
    discovery_summary:      extrahiere_tabelle("[DISCOVERY-GAPS]") oder null,
    architectural_decisions: extrahiere_tabelle("[ADR-RATIONALE]") oder null
  }
}
```

---

## 0.4e: handoff_context im Manifest speichern

```
Schreibe ins Manifest:
  handoff_context: {handoff_context}
```

---

## 0.4f: Konsumptions-Flags setzen

```
Schreibe ins Manifest:
  handoff_consumed: true
  handoff_consumed_at: {jetzt ISO8601}
  handoff_consumed_by: "i-orchestrate-agent"

  i_gate_response:
    i_decision: accept_start
    handoff_completeness: OK
    approved_by: "i-orchestrate-agent"
    approved_at: {jetzt ISO8601}
    rejection_reason: null
```

---

## 0.4g: handoff_context an KURZLEBIG_PROMPT uebergeben

```
KURZLEBIG_PROMPT-Erweiterung:
  Der handoff_context (ADRs, offene Aufgaben, Discovery-Gaps) wird als
  KONTEXT-Block in KURZLEBIG_PROMPT der Worker eingefuegt (siehe Phase 2
  ADR-KONTEXT Sektion — bereits vorhanden, wird um handoff_context-Felder ergaenzt).
```

**Logging:**
```
Logge: "HANDOFF-Konsumption erfolgreich: {n} offene Aufgaben, {m} ADRs, srs_trend: {interpretation}"
```
