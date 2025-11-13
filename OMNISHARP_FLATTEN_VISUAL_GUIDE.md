# OmniSharp Settings Flattening - Visual Quick Reference

**Quick Reference Guide with Visual Examples**

---

## The Flatten Function - Visual Walkthrough

### How It Works (Animation)

```
INPUT TABLE:
┌─────────────────────────────────────────────────────────┐
│ {                                                       │
│   RoslynExtensionsOptions = {                          │
│     EnableAnalyzersSupport = true,                     │
│     AnalyzeOpenDocumentsOnly = false,                  │
│   },                                                    │
│   FormattingOptions = {                                │
│     EnableEditorConfigSupport = true,                  │
│   }                                                     │
│ }                                                       │
└─────────────────────────────────────────────────────────┘
              │
              │ flatten() function processes
              ▼

PROCESSING STEPS:

Step 1: Iterate through table
┌─────────────────────────────────────────────┐
│ for k, v in pairs(tbl) do                  │
│   k="RoslynExtensionsOptions"              │
│   v={EnableAnalyzersSupport=true, ...}     │
│                                            │
│   type(v) == "table" ✓ → RECURSE           │
└─────────────────────────────────────────────┘

Step 2: Recursive call on nested table
┌─────────────────────────────────────────────┐
│ flatten({EnableAnalyzersSupport=true, ...}) │
│                                             │
│ Returns:                                    │
│ ["EnableAnalyzersSupport=true",             │
│  "AnalyzeOpenDocumentsOnly=false"]          │
└─────────────────────────────────────────────┘

Step 3: Prepend parent key
┌─────────────────────────────────────────────────────────────┐
│ for _, pair in ipairs(result) do                           │
│   ret[#ret+1] = "RoslynExtensionsOptions" .. ':' .. pair   │
│   ret[#ret+1] = "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
│   ret[#ret+1] = "RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false"
│ end                                                         │
└─────────────────────────────────────────────────────────────┘

Step 4: Process next parent key (FormattingOptions)
┌─────────────────────────────────────────────────────────────┐
│ k="FormattingOptions"                                       │
│ v={EnableEditorConfigSupport=true}                          │
│                                                             │
│ Recurse → ["EnableEditorConfigSupport=true"]               │
│ Prepend → "FormattingOptions:EnableEditorConfigSupport=true"
└─────────────────────────────────────────────────────────────┘

OUTPUT:
┌───────────────────────────────────────────────────────────┐
│ [1] "RoslynExtensionsOptions:EnableAnalyzersSupport=true"  │
│ [2] "RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false" │
│ [3] "FormattingOptions:EnableEditorConfigSupport=true"    │
└───────────────────────────────────────────────────────────┘
```

### Nil Values - Visual

```
INPUT:
{
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,
    EnableImportCompletion = nil,  ← This key skipped in pairs()
  }
}

PROCESSING:
for k, v in pairs(tbl) do
  k="EnableAnalyzersSupport" → INCLUDED ✓
  k="EnableImportCompletion" → SKIPPED (nil not in pairs iteration)
end

OUTPUT:
[1] "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
-- EnableImportCompletion NOT present
```

### Deep Nesting - Visual

```
INPUT:
{
  RoslynExtensionsOptions = {
    InlayHints = {
      EnableForParameters = true,
    }
  }
}

RECURSION TREE:
flatten({RoslynExtensionsOptions={...}})
  └─ flatten({InlayHints={...}})
       └─ flatten({EnableForParameters=true})
            └─ "EnableForParameters=true"
       ← prepend "InlayHints"
  ← prepend "RoslynExtensionsOptions"

OUTPUT:
[1] "RoslynExtensionsOptions:InlayHints:EnableForParameters=true"
```

---

## on_new_config - Visual Pipeline

### Command Building Process

```
USER CONFIG IN init.lua:
┌─────────────────────────────────────────────┐
│ omnisharp = {                               │
│   cmd = {                                   │
│     'dotnet',                               │
│     '/path/to/OmniSharp.dll'               │
│   },                                        │
│   settings = {                              │
│     RoslynExtensionsOptions = {             │
│       EnableAnalyzersSupport = true,        │
│     },                                      │
│     FormattingOptions = {                   │
│       EnableEditorConfigSupport = true,     │
│     }                                       │
│   }                                         │
│ }                                           │
└─────────────────────────────────────────────┘
              │
              │ on_new_config(new_config, _)
              ▼

STEP 1: Copy cmd array
┌─────────────────────────────────────────────┐
│ new_config.cmd = { unpack(new_config.cmd) } │
│                                             │
│ [1] 'dotnet'                                │
│ [2] '/path/to/OmniSharp.dll'               │
└─────────────────────────────────────────────┘
              │
              ▼

STEP 2: Append hard-coded arguments
┌──────────────────────────────────────────────────┐
│ table.insert(new_config.cmd, '-z')               │
│ vim.list_extend(new_config.cmd,                  │
│   {'--hostPID', '12345'})                        │
│ table.insert(new_config.cmd,                     │
│   'DotNet:enablePackageRestore=false')           │
│ vim.list_extend(new_config.cmd,                  │
│   {'--encoding', 'utf-8'})                       │
│ table.insert(new_config.cmd, '--languageserver') │
│                                                  │
│ [1] 'dotnet'                                     │
│ [2] '/path/to/OmniSharp.dll'                    │
│ [3] '-z'                                         │
│ [4] '--hostPID'                                  │
│ [5] '12345'                                      │
│ [6] 'DotNet:enablePackageRestore=false'         │
│ [7] '--encoding'                                 │
│ [8] 'utf-8'                                      │
│ [9] '--languageserver'                           │
└──────────────────────────────────────────────────┘
              │
              ▼

STEP 3: Flatten and append settings
┌──────────────────────────────────────────────────┐
│ vim.list_extend(new_config.cmd,                  │
│   flatten(new_config.settings))                  │
│                                                  │
│ flatten() returns:                               │
│ [1] "RoslynExtensionsOptions:EnableAnalyzersSupport=true"
│ [2] "FormattingOptions:EnableEditorConfigSupport=true"    │
│                                                  │
│ new_config.cmd now:                              │
│ [1] 'dotnet'                                     │
│ [2] '/path/to/OmniSharp.dll'                    │
│ [3] '-z'                                         │
│ [4] '--hostPID'                                  │
│ [5] '12345'                                      │
│ [6] 'DotNet:enablePackageRestore=false'         │
│ [7] '--encoding'                                 │
│ [8] 'utf-8'                                      │
│ [9] '--languageserver'                           │
│ [10] 'RoslynExtensionsOptions:EnableAnalyzersSupport=true'  │
│ [11] 'FormattingOptions:EnableEditorConfigSupport=true'    │
└──────────────────────────────────────────────────┘
              │
              ▼

STEP 4: Modify capabilities
┌──────────────────────────────────────────────────┐
│ new_config.capabilities.workspace.workspaceFolders = false
└──────────────────────────────────────────────────┘
              │
              ▼

RETURN modified config ready for process spawn
┌──────────────────────────────────────────────────┐
│ return new_config                                │
└──────────────────────────────────────────────────┘
```

---

## Complete Example - Visual

### Input Configuration

```lua
┌────────────────────────────────────────────────────────────┐
│ omnisharp = {                                              │
│   cmd = {                                                  │
│     'dotnet',                                              │
│     '/home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll'
│   },                                                       │
│   settings = {                                             │
│     RoslynExtensionsOptions = {                            │
│       EnableAnalyzersSupport = true,                       │
│       EnableImportCompletion = true,                       │
│       AnalyzeOpenDocumentsOnly = false,                    │
│     },                                                     │
│     FormattingOptions = {                                  │
│       EnableEditorConfigSupport = true,                    │
│       OrganizeImports = true,                              │
│     },                                                     │
│     Sdk = {                                                │
│       IncludePrereleases = true,                           │
│     }                                                      │
│   }                                                        │
│ }                                                          │
└────────────────────────────────────────────────────────────┘
```

### After on_new_config Processing

```bash
COMMAND LINE ARRAY:
┌─────────────────────────────────────────────────────────┐
│ [1]  'dotnet'                                           │
│ [2]  '/home/user/.../OmniSharp.dll'                    │
│ [3]  '-z'                                               │
│ [4]  '--hostPID'                                        │
│ [5]  '19758'                                            │
│ [6]  'DotNet:enablePackageRestore=false'               │
│ [7]  '--encoding'                                       │
│ [8]  'utf-8'                                            │
│ [9]  '--languageserver'                                 │
│ [10] 'RoslynExtensionsOptions:EnableAnalyzersSupport=true'
│ [11] 'RoslynExtensionsOptions:EnableImportCompletion=true'
│ [12] 'RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false'
│ [13] 'FormattingOptions:EnableEditorConfigSupport=true' │
│ [14] 'FormattingOptions:OrganizeImports=true'           │
│ [15] 'Sdk:IncludePrereleases=true'                      │
└─────────────────────────────────────────────────────────┘

ACTUAL SHELL COMMAND EXECUTED:
┌─────────────────────────────────────────────────────────┐
│ dotnet                                                  │
│   /home/user/.../OmniSharp.dll                         │
│   -z                                                    │
│   --hostPID 19758                                       │
│   DotNet:enablePackageRestore=false                     │
│   --encoding utf-8                                      │
│   --languageserver                                      │
│   RoslynExtensionsOptions:EnableAnalyzersSupport=true   │
│   RoslynExtensionsOptions:EnableImportCompletion=true   │
│   RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly=false│
│   FormattingOptions:EnableEditorConfigSupport=true      │
│   FormattingOptions:OrganizeImports=true                │
│   Sdk:IncludePrereleases=true                           │
└─────────────────────────────────────────────────────────┘
```

---

## Timing Visualization

### When on_new_config Executes

```
NEOVIM LIFECYCLE:
═════════════════════════════════════════════════════════════

T0: Startup
   ├─ Load init.lua
   ├─ Register LSP configurations
   └─ on_new_config callback registered (not called yet)
       │
       └─ Waiting...

T0.5: User opens C# file (:e UserController.cs)
   ├─ File type detected: csharp
   ├─ Check: Is there an LSP for this?
   ├─ Found: omnisharp
   ├─ Decide: Attach LSP to buffer
   │
   └─ ⭐️ CALL on_new_config(config, _)
        │
        ├─ Copy cmd ✓
        ├─ Append hard-coded args ✓
        ├─ Flatten settings ✓
        ├─ Append flattened args ✓
        ├─ Modify capabilities ✓
        └─ Return
            │
            └─ Process spawned with full command line
                │
                └─ OmniSharp receives all settings
                   as command-line arguments

                   Analyzer support enabled! ✓

T1-T3: LSP initialization happens
   ├─ LSP handshake
   ├─ Initialize request/response
   └─ Server ready

T4+: Normal operation
   ├─ User edits file
   ├─ Diagnostics published
   └─ Analyzers running ✓

═════════════════════════════════════════════════════════════

⚠️  CRITICAL MOMENT: T0.5
    on_new_config runs ONCE per LSP instance
    Settings applied in command-line arguments
    Cannot be changed without :LspRestart
```

---

## Decision Tree - Why Settings Appear Empty

```
You see: :LspInfo shows RoslynExtensionsOptions = {}
                │
                ▼
        Is this wrong?
         /    \
       YES    NO
       /       \
      │         └─ Settings ARE applied (command-line args show they're passed)
      │            This is just :LspInfo display issue
      │
      └─ Check: Is OmniSharp process running?
            │
            ├─ NO → Settings weren't applied
            │       └─ Debug: Was on_new_config called?
            │           │
            │           ├─ NO → Configuration problem
            │           │       └─ Fix: servers.omnisharp in scope?
            │           │           Proper setup() call?
            │           │
            │           └─ YES → Old process issue
            │                    └─ Fix: pkill -f omnisharp
            │                           Restart Neovim
            │
            └─ YES → Check command line
                    │
                    ├─ Shows flattened settings?
                    │  └─ YES → Settings ARE applied ✓
                    │
                    └─ No flattened settings?
                       └─ on_new_config didn't flatten
                           └─ Check: Do you have settings table?
                               Was it in scope during setup()?
```

---

## Verification Checklist

### Quick Verification (Copy-Paste)

```bash
# 1. Check running process command line
ps aux | grep omnisharp | grep -v grep

# Expected output contains:
# ✓ RoslynExtensionsOptions:EnableAnalyzersSupport=true
# ✓ FormattingOptions:EnableEditorConfigSupport=true
# ✓ Sdk:IncludePrereleases=true

# 2. If you see these → Settings ARE applied (even if :LspInfo shows empty!)

# 3. If you DON'T see these → Debugging needed
#    • Was on_new_config called?
#    • Was settings table in scope?
#    • Was flatten() invoked?
```

### In Neovim

```vim
" Check 1: Config has settings?
:lua print(vim.inspect(servers.omnisharp.settings))
" Should show your nested settings table

" Check 2: Client config has settings?
:lua print(vim.inspect(vim.lsp.get_clients({name='omnisharp'})[1].config.settings))
" Should show same as above

" Check 3: Command array (rarely helpful but possible)
:lua print(vim.inspect(vim.lsp.get_clients({name='omnisharp'})[1].cmd))
" Should show command with flattened args

" Check 4: LSP logs
:e ~/.local/state/nvim/lsp.log
" Look for RoslynExtensionsOptions entries
```

---

## Common Patterns

### Pattern 1: Correct Configuration

```lua
✓ Nested settings table
✓ PascalCase property names
✓ Boolean (not string) values
✓ Settings in proper table structure

omnisharp = {
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,     -- ✓ Correct
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,  -- ✓ Correct
    }
  }
}
```

### Pattern 2: Wrong Configuration

```lua
❌ Flat settings (no parent key)
❌ snake_case instead of PascalCase
❌ String values instead of boolean
❌ Settings at root level

omnisharp = {
  enable_analyzers_support = true,       -- ❌ Wrong
  EnableAnalyzersSupport = "true",       -- ❌ Wrong
  settings = {
    enable_editor_config = true,         -- ❌ Wrong
  }
}
```

---

## The Essential Fact

```
┌─────────────────────────────────────────────────────────────┐
│ YOUR SETTINGS ARE FLATTENED TO COMMAND-LINE ARGUMENTS       │
│ ONCE, AT T0.5, BY on_new_config                             │
│                                                             │
│ They are NOT sent via LSP protocol after startup            │
│ They are NOT shown in :LspInfo (only cmd array matters)    │
│                                                             │
│ VERIFY BY:                                                  │
│ $ ps aux | grep omnisharp                                   │
│                                                             │
│ If you see:                                                 │
│ RoslynExtensionsOptions:EnableAnalyzersSupport=true         │
│                                                             │
│ THEN YOUR SETTINGS ARE APPLIED ✓                            │
└─────────────────────────────────────────────────────────────┘
```

---

**Quick Reference Sheet Complete**
Use this alongside OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md for deep dives.
