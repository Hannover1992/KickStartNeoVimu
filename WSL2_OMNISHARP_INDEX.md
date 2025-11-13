# WSL2 + OmniSharp Research Index

**Quick Navigation to All Research Documents**

Created: 2025-11-13
Research Completed: Comprehensive WSL2-specific OmniSharp analysis
Status: ✅ Ready for implementation

---

## Quick Start (2 Minutes)

### 1️⃣ What's the Answer?
**Q: Does OmniSharp work with /mnt/c paths in WSL2?**

**A: Yes, but it's 10x slower than native Linux paths. Here's what to do:**

- **If you want it working now**: Follow Quick Reference → Use /mnt/c (accept 20-30s startup)
- **If you want it fast**: Follow Quick Reference → Move to /home (2-3s startup)

### 2️⃣ Start Here Based on Your Situation

| Your Situation | Read This | Time |
|---|---|---|
| **"Just tell me what's wrong"** | WSL2_OMNISHARP_QUICK_REFERENCE.md | 5 min |
| **"I want to implement a fix"** | WSL2_OMNISHARP_CONFIG_RECOMMENDATIONS.md | 15 min |
| **"I need to understand WHY"** | WSL2_OMNISHARP_RESEARCH.md | 30+ min |
| **"Navigation guide"** | This file (WSL2_OMNISHARP_INDEX.md) | 2 min |

### 3️⃣ TL;DR

**The Problem**:
- OmniSharp can load from `/mnt/c/...` paths
- But filesystem access is 10x slower via DrvFs (Windows filesystem layer)
- NuGet caches are separate between Windows and WSL2
- File locking possible when both access simultaneously

**The Solution** (pick one):
1. **Scenario A** (Quick): Stay on /mnt/c, accept slowness, use `fixlsp` alias
2. **Scenario B** (Recommended): Move to ~/projects, enjoy 10x speed boost
3. **Scenario C** (Hybrid): Use /home for speed, sync to Windows when needed

---

## Document Library

### 📄 WSL2_OMNISHARP_QUICK_REFERENCE.md
**Length**: 1-2 pages (cheat sheet)
**Reading time**: 5 minutes
**Best for**: Quick lookups and immediate answers

**Contains**:
- Does OmniSharp work? (Yes/No table)
- 4 Key Issues explained simply
- Symptom → Solution lookup
- Copy-paste fixes
- One-minute troubleshooting

**When to read**: You need a quick answer, have a specific symptom, or want the cheat sheet

**Key snippet**:
```bash
# Add to ~/.bashrc
export NUGET_PACKAGES="$HOME/.nuget/packages"
alias fixlsp='dotnet restore --force-evaluate --no-cache && pkill -f omnisharp'
```

---

### 📘 WSL2_OMNISHARP_CONFIG_RECOMMENDATIONS.md
**Length**: 6-8 pages
**Reading time**: 15-20 minutes
**Best for**: Implementation and scenario selection

**Contains**:
- **Scenario 1**: Keep /mnt/c (accept slowness)
  - When to use, pros/cons, step-by-step
- **Scenario 2**: Move to /home (RECOMMENDED)
  - When to use, pros/cons, step-by-step
- **Scenario 3**: Hybrid (fastest with sync)
  - When to use, pros/cons, sync helpers
- **Scenario 4**: Symlink approach (not recommended)
- Complete init.lua configs for each
- ~/.bashrc setup for each
- NuGet cache options
- Verification script
- Implementation checklist

**When to read**: Ready to implement a solution, need step-by-step instructions

**Key selection**:
- Small project + want simplicity → Scenario 1
- Large project + want speed → Scenario 2 ⭐ RECOMMENDED
- Need Windows + WSL2 access → Scenario 3
- Everything else → Scenario 2

---

### 📗 WSL2_OMNISHARP_RESEARCH.md
**Length**: 30+ pages
**Reading time**: 45-60 minutes
**Best for**: Deep technical understanding

**Contains**:
1. **Filesystem Performance** (10x slowness)
   - Why it's slow (DrvFs layer)
   - Measurements and benchmarks
   - Solutions (move to /home)

2. **NuGet Cache Incompatibility**
   - Windows vs WSL2 separate caches
   - Environment variable configuration
   - Shared cache strategies

3. **Case Sensitivity Issues**
   - Windows case-insensitive vs WSL2 case-sensitive
   - How it affects OmniSharp
   - Solutions (exact casing, prefer /home)

4. **File Locking and Interop**
   - Windows locks during build
   - WSL2 can't break Windows locks
   - Solutions (use dotnet + DLL, avoid simultaneous builds)

5. **Symlink Handling**
   - OmniSharp may not follow symlinks on /mnt/c
   - Solutions (avoid symlinks, use copies)

6. **Optimal Configuration**
   - Recommended init.lua setup
   - Alternative native Linux paths
   - Environment setup

7. **Troubleshooting Checklist**
   - OmniSharp won't connect
   - NuGet packages not found
   - Intellisense slow
   - Files locked

8. **Performance Comparison**
   - /mnt/c vs /home benchmarks
   - Recommendation table

9. **Known Issues & Workarounds**
   - Issue 1: "No LSP client attached"
   - Issue 2: "dotnet: not found"
   - Issue 3: File lock errors

10. **References & Further Reading**

**When to read**: Need to understand the technical details, want background knowledge, debugging complex issues

**Key insight**:
```
/mnt/c performance:  25-30s OmniSharp startup
/home performance:    2-3s OmniSharp startup
                      ↓
                   10x FASTER!
```

---

### 📋 WSL2_RESEARCH_SUMMARY.md
**Length**: 4-5 pages
**Reading time**: 10 minutes
**Best for**: Executive summary and overview

**Contains**:
- Direct answer to the main question
- Summary of all 3 documents
- Key findings (5 major discoveries)
- Recommended implementation (3 tiers)
- Configuration checklist
- Performance expectations
- Next steps (immediate, short-term, long-term)
- Troubleshooting decision tree
- Technical details reference
- System information
- Document navigation map
- Conclusion

**When to read**: Want overview before diving into details, need to brief someone else on findings

---

## Decision Tree: Which Document?

```
START: "I need help with WSL2 + OmniSharp"
│
├─ "Give me a quick answer" → Quick Reference (5 min)
│  └─ Get immediate answers and symptom fixes
│
├─ "I want to fix it now" → Config Recommendations (15 min)
│  ├─ Pick Scenario A/B/C
│  ├─ Follow step-by-step
│  └─ Test and verify
│
├─ "I need to understand why" → Research Document (45 min)
│  ├─ Learn about DrvFs, NuGet, file locking
│  ├─ Understand performance characteristics
│  └─ Deep technical knowledge
│
├─ "I want an overview first" → Summary (10 min)
│  ├─ Understand key findings
│  ├─ Read all important details quickly
│  └─ Decide which detailed doc to read
│
└─ "What's this all about?" → This file (2 min)
   └─ Navigation guide (you are here!)
```

---

## Common Questions Answered

### "Does OmniSharp work with /mnt/c paths?"
**See**: Quick Reference → "Does OmniSharp Work with /mnt/c Paths?"
**Quick answer**: Yes ✅, but 10x slower ⚠️

### "What's slow about /mnt/c?"
**See**: Research.md → "Filesystem Performance Analysis"
**Quick answer**: DrvFs layer adds overhead for every file access

### "My NuGet packages aren't found"
**See**: Quick Reference → Symptoms and Solutions table
**Quick answer**: Set `export NUGET_PACKAGES="$HOME/.nuget/packages"` in ~/.bashrc

### "How do I fix this TODAY?"
**See**: Config Recommendations → Scenario 1 (keep /mnt/c)
**Quick answer**: Follow steps, use `fixlsp` alias, accept 20-30s startup

### "What's the BEST solution?"
**See**: Config Recommendations → Scenario 2 (move to /home)
**Quick answer**: 10x faster, more reliable, recommended for serious development

### "My OmniSharp won't start"
**See**: Quick Reference → "Symptoms and Solutions" or Research.md → "Troubleshooting Checklist"
**Quick answer**: Run: `pkill -f omnisharp && rm -rf ~/.cache/nvim/luac/ && fixlsp`

### "Why 10x slower?"
**See**: Research.md → "Filesystem Performance Analysis"
**Quick answer**: Windows filesystem accessed through WSL2's DrvFs layer incurs boundary crossing overhead for every I/O operation

### "Can I use OmniSharp.exe?"
**See**: Research.md → "File Locking and Interop Issues"
**Quick answer**: No ❌, it's Windows-only. Use `dotnet OmniSharp.dll` instead ✅

### "Should I move to /home?"
**See**: Config Recommendations → "Scenario 2"
**Quick answer**: Yes ✅ if project is large (500+ files) or speed matters. No ⚠️ if project is small and single filesystem is OK.

---

## Implementation Paths

### Path A: "Fix It Now with /mnt/c"
```
1. Read: Quick Reference (5 min)
2. Add to ~/.bashrc: NUGET_PACKAGES, fixlsp alias
3. Update init.lua: Add correct path
4. Run: fixlsp
5. Test: Open C# file
Done! Accept 20-30s startup time
```

### Path B: "Optimize to /home" (RECOMMENDED)
```
1. Read: Config Recommendations Scenario 2 (10 min)
2. Run: mkdir -p ~/projects && cp -r /mnt/c/.../DCSRE ~/projects/
3. Update init.lua: Change path to ~/projects/DCSRE/Sources/Backend
4. Add ~/.bashrc: NUGET_PACKAGES, fixlsp alias
5. Test: Open C# file
Done! Enjoy 2-3s startup and no file locking!
```

### Path C: "Understand Everything"
```
1. Read: Summary (10 min) - get overview
2. Read: Quick Reference (5 min) - understand immediate needs
3. Read: Config Recommendations (15 min) - select scenario
4. Read: Research Document (45 min) - deep knowledge
5. Implement: Follow chosen scenario
Done! Expert-level understanding
```

---

## Key Facts (Memorize These)

| Fact | Source | Impact |
|------|--------|--------|
| /mnt/c is 10x slower than /home | Research.md § 1 | Choose /home for speed |
| NuGet caches are separate | Research.md § 2 | Must set NUGET_PACKAGES env var |
| Always use `dotnet OmniSharp.dll` not `.exe` | Research.md § 4 | Critical for WSL2 compatibility |
| Use exact Windows path casing | Research.md § 3 | Avoids case-sensitivity issues |
| Don't build in Windows and WSL2 simultaneously | Research.md § 4 | Prevents file lock conflicts |
| AnalyzeOpenDocumentsOnly can improve speed | Config Rec. § Various | Trade-off: speed vs thoroughness |

---

## Files at a Glance

```
WSL2 Research Documentation
├── WSL2_OMNISHARP_INDEX.md (THIS FILE)
│   └─ Navigation guide, document overview, FAQs
│
├── WSL2_OMNISHARP_QUICK_REFERENCE.md
│   └─ 1-2 page cheat sheet - symptoms, fixes, quick answers
│
├── WSL2_OMNISHARP_CONFIG_RECOMMENDATIONS.md
│   └─ 4 scenarios, step-by-step implementation, checklistsls
│
├── WSL2_OMNISHARP_RESEARCH.md
│   └─ 30+ pages, deep technical analysis, all details
│
└── WSL2_RESEARCH_SUMMARY.md
    └─ 4-5 pages, executive summary, key findings, overview
```

---

## Reading Recommendations

### For Developers (Want to Fix It Fast)
1. Quick Reference (5 min) - what's wrong?
2. Config Recommendations Scenario 2 (10 min) - how to fix?
3. Implement (30 min) - do it!
4. Quick Reference again for troubleshooting if needed

### For Technical Leads (Need to Understand)
1. Summary (10 min) - overview
2. Research.md (45 min) - deep dive
3. Config Recommendations (15 min) - implementation options
4. Summary again to decide on recommendation

### For Architects (Making Long-term Decisions)
1. Summary (10 min) - context
2. Research.md §1-4 (30 min) - key technical issues
3. Config Recommendations all scenarios (20 min) - options
4. Summary next steps section (5 min) - long-term plan

### For Troubleshooting (Something Broke)
1. Quick Reference → "Symptoms and Solutions" table (2 min)
2. Apply suggested fix (5-10 min)
3. If still broken, read Research.md § Troubleshooting (15 min)

---

## Quick Links by Topic

| Topic | See |
|-------|-----|
| **Performance** | Quick Ref § Performance Chart, Research.md § 1, § 8 |
| **NuGet Issues** | Quick Ref § Key Issues #2, Research.md § 2 |
| **Case Sensitivity** | Quick Ref § Key Issues #3, Research.md § 3 |
| **File Locking** | Quick Ref § Key Issues #4, Research.md § 4 |
| **Configuration** | Config Rec § Scenario 1-3, Research.md § 6 |
| **Troubleshooting** | Quick Ref § Symptoms Table, Research.md § 7, § 9 |
| **Symlinks** | Research.md § 5 |
| **Environment Setup** | Config Rec § All sections, Quick Ref § Environment Variables |
| **Next Steps** | Summary § Next Steps |

---

## Contact & Updates

**These documents are accurate as of**: 2025-11-13
**System tested on**: WSL2 Ubuntu 24.04 LTS, Neovim 0.11.4, .NET 9.0.306

**For updates if**:
- Neovim version changes significantly
- WSL2 releases major update
- OmniSharp behavior changes
- .NET version changes (especially .NET 10+)

Revisit Research.md and potentially update based on new findings.

---

## Success Criteria

You've successfully completed this research if you can:

- [ ] Answer: "Does OmniSharp work with /mnt/c?" (Yes, but 10x slower)
- [ ] Explain the 5 key issues (performance, NuGet, case sensitivity, locking, symlinks)
- [ ] Choose appropriate scenario (A/B/C) for your use case
- [ ] Implement and test your chosen scenario
- [ ] Fix issues using the troubleshooting guides
- [ ] Achieve OmniSharp startup time of either:
  - 20-30s with /mnt/c (acceptable)
  - 2-3s with /home (optimal)

---

## Document Statistics

| Document | Pages | Words | Time |
|----------|-------|-------|------|
| Quick Reference | 2 | ~2,000 | 5 min |
| Config Recommendations | 8 | ~8,000 | 15 min |
| Research (Full) | 30+ | ~15,000 | 45 min |
| Summary | 5 | ~3,000 | 10 min |
| Index (This file) | 4 | ~3,000 | 2 min |
| **Total** | **~48** | **~31,000** | **~77 min** |

**Modular reading**: Read what you need, not everything!

---

## Final Recommendation

### For Most Developers:
**Start here** → Config Recommendations Scenario 2 (Move to /home)
- 10x performance improvement
- No file locking issues
- No NuGet cache conflicts
- Simplest long-term solution

### If You're in a Hurry:
**Start here** → Quick Reference
- Get immediate answers
- Find copy-paste fixes
- Troubleshoot current issues

### If You Want Deep Knowledge:
**Start here** → Research.md
- Understand everything
- Make informed decisions
- Debug complex issues

---

**You are reading**: WSL2_OMNISHARP_INDEX.md (Navigation Guide)
**Next step**: Pick a document above and start reading!

🎯 **Recommendation**: Start with Quick Reference, then move to Config Recommendations, then read Research.md for full understanding.

---

*WSL2 + OmniSharp Research Project - Complete Documentation Set - 2025-11-13*
