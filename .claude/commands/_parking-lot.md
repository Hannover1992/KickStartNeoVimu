---
type: satellite
version: 3.2.0
bl_201: true
bl_271: true
entry_point: 3
invariant: INV-PL-WRITER-1, INV-PL-LEARN-1, INV-PL-LEARN-2, INV-PL-LEARN-3
---

# CMD: _parking-lot.md

**Status:** v3.2.0 (BL-271 batch_2: Modus-Capture-Routing INV-PL-LEARN-3 + AK-S3/S4-Reuse + Git-Trailer-Follow-up; batch_1 Lern-Felder commit_ref + classification; BL-201 Entry-3-Upgrade)
**Typ:** 3. Entry-Point (Leichtgewicht) + Legacy APPEND-ONLY Queue
**Zweck:** Entry 3 — direkter Eingang ins PL-Stream (LEICHTGEWICHT) + Incidental Findings sammeln

---

## BL-201: Entry 3 Skill-Vertrag (NEU v3.0.0)

```
+======================================================================+
|  VERTRAG: /_parking-lot (Entry 3 — Leichtgewichts-Direkt-Pfad)       |
|  BL-201 | INV-ENTRY-3 | INV-PL-WRITER-1                              |
+======================================================================+
|  LIEST:                                                              |
|    - --bl=BL-NNN Parameter (explizit, hoechste Prio)                |
|    - {vault}/_current_context.md oder {factory_manifest}            |
|      current_context.bl_id (wenn kein --bl Parameter)               |
|                                                                      |
|  SCHREIBT (Single-Writer — INV-PL-WRITER-1):                        |
|    - Prio 1: {vault}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md  |
|              (wenn BL-Kontext bekannt via --bl oder current_context) |
|    - Fallback: {vault}/_parking-lot.md                               |
|              (wenn kein Kontext + GLOBAL_HIL=off)                   |
|    - {bl_slug}/_manifest.md:                                         |
|      DF_BATCH_STATE.parking_lot_modified_since_last_idf = true       |
|                                                                      |
|  OUTPUTS:                                                            |
|    - PL-Item-ID (PL-{BL-NNN}-{NNN} oder PL-GLOBAL-{NNN})           |
|    - Schreibpfad (zur Verifikation)                                  |
|    - Bestaetigung: "PL-Item angelegt: {ID} in {Pfad}"               |
|                                                                      |
|  PARAMETER:                                                          |
|    - args[0]: Freitext (Beschreibung des PL-Items) PFLICHT           |
|    - --bl=BL-NNN: BL-Zuordnung (optional, empfohlen)                |
|    - --type=correction|addition|question|learning|observation        |
|      (optional, Default: addition)                                   |
|      BL-271 AK-S1 correction-Subtypen:                               |
|        inkorrekte_umsetzung | kurs_korrektur (zaehlen als Lern-Signal)|
|    - --commit-ref=<hash> (optional, BL-271 — Korrektur-Commit 7-40 Hex)|
|    - --classification=semantic|architectural|fachlich|factoring       |
|      (optional, BL-271 — die 4 PT-classify-Achsen)                   |
|    - --priority=HIGH|MEDIUM|LOW (optional, Default: MEDIUM)         |
|    - --ak=AK-N (optional, AK-Referenz)                              |
|                                                                      |
|  ANTI (VERBOTEN):                                                    |
|    - KEIN A-Pipeline-Run ausloesen                                   |
|    - KEIN IDF-Direkt-Aufruf                                          |
|    - KEIN HiL-Dialog wenn GLOBAL_HIL=off                            |
|    - KEIN Batching mehrerer Items pro Aufruf                         |
|    - KEIN Schreiben in Backlog/{bl_slug}/_manifest.md ausser         |
|      DF_BATCH_STATE.parking_lot_modified_since_last_idf              |
+======================================================================+
```

### INV-PL-WRITER-1 — Single-Writer-Disziplin

```
INV-PL-WRITER-1: {bl_id}-parking-lot.md Single-Writer-Disziplin (BL-201; Kanon-Name 2026-05-29)
  ERLAUBTE Writer fuer {bl_slug}/6_PL/{bl_id}-parking-lot.md:
    a) _A_berater_plAggregation (Phase 5c — Forward-Generierung aus Spec)
       [INV-PL-1 in _A_orchestrate]
    b) /_parking-lot Skill (Entry 3 — direkter User-Eingriff, Leichtgewicht)
    c) _IDF_berater_modelSync (Phase 3.7 — Reverse-Annotationen)
       [INV-IDF-REVERSE-1 in _IDF_orchestrate]
  VERBOTEN: alle anderen Komponenten
  ENFORCEMENT: konventionell (Skill-Vertraege dokumentieren Scope)
  RATIONALE: Race-Condition-Verhinderung bei parallelen Terminals.
             Append-Only-Semantik der Schreibweise schafft zusaetzliche Sicherheit.
  REFERENZEN: BL-201, architecture-vision-2026-05-22.md INV-ENTRY-3
```

### INV-ENTRY-3 — Stream-Charakter

```
INV-ENTRY-3: Entry 3 ist Stream (viele kleine Eintraege), nicht Reservoir.
  - Jeder Aufruf erzeugt GENAU 1 PL-Item
  - Keine Bulk-Imports
  - Granularitaet muss erhalten bleiben
  - Kein Batching
  Quelle: architecture-vision-2026-05-22.md Sanduhren-Prinzip
```

### PL-Item-Frontmatter-Schema (BL-201 AK-4)

Jedes von `/_parking-lot` geschriebene PL-Item hat folgendes Frontmatter:

```yaml
---
pl_item_id: "PL-{BL-NNN}-{NNN}"    # z.B. PL-201-001
title: "Kurzbeschreibung"
type: correction | addition | question | learning | observation
bl_ref: "BL-{NNN}"                  # BL-Referenz (oder GLOBAL)
ak_ref: "AK-{N}"                    # optional
priority: HIGH | MEDIUM | LOW
status: OPEN                        # Initial immer OPEN
created: "YYYY-MM-DD"
source: entry3                      # IMMER entry3 bei /_parking-lot
depends_on: []                      # andere PL-Item-IDs (optional)
entry_point: "/_parking-lot"
# --- BL-271 Lern-Felder (OPTIONAL, abwaertskompatibel) ---
commit_ref: "a96eb1c"               # OPTIONAL — Commit-Hash der Korrektur (7-40 Hex)
classification: factoring           # OPTIONAL — eine der 4 PT-classify-Achsen
                                    #   semantic | architectural | fachlich | factoring
---
```

### BL-271: Lern-Felder am Capture-Punkt (commit_ref + classification)

**Problem (User-Voice + 486-Empirie):** Stille Korrekturen = verlorenes Lernen.
Soll ein PL-Item-Lern-Signal spaeter ERNTBAR sein (`_PT_berater_classify` /
PT-Extraction), braucht das Item die Klassifikations-Achse + den Korrektur-Commit
schon am **Entstehungsort**. 486-Empirie: nur ~19% der `[x]`-Items trugen einen
Commit-Pointer (als Freitext), und KEIN Item trug ein Klassifikations-Label —
`_PT_berater_classify` musste die Achse teuer rekonstruieren statt sie zu lesen.

Darum tragen PL-Items ZWEI neue, **OPTIONALE** Frontmatter-Felder:

```yaml
commit_ref: "<hash>"          # OPTIONAL — Pointer auf den Commit der Korrektur.
                              #   Plausibler Git-Hash: 7-40 Hex-Zeichen (abgekuerzt..voll).
classification: <achse>       # OPTIONAL — eine der 4 PT-classify-Achsen am Entstehungsort:
                              #   semantic | architectural | fachlich | factoring
```

**classification-Enum = EXAKT die 4 `_PT_berater_classify`-Achsen** (reuse, KEINE
Divergenz — Single-Source ist `_PT_berater_classify.md`):

| Achse | Bedeutung (PT-classify) |
|---|---|
| `semantic` | Naming/Vokabular/Ausdrucks-Konvention |
| `architectural` | Struktur/Layer/Kopplung/Schichtgrenze (statischer ZUSTAND) |
| `fachlich` | Domaenen-Begriff/Geschaeftsregel (== der Auftrags-Sprachgebrauch "domain") |
| `factoring` | Struktur-TRANSFORMATION / Refactoring-Bewegung (== "refactoring") |

> **Naming-Hinweis:** der PT-classify-Vertrag nutzt die deutschen/etablierten
> Labels `fachlich` und `factoring`. Wer umgangssprachlich "domain" bzw.
> "refactoring" meint, schreibt trotzdem `fachlich` / `factoring` — NICHT
> divergieren, sonst liest `_PT_berater_classify` die Achse nicht.

**INV-PL-LEARN-1 (Abwaertskompatibilitaet):** BEIDE Felder sind OPTIONAL. Ein
Bestands-PL-Item OHNE diese Felder bleibt VOLLSTAENDIG valide. Fehlend / `None` /
Leer-String == "nicht gesetzt" == valide. Der bestehende /_parking-lot-Vertrag
(Checkboxen, APPEND-ONLY, INV-5) wird NICHT gebrochen.

**INV-PL-LEARN-2 (Achsen-Reuse):** `classification` MUSS in
`{semantic, architectural, fachlich, factoring}` liegen (sonst Reject). Diese
Menge ist die Single-Source aus `_PT_berater_classify.md` — sie wird hier NICHT
neu definiert, nur zitiert.

**AK-S1 — zweite Signal-Klasse (inkorrekte Umsetzung / Kurs-Korrektur):** Neben
der "widerlegten Wahrheit" ist auch die **inkorrekte Umsetzung / Kurs-Korrektur**
ein capture-barer PL-Item-Typ. Sie wird ueber `type` markiert:
`type: correction` (Kanon) bzw. die Subtypen `inkorrekte_umsetzung` /
`kurs_korrektur`. Ein solches Item zaehlt als Lern-Signal AUCH ohne `commit_ref`
oder `classification`.

**Validierung (testbare M3-Naht):** `.claude/scripts/pl_learning_schema.py` —
reiner, deterministischer Validator (kein IO, cwd-stabil):

```
validate_learning_fields(item) -> {ok: bool, errors: [str]}
    commit_ref (wenn gesetzt)     -> plausibler Hash-String (7-40 Hex)
    classification (wenn gesetzt) -> in CLASSIFICATION_AXES
    BEIDE optional -> fehlend/None/leer == valide (abwaertskompatibel)

has_learning_signal(item) -> bool
    True gdw. commit_ref ODER classification gesetzt ODER type ∈
    {correction, inkorrekte_umsetzung, kurs_korrektur} (AK-S1)
```

**Scope-Abgrenzung (batch_1 = NUR Schema + Validator):** Das Capture-Routing
(SDF→HiL/BDF→PL), die `commit_ref`-Auto-Population in C7 `statusTransition`, der
Git-Trailer und der Library-Feed sind **batch_2** — siehe die folgenden Abschnitte.

---

### BL-271 batch_2 — AK-S2: Modus-abhaengiges Capture-Routing einer KORREKTUR

**Problem:** Eine **Korrektur** (zweite Signal-Klasse — `type: correction` bzw. die
Subtypen `inkorrekte_umsetzung` / `kurs_korrektur`, AK-S1) darf NICHT bei jedem
Betriebsmodus auf demselben Weg captured werden. Im **menschen-begleiteten**
Modus soll der Mensch entscheiden (lange Abnahme, hoechste Vorsicht); im
**autonomen** Modus muss die Korrektur als Lern-Signal selbsttaetig ins
Parking-Lot fliessen, ohne zu stallen.

**INV-PL-LEARN-3 (Modus-Routing einer Korrektur):** Wohin eine Korrektur captured
wird, haengt vom **Betriebsmodus** ab (gelesen aus den Session-Params, NICHT neu
erfunden):

| Modus | Session-Param-Signal | Capture-Ziel | Mechanik |
|---|---|---|---|
| **Small Dark Factory** (mensch-begleitet) | `dark_factory=false` UND `bdf=false` UND `hil != off` | **HiL-Frage** | `AskUserQuestion` — der Mensch entscheidet ueber die Korrektur (lange Abnahme, vorsichtig). Erst NACH der Mensch-Entscheidung wird ggf. ein PL-Item geschrieben. |
| **Big Dark Factory** (autonom) | `bdf=true` (impliziert `hil=off`) | **Parking-Lot-Append** | Entry-3-Schreibweg (oben). Die Korrektur wird autonom als Lern-Signal captured (`type=correction` + ggf. `commit_ref`/`classification`). KEIN HiL-Dialog. |

**Wie die Session-Params gelesen werden (REUSE — nicht neu erfinden):** GENAU wie
jeder andere Skill seine Modus-Schalter aufloest —
`session_params_resolver.resolve_param(...)` (3-Stufen-Inheritance:
BL-Override > Vault-Default > Framework-Default, `.claude/scripts/session_params_resolver.py`).
Relevante Params (alle existieren bereits in `FRAMEWORK_DEFAULTS`):

```
bdf            = resolve_param("bdf")           # Framework-Default: false
dark_factory   = resolve_param("dark_factory")  # Framework-Default: false
hil            = resolve_param("hil")           # Framework-Default: "off"
```

```
# Routing-Entscheidung (deterministisch, gelesen — kein neuer Schreibweg):
IF bdf == true:                       # Big Dark Factory (autonom, hil=off impliziert)
    → Parking-Lot-Append (Entry-3-Schreibweg oben), type=correction
ELIF hil != "off":                    # Small Dark Factory, mensch-begleitet
    → AskUserQuestion (HiL-Frage) — Mensch entscheidet; PL-Item erst nach Abnahme
ELSE:                                 # hil=off ohne bdf -> autonom-aehnlich
    → Parking-Lot-Append (Entry-3-Schreibweg), type=correction
```

**Begruendung des `bdf`-Vorrangs:** `bdf=true` impliziert `hil=off` (autonomer
Fabrik-Lauf). Steht `bdf` an, ist autonomes PL-Append der korrekte Weg AUCH wenn
ein verirrtes `hil`-Flag gesetzt waere — die Fabrik darf nicht auf eine
Mensch-Frage stallen (vgl. `feedback_machine_not_context` / Anti-Stall). Der
`ELSE`-Zweig (`hil=off` OHNE `bdf`) faellt sicherheitshalber auf autonomes
PL-Append zurueck — niemals auf einen blockierenden HiL-Dialog bei `hil=off`
(konsistent mit `ANTI: KEIN HiL-Dialog wenn GLOBAL_HIL=off` im Entry-3-Vertrag).

> **Naht-Konsistenz:** Das Routing-Signal kommt AUSSCHLIESSLICH aus den
> Session-Params — es gibt KEIN korrektur-spezifisches Modus-Feld am PL-Item und
> KEINEN zweiten Schreibweg. Der `session_params_resolver` ist die Single-Source
> (analog wie `_param` schreibt und alle Skills lesen).

---

### BL-271 batch_2 — AK-S3: Library-Feed (REUSE — der Loop schliesst sich)

Mit den batch_1-Feldern (`classification` + `commit_ref` am PL-Item-Frontmatter)
ist der **Library-Feed jetzt offen**: `_PT_berater_classify` (PT-Extraction
Stage 5) kann die Klassifikations-Achse + den Korrektur-Commit am PL-Item
**DIREKT LESEN**, statt sie teuer aus Roh-Signalen zu rekonstruieren. 486-Empirie
(siehe BL-271-Abschnitt oben): KEIN `[x]`-Item trug ein Label → `classify` musste
die Achse jedes Mal neu ableiten. Mit dem Capture-Punkt-Feld liest `classify` das
Label, statt es zu raten — der Feedback-Loop (Korrektur → Lern-Signal →
Library-Eintrag) schliesst sich.

> **REUSE, KEINE neue Mechanik:** `_PT_berater_classify` nutzt seine 4 Achsen
> (`semantic | architectural | fachlich | factoring`) bereits — das PL-Feld
> `classification` ist EXAKT diese Menge (INV-PL-LEARN-2). batch_2 baut hier NICHTS
> Neues; es dokumentiert nur, dass die batch_1-Felder als Lese-Quelle bereitstehen.

---

### BL-271 batch_2 — AK-S4: Anti-still-fix (REUSE — bereits getragen)

Der Anti-still-fix-Grundsatz ("jede Korrektur hinterlaesst ein Signal, kein
stiller Fix") wird NICHT von BL-271 neu gebaut — er ist bereits getragen durch:

- **Architekt-1-Pflicht** (CLAUDE.md, OBERSTE Standing-Rule): jedes ad-hoc Pflaster
  → SOFORT proper-fix BL (priority=hoch), nie still.
- **Feldjaeger** [[_disciplinary_report]] (BL-324): Lead-Abweichungs-Capture.
- **Crown-2** [[_crown2_orchestrate]] (BL-252): System-Health-Deviation-Observer
  → Anti-Pflaster-BL-Generierung.

**BL-271 ergaenzt** dazu die **ITEM-granulare Capture-Naht** — das Schema
(`commit_ref` + `classification`, batch_1) + das Modus-Routing (AK-S2, batch_2).
KEINE Duplikat-Mechanik: BL-271 dupliziert weder den Feldjaeger noch Crown-2,
sondern verankert das Lern-Signal AM EINZELNEN PL-Item, das die genannten
Observer anschliessend ernten.

---

### BL-271 batch_2 — Getrackter Follow-up: Git-Trailer (NICHT in dieser batch gebaut)

Ein **Git-Trailer** (z.B. `Batch:` / `PL-Item:` als Commit-Message-Trailer, der
einen Commit deterministisch zurueck ans PL-Item bindet) waere die natuerliche
Ergaenzung zur `commit_ref`-Auto-Population. Er wird in dieser batch **NICHT
gebaut** — getrackter Follow-up (so sagt das BL-271-Node selbst), Grund:

> **Kollision mit dem BL-299-Security-Gate (`_stage_orchestrate` Pruefung 5):**
> Pruefung 5 blockt Prozess-Cross-Referenzen in der Commit-Message als
> Leak-Schutz — und die naheliegenden Trailer-Keys verletzen exakt diese Patterns:
> `PL-Item` (→ Parking-Lot-Referenz) und `BL-\d+` (→ Backlog-Item-Referenz) sind
> explizit gelistete Leak-Patterns. Ein naiver `PL-Item: PL-271-003`-Trailer wuerde
> vom Gate (und vom commit-msg-Hook `commit_msg_leak_guard.py`) ZURUECKGEROLLT.
>
> **Design-Hinweis fuer die Spec (NICHT hier umgesetzt):** der Trailer braucht ein
> **leak-neutrales Ref-Format** — entweder ein neutraler, prozess-freier Token
> (z.B. ein opaker Hash/Slug ohne `PL-`/`BL-`-Prefix) ODER eine explizite
> Whitelist-Ausnahme im Pruefung-5-Pattern-Set (`leak_patterns.py`,
> Single-Source). Das `_stage_orchestrate`-Security-Gate wird dabei NICHT
> umgangen — die Whitelist/das neutrale Format muss durch das Gate, nicht an ihm
> vorbei. Diese Abwaegung gehoert in die BL-271-Spec, nicht in den Skill-Doc.

---

### Schreibweg-Logik

```python
# KANON (2026-05-29, Owner-Entscheidung): per-BL Parking-Lot heisst {bl_id}-parking-lot.md
# (z.B. DCSRE-486-parking-lot.md), NICHT das alte unpraefixte parking-lot.md.
# Begruendung: die Pipeline-Mehrheit (A/IDF/SDF-Berater, 32 Dateien/~110 Refs) liest/schreibt
# bereits {bl_id}-parking-lot.md — Entry-3 (/_parking-lot) war der EINZIGE Writer des unpraefixten
# Namens => Split-Brain (Reader fanden die Datei nie). Diese Angleichung loest den Split-Brain.
# {bl_id} = blanke BL-ID (DCSRE-486 / BL-NNN), {bl_slug} = Ordnername (BL-NNN-slug).
def resolve_write_path(args, session_params):
    bl_id = args.get("--bl") or get_current_context().bl_id

    if bl_id:
        bl_slug = resolve_bl_slug(bl_id)  # BL-NNN → BL-NNN-slug
        return f"{vault}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", bl_slug
    elif session_params.GLOBAL_HIL == "on":
        bl_id = ask_user("Welches BL?")
        bl_slug = resolve_bl_slug(bl_id)
        return f"{vault}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", bl_slug
    else:
        return f"{vault}/_parking-lot.md", None  # global fallback (GLOBAL bleibt unpraefixt)

def get_next_pl_id(write_path, bl_id):
    if bl_id:
        existing = count_existing_items(write_path)
        return f"PL-{bl_id}-{existing+1:03d}"
    else:
        existing = count_existing_global_items(write_path)
        return f"PL-GLOBAL-{existing+1:03d}"

def write_pl_item(text, bl_id, type, priority, ak_ref):
    path, bl_slug = resolve_write_path(args, session_params)
    pl_id = get_next_pl_id(path, bl_id)

    item = format_pl_item(pl_id, text, type, bl_id, ak_ref, priority)
    append_to_file(path, item)

    if bl_slug:
        set_manifest_flag(bl_slug, "parking_lot_modified_since_last_idf", True)

    return pl_id, path
```

### Integration BL-199 (IDF Loop-Check)

Nach jedem `/_parking-lot`-Schreibvorgang wird der Marker gesetzt:
- `{bl_slug}/_manifest.md → DF_BATCH_STATE.parking_lot_modified_since_last_idf = true`

Beim naechsten IDF-Lauf erkennt `_IDF_berater_loopCheck` diesen Marker:
- INV-IDF-LOOP-4: `parking_lot_modified=true` → `FULL_LOOP_WITH_REVERSE`
- Phase 3.7 modelSync bekommt Entry-3-Item mit `source=entry3` und `type=correction`
- Reverse-Sync: PL-Korrektur fliesst zurueck ins Model

---

---

## Transkript-Handling (v2.3, PFLICHT)

Wenn ein Transkript (Sprachnotiz, langer Text) als Argument uebergeben wird:

```
SCHRITT 1: RAW-Text IMMER speichern (PFLICHT, KEINE Ausnahme)
  Datei: .claude/pileOfMud/{THEMA}_RAW_{DATUM}.md
  Inhalt: Der KOMPLETTE uebergebene Text, unveraendert
  Grund: Transkripte koennen stundenlang sein — Destillation verliert Details

SCHRITT 2: Destillation erstellen (ZUSAETZLICH zum RAW)
  Datei: .claude/pileOfMud/{THEMA}_Destilliert_{DATUM}.md
  Inhalt: Kern-Ideen extrahiert, strukturiert

SCHRITT 3: PL-Item erstellen mit BEIDEN Referenzen
  - **Transkript (RAW):** .claude/pileOfMud/{THEMA}_RAW_{DATUM}.md
  - **Transkript (Destilliert):** .claude/pileOfMud/{THEMA}_Destilliert_{DATUM}.md

REIHENFOLGE: RAW zuerst (Datenverlust-Schutz), Destillation danach, PL-Item zuletzt.
```

**Warum RAW PFLICHT:** taskDefinition braucht spaeter das Rohmaterial um Findings
zu extrahieren. Destillation kann Details verlieren. RAW ist die Primaerquelle.

---

## Konzept

Der **Parking Lot** ist eine **globale Queue** für **Incidental Findings** - Tasks, die während der Arbeit entdeckt werden, aber NICHT zum aktuellen Zyklus gehören.

### Problem (vor v2.2)

**Beispiel:**
```
User arbeitet an: "User-Login Feature (Cycle 4)"

Während /_SC_observe fällt auf:
  "S3-Integration sollte auf MinIO migriert werden"

Frage: Wohin mit diesem Task?
  ❌ In aktuellen Cycle? → Nein, gehört nicht zu User-Login
  ❌ Vergessen? → Nein, Task geht verloren
  ❌ In neuem Cycle? → Nein, _taskDefinition würde falsche Priorität setzen
```

### Lösung (v2.2)

**Parking Lot Pattern (Uncle Bob):**

> "Separate concerns from current work. Maintain a shared, visible parking lot where any team member can drop incidental findings. Process at natural boundaries (end of cycle, planning sessions)."

```
Während Arbeit:
  Task entdeckt → _parking-lot.md (APPEND)

Bei Cycle-Ende:
  _taskDefinition LIEST _parking-lot.md
  → Verarbeitet Tasks mit Proximity-Priorisierung
  → Markiert als [x] (verarbeitet) oder [~] (verworfen)
```

---

## Index-First Pattern (INV-VAULT-1, INV-VAULT-2, INV-VAULT-9)

Ab BL-151 Phase D: Per-BL-Folder haben eigene `_parking_lot_index.md`. Dieser Skill liest zuerst den Index, dann bei Bedarf Detail-Files.

```
RESOLVE WORKING_DIR = resolve_bl_path(ACTIVE_BL_ID)
  → Lese: {WORKING_DIR}/_parking_lot_index.md   # ~20 LOC Index (INV-VAULT-1)
  → Falls Item selektiert:
      Lese: {WORKING_DIR}/ParkingLot/PL-{n}-{slug}.md  # nur bei Bedarf (INV-VAULT-2)

FALLBACK (kein ACTIVE_BL_ID oder kein Index vorhanden):
  → Lese globales: .claude/analysis/_parking-lot.md  (Legacy, READ-ONLY)
```

**INV-VAULT-Vertraege:**
- INV-VAULT-1: Index-First — Detail-File NIEMALS ohne Index-Check lesen
- INV-VAULT-2: Detail-On-Demand — nur lesen wenn konkret benoetigt
- INV-VAULT-9: Working-Dir-Resolver — `resolve_bl_path(ACTIVE_BL_ID)` bestimmt Ziel-Pfad

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  FILE: _parking-lot.md                                                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  SCHREIBT (APPEND-ONLY):                                                  ║
║    - ALLE Commands können schreiben:                                      ║
║      /_SC_observe, /_SC_modelMaintain, /_SC_qualityGate,                          ║
║      /_SC_hypothese, /_SC_implement, /_SC_ergebnis,                                ║
║      /_knowledge, /_blindspotDetection, etc.                              ║
║                                                                          ║
║  LIEST (READ-ONLY):                                                       ║
║    - /_taskDefinition (bei Cycle-Ende)                                   ║
║      → Verarbeitet [  ] offene Tasks                                     ║
║      → Markiert [x] (aufgenommen) oder [~] (verworfen)                   ║
║                                                                          ║
║  LESE-REIHENFOLGE (INDEX-FIRST, INV-VAULT-1):                            ║
║    1. resolve_bl_path(ACTIVE_BL_ID) → BL-Folder ermitteln               ║
║    2. {BL-Folder}/_parking_lot_index.md lesen (PRIMARY)                  ║
║    3. Detail-File NUR bei konkreter Selektion (INV-VAULT-2)             ║
║    4. Fallback: globales _parking-lot.md (Legacy, READ-ONLY)             ║
║                                                                          ║
║  REGELN:                                                                  ║
║    1. APPEND-ONLY: Commands fügen hinzu, NIEMALS löschen                 ║
║    2. Checkboxes: [ ] offen, [x] verarbeitet, [~] verworfen             ║
║    3. Timestamp + Quelle PFLICHT                                          ║
║    4. TC-Nähe angeben (für Proximity-Priorisierung)                      ║
║    5. Format einhalten (siehe unten)                                      ║
║    6. Index-First IMMER (INV-VAULT-1) — kein direkter Detail-File-Read  ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Format-Template

```markdown
# Parking Lot: Incidental Findings

**Letzte Aktualisierung:** {YYYY-MM-DD HH:MM}

## Legende
- [ ] Offen
- [x] In _taskDefinition aufgenommen (Cycle {N})
- [~] Verworfen (Grund: ...)

---

## {YYYY-MM-DD} - Von /{COMMAND} (Cycle {N})

- [ ] **{Task-Titel}**
  - **Beschreibung:** {1-2 Sätze}
  - **Grund:** {Warum aufgefallen?}
  - **Priorität:** HOCH / MITTEL / NIEDRIG
  - **Komplexitaet:** LOW / MITTEL / HOCH / KRITISCH (Schaetzung)
  - **TC-Nähe:** {Technologie-Concern oder "NONE"}
  - **Quelle:** {Finding F{N} / Model W{n} / Gate Check / ...}
  - **commit_ref:** {Commit-Hash der Korrektur, 7-40 Hex} (optional, BL-271 — nur bei Korrektur-Items)
  - **classification:** {semantic | architectural | fachlich | factoring} (optional, BL-271 — die 4 PT-classify-Achsen)
  - **Transkript (RAW):** .claude/pileOfMud/{THEMA}_RAW_{DATUM}.md (optional — nur wenn Transkript vorhanden)

- [ ] **{Weiterer Task}**
  - ...

---

## {YYYY-MM-DD} - Von /{ANDERES_COMMAND} (Cycle {M})

- [x] **{Verarbeiteter Task}**
  - **Beschreibung:** ...
  - **Status:** Aufgenommen in Cycle {M+1} (Task: {NAME})
  - **Grund:** ...

- [~] **{Verworfener Task}**
  - **Beschreibung:** ...
  - **Status:** Verworfen (Grund: Außerhalb Scope, geringe Priorität)
  - **Grund:** ...
```

---

## Beispiel: Real-World Usage

### Während /_SC_observe (Cycle 4)

**Aktueller Task:** User-Login Feature

**Incidental Finding:**
"Bei Observation von AuthController fällt auf: S3BucketService verwendet veraltete AWS SDK v2, Migration zu v3 empfohlen"

**Action:**
```bash
# Während /_SC_observe läuft:
APPEND zu _parking-lot.md:
```

```markdown
## 2026-02-03 14:35 - Von /_SC_observe (Cycle 4)

- [ ] **AWS SDK v2 → v3 Migration**
  - **Beschreibung:** S3BucketService nutzt veraltete SDK v2, v3 bringt Performance-Verbesserungen
  - **Grund:** Entdeckt während AuthController Observation (Finding F3)
  - **Priorität:** MITTEL
  - **TC-Nähe:** Storage (nicht aktueller Fokus: Authentication)
  - **Quelle:** Finding F3 in OBSERVE4.md, Datei: S3BucketService.cs:15
```

### Während /_SC_qualityGate (Cycle 4)

**Incidental Finding:**
"Gate 2 (Kohäsion) zeigt: Logging-TC hat nur 4 W{n}, evtl. Structured Logging einführen?"

**Action:**
```markdown
## 2026-02-03 15:10 - Von /_SC_qualityGate (Cycle 4)

- [ ] **Structured Logging evaluieren**
  - **Beschreibung:** Logging-TC hat aktuell nur 4 W{n}, Structured Logging (Serilog?) könnte Observability verbessern
  - **Grund:** Quality-Gate Kohäsions-Check ergab geringe W{n}-Dichte
  - **Priorität:** NIEDRIG
  - **TC-Nähe:** Logging
  - **Quelle:** Gate 2 (Kohäsions-Check) in QUALITYGATE4.md
```

### Bei Cycle-Ende: /_taskDefinition (Cycle 5)

**_taskDefinition liest _parking-lot.md:**

```markdown
## Parking Lot Processing (Cycle 5)

**Offene Tasks:** 2

### Task 1: AWS SDK v2 → v3 Migration
- **TC-Nähe:** Storage
- **Aktueller Fokus:** Authentication
- **Proximity-Score:** 0.3 (niedriger, da anderer TC)
- **Entscheidung:** Warten (nicht im Fokus)

### Task 2: Structured Logging evaluieren
- **TC-Nähe:** Logging
- **Aktueller Fokus:** Authentication
- **Proximity-Score:** 0.1 (sehr niedrig)
- **Entscheidung:** Warten (niedrige Priorität)

**Feature-Status User-Login:** 90% Coverage
**Empfehlung:** 1 weiterer Cycle für User-Login, DANN Parking Lot erneut prüfen
```

**_parking-lot.md bleibt unverändert** (Tasks bleiben [ ] offen)

### Nach Feature-Abschluss: /_taskDefinition (Cycle 6)

**User-Login Feature:** ✅ ABGESCHLOSSEN (95% Coverage)

**_taskDefinition verarbeitet Parking Lot:**

```markdown
## 2026-02-05 09:00 - Verarbeitung durch /_taskDefinition (Cycle 6)

- [x] **AWS SDK v2 → v3 Migration**
  - **Beschreibung:** ...
  - **Status:** Aufgenommen als nächstes Feature (Task: S3-Modernisierung)
  - **Grund:** Feature-Abschluss User-Login, Storage-TC ist next
  - **Proximity-Score:** 0.8 (hoch, weil nächster TC)

- [~] **Structured Logging evaluieren**
  - **Beschreibung:** ...
  - **Status:** Verworfen (Grund: Logging funktioniert ausreichend, niedrige Priorität)
  - **Entscheidung:** Prof. Feedback: "Nice-to-have, aber nicht kritisch"
```

---

## Integration in Commands

### /_SC_observe

```python
# Pseudo-Code
if incidental_finding_detected():
    append_to_parking_lot(
        title="AWS SDK v2 → v3 Migration",
        description="...",
        reason="Entdeckt während AuthController Observation",
        priority="MITTEL",
        tc_proximity="Storage",
        source="Finding F3 in OBSERVE4.md"
    )
```

### /_SC_modelMaintain

```python
if w_n_implies_external_task():
    append_to_parking_lot(
        title="Entity-Framework 6.x → 8.x Upgrade",
        description="W42 lässt vermuten, dass EF-Upgrade nötig",
        reason="Model-Maintenance ergab Abhängigkeit",
        priority="HOCH",
        tc_proximity="Data-Access",
        source="W42 Implikation"
    )
```

### /_SC_qualityGate

```python
if gate_reveals_improvement():
    append_to_parking_lot(
        title="Structured Logging evaluieren",
        description="Logging-TC hat nur 4 W{n}",
        reason="Quality-Gate Kohäsions-Check",
        priority="NIEDRIG",
        tc_proximity="Logging",
        source="Gate 2 (Kohäsions-Check)"
    )
```

### /_taskDefinition

```python
# Bei Cycle-Ende:
open_tasks = read_parking_lot()
for task in open_tasks:
    proximity_score = calculate_proximity(task.tc, current_focus_tc)
    if proximity_score > 0.7:
        mark_as_processed(task, reason="Aufgenommen in nächsten Cycle")
        create_new_task(task)
    else:
        # Warten auf besseren Zeitpunkt
        pass
```

---

## Proximity-Priorisierung

Tasks im Parking Lot werden nach **TC-Nähe** priorisiert:

```python
def calculate_proximity(task_tc, current_focus_tc):
    if task_tc == current_focus_tc:
        return 1.0  # Gleicher TC = höchste Priorität
    elif task_tc in get_cross_cutting_tcs():
        return 0.7  # Cross-Cutting (z.B. Logging) = hohe Priorität
    elif task_tc in get_active_tcs():
        return 0.5  # Aktiver TC (nicht Fokus) = mittlere Priorität
    elif task_tc == get_next_tc():
        return 0.8  # Nächster geplanter TC = hohe Priorität
    else:
        return 0.2  # Weit entfernt = niedrige Priorität
```

---

## Vorteile

1. **Task Continuity:** Keine verlorenen Tasks
2. **Fokus:** Aktueller Cycle wird nicht unterbrochen
3. **Visibility:** Alle sehen, was "geparkt" wurde
4. **Proximity-Based:** Intelligente Priorisierung
5. **Simple:** APPEND-ONLY, keine komplexen Regeln

---

## Anti-Patterns

### ❌ Task sofort starten

```
# FALSCH:
if incidental_task_detected():
    start_new_cycle(task)  # Unterbricht aktuellen Cycle!
```

### ❌ Task vergessen

```
# FALSCH:
if incidental_task_detected():
    pass  # Task geht verloren!
```

### ❌ Parking Lot ignorieren

```
# FALSCH bei _taskDefinition:
# Parking Lot wird nicht gelesen
→ Tasks bleiben ewig [ ] offen
```

### ✅ Richtig: Parking Lot Pattern

```
# RICHTIG:
if incidental_task_detected():
    append_to_parking_lot(task)  # Parken
    continue_current_cycle()     # Weitermachen

# Bei Cycle-Ende:
process_parking_lot_with_proximity()
```

---

## Obsidian-Tags

```yaml
tags:
  - type/parking-lot
  - topic/Task-Management
  - topic/Workflow
```

---

## Siehe auch

- [[_taskDefinition]] - Verarbeitet Parking Lot bei Cycle-Ende
- [[_SC_observe]] - Schreibt Incidental Findings
- [[_SC_modelMaintain]] - Schreibt Incidental Findings
- [[_SC_qualityGate]] - Schreibt Incidental Findings
- [[Uncle Bob: Parking Lot Pattern]] - Theoretische Basis

---

## Dual-Kanal-Architektur

Ab Backlog v1.0 existieren ZWEI Kanaele fuer Task-Erfassung. PL bleibt vollstaendig unveraendert (INV-5).

| Eigenschaft | Parking Lot (PL) | Backlog |
|-------------|-------------------|---------|
| **Zweck** | Incidental Findings (ad-hoc) | A-Pipeline Output (strukturiert) |
| **Ausloeser** | Jeder Command waehrend Arbeit | /_backlog nach A-Pipeline Phase 4.2b |
| **Format** | Checkboxen, APPEND-ONLY | YAML-Frontmatter, Schema-konform (12 Pflichtfelder) |
| **Speicherort** | `{VAULT}/_parking-lot.md` | Vault-First: `{VAULT_ROOT}/Backlog/BL-{NNN}-{slug}.md` (BL-151) |
| **Schreibrecht** | Alle Commands (APPEND) | NUR /_backlog (Single Writer) |
| **Index** | Keiner (direkt in Datei) | `_backlog_index.md` (Mirror + Tabelle) |
| **Verarbeitung** | /_taskDefinition bei Cycle-Ende | BDF/SDF liest Vault-Items (v2.0) |
| **Status-Tracking** | `[ ]` / `[x]` / `[~]` | Status-Maschine: DRAFT → READY → PLANNED → IN_PROGRESS → DONE → ARCHIVIERT |

**Abgrenzung:** PL ist fuer spontane Entdeckungen waehrend der Arbeit. Backlog ist fuer systematisch erzeugte Items aus der A-Pipeline (Spec, Model, Gap-Analyse). Beide Kanaele sind unabhaengig — PL-Items werden NICHT automatisch in Backlog ueberfuehrt.

**INV-5 Garantie:** PL-Format (Checkboxen, APPEND-ONLY, Proximity-Priorisierung) bleibt vollstaendig unveraendert. Backlog ist ein ZUSAETZLICHER Kanal, kein Ersatz.
