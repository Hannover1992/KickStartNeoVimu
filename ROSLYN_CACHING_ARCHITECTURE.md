# Roslyn Caching Architecture - Deep Dive

**Technical deep-dive into Roslyn's multi-layered caching system**

---

## Overview: The Three Levels of Roslyn Caching

Roslyn implements three distinct levels of caching, each optimizing different aspects of compilation:

```
LEVEL 1: SYNTAX TREE CACHE
├─ What: Parsed code structure
├─ Keyed by: Source file content hash
├─ Speed: ~5-10ms per file (just parsing)
└─ Invalidation: When file content changes

LEVEL 2: COMPILATION CACHE (Symbol Table)
├─ What: Symbol definitions, types, bindings
├─ Keyed by: Syntax trees + references (value equality)
├─ Speed: ~50-200ms per file (semantic analysis)
└─ Invalidation: When syntax trees change OR references change

LEVEL 3: ANALYZER CACHE
├─ What: Diagnostic results (warnings, errors)
├─ Keyed by: Compilation + file being analyzed
├─ Speed: ~10-50ms per file (just reporting)
└─ Invalidation: When compilation changes
```

---

## Level 1: Syntax Tree Caching

### Architecture

```
Source File Input
       ↓
[File Content Hash Calculated]
       ↓
Query Syntax Tree Cache
       ├─ CACHE HIT (hash matches)
       │  └─ Return cached SyntaxTree
       │
       └─ CACHE MISS (hash differs or first time)
          ├─ Parse source text
          ├─ Build syntax tree (immutable)
          ├─ Store in cache with hash
          └─ Return SyntaxTree
```

### Key Properties

**Immutability:**
```
SyntaxTree is immutable
  ├─ Can be safely shared across threads
  ├─ Can be reused in multiple compilations
  ├─ Changes create new tree, don't modify existing
  └─ Old tree can be garbage collected
```

**Comparison Strategy:**
```
Hash(FileContent_1) vs Hash(FileContent_2)
  ├─ If EQUAL
  │  └─ Syntax trees guaranteed identical
  │     (same token stream, same structure)
  │     → REUSE cached tree
  │
  └─ If DIFFERENT
     └─ Re-parse and create new tree
        (content changed, structure may differ)
```

### Example: Single Character Change

```
Scenario: Add a comment to Program.cs
Before:   Console.WriteLine("Hello");
After:    // Comment here
          Console.WriteLine("Hello");

File hash changes:
  Before: SHA256(content) = 0xABC...
  After:  SHA256(content) = 0xXYZ...

Result: Syntax tree must be re-parsed (~10ms)
```

### Example: Whitespace-Only Change

```
Scenario: Add blank line (comment still there, code unchanged)
Before:   // Comment here
          Console.WriteLine("Hello");

After:    // Comment here

          Console.WriteLine("Hello");

File hash changes (content is different):
  Before: SHA256(content) = 0xABC...
  After:  SHA256(content) = 0xZZZ...

Result: Must re-parse, but resulting AST structure is similar
```

---

## Level 2: Compilation Cache (Symbol Table)

### Architecture

```
Compilation Creation Request
       ↓
[Build new Compilation with N syntax trees]
       ↓
Compare Compilation to Previous Compilation
       ├─ Syntax trees: VALUE EQUALITY check
       ├─ References: VALUE EQUALITY check
       └─ Options: VALUE EQUALITY check
       ↓
For each unchanged input:
  └─ Copy reference to cached symbols
     (don't recompute declarations/bindings)
       ↓
For each changed input:
  └─ Recompute symbols
     (declaration + binding phases)
       ↓
Merged Compilation with partial cache reuse
```

### Key Mechanism: Value Equality

**Roslyn uses VALUE EQUALITY (not reference equality):**

```csharp
// Conceptual code
public bool CompileationsEqual(Compilation old, Compilation new)
{
    // Check each component with value equality
    if (old.SyntaxTrees.Count == new.SyntaxTrees.Count)
    {
        for (int i = 0; i < old.SyntaxTrees.Count; i++)
        {
            // SyntaxTrees are compared by VALUE
            // (structure + content), not by reference
            if (!SyntaxTreesEqual(old.SyntaxTrees[i], new.SyntaxTrees[i]))
                return false;
        }
    }
    else
        return false;

    // Same for references...
    // if (!ReferencesEqual(old.References, new.References))
    //     return false;

    return true;
}
```

### Item-Wise Transformation (Key Optimization)

**When compilation changes at the collection level:**

```
Compilation N-1 (previous):
  Project A: SyntaxTree[A1, A2, A3]
  Project B: SyntaxTree[B1, B2]
  Project C: SyntaxTree[C1, C2, C3, C4]

Change: User edits B1

Compilation N (new):
  Project A: SyntaxTree[A1, A2, A3]  ← UNCHANGED
  Project B: SyntaxTree[B1', B2]     ← B1 changed
  Project C: SyntaxTree[C1, C2, C3, C4] ← UNCHANGED

Roslyn's optimization:
  ├─ Tree A1: SAME as before → REUSE cached symbols
  ├─ Tree A2: SAME as before → REUSE cached symbols
  ├─ Tree A3: SAME as before → REUSE cached symbols
  ├─ Tree B1: DIFFERENT → Recompute symbols (ONLY THIS ONE)
  ├─ Tree B2: SAME as before → REUSE cached symbols
  └─ Trees C1-C4: SAME as before → REUSE cached symbols

Result: 1 file changed = 1 file recomputed ✅
        Not all 12 files recomputed ✅
```

### Symbol Table Caching

```
Symbol Table Cache (in Compilation object)
├─ Global namespace symbol
├─ Namespaces: Dictionary[string, NamespaceSymbol]
├─ Types: Dictionary[string, INamedTypeSymbol]
├─ Methods: Dictionary[string, IMethodSymbol]
└─ Fields/Properties: Dictionary[string, ISymbol]
    ↓
When accessed (e.g., "Find all usages of MyClass"):
  ├─ Lookup in symbol table cache: FAST ~1ms
  └─ Not recomputed unless syntax changed
```

### Example: Cross-File Change

```
Scenario: UserService.cs modified
          UserController.cs depends on UserService

What happens:
  1. UserService.cs syntax tree changes
     → Symbol table for UserService recomputed (~50ms)

  2. UserController.cs syntax tree unchanged
     → BUT it depends on UserService
     → Binding needs to be redone (~50ms)
     → Symbol cache for UserController invalidated

  3. Other files unchanged and independent
     → Symbol caches remain valid (~0ms)

Total recomputation: ~100ms for 2 files (not all files in solution)
```

---

## Level 3: Analyzer Execution Cache

### Analyzer Execution Flow

```
Compilation Ready
       ↓
Initialize Analyzer State
  ├─ OnCompilationStart callbacks
  └─ Set up any caches needed
       ↓
For each File in Compilation:
  ├─ Get SemanticModel (uses Level 2 cache)
  ├─ Visit syntax tree nodes
  │  └─ Call analyzer for each node type
  │
  └─ For each Symbol:
     └─ Call analyzer for symbol
       ↓
Analyzer Results Cached
  └─ Key: (Compilation, File, Analyzer)
  └─ Value: Diagnostics found
       ↓
Finalize
  ├─ OnCompilationEnd callbacks
  └─ Dispose analyzer state
```

### Analyzer Caching Within Compilation

**When same analyzer runs on same compilation twice:**

```
First Run:
  └─ Symbol table computed and in memory
  └─ All semantic information available
  └─ Analyzer produces diagnostics

Second Run (same compilation, different analyzer):
  └─ Symbol table ALREADY IN MEMORY
  └─ Reused for this analyzer
  └─ ~10-30% faster than first run

Third Run (DIFFERENT compilation due to file change):
  └─ OLD symbol table discarded (memory freed)
  └─ NEW symbol table computed
  └─ Analyzer produces new diagnostics
```

### Analyzer Result Cache Invalidation

```
Scenario: Two files, single analyzer

State 1 (Initial):
  FileA.cs
  FileB.cs
  Analyzer results cached:
    ├─ [Compilation₁, FileA] → [Diagnostic1, Diagnostic2]
    └─ [Compilation₁, FileB] → [Diagnostic3]

User edits FileB.cs

State 2 (After edit):
  FileA.cs (unchanged)
  FileB.cs (changed)

  Cache state:
    ├─ [Compilation₁, FileA] → KEEP (but Compilation₁ now unused)
    ├─ [Compilation₁, FileB] → INVALIDATE (old compilation)
    └─ [Compilation₂, FileB] → RECOMPUTE (new compilation)

  Analyzer runs on FileB with Compilation₂
  Produces new diagnostics

  FileA:
    ├─ SemanticModel reused (Level 2 cache)
    ├─ If symbol used by FileB changed
    │  └─ FileA analyzer must re-run
    │  └─ Detects FileA breakage
    └─ Diagnostics updated
```

---

## How to Verify Caching is Working

### Check OmniSharp Logs

```bash
# Linux/WSL
tail -f ~/.local/state/nvim/lsp.log

# Look for messages like:
# "Reusing previous compilation"
# "Updated compilation"
# "Analyzed 1 file out of 150"  ← Good! Not all 150
```

### Observe Response Times

```
Edit file → Wait for diagnostics
├─ < 200ms : Excellent (cached symbols)
├─ 200-500ms : Good (some analysis)
├─ 500ms-2s : Acceptable (more analysis)
└─ > 2s : Something wrong (check logs)
```

### Compare with/without caching

**Scenario: Make 5 consecutive single-character edits to same file**

With caching working:
```
Edit 1: 300ms response → First full analysis
Edit 2: 200ms response → Some reuse
Edit 3: 200ms response → More reuse
Edit 4: 200ms response → Cache hits
Edit 5: 200ms response → Cache hits

Average after first: ~200ms ✅
```

Without caching (if broken):
```
Edit 1: 300ms response
Edit 2: 300ms response → FULL REANALYSIS
Edit 3: 300ms response → FULL REANALYSIS
Edit 4: 300ms response → FULL REANALYSIS
Edit 5: 300ms response → FULL REANALYSIS

Every edit same cost → Cache not working ❌
```

---

## Level-by-Level Caching Example: Complete Flow

### Scenario: User edits UserService.cs

```
TIME T1: Initial State
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Source files:
  UserService.cs (version A)
  UserController.cs (depends on UserService)

Compilation Cache State:
  ├─ Compilation₁ (syntax trees for both)
  │  └─ Symbol table cached
  └─ Analyzer results cached for both files

═══════════════════════════════════════════

USER EDITS: Saves UserService.cs
┊
┊ T2: File Read
┊
┊ Roslyn detects: UserService.cs modified


TIME T3: Level 1 Caching - Syntax Trees
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UserService.cs new hash ≠ old hash
  └─ Re-parse UserService.cs → SyntaxTree₂ (~10ms)

UserController.cs unchanged
  └─ Syntax tree reused (no re-parse) ✅


TIME T4: Level 2 Caching - Compilation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Build Compilation₂:
  ├─ SyntaxTree₂ (UserService, changed)
  │  └─ Must recompute symbols (~50ms)
  │
  └─ SyntaxTree₁ (UserController, unchanged)
     └─ Symbol references can be reused ✅

Symbol table comparison:
  UserController symbols reference UserService symbols
  → UserService symbols changed
  → UserController's references now invalid
  → Rebind UserController symbols (~50ms)

Symbol table delta:
  ├─ UserService symbols: RECOMPUTED
  ├─ UserController symbols: PARTIALLY REUSED (binding repeated)
  └─ Other project symbols: FULLY REUSED ✅


TIME T5: Level 3 Caching - Analyzers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

With AnalyzeOpenDocumentsOnly = false:
  ├─ UserService.cs: Analyzer runs (~30ms)
  ├─ UserController.cs: Analyzer runs (~30ms)
  │  (Symbols changed, must re-analyze)
  └─ Other files in solution: NOT analyzed ✅
     (symbols unchanged, don't affect them)

Diagnostic results:
  ├─ UserService diagnostics: UPDATED
  ├─ UserController diagnostics: UPDATED
  └─ Others: REUSED FROM CACHE ✅


TIMING SUMMARY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Time T3 (syntax tree parsing):       10ms
Time T4 (compilation + symbols):     100ms  (could reuse some of this!)
Time T5 (analyzer run):              60ms   (only 2 files)

Total: ~170ms for IDE response ✅

WITHOUT CACHING:
  If entire solution analyzed: 500-2000ms ❌
  If all symbols recomputed: 500-1000ms ❌
```

---

## Performance Characteristics by Cache Level

### Level 1: Syntax Tree Parsing Performance

```
Small file (< 1KB):       ~1-5ms
Medium file (1-10KB):     ~5-15ms
Large file (10-100KB):    ~20-50ms
Huge file (100KB+):       ~100-500ms

BUT: With syntax tree cache → 0ms (cache hit)
     Difference: 5-500ms saved per keystroke!
```

### Level 2: Compilation/Symbol Performance

```
Small project (< 50 files):      50-200ms per change
Medium project (50-500 files):   200-500ms per change
Large project (500-2000 files):  1-5 seconds per change

WITH CACHING:
  - Changed file + dependents: recomputed
  - Unchanged files: 0ms (symbols cached)

WITHOUT CACHING:
  - Every file recompiled regardless
  - 5-10x slower
```

### Level 3: Analyzer Performance

```
Per analyzer per file:        5-50ms (depends on complexity)
With N=10 analyzers:          50-500ms per file

WITH AnalyzeOpenDocumentsOnly=true on 1000-file project:
  - Only open files analyzed:  ~100ms total
  - Unopened files cached:     ~0ms

WITHOUT AnalyzeOpenDocumentsOnly:
  - All 1000 files analyzed:   ~50-500 seconds total ❌
  - Huge IDE latency
```

---

## Worst-Case Scenarios (Cache Invalidation)

### Scenario 1: Change Breaks Entire Dependency Tree

```
ProjectA (changed)
  ↓ depends on
ProjectB
  ↓ depends on
ProjectC
  ↓ depends on
ProjectD

Change in ProjectA:
  └─ Invalidates cache for: A, B, C, D
  └─ Must recompile all (~2-5 seconds)
  └─ But only 4 projects affected, not all!
```

### Scenario 2: Circular Dependencies

```
ProjectA depends on ProjectB
ProjectB depends on ProjectA
  └─ Change in A → affects B
  └─ Change in B → affects A
  └─ Forces recompile of both every time
  └─ 50% performance loss vs linear deps
```

### Scenario 3: Bad Source Generator

```
Generator caches ISymbol in model:
  ├─ ISymbol prevents old Compilation garbage collection
  ├─ Old compiler symbols kept in memory
  ├─ Memory usage grows: 500MB → 2GB over time
  ├─ Generator can't reuse cache (value equality broken)
  ├─ Every compilation full recomputation
  └─ Performance degrades to ~100ms+ per keystroke
```

---

## Monitoring Cache Effectiveness

### Key Metrics to Watch

```
Metric 1: Response Time Per Keystroke
  ├─ < 200ms = Cache very effective
  ├─ 200-500ms = Cache effective
  ├─ 500ms-2s = Cache somewhat effective
  └─ > 2s = Cache not effective or too much work

Metric 2: Memory Usage
  ├─ Stable (doesn't grow) = Cache working well
  ├─ Slowly growing = Minor cache misses
  └─ Rapidly growing (500MB/min) = Bad cache issue

Metric 3: CPU Usage
  ├─ Spike during edit = Expected recompilation
  ├─ Sustained high CPU = Cache not working
  ├─ Consistent low baseline = Cache working well
```

### Tools to Monitor

**OmniSharp logs:**
```bash
tail -f ~/.local/state/nvim/lsp.log | grep -i "compilation\|cache"
```

**System monitoring:**
```bash
# Linux/macOS
top -p $(pgrep -f omnisharp)

# Watch memory growth over 5 minutes of editing
watch -n 1 'ps aux | grep omnisharp | grep -v grep | awk "{print \$6}"'
```

---

## Optimization Strategies by Cache Level

### Level 1 Optimizations (Syntax Trees)

**Rarely needed** (parsing is fast)

```
If parse time bottleneck:
  ├─ Check file size (unusually large?)
  ├─ Check if file has extremely deep nesting
  └─ Usually indicates malformed code
```

### Level 2 Optimizations (Symbol Table)

**Most impactful:**

```
✅ Reduce project count
   └─ Each project needs separate symbol table
   └─ Combining 5 projects into 1: -5x recompilation

✅ Break circular dependencies
   └─ A → B → C (clean) = fast
   └─ A ↔ B (circular) = slow
   └─ Find and refactor

✅ Reduce compilation dependencies
   └─ If only ProjectA needs ProjectB
   └─ Remove ProjectA → B → C → A → ... chains
```

### Level 3 Optimizations (Analyzers)

**Most user-controlled:**

```
✅ Use AnalyzeOpenDocumentsOnly=true for large projects
   └─ Only analyze files you're looking at

✅ Reduce analyzer count
   └─ 5 analyzers: ~50ms per file
   └─ 20 analyzers: ~200ms per file
   └─ Disable unused analyzers

✅ Use ForAttributeWithMetadataName in generators
   └─ 99x faster than CreateSyntaxProvider
   └─ Enables better caching
```

---

## Summary: The Caching Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ LEVEL 1: Syntax Tree Cache                              │
│ ─────────────────────────────────────────────────────   │
│ Keyed by: File content hash                             │
│ Speed: 5-50ms per file (if not cached)                  │
│ Savings: Up to 50ms per edit                            │
│ When invalidated: File content changes                  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ LEVEL 2: Compilation Cache (Symbol Table)              │
│ ─────────────────────────────────────────────────────   │
│ Keyed by: Syntax trees + references (value equality)   │
│ Speed: 50-200ms per file (if not cached)                │
│ Savings: Up to 200ms per edit                           │
│ When invalidated: Syntax trees or references change    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ LEVEL 3: Analyzer Cache (Diagnostic Results)           │
│ ─────────────────────────────────────────────────────   │
│ Keyed by: Compilation + file                           │
│ Speed: 10-50ms per file (if not cached)                 │
│ Savings: Up to 50ms per edit (per analyzer)             │
│ When invalidated: Compilation changes                  │
│ Controllable via: AnalyzeOpenDocumentsOnly             │
└─────────────────────────────────────────────────────────┘

Total potential savings: 50 + 200 + 50 = 300ms per keystroke
Typical IDE response times with caching: 100-300ms
Without caching: 1-5 seconds
```

---

## References

- Roslyn Architecture: https://github.com/dotnet/roslyn
- Incremental Generators: https://github.com/dotnet/roslyn/blob/main/docs/features/incremental-generators.md
- OmniSharp Roslyn: https://github.com/OmniSharp/omnisharp-roslyn

