# Manifest-Write-Disziplin (BL-367 F8/F9, parent BL-322)

**Geladen von:** jedem Berater / Worker, der einen Block an ein Manifest (`_manifest.md`,
`_factory_manifest.md`, BL-folder-Manifeste) anhaengt. **Quelle:** Gate-C C1-VOLL + BL-332
IDF-Run Findings (F8 Fence-Imbalance, F9 python3-silent-no-op, Glue-Klasse).

---

## INV-MANIFEST-WRITE-1 (MANDAT)

**Jeder Manifest-Block-Append MUSS ueber den gemeinsamen Helper laufen:**
`.claude/scripts/manifest_append.py` (`append_block(...)` / CLI). **Kein** ad-hoc
PowerShell/Python-Append mehr.

**VERBOTEN** (die drei Live-belegten Fehlerklassen):
- PowerShell here-strings / `Add-Content` / `Out-File` / `Set-Content` direkt aufs Manifest
  -> Glue-Klasse (`...befund: true    batch_PL3:` — Zeilen verkleben, kein Trenn-NL).
- `python3 ...` als Interpreter -> auf Windows MS-Store-Stub, **silent no-op** (Phantom-Write,
  exit 49 maskiert, Manifest unveraendert ohne Fehler). **IMMER `py -3`** (oder den Helper).
- Roh-Append ohne Fence-Balance-Pruefung -> ungerade col-0-```-Fences -> latentes
  YAML-Block-Parser-Korruptions-Risiko (Guards/Reader mis-parsen den offenen Block + alles danach).

## Die 5 Eigenschaften des Helpers (warum er die Klasse eliminiert)

1. **utf-8 no-BOM** — read strip-BOM (utf-8-sig), write IMMER ohne BOM.
2. **col-0-fence-balanced** — zaehlt NUR Spalte-0-```; indentierte/Prosa-``` ausgeschlossen
   (F8-KORREKTUR: naive ```-Zaehlung zaehlt ein eingeruecktes Prosa-Zitat als Fence -> Fehlalarm
   + Risiko einer Falsch-"Reparatur", die erst eine echte Imbalance einfuehrt). Ungerade
   col-0-Fences nach Append -> **RAISE, KEIN Write**.
3. **line-separator-safe** — Block startet IMMER auf neuer Zeile; bestehender NL-Stil (CRLF/LF)
   bleibt. Kein Zeilen-Merge/Glue.
4. **post-write Re-Read-Assert** — nach dem Write: re-read + verify Marker praesent; sonst
   `RuntimeError` (NIE silent — faengt den F9-Phantom-Write strukturell).
5. **py-3** — reines Python-Modul; der F9-Stub kann es nicht laden -> kein Phantom-Write.

## Nutzung

```
# CLI (Worker / Berater-Pseudocode):
py -3 .claude/scripts/manifest_append.py {manifest_path} --block-file {block.md} --marker "{eindeutig}"
echo "{block}" | py -3 .claude/scripts/manifest_append.py {manifest_path} --block - --marker "{eindeutig}"

# API (Python):
from manifest_append import append_block
append_block(manifest_path, block_text, marker=None)   # marker default = erste Block-Zeile
```

Bei Erfolg: JSON `{"ok": true, ...}` (stdout, exit 0). Bei Fence-Imbalance / fehlendem Marker:
`{"ok": false, "error": ...}` (stderr, **exit 1**) — der Worker MUSS exit!=0 als Fehlschlag werten
(nie "ich habe geschrieben" melden, wenn exit!=0).

## Rollout-Status (BL-367)

- **Helper:** LIVE + getestet (16 Tests + Behavior-Review API+CLI, repo-root gruen; commit 9b72f07).
- **Per-Berater Inline-Migration** (alle Manifest-Writer-Pseudocodes auf den Helper umstellen) +
  **Enforcement-Guard** (Pre-Write-Hook der ad-hoc Manifest-Writes blockt + auf den Helper verweist):
  getrackt als BL-367-Remainder (parent BL-322). Bis der Guard steht, ist INV-MANIFEST-WRITE-1
  die manuelle Standing-Disziplin.
