# Setup: Neuer Windows-Laptop fuer DCSRE-Entwicklung mit Neovim

**Zweck:** Diese Anleitung soll Claude (oder ein Mensch) auf einer **neuen Windows-Maschine** Schritt-fuer-Schritt durcharbeiten, um DCSRE-Entwicklung mit dieser Neovim-Config zum Laufen zu bringen.

**WICHTIG fuer Claude:**
- Diese Anleitung ist **interaktiv** — frage den User wenn Pfade unklar sind!
- Username muss NICHT mehr `Administrator` sein (Refactor 2026-04-25 hat alle Pfade portabel gemacht).
- Pfade fuer **DCSRE-Repo** und **Obsidian-Vaults** koennen auf neuer Maschine **anders sein** — User fragen!

---

## 0. Vorab-Klaerung mit User (PFLICHT!)

Bevor Claude irgendetwas installiert, **diese Fragen an User stellen**:

1. **Wo soll das DCSRE-Repo geklont werden?**
   - Default-Annahme: `<USERPROFILE>\Documents\Work\Code2\DCSRE`
   - Wichtig: Pfad muss **"DCSRE" im Namen** enthalten (sonst greift die Project-Detection nicht)
   - Beispiel-Antworten:
     - `C:\Users\Patryk\Documents\Work\Code2\DCSRE`
     - `D:\Repos\DCSRE`

2. **Wo liegen die Obsidian-Vaults?** (oder: werden sie auf dieser Maschine ueberhaupt genutzt?)
   - Default-Annahme: `<USERPROFILE>\Documents\DCS`, `<USERPROFILE>\Documents\Obsydian\CenCoCo`, `<USERPROFILE>\Documents\Brain`
   - Optional: andere Pfade (dann muss `lua/shared/core.lua` Workspaces angepasst werden)
   - Optional: gar nicht installieren, falls nicht genutzt

3. **Wo liegt das `AgentsArchive`?** (fuer claude_sync)
   - Default: `<USERPROFILE>\Documents\Projekt\AgentsArchive`
   - Wenn nicht vorhanden: muss zuerst aus Backup uebertragen werden (oder feature dauerhaft deaktivieren)

4. **DCSRE_Azure-Script genutzt?** (`<leader>rsc` — `new-research-project.ps1`)
   - Default: `<USERPROFILE>\Documents\Work\Code2\DCSRE_Azure\OmniCommand\.claude\new-research-project.ps1`
   - Falls anderer Pfad: in `init.lua` einmalig setzen: `vim.g.dcsre_azure_script = 'D:\\...\\new-research-project.ps1'`
   - Falls nicht genutzt: ignorieren

5. **Soll Frontend-Entwicklung auch auf dieser Maschine laufen?**
   - Falls ja: zusaetzliche Tools noetig (Node.js, npm, ggf. WSL2)

---

## 1. Tools installieren (Tier 1 — Basics)

```powershell
# Per winget (admin nicht zwingend noetig):
winget install --id Neovim.Neovim
winget install --id Git.Git
winget install --id OpenJS.NodeJS.LTS
winget install --id Microsoft.DotNet.SDK.8
winget install --id Microsoft.PowerShell        # PowerShell 7
winget install --id Docker.DockerDesktop
winget install --id Google.Chrome
```

**Verifikation:**
```powershell
nvim --version          # >= 0.11
git --version
node --version
dotnet --version        # 8.x oder hoeher
docker --version
```

---

## 2. Neovim-Config deployen

```powershell
# Repo klonen (Pfad nach User-Wahl, hier Default-Annahme):
$nvimSrc = "$env:USERPROFILE\Documents\Projekt\KickStartNeoVim"
git clone https://github.com/<dein-fork>/KickStartNeoVim.git $nvimSrc

# Config-Verzeichnis vorbereiten:
$nvimDst = "$env:LOCALAPPDATA\nvim"
New-Item -ItemType Directory -Force -Path "$nvimDst\lua" | Out-Null

# Config kopieren (Inhalt von lua\, NICHT lua\ selbst):
Copy-Item -Recurse -Force "$nvimSrc\lua\*" "$nvimDst\lua\"
Copy-Item -Force "$nvimSrc\init.lua" "$nvimDst\init.lua"
```

**OmniSharp-Config:**
```powershell
$omniDir = "$env:USERPROFILE\.omnisharp"
New-Item -ItemType Directory -Force -Path $omniDir | Out-Null

@'
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,
    "EnableImportCompletion": true,
    "AnalyzeOpenDocumentsOnly": false
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,
    "OrganizeImports": true
  }
}
'@ | Out-File -Encoding utf8 "$omniDir\omnisharp.json"
```

---

## 3. Erststart Neovim

```powershell
nvim
```

- Lazy.nvim installiert automatisch alle Plugins (~1-2 Min, Internet noetig).
- Wenn fertig: `:q` zum Beenden.
- Wieder oeffnen, dann `:Mason` → `omnisharp` suchen, `i` zum Installieren, dasselbe fuer `netcoredbg`.
- `:checkhealth` zeigt evtl. fehlende Tools.

---

## 4. .NET / DCSRE Backend vorbereiten

```powershell
# In den DCSRE-Repo-Pfad wechseln (User-spezifisch, Default-Annahme):
$dcsreRoot = "$env:USERPROFILE\Documents\Work\Code2\DCSRE"
cd "$dcsreRoot\Sources\Backend"

# HTTPS Dev-Cert (einmalig pro Maschine):
dotnet dev-certs https --trust

# Restore + Build:
dotnet restore --force-evaluate --no-cache
dotnet build VDEK.DCSP.IntegrationTests

# Wichtig: appsettings.Development.json aus Backup uebernehmen
# (Connection-Strings, DIC-Mock-URLs - NICHT im Repo!)
```

---

## 5. VPN + TFS-Zugang

- VPN-Client installieren (Corporate-spezifisch — Standard-Setup je nach Firma)
- Test: `git pull` im DCSRE-Repo muss funktionieren
- Wenn Credential-Manager gewuenscht: `git config --global credential.helper manager`

---

## 6. Frontend (optional, falls auf dieser Maschine genutzt)

```powershell
cd "$dcsreRoot\Sources\Frontend"
npm install
# SSL-Zertifikate fuer https://localhost:8443 ggf. noetig (siehe Frontend-README)
```

---

## 7. Docker Desktop konfigurieren

- Nach Erst-Install: WSL2-Backend aktivieren (Docker Desktop Settings → General → "Use WSL 2 based engine")
- Reboot empfohlen
- Test: `docker run --rm hello-world`

---

## 8. Optionale Konfiguration

**a) Falls Obsidian-Vault-Pfade abweichen:**
Editiere `lua/shared/core.lua` ~Zeile 595, oder besser: `vim.g.obsidian_vaults` in `init_windows.lua` setzen (TODO: configurable machen, aktuell direkt im Code).

**b) Falls DCSRE_Azure-Script abweicht:**
In `init_windows.lua` oder einer eigenen `lua/local.lua` setzen:
```lua
vim.g.dcsre_azure_script = 'D:\\Work\\DCSRE_Azure\\...\\new-research-project.ps1'
```

**c) PowerShell ExecutionPolicy (falls Scripts nicht starten):**
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 9. Smoke-Test (alles laeuft?)

```powershell
cd $dcsreRoot
nvim Sources/Backend/VDEK.DCSP.WebHost/Program.cs
```

In Neovim:
- `:LspInfo` → omnisharp attached?
- `<leader>sd` → Diagnostics anzeigbar?
- `<leader>gg` → Neogit oeffnet?
- `<leader>rim` → Integration Tests starten? (vorher `dotnet build` muss durchgelaufen sein)

---

## 10. Troubleshooting

| Problem | Loesung |
|---------|---------|
| `Project-Detection greift nicht` | Repo-Pfad enthaelt kein "DCSRE" — umbenennen oder Symlink |
| `OmniSharp findet keine Pakete` | `dotnet restore --force-evaluate --no-cache` im Backend |
| `riA/rim Tests: DLL not found` | Vorher `dotnet build VDEK.DCSP.IntegrationTests` |
| `claude_sync findet kein Archive` | `AgentsArchive` Ordner existiert nicht — Backup einspielen oder Feature ignorieren |
| `Obsidian Workspaces broken` | Vault-Pfade existieren nicht — Vaults klonen oder `core.lua` anpassen |
| `<leader>rp` Push schlaegt fehl` | VPN nicht verbunden |

---

## Was wurde portabel gemacht? (Refactor 2026-04-25)

| Datei | Vorher | Jetzt |
|-------|--------|-------|
| `platform.lua` | — | Neue Helper `user_home()`, `user_home_windows()` |
| `tests.lua` | 8x hardcoded `C:\Users\Administrator\...\Temp` | Helper `tests_temp()` |
| `project.lua` (CENCOCD) | hardcoded `Administrator` | `platform.user_home()` |
| `core.lua` (AgentsArchive) | hardcoded `Administrator` | `user_home()` + Legacy-Fallback |
| `core.lua` (Obsidian) | hardcoded `Administrator` | `user_home()` |
| `claude_sync.lua` | hardcoded `Administrator` | `USERPROFILE` env |
| `git.lua` (DCSRE_Azure) | hardcoded `Administrator` | `USERPROFILE` + `vim.g.dcsre_azure_script` |

**DCSRE-Detection** war schon vorher portabel via `find_dcsre_root()` — Pfad-Pattern statt Hardcoded.

---

## Anhang: Hardcoded-Fallbacks (Bestand-Schutz)

Auf der **alten Maschine** (User: `Administrator`) bleibt alles wie vorher — die Refactor-Helper liefern dort exakt dieselben Pfade. Auf neuer Maschine greifen automatisch `USERPROFILE`/`USERNAME`.

Wenn auf neuer Maschine ein Tool dennoch alte `Administrator`-Pfade sucht (z.B. CI-Scripts ausserhalb dieser Config), helfen Symlinks:

```powershell
# Als Admin:
New-Item -ItemType SymbolicLink -Path "C:\Users\Administrator" -Target "$env:USERPROFILE"
```

(Nur als letzte Notloesung — sauberer ist, die jeweilige Stelle zu fixen.)
