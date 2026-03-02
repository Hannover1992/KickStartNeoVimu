---
status: active
version: 1.0.0
created: 2026-02-26
op: ReviewCycle
phase: Meta
type: command
chain_position: standalone
changelog: |
  v1.0.0: Initialer Entwurf. Erstellt strukturiertes Evidence-Dokument
          aus Freitext-Beschreibung. 1-Satz PR-Justification als Output.
          Obsidian-Sync via _W_obsidianSync. Wird von /_R_orchestrate
          als Kontext gelesen (LIEST: analysis/evidence/*.md).
---

# /_R_evidence — Evidence-Dokument erstellen

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_R_evidence                                               ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    $description          (Freitext: Problem + Entscheidung)         ║
║    $code_files           (optional: konkrete Dateipfade)            ║
║    .claude/analysis/evidence/*.md  (Duplikat-Check)                 ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/analysis/evidence/EVIDENCE-{FEATURE}-{SLUG}-{DATE}.md   ║
║    (optional) C:\Users\...\DCS\{SLUG}.md  (via Obsidian-Sync)      ║
║                                                                      ║
║  AUSGABEN:                                                           ║
║    Evidence-Dokument (strukturiert, PR-ready)                        ║
║    1-Satz PR-Justification (direkt kopierbar)                        ║
║    Obsidian-Sync (wenn konfiguriert)                                 ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    NIE Code aendern (Analysis-only)                                  ║
║    NIE bestehende Evidence ueberschreiben (nur NEU erstellen)        ║
║    NIE Team spawnen (Solo-Command, Team Lead fuehrt aus)             ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

```
+======================================================================+
| META-COMMAND: /_R_evidence                                           |
+======================================================================+
|                                                                      |
| ACTOR: TEAM LEAD (DU — direkt, kein Worker-Spawn)                   |
|                                                                      |
| ZWECK: Technische Entscheidung atomisch dokumentieren.               |
|   Eingabe = Freitext (Problem + Entscheidung + ggf. Code).          |
|   Ausgabe = Evidence-Dokument (strukturiert) + 1-Satz PR-Summary.   |
|                                                                      |
| WANN:                                                                |
|   - WAEHREND oder NACH einer Code-Aenderung die Fragen provoziert   |
|   - NACH einem /_R_orchestrate Review der neue Evidence enthüllt    |
|   - VOR einem PR wenn der Architekt sicher Fragen stellen wird      |
|   - IMMER wenn "das muss ich spaeter erklaeren koennen"             |
|                                                                      |
| OUTPUT-NUTZUNG:                                                      |
|   - PR-Kommentar: 1-Satz direkt einfuegen (präemptiv)              |
|   - Architect-Frage: Evidence zeigen                                 |
|   - /_R_orchestrate: liest evidence/*.md automatisch als Kontext    |
|   - Obsidian: dauerhaftes Wissens-Atom                              |
+======================================================================+
```

---

## Aufruf

```
/_R_evidence "{description}" [{feature}] [{type}]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `description` | (PFLICHT) | Freitext | Problem + Entscheidung + optionaler Code |
| `feature` | aktuell aus _manifest.md | String | z.B. "DCSRE-93", "DCSRE-881" |
| `type` | constraint | analyse, constraint, risk | Art der Evidence |

**type-Bedeutung:**

| Typ | Wann | Beispiel |
|-----|------|---------|
| `constraint` | "Darf NICHT weil..." (technische Einschraenkung) | Junction-Tabelle kein TrackableEntityBase |
| `analyse` | "Haben untersucht und festgestellt..." (Analyse-Ergebnis) | LandesverbandBasicReadDto reicht aus |
| `risk` | "Wenn wir X tun riskieren wir Y..." | Ohne Ignores: EF Core loescht Daten |

**Beispiele:**
```
/_R_evidence "Junction-Tabelle kein TrackableEntityBase weil surrogate Id"
/_R_evidence "AutoMapper 11 Ignores wegen IdentityCrudDbProvider" DCSRE-881 risk
/_R_evidence "LandesverbandBasicReadDto statt Minimal — FE braucht nur Id+Name" DCSRE-93 analyse
```

---

## ABLAUF (Team Lead fuehrt aus — kein Worker-Spawn)

### Schritt 1: Description parsen

Extrahiere aus `$description`:
- **Problem-Kern:** Was war das technische Problem?
- **Entscheidung:** Was wurde entschieden (und was wurde NICHT gemacht)?
- **Mechanismus:** Warum erzwingt die Basis-Klasse/Pattern das Problem?
- **Code-Referenzen:** Welche Dateien/Klassen sind betroffen?

Falls Code-Snippets in description enthalten → direkt verwenden.
Falls Dateipfade genannt → lesen mit Read-Tool.

### Schritt 2: Duplikat-Check

Lies `.claude/analysis/evidence/*.md` kurz:
- Gibt es bereits eine Evidence zu diesem Problem?
- Wenn JA → ABBRUCH, zeige User: "Evidence existiert bereits: {datei}"
- Wenn NEIN → weiter

### Schritt 3: Evidence-Dokument schreiben

**Dateiname:** `EVIDENCE-{FEATURE}-{SLUG}-{DATE}.md`
- `{FEATURE}`: aus Parameter oder _manifest.md NAME (OHNE Bindestrich im Dateinamen: "DCSRE93")
- `{SLUG}`: 3-4 Worte aus dem Kern-Problem, kebab-case (z.B. "junction-kein-trackable")
- `{DATE}`: YYYY-MM-DD

**Speicherort:** `.claude/analysis/evidence/`

**Format:**

```yaml
---
id: EVIDENCE-{FEATURE}-{SLUG}-{DATE}
feature: '{FEATURE-MIT-BINDESTRICH}'  # z.B. 'DCSRE-93'
type: constraint  # oder: analyse | risk
status: VERIFIED
date: {DATE}
author: team-lead
tags:
  - type/evidence
  - op/{FEATURE}
  - topic/{hauptthema}
entscheidung: "{1-Satz was entschieden wurde}"
warum: "{1-Satz mechanistische Begründung}"
---
```

**Pflicht-Sektionen:**

```markdown
# Evidence: {Titel}

**Datum:** {DATE}
**Feature:** {FEATURE}
**Typ:** constraint | analyse | risk

---

## Problem

[Was war das technische Problem? Mechanismus beschreiben, nicht Symptome.]
[Code-Snippet der FALSCHEN Variante wenn möglich]

## Entscheidung

[Was wurde gemacht? Was wurde NICHT gemacht und warum?]
[Code-Snippet der RICHTIGEN Variante]

## Mechanismus / Begründung

[Warum erzwingt die Architektur diese Entscheidung?
 Vererbungsketten, EF-Core-Verhalten, Interface-Constraints etc.]

## Regel

> **{Generalisierte Regel als 1 Satz — gilt für alle ähnlichen Fälle}**

---

## PR-Justification (direkt verwendbar)

**Kurz (PR-Kommentar):**
> "{max. 1 Satz, technisch präzise, für Architekt verständlich}"

**Lang (falls nachgefragt):**
> "{2-3 Sätze, mit Mechanismus}"

---

## Dateipfade

| Rolle | Pfad |
|-------|------|
| {Entity/Klasse} | {relativer Pfad} |
```

### Schritt 4: 1-Satz PR-Justification ausgeben

Nach dem Schreiben: direkt im Chat ausgeben:

```
✅ Evidence erstellt: .claude/analysis/evidence/EVIDENCE-{...}.md

PR-Justification (kurz):
"{der 1-Satz}"

PR-Justification (lang):
"{2-3 Sätze}"

Regel:
"{die generalisierte Regel}"
```

### Schritt 5: Obsidian-Sync

Lies `.claude/analysis/_manifest.md` → VAULT-Pfad extrahieren.

Sync die Evidence-Datei via `/_W_obsidianSync` (easy-Modus):
- Quelle: `.claude/analysis/evidence/EVIDENCE-{...}.md`
- Ziel: `{VAULT}/EVIDENCE-{...}.md`
- Obsidian-Frontmatter ergaenzen: `type: evidence`, `feature: {FEATURE}`, `tags: [evidence, {FEATURE}]`

Falls VAULT nicht konfiguriert → SKIP mit Hinweis: "Obsidian-Sync nicht konfiguriert."

---

## Output-Beispiel

Eingabe:
```
/_R_evidence "VersorgungsvertragSpezialisierungEntity erbt nicht von TrackableEntityBase weil EntityBase<Guid> eine surrogate [Key] Id erzeugt — Junction-Tabelle hat composite PK via UsingEntity" DCSRE-93 constraint
```

Ausgabe:
```
✅ Evidence erstellt:
   .claude/analysis/evidence/EVIDENCE-DCSRE93-junction-kein-trackable-2026-02-26.md

PR-Justification (kurz — direkt in PR-Kommentar):
"Junction-Tabelle → kein TrackableEntityBase (EntityBase<Guid> würde surrogate [Key] Id erzwingen);
 composite PK via UsingEntity im DbContext."

PR-Justification (lang — für Architekt-Nachfrage):
"VersorgungsvertragSpezialisierungEntity erbt bewusst nicht von TrackableEntityBase, weil
 TrackableEntityBase→EntityBase<Guid> automatisch [Key] public Guid Id hinzufügt — das
 korrumpiert den kompositären PK (VersorgungsvertragId + SpezialisierungId). Tracking-Felder
 werden stattdessen explizit deklariert, der composite PK implizit via UsingEntity konfiguriert."

Regel:
"Junction-Tabellen mit kompositärem PK erben NIE von TrackableEntityBase."

📎 Obsidian-Sync: EVIDENCE-DCSRE93-junction-kein-trackable-2026-02-26.md → Vault
```

---

## Integration mit /_R_orchestrate

`/_R_orchestrate` liest ab v1.1 automatisch `.claude/analysis/evidence/*.md` als Kontext
für Welle 1 (RAG-Scan) und Welle 3 (DickBob-Synthese).

Das bedeutet: Wenn du nach `/_R_evidence` ein `/_R_orchestrate` aufrufst,
kennt Uncle Bob bereits die dokumentierten Entscheidungen und kann sie
im Review zitieren statt sie neu zu entdecken.

**Empfohlener Flow:**
```
1. Code schreiben (technische Entscheidung getroffen)
2. /_R_evidence "{beschreibung}"
   → Evidence-Dokument + 1-Satz PR-Summary
3. PR erstellen → 1-Satz preemptiv in PR-Beschreibung einfügen
4. (optional) /_R_orchestrate → Uncle Bob kennt Evidence als Kontext
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Evidence bereits vorhanden | ABBRUCH + Pfad der existierenden Evidence zeigen |
| Datei-Pfad nicht lesbar | Ohne Code-Kontext schreiben, Warnung ausgeben |
| feature nicht ermittelbar | Fragt User nach Feature-Name |
| Vault nicht konfiguriert | Obsidian-Sync überspringen, Hinweis ausgeben |
