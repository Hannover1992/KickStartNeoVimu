---
name: batch-simple
description: Paralleler Batch - teilt Aufgabe in max. 10 Agents auf. 1 Agent = 1 Datei. Opus plant, Haiku/Sonnet fuehrt aus.
args:
  aufgabe:
    description: Die Aufgabe die parallel bearbeitet werden soll
    required: true
  kontext:
    description: Regeln, Standards, Beispiele (optional)
    required: false
---

# Batch Simple

```
OPUS ──┬──► Agent 1 ──► Datei A
       ├──► Agent 2 ──► Datei B
       ├──► ...
       └──► Agent N ──► Datei N (max 10)
              │
              ▼
         OPUS sammelt
              │
              ▼
           NOTIFY
```

## Eiserne Regeln

| Regel | Agent MUSS |
|-------|------------|
| **Isolation** | NUR in zugewiesener Datei arbeiten |
| **Kein Build** | KEINEN `dotnet build/test` ausfuehren |
| **Kein Commit** | NICHT committen |
| **Rueckmeldung** | Aenderungen zusammenfassen |

---

## Aufgabe

{{aufgabe}}

## Kontext

{{kontext}}

---

## Ausfuehrung

### Schritt 1: Dateien finden

Identifiziere alle betroffenen Dateien mit Glob/Grep.

### Schritt 2: Batch-Plan erstellen

| # | Datei | Was tun | Model |
|---|-------|---------|-------|
| 1 | ... | ... | haiku/sonnet |

**Model-Wahl:**
- `haiku` = Pattern-Ersetzung, klare Regeln
- `sonnet` = Komplexe Logik, Architektur-Entscheidungen

### Schritt 3: Agents parallel starten

**WICHTIG:** Alle Task-Aufrufe in EINEM Message-Block!

**Agent-Prompt Template:**
```
## Aufgabe
{Was zu tun ist}

## Datei
{Vollstaendiger Pfad}

## Regeln
{Standards/Patterns die einzuhalten sind}

## Beispiel
VORHER: {altes Pattern}
NACHHER: {neues Pattern}

## Grenzen
- Du arbeitest AUSSCHLIESSLICH in: {Dateiname}
- Du aenderst KEINE anderen Dateien
- Du fuehrst KEINEN Build aus
- Du commitest NICHT

## Rueckmeldung
Liste alle Aenderungen auf (Zeile, vorher, nachher).
```

### Schritt 4: Ergebnisse sammeln

Nach Abschluss aller Agents:
1. Zusammenfassung erstellen
2. Commit-Message vorschlagen (User committed!)

### Schritt 5: Benachrichtigung senden

**WICHTIG:** Wenn alle Agents fertig sind, MUSS eine Benachrichtigung gesendet werden!

```bash
powershell -Command "notify 'Batch fertig: {Anzahl} Dateien bearbeitet, {Anzahl} Aenderungen'"
```

Beispiele:
- `notify 'Batch fertig: 7 Dateien, 38 Log-Messages geaendert'`
- `notify 'Batch fertig mit Fehlern - 2 von 5 Agents fehlgeschlagen'`
- `notify 'Batch abgeschlossen - bereit zum Commit'`

---

## Jetzt starten

Analysiere: **{{aufgabe}}**

Finde betroffene Dateien und erstelle den Batch-Plan.
