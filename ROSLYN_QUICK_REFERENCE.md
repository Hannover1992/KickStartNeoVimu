# Roslyn Quick Reference for Neovim/OmniSharp Users

## TL;DR

**Roslyn** = Compiler platform that parses C# code and provides semantic analysis
**MSBuild** = Build system that describes project structure
**OmniSharp** = LSP server that uses Roslyn to provide code intelligence in editors
**NuGet** = Package manager that provides dependencies and analyzers

---

## The Three Loading Phases

### Phase 1: Solution Discovery (MSBuild)
```
OmniSharp receives: -s /path/to/solution/
    ↓
MSBuild reads: Solution.sln
    ↓
Discovers all .csproj files
```

**Files Involved**:
- `Solution.sln` - Solution file (lists all projects)
- `*.csproj` - Project files (describes build configuration)

### Phase 2: Project Evaluation (MSBuild)
```
For each .csproj:
  - Read project structure
  - Evaluate MSBuild properties
  - Extract compiler settings
  - List package references
  - List project references
```

**Examples of MSBuild Properties**:
- `<TargetFramework>net8.0</TargetFramework>`
- `<LangVersion>latest</LangVersion>`
- `<Nullable>enable</Nullable>`
- `<PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />`

### Phase 3: Compilation (Roslyn)
```
Create compilation with:
  - Syntax trees from .cs files
  - Metadata references from assemblies
  - Project references from other projects
  - NuGet packages
  - Analyzer assemblies
```

**Result**: Full semantic model for entire solution

---

## How Roslyn Works Internally

### Data Structures

```
Compilation (top level)
├── MetadataReferences (assemblies + NuGet packages)
├── SyntaxTrees (from .cs files)
│   └── SyntaxNodes (language constructs)
│       ├── SyntaxTokens (keywords, identifiers)
│       └── SyntaxTrivia (whitespace, comments)
└── Symbols (declared types/methods/fields)
```

### Two Types of Analysis

**Syntax Analysis** (structure only):
```csharp
// What does the code look like?
var tree = CSharpSyntaxTree.ParseText(code);
var classNode = tree.GetRoot().DescendantNodes()
    .OfType<ClassDeclarationSyntax>()
    .First();
```

**Semantic Analysis** (meaning):
```csharp
// What does the code mean?
var semanticModel = compilation.GetSemanticModel(tree);
var symbol = semanticModel.GetSymbolInfo(node).Symbol;
var type = semanticModel.GetTypeInfo(expression).Type;
```

---

## NuGet Package Flow

### How Packages Get Loaded

```
1. Project declares:
   <PackageReference Include="StyleCop.Analyzers" Version="1.1.118" />

2. NuGet resolves to cache:
   ~/.nuget/packages/stylecop.analyzers/1.1.118/

3. Roslyn discovers:
   lib/netXX/
     └── StyleCop.Analyzers.dll (assembly)
   analyzers/
     └── StyleCopAnalyzers.dll (analyzer code)

4. Roslyn loads analyzer:
   - Finds [DiagnosticAnalyzer] class
   - Registers with compilation
   - Runs on each file

5. Analyzer reports diagnostics:
   SA1116, SA1117, etc.
```

### Why WSL2 Breaks This

**Problem Scenario**:
- Build in Windows PowerShell → Packages downloaded to Windows cache
- Open in WSL2 Neovim → OmniSharp looks in WSL2 cache
- Caches are different locations → Packages not found

**Solution**:
```bash
# In WSL2 terminal (not Windows PowerShell)
cd /path/to/solution
dotnet restore --force-evaluate --no-cache
```

**Why This Works**:
- Forces .NET to download packages into WSL2 NuGet cache
- OmniSharp can now find packages
- Analyzers can load
- StyleCop warnings appear

---

## Troubleshooting: No StyleCop Warnings

**Checklist**:
1. Is `-s` pointing to correct solution?
   - Check: `ps aux | grep omnisharp` shows correct path

2. Is `EnableAnalyzersSupport = true`?
   - Check: `:LspInfo` shows the setting

3. Is StyleCop.Analyzers installed?
   - Check: `.csproj` has package reference

4. Are packages in WSL2 cache?
   - Run: `dotnet restore --force-evaluate --no-cache`
   - Check: `~/.nuget/packages/stylecop.analyzers/` exists

5. Restart OmniSharp:
   - Kill: `pkill -f omnisharp`
   - Clear: `rm -rf ~/.cache/nvim/luac/`
   - Restart: `:LspRestart` in Neovim

---

## Summary

```
Neovim config
    ↓
OmniSharp process started with -s solution_path
    ↓
Roslyn MSBuildWorkspace loads solution
    ↓
For each project in solution:
  - Parse .csproj
  - Extract compiler settings
  - Resolve NuGet packages
  - Resolve project references
    ↓
For each C# file:
  - Parse to syntax tree
  - Create semantic model
  - Run analyzers (StyleCop, etc.)
    ↓
Return diagnostics to Neovim
    ↓
User sees warnings/errors
```

**Key Insight**: The `-s` parameter is the root of everything. Without it, Roslyn doesn't know what to analyze.
