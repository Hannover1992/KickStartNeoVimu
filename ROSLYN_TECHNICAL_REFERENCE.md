# Roslyn Technical Reference - Quick Lookup Guide

**Purpose**: Fast reference for Roslyn concepts, APIs, and patterns
**Date**: November 13, 2025

---

## Quick Reference Tables

### Compilation Pipeline Phases

| Phase | Name | Purpose | Input | Output | API Object |
|-------|------|---------|-------|--------|-----------|
| 1 | **Parse** | Tokenize and parse source | Raw text | Syntax tree | `SyntaxTree` |
| 2 | **Declaration** | Analyze source + metadata | Source + refs | Symbol table | `ISymbol` |
| 3 | **Bind** | Link names to symbols | Symbols + context | Resolved names | `SemanticModel` |
| 4 | **Emit** | Generate IL bytecode | Compiled info | Assembly + IL | `.dll`, `.exe` |

### Syntax Tree Element Types

| Element | Represents | Properties | Example |
|---------|-----------|-----------|---------|
| **SyntaxTree** | Entire file | Root, all descendants | Root of parse tree |
| **SyntaxNode** | Grammar construct | Parent, children, span | `MethodDeclarationSyntax` |
| **SyntaxToken** | Terminal symbol | Text, kind, trivia | Keyword `class` |
| **SyntaxTrivia** | Non-syntax info | Text, kind | Comment, whitespace |

### Common SyntaxNode Types (C#)

```
Declarations:
├── NamespaceDeclarationSyntax
├── ClassDeclarationSyntax
├── InterfaceDeclarationSyntax
├── StructDeclarationSyntax
├── MethodDeclarationSyntax
├── PropertyDeclarationSyntax
├── FieldDeclarationSyntax
└── VariableDeclaratorSyntax

Statements:
├── IfStatementSyntax
├── WhileStatementSyntax
├── ForStatementSyntax
├── ReturnStatementSyntax
└── LocalDeclarationStatementSyntax

Expressions:
├── InvocationExpressionSyntax
├── BinaryExpressionSyntax
├── UnaryExpressionSyntax
├── CastExpressionSyntax
└── LiteralExpressionSyntax
```

### Symbol Types (ISymbol Implementations)

| Symbol Type | Represents | Properties |
|-------------|-----------|-----------|
| `INamespaceSymbol` | Namespace | Name, containing namespace, members |
| `ITypeSymbol` | Type (class, interface, struct) | Name, members, base types, accessibility |
| `IMethodSymbol` | Method or function | Name, parameters, return type, accessibility |
| `IPropertySymbol` | Property | Name, type, get/set accessors |
| `IFieldSymbol` | Field | Name, type, initialization |
| `IParameterSymbol` | Method parameter | Name, type, default value |
| `ILocalSymbol` | Local variable | Name, type |
| `INamedTypeSymbol` | Named type (class, etc.) | Name, members, constructors |

### SemanticModel Query Operations

| Operation | Method | Returns | Used For |
|-----------|--------|---------|----------|
| What symbol? | `GetSymbolInfo()` | `SymbolInfo` | Find what name refers to |
| What type? | `GetTypeInfo()` | `TypeInfo` | Determine expression type |
| All diagnostics? | `GetDiagnostics()` | `ImmutableArray<Diagnostic>` | Get all errors/warnings |
| Accessibility? | `IsAccessible()` | `bool` | Check if symbol accessible |
| Data flow? | `AnalyzeDataFlow()` | `DataFlowAnalysis` | Track variable usage |

### Analyzer Registration Actions

| Action | Triggers On | Use For |
|--------|------------|---------|
| `RegisterSyntaxNodeAction` | Specific syntax node type | Checking structure |
| `RegisterSemanticModelAction` | Entire semantic model | Cross-file analysis |
| `RegisterSymbolAction` | Specific symbol type | Declaration analysis |
| `RegisterCodeBlockAction` | Method/property bodies | Control flow analysis |
| `RegisterOperationAction` | Specific operation type | Semantic operations |

---

## Common Patterns

### Pattern 1: Create Compilation and Get Semantic Model

```csharp
// Create compilation
var syntaxTree = CSharpSyntaxTree.ParseText(sourceCode);
var compilation = CSharpCompilation.Create("TestAssembly")
    .AddReferences(MetadataReference.CreateFromFile(typeof(object).Assembly.Location))
    .AddSyntaxTrees(syntaxTree);

// Get semantic model
var semanticModel = compilation.GetSemanticModel(syntaxTree);
```

### Pattern 2: Query Symbols

```csharp
// Get symbol information
var node = /* some SyntaxNode */;
var symbolInfo = semanticModel.GetSymbolInfo(node);
var symbol = symbolInfo.Symbol;

// Check symbol type
if (symbol is IMethodSymbol method)
{
    var returnType = method.ReturnType;
    var parameters = method.Parameters;
    var accessibility = method.DeclaredAccessibility;
}
```

### Pattern 3: Navigate Syntax Tree

```csharp
// Find all methods
var methods = root.DescendantNodes()
    .OfType<MethodDeclarationSyntax>();

// Find class with specific name
var userClass = root.DescendantNodes()
    .OfType<ClassDeclarationSyntax>()
    .FirstOrDefault(c => c.Identifier.Text == "User");

// Get parent class of a method
var methodParent = method.Parent as ClassDeclarationSyntax;
```

### Pattern 4: Create Analyzer

```csharp
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public class MyAnalyzer : DiagnosticAnalyzer
{
    private static readonly DiagnosticDescriptor Rule =
        new DiagnosticDescriptor(
            id: "MY001",
            title: "My Rule Title",
            messageFormat: "Description of issue: {0}",
            category: "Naming",
            defaultSeverity: DiagnosticSeverity.Warning,
            isEnabledByDefault: true);

    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics =>
        ImmutableArray.Create(Rule);

    public override void Initialize(AnalysisContext context)
    {
        context.RegisterSyntaxNodeAction(
            ctx => AnalyzeMethodDeclaration(ctx),
            SyntaxKind.MethodDeclaration);
    }

    private void AnalyzeMethodDeclaration(SyntaxNodeAnalysisContext context)
    {
        var method = (MethodDeclarationSyntax)context.Node;

        // Check condition
        if (ViolatesRule(method))
        {
            var diagnostic = Diagnostic.Create(
                Rule,
                method.Identifier.GetLocation(),
                method.Identifier.Text);
            context.ReportDiagnostic(diagnostic);
        }
    }

    private bool ViolatesRule(MethodDeclarationSyntax method)
    {
        // Your analysis logic
        return false;
    }
}
```

### Pattern 5: Create Workspace and Load Solution

```csharp
using var workspace = MSBuildWorkspace.Create();
var solution = await workspace.OpenSolutionAsync(solutionPath);

foreach (var project in solution.Projects)
{
    var compilation = await project.GetCompilationAsync();

    foreach (var document in project.Documents)
    {
        var syntaxTree = await document.GetSyntaxTreeAsync();
        var semanticModel = await document.GetSemanticModelAsync();
    }
}
```

---

## Diagnostic Severity Levels

| Severity | Meaning | Display |
|----------|---------|---------|
| `Error` | Compilation fails | Red underline |
| `Warning` | Likely mistake | Yellow/orange underline |
| `Info` | Informational | Blue/light underline |
| `Hidden` | Not visible to user | Not shown |

---

## StyleCop Analyzer Integration

### How Settings Reach Analyzers

```
OmniSharp Settings (NVIM)
    └─> RoslynExtensionsOptions:EnableAnalyzersSupport=true
        └─> CLI argument to OmniSharp process
            └─> Roslyn initialization
                └─> Load analyzer packages
                    └─> Execute analyzers
                        └─> Report StyleCop violations
```

### Critical Setting

```lua
RoslynExtensionsOptions = {
  EnableAnalyzersSupport = true,      -- Enable analyzer loading/execution
  AnalyzeOpenDocumentsOnly = false,   -- Analyze all files in solution
}
```

### StyleCop Rule Categories

| Code Range | Category |
|-----------|----------|
| SA1xxx | Naming conventions and ordering |
| SA2xxx | Readability and spacing |
| SA3xxx | Ordering (alphabetical, etc.) |
| SA4xxx | Maintenance rules |
| SA5xxx | Documentation |
| SA6xxx | Readability and spacing continued |

### Common StyleCop Rules

- **SA1116**: Split parameters must start on line after declaration
- **SA1117**: Parameters should be on same line or separate lines
- **SA1402**: File may only contain a single type definition
- **SA1414**: Parameters should be on same line as declaration
- **SA0001**: Invalid XML documentation

---

## Performance Considerations

### Incremental Compilation Strategy

```csharp
// Initial
var comp1 = CSharpCompilation.Create("Proj")
    .AddSyntaxTrees(tree1, tree2, tree3);

// File changes
var comp2 = comp1.ReplaceSyntaxTree(tree1, newTree1);
// Only tree1 is reparsed and rebound!
// tree2 and tree3 reuse cached symbols

// Efficient repeated analysis
var diags1 = comp2.GetDiagnostics();  // Uses cache
var diags2 = comp2.GetDiagnostics();  // Uses same cache
```

### Caching Best Practices

1. **Reuse Compilation objects**: Create once, query multiple times
2. **Reuse SemanticModel**: Get once per file, query many times
3. **Batch operations**: Process multiple nodes in single pass
4. **Avoid reparsing**: Only reparse changed files

---

## Common API Calls

### Getting Syntax Information

```csharp
// Get node kind
var kind = node.Kind();           // SyntaxKind enum

// Get position
var span = node.Span;              // Start-end positions
var line = node.GetLocation().GetLineSpan();  // Line/column

// Get text
var text = node.ToString();         // String representation
var source = root.ToFullString();   // Exact source (with trivia)

// Navigate
var parent = node.Parent;
var children = node.ChildNodes();
```

### Getting Type Information

```csharp
// From expression
var typeInfo = semanticModel.GetTypeInfo(expression);
var type = typeInfo.Type;
var convertedType = typeInfo.ConvertedType;

// From symbol
if (symbol is IFieldSymbol field)
    var fieldType = field.Type;

if (symbol is IPropertySymbol property)
    var propertyType = property.Type;
```

### Checking Accessibility

```csharp
var accessibility = symbol.DeclaredAccessibility;

// accessibility values:
// Accessibility.Public
// Accessibility.Private
// Accessibility.Protected
// Accessibility.Internal
// Accessibility.ProtectedAndInternal
// Accessibility.ProtectedOrInternal
```

---

## Debugging Tips

### Print Syntax Tree Structure

```csharp
var tree = CSharpSyntaxTree.ParseText(code);
var root = tree.GetCompilationUnitSyntax();

// Print tree
var printer = new CSharpSyntaxWalker();
printer.Visit(root);

public class CSharpSyntaxWalker : SyntaxWalker
{
    private int indent = 0;

    public override void Visit(SyntaxNode node)
    {
        Console.WriteLine(new string(' ', indent * 2) + node.Kind());
        indent++;
        base.Visit(node);
        indent--;
    }
}
```

### Inspect Symbol Details

```csharp
var symbol = symbolInfo.Symbol;
Console.WriteLine($"Name: {symbol.Name}");
Console.WriteLine($"Kind: {symbol.Kind}");
Console.WriteLine($"Accessibility: {symbol.DeclaredAccessibility}");
Console.WriteLine($"Namespace: {symbol.ContainingNamespace}");
if (symbol is ITypeSymbol type)
    Console.WriteLine($"Members: {type.GetMembers().Length}");
```

### Check Compilation Diagnostics

```csharp
var diagnostics = compilation.GetDiagnostics();
foreach (var diag in diagnostics)
{
    Console.WriteLine($"[{diag.Severity}] {diag.Id}: {diag.GetMessage()}");
    Console.WriteLine($"  Location: {diag.Location}");
}
```

---

## Key API Classes

### Core Compilation APIs

```csharp
// Main types
CSharpCompilation              // The compilation itself
CSharpSyntaxTree               // Parsed source tree
SemanticModel                  // Symbol/type resolution
DiagnosticDescriptor           // Rule definition
Diagnostic                     // Issue instance

// Creation
CSharpCompilation.Create()
CSharpSyntaxTree.ParseText()
compilation.GetSemanticModel()

// Analysis
compilation.GetDiagnostics()
semanticModel.GetSymbolInfo()
semanticModel.GetTypeInfo()
```

### Analyzer APIs

```csharp
DiagnosticAnalyzer             // Base class for analyzers
AnalysisContext                // Context passed to analyzers
SyntaxNodeAnalysisContext      // Context for node analysis
SemanticModelAnalysisContext   // Context for semantic analysis
Diagnostic                     // Output (found issue)
DiagnosticDescriptor           // Rule metadata
```

### Workspace APIs

```csharp
Workspace                      // Container for solution(s)
MSBuildWorkspace               // Loads from MSBuild (.sln, .csproj)
Solution                       // Collection of projects
Project                        // Source code + references
Document                       // Single source file
```

### Symbol APIs

```csharp
ISymbol                        // Base symbol interface
INamespaceSymbol               // Namespace
ITypeSymbol                    // Type (class, struct, interface)
IMethodSymbol                  // Method
IPropertySymbol                // Property
IFieldSymbol                   // Field
IParameterSymbol               // Parameter
```

---

**Document Version**: 1.0
**Last Updated**: November 13, 2025
**Purpose**: Quick technical reference for Roslyn API and compilation pipeline
