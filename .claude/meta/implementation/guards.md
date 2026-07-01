# I-Pipeline Guards (Pre-Pipeline Checks)

**Quelle:** Extrahiert aus `_I_orchestrate.md` v3.2 → v3.3 (Decomposition)
**Geladen von:** Team Lead vor Pipeline-Start (Schritt 0)

---

## G-SESSION-INIT (Stale-Task-Cleanup, F06-Guard, W162)

**Zweck:** Erkennt und bereinigt stale `in_progress` Tasks aus einer vorangegangenen abgebrochenen Session.

```
G-SESSION-INIT Algorithmus:

1. TaskList aufrufen → alle Tasks lesen
2. Gibt es Tasks mit status=in_progress?
   → NEIN: Keine stale Tasks → WEITER zu naechstem Guard
   → JA: Pruefe ob laufendes Team vorhanden

3. Laufendes Team erkennbar (SendMessage-Partner erreichbar)?
   → JA:  HiL: "Bestehendes Team mit offenen Tasks gefunden. Fortsetzen? (j/n)"
          → j: WEITER (Team-Resume Modus)
          → n: ABBRUCH
   → NEIN: Auto-Cancel (Schritt 4)

4. Auto-Cancel:
   → Logge: "G-SESSION-INIT: {N} stale in_progress Tasks gefunden."
   → Fuer jeden in_progress Task:
     TaskUpdate(taskId=..., status="completed",
       subject="[STALE-CANCELLED] {original_subject}")
   → Logge: "SESSION_RESUME: Stale Tasks bereinigt, starte neu."
```

**Schutz:** Nur `in_progress` Tasks werden gecancelt. Pending Tasks bleiben unberuehrt.

---

## G-DARK-FACTORY-READY (RF-DF-001, RF-DF-002)

**Zweck:** Prueft VOR dem Dark-Factory-Start (hil=off / vollautonomer Betrieb) ob der
Mindest-Kontext vollstaendig geladen ist. Verhindert autonome Laeufe ohne ausreichende
Wissensgrundlage (W219).

**Aktivierung:** Nur wenn `GLOBAL_HIL = off` im Manifest (Dark-Factory-Modus).
Bei `GLOBAL_HIL = on` (Standard): Guard SKIP (PASS automatisch).

```
G-DARK-FACTORY-READY Algorithmus:

1. Pruefe GLOBAL_HIL aus Manifest:
   → GLOBAL_HIL != "off" → SKIP (PASS, normaler Betrieb mit HiL)
   → GLOBAL_HIL == "off" → Guard ausfuehren (vollautonomer Modus)

2. Kontext-Checkliste pruefen (RF-DF-002: vollstaendiger Mindest-Kontext):

   MINDEST-DATEIEN (Pre-Load Checkliste):
   ┌─────────────────────────────────────────────────────────────────┐
   │ WAS (Feature-Wissen):                                           │
   │   [?] .claude/models/{NAME}_Model.md                           │
   │       → Existiert + nicht leer (>50 Zeilen)                    │
   │   [?] .claude/analysis/synthese/{NAME}-SPEC.md  (optional v3+) │
   │                                                                 │
   │ WIE (Pattern Library + Metadaten):                              │
   │   [?] .claude/patterns/_pl-index.md             (PL-Index)     │
   │   [?] .claude/meta/implementation/ (mind. 1 Datei existiert)   │
   │   [?] .claude/meta/codeKonvention/ (mind. 3 Dateien: naming,   │
   │        cleanup, architektur)                                    │
   │   [?] .claude/meta/architekturKonventionen/ (mind. 1 be-*.md)  │
   │                                                                 │
   │ PIPELINE-VORBEREITUNG:                                          │
   │   [?] {VAULT}/Task.md                                            (Task-Def.)    │
   │   [?] .claude/analysis/synthese/{NAME}-ARCHITECT.md (Blueprint) │
   └─────────────────────────────────────────────────────────────────┘

3. Pruefe jede Datei/Verzeichnis: existiert? nicht leer?
   Sammle fehlende Eintraege in MISSING_LIST

4. Ergebnis:
   MISSING_LIST leer:
     → DARK_FACTORY_READY = true
     → Manifest schreiben: dark_factory_ready = true, dark_factory_checked_at = {DATUM}
     → Logge: "G-DARK-FACTORY-READY: PASS — Kontext vollstaendig"
     → WEITER mit naechstem Schritt

   MISSING_LIST nicht leer:
     → WARNUNG ausgeben (KEIN harter Abbruch — Graceful Degradation):
     → "G-DARK-FACTORY-READY: WARN — Fehlende Mindest-Dateien:"
       [Fuer jede fehlende Datei:]
       "  FEHLT: {PFAD}"
     → "Dark-Factory-Modus eingeschraenkt. Betroffene Slices koennen blockieren."
     → Manifest schreiben: dark_factory_ready = false, dark_factory_missing = [LISTE]
     → WEITER (kein Stopp — User hat hil=off bewusst gesetzt)
```

**Invariante:** Guard laeuft NUR einmal pro Session (Manifest dark_factory_checked_at verhindert
Mehrfach-Ausfuehrung nach /compact). Falls dark_factory_checked_at gesetzt → SKIP.

---

## Entity-Readiness-Check (W97, OP-5)

**Zweck:** Verhindert vollstaendige Pipeline-Abbrueche durch fehlende Entities.
DCSRE-93 I-Pipeline v1: 100% Artefakte verschwendet weil VersorgungsvertragEntity.cs
aus DCSRE-1212 noch nicht existierte. Ein 2-3 Min haiku-Check haette das verhindert.

**Wann:** VOR Pipeline-Start, NACH Model+Task-Pruefung (Schritt 0.2).

**Aktion:**

```
Team Lead spawnt 1 haiku-Agent (sc-entity-check):

Du bist ein Entity-Readiness-Checker.

═══ DEIN AUFTRAG ═══

Pruefe ob alle Entities aus dem ARCHITECT-Scope im Code existieren.

═══ SCHRITTE ═══

1. Lies .claude/models/{NAME}_Model.md
   → Extrahiere alle referenzierten Entities (Klassen, Dateien, DB-Tabellen)
2. Lies {VAULT}/Task.md
   → Extrahiere Scope-Dateien und Abhaengigkeiten
3. Pruefe fuer JEDE referenzierte Entity:
   a) Existiert die Datei? (Glob-Suche)
   b) Ist die Klasse compilierbar? (Grundstruktur vorhanden)
   c) Sind referenzierte Navigation-Properties vorhanden?
4. Erstelle Entity-Readiness-Report

═══ OUTPUT FORMAT ═══

CLEAR:   Alle Entities vorhanden → Pipeline kann starten
BLOCKED: {N} Entities fehlen → Liste mit Blockern

Sende Ergebnis an Team Lead.
```

**Auswertung durch Team Lead:**

```
Falls CLEAR:
  → Weiter mit Schritt 0.5 (Manifest initialisieren)
  → Manifest: entity_readiness=CLEAR

Falls BLOCKED:
  → STOPP mit konkretem Blocker-Bericht
  → AskUserQuestion:
    "Entity-Readiness-Check FEHLGESCHLAGEN. {N} Entities fehlen:
     {blocker_liste}
     Optionen:
     A) WARTEN  → Pipeline stoppt. Entity zuerst erstellen/mergen, dann neu starten.
     B) SCOPE-AENDERN → Entity aus Scope entfernen, Pipeline mit reduziertem Scope starten.
     C) FORCE   → Auf eigenes Risiko starten. Manifest: entity_readiness=OVERRIDE"
```

---

## pipeline_mode State Machine (EC-4, EC-5, W200)

**Zweck:** Pre-Check ob I-Pipeline starten darf, basierend auf SC-Phase-Status.

| pipeline_mode | Bedeutung | Aktion |
|---------------|-----------|--------|
| `READY_FOR_I` | SC-Gate PASS + Finale Verifikation OK | I-Pipeline startet normal (scope_mode=full) |
| `SC_SYMBIOSE_I_ACTIVE` | SC⟲I Symbiose: SC ruft I im Core-Modus | I-Pipeline startet mit scope_mode=core (Schritte 0-8, dann EXIT) |
| `pending_approval` | TIER-1+2 OK, HiL-Signatur ausstehend | HiL-Warnung: Frage User ob Fortfahren |
| `POST_CYCLE` | SC-Phase laeuft noch (POST-CYCLE aktiv) | STOPP: "POST-CYCLE noch aktiv." |
| `POST_CYCLE_RETRY` | Gate FAIL — SC muss weiterlaufen | STOPP: "SC-Gate FAILED." |
| `SC_RECOVERY` | I→SC-Rueckkehr laeuft | STOPP: "SC-Recovery laeuft." |
| `SC` | SC noch aktiv | STOPP: "SC-Phase noch nicht abgeschlossen." |
| (kein pipeline_mode) | Kein SC-Vorzyklus oder altes Manifest | Graceful Degradation: Weiter (scope_mode=full) |

```
Auswertungslogik:

pm = manifest.get("pipeline_mode", None)

IF pm == "READY_FOR_I":
  scope_mode = "full"
  i_gate_response.i_decision = "accept_start"
  Logge: "pipeline_mode=READY_FOR_I bestaetigt. I-Pipeline berechtigt (scope_mode=full)."

ELIF pm == "SC_SYMBIOSE_I_ACTIVE":
  scope_mode = "core"
  i_gate_response.i_decision = "accept_start_core"
  Logge: "pipeline_mode=SC_SYMBIOSE_I_ACTIVE erkannt. Core-Modus (Schritte 0-8)."

ELIF pm == "pending_approval":
  AskUserQuestion(
    "SC-Gate ausstehend (pipeline_mode=pending_approval). "
    + "TIER-3 HiL-Signatur noch nicht gesetzt. Fortfahren? (j=Ja, n=STOPP)")
  → j: weiter (User uebernimmt Verantwortung)
  → n: STOPP

ELIF pm IN ["POST_CYCLE", "POST_CYCLE_RETRY", "SC_RECOVERY", "SC"]:
  AUSGABE: "STOPP: pipeline_mode={pm}. I-Pipeline darf nicht starten."
  i_gate_response:
    i_decision: reject_needs_more_sc
    rejection_reason: "pipeline_mode={pm} — SC nicht abgeschlossen"
  → Manifest updaten + HARD STOP

ELIF pm IS None:
  scope_mode = "full"
  Logge: "pipeline_mode nicht im Manifest — Graceful Degradation (scope_mode=full)."
```

Schreibe nach Pre-Check in Manifest (bei READY_FOR_I, SC_SYMBIOSE_I_ACTIVE oder None/Graceful):
  pipeline_mode: I_RUNNING
  i_gate_response: ACKNOWLEDGED
