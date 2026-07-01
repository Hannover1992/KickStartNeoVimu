---
name: _vault_migration
description: Migriert Fremdprojekte auf VaultDrivenDevelopment Per-BL-Folder-Schema — Lock + Migration + Caller-Refactor
type: tool
op: VaultMigration
status: active
version: 1.0.0
---

# /_vault_migration

**Zweck:** Reproduzierbares Werkzeug fuer Cross-Project-Migration auf VDD-Schema (AK-I-3..I-6).
Delegiert an `scripts/vault_migration.py` — verallgemeinert die BL-151-Bausteine fuer Fremdprojekte.

**Aufruf:**
```
/_vault_migration PROJECT_PATH VAULT_PATH [--dry-run] [--in-flight]
```

**Parameter:**
- `PROJECT_PATH` — Absoluter Pfad zum Ziel-Projekt-Repo (enthaelt `.claude/`)
- `VAULT_PATH`   — Absoluter Pfad zum Vault-Root (enthaelt `Backlog/`)
- `--dry-run`    — Nur Vorschau, keine Datei-Schreibvorgaenge (Standard: aktiv empfohlen)
- `--in-flight`  — Aktive PL-Items via `status: in_progress` erkennen + Locks waehrend Migration

**Beispiele:**
```
/_vault_migration C:/Repos/DCSRE C:/Vault/DCSRE --dry-run
/_vault_migration C:/Repos/DCSRE C:/Vault/DCSRE --in-flight
```

---

## VERTRAG

### LIEST
- `{VAULT_PATH}/_backlog_index.md` — BL-Inventur (alle aktiven BLs)
- `{PROJECT_PATH}/.claude/analysis/_manifest.md` — Legacy-Manifest (falls vorhanden)
- `{VAULT_PATH}/Backlog/BL-{N}-*/` — Bestehende BL-Folder
- `{PROJECT_PATH}/scripts/bl_manifest_lock.py` — Dependency-Check
- `{PROJECT_PATH}/scripts/resolve_bl_path.py` — Dependency-Check

### SCHREIBT (nur bei echtem Run, nicht --dry-run)
- `{VAULT_PATH}/Backlog/BL-{N}-*/_manifest.md` — Migriertes Manifest (via BLManifestLock)
- `{VAULT_PATH}/archive/_manifest_legacy_{DATE}.md` — Backup des Legacy-Manifests
- `{VAULT_PATH}/output/vault_migration_report_{DATE}.md` — Migrations-Report
- `{PROJECT_PATH}/scripts/bl_manifest_lock.py` — Kopiert falls fehlend
- `{PROJECT_PATH}/scripts/resolve_bl_path.py` — Kopiert falls fehlend

### INVARIANTEN
- INV-VAULT-5: Alle Pfade absolut
- INV-VAULT-8: Per-BL-Manifest-Geographie einhalten
- BLManifestLock: Jeder Manifest-Write serialisiert (AK-C-12)
- Echter Run nur nach expliziter User-Bestaetigung (kein Auto-Delete)

---

## Vorbedingungen

Vor dem ersten echten Run pruefen:
1. `VAULT_PATH/Backlog/` existiert
2. `_backlog_index.md` vorhanden und lesbar
3. Git-Repo sauber (keine uncommitted changes) — fuer git-Tag-Sicherheit
4. Kein anderer Prozess haelt `_manifest.lock` in Ziel-BL-Folder

---

## Schritt-fuer-Schritt-Logik

### Schritt 1 — Script-Aufruf vorbereiten

Delegiere an Wrapper-Skript mit allen Parametern:

```bash
py -3 {OMNICOMMAND_SCRIPTS}/vault_migration.py \
  PROJECT_PATH VAULT_PATH [--dry-run] [--in-flight]
```

Script liegt in: `{OMNICOMMAND_SCRIPTS}/vault_migration.py`
(`{OMNICOMMAND_SCRIPTS}` wird per Env-Var oder via `current_context.py` aufgeloest;
auf der aktuellen Maschine z.B. `C:/Users/Administrator/Documents/OmniCommand/scripts/`).

### Schritt 2 — Dry-Run pruefen (immer zuerst)

Bei `--dry-run` zeigt das Script:
- Welche BLs migriert wuerden
- Welche Dateien erstellt/kopiert wuerden
- Welche In-Flight-Items gesperrt wuerden (bei --in-flight)
- Kein einziger Write findet statt

**Empfehlung:** IMMER zuerst `--dry-run` ausfuehren, Output lesen, dann echten Run bestaetigen.

### Schritt 3 — Echter Run (nur nach User-Bestaetigung)

Nach Dry-Run-Pruefung den echten Run starten:
```bash
py -3 vault_migration.py PROJECT_PATH VAULT_PATH --in-flight
```

Output-Datei: `{VAULT_PATH}/output/vault_migration_report_{DATE}.md`

### Schritt 4 — Verifikation

Nach echtem Run Smoke-Test:
```bash
py -3 {PROJECT_PATH}/scripts/resolve_bl_path.py BL-{N} VAULT_PATH
# Erwartung: Pfad zum migrierten BL-Folder, kein Fehler
```

---

## Fehler-Handling

| Fehler                          | Ursache                             | Massnahme                              |
|---------------------------------|-------------------------------------|----------------------------------------|
| `BLNotFoundError`               | BL-Folder nicht angelegt            | Schritt 5 des rollout_guide.md         |
| `LockTimeout`                   | Anderer Prozess haelt Lock          | Warten, dann Retry                     |
| `MigrationError: Quelle fehlt`  | Legacy-Manifest nicht vorhanden     | Manuell `_manifest.md` erstellen       |
| `git tag already exists`        | Migration bereits teilweise gelaufen| `git tag -d migration-BL-N-pre-DATE`   |
| Dependency fehlt                | bl_manifest_lock.py nicht im Projekt| Script kopiert automatisch (Schritt 2) |

---

## Referenzen

- `scripts/vault_migration.py` — Wrapper-Implementierung
- `scripts/migrate_manifest_to_bl_folder.py` — Einzel-BL-Migration
- `meta/architekturKonventionen/rollout_guide.md` — 7-Schritte-Anleitung
- `meta/architekturKonventionen/rollout_stichtag.md` — Stichtag-Policy
- `meta/architekturKonventionen/redeploy_policy.md` — Redeploy-Mechanik
