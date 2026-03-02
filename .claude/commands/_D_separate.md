# /_D_separate - Protokoll-Datei anlegen

```yaml
status: active
version: 1.0.0
created: 2026-02-26
op: Debloat
phase: separation
type: single-command
chain_position: pre-kollaps
team_based: false
changelog: |
  v1.0.0: Initialer Entwurf (S1_DOrchestrate, ModelBloat-Implementation).
          Erstellt {FEATURE}_Protokoll.md aus W{n}-Bloecken des Models.
          Nutzt Protokoll_Template.md (S2_Protokoll) als Basis.
          Klassifiziert W{n}: Beobachtung → Protokoll, Mechanismus → Model.
          KURZLEBIG: 1 Agent = 1 Command = 1 Response (kein Worker-Loop).
```

---

```
+======================================================================+
| SINGLE COMMAND: /_D_separate {FEATURE}                               |
+======================================================================+
|                                                                        |
| ACTOR: SEPARATOR (DU - die ausfuehrende Claude-Instanz)              |
|                                                                        |
| ZWECK: Erstellt {FEATURE}_Protokoll.md aus dem bestehenden Model.   |
|        Falls Protokoll bereits existiert: Format pruefen, melden.   |
|        Grundlage fuer _D_kollaps (Voraussetzung fuer Kollaps).      |
|                                                                        |
| ENTSCHEIDUNGSBAUM W{n}-Klassifizierung (W04):                        |
|   Ist W{n} ein "was wurde gemessen/beobachtet"?                      |
|     → Beobachtung → Protokoll (Status beibehalten: OFFEN/BESTAETIGT)|
|   Ist W{n} ein "wie/warum funktioniert etwas (kausal)"?             |
|     → Mechanismus → bleibt im Model                                  |
|   Zweifelsfaelle: lieber ins Protokoll (konservativ)                 |
|                                                                        |
| KURZLEBIG: Spawne KEINE Sub-Agents. Alles in dieser einen Response. |
+======================================================================+
```

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_D_separate {FEATURE}                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. .claude/models/{FEATURE}_Model.md (MUSS EXISTIEREN)              ║
║       → Alle W{n}-Bloecke extrahieren + klassifizieren                 ║
║    2. .claude/templates/Protokoll_Template.md (Basis-Template)          ║
║       (aus S2_Protokoll; falls nicht vorhanden: W14-Format direkt)     ║
║                                                                          ║
║  LIEST (Input) - OPTIONAL:                                               ║
║    3. .claude/models/{FEATURE}_Protokoll.md                             ║
║       (nur pruefen ob vorhanden + Format validieren)                    ║
║                                                                          ║
║  SCHREIBT (Output) - HAUPTFALL (Protokoll noch nicht vorhanden):        ║
║    .claude/models/{FEATURE}_Protokoll.md (NEU erstellt)                ║
║    → YAML-Header (feature, type, blueprint, version)                    ║
║    → Sektion "Aktive W{n}" (alle OFFEN + BESTAETIGT Beobachtungen)    ║
║    → Sektion "Archivierte W{n}" (WIDERLEGT / INTEGRATED falls vorhanden)║
║    → Cluster-Tags <!-- cluster: X --> aus Model uebernehmen            ║
║                                                                          ║
║  SCHREIBT (Output) - SONDERFALL (Protokoll bereits vorhanden):          ║
║    NICHTS (nur Format-Report ausgeben)                                  ║
║                                                                          ║
║  INVARIANTEN:                                                            ║
║    - {FEATURE}_Model.md MUSS vor Aufruf existieren                     ║
║    - Kein Ueberschreiben vorhandener Protokoll-Datei                   ║
║    - W{n}-Klassifizierung: konservativ (Zweifelsfaelle → Protokoll)    ║
║    - Mechanismus-W{n} bleiben im Model (werden NICHT verschoben)       ║
║    - NUR Protokoll-Erstellung, KEIN Model-Cleanup (→ _D_kollaps)       ║
║                                                                          ║
║  N+1 LIEST:                                                              ║
║    _D_kollaps liest {FEATURE}_Protokoll.md (P1: Kandidaten-Scan)       ║
║                                                                          ║
║  ACTOR: SEPARATOR                                                        ║
║    Erstellt Protokoll aus Model-W{n}. Schreibt nichts ins Model.       ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Chain-Position

```
_D_orchestrate → **_D_separate** → _D_kollaps
```

**Prev:** `_D_orchestrate` (entscheidet ob Protokoll anlegen noetig)
**Next:** `_D_kollaps` (liest Protokoll als Haupt-Input fuer P1-P5)

---

## Verantwortlichkeit

Der **SEPARATOR** Actor hat eine einzige Verantwortung:

**Protokoll-Datei erstellen (einmalig, unveraenderlich)**

Was der Separator **TUT**:
- Alle W{n}-Bloecke aus dem Model lesen
- Jeden W{n} klassifizieren (Beobachtung vs. Mechanismus)
- Protokoll-Datei nach W14-Format erstellen
- Cluster-Tags aus Model-Kommentaren uebernehmen
- Format bestehender Protokoll-Datei validieren (falls vorhanden)

Was der Separator **NICHT TUT**:
- Model veraendern (kein W{n} loeschen/verschieben → das ist _D_kollaps)
- Kollaps ausfuehren (→ _D_kollaps)
- Manifest aktualisieren (→ _D_orchestrate)
- Sub-Agents spawnen (kurzlebig, alles in einer Response)

---

## SCHRITTE

### Schritt 0: Vorbedingungen pruefen

```
1. Lies .claude/models/{FEATURE}_Model.md
   → Existiert? NEIN → Fehler ausgeben, abbrechen
   → JA → weiter

2. Pruefe .claude/models/{FEATURE}_Protokoll.md
   → Existiert? JA → Schritt 1 (Format-Check), dann Schritt 4
   → Existiert? NEIN → Schritt 2 (Neu erstellen)

3. Pruefe .claude/templates/Protokoll_Template.md
   → Existiert? JA → als Basis verwenden
   → Existiert? NEIN → W14-Format direkt anwenden (aus ModelBloat_Model.md Kap. W14)
```

### Schritt 1: Bestehendes Protokoll validieren (nur bei Existenz)

```
Lies {FEATURE}_Protokoll.md, pruefe:
  □ YAML-Header vorhanden? (feature, type, blueprint)
  □ Sektion "Aktive W{n}" vorhanden?
  □ Sektion "Archivierte W{n}" vorhanden?
  □ W{n}-Bloecke mit Status-Attribut?

Ausgabe:
  "Protokoll bereits vorhanden: {FEATURE}_Protokoll.md
   Format-Status: [OK / VERALTET (fehlende Felder: X, Y)]
   Aktion: Keine Erstellung noetig."

→ Fertig (keine weiteren Schritte)
```

### Schritt 2: W{n}-Bloecke aus Model extrahieren

```
Lese {FEATURE}_Model.md vollstaendig.
Extrahiere ALLE W{n}-Bloecke (Muster: "### W{N}: {Titel}" oder "**W{N}:**").

Fuer jeden W{n}-Block:
  - Titel extrahieren
  - Status extrahieren (AKTIV / OFFEN / BESTAETIGT / WIDERLEGT / INTEGRATED)
  - These/Beschreibung extrahieren (1-3 Saetze)
  - Quelle extrahieren (falls vorhanden: Drafter-Datei, Zyklus)
  - Cluster-Tag extrahieren (<!-- cluster: X --> falls vorhanden)

Erstelle interne Liste:
  [{ n, titel, status, beschreibung, quelle, cluster }]
```

### Schritt 3: W{n} klassifizieren

```
Fuer jeden W{n} in der Liste:

  ENTSCHEIDUNGSBAUM:
  Frage 1: Ist die These eine BEOBACHTUNG?
    ("was wurde gemessen/festgestellt/entdeckt/zaehlt X")
    → JA: Typ = PROTOKOLL
    → NEIN: Frage 2

  Frage 2: Beschreibt die These einen MECHANISMUS/KAUSALITAET?
    ("wie funktioniert X", "warum passiert Y", "kausale Kette: A → B → C")
    → JA: Typ = MODEL (bleibt im Model, nicht ins Protokoll)
    → NEIN: Frage 3

  Frage 3: Widerlegt die These ein anderes W{m}?
    ("widerlegt W{m}", "gegenteilig zu", "korrigiert")
    → JA: Typ = PROTOKOLL (mit Widerlegungs-Referenz)
    → NEIN: Typ = PROTOKOLL (Zweifelsfaelle konservativ → Protokoll)

  Mapping auf Protokoll-Sektion:
    Status OFFEN | AKTIV | BESTAETIGT → "Aktive W{n}"
    Status WIDERLEGT | INTEGRATED    → "Archivierte W{n}"

Protokoll-Liste: alle Typ=PROTOKOLL Eintraege
Model-Liste: alle Typ=MODEL Eintraege (zur Dokumentation, nicht veraendert)
```

### Schritt 4: Protokoll-Datei erstellen

```
Erstelle .claude/models/{FEATURE}_Protokoll.md:

Format (W14-Spezifikation):

---
feature: {FEATURE}
type: wahrheiten-protokoll
blueprint: {FEATURE}_Model.md
version: 1.0
created: {YYYY-MM-DD}
last_collapse: null
w_n_count: {ANZAHL_AKTIVE}
---

# {FEATURE}_Protokoll

## Aktive W{n} (OFFEN / BESTAETIGT)

{Fuer jeden W{n} in Protokoll-Liste mit Status OFFEN/BESTAETIGT/AKTIV:}

### W{N}: {Titel}  <!-- cluster: {X} -->
**Status:** {OFFEN | BESTAETIGT}
**Quelle:** {D-Datei oder OBSERVE-Zyklus oder "Migration aus Model v{VERSION}"}
{Beschreibung, 1-3 Saetze aus Model uebernehmen}

---

## Archivierte W{n} (INTEGRATED / WIDERLEGT)

{Fuer jeden W{n} in Protokoll-Liste mit Status WIDERLEGT/INTEGRATED:}

### W{N}: {Titel}
**Status:** {WIDERLEGT | INTEGRATED}
**Quelle:** {D-Datei oder OBSERVE-Zyklus}
**Backref:** {Blueprint-Stelle falls INTEGRATED, Gegen-W{m} falls WIDERLEGT}
{Beschreibung, 1-3 Saetze}

---
```

### Schritt 5: Abschluss-Report ausgeben

```
Ausgabe:

"_D_separate {FEATURE}: Protokoll erstellt.

  Datei: .claude/models/{FEATURE}_Protokoll.md
  W{n} gesamt im Model: {GESAMT}
  → Protokoll (Beobachtungen): {N_PROTO} W{n}
  → Model (Mechanismen, unveraendert): {N_MODEL} W{n}
  Aktive W{n}: {N_AKTIV}
  Archivierte W{n}: {N_ARCHIV}

  Naechster Schritt: /_D_kollaps {FEATURE}"
```

---

## Klassifizierungs-Beispiele (W04-basiert)

| W{n}-Typ | Beispiel-These | Klassifizierung |
|----------|---------------|-----------------|
| Beobachtung | "71% der W{n} in OmniCommand_Model sind Beobachtungen" | PROTOKOLL |
| Beobachtung | "+20 W{n}/Zyklus monoton wachsend" | PROTOKOLL |
| Mechanismus | "Ein Blueprint erklaert 'wie funktioniert das System kausal'" | MODEL |
| Mechanismus | "Kondensierung erfordert Human-in-Loop bei Conf. <0.85" | MODEL |
| Widerlegung | "Token-basierter Trigger wurde verworfen, weil..." | PROTOKOLL |
| Zweifelsfaelle | Gemischte These (Beobachtung + kleiner Kausal-Anteil) | PROTOKOLL (konservativ) |

---

## QUICK-START

```bash
# Direkt aufrufen (selten, meist von _D_orchestrate gespawnt):
/_D_separate OmniCommand

# Was passiert:
# 1. Prueft ob Protokoll existiert
# 2. Falls JA: Format validieren, Meldung, fertig
# 3. Falls NEIN: alle W{n} aus Model lesen
# 4. Jeden W{n} klassifizieren (Beobachtung vs. Mechanismus)
# 5. Protokoll-Datei erstellen (W14-Format)
# 6. Report ausgeben
```

---

## Fehler-Handling

| Fehler | Reaktion |
|--------|----------|
| `{FEATURE}_Model.md` nicht gefunden | Fehler ausgeben, abbrechen |
| Keine W{n}-Bloecke im Model | Warnung: "Model hat keine W{n}-Bloecke. Protokoll leer erstellt." |
| `Protokoll_Template.md` fehlt | W14-Format direkt aus ModelBloat_Model.md W14 verwenden |
| Schreibfehler Protokoll-Datei | Fehler ausgeben, abbrechen (nichts halb-geschrieben) |

---

## Siehe auch

- [[_D_orchestrate]] - Ruft _D_separate auf (falls Protokoll fehlt)
- [[_D_kollaps]] - Liest Protokoll als Haupt-Input (N+1)
- [[Protokoll_Template]] - Template-Basis (S2_Protokoll)
- [[ModelBloat_Model]] - W04 (Klassifizierung), W14 (Dateiformat)
