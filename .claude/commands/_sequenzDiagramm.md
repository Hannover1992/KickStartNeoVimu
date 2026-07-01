---
type: satellite
---

# /_sequenzDiagramm — Abstraktions-Layer aufdecken (3 Perspektiven)

```yaml
status: active
version: 2.0.0
created: 2026-04-15
op: SequenzDiagramm
phase: Output
chain_position: standalone
difficulty_scaling: false
coldstart: true
```

## Zweck

Jede Zeile Code ist eine Abstraktion. Dieses Command deckt die versteckten
Kaskaden auf — in **drei Perspektiven**, die sich ergaenzen:

| Perspektive | Was | Analogie |
|-------------|-----|----------|
| **Mermaid Sequence Diagram** | Ueberblick — wer redet mit wem, in welcher Reihenfolge | wie `/_presentation` |
| **Tiefen-Baum** | Detail — jeder versteckte Schritt, mit GOTCHAs und FAILs an den Bruchstellen | das Neue |
| **Essenz** | Reflexion — was lehrt diese Kaskade, was ist die Kern-Erkenntnis | wie `/_assay` |

**Warum alle drei?**
- Das Mermaid zeigt die Architektur auf einen Blick (10 Sekunden)
- Der Tiefen-Baum zeigt WO es bricht und WARUM (2 Minuten)
- Die Essenz destilliert die eine Erkenntnis (10 Sekunden)

---

## Aufruf

```
/_sequenzDiagramm {THEMA}
```

| Parameter | Default | Beschreibung |
|-----------|---------|--------------|
| THEMA | (PFLICHT) | Die Abstraktion die aufgedeckt wird. Code-Zeile, API-Call, User-Aktion oder Konzept. |

**Beispiele:**
```
/_sequenzDiagramm "git commit"
/_sequenzDiagramm "async/await in C#"
/_sequenzDiagramm "LINQ .ToList() mit EF Core"
/_sequenzDiagramm "DCSRE Login"
/_sequenzDiagramm "Stage 6 PE-Guard API-Call"
/_sequenzDiagramm "spawne_worker() vs Skill()"
/_sequenzDiagramm "Handschuh-Wechsel I→SDF"
```

---

## VERTRAG

```
+======================================================================+
| VERTRAG: /_sequenzDiagramm                                            |
+======================================================================+
|                                                                        |
| ACTOR: SEQUENCE WRITER (Claude)                                       |
|   TUT:                                                                 |
|     - Identifiziert die Abstraktion und alle Teilnehmer (Actors)      |
|     - Deckt die versteckten Schritte auf (Kaskade)                    |
|     - Erzeugt 3 Perspektiven:                                         |
|       1. Mermaid sequenceDiagram (Ueberblick, ~10-15 Messages)       |
|       2. Tiefen-Baum (jeder Schritt, Phasen, GOTCHAs, FAILs)        |
|       3. Essenz (2-5 Saetze, reflektiv)                               |
|   NICHT:                                                               |
|     - Flowcharts (→ /_presentation)                                   |
|     - Vollstaendige Essays (→ /_assay)                                |
|     - Vollstaendige technische Doku                                   |
|     - Mehr als EIN Thema pro Aufruf                                   |
|                                                                        |
| LIEST:                                                                 |
|   - Eigenes Wissen ueber die Abstraktion                              |
|   - Optional: Codebase-Dateien wenn THEMA projektspezifisch ist       |
|                                                                        |
| SCHREIBT:                                                              |
|   1. .claude/output/SequenzDiagramm_{DATE}_{THEMA_CLEAN}.md          |
|                                                                        |
| POSITION:                                                              |
|   TYPE: STANDALONE (Satellit-Command)                                  |
|   EINSATZ: Frei einsetzbar — Erklaerung, Onboarding, Debugging,      |
|            Architektur-Verstaendnis, Case Studies                      |
+======================================================================+
```

---

## Ablauf

### Schritt 1: Parameter validieren

```
1. THEMA vorhanden?
   → NEIN: FEHLER. THEMA ist PFLICHT.
   → JA: Weiter.

2. Sanitize THEMA → {THEMA_CLEAN} (Leerzeichen→Underscore, Sonderzeichen weg)
3. DATE = YYYY-MM-DD (heute)
4. Output-Pfad: .claude/output/SequenzDiagramm_{DATE}_{THEMA_CLEAN}.md
```

### Schritt 2: Abstraktion analysieren

```
Beantworte fuer dich selbst:

1. WAS SCHREIBT/SIEHT DER USER? (Die sichtbare Abstraktion — 1 Zeile / 1 Aktion)
2. WELCHE PHASEN HAT DIE KASKADE? (Gruppiere in 2-5 logische Phasen)
3. WELCHE ACTORS SIND PRO PHASE BETEILIGT? (Komponenten, Services, OS, Runtime, DB, ...)
4. WAS PASSIERT IN JEDER PHASE? (Chronologisch, Schritt fuer Schritt, beliebig tief)
5. WO SIND DIE GOTCHAS? (Ueberraschungen, Fehler, unerwartetes Verhalten)
6. WO SIND DIE FAILS? (Dinge die NICHT funktioniert haben — Anlaeufe, Workarounds)

Wenn THEMA projektspezifisch ist (OmniCommand, DCSRE, Pipeline):
→ Lies relevante Command-Dateien / Code um die echten Schritte zu kennen.
```

### Schritt 3: Output-Datei schreiben

Die Datei hat 4 Sektionen:

**Sektion 1: "Was du schreibst"** — Die eine Zeile / Aktion

**Sektion 2: "Ueberblick" (Mermaid)** — High-Level Sequence Diagram
- Max ~15 Messages
- Phasen als `rect` oder `Note` Bloecke
- GOTCHAs als `Note` Annotationen
- Zeigt den HAPPY PATH + wichtigste Abzweigung

**Sektion 3: "Tiefen-Baum"** — Der Kern des Dokuments
- Phasen als Ueberschriften mit `├─` und `└─` Baum-Notation
- Beliebig tief verschachtelt (so tief wie noetig)
- `GOTCHA:` Annotationen inline (Ueberraschungen)
- `FAIL:` Annotationen inline (Fehlversuche die zum Verstaendnis beitragen)
- Am Ende: "Was auf dem Bildschirm stand: ... / Was tatsaechlich passiert ist: ..."

**Sektion 4: "Essenz"** — 2-5 Saetze, reflektiv (wie mini-Assay)

Format der Output-Datei:

```markdown
---
id: SequenzDiagramm_{DATE}_{THEMA_CLEAN}
tags:
  - type/sequenzdiagramm
  - topic/{THEMA_CLEAN}
date: {DATE}
---

# {THEMA}

## Was du schreibst

\`\`\`
{Die eine Zeile / Aktion}
\`\`\`

## Ueberblick

\`\`\`mermaid
sequenceDiagram
    participant A as {Actor1}
    participant B as {Actor2}
    ...
    A->>B: Schritt 1
    Note over B: GOTCHA: {Ueberraschung}
    ...
\`\`\`

## Tiefen-Baum

┌─ PHASE 1: {Name} ──────────────────────────────
│
│  {Beschreibung des Einstiegspunkts}
│  ├─ Schritt 1
│  │   ├─ Detail
│  │   └─ GOTCHA: {Warum das ueberraschend ist}
│  ├─ Schritt 2
│  │   ├─ Sub-Schritt
│  │   │   ├─ Sub-Sub-Schritt (beliebig tief)
│  │   │   └─ ...
│  │   └─ FAIL: {Was NICHT funktioniert hat und warum}
│  └─ Ergebnis dieser Phase
│
├─ PHASE 2: {Name} ──────────────────────────────
│
│  ...
│
└──────────────────────────────────────────────────

Was auf dem Bildschirm stand: {1 Zeile}
Was tatsaechlich passiert ist: {Aufzaehlung der versteckten Schritte}

## Essenz

{2-5 Saetze: Was lehrt diese Kaskade? Was ist die Kern-Erkenntnis?
 Nicht Zusammenfassung — sondern was UEBERRASCHT und was man DARAUS LERNT.}
```

### Schritt 4: Terminal-Output + fullPath

```
1. TERMINAL-OUTPUT (PFLICHT):
   Gib das komplette Dokument im Terminal aus — der User soll es sofort lesen.

2. Rufe /_fullPath auf damit der Pfad im Clipboard landet.
```

---

## One-Shot-Example (Stage 6: PE-Guard API-Call aus DCSRE-1430)

Dieses Beispiel stammt aus einer echten Session. Ein einziger API-Call
mit Bearer-Token gegen einen laufenden Controller — und was dahinter passiert.

```markdown
---
id: SequenzDiagramm_2026-04-14_Stage6_PE_Guard_API_Call
tags:
  - type/sequenzdiagramm
  - topic/Stage6_PE_Guard_API_Call
date: 2026-04-14
---

# Stage 6: PE-Guard API-Call

## Was du schreibst

` ` `powershell
Test-Endpoint $petra_token $elbblick_vv "Petra->Elbblick(fremde)" 401
` ` `

Ergebnis: HTTP 401 [PASS]

## Ueberblick

` ` `mermaid
sequenceDiagram
    participant PS as PowerShell
    participant KC as Keycloak
    participant API as ASP.NET API
    participant MW as Middleware Pipeline
    participant Ctrl as Controller
    participant Svc as Service + Guard
    participant DB as SQL Server

    rect rgb(40, 40, 60)
    Note over PS,KC: PHASE 1: Token holen
    PS->>KC: POST /token (password grant)
    Note over KC: 3 Anlaeufe bis es klappt
    KC-->>PS: access_token (JWT, RS256)
    end

    rect rgb(40, 60, 40)
    Note over PS,DB: PHASE 2: API Call
    PS->>API: GET /qdvtp/{vvId} + Bearer
    API->>MW: Authentication Middleware
    MW->>MW: JWT validieren (Signatur, Issuer, Expiry)
    MW->>Ctrl: ClaimsPrincipal gesetzt
    Ctrl->>Svc: ReadById(vvId)
    Svc->>DB: SELECT Versorgungsvertrag
    DB-->>Svc: VV mit EinrichtungsId
    Svc->>Svc: CheckPeGuard()
    Note over Svc: Herbstlaub-PE != Elbblick-PE → BLOCKED
    Svc-->>Ctrl: Result.AccessDenied
    Ctrl-->>MW: ErrorResult
    MW->>MW: ResultUnpackingFilter
    Note over MW: AccessDenied → 401 (NICHT 403!)
    MW-->>PS: HTTP 401
    end
` ` `

## Tiefen-Baum

┌─ PHASE 1: Token holen (Keycloak OAuth2 Password Grant) ──────────
│
│  POST https://localhost:5080/realms/dcs/protocol/openid-connect/token
│  ├─ SSL/TLS Handshake gegen selbstsigniertes Zertifikat
│  │   └─ GOTCHA: PS 5.1 hat kein -SkipCertificateCheck
│  │       → add-type: C#-Klasse zur Laufzeit kompilieren (ICertificatePolicy)
│  │       → ServicePointManager.CertificatePolicy global setzen
│  ├─ Body: grant_type=password, client_id, client_secret, username, password
│  │   ├─ FAIL: dcsp-frontend → 400 (keine Direct Access Grants)
│  │   ├─ FAIL: dcsp-backend ohne secret → 401 (confidential client)
│  │   └─ dcsp-backend MIT secret → OK
│  ├─ Keycloak intern:
│  │   ├─ Client validieren (dcsp-backend, confidential, secret pruefen)
│  │   ├─ User lookup (pe-admin@dcs.invalid in realm "dcs")
│  │   ├─ Password Hash vergleichen
│  │   ├─ Realm + Client Roles laden
│  │   ├─ User Attributes laden (PflegeeinrichtungId aus realm.json)
│  │   ├─ JWT Claims bauen (sub, iss, aud, azp, roles, custom claims)
│  │   ├─ RSA-Sign (RS256) mit Realm Private Key
│  │   └─ access_token + refresh_token + expires_in zurueckgeben
│  ├─ Token extrahieren: $r.access_token
│  └─ GOTCHA: Write-Output in PS-Funktion verschmutzt Return-Wert
│      → Token war Array [Log-Zeile, Token] statt String
│      → Fix: Write-Host statt Write-Output
│
├─ PHASE 2: API-Call mit Bearer Token ──────────────────────────────
│
│  GET https://localhost:5443/api/v1/selbstauskunft/qdvtp/{vvId}
│  ├─ Authorization: Bearer eyJhbGciOi...
│  ├─ Kestrel empfaengt Request
│  ├─ ASP.NET Middleware Pipeline:
│  │   ├─ Authentication Middleware
│  │   │   ├─ JWT aus Header extrahieren
│  │   │   ├─ Base64-Decode Header + Payload
│  │   │   ├─ Signatur verifizieren (RS256 gegen Keycloak Public Key)
│  │   │   ├─ Issuer pruefen: "https://localhost:5080/realms/dcs" in ValidIssuers?
│  │   │   ├─ Expiration pruefen (exp > now)
│  │   │   ├─ ClaimsPrincipal bauen (sub, roles, custom claims)
│  │   │   └─ HttpContext.User = ClaimsPrincipal
│  │   ├─ Authorization Middleware
│  │   │   ├─ [Authorize(Policy = Policy.Pflegeeinrichtung)] pruefen
│  │   │   ├─ Policy Handler: Hat User PE-Rolle? → JA → weiter
│  │   │   └─ GOTCHA: Policy ist PERMISSIV — laesst alle PE-Rollen durch
│  │   │       Der eigentliche Check kommt SPAETER im Service
│  │   └─ Routing → SelbstauskunftController.GetQdvtp(vvId)
│  │
│  ├─ Controller → Service:
│  │   ├─ SelbstauskunftQdvtpService.ReadById(vvId)
│  │   │   ├─ VersorgungsvertragProvider.ReadByIdWithFullIncludes(vvId)
│  │   │   │   ├─ EF Core: Expression Tree → SQL
│  │   │   │   ├─ SELECT * FROM Versorgungsvertrag WHERE Id = @vvId
│  │   │   │   │   + JOINs (Pflegeeinrichtung, Landesverband, etc.)
│  │   │   │   ├─ SQL Server Container (Docker, Port 5433)
│  │   │   │   └─ Return: VV mit EinrichtungsId = Elbblick PE-ID
│  │   │   │
│  │   │   ├─ CheckPeGuard(vv.EinrichtungsId)    ← HIER PASSIERT ES
│  │   │   │   ├─ UserContextService.GetCurrentUser()
│  │   │   │   │   ├─ HttpContext.User.Claims lesen
│  │   │   │   │   ├─ Sub-Claim → User-ID → DB Lookup
│  │   │   │   │   └─ User mit PflegeeinrichtungId = Herbstlaub
│  │   │   │   ├─ user.HasPflegeeinrichtungRole() → TRUE
│  │   │   │   ├─ user.IsRestrictedFromPflegeeinrichtung(EinrichtungsId)
│  │   │   │   │   └─ Herbstlaub-PE-ID != Elbblick-PE-ID → RESTRICTED
│  │   │   │   └─ return Result.AccessDenied(ErrorCode.Forbidden)
│  │   │   │
│  │   │   └─ return AccessDenied (Guard hat geblockt)
│  │   │
│  │   └─ if (serviceResult is ErrorResult) → error.As<ReadDto>()
│  │
│  ├─ ResultUnpackingFilter (Action Filter):     ← UND HIER
│  │   ├─ IResult<T> in IActionResult konvertieren
│  │   ├─ AccessDeniedResult → new UnauthorizedObjectResult(...)
│  │   │   └─ GOTCHA: NICHT ForbidResult! → HTTP 401, NICHT 403
│  │   │       Framework-Entscheidung die man NUR durch Ausfuehren findet
│  │   └─ Response schreiben
│  │
│  └─ HTTP 401 Unauthorized → zurueck an PowerShell
│
├─ PHASE 3: Assertion ─────────────────────────────────────────────
│
│  $s = $_.Exception.Response.StatusCode.value__  → 401
│  401 -eq 401 → [PASS]
│  Write-Host "Petra->Elbblick(fremde) => HTTP 401 (erwartet: 401) [PASS]"
│
└──────────────────────────────────────────────────────────────────

Was auf dem Bildschirm stand: 1 Zeile (`HTTP 401 [PASS]`).
Was tatsaechlich passiert ist: SSL-Bypass kompilieren → Keycloak Token-Endpoint
(3 Client-Versuche) → JWT-Signatur → 7 Middleware-Stationen → DB-Query →
PE-Guard (3 Checks) → ResultUnpackingFilter → HTTP 401.

## Essenz

Die Testpyramide hat keine Spitze bis jemand den echten Endpunkt mit echten
Credentials anruft. Unit-Tests pruefen Logik. Integration-Tests pruefen
Verdrahtung. Aber erst der manuelle HTTP-Call — Token holen, Header setzen,
Status lesen — beweist, dass der Guard in der echten Middleware-Kette
funktioniert. Die drei FAILs auf dem Weg (falscher Client, fehlendes Secret,
verschmutzter Return-Wert) sind keine Fehler — sie sind der Beweis, dass
jede Schicht ihre eigenen Regeln hat die man nur durch Ausfuehren lernt.
```

**Was dieses Example zeigt:**
- **Mermaid:** 15 Messages, 2 Phasen-Bloecke, GOTCHA als Note
- **Tiefen-Baum:** 3 Phasen, ~40 Zeilen tief, 3 FAILs + 4 GOTCHAs
- **Essenz:** 5 Saetze, reflektiv, nicht zusammenfassend
- **Zusammenfassung am Ende:** "Was auf dem Bildschirm / Was dahinter"
- **Echte Session:** Kein theoretisches Beispiel sondern aus DCSRE-1430

---

## Fehler-Handling

```
+-------------------------------+--------------+-----------------------------------+
| Fehler                        | Typ          | Reaktion                          |
+-------------------------------+--------------+-----------------------------------+
| THEMA fehlt                   | BLOCKING     | FEHLER: THEMA ist Pflicht         |
| Output-Datei existiert        | NON-BLOCKING | Suffix anhaengen (_v2, _v3)       |
| Thema zu breit (>40 Zeilen)   | NON-BLOCKING | Phasen splitten, Tiefe begrenzen  |
| Thema zu trivial (<3 Schritte)| NON-BLOCKING | WARNUNG, trotzdem erstellen       |
+-------------------------------+--------------+-----------------------------------+
```

ARGUMENTS: $ARGUMENTS
