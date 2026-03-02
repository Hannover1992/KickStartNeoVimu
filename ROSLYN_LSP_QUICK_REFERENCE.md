# Roslyn & OmniSharp LSP - Quick Reference Guide

**For Developers:** Quick answers to common questions

---

## Quick Answers

### Q: What is Roslyn?
**A:** The .NET compiler platform (open source). Provides APIs for code analysis, compilation, and refactoring. Powers Visual Studio's IntelliSense.

**Key Point:** Roslyn = Language analysis engine

---

### Q: What is OmniSharp?
**A:** A wrapper around Roslyn workspaces that provides an LSP server. Connects any editor (VS Code, Vim, Neovim) to Roslyn's capabilities.

**Key Point:** OmniSharp = Roslyn's LSP translator

---

### Q: What is LSP?
**A:** Language Server Protocol. A standardized format for editors to communicate with language analysis servers via JSON-RPC messages.

**Key Point:** LSP = Editor-server communication protocol

---

### Q: Why aren't StyleCop warnings showing?
**A:** Most likely: `EnableAnalyzersSupport=false` (default). The setting must be explicitly enabled in configuration.

**Fix:** Add to init.lua:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,  -- THIS LINE IS CRITICAL
  }
}
```

---

### Q: How do diagnostics get from analyzer to my editor?

```
Analyzer (Roslyn)
  ↓ reports
Diagnostic object
  ↓ collected by
OmniSharp handler
  ↓ formatted as
LSP publishDiagnostics
  ↓ transmitted via
LSP protocol
  ↓ displayed by
Your editor (Neovim)
```

---

### Q: What's the relationship between Roslyn and Analyzers?

```
Roslyn (Compiler Platform)
  ├─ Provides APIs
  └─ Executes analyzers
    ├─ StyleCop.Analyzers (naming, formatting)
    ├─ FxCop (security, design)
    ├─ SonarAnalyzer (quality)
    └─ Custom analyzers (your rules)
```

**Key Point:** Roslyn = framework, Analyzers = plugins that run on Roslyn

---

### Q: Where does OmniSharp get configuration?

**Priority (highest to lowest):**
1. Local omnisharp.json
2. Global ~/.omnisharp/omnisharp.json
3. Command-line arguments
4. Environment variables (OMNISHARP_ prefix)
5. Hardcoded defaults

---

### Q: How does nvim-lspconfig convert Lua settings to OmniSharp?

The `on_new_config` function:

```
Lua settings table
  ↓ flattened into
Command-line arguments
  ↓ passed to
OmniSharp process
  ↓ parsed by
OmniSharp configuration system
  ↓ applied to
Roslyn analyzers
```

**Example:**
```lua
settings.RoslynExtensionsOptions.EnableAnalyzersSupport = true
  ↓
RoslynExtensionsOptions:EnableAnalyzersSupport=true
  ↓
Command line: "... RoslynExtensionsOptions:EnableAnalyzersSupport=true"
```

---

### Q: What are LSP ServerCapabilities?

**OmniSharp announces it can provide:**
- Code completion
- Go to definition
- Find references
- Hover information
- Code formatting
- Diagnostics (errors/warnings)
- Code actions (quick fixes)
- Symbol renaming
- Type information
- Syntax highlighting
- And ~12 more...

**Key Point:** Capabilities = "What features this LSP server supports"

---

### Q: What if configuration isn't applied?

**Debug checklist:**
```
1. ✓ Is RoslynExtensionsSupport=true in settings?
2. ✓ Is solution path (-s) correct?
3. ✓ Clear cache: rm -rf ~/.cache/nvim/luac/
4. ✓ Kill processes: pkill -f omnisharp
5. ✓ Restart Neovim
6. ✓ Check: ps aux | grep omnisharp
```

**Verify command line includes:**
- `-s /path/to/solution.sln`
- `RoslynExtensionsOptions:EnableAnalyzersSupport=true`

---

### Q: How do analyzers report problems?

**Each diagnostic includes:**
- **Id:** "SA1116" (unique rule identifier)
- **Severity:** Error/Warning/Info/Hint
- **Location:** file, line, column
- **Message:** Human-readable description
- **Tags:** Unnecessary/Deprecated/etc

---

### Q: Can I configure analyzers?

**Via multiple methods:**
1. `.editorconfig` file (best practice - shared with VS)
2. `.ruleset` file (MSBuild format)
3. `omnisharp.json` (OmniSharp-specific)
4. Environment variables (`OMNISHARP_RoslynExtensionsOptions:...`)
5. Command-line arguments

---

### Q: What's the difference between LSP push vs pull diagnostics?

**Push Model (OmniSharp default):**
- Server sends diagnostics whenever it wants
- Server decides when to analyze
- More proactive

**Pull Model (LSP 3.17+):**
- Client requests diagnostics on-demand
- Server responds to request
- More efficient

OmniSharp uses push model primarily.

---

### Q: Why does OmniSharp care about the solution path (-s)?

```
With -s /path/to/solution.sln:
  ├─ Loads all projects in solution
  ├─ Can analyze project dependencies
  ├─ Resolves types across projects
  └─ StyleCop runs on all files

Without -s:
  ├─ OmniSharp searches for solution
  ├─ May only find single project
  ├─ Limited cross-file analysis
  └─ Fewer warnings available
```

**Key Point:** Solution path determines analysis scope

---

### Q: How does Roslyn know about .editorconfig?

```
.editorconfig in project
  ↓ Roslyn reads automatically
  ↓ FormattingOptions:EnableEditorConfigSupport=true
  ↓ Applies style rules
  ↓ Formatters use rules
  ↓ OmniSharp reports violations
```

---

### Q: What happens during LSP initialization?

1. Editor sends `initialize` request
2. OmniSharp reads config files
3. OmniSharp loads Roslyn workspace
4. OmniSharp registers handlers
5. OmniSharp returns capabilities
6. Editor confirms: ready to send requests
7. OmniSharp can now serve completions, diagnostics, etc.

---

### Q: What's a handler?

**OmniSharp has 22+ handlers:**

| Handler | Does |
|---------|------|
| CompletionHandler | Responds to code completion requests |
| DefinitionHandler | Finds where symbol is defined |
| DiagnosticsHandler | Collects and sends error/warnings |
| FormattingHandler | Formats code |
| HoverHandler | Shows type info on hover |

**Key Point:** Handler = "I know how to respond to this LSP request"

---

### Q: How are analyzers executed?

**Roslyn execution model:**
```
Initialize (once per compilation)
  ↓
Register actions (SyntaxNodeAction, SymbolAction, etc.)
  ↓
For each action type:
  ├─ Actions run (order guaranteed: CompilationStart → Symbols → Nodes → End)
  ├─ No two actions from same analyzer run concurrently
  └─ Different analyzers may run in parallel
  ↓
Report diagnostics
```

---

### Q: What does "EnableImportCompletion" do?

**True:**
- IntelliSense suggests namespace imports
- Shows "using System;" completions
- Auto-adds missing using statements

**False:**
- No import completions
- Must manually type "using" statements

---

### Q: What does "AnalyzeOpenDocumentsOnly" do?

**False (recommended for style checking):**
- Analyze entire solution
- StyleCop warnings on all files
- More comprehensive checking
- May be slower

**True:**
- Only analyze files currently open in editor
- Faster but incomplete
- Good for large solutions with many projects

---

### Q: How is this different from local build errors?

```
Local build (dotnet build):
  ├─ Checks compilation errors only
  ├─ Shows in build output
  └─ No style rules

LSP Diagnostics (OmniSharp):
  ├─ Shows compilation errors
  ├─ Plus style violations (StyleCop)
  ├─ Plus design issues (FxCop)
  ├─ Shows in real-time as you type
  └─ No need to run build command
```

---

### Q: Can I suppress specific StyleCop warnings?

**Yes, multiple ways:**

1. **In code:**
```csharp
#pragma warning disable SA1116
// code here
#pragma warning restore SA1116
```

2. **In .editorconfig:**
```ini
[*.cs]
# Suppress SA1116
severity = none
```

3. **Via ruleset:**
```xml
<Rule Id="SA1116" Action="None" />
```

---

### Q: What's the actual LSP message format?

**Example diagnostic from OmniSharp:**
```json
{
  "method": "textDocument/publishDiagnostics",
  "params": {
    "uri": "file:///c%3A/path/UserController.cs",
    "diagnostics": [
      {
        "range": {
          "start": { "line": 55, "character": 25 },
          "end": { "line": 56, "character": 0 }
        },
        "severity": 2,
        "code": "SA1116",
        "source": "csharp",
        "message": "Split parameters must begin on new line"
      }
    ]
  }
}
```

---

### Q: Why is clearning cache important?

Neovim compiles Lua to bytecode (.luac) for speed:
```
~/.cache/nvim/luac/
  ├─ Contains compiled Lua bytecode
  ├─ Stale cache = old configuration
  └─ Clear with: rm -rf ~/.cache/nvim/luac/
```

If configuration changes don't take effect, clear cache + restart.

---

### Q: How do I verify OmniSharp got my settings?

```bash
# See actual running process
ps aux | grep omnisharp | grep -v grep

# Output should include:
# ... RoslynExtensionsOptions:EnableAnalyzersSupport=true ...
# ... -s /path/to/solution.sln ...
```

If settings aren't in the process, they weren't applied.

---

### Q: What's a "diagnostic"?

**In LSP context:**
A problem reported by the language server:
- Line and column location
- Error/warning/info severity
- Rule code (SA1116, CS8600, etc.)
- Human-readable message
- Optional: suggestion for fix

---

### Q: How is this all connected?

```
Developer writes code in Neovim
  ↓ (code changes)
Neovim tells OmniSharp via LSP
  ↓ (textDocument/didChange)
OmniSharp updates Roslyn workspace
  ↓
Roslyn re-compiles for semantic model
  ↓
Roslyn runs all loaded analyzers
  ├─ StyleCop checks formatting
  ├─ FxCop checks design
  └─ Custom analyzers check rules
  ↓
OmniSharp collects diagnostics
  ↓
OmniSharp sends via LSP
  ↓ (textDocument/publishDiagnostics)
Neovim receives notification
  ↓
Neovim shows red squiggles
  ↓
Developer sees warnings
```

---

## Troubleshooting Flowchart

```
StyleCop warnings not showing?
  ├─ Is EnableAnalyzersSupport=true?
  │  ├─ NO → Add to settings
  │  └─ YES → Continue
  ├─ Is solution path correct?
  │  ├─ NO → Fix -s parameter
  │  └─ YES → Continue
  ├─ Is StyleCop.Analyzers package installed?
  │  ├─ NO → dotnet add package StyleCop.Analyzers
  │  └─ YES → Continue
  ├─ Clear cache and restart
  │  ├─ rm -rf ~/.cache/nvim/luac/
  │  ├─ pkill -f omnisharp
  │  └─ nvim /path/to/file.cs
  ├─ Check: ps aux | grep omnisharp
  │  ├─ Settings in output?
  │  ├─ YES → Check :LspInfo
  │  └─ NO → Configuration not applied
  └─ Still not working?
     └─ Check: ~/.local/state/nvim/lsp.log
```

---

## Common Settings Reference

```json
{
  "RoslynExtensionsOptions": {
    "EnableAnalyzersSupport": true,        // CRITICAL for StyleCop
    "EnableImportCompletion": true,        // Suggest imports
    "AnalyzeOpenDocumentsOnly": false,    // true = fast, false = complete
    "DocumentAnalysisTimeoutMs": 30000    // Analyzer timeout
  },
  "FormattingOptions": {
    "EnableEditorConfigSupport": true,    // Read .editorconfig
    "OrganizeImports": true,              // Remove unused using
    "tabSize": 4,
    "insertSpaces": true
  }
}
```

---

## Key Files

| File | Purpose |
|------|---------|
| ~/.config/nvim/init.lua | Neovim config with omnisharp settings |
| ~/.omnisharp/omnisharp.json | Global OmniSharp config |
| ./.omnisharp/omnisharp.json | Project-specific OmniSharp config |
| .editorconfig | Formatting and style rules |
| .ruleset | MSBuild analyzer rules |
| ~/.local/state/nvim/lsp.log | OmniSharp debug log |
| ~/.cache/nvim/luac/ | Neovim Lua bytecode cache |

---

## One-Liner Fixes

```bash
# Clear cache and restart
rm -rf ~/.cache/nvim/luac/ && pkill -f omnisharp

# Check if settings applied
ps aux | grep omnisharp | grep -v grep | grep -i roslyn

# Monitor OmniSharp logs
tail -f ~/.local/state/nvim/lsp.log | grep -i analyzer

# Force LSP restart in Neovim
:LspRestart

# View all diagnostics
:Telescope diagnostics

# View current file diagnostics
:Telescope diagnostics bufnr=0
```

---

## Remember

1. **Configuration must be explicit** - defaults usually don't enable analyzers
2. **Solution path is important** - defines analysis scope
3. **Settings flow through layers** - Lua → CLI args → OmniSharp → Roslyn → Analyzers
4. **Restart is often needed** - Cache, processes, Neovim instance
5. **LSP is just protocol** - Roslyn does the real work, LSP delivers results

