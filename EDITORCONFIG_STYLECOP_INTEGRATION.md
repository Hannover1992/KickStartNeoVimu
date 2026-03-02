# EditorConfig + StyleCop Integration Guide for Neovim/OmniSharp

**Objective**: Get StyleCop analyzer warnings to appear in Neovim while respecting EditorConfig settings

---

## 1. Architecture Overview

```
.editorconfig (configuration)
    ↓
Roslyn Compiler (reads config)
    ↓
OmniSharp LSP Server (passes to client)
    ↓
Neovim/LSP Client (displays warnings)
```

**Key enabler**: `FormattingOptions:EnableEditorConfigSupport = true` in OmniSharp

---

## 2. Step-by-Step Setup

### Step 1: Create .editorconfig in Solution Root

**File**: `/path/to/solution/.editorconfig`

```ini
root = true

[*.cs]
indent_style = space
indent_size = 4

# StyleCop enforcement (if using StyleCop.Analyzers NuGet package)
dotnet_diagnostic.SA1000.severity = warning
dotnet_diagnostic.SA1001.severity = warning
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1117.severity = warning
dotnet_diagnostic.SA1309.severity = warning
```

**Verify file exists**:
```bash
ls -la /path/to/solution/.editorconfig
# Should show the file
```

### Step 2: Install StyleCop.Analyzers NuGet Package

Ensure your **project file** (.csproj) includes StyleCop:

```xml
<ItemGroup>
  <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
</ItemGroup>
```

**Verify installation**:
```bash
# After dotnet restore, check if it exists
find ~/.nuget/packages -name "stylecop.analyzers" | head -5
```

### Step 3: Configure OmniSharp in Neovim

**File**: `~/.config/nvim/init.lua` or your repo's linked init.lua

```lua
-- Define the servers table with omnisharp configuration
local servers = {
  omnisharp = {
    -- Use dotnet to call OmniSharp.dll directly
    cmd = {
      'dotnet',
      vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
      '-s', vim.fn.expand('/path/to/solution'),  -- Solution directory
      '-loglevel', 'Information',
    },

    -- Critical settings for EditorConfig and StyleCop support
    settings = {
      -- Enable analyzers (StyleCop, design, security rules)
      RoslynExtensionsOptions = {
        EnableAnalyzersSupport = true,        -- ⭐ ENABLES STYLECOP
        EnableImportCompletion = true,        -- Code completion from imports
        AnalyzeOpenDocumentsOnly = false,     -- Analyze entire solution
      },

      -- Enable reading .editorconfig files
      FormattingOptions = {
        EnableEditorConfigSupport = true,     -- ⭐ READS .editorconfig
        OrganizeImports = true,
        EnableEditorConfigSupport = true,
      },

      -- Optional: Fine-tune analyzer behavior
      Sdk = {
        IncludePrereleases = true,
      },
    },
  },
  -- ... other servers
}

-- Setup mason-lspconfig to handle server setup
require('mason-lspconfig').setup {
  handlers = {
    function(server_name)
      local server = servers[server_name] or {}
      server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
      require('lspconfig')[server_name].setup(server)
    end,
  },
}
```

### Step 4: Clear Cache and Restart

```bash
# 1. Clear Neovim Lua bytecode cache
rm -rf ~/.cache/nvim/luac/

# 2. Kill all OmniSharp processes
pkill -f omnisharp

# 3. Restart Neovim
nvim /path/to/solution/SomeFile.cs
```

### Step 5: Verify Configuration

**In Neovim**:
```vim
" Check LSP configuration
:LspInfo

" Should show:
" - cmd: starts with { "dotnet", ".../OmniSharp.dll", "-s", ... }
" - RoslynExtensionsOptions: { EnableAnalyzersSupport = true, ... }
" - FormattingOptions: { EnableEditorConfigSupport = true, ... }
```

**In terminal** (while Neovim has file open):
```bash
ps aux | grep omnisharp | grep -v grep
# Should show command like:
# dotnet /home/user/.local/share/nvim/mason/packages/omnisharp/libexec/OmniSharp.dll \
#   -s /path/to/solution \
#   -loglevel Information \
#   ... flattened settings ...
```

---

## 3. Understanding the Configuration

### FormattingOptions:EnableEditorConfigSupport

**What it does**:
- Tells OmniSharp to **read and apply** `.editorconfig` files
- When enabled, OmniSharp searches for `.editorconfig` up directory hierarchy
- Settings from `.editorconfig` override OmniSharp defaults

**What it doesn't do**:
- It doesn't enable analyzers (that's `EnableAnalyzersSupport`)
- It doesn't configure which rules are enabled (that's in `.editorconfig`)

### RoslynExtensionsOptions:EnableAnalyzersSupport

**What it does**:
- Enables **all Roslyn analyzers** including StyleCop
- Without this, analyzer warnings won't appear regardless of `.editorconfig`

**What it doesn't do**:
- It doesn't configure which specific analyzers run (that's `AnalyzeOpenDocumentsOnly`)
- It doesn't set rule severity (that's in `.editorconfig`)

### RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly

**What it does**:
- `false` = Analyze entire solution (thorough but slower)
- `true` = Only analyze files you have open (faster but incomplete)

**Recommended**: `false` for accurate analysis, `true` if performance is critical

---

## 4. Complete .editorconfig Example

```ini
# Root marker - prevents searching parent directories
root = true

# All files
[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

# C# specific
[*.cs]
indent_style = space
indent_size = 4

# ============================================================================
# CODE STYLE RULES (IDE rules - color/formatting suggestions in editor)
# ============================================================================

# Variable usage
csharp_style_var_for_built_in_types = false
csharp_style_var_when_type_is_apparent = true
csharp_style_var_elsewhere = false

# Expression preferences
csharp_style_expression_bodied_methods = false
csharp_style_expression_bodied_properties = true
csharp_style_expression_bodied_indexers = true
csharp_style_throw_expression = true
csharp_prefer_simple_using_statement = true

# Pattern matching
csharp_style_pattern_matching_over_as_with_null_check = true
csharp_style_pattern_matching_over_is_with_cast_check = true

# Null-coalescing and conditional operator preferences
dotnet_style_coalesce_expression = true
dotnet_style_prefer_compound_assignment = true
dotnet_style_prefer_conditional_expression_over_assignment = true

# ============================================================================
# FORMATTING RULES (IDE0055 and related - actual formatting)
# ============================================================================

# Spacing
csharp_space_after_cast = false
csharp_space_after_keywords_in_control_flow_statements = true
csharp_space_between_method_declaration_parameter_list_parentheses = false
csharp_space_between_method_declaration_empty_parameter_list_parentheses = false
csharp_space_between_method_call_name_and_opening_parenthesis = false
csharp_space_between_method_call_parameter_list_parentheses = false

# Indentation
csharp_indent_case_contents = true
csharp_indent_switch_labels = true
csharp_indent_block_contents = true
csharp_indent_braces = false
csharp_indent_case_contents_when_block = false

# New lines
csharp_new_line_before_open_brace = all
csharp_new_line_before_else = true
csharp_new_line_before_catch = true
csharp_new_line_before_finally = true

# ============================================================================
# NAMING CONVENTIONS
# ============================================================================

# Define style: PascalCase
dotnet_naming_style.pascal_case_style.capitalization = pascal_case

# Define style: camelCase with leading underscore (private fields)
dotnet_naming_style.camel_case_with_underscore.capitalization = camel_case
dotnet_naming_style.camel_case_with_underscore.required_prefix = _

# Types (classes, interfaces, structs, enums, delegates) should be PascalCase
dotnet_naming_symbols.type_symbols.applicable_kinds = class,struct,interface,enum,delegate,record
dotnet_naming_symbols.type_symbols.applicable_accessibilities = public,internal,private,protected,protected_internal,private_protected

dotnet_naming_rule.types_should_be_pascal_case.symbols = type_symbols
dotnet_naming_rule.types_should_be_pascal_case.style = pascal_case_style
dotnet_naming_rule.types_should_be_pascal_case.severity = warning

# Private fields should be _camelCase
dotnet_naming_symbols.private_field_symbols.applicable_kinds = field
dotnet_naming_symbols.private_field_symbols.applicable_accessibilities = private

dotnet_naming_rule.private_fields_should_be_prefixed.symbols = private_field_symbols
dotnet_naming_rule.private_fields_should_be_prefixed.style = camel_case_with_underscore
dotnet_naming_rule.private_fields_should_be_prefixed.severity = warning

# ============================================================================
# STYLECOP RULES (SA rules - enforce C# style conventions)
# ============================================================================

# Spacing rules
dotnet_diagnostic.SA1000.severity = warning    # Keywords should be followed by space
dotnet_diagnostic.SA1001.severity = warning    # Commas should not be preceded by whitespace
dotnet_diagnostic.SA1002.severity = warning    # Semicolons should not be preceded by whitespace
dotnet_diagnostic.SA1003.severity = warning    # Operators should be separated by whitespace
dotnet_diagnostic.SA1004.severity = warning    # Documentation line should begin with single space
dotnet_diagnostic.SA1005.severity = warning    # Single line comment should begin with single space
dotnet_diagnostic.SA1006.severity = warning    # Preprocessor keyword should not be preceded by space
dotnet_diagnostic.SA1007.severity = warning    # Operator keyword should be surrounded by space
dotnet_diagnostic.SA1008.severity = warning    # Opening parenthesis should not be preceded by space

# Indentation rules
dotnet_diagnostic.SA1025.severity = warning    # Code should not contain multiple whitespace in a row
dotnet_diagnostic.SA1027.severity = warning    # Tabs and spaces should not be mixed

# Brace spacing rules
dotnet_diagnostic.SA1100.severity = warning    # Do not prefix local calls with this

# Method declaration rules
dotnet_diagnostic.SA1110.severity = warning    # Opening parenthesis or bracket should not be followed by space
dotnet_diagnostic.SA1111.severity = warning    # Closing parenthesis should not be preceded by space
dotnet_diagnostic.SA1112.severity = warning    # Closing parenthesis should be on line of last parameter
dotnet_diagnostic.SA1113.severity = warning    # Comma should not be followed by whitespace
dotnet_diagnostic.SA1114.severity = warning    # Parameter list should not contain multiple lines per parameter
dotnet_diagnostic.SA1115.severity = warning    # Parameter should follow comma
dotnet_diagnostic.SA1116.severity = warning    # Split parameters should start on line after declaration
dotnet_diagnostic.SA1117.severity = warning    # Parameters should be on same line or separate lines
dotnet_diagnostic.SA1118.severity = warning    # Parameter should not span multiple lines

# Field naming rules
dotnet_diagnostic.SA1306.severity = warning    # Field names should begin with lower-case letter
dotnet_diagnostic.SA1307.severity = warning    # Accessible fields should begin with upper-case letter
dotnet_diagnostic.SA1308.severity = warning    # Variable names should not be prefixed
dotnet_diagnostic.SA1309.severity = warning    # Field names should not begin with underscore
dotnet_diagnostic.SA1310.severity = warning    # Field names should not contain underscore

# ============================================================================
# CODE QUALITY RULES (CA and other rules)
# ============================================================================

# Enable security rules
dotnet_analyzer_diagnostic.category-Security.severity = warning

# Enable design rules
dotnet_analyzer_diagnostic.category-Design.severity = warning

# Enable performance rules
dotnet_analyzer_diagnostic.category-Performance.severity = suggestion

# ============================================================================
# ENABLE THESE RULES ON BUILD (only for strong enforcement)
# ============================================================================

# To make style violations break the build:
# Set severity = error instead of warning
# Then in .csproj: <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>

# Example (commented out - uncomment to enforce on build):
# dotnet_diagnostic.IDE0055.severity = error   # Format issues = build error
# dotnet_diagnostic.SA1116.severity = error    # Parameter splitting = build error
```

---

## 5. Optional: .csproj Configuration

For **build-time enforcement** of EditorConfig rules:

```xml
<PropertyGroup>
  <!-- Enable code style analysis on build -->
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>

  <!-- Enable code quality analysis on build -->
  <EnableNETAnalyzers>true</EnableNETAnalyzers>

  <!-- Which rules to enable (Minimum, Recommended, All) -->
  <AnalysisMode>Recommended</AnalysisMode>

  <!-- Treat style warnings as errors (for CI/CD) -->
  <!-- <TreatWarningsAsErrors>true</TreatWarningsAsErrors> -->
</PropertyGroup>
```

Then in `dotnet build`:
```bash
dotnet build
# Will show StyleCop and style violations as build warnings/errors
```

---

## 6. Verification Checklist

Before assuming configuration works:

- [ ] `.editorconfig` file exists in solution directory: `ls .editorconfig`
- [ ] StyleCop.Analyzers is in .csproj: `cat *.csproj | grep -i stylecop`
- [ ] OmniSharp cmd uses `dotnet` + DLL path (not wrapper)
- [ ] `FormattingOptions:EnableEditorConfigSupport = true` in init.lua
- [ ] `RoslynExtensionsOptions:EnableAnalyzersSupport = true` in init.lua
- [ ] Cache cleared: `rm -rf ~/.cache/nvim/luac/`
- [ ] OmniSharp process killed: `pkill -f omnisharp`
- [ ] Neovim restarted and file reopened
- [ ] `:LspInfo` shows correct cmd and settings
- [ ] `ps aux | grep omnisharp` shows flattened settings in command line

---

## 7. Troubleshooting

### Symptom: No StyleCop warnings appear

**Step 1**: Check if OmniSharp has analyzer support enabled
```vim
:LspInfo
```
Look for: `RoslynExtensionsOptions = { EnableAnalyzersSupport = true, ... }`

**If not**:
- Add `EnableAnalyzersSupport = true` to settings in init.lua
- Restart Neovim

**Step 2**: Check if EditorConfig is being read
```vim
:LspInfo
```
Look for: `FormattingOptions = { EnableEditorConfigSupport = true, ... }`

**If not**:
- Add `EnableEditorConfigSupport = true` to settings
- Ensure `.editorconfig` file exists in solution directory

**Step 3**: Check if `.editorconfig` has StyleCop rules defined
```bash
cat .editorconfig | grep -i "SA1"
```

**If empty**:
- Add StyleCop rule definitions (see section 4)

**Step 4**: Verify StyleCop.Analyzers is installed
```bash
# After running dotnet restore in solution
find ~/.nuget/packages -name "stylecop.analyzers" | head -1
```

**If not found**:
- Add to .csproj: `<PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />`
- Run `dotnet restore`

### Symptom: EditorConfig changes don't take effect

**Solution**: Clear cache and restart
```bash
rm -rf ~/.cache/nvim/luac/
pkill -f omnisharp
# Reopen file in Neovim
```

### Symptom: Rule severity set but still not showing

**Check**: Is severity set to `none`?
```bash
grep "dotnet_diagnostic.SA1116.severity" .editorconfig
```

**If it says `none`**: Change to `warning` or `error`

### Symptom: Performance is very slow

**Solution**: Use `AnalyzeOpenDocumentsOnly = true` to reduce load
```lua
RoslynExtensionsOptions = {
  AnalyzeOpenDocumentsOnly = true,  -- Only current file
}
```

---

## 8. Complete Working Example

Assuming your solution is at `/home/user/MyProject/MySolution.sln`:

**1. Create .editorconfig**:
```bash
cat > /home/user/MyProject/.editorconfig << 'EOF'
root = true
[*.cs]
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1309.severity = warning
EOF
```

**2. Update init.lua**:
```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', '/home/user/MyProject',
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      AnalyzeOpenDocumentsOnly = false,
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,
    },
  },
}
```

**3. Restart**:
```bash
pkill -f omnisharp
rm -rf ~/.cache/nvim/luac/
nvim /home/user/MyProject/Program.cs
```

**4. Verify**:
```vim
:LspInfo
# Should show RoslynExtensionsOptions with EnableAnalyzersSupport = true
# Should show FormattingOptions with EnableEditorConfigSupport = true
```

**5. See warnings**:
- Open any C# file
- You should see StyleCop warnings (if code violates rules)

---

## 9. Summary

| Component | Purpose | Configuration |
|-----------|---------|----------------|
| **.editorconfig** | Define rule severity and formatting | File in solution directory |
| **EnableAnalyzersSupport** | Enable analyzers (StyleCop, etc.) | OmniSharp setting = true |
| **EnableEditorConfigSupport** | Read .editorconfig files | OmniSharp setting = true |
| **RoslynExtensionsOptions** | Analyzer behavior (scope, threading) | OmniSharp settings |
| **StyleCop.Analyzers NuGet** | Package providing SA* rules | .csproj ItemGroup |

When all are configured correctly → StyleCop warnings appear in Neovim as you type!

---

## 10. Advanced: Custom .editorconfig Rules

You can create project-specific rule configurations:

```ini
# Only for test files
[*Tests.cs]
dotnet_diagnostic.SA1309.severity = none  # Allow underscore prefix in tests

# Only for generated code
[*.Designer.cs]
generated_code = true  # Excluded from most rules

# Only for Domain-Driven Design contexts
[*Domain/*.cs]
dotnet_diagnostic.SA1402.severity = none  # Allow multiple classes per file in Domain folder
```

