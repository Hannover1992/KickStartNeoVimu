# /stage — Commit-Normen-Dokument

Dieses Dokument definiert verbindliche Commit-Message-Normen fuer alle Produkt-Commits.
Maschinenlesbare Quelle fuer `/_stage_orchestrate`.

---

## 1. Commit-Message-Normen

| Norm | Regel | Schwere | Pruef-Pattern |
|------|-------|---------|---------------|
| Format | `$branch: $Title` — Pflichtformat | KRITISCH | `^[A-Z0-9_-]+: .+` |
| Laenge | Nur EINE Zeile (kein Mehrzeiler) | KRITISCH | Anzahl Zeilen == 1 (nach Trim) |
| Co-Worker | Kein `Co-Authored-By` in Message | KRITISCH | `(?i)co-authored-by` |
| Anthropic | Keine Erwaehnung von `Anthropic` | KRITISCH | `(?i)anthropic` |
| Claude | Kein `Claude` als Co-Author | KRITISCH | `(?i)claude` (in Trailer-Kontext) |
| Description | Kein Description-Block (nur Titel) | MITTEL | Zeilen > 1 nach erster Leerzeile |
| Separator | Kein `---` nach Titel-Zeile | MITTEL | `^---` nach erster Zeile |

**Beispiel-Commit (korrekt):**
```
DCSRE-1189: S3442 - Constructor visibility auf protected geaendert
```

**Beispiel-Commit (falsch — wird von stage_orchestrate abgelehnt):**
```
DCSRE-1189: S3442 - Constructor visibility geaendert

Co-Authored-By: Claude Sonnet <noreply@anthropic.com>
```

---

## 2. Security-Verbote

| Verbot | Pattern (case-insensitive) | Reaktion bei Verstoss |
|--------|---------------------------|----------------------|
| Co-Authored-By Trailer | `co-authored-by:` | KRITISCH: Zeile entfernen |
| Co-Author Variante | `co-author:` | KRITISCH: Zeile entfernen |
| Anthropic-Erwaehnung | `anthropic` | KRITISCH: Manuell pruefen |
| Claude als Co-Author | `claude` im Trailer-Kontext | KRITISCH: Zeile entfernen |

**Pruef-Befehl (stage_orchestrate intern):**
```bash
git log --format="%B" | grep -i "co-authored-by\|co-author:\|anthropic"
```

---

## 3. Korrektur-Prozedur

**Modus-Quelle (PFLASTER 2026-06-11, BL-295 AK-5 — Live-Bug DCSRE-1944):** Ob die Korrektur
im HiL- oder Dark-Factory-Modus laeuft, entscheidet AUSSCHLIESSLICH der `hil`-Param
(Session-Params via BL-174-Resolver: `py -3 .claude/scripts/session_params_resolver.py resolve
--param=hil --bl-id={BL_ID}`; Fallback `{VAULT}/_session_params.md` **HiL:**). `GLOBAL_MODUS` ist
KEIN HiL-Proxy mehr (PL-S2-06: BDF/Modus und HiL sind ORTHOGONAL). `hil=off` ⇒ Dark-Factory-Pfad
(autonom, KEIN Go-Gate) — fuer small_dark_factory UND big_dark_factory. Der alte Check erkannte
nur `small_dark_factory`; `big_dark_factory` fiel faelschlich in den HiL-Zweig → „Go?"-Gate trotz
hil=off.

### 3.1 HiL-Modus (Normal — `hil` != off)

1. Verstoesse anzeigen: Hash, Message-Ausschnitt, Verstoss-Typ, Schwere
2. User-Frage: "Commit korrigieren? (ja/nein/abbruch)"
3. Bei `ja`: Korrektur-Vorschlag anzeigen, User bestaetigt
4. Bei `nein`: Commit bleibt unveraendert → stage_gate_status=FAIL
5. Bei `abbruch`: Command stoppt, kein Manifest-Update

### 3.2 Dark Factory Modus (`hil` = off — gilt fuer small UND big_dark_factory)

1. Alle KRITISCH-Verstoesse autonom korrigieren
2. Kein HiL, keine Bestaetigung
3. Rebase-Script (Option C) fuer mehrere Commits:
   ```bash
   # Letzter Commit:
   git commit --amend --message "BRANCH: Korrigierter Titel" --no-edit

   # Mehrere Commits (non-interaktiv):
   GIT_SEQUENCE_EDITOR="sed -i 's/pick/reword/g'" git rebase -i BASE_BRANCH
   ```
4. Bei Rebase-Konflikt: FAIL-Status, HiL anfordern (kein stilles Fehlschlagen)

### 3.3 Gemeinsame Nachbedingungen (beide Modi)

- Kein Commit mit Co-Autor-Signatur im Branch
- `stage_gate_status` in Manifest gesetzt (PASS / FAIL / CORRECTED)
- Report in `.claude/analysis/findings/` geschrieben

---

## 4. Geheimhaltungs-Filter

stage_orchestrate prueft AUSSCHLIESSLICH Produkt-Commits (Feature-Branch Commits).

**Filter-Regeln:**
- `.claude/commands/*.md` Dateien werden NICHT geprueft
- `.claude/analysis/` Pfade werden NICHT in Commit-Messages geschrieben
- K-R4: OmniCommand-Existenz darf nicht in git-History erscheinen
