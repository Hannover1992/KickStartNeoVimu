---
type: satellite
---

# Out of the Box - First Principles Debugging

Wenn ein Problem hartnäckig ist und normale Lösungen nicht funktionieren, wende diesen Prozess an:

## Phase 1: Ursache und Wirkung (Root Cause)

Frage dich:
1. **Was ist das SYMPTOM?** (Was sehen wir?)
2. **Was ist die URSACHE?** (Warum passiert das?)
3. **Was ist die ROOT CAUSE?** (Die tiefste Ursache)

```
SYMPTOM → URSACHE → ROOT CAUSE
   ↑         ↑          ↑
 sichtbar  vermutet   WAHR
```

## Phase 2: Flaschenhals identifizieren

```
A ──► B ──► C ──► D
      │
      └─► FLASCHENHALS (hier staut es sich)
```

Fragen:
1. **WO staut es sich?** (Welcher Schritt dauert ewig?)
2. **WARUM staut es sich?** (Ressource, Netzwerk, Berechtigung?)
3. **Kann ich den Flaschenhals UMGEHEN?** (Alternativer Pfad?)

**Typische Flaschenhälse:**
| Bereich | Beispiele |
|---------|-----------|
| Netzwerk | Proxy, Firewall, DNS, Timeout |
| Ressourcen | CPU, RAM, Disk I/O |
| Externe Services | npm Registry, NuGet, Docker Hub |
| Berechtigungen | Zertifikate, Tokens, API Keys |

## Phase 3: First Principles

Zerlege das Problem in Grundbausteine:
1. **Was passiert WIRKLICH?** (nicht was wir denken)
2. **Was sind die KOMPONENTEN?** (Netzwerk, Dateien, Prozesse)
3. **Was ist der DATENFLUSS?** (A → B → C)

## Phase 3: Think Out of the Box

Buchstäblich "außerhalb der Box" denken:
- **Docker Box:** Was passiert AUSSERHALB des Containers?
- **Netzwerk Box:** Was passiert ZWISCHEN den Systemen?
- **Firmen Box:** Welche Firmen-Infrastruktur ist beteiligt? (Proxy, VPN, Firewall)

## Phase 4: Was ist IN UNSERER MACHT?

| In unserer Macht | Nicht in unserer Macht |
|------------------|------------------------|
| Code ändern | Server-Infrastruktur |
| Config ändern | Firmen-Proxy |
| Workaround finden | Externe APIs |
| Parameter nutzen | Netzwerk-Policies |

**ABER:** Manchmal gibt es schon eine Lösung die wir übersehen haben!

## Phase 5: Die versteckten Optionen

Suche nach:
1. **Bestehende Config-Dateien** (`.env`, `.env.noproxy`, etc.)
2. **Ungenutzte Parameter** (`-EnvFile`, `--no-proxy`, etc.)
3. **Alternative Pfade** (direkt statt über Proxy)

## Beispiel: npm ci hängt

```
SYMPTOM:     npm ci hängt im Docker Build
URSACHE:     Netzwerk-Problem beim Laden von Paketen
ROOT CAUSE:  Firmen-Proxy (blackspider) blockiert/verlangsamt npm

FLASCHENHALS IDENTIFIZIERT:
┌────────┐    ┌─────────────┐    ┌──────────┐
│ Docker │ ─► │ PROXY       │ ─► │ npmjs.org│
│        │    │ blackspider │    │          │
└────────┘    └─────────────┘    └──────────┘
                    │
                    └─► FLASCHENHALS! (langsam/blockiert)

FLASCHENHALS UMGEHEN:
┌────────┐                       ┌──────────┐
│ Docker │ ─────── direkt ─────► │ npmjs.org│
└────────┘                       └──────────┘
       │
       └─► KEIN Proxy = SCHNELL!

OUT OF THE BOX DENKEN:
- Docker = eigenes Netzwerk (nicht Windows-Host)
- Muss NICHT über Firmen-Proxy gehen
- .env.noproxy existiert bereits! (versteckte Lösung)

LÖSUNG:
.\docker-up.ps1 -EnvFile "./.env.noproxy" -NoCache -SkipTests
```

## Checkliste

- [ ] Symptom klar identifiziert?
- [ ] Ursache vs. Root Cause unterschieden?
- [ ] **FLASCHENHALS gefunden?** (Wo staut es sich?)
- [ ] **Kann Flaschenhals UMGANGEN werden?**
- [ ] Alle "Boxen" betrachtet? (Docker, Netzwerk, Firma)
- [ ] Bestehende Lösungen/Configs gesucht?
- [ ] Was ist IN unserer Macht?

---

**Referenz:** MODEL.md v1.5, W23-W24
