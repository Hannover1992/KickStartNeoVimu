# /_pattern_add — Easy Pattern-Capture (Arch + Semantic), einstufig + vault-resolved

```yaml
status: active
version: 1.0.0
created: 2026-06-02
op: SubCommand
type: building-block
feature_anchor: DCSRE-486-Pattern-Capture-Leak-Audit
related: [_PT_promoteFromPL, _PT_extract, _SL_promoteFromPL, _I_architecturalLibrary, _SL_conformance]
engine: .claude/scripts/pattern_library.py
```

## Zweck

**Out-of-the-box Pattern hinzufuegen** — der schnelle, EINSTUFIGE Direkt-Add, der dem Capture-Pfad
heute fehlt. Motiviert vom **DCSRE-486-Audit (2026-06-02):** der mehrstufige Pfad
(`promoteFromPL` → Kandidaten-Liste → `_PT_extract` → materialisieren) ist leck — 486s Promote-Log
notierte *"PT-Library war leer"* (Resolution-Bug, Dedup tot) und 7 Kandidaten blieben
un-materialisiert; von ~80 Pattern-Signalen landeten ~4. Dieser Befehl macht den Add **einstufig,
vault-resolved (fixt den "leer"-Bug), konsistent (Skript statt Hand), mit Dedup.**

`{META}`-konsistent: alles laeuft ueber den deterministischen Motor `pattern_library.py` → keine
hand-geschriebene Format-Drift, im Vault abgelegt, ueber `_index.md` findbar.

## Aufruf

```
/_pattern_add --arch     {LAYER} "{Name}"   # PatternLibrary: PT-{SHORT}-{NNN} materialisieren
/_pattern_add --semantic {LAYER} "{Term}"   # SemanticLibrary: Term/Konvention anhaengen
/_pattern_add --consult  "{Topic|Diff}"     # Consult: passende Patterns surfacen (vor Impl)
/_pattern_add --harvest  {BL_ID}            # Pattern-Signale eines BL ernten (gegen den Leak)
```

LAYER z.B. `BE-DOMAIN`, `BE-CONT`, `BE-TEST`, `FE-FORM`. Semantic-Target via `--target terms|naming|glossary`.

## Ablauf (Lead fuehrt selbst — INV-AO-CALLER)

### Modus `--arch` / `--semantic` (Easy-Add)
1. **Erden (PFLICHT — kein Erfinden):** lies den realen Code/Diff/die Entscheidung. Felder kommen
   AUS dem Code (wie 486s PT-DOM-005 `sources:` echte .cs-Dateien zitiert), nicht aus der Fantasie.
2. **Consult-Vorlauf:** `py -3 .claude/scripts/pattern_library.py find "{kernbegriff}"` → existiert das
   Pattern schon? Wenn ja → NICHT neu anlegen (Dedup), ggf. bestehendes via `_PT_update` erweitern.
3. **Felder entwerfen:** name (kurz), description (1 Satz), tags, sources (echte Pfade),
   pattern (Regel-Bullets), beispiel (Code-Fence), abgrenzung (Abgrenzungs-Bullets).
4. **Materialisieren (einstufig):**
   ```
   py -3 .claude/scripts/pattern_library.py add --arch --layer {LAYER} \
       --name "{Name}" --description "{desc}" --tags {t1,t2} --sources {p1,p2} \
       --pattern "{regel}" --beispiel @{tmpfile_or_-} --abgrenzung "{abgr}" --story {BL_ID}
   ```
   (laengere Bloecke via `@pfad`-Datei oder `-` fuer Skelett-TODO.) Semantic analog mit `--semantic --target`.
5. **Quittung:** der Motor druckt `PT-{SHORT}-{NNN} -> {pfad}` + ggf. `[WARN] aehnliches Pattern`.
   Verifiziere die `_index.md`-Zeile.

### Modus `--consult` (formalisiert was Fenster 2 manuell tat — 25k Token gespart)
- `pattern_library.py find "{topic}"` über alle `_index.md` → Kandidaten-Patterns + Layer.
- Lies die Top-Treffer, gib ein **Konformitaets-Verdikt**: "PT-X/PT-Y treffen zu → konforme Form ist Z".
  (Das ersetzt die 5 manuellen Greps des Enum-Falls.)

### Modus `--harvest {BL_ID}` (der Leak-Fix forward)
- Sammle die **Pattern-Signale** des BL (PL-Items mit arch/cross-cutting/validation/example-Signal;
  vgl. 486 `_ptPromote_log` Spalte "Reasons").
- Pro pattern-wuerdigem Signal → **direkt** `add --arch` (kein Kandidat-Zwischenschritt mehr).
- Skip trivial/lokal/dup (wie 486s Skip-Liste). Report: N materialisiert / M skipped.

## INVARIANTEN
- **INV-PAT-1:** Add laeuft AUSSCHLIESSLICH ueber `pattern_library.py` (kein Lead-Inline-File-Write) →
  Format-Konsistenz garantiert.
- **INV-PAT-2:** Felder code-grounded (`sources:` echte Pfade) — kein erfundenes Pattern.
- **INV-PAT-3:** Dedup-Vorlauf (`find`) PFLICHT vor `add` — kein Doppel-Pattern.
- **INV-PAT-4:** EINSTUFIG materialisieren — KEIN Kandidat-Listen-Zwischenschritt (das war der 486-Leak).
- **INV-PAT-5 (Quiescenz):** schreibt in `{VAULT}/Libraries/...` — bei aktiver Zweit-Session auf
  demselben Vault NICHT konkurrierend schreiben (vgl. BL-229 AK-E `manifest_quiescence`).

## Verwandt / Abloesung
- Ersetzt NICHT `_PT_promoteFromPL` (Batch-Ernte am Story-Ende) — ist der **schnelle Single-Add** dazwischen.
- `pattern_library.py` SOLL der gemeinsame Motor werden, den auch `_PT_promoteFromPL`/`_PT_extract`
  nutzen (fixt deren "war leer"-Resolution-Bug = DRY). Folge-Refactor.
```
