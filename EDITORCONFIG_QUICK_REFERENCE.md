# EditorConfig with Roslyn and OmniSharp - Quick Reference

## TL;DR

**EditorConfig** is configuration files (`.editorconfig`) that Roslyn reads to configure:
- Code style rules (formatting, naming, language preferences)
- Analyzer behavior (severity, enabled/disabled rules)
- Formatter options (indentation, spacing, imports organization)

**OmniSharp** must have `FormattingOptions:EnableEditorConfigSupport = true` to read these files.

---

## 1. Minimal .editorconfig for C# Project

**File**: `.editorconfig` (in repository root)

```ini
root = true

[*.cs]
indent_style = space
indent_size = 4

# Code style
csharp_style_var_for_built_in_types = false
csharp_style_var_when_type_is_apparent = true

# Formatting
dotnet_diagnostic.IDE0055.severity = warning

# StyleCop (if using StyleCop.Analyzers)
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1309.severity = warning
```

---

## 2. OmniSharp Configuration for EditorConfig

**In Neovim init.lua**:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/path/to/solution'),
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,      -- Enable StyleCop/analyzers
      AnalyzeOpenDocumentsOnly = false,   -- Analyze whole solution
    },
    FormattingOptions = {
      EnableEditorConfigSupport = true,   -- READ .editorconfig files
      OrganizeImports = true,
    },
  },
}
```

**Critical**: `FormattingOptions:EnableEditorConfigSupport = true`

---

## 3. Rule Configuration Syntax

### Set Rule Severity (Any rule)
```ini
[*.cs]
dotnet_diagnostic.<RULE_ID>.severity = warning
```

**Severity values**: `suggestion`, `warning`, `error`, `none`

**Examples**:
```ini
# Style rules
dotnet_diagnostic.IDE0001.severity = warning   # Simplify name
dotnet_diagnostic.IDE0055.severity = error     # Format code

# StyleCop rules
dotnet_diagnostic.SA1116.severity = warning    # Split params
dotnet_diagnostic.SA1309.severity = warning    # Field naming

# Code quality rules
dotnet_analyzer_diagnostic.category-Security.severity = error
```

### Configure Language Options
```ini
[*.cs]
csharp_style_var_for_built_in_types = false
csharp_style_var_when_type_is_apparent = true
csharp_space_after_cast = false
dotnet_naming_style.pascal_style.capitalization = pascal_case
```

### Configure Specific Analyzer Behavior
```ini
[*.cs]
dotnet_code_quality.CA1810.api_surface = public,internal
dotnet_code_quality.exclude_async_void_methods = false
```

---

## 4. Complete Realistic .editorconfig

```ini
root = true

# All files
[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

# C# files
[*.cs]
indent_style = space
indent_size = 4

## Language Rules
# Variables
csharp_style_var_for_built_in_types = false
csharp_style_var_when_type_is_apparent = true
csharp_style_var_elsewhere = false

# Expressions
csharp_style_expression_bodied_methods = false
csharp_style_expression_bodied_properties = true
csharp_style_throw_expression = true
csharp_prefer_simple_using_statement = true

# Pattern matching
csharp_style_pattern_matching_over_as_with_null_check = true
csharp_style_pattern_matching_over_is_with_cast_check = true

## Formatting Rules
csharp_space_after_cast = false
csharp_space_after_keywords_in_control_flow_statements = true
csharp_space_between_method_declaration_parameter_list_parentheses = false
csharp_indent_case_contents = true
csharp_indent_switch_labels = true

## Naming Conventions
# Types should be PascalCase
dotnet_naming_style.pascal_case_style.capitalization = pascal_case

dotnet_naming_rule.types_should_be_pascal_case.symbols = type_symbols
dotnet_naming_rule.types_should_be_pascal_case.style = pascal_case_style
dotnet_naming_rule.types_should_be_pascal_case.severity = warning

dotnet_naming_symbols.type_symbols.applicable_kinds = class,struct,interface,enum,delegate
dotnet_naming_symbols.type_symbols.applicable_accessibilities = *

# Private fields should be _camelCase
dotnet_naming_style.private_field_style.capitalization = camel_case
dotnet_naming_style.private_field_style.required_prefix = _

dotnet_naming_rule.private_fields_should_be_underscore_camel_case.symbols = private_field_symbols
dotnet_naming_rule.private_fields_should_be_underscore_camel_case.style = private_field_style
dotnet_naming_rule.private_fields_should_be_underscore_camel_case.severity = warning

dotnet_naming_symbols.private_field_symbols.applicable_kinds = field
dotnet_naming_symbols.private_field_symbols.applicable_accessibilities = private

## Code Quality & Style Rules
# Enable all design rules
dotnet_analyzer_diagnostic.category-Design.severity = warning

# StyleCop rules
dotnet_diagnostic.SA1116.severity = warning    # Split params across lines
dotnet_diagnostic.SA1117.severity = warning    # Params should be aligned
dotnet_diagnostic.SA1309.severity = warning    # Fields should not start with underscore
dotnet_diagnostic.SA0001.severity = warning    # All analyzer rules

# Code style enforcement (make it a build error)
dotnet_diagnostic.IDE0055.severity = warning   # Format code

# JSON files
[*.json]
indent_style = space
indent_size = 2
```

---

## 5. Troubleshooting

### EditorConfig Not Applied?

**Check 1**: File is named `.editorconfig` (lowercase, no extension)
```bash
ls -la | grep editorconfig
```

**Check 2**: File is in project root or parent directory
```bash
find . -name ".editorconfig" -type f
```

**Check 3**: OmniSharp has `EnableEditorConfigSupport = true`
```vim
:LspInfo
# Look for: FormattingOptions = { EnableEditorConfigSupport = true, ... }
```

**Check 4**: Restart OmniSharp
```bash
pkill -f omnisharp
# Then reopen file in Neovim
```

### Rule Not Showing?

**Check 1**: Rule severity is not `none`
```ini
dotnet_diagnostic.SA1116.severity = warning  # ✅ Shows
dotnet_diagnostic.SA1116.severity = none     # ❌ Hidden
```

**Check 2**: Analyzer package is installed (e.g., StyleCop.Analyzers)
```bash
# In .csproj file
<ItemGroup>
  <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
</ItemGroup>
```

**Check 3**: Analyzer support is enabled in OmniSharp
```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,  -- ✅ Must be true
}
```

---

## 6. Configuration Precedence

Lower precedence → Higher precedence

1. Hardcoded Roslyn defaults
2. Global AnalyzerConfig (`~/.globalconfig`)
3. EditorConfig from parent directory (least specific)
4. EditorConfig from current directory (more specific)
5. Command-line options (highest - overrides everything)

**Example**: `.editorconfig` in subdirectory overrides parent `.editorconfig`

---

## 7. Common Rules Reference

| Rule ID | Name | Sets |
|---------|------|------|
| **IDE0055** | Format code | Indentation, spacing, newlines |
| **IDE0001** | Simplify name | Unnecessary qualification |
| **IDE0003** | Remove `this`/`me` | Removes unnecessary this |
| **IDE0008** | Use explicit type | Prefers explicit over `var` |
| **SA1116** | Split params | Parameters on separate lines |
| **SA1117** | Align params | Parameter alignment |
| **SA1309** | Field naming | Fields should not start with `_` |
| **SA1401** | Expose fields | Public fields not allowed |

---

## 8. Useful OmniSharp Settings Summary

```lua
settings = {
  -- Analyzer configuration
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,         -- Enable StyleCop/analyzers
    EnableImportCompletion = true,         -- Code completion from imports
    AnalyzeOpenDocumentsOnly = false,      -- Analyze entire solution (slower but thorough)
  },

  -- Formatting and EditorConfig
  FormattingOptions = {
    EnableEditorConfigSupport = true,      -- READ .editorconfig
    OrganizeImports = true,                -- Auto-organize using statements
  },

  -- Code quality
  Sdk = {
    IncludePrereleases = true,             -- Include preview SDKs
  },
}
```

---

## 9. Verification Commands

**Check if OmniSharp sees settings**:
```bash
ps aux | grep omnisharp | head -1
# Should show: FormattingOptions:EnableEditorConfigSupport=true
#             RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

**Check Neovim LSP config**:
```vim
:LspInfo
# Look for cmd and settings sections
```

**Force OmniSharp restart**:
```bash
pkill -f omnisharp
```

**Clear Neovim cache**:
```bash
rm -rf ~/.cache/nvim/luac/
```

---

## 10. Best Practices

1. **Place .editorconfig at repo root** - Applies to entire project
2. **Use `root = true`** - Prevents searching parent directories
3. **Enable EditorConfig in OmniSharp** - Must be explicitly enabled
4. **Set rule severity to `error` for CI/CD** - Breaks builds if violated
5. **Use file sections** - `[*.cs]` groups settings logically
6. **Version control .editorconfig** - Keep settings consistent across team
7. **Test configuration** - Verify with `:LspInfo` before committing
8. **Document team conventions** - Add comments explaining why rules matter

---

## 11. Example Workflow

1. **Create .editorconfig** in project root:
   ```bash
   cat > .editorconfig << 'EOF'
   root = true
   [*.cs]
   dotnet_diagnostic.SA1116.severity = warning
   EOF
   ```

2. **Enable in OmniSharp** (init.lua):
   ```lua
   FormattingOptions = {
     EnableEditorConfigSupport = true,
   }
   ```

3. **Restart Neovim**:
   ```bash
   pkill -f omnisharp
   nvim myfile.cs
   ```

4. **Verify**:
   ```vim
   :LspInfo
   ```

5. **See warnings** in code as you type!

