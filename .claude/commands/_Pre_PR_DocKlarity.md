---
name: _Pre_PR_DocKlarity
description: Pre-PR XML-Doc Klarheit - entfernt kryptische Referenzen, Ticket-Nummern und internen Jargon aus XML-Summaries
type: building-block
---

# /_Pre_PR_DocKlarity

**Zweck:** XML-Dokumentation verstaendlich machen. Kryptische interne Referenzen, Jira-Ticket-Nummern und Jargon aus allen `///`-Kommentaren entfernen. Nur beschreibende, klare Sprache.

**Scope:** Ausschliesslich `*.cs` Dateien im Branch-Diff (`develop...HEAD`)

**Auto-Fix:** JA — kryptische Teile direkt entfernen, Kern-Aussage behalten

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════╗
║  COMMAND: /_Pre_PR_DocKlarity                                ║
╠══════════════════════════════════════════════════════════════╣
║  LIEST:                                                      ║
║    1. Git Diff (develop...HEAD) — DIRTY-Scope ermitteln      ║
║    2. Alle *.cs Dateien im DIRTY-Scope                       ║
║    3. Nur /// XML-Kommentar-Zeilen                           ║
║  SCHREIBT:                                                   ║
║    1. Auto-Fix direkt in *.cs Dateien (kryptische Teile)     ║
║    2. Bericht als Terminal-Output                            ║
║  SCHREIBT NICHT:                                             ║
║    1. Keine neuen XML-Doc-Gerueste (das macht _Dokumentation)║
║    2. Keine Aenderungen ausserhalb von XML-Docs              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: DIRTY-Scope ermitteln

```bash
git diff --name-only develop...HEAD | grep "\.cs$" | grep -v "\.Designer\.cs$" | grep -v "Migrations/"
```

Ergebnis: Liste aller `.cs` Dateien die im Branch geaendert wurden.

**Output:**
```
DIRTY-SCOPE: [N] CS-Dateien gefunden
  Beispiele: DicGatewayAdapter.cs, DicFileMetadataJson.cs, ...
```

Falls 0 Dateien → PASS (nichts zu pruefen) → EXIT 0.

---

## Schritt 1: Kryptische Muster erkennen

Alle XML-Kommentar-Zeilen (`///`) in jeder DIRTY-CS-Datei scannen.

### Verbotene Muster (KRYPTISCH)

| Kategorie | Muster | Beispiel | Schwere |
|-----------|--------|---------|--------|
| Jira-Tickets | `[A-Z]+-\d{3,6}` | DCSRE-881, DCSP-1317 | AUTO-FIX |
| Test-IDs | `\bT\d{1,3}\b` | T0, T15, T1-T5 | AUTO-FIX |
| Sub-Test-IDs | `\bST\d{1,3}\b` | ST1, ST3 | AUTO-FIX |
| Slice-Nummern | `\b(S\d{1,2}\|Slice[-_]?\d{1,2})\b` | S1, Slice4, Slice-2 | AUTO-FIX |
| Wahrheiten | `\bW\d{1,3}\b` | W1, W42 | AUTO-FIX |
| Akzeptanzkriterien | `\bAK\d{1,3}\b` | AK1, AK15 | AUTO-FIX |
| Interne Docs | `\b\w+(PLAN\|ATOMIC\|VERIFY\|MODEL\|SPEC\|GAP)\b` | DIC-PLAN.md | AUTO-FIX |
| Referenz-Saetze | `Referenz:\s*.+\.md` | Referenz: HappyPath-PLAN.md | AUTO-FIX |
| Interne Jargon | `ist das FUNDAMENT` / `GRAY\|ORANGE\|RED Pattern` | "T0 ist das FUNDAMENT" | AUTO-FIX |
| Ticket-URLs | `projekte\.itsg\.de.+DCSRE-\d+` | URL zu Jira | AUTO-FIX |
| EM-Felder | `\bEM\d{4}\b` | EM0012 | AUTO-FIX |
| Sidecar | `[Ss]idecar\b` | JSON-Sidecar-DTO | AUTO-FIX |
| PB-Datei | `\bPB-Datei\b` | neben der PB-Datei | ERSETZE mit "Nutzdatei" |
| Test-Querverweise | `\b\w*(Tests?)\b` in `/// <summary>` | "Getestet in DicGatewayAdapterTests" | AUTO-FIX |
| Test-Querverweise | `getestet in\|wird getestet\|Test fuer\|siehe.*Test` | "wird getestet in ..." | AUTO-FIX |
| Test-Nummern-Prefix | `^Test #?\d+[a-z]?:` am Satzanfang | "Test #5b: GetFile..." | AUTO-FIX (Prefix entfernen) |
| Root-Cause-Satz | `Root\s*Cause:\|Root-Cause:` | "Root Cause: SFTP bekam..." | AUTO-FIX (ganze Zeile entfernen) |
| OmniCommand-Jargon | Stage-bezogen | "Stage 2 Wiring-Tests", "S1-S5" | AUTO-FIX |
| OmniCommand-Jargon | Pipeline-bezogen | "SC-FULL", "SC-INLINE", "Hub-Invariante" | AUTO-FIX |
| OmniCommand-Jargon | TDD-bezogen | "TDD RED", "TDD GREEN", "Red/Green/Refactor" | AUTO-FIX |
| OmniCommand-Jargon | Factory-bezogen | "Dark Factory", "Parking-Lot", "Big Dark Factory" | AUTO-FIX |
| OmniCommand-Jargon | Wellen-bezogen | "Welle 1", "W1 Haiku", "Wellen-Pattern" | AUTO-FIX |
| Unerklärte Abkuerzungen | Nackte 2-Buchstaben-Kombis ohne Kontext | BK, KV, PE, IK, BO, PB, FA (solo) | WARNUNG |

### Regel: Unerklärte Abkuerzungen (WARNUNG, kein Auto-Fix)

Abkuerzungen die ALLEIN stehen — ohne Vollform im gleichen Satz — koennen nicht
automatisch aufgeloest werden (Halluzinationsrisiko). Daher: WARNUNG + manuelle Action.

```
WARNUNG: Abkuerzung ohne Erklaerung in XML-Doc
  Datei: DicFileImportService.cs:12
  Text:  "Verarbeitet BK-Zuweisung nach KV-Regelwerk."
  Grund: "BK" und "KV" sind intern — Reviewer/Client kennt sie nicht.
  Action: Vollform ausschreiben oder erklaeren:
    "Verarbeitet Buchungskreis-Zuweisung nach Kassenverzeichnis-Regelwerk."
    ODER
    "Verarbeitet BK- (Buchungskreis) Zuweisung nach KV- (Kassenverzeichnis) Regelwerk."
```

**Erkannte Abkuerzungs-Muster (Heuristik):**
```regex
# Standalone 2-Buchstaben-Gross in Freitext (nicht in Typnamen oder cref):
# Trifft: "nach BK-Vorgabe", "gemaess KV", "fuer BO-Typ"
# Trifft NICHT: "DIC", "HTTP", "JSON", "S3" (bekannte IT-Standards)
\b(?!HTTP|JSON|REST|XML|DTO|DIC|DAL|SQL|S3|EF|ID\b)[A-Z]{2}\b(?![-A-Za-z])
```

**Whitelist (NICHT melden):**
```
HTTP, JSON, REST, XML, DTO, SQL, S3, EF, ID, DI, UI, DB, OK,
DIC, DAL, MVC, API, URL, URI, UTC, ISO, RFC
```

### ERLAUBT (NICHT anfassen)

```
✓ Fachliche Abkuerzungen: MinIO, S3, DIC, HTTP, REST, JSON, DTO, EF Core
✓ Oeffentliche Standards: ISO-8601, RFC 7807, UTF-8
✓ Framework-Namen: AutoMapper, Entity Framework, xUnit
✓ Echte Klassen-Referenzen in <see cref="..."> — NIEMALS anfassen!
✓ Produkt-interne Begriffe die KEIN Reviewer erklaeren muss: DicGateway, LandesverbandProvider
✓ Abkuerzungen MIT Vollform: "BK (Buchungskreis)" oder "Buchungskreis (BK)" → PASS
✓ Test-Klassen-Namen in Test-Dateien selbst (nur in Produktions-Dateien pruefen)
```

### NEGATIV-LISTE: OmniCommand-Prozess-Jargon (IMMER entfernen)

Prozess-interne Begriffe die NIEMALS in Produktions-XML-Docs stehen duerfen.
Diese Liste waechst organisch — bei neuem Jargon: hier ergaenzen.

| Kategorie | Begriffe (Regex-Pattern) |
|-----------|------------------------|
| Stage-System | `Stage\s*\d`, `S\d[-–]\S*`, `Stufe\s*\d`, `Wiring[-\s]?Tests?` |
| Pipeline | `SC[-\s]?(FULL\|INLINE\|ANALYSE)`, `Hub[-\s]?Invariante`, `Handschuh[-\s]?Wechsel`, `Puppet[-\s]?Master` |
| TDD | `TDD\s*(RED\|GREEN\|REFACTOR)`, `Red/Green/Refactor`, `GOLD[-\s]?Definition` |
| Factory | `(Big\|Small)\s*Dark\s*Factory`, `Parking[-\s]?Lot`, `PL[-\s]?Item` |
| Wellen | `Welle\s*\d`, `W\d\s*(Haiku\|Sonnet\|Opus)`, `Wellen[-\s]?Pattern`, `Explorer.*Drafter.*Synthese` |
| Agenten | `Team\s*Lead`, `Worker[-\s]?Spawn`, `Handschuh`, `Skill\(`, `spawn_agent` |
| Metriken | `SRS[-\s]?\d`, `GAP[-\s]?\d*%`, `K[-\s]?Score`, `Stagnation`, `Komplexitaets[-\s]?Bemessung` |
| Dateien | `_manifest\.md`, `_parking[-\s]?lot\.md`, `_session[-\s]?params`, `pileOfMud`, `crumbs` |

**Anwendung:** Alle Muster oben werden wie andere kryptische Muster behandelt:
AUTO-FIX (Zeile/Teil entfernen, Kern-Aussage behalten). Wenn der gesamte Satz
nur aus Prozess-Jargon besteht: Zeile komplett entfernen.

---

## Schritt 2: Auto-Fix Strategie

### Regel 1: Kryptischen Satz/Teil ENTFERNEN

Kryptischer Teil liegt am ANFANG oder in der MITTE der Summary:

```csharp
// VORHER:
/// <summary>
/// MinIO Canary Tests  Verifiziert dass die MinIO Container-Infrastruktur funktioniert.
/// T0 ist das FUNDAMENT: Wenn T0 fehlschlaegt, ist die Infrastruktur kaputt.
/// Referenz: DIC-IntegrationTests-Slice4-PLAN.md, T0.
/// </summary>

// NACHHER (kryptische Zeilen entfernt, Kern-Aussage behalten):
/// <summary>
/// Verifiziert die MinIO-Objektspeicher-Infrastruktur.
/// Grundlegender Konnektivitaetstest — wenn dieser fehlschlaegt,
/// ist der Objektspeicher nicht verfuegbar.
/// </summary>
```

### Regel 2: Inline-Ersetzungen

Wenn kryptisches Muster mitten in einem Satz steht:

```csharp
// VORHER:
/// <summary>Verarbeitet DIC-Dateien gemaess DCSRE-881 und S3-Konfiguration.</summary>

// NACHHER (Ticket-Nummer entfernt, Satz bereinigt):
/// <summary>Verarbeitet DIC-Dateien gemaess S3-Konfiguration.</summary>
```

**WICHTIG:**
- Satz grammatikalisch korrekt lassen
- Nie `<see cref="...">` Tags veraendern — das ist R1-Blocker-Bereich
- Nie Beschreibungen erfinden (Halluzinationsrisiko)
- Wenn nach Fix nichts Sinnvolles uebrig bleibt → Zeile vollstaendig entfernen

### Regel 3: PB-Datei → Nutzdatei

```csharp
// VORHER: neben der PB-Datei in S3 abgelegt.
// NACHHER: neben der Nutzdatei in S3 abgelegt.
```

---

## Schritt 3: Durchfuehren + Bericht

Fuer jede DIRTY-CS-Datei:

1. XML-Kommentare lesen
2. Kryptische Muster finden
3. Auto-Fix anwenden (Datei direkt editieren)
4. Finding fuer Bericht notieren

**Bericht-Format:**

```
_Pre_PR_DocKlarity — XML-Doc Klarheit
======================================

Branch: [Branch-Name]
Datum:  [ISO-8601]
Scope:  [N] CS-Dateien geprueft

FIXES ANGEWENDET: [N]

  1. DicFileMetadataJson.cs
     Vorher: "JSON-Sidecar-DTO mit den 10 EM0012-Metadatenfeldern."
     Nachher: "Metadaten einer abgeholten DIC-Datei."
     Entfernt: EM0012, Sidecar

  2. MinioCanaryTests.cs:12
     Vorher: "T0 ist das FUNDAMENT. Referenz: Slice4-PLAN.md"
     Nachher: (Zeile entfernt, kein sinnvoller Rest)
     Entfernt: T0-Referenz, PLAN.md-Referenz

  3. DicImportService.cs:8
     Vorher: "Verarbeitet DIC-Dateien gemaess DCSRE-881."
     Nachher: "Verarbeitet DIC-Dateien."
     Entfernt: Jira-Ticket DCSRE-881

KEINE FIXES NOETIG: [M] Dateien bereits klar

Gesamtstatus: PASS  (alle kryptischen Referenzen entfernt)
```

---

## Qualitaetskriterien

### PASS

- 0 kryptische Muster in XML-Docs nach Auto-Fix
- Alle Summaries beschreiben WAS die Klasse/Methode tut
- Kein Reviewer muss interne Projekt-Dokumente kennen um die Docs zu verstehen

### FAIL (nur wenn Auto-Fix nicht moeglich)

- XML-Doc enthaelt kryptisches Muster das grammatikalisch nicht entfernt werden kann → WARNUNG, manuelle Nacharbeit noetig

---

## ANTI-PATTERNS

```
VERBOTEN in XML-Docs:
  ✗ "gemaess DCSRE-1234"                    → Jira-Tickets gehoeren nicht in Code-Docs
  ✗ "Referenz: PLAN.md"                     → Interne Pipeline-Docs nicht erwaehnen
  ✗ "T0 ist das FUNDAMENT"                  → Interne Test-IDs nicht erwaehnen
  ✗ "EM0012-Metadatenfelder"                → Interne Norm-Bezeichner vermeiden
  ✗ "JSON-Sidecar-DTO"                      → Kryptischer Jargon
  ✗ "neben der PB-Datei"                    → Erklaere was PB-Datei bedeutet (oder: Nutzdatei)
  ✗ "Getestet in DicGatewayAdapterTests"    → Test-Klassen gehoeren nicht in Produktions-Docs
  ✗ "wird getestet durch IntegrationTest"   → Reviewer interessiert sich nicht fuer Teststruktur
  ✗ "Test fuer S4-HappyPath"                → Slice + Test-Querverweis
  ✗ "Verarbeitet BK-Zuweisung nach KV"      → BK/KV unerklärte interne Abkuerzungen
  ✗ "Buchungskreis (BK) nach PE-Norm"       → PE unerklärte Abkuerzung, BK hier OK weil erklärt
  ✗ "Test #5b: GetFileContentAsync ..."     → Nummern-Prefix entfernen, Rest behalten
  ✗ "Root Cause: SFTP bekam FA-Dateinamen"  → Root-Cause-Analyse + FA unerklärte Abkuerzung
  ✗ "DicFileName-Fix DCSRE-882"             → Ticket-Referenz in Klammern → entfernen
  ✗ "Stage 2 Wiring-Tests"                 → OmniCommand-interner Prozess-Jargon
  ✗ "SC-FULL Symbiose"                     → Pipeline-Modus, extern unverstaendlich
  ✗ "TDD RED fuer S4-HappyPath"            → TDD-Phase + Slice, doppelt kryptisch
  ✗ "Hub-Invariante #8 verletzt"           → Architektur-intern, Reviewer versteht es nicht
  ✗ "Dark Factory Guard"                   → Prozess-interner Mechanismus

RICHTIG:
  ✓ "Metadaten einer abgeholten DIC-Datei."
  ✓ "Verarbeitet eingehende Nachrichten aus der Warteschlange."
  ✓ "Grundlegender Konnektivitaetstest fuer den Objektspeicher."
  ✓ "Wird als JSON-Datei neben der Nutzdatei in S3 abgelegt."
  ✓ "Verarbeitet Buchungskreis-Zuweisung nach Kassenverzeichnis-Regelwerk."
  ✓ "Buchungskreis (BK) — kurze Erklaerung ist ausreichend."
```

---

## Verwendung

```bash
/_Pre_PR_DocKlarity
```

**Laufzeit:** 30-90 Sekunden (abhaengig von Scope-Groesse)

**Wann ausfuehren:**
- Als Teil von `/_Pre_PR_orchestrate` (nach `_Pre_PR_Dokumentation`)
- Standalone nach grossen Refactoring-Sessions
- Immer wenn KI-Tools XML-Docs bearbeitet haben

---

**Ende des Commands**
