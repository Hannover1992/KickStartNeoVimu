---
type: building-block
---

# /_W_push_global

**Status:** v1.0 (Quality Gate + Dual-Push)
**Actor:** KNOWLEDGE-GATEKEEPER
**Zweck:** Verifiziertes Wissen nach Feature-Ende global pushen (RAG + Vault mit Quality Gate)
**Basis:** WissensPipeline-GAP.md (GAP-003, GAP-005)

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_W_push_global {DOCUMENT}                           |
+===============================================================+
|                                                                |
|  KERN-PROBLEM:                                                 |
|    Am Feature-Ende liegen Models und Wissen in .claude/       |
|    Nicht alles ist verifiziert — manche W{n} sind WIDERLEGT.  |
|    Temporäres RAG (local_knowledge_*) ist Feature-isoliert.   |
|    Kein Mechanismus für Quality-geprüften Global-Push.        |
|                                                                |
|  KERN-PRINZIP:                                                 |
|    Quality Gate BEFORE Push:                                   |
|    → W{n}-Status prüfen (BESTÄTIGT vs WIDERLEGT)              |
|    → User-Approval für Dokumente ohne W{n}                    |
|    → Dual-Push: RAG (global_knowledge) + Vault (optional)     |
|    "Only verified knowledge goes global."                      |
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. {DOCUMENT} (Pfad relativ zu .claude/ oder absolut)      |
|       → Dokument validieren (existiert, .md, erlaubter Ordner)|
|    2. {VAULT}/_manifest.md                            |
|       → NAME-Feld für Feature-ID (für Log)                     |
|    3. {DOCUMENT} Inhalt (für Quality Gate):                    |
|       → W{n}-Referenzen extrahieren                            |
|       → Status-Prüfung (BESTÄTIGT, ZUR PRÜFUNG, WIDERLEGT)    |
|                                                                |
|  LIEST OPTIONAL (Vault + Routing):                              |
|    4. .claude/config/vault-routing.json (Kategorie-Routing)    |
|       → Bestimmt Vault-Pfad + globale RAG-Collection           |
|       → 3 Kategorien: DCS, CenCoCo, Brain                     |
|    5. $OBSIDIAN_VAULT_PATH Environment Variable (Fallback)     |
|       → Falls vault-routing.json fehlt: Env-Var als Fallback  |
|       → Falls beides fehlt: Nur RAG-Push (degraded mode)      |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. RAG Collection: {GLOBAL_RAG aus vault-routing.json}      |
|       → DCS-Projekte: global_knowledge                        |
|       → CenCoCo-Projekte: global_knowledge_cencoco            |
|       → Brain-Projekte: global_knowledge_brain                 |
|       → Via MCP create_collection() + ingest()                 |
|    2. {VAULT}/_manifest.md:                           |
|       → "## Quality Gate Log" Sektion                          |
|       → "## RAG Push Status" Sektion (Status: GLOBAL)          |
|                                                                |
|  MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):               |
|    Pattern C: Protokoll-Only-Write + State-Einzeiler           |
|    SCHREIBT PROTOKOLL: Quality-Gate-Log + RAG-Push-Log         |
|      vollstaendig (Prepend → _manifest_protokoll.md)           |
|    SCHREIBT STATE: W_PUSH_STATUS-Einzeiler in _manifest.md     |
|    SCHREIBT NICHT: Detaillierte Logs in _manifest.md           |
|      (nur W_PUSH_STATUS-Einzeiler)                             |
|                                                                |
|  SCHREIBT OPTIONAL (Vault):                                    |
|    3. {VAULT}/{DOKUMENT_NAME} (mit Frontmatter)                |
|       → Frontmatter-Header: source, pushed_global, W{n}-count  |
|       → Nur falls Vault konfiguriert + erreichbar              |
|                                                                |
|  SCHREIBT NICHT:                                               |
|    - Keine local_knowledge_* Collections (das macht W_push_temp)|
|    - Kein .claude/ Dokument-Modifikation (nur LESEN)           |
|                                                                |
|  PIPELINE:                                                     |
|    [Feature-Ende] → [/_W_push_global {MODELS}] →               |
|    [/_W_push_global {WISSEN}] → [/_W_push_global {OBSERVE}]    |
|    (Nach Feature-Abschluss, selektiv pro Dokument)            |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**KNOWLEDGE-GATEKEEPER:** Bewacht den Zugang zu global_knowledge mit Quality Gate.

**TUT:** Quality Gate prüfen (W{n}-Status), User-Approval einholen, RAG global pushen, optional Vault pushen, Manifest dokumentieren.

**NICHT:** Dokumente ohne Gate pushen, unverifiziertes Wissen global machen, Quality Gate umgehen, W{n}-Status ignorieren.

---

## Schritt 0: Feature-ID extrahieren

```
1. Lies {VAULT}/_manifest.md
2. Extrahiere NAME-Feld (erste Zeile mit "**NAME:**")
   → Beispiel: **NAME:** TwoTierBridge → Feature-ID = "twotierbridge"

3. Sanitize Feature-ID:
   → Lowercase
   → Leerzeichen → Underscore
   → Sonderzeichen entfernen (nur a-z, 0-9, _ erlaubt)

AUSGABE:
  "Feature: {NAME} (ID: {feature_id})"
```

---

## Schritt 1: Dokument validieren

```
Prüfe {DOCUMENT}:

  1. Pfad validieren:
     → Relativer Pfad zu .claude/? → Absolut machen
     → Absoluter Pfad? → Prüfen ob in .claude/
     → Beispiel: "models/Model.md" → ".claude/models/Model.md"

  2. Datei-Checks:
     a) Existiert die Datei?
        → NEIN: FEHLER "Dokument nicht gefunden: {DOCUMENT}"
        → ABBRUCH

     b) Dateiendung = .md?
        → NEIN: FEHLER "Nur .md Dateien unterstützt. Erhalten: {EXT}"
        → ABBRUCH

     c) Ordner erlaubt? (GAP-003 SOLL)
        ERLAUBT (Wissens-Charakter):
          → .claude/models/          (technische Models mit W{n})
          → .claude/wissen/           (erklärende Wissens-Dokumente)
          → .claude/specs/            (Spezifikationen)
          → .claude/analysis/synthese/ (OBSERVE, ERGEBNIS, HYPOTHESEN, GAP, QUALITYGATE)

        NICHT ERLAUBT (temporär/roh):
          → .claude/crumbs/           (Rohdaten, unsortiert)
          → .claude/analysis/drafts/  (Zwischen-Entwürfe)
          → .claude/temp/             (temporäre Dateien)
          → .claude/commands/         (Code, kein Wissen)
          → .claude/presentation/     (Präsentation, nicht Wissen)

        → NICHT ERLAUBT: FEHLER "Ordner {ORDNER} ist nicht für Global-Push vorgesehen.
                                 Erlaubt: models/, wissen/, specs/, analysis/synthese/"
        → ABBRUCH

  3. Bereits global gepusht? (Manifest-Check)
     → Prüfe Manifest "## RAG Push Status" Sektion
     → Falls DOCUMENT mit Status "GLOBAL" gelistet:
       WARNUNG: "Dokument bereits global gepusht am {DATUM} ({CHUNKS} chunks).
                 Erneuter Push erzeugt Duplikate in global_knowledge.
                 Fortfahren? (j/n)"
       → User entscheidet

AUSGABE:
  "Dokument validiert: {DOCUMENT} ({ZEILEN} Zeilen, Ordner: {ORDNER})"
```

---

## Schritt 2: Quality Gate — W{n}-Status prüfen

```
**KERN:** GAP-005 Quality Gate Logik (P1)

Lies {DOCUMENT} Inhalt:

  1. W{n}-Referenzen extrahieren:
     → Regex-Pattern: \bW\d+\b (z.B. "W1", "W12", "W3")
     → Alle Matches sammeln
     → Deduplizieren (W1 kann mehrfach vorkommen)

  2. Status-Suffixe erkennen:
     Für jedes W{n}:
       → Suche nach Status-Keyword (case-insensitive):
         - "BESTÄTIGT" / "CONFIRMED" / "VERIFIED" → Status = BESTÄTIGT
         - "ZUR PRÜFUNG" / "TO_REVIEW" / "PENDING" → Status = ZUR_PRÜFUNG
         - "WIDERLEGT" / "REFUTED" / "DISPROVEN" → Status = WIDERLEGT
         - "OFFEN" / "OPEN" → Status = OFFEN
       → Falls kein Status gefunden: Status = UNBEKANNT

  3. Statistik erstellen:
     → BESTÄTIGT: N1 W{n}
     → ZUR_PRÜFUNG: N2 W{n}
     → WIDERLEGT: N3 W{n}
     → OFFEN: N4 W{n}
     → UNBEKANNT: N5 W{n}
     → GESAMT: N = N1 + N2 + N3 + N4 + N5

  4. Quality Gate Entscheidung (GAP-005 SOLL):

     a) Falls N = 0 (kein W{n} im Dokument):
        → Dokument-Typ prüfen:
          - *_Wissen.md oder *-OBSERVE*.md → ERLAUBT (erklärendes Wissen)
          - *_Model.md → WARNUNG "Model ohne W{n} ist ungewöhnlich"
        → FRAGE User:
          "Dieses Dokument hat keine W{n}-Referenzen.
           Es handelt sich um erklärendes Wissen ohne verifizierte Wahrheiten.
           Trotzdem global pushen? (j/n)"
        → User entscheidet (j = PASS, n = REJECT)

     b) Falls N3 > 0 (WIDERLEGT W{n} vorhanden):
        → KRITISCH: Liste alle WIDERLEGT W{n}
        → WARNUNG:
          "Dokument referenziert {N3} widerlegte Wahrheit(en): {W_LISTE}
           Diese sollten vor Global-Push entfernt oder korrigiert werden.
           Fortfahren? (j/n/edit)"
        → User-Optionen:
          - j = PASS (trotzdem pushen, mit Log-Eintrag)
          - n = REJECT (abbrechen)
          - edit = PAUSE (User korrigiert Dokument, Command neu starten)

     c) Falls N1 >= 1 UND N3 = 0 (mindestens 1 BESTÄTIGT, keine WIDERLEGT):
        → AUTO-PASS
        → AUSGABE: "Quality Gate: PASS ({N1} BESTÄTIGT, {N2} ZUR_PRÜFUNG, {N4} OFFEN)"

     d) Falls N1 = 0 UND N3 = 0 (nur ZUR_PRÜFUNG/OFFEN/UNBEKANNT):
        → FRAGE User:
          "Dokument hat {N2} ZUR_PRÜFUNG, {N4} OFFEN, {N5} UNBEKANNT W{n}.
           Keine bestätigten Wahrheiten.
           Global pushen? (j/n)"
        → User entscheidet

  5. Gate-Ergebnis:
     → PASS: Weiter zu Schritt 3
     → REJECT: ABBRUCH mit "Quality Gate: REJECT — Dokument nicht gepusht"

AUSGABE:
  "Quality Gate: {ERGEBNIS}"
  "W{n}-Status: {N1} BESTÄTIGT, {N2} ZUR_PRÜFUNG, {N3} WIDERLEGT, {N4} OFFEN, {N5} UNBEKANNT"
  Falls REJECT:
    "Grund: {GRUND}"
```

---

## Schritt 2b: Vault-Routing laden (Kategorie-Erkennung)

```
  CONFIG_PATH = ".claude/config/vault-routing.json"

  IF CONFIG_PATH existiert:
    routing = JSON.parse(CONFIG_PATH)
    cwd = aktueller Pfad (pwd)

    # Pattern-Matching (nach Prioritaet sortiert)
    FUER JEDE rule IN routing.detection.rules (sortiert nach priority):
      IF cwd CONTAINS rule.pattern (case-insensitive):
        MATCHED_RULE = rule
        GLOBAL_RAG = rule.rag_collections[0]  # Erste Collection = globale
        VAULT_NAME = rule.vault
        VAULT_PATH = routing.vaults[VAULT_NAME].windows_path
        BREAK

    Logge: "Vault-Routing: Pattern={MATCHED_RULE.pattern}, Vault={VAULT_NAME}, RAG={GLOBAL_RAG}"

  ELSE:
    # Fallback: kein Routing → Default global_knowledge
    GLOBAL_RAG = "global_knowledge"
    VAULT_PATH = $OBSIDIAN_VAULT_PATH ?? null
    Logge WARNUNG: "vault-routing.json nicht gefunden → Fallback: global_knowledge"
```

---

## Schritt 3: RAG Push ({GLOBAL_RAG})

```
Nach Quality Gate PASS:

  1. Collection sicherstellen (idempotent):
     → MCP create_collection(name="{GLOBAL_RAG}")
     → Return: {"status": "created"|"exists", "collection": "{GLOBAL_RAG}", "count": int}
     → AUSGABE: "Collection: {GLOBAL_RAG} (Status: {STATUS}, Docs: {COUNT})"

  2. Absoluten Pfad ermitteln:
     → Falls relativ zu .claude/: Absolut machen
     → Beispiel: "models/Model.md" → "/abs/path/.claude/models/Model.md"

  3. MCP ingest aufrufen:
     → MCP ingest(
         file_path="{ABSOLUTER_PFAD}",
         collection="{GLOBAL_RAG}",
         options=None
       )
     → Return: {
         "status": "completed"|"failed",
         "document_id": str,
         "file_path": str,
         "collection": str,
         "stages_completed": list[str],
         "chunks_created": int,
         "total_duration_seconds": float,
         "error": str|None
       }

  4. Ergebnis auswerten:
     a) status = "completed":
        → AUSGABE: "[RAG OK] global_knowledge → {chunks_created} chunks in {duration}s"
        → RAG_SUCCESS = True

     b) status = "failed":
        → FEHLER: "[RAG FAIL] Ingest fehlgeschlagen: {error}"
        → RAG_SUCCESS = False
        → FRAGE User: "RAG-Push fehlgeschlagen. Vault-Push trotzdem versuchen? (j/n)"
        → Falls n: ABBRUCH

  5. RAG-Push-Metadaten sammeln:
     → document_id, chunks_created, duration
```

---

## Schritt 4: Vault Push (optional)

```
**OPTIONAL:** Nur falls Vault konfiguriert (GAP-005, GAP-006)

  1. Vault-Verfügbarkeit prüfen:
     a) Environment Variable $OBSIDIAN_VAULT_PATH gesetzt?
        → NEIN: SKIP Vault-Push (degraded mode)
          AUSGABE: "[VAULT SKIP] $OBSIDIAN_VAULT_PATH nicht gesetzt. Nur RAG-Push."
        → JA: Weiter zu 1b

     b) Vault-Pfad existiert und ist beschreibbar?
        → Bash: test -d "$OBSIDIAN_VAULT_PATH" && test -w "$OBSIDIAN_VAULT_PATH"
        → NEIN: SKIP Vault-Push mit Warnung
          WARNUNG: "[VAULT SKIP] Pfad nicht erreichbar: $OBSIDIAN_VAULT_PATH"
        → JA: Weiter zu 2

  2. Frontmatter-Header generieren:
     ```yaml
     ---
     source: .claude/{ORDNER}/{DOKUMENT_NAME}
     feature: {FEATURE_NAME}
     pushed_global: {DATUM}
     rag_collection: global_knowledge
     rag_document_id: {document_id}
     rag_chunks: {chunks_created}
     quality_gate: PASS
     w_count: {N}
     w_confirmed: {N1}
     w_refuted: {N3}
     ---
     ```

  3. Dokument mit Frontmatter kopieren:
     → Ziel-Pfad: {VAULT}/{DOKUMENT_NAME}
     → Falls Dokument bereits existiert:
       FRAGE: "{DOKUMENT_NAME} existiert bereits im Vault. Überschreiben? (j/n)"
       → User entscheidet

     → Linux: cat Frontmatter + Dokument > {VAULT}/{DOKUMENT_NAME}
     → Windows: PowerShell Get-Content | Set-Content

  4. Ergebnis:
     a) Erfolg:
        → AUSGABE: "[VAULT OK] {VAULT}/{DOKUMENT_NAME} geschrieben"
        → VAULT_SUCCESS = True

     b) Fehler:
        → WARNUNG: "[VAULT FAIL] Kopieren fehlgeschlagen: {error}"
        → VAULT_SUCCESS = False
        → RAG-Push bleibt gültig (nicht rückgängig machen)
```

---

## Schritt 4b: BL-242-Index-Refresh (BL-275 AK-S1 — Forward Write→Index-Seam)

```
**ZWECK (BL-275 „ab-jetzt-sauber"):** Sobald ein Dokument als Vault-Knoten landet (VAULT_SUCCESS),
den vorab gebauten BL-242-Schnell-Index (keyword/edge/anchor/backlinks-JSON + _Tag-Index.md) auffrischen.
Sonst veraltet der Index ab dem ersten Write → _W_fetch Schritt 0d (Index-First-Read, BL-242 AK-5) findet
den neuen Knoten NICHT im Schnell-Pfad (faellt auf RAG/Laufzeit-Walk zurueck = weiterhin findbar, nur langsam).

**GRANULARITAET (Design-Resolution BL-275):** Die Naht sitzt bewusst HIER (Feature-Ende, pro gepushtem
Dokument — selten), NICHT in _W_push_temp (kein Vault-Knoten) und NICHT pro einzelnem Truth-Write (das waere
der „staendige teure Reindex", den BL-275 vermeiden will). Bei dieser Granularitaet ist der aktuelle
Full-Rebuild-`--incremental` kostentragbar.

  IF VAULT_SUCCESS == True:
    rel = "{DOKUMENT_NAME}"   # geschrieben unter {VAULT}/{DOKUMENT_NAME}; relativ zum Vault-Root
    Bash("py -3 .claude/scripts/build_retrieval_index.py --incremental --path={rel}")
      → exit 0:    "[INDEX OK] BL-242-Index aufgefrischt fuer {rel} (Schnell-Pfad fuer _W_fetch Schritt 0d)"
      → exit != 0: WARNUNG "[INDEX SKIP] Refresh fuer {rel} fehlgeschlagen (Pfad nicht im Vault /
                   Resolver-Mismatch / Build-Fehler) — _W_fetch nutzt RAG/Walk-Fallback (KEIN
                   Korrektheits-Verlust). Bulk-Catch-up via Reindex (BL-274) moeglich."
    # NON-BLOCKING: ein Refresh-Fehler nimmt den erfolgreichen RAG/Vault-Push NICHT zurueck.
  ELSE:
    Logge: "[INDEX SKIP] VAULT_SUCCESS=False (RAG-only-Modus) → kein Vault-Knoten, kein Index-Refresh noetig."

# Resolver-Alignment: build_retrieval_index nutzt resolve_vault_root() als Root. Bei DCS/CenCoCo/Brain ==
# vault-routing.json VAULT_PATH (derselbe Vault). Bei Abweichung greift der graceful Skip oben (kein Hard-Fail).
# Optimierung (Folge-Sub-AK, optional): patch_index (build_retrieval_index.py:174) statt Full-Rebuild in die
# --incremental-CLI verdrahten → O(1)-Patch des persistierten JSON statt Re-Walk. Bei Feature-Ende-Granularitaet
# NICHT erforderlich; erst relevant falls Feature-Ende-Rebuilds zum Bottleneck werden. [BL-275 AK-S1]
```

---

## Schritt 5: Manifest aktualisieren

```
In {VAULT}/_manifest.md:

  1. Sektion "## Quality Gate Log" (GAP-008):
     → Falls nicht vorhanden: Sektion NEU erstellen (APPEND am Ende)

     Template:
     ```
     ## Quality Gate Log

     **Feature:** {FEATURE_NAME}
     **Letztes Gate:** {DATUM}

     | Dokument | W{n} Status | Gate-Ergebnis | Datum |
     |----------|-------------|---------------|-------|
     ```

     Neue Zeile:
     | {DOKUMENT_NAME} | {N1}B / {N3}W / {N2}P / {N4}O | {PASS|REJECT} | {DATUM} |

     Legende: B=BESTÄTIGT, W=WIDERLEGT, P=ZUR_PRÜFUNG, O=OFFEN

  2. Sektion "## RAG Push Status" (GAP-008):
     → Falls nicht vorhanden: Sektion NEU erstellen

     Template:
     ```
     ## RAG Push Status

     **Collection:** mixed (local + global)
     **Letzter Push:** {DATUM}

     | Dokument | Collection | Chunks | Datum | Status |
     |----------|-----------|--------|-------|--------|
     ```

     Neue/Update Zeile:
     | {DOKUMENT_NAME} | global_knowledge | {chunks_created} | {DATUM} | GLOBAL |

  3. Optional: Sektion "## Obsidian Sync" aktualisieren:
     → Falls VAULT_SUCCESS = True:
       Bestehende Hash-Tabelle in _W_obsidianSync.md updaten
       (Aber das macht _W_obsidianSync selbst, nicht hier)

AUSGABE:
  "Manifest aktualisiert:"
  "  - Quality Gate Log: {DOKUMENT_NAME} → {GATE_ERGEBNIS}"
  "  - RAG Push Status: {DOKUMENT_NAME} → GLOBAL"
```

---

## Schritt 6: Zusammenfassung

```
AUSGABE:

  "=== Global Push Abgeschlossen ==="
  ""
  "Dokument: {DOCUMENT}"
  "Feature: {FEATURE_NAME}"
  ""
  "Quality Gate:"
  "  Ergebnis: {PASS|REJECT}"
  "  W{n}-Status: {N1} BESTÄTIGT, {N3} WIDERLEGT, {N2} ZUR_PRÜFUNG, {N4} OFFEN"
  ""
  "RAG Push:"
  Falls RAG_SUCCESS:
    "  Collection: global_knowledge"
    "  Document-ID: {document_id}"
    "  Chunks: {chunks_created}"
    "  Dauer: {duration}s"
    "  Status: SUCCESS"
  Falls NOT RAG_SUCCESS:
    "  Status: FAILED ({error})"
  ""
  "Vault Push:"
  Falls VAULT_SUCCESS:
    "  Pfad: {VAULT}/{DOKUMENT_NAME}"
    "  Status: SUCCESS"
  Falls VAULT_SKIP:
    "  Status: SKIPPED (Vault nicht konfiguriert)"
  Falls VAULT_FAIL:
    "  Status: FAILED ({error})"
  ""
  "Manifest:"
  "  Quality Gate Log: ✓"
  "  RAG Push Status: ✓"
  ""
  "Nächste Schritte:"
  "  → /_W_push_global {ANDERES_DOK} (weitere Dokumente global pushen)"
  "  → /_W_fetch (kann jetzt globales Wissen finden)"
  "  → MCP query(collection='global_knowledge', query_text=...)"
```

---

## Abgrenzung

```
/_W_push_global = GLOBALES Pushen (Feature-Ende, MIT Quality Gate)
/_W_push_temp   = TEMPORÄRES Pushen (während Feature, KEIN Quality Gate)
/_W_fetch       = Wissen HOLEN (Vault + RAG → .claude/)
/_W_obsidianSync  = Synthese TRANSPORTIEREN (.claude/ → Vault, ohne RAG)

          Feature-Ende
                ↓
          /_W_push_global {MODEL}
                ↓
          Quality Gate (W{n} prüfen)
                ↓
          PASS → RAG Push (global_knowledge)
                ↓
          PASS → Vault Push (optional)
                ↓
          Manifest Update (Gate Log + RAG Status)
                ↓
          Nächstes Feature
                ↓
          /_W_fetch (findet jetzt globales Wissen)

W_push_global ist GATEKEEPER:
  → Quality Gate IMMER (W{n}-Status prüfen)
  → Dual-Push: RAG (PFLICHT) + Vault (OPTIONAL)
  → Manifest-Dokumentation (Gate Log + RAG Status)
  → Collection: global_knowledge (eine Collection für alles)
  → Nur verifiziertes Wissen

W_push_temp ist SPEED:
  → KEIN Quality Gate (schnell, temporär)
  → NUR RAG Push (local_knowledge_{feature_id})
  → Feature-isoliert (andere Features sehen es nicht)
```

---

## Qualitätskriterien

- Quality Gate ist PFLICHT (nicht optional)
- W{n}-Status-Parsing robust (Regex + Status-Keywords)
- User-Approval bei kritischen Fällen (WIDERLEGT, kein W{n})
- RAG-Push IMMER versuchen (auch wenn Vault fehlschlägt)
- Vault-Push OPTIONAL (degraded mode ohne Vault möglich)
- global_knowledge = eine Collection (nicht pro Feature)
- Manifest NUR bei erfolgreichem RAG-Push aktualisieren
- Frontmatter-Header mit RAG-Metadaten (document_id, chunks, W{n}-count)
- Keine Rollback-Logik (RAG + Vault sind unabhängig)
- Feature-ID aus Manifest (nicht raten)

---

## Fehlerbehandlung

| Fehler | Ursache | Lösung |
|--------|---------|---------|
| Manifest nicht gefunden | _manifest.md fehlt | FEHLER: "Starte mit /_taskDefinition" |
| Dokument nicht gefunden | Pfad falsch | FEHLER mit Pfad-Hinweis |
| Nicht-erlaubter Ordner | crumbs/drafts/temp | FEHLER mit Liste erlaubter Ordner |
| Quality Gate REJECT | WIDERLEGT W{n} oder User-Ablehnung | ABBRUCH mit Grund-Ausgabe |
| RAG-Push fehlschlägt | ChromaDB nicht erreichbar | FEHLER, FRAGE User ob Vault trotzdem |
| Vault nicht konfiguriert | $OBSIDIAN_VAULT_PATH nicht gesetzt | SKIP Vault, NUR RAG (degraded mode) |
| Vault nicht erreichbar | Pfad existiert nicht | WARNUNG, weiter mit RAG-only |
| Duplikat-Warnung | Dokument bereits GLOBAL | WARNUNG, User entscheidet |
| W{n}-Parsing fehlschlägt | Regex-Error | WARNUNG, User-Approval-Fallback |

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (Quality Gate, RAG/Vault Push, Manifest Update, Zusammenfassung):

```bash
# Linux:
echo "/_W_push_global {DOCUMENT} abgeschlossen → global_knowledge"

# Windows:
powershell -Command "notify '{DOCUMENT} global gepusht'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
