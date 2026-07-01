---
type: satellite
---

# /_user_journey — Browser-basierte User Journey Tests (Playwright)

```yaml
status: active
version: 1.0.0
created: 2026-03-30
op: UserJourney
phase: Testing
chain_position: standalone
difficulty_scaling: false
coldstart: true
```

## Zweck

`/_user_journey` ersetzt manuelles Browser-Testen. Du beschreibst eine User Journey
in Klartext — die KI plant die Schritte, navigiert den Browser, klickt, fuellt aus,
verifiziert und liefert einen PASS/FAIL Report mit Screenshot-Evidence.

**Kern-Idee:** Statt selbst durch die App zu klicken, beschreibst du WAS getestet
werden soll. Die KI macht den Rest.

---

## VERTRAG

```
INPUT   : JOURNEY (Pflicht) + optionale URL + optionale CREDENTIALS
OUTPUT  : PASS/FAIL Report mit Screenshot-Evidence pro Schritt
TOOLS   : Playwright MCP (browser_navigate, browser_click, browser_fill_form,
           browser_snapshot, browser_take_screenshot, browser_wait_for, etc.)
           + Read, Grep, Glob (fuer Kontext-Laden)
SCHREIBT: .claude/output/UJ-{FEATURE}-{DATE}.md (Report)
PIPELINE: standalone — kein Manifest, kein Pipeline-State noetig
```

---

## Aufruf

```
/_user_journey {JOURNEY_BESCHREIBUNG} [--url=BASE_URL] [--auth=USER:PASS]
```

- `JOURNEY_BESCHREIBUNG` — Was getestet werden soll, in Klartext (Pflicht)
- `--url` — Basis-URL der Anwendung (optional, Default aus SYSTEMZUGANG)
- `--auth` — Login-Credentials USER:PASS (optional, Default aus SYSTEMZUGANG)

**Beispiele:**

```
/_user_journey Login → Einrichtungen oeffnen → nach PLZ filtern → Ergebnis pruefen
/_user_journey Selbstauskunft anlegen, Pflichtfelder ausfuellen, speichern, in Liste pruefen
/_user_journey Pruefgrundlage zuordnen und Zuordnung in der Liste verifizieren --url=https://localhost:5001
```

---

## SYSTEMZUGANG (Credentials + URLs)

Bevor Playwright loslegt, braucht der Command die Zugangsdaten.
Reihenfolge der Aufloesung:

```
1. CLI-Parameter (--url, --auth) → hoechste Prioritaet
2. stage_5.md SYSTEMZUGANG-Block → projektspezifisch
3. _session_params.md → globale Session-Werte
4. AskUserQuestion → Fallback: User direkt fragen
```

```
# stage_5.md SYSTEMZUGANG-Block (Beispiel):
SYSTEMZUGANG:
  base_url: https://localhost:5001
  auth_url: https://localhost:5001/login
  user: testadmin
  pass: Test1234!
  docker_compose: docker-compose.e2e.yml
```

---

## Phase 1: PLAN (Journey → Schritte)

```
SCHRITT 1.1: Journey-Text parsen

  Lies JOURNEY_BESCHREIBUNG
  Zerlege in einzelne Schritte (Trennzeichen: →, Komma, Zeilenumbruch, "dann", "danach")

  Beispiel Input:
    "Login → Einrichtungen oeffnen → nach PLZ 12345 filtern → 3 Ergebnisse pruefen"

  Beispiel Output:
    steps = [
      {nr: 1, aktion: "LOGIN",    detail: "Mit Credentials einloggen",         verify: "Dashboard sichtbar"},
      {nr: 2, aktion: "NAVIGATE", detail: "Einrichtungen-Seite oeffnen",       verify: "Liste geladen"},
      {nr: 3, aktion: "INTERACT", detail: "PLZ-Filter auf 12345 setzen",       verify: "Filter aktiv"},
      {nr: 4, aktion: "VERIFY",   detail: "3 Ergebnisse in der Liste pruefen", verify: "Anzahl == 3"}
    ]


SCHRITT 1.2: Kontext laden (optional, wenn Feature-Name bekannt)

  IF Feature-Kontext verfuegbar (Model, Spec, Task.md):
    Lies relevante AKs / ECs fuer die Journey
    Ergaenze steps mit spezifischen Selektoren / Erwartungswerten
    Logge: "[PLAN] Feature-Kontext geladen: {N} AKs relevant"
  ELSE:
    Logge: "[PLAN] Kein Feature-Kontext — generische Journey"


SCHRITT 1.3: Plan ausgeben + bestaetigen

  Logge:
    ┌────┬───────────┬──────────────────────────────────┬─────────────────────────────┐
    │ #  │ Aktion    │ Detail                           │ Verifikation                │
    ├────┼───────────┼──────────────────────────────────┼─────────────────────────────┤
    │ 1  │ LOGIN     │ Mit Credentials einloggen        │ Dashboard sichtbar          │
    │ 2  │ NAVIGATE  │ Einrichtungen-Seite oeffnen      │ Liste geladen               │
    │ 3  │ INTERACT  │ PLZ-Filter auf 12345 setzen      │ Filter aktiv                │
    │ 4  │ VERIFY    │ 3 Ergebnisse in der Liste        │ Anzahl == 3                 │
    └────┴───────────┴──────────────────────────────────┴─────────────────────────────┘

  # KEIN HiL-Stop: Plan wird SOFORT ausgefuehrt (User kann ^C druecken)
```

---

## Phase 2: EXECUTE (Playwright Browser-Steuerung)

```
SCHRITT 2.0: Browser starten + Basis-Navigation

  # Playwright MCP: Browser navigieren
  browser_navigate(url="{base_url}")
  browser_wait_for(state="domcontentloaded")
  browser_take_screenshot(name="00-start")
  Logge: "[EXECUTE] Browser gestartet: {base_url}"


SCHRITT 2.1: Login (wenn auth vorhanden)

  IF auth != null:
    browser_navigate(url="{auth_url}")
    browser_wait_for(state="domcontentloaded")

    # Snapshot nehmen um Login-Felder zu finden
    snapshot = browser_snapshot()
    # Aus Snapshot: Username-Feld, Password-Feld, Submit-Button identifizieren
    # Heuristik: input[type=text/email] + input[type=password] + button[type=submit]

    browser_fill_form(values=[
      {ref: "{username_field_ref}", value: "{user}"},
      {ref: "{password_field_ref}", value: "{pass}"}
    ])
    browser_click(element="{submit_button_ref}")
    browser_wait_for(state="networkidle", timeout=10000)
    browser_take_screenshot(name="01-login")

    # Verify: Sind wir eingeloggt?
    post_login_snapshot = browser_snapshot()
    IF "login" IN post_login_snapshot.url.lower() OR "error" IN post_login_snapshot.text.lower():
      results[0] = {step: "LOGIN", status: "FAIL", reason: "Login fehlgeschlagen"}
      → Phase 3 (Report) — kein Weitermachen ohne Login
    ELSE:
      results[0] = {step: "LOGIN", status: "PASS", screenshot: "01-login"}
      Logge: "[EXECUTE] ✓ Login erfolgreich"


SCHRITT 2.2: Journey-Schritte ausfuehren (FUER JEDEN step)

  FUER JEDEN step IN steps (ab Schritt 2, Login war Schritt 1):

    Logge: "[EXECUTE] Schritt {step.nr}/{steps.length}: {step.aktion} — {step.detail}"

    # Snapshot VOR der Aktion (Zustand erfassen)
    pre_snapshot = browser_snapshot()

    # ═══ AKTION ausfuehren (abhaengig vom Typ) ═══

    IF step.aktion == "NAVIGATE":
      # Navigation: Link/Menuepunkt finden und klicken
      # Strategie: Snapshot → Text-Match → Element-Ref → Click
      target = finde_element_by_text(pre_snapshot, step.detail)
      IF target == null:
        # Fallback: URL direkt navigieren wenn erkennbar
        browser_navigate(url="{base_url}/{step.path_hint}")
      ELSE:
        browser_click(element=target.ref)
      browser_wait_for(state="networkidle", timeout=15000)

    ELIF step.aktion == "INTERACT":
      # Interaktion: Formular ausfuellen, Dropdown waehlen, Button klicken
      # Snapshot → Feld finden → Wert setzen
      target = finde_element_by_context(pre_snapshot, step.detail)
      IF "filter" IN step.detail.lower() OR "suche" IN step.detail.lower():
        # Input-Feld fuellen
        browser_click(element=target.ref)
        browser_type(element=target.ref, text="{step.value}")
        browser_press_key(key="Enter")
      ELIF "dropdown" IN step.detail.lower() OR "waehle" IN step.detail.lower():
        browser_select_option(element=target.ref, values=["{step.value}"])
      ELIF "klick" IN step.detail.lower() OR "button" IN step.detail.lower():
        browser_click(element=target.ref)
      ELSE:
        # Generisch: Klick auf gefundenes Element
        browser_click(element=target.ref)
      browser_wait_for(state="networkidle", timeout=10000)

    ELIF step.aktion == "VERIFY":
      # Verifikation: Nur pruefen, nichts aendern
      # Snapshot → Inhalt pruefen gegen step.verify
      pass  # Verifikation passiert unten

    ELIF step.aktion == "FILL":
      # Formular ausfuellen (mehrere Felder)
      browser_fill_form(values=step.form_values)
      browser_wait_for(state="networkidle", timeout=10000)

    # ═══ Screenshot NACH der Aktion ═══
    screenshot_name = "{step.nr:02d}-{step.aktion.lower()}"
    browser_take_screenshot(name=screenshot_name)

    # ═══ Verifikation ═══
    post_snapshot = browser_snapshot()

    # Verify-Strategie: Text-Match im Snapshot
    verify_passed = pruefe_verifikation(post_snapshot, step.verify)
    # Heuristik:
    #   - Zahlen: Zaehle Elemente / Zeilen in Tabelle
    #   - Text: Suche String im Snapshot
    #   - Sichtbarkeit: Element mit Text/Klasse vorhanden?
    #   - URL: Pruefe ob URL sich geaendert hat
    #   - Fehlermeldung: Pruefe ob KEIN error/alert sichtbar

    IF verify_passed:
      results[step.nr] = {step: step.detail, status: "PASS", screenshot: screenshot_name}
      Logge: "[EXECUTE] ✓ Schritt {step.nr} PASS: {step.verify}"
    ELSE:
      results[step.nr] = {step: step.detail, status: "FAIL", screenshot: screenshot_name,
                          reason: "Verifikation fehlgeschlagen: {step.verify}",
                          snapshot_text: post_snapshot.text[0:500]}
      Logge: "[EXECUTE] ✗ Schritt {step.nr} FAIL: {step.verify}"
      # KEIN Abbruch: Alle Schritte ausfuehren, Fehler sammeln


  # ═══ FINALER Screenshot (Endzustand) ═══
  browser_take_screenshot(name="99-final")
  Logge: "[EXECUTE] Journey abgeschlossen: {steps.length} Schritte ausgefuehrt"
```

---

## Phase 3: REPORT (Ergebnis + Evidence)

```
SCHRITT 3.1: Zusammenfassung berechnen

  total_steps   = results.length
  passed_steps  = results.filter(r → r.status == "PASS").length
  failed_steps  = results.filter(r → r.status == "FAIL").length
  journey_pass  = (failed_steps == 0)


SCHRITT 3.2: Report ausgeben (Konsole)

  Logge:
    ╔══════════════════════════════════════════════════════════════╗
    ║  USER JOURNEY REPORT                                         ║
    ║  Journey: {JOURNEY_BESCHREIBUNG}                             ║
    ║  URL: {base_url}                                             ║
    ║  Datum: {Datum}                                              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Ergebnis: {journey_pass ? "✓ PASS" : "✗ FAIL"}             ║
    ║  Schritte: {passed_steps}/{total_steps} PASS                 ║
    ╚══════════════════════════════════════════════════════════════╝

    ┌────┬───────────┬──────────────────────────────────┬────────┬─────────────────────────┐
    │ #  │ Aktion    │ Detail                           │ Status │ Verifikation            │
    ├────┼───────────┼──────────────────────────────────┼────────┼─────────────────────────┤
    │ 1  │ LOGIN     │ Mit Credentials einloggen        │ ✓ PASS │ Dashboard sichtbar      │
    │ 2  │ NAVIGATE  │ Einrichtungen-Seite oeffnen      │ ✓ PASS │ Liste geladen           │
    │ 3  │ INTERACT  │ PLZ-Filter auf 12345 setzen      │ ✓ PASS │ Filter aktiv            │
    │ 4  │ VERIFY    │ 3 Ergebnisse in der Liste        │ ✗ FAIL │ Anzahl: 5 (erwartet: 3) │
    └────┴───────────┴──────────────────────────────────┴────────┴─────────────────────────┘

    FAIL Details:
      Schritt 4: Verifikation "Anzahl == 3" fehlgeschlagen.
        Gefunden: 5 Zeilen in der Tabelle.
        Screenshot: 04-verify.png


SCHRITT 3.3: Report als Datei schreiben

  feature_name = NAME ?? "manual"
  report_path = ".claude/output/UJ-{feature_name}-{DATE}.md"

  Schreibe report_path:
    ---
    type: user-journey-report
    date: {Datum}
    journey: "{JOURNEY_BESCHREIBUNG}"
    url: "{base_url}"
    result: {journey_pass ? "PASS" : "FAIL"}
    steps_total: {total_steps}
    steps_passed: {passed_steps}
    steps_failed: {failed_steps}
    ---

    # User Journey Report: {JOURNEY_BESCHREIBUNG}

    {Report-Tabelle wie oben}

    ## FAIL Details
    {Fuer jeden FAIL-Schritt: Grund, Screenshot-Referenz, Snapshot-Auszug}

    ## Screenshots
    {Liste aller Screenshots mit Beschreibung}

  Logge: "[REPORT] Gespeichert: {report_path}"
```

---

## Playwright MCP Tools — Referenz

| Tool | Wann | Beispiel |
|------|------|---------|
| `browser_navigate` | Seite oeffnen | `url="https://localhost:5001/einrichtungen"` |
| `browser_snapshot` | DOM-Zustand lesen (Accessibility Tree) | Liefert Text + Element-Refs |
| `browser_click` | Element klicken | `element="ref:button-submit"` |
| `browser_fill_form` | Formular ausfuellen | `values=[{ref, value}]` |
| `browser_type` | Text tippen | `element="ref:input-plz", text="12345"` |
| `browser_select_option` | Dropdown waehlen | `element="ref:select-land"` |
| `browser_press_key` | Taste druecken | `key="Enter"` |
| `browser_wait_for` | Warten (load, networkidle) | `state="networkidle"` |
| `browser_take_screenshot` | Screenshot machen | `name="03-filter"` |
| `browser_hover` | Hover (Tooltip, Submenu) | `element="ref:menu-item"` |
| `browser_evaluate` | JS ausfuehren | `expression="document.querySelectorAll('tr').length"` |
| `browser_navigate_back` | Zurueck | — |
| `browser_tabs` | Tabs auflisten | — |
| `browser_close` | Browser schliessen | Am Ende |

---

## Hinweise

- **Snapshot ist dein Auge:** `browser_snapshot()` liefert den Accessibility Tree mit Element-Refs.
  IMMER Snapshot nehmen bevor du klickst/fuellst — damit du die richtigen Refs hast.
- **Refs sind fluechtig:** Nach jeder Navigation/Aktion neue Snapshot nehmen — alte Refs sind ungueltig.
- **Warten ist Pflicht:** Nach JEDER Aktion `browser_wait_for` aufrufen (mindestens `domcontentloaded`).
  Angular-Apps brauchen oft `networkidle` weil API-Calls nachladen.
- **Fehler-Toleranz:** Wenn ein Element nicht gefunden wird → Screenshot + FAIL fuer diesen Schritt,
  aber WEITER mit dem naechsten Schritt (alle Fehler sammeln).
- **Kein Cleanup:** Browser wird NICHT geschlossen — User kann manuell weitertesten.
- **Angular SPA:** Navigation aendert oft nur die Route, nicht die ganze Seite.
  `browser_wait_for(state="networkidle")` ist besser als `state="load"`.
