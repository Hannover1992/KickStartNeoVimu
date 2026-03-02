# Knowledge → Obsidian Vault Sync (SUPERSEDED)

**HINWEIS:** Dieses Command wurde durch `/_W_obsidianSync` ersetzt.
`/_W_obsidianSync {FEATURE}` synchronisiert ALLE Synthese-Dokumenttypen (Model, Analyse,
Hypothesen, Wissen, Presentation), nicht nur Knowledge.

---

Synchronisiert fertige Wissen-Dokumente aus `.claude/wissen/` in den Obsidian Vault.
Fuegt Obsidian-Syntax hinzu (Frontmatter, Wiki-Links, Callout, Tags) und verlinkt
das Feature-Note bidirektional.

## Aufruf

```
/_knowledgeObsidianSync {FEATURE}
```

- **FEATURE** (Pflicht): Die Feature-ID, z.B. `DCSRE-881`
  Falls nicht angegeben → FRAGE den User nach dem Feature

---

## VERTRAG (Pflicht-I/O)

```
+===============================================================+
|  COMMAND: /_knowledgeObsidianSync {FEATURE}                    |
+===============================================================+
|                                                                |
|  LIEST (Input):                                                |
|    1. .claude/analysis/_manifest.md                            |
|       → Ermittle alle abgeschlossenen Knowledge-Sektionen      |
|    2. .claude/wissen/*_Wissen.md                               |
|       → Die fertigen Wissen-Dokumente (Synthese)               |
|    3. {VAULT}/{FEATURE}.md                                     |
|       → Das Feature-Note im Obsidian Vault                     |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. {VAULT}/{THEMA}_Wissen.md                                |
|       → Vollstaendige Kopie MIT Obsidian-Frontmatter           |
|    2. {VAULT}/{FEATURE}.md                                     |
|       → Wiki-Link [[{THEMA}_Wissen]] in Wissen-Sektion         |
|                                                                |
|  VAULT-PFAD:                                                   |
|    C:\Users\Administrator\Documents\DCS                        |
|    (Obsidian Vault mit .obsidian/ Ordner)                      |
|                                                                |
|  WICHTIG - TECHNISCHE EINSCHRAENKUNGEN:                        |
|    - Wissen-Dateien sind GROSS (500-1100 Zeilen)               |
|    - NICHT mit dem Write-Tool kopieren (haengt sich auf)       |
|    - IMMER PowerShell fuer Datei-Operationen verwenden         |
|    - Frontmatter via .ps1 Temp-Script voranstellen             |
|      (Bash-Heredoc bricht bei Sonderzeichen)                   |
|                                                                |
+===============================================================+
```

---

## OBSIDIAN VAULT KONVENTIONEN

Diese Konventionen wurden aus dem DCS Vault analysiert:

### Frontmatter-Format (YAML)

```yaml
---
id: {Dateiname ohne .md}
aliases:
  - {Alias1}
  - {Alias2}
tags:
  - knowledge
feature: '[[{FEATURE}]]'
---
```

### Tag-Taxonomie (bestehend im Vault)

| Tag | Verwendung |
|-----|-----------|
| `feature` | Haupt-Feature/User-Story Notes (z.B. DCSRE-881.md) |
| `task` | Sub-Tasks und Implementierungs-Aufgaben |
| `knowledge` | Wissens-Referenz-Notizen (UNSER TAG) |
| `crumble` | Breadcrumb/Kontext-Notizen |
| `presentation` | Praesentations-Notizen |
| `RAW` | Rohe Transkriptionen/Voice-Notes |
| `daily` | Tages-Notizen (Daily/ Ordner) |

### Linking-Konventionen

- **Wiki-Links:** `[[Note Name]]` (Obsidian Standard)
- **Callout-Boxen:** `> [!info]`, `> [!warning]`, `> [!tip]`
- **Feature-Notes** haben Sektionen: `# US`, `# Crummel`, `# Task`, `# Wissen`, `# Model`, `# Presentation`, `# Analyse`
- **Knowledge-Links** gehoeren in die `# Wissen` Sektion des Feature-Notes

### Feature-Note Struktur (Beispiel DCSRE-881.md)

```markdown
---
id: DCSRE-881
aliases: []
tags:
  - feature
---

# US
https://projekte.itsg.de/browse/DCSRE-881 #story

# Crummel:
[...]

# Task:
- [x] [[Task1]]
- [ ] [[Task2]]

# Wissen            ← HIER werden Knowledge-Links eingefuegt
[[WSDL]]
[[Zertifikate_Wissen]]     ← von diesem Command eingefuegt

# Model
# Presentation
# Analyse
```

---

## ABLAUF

### Schritt 0: Manifest lesen + Wissen-Dateien finden

```
1. Lies .claude/analysis/_manifest.md
2. Finde alle "Knowledge: {THEMA}" Sektionen mit Status "abgeschlossen"
3. Finde die zugehoerigen .claude/wissen/{THEMA}_Wissen.md Dateien
4. Pruefe: Existiert die Datei? Ist sie nicht leer?
5. Falls KEINE abgeschlossenen Knowledge-Dateien:
   → FEHLER: "Keine fertigen Wissen-Dokumente gefunden.
              Fuehre zuerst /_knowledge {THEMA} hard aus."
```

### Schritt 1: Vault verifizieren

```
1. Pruefe ob der Vault-Pfad existiert:
   C:\Users\Administrator\Documents\DCS
2. Pruefe ob .obsidian/ Ordner existiert (= ist ein Obsidian Vault)
3. Pruefe ob {FEATURE}.md im Vault existiert
4. Falls {FEATURE}.md nicht existiert:
   → FRAGE: "Feature-Note {FEATURE}.md existiert nicht im Vault.
             Soll ich es erstellen?"
```

### Schritt 2: Fuer jedes {THEMA}_Wissen.md → In Vault kopieren

**WICHTIG: PowerShell verwenden, NICHT Write-Tool!**

```
Fuer jedes {THEMA}_Wissen.md:

  1. KOPIERE die Datei mit PowerShell:
     powershell -Command "Copy-Item '{QUELLE}' '{VAULT}\{THEMA}_Wissen.md'"

  2. ERSTELLE ein Temp-PowerShell-Script fuer den Header:
     Schreibe eine .ps1 Datei die:
     a) Den Obsidian-Frontmatter-Header definiert:
        ---
        id: {THEMA}_Wissen
        aliases:
          - {ALIAS1 aus dem Thema abgeleitet}
          - {ALIAS2}
          - {THEMA}
        tags:
          - knowledge
        feature: '[[{FEATURE}]]'
        ---

        > [!info] Feature-Kontext
        > Diese Knowledge-Notiz gehoert zu [[{FEATURE}]] ({Feature-Beschreibung}).
        > Erstellt via /_knowledge {THEMA} hard (3-Wellen Feynman-Methode).

     b) Die bestehende Datei liest
     c) Header + Inhalt zusammenfuegt
     d) Mit UTF8 speichert

  3. FUEHRE das Script aus:
     powershell -ExecutionPolicy Bypass -File "{VAULT}\prepend-header.ps1"

  4. LOESCHE das Temp-Script:
     powershell -Command "Remove-Item '{VAULT}\prepend-header.ps1'"

  5. VERIFIZIERE:
     - Datei existiert im Vault
     - Frontmatter ist korrekt (erste Zeile = "---")
     - Zeilenanzahl = Original + Header-Zeilen
```

### Schritt 3: Feature-Note verlinken

```
1. Lies {VAULT}/{FEATURE}.md
2. Finde die "# Wissen" Sektion
3. Pruefe ob [[{THEMA}_Wissen]] bereits verlinkt ist
4. Falls NICHT verlinkt:
   → Fuege [[{THEMA}_Wissen]] unter der "# Wissen" Sektion hinzu
     (nach den bestehenden Links)
5. Falls bereits verlinkt:
   → SKIP (keine Duplikate)
```

### Schritt 4: Zusammenfassung ausgeben

```
Ausgabe:

  /_knowledgeObsidianSync {FEATURE} - Ergebnis:

  | Wissen-Dokument | Vault-Pfad | Zeilen | Status |
  |-----------------|-----------|--------|--------|
  | {THEMA}_Wissen.md | {VAULT}\{THEMA}_Wissen.md | {N} | Sync OK |

  Feature-Note {FEATURE}.md aktualisiert:
  - [[{THEMA}_Wissen]] in # Wissen Sektion verlinkt

  Obsidian-Zugriff via:
  - [[{THEMA}_Wissen]] (Wiki-Link)
  - [[{ALIAS1}]], [[{ALIAS2}]] (Aliases)
```

---

## ALIAS-ABLEITUNG

Leite aus dem {THEMA} sinnvolle Obsidian-Aliases ab:

| THEMA | Aliases |
|-------|---------|
| Zertifikate | X509, TLS, HTTPS, SSL, Zertifikate |
| WCF-Binding | WCF, SOAP, BasicHttpBinding |
| SFTP-Protokoll | SFTP, SSH, SecureFileTransfer |
| Docker-Networking | Docker, ContainerNetwork, BridgeNetwork |
| MinIO-S3 | MinIO, S3, ObjectStorage |
| FluentMigrator | Migration, DatabaseSchema, FluentMigrator |

Verwende 3-5 Aliases die das Thema aus verschiedenen Perspektiven
auffindbar machen. Die Aliases ermoeglichen Wiki-Links wie
`[[X509]]` oder `[[TLS]]` die automatisch auf Zertifikate_Wissen.md zeigen.

---

## FEHLERBEHANDLUNG

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| Write-Tool haengt | Datei > 500 Zeilen | PowerShell Copy-Item verwenden |
| Bash-Heredoc bricht | Sonderzeichen (Backticks, Slashes) | .ps1 Temp-Script schreiben |
| Vault nicht gefunden | Pfad falsch | .obsidian/ Ordner suchen |
| Feature-Note fehlt | Noch nicht angelegt | User fragen ob erstellen |
| Wissen-Datei fehlt | Knowledge nicht abgeschlossen | Erst /_knowledge ausfuehren |
| Encoding-Probleme | UTF8 BOM | `-Encoding UTF8` in PowerShell |
| Link-Duplikat | Bereits synchronisiert | Skip, keine Aenderung |

---

## BEISPIEL-AUSFUEHRUNG

```
User: /_knowledgeObsidianSync DCSRE-881

Agent:
  Schritt 0: Manifest lesen...
    → Knowledge: Zertifikate = abgeschlossen
    → Zertifikate_Wissen.md existiert (1027 Zeilen)

  Schritt 1: Vault verifizieren...
    → C:\Users\Administrator\Documents\DCS\.obsidian\ existiert
    → DCSRE-881.md existiert im Vault

  Schritt 2: Sync Zertifikate_Wissen.md...
    → Copy-Item → Vault (1027 Zeilen)
    → Frontmatter: id=Zertifikate_Wissen, tags=[knowledge],
      feature=[[DCSRE-881]], aliases=[X509, TLS, HTTPS, SSL, Zertifikate]
    → Prepend via .ps1 Script → 1044 Zeilen
    → Temp-Script geloescht

  Schritt 3: Feature-Note verlinken...
    → DCSRE-881.md: # Wissen Sektion gefunden
    → [[Zertifikate_Wissen]] hinzugefuegt

  Ergebnis:
  | Wissen-Dokument | Vault-Pfad | Zeilen | Status |
  |-----------------|-----------|--------|--------|
  | Zertifikate_Wissen.md | DCS\Zertifikate_Wissen.md | 1044 | Sync OK |

  Feature-Note DCSRE-881.md aktualisiert.
  Obsidian-Zugriff: [[Zertifikate_Wissen]], [[X509]], [[TLS]], [[HTTPS]]
```

---

## MEHRERE THEMEN

Falls fuer ein Feature mehrere Knowledge-Dokumente abgeschlossen sind:

```
.claude/wissen/Zertifikate_Wissen.md    → abgeschlossen
.claude/wissen/WCF-Binding_Wissen.md    → abgeschlossen
.claude/wissen/SFTP_Wissen.md           → ausstehend (Welle 2)
```

Dann werden NUR die abgeschlossenen synchronisiert:

```
User: /_knowledgeObsidianSync DCSRE-881

→ Sync: Zertifikate_Wissen.md ✓
→ Sync: WCF-Binding_Wissen.md ✓
→ Skip: SFTP_Wissen.md (nicht abgeschlossen)

Feature DCSRE-881.md:
# Wissen
[[WSDL]]
[[Zertifikate_Wissen]]     ← neu
[[WCF-Binding_Wissen]]     ← neu
```

---

## IDEMPOTENZ

Dieses Command ist **idempotent**: Mehrfaches Ausfuehren hat keinen
negativen Effekt.

- Bereits synchronisierte Dateien werden **ueberschrieben** (neueste Version)
- Bereits vorhandene Wiki-Links werden **nicht dupliziert**
- Frontmatter wird immer **neu generiert** (konsistenter Zustand)

ARGUMENTS: $ARGUMENTS
