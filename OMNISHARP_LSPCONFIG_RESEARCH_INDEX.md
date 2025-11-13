# OmniSharp LSP Settings Flattening - Complete Research Index

**Date:** 2025-11-13
**Topic:** How nvim-lspconfig flattens OmniSharp settings to command-line arguments
**Status:** Complete analysis with technical deep-dives and visual guides

---

## Quick Navigation

### For Quick Understanding (5 min read)
- **[OMNISHARP_FLATTEN_VISUAL_GUIDE.md](OMNISHARP_FLATTEN_VISUAL_GUIDE.md)** - Visual walkthroughs, decision trees, quick reference

### For Debugging Issues (10 min read)
- **[OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md](OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md)** - Exactly when settings apply, timing diagrams, verification scripts

### For Technical Understanding (30 min read)
- **[OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md](OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md)** - Complete algorithm explanation, LSP startup sequence, all gory details

---

## The Four Research Questions - Answered

### 1. How does the flatten() function in on_new_config work?

**Location:** nvim-lspconfig omnisharp.lua lines ~58-70

**Summary:** Recursive table traversal that converts nested Lua tables to colon-delimited command-line arguments.

```lua
Algorithm:
  For each key-value pair:
    If value is table → recurse and prepend key with ':'
    Else (scalar) → format as key=value
  Return array of formatted strings

Example:
  Input:  {RoslynExtensionsOptions = {EnableAnalyzersSupport = true}}
  Output: ["RoslynExtensionsOptions:EnableAnalyzersSupport=true"]
```

**Key Behaviors:**
- Handles arbitrary nesting depth
- nil values are skipped (not included in pairs iteration)
- Boolean values converted to strings "true"/"false" via vim.inspect()
- Preserves order of iteration (Lua 5.1+ table iteration)

**For Details:** See OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md, Section "The Flatten Function"

---

### 2. What format does OmniSharp expect for settings on command line?

**Answer:** Colon-delimited configuration arguments following OmniSharp's internal configuration schema

```bash
Format: ParentKey:ChildKey=value

Examples:
  RoslynExtensionsOptions:EnableAnalyzersSupport=true
  FormattingOptions:EnableEditorConfigSupport=true
  Sdk:IncludePrereleases=true
  DotNet:enablePackageRestore=false

Requirements:
  - PascalCase for property names (not snake_case)
  - Values as strings: "true", "false", "42"
  - Colon as nesting delimiter (not dot)
  - Each argument separate command-line parameter
```

**OmniSharp Parsing:**
1. Parse command-line arguments
2. Split on ':' and '=' to extract hierarchy
3. Build configuration object
4. Merge with omnisharp.json and defaults
5. Command-line args have HIGHEST priority

**For Details:** See OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md, Section "What format does OmniSharp expect"

---

### 3. Why might RoslynExtensionsOptions be empty in :LspInfo but present in config?

**Answer:** :LspInfo displays settings table AS CONFIGURED, not as applied. The settings are actually being passed as command-line arguments (flattened), which :LspInfo doesn't display.

**Verification:** Check the running process
```bash
ps aux | grep omnisharp | grep -v grep
# If output contains: RoslynExtensionsOptions:EnableAnalyzersSupport=true
# THEN: Settings ARE applied ✓

# If output shows NO flattened settings:
# THEN: Debug why on_new_config didn't flatten them
```

**Root Causes (if truly empty):**
1. Settings not defined in servers.omnisharp.settings table
2. servers variable out of scope during setup()
3. Multiple setup() calls (first one wins)
4. Old OmniSharp process still running (needs pkill -f omnisharp)
5. Using deprecated root-level flags (enable_roslyn_analyzers instead of settings table)

**For Details:** See OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md, Section "Why RoslynExtensionsOptions Might Be Empty"

---

### 4. Does on_new_config run before or after the server starts?

**Answer:** BEFORE the server spawns. It runs at T0.5 (pre-spawn phase) to build the complete command-line arguments.

**Timeline:**
- T0: Neovim starts, loads init.lua
- T0.25: User opens C# file, LSP detection begins
- **T0.5: on_new_config called** (PRE-SPAWN) ← Settings flattened here
- T0.6: Process spawned with complete command array
- T0.7: OmniSharp loads configuration from command-line args
- T1+: LSP handshake begins

**Critical Implications:**
- on_new_config runs exactly ONCE per LSP instance
- Settings embedded in command-line arguments, not sent via LSP protocol
- Cannot change settings without :LspRestart (must respawn process)
- Changing init.lua without :LspRestart has no effect

**For Details:** See OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md, Section "Does on_new_config run before or after the server starts"

---

## Document Map

### Core Technical Documents

#### 1. OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md
**Purpose:** Complete technical reference with algorithm details
**Length:** ~2000 lines
**Contents:**
- The flatten() function explained line-by-line
- The on_new_config() function execution steps
- Complete command generation example
- Settings structure requirements
- Version history and breaking changes (April 2024)
- Common mistakes and how to fix them
- Debugging guide

**Best For:** Understanding HOW the system works in detail

---

#### 2. OMNISHARP_FLATTEN_VISUAL_GUIDE.md
**Purpose:** Quick reference with visual walkthroughs
**Length:** ~500 lines
**Contents:**
- Animation-style flatten() process visualization
- Visual command building pipeline
- Complete example with diagrams
- Timing visualization
- Decision tree for debugging
- Verification checklist
- Common patterns (right vs wrong)

**Best For:** Visual learners, quick reference, debugging flowchart

---

#### 3. OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md
**Purpose:** Deep dive into exact timing and execution order
**Length:** ~600 lines
**Contents:**
- Three research questions with detailed answers
- Precise timing diagram with seconds marked
- Lua call stack during execution
- Settings persistence explanation
- Example timeline showing how changes propagate
- Verification script (bash)
- Summary table

**Best For:** Understanding when things happen, debugging timing issues

---

### Related Documentation

#### From Previous Research (Cross-Reference)
- **CLAUDE.md** - Final solution summary (quick TL;DR)
- **OMNISHARP_SETTINGS_FLOW_ANALYSIS.md** - Flow analysis with test cases
- **OMNISHARP_LSP_IMPLEMENTATION.md** - Configuration patterns and examples
- **OMNISHARP_LSP_SETTINGS_GUIDE.md** - LSP specification research

---

## Key Insights Summary

### The Flattening Process

```
Nested Lua Table          Flattening Algorithm           Command-Line Arguments
──────────────────       ────────────────────           ──────────────────────

{
  RoslynExtensions... = {   1. Iterate table
    Enable...=true,   ────► 2. Detect nested table
    Analyze...=false,        3. Recurse
  },                         4. Prepend parent key
  FormattingOptions = {      5. Add ':'
    Enable...=true,     ────►  separator
  }                          6. Return strings
}                            7. Append to cmd array

                             RoslynExtensionsOptions:Enable...=true
                             RoslynExtensionsOptions:Analyze...=false
                             FormattingOptions:Enable...=true
```

### The Timing Critical Point

```
Neovim Lifecycle:

T0    ┌─ init.lua loads
      │  servers.omnisharp defined
      │  on_new_config callback registered
      │
T0.5  │  ⭐️ on_new_config CALLED ⭐️
      │  │ Flattens settings to CLI args
      │  │ Builds complete cmd array
      │  │ SETTINGS FROZEN at this point
      │
T0.6  ├─ Process spawns with cmd
      │  OmniSharp reads command-line
      │  Configuration loaded
      │  Analyzers enabled ✓
      │
T1+   ├─ LSP handshake
      │  Normal operation
      │
T10   ├─ User edits init.lua
      │  (on_new_config does NOT run)
      │  Settings still old ✗
      │
T11   ├─ User runs :LspRestart
      │  (on_new_config called AGAIN)
      │  New settings flattened ✓
      │  Process respawned
      └─ Settings now applied ✓
```

### The Essential Fact

```
┌──────────────────────────────────────────────────────────────┐
│ SETTINGS ARE PASSED AS COMMAND-LINE ARGUMENTS                │
│                                                              │
│ NOT via LSP initializationOptions (ignored by OmniSharp)    │
│ NOT via workspace/didChangeConfiguration (LSP protocol)    │
│ NOT via omnisharp.json override                             │
│                                                              │
│ They are FLATTENED to command-line args                    │
│ at PRE-SPAWN time (T0.5)                                   │
│ by the on_new_config() callback                             │
│                                                              │
│ This is why:                                                 │
│ ✓ Settings are applied on startup                           │
│ ✓ OmniSharp receives them reliably                          │
│ ✓ They override omnisharp.json                              │
│ ✗ They can't change without process restart                │
│ ✗ :LspInfo doesn't show flattened form                     │
│ ✗ Changing init.lua doesn't auto-apply                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Practical Scenarios and Solutions

### Scenario 1: Debugger asks "Where do my settings go?"

**Answer Flow:**
1. Settings defined in init.lua: `servers.omnisharp.settings = {}`
2. on_new_config called (T0.5)
3. flatten() processes settings table
4. Returns array of command-line args
5. Appended to cmd array
6. Process spawned with complete command
7. OmniSharp parses command-line args
8. Configuration applied ✓

**Verification:**
```bash
ps aux | grep omnisharp | grep EnableAnalyzersSupport
```

---

### Scenario 2: Settings show empty in :LspInfo

**Diagnosis:**
- Check if actually empty (not just display issue)
- Verify running process has flattened settings
- Check if on_new_config was called
- Verify servers.omnisharp in scope

**Solution:**
```bash
# 1. Check running process
ps aux | grep omnisharp | head -1

# 2. If no flattened settings → fix configuration
# 3. If flattened settings present → :LspInfo is just not showing them (normal)

# 3. If process not running → start C# file in Neovim
nvim SomeFile.cs
```

---

### Scenario 3: Changed init.lua but settings didn't apply

**Expected Behavior:**
- Edit init.lua
- Run `:LspRestart` (required!)
- Settings applied to new process

**What NOT to do:**
- ✗ Just edit and save init.lua (on_new_config won't be called)
- ✗ Open another C# file (uses existing LSP connection)
- ✗ Source init.lua without :LspRestart (callback already ran)

---

### Scenario 4: Multiple setup() calls causing issues

**Problem:** Only first setup() call is processed
```lua
require('lspconfig').omnisharp.setup(config1)  -- ✓ Works
require('lspconfig').omnisharp.setup(config2)  -- ✗ Ignored
```

**Solution:** Use mason-lspconfig handler
```lua
require('mason-lspconfig').setup {
  handlers = {
    omnisharp = function()
      require('lspconfig').omnisharp.setup(config)  -- ✓ Controlled call
    end
  }
}
```

---

## Verification Checklist

### Quick Verification (1 minute)

```bash
# 1. Is OmniSharp running with your settings?
ps aux | grep omnisharp | grep EnableAnalyzersSupport
# YES → Settings applied ✓
# NO  → Debugging needed

# 2. Is process using correct path?
ps aux | grep omnisharp | grep -o "OmniSharp.dll[^[:space:]]*"
# Should show: /path/to/mason/packages/omnisharp/libexec/OmniSharp.dll

# 3. Has host PID?
ps aux | grep omnisharp | grep hostPID
# Should show: --hostPID 12345 (some number)
```

### Complete Verification (5 minutes)

In Neovim:
```vim
" 1. Check config defined
:lua print(vim.inspect(servers.omnisharp.settings))

" 2. Check client received it
:lua print(vim.inspect(vim.lsp.get_clients({name='omnisharp'})[1].config.settings))

" 3. Check logs
:e ~/.local/state/nvim/lsp.log
" Search for: RoslynExtensionsOptions
```

---

## Document Cross-References

### For Understanding flatten():
1. OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md → "The Flatten Function"
2. OMNISHARP_FLATTEN_VISUAL_GUIDE.md → "The Flatten Function - Visual Walkthrough"
3. OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md → "Answer to Question 1"

### For Understanding on_new_config Timing:
1. OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md → "Complete Timing Sequence"
2. OMNISHARP_FLATTEN_VISUAL_GUIDE.md → "Timing Visualization"
3. OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md → "Timing Diagram"

### For Debugging Settings:
1. OMNISHARP_FLATTEN_VISUAL_GUIDE.md → "Decision Tree - Why Settings Appear Empty"
2. OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md → "Why RoslynExtensionsOptions Might Be Empty"
3. OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md → "Verification - Prove Settings Were Applied"

### For Common Mistakes:
1. OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md → "Common Pitfalls and Solutions"
2. OMNISHARP_FLATTEN_VISUAL_GUIDE.md → "Common Patterns"
3. OMNISHARP_LSP_IMPLEMENTATION.md → "Common Issues and Solutions"

---

## Technical References

### Source Code Locations
- **nvim-lspconfig omnisharp.lua** (GitHub)
  - Lines ~5-42: default_config
  - Lines ~46-78: on_new_config function
  - Lines ~58-70: flatten function (local)

### Related Projects
- nvim-lspconfig: https://github.com/neovim/nvim-lspconfig
- OmniSharp: https://github.com/OmniSharp/omnisharp-roslyn
- Neovim LSP: https://neovim.io/doc/user/lsp.html

### Standards
- LSP Specification 3.17: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/

---

## Summary Table

| Question | Quick Answer | Detailed Answer Location |
|----------|--------------|--------------------------|
| **How does flatten() work?** | Recursive table traversal, prepends parent keys with ':' | OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md |
| **What format does OmniSharp expect?** | Colon-delimited: `ParentKey:ChildKey=value` | OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md |
| **Why is RoslynExtensionsOptions empty?** | :LspInfo doesn't show flattened form, check process | OMNISHARP_FLATTEN_VISUAL_GUIDE.md (Decision Tree) |
| **When does on_new_config run?** | T0.5 (pre-spawn), ONCE per LSP instance | OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md |
| **How to verify settings applied?** | `ps aux \| grep omnisharp \| grep EnableAnalyzersSupport` | OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md (Verification) |
| **How to apply new settings?** | `:LspRestart` to respawn with new config | OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md (Why Settings Can't Change) |

---

## Document Statistics

| Document | Lines | Topics | Best For |
|----------|-------|--------|----------|
| OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md | ~1200 | Algorithm, timing, debugging | Deep understanding |
| OMNISHARP_FLATTEN_VISUAL_GUIDE.md | ~550 | Visuals, decision trees, patterns | Quick reference |
| OMNISHARP_ON_NEW_CONFIG_TIMING_DETAILED.md | ~700 | Timing, call stacks, verification | Debugging |

**Total:** ~2450 lines of technical documentation

---

## Getting Started

### If you have 5 minutes:
1. Read: OMNISHARP_FLATTEN_VISUAL_GUIDE.md "How It Works"
2. Run: Verification commands
3. Understand: The flattening happens once at T0.5

### If you have 15 minutes:
1. Read: OMNISHARP_FLATTEN_VISUAL_GUIDE.md (all)
2. Skim: OMNISHARP_SETTINGS_FLATTENING_TECHNICAL_ANALYSIS.md (flatten function section)
3. Understand: What, When, and How settings are applied

### If you have 45 minutes:
1. Read: All three technical documents in order
2. Study: Timing diagrams and call stacks
3. Practice: Run verification scripts
4. Understand: Complete LSP startup sequence

---

**Research Completed:** 2025-11-13
**Coverage:** Comprehensive technical analysis of nvim-lspconfig OmniSharp settings flattening mechanism
**Status:** Ready for reference and debugging
