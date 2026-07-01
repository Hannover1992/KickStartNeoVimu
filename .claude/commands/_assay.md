---
type: satellite
---

# /_assay — Reflektiver Mini-Essay (Assay) als Tiefenverstaendnis-Report

```yaml
status: active
version: 2.1.0
created: 2026-03-02
updated: 2026-06-12
op: Assay
phase: Output
chain_position: standalone
difficulty_scaling: false
coldstart: true
```

## Zweck

Der Assay ist ein **Tiefenverstaendnis-Report** — ein kurzer, reflektiver Mini-Essay
den Claude schreibt um zu ZEIGEN, dass die Essenz einer Aufgabe, Forschung oder
Erkenntnis wirklich verstanden wurde.

**Komplement zu /_presentation:**
- `/_presentation` = technisch (Flowcharts, Diagramme, Architektur-Uebersichten)
- `/_assay` = reflektiv (Essenz, Nuancen, Tiefe — leicht lesbar, menschlich)

**Feynman-Prinzip angewendet auf Claude (W9):**
Wenn Claude die Essenz in eigenen Worten, kurz und klar erklaeren kann —
dann hat Claude die Aufgabe wirklich verstanden.
Wenn nur Oberflaechliches kommt — hat Claude die Tiefe nicht erfasst.
Der Assay macht das SICHTBAR (Spiegel-Analogie, W10).

---

## Aufruf

```
/_assay [{THEMA}] [expository|argumentative|reflective] [@kontext] [global=true] [bl=BL-XXX]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|--------------|
| THEMA | (OPTIONAL) | String | Die EINE Idee / Essenz die erfasst wird. Fehlt THEMA: aus Gespraechskontext herleiten. |
| style | expository | expository, argumentative, reflective | Essay-Stil |
| @kontext | (optional) | Dateipfad(e) | Kontext-Dateien zum Lesen (Coldstart-Modus) |
| global | false | true, false | **v2.1.0 (Pflaster 2026-06-12):** true = Assay auf Projekt-Ebene (.claude/output/) erzwingen. Default false = Assay gehoert in das Backlog-Item an dem gerade gearbeitet wird ({bl_folder}/Assays/). |
| bl | (optional) | BL-XXX / DCSRE-XXX | Explizite BL-ID — uebersteuert die automatische BL-Kontext-Aufloesung (Schritt 1.4). |

**Beispiele:**
```
# Nach einer SC-Phase — Essenz der Forschung erfassen:
/_assay "Warum die Stille-Post-Regel das Fundament der Wellen-Architektur ist"

# Argumentativ — Position zu einer Architektur-Entscheidung:
/_assay "Kurzlebige Agents sind besser als persistente Worker" argumentative

# Reflektiv — was bei einer schwierigen Aufgabe gelernt wurde:
/_assay "Was der PatternLibrary-Endlos-Loop ueber theoretische Analyse lehrt" reflective

# Coldstart mit Kontext:
/_assay "Die Essenz von First Principles Thinking" @.claude/crumbs/FirstPrinciples.md

# Zwischen Phasen — zeige Verstaendnis vor naechstem Schritt:
/_assay "Warum dieser SC-Zyklus 3 Iterationen brauchte"
```

---

## VERTRAG

```
+======================================================================+
| VERTRAG: /_assay                                                      |
+======================================================================+
|                                                                        |
| ACTOR: ASSAY WRITER (Claude)                                          |
|   TUT:                                                                 |
|     - Liest Kontext (Manifest, Model, Artefakte ODER @kontext)        |
|     - Erfasst die ESSENZ — nicht die Oberflaeche                      |
|     - Schreibt einen kurzen, reflektiven Mini-Essay (100-500 Woerter) |
|     - Wendet 4 Self-Checks an VOR dem Schreiben                       |
|     - Behandelt genau EINE Idee pro Assay (W1)                        |
|   NICHT:                                                               |
|     - Technische Dokumentation (→ /_presentation)                     |
|     - Zusammenfassung / Executive Summary (zu oberflaechlich)         |
|     - Bullet-Point-Listen (das ist kein Essay)                        |
|     - Flowcharts oder Diagramme (→ /_presentation)                    |
|     - Mehrere Themen in einem Assay (W1 Verletzung)                   |
|                                                                        |
| LIEST:                                                                 |
|   Kontext-Modus (automatisch erkannt):                                |
|   A) PIPELINE-MODUS (Manifest vorhanden + Feature aktiv):            |
|      1. {VAULT}/_manifest.md                                 |
|      2. .claude/models/{NAME}_Model.md                                |
|      3. .claude/analysis/synthese/{NAME}-*.md (letzte Artefakte)     |
|      4. {VAULT}/Task.md (Aufgaben-Kontext)                           |
|   B) COLDSTART-MODUS (@kontext angegeben ODER kein Manifest):        |
|      1. @kontext Dateien (falls angegeben)                            |
|      2. Eigenes Wissen / Gespraechs-Kontext                          |
|                                                                        |
| SCHREIBT (v2.1.0 BL-Routing, Pflaster 2026-06-12):                    |
|   DEFAULT (BL-Kontext aufloesbar, global!=true):                       |
|     1. {bl_folder}/Assays/Assay_{DATE}_{THEMA_CLEAN}.md               |
|        (Vault, im Backlog-Item an dem gerade gearbeitet wird;         |
|         Assays/-Ordner lazy erstellen — ADR-03)                       |
|   GLOBAL (global=true ODER kein BL-Kontext aufloesbar):               |
|     1. .claude/output/Assay_{DATE}_{THEMA_CLEAN}.md  (Projekt-Ebene) |
|                                                                        |
| POSITION:                                                              |
|   TYPE: STANDALONE (Satellit-Command)                                  |
|   EINSATZ: Zwischen beliebigen Phasen, nach Forschung, nach           |
|            Implementation, auf Anfrage, als Verstaendnis-Beweis       |
|   CHAIN: Keine feste Position — frei einsetzbar                       |
+======================================================================+
```

---

## Ablauf

### Schritt 0: Kontext erkennen und laden

```
1. @kontext angegeben?
   → JA: Lies die angegebenen Dateien. COLDSTART-MODUS.
   → NEIN: Weiter zu Schritt 0.2

2. Manifest vorhanden ({VAULT}/_manifest.md)?
   → JA: Lies Manifest. Bestimme aktuelles Feature/Phase.
         Lies zugehoerige Artefakte (Model, Synthese, Task.md).
         PIPELINE-MODUS.
   → NEIN: COLDSTART-MODUS. Nutze Gespraechs-Kontext + eigenes Wissen.

3. Bestimme Datum (YYYY-MM-DD) und Output-Pfad.
```

### Schritt 1: Parameter validieren

```
1. THEMA vorhanden?
   → JA: Verwende angegebenes THEMA.
   → NEIN: THEMA aus Gespraechskontext herleiten (AUTO-MODUS):
     a) Was wurde zuletzt im Chat besprochen / entschieden / entdeckt / geloest?
     b) Was war die relevanteste Erkenntnis oder Wendung in diesem Gespraech?
     c) Formuliere daraus EINE praegnante Thesen-Formulierung (Satz, kein Stichwort).
        Beispiel: "Warum THEMA wichtiger ist als X" oder "Was PROBLEM ueber Y lehrt"
     d) Gib vor dem Schreiben aus: "Assay-Thema (auto): {abgeleitetes THEMA}"

2. Style validieren:
   → expository (Default): Erklaere die Idee klar und direkt
   → argumentative: Nimm eine Position ein und begruende sie
   → reflective: Was wurde gelernt? Was war die tiefere Erkenntnis?
   → Unbekannt: WARNUNG + Fallback expository

3. Sanitize THEMA → {THEMA_CLEAN} (Leerzeichen→Underscore, Sonderzeichen weg)

4. OUTPUT-ROUTING (v2.1.0 Pflaster 2026-06-12 — Assay gehoert ins Backlog-Item):

   IF global == true:
     OUTPUT_PATH = .claude/output/Assay_{DATE}_{THEMA_CLEAN}.md
     → Logge: "[ASSAY] global=true → Projekt-Ebene"
   ELSE:
     BL-KONTEXT-AUFLOESUNG (Prioritaets-Kette, erste Quelle gewinnt):
       a) Expliziter Param: bl=BL-XXX
       b) Branch-Kontext: py -3 .claude/scripts/current_context.py --format=json
          → bl_id (nur wenn != null; auf generischen Branches wie
          feature/bdf-YYYY-MM-DD liefert das null — dann weiter zu c)
       c) Gespraechskontext: An welchem BL-Item wird in dieser Session
          GERADE gearbeitet? (Dieselbe Herleitung wie das feature:-Feld
          im Frontmatter — wenn du dort eine BL-ID einsetzen kannst,
          IST das der BL-Kontext.)
       d) Keine Quelle liefert BL-ID → FALLBACK global:
          OUTPUT_PATH = .claude/output/Assay_{DATE}_{THEMA_CLEAN}.md
          → Logge: "[ASSAY] Kein BL-Kontext aufloesbar → Fallback Projekt-Ebene
            (explizit erzwingen: bl=BL-XXX)"

     IF BL_ID aufgeloest:
       bl_folder = py -3 .claude/scripts/resolve_bl_path.py {BL_ID}
       mkdir -p {bl_folder}/Assays/        # lazy, ADR-03
       OUTPUT_PATH = {bl_folder}/Assays/Assay_{DATE}_{THEMA_CLEAN}.md
       → Logge: "[ASSAY] BL-Kontext: {BL_ID} → {bl_folder}/Assays/"
```

### Schritt 2: Self-Checks (VOR dem Schreiben)

Bevor du den Assay schreibst, pruefe dich selbst:

**G1 — 1-Idee-Check (W1):**
```
Habe ich genau EINE Idee identifiziert?
Wenn beim Nachdenken mehrere Ideen auftauchen: Waehle die EINE
die am tiefsten geht. Die anderen werden eigene Assays.
```

**G2 — Tiefenverstaendnis-Check (Feynman, W9):**
```
Kann ich diese Idee erklaeren ohne auf die Quellen zu schauen?
Kann ich die NUANCEN benennen — nicht nur die Oberflaeche?
Wenn ich stocke: Zurueck zum Kontext, tiefer lesen.
```

**G3 — Essenz-Check:**
```
Ist das was ich schreiben will die ESSENZ — oder nur eine Zusammenfassung?
Essenz = der Kern der Sache, das was bleibt wenn man alles Unwichtige wegstreicht.
Zusammenfassung = alles ein bisschen, nichts richtig tief.
Ein Assay ist KEIN Executive Summary.
```

**G4 — Stil-Passung:**
```
Passt der gewaehlte Stil zum Thema?
- Erklaerung einer Erkenntnis → expository
- Verteidigung einer Entscheidung → argumentative
- Reflexion ueber Gelerntes → reflective
```

### Schritt 3: Assay schreiben

Schreibe den Assay in die Output-Datei. Folge dem gewaehlten Stil:

---

**Expository (Erklaerung — Default):**

```
Struktur: Punkt → Erklaerung → (optional) Beispiel

Erklaere die EINE Idee klar, direkt, in eigenen Worten.
Kein Intro noetig — direkt zur Sache.
Wenn ein Beispiel die Idee greifbar macht: nutze es.
Schliesse mit einem Satz der die Idee auf den Punkt bringt.
```

**Argumentative (Position):**

```
Struktur: These → Begruendung → Fazit

Nimm eine klare Position ein. "X ist Y" — nicht "man koennte argumentieren".
Begruende mit Evidenz aus dem Kontext (Forschung, Code, Erfahrung).
Schliesse mit der Konsequenz: Was folgt daraus?
```

**Reflective (Reflexion):**

```
Struktur: Beobachtung → Bedeutung → Erkenntnis

Was wurde beobachtet/erlebt? (Konkret, nicht abstrakt)
Was bedeutet das — was ist die tiefere Implikation?
Was wurde daraus gelernt — was aendert sich dadurch?
```

---

**Formatierung der Output-Datei:**

```markdown
---
id: Assay_{DATE}_{THEMA_CLEAN}
type: assay
tags:
  - type/assay
  - style/{STYLE}
  - topic/{THEMA_CLEAN}
  - context/{PIPELINE|COLDSTART}
  - bl/{BL_ID}                      # nur wenn BL-Kontext aufgeloest (v2.1.0)
date: {DATE}
created: {DATE}
updated: {DATE}
feature: {NAME oder "standalone"}
bl-item: {BL_ID oder null}          # v2.1.0 — Pflicht wenn Assay im Vault landet
                                    # (vault_document_frontmatter_schema, BL-045 RF-06)
phase: {aktuelle Phase oder "coldstart"}
---

# {THEMA}

[Der Assay — 100-500 Woerter, EINE Idee, eigene Worte]
```

### Schritt 4: Post-Check und Output

```
1. Woerter zaehlen:
   < 100:   WARNUNG an dich selbst — ist die Idee vollstaendig ausgedrueckt?
            Ggf. vertiefen.
   100-500: PASS (Ziel-Bereich)
   > 500:   KUERZEN. Was kann weg ohne die Idee zu verlieren?
            Kuerze ist Staerke (W2). Kein Scrollen noetig.
   > 700:   AUFTEILEN. Das sind 2+ Assays.

2. Feynman-Selbsttest:
   Lies deinen Assay nochmal. Wuerde ein Mensch der die Aufgabe nicht kennt
   nach dem Lesen die ESSENZ verstehen? Wenn nein: umschreiben.

3. Datei schreiben: {OUTPUT_PATH}  (aus Schritt 1.4 — BL-Ordner ODER Projekt-Ebene)

4. TERMINAL-OUTPUT (PFLICHT):
   Gib den kompletten Assay IMMER im Terminal aus — direkt als Text,
   nicht nur den Dateipfad. Der User soll den Assay sofort lesen koennen.

   Format:
   ---
   **Assay** | {DATE} | {STYLE} | Feature: {NAME} | Phase: {PHASE} | Ziel: {BL_ID|global}

   # {THEMA}

   [Der volle Assay-Text]

   ---
   *~{N} Woerter | Datei: {OUTPUT_PATH}*
```

---

## One-Shot-Example (Leitfaden — SO soll ein Assay aussehen)

Dieser Assay wurde als erster Test des Commands geschrieben. Er dient als
**roter Faden** fuer Ton, Tiefe, Laenge und Struktur aller zukuenftigen Assays.

```markdown
---
id: Assay_2026-03-02_Wie_man_einen_Assay_schreibt
tags:
  - type/assay
  - style/expository
  - topic/Wie_man_einen_Assay_schreibt
  - context/pipeline
date: 2026-03-02
feature: Assay
phase: SC-DONE
---

# Wie man einen Assay schreibt

Das Wort kommt aus dem Franzoesischen: *essayer* — versuchen. Nicht berichten,
nicht zusammenfassen, nicht dokumentieren. Versuchen. Das ist der ganze Trick,
und er ist leicht zu uebersehen.

Wir haben heute ein Command gebaut, das Assays erzeugt, und dabei den Zweck
zweimal missverstanden. Erst dachten wir, der Assay sei ein Leer-Template, das
der User ausfuellt — ein Scaffold, eine Struktur ohne Inhalt. Dann korrigierte
der User: Nein, Claude soll schreiben. Der Assay ist ein Report. Aber nicht
irgendein Report. Er ist der Beweis, dass der Schreibende die Sache wirklich
verstanden hat.

Was unterscheidet einen Assay von einer Zusammenfassung? Die Zusammenfassung
sagt: hier sind die Fakten, geordnet. Der Assay sagt: hier ist, was ich
begriffen habe — und du kannst pruefen, ob das stimmt. Der Unterschied liegt
nicht in der Laenge oder im Format. Er liegt in der Verletzlichkeit. Ein Assay
kann falsch liegen. Eine Zusammenfassung kann hoechstens unvollstaendig sein.

Die zwei Regeln, die alles tragen: Eine Idee. Kurz. Eine Idee, weil Fokus
erzwingt, dass man weiss, was der Kern ist. Wer drei Punkte macht, hat keinen
Punkt. Kurz, weil Kuerze Klarheit erzwingt. Wer in 300 Woertern nicht auf den
Punkt kommt, hat den Punkt noch nicht gefunden.

Das Transkript, aus dem wir die Methodik gezogen haben, formuliert es so: Man
koennte den Assay nach dem Schreiben loeschen. Das Lernen haette trotzdem
stattgefunden. Das klingt paradox, ist aber der Kern. Der Wert liegt nicht im
Dokument. Er liegt im Zwang zur Destillation — im Moment, wo man entscheidet:
*das* ist wichtig, und *das* nicht.

Fuer ein AI-System hat das eine besondere Schaerfe. Claude kann beliebig viel
Text produzieren. Die Versuchung ist, alles zu sagen. Der Assay verbietet das.
Er fragt: Was ist die eine Sache, die du wirklich verstanden hast? Und wenn die
Antwort duenn ist, war das Verstaendnis duenn.

So schreibt man einen Assay: Man hoert auf, vollstaendig sein zu wollen, und
faengt an, ehrlich zu sein.
```

**Was dieses Example zeigt:**
- ~320 Woerter (im Zielbereich 100-500)
- EINE Idee: Der Assay ist ein Versuch, kein Bericht
- Eigene Stimme, keine Bullet-Points, kein Executive-Summary-Ton
- Konkreter Bezug zum Erlebten (das Missverstaendnis v1→v2)
- Schluss-Satz der die Essenz auf den Punkt bringt
- Ehrlich ueber eigene Fehler (zweimal missverstanden)

---

## Essenz (Warum der Assay funktioniert)

*essayer* (franzoesisch) = versuchen, erproben.

Der Assay ist kein Statusbericht. Er ist ein **Beweis fuer Verstaendnis**.
Wenn Claude nach einer komplexen Forschungsphase oder Implementation in 300 Woertern
die Essenz erfassen kann — klar, nuanciert, ohne Bullet-Points — dann hat Claude
die Aufgabe wirklich verstanden.

**Spiegel-Analogie (W10):** Der Assay macht sichtbar, ob die Tiefe da ist.
Eine oberflaechliche Zusammenfassung verraet sich sofort. Echtes Verstaendnis
erkennt man daran, dass die Nuancen stimmen — die kleinen Details, die nur
jemand sieht der wirklich hingeschaut hat.

**Prozess > Produkt (W11):** Der Wert des Assays liegt nicht im Dokument.
Er liegt darin, dass Claude GEZWUNGEN wird, die Essenz zu destillieren.
Diese Destillation ist der eigentliche Denkprozess.

**Kuerze als Disziplin (W2):** 500 Woerter Maximum zwingt zur Auswahl.
Was ist wirklich wichtig? Was kann weg? Diese Auswahl IST das Verstaendnis.

---

## EMAIL-VERSAND (nach Datei geschrieben + Terminal-Output)

**NUR wenn Output-Datei erfolgreich geschrieben wurde.**

Sende den Assay als **Email-Body** (KEIN Attachment — MD-Inhalt = Email-Inhalt):

```bash
python3 .claude/scripts/email_sender.py \
  "[OmniCommand] Assay: {THEMA}" \
  --body-from-file "{OUTPUT_PATH}"
```

**Fehlerbehandlung:** Falls Email fehlschlaegt (GMAIL_ADDRESS/GMAIL_APP_PASSWORD nicht gesetzt):
→ WARNUNG ausgeben, NICHT abbrechen. Datei + Terminal-Output sind trotzdem da.

---

## Fehler-Handling

```
+-------------------------------+--------------+-----------------------------------+
| Fehler                        | Typ          | Reaktion                          |
+-------------------------------+--------------+-----------------------------------+
| THEMA fehlt                   | NON-BLOCKING | AUTO-MODUS: Thema aus Chat-Kontext herleiten, ausgeben |
| Unbekannter Style             | NON-BLOCKING | WARNUNG + Fallback expository     |
| Output-Datei existiert        | NON-BLOCKING | Datum-Suffix anhaengen            |
| Manifest nicht lesbar         | NON-BLOCKING | COLDSTART-Modus (kein Kontext)    |
| BL-Kontext nicht aufloesbar   | NON-BLOCKING | Fallback Projekt-Ebene + Log-Hint |
|                               |              | "explizit: bl=BL-XXX" (v2.1.0)    |
| resolve_bl_path schlaegt fehl | NON-BLOCKING | Fallback Projekt-Ebene + WARNUNG  |
| Kontext zu duenn fuer Tiefe   | NON-BLOCKING | Ehrlich sagen: "Mein Verstaendnis |
|                               |              | ist begrenzt weil [Grund]"        |
| Email fehlgeschlagen          | NON-BLOCKING | WARNUNG + weiter (Datei existiert)|
+-------------------------------+--------------+-----------------------------------+
```

---

## Changelog

### v2.1.0 (2026-06-12) — Pflaster: Assay gehoert ins Backlog-Item (User-Direktive)

- **Default-Routing geaendert:** Assay landet im BL-Ordner an dem gerade gearbeitet
  wird ({bl_folder}/Assays/, lazy mkdir) statt pauschal .claude/output/.
- **BL-Kontext-Aufloesung** (Schritt 1.4): bl=-Param > Branch (current_context.py)
  > Gespraechskontext (analog feature:-Feld) > Fallback Projekt-Ebene mit Log.
  Live-Anlass: Assay zu BL-322 landete auf Projekt-Ebene, weil der generische
  Branch feature/bdf-YYYY-MM-DD bl_id=null liefert — Gespraechskontext wusste es.
- **global=true** Param: erzwingt Projekt-Ebene (.claude/output/) auf expliziten Wunsch.
- **Vault-Frontmatter-Konformitaet:** type/bl-item/created/updated + bl/{BL_ID}-Tag
  ergaenzt (vault_document_frontmatter_schema, BL-045 RF-06) — Pflicht sobald der
  Assay im Vault liegt (P-12 Rueckverfolgbarkeit).
- Forward-Verification + Satelliten-Sweep (gleiche Frage fuer /_presentation,
  /_answer, /_handout): getrackt im Backlog (Stealth-Intake 2026-06-12).
