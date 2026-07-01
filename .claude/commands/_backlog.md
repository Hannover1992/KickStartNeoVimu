---
status: active
version: 1.6
created: 2026-04-01
updated: 2026-06-01
bl_142_phase_5e_migration: true
changelog_inbox: |
  v1.6 - Intake-from-Inbox (2026-06-01, User-Direktive): `/_backlog {NAME}` (Name,
    KEIN Pfad) verschlingt bei nicht-leerer `.claude/pileOfMud/`-Inbox AUTOMATISCH
    den gesamten Briefkasten als Rohmaterial der neuen User-Story (Auto-Detect, kein
    Flag). NAME aus Argument, nicht aus Dateinamen. inbox_source=true → kein Re-Copy
    (Files liegen schon am Zielort den A-Pipeline Phase 0.5 liest), nur Vault-Snapshot.
    Briefkasten existiert nach Redeploy via .claude/pileOfMud/.gitignore (git-ignored
    Inhalt, Ordner bleibt). Inbox leer → altes Verhalten (Feature-Name/A-Output-Persist).
changelog_142: |
  v1.5 - BL-142 Phase 5E (2026-04-26): recommendation → aggregat_score.
    VERTRAG: recommendation gestrichen, aggregat_score eingetragen.
    SCHRITT 4 + Template: Empfehlung-Sektion → Aggregat-Score.
  v1.4 - BL-142 Phase 5E (2026-04-25): reifegrad_hint Override-Mechanismus.
    Schritt 3.5b: Externer Hint kann automatischen Reifegrad ueberschreiben.
    Quellen: CLI (--hint), BL_LIFECYCLE_STATE.reifegrad_hint, A_PIPELINE_STATE.reifegrad_hint.
    Prioritaet: CLI > BL_LIFECYCLE_STATE > A_PIPELINE_STATE > berechnet.
    INV-HINT-1: Hint nur aus ENUM {REIF, SC-REIF, UNREIF}.
    INV-HINT-2: Aufstieg nur mit --hint-force; Rueckstufung erlaubt.
    Audit-Trail: reifegrad_hint_applied im BL-Frontmatter.
type: satellite
chain_position: nach _gap, vor Handschuh-Wechsel (A-Pipeline Phase 4.2b)
depends_on:
  - _gap
  - _spec
  - _model
feeds_into:
  - _BDF_orchestrate
  - _A_orchestrate
related:
  - _parking-lot
  - _backlog_index
---

# CMD: _backlog.md

**Status:** NEU v1.2
**Typ:** Satellite (Single Writer fuer Backlog-Items)
**Zweck:** Strukturiertes Backlog-Item im DCS-Vault erzeugen oder aktualisieren.
A-Pipeline-Output wird als implementierungsfaehiges Paket persistiert.

---

## Aufruf

```
/_backlog {NAME_ODER_DATEIPFAD} [--mode=create|update]
```

- **NAME_ODER_DATEIPFAD** (Pflicht):
  - Wenn Dateipfad (endet auf .md/.txt/.mp3/.wav/.ogg/.m4a/.webm oder enthaelt `/`):
    **AUTO-INTAKE**: Datei wird automatisch als RAW-Transkript erkannt.
    Name wird aus Dateiname abgeleitet (ohne Extension, Underscores→Spaces).
    Erstellt BL-Item mit reifegrad=UNREIF, needs_a_pipeline=true.
    RAW wird nach pileOfMud/ kopiert. BDF routet automatisch durch A-Pipeline.
    Mehrere Dateien: Leerzeichen-getrennt (`/_backlog datei1.md datei2.md`).
  - Wenn KEIN Dateipfad, ABER `.claude/pileOfMud/` nicht-leer (2026-06-01 User-Direktive):
    **INTAKE-FROM-INBOX (Auto-Detect)**: `/_backlog {NAME}` verschlingt ALLES was im
    Briefkasten `.claude/pileOfMud/` liegt (kann hunderte Files sein). NAME kommt aus
    dem Argument (z.B. `DCSRE-1486_CreateSomething`), NICHT aus Dateinamen. Erstellt
    BL-Item (UNREIF, needs_a_pipeline=true) + snapshotted ALLE Pile-Files in den Vault.
    `/_A_orchestrate` Phase 0.5 verdaut danach den GESAMTEN Pile (1 Worker pro File).
    Trigger ist die nicht-leere Inbox — kein Flag noetig.
  - Wenn KEIN Dateipfad UND Inbox leer: Feature-Name-Route (A-Pipeline-Output
    persistieren, identisch mit /_spec, /_model, /_gap).
- **--mode** (Optional):
  - `create` (Default): Neues Backlog-Item, counter+1, neue BL-Nummer
  - `update`: Bestehendes Item aktualisieren (version N+1, KEIN counter-Inkrement)

---

## BL-178 Re-Activation (Index-Split, NEU 2026-05-19)

Per INV-INDEX-SPLIT-4 (BL-178): DONE-Items landen in `_backlog_index_done.md`.
Um ein archiviertes Item wieder zu aktivieren:

```
/_backlog show-archive                 # Zeigt _backlog_index_done.md
/_backlog reopen BL-XXX               # Re-Aktiviert Item: DONE→DRAFT
```

**Ablauf `reopen`:**
1. Suche BL-XXX in `_backlog_index_done.md`
2. Zeile nach `_backlog_index.md` verschieben (status=DRAFT)
3. Detail-File: status=DRAFT + reactivated_at={Datum}
4. Audit-Event REACTIVATION in `audit.jsonl`

**Wichtig:** Nur `/_backlog reopen` darf Archive→Active verschieben (Single-Writer-Prinzip).
Direktes Editieren von `_backlog_index_done.md` verletzt INV-INDEX-SPLIT-3.

---

## VERTRAG (Pflicht-I/O)

```
+===============================================================+
|  COMMAND: /_backlog {NAME} [--mode=create|update]              |
+===============================================================+
|                                                                |
|  LIEST (Input) — AK-06-01: genau 6 Quellen                    |
|    1a. {WORKING_DIR}/_manifest.md  (per-Story, BL-155 AK-1)    |
|       --> A_PIPELINE_STATE: spec_link, model_links, crumbs_ref |
|           aggregat_score, k_aufwand, k_kopplung, k_fragilitaet |
|           modus (FRESH/RESYNC), MODEL_MATURITY                 |
|    1b. {VAULT}/_manifest.md  (global)                          |
|       --> BACKLOG_STATE: backlog_counter, backlog_last_id      |
|    2. .claude/config/vault-routing.json                        |
|       --> detection.rules[pattern="OmniCommand"].vault → "DCS" |
|       --> vaults.DCS.linux_path + backlog.subfolder            |
|    3. {VAULT}/_backlog_index.md                                |
|       --> Fallback-Counter bei Manifest-Inkonsistenz           |
|    4. .claude/specs/{NAME}_Spec.md                             |
|       --> spec_link fuer Backlog-Item (BL-008)                 |
|    5. .claude/models/{NAME}_Model.md                           |
|       --> model_links fuer Backlog-Item                        |
|    6. .claude/crumbs/{NAME}_crumbs.md (OPTIONAL, INV-8)       |
|       --> crumbs_ref — null wenn nicht vorhanden               |
|    7. {VAULT}/.../4_K-Score/{NAME}-K-SCORE.md (OPTIONAL, BL-142|
|       RF-A6) Frontmatter.ak_details + Body-Tabelle             |
|       --> ak_anchors, srs_per_ak, k_score_per_ak (Per-AK)      |
|       --> Leer/null wenn K-SCORE.md fehlt (additiv, INV-8)     |
|                                                                |
|  SCHREIBT (Output) — AK-06-02: genau 3 Ziele, AK-05-01 Reihenf|
|    1. {VAULT_BASE}/BL-{NNN:03d}-{slug}.md                     |
|       --> Vault-Datei mit Frontmatter (13 Pflicht + 3 Optional)|
|       --> ZUERST geschrieben (Phase 1, idempotent — AK-05-02)  |
|    2. {VAULT}/_backlog_index.md                                |
|       --> APPEND: neue Zeile (create)                          |
|       --> UPDATE: bestehende Zeile (update)                    |
|       --> ZWEITES geschrieben (Phase 2)                        |
|    3a. {VAULT}/_manifest.md  (global)                          |
|       --> BACKLOG_STATE: counter+1 (nur create), last_id       |
|    3b. {WORKING_DIR}/_manifest.md  (per-Story, BL-155 AK-1)    |
|       --> A_PIPELINE_STATE: backlog_item_created=true,         |
|           backlog_item_id, backlog_item_status="DRAFT"         |
|       --> LETZTES geschrieben (Phase 3 — AK-05-03 Dual-Counter)|
|                                                                |
|  SCHREIBT NICHT — AK-06-03 (INV-5):                            |
|    - _parking-lot.md (W16 unveraendert, SDF-exklusiv, INV-5)  |
|                                                                |
+===============================================================+
```

---

## Invarianten

- **INV-1:** /_backlog wird VOR Handschuh-Wechsel in A-Pipeline aufgerufen
- **INV-3:** backlog_counter ist APPEND-ONLY (nur +1 bei create, nie zuruecksetzen)
- **INV-5:** _parking-lot.md bleibt vollstaendig unveraendert
- **INV-6:** Vault-Pfad wird aus vault-routing.json gelesen, nie hartcodiert
- **INV-8:** crumbs_ref darf null sein (kein Fehler bei fehlendem _gap-Output)
- **INV-COUNTER-LOCK-1:** counter-Inkrement IMMER atomar via `backlog_counter_lock.allocate_next_bl_id` — nie nackt read-then-write. Verhindert Duplikat-BL-Nummern und lost-increments bei nebenlaeufigem Filing mehrerer Lanes (factory_lock backlog_counter-scope).
- **INV-COUNTER-LOCK-2 (BL-475):** Die neue BL-Nummer ist IMMER `max(stored_counter, scan_max_existing_bl(vault_root)) + 1` unter dem Lock — faellt NIE hinter die real existierende Max-BL-Nummer (heilt korrupte/zurueckgefallene Counter, verhindert Kollision mit existierendem BL). Quellen-Scan: Backlog/-Ordner + _backlog_index.md + _backlog_index_done.md.

---

## Pseudocode

```
FUNCTION _backlog(NAME_ODER_DATEIPFAD, mode="create"):

  # ============================================================
  # SCHRITT 0: AUTO-INTAKE-ERKENNUNG (RAW-Datei droppen)
  # ============================================================
  # AK-03-01: Auto-Intake-Erkennung
  # Argument wird als Dateipfad erkannt wenn: (a) "/" enthalten ODER (b) Extension
  # in RAW_EXTENSIONS. Mehrere Dateien leerzeichen-getrennt moeglich.
  RAW_EXTENSIONS = [".md", ".txt", ".mp3", ".wav", ".ogg", ".m4a", ".webm"]
  args = NAME_ODER_DATEIPFAD.split(" ")  # Mehrere Dateien moeglich

  # Erkennung: Ist das erste Argument ein Dateipfad?
  is_file = (
    "/" IN args[0] OR                           # Pfad mit Verzeichnis
    ANY(args[0].endswith(ext) FOR ext IN RAW_EXTENSIONS)  # Datei-Extension
  )

  IF is_file:
    # ═══ AUTO-INTAKE MODUS ═══
    raw_files = [arg FOR arg IN args IF EXISTS(arg)]
    IF raw_files.length == 0:
      LOGGE: "FEHLER: Keine der angegebenen Dateien gefunden: {args}"
      RETURN

    # AK-03-04: Name-Ableitung aus Dateiname
    first_basename = BASENAME(raw_files[0])
    # Entferne Extension
    NAME = first_basename
      .replace(".md", "").replace(".txt", "")
      .replace(".mp3", "").replace(".wav", "")
      .replace(".ogg", "").replace(".m4a", "").replace(".webm", "")
    # Entferne RAW-Prefixe und Datum-Muster (YYYY-MM-DD, YYYYMMDD)
    NAME = NAME
      .replace("_RAW_", "_").replace("-RAW-", "_")
      .regex_replace(r"\d{4}-\d{2}-\d{2}", "")
      .regex_replace(r"\d{8}", "")
      .strip("_").strip("-")
      .replace(" ", "_")
    # Wenn Name zu generisch: Datum-Suffix anhaengen
    IF NAME.lower() IN ["transkript", "audio", "notiz", "raw", "sprachnotiz", ""]:
      NAME = (NAME + "_" + HEUTE) IF NAME != "" ELSE ("intake_" + HEUTE)

    Logge: "[AUTO-INTAKE] {raw_files.length} RAW-Dateien erkannt → Name: {NAME}"
    mode = "intake"
    inbox_source = false  # Files kommen aus Argument-Pfaden, muessen nach pileOfMud kopiert werden
    # Weiter mit SCHRITT 1 (intake-Modus aktiv, raw_files gesetzt)
  ELSE:
    # ═══ INTAKE-FROM-INBOX (NEU 2026-06-01, User-Direktive Auto-Detect) ═══
    # `/_backlog {NAME}` (Name, KEIN Pfad) + nicht-leere Inbox .claude/pileOfMud/
    # → verschlinge ALLES was drin liegt als Rohmaterial dieser neuen User-Story.
    # Trigger: Inbox nicht-leer (Auto-Detect, kein Flag). NAME aus Argument.
    # Vorrang vor der alten Feature-Name-Route (A-Output-Persist) — der Briefkasten
    # ist das staerkere Signal "frisches Rohmaterial liegt vor".
    # DEFERRED (User-Call): Disambiguierung welche Files zu welcher Story gehoeren
    # (Pile-Aufraeumen / "echter Misthaufen") — separates Problem, hier NICHT geloest.
    pile_files = Glob(".claude/pileOfMud/*")
    pile_files = [f FOR f IN pile_files
                  IF ANY(f.endswith(ext) FOR ext IN RAW_EXTENSIONS)
                  AND BASENAME(f) NOT IN [".gitignore", ".gitkeep"]]
    IF pile_files.length > 0:
      NAME = NAME_ODER_DATEIPFAD          # Name aus User-Argument (Pflicht, z.B. "DCSRE-1486_CreateSomething")
      raw_files = pile_files              # ALLE Inbox-Files = Rohmaterial
      mode = "intake"
      inbox_source = true                 # Files liegen SCHON in pileOfMud → KEIN Re-Copy
      Logge: "[AUTO-INTAKE/INBOX] {pile_files.length} Files in .claude/pileOfMud/ → BL-Item '{NAME}' (verschlingt gesamten Pile)"
    ELSE:
      # Inbox leer → altes Verhalten (Feature-Name-Route, A-Output-Persist)
      NAME = NAME_ODER_DATEIPFAD
      raw_files = null
      inbox_source = false
      Logge: "[BACKLOG] Inbox .claude/pileOfMud/ leer → Feature-Name-Route (A-Output-Persist). Falls du Rohmaterial verschlingen wolltest: Files in .claude/pileOfMud/ legen und /_backlog {NAME} wiederholen."

  # ============================================================
  # SCHRITT 1: GUARD — Vault-Pfad und Vorbedingungen
  # ============================================================

  LIES vault-routing.json
  # BL-210 M2 Fix 2026-05-24: Projekt-generisch statt hardcoded "OmniCommand".
  # Vorher: pattern = WHERE pattern == "OmniCommand" — funktionierte nur fuer OmniCommand-Projekt.
  # Fix: Projekt-Discovery via current_context.py (liefert {branch, bl_id, vault_root, project_name}).
  # Fallback: default_project aus vault-routing.json oder erste Rule die zum cwd passt.
  worker_ctx = subprocess(.claude/scripts/current_context.py --format=json).stdout
  project_name = json.loads(worker_ctx).project_name ?? "OmniCommand"
  pattern = detection.rules WHERE pattern == project_name
  IF pattern == null:
    # Fallback 1: pattern_default aus routing.json
    pattern = detection.rules WHERE pattern == detection.default_pattern
  IF pattern == null:
    # Fallback 2: erste Rule die cwd matched
    pattern = detection.rules.first(WHERE cwd_matches(cwd))

  # AK-07-02: PATTERN_NOT_FOUND → HiL-Fehler wenn keine Rule passt
  IF pattern == null:
    SCHREIBE _manifest.md → BACKLOG_STATE.backlog_error = "PATTERN_NOT_FOUND"
    LOGGE: "HiL-FEHLER: Kein Pattern in vault-routing.json fuer project_name='{project_name}' — manuelle Korrektur noetig (M2 Fix)"
    RETURN  # HiL-Break

  vault_name = pattern.vault  # "DCS"
  vault_base = vaults[vault_name].linux_path  # z.B. resolved Vault-Pfad
  subfolder = pattern.backlog.subfolder  # "OmniCommand/Backlog"
  VAULT_PATH = vault_base + "/" + subfolder
  # Ergebnis: {VAULT_ROOT}/Backlog/   (z.B. C:/Users/.../Documents/OmniCommand/Backlog/ bei OmniCommand-Projekt)

  # AK-07-01: VAULT_UNREACHABLE → non-blocking, Pipeline faehrt fort
  IF VAULT_PATH nicht erreichbar:
    SCHREIBE _manifest.md → BACKLOG_STATE.backlog_error = "VAULT_UNREACHABLE"
    LOGGE: "FEHLER: Vault-Pfad {VAULT_PATH} nicht erreichbar"
    RETURN (non-blocking — Pipeline faehrt fort)

  mkdir -p VAULT_PATH  # Ordner erstellen falls nicht vorhanden

  LIES _manifest.md → A_PIPELINE_STATE, BACKLOG_STATE

  # ============================================================
  # SCHRITT 2: BL-Nummer berechnen
  # ============================================================

  IF mode == "create":
    # AK-01-02: BL-Nummer monoton steigend (counter+1, nie wiederverwendet, INV-3)
    # INV-COUNTER-LOCK-1 + INV-COUNTER-LOCK-2 (BL-475): counter-Inkrement IMMER atomar
    # via allocate_next_bl_id — nie nackt read-then-write. floor_provider stellt sicher
    # dass neue Nr >= max(stored, scan_max_existing_bl) + 1 (Self-Heal-Floor).
    import backlog_counter_lock
    neue_nr = backlog_counter_lock.allocate_next_bl_id(
        vault_root,
        read_counter=lambda: BACKLOG_STATE.backlog_counter,
        write_counter=lambda n: write_manifest(BACKLOG_STATE.backlog_counter = n),
        floor_provider=lambda: backlog_counter_lock.scan_max_existing_bl(vault_root))
    bl_id = FORMAT("BL-%03d", neue_nr)  # z.B. "BL-001"
    slug = kebab_case(NAME)  # z.B. "omnicommand-backlog"
    dateiname = bl_id + "-" + slug + ".md"

    # AK-01-03: EXISTS-Check bei Partial-Write-Recovery (idempotent)
    IF DATEI EXISTIERT(VAULT_PATH + "/" + dateiname):
      LOGGE: "WARNING: {dateiname} existiert bereits — Partial-Write-Recovery"
      # Datei wird ueberschrieben (idempotent, kein Doppel-Item)

  ELIF mode == "intake":
    # ═══ INTAKE-MODUS (RAW-Audio/Transkript → BL-Item + pileOfMud) ═══
    # Erstellt BL-Item mit reifegrad=UNREIF, kopiert RAW nach pileOfMud.
    # BDF erkennt needs_a_pipeline=true und routet durch A-Pipeline (Fresh).
    #
    # FLOW: User legt RAW-Datei → /_backlog intake → BL-Item UNREIF →
    #       BDF SCANNING → A-Pipeline (Fresh) → Model+Spec+Gap → SDF → SC/I
    #
    # Mehrere Dateien: --raw=datei1.md,datei2.md (kommasepariert)
    # ODER (2026-06-01): inbox_source=true → Files liegen SCHON in .claude/pileOfMud/

    pileOfMud_dir = ".claude/pileOfMud/"
    mkdir -p pileOfMud_dir

    IF inbox_source == true:
      # ═══ INBOX-INTAKE: Files SCHON im Briefkasten (kein Re-Copy) ═══
      # SCHRITT 0 hat raw_files = pile_files (alle .claude/pileOfMud/*-RAW-Files) gesetzt.
      # Sie sind bereits am Zielort, den A-Pipeline Phase 0.5 liest → nur Snapshot folgt.
      copied_files = raw_files
      Logge: "[INTAKE/INBOX] {copied_files.length} Files bereits in pileOfMud — kein Re-Copy, Vault-Snapshot folgt"
    ELSE:
      # ═══ FILE-PATH-INTAKE: gedroppte Pfade nach pileOfMud kopieren ═══
      # raw_files aus SCHRITT 0 (Argument-Pfade); --raw bleibt Legacy-CLI-Alias.
      IF raw_files == null OR raw_files.length == 0:
        raw_paths = CLI_PARAM("--raw")
        IF raw_paths == null OR raw_paths == "":
          LOGGE: "FEHLER: keine RAW-Dateien (weder Argument-Pfade, Inbox, noch --raw)"
          RETURN
        raw_files = raw_paths.split(",")

      # AK-03-02: RAW-Dateien nach pileOfMud kopieren
      # Ziel: .claude/pileOfMud/{NAME}_RAW_{HEUTE}_{basename}
      # Nicht existierende Dateien werden mit WARNING uebersprungen.
      copied_files = []
      FUER raw_file IN raw_files:
        raw_file = raw_file.strip()
        IF NOT EXISTS(raw_file):
          LOGGE: "WARNING: RAW-Datei nicht gefunden: {raw_file} — uebersprungen"
          CONTINUE
        # Ziel-Name: {NAME}_RAW_{datum}_{basename}.md
        basename = BASENAME(raw_file).replace(" ", "_")
        ziel = pileOfMud_dir + NAME + "_RAW_" + HEUTE + "_" + basename
        KOPIERE raw_file → ziel
        copied_files.append(ziel)
        LOGGE: "[INTAKE] RAW kopiert: {raw_file} → {ziel}"

    IF copied_files.length == 0:
      LOGGE: "FEHLER: Keine RAW-Dateien gefunden — kein BL-Item erstellt"
      RETURN

    # BL-Nummer berechnen (gleich wie create)
    # INV-COUNTER-LOCK-1 + INV-COUNTER-LOCK-2 (BL-475): counter-Inkrement IMMER atomar
    # via allocate_next_bl_id — nie nackt read-then-write. floor_provider stellt sicher
    # dass neue Nr >= max(stored, scan_max_existing_bl) + 1 (Self-Heal-Floor).
    import backlog_counter_lock
    neue_nr = backlog_counter_lock.allocate_next_bl_id(
        vault_root,
        read_counter=lambda: BACKLOG_STATE.backlog_counter,
        write_counter=lambda n: write_manifest(BACKLOG_STATE.backlog_counter = n),
        floor_provider=lambda: backlog_counter_lock.scan_max_existing_bl(vault_root))
    bl_id = FORMAT("BL-%03d", neue_nr)
    slug = kebab_case(NAME)
    dateiname = bl_id + "-" + slug + ".md"

    # Vault-Datei schreiben (UNREIF + needs_a_pipeline)
    # AK-03-03: Alle 13 Pflichtfelder + 3 Optionalfelder (BacklogItem-Schema v1.0)
    # BY DESIGN (AK-06-02, BL-025): Neue Items aus Intake haben typischerweise
    # niedrige Metriken (modellreife 1-2, hohe fragilitaet). Dies ist kein Fehler
    # sondern Design-Entscheidung — Items reifen durch SC-Zyklen.
    slug = kebab_case(NAME)
    vault_knoten_id = bl_id + "-" + slug  # Obsidian-Node-ID
    SCHREIBE VAULT_PATH + "/" + dateiname:
      ---
      id: {bl_id}
      title: {NAME}
      version: 1
      created: {HEUTE}
      updated: {HEUTE}
      spec_link: null
      model_links: []
      vault_knoten_id: {vault_knoten_id}
      status: DRAFT
      komplexitaet: null
      modellreife: null
      fragilitaet: null
      reifegrad: UNREIF
      crumbs_ref: null
      ankerknoten: []
      dependencies: []
      needs_a_pipeline: true
      raw_source: {copied_files}
      ---

      # {NAME}

      ## Quelle
      RAW-Intake: {copied_files.length} Dateien in pileOfMud/

      ## Status
      UNREIF — wartet auf A-Pipeline (/_A_orchestrate fresh).
      BDF erkennt needs_a_pipeline=true und startet automatisch.

    # Index + Manifest aktualisieren
    APPEND _backlog_index.md:
      | {bl_id} | {NAME} | DRAFT | {VAULT_PATH}/{dateiname} | {HEUTE} | {HEUTE} | null | UNREIF |

    SCHREIBE _manifest.md → BACKLOG_STATE:
      backlog_counter: {neue_nr}
      backlog_last_id: {bl_id}
      backlog_last_update: {HEUTE}

    LOGGE: "[INTAKE] {bl_id} erstellt: {NAME} (UNREIF, {copied_files.length} RAW-Dateien, needs_a_pipeline=true)"

    # ============================================================
    # ## AK-2 Snapshot-Block BEGIN
    # BL-160 AK-2 — entferne diesen Block fuer Rollback (PL-AK2-1..3)
    # PRIMAER: vault-routing.json (sources_pileOfMud_snapshot, INV-6)
    # FALLBACK: Hardcoded "Sources/_pileOfMud_snapshot" wenn Routing nicht gelesen
    # ============================================================
    # VERTRAG:
    #   LIEST:  copied_files (aus PL-AK2-1 Glob), vault-routing.json
    #   SCHREIBT: VAULT_PATH/{bl_id}-{slug}/Sources/_pileOfMud_snapshot/{basename}
    #             mit source_provenance + provenance_chain (INV-PROVENANCE-1)
    #   SCHREIBT NICHT: .claude/pileOfMud/** (W27 Decision A, Read-Only-Original)
    #                   used_in (W25 Decision A, AK-6-Writer)

    # PL-AK2-1: Silent-Skip wenn keine pileOfMud-Dateien (PT-CMD-023)
    IF copied_files.length == 0:
      LOGGE: "[SNAPSHOT] kein pileOfMud-Input — Snapshot-Schritt uebersprungen"
      RETURN

    # Vault-First-Resolution des Snapshot-Ordners (PT-CMD-006)
    snapshot_subfolder = LIES vault_routing.backlog.subfolder_structure.folders
                         WHERE typ == "sources_pileOfMud_snapshot"
                         → .ordner  # "Sources/_pileOfMud_snapshot"
    IF snapshot_subfolder == null:
      snapshot_subfolder = "Sources/_pileOfMud_snapshot"  # FALLBACK
    snapshot_dir = VAULT_PATH + "/" + bl_id + "-" + slug + "/" + snapshot_subfolder + "/"
    mkdir -p snapshot_dir

    FUER original_path IN copied_files:
      basename = BASENAME(original_path)
      ziel = snapshot_dir + basename

      # PL-AK2-2 SHA-256 Dual-Pfad (BL-111-feature_override)
      neuer_hash = bash("sha256sum '{original_path}' | cut -d' ' -f1")
                   ODER powershell("(Get-FileHash '{original_path}' -Algorithm SHA256).Hash.ToLower()")

      # PT-CMD-007 Idempotenz-Guard via SHA-256
      IF DATEI_EXISTIERT(ziel):
        alter_hash = LIES Frontmatter(ziel).source_provenance.original_hash
        IF alter_hash == neuer_hash:
          LOGGE: "[SNAPSHOT] Snapshot bereits aktuell: {basename} (Hash unveraendert)"
          CONTINUE  # Silent-Skip (PT-CMD-007)

      # PL-AK2-2 Kopier-Logik (Original unveraendert — W27 Decision A)
      KOPIERE original_path → ziel

      # PL-AK2-3 INV-PROVENANCE-1 Frontmatter (Dual-Layer)
      original_fm = LIES Frontmatter(original_path)  # Best-Effort, leer wenn nicht vorhanden
      SCHREIBE Frontmatter(ziel):
        source_provenance:
          source_kind: original_fm.source_kind ?? "voice-note"
          source_url: original_fm.source_url ?? null   # W26: null bei voice-note valid
          original_hash: neuer_hash                    # 64-Hex-String, deterministisch
          snapshot_date: HEUTE
          derived_from: original_path
          used_in: []                                  # W25: AK-6 befuellt spaeter
          provenance_chain:
            - layer: 1
              type: "legacy_pre_BL-160"
              note: "Original pileOfMud — keine provenance_chain vorhanden vor BL-160"
              source: original_path
            - layer: 2
              type: "snapshot"
              note: "Vault-Snapshot via BL-160 AK-2 — automatisch erstellt"
              snapshot_path: ziel
              snapshot_date: HEUTE
              snapshot_hash: neuer_hash
      LOGGE: "[SNAPSHOT] Snapshot erstellt: {ziel} (hash={neuer_hash[:8]}...)"
    # ## AK-2 Snapshot-Block END

    RETURN

  ELIF mode == "update":
    # AK-02-02: Fallback auf create bei fehlendem BL-Item
    bl_id = BACKLOG_STATE.backlog_last_id  # z.B. "BL-001"
    IF bl_id == "NONE" OR bl_id == null:
      LOGGE: "WARNING: RESYNC ohne bestehendes BL-Item — Fallback auf create"
      RETURN _backlog(NAME, mode="create")

    # Bestehende Datei finden via Index oder Manifest
    LIES _backlog_index.md → Zeile mit bl_id → vault_pfad
    IF Datei nicht gefunden:
      LOGGE: "WARNING: BL-Item {bl_id} nicht im Vault — Fallback auf create"
      RETURN _backlog(NAME, mode="create")

    dateiname = BASENAME(vault_pfad)
    # AK-02-01: Version inkrementiert, Counter stabil (INV-3: counter NICHT aendern)
    bestehende_version = LIES Frontmatter(vault_pfad).version
    neue_version = bestehende_version + 1
    # AK-02-03: created-Datum aus bestehender Datei beibehalten
    bestehende_created = LIES Frontmatter(vault_pfad).created
    # Reifungs-Tracking (AK-02-02/AK-02-03, BL-025): alter Reifegrad fuer Vergleich
    alter_reifegrad = LIES Frontmatter(vault_pfad).reifegrad  # null bei create-Pfad

  # ============================================================
  # SCHRITT 3: Metriken normieren (K-SCORE → 1-5 Skala)
  # ============================================================

  k_aufwand = A_PIPELINE_STATE.k_aufwand         # 0-100
  k_kopplung = A_PIPELINE_STATE.k_kopplung        # 0-100
  k_fragilitaet = A_PIPELINE_STATE.k_fragilitaet  # 0-100
  model_maturity = A_PIPELINE_STATE.MODEL_MATURITY # 0-100%

  # Normierung k_aufwand / k_fragilitaet (Rohwert 0-100 → 1-5)
  # KANONISCH: _backlog.md-Tabelle (engere Baender, konservativer)
  # OQ-01 [PENDING HiL-Gate T1]: BacklogItem-Schema 5.1 hat breitere Baender
  #   (41-60=3, 61-80=4, 81-100=5). Spec ADR-01 empfiehlt DIESE Tabelle.
  #   Rohwert 58 → hier: 4 (Hoch), Schema: 3 (Mittel).
  #   Nach HiL-Entscheidung: Verlierertabelle synchronisieren.
  FUNCTION normiere(wert):
    IF wert == null: RETURN null  # INV-8: fehlende Felder → null propagieren
    IF wert <= 20: RETURN 1
    IF wert <= 40: RETURN 2
    IF wert <= 55: RETURN 3
    IF wert <= 65: RETURN 4
    RETURN 5

  # Modellreife (MODEL_MATURITY Prozent → 1-5)
  # KONSISTENT in _backlog.md UND BacklogItem-Schema 5.2 — keine Diskrepanz.
  FUNCTION normiere_reife(prozent):
    IF prozent == null: RETURN null  # INV-8: fehlende Felder → null propagieren
    IF prozent <= 20: RETURN 1
    IF prozent <= 40: RETURN 2
    IF prozent <= 60: RETURN 3
    IF prozent <= 80: RETURN 4
    RETURN 5

  komplexitaet = normiere(k_aufwand)
  fragilitaet = normiere(k_fragilitaet)
  modellreife = normiere_reife(model_maturity)

  # ============================================================
  # SCHRITT 3.5: Reifegrad-Inferenz (Backlog_Reifegradrouting v1.0)
  # ============================================================
  # Input: modellreife (1-5), fragilitaet (1-5), komplexitaet (1-5)
  # Output: reifegrad ENUM {REIF, SC-REIF, UNREIF}
  # Schwellenwerte: v1.0-Vorschlag, kalibrierbar per SC-Zyklus (INV-7)

  # AK-04-01: Schwellenwerte korrekt implementiert (konjunktiv/disjunktiv)
  FUNCTION berechne_reifegrad(modellreife, fragilitaet, komplexitaet):
    # AK-04-02: Default UNREIF bei fehlenden Feldern (INV-8)
    IF modellreife == null OR fragilitaet == null OR komplexitaet == null:
      LOGGE: "[REIFEGRAD] Fehlende Metrik(en) — Default UNREIF (INV-8)"
      RETURN "UNREIF"
    # REIF: modellreife>=4 AND fragilitaet<=2 AND komplexitaet<=3 (konjunktiv)
    IF (modellreife >= 4) AND (fragilitaet <= 2) AND (komplexitaet <= 3):
      RETURN "REIF"
    # UNREIF: modellreife<=1 OR (modellreife==2 AND fragilitaet>=4) (disjunktiv)
    ELIF (modellreife <= 1) OR (modellreife == 2 AND fragilitaet >= 4):
      RETURN "UNREIF"
    # REIF: ELSE — buildable middle ist Default BAU, NICHT SC.
    # [BL-246 / Rolled-Back-Big-Factory-Fix 2026-06-03] SC-REIF war hier faelschlich der ELSE-Default —
    # Residue des ZURUECKGEBAUTEN Big-Factory-"Order-Decision"-Designs (BLs gingen erst zur Big Factory/SC,
    # die mit mehr Info die Aufgaben-Reihenfolge entscheiden sollte; das Design wurde zurueckgebaut, aber der
    # SC-REIF-Default blieb als tote Annahme haengen). SC (Scientific Cycle) ist die EPISTEMISCHE AUSNAHME,
    # nicht der Fallback. Der buildable-middle-Bereich (REIF-Konjunktion nicht-streng erfuellt, aber NICHT
    # UNREIF) gehoert in den IDF->SDF-Bau = REIF. SC-REIF bleibt erreichbar via explizitem reifegrad_hint
    # (SCHRITT 3.5b), NICHT als Auto-Default. Analog BL-239: SC nur bei genuiner Epistemik, nicht per Default.
    ELSE:
      RETURN "REIF"

  reifegrad = berechne_reifegrad(modellreife, fragilitaet, komplexitaet)
  Logge: "[REIFEGRAD] {reifegrad} (modellreife={modellreife}, fragilitaet={fragilitaet}, komplexitaet={komplexitaet})"

  # ============================================================
  # SCHRITT 3.5b: reifegrad_hint Override (BL-142 Phase 5E Migration)
  # ============================================================
  # Externer Hint kann automatischen Reifegrad ueberschreiben.
  # Quellen: BDF (Spec-AK-Lueckenscan), IDF (post Decomposition), User (--hint).
  # Manifest-Pfad: A_PIPELINE_STATE.reifegrad_hint ODER
  #                BL_LIFECYCLE_STATE.reifegrad_hint (BDF-getriggert).
  # Aufruf-Override: --hint=UNREIF|SC-REIF|REIF (CLI)
  # Prioritaet: CLI > BL_LIFECYCLE_STATE > A_PIPELINE_STATE > berechnet
  # INV-HINT-1: Hint nur aus erlaubter ENUM {REIF, SC-REIF, UNREIF}
  # INV-HINT-2: Hint < berechnet erlaubt (Rueckstufung), Hint > berechnet
  #             nur mit explizitem User-Override (--hint-force)
  reifegrad_hint = (
    CLI_PARAM("--hint")
    OR LIES Manifest.BL_LIFECYCLE_STATE.reifegrad_hint
    OR LIES Manifest.A_PIPELINE_STATE.reifegrad_hint
    OR null
  )
  IF reifegrad_hint != null:
    IF reifegrad_hint NOT IN ["REIF", "SC-REIF", "UNREIF"]:
      Logge: "[REIFEGRAD-HINT] WARN: Ungueltiger Hint '{reifegrad_hint}' — ignoriert (INV-HINT-1)"
    ELIF REIFEGRAD_RANKING[reifegrad_hint] > REIFEGRAD_RANKING[reifegrad]:
      hint_force = CLI_PARAM("--hint-force") == true
      IF hint_force:
        Logge: "[REIFEGRAD-HINT] FORCE-AUFSTIEG: berechnet={reifegrad} → hint={reifegrad_hint} (--hint-force)"
        reifegrad = reifegrad_hint
      ELSE:
        Logge: "[REIFEGRAD-HINT] HINT-AUFSTIEG OHNE FORCE — ignoriert (INV-HINT-2): berechnet={reifegrad}, hint={reifegrad_hint}"
    ELSE:
      Logge: "[REIFEGRAD-HINT] OVERRIDE: berechnet={reifegrad} → hint={reifegrad_hint} (Rueckstufung erlaubt)"
      reifegrad = reifegrad_hint
    # Hint im BL-Frontmatter persistieren (Audit-Trail)
    reifegrad_hint_applied = reifegrad_hint
  ELSE:
    reifegrad_hint_applied = null

  # Reifungs-Tracking (AK-02-02/AK-02-03, BL-025)
  REIFEGRAD_RANKING = {UNREIF: 1, SC-REIF: 2, REIF: 3}
  IF alter_reifegrad != null AND alter_reifegrad != reifegrad:
    IF REIFEGRAD_RANKING[reifegrad] > REIFEGRAD_RANKING[alter_reifegrad]:
      Logge: "[REIFEGRAD-AUFSTIEG] BL-{bl_id}: {alter_reifegrad} → {reifegrad}"
    ELSE:
      Logge: "[REIFEGRAD-RUECKSTUFUNG] BL-{bl_id}: {alter_reifegrad} → {reifegrad}"

  # ============================================================
  # SCHRITT 4: Vault-Datei schreiben (ZUERST — idempotent)
  # AK-01-01: Vault-Datei mit 13 Pflicht + 3 Optionalfeldern = 16 Felder
  # AK-05-01: Phase 1 der 3-Phasen-Persistenz (Vault → Index → Manifest)
  # ============================================================

  spec_link = "{WORKING_DIR}/.claude/specs/" + NAME + "_Spec.md"  # BL-008: kanonischer Pfad
  model_link = "{WORKING_DIR}/.claude/models/" + NAME + "_Model.md"

  # crumbs_ref null-tolerant (INV-8, AK-07-03)
  # KEIN Fehler bei fehlender Datei — null ist valider Wert
  crumbs_pfad = "{WORKING_DIR}/.claude/crumbs/" + NAME + "_crumbs.md"
  IF DATEI EXISTIERT(crumbs_pfad):
    crumbs_ref = crumbs_pfad
  ELSE:
    crumbs_ref = null
    LOGGE: "[INV-8] crumbs_ref = null (Datei nicht vorhanden: {crumbs_pfad})"

  vault_knoten_id = bl_id + "-" + slug  # Obsidian-Node-ID

  heute = DATE_ISO8601()  # z.B. "2026-04-01"

  # BL-142 RF-A6: Per-AK Anker aus K-SCORE.md Frontmatter (ak_details) lesen
  # Additiv — fehlend = leere Listen/Maps, kein Fail
  k_score_path = "{VAULT}/Backlog/{BL_SLUG}/4_K-Score/{NAME}-K-SCORE.md"   # Vault-First (BL-151 Migration abgeschlossen 2026-05-06)
  IF NOT exists(k_score_path):
    k_score_path = ".claude/analysis/synthese/{NAME}-K-SCORE.md"  # Legacy Read-Fallback
  ak_anchors    = []
  srs_per_ak    = {}
  k_score_per_ak = {}
  IF exists(k_score_path):
    k_data = LIES Frontmatter(k_score_path)
    IF k_data.ak_details:
      FUER ak_id, ak_data IN k_data.ak_details:
        ak_anchors.append(ak_id)
        srs_per_ak[ak_id] = ak_data.srs_pro_ak
      # k_score_per_ak: Body-Tabelle "Pro-AK Detail" parsen, Spalte K-Score
      k_score_per_ak = parse_k_score_body_table(k_score_path)
  ELSE:
    LOGGE: "[INV-8] ak_anchors/srs_per_ak/k_score_per_ak leer (K-SCORE.md fehlt)"

  SCHREIBE VAULT_PATH + "/" + dateiname:
    ---
    id: {bl_id}
    title: {NAME}
    version: {1 bei create, neue_version bei update}
    created: {heute bei create, bestehende_created bei update}  # AK-02-03
    updated: {heute}
    spec_link: {spec_link}
    model_links:
      - {model_link}
    vault_knoten_id: {vault_knoten_id}
    status: DRAFT
    komplexitaet: {komplexitaet}
    modellreife: {modellreife}
    fragilitaet: {fragilitaet}
    reifegrad: {reifegrad}
    crumbs_ref: {crumbs_ref}
    ankerknoten: []
    dependencies: []
    # BL-142 RF-A6 (additiv) — Per-AK Anker fuer IDF/SDF
    ak_anchors: {ak_anchors}             # ["AK-001", "AK-002", ...]
    srs_per_ak: {srs_per_ak}             # {AK-001: 35, AK-002: 62, ...}
    k_score_per_ak: {k_score_per_ak}     # {AK-001: 28, AK-002: 71, ...}
    ---

    # {NAME}

    ## Spec
    Siehe: [[{spec_link}]]

    ## Model
    Siehe: [[{model_link}]]

    ## Metriken
    - K-Score: {A_PIPELINE_STATE.k_score} ({A_PIPELINE_STATE.k_label})
    - Aufwand: {k_aufwand} → normiert {komplexitaet}/5
    - Fragilitaet: {k_fragilitaet} → normiert {fragilitaet}/5
    - Modellreife: {model_maturity}% → normiert {modellreife}/5
    - Reifegrad: {reifegrad}

    ## Aggregat-Score
    {A_PIPELINE_STATE.aggregat_score}

  # ============================================================
  # SCHRITT 4.5: BL-Item Ordnerstruktur im Vault (BL-034, RF-01)
  # AK-01-01: Unterordner aus vault-routing.json (subfolder_structure)
  # AK-01-02: Index-Knoten mit Obsidian-Links zu Unterordnern
  # AK-01-03: Vault-Pfad aus vault-routing.json (INV-6, nie hartcodiert)
  # ============================================================

  IF mode == "create" OR mode == "intake":
    # Lese Ordnerstruktur aus vault-routing.json (AK-01-03)
    subfolder_config = vault_routing.backlog.subfolder_structure ?? null
    IF subfolder_config != null AND subfolder_config.enabled == true:
      bl_ordner = VAULT_PATH + "/" + bl_id + "-" + slug + "/"
      mkdir -p bl_ordner

      # Unterordner aus Konfiguration erstellen (NICHT hartcodiert)
      ordner_links = []
      FUER folder IN subfolder_config.folders:
        mkdir -p bl_ordner + folder.ordner
        ordner_links.append("[[" + folder.ordner + "/]]")
        LOGGE: "[ORDNERSTRUKTUR] Erstellt: {bl_ordner}{folder.ordner}/"

      # Index-Knoten im Ordner-Root aktualisieren (AK-01-02)
      # Obsidian-Links zu allen Unterordnern hinzufuegen
      index_knoten = VAULT_PATH + "/" + dateiname
      IF DATEI_EXISTIERT(index_knoten):
        # Obsidian-Links-Sektion am Ende des Index-Knotens anhaengen
        APPEND index_knoten:

          ## Artefakte
          FUER folder IN subfolder_config.folders:
            - [[{bl_id}-{slug}/{folder.ordner}/|{folder.ordner}]]

      Logge: "[ORDNERSTRUKTUR] {bl_id}: {subfolder_config.folders.length} Unterordner + Index-Links erstellt"
    ELSE:
      Logge: "[ORDNERSTRUKTUR] subfolder_structure nicht aktiviert in vault-routing.json — Skip"

  # ============================================================
  # SCHRITT 5: Index APPEND (ZWEITES)
  # AK-05-01: Phase 2 der 3-Phasen-Persistenz
  # AK-05-03: Dual-Persistenz — counter in Index-Frontmatter (Mirror)
  # ============================================================

  IF mode == "create":
    APPEND _backlog_index.md Tabelle:
      | {bl_id} | {NAME} | DRAFT | {VAULT_PATH}/{dateiname} | {heute} | {reifegrad} |

    UPDATE _backlog_index.md Frontmatter:
      backlog_counter: {neue_nr}
      backlog_last_update: {heute}

  ELIF mode == "update":
    UPDATE _backlog_index.md Zeile WHERE BL-ID == bl_id:
      Status beibehalten, Vault-Pfad beibehalten
      # Nur Metadaten-Aenderung im Vault-Item selbst

    UPDATE _backlog_index.md Frontmatter:
      backlog_last_update: {heute}
      # backlog_counter NICHT aendern (INV-3)

  # ============================================================
  # SCHRITT 6: Manifest-Update (LETZTES)
  # AK-05-01: Phase 3 der 3-Phasen-Persistenz (counter+1 NUR hier)
  # AK-05-02: Crash vor Phase 3 → counter=alt → idempotente Wiederholung
  # AK-05-03: Dual-Persistenz — counter in Manifest (primaer) identisch mit Index
  # ============================================================

  IF mode == "create":
    UPDATE _manifest.md:
      BACKLOG_STATE:
        backlog_counter: {neue_nr}
        backlog_last_id: {bl_id}
        backlog_active: {bl_id}

      A_PIPELINE_STATE (APPEND-Felder):
        backlog_item_created: true
        backlog_item_id: {bl_id}
        backlog_item_status: "DRAFT"

  ELIF mode == "update":
    UPDATE _manifest.md:
      BACKLOG_STATE:
        backlog_last_id: {bl_id}  # unveraendert
        backlog_active: {bl_id}   # unveraendert
        # backlog_counter: NICHT AENDERN (INV-3)

      A_PIPELINE_STATE (APPEND-Felder):
        backlog_item_created: true
        backlog_item_id: {bl_id}
        backlog_item_status: "DRAFT"

  LOGGE: "/_backlog {mode}: {bl_id} → {VAULT_PATH}/{dateiname}"
  # BL-210 M1 Fix 2026-05-24: User-Visible-Hint dass Item DRAFT ist und Reifungs-Routing braucht
  IF mode == "create" OR mode == "intake":
    LOGGE: "/_backlog HINWEIS: BL-Item ist status=DRAFT. BDF Phase 2 SCANNING liest nur status=READY."
    LOGGE: "/_backlog HINWEIS: Naechster Schritt — Skill(_BL_orchestrate) fuer Reifungs-Routing (DRAFT → READY)."

  # BL-210 M13 Fix 2026-05-24: backlog_active Audit-Marker-Doku
  # `backlog_active` ist Audit-Marker (wer/wann zuletzt aktiv), NICHT Filter-Feld fuer BDF.
  # BDF Phase 2 SCANNING liest backlog_last_id, NICHT backlog_active (kein Reader).
  # Daher: backlog_active bleibt als Audit-Trail (last_touched_bl), KEIN Feld-Remove noetig.
  # Bei Reset/Cleanup: backlog_active kann manuell auf null gesetzt werden.
  RETURN bl_id
```

---

## Schreibreihenfolge (Atomaritaet) — AK-05-01, AK-05-02, AK-05-03

Die Reihenfolge ist KRITISCH fuer Crash-Safety:

```
1. Vault-Datei  (idempotent — kann wiederholt geschrieben werden)
2. Index-APPEND (safe — neue Zeile oder Feld-Update)
3. Manifest     (LETZTER Schritt — counter+1 erst wenn alles andere steht)
```

**Warum diese Reihenfolge:**
- Bei Crash nach Schritt 1: Vault-Datei existiert, aber counter=alt → naechster
  Aufruf erkennt via EXISTS-Check, ueberschreibt idempotent
- Bei Crash nach Schritt 2: Index hat Eintrag, Manifest alt → Manifest ist PRIMAER,
  Index-Eintrag wird bei naechstem create ignoriert (counter stimmt noch)
- Manifest zuletzt: Erst wenn Vault+Index konsistent sind, wird counter inkrementiert

---

## Fehlerbehandlung

| Fehlerfall | Verhalten | Manifest-Eintrag |
|-----------|-----------|-------------------|
| Vault-Pfad nicht erreichbar | RETURN, Pipeline faehrt fort (non-blocking) | BACKLOG_STATE.backlog_error = "VAULT_UNREACHABLE" |
| OmniCommand-Pattern nicht in vault-routing.json | HiL-Fehler — manuelle Korrektur noetig | BACKLOG_STATE.backlog_error = "PATTERN_NOT_FOUND" |
| RESYNC ohne bestehendes BL-Item | Fallback auf create, Log-Warning | — |
| crumbs_ref Datei nicht vorhanden | crumbs_ref = null, kein Fehler (INV-8) | — |
| Vault-Datei existiert bereits (create) | Ueberschreiben (idempotent, Partial-Write-Recovery) | — |
| Manifest-Schreibfehler | LOGGE FEHLER, Items im Vault+Index konsistent | Pipeline stoppt |

---

## raw_source Append (BL-043, RF-03)

Externer Mechanismus fuer Post-WP raw_source-Erweiterung.
Wird von `_WP_orchestrate.md` Schritt 4c aufgerufen (NICHT von _backlog selbst).

```
# BL-043 AK-03-01: raw_source APPEND (bestehende Eintraege bleiben erhalten)
# AK-03-02: crumbs_ref bleibt single-value (kein Schema-Breaking-Change)
# AK-03-03: Non-blocking — Fehler blockiert aufrufende Pipeline NICHT
#
# Aufruf: Direkt durch _WP_orchestrate Schritt 4c (kein eigener Command)
# Input: vault_pfad (BL-Item im Vault), neuer_pfad (WP-Crumbs-Pfad)
# Output: raw_source im Frontmatter um neuer_pfad erweitert
#
# FUNCTION raw_source_append(vault_pfad, neuer_pfad):
#   bestehende = LIES Frontmatter(vault_pfad).raw_source
#   IF bestehende IST String:
#     neue_raw_source = [bestehende, neuer_pfad]
#   ELIF bestehende IST Liste:
#     IF neuer_pfad IN bestehende:
#       LOGGE: "[RAW_SOURCE] Duplikat-Schutz: {neuer_pfad} bereits vorhanden"
#       RETURN
#     neue_raw_source = bestehende + [neuer_pfad]
#   ELSE:
#     neue_raw_source = [neuer_pfad]
#   SCHREIBE Frontmatter(vault_pfad).raw_source = neue_raw_source
#   LOGGE: "[RAW_SOURCE] Erweitert: {vault_pfad} +{neuer_pfad}"
```

**Hinweis:** crumbs_ref wird NICHT geaendert (ADR-02, AK-03-02). WP-Crumbs werden
via Naming-Convention `{NAME}_wp_crumbs.md` per Glob gefunden (Phase 0.5.0 in A-Pipeline).

---

## RESYNC-Logik

```
IF A_PIPELINE_STATE.modus == "FRESH":
  → mode = "create" (Default)
  → Neue BL-Nummer (counter+1)
  → Neues Item mit version=1

IF A_PIPELINE_STATE.modus == "RESYNC":
  → mode = "update"
  → Bestehendes Item: version N+1
  → counter NICHT inkrementieren (INV-3)
  → created beibehalten, updated = heute
  → Status beibehalten (kein Reset auf DRAFT)

IF RESYNC aber kein bestehendes BL-Item:
  → Fallback auf create mit Log-Warning
  → "RESYNC ohne BL-Item: Erstelle neues Item (Fallback)"
```

---

## Vault-Datei Template

```markdown
---
id: "BL-001"
title: "OmniCommand_Backlog"
version: 1
created: "2026-04-01"
updated: "2026-04-01"
spec_link: ".claude/specs/OmniCommand_Backlog_Spec.md"  # BL-008: kanonischer Pfad
model_links:
  - ".claude/models/OmniCommand_Backlog_Model.md"
vault_knoten_id: "BL-001-omnicommand-backlog"
status: DRAFT
komplexitaet: 2
modellreife: 3
fragilitaet: 2
reifegrad: SC-REIF
crumbs_ref: ".claude/crumbs/OmniCommand_Backlog_crumbs.md"
ankerknoten: []
dependencies: []
# BL-142 RF-A6 (additiv) — Per-AK Anker fuer IDF/SDF
ak_anchors: ["AK-001", "AK-002", "AK-003"]
srs_per_ak:
  AK-001: 35
  AK-002: 62
  AK-003: 18
k_score_per_ak:
  AK-001: 28
  AK-002: 71
  AK-003: 22
---

# OmniCommand_Backlog

## Spec
Siehe: [[{spec_link}]]

## Model
Siehe: [[.claude/models/OmniCommand_Backlog_Model.md]]

## Metriken
- K-Score: 33.61 (MEDIUM)
- Aufwand: 36.62 → normiert 2/5
- Fragilitaet: 34.72 → normiert 2/5
- Modellreife: 53% → normiert 3/5
- Reifegrad: SC-REIF

## Aggregat-Score
{A_PIPELINE_STATE.aggregat_score}
```

---

## Integration

### Aufrufer
- `_A_berater_metadatenAggregation` (gerufen von `_A_orchestrate` Phase 4.2a, BL-142 RF-A-RENAME)

### Abhaengig von
- `_gap` — muss vorher gelaufen sein (A-Pipeline Reihenfolge)
- `_spec` / `_model` — Dateien muessen existieren fuer spec_link/model_links

### Downstream
- `_BDF_orchestrate` (v2.0) — liest Backlog-Items fuer Batch-Planung
- `_backlog_index.md` — APPEND-ONLY Index aller Items

---

## Changelog

### v1.5 (2026-04-26) — BL-142 Phase 5E: recommendation → aggregat_score

- VERTRAG LIEST: `recommendation` → `aggregat_score` (A_PIPELINE_STATE; recommendation gestrichen)
- SCHRITT 4 Pseudocode: `{A_PIPELINE_STATE.recommendation}` → `{A_PIPELINE_STATE.aggregat_score}`
- Vault-Template: Sektion `## Empfehlung` → `## Aggregat-Score` + Platzhalter angepasst
- Changelog-Notiz Zeile 789 (nur Doku) bleibt unberuehrt
- Kein `complexity_*` in dieser Datei vorhanden

### v1.4 (2026-04-25) — BL-142 Phase 5E: reifegrad_hint Override-Mechanismus

- Schritt 3.5b: Externer Hint kann automatischen Reifegrad ueberschreiben.
  Quellen: CLI (--hint), BL_LIFECYCLE_STATE.reifegrad_hint, A_PIPELINE_STATE.reifegrad_hint.
  Prioritaet: CLI > BL_LIFECYCLE_STATE > A_PIPELINE_STATE > berechnet.
  INV-HINT-1: Hint nur aus ENUM {REIF, SC-REIF, UNREIF}.
  INV-HINT-2: Aufstieg nur mit --hint-force; Rueckstufung erlaubt.
  Audit-Trail: reifegrad_hint_applied im BL-Frontmatter.

### v1.3 (2026-04-25) — BL-142 RF-A6: Per-AK Anker

- VERTRAG LIEST: Quelle 7 ergaenzt: {VAULT}/.../4_K-Score/{NAME}-K-SCORE.md (OPTIONAL, additiv)
- SCHRITT 3.5 ergaenzt: K-SCORE.md Frontmatter ak_details lesen → ak_anchors, srs_per_ak, k_score_per_ak
- Frontmatter-Schema: 3 neue Felder additiv: ak_anchors (Liste), srs_per_ak (Map), k_score_per_ak (Map)
- Vault-Datei-Template: BL-142 RF-A6 Beispiel-Werte ergaenzt (AK-001..AK-003)
- INV-8: Fehlende K-SCORE.md → leere Listen/Maps, kein Fail
- KEIN unreife_typ_kandidat (gehoert zu IDF Phase 7)
- KEIN forced_mode_hint (kommt von User oder Findings)

### v1.2 (2026-04-04) — BL-024 M2 Inline (16 AKs)
- AK-01-01: Vault-Datei 16-Felder-Annotation im Pseudocode (SCHRITT 4)
- AK-01-02: BL-Nummer monoton steigend — explizite Annotation (SCHRITT 2 create)
- AK-01-03: EXISTS-Check Partial-Write-Recovery — explizite Annotation
- AK-02-01: Version inkrementiert, Counter stabil — Annotation + INV-3 Verweis
- AK-02-02: Fallback auf create bei fehlendem Item — WARNING-Log-Level + Annotation
- AK-02-03: created-Datum beibehalten — bestehende_created explizit ausgelesen + Annotation
- AK-03-01: Auto-Intake-Erkennung — Annotation + Aufruf-Doku um .m4a/.webm ergaenzt
- AK-03-02: RAW-pileOfMud-Kopie — Annotation + Ziel-Schema-Kommentar
- AK-04-01: Schwellenwerte korrekt — Annotation mit konjunktiv/disjunktiv-Verweis
- AK-05-01: Schreibreihenfolge 3-Phasen — Annotationen in SCHRITT 4/5/6 + VERTRAG
- AK-05-02: Crash nach Phase 1 idempotent — Annotation in SCHRITT 6 + VERTRAG
- AK-05-03: Dual-Persistenz Counter — Annotationen in SCHRITT 5/6 + VERTRAG
- AK-06-01: LIEST 6 Quellen — Annotation im VERTRAG-Block
- AK-06-02: SCHREIBT 3 Ziele — Annotation im VERTRAG-Block
- AK-06-03: SCHREIBT NICHT PL (INV-5) — Annotation im VERTRAG-Block
- AK-07-01: VAULT_UNREACHABLE non-blocking — Annotation im GUARD-Pseudocode
- AK-07-02: PATTERN_NOT_FOUND HiL-Guard — NEU: explizite Guard-Logik im Pseudocode
- Schreibreihenfolge-Sektion: AK-05-01/02/03 Ueberschrift-Referenz

### v1.1 (2026-04-04) — BL-024 M1 Inline (6 AKs)
- AK-03-03: Intake-Template auf 13+3 Felder (BacklogItem-Schema v1.0) erweitert
- AK-03-04: Name-Ableitung um .m4a/.webm Extensions + regex_replace Datum-Muster
- AK-04-02: Default UNREIF Guard in berechne_reifegrad() hinzugefuegt
- AK-04-03: OQ-01 Normierungs-Diskrepanz als PENDING-Kommentar dokumentiert
- AK-07-03: crumbs_ref null-tolerant — INV-8 Log-Meldung + expliziter Guard
- VERTRAG: "12+ Pflichtfelder" korrigiert zu "13 Pflicht + 3 Optional"

### v1.0 (2026-04-01) — Initialer Pseudocode
- 560 LOC Pseudocode: 3 Modi (create/update/intake), VERTRAG, Invarianten
- berechne_reifegrad(), normiere(), normiere_reife()
- Crash-Safety 3-Phasen-Persistenz Design
- Fehlerbehandlungstabelle, RESYNC-Logik, Vault-Template
