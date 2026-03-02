# Obsidian Sync Scripts

**Version:** 2.0 (2026-02-01)
**Projekt-agnostisch:** Funktioniert in DCSLESE, DCSRE, CenCoCo, Private/Brain

Diese Scripts werden von `/_obsidianSync` verwendet um:
1. Hashes zu berechnen (Redundanz-Vermeidung)
2. Dateien mit Frontmatter zu syncen
3. Topology-Guards auszufuehren

---

## Scripts

### 1. compute-hashes.ps1

Berechnet MD5-Hashes fuer alle Sync-Kandidaten.

**Parameter:**
- `FilesJson` (JSON-Array): Liste der Dateipfade

**Beispiel:**
```powershell
$files = @(
    "C:\...\DCSRE-881-Retrospekt\.claude\models\Dateiabholung_Model.md",
    "C:\...\DCSRE-881-Retrospekt\.claude\analysis\opus\Dateiabholung-ANALYSE.md"
)
$json = $files | ConvertTo-Json
.\compute-hashes.ps1 -FilesJson $json
```

**Output (JSON):**
```json
[
  { "Path": "...", "Hash": "15808C7046BA", "Exists": true },
  { "Path": "...", "Hash": "682B59D386E3", "Exists": true }
]
```

---

### 2. sync-with-frontmatter.ps1

Kopiert Datei in Vault und fuegt YAML-Frontmatter hinzu.

**Parameter:**
- `SourcePath`: Quell-Datei (absolute path)
- `VaultPath`: Ziel im Vault (absolute path)
- `FrontmatterJson` (JSON-Objekt): Frontmatter-Felder

**Beispiel:**
```powershell
$fm = @{
    id = "Dateiabholung-ANALYSE"
    aliases = @("Analyse1", "Verifikation")
    tags = @("type/analyse", "op/DCSRE-881", "topic/DIC")
    feature = "[[DCSRE-881]]"
    cycle = 1
    'chain-position' = "analyse"
    prev = "[[Dateiabholung_Model]]"
    next = "[[Dateiabholung-HYPOTHESEN]]"
    callout = "Analyse-Dokument fuer [[DCSRE-881]]. Zyklus 1."
} | ConvertTo-Json

.\sync-with-frontmatter.ps1 `
    -SourcePath "C:\...\Dateiabholung-ANALYSE.md" `
    -VaultPath "C:\Users\...\DCS\Dateiabholung-ANALYSE.md" `
    -FrontmatterJson $fm
```

**Output:**
```
Synced: C:\Users\...\DCS\Dateiabholung-ANALYSE.md (520 lines)
```

---

### 3. run-topology-guards.ps1

Fuehrt 5 Topology-Guards aus (G-CHAIN, G-BIDIR, G-NAME, G-XREF, G-CAUSAL).

**Parameter:**
- `ChainMapJson` (JSON): Chain-Map (Knoten + Kanten)
- `SyncTableJson` (JSON): Sync-Tabelle (Quelle → Vault Mapping)
- `ManifestHistoryJson` (JSON): Zyklus-Historie

**Beispiel:**
```powershell
$chainMap = @{
    nodes = @(
        @{ id = "ANALYSE"; type = "analyse"; cycle = 1; prev = "MODEL"; next = "HYPOTHESEN" },
        @{ id = "HYPOTHESEN"; type = "hypothese"; cycle = 1; prev = "ANALYSE"; next = "ERGEBNIS" }
    )
    edges = @(
        @{ from = "ANALYSE"; to = "HYPOTHESEN"; type = "chain"; label = "3 Hypothesen" },
        @{ from = "ANALYSE"; to = "MODEL"; type = "update"; label = "+W11+W12" }
    )
} | ConvertTo-Json -Depth 10

$syncTable = @(
    @{ source = "models/Dateiabholung_Model.md"; vault = "Dateiabholung_Model.md" },
    @{ source = "models/Retrospekt_Model.md"; vault = "OmniCommand_Model.md" }  # RENAME!
) | ConvertTo-Json

$history = @(
    @{ cycle = 1; ergebnis = "W11+W12, Config-Blocker" }
) | ConvertTo-Json

.\run-topology-guards.ps1 `
    -ChainMapJson $chainMap `
    -SyncTableJson $syncTable `
    -ManifestHistoryJson $history
```

**Output (JSON):**
```json
{
  "Guards": {
    "G-CHAIN": { "Status": "PASS", "Details": ["Alle 1 Zyklen vollstaendig"] },
    "G-BIDIR": { "Status": "PASS", "Details": ["2 prev/next-Paare symmetrisch"] },
    "G-NAME": { "Status": "WARN", "Details": ["1 Umbenennungen gefunden:", "Retrospekt_Model.md → OmniCommand_Model.md"] },
    "G-XREF": { "Status": "PASS", "Details": ["Alle 1 ANALYSE-Knoten haben MODEL-Kante"] },
    "G-CAUSAL": { "Status": "PASS", "Details": ["Alle 1 kausalen Kanten haben Label"] }
  },
  "PassCount": 4,
  "WarnCount": 1
}
```

---

## Verwendung in anderen Projekten

Diese Scripts sind **projekt-agnostisch**. Um sie in einem anderen Projekt zu nutzen:

1. Kopiere das gesamte `.claude/scripts/obsidian/` Verzeichnis
2. Die Scripts benoetigen KEINE Anpassung (alle Pfade als Parameter)
3. `/_obsidianSync` Command muss die richtigen Parameter uebergeben

**Projekte:**
- DCSRE: Vault → `C:\Users\...\DCS`
- CenCoCo: Vault → `C:\Users\...\CenCoCo-Vault`
- Private/Brain: Vault → `C:\Users\...\Brain`

---

### 4. detect-vault.ps1

**NEU in v2.0!** Erkennt automatisch den Ziel-Vault basierend auf Projekt-Pfad.

**Parameter:**
- `CurrentPath` (optional): Pfad zum Analysieren (Default: aktueller Pfad)
- `ConfigPath` (optional): Pfad zur vault-routing.json (Default: auto-detect)

**Beispiel:**
```powershell
# Auto-Detection (nutzt aktuellen Pfad)
.\detect-vault.ps1

# Expliziter Pfad
.\detect-vault.ps1 -CurrentPath "C:\Some\Path\CenCoCo\Project"
```

**Output (JSON):**
```json
{
  "Vault": "DCS",
  "Path": "C:\\Users\\Administrator\\Documents\\DCS",
  "Rule": {
    "Pattern": "DCSRE",
    "Priority": 1,
    "Description": "DCSRE-Projekt → DCS Vault"
  },
  "CurrentPath": "C:\\...\\DCSRE-881-Retrospekt",
  "IsValidVault": true,
  "ObsidianPath": "C:\\Users\\Administrator\\Documents\\DCS\\.obsidian"
}
```

**Detection-Regeln:**
1. Pfad enthält "DCSRE" → DCS Vault
2. Pfad enthält "CenCoCo" → CenCoCo-Vault
3. Sonst → Brain (Default für Private)

**Config-Datei:** `.claude/config/vault-routing.json`

---

## Technische Hinweise

### Encoding
Alle Scripts verwenden **UTF8** fuer Dateien (wichtig fuer Umlaute).

### JSON-Parameter
Komplexe Parameter (Arrays, Objekte) werden als JSON-String uebergeben und
mit `ConvertFrom-Json` geparst. Das vermeidet PowerShell-Escaping-Probleme.

### Fehlerbehandlung
- `compute-hashes.ps1`: Fehlende Dateien → `Exists: false`
- `sync-with-frontmatter.ps1`: Fehlende Felder → werden uebersprungen
- `run-topology-guards.ps1`: Fehlende Knoten/Kanten → WARN statt FAIL

---

## Versionierung

| Version | Datum | Aenderungen |
|---------|-------|-------------|
| 1.0 | 2026-01-31 | Initial (temporaere .ps1 Dateien) |
| 2.0 | 2026-02-01 | Persistent in `.claude/scripts/obsidian/`, projekt-agnostisch |
