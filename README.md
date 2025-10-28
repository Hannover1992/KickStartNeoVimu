# Neovim Kickstart Configuration for DCSRE Project

A customized Neovim configuration based on kickstart.nvim, optimized for full-stack development with Angular/TypeScript frontend and C#/.NET backend.

## Tech Stack Support
- **Frontend**: Angular 18.2.9, TypeScript 5.5.4, NgRx, Jest, Cypress
- **Backend**: .NET 8.0.400, C#, xUnit
- **Tools**: Docker, YAML, HTML, CSS, JSON

## Installation Steps

### 1. Install Neovim (0.10+ required)
```bash
# Download latest Neovim
wget https://github.com/neovim/neovim/releases/download/v0.11.4/nvim-linux64.tar.gz
tar xf nvim-linux64.tar.gz
sudo mv nvim-linux64 /opt/
sudo ln -sf /opt/nvim-linux64/bin/nvim /usr/local/bin/nvim
```

### 2. Install .NET SDK
```bash
# Download and install .NET SDK 8.0
wget https://dot.net/v1/dotnet-install.sh
chmod +x dotnet-install.sh
./dotnet-install.sh --channel 8.0

# Add to PATH in ~/.bashrc
echo 'export PATH="$HOME/.dotnet:$PATH"' >> ~/.bashrc
echo 'export DOTNET_ROOT="$HOME/.dotnet"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Clone Configuration
```bash
cd ~/.config
git clone https://github.com/yourusername/nvim-config nvim
```

### 4. First Launch
```bash
# Open Neovim - plugins will auto-install
nvim

# Wait for installation to complete
# Restart Neovim when done
```

### 5. Install LSP Servers
Open Neovim and run:
```vim
:Mason
```
Install the following servers:
- `typescript-language-server`
- `angular-language-server`
- `omnisharp`
- `html-lsp`
- `css-lsp`
- `json-lsp`
- `yaml-language-server`
- `dockerfile-language-server`
- `docker-compose-language-service`

## Key Features

### LSP Support
- Full IntelliSense for C#, TypeScript, Angular
- Go to Definition (`gd`)
- Find References (`grr`)
- Hover Documentation (`K`)
- Code Actions (`<Space>ca`)
- Rename Symbol (`<Space>rn`)

### File Navigation
- Find Files: `<Space>sf`
- Search in Files: `<Space>sg`
- Search Word: `<Space>sw`
- File Explorer: `<Space>e`

### Code Refactoring
- Format Document: `<Space>f`
- Code Actions: `<Space>ca`
- Rename: `<Space>rn`
- Extract Method/Variable: via Code Actions

### Debugging
- Debug Test: `<Space>dt`
- Run Test: `<Space>tr`
- Toggle Breakpoint: `<F5>`
- Continue: `<F10>`
- Step Over: `<F11>`
- Step Into: `<F12>`

### Additional Plugins
- **Telescope**: Fuzzy finder for files, grep, symbols
- **Treesitter**: Advanced syntax highlighting
- **DAP**: Debug Adapter Protocol for debugging
- **Neotest**: Test runner integration
- **Zen Mode**: Distraction-free coding
- **Twilight**: Dims inactive code sections
- **ToggleTerm**: Integrated terminal

## Project Structure
```
~/.config/nvim/
├── init.lua          # Main configuration
├── lua/
│   └── custom/       # Custom configurations
└── after/
    └── plugin/       # Plugin-specific configs
```

## Troubleshooting

### OmniSharp Not Working
1. Check installation: `:Mason` - ensure omnisharp is installed
2. Kill stuck processes: `pkill -f omnisharp`
3. Clear swap files: `rm ~/.local/state/nvim/swap/*.swp`
4. Restart Neovim

### LSP Not Attaching
1. Check LSP status: `:LspInfo`
2. Restart LSP: `:LspRestart`
3. Check logs: `:LspLog`

### Performance Issues
1. Disable unused plugins in init.lua
2. Reduce Treesitter parsers
3. Adjust completion settings

## Keyboard Shortcuts Reference

### General
- Leader key: `<Space>`
- Save: `<C-s>`
- Quit: `:q`
- Force Quit: `:q!`

### Navigation
- File Explorer: `<Space>e`
- Find Files: `<Space>sf`
- Recent Files: `<Space>sr`
- Buffers: `<Space>sb`

### Code Intelligence
- Go to Definition: `gd`
- Find References: `grr`
- Hover: `K`
- Code Actions: `<Space>ca`
- Format: `<Space>f`

### Testing
- Run Test: `<Space>tr`
- Debug Test: `<Space>dt`
- Run All Tests: `<Space>ta`

## Working with DCSRE Project

### Backend Development
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend
nvim VDEK.DCSP.WebApi/Controllers/UserController.cs
```

### Frontend Development
```bash
cd /mnt/c/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Frontend
nvim src/app/components/user/user.component.ts
```

## Contributing
Feel free to customize the configuration to match your workflow!

## License
MIT