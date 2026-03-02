# /_D_migrate

**Status:** v1.0
**Actor:** DEBLOAT-MIGRATOR
**Zweck:** Konvertiert ein Legacy-Model (gross, Beobachtungs-orientiert) in das neue Separation-Format (Blueprint + Protokoll)

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_D_migrate {FEATURE} [--dry-run] [--interactive]                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                   ║
║    1. .claude/models/{FEATURE}_Model.md (Legacy-Format, gross)             ║
║    2. .claude/templates/Protokoll_Template.md (Ziel-Format)                ║
║                                                                             ║
║  LIEST (Input) - OPTIONAL:                                                  ║
║    3. .claude/analysis/_manifest.md (Kontext)                              ║
║                                                                             ║
║  SCHREIBT (Output) - PFLICHT:                                               ║
║    Backup (vor Aenderung):                                                  ║
║      .claude/models/{FEATURE}_Model_pre_migrate_{DATUM}.md                 ║
║    Protokoll-Datei (NEU):                                                   ║
║      .claude/models/{FEATURE}_Protokoll.md (via /_D_separate intern)       ║
║    Model bereinigt (via /_D_kollaps intern):                                ║
║      .claude/models/{FEATURE}_Model.md (Blueprint-Format, kompakt)         ║
║                                                                             ║
║  SCHREIBT NICHT bei --dry-run:                                              ║
║    Nur Analyse-Report, keine Datei-Aenderungen                              ║
║                                                                             ║
║  ACTOR: DEBLOAT-MIGRATOR                                                    ║
║    Fuhrt Big-Bang-Migration durch: Backup → Separate → Kollaps → Validate   ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **DEBLOAT-MIGRATOR** Actor hat eine einzige Verantwortung:

**Big-Bang-Migration: Legacy-Model → Blueprint + Protokoll**

Was der Debloat-Migrator **TUT**:
- Liest Legacy-Model und klassifiziert alle W{n} (Beobachtung vs. Mechanismus)
- Erstellt Backup vor jeder Aenderung
- Legt Protokoll-Datei an (via /_D_separate intern)
- Fuehrt Wahrheiten-Kollaps durch (via /_D_kollaps intern)
- Validiert Ergebnis gegen 5 Activation-Gate-Kriterien (W13)
- Zeigt Vorher/Nachher-Bericht

Was der Debloat-Migrator **NICHT TUT**:
- Loescht Backups (bleibt 7 Tage als Rollback-Option)
- Migriert mehrere Features gleichzeitig
- Schreibt Code (kein I-Zyklus)
- Pusht zu Git (kein git push)

---

## Chain-Position

```
MANUELL oder /_D_orchestrate
        |
        v
/_D_migrate {FEATURE}
        |
        +-- [Backup erstellen]
        +-- [/_D_separate {FEATURE}] (intern)
        +-- [HiL-Checkpoint: Bestaetigung vor Kollaps]
        +-- [/_D_kollaps {FEATURE}] (intern)
        +-- [Validation: 5 Gate-Kriterien]
        |
        v
  {FEATURE}_Model.md (Blueprint, kompakt)
  {FEATURE}_Protokoll.md (Wahrheiten, neu)
  {FEATURE}_Model_pre_migrate_{DATUM}.md (Backup, 7 Tage)
```

---

## Ablauf

### Phase 1: Analyse

```
1. Lies {FEATURE}_Model.md (Legacy)
2. Zaehle W{n} gesamt
3. Klassifiziere jeden W{n}-Block:
   - BEOBACHTUNG: "Was haben wir gemessen/festgestellt?" → gehoert ins Protokoll
   - MECHANISMUS:  "Wie funktioniert es kausal?"          → gehoert ins Blueprint
4. Erzeuge Klassifizierungs-Report:
   - Anzahl W{n} total
   - Anzahl Beobachtungen (→ Protokoll)
   - Anzahl Mechanismen (→ Blueprint behalten)
   - Cluster-Vorschlaege (<!-- cluster: X --> Tags)
   - Geschaetzte neue Model-Zeilenzahl nach Migration
```

**Klassifizierungs-Entscheidungshilfe:**

| Frage | Antwort JA | Antwort NEIN |
|-------|-----------|-------------|
| "Was haben wir gemessen?" | BEOBACHTUNG → Protokoll | weiter |
| "Wie funktioniert X kausal?" | MECHANISMUS → Blueprint | weiter |
| "Widerlegt es ein anderes W{n}?" | WIDERL. → Protokoll archiviert | weiter |
| "Zeigt es ein Cluster-Muster (>=5)?" | Kollaps-Kandidat | PENDING |

**Bei --dry-run:** Endet hier. Zeigt Report, keine Datei-Aenderungen.

---

### Phase 2: HiL-Checkpoint (Human-in-Loop)

```
[PAUSE - BESTAETIGUNG ERFORDERLICH]

Migrationsziel: {FEATURE}_Model.md
  Aktuell: {N} W{n} / {ZEILEN} Zeilen
  Nach Migration: ~{M} Mechanismen im Blueprint / ~{K} Zeilen
  Beobachtungen → Protokoll: {X} W{n}

Backup wird erstellt: {FEATURE}_Model_pre_migrate_{DATUM}.md
Rollback-Fenster: 7 Tage (T+7)

[Y/N] Migration starten?
```

Bei N: Abbruch. Keine Datei-Aenderungen. Exit.
Bei Y: Weiter zu Phase 3.

**Bei --interactive:** Zeigt zusaetzlich jeden W{n} einzeln:
```
W{N}: {Titel}
  {These-Text (gekuerzt)}
  Klassifizierung: BEOBACHTUNG | MECHANISMUS | WIDERL.?
  [B/M/W] Ihre Entscheidung:
```

---

### Phase 3: Sicherung (Backup)

```
1. Kopiere {FEATURE}_Model.md → {FEATURE}_Model_pre_migrate_{DATUM}.md
   (DATUM = YYYY-MM-DD, z.B. OmniCommand_Model_pre_migrate_2026-02-26.md)
2. Verifiziere Backup: Groesse > 0, Zeilen == Original
3. Log: "Backup erstellt: {PFAD}"
```

Rollback-Anweisung (falls noetig):
```bash
# Manueller Rollback:
cp .claude/models/{FEATURE}_Model_pre_migrate_{DATUM}.md .claude/models/{FEATURE}_Model.md
```

---

### Phase 4: Protokoll anlegen (via /_D_separate intern)

```
Rufe /_D_separate {FEATURE} intern auf:
  → Prueft ob {FEATURE}_Protokoll.md existiert
  → Falls NEIN: Erstellt aus Protokoll_Template.md
  → Falls JA: Prueft ob Format aktuell (YAML + 3 Sektionen)
  → Traegt alle klassifizierten BEOBACHTUNGS-W{n} ein (Status: OFFEN)
  → Setzt Cluster-Tags (<!-- cluster: X -->) aus Phase 1 Analyse
```

---

### Phase 5: Kollaps (via /_D_kollaps intern)

```
Rufe /_D_kollaps {FEATURE} intern auf:
  → P1 SCAN: W{n} seit letztem Kollaps zaehlen (alle, da erste Migration)
  → P2 ANALYSE: Cluster identifizieren, Kausal-Ketten finden
  → P3 KONDENSIERUNG: Mermaid-Update generieren
       - Bei NLP-Confidence >0.85: vollautomatisch
       - Bei Confidence 0.65-0.85: Human-Review (W07)
       - Bei Confidence <0.65: Human-Review zwingend (W07)
  → P4 MARKING: INTEGRATED-Status setzen + Backref eintragen
  → P5 QS: Checks Q1-Q6, Rollback bei Fehler
```

---

### Phase 6: Validation (Activation-Gate, W13)

5 Pass/Fail-Kriterien (alle muessen PASS sein):

| # | Kriterium | Pass-Bedingung | Pruefung |
|---|-----------|---------------|---------|
| 1 | Groesse | Neues Model ≤30KB (oder <=500 Zeilen) | `wc -c`, `wc -l` |
| 2 | Vollstaendigkeit | Alle W{n} aus Legacy tracebar (in Protokoll ODER Blueprint) | Mapping-Report |
| 3 | Konsistenz | BESTAETIGTE W{n} validiert gegen neues Blueprint | Stichprobe |
| 4 | Links | Alle Querverweise (Backref) funktionieren | Link-Check |
| 5 | Freigabe | Team-Lead Signoff | [Y/N] Prompt |

Bei FAIL: Kein Rollback automatisch. User entscheidet:
```
[GATE FAIL: Kriterium {N} - {Beschreibung}]
Optionen:
  [R] Rollback auf Backup
  [C] Manuell korrigieren und Gate nochmal pruefen
  [S] Skip (auf eigene Verantwortung, nicht empfohlen)
```

---

### Phase 7: Summary

```
Migration abgeschlossen:

{FEATURE}_Model.md:
  Vorher: {N} W{n} / {ZEILEN_ALT} Zeilen / {KB_ALT} KB
  Nachher: {M} Mechanismen / {ZEILEN_NEU} Zeilen / {KB_NEU} KB
  Reduktion: {PROZENT}%

{FEATURE}_Protokoll.md:
  Erstellt: {ZEILEN_PROT} Zeilen
  Aktive W{n}: {X} (OFFEN/BESTAETIGT)
  Archivierte W{n}: {Y} (INTEGRATED aus Kollaps-Lauf)

Backup:
  {FEATURE}_Model_pre_migrate_{DATUM}.md
  Rollback-Fenster: bis {DATUM+7}

Activation-Gate: PASS (alle 5 Kriterien erfuellt)
```

---

## Migrations-Zeitplan (Big-Bang, W10)

```
T-1:  Git-Tag erstellen: "pre-collapse-{FEATURE}-{DATUM}"
T+0:  Migration starten (/_D_migrate {FEATURE})
T+2:  Activation-Gate: 5-Kriterien-Check + Team-Lead Signoff
      → PASS: Migration produktiv
      → FAIL: Rollback, altes Model bleibt aktiv
T+7:  Rollback-Fenster endet. Backup → cold (kein Auto-Delete)
```

---

## Migrations-Reihenfolge (W10, Prio)

| Prio | Model | Groesse | Strategie |
|------|-------|---------|-----------|
| 1 (Pilot) | OmniCommand_Model.md | 120KB / 70 W{n} | Big-Bang |
| 2 | WissensKoaleszenz_Model.md | ~50KB / ~35 W{n} | Big-Bang |
| 3 | WritePaper_Vorlage_Model.md | ~20KB / ~15 W{n} | Inkrementell |
| 4+ | Weitere Models | 10-30KB | Inkrementell |

---

## Flags

| Flag | Bedeutung |
|------|----------|
| `--dry-run` | Nur Analyse-Report (Phase 1), keine Datei-Aenderungen |
| `--interactive` | Zeigt jeden W{n} einzeln zur manuellen Klassifizierung (Phase 1+2) |

Kombination `--dry-run --interactive` nicht sinnvoll (--dry-run endet vor HiL).

---

## Kompakt-Sicherheit

Command schreibt in drei Dateien:
- **Backup:** unveraenderte Kopie (Rollback-Option)
- **Protokoll:** neue Datei (append-only Wahrheiten)
- **Model:** bereinigt zu Blueprint-Format

State nach Migration: Beide Dateien existieren, Model ist kompakt (<500 Zeilen).
Resume nach Unterbrechung: Backup pruefen → falls vorhanden, Migration abgebrochen.
Rollback: Backup-Datei manuell zurueckkopieren.

---

## Siehe auch

- [[_D_orchestrate]] - Entry-Point (ruft /_D_migrate bei fehlerhaftem Format)
- [[_D_separate]] - Protokoll-Anlege-Logik (wird intern aufgerufen)
- [[_D_kollaps]] - 5-Phasen-Wahrheiten-Kollaps (wird intern aufgerufen)
- [[Protokoll_Template]] - Template fuer neue Protokoll-Dateien
- [[ModelBloat_Model]] - W10 (Big-Bang), W13 (Activation-Gate), Kap. 6 (Migrations-Strategie)
