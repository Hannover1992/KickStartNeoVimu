---
type: building-block
status: active
version: 1.0.0
created: 2026-05-17
op: ProvenanceExtractor
phase: Pre-Backlog
tier: sonnet
depends_on:
  - _backlog (intake)
feeds_into:
  - _A_orchestrate
  - _backlog (auto-promote)
related:
  - _W_fetch
backlog_origin: BL-160
ak_refs: [AK-3-REFINEMENT, AK-3-ERWEITERUNG]
---

# /_w_user_story_extended — Web-Agent-Prompt-Generator + Source-Konsistenz-Validator

**Status:** v1.0 (BL-160 AK-3 REFINED 2026-05-17, User-Direktive Prompt-Generator-Pattern)
**Actor:** PROVENANCE-EXTRACTOR
**Zweck:** Strukturiertes Prompt fuer Web-AI-Agent generieren + Output validieren + auto-promoten nach Vault. Kein nativer Web-Fetch (Auth-Huerden Confluence/Jira).

---

## Vertrag

```
+===========================================================================+
|  COMMAND: /_w_user_story_extended {URL} [--depth=2]                       |
|             [--story-type=user-story|task|spec]                           |
|             [--validate {drop_zone.md}]                                   |
+===========================================================================+
|                                                                           |
|  KERN-PROBLEM:                                                            |
|    Confluence/Jira hat SSO/MFA/Cookie-Auth — nativer In-Skill Fetch       |
|    scheitert. Web-AI-Agents (Gemini, ChatGPT, Claude.ai) koennen          |
|    Auth-Session des User-Browsers nutzen. Source-Konsistenz fehlt         |
|    ohne erzwungenes Quellen-Tagging.                                      |
|                                                                           |
|  KERN-PRINZIP (Prompt-Generator-Pattern):                                 |
|    Skill generiert strukturiertes Prompt → User kopiert in Web-Agent      |
|    → Web-Agent fetcht + extrahiert → User paste't in Drop-Zone            |
|    → Skill validiert + auto-promoted bei GREEN.                           |
|    Portable zwischen Web-AI-Agents, kein In-Skill-Auth noetig.           |
|                                                                           |
|  LIEST (Input):                                                           |
|    1. {URL}                — Confluence/Jira URL (Pflicht im Generate-Modus)|
|    2. {drop_zone.md}       — User-ausgefuellte Drop-Zone (nur --validate) |
|    3. pileOfMud/_index.md  — BL-ID-Ermittlung (falls noch nicht bekannt)  |
|                                                                           |
|  SCHREIBT (Output):                                                       |
|    1. pileOfMud/{BL-ID}_PROMPT_{DATE}.md     — Web-Agent-Prompt          |
|    2. pileOfMud/{BL-ID}_RAW_{DATE}.md        — leere Drop-Zone            |
|    3. pileOfMud/{BL-ID}_VALIDATION_FAIL_{DATE}.md  — nur bei FAIL        |
|    4. Backlog/{slug}/Sources/_pileOfMud_snapshot/  — nur bei GREEN        |
|                                                                           |
|  INVARIANTEN:                                                             |
|    INV-PROV-1: Prompt-Datei MUSS Source-Comment-Pflicht + Anti-Halluzination enthalten|
|    INV-PROV-2: Drop-Zone enthaelt NUR Frontmatter-Template — kein Inhalt-Praefill   |
|    INV-PROV-3: Validator-Lauf ist idempotent (Re-Run safe)                |
|    INV-PROV-4: Auto-Promote erst nach Validator GREEN — NIE bei FAIL      |
|    INV-PROV-5: pileOfMud-Original bleibt erhalten (haendischer Sync-Punkt)|
+===========================================================================+
```

---

## Aufruf

| Parameter | Default | Werte | Beschreibung |
|---|---|---|---|
| `{URL}` | — | beliebige URL | Confluence-Page, Jira-Ticket (Pflicht ohne --validate) |
| `--depth` | `1` | `1`, `2`, `3` | Tiefe fuer verlinkte Child-Pages |
| `--story-type` | `user-story` | `user-story`, `task`, `spec` | Steuert Output-Schema im Prompt |
| `--validate {file}` | — | Pfad zu Drop-Zone | Wechselt in Validate-Modus statt Generate |

**Beispiele:**
```
/_w_user_story_extended https://confluence.example.com/pages/406159586
/_w_user_story_extended https://jira.example.com/browse/PROJ-123 --story-type=task --depth=2
/_w_user_story_extended --validate pileOfMud/BL-123_RAW_2026-05-17.md
```

---

## Workflow-Sequenz (8-Step)

```
1. User:          /_w_user_story_extended {URL}
2. Skill:         schreibt {BL-ID}_PROMPT_{DATE}.md + leere Drop-Zone {BL-ID}_RAW_{DATE}.md
3. User:          oeffnet Prompt-Datei, kopiert Inhalt in Web-AI-Agent (Gemini / ChatGPT / Claude.ai)
4. Web-AI-Agent:  fetcht URL + extrahiert strukturiert + antwortet mit Source-getaggtem Output
5. User:          paste't Web-Agent-Output in pileOfMud/{BL-ID}_RAW_{DATE}.md
6. User:          /_w_user_story_extended --validate pileOfMud/{BL-ID}_RAW_{DATE}.md
7. Skill:         validiert Source-Konsistenz — bei GREEN: auto-promote nach Vault-Snapshot
8. Skill:         triggert /_A_orchestrate {BL-ID} (Pipeline-Start)
```

---

## Modus 1 — Generate (Default, ohne --validate)

**Trigger:** `/_w_user_story_extended {URL} [--depth=N] [--story-type=X]`

**Pseudocode:**
```
FUNCTION generate(url, depth, story_type):
  bl_id   = derive_bl_id_from_url_or_prompt(url)  // z.B. aus pileOfMud/_index.md oder User-Input
  date    = today_iso()                             // 2026-05-17
  slug    = slugify(url)                            // url-basierter Kurzname
  
  prompt_path = "pileOfMud/{bl_id}_PROMPT_{date}.md"
  raw_path    = "pileOfMud/{bl_id}_RAW_{date}.md"
  
  // INV-PROV-1: Prompt-Datei mit Anti-Halluzinations-Pflicht + Source-Comment-Zwang
  write(prompt_path, render_prompt_template(url, depth, story_type))
  
  // INV-PROV-2: Drop-Zone nur mit Frontmatter-Template, kein Inhalt-Praefill
  write(raw_path, render_dropzone_template(url, bl_id, date))
  
  OUTPUT:
    "Prompt-Datei: {prompt_path}"
    "Drop-Zone:    {raw_path}"
    "Naechster Schritt: Oeffne Prompt-Datei, kopiere Inhalt in Web-AI-Agent"
    "Dann: Paste Web-Agent-Output in Drop-Zone, dann: --validate {raw_path}"
```

**Erwartetes Output:**
- `pileOfMud/{BL-ID}_PROMPT_{DATE}.md` — vollstaendiges Prompt an Web-AI-Agent
- `pileOfMud/{BL-ID}_RAW_{DATE}.md` — leere Drop-Zone mit Frontmatter-Template
- Terminal-Ausgabe mit naechsten Schritten fuer User

---

## Modus 2 — Validate (--validate {drop_zone.md})

**Trigger:** `/_w_user_story_extended --validate pileOfMud/{BL-ID}_RAW_{DATE}.md`

**Pseudocode:**
```
FUNCTION validate(drop_zone_path):
  content = read(drop_zone_path)
  errors  = []
  
  // Regel V-1: Frontmatter-Pflichtfelder
  FOR field IN [source_url, fetched_at, source_kind, page_id]:
    IF field NOT IN frontmatter OR frontmatter[field] == "":
      errors.append("V-1: Pflichtfeld '{field}' fehlt oder leer")
  
  // Regel V-2: Jede Section >= 1 source-Comment
  sections = extract_sections(content)
  FOR section IN sections:
    IF count("<!-- source:", section) == 0:
      errors.append("V-2: Section '{section.title}' hat kein <!-- source: ... --> Comment")
  
  // Regel V-3: URL-Erreichbarkeit (best-effort, kein Pflicht-Block bei Offline)
  urls = extract_source_urls(content)
  FOR url IN urls:
    status = http_head(url)
    IF status NOT IN [200, 302] AND status != "offline":
      errors.append("V-3 (best-effort): URL '{url}' nicht erreichbar (HTTP {status})")
  
  IF errors:
    fail_path = derive_fail_path(drop_zone_path)
    write(fail_path, render_fail_report(errors, drop_zone_path))
    OUTPUT: "VALIDATION FAIL — {len(errors)} Fehler. Report: {fail_path}"
    EXIT
  
  // GREEN — INV-PROV-4: Auto-Promote erst jetzt
  bl_id = extract_bl_id(drop_zone_path)
  snapshot_path = "Backlog/{bl_id}/Sources/_pileOfMud_snapshot/"
  copy(drop_zone_path, snapshot_path)          // INV-PROV-5: Original bleibt in pileOfMud
  
  Skill(_backlog, mode=intake, source=snapshot_path)
  Skill(_A_orchestrate, bl_id)
  
  OUTPUT: "VALIDATION GREEN — Promoted nach {snapshot_path}, Pipeline gestartet"
```

**Validator-Exit-Codes:**
| Code | Bedeutung |
|---|---|
| `GREEN` | Alle Pflicht-Regeln erfuellt, Auto-Promote ausgefuehrt |
| `FAIL` | Mindestens ein Fehler — Fail-Report geschrieben, kein Promote |
| `ERROR` | Drop-Zone-Datei nicht lesbar oder fehlt |

---

## Prompt-Template (eingebettet im Skill)

Dieser Block wird in `{BL-ID}_PROMPT_{DATE}.md` geschrieben:

```markdown
# Auftrag an Web-AI-Agent — Source-Extraktor fuer User-Story

**ROLLE:** Du bist ein Source-treuer Extractor fuer User-Stories aus Confluence/Jira.
Deine Aufgabe ist es, strukturierten Output zu produzieren, bei dem JEDE Aussage
auf eine konkrete Quellenposition zurueckgefuehrt werden kann.

---

## Ziel

Lese folgende URL: {URL}
Tiefe: {DEPTH} (folge verlinkten Child-Pages bis Tiefe {DEPTH})
Story-Typ: {STORY_TYPE}

Extrahiere:
- User-Story (Als/Moechte/Damit)
- Alle Akzeptanzkriterien (nummeriert)
- Akkordeons / Aufklappsektionen (vollstaendig)
- DoR-Items (Definition of Ready)
- Tabellen (vollstaendig, mit Header)

---

## Output-Schema (STRIKT einhalten)

Beginne die Antwort mit diesem YAML-Frontmatter-Block:

\`\`\`yaml
---
source_url: {URL}
source_kind: confluence|jira|other   # zutreffendes auswaehlen
page_id: ""                          # Confluence Page-ID oder Jira Ticket-Key
fetched_at: ""                       # ISO-Datetime deines Fetch-Zeitpunkts
depth_fetched: {DEPTH}
story_type: {STORY_TYPE}
---
\`\`\`

Danach folgen die Sections:

### User-Story
Als [Rolle] <!-- source: {URL}#user-story-anchor -->
moechte ich [Ziel] <!-- source: {URL}#user-story-anchor -->
damit [Nutzen] <!-- source: {URL}#user-story-anchor -->

### Akzeptanzkriterien
- AK-1: [Text] <!-- source: {URL}#ak-section-anchor -->
- AK-2: [Text] <!-- source: {URL}#ak-section-anchor -->

### Akkordeons (falls vorhanden)
#### [Akkordeon-Titel]
[Inhalt] <!-- source: {URL}#akkordeon-anchor -->

### DoR-Items (falls vorhanden)
- [ ] [Item-Text] <!-- source: {URL}#dor-anchor -->

### Tabellen (falls vorhanden)
<!-- source: {URL}#tabellen-anchor -->
| Spalte 1 | Spalte 2 |
|---|---|
| Wert | Wert |

---

## Konsistenz-Regeln (PFLICHT — keine Ausnahmen)

1. JEDE Aussage, jeder Stichpunkt, jede Tabellenzeile MUSS einen
   `<!-- source: {URL}#anchor -->` Comment haben.
   Anchor = konkreter Seitenabschnitt (ID, Ueberschrift-Slug, o.ae.)

2. Wenn eine Information NICHT in der Quelle steht: schreibe `<MISSING>`.
   NIEMALS Informationen erfinden oder aus Allgemeinwissen ersetzen.

3. Bei verlinkten Child-Pages: gleiche Regeln gelten pro Unter-URL.
   Nutze den jeweiligen Child-URL als source-Wert.

4. Tabellen: Source-Comment steht direkt ueber der Tabelle (nicht in jeder Zeile).

5. Frontmatter: source_url und fetched_at MUESSEN gesetzt sein.
   page_id: Confluence Page-ID aus der URL oder Seiteninfo extrahieren.

---

## Beispiel (korrekt formatierter Output-Ausschnitt)

\`\`\`
### Akzeptanzkriterien
- AK-3: Der Fahrer erhaelt eine Push-Benachrichtigung <!-- source: https://confluence.example.com/pages/406159586#ak-3 -->
- AK-4: Benachrichtigung enthaelt Auftragsdetails <!-- source: https://confluence.example.com/pages/406159586#ak-4 -->

### Akkordeons
#### 11.4 Fahrdienst Ausserhalb Vertragsleistung
Beschreibung der Regelung... <!-- source: https://confluence.example.com/pages/406159586#akkordeon-11-4 -->
\`\`\`

---

**Wichtig:** Liefere den vollstaendigen Output in einem einzigen Antwort-Block.
Der Output wird direkt in eine Drop-Zone-Datei eingefuegt und maschinell validiert.
```

---

## Drop-Zone-Frontmatter-Template

Dieser Block wird in `{BL-ID}_RAW_{DATE}.md` geschrieben (kein weiterer Inhalt):

```markdown
---
source_url: ""
source_kind: ""
page_id: ""
fetched_at: ""
depth_fetched: 1
story_type: user-story
generated_by: _w_user_story_extended
prompt_file: "{BL-ID}_PROMPT_{DATE}.md"
validated: false
---

<!-- Hier den Web-Agent-Output einfuegen. -->
<!-- Danach: /_w_user_story_extended --validate {BL-ID}_RAW_{DATE}.md -->
```

---

## Validator-Schema

**Regel V-1 — Frontmatter-Pflichtfelder:**
- `source_url` — gesetzt, nicht leer, valide URL
- `fetched_at` — gesetzt, nicht leer
- `source_kind` — gesetzt, Wert in `[confluence, jira, other]`
- `page_id` — gesetzt, nicht leer

**Regel V-2 — Source-Comments:**
- Jede Markdown-Section (`## ...`, `### ...`) enthaelt mind. 1 `<!-- source: ... -->` Comment
- Ausnahmen: Frontmatter-Block, rein-strukturelle Ueberschriften ohne Inhalt

**Regel V-3 — URL-Erreichbarkeit (best-effort):**
- HTTP HEAD fuer jede in source-Comments genannte URL
- Akzeptierte Status-Codes: 200, 301, 302
- Bei Netzwerk-Ausfall / Offline: Warnung ohne Block (kein FAIL)
- Bei HTTP 404/403/500: Warnung im Fail-Report, aber kein zwingender FAIL
- Regel V-3 blockiert NICHT den Promote-Pfad (best-effort)

**Fail-Report-Format (`{BL-ID}_VALIDATION_FAIL_{DATE}.md`):**
```markdown
# Validation FAIL — {drop_zone_path}
Datum: {ISO-DATE}

## Fehler

| Nr | Regel | Beschreibung | Korrektur-Vorschlag |
|---|---|---|---|
| 1 | V-1 | Pflichtfeld 'source_url' leer | Frontmatter source_url setzen |
| 2 | V-2 | Section '### Akkordeons' ohne source-Comment | <!-- source: {URL}#anchor --> ergaenzen |

## Naechste Schritte
1. Oeffne {drop_zone_path}
2. Behebe alle Fehler gemaess Tabelle
3. Fuelle fehlende source-Comments nach
4. Fuehre erneut aus: /_w_user_story_extended --validate {drop_zone_path}
```

---

## INVARIANTEN

- **INV-PROV-1:** Prompt-Datei MUSS `<!-- source: -->`-Pflicht-Sektion + Anti-Halluzinations-Klausel (`<MISSING>` statt Erfinden) enthalten.
- **INV-PROV-2:** Drop-Zone enthaelt ausschliesslich Frontmatter-Template + Einfuege-Hinweis — kein Inhalt-Praefill.
- **INV-PROV-3:** Validator-Lauf ist idempotent — mehrfaches Ausfuehren derselben Drop-Zone erzeugt konsistenten Ergebnis (kein Doppel-Promote, kein Datei-Konflikt bei Fail-Reports).
- **INV-PROV-4:** Auto-Promote nach `Backlog/{slug}/Sources/_pileOfMud_snapshot/` erfolgt ausschliesslich nach Validator GREEN. Bei FAIL kein Promote.
- **INV-PROV-5:** pileOfMud-Original bleibt nach Promote erhalten (haendischer Sync-Punkt, BL-160 Z204).

---

## Fehlerbehandlung

| Fehler-Typ | Aktion |
|---|---|
| URL nicht angegeben (Generate-Modus) | Abbruch mit Hinweis: "URL Pflicht-Parameter fehlt" |
| Drop-Zone-Datei nicht gefunden (--validate) | Abbruch mit Fehler-Pfad + Hinweis |
| Drop-Zone leer (nur Frontmatter, kein Inhalt) | FAIL mit Hinweis "Kein Web-Agent-Output eingefuegt" |
| Frontmatter nicht parsebar | FAIL mit Zeile + Kontext |
| pileOfMud-Verzeichnis fehlt | Verzeichnis anlegen, dann fortfahren |
| Snapshot-Zielverzeichnis fehlt | Anlegen + kopieren |
| HTTP HEAD Fehler (V-3) | Warnung in Fail-Report, kein Hard-FAIL |
| BL-ID nicht ableitbar | User-Prompt: "Bitte BL-ID angeben (z.B. BL-160)" |

---

## Namensgebung Ausgabe-Dateien

```
pileOfMud/
  {BL-ID}_PROMPT_{YYYY-MM-DD}.md       — Prompt an Web-AI-Agent
  {BL-ID}_RAW_{YYYY-MM-DD}.md          — Drop-Zone (User-Paste)
  {BL-ID}_VALIDATION_FAIL_{YYYY-MM-DD}.md  — Fehler-Report (nur bei FAIL)

Backlog/{slug}/Sources/_pileOfMud_snapshot/
  {BL-ID}_RAW_{YYYY-MM-DD}.md          — Promote-Kopie (nur bei GREEN)
```

Wenn am selben Tag mehrere Laeufe: Suffix `_v2`, `_v3` anhaengen.

---

## Verwandte Commands

- `/_backlog` (mode=intake) — Auto-Promote-Ziel nach GREEN
- `/_A_orchestrate` — Pipeline-Trigger nach Promote
- `/_W_fetch` — verwandter Knowledge-Scout (Cache/Graph-Traversal-orientiert vs. dieser Web-Fetch-orientiert)

ARGUMENTS: {URL} [--depth=N] [--story-type=user-story|task|spec] [--validate {drop_zone.md}]
