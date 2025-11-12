# Neovim Setup & Deployment für DCSRE

Complete guide für Installation auf neuen Maschinen und Verwendung im Projekt.

## Schnellstart (Existing Config)

Wenn du dieses Repository bereits hast, brauchst du nur:

```bash
# 1. Clone the config
git clone <your-repo> ~/.config/nvim

# 2. Install dependencies (einmalig)
./setup.sh

# 3. Start Neovim
nvim
```

---

## Installation auf NEUER Maschine

### Voraussetzungen

```bash
# Linux/WSL
sudo apt update
sudo apt install -y git curl wget build-essential unzip

# Neovim installieren
wget https://github.com/neovim/neovim/releases/download/v0.11.4/nvim-linux64.tar.gz
tar xf nvim-linux64.tar.gz
sudo mv nvim-linux64 /opt/nvim-linux64
sudo ln -sf /opt/nvim-linux64/bin/nvim /usr/local/bin/nvim

# .NET SDK 8.0 (für C# Backend)
wget https://dot.net/v1/dotnet-install.sh
chmod +x dotnet-install.sh
./dotnet-install.sh --channel 8.0
echo 'export PATH="$HOME/.dotnet:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Node.js (für TypeScript/Angular Frontend)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Ripgrep (für Telescope)
sudo apt install -y ripgrep fd-find xclip
```

### Config Setup

```bash
# 1. Clone configuration
git clone <your-nvim-config-repo> ~/.config/nvim
cd ~/.config/nvim

# 2. Run setup script
bash setup.sh

# 3. Start Neovim (plugins auto-install)
nvim

# Wait 2-3 minutes for first-time plugin installation
# Then restart: :qa and nvim again
```

---

## C# Backend Setup

### NuGet Packages Restore (ONE TIME!)

```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
bash .setup-omnisharp.sh
```

**Was es macht:**
- Restored alle NuGet Packages
- OmniSharp kann dann alle 26+ Projekte laden
- Dauert 2-5 Minuten beim ersten Mal

### Nach Setup: Tests ausführen

```bash
# Im Backend Directory:
cd Sources/Backend

# Alle Tests:
dotnet test

# Ein spezifisches Test-Projekt:
dotnet test VDEK.DCSP.Test/VDEK.DCSP.Test.csproj

# Mit Output:
dotnet test --verbosity detailed

# Mit Code Coverage:
dotnet test /p:CollectCoverage=true
```

### In Neovim Tests laufen lassen

```vim
" Terminal öffnen
<C-\>                    " Toggle Terminal

" Im Terminal:
cd Sources/Backend
dotnet test

" Oder schneller in Neovim:
<leader>tt               " Run nearest test (mit Neotest)
<leader>tf               " Run current file tests
<leader>td               " Debug test
<leader>ts               " Show test summary
<leader>to               " Show test output
```

---

## TypeScript/Angular Frontend Setup

### Dependencies installieren

```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Frontend
npm install
```

### Tests & Development

```bash
# Unit Tests (Jest)
npm test

# E2E Tests (Cypress)
npm run cypress

# Start dev server
npm start

# Build
npm run build
```

### In Neovim

```vim
<leader>sf               " Search Frontend files
<leader>s/               " Grep in Frontend code
gd                       " Go to TypeScript definition
grr                      " Find all references
K                        " Show documentation
```

---

## Hotkeys Übersicht

### Navigation & Code
| Key | Aktion |
|-----|--------|
| `gd` | Go to Definition |
| `grr` | Find All References |
| `K` | Hover Documentation |
| `<leader>o` | Toggle Code Outline |
| `<leader>cp` | Copy File Path |

### Search & File Operations
| Key | Aktion |
|-----|--------|
| `<leader>sf` | Search Files |
| `<leader>s/` | Grep/Search in Code |
| `<leader>sb` | Search Buffers |
| `<leader>sh` | Search Help |
| `<leader>s.` | Search Recent Files |

### LSP & Diagnostics
| Key | Aktion |
|-----|--------|
| `<leader>q` | Show Diagnostics |
| `<leader>ca` | Code Actions |
| `<leader>f` | Format Code |
| `gI` | Goto Implementation |
| `<leader>D` | Type Definition |

### Debug (C#/.NET)
| Key | Aktion |
|-----|--------|
| `<F5>` | Continue/Start Debug |
| `<F10>` | Step Over |
| `<F11>` | Step Into |
| `<leader>b` | Toggle Breakpoint |
| `<leader>du` | Toggle Debug UI |

### Tests
| Key | Aktion |
|-----|--------|
| `<leader>tt` | Run Nearest Test |
| `<leader>tf` | Run Test File |
| `<leader>td` | Debug Test |
| `<leader>ts` | Test Summary |
| `<leader>to` | Test Output |

### Terminal
| Key | Aktion |
|-----|--------|
| `<C-\>` | Toggle Terminal |
| `<C-t>d` | New Terminal Down |
| `<C-t>r` | New Terminal Right |
| `<C-t>f` | New Terminal Float |

---

## Portable Setup (Sync auf andere Maschine)

### Option 1: Git Push (EMPFOHLEN)

```bash
# Auf erste Maschine:
cd ~/.config/nvim
git remote add origin https://github.com/yourusername/nvim-config.git
git push -u origin master

# Auf neue Maschine:
git clone https://github.com/yourusername/nvim-config.git ~/.config/nvim
cd ~/.config/nvim
bash setup.sh
```

### Option 2: Manual Copy

```bash
# Auf erste Maschine:
tar czf nvim-config.tar.gz ~/.config/nvim/
# → Download nvim-config.tar.gz

# Auf neue Maschine:
tar xzf nvim-config.tar.gz
mv .config/nvim ~/.config/nvim
cd ~/.config/nvim
bash setup.sh
```

### Option 3: Rsync (über SSH)

```bash
# Von neue Maschine zu alte Maschine:
rsync -avz --delete user@old-machine:~/.config/nvim/ ~/.config/nvim/
cd ~/.config/nvim
bash setup.sh
```

---

## Nach Neustart: Was funktioniert?

✅ **Alle Funktionen sind automatisch aktiv:**

- OmniSharp lädt beim Öffnen von `.cs` Dateien
- Alle Plugins installiert und ready
- All keybindings funktionieren
- Clipboard sync aktiv
- Diagnostics live
- Tests ready to run

✅ **Keine Manual Konfiguration nötig!**

---

## Troubleshooting

### OmniSharp nicht attached
```bash
pkill -f omnisharp
rm -f ~/.local/state/nvim/swap/*.swp
nvim <your-csharp-file>
```

### Plugins nicht installed
```vim
:Lazy sync
:TSUpdate
:Mason
```

### Langsam on startup?
```vim
:Lazy profile
" Zeigt welche Plugins langsam sind
```

### Tests funktionieren nicht
```bash
# Check if dotnet is installed
dotnet --version

# Restore packages
cd Sources/Backend
dotnet restore
```

---

## Project Structure

```
DCSRE/
├── Sources/
│   ├── Backend/
│   │   ├── VDEK.DCSP.sln
│   │   ├── VDEK.DCSP.WebApi/        (C# Main API)
│   │   ├── VDEK.DCSP.Domain/        (Business Logic)
│   │   ├── VDEK.DCSP.Data/          (Database)
│   │   ├── VDEK.DCSP.Test/          (Unit Tests - xUnit)
│   │   └── .setup-omnisharp.sh       (NuGet restore)
│   │
│   └── Frontend/
│       ├── package.json
│       ├── angular.json              (Angular config)
│       ├── src/
│       │   ├── app/                  (Angular components)
│       │   └── environments/         (Environment config)
│       ├── karma.conf.js             (Test config)
│       └── cypress/                  (E2E Tests)
│
└── ~/.config/nvim/                   (THIS REPO)
    ├── init.lua                      (Main config)
    ├── lazy-lock.json                (Plugin versions)
    ├── setup.sh                      (Setup script)
    └── CLAUDE.md                     (OmniSharp fixes)
```

---

## Tips & Tricks

### Schnelle Backend Tests in Neovim
```bash
# Im Terminal:
<C-\>
cd Sources/Backend
dotnet test --no-build

# Oder mit Watch Mode:
dotnet watch test
```

### Schnelle Frontend Tests
```bash
<C-\>
cd Sources/Frontend
npm test -- --watch
```

### Code von IDE zu Neovim

Wenn du in C# IDE etwas siehst:
1. Hover über Symbol → Copy Reference
2. In Neovim: `<leader>sf` + paste Dateiname
3. `gd` auf Symbol → Go to Definition

### Debugging C# in Neovim
```vim
<F5>           " Start debugger
<F10>          " Step over
<F11>          " Step into
<leader>b      " Set breakpoint
<leader>du     " Show debug panel
```

---

## Häufige Fragen

### Q: Funktioniert das auf Windows?
**A:** Ja, mit WSL2. Alle Befehle sind identisch.

### Q: Kann ich meine Einstellungen speichern?
**A:** Ja, `git commit` deine Changes:
```bash
cd ~/.config/nvim
git add init.lua
git commit -m "deine Änderung"
```

### Q: Werden Plugins automatisch aktualisiert?
**A:** Nein. Manuell mit `:Lazy update`

### Q: Kann ich das auf mehreren Maschinen nutzen?
**A:** Ja! Einfach `git clone` auf jeder Maschine.
Config wird über Git synchronisiert.

### Q: Was tun wenn etwas broken ist?
**A:**
1. `:checkhealth` - zeigt Probleme
2. `:LspLog` - zeigt LSP Fehler
3. Siehe CLAUDE.md für OmniSharp Fixes

---

## Nächste Schritte

1. ✅ Neovim & Dependencies installieren
2. ✅ Config clonen & setup.sh laufen lassen
3. ✅ Backend Setup (dotnet restore)
4. ✅ Frontend Setup (npm install)
5. ✅ Tests ausführen (`dotnet test`, `npm test`)
6. ✅ Auf andere Maschine übertragen (git push/clone)

---

**Happy coding!** 🚀
