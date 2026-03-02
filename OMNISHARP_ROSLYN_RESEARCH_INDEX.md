# OmniSharp + Roslyn Research Documentation Index

**Research Completion Date**: November 13, 2025
**Status**: Comprehensive research complete - 3 major new documents created

---

## Overview

This index documents the complete research on how OmniSharp is built on Roslyn, including:
- Architecture and integration points
- Key Roslyn APIs used by OmniSharp
- How OmniSharp exposes Roslyn settings
- Complete diagnostic flow from Roslyn to LSP
- Roslyn version compatibility

---

## New Research Documents

### 1. OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md
**Size**: 30 KB | **Type**: Comprehensive Architecture Guide

**Contents**:
- Executive summary of OmniSharp + Roslyn relationship
- High-level architecture diagram
- Complete list of Roslyn APIs used (8 major categories)
- Configuration system and hierarchy
- Diagnostic flow from Roslyn to LSP (6-phase pipeline)
- Roslyn version compatibility table
- Key OmniSharp components (6 main modules)
- Code examples for practical usage
- References and further reading

**Best for**:
- Understanding overall architecture
- Learning which Roslyn APIs are used
- Configuration troubleshooting
- Implementation details

**Key Sections**:
```
1. Executive Summary
2. Architecture Overview
3. Roslyn APIs Used by OmniSharp
   - Workspace Layer
   - Compilation and Analysis
   - Analyzers and Code Actions
   - Syntax and Semantic Analysis
   - Formatting and EditorConfig
   - Project System Support
   - Code Classification
   - Logging and Diagnostics
4. OmniSharp Configuration and Roslyn Settings
5. Diagnostic Flow: Roslyn to LSP
6. Roslyn Version Compatibility
7. Key OmniSharp Components
8. Code Examples
9. Summary: Architectural Principles
```

---

### 2. OMNISHARP_ROSLYN_QUICK_REFERENCE.md
**Size**: 13 KB | **Type**: Quick Lookup Guide

**Contents**:
- Quick start: Enable StyleCop warnings (3 methods)
- Configuration quick reference table
- Diagnostic sources and their configuration impact
- Command-line usage examples
- Troubleshooting guide
- Roslyn version compatibility table
- LSP diagnostic severity mapping
- Performance tips for different scenarios
- Analyzer discovery locations
- Popular analyzers reference
- Useful LSP key bindings
- Configuration file locations
- Environment variable examples

**Best for**:
- Quick lookup while coding
- Configuration reference
- Troubleshooting specific issues
- Performance tuning
- Understanding diagnostic severity

**Quick Links**:
- Enable StyleCop in 30 seconds
- Fix "no diagnostics appearing" issue
- Optimize for large projects
- Environment variable format reference

---

### 3. OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md
**Size**: 29 KB | **Type**: Technical Deep-Dive

**Contents**:
- Complete diagnostic pipeline with visual timeline
- Phase 1: Roslyn Compilation (project load, parsing, semantic models)
- Phase 2: Analyzer Discovery (how analyzers are found)
- Phase 3: Diagnostic Collection (syntax, semantic, compiler diagnostics)
- Phase 4: Diagnostic Processing (OmniSharp's diagnostic worker)
- Phase 5: LSP Conversion (format transformation with code examples)
- Phase 6: Publishing (how diagnostics reach the editor)
- Configuration impact on each phase
- Performance considerations and optimization strategies
- Complete debugging guide
- Full example: From code change to editor display

**Best for**:
- Understanding complete diagnostic pipeline
- Debugging diagnostic issues
- Performance analysis
- Learning diagnostic conversion logic
- Implementation understanding

**Key Sections**:
```
1. Complete Diagnostic Pipeline (visual)
2. Phase 1: Roslyn Compilation
   - Project discovery
   - Document parsing
   - Semantic model creation
   - Compilation finalization
3. Phase 2: Analyzer Discovery
   - Source discovery
   - Analyzer registration
4. Phase 3: Diagnostic Collection
   - Syntax diagnostics
   - Semantic diagnostics
   - Compiler diagnostics
   - Diagnostic filtering
5. Phase 4: Diagnostic Processing
   - Diagnostic worker
   - Event forwarding
   - Background vs foreground analysis
6. Phase 5: LSP Conversion
   - Format conversion code
   - Severity mapping
   - Location calculation
7. Phase 6: Publishing
   - LSP notification format
   - Complete example
   - Continuous publishing
8. Configuration Impact
9. Performance Considerations
10. Debugging Diagnostics
11. Complete Example Walkthrough
12. Summary & Key Takeaways
```

---

## Document Relationships

```
OMNISHARP_ROSLYN_RESEARCH_INDEX.md (YOU ARE HERE)
│
├─ High-level Overview
│  └─ OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md
│     ├─ Understand complete architecture
│     ├─ Learn Roslyn APIs used
│     └─ See configuration system
│
├─ Quick Reference (Bookmark this!)
│  └─ OMNISHARP_ROSLYN_QUICK_REFERENCE.md
│     ├─ Quick configuration lookup
│     ├─ Troubleshooting guide
│     └─ Performance tips
│
└─ Technical Details
   └─ OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md
      ├─ Understand diagnostic pipeline
      ├─ Debug diagnostic issues
      └─ Optimize performance
```

---

## Key Findings Summary

### Architecture

**OmniSharp is fundamentally a Language Server Protocol wrapper around Roslyn's Workspace APIs.**

```
Text Editor (VSCode, Neovim, Emacs)
        ↓ (LSP Protocol)
    ┌─────────────────────┐
    │ OmniSharp Server    │
    ├─────────────────────┤
    │ LSP Handler Layer   │
    ├─────────────────────┤
    │ Service Layer       │
    ├─────────────────────┤
    │ OmniSharp Workspace │
    ├─────────────────────┤
    │ Roslyn Platform     │ ← All actual language work happens here
    └─────────────────────┘
        ↓
Project Files (.csproj, .sln, .cs)
```

### Roslyn APIs Used

**8 Major API Categories**:

1. **Workspace Layer** - `Microsoft.CodeAnalysis.Workspace`
   - Project/Document management
   - Metadata references
   - Solution organization

2. **Compilation and Analysis** - `Microsoft.CodeAnalysis.Compilation`
   - Full compilation with all metadata
   - Semantic model creation
   - Symbol binding

3. **Analyzers** - `Microsoft.CodeAnalysis.Diagnostics`
   - `DiagnosticAnalyzer` base class
   - `CompilationWithAnalyzers`
   - Analyzer discovery and execution

4. **Syntax and Semantics** - `Microsoft.CodeAnalysis.Semantics`
   - `SyntaxTree` - AST representation
   - `SemanticModel` - Compiler analysis
   - Symbol information

5. **Formatting** - `Microsoft.CodeAnalysis.Formatting`
   - Code formatting services
   - EditorConfig support

6. **Project Systems** - `Microsoft.CodeAnalysis.MSBuild`
   - Load .sln files
   - Project discovery

7. **Code Classification** - `Microsoft.CodeAnalysis.CSharp.Workspaces`
   - Semantic highlighting
   - Classification services

8. **Logging** - Internal diagnostic forwarding

### Configuration System

**3-Level Hierarchy** (with flattening):

1. **omnisharp.json** - JSON format (local or global)
   ```json
   {
     "RoslynExtensionsOptions": {
       "enableAnalyzersSupport": true
     }
   }
   ```

2. **Environment Variables** - Flattened with `:` delimiter
   ```bash
   export OMNISHARP_RoslynExtensionsOptions:EnableAnalyzersSupport=true
   ```

3. **LSP Settings** (Neovim, etc.) - Passed through settings
   ```lua
   settings = {
     RoslynExtensionsOptions = {
       EnableAnalyzersSupport = true
     }
   }
   ```

**Key Settings**:
- `RoslynExtensionsOptions.enableAnalyzersSupport` - Enable/disable analyzers
- `RoslynExtensionsOptions.analyzeOpenDocumentsOnly` - Background analysis control
- `FormattingOptions.enableEditorConfigSupport` - EditorConfig rules
- `analysisBudget` - Analyzer timeout

### Diagnostic Flow

**6-Phase Pipeline**:

1. **Roslyn Compilation** - Parse and compile project
2. **Analyzer Discovery** - Find all available analyzers (StyleCop, Roslynator, etc.)
3. **Diagnostic Collection** - Run analyzers and collect issues
4. **Diagnostic Processing** - Filter and organize diagnostics
5. **LSP Conversion** - Convert to LSP diagnostic format
6. **Publishing** - Send to editor via LSP notification

**Total time for large project**: 2-10 seconds first time, 0.5-2 seconds per edit

### Version Compatibility

**Latest Stable**: v1.39.14 with Roslyn 4.14.0-3.25168.13
**Latest Pre-release**: v1.39.15-beta.60 with Roslyn 5.1.0-1.25475.3

**Framework Support**:
- net6.0 - Primary (requires .NET 6+)
- net472 - Legacy (.NET Framework 4.7.2)

---

## How to Use These Documents

### Quick Start (5 minutes)

1. Read this index (you're doing it!)
2. Open `OMNISHARP_ROSLYN_QUICK_REFERENCE.md`
3. Find your specific need in the Quick Reference section
4. Apply the solution

### Understanding the Architecture (30 minutes)

1. Read "Executive Summary" in `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md`
2. Review "High-Level Architecture Diagram"
3. Scan the "Roslyn APIs Used by OmniSharp" section
4. Look at the "Key OmniSharp Components" section

### Deep Technical Understanding (1-2 hours)

1. Read `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md` completely
2. Read `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md` completely
3. Study the code examples in both documents
4. Reference specific sections as needed

### Troubleshooting Diagnostics

1. Check `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Troubleshooting" section
2. Use `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md` - "Debugging Diagnostics" section
3. Reference "Phase X" sections for specific part of pipeline

### Performance Optimization

1. See `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Performance Tips"
2. See `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md` - "Performance Considerations"
3. Refer to configuration examples for different scenarios

---

## Common Tasks

### Task: Enable StyleCop Warnings

**File**: `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Quick Start" section
**Time**: 5 minutes
**Steps**:
1. Create `~/.omnisharp/omnisharp.json`
2. Set `enableAnalyzersSupport: true`
3. Ensure StyleCop.Analyzers NuGet package in project
4. Restart OmniSharp

### Task: Fix "No Diagnostics Appearing"

**File**: `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Troubleshooting" section
**Time**: 10-15 minutes
**Steps**:
1. Verify configuration applied (`:LspInfo`)
2. Verify process parameters (`ps aux`)
3. Verify analyzers in project
4. Check OmniSharp logs
5. Test manually with `dotnet build`

### Task: Optimize for Large Projects

**File**: `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Performance Tips" section
**Time**: 5 minutes
**Solution**:
```json
{
  "RoslynExtensionsOptions": {
    "analyzeOpenDocumentsOnly": true,
    "analysisBudget": 300,
    "diagnosticWorkerThreadCount": 1
  }
}
```

### Task: Understand Diagnostic Conversion

**File**: `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md` - "Phase 5: LSP Conversion" section
**Time**: 20 minutes
**Contains**:
- Roslyn to OmniSharp DTO mapping
- Severity mapping logic
- Location calculation
- Complete conversion code

### Task: Debug Performance Issues

**File**: `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md` - "Performance Debugging" section
**Time**: 30 minutes
**Process**:
1. Identify slow phase (project load, compilation, analyzer run)
2. Apply performance optimization
3. Test and verify improvement

---

## Related Existing Documentation

**In same directory** (`/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/`):

- `CLAUDE.md` - Project context and configuration history
- `QUICK_FIX_GUIDE.md` - User-facing troubleshooting
- Various OMNISHARP_*.md files - Additional research from previous sessions

**External References**:
- https://github.com/OmniSharp/omnisharp-roslyn - Primary repository
- https://github.com/dotnet/roslyn - Roslyn compiler repository
- https://github.com/OmniSharp/omnisharp-roslyn/wiki/Configuration-Options - Official configuration docs

---

## Document Statistics

| Document | Size | Sections | Key Topics |
|----------|------|----------|-----------|
| OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md | 30 KB | 9 | APIs, Config, Flow, Compatibility |
| OMNISHARP_ROSLYN_QUICK_REFERENCE.md | 13 KB | 11 | Quick start, Troubleshooting, Tuning |
| OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md | 29 KB | 10 | Pipeline, Phases, Performance, Debug |

**Total New Documentation**: ~72 KB of comprehensive technical information

---

## Quick Navigation

### By Question

**Q: How is OmniSharp built?**
A: See `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md` - "Architecture Overview"

**Q: What Roslyn APIs does OmniSharp use?**
A: See `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md` - "Roslyn APIs Used by OmniSharp"

**Q: How do I enable StyleCop warnings?**
A: See `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Quick Start"

**Q: Why aren't my diagnostics showing?**
A: See `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Troubleshooting"

**Q: How do diagnostics flow from Roslyn to my editor?**
A: See `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md` - "Complete Diagnostic Pipeline"

**Q: How do I debug performance issues?**
A: See `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md` - "Debugging Diagnostics"

**Q: What versions of Roslyn are compatible?**
A: See `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md` - "Roslyn Version Compatibility"

**Q: How is configuration passed to OmniSharp?**
A: See `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md` - "OmniSharp Configuration and Roslyn Settings"

### By Role

**LSP Client Developer** (Neovim, VS Code, etc.):
→ Start with `OMNISHARP_ROSLYN_QUICK_REFERENCE.md`

**OmniSharp Contributor**:
→ Start with `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md`

**DevOps / Environment Setup**:
→ Start with `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Configuration File Locations"

**Support / Troubleshooting**:
→ Start with `OMNISHARP_ROSLYN_QUICK_REFERENCE.md` - "Troubleshooting"

**Performance Optimization**:
→ Start with `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md` - "Performance Considerations"

---

## Search Tips

**Using grep to search documentation**:

```bash
# Find references to a specific setting
grep -r "enableAnalyzersSupport" *.md

# Find all configuration examples
grep -r "omnisharp.json" *.md

# Find diagnostic-related content
grep -r "diagnostic" OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md | head -20

# Find performance tips
grep -r "performance\|slow\|hang" *.md | grep -i omnisharp
```

---

## Contribution Notes

**For future updates**:

1. **Architecture Changes**: Update `OMNISHARP_ROSLYN_ARCHITECTURE_RESEARCH.md`
2. **New Configuration Options**: Update `OMNISHARP_ROSLYN_QUICK_REFERENCE.md`
3. **Diagnostic Flow Changes**: Update `OMNISHARP_DIAGNOSTIC_FLOW_DETAILED.md`
4. **New Findings**: Create new document with `OMNISHARP_` prefix

**Format Consistency**:
- Use markdown formatting
- Include code examples where applicable
- Add TOC for documents >10 KB
- Reference other documents with file paths
- Include timestamps and status

---

## Summary

This research package provides **comprehensive documentation** of:

1. **How OmniSharp is built on Roslyn** - Architecture and integration points
2. **Which Roslyn APIs OmniSharp uses** - 8 major API categories with examples
3. **How Roslyn settings are exposed** - Configuration hierarchy and environment variables
4. **Complete diagnostic pipeline** - 6-phase flow from Roslyn to LSP client
5. **Version compatibility** - Roslyn and OmniSharp version relationships

**Three documents work together**:
- **Architecture Research** - Deep understanding
- **Quick Reference** - Quick lookup and troubleshooting
- **Diagnostic Flow** - Technical implementation details

Choose your entry point based on your needs, then navigate as required.

---

**Research Completed**: November 13, 2025
**Status**: Ready for use
**Last Updated**: November 13, 2025 16:22 UTC

**Navigation**: Use this file as your starting point for any OmniSharp + Roslyn questions!
