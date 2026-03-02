---
name: _Pre_PR_Architektur
description: Pre-PR Architektur Quality Gate - prueft Architektur-Konformitaet (Controller, Interfaces, Provider, Konfiguration, DI)
---

# /_Pre_PR_Architektur

**Zweck:** Sicherstellen dass neue Features die bestehende Architektur respektieren und keine redundanten Strukturen einfuehren.

**Abdeckung:** 45 Kommentare (16.4% aller Code-Review-Kommentare)

**Schwierigkeit:** HARD (Ceiling: opus, Floor: sonnet)

**Auto-Fix:** NEIN (nur Bericht mit Empfehlungen)

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════╗
║  COMMAND: /_Pre_PR_Architektur                               ║
╠══════════════════════════════════════════════════════════════╣
║  LIEST:                                                      ║
║    1. .claude/meta/codeKonvention/architektur.md             ║
║    2. Git Diff (develop...HEAD)                              ║
║    3. Codebase (Kontext: Controller, Interfaces, Provider)   ║
║  SCHREIBT:                                                   ║
║    1. Bericht mit Warnungen und Empfehlungen                 ║
║    2. KEINE Code-Fixes (nur manuelle Review-Ergebnisse)      ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: DIRTY-Scope ermitteln

**Aktion:** Git Diff analysieren um geaenderte Dateien zu identifizieren.

```bash
# Im Backend-Root ausfuehren
git diff --name-status develop...HEAD
```

**Filter fuer Architektur-relevante Dateien:**
- `*Controller.cs` (neue oder geaenderte Controller)
- `*Provider.cs` (neue oder geaenderte Provider)
- `I*Provider.cs` (neue oder geaenderte Interfaces)
- `*ServiceModule.cs` (DCSRE: Service-Registrierung via IServiceModule-Pattern)
- `appsettings*.json` (Konfiguration)
- `*.cs` (alle C#-Dateien fuer R6: DateTime-Konsistenz, R12: DbContext-Check)

**SKIP-Pfad:** Falls DIRTY-SCOPE = 0 → "Keine Architektur-relevanten Dateien gefunden. Gate PASS." → EXIT 0

**Output:**
```
DIRTY-SCOPE: [Anzahl] Architektur-relevante Dateien gefunden
- [Liste der Dateien mit Kategorie]
```

---

## Schritt 1: Regeln lesen

**Aktion:** Konvention laden.

```bash
# Datei lesen
cat .claude/meta/codeKonvention/architektur.md
```

**Fehlerbehandlung:** Falls die Datei nicht existiert → FEHLER: "Knowledge-Datei .claude/meta/codeKonvention/architektur.md nicht gefunden. Starte _I_fanOut oder erstelle die Datei manuell." → EXIT 1

**Regeln:** Alle R1-R9, R12 werden aus der Knowledge-Datei gelesen. Siehe `.claude/meta/codeKonvention/architektur.md` fuer die vollstaendigen Regelbeschreibungen mit Severity und Auto-Fix Status.

---

## Welle 1: Exploration

### Task 1.1: Neue Controller analysieren

**Fuer jede neue `*Controller.cs` Datei:**

1. Datei lesen
2. Fragen:
   - Existiert bereits ein Controller fuer diese Domain?
   - Kann die Funktionalitaet in bestehenden Controller integriert werden?
   - Leitet der Controller von einer Basis-Klasse ab?

**Suche in Codebase:**
```bash
# Alle Controller finden
find . -name "*Controller.cs" -type f
```

**Output Task 1.1:**
```
[WARNUNG/OK] Controller: BenutzerAdresseController
  - Status: NEUE DATEI
  - Problem: Bestehender BenutzerController kann erweitert werden
  - Empfehlung: Methode GetAdressen() in BenutzerController integrieren
```

### Task 1.2: Neue Interfaces analysieren (R2: Interface-Hierarchie-Konformitaet)

**DCSRE-Konvention:** In DCSRE definieren Provider-Interfaces KEINE CRUD-Methoden selbst.
CRUD-Methoden werden von `IIdentityCrudProvider<T>` oder `ICrudProvider<T, TId>` geerbt.

**Fuer jede neue `I*Provider.cs` Datei:**

1. Datei lesen
2. Pruefen ob das Interface von der richtigen Basis-Hierarchie erbt:

**Suche nach korrekte Basis-Hierarchie:**
```bash
# RICHTIG: Interface erbt von Basis
grep -n "IIdentityCrudProvider\|ICrudProvider" I*Provider.cs

# FALSCH: Interface ohne Basis (nur domain-spezifische Methoden + kein Basis-Interface)
# Warnung wenn Interface kein IIdentityCrudProvider/ICrudProvider erbt
# UND kein bewusstes Non-CRUD Interface ist (z.B. IEmailService)
```

**Heuristik fuer Bewertung:**
- Interface enthaelt `: IIdentityCrudProvider<T>` oder `: ICrudProvider<T, TId>` → OK
- Interface enthaelt KEIN Basis-CRUD-Interface ABER Klasse heisst I*Provider → WARNUNG (pruefen)
- Interface ist bewusst kein CRUD (IEmailService, IUserContextService) → OK (kein Finding)

**Output Task 1.2:**
```
[WARNUNG/OK] Interface: IBenutzerProvider
  - Status: NEUE DATEI
  - Problem: Kein IIdentityCrudProvider<T> Basis-Interface gefunden
  - Empfehlung: Von IIdentityCrudProvider<Benutzer> ableiten (erbt GetById/GetAll/Create/Update/Delete)
```

### Task 1.3: Provider-Implementierungen analysieren

**Fuer jede neue `*Provider.cs` Datei:**

1. Datei lesen
2. Fragen:
   - Implementiert die Klasse CRUD-Methoden manuell?
   - Leitet sie von IdentityCrudDbProviderBase ab?

**Output Task 1.3:**
```
[WARNUNG/OK] Provider: BenutzerProvider
  - Status: NEUE DATEI
  - Problem: Implementiert CRUD-Methoden manuell (200 Zeilen Boilerplate)
  - Empfehlung: Von IdentityCrudDbProviderBase<Benutzer, BenutzerFilter> ableiten
```

### Task 1.4: Hardcoded Konfiguration finden

**Pattern-Suche in geaenderten Dateien:**
- URLs: `"http://..."` oder `"https://..."`
- Timeouts: `TimeSpan.FromSeconds(...)`
- API-Keys: `"Bearer ..."` oder `"ApiKey: ..."`
- Limits: Hardcoded Zahlen in Business-Logik

**Output Task 1.4:**
```
[INFO/OK] Hardcoded Werte gefunden:
  - ExternalApiClient.cs:42: "https://api.example.com"
    Empfehlung: In appsettings.json unter ExternalApi.BaseUrl
  - RateLimiter.cs:15: TimeSpan.FromSeconds(30)
    Empfehlung: In appsettings.json unter RateLimiting.Timeout
```

### Task 1.5: Service-Registrierung pruefen (R5: DCSRE *ServiceModule-Pattern)

**DCSRE-Konvention:** Service-Registrierung erfolgt in `*ServiceModule.cs` (NICHT in `Startup.cs` oder `*Extensions.cs`).
- `DataServiceModule.cs` → Provider (auto-registriert via `RegisterCrudDbProviders()`)
- `ApplicationServiceModule.cs` → Services (auto-registriert via `RegisterIdentityCrudServices()`)
- `WebApiServiceModule.cs` → WebApi-Services

**Suche in *ServiceModule.cs Dateien:**
```bash
# Alle ServiceModule-Dateien im DIRTY-Scope finden
git diff --name-only develop...HEAD | grep "ServiceModule.cs"

# Manuelle AddSingleton/AddScoped/AddTransient Aufrufe pruefen
grep -n "AddScoped\|AddTransient\|AddSingleton" *ServiceModule.cs
```

**Pruefung:**
1. Neue Provider/Services in `*ServiceModule.cs` registriert? (nicht in Startup.cs)
2. Duplikate: gleiches Interface mehrfach registriert?
3. Lifetime-Konsistenz: Neue manuelle Registrierungen = `AddSingleton` (DCSRE-Standard)?
   - `AddScoped` oder `AddTransient` fuer neue Klassen → WARNUNG (R9-Verletzung)

**Output Task 1.5:**
```
[INFO/OK] Service-Registrierung:
  - IBenutzerProvider: 2x registriert in DataServiceModule.cs
    Zeile 45: services.AddSingleton<IBenutzerProvider, BenutzerProvider>(); [DUPLIKAT]
  - WARNUNG: services.AddScoped<IXyzService, XyzService>(); → Scoped in Singleton-Kontext!
```

### Task 1.6: DateTime-Konsistenz pruefen

**Regel R6:** Im Projekt gilt: **`DateTimeOffset.Now`** ist der Standard (konsistent mit bestehendem Production-Code).

**Verboten in Production-Code (WARNUNG):**
- `DateTime.Now` → verwende `DateTimeOffset.Now`
- `DateTime.UtcNow` → verwende `DateTimeOffset.Now`
- `DateTimeOffset.UtcNow` → verwende `DateTimeOffset.Now`
- `new DateTime(...)` → verwende `new DateTimeOffset(...)`

**Erlaubt:**
- `DateTimeOffset.Now` (Projekt-Standard)
- `DateTimeOffset.MinValue` / `DateTimeOffset.MaxValue` (Sentinel-Werte)
- `DateTime` in Migrations, generierten Dateien, externen DTOs (wenn API es erfordert)

**Suche in allen geaenderten `*.cs` Dateien im DIRTY-Scope:**

```bash
# Verbotene Patterns suchen (nur in geaenderten Dateien)
git diff --name-only develop...HEAD -- '*.cs' | xargs grep -n -E 'DateTime\.(Now|UtcNow)|DateTimeOffset\.UtcNow|new DateTime\('
```

**Ausnahmen (kein Finding):**
- `**/Migrations/*.cs` (EF Migrations)
- `*.Designer.cs` (generierte Dateien)
- Zeilen mit `// R6-exempt` Kommentar (explizite Ausnahme)

**Output Task 1.6:**
```
[WARNUNG/OK] DateTime-Konsistenz:
  - MyService.cs:42: DateTimeOffset.UtcNow → DateTimeOffset.Now
  - MyProvider.cs:30: DateTime.UtcNow → DateTimeOffset.Now
  - MyHelper.cs:15: DateTime.Now → DateTimeOffset.Now
  Empfehlung: Alle Zeitstempel auf DateTimeOffset.Now vereinheitlichen (Projekt-Standard)
```

### Task 1.7: Basisklassen-Konformitaet pruefen (R8: DCSRE-spezifisch)

**DCSRE-Pflicht-Basisklassen:**

| Datei-Typ | Pflicht-Basisklasse |
|-----------|---------------------|
| `*Controller.cs` (WebApi) | `ApiControllerBase` |
| `*Provider.cs` (Data) | `IdentityCrudDbProviderBase<TCtx,T,TEntity>` oder `CrudDbProviderBase<...>` |
| `*Service.cs` (Application) | `IdentityCrudServiceBase<T>` oder `CrudServiceBase<T>` |

**Suche fuer jede neue Controller-, Provider- und Service-Datei:**

```bash
# Controller: Erbt ApiControllerBase?
grep -n "class.*Controller.*:" *Controller.cs | grep -v "ApiControllerBase"
# Falls Treffer → WARNUNG (ausser PingController)

# Provider: Erbt IdentityCrudDbProviderBase oder CrudDbProviderBase?
grep -n "class.*Provider.*:" *Provider.cs | grep -v "CrudDbProviderBase"
# Falls Treffer → WARNUNG (ausser Non-CRUD Provider wie IEmailService)

# Service: Erbt IdentityCrudServiceBase oder CrudServiceBase?
grep -n "class.*Service.*:" *Service.cs | grep -v "CrudServiceBase"
# Falls Treffer → WARNUNG (ausser Non-CRUD Services)
```

**Ausnahmen (kein Finding):**
- `PingController` (health-check, ControllerBase erlaubt)
- Bewusst kein CRUD (z.B. `EmailService`, `UserContextService`)

**Output Task 1.7:**
```
[WARNUNG/OK] Basisklassen-Konformitaet (R8):
  - OrderController: erbt ControllerBase statt ApiControllerBase → WARNUNG
    Empfehlung: class OrderController : ApiControllerBase { }
  - OrderProvider: erbt IOrderProvider direkt ohne IdentityCrudDbProviderBase → WARNUNG
    Empfehlung: class OrderProvider : IdentityCrudDbProviderBase<DcspDbContext, Order, OrderEntity>, IOrderProvider
```

---

### Task 1.8: DbContext-Direktinjektion pruefen (R12: BLOCKER)

**DCSRE-Konvention:** DbContext darf NIEMALS direkt in einen Singleton-Provider/Service injiziert werden.
Provider/Services sind Singleton. DbContext ist per-Request (Scoped).
Direktinjektion = Thread-Safety-Problem (mehrere Requests teilen denselben DbContext).

**Korrekte Loesung:** `IDbContextFactory<TContext>` verwenden (automatisch durch Basisklasse).

**Suche in allen neuen *Provider.cs und *Service.cs Dateien:**

```bash
# DbContext direkt im Konstruktor-Parameter? → BLOCKER
grep -n "DcspDbContext\|DbContext" *Provider.cs *Service.cs | grep -v "IDbContextFactory\|Factory"
# Falls Treffer in Konstruktor-Signatur → BLOCKER
```

**Heuristik:**
- `IDbContextFactory<DcspDbContext>` im Konstruktor → OK (korrekt)
- `DcspDbContext` direkt im Konstruktor → BLOCKER
- `DbContext` im Methoden-Body via `using var ctx = _factory.CreateDbContext()` → OK (korrekte Factory-Nutzung)

**Output Task 1.8:**
```
[BLOCKER/OK] DbContext-Direktinjektion (R12):
  - OrderProvider.cs:12: public OrderProvider(DcspDbContext context) → BLOCKER!
    Problem: Singleton-Provider injiziert Scoped DbContext (Thread-Safety-Verletzung)
    Empfehlung: Erbe von IdentityCrudDbProviderBase<DcspDbContext, Order, OrderEntity>
    oder: public OrderProvider(IDbContextFactory<DcspDbContext> dbContextFactory)
```

---

## Welle 2: Synthese + Bericht

**Aktion:** Alle Findings zusammenfassen.

### Berichts-Format

```markdown
# Pre-PR Architektur Quality Gate Report

**Branch:** [Branch-Name]
**Datum:** [ISO-8601]
**Analysierte Dateien:** [Anzahl]

---

## Zusammenfassung

| Level | Anzahl | Status |
|-------|--------|--------|
| BLOCKER | [N] | [PASS/FAIL] |
| WARNUNG | [N] | [PASS/FAIL] |
| INFO | [N] | [PASS/FAIL] |

**Gesamtstatus:** [PASS/FAIL]

---

## Details

### R1: Neue Controller

[Liste der Findings aus Task 1.1]

**Empfehlungen:**
- [Konkrete Handlungsanweisungen]

---

### R2: Neue Interfaces

[Liste der Findings aus Task 1.2]

**Empfehlungen:**
- [Konkrete Handlungsanweisungen]

---

### R3: Provider

[Liste der Findings aus Task 1.3]

**Empfehlungen:**
- [Konkrete Handlungsanweisungen]

---

### R4: Konfiguration

[Liste der Findings aus Task 1.4]

**Empfehlungen:**
- [Konkrete Handlungsanweisungen]

---

### R5: Service-Registrierung

[Liste der Findings aus Task 1.5]

**Empfehlungen:**
- [Konkrete Handlungsanweisungen]

---

### R6: DateTime-Konsistenz

[Liste der Findings aus Task 1.6]

**Standard:** `DateTimeOffset.Now` (Projekt-Standard, keine Ausnahmen in Production-Code)

**Empfehlungen:**
- [Konkrete Handlungsanweisungen pro Finding]

---

### R8: Basisklassen-Konformitaet (DCSRE-spezifisch)

[Liste der Findings aus Task 1.7]

**Pflicht-Basisklassen:** ApiControllerBase (Controller), IdentityCrudDbProviderBase (Provider), IdentityCrudServiceBase (Service)

**Empfehlungen:**
- [Konkrete Handlungsanweisungen: welche Basisklasse fuer welche Datei]

---

### R12: DbContext-Direktinjektion (BLOCKER)

[Liste der Findings aus Task 1.8]

**Null-Toleranz:** Kein DbContext direkt in Singleton-Klasse erlaubt. Immer `IDbContextFactory<TContext>`.

**Empfehlungen:**
- [Konkrete Fix-Anleitung: Basisklasse verwenden oder IDbContextFactory injizieren]

---

## Naechste Schritte

1. [Priorisierte Liste der Fixes]
2. [Diskussionspunkte fuer Team-Review]
3. [Architektur-Entscheidungen die getroffen werden muessen]

---

**Hinweis:** Dieser Bericht enthaelt keine automatischen Fixes.
Alle Aenderungen erfordern manuelle Pruefung und Umsetzung durch den Entwickler.
```

---

## Qualitaetskriterien

### Erfolg (PASS)
- Alle Dateien im DIRTY-Scope wurden analysiert
- Jede Regel (R1-R9, R12) wurde geprueft
- Bericht enthaelt konkrete Empfehlungen
- Keine BLOCKER-Level Findings (R12: DbContext-Direktinjektion)

### Misserfolg (FAIL)
- BLOCKER: Mindestens 1 R12-Verletzung (DbContext direkt injiziert) → sofortiger FAIL
- FAIL: Findings mit WARNUNG-Level wurden gefunden (R1, R2, R3, R5, R6, R8, R9)
- Findings mit INFO-Level sind optional (kein automatischer FAIL)

### BLOCKER-Level (sofortiger FAIL, Null-Toleranz)
- R12: DbContext direkt in Konstruktor eines Provider/Service injiziert (Thread-Safety-Verletzung)

### WARNUNG-Level (manuelles Review erforderlich)
- R1: Neue Controller ohne Pruefung auf Redundanz
- R2: Neue Interfaces ohne IIdentityCrudProvider<T> / ICrudProvider<T,TId> Basis
- R3: Provider ohne IdentityCrudDbProviderBase Basis-Klasse
- R5: Service-Registrierung ausserhalb *ServiceModule.cs oder Duplikate
- R6: DateTime statt DateTimeOffset, oder .UtcNow statt .Now
- R8: Controller/Provider/Service ohne richtige Basisklasse
- R9: Neue manuelle DI-Registrierung mit AddScoped/AddTransient statt AddSingleton

### INFO-Level (Best Practice Empfehlungen)
- R4: Hardcoded Konfiguration (URLs, Timeouts, API-Keys)

---

## Verwendung

```bash
# Ausfuehren vor PR-Erstellung
/_Pre_PR_Architektur

# Output
# - Bericht als Markdown
# - Exit-Code 0 bei PASS, 1 bei FAIL
```

**Erwartete Laufzeit:** 2-5 Minuten (haengt von Anzahl neuer Dateien ab)

**Ressourcen:** Opus bei komplexen Architektur-Fragen, Sonnet fuer Standard-Pruefungen

---

## Debugging

**Haeufige Probleme:**

1. **"Keine Controller gefunden"**
   - Pruefe DIRTY-Scope Filter
   - Sind die Dateien in Git committed?

2. **"Basis-Interface nicht erkannt"**
   - Pruefe ob IIdentityCrud* Namenskonvention eingehalten wird
   - Suche nach alternativen Base-Interfaces in Codebase

3. **"Falsche Warnungen"**
   - Manuelles Override moeglich wenn Architektur-Entscheidung begruendet ist
   - Dokumentiere Ausnahmen im PR-Kommentar

---

**Ende des Commands**
