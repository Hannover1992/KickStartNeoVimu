# _archive_BL-065 — Archivierte obsolete W-Commands

**Grund:** BL-065 DirectWrite_Completion (C.2 Real-Run Session 2 2026-04-12)

Die 3 Commands in diesem Verzeichnis wurden im Rahmen von BL-065
DirectWrite_Completion archiviert (nicht geloescht). BL-065 schliesst die
Vault-First-Luecke aus BL-050: Synthese-Commands schreiben direkt in den
Vault, die alten Push/Sync-Commands sind dadurch obsolet geworden.

## Archivierte Dateien

1. `_W_push_orchestrate.md` — Push-Orchestrator (ersetzt durch DirectWrite)
2. `_W_obsidianSync.md` — Obsidian-Sync (ersetzt durch DirectWrite)
3. `_W_fireTogether.md` — Satellite-Fire-Together (ersetzt durch DirectWrite)

Alle 3 haben `deprecated: true` im Frontmatter (AK-06, Commit 1 9356ff6).

## Baseline-SHA (vor BL-065)

**Baseline-SHA:** `01c2caeeb49354ed565c82c7090cc52115e0d75a` (Commit vor BL-065 Commit 1 9356ff6)

## Rollback-Befehl

Um die Archivierung rueckgaengig zu machen (z.B. bei Scope-Reversion):

```bash
cd /home/uczen/Projekt/AllProjekt/Projekt/OmniCommand
git mv .claude/commands/_archive_BL-065/_W_push_orchestrate.md .claude/commands/_W_push_orchestrate.md
git mv .claude/commands/_archive_BL-065/_W_obsidianSync.md .claude/commands/_W_obsidianSync.md
git mv .claude/commands/_archive_BL-065/_W_fireTogether.md .claude/commands/_W_fireTogether.md
git commit -m "BL-065 AK-08 rollback: restore obsolete W-Commands"
```

Zusaetzlich muessen die Caller-Refactors aus Commit 2 (8df780a) rueckgaengig
gemacht werden — Phase 3 in `_W_orchestrate.md` und Z.478 in `_SC_implement.md`:

```bash
git revert 8df780a
```

## Datum

**Archiviert:** 2026-04-12
**Session:** C.2 BL-065 Real-Run Session 2 (autonome Sanduhr-Validierung)
