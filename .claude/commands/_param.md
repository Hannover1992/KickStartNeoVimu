# /_param - Globale Session-Parameter setzen

```yaml
status: active
version: 1.0.0
created: 2026-02-28
type: command
chain_position: standalone
team_based: false
changelog: |
  v1.0: Initialer Entwurf (Vorhaben 1: Globale Parameter).
        Setzt GLOBAL_DIFFICULTY, GLOBAL_CEILING, GLOBAL_FLOOR im Manifest.
        Validierung: ceiling >= floor (Opus=3 > Sonnet=2 > Haiku=1).
        Alle Orchestratoren lesen diese Werte beim Start.
```

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_param                                                    ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    .claude/analysis/_manifest.md  (aktuelle GLOBAL_* Werte)         ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/analysis/_manifest.md  (GLOBAL_DIFFICULTY/CEILING/FLOOR) ║
║                                                                      ║
║  ACTOR: DU (die ausfuehrende Claude-Instanz, KEIN Team)            ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_param [difficulty=WERT] [ceiling=WERT] [floor=WERT]
/_param show
/_param reset
```

| Parameter | Werte | Beschreibung |
|-----------|-------|-------------|
| `difficulty` | easy, normal, hard | Globale Schwierigkeit (ueberschreibt lokale Defaults) |
| `ceiling` | haiku, sonnet, opus | Hoechstes erlaubtes Modell fuer alle Orchestratoren |
| `floor` | haiku, sonnet | Niedrigstes Modell fuer Exploration-Wellen |
| `show` | — | Zeigt aktuelle globale Parameter |
| `reset` | — | Entfernt alle GLOBAL_* Felder (zurueck zu lokalen Defaults) |

**Beispiele:**
```
/_param difficulty=hard ceiling=opus floor=sonnet    → Volle Kraft
/_param difficulty=normal ceiling=sonnet floor=haiku  → Standard
/_param ceiling=sonnet                                → Nur ceiling aendern
/_param show                                          → Aktuellen Stand zeigen
/_param reset                                         → Globale Parameter entfernen
```

---

## Modell-Hierarchie

```
Opus(3) > Sonnet(2) > Haiku(1)
```

**Validierung:** ceiling >= floor (sonst Fehler).
**Capping-Formel (von Orchestratoren angewandt):**
```
effektiv_ceiling = min(lokal_ceiling, GLOBAL_CEILING)
effektiv_floor   = max(lokal_floor, GLOBAL_FLOOR)
effektiv_difficulty = GLOBAL_DIFFICULTY (falls gesetzt, ueberschreibt lokal)
```

---

## Schritte

### Schritt 1: Argumente parsen

Parse `$ARGUMENTS` nach key=value Paaren:
- `difficulty=X` → validiere X in {easy, normal, hard}
- `ceiling=X` → validiere X in {haiku, sonnet, opus}
- `floor=X` → validiere X in {haiku, sonnet}
- `show` → springe zu Schritt 4
- `reset` → springe zu Schritt 5
- Keine Argumente → zeige aktuellen Stand (wie `show`)

### Schritt 2: Validierung

Falls sowohl ceiling als auch floor angegeben (oder einer gesetzt + anderer aus Manifest):
```
Hierarchie-Werte: opus=3, sonnet=2, haiku=1
IF ceiling_wert < floor_wert:
  FEHLER: "ceiling ({ceiling}) darf nicht unter floor ({floor}) liegen."
  ABBRUCH.
```

### Schritt 3: In Manifest schreiben

Lies `.claude/analysis/_manifest.md`.
Aktualisiere die GLOBAL_* Felder im Header-Bereich (nach Zeile 1, vor dem ersten `###`):

- Falls `difficulty` angegeben: Setze/aktualisiere `**GLOBAL_DIFFICULTY:** {wert}`
- Falls `ceiling` angegeben: Setze/aktualisiere `**GLOBAL_CEILING:** {wert}`
- Falls `floor` angegeben: Setze/aktualisiere `**GLOBAL_FLOOR:** {wert}`

Falls ein GLOBAL_* Feld schon existiert: ueberschreiben.
Falls es nicht existiert: nach der letzten GLOBAL_* Zeile (oder nach PUSH_STATUS) einfuegen.

### Schritt 4: Show (Anzeige)

Lies Manifest und zeige:
```
Globale Parameter:
  GLOBAL_DIFFICULTY: {wert | "nicht gesetzt (lokale Defaults)"}
  GLOBAL_CEILING:    {wert | "nicht gesetzt (lokale Defaults)"}
  GLOBAL_FLOOR:      {wert | "nicht gesetzt (lokale Defaults)"}

Effektive Wirkung auf Orchestratoren:
  Explorer:  {floor}
  Drafter:   {middle}
  Synthese:  {ceiling}
```

### Schritt 5: Reset

Entferne alle Zeilen mit `**GLOBAL_DIFFICULTY:**`, `**GLOBAL_CEILING:**`, `**GLOBAL_FLOOR:**` aus dem Manifest.
Melde: "Globale Parameter entfernt. Orchestratoren nutzen lokale Defaults."
