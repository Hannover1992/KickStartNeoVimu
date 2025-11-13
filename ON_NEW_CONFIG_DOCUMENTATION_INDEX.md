# on_new_config Function - Documentation Index

**Created:** 2025-11-13
**Purpose:** Complete technical analysis of nvim-lspconfig omnisharp on_new_config behavior
**Total Pages:** 4 comprehensive documents
**Total Size:** 70 KB of detailed analysis

---

## Quick Navigation

### Start Here (5 min read)
→ **ON_NEW_CONFIG_SUMMARY.md**
- Direct answers to all 4 key questions
- Executive summary of on_new_config function
- Key insights and debugging checklist
- Perfect for quick reference

### Detailed Analysis (20 min read)
→ **ON_NEW_CONFIG_DEEP_DIVE.md**
- In-depth technical analysis of each question
- Complete function reference
- Detailed examples and code samples
- Verification commands
- Critical findings section

### Visual Reference (15 min read)
→ **ON_NEW_CONFIG_FLOW_DIAGRAM.txt**
- Flowcharts of all scenarios
- Step-by-step transformations
- ASCII diagrams showing data flow
- Config merge order
- Key takeaway flowchart

### Source Code Analysis (20 min read)
→ **ON_NEW_CONFIG_SOURCE_ANNOTATED.md**
- Line-by-line code annotations
- flatten() function explained with examples
- Complete execution flow example
- Key implementation details
- Critical insights section

---

## The 4 Key Questions Answered

### Q1: What happens if new_config.cmd is nil?
**File:** All documents
**Quick Answer:** ON_NEW_CONFIG_SUMMARY.md (section "Question 1")
**Detailed Answer:** ON_NEW_CONFIG_DEEP_DIVE.md (section "QUESTION 1")
**Visual Explanation:** ON_NEW_CONFIG_FLOW_DIAGRAM.txt (section "SCENARIO 3")
**Code Example:** ON_NEW_CONFIG_SOURCE_ANNOTATED.md (line 48 annotation)

**TL;DR:** Becomes empty array `{}`, hard-coded args added, no binary to execute → process fails

---

### Q2: Where does the "OmniSharp" wrapper cmd come from?
**File:** All documents
**Quick Answer:** ON_NEW_CONFIG_SUMMARY.md (section "Question 2")
**Detailed Answer:** ON_NEW_CONFIG_DEEP_DIVE.md (section "QUESTION 2")
**Visual Explanation:** ON_NEW_CONFIG_FLOW_DIAGRAM.txt (section "SCENARIO 2")
**Historical Context:** OMNISHARP_SETTINGS_FLOW_ANALYSIS.md (section "Version History")

**TL;DR:** From omnisharp.lua default_config: `cmd = { "OmniSharp" }`. Users are expected to override it.

---

### Q3: Does Mason inject a default cmd before on_new_config runs?
**File:** All documents
**Quick Answer:** ON_NEW_CONFIG_SUMMARY.md (section "Question 3")
**Detailed Answer:** ON_NEW_CONFIG_DEEP_DIVE.md (section "QUESTION 3")
**Comprehensive Research:** MASON_OMNISHARP_RESEARCH.md (sections "How Mason Installs", "Settings Propagation Flow")
**Visual Flow:** ON_NEW_CONFIG_FLOW_DIAGRAM.txt (section "SCENARIO 4")

**TL;DR:** NO. Mason only installs binary and adds to PATH. Configuration is entirely user's responsibility.

---

### Q4: How to ensure user cmd is used instead of default?
**File:** All documents
**Quick Answer:** ON_NEW_CONFIG_SUMMARY.md (section "Question 4")
**Detailed Answer:** ON_NEW_CONFIG_DEEP_DIVE.md (section "QUESTION 4")
**Code Examples:** ON_NEW_CONFIG_SOURCE_ANNOTATED.md (section "Complete Flow Example")
**Scope Analysis:** ON_NEW_CONFIG_DEEP_DIVE.md (section "CRITICAL FINDING")

**TL;DR:** Define cmd in servers table or explicit setup() while variable is in scope. Verify with `:LspInfo`.

---

## Document Summaries

### 1. ON_NEW_CONFIG_SUMMARY.md
**Read Time:** 5 minutes
**Best For:** Quick reference, understanding core concepts
**Contains:**
- Direct Q&A format
- Key insights bullets
- Complete flow schematic
- Debugging checklist
- Summary table

**Key Sections:**
- Direct Answers to Your Questions
- The Critical Issue from CLAUDE.md
- on_new_config Function: What It Does
- Key Insights
- Complete Flow (Schematic)
- Debugging Checklist
- Summary Table

---

### 2. ON_NEW_CONFIG_DEEP_DIVE.md
**Read Time:** 20 minutes
**Best For:** Deep technical understanding
**Contains:**
- Line-by-line explanation of each question
- Proof and verification examples
- Known good configuration patterns
- Debugging commands
- Scope problem analysis

**Key Sections:**
- QUESTION 1: What if new_config.cmd is nil?
  - Analysis with examples
  - Verification with Neovim
  - What this means practically

- QUESTION 2: Where does "OmniSharp" come from?
  - The Source: default_config
  - How Default Gets Loaded
  - The Merge Mechanism
  - Problem with Default

- QUESTION 3: Does Mason Inject Default cmd?
  - Short Answer: NO
  - Long Answer: Actual Flow
  - Mason's Role
  - Why Users See "OmniSharp"
  - Proof: Mason Doesn't Touch cmd

- QUESTION 4: How to Ensure User cmd Used?
  - Method 1: Explicit Define in servers
  - Method 2: Explicit Setup After mason-lspconfig
  - Method 3: Override at Setup Time
  - Verification: Check if Your cmd Used

- CRITICAL FINDING: The Real Problem
  - The Scope Problem
  - The Solution

- on_new_config Function: Complete Reference
  - Full Source Code
  - What Each Step Does
  - Execution Order

- Key Insights
- Debugging Checklist
- Summary

---

### 3. ON_NEW_CONFIG_FLOW_DIAGRAM.txt
**Read Time:** 15 minutes
**Best For:** Visual understanding of data flow
**Contains:**
- ASCII flowcharts
- Step-by-step state transformations
- Scenario comparisons
- Mason integration diagram
- Config merge order

**Key Sections:**
- SCENARIO 1: User Provides Custom cmd (CORRECT)
  - User Configuration box
  - Step-by-step transformation
  - Final result

- SCENARIO 2: User Doesn't Provide cmd (DEFAULT - WRONG)
  - Shows path to default config
  - Issues encountered

- SCENARIO 3: cmd is nil (WORST CASE)
  - Empty array creation
  - Process failure

- SCENARIO 4: Mason Installing OmniSharp
  - Mason's role
  - Installation results
  - What Mason does/doesn't do

- CONFIG MERGE ORDER
  - Priority levels
  - Decision tree

- CRITICAL ISSUE: SCOPE PROBLEM
  - Visual representation

- KEY TAKEAWAY FLOWCHART
  - Decision tree for debugging

---

### 4. ON_NEW_CONFIG_SOURCE_ANNOTATED.md
**Read Time:** 20 minutes
**Best For:** Understanding implementation details
**Contains:**
- Complete source code with annotations
- Line-by-line explanations
- flatten() function detailed
- Examples with transformations
- Critical implementation details

**Key Sections:**
- Complete Function with Line-by-Line Annotations (lines 46-78)
  - Parameter descriptions
  - Critical Line #1 analysis
  - Step-by-step breakdown
  - Examples for each step

- The flatten() Function
  - Source code with annotations
  - flatten() Examples
    - Example 1: Simple nested structure
    - Example 2: Multiple settings
    - Example 3: Multiple categories
    - Example 4: Deep nesting

- Complete Flow Example: Step by Step
  - Initial state
  - 10-step transformation
  - Final result
  - Actual command that executes

- Key Implementation Details
  - Why unpack(array or {})?
  - Why vim.list_extend?
  - Why vim.deepcopy?
  - Why flatten() is recursive?

- Summary Table
- Critical Insights
- Summary of on_new_config Behavior

---

## How to Use These Documents

### Scenario 1: "My OmniSharp settings aren't working"
1. Start: ON_NEW_CONFIG_SUMMARY.md
2. Check `:LspInfo` - what does cmd show?
3. If cmd wrong: Read Question 2 & 4 (DEEP_DIVE.md)
4. Read SCENARIO 2 (FLOW_DIAGRAM.txt)
5. Apply solution and verify

### Scenario 2: "I need to understand on_new_config behavior"
1. Start: ON_NEW_CONFIG_SUMMARY.md (key insights)
2. Read: ON_NEW_CONFIG_DEEP_DIVE.md (complete reference)
3. Visual: ON_NEW_CONFIG_FLOW_DIAGRAM.txt (see the flow)
4. Code: ON_NEW_CONFIG_SOURCE_ANNOTATED.md (understand implementation)

### Scenario 3: "Configuration out of scope - what should I do?"
1. Read: ON_NEW_CONFIG_DEEP_DIVE.md → "CRITICAL FINDING"
2. See: ON_NEW_CONFIG_FLOW_DIAGRAM.txt → "CRITICAL ISSUE"
3. Apply: ON_NEW_CONFIG_SUMMARY.md → "Method 1" or "Method 2"
4. Verify: Debug checklist

### Scenario 4: "Mason installed OmniSharp but LSP not working"
1. Read: ON_NEW_CONFIG_SUMMARY.md → "Question 3"
2. Read: MASON_OMNISHARP_RESEARCH.md (comprehensive)
3. Check: FLOW_DIAGRAM.txt → "SCENARIO 4"
4. Verify: Installation checklist in MASON_OMNISHARP_RESEARCH.md

### Scenario 5: "What does flatten() actually do?"
1. Read: ON_NEW_CONFIG_SOURCE_ANNOTATED.md → "flatten() Function"
2. Study: flatten() Examples (4 detailed examples)
3. Understand: Key implementation details section

---

## Cross-References

### Related Documents Already in Repository
- **OMNISHARP_SETTINGS_FLOW_ANALYSIS.md** - Settings flattening mechanism
- **OMNISHARP_CMD_PARAMETER_ANALYSIS.md** - cmd parameter handling
- **MASON_OMNISHARP_RESEARCH.md** - Mason installation process
- **CLAUDE.md** - Original project documentation with issues

### Connection Map
```
ON_NEW_CONFIG documents (NEW)
    ↓
Explains behavior of on_new_config function
    ↓
References and builds on:
    - OMNISHARP_SETTINGS_FLOW_ANALYSIS.md (flatten mechanism)
    - OMNISHARP_CMD_PARAMETER_ANALYSIS.md (cmd flow)
    - MASON_OMNISHARP_RESEARCH.md (Mason's role)
    ↓
Solves issues from:
    - CLAUDE.md (configuration problems)
```

---

## Key Takeaways

### The Core Function Behavior
```lua
on_new_config = function(new_config, _)
  -- 1. Copy cmd (ensure it's array)
  -- 2. Append hard-coded LSP args ("-z", "--hostPID", etc.)
  -- 3. Flatten and append settings
  -- 4. Disable unsupported capabilities
  -- Result: Modified cmd ready for execution
end
```

### The 3 Critical Points
1. **User cmd is preserved and EXTENDED** - not replaced
2. **Hard-coded args are ALWAYS added** - can't be disabled
3. **Settings must be properly nested** - flat structure doesn't work

### The 2 Common Mistakes
1. Not providing custom cmd → defaults to unreliable `{ "OmniSharp" }`
2. Defining servers.omnisharp outside of scope → variable not accessible

### The 1 Golden Rule
**Always explicitly define cmd with full path to binary and ensure the variable is in scope when setup() is called.**

---

## Verification Commands

### Check Your Current Configuration
```vim
" In Neovim after opening C# file:
:LspInfo
" Look at cmd line - should show YOUR custom cmd with full path
```

### Verify Command Being Executed
```bash
# Terminal: See actual process command
ps aux | grep omnisharp | grep -v grep
```

### Check Settings Structure
```vim
" In Neovim:
:lua print(vim.inspect(require('lspconfig').omnisharp._cmd))
" Should show all hard-coded args + your settings flattened
```

---

## File Statistics

| Document | Size | Read Time | Focus |
|----------|------|-----------|-------|
| ON_NEW_CONFIG_SUMMARY.md | 15 KB | 5 min | Quick reference |
| ON_NEW_CONFIG_DEEP_DIVE.md | 17 KB | 20 min | Deep analysis |
| ON_NEW_CONFIG_FLOW_DIAGRAM.txt | 20 KB | 15 min | Visual flow |
| ON_NEW_CONFIG_SOURCE_ANNOTATED.md | 18 KB | 20 min | Code details |
| **TOTAL** | **70 KB** | **60 min** | Complete knowledge |

---

## Reading Recommendations

### Path 1: "Give me the quick answer" (5 min)
→ ON_NEW_CONFIG_SUMMARY.md

### Path 2: "I need to fix my config" (25 min)
→ ON_NEW_CONFIG_SUMMARY.md
→ ON_NEW_CONFIG_DEEP_DIVE.md (Q4 section)
→ ON_NEW_CONFIG_FLOW_DIAGRAM.txt (SCENARIO 1)

### Path 3: "I want to understand everything" (60 min)
→ ON_NEW_CONFIG_SUMMARY.md
→ ON_NEW_CONFIG_DEEP_DIVE.md
→ ON_NEW_CONFIG_FLOW_DIAGRAM.txt
→ ON_NEW_CONFIG_SOURCE_ANNOTATED.md

### Path 4: "I'm debugging a specific issue" (varies)
- **Settings not working?** → Q2, Q4 sections in DEEP_DIVE.md
- **Scope problems?** → CRITICAL FINDING in DEEP_DIVE.md
- **Need visual flow?** → FLOW_DIAGRAM.txt scenarios
- **Understanding flatten?** → SOURCE_ANNOTATED.md flatten section

---

## Version Info

**Analysis Date:** 2025-11-13
**Source:** nvim-lspconfig omnisharp.lua (lines 1-78)
**Neovim Version:** Compatible with all recent versions
**OmniSharp Version:** v1.39.x and later (Roslyn)
**Status:** Complete and verified ✅

---

## Next Steps

1. **Review:** Start with ON_NEW_CONFIG_SUMMARY.md
2. **Understand:** Read relevant sections in DEEP_DIVE.md
3. **Apply:** Update your init.lua with correct cmd configuration
4. **Verify:** Run `:LspInfo` to check cmd field
5. **Test:** Open a C# file and verify OmniSharp attaches
6. **Debug:** Use verification commands if needed

---

**Last Updated:** 2025-11-13
**Status:** Complete and ready for use
**Questions?** Refer to the appropriate section in the documents above

