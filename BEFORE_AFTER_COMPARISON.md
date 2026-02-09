# Before/After Comparison - Keybinding Descriptions

## Example: Backend Operations

### Before
```lua
end, { desc = '[R]un [B]ackend [W]ebhost' })
end, { desc = '[R]un [B]ackend [S]etup (Migrations)' })
end, { desc = '[R]un [B]ackend [B]uild (dotnet build)' })
end, { desc = '[R]un [B]ackend [T]ests' })
end, { desc = '[R]un [B]ackend [U]nit tests (no DB/Storage/Docker)' })
```

### After
```lua
end, { desc = '[R]un [B]ackend [W]ebhost | dotnet run' })
end, { desc = '[R]un [B]ackend [S]etup | dotnet run --project VDEK.DCSP.Setup' })
end, { desc = '[R]un [B]ackend [B]uild | dotnet clean && dotnet build' })
end, { desc = '[R]un [B]ackend [T]ests | dotnet test --filter FullyQualifiedName~{file}' })
end, { desc = '[R]un [B]ackend [U]nit tests | dotnet test --filter Category!=Database&Storage&Docker' })
```

**Benefit**: You can immediately see what command runs without reading the function code!

---

## Example: Docker Operations

### Before
```lua
end, { desc = '[R]un [D]ocker [I]nfrastructure (up)' })
end, { desc = '[R]un [D]ocker [A]ll (Profile=all, DCSRE)' })
end, { desc = '[R]un [D]ocker [r]undown (quick, keep data)' })
end, { desc = '[R]un [D]ocker [R]eset (full cleanup)' })
```

### After
```lua
end, { desc = '[R]un [D]ocker [I]nfrastructure | docker-up.ps1 / docker compose up' })
end, { desc = '[R]un [D]ocker [A]ll | docker-up.ps1 -Profile all' })
end, { desc = '[R]un [D]ocker [r]undown | docker compose down' })
end, { desc = '[R]un [D]ocker [R]eset | docker compose down -v --rmi all' })
```

**Benefit**: Clear indication of what each Docker command does - infrastructure vs all services, keep data vs full cleanup.

---

## Example: Frontend Operations

### Before
```lua
end, { desc = '[R]un [F]rontend [W]eb (dev server)' })
end, { desc = '[R]un [F]ront [B]uild (production)' })
end, { desc = '[R]un [F]ront [T]est' })
```

### After
```lua
end, { desc = '[R]un [F]rontend [W]eb | npm start / dotnet run' })
end, { desc = '[R]un [F]ront [B]uild | npm run build / docker compose build' })
end, { desc = '[R]un [F]ront [T]est | npm test' })
```

**Benefit**: Shows project-specific commands (DCSRE uses npm, CENCOCD uses dotnet/docker).

---

## Example: Git Operations

### Before
```lua
end, { desc = '[R]un [C]ommit (open in TFS browser)' })
end, { desc = '[R]un [P]ush (Windows VPN)' })
end, { desc = '[R]un [P]ull (Windows VPN)' })
```

### After
```lua
end, { desc = '[R]un [C]ommit | Open in TFS browser (from clipboard)' })
end, { desc = '[R]un [P]ush | git push (Windows VPN)' })
end, { desc = '[R]un [P]ull | git pull (Windows VPN)' })
```

**Benefit**: Explicit git commands shown, easier to search for "push" or "pull".

---

## Example: Integration Tests

### Before
```lua
end, { desc = '[R]un [I]ntegration [M]ock (DicMockServer, 38 threads)' })
end, { desc = '[R]un [I]ntegration [D]B (non-mock, 8 threads)' })
```

### After
```lua
end, { desc = '[R]un [I]ntegration [M]ock | dotnet test --filter DicMockServer' })
end, { desc = '[R]un [I]ntegration [D]B | dotnet test --filter !DicMockServer' })
```

**Benefit**: Shows the actual filter being used - instantly clear what the difference is.

---

## How to See These Descriptions

### Method 1: Command Mode
```vim
:map <leader>r
```

Shows all keybindings starting with `<leader>r`:
```
n  <leader>rbw       * dotnet run
   [R]un [B]ackend [W]ebhost | dotnet run
n  <leader>rbs       * dotnet run --project VDEK.DCSP.Setup
   [R]un [B]ackend [S]etup | dotnet run --project VDEK.DCSP.Setup
```

### Method 2: Telescope (if installed)
```vim
:Telescope keymaps
```

Then search for:
- `dotnet` - finds all dotnet-related keybindings
- `docker` - finds all Docker keybindings
- `npm` - finds all Node.js keybindings
- `git` - finds all git keybindings

### Method 3: Leader Help (Lazy.nvim with which-key)
```vim
<leader>?
```

Shows all keybindings with descriptions in a nice menu.

---

## Pattern Explanation

All descriptions follow this pattern:

```
[Brief Description] | actual-command [with arguments]
```

Examples:
- `[R]un [B]ackend [W]ebhost | dotnet run`
- `[R]un [D]ocker [I]nfrastructure | docker-up.ps1 / docker compose up`
- `[R]un [I]ntegration [M]ock | dotnet test --filter DicMockServer`

The pipe `|` separates the user-friendly description from the technical command.

---

## Why This Matters

1. **Self-documenting**: No need to open init.lua to understand what a keybinding does
2. **Searchable**: Can search for specific commands (e.g., "dotnet build") in Telescope
3. **Consistency**: All keybindings follow the same format
4. **Learning**: New team members can understand all available commands at a glance
5. **Debugging**: When helping others, you can say "press `<leader>rbw` to run the backend" and they see exactly what it does

---

**Total keybindings updated**: 27
**Date**: 2025-02-09
