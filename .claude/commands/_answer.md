---
type: satellite
---

# /_answer — Frage beantworten (Extensiv + Kurzform)

```yaml
status: active
version: 1.0.0
created: 2026-03-30
op: Answer
phase: Output
chain_position: standalone
difficulty_scaling: false
coldstart: true
```

## Zweck

`/_answer` beantwortet eine konkrete Frage in zwei Stufen:
- **EXTENSIV:** Gruendliche Recherche, ausfuehrliche Erklaerung, Belege mit Datei:Zeile
- **KURZFORM:** 3-5 Saetze, copy-paste-fertig, kein Jargon, verstaendlich ohne Kontext

---

## VERTRAG

```
INPUT   : FRAGE (Pflicht) + optionale @kontext-Pfade
OUTPUT  : Abschnitt EXTENSIV + Abschnitt KURZFORM
TOOLS   : Read, Grep, Glob (Recherche) — KEIN Task-Tool, KEIN Sub-Agent
SCHREIBT: Nichts (reiner Output-Command)
PIPELINE: standalone — kein Manifest, kein Pipeline-State noetig
```

---

## Aufruf

```
/_answer {FRAGE} [@kontext]
```

- `FRAGE` — Die Frage, die beantwortet werden soll (Pflicht)
- `@kontext` — Optionale Datei- oder Verzeichnispfade fuer gezieltes Suchen

**Beispiele:**
```
/_answer "Warum ist Sperrgrund nullable?"
/_answer "Wie funktioniert VaultRouting?" @.claude/commands/_SC_orchestrate.md
```

---

## Ablauf

**Schritt 1 — Frage parsen**
- Frage und optionale @kontext-Angaben identifizieren
- Kernbegriffe extrahieren (Klasse, Methode, Feature, Konzept)

**Schritt 2 — EXTENSIV: Recherche**
- Glob: relevante Dateien finden (Namens-Muster, Verzeichnisse)
- Grep: Kernbegriffe suchen, Vorkommnisse lokalisieren
- Read: Relevante Stellen lesen, Zusammenhaenge verstehen
- Falls @kontext angegeben: dort priorisiert suchen
- Mindestens 3 unabhaengige Quellen pruefe (Code, Tests, Doku) wenn vorhanden

**Schritt 3 — EXTENSIV-Output**
Ausgabe als Abschnitt `## EXTENSIV`:
- Vollstaendige Erklaerung der Antwort
- Zusammenhaenge zwischen Komponenten beschreiben
- Jeden Beleg als `Datei:Zeile` angeben
- Annahmen explizit markieren wenn keine direkte Quelle gefunden

**Schritt 4 — KURZFORM-Output**
Ausgabe als Abschnitt `## KURZFORM`:
- Max 3-5 Saetze
- Copy-paste-fertig fuer Kollegen ohne Kontext
- Kein KI-Jargon ("Artefakt", "Prompt", "Worker", "Wave")
- Kein OmniCommand-Vokabular
- Pragmatisch, direkt, technisch korrekt

---

## Output-Format

```
## EXTENSIV

[Ausfuehrliche Erklaerung mit Datei:Zeile Belegen]

## KURZFORM

[3-5 Saetze, copy-paste-fertig]
```
