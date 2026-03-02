# /_D_kollaps - Wahrheiten-Kollaps (5-Phasen)

```yaml
status: active
version: 1.1.0
created: 2026-02-26
op: Debloat
phase: kollaps
type: single-command
chain_position: terminal
team_based: false
changelog: |
  v1.1.0: OP-11 Fix (2026-02-26): P3 INTEGRATION-CHECK SCHRITT 0 (LOCATE + FORMAT-LOCK + Kap.7-Typ).
          P5 Q4 aufgeteilt: Q4a (Format-Compliance) + Q4b (Syntax-Check).
          Rollback-Trigger erweitert um Q4a.
  v1.0.0: Initialer Entwurf (S1_DOrchestrate, ModelBloat-Implementation).
          5-Phasen-Ablauf aus ModelBloat_Model.md Kap. 4 (W06-W08).
          Dual-Track: Track 1 (manuelle Tags, Default) + Track 2 (NLP, Enhancement).
          Human-in-Loop bei P3 wenn Confidence <0.85 (W07).
          --dry-run: zeigt was kollabiert wuerde, schreibt nichts.
          --scan-only: P1+P2 ohne Schreiben (SOFT-Trigger).
          KURZLEBIG: 1 Agent = 1 Command = 1 Response.
          AE-3: Track 1 Default (W08). AE-4: HiL bei Conf. <0.85 (W07).
```

---

```
+======================================================================+
| SINGLE COMMAND: /_D_kollaps {FEATURE} [--dry-run] [--scan-only]     |
+======================================================================+
|                                                                        |
| ACTOR: KOLLAPS-AGENT (DU - die ausfuehrende Claude-Instanz)          |
|                                                                        |
| ZWECK: Fuehrt den Wahrheiten-Kollaps durch (5-Phasen-Ablauf aus     |
|        ModelBloat_Model.md Kap. 4: W06, W07, W08).                  |
|        Kollabiert Beobachtungs-W{n} aus dem Protokoll               |
|        zu kompakten Mermaid-Updates im Blueprint-Model.              |
|                                                                        |
| VORAUSSETZUNG (PFLICHT):                                               |
|   {FEATURE}_Protokoll.md MUSS existieren (erstellt von _D_separate) |
|   → Fehler wenn Protokoll fehlt: "Fuehre zuerst /_D_separate aus"   |
|                                                                        |
| MODI:                                                                  |
|   Standard:    /_D_kollaps {FEATURE}        → P1-P5 vollstaendig    |
|   Dry-Run:     /_D_kollaps {FEATURE} --dry-run  → zeigt Plan, kein  |
|                                                      Schreiben        |
|   Scan-Only:   /_D_kollaps {FEATURE} --scan-only → P1+P2, kein      |
|                                                      Schreiben        |
|                (SOFT-Trigger Modus von _D_orchestrate)               |
|                                                                        |
| 5-PHASEN-ABLAUF:                                                       |
|   P1: SCAN      → W{n} zaehlen, Kandidaten identifizieren            |
|   P2: ANALYSE   → Cluster bilden, Kausal-Ketten erkennen             |
|   P3: KONDENSIERUNG → Mermaid-Update generieren (HiL wenn <0.85)    |
|   P4: MARKING   → W{n} als INTEGRATED markieren + Backref           |
|   P5: QS        → Q1-Q6 Checks, Rollback bei Fehler                 |
|                                                                        |
| DUAL-TRACK (W08):                                                      |
|   Track 1 (Default): Manuelle <!-- cluster: X --> Tags aus Protokoll |
|   Track 2 (Enhancement): MCP cleancodermcp Embedding-Similarity >0.75|
|   Fallback: Track 2 → Track 1 wenn NLP nicht verfuegbar             |
|                                                                        |
| HUMAN-IN-LOOP (W07):                                                   |
|   P3 Confidence >0.85: vollautomatisch                               |
|   P3 Confidence 0.65-0.85: Human-Review anfordern (pausieren)        |
|   P3 Confidence <0.65: Human-Review zwingend                          |
|   P5 Rollback-Trigger: Human-Entscheidung noetig                     |
|                                                                        |
| KURZLEBIG: Spawne KEINE Sub-Agents. Alles in dieser einen Response.  |
+======================================================================+
```

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_D_kollaps {FEATURE} [--dry-run] [--scan-only]               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. .claude/models/{FEATURE}_Protokoll.md (MUSS EXISTIEREN)          ║
║       → P1: Kandidaten-Scan (OFFEN/BESTAETIGT W{n} mit Cluster-Tags)  ║
║    2. .claude/models/{FEATURE}_Model.md (MUSS EXISTIEREN)              ║
║       → P3: Mermaid-Abschnitte lesen fuer Update-Stellen               ║
║       → P5: Model nach Kollaps messen (<500 Zeilen Ziel)               ║
║                                                                          ║
║  SCHREIBT (Output) - Standard-Modus (P1-P5):                            ║
║    1. .claude/models/{FEATURE}_Model.md (aktualisiert)                 ║
║       → P3: Mermaid-Update (neue Kanten/Knoten fuer kollabierte W{n}) ║
║       → Bereinigt: Beobachtungs-W{n} aus Model entfernt                ║
║    2. .claude/models/{FEATURE}_Protokoll.md (aktualisiert)             ║
║       → P4: Kollabierte W{n} als INTEGRATED markiert                  ║
║       → P4: Backref auf Blueprint-Stelle eingetragen                   ║
║       → YAML: last_collapse Datum aktualisiert                          ║
║                                                                          ║
║  SCHREIBT (Output) - --scan-only Modus (P1+P2):                         ║
║    NICHTS (nur Scan-Report ausgeben)                                    ║
║                                                                          ║
║  SCHREIBT (Output) - --dry-run Modus:                                   ║
║    NICHTS (zeigt Plan: was wuerde kollabiert, welche Mermaid-Updates)  ║
║                                                                          ║
║  INVARIANTEN:                                                            ║
║    - {FEATURE}_Protokoll.md MUSS vor Aufruf existieren (via _D_separate)║
║    - Rollback bei P5-Fehler: Model + Protokoll auf Stand vor P3         ║
║    - Mechanismus-W{n} NIEMALS kollabieren (nur Beobachtungen)           ║
║    - Minden 5 W{n} desselben Clusters als Kollaps-Vorbedingung (W10)   ║
║    - NLP-Confidence <0.85: Human-in-Loop PFLICHT (W07)                  ║
║                                                                          ║
║  N-1 SCHREIBT (via _D_separate):                                         ║
║    {FEATURE}_Protokoll.md (dieser Command liest es in P1)               ║
║                                                                          ║
║  ACTOR: KOLLAPS-AGENT                                                    ║
║    Liest Protokoll + Model. Baut Mermaid-Update. Markiert INTEGRATED.  ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Chain-Position

```
_D_separate → **_D_kollaps** → [fertig]
```

**Prev:** `_D_separate` (schreibt Protokoll, das dieser Command liest)
**Next:** Keiner (terminal in der D-Chain)

---

## Verantwortlichkeit

Der **KOLLAPS-AGENT** Actor hat eine einzige Verantwortung:

**Wahrheiten aus Protokoll ins Blueprint kollabieren**

Was der Kollaps-Agent **TUT**:
- Protokoll nach Kollaps-Kandidaten scannen (P1)
- Cluster bilden und Kausal-Ketten erkennen (P2)
- Mermaid-Updates fuer Blueprint generieren (P3)
- W{n} als INTEGRATED markieren + Backref eintragen (P4)
- Qualitaets-Checks durchfuehren, Rollback bei Fehler (P5)

Was der Kollaps-Agent **NICHT TUT**:
- Protokoll erstellen (→ _D_separate)
- Manifest aktualisieren (→ _D_orchestrate)
- Sub-Agents spawnen (kurzlebig, alles in einer Response)
- Mechanismus-W{n} aus dem Model entfernen (nur Beobachtungs-W{n})

---

## SCHRITTE

### Schritt 0: Vorbedingungen + Modus pruefen

```
1. Flag pruefen:
   --dry-run gesetzt? → DRY_RUN = true
   --scan-only gesetzt? → SCAN_ONLY = true
   (beide koennen kombiniert werden, macht aber keinen Sinn)

2. Lies .claude/models/{FEATURE}_Protokoll.md
   → Existiert? NEIN → Fehler:
     "Voraussetzung fehlt: {FEATURE}_Protokoll.md nicht gefunden.
      Fuehre zuerst /_D_separate {FEATURE} aus."
   → JA → weiter

3. Lies .claude/models/{FEATURE}_Model.md
   → Existiert? NEIN → Fehler ausgeben, abbrechen
   → JA → weiter

4. Backup vorbereiten (nur bei Standard-Modus, nicht dry-run/scan-only):
   Merke aktuellen Stand von Model + Protokoll fuer P5-Rollback
   (inhaltlich, als interner State dieser Session)
```

### P1: SCAN - Kandidaten identifizieren

```
Lies alle W{n} aus Protokoll-Sektion "Aktive W{n}":
  Filtere: Status OFFEN oder BESTAETIGT

Fuer jeden aktiven W{n}:
  - Cluster-Tag extrahieren (<!-- cluster: X -->)
  - Status notieren (OFFEN / BESTAETIGT)
  - Confidence-Indikator schatzen:
    BESTAETIGT = hoehere Confidence (bevorzugter Kollaps-Pfad, W10)
    OFFEN = niedrigere Confidence

Erstelle Kandidaten-Liste:
  [{ n, titel, status, cluster, confidence_basis }]

Ausgabe P1:
  "P1 SCAN: {N} aktive W{n} gefunden.
   Clusters: {Cluster-Liste mit Anzahl je Cluster}
   BESTAETIGT: {N_BEST}, OFFEN: {N_OFFEN}"

IF SCAN_ONLY: → P2 ausfuehren, dann Schritt 5 (Abschluss-Report), STOP
IF DRY_RUN: → alle Phasen ausfuehren, aber NICHTS schreiben
```

### P2: ANALYSE - Cluster bilden + Kausal-Ketten erkennen

```
DUAL-TRACK (W08):

Track 1 (Default - manuelle Tags):
  Gruppiere Kandidaten nach Cluster-Tag (<!-- cluster: X -->):
    Cluster X = { W{n}, W{m}, W{k}, ... }
  Kollaps-Vorbedingung (W10): >= 5 W{n} im selben Cluster?
    JA → Cluster ist Kollaps-Kandidat
    NEIN → Cluster vorerst nicht kollabieren (zu klein)

Track 2 (Enhancement - nur wenn MCP cleancodermcp verfuegbar):
  Fuer W{n} OHNE Cluster-Tag:
    Versuche: mcp__cleancodermcp__generate_embedding(w_n_text)
    Berechne Embedding-Similarity zwischen W{n}-Paaren
    Similarity >0.75 → auto-clustern (neuer Cluster-Name generieren)
  Falls MCP nicht antwortet: Fallback auf Track 1

Fuer jeden Kollaps-Kandidaten-Cluster:
  Erkenne gemeinsames Muster / Kausal-Kette:
    "Was ist der Kern-Mechanismus hinter diesen W{n}?"
  Schaetze Confidence:
    > 0.85: vollautomatisch
    0.65-0.85: Human-Review anfordern
    < 0.65: Human-Review zwingend

Ausgabe P2:
  "P2 ANALYSE: {N} Kollaps-Kandidaten-Cluster.
   Cluster {X}: {M} W{n}, Confidence: {SCORE} → {AUTO|HiL}"
```

### P3: KONDENSIERUNG - Mermaid-Update generieren

```
Fuer jeden Kollaps-Kandidaten-Cluster:

  SCHRITT 0: INTEGRATION-CHECK (PFLICHT, vor Confidence-Pruefung)

    A) Bestehendes Mermaid lokalisieren:
       Suche in {FEATURE}_Model.md nach ```mermaid ... ``` Bloecken.
       Fuer jeden gefundenen Block: Pruefe ob der Cluster-Kern-Mechanismus
       semantisch in diesen Block passt.

       Pruef-Kriterium: Passt die Kausal-Kette des Clusters zum Thema
       des bestehenden Mermaid?
         JA → MERMAID_ANCHOR = { Datei, Kapitel, Block-Inhalt }
              → Modus: INTEGRATION (Kante/Knoten in bestehendes Mermaid einbauen)
         NEIN (fuer alle Bloecke) → weiter mit B)

    B) Wenn kein passendes Mermaid gefunden: Mermaid-Typ bestimmen
       Wende Kap.7-Entscheidungsbaum (ModelBloat_Model.md) an:
         Zeitliche Reihenfolge + >2 Akteure? → sequenceDiagram
         Zeitliche Reihenfolge + 1 Aktor?   → flowchart TD/LR
         Zustaende mit Uebergaengen >3?      → stateDiagram-v2
         Zustaende ≤3?                       → Tabelle mit Status-Spalte
         Hierarchische Konzept-Struktur?     → mindmap
         Statische Daten, kein Ablauf?       → Tabelle

       MERMAID_TYP = {Ergebnis aus Entscheidungsbaum}
       → Modus: NEUERSTELLUNG (neuen Mermaid-Block anlegen)

    C) FORMAT-LOCK setzen:
       Wenn Modus = INTEGRATION oder NEUERSTELLUNG:
         → P3-Output MUSS ein Mermaid-Block sein (gemaess MERMAID_TYP)
         → Tabellen als Output: NUR fuer MERMAID_TYP = "Tabelle" (≤3 Zustaende / statische Daten)
         → Freie Prosa, Listen: VERBOTEN als P3-Output

  Danach: Confidence-Pruefung ausfuehren

  IF Confidence >= 0.85 (oder DRY_RUN):

    IF Modus = INTEGRATION:
      Ergaenze MERMAID_ANCHOR-Block mit neuer Kante/neuem Knoten:
        Neue Kante: "{Cluster-Kern}" → "{Ziel-Knoten}"
        Format: style-konform zum bestehenden Block
      DRY_RUN: Zeige geplante Integration, schreibe NICHTS
      Standard: Wende Update auf {FEATURE}_Model.md an

    IF Modus = NEUERSTELLUNG:
      Erstelle neuen {MERMAID_TYP}-Block:
        Position: Als neue Sub-Sektion im thematisch naechsten Kapitel
        Inhalt: Kern-Mechanismus des Clusters als Diagramm
        Format: Standard-Mermaid-Syntax (keine Leerzeichen in IDs)
      DRY_RUN: Zeige geplanten Block, schreibe NICHTS
      Standard: Fuege Block in {FEATURE}_Model.md ein

    Beispiel INTEGRATION:
      Bestehend:  BLOAT --> SPLIT["Symptom: Split"]
      Neu:        BLOAT --> GC_FAIL --> KOLLAPS_TRIGGER["Dual-Trigger W06"]

    Beispiel NEUERSTELLUNG (sequenceDiagram):
      sequenceDiagram
        participant TL as Team Lead
        participant W as Worker Agent
        TL->>W: spawn (1 Command)
        W-->>TL: Ergebnis
        TL->>W: shutdown

  ELIF Confidence 0.65-0.85 (HiL anfordern):
    Pausiere:
    "P3 KONDENSIERUNG benoetigt Human-Review fuer Cluster {X}:
     - {N} W{n} in Cluster: {Titel-Liste}
     - INTEGRATION-CHECK Ergebnis: {INTEGRATION|NEUERSTELLUNG} (Mermaid-Typ: {TYP})
     - Vorgeschlagener Mechanismus: '{VORSCHLAG}'
     - Vorgeschlagenes Mermaid-Update:
       {MERMAID_SNIPPET}
     Bitte bestaetigen (ja/nein/anpassen): "
    → Warte auf User-Input
    → User: "ja" → Update anwenden
    → User: "nein" → Cluster ueberspringen
    → User: "anpassen: {TEXT}" → angepassten Text verwenden

  ELSE Confidence < 0.65 (HiL zwingend):
    Gleiche Pause wie oben, aber mit explizitem Hinweis:
    "P3 KONDENSIERUNG: Confidence zu niedrig fuer Auto-Kondensierung.
     Human-Review ERFORDERLICH fuer Cluster {X}:"

Ausgabe P3 (nach allen Clustern):
  "P3 KONDENSIERUNG: {N_AUTO} Cluster automatisch, {N_HIL} mit HiL.
   {M_INT} Integrationen in bestehende Mermaids, {M_NEU} neue Mermaids erstellt.
   {M_TAB} als Tabellen (statt Mermaid, gemaess Kap.7-Baum)."
```

### P4: MARKING - INTEGRATED Status setzen

```
Fuer jeden erfolgreich kollabiertern W{n}:

  Im Protokoll ({FEATURE}_Protokoll.md):
    1. Status von OFFEN/BESTAETIGT auf INTEGRATED setzen:
       **Status:** INTEGRATED
    2. Backref auf Blueprint-Stelle eintragen:
       **Backref:** {FEATURE}_Model.md Kap. {N} (Mermaid-Update {DATUM})
    3. W{n} aus Sektion "Aktive W{n}" in "Archivierte W{n}" verschieben

  Im Protokoll YAML-Header:
    last_collapse: {YYYY-MM-DD}
    w_n_count: {NEUE_ANZAHL_AKTIVER}

  DRY_RUN: Zeige was markiert wuerde, schreibe NICHTS

Ausgabe P4:
  "P4 MARKING: {N} W{n} als INTEGRATED markiert.
   Backref eingetragen fuer: {Titel-Liste}"
```

### P5: QS - Qualitaets-Check

```
Fuehre Q1-Q6 Checks aus:

  Q1 Groesse: {FEATURE}_Model.md nach Kollaps < 500 Zeilen?
     OK: Ziel erreicht
     WARNUNG: Noch >500 Zeilen (kein Fehler, nur Hinweis)

  Q2 Mechanismus-Erhalt: Alle Mechanismus-W{n} noch im Model?
     Pruefe: Kein Mechanismus versehentlich entfernt?
     FEHLER: Rollback triggern

  Q3 Protokoll-Konsistenz: Alle INTEGRATED W{n} haben Backref?
     FEHLER: Fehlende Backrefs korrigieren (kein Rollback)

  Q4 Mermaid-Format: Alle P3-Outputs korrekt formatiert?
     Q4a PFLICHT-CHECK: Hat jedes kondensierte Cluster-Ergebnis einen Mermaid-Block
         ODER eine explizit mit Kap.7-Baum begruendete Tabelle?
         Falls reiner Prosa-Text oder ungekennzeichnete Tabelle: FEHLER → Rollback
     Q4b SYNTAX-CHECK: Alle Mermaid-Bloecke syntaktisch valide?
         Grundlegende Syntax (Kanten, Knoten-IDs, kein Leerzeichen in IDs)
         FEHLER: Rollback triggern

  Q5 Cluster-Vollstaendigkeit: Kein aktiver W{n} in kollabiertem Cluster
     noch als OFFEN/BESTAETIGT im Protokoll?
     FEHLER: Fehlende INTEGRATED-Markierung nachtragen

  Q6 YAML-Header: last_collapse korrekt gesetzt?
     FEHLER: Korrigieren

IF Q2 FEHLER oder Q4a FEHLER oder Q4b FEHLER:
  Rollback:
    Model + Protokoll auf Stand vor P3 zuruecksetzen
    Ausgabe:
    "P5 QS FEHLER: Rollback ausgefuehrt.
     Grund: {Q2 Mechanismus-Verlust | Q4a Format-Compliance | Q4b Mermaid-Syntax-Fehler}
     Model + Protokoll unveraendert.
     Manueller Eingriff noetig: {Empfehlung}"

IF alle Checks OK (oder nur Q1/Q3/Q5/Q6 WARNUNG):
  Ausgabe P5:
  "P5 QS: Alle Checks OK.
   Q1 Groesse: {N} Zeilen ({< | > }500Z Ziel)
   Q2 Mechanismus-Erhalt: OK
   Q3 Protokoll-Konsistenz: OK
   Q4a Format-Compliance: OK
   Q4b Mermaid-Syntax: OK
   Q5 Cluster-Vollstaendigkeit: OK
   Q6 YAML-Header: OK"
```

### Schritt 5: Abschluss-Report

```
IF SCAN_ONLY:
  Ausgabe:
  "_D_kollaps {FEATURE} --scan-only ABGESCHLOSSEN.

   P1 SCAN: {N_KANDIDATEN} Kollaps-Kandidaten
   P2 ANALYSE: {N_CLUSTER} Cluster
     → {K} Cluster mit >= 5 W{n} (Kollaps-bereit)
     → {J} Cluster zu klein (< 5 W{n})
   Groesste Cluster:
     Cluster {X}: {M} W{n}, Confidence: {SCORE}
     Cluster {Y}: ...

   Empfehlung: {
     N_KOLLAPS_BEREIT > 0:
       'HARD-Trigger empfohlen: /_D_kollaps {FEATURE} (vollstaendiger Kollaps)'
     N_KOLLAPS_BEREIT = 0:
       'Kein Kollaps noetig: Cluster zu klein, mehr W{n} sammeln'
   }"

IF DRY_RUN:
  Ausgabe:
  "_D_kollaps {FEATURE} --dry-run ABGESCHLOSSEN.

   Was wuerde kollabiert:
   Cluster {X}: W{n}, W{m}, W{k} → Mermaid-Update Kap. {N}
     Preview: {MERMAID_SNIPPET}
   Cluster {Y}: ...

   Modell-Groesse vorher: {N_VORHER} Zeilen → nachher geschaetzt: {N_NACHHER} Zeilen
   Kein Schreiben. Fuehre ohne --dry-run aus fuer echten Kollaps."

IF Standard (P1-P5 erfolgreich):
  Ausgabe:
  "_D_kollaps {FEATURE} ABGESCHLOSSEN.

   P1-P5 vollstaendig ausgefuehrt:
   Kollabierte Cluster: {N_KOLLAPS}
   INTEGRATED W{n}: {N_INTEGRATED}
   Mermaid-Updates: {N_MERMAID}
   Model-Groesse: {N_VORHER}Z → {N_NACHHER}Z
   Protokoll aktualisiert: last_collapse = {DATUM}

   Naechster Schritt: Kein weiterer Schritt noetig.
   (Manifest-Update durch _D_orchestrate)"
```

---

## Kollaps-Beispiel (konzeptuell)

```
Angenommen: Cluster "accumulation" mit W{n} W01, W03, W05, W11, W12 (5 W{n}):

P1 SCAN:   5 aktive W{n} in Cluster "accumulation" gefunden
P2 ANALYSE: Kausal-Kern: "Akkumulation entsteht durch fehlende Separation"
            Confidence: 0.88 (>0.85 → vollautomatisch)

P3 KONDENSIERUNG:
  Bestehend: ROOT --> BLOAT
  Neu:       ROOT --> FEHLENDE_SEP["Fehlende Separation"] --> BLOAT

  Mermaid-Update in {FEATURE}_Model.md:
    style FEHLENDE_SEP fill:#ff6b6b

P4 MARKING: W01, W03, W05, W11, W12 → Status INTEGRATED
  Backref: "{FEATURE}_Model.md Kap.1 Mechanismus-Uebersicht (2026-02-26)"
  W{n} in "Archivierte W{n}" verschoben

P5 QS: Model 320Z (<500Z OK), Mechanismus erhalten, Mermaid-Syntax OK
  → DONE
```

---

## Dual-Track Detail (W08)

| Track | Voraussetzung | Methode | Fallback |
|-------|---------------|---------|----------|
| Track 1 (Default) | Keine NLP-Infra | `<!-- cluster: X -->` Tags im Protokoll | - |
| Track 2 (Enhancement) | MCP cleancodermcp | Embedding-Similarity >0.75 fuer Auto-Clustering | → Track 1 |

Track 2 ergaenzt Track 1 (clustert W{n} OHNE manuelle Tags), ersetzt ihn nicht.

---

## Autonomie-Grenze (W07, Kap. 4.3)

| Phase | Automatisch? | Human-in-Loop? | Grund |
|-------|-------------|----------------|-------|
| P1: SCAN | Ja (vollstaendig) | Nein | Zaehlen ist mechanisch |
| P2: ANALYSE | Ja (Vorschlag) | Optional (Cluster-Review) | Grenzfaelle bei Zuordnung |
| P3: KONDENSIERUNG | Nur bei Conf. >0.85 | Ja bei Conf. <0.85 | Mechanismus-Umschreibung semantisch heikel |
| P4: MARKING | Ja (vollstaendig) | Nein | Status setzen ist administrativ |
| P5: QS | Ja (Checks) | Ja bei Rollback-Trigger | Rollback-Entscheidung braucht Kontext |

---

## QUICK-START

```bash
# Standard-Kollaps (gespawnt von _D_orchestrate bei HARD-Trigger):
/_D_kollaps OmniCommand

# Nur Scan (gespawnt von _D_orchestrate bei SOFT-Trigger):
/_D_kollaps OmniCommand --scan-only

# Dry-Run (zeigt Plan, schreibt nichts):
/_D_kollaps OmniCommand --dry-run

# Direkt aufrufen (selten, Voraussetzung: Protokoll muss existieren):
/_D_kollaps DCSRE-93
```

---

## Fehler-Handling

| Fehler | Reaktion |
|--------|----------|
| `{FEATURE}_Protokoll.md` fehlt | Fehler: "Fuehre zuerst /_D_separate aus", abbrechen |
| `{FEATURE}_Model.md` fehlt | Fehler ausgeben, abbrechen |
| Kein Cluster mit >= 5 W{n} | Warnung: "Kein Kollaps noetig", fertig |
| P3 Confidence < 0.65 | HiL zwingend, pausieren |
| Q2 Mechanismus-Verlust | Rollback, Meldung |
| Q4 Mermaid-Syntax-Fehler | Rollback, Meldung |
| MCP cleancodermcp nicht verfuegbar | Fallback auf Track 1, Warnung ausgeben |

---

## Siehe auch

- [[_D_separate]] - Erstellt Protokoll (Voraussetzung fuer diesen Command)
- [[_D_orchestrate]] - Orchestrator der D-Chain (spawnt diesen Command)
- [[ModelBloat_Model]] - W06 (Trigger), W07 (HiL/Autonomie), W08 (Dual-Track)
- [[ModelBloat_Model]] - Kap. 4 (5-Phasen-Ablauf, vollstaendige Spezifikation)
