---
type: building-block
---

# /_I_diffAudit

**Status:** v1.0
**Actor:** DIFF-AUDITOR
**Zweck:** Gesamten Feature-Diff gegen develop auditieren — jede Aenderung muss sich rechtfertigen

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_diffAudit {NAME}                                 |
+===============================================================+
|                                                                |
|  KERN-PROBLEM:                                                 |
|    Entwicklung ist nicht linear. Man probiert, driftet ab,     |
|    korrigiert. Jeder Umweg hinterlaesst Spuren im Code.        |
|    Diese Spuren sind im finalen Diff — aber nicht noetig.      |
|    "Jede Aenderung ist boese" — je weniger Diff, desto         |
|    besser der PR.                                              |
|                                                                |
|  KERN-PRINZIP:                                                 |
|    Rueckwaerts vom Endergebnis: Model = was GEBRAUCHT wurde.   |
|    Diff = was GEAENDERT wurde. Jede Diff-Zeile muss sich      |
|    gegen Model/Spec/AK rechtfertigen.                          |
|    Was sich nicht rechtfertigt → Revert-Kandidat.              |
|                                                                |
|  DIFF-BASIS:                                                   |
|    git diff develop...HEAD (NICHT main!)                       |
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. git diff develop...HEAD (Gesamt-Diff)                    |
|    2. models/{NAME}_Model.md (Wahrheiten W{n})                 |
|    3. specs/{NAME}_Spec.md (Anforderungen/AK)                  |
|    4. synthese/{NAME}-VERIFY.md (getestete Abdeckung)          |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    5. synthese/{NAME}-GAP.md (bekannte Deltas)                 |
|    6. synthese/{NAME}-ARCHITECT.md (Slice-Zuordnung)           |
|    7. _parking-lot.md (bewusst verschobene Items)              |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. synthese/{NAME}-DIFFAUDIT.md                             |
|       → Audit-Report mit Kategorisierung                       |
|    2. _manifest.md Update                                      |
|                                                                |
|  SCHREIBT NICHT:                                               |
|    - Code (NUR der User entscheidet ueber Reverts)             |
|    - Model (keine neuen Wahrheiten)                            |
|                                                                |
|  PIPELINE:                                                     |
|    [/_gap] → [/_I_diffAudit] → [/_Pre_PR] → [PR erstellen]   |
|                              → [/_W_modelSplit] (parallel)     |
|    (Nach Gap: erst Diff auditieren, dann Pre-PR Quality Gates  |
|     UND Model-Split fuer Wissens-Koaleszenz)                   |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**DIFF-AUDITOR:** Prueft ob jede Code-Aenderung eine Daseinsberechtigung hat.

**TUT:** Diff lesen, gegen Model/Spec mappen, kategorisieren, Cleanup-Liste erstellen.

**NICHT:** Code aendern, Tests schreiben, Model updaten. NUR auditieren und berichten.

---

## Agent-Strategie + Modell-Zuweisung

```
Feature-Diffs koennen 10.000+ Zeilen umfassen.
Haiku ist zu beschraenkt fuer Traceability-Mapping.
Deshalb: Opus-Sonnet-Opus Sandwich.

WELLE 0 — OPUS (Hauptagent):
  Diff laden, Model/Spec/Verify lesen.
  Suchgebiet strukturieren: Dateien → logische Gruppen.
  Drafter-Auftraege definieren (welcher Drafter prueft welche Gruppen).

WELLE 1 — SONNET (3-5 Drafter, parallel):
  Jeder Drafter bekommt:
    - Eine Datei-Gruppe (5-15 Dateien)
    - Die W{n}-Liste + AK-Liste (Kontext)
    - Die Spuren-Heuristiken (SPUR-1 bis SPUR-7)
  Jeder Drafter schreibt:
    - drafts/{NAME}-diffaudit-D{NN}-{GRUPPE}.md
    - Pro Datei: Kategorie + Begruendung

WELLE 2 — OPUS (Hauptagent, Synthese):
  Alle Drafter-Reports lesen.
  Konflikte aufloesen (gleiche Datei, unterschiedliche Bewertung).
  Finale Kategorisierung: NOTWENDIG / FRAGLICH / REVERT.
  Cleanup-Plan mit Risiko-Reihenfolge erstellen.
  → synthese/{NAME}-DIFFAUDIT.md

  *** Nach JEDER Welle: /compact moeglich ***

| Phase   | Modell | Agents  | Aufgabe                           |
|---------|--------|---------|-----------------------------------|
| Welle 0 | opus   | 1 (DU)  | Diff laden, Gruppen definieren    |
| Welle 1 | sonnet | 3-5     | Traceability + Spuren pro Gruppe  |
| Welle 2 | opus   | 1 (DU)  | Synthese + Cleanup-Plan           |
```

---

## Welle 0: Diff + Kontext laden (OPUS)

```
DU (Hauptagent) fuehrst aus:

1. git diff develop...HEAD --stat
   → Ueberblick: welche Dateien, wie viele Aenderungen

2. git diff develop...HEAD --name-only
   → Datei-Liste fuer systematische Durcharbeitung

3. Model lesen → W{n}-Liste extrahieren (nur AKTIVE Wahrheiten)
4. Spec lesen → AK-Liste extrahieren (Akzeptanzkriterien)
5. Verify lesen → Was ist getestet/abgedeckt?

6. Dateien in GRUPPEN aufteilen:

   Gruppen-Typen:
     FEATURE-CORE    → Kern-Implementierung (Business Logic)
     FEATURE-INFRA   → Unterstuetzend (DI, Config, .csproj)
     TEST            → Test-Code (Unit, Integration, E2E)
     REFACTOR        → Struktur-Aenderungen ohne neue Funktionalitaet
     MIGRATION       → DB-Migrationen, Schema-Aenderungen
     UNKNOWN         → Keiner Gruppe zuordenbar (VERDAECHTIG)

7. Drafter-Auftraege erstellen:
   → Pro Drafter: 1-2 Gruppen (5-15 Dateien)
   → Jeder bekommt: Datei-Liste + W{n}-Kontext + AK-Kontext

AUSGABE:
  "Diff: {N} Dateien geaendert, +{A}/-{R} Zeilen"
  "Model: {M} aktive Wahrheiten"
  "Spec: {K} Akzeptanzkriterien"
  "Gruppen: {G} definiert, {D} Drafter geplant"
```

---

## Welle 1: Traceability + Spuren (SONNET, 3-5 Drafter parallel)

```
Jeder Drafter bekommt seinen Auftrag aus Welle 0.

PRO DATEI in der zugewiesenen Gruppe:

  Schritt A: Diff-Hunk lesen
    → git diff develop...HEAD -- {DATEI}
    → Aenderungen verstehen (hinzugefuegt/entfernt/geaendert)

  Schritt B: Traceability-Mapping
    1. WAHRHEITS-CHECK:
       → Trackt diese Aenderung zu einem W{n}?
       → Welchem? (Referenz angeben)
    2. AK-CHECK:
       → Trackt diese Aenderung zu einem AK?
       → Ist sie NOTWENDIG fuer das AK oder nur "nice to have"?
    3. SPEC-CHECK:
       → Wird diese Aenderung von der Spec gefordert?
    4. TEST-CHECK:
       → Gibt es einen Test der diese Aenderung verifiziert?
       → Wuerde der Test OHNE diese Aenderung fehlschlagen?
    5. ABHAENGIGKEITS-CHECK:
       → Haengt eine ANDERE notwendige Aenderung von dieser ab?

  Schritt C: Spuren-Erkennung (Heuristiken)
    SPUR-1: Auskommentierter Code
      → War mal aktiv, wurde deaktiviert statt geloescht
      → FAST IMMER revertbar
    SPUR-2: Debug-Logging / Console.WriteLine
      → Waehrend Debugging eingefuegt, vergessen zu entfernen
      → Revertbar wenn nicht im Logging-Konzept
    SPUR-3: Defensive Checks fuer unmoeglche Szenarien
      → "Was wenn X null ist?" — aber X kann nie null sein
      → Revertbar wenn kein Test davon abhaengt
    SPUR-4: Doppelt-angefasste Stellen
      → Datei wurde in Commit A geaendert, in Commit B NOCHMAL
      → Die erste Aenderung ist moeglicherweise subsumiert
      → Pruefen: Ist der finale Zustand = develop + Commit B?
    SPUR-5: Explorations-Reste
      → Klassen/Methoden die erstellt aber nie genutzt werden
      → Config-Werte die nicht referenziert werden
      → IMMER revertbar
    SPUR-6: Ueberschuessige Using-Statements / Imports
      → Fuer Typen die nicht mehr verwendet werden
      → Revertbar
    SPUR-7: Whitespace / Formatting-Only Changes
      → Kein funktionaler Unterschied
      → Revertbar (reduziert Diff-Noise)

  Schritt D: Kategorisierung pro Datei
    NOTWENDIG  → mindestens 1 Traceability-Check positiv
    FRAGLICH   → kein Check eindeutig positiv, aber plausibel
    REVERT     → kein Check positiv, keine Abhaengigkeit

JEDER DRAFTER SCHREIBT:
  drafts/{NAME}-diffaudit-D{NN}-{GRUPPE}.md

  Format pro Datei:
  | Datei | Kategorie | W{n}/AK | Spur? | Begruendung |
```

---

## Welle 2: Synthese + Cleanup-Plan (OPUS)

```
DU (Hauptagent) liest alle Drafter-Reports.

Schritt A: Konsolidierung
  → Alle Datei-Bewertungen zusammenfuehren
  → Konflikte aufloesen (gleiche Datei in 2 Draftern?)
  → UNKNOWN-Gruppen besonders kritisch pruefen

Schritt B: Finale Kategorisierung
  → Jede Aenderung bekommt finales Urteil:
    NOTWENDIG / FRAGLICH / REVERT

Schritt C: Audit-Report schreiben

synthese/{NAME}-DIFFAUDIT.md:

  ---
  id: {NAME}-DIFFAUDIT
  type: diff-audit
  status: partial|final
  diff-basis: develop...HEAD
  dateien-total: {N}
  aenderungen-total: +{A}/-{R}
  ---

  ## Zusammenfassung

  | Kategorie | Dateien | Zeilen | Anteil |
  |-----------|---------|--------|--------|
  | NOTWENDIG | {n1} | {z1} | {p1}% |
  | FRAGLICH | {n2} | {z2} | {p2}% |
  | REVERT | {n3} | {z3} | {p3}% |

  ## NOTWENDIG (behalten)

  | # | Datei | Aenderung | Rechtfertigung |
  |---|-------|-----------|----------------|
  | 1 | Foo.cs | +Method() | W12: Retry-Logik |

  ## FRAGLICH (User entscheidet)

  | # | Datei | Aenderung | Verdacht | Empfehlung |
  |---|-------|-----------|----------|------------|
  | 1 | Bar.cs | +NullCheck | SPUR-3 | REVERT? |

  ## REVERT-KANDIDATEN

  | # | Datei | Aenderung | Spur-Typ | Begruendung |
  |---|-------|-----------|----------|-------------|
  | 1 | Baz.cs | +Debug.Log | SPUR-2 | Kein Logging-Konzept |

  ## Cleanup-Plan

  Reihenfolge fuer Reverts (sicherste zuerst):
  1. Whitespace/Formatting (SPUR-7) → risikofrei
  2. Unused Imports (SPUR-6) → risikofrei
  3. Auskommentierter Code (SPUR-1) → risikofrei
  4. Debug-Logging (SPUR-2) → niedrig
  5. Explorations-Reste (SPUR-5) → mittel (Tests pruefen!)
  6. Defensive Checks (SPUR-3) → mittel (Tests pruefen!)
  7. Doppelt-angefasste Stellen (SPUR-4) → HOCH (genau pruefen!)

  Nach JEDEM Revert-Block: Tests laufen lassen!
```

---

## Schritt 5: User-Review + Cleanup

```
1. Report dem User praesentieren
2. User markiert FRAGLICH-Items als BEHALTEN oder REVERT
3. Cleanup in Reihenfolge des Plans (sicherste zuerst)
4. Nach jedem Block: Build + Tests
   → GRUEN: weiter
   → ROT: Revert des Reverts, Item als NOTWENDIG markieren

AUSGABE:
  "Diff-Audit abgeschlossen."
  "Vorher: {N} Dateien, +{A}/-{R} Zeilen"
  "Nachher: {M} Dateien, +{B}/-{S} Zeilen"
  "Reduzierung: -{X} Zeilen ({Y}% schlanker)"
  "Tests: {T} PASS, 0 FAIL"
```

---

## Qualitaetskriterien

- Diff-Basis ist IMMER develop (nicht main, nicht vorheriger Commit)
- JEDE Aenderung wird geprueft, nicht nur "verdaechtige"
- Model-Wahrheiten sind die PRIMAERE Rechtfertigung
- Tests sind der BEWEIS: Revert + Tests gruen = war nicht noetig
- User entscheidet IMMER ueber FRAGLICH-Items
- Reverts gehen vom Sichersten zum Riskantesten
- Nach JEDEM Revert-Block: Build + Tests validieren
- KEIN Revert ohne Test-Validierung
- Haiku zu beschraenkt — Sonnet MINIMUM fuer Traceability-Mapping

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_diffAudit abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
