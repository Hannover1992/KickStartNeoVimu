# Roslyn Performance - Quick Reference Guide

**For busy developers who want practical answers, not theory.**

---

## Q1: How fast is Roslyn incremental compilation?

**Answer:**
- **Single file change in small project (<50 files):** ~100-300ms
- **Single file change in medium project (50-500 files):** ~300ms-2s
- **Single file change in large project (1000+ files):** ~2-10s
- **Full project first compilation:** 5-60s (depends on project size)

**Why:** Only the changed file and its dependents are recompiled. Unchanged files use cached syntax trees and semantic information.

---

## Q2: What slows down Roslyn?

**Biggest performance killers (ranked):**

| Killer | Impact | Fix |
|--------|--------|-----|
| Analyzing entire solution | ~1000ms+ | Use `AnalyzeOpenDocumentsOnly = true` |
| Complex analyzers | ~50-200ms per file | Disable unused analyzers |
| Many analyzers running | O(n) additive | Reduce from 20+ to 5-10 analyzers |
| Deep cross-file dependencies | 100-500ms | Reduce project interdependencies |
| Inlay hints rendering | 50-100ms per keystroke | Disable in config |
| Symbol lookups on large compilation | 100-1000ms | Use `ForAttributeWithMetadataName` in generators |

---

## Q3: Should I use AnalyzeOpenDocumentsOnly?

**Decision tree:**

```
Is your project > 100 files?
├─ YES → Use AnalyzeOpenDocumentsOnly = true
│        You'll get faster IDE response
│        (you'll see diagnostics for unopened files when you open them)
│
└─ NO → Use AnalyzeOpenDocumentsOnly = false
         Quick enough anyway, and you see all issues upfront
```

**Real-world impact:**
- **With = true:** IDE responds in 100-300ms, shows unopened file issues on open
- **With = false:** IDE responds in 500ms-2s, shows all issues immediately

---

## Q4: What should I cache if I'm writing custom code?

**What to cache:**
- ✅ String values extracted from symbols
- ✅ `record` types with only value-type fields
- ✅ Parsed AST snapshots (immutable)
- ✅ Compilation snapshots

**What NOT to cache:**
- ❌ `ISymbol` objects
- ❌ `SyntaxNode` objects
- ❌ Mutable collections
- ❌ Raw `Compilation` objects in models

**Why:** Caching `ISymbol` prevents garbage collection of old compilations, causing memory bloat.

---

## Q5: Why did my code analysis suddenly get slow?

**Checklist:**

1. **Did you add a new analyzer?**
   - Run `:LspInfo` to see which analyzers are loaded
   - Disable unused ones
   - Each analyzer adds ~10-50ms latency per file

2. **Did you open a larger project?**
   - Roslyn performance scales O(n) with file count
   - Larger projects naturally slower
   - Use `AnalyzeOpenDocumentsOnly = true`

3. **Did you check if only one file changed?**
   - Roslyn should only reprocess that file + dependents
   - If entire solution reprocesses, something's wrong
   - Check OmniSharp logs

4. **Did someone add circular dependencies?**
   - Project A depends on B, B depends on A
   - Forces full recompilation of both
   - Refactor to break cycle

---

## Q6: How does Roslyn caching work?

**Simple explanation:**

```
Step 1: Roslyn sees file changed
        ↓
Step 2: Hash the file content
        ↓
Step 3: Compare hash with cached version
        ├─ MATCH → Reuse cached syntax tree ✅
        └─ NO MATCH → Re-parse file
        ↓
Step 4: Parse syntax tree (fast, ~10-50ms)
        ↓
Step 5: Update semantic model (medium, ~50-200ms)
        ↓
Step 6: Run analyzers on changed + dependent files (slow, ~50-1000ms)
```

**Key insight:** Steps 1-3 skip reprocessing unchanged files. Step 4 skips reanalysis of unchanged syntax.

---

## Q7: What are the two types of Roslyn caching?

### Type 1: Syntax Tree Caching
**What:** Parsed structure of code
**When:** Stays cached if file content unchanged
**Speed:** Parsing is relatively fast
**Example:** File with just a whitespace change → tree could be reused (if unchanged semantically)

### Type 2: Semantic Model Caching
**What:** Symbols, types, bindings (the "meaning" of code)
**When:** Reused if syntax tree unchanged
**Speed:** Semantic analysis slower than parsing
**Example:** Add a comment → syntax tree unchanged → semantic model reused

---

## Q8: How do source generators affect performance?

**Incremental generators (v2):**
- Fast because they use caching
- Only recompute when their input changes
- Support `record` type value equality for efficient comparison

**Impact if misconfigured:**
```csharp
// BAD: Includes ISymbol
record MyModel(ISymbol Type);
→ Generator can't cache effectively
→ Full recomputation every time

// GOOD: Only strings
record MyModel(string TypeName);
→ Generator caches and reuses efficiently
→ 10-100x faster
```

---

## Q9: Practical optimization checklist

**For maximum IDE responsiveness:**

- [ ] Set `AnalyzeOpenDocumentsOnly = true` if project > 100 files
- [ ] List enabled analyzers with `:LspInfo`
- [ ] Remove analyzers you don't use (especially unused code detectors)
- [ ] Disable inlay hints in config (50-100ms overhead)
- [ ] Keep project under 500 files per project (split if larger)
- [ ] Reduce circular dependencies between projects
- [ ] Use `dotnet restore --force-evaluate` if WSL2 + Windows cross-compilation

**For CI/CD:**

- [ ] Disable IDE-only features (InlayHints, InlineCodeLens)
- [ ] Keep `AnalyzeOpenDocumentsOnly = false` (want all issues)
- [ ] Run with `--no-restore` (assume dependencies cached)
- [ ] Consider parallel analyzer execution

---

## Q10: OmniSharp configuration settings explained

```json
{
  "RoslynExtensionsOptions": {
    // Enable/disable analyzer support
    "EnableAnalyzersSupport": true,

    // Import completion (auto-import suggestions)
    "EnableImportCompletion": true,

    // CRITICAL: Analyze only open files (set to true for large projects)
    "AnalyzeOpenDocumentsOnly": false,

    // Include pre-release SDK when resolving packages
    "InlayHints": {
      "EnableForParameters": false,      // Disable for speed
      "EnableForTypes": false,           // Disable for speed
      "EnableForLambdaParameterTypes": false
    }
  },

  "FormattingOptions": {
    "EnableEditorConfigSupport": true,  // Use .editorconfig rules
    "OrganizeImports": true             // Sort using statements
  }
}
```

---

## Roslyn Performance by the Numbers

### Typical Timings (Modern Hardware)

| Operation | Time | Notes |
|-----------|------|-------|
| Parse single file | 5-10ms | Fast |
| Semantic analysis single file | 20-100ms | Medium |
| Single analyzer on single file | 5-50ms | Depends on complexity |
| Full solution first scan (1000 files) | 10-60s | One-time only |
| Incremental update (1 file changed) | 100-500ms | Depends on dependencies |
| Analyzer suite (20 analyzers) | 50-200ms per file | Cumulative |

### Memory Usage

| Scenario | Memory | Notes |
|----------|--------|-------|
| Typical project (100 files) | 200-500 MB | Roslyn + LSP server |
| Large project (1000 files) | 1-3 GB | Can be high with full analysis |
| With bad caching (ISymbol cached) | 3-8 GB | Old compilations not freed |

---

## When to Suspect Performance Issues

**Rule of Thumb:**
- Expect IDE response **< 500ms** for edits
- Expect analysis **< 1s** for file open/save
- Expect analyzer run **< 2s** for keystroke

If you're seeing:
- **> 1s response time** → Check `AnalyzeOpenDocumentsOnly`, reduce analyzers
- **> 5s on save** → Disable complex analyzers, check for circular deps
- **Memory growing** → Check for ISymbol in source generators
- **Entire solution recompiling** → You have a circular dependency

---

## The Golden Rule

**"Code is fast to analyze when unchanged."**

This is Roslyn's entire design philosophy:
1. Immutable objects enable safe caching
2. Value equality enables comparison without computation
3. Fine-grained transformations enable item-wise caching
4. Only the minimum necessary gets recomputed

If Roslyn is slow, you're probably:
- Analyzing too much (disable `AnalyzeOpenDocumentsOnly = false` on large projects)
- Caching wrong things (using `ISymbol` in generators)
- Running too many analyzers (disable unused ones)
- Working with circular dependencies (refactor project structure)

---

## Quick Wins for Performance

**Immediate improvements (< 5 minutes):**

1. Add to `omnisharp.json`:
```json
{
  "RoslynExtensionsOptions": {
    "AnalyzeOpenDocumentsOnly": true
  }
}
```
**Expected improvement:** 20-50% faster IDE response on large projects

2. List analyzers:
```vim
:LspInfo
```
**Look for:** Unnecessary analyzers like unused code detectors
**Action:** Remove ones you don't actively use

3. Disable inlay hints:
```vim
:LspInfo → Look for "textDocument/inlayHint"
```
**Expected improvement:** 10-20% faster keystroke response

---

## References

- Full research: `/mnt/c/Users/Administrator/Documents/Projekt/KickStartNeoVim/ROSLYN_PERFORMANCE_RESEARCH.md`
- Roslyn docs: https://github.com/dotnet/roslyn
- OmniSharp docs: https://github.com/OmniSharp/omnisharp-roslyn

