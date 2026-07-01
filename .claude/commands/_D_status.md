---
type: building-block
---

# /_D_status

**Status:** NEU v1.0 (KontextManagement Slice 1)
**Actor:** DIAGNOSE
**Zweck:** Globaler Health-Check — Zeilen-Karte + Ampel-System fuer alle Artefakt-Typen

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_D_status [NAME] [--full] [--fix] [--type=<typ>]    |
+===============================================================+
|                                                                |
|  LIEST (Input) — PFLICHT:                                      |
|    .claude/commands/*.md                                       |
|    .claude/models/*.md                                         |
|    {VAULT}/_manifest.md                               |
|    {VAULT}/_manifest_protokoll.md                     |
|    .claude/wissen/*.md                                         |
|    .claude/specs/*.md                                          |
|    .claude/analysis/synthese/*.md                              |
|    .claude/pileOfMud/*.md                                      |
|    .claude/analysis/drafts/*.md (falls vorhanden)              |
|    .claude/crumbs/*.md (falls vorhanden)                       |
|    (Schwellen-Matrix: eingebettet, siehe Kap. 2)               |
|                                                                |
|  SCHREIBT (Output) — ohne --fix:                               |
|    KEINES — rein diagnostisch, idempotent                      |
|    [Ausgabe: Zeilen-Karte als Text-Tabelle]                    |
|                                                                |
|  SCHREIBT (Output) — mit --fix:                                |
|    Delegiert an /_D_orchestrate (schreibt Model + Manifest)    |
|    Nur fuer ROT-Artefakte (HARD-Schwelle ueberschritten)       |
|                                                                |
|  INVARIANTEN:                                                  |
|    - Synthese-Dateien: NIEMALS WARNING/ALARM (Ampel = n/a)     |
|    - pileOfMud: IMMER INFO, nie GELB/ROT                       |
|    - Exploration/Drafts: IMMER INFO, nie GELB/ROT              |
|    - --fix: NUR bei ROT (HARD-Trigger), niemals bei GELB       |
|    - Ohne --fix: 0 Schreiboperationen (idempotent)             |
|    - bob.md ist Referenz-Datei — von Schwellen ausgenommen     |
|                                                                |
+===============================================================+
```

---

## 1. Verantwortlichkeit

Der **DIAGNOSE** Actor hat eine einzige Verantwortung:

**Messen und Melden — niemals selbst handeln (ohne --fix)**

Was /_D_status **TUT**:
- Zaehlt Zeilen aller Artefakt-Dateien (`wc -l`)
- Berechnet Ampel pro Datei (GRUEN / GELB / ROT / INFO / n/a)
- Gibt Zeilen-Karte als Tabelle aus
- Optional: filtert nach Artefakt-Typ (`--type=Model`)
- Optional: zeigt Details aller Dateien (`--full`)
- Optional: delegiert Debloat an /_D_orchestrate (`--fix`)

Was /_D_status **NICHT TUT**:
- Dateien aendern (ohne --fix)
- Debloat selbst ausfuehren (delegiert an _D_orchestrate)
- Archivierung ausfuehren
- VERTRAG-Bloecke pruefen (das macht Gate 7 in _SC_qualityGate)

---

## 2. Schwellen-Matrix (eingebettet)

```
Ampel-System: GRUEN (< SOFT) → GELB (>= SOFT, < HARD) → ROT (>= HARD)
Sonderstatus: INFO (kein Trigger) | n/a (SCHUTZ, niemals Alarm)
```

| Artefakt-Typ | Glob-Pattern | SOFT | HARD | Mechanismus bei ROT | Klasse |
|-------------|-------------|------|------|---------------------|--------|
| Model | `models/*_Model.md` | 500 | 700 | _D_orchestrate (Debloat) | A |
| Command | `commands/*.md` | 800 | 1200 | Konsolidierung (HiL, manuell) | D |
| Spec | `specs/*_Spec.md` | 700 | 1000 | Review (HiL, manuell) | D |
| Manifest-State | `analysis/_manifest.md` | 400 | 600 | Pattern B Rollover | A |
| Manifest-Protokoll | `analysis/_manifest_protokoll.md` | 5000 | 8000 | Jahres-Block-Rotation | C |
| Wissen | `wissen/*.md` | 400 | 600 | Vault-Sync (_W_obsidianSync) | B |
| Crumbs | `crumbs/*.md` | 300 | 500 | Konsolidierung | B |
| pileOfMud | `pileOfMud/*.md` | INFO | INFO | keine (Sonderstatus) | C |
| Exploration/Drafts | `analysis/drafts/*.md` | INFO | INFO | Archive-Hook | B |
| Synthese | `analysis/synthese/*.md` | n/a | n/a | NIEMALS (SCHUTZ) | C |

**Ausnahmen:**
- `commands/bob.md` — Referenz-Datei, wird uebersprungen
- `*-Topologie.md` in models/ — Topologie-Dateien, Schwelle wie Model

---

## 3. Algorithmus

```
SCHRITT 1: Dateien sammeln
  Fuer jeden Artefakt-Typ aus Schwellen-Matrix:
    → Glob-Pattern ausfuehren
    → Zeilen zaehlen (wc -l)
    → Ausnahmen filtern (bob.md)

SCHRITT 2: Ampel berechnen
  Fuer jede Datei:
    WENN Typ = Synthese     → Ampel = n/a
    WENN Typ = pileOfMud    → Ampel = INFO
    WENN Typ = Drafts       → Ampel = INFO

    # Index-Model-Erkennung (IF-10, Pfad A)
    WENN Typ = Model:
      Lies Model-Frontmatter → model_type Feld
      IF model_type == "index":
        Logge: "Index-Model erkannt: HARD-Trigger wird auf 2000 Zeilen angehoben (statt 700)"
        HARD = 2000
        SOFT = 1200
      ELSE:
        # Standard-Schwellen (Content-Model)
        HARD = 700
        SOFT = 500

    WENN Zeilen >= HARD     → Ampel = ROT
    WENN Zeilen >= SOFT     → Ampel = GELB
    SONST                   → Ampel = GRUEN

SCHRITT 3: --type Filter (optional)
  WENN --type angegeben:
    → Nur Dateien des angegebenen Typs anzeigen
    → Gueltige Typen: Model, Command, Spec, Manifest, Protokoll,
                       Wissen, Crumbs, pileOfMud, Drafts, Synthese

SCHRITT 4: Ausgabe
  WENN --full:
    → Alle Dateien anzeigen (inkl. GRUEN)
  SONST:
    → Nur GELB + ROT + Summary anzeigen

SCHRITT 5: --fix Delegation (optional)
  WENN --fix UND ROT-Models vorhanden:
    → Fuer jedes ROT-Model: /_D_orchestrate {MODEL_NAME}
    → Fuer andere ROT-Typen: WARNING ausgeben (manuell via HiL)
  WENN --fix UND keine ROT-Artefakte:
    → "Keine ROT-Artefakte. Nichts zu tun."
```

---

## 4. Ausgabe-Format (Zeilen-Karte)

### Standard-Ausgabe (nur Probleme + Summary)

```markdown
# Zeilen-Karte: {NAME} ({Datum})

## Zusammenfassung

| Ampel | Anzahl |
|-------|--------|
| ROT   | {N}    |
| GELB  | {N}    |
| GRUEN | {N}    |
| INFO  | {N}    |
| n/a   | {N}    |

## Probleme (GELB + ROT)

| Datei | Typ | Zeilen | Ampel | SOFT | HARD |
|-------|-----|--------|-------|------|------|
| models/X_Model.md | Model | 1330 | ROT | 500 | 700 |
| commands/_WP_orchestrate.md | Command | 1423 | ROT | 800 | 1200 |
| ... | ... | ... | ... | ... | ... |

## Empfehlung

- ROT Models: `/_D_status --fix` oder `/_D_orchestrate {NAME}`
- ROT Commands: Manuelle Konsolidierung empfohlen (HiL)
- GELB: Beobachten, kein sofortiger Handlungsbedarf
```

### --full Ausgabe (alle Dateien)

Wie Standard, aber mit zusaetzlicher Tabelle:

```markdown
## Alle Artefakte

| Datei | Typ | Zeilen | Ampel | SOFT | HARD |
|-------|-----|--------|-------|------|------|
| models/X_Model.md | Model | 320 | GRUEN | 500 | 700 |
| analysis/synthese/X-GAP.md | Synthese | 294 | n/a | - | - |
| pileOfMud/X_Kontext.md | pileOfMud | 150 | INFO | - | - |
| ... | ... | ... | ... | ... | ... |
```

---

## 5. Parameter

| Parameter | Pflicht | Beschreibung |
|-----------|---------|-------------|
| `NAME` | OPTIONAL | Feature-Name — wenn angegeben, nur Dateien mit {NAME} im Pfad. Ohne NAME: alle Dateien. |
| `--full` | OPTIONAL | Alle Dateien anzeigen (inkl. GRUEN, INFO, n/a) |
| `--fix` | OPTIONAL | ROT-Models automatisch an /_D_orchestrate delegieren |
| `--type=<typ>` | OPTIONAL | Nur einen Artefakt-Typ pruefen (Model, Command, Spec, Manifest, Protokoll, Wissen, Crumbs, pileOfMud, Drafts, Synthese) |

---

## 6. Integration

### CP-1 PRE-CYCLE (in _SC_orchestrate)

/_D_status wird automatisch als erster PRE-CYCLE-Schritt aufgerufen.
Ausgabe dient als Baseline-Orientierung fuer den Team Lead.
Bei HARD-Trigger: WARNING + Log (kein ABORT — informativ).

### CP-3 nach modelMaintain (existiert bereits)

_SC_modelMaintain Schritt 0 hat bereits einen SOFT/HARD-Check fuer Models.
/_D_status verallgemeinert dies auf alle Artefakt-Typen.

### Ad-hoc Aufruf

/_D_status kann jederzeit manuell aufgerufen werden.
Idempotent: beliebig oft aufrufbar ohne Seiteneffekte.

---

## Kompakt-Sicherheit

Nach Command-Abschluss:
- State: Keine Aenderungen (ohne --fix)
- Resume: Zeilen-Karte als Text-Output, nicht persistent

---

## Siehe auch

- [[_D_orchestrate]] - Debloat-Aktor (wird von --fix aufgerufen)
- [[_D_kollaps]] - 5-Phasen-Kollaps fuer Models
- [[_SC_modelMaintain]] - Hat Mini-Version fuer Models (Schritt 0)
- [[_SC_qualityGate]] - Gate 7 Contract Audit (orthogonale Achse)
- [[_SC_orchestrate]] - CP-1 PRE-CYCLE Integration
