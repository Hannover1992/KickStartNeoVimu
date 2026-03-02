# Roslyn EditorConfig Integration Research

**Research Date**: 2025-11-13
**Source**: GitHub (dotnet/roslyn), Microsoft Learn Documentation, OmniSharp Project
**Objective**: Understand how Roslyn integrates with EditorConfig for diagnostic configuration

---

## 1. How Roslyn Integrates with EditorConfig

### Core Integration

Roslyn (the .NET Compiler Platform) has **first-class EditorConfig support built into the compiler itself**. This means:

1. **Native Support**: EditorConfig files are automatically recognized and parsed by Roslyn during compilation
2. **Compiler Level**: Configuration happens at the compiler level, not just in the IDE
3. **Build-Time Enforcement**: EditorConfig settings are enforced both in:
   - Interactive editing (in Visual Studio/Neovim via LSP)
   - Command-line builds (`dotnet build`)

### Configuration Files Roslyn Recognizes

Roslyn supports **two types** of configuration files:

#### 1. EditorConfig Files (`.editorconfig`)
- **File name**: `.editorconfig`
- **Format**: INI-style sections with glob patterns
- **Scope**: Per-file or per-directory
- **Search mechanism**: Searches directory hierarchy upward; stops at `root = true`
- **Example**:
  ```ini
  [*.cs]
  indent_style = space
  indent_size = 4
  dotnet_naming_style.my_style.capitalization = pascal_case
  ```

#### 2. Global AnalyzerConfig Files (`.globalconfig`)
- **File name**: `.globalconfig` (or `<PackageName>.globalconfig` for NuGet packages)
- **Scope**: Applies to entire project regardless of file paths
- **Format**: Similar INI format, but with `is_global = true` header
- **When used**: For generated files, NuGet package defaults, or project-wide settings

### Configuration Hierarchy and Precedence

When conflicts occur, Roslyn applies this precedence (highest to lowest):

1. **Command-line compiler options** - Override everything
2. **Later entries in same file** - Win over earlier entries
3. **EditorConfig files in deeper paths** - Override parent directories
4. **EditorConfig settings** - Override `.globalconfig` settings
5. **Earlier entries in same file** - Lowest precedence

**Example**:
```ini
# Root .editorconfig
[*.cs]
dotnet_naming_style.style1.capitalization = pascal_case

# Subdirectory/.editorconfig (wins)
[*.cs]
dotnet_naming_style.style1.capitalization = camel_case
```

---

## 2. What Can Be Configured via EditorConfig

Roslyn supports three major categories of rules via EditorConfig:

### A. Code Style Rules (IDE Rules)

**Format**: `dotnet_diagnostic.<rule-ID>.severity = <severity>`
**Rule IDs**: IDE0001 through IDE0380+

**Examples of Configurable Style Rules**:

| Rule | Purpose | EditorConfig Setting |
|------|---------|----------------------|
| IDE0001 | Remove unnecessary name qualification | `dotnet_diagnostic.IDE0001.severity = warning` |
| IDE0055 | Format code (indentation, spacing) | `dotnet_diagnostic.IDE0055.severity = error` |
| IDE0003 | Remove unnecessary `this` or `me` | `dotnet_diagnostic.IDE0003.severity = warning` |
| IDE0008 | Use explicit type over `var` | `csharp_style_var_for_built_in_types = false` |

**Severity levels**:
- `suggestion` - Light bulb in Visual Studio (informational)
- `warning` - Shows as warning during build
- `error` - Breaks build (treated as compiler error)
- `none` - Disables the rule

### B. Language and Formatting Options

**C# and VB Specific Options**:

```ini
[*.cs]
# Indentation and spacing
csharp_indent_case_contents = true
csharp_space_after_cast = false
csharp_space_after_keywords_in_control_flow_statements = true

# Variable preferences
csharp_style_var_for_built_in_types = false
csharp_style_var_when_type_is_apparent = true
csharp_style_var_elsewhere = false

# Expression preferences
csharp_style_expression_bodied_methods = true
csharp_style_throw_expression = true
csharp_style_pattern_matching_over_is_with_cast_check = true

# Naming conventions (define a custom style)
dotnet_naming_style.pascal_case_style.capitalization = pascal_case
dotnet_naming_rule.types_should_be_pascal_case.symbols = types
dotnet_naming_rule.types_should_be_pascal_case.style = pascal_case_style
dotnet_naming_rule.types_should_be_pascal_case.severity = warning
```

**Language Options** (apply to both C# and VB):

```ini
[*.{cs,vb}]
# Modifier preferences
csharp_prefer_static_local_function = true
dotnet_style_require_accessibility_modifiers = for_non_interface_members

# Organization options
dotnet_separate_import_directive_groups = false
dotnet_sort_system_directives_first = true
```

### C. Code Quality Rules

**Format**: `dotnet_code_quality.<RuleId>.<OptionName> = <Value>`
**or**: `dotnet_analyzer_diagnostic.category-<Category>.severity = <Severity>`

**Examples**:

```ini
# Configure specific rule behavior
dotnet_code_quality.CA1810.api_surface = public,internal

# Configure entire category
dotnet_analyzer_diagnostic.category-Security.severity = error
dotnet_analyzer_diagnostic.category-Performance.severity = warning

# Per-category rule application
dotnet_code_quality.exclude_async_void_methods = false
dotnet_code_quality.null_check_validation_methods = Validate
```

**Available Categories** (12 total):
- Design
- Documentation
- Security
- Performance
- Reliability
- Naming
- Maintainability
- Globalization
- Portability/Interoperability
- Usage
- Style
- SingleFile

---

## 3. How EditorConfig Affects Analyzer Behavior

### Automatic Rule Application

When Roslyn encounters an EditorConfig file:

1. **Discovery**: Searches upward from the file being compiled
2. **Parsing**: Reads and parses all `.editorconfig` files found
3. **Matching**: Determines which settings apply via glob patterns (`[*.cs]`)
4. **Application**: Applies configuration to diagnostic rules

### Analyzer Settings Flattening

This is **critical for OmniSharp**: When Roslyn reads EditorConfig, it **flattens settings into command-line arguments**.

**Example conversion**:

```ini
# In .editorconfig
[*.cs]
csharp_style_var_for_built_in_types = false
dotnet_naming_style.style1.capitalization = pascal_case
RoslynExtensionsOptions:EnableAnalyzersSupport = true
```

**Becomes command-line args**:
```bash
dotnet OmniSharp.dll \
  -z --hostPID 12345 \
  csharp_style_var_for_built_in_types=false \
  dotnet_naming_style.style1.capitalization=pascal_case \
  RoslynExtensionsOptions:EnableAnalyzersSupport=true
```

### Build vs. IDE Behavior

**In IDE (Visual Studio/Neovim + LSP)**:
- Code-style rules (IDE*) shown as light bulbs (suggestions)
- Severity determines display level
- Real-time feedback as you type

**In Build (`dotnet build`)**:
- Only rules with severity `warning` or `error` are enforced
- Default for style rules is no enforcement
- Must set severity to `error` to break build

---

## 4. How OmniSharp Enables/Disables EditorConfig Support

### OmniSharp Configuration Hierarchy

OmniSharp uses **5 levels of configuration** (in order of precedence):

1. **Hardcoded defaults** (lowest)
2. **Environment variables** (`OMNISHARP_` prefix, `:` delimiter)
3. **Command-line arguments** (flattened JSON paths)
4. **Global config** (`~/.omnisharp/omnisharp.json`)
5. **Project-specific config** (`omnisharp.json` in working directory) (highest)

### EditorConfig Support Setting

**Key Setting**: `FormattingOptions:EnableEditorConfigSupport`

**In omnisharp.json**:
```json
{
  "FormattingOptions": {
    "EnableEditorConfigSupport": true
  }
}
```

**Via OmniSharp LSP Settings** (e.g., in init.lua for Neovim):
```lua
settings = {
  FormattingOptions = {
    EnableEditorConfigSupport = true,
    OrganizeImports = true,
  },
}
```

**Via Command Line** (passed to OmniSharp):
```bash
dotnet OmniSharp.dll \
  FormattingOptions:EnableEditorConfigSupport=true
```

### What `EnableEditorConfigSupport` Does

When **enabled** (`true`):
- OmniSharp reads `.editorconfig` files from the project directory and parents
- Formatting operations respect EditorConfig settings
- Code actions and refactorings follow EditorConfig conventions
- Settings from `.editorconfig` override hardcoded OmniSharp defaults

When **disabled** (`false`):
- OmniSharp ignores `.editorconfig` files
- Uses built-in defaults or explicit omnisharp.json settings only
- Useful for enforcing consistent settings across team regardless of EditorConfig

### Other Related Roslyn Extension Settings

OmniSharp exposes Roslyn analyzer settings via the same mechanism:

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,      -- Enable StyleCop/other Roslyn analyzers
    EnableImportCompletion = true,      -- Enable completion from imports
    AnalyzeOpenDocumentsOnly = false,   -- Analyze entire solution or just open docs
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true,   -- Read .editorconfig files
    OrganizeImports = true,             -- Auto-organize using statements
  },
}
```

---

## 5. Best Practices for EditorConfig with Roslyn

### A. Create Effective .editorconfig Files

**File Location**: Place `.editorconfig` at your **repository root** and in subdirectories as needed.

**Recommended Structure**:

```ini
# Root .editorconfig (applies to entire project)
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

# Language and style rules
csharp_style_var_for_built_in_types = false
csharp_style_var_when_type_is_apparent = true
csharp_style_var_elsewhere = false
csharp_prefer_simple_using_statement = true

# Naming conventions (PascalCase for types)
dotnet_naming_style.pascal_case_style.capitalization = pascal_case
dotnet_naming_rule.types_should_be_pascal_case.symbols = type_symbols
dotnet_naming_rule.types_should_be_pascal_case.style = pascal_case_style
dotnet_naming_rule.types_should_be_pascal_case.severity = warning

# Code quality rules
dotnet_analyzer_diagnostic.category-Design.severity = warning
dotnet_analyzer_diagnostic.category-Performance.severity = warning

# Optional: StyleCop rules (if using StyleCop.Analyzers)
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1309.severity = warning

# JSON files
[*.json]
indent_style = space
indent_size = 2
```

### B. Enable EditorConfig in OmniSharp Configuration

Ensure OmniSharp is configured to **read** .editorconfig files:

```lua
-- In Neovim init.lua or omnisharp.json
FormattingOptions = {
  EnableEditorConfigSupport = true,
}
```

### C. Verify Configuration is Applied

**Check running OmniSharp process**:
```bash
ps aux | grep omnisharp
```

Look for:
- `-s /path/to/solution` (solution path)
- `FormattingOptions:EnableEditorConfigSupport=true`
- Other flattened settings

**In Neovim**:
```vim
:LspInfo
```

Look for `RoslynExtensionsOptions` and `FormattingOptions` sections.

### D. Rule Configuration Strategy

**Recommended approach**:

1. **Use EditorConfig for project-wide standards** (formatting, naming, style)
   - These rarely change between environments
   - Versioned in Git for consistency across team
   - Readable and discoverable

2. **Use omnisharp.json for environment-specific settings** (local development)
   - OmniSharp server behavior (timeouts, worker threads)
   - Developer-specific preferences
   - Not versioned in Git

3. **Use command-line for CI/CD overrides** (in build pipelines)
   - Stricter checks in CI
   - Different rules for different branches
   - Runtime configuration

**Example CI setup**:
```bash
# In CI pipeline: Enable all Security and Performance rules
dotnet build \
  /p:EnforceCodeStyleInBuild=true \
  /p:EnableNETAnalyzers=true \
  /p:AnalysisMode=All \
  -p:TreatWarningsAsErrors=true
```

### E. Common Pitfalls to Avoid

| Problem | Solution |
|---------|----------|
| EditorConfig not found | Ensure `.editorconfig` is in project root or parent dirs; set `root = true` |
| Settings not applied | Enable `FormattingOptions:EnableEditorConfigSupport = true` in OmniSharp |
| Conflicting rules | Check precedence: command-line > deeper EditorConfig > global config |
| IDE vs. Build differences | Set rule severity to `error` for build enforcement; check `EnforceCodeStyleInBuild` property |
| Performance issues | Use `AnalyzeOpenDocumentsOnly = true` to reduce analyzer workload |

### F. Integration with Continuous Integration

**In .NET build**:
```xml
<!-- In .csproj file -->
<PropertyGroup>
  <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
  <EnableNETAnalyzers>true</EnableNETAnalyzers>
  <AnalysisMode>All</AnalysisMode>
  <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
</PropertyGroup>
```

**In GitHub Actions or other CI**:
```yaml
- name: Build with code analysis
  run: |
    dotnet build \
      -p:EnforceCodeStyleInBuild=true \
      -p:EnableNETAnalyzers=true \
      -p:TreatWarningsAsErrors=true
```

---

## 6. StyleCop.Analyzers Configuration via EditorConfig

### How StyleCop Rules Work

StyleCop.Analyzers package provides **SA*** rules (e.g., SA1116, SA1309) that enforce C# style conventions. These are **regular Roslyn analyzers** and **fully support EditorConfig configuration**.

### Configuring StyleCop Rules

```ini
[*.cs]
# StyleCop SA rules - configure severity and behavior
dotnet_diagnostic.SA1116.severity = warning
dotnet_diagnostic.SA1117.severity = warning
dotnet_diagnostic.SA1118.severity = warning
dotnet_diagnostic.SA1309.severity = warning

# StyleCop naming conventions
dotnet_naming_rule.private_members_with_leading_underscore.severity = suggestion
```

### Enabling StyleCop Support in OmniSharp

```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,    -- ⚠️ CRITICAL: Enables StyleCop analyzers
    AnalyzeOpenDocumentsOnly = false, -- Analyze entire solution, not just open files
  },
  FormattingOptions = {
    EnableEditorConfigSupport = true, -- Read StyleCop rules from .editorconfig
  },
}
```

---

## 7. OmniSharp Configuration Recommendation for StyleCop

To ensure StyleCop warnings appear in Neovim with full EditorConfig support:

### Complete Configuration Example

```lua
-- In init.lua (Neovim)
omnisharp = {
  -- Use dotnet command to call OmniSharp DLL directly
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/path/to/solution'),  -- Full solution path
    '-loglevel', 'Information',                  -- Detailed logging
  },

  -- Settings that affect analyzer and formatter behavior
  settings = {
    -- Enable StyleCop and other Roslyn analyzers
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,  -- Analyze entire solution
    },

    -- Enable .editorconfig support
    FormattingOptions = {
      EnableEditorConfigSupport = true,
      OrganizeImports = true,
    },
  },
}
```

### Verification

1. **Clear cache**: `rm -rf ~/.cache/nvim/luac/`
2. **Restart OmniSharp**: `pkill -f omnisharp`
3. **Open C# file**: Should see notification that OmniSharp is loading
4. **Check configuration**:
   ```vim
   :LspInfo
   ```
   Should show:
   - `RoslynExtensionsOptions: { EnableAnalyzersSupport = true, ... }`
   - `FormattingOptions: { EnableEditorConfigSupport = true, ... }`

5. **Verify running process**:
   ```bash
   ps aux | grep omnisharp | grep -v grep
   ```
   Should include `-loglevel Information` and solution path

---

## 8. Summary Table

| Aspect | Details |
|--------|---------|
| **Roslyn EditorConfig Discovery** | Automatic; searches upward from file to root or `root = true` |
| **Configuration Methods** | EditorConfig files (`.editorconfig`) + Global config files (`.globalconfig`) |
| **Precedence** | Command-line > deeper EditorConfig > global config |
| **Code Style Rules** | IDE0001-IDE0380+; configured with `dotnet_diagnostic.<id>.severity` |
| **Language Options** | `csharp_*` and `dotnet_*` prefixed settings |
| **Code Quality Rules** | CAxxxx rules; configured with `dotnet_analyzer_diagnostic.category-<Cat>.severity` |
| **OmniSharp EditorConfig Enable** | `FormattingOptions:EnableEditorConfigSupport = true` |
| **Analyzer Support Enable** | `RoslynExtensionsOptions:EnableAnalyzersSupport = true` |
| **Analyzer Scope** | `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly = false` for full solution |
| **StyleCop Rules** | SA* rules; standard Roslyn analyzers, fully EditorConfig configurable |
| **Best Practice** | Place .editorconfig at repo root; enable EditorConfig in OmniSharp |

---

## 9. References

**Official Documentation**:
- Microsoft Learn: [Code Analysis Configuration Files](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/configuration-files)
- Microsoft Learn: [Code Style Rules Overview](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/style-rules/)
- Microsoft Learn: [EditorConfig Code Style Settings Reference](https://learn.microsoft.com/en-us/visualstudio/ide/editorconfig-code-style-settings-reference)
- EditorConfig.org: [EditorConfig Format Specification](https://editorconfig.org)

**Project Examples**:
- Roslyn Project .editorconfig: [github.com/dotnet/roslyn/.editorconfig](https://github.com/dotnet/roslyn/blob/main/.editorconfig)
- OmniSharp Configuration: [github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options](https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options)

**StyleCop**:
- StyleCop.Analyzers NuGet: [Roslyn source analyzers for StyleCop](https://www.nuget.org/packages/StyleCop.Analyzers)

---

## 10. Action Items for OmniSharp/StyleCop Integration

To ensure StyleCop warnings display correctly in your C# LSP setup:

1. ✅ Create `.editorconfig` in solution root
2. ✅ Set `FormattingOptions:EnableEditorConfigSupport = true`
3. ✅ Set `RoslynExtensionsOptions:EnableAnalyzersSupport = true`
4. ✅ Set `RoslynExtensionsOptions:AnalyzeOpenDocumentsOnly = false`
5. ✅ Verify configuration with `:LspInfo`
6. ✅ Verify running process includes flattened settings
7. ✅ Define StyleCop rule severities in `.editorconfig`
8. ✅ Ensure StyleCop.Analyzers package is referenced in project

