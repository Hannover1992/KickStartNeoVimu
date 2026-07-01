---
status: active
version: 1.0.0
created: 2026-05-28
op: HookWorkaround
type: command
chain_position: standalone
owner_only: true
hard_constraint: "OWNER-ONLY. Agents BLOCKIERT via guard_hook_prep_owner_only.py. Bewusster Mensch-Override."
governing_doc: Enforce_Refactor_Master_Analyse_2026-05-27.md
---

# /_hook_workaround — Owner-Only Hook-Aussetzer

## Was es IST

Ein **bewusster, menschlich-autorisierter Aussetzer**. Wenn DU (der Mensch) legitim vom Prozess
abweichst (z.B. IDF pragmatisch übersprungen), präpariert dieser Befehl den State so dass die
blockierende Hook-Vorbedingung erfüllt ist — und du läufst **prozesskonform weiter** mit den
nächsten Schritten.

## Was es NICHT ist

- **KEIN Agent-Tool.** `guard_hook_prep_owner_only.py` BLOCKIERT jeden Agent/Worker-Aufruf HART.
- **KEIN Drift-Laundering durch Automatik.** Nur DU entscheidest wann ein Block ein False-Positive ist.
- **KEINE Hook-Deaktivierung.** Die Hooks bleiben aktiv — nur DIESER eine Übergang wird präpariert.

## OWNER-ONLY Enforcement

```
guard_hook_prep_owner_only.py (PreToolUse Skill):
  - Triggert bei Skill(_hook_workaround)
  - Prueft OMNI_AGENT_NAME / OMNI_WORKER_ID / OMNI_SUBAGENT env
  - Wenn Agent-Kontext erkannt -> HARTER BLOCK (kein Toggle)
  - Nur Main-Session (Mensch tippt Befehl) -> erlaubt
  - Jeder Aufruf -> audit.jsonl event=HOOK_PREP_OWNER_INVOKED
```

## Aufruf

```
/_hook_workaround [--position=auto] [--target-hook=NAME] [--op=OPERATION] [--dry-run]
```

| Parameter | Default | Beschreibung |
|---|---|---|
| `--position` | auto | Geist-Position (auto = aus Manifest detecten) |
| `--target-hook` | auto | Welcher Hook blockt (auto = aus _guard_log letzte BLOCKED) |
| `--op` | auto | Welche Operation (siehe Operations-Katalog) |
| `--dry-run` | false | Zeigt was praepariert wuerde, ohne zu schreiben |

## Phasen

### Phase 1: Block-Diagnose

```python
# Lese letzte BLOCKED-Eintraege aus _guard_log.md
last_blocks = read_guard_log_blocks(limit=10)
# Lese aktuellen Manifest-State (per-BL-folder ODER flat-vault aware)
manifest = resolve_manifest()  # current_context.py bl_manifest_path bevorzugt
# Detecte Geist-Position (welcher Uebergang ist aktiv?)
position = detect_geist_position(manifest)
```

### Phase 2: Klassifikation (DU entscheidest)

Der Befehl PRAESENTIERT die Diagnose. **DU** klassifizierst:

```
Block: GEIST5_CONTRACT_VIOLATION (IDF->SDF)
  Hook sagt: "Manifest nicht gefunden — SDF darf nicht starten"
  IST-State: Manifest existiert @ Backlog/DCSRE-486/_manifest.md
             mit batch_mode_hints (line 8080), batch_stages (line 8045)
  → KLASSE: HOOK-BUG (Pfad-Resolution flat-vault statt per-BL-folder)

  DEINE Entscheidung:
    [a] HOOK-BUG → /_hook_workaround --op=manifest-path-bridge
    [b] STRUKTUR-FP → /_hook_workaround --op=...
    [c] REAL-DRIFT → KEIN workaround, Prozess befolgen
```

### Phase 3: Operation ausführen (nur was DU autorisierst)

## Operations-Katalog

| Operation | Was sie tut | Für welchen Hook |
|---|---|---|
| `manifest-path-bridge` | Sorgt dass Manifest am erwarteten Pfad findbar ist (Symlink/Kopie per-BL → erwarteter Ort) | guard_geist5 |
| `manifest-dedup` | Konsolidiert Duplikat-Sections (A_PIPELINE_STATE x2 → Round-Suffix) | guard_stab9 |
| `batch-contract-mark` | Markiert batch_mode_hints als IDF-geliefert (nur wenn IDF wirklich lief!) | guard_geist5 |
| `counter-reset` | Reset Loop-Counter (du autorisierst) | guard_stab8 |
| `provenance-backfill` | set_by/exit_code/ts an existing Berater-Blocks (du verifizierst dass Worker liefen) | guard_stab1 |
| `state-disarm` | Reset stale Geist10/Geist11 State-Files | guard_geist10/11 |

## INVARIANTEN

- **INV-HOOKWA-1:** OWNER-ONLY. Agents HART blockiert (guard_hook_prep_owner_only.py).
- **INV-HOOKWA-2:** Jede Operation wird in audit.jsonl geloggt (event=OWNER_MANUAL_WORKAROUND mit op + position + ts). Voller Trail deiner Override-Entscheidungen.
- **INV-HOOKWA-3:** Hooks bleiben AKTIV. Nur der spezifische Übergang wird präpariert, kein globales Off.
- **INV-HOOKWA-4:** Bei REAL-DRIFT verweigert der Befehl die Operation NICHT — aber er WARNT explizit "Das sieht nach echter Drift aus, nicht nach False-Positive. Sicher?" — DU entscheidest final.
- **INV-HOOKWA-5:** `--dry-run` zeigt immer zuerst was passieren würde. Default-Empfehlung: erst dry-run.

## Beispiel-Flow (der Live-Fall 2026-05-28)

```
Situation: IDF pragmatisch übersprungen, SDF soll starten.
guard_geist5 blockt: "Manifest nicht gefunden"

DU: /_hook_workaround --dry-run

[HOOK-WA] Phase 1 Diagnose:
  Letzter Block: GEIST5_CONTRACT_VIOLATION @ 11:25
  Manifest-IST: Backlog/DCSRE-486-.../_manifest.md EXISTS
    - batch_mode_hints: ✓ (line 8080, Round 15)
    - batch_stages: ✓ (line 8045)
    - ANTI_SHADOW_NOTE: "batch_modes NICHT geschrieben" ✓
  Geist-Position: IDF→SDF (Round 16)

[HOOK-WA] Klassifikation:
  → HOOK-BUG: guard_geist5 sucht {vault_root}/_manifest.md,
    aber DCSRE nutzt per-BL-folder. IDF-Output IST korrekt vorhanden.
  → Empfohlene Op: manifest-path-bridge

[HOOK-WA] DRY-RUN — würde tun:
  1. guard_geist5 manifest-resolution auf per-BL-folder erweitern
     ODER (temporär): Bridge-Marker setzen
  2. Log OWNER_MANUAL_WORKAROUND --op=manifest-path-bridge

DU: /_hook_workaround --op=manifest-path-bridge --apply

[HOOK-WA] Applied. SDF kann jetzt starten. Prozess läuft weiter.
[HOOK-WA] audit.jsonl: OWNER_MANUAL_WORKAROUND logged.
```

## Wann NICHT nutzen (REAL-DRIFT)

| Block | Klasse | /_hook_workaround? |
|---|---|---|
| guard_geist7: Mega-Worker statt Step-Pipeline | REAL-DRIFT | NEIN — Pipeline-Steps nachfahren |
| guard_geist5: batch_modes ohne SDF-Berater | REAL-DRIFT | NEIN — SDF Phase 1.1 laufen lassen |
| guard_stab3: M3-Code ohne RED-Test | REAL-DRIFT | NEIN — TDD befolgen |
| guard_geist5: Manifest-Pfad falsch (existiert aber) | HOOK-BUG | JA — manifest-path-bridge |
| guard_stab9: Pre-existing dup blockt neue Writes | STRUKTUR-FP | JA — manifest-dedup |
| guard_stab10: DCSRE-prefix nicht erkannt | HOOK-BUG | JA (oder Hook patchen) |

**Faustregel:** Wenn der Prozess INHALTLICH korrekt lief (IDF schrieb echte hints, Worker liefen wirklich) aber der Hook die Daten nur in falscher SHAPE sieht → workaround OK. Wenn der Prozess INHALTLICH übersprungen wurde → kein workaround, Prozess befolgen.

## Verwandte Commands

- `/_sanity_process` — prüft ob Prozess wirklich befolgt wurde (komplementär: workaround sagt "Daten-Shape", sanity sagt "Prozess-Inhalt")
- `/_param enforceProcess=false` — globaler Off-Switch (gröber, nicht positions-spezifisch)
- `process_preflight.py` — zeigt erwartbare Hook-Trigger VOR Lauf

## Changelog

### v1.0.0 (2026-05-28) — Initial Release
- Owner-Only Hook-Precondition-Preparer
- guard_hook_prep_owner_only.py enforced Agent-Block
- 6 Operations (manifest-path-bridge, manifest-dedup, batch-contract-mark, counter-reset, provenance-backfill, state-disarm)
- INV-HOOKWA-1..5
- Anlass: DCSRE-486 Round 16 — guard_geist5 + guard_stab9 False-Positives durch
  per-BL-folder-vault-structure (Hooks waren flat-vault-centric)
