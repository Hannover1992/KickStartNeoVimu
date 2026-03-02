# Roslyn, MSBuild, and OmniSharp Connection for Neovim

## How Roslyn Uses MSBuild to Load Projects

When OmniSharp runs in your Neovim with the configuration:
```lua
cmd = {
  'dotnet',
  '/path/to/OmniSharp.dll',
  '-s', '/path/to/solution/',  -- Solution path
  '-loglevel', 'Information',
},
```

Here's exactly what happens under the hood:

### Step 1: OmniSharp Initialization

1. **OmniSharp starts** and listens on a port for LSP requests
2. **Receives `-s` parameter** with solution path
3. **Creates MSBuildWorkspace** internally:
   ```csharp
   var workspace = MSBuildWorkspace.Create();
   ```

### Step 2: Solution Loading

1. **Reads .sln file** at the provided path
2. **Parses solution structure** to discover all projects:
   ```
   Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "ProjectName", "path/to/project.csproj"
   EndProject
   ```
3. **Enumerates all .csproj files** referenced in solution

### Step 3: Project Evaluation via MSBuild

For each `.csproj` file discovered:

1. **MSBuild evaluates the project** to extract:
   - **Target Framework**: `<TargetFramework>net8.0</TargetFramework>`
   - **Language Version**: `<LangVersion>latest</LangVersion>`
   - **Nullable References**: `<Nullable>enable</Nullable>`
   - **Output Path**: `<OutputPath>bin/Release</OutputPath>`
   - **Preprocessor Symbols**: `<DefineConstants>DEBUG;TRACE</DefineConstants>`

2. **Creates compilation options** from MSBuild properties:
   ```csharp
   var compilationOptions = new CSharpCompilationOptions
   {
       OutputKind = OutputKind.DynamicallyLinkedLibrary,
       OptimizationLevel = OptimizationLevel.Release,
       NullableContextOptions = NullableContextOptions.Enable,
       // ... other options from MSBuild
   };
   ```

### Step 4: Package Reference Resolution

For each `<PackageReference>` in the project:

1. **Extracts package name and version**:
   ```xml
   <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
   ```

2. **Resolves from NuGet cache**:
   ```
   ~/.nuget/packages/stylecop.analyzers/1.1.118/
   ```

3. **Discovers all assemblies** in package:
   ```
   analyzers/
   lib/
     net6.0/
       StyleCopAnalyzers.dll
   ```

4. **Creates MetadataReferences** for each assembly

### Step 5: Project Reference Resolution

For each `<ProjectReference>`:

1. **Identifies referenced project** path:
   ```xml
   <ProjectReference Include="../Core/Core.csproj" />
   ```

2. **Recursively loads referenced project** (same process)

3. **Establishes reference** from current project to referenced compilation

### Step 6: Compilation Creation

With all information gathered:

```csharp
var compilation = CSharpCompilation.Create("ProjectName")
    .AddReferences(
        // References to framework assemblies
        // References to NuGet packages
        // References to project outputs
    )
    .AddSyntaxTrees(
        // Syntax trees from all .cs files
    )
    .WithOptions(compilationOptions);
```

### Step 7: Analyzer Binding

StyleCop and other analyzers are now available:

1. **Roslyn discovers analyzers** from packages:
   - `StyleCopAnalyzers.dll` is an analyzer
   - System scans for `[DiagnosticAnalyzer]` attributes

2. **Initializes analyzers** with:
   - Compilation context
   - Syntax tree
   - Semantic model
   - Analysis context

3. **Runs analyzers** to produce diagnostics:
   - SA1116 - Opening parenthesis must be on declaration line
   - SA1117 - Closing parenthesis must be on line of last parameter
   - etc.

---

## Why the Solution Path Parameter is Critical

The `-s` parameter is **the entry point** for Roslyn to understand your project:

### Without Solution Path
```bash
dotnet OmniSharp.dll  # No -s parameter
```
- ❌ OmniSharp doesn't know what to load
- ❌ No compilation context
- ❌ No type information
- ❌ No analyzers run
- ❌ LSP features won't work

### With Solution Path
```bash
dotnet OmniSharp.dll -s /path/to/solution/
```
- ✅ MSBuildWorkspace loads all projects
- ✅ Compilation is created with all references
- ✅ Semantic analysis works
- ✅ Analyzers run with full context
- ✅ LSP features fully functional

---

## How NuGet Package Resolution Affects Analyzers

### StyleCop.Analyzers Example

In your `.csproj`:
```xml
<ItemGroup>
  <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />
</ItemGroup>
```

**Loading Process**:

1. **MSBuild parses package reference**
2. **NuGet resolves from cache**:
   ```
   ~/.nuget/packages/stylecop.analyzers/1.1.118/
   ├── analyzers/
   │   └── dotnet/
   │       └── cs/
   │           └── StyleCopAnalyzers.dll
   └── lib/
       └── net6.0/
           └── StyleCop.Analyzers.dll
   ```

3. **Roslyn discovers analyzer assembly** in `analyzers/` folder
4. **Analyzer is loaded and registered** with compilation
5. **Analyzer receives semantic model** for each file
6. **Analyzer reports diagnostics** (StyleCop warnings)

### Why WSL2 Cross-Filesystem Breaks This

**Scenario**: Build in Windows PowerShell, then open in WSL2 Neovim

**Problem**:
1. Windows builds → NuGet downloads to `C:\Users\...\AppData\Local\nuget\cache\`
2. WSL2 Roslyn looks in `~/.nuget/packages/` (different location!)
3. **NuGet cache miss** → Packages not found
4. **Analyzers not loaded**
5. **No StyleCop warnings**

**Solution**:
```bash
# In WSL2, before opening Neovim
cd /path/to/project
dotnet restore --force-evaluate --no-cache
```

This forces .NET/NuGet to re-download packages into WSL2's NuGet cache.

---

## Roslyn's Four-Phase Compilation Model in OmniSharp

When OmniSharp analyzes your C# files, it uses Roslyn's compiler pipeline:

### Phase 1: Parse
```csharp
var tree = CSharpSyntaxTree.ParseText(sourceCode);
// Result: Syntax tree (AST) with complete source fidelity
```

**Example**: For this code:
```csharp
public class User
{
    public string Name { get; set; }
}
```

Produces a syntax tree representing:
- ClassDeclaration node
- PropertyDeclaration node
- Token nodes (keywords, identifiers)
- Trivia (whitespace, comments)

### Phase 2: Declaration
```csharp
var compilation = CSharpCompilation.Create("Assembly")
    .AddSyntaxTrees(tree)
    .AddReferences(/*...*/);
// Result: Symbol table with all declared types/methods
```

Extracts declarations like:
- `User` class in `MyNamespace`
- `Name` property
- Implicit constructor

### Phase 3: Bind
```csharp
var semanticModel = compilation.GetSemanticModel(tree);
var symbol = semanticModel.GetSymbolInfo(identifierNode).Symbol;
// Result: Identifiers matched to symbols
```

Answers questions like:
- What symbol does `Name` refer to?
- What is the type of this expression?
- Which method overload is called?

### Phase 4: Emit
```csharp
using var ms = new MemoryStream();
compilation.Emit(ms);
// Result: IL byte code (normally done by compiler, not LSP)
```

Produces the actual `.dll` file (not usually relevant for LSP).

---

## How OmniSharp's StyleCop Configuration Works

Your Neovim configuration includes:
```lua
settings = {
  RoslynExtensionsOptions = {
    EnableAnalyzersSupport = true,      -- Enable analyzers
    EnableImportCompletion = true,      -- Smart imports
    AnalyzeOpenDocumentsOnly = false,   -- Analyze all files
  },
},
```

### What Each Setting Does

**EnableAnalyzersSupport = true**
- Loads all analyzers from NuGet packages
- Runs diagnostic analysis on code
- Reports analyzer warnings (StyleCop SA* codes)

**EnableImportCompletion = true**
- Suggests imports when you reference undefined types
- Requires full workspace semantic analysis

**AnalyzeOpenDocumentsOnly = false**
- Analyzes **all files in solution**, not just open ones
- Detects cross-file issues
- More CPU intensive but more complete

### The Configuration Flow

```
OmniSharp Config
    ↓
RoslynExtensionsOptions:EnableAnalyzersSupport=true
    ↓
MSBuildWorkspace loads all projects
    ↓
For each project:
  - Create compilation
  - Discover analyzers from NuGet
  - Register analyzers with Roslyn
    ↓
For each C# file:
  - Parse syntax tree
  - Create semantic model
  - Run all analyzers
  - Collect diagnostics
    ↓
Return diagnostics to Neovim
    ↓
Warnings appear as red underlines
```

---

## Workspace and Project Management in OmniSharp

### Solution Structure
```
Solution
├── Project A (Core.API)
│   ├── File1.cs → Syntax Tree → Semantic Model → Diagnostics
│   ├── File2.cs → Syntax Tree → Semantic Model → Diagnostics
│   └── Compilation (using references from B)
├── Project B (Data.Layer)
│   ├── File3.cs
│   ├── File4.cs
│   └── Compilation
└── Project C (Tests)
    ├── File5.cs
    ├── File6.cs
    └── Compilation (using references from A and B)
```

### Key Properties of Roslyn's Workspace

**1. Immutability**
- Changes to workspace create new instances
- Old instances remain valid
- Safe for concurrent access
- Enables undo/redo

**2. Lazy Loading**
- Projects loaded on-demand
- Compilations built when first requested
- Results cached
- Performance optimized

**3. Incremental Updates**
- Changes to one file don't recompile entire project
- Affected files are reanalyzed
- Unaffected files use cached results

**4. Project Dependencies**
- Roslyn knows Project A depends on Project B
- Compilation order is determined
- Cross-project navigation works (go to definition)

---

## Diagnostic Flow in OmniSharp/Neovim

When you open a C# file in Neovim with OmniSharp:

### 1. File Open Event
```
Neovim sends: "file opened"
    ↓
OmniSharp receives event
```

### 2. Workspace Update
```
OmniSharp adds document to workspace
    ↓
Resets cached compilation for project
```

### 3. Syntax Analysis
```
Roslyn parses file → Syntax Tree
    ↓
Checks for syntax errors
    ↓
Reports syntax diagnostics
```

### 4. Semantic Analysis
```
Create/update compilation
    ↓
Generate semantic model for file
    ↓
Roslyn runs:
  - Built-in compiler checks
  - StyleCop analyzers
  - Other configured analyzers
    ↓
Each analyzer reports diagnostics
```

### 5. Diagnostic Aggregation
```
OmniSharp collects all diagnostics:
  - Syntax errors (red squiggles)
  - Type errors (red squiggles)
  - StyleCop warnings (yellow squiggles)
  - Other analyzer warnings
```

### 6. Return to Neovim
```
OmniSharp sends:
  [
    { "line": 5, "column": 10, "message": "SA1116: ...", "severity": "warning" },
    { "line": 8, "column": 0, "message": "CS1234: ...", "severity": "error" },
    ...
  ]
    ↓
Neovim displays diagnostics
```

### 7. User Hovers (K in Normal Mode)
```
Neovim requests: "semantic info at cursor"
    ↓
OmniSharp queries semantic model
    ↓
Returns type info, documentation
    ↓
Neovim displays hover popup
```

---

## Project Dependencies and Cross-Project Analysis

### Reference Resolution Example

**Solution**: DCSRE
```
- VDEK.DCSP.Core
- VDEK.DCSP.Data  (references Core)
- VDEK.DCSP.Service (references Data and Core)
- VDEK.DCSP.WebApi (references Service, Data, Core)
```

**When OmniSharp loads**:

1. **Create compilation for VDEK.DCSP.Core**
   - No project dependencies
   - Just framework references and NuGet packages

2. **Create compilation for VDEK.DCSP.Data**
   - Reference Core's compilation
   - Add Core's output assembly as MetadataReference
   - Now can resolve Core types

3. **Create compilation for VDEK.DCSP.Service**
   - Reference Data's compilation
   - Reference Core's compilation
   - Can resolve types from both

4. **Create compilation for VDEK.DCSP.WebApi**
   - Reference Service, Data, Core
   - Full transitive closure

### Go to Definition Across Projects

When you press `gd` on a type from another project:

```
Position: "var user = new User();"
          Cursor on "User"
    ↓
OmniSharp queries semantic model
    ↓
Finds symbol: "User" class
    ↓
Symbol location: VDEK.DCSP.Core / User.cs / line 42
    ↓
Neovim opens that file
    ↓
Jumps to line 42
```

This works because:
- User's project is in workspace
- Compilation includes all projects
- Symbols are resolved across project boundaries

---

## Why Neovim OmniSharp Configuration Matters

Your init.lua configuration:

```lua
omnisharp = {
  cmd = {
    'dotnet',
    vim.fn.stdpath('data') .. '/mason/packages/omnisharp/libexec/OmniSharp.dll',
    '-s', vim.fn.expand('/mnt/c/Users/.../Backend'),
    '-loglevel', 'Information',
  },
  settings = {
    RoslynExtensionsOptions = {
      EnableAnalyzersSupport = true,
      EnableImportCompletion = true,
      AnalyzeOpenDocumentsOnly = false,
    },
  },
}
```

**Each part is essential**:

1. **`cmd` - OmniSharp executable path**
   - Must point to actual OmniSharp.dll
   - Must be correct version
   - Used by Neovim to start process

2. **`-s /path/to/Backend`**
   - Tells OmniSharp which solution to load
   - Triggers MSBuildWorkspace initialization
   - Enables all Roslyn features

3. **`-loglevel Information`**
   - Enables detailed logging
   - Helps debug project loading issues
   - Logs saved to `~/.local/state/nvim/lsp.log`

4. **`RoslynExtensionsOptions`**
   - Enables StyleCop and other analyzers
   - Configures analysis behavior
   - Affects completeness and performance

---

## Summary

**The Chain**:
```
Neovim init.lua config
    ↓ (passes parameters)
OmniSharp process
    ↓ (uses solution path)
Roslyn MSBuildWorkspace
    ↓ (loads and evaluates)
MSBuild (.csproj and .sln files)
    ↓ (extracts project structure)
Package Resolution
    ↓ (resolves NuGet packages)
Compilation Creation
    ↓ (creates compilation objects)
Analyzer Loading
    ↓ (loads StyleCop, etc.)
Diagnostic Analysis
    ↓ (runs analyzers)
Diagnostics returned to Neovim
    ↓
User sees warnings/errors
```

This is why getting the configuration right is critical - each step depends on the previous one working correctly!
