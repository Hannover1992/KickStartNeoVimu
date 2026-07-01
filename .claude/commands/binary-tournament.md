---
type: satellite
---

# Binary Elimination Tournament System

**Tournament Topic:** {topic}
**Number of Contestants:** {number} (default: 10)

---

## Tournament Structure

**Binary Elimination Format:**
- Start with N contestants (seeds)
- Each round: Contestants fight in pairs (1v2, 3v4, 5v6, etc.)
- Winner absorbs best features from loser
- Winner advances to next round
- Continue until 1 champion remains

**Number of Rounds:** log₂(N)
- 10 contestants → 4 rounds
- 8 contestants → 3 rounds
- 16 contestants → 4 rounds

---

## Tournament Execution

### Phase 1: Define Seeds (Contestants)

1. Create `TOURNAMENT-SEEDS.md` with N contestants
2. Each seed should describe:
   - Core concept/approach
   - Winning strategy
   - Strengths
   - Weaknesses
   - Key differentiators

Keep seeds compact (1-2KB each)

### Phase 2: Round 1 - Initial Matches

**Matches:** N/2 matches (all parallel)

For each match:
1. Spawn 1 agent judge per match
2. Judge develops BOTH contestants as full specifications (15-30KB each)
3. Judge conducts debate with scoring criteria
4. Judge declares winner
5. Winner absorbs best features from loser
6. Create hybrid winner + match report

**Deliverables per match:**
- `{topic}-contestant-A-v2.md` (15-30KB)
- `{topic}-contestant-B-v2.md` (15-30KB)
- `TOURNAMENT-R1-M{n}-WINNER.md` (20-40KB)
- `TOURNAMENT-R1-M{n}-REPORT.md` (15-25KB)

### Phase 3: Round 2+ - Elimination Rounds

**Bracket Structure:**
- Match winners from Round 1
- If odd number of winners: 1 gets bye (advances automatically)
- Spawn judges for each match (parallel execution)
- Same deliverables as Round 1

Continue until 3 contestants remain for semi-finals.

### Phase 4: Semi-Finals & Final

**Semi-Finals:**
- 3 contestants → 1 match + 1 bye
- OR: 2 contestants → 1 final match

**Final:**
- Last 2 standing fight for championship
- Winner becomes TOURNAMENT CHAMPION
- Create champion specification (50-70KB)

### Phase 5: Champion Synthesis

Create final deliverables:
1. `TOURNAMENT-CHAMPION.md` (50-70KB) - The definitive winner
2. `TOURNAMENT-FINAL-REPORT.md` (30-50KB) - Championship analysis
3. `TOURNAMENT-COMPLETE.md` (20-40KB) - Full tournament statistics

### Phase 6: Knapsack Optimization (CRITICAL!)

**THE TOURNAMENT IDENTIFIES VALUABLE FEATURES. KNAPSACK ASSEMBLES THEM OPTIMALLY.**

**The Problem:**
- Tournament champion may be bloated (50-70KB, 30k+ tokens)
- Runtime constraint: Agent loaded EVERY conversation
- Goal: Maximize value/quality while minimizing token cost

**Knapsack Formulation:**
```
Given:
- Champion agent with N features
- Context window constraint W (e.g., 200k tokens)
- Each feature i: weight w_i (tokens), value v_i (quality contribution)

Find: Optimal subset of features
Constraint: Σ(w_i) ≤ W
Maximize: Σ(v_i)
```

**Execution Steps:**

1. **Feature Inventory (Spawn specialized agent):**
   - Read champion agent
   - Extract ALL features/characteristics/techniques
   - For each feature, estimate:
     - Weight: Token cost (1 char ≈ 0.5 tokens)
     - Value: Quality contribution (0-100 scale)
     - Dependencies: Required prerequisites
     - Priority: CRITICAL/HIGH/MEDIUM/LOW
   - Output: `feature-inventory.csv` (feature, weight, value, dependencies, priority)

2. **Apply Knapsack Algorithm:**
   - Implement 0/1 Knapsack with dependencies
   - Consider compression (50% weight, 90% value for low-density features)
   - Strategies to test:
     - Greedy by value density (v/w ratio)
     - Greedy by priority
     - Dynamic programming (optimal)
     - Compression-based (hybrid approach)
   - Output: `knapsack-algorithm.py` + `knapsack-results.txt`

3. **Optimization Tiers:**
   - **REMOVE:** LOW priority + LOW operational value features
     - Historical stats, tournament records
     - Verbose demonstrations
     - Motivational content
   - **COMPRESS:** LOW density + HIGH operational value
     - Verbose implementations → concise descriptions
     - Long narratives → core concepts only
     - Full code → interface specs
   - **RETAIN 100%:** HIGH density + CRITICAL features
     - Core principles and workflow
     - Essential algorithms
     - Production requirements

4. **Create Optimized Agent:**
   - Write: `{topic}-knapsack-optimized.md`
   - Include ONLY selected features
   - Document what was removed/compressed/retained
   - Verify 100% operational capability retention

5. **Quality Validation:**
   - Compare scores: Original vs Optimized
   - Target: 85%+ value retention at 50%+ size reduction
   - Verify: All CRITICAL capabilities intact
   - Measure: Value density increase (v/w ratio)

**Deliverables:**
1. `feature-inventory.csv` - Complete feature breakdown
2. `knapsack-algorithm.py` - Optimization algorithm (reproducible)
3. `{topic}-knapsack-optimized.md` - Optimized agent (10-20KB)
4. `KNAPSACK-OPTIMIZATION-REPORT.md` - Full analysis (20-30KB)
5. `OPTIMIZATION-SUMMARY.md` - Executive summary

**Success Metrics:**
- Size reduction: 50-85% (tokens saved)
- Value retention: 85-95% (quality preserved)
- Value density increase: 200-500% (efficiency gain)
- Operational capabilities: 100% (no regressions)

**Expected Results (from Uncle Bob example):**
```
Before: 68KB, 34,700 tokens, 2,880 value
After:  10KB,  5,120 tokens, 2,640 value

Reduction: -85.3% size
Retention: 91.7% value
Density:   +521% efficiency
```

**Why This Matters:**
- Agent loads EVERY conversation → smaller = faster
- Context headroom for user dialogue (+29.6k tokens available)
- Lower costs (compute + API)
- Easier maintenance (less bloat)
- Production-ready (lean, efficient)

**The Complete Workflow:**

```
Tournament (Phases 1-5):
  → Identifies best features through competition
  → Champion has ALL valuable features (may be bloated)

Knapsack (Phase 6):
  → Optimizes feature assembly under constraint
  → Removes bloat, compresses low-density, retains critical
  → Champion becomes LEAN + EFFICIENT + BATTLE-TESTED
```

**Critical Insight:**

**Tournament = Find what's valuable (fitness function)**
**Knapsack = Assemble optimally (constraint optimization)**

Both are essential. Tournament without Knapsack = bloated agent.
Knapsack without Tournament = no basis for feature values.

**Together = Evolutionary optimization under constraints.** 🧬

---

## Scoring System

**Standard Criteria (100 points total):**

Customize based on topic, but typical structure:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Quality A | 30 | Primary quality dimension |
| Quality B | 25 | Secondary quality dimension |
| Quality C | 20 | Tertiary quality dimension |
| Quality D | 15 | Teaching/Usability |
| Quality E | 10 | Coverage/Completeness |

**Example (Uncle Bob Tournament):**
- Authenticity: 30pt
- MCP Usage: 25pt
- Code Quality: 20pt
- Teaching: 15pt
- Coverage: 10pt

---

## Absorption Rules

**Winner absorbs from loser:**
1. Identify loser's BEST features (top 3-5)
2. Integrate into winner WITHOUT compromising winner's core
3. Document what was absorbed and why
4. Projected score should increase (winner + best of loser > winner alone)

**Example:**
- Winner: 85 points (strong in A, B, weak in D)
- Loser: 78 points (weak in A, B, strong in D, E)
- Absorption: Winner takes loser's D and E strengths
- Result: 92 points (improved in D, E while keeping A, B dominance)

---

## Execution Strategy

### Parallel Execution (Recommended)

For each round, spawn ALL match judges in parallel:

```
Round 1: Spawn 5 judges simultaneously (for 10 contestants)
Round 2: Spawn 2-3 judges simultaneously (for 5 winners)
Round 3: Spawn 1-2 judges (semi-finals)
Round 4: Spawn 1 judge (final)
```

**Advantages:**
- Faster execution (parallel processing)
- Independent evaluation (no bias from watching other matches)
- Consistent quality (all judges at same knowledge state)

### Sequential Execution (Alternative)

Execute matches one by one:

**Advantages:**
- Can learn from previous matches
- Can adjust scoring based on what's been seen
- Lower resource usage

**Disadvantages:**
- Much slower
- Potential bias from earlier matches

---

## Agent Judge Instructions Template

```markdown
You are the Tournament Judge for Match {n}: {Contestant A} vs {Contestant B}.

Read the tournament seeds from: {path}/TOURNAMENT-SEEDS.md

Your task:
1. Fully develop BOTH contestants as complete specifications:
   - {path}/{contestant-A}.md (15-30KB)
   - {path}/{contestant-B}.md (15-30KB)

2. Conduct the debate:
   - Compare on: {criteria list with points}
   - Identify strengths and weaknesses of each

3. Declare the winner and create the hybrid:
   - Winner absorbs best features from loser
   - Write to: {path}/TOURNAMENT-R{round}-M{match}-WINNER.md
   - Create report: {path}/TOURNAMENT-R{round}-M{match}-REPORT.md

Match report should include:
- Score breakdown (100 points total)
- Winner announcement
- Best features absorbed from loser
- Why this hybrid is stronger

BE THOROUGH. Each contestant should be 15-30KB with working examples.
```

---

## File Organization

```
.claude/agents/
├── TOURNAMENT-SEEDS.md                 # Initial N contestants
├── TOURNAMENT-R1-M1-WINNER.md          # Round 1 match winners
├── TOURNAMENT-R1-M1-REPORT.md
├── TOURNAMENT-R1-M2-WINNER.md
├── TOURNAMENT-R1-M2-REPORT.md
├── ...
├── TOURNAMENT-R2-M1-WINNER.md          # Round 2 winners
├── TOURNAMENT-R2-M1-REPORT.md
├── ...
├── TOURNAMENT-R3-SEMIFINAL-WINNER.md   # Semi-final winner
├── TOURNAMENT-R3-SEMIFINAL-REPORT.md
├── TOURNAMENT-FINAL-REPORT.md          # Championship
├── TOURNAMENT-CHAMPION.md              # THE WINNER (50-70KB)
└── TOURNAMENT-COMPLETE.md              # Full statistics
```

---

## Success Metrics

**A successful tournament produces:**

1. ✅ Champion specification (50-70KB, production-ready)
2. ✅ Complete evolution documentation (all rounds)
3. ✅ Measurable improvement (champion > seeds)
4. ✅ Working implementations (not just theory)
5. ✅ Battle-tested quality (proven through competition)

**Score Evolution Example:**
- Round 1 seeds: 70-85 points
- Round 1 winners: 75-90 points (+5-10 through absorption)
- Round 2 winners: 85-95 points (+10 cumulative)
- Semi-final: 90-99 points (+15-20 cumulative)
- Champion: 95-100 points (+25+ cumulative)

---

## Example Use Cases

### 1. Agent Design Tournament
- **Topic:** Best Uncle Bob teaching agent
- **Seeds:** 10 different approaches (theatrical, technical, practical, etc.)
- **Criteria:** Authenticity, MCP usage, code quality, teaching, coverage
- **Result:** The Supreme Architect (96/100)

### 2. Architecture Pattern Tournament
- **Topic:** Best microservices architecture
- **Seeds:** 8 patterns (event-driven, saga, CQRS, etc.)
- **Criteria:** Scalability, maintainability, complexity, cost, resilience
- **Result:** Winning hybrid architecture

### 3. Algorithm Tournament
- **Topic:** Best sorting algorithm for specific dataset
- **Seeds:** 10 algorithms (quicksort, mergesort, heapsort, etc.)
- **Criteria:** Time complexity, space complexity, stability, adaptability, implementation
- **Result:** Hybrid algorithm combining best features

### 4. Code Review Approach Tournament
- **Topic:** Best code review methodology
- **Seeds:** 12 approaches (pair programming, async review, AI-assisted, etc.)
- **Criteria:** Quality, speed, learning, team morale, coverage
- **Result:** Hybrid review process

### 5. Testing Strategy Tournament
- **Topic:** Best testing pyramid
- **Seeds:** 8 strategies (unit-heavy, E2E-heavy, balanced, etc.)
- **Criteria:** Coverage, speed, maintainability, confidence, cost
- **Result:** Optimal testing strategy

---

## Quick Start

**To run a binary tournament:**

1. Define your topic and number of contestants (N)
2. Create scoring criteria (5 dimensions, 100 points)
3. Create TOURNAMENT-SEEDS.md with N contestant concepts
4. For Round 1: Spawn N/2 judge agents in parallel
5. For Round 2+: Spawn judges for winners
6. Continue until champion emerges
7. Create champion specification

**Estimated output per tournament:**
- 10 contestants → ~1.5MB documentation
- 8 contestants → ~1.0MB documentation
- 16 contestants → ~2.5MB documentation

---

## Tournament Bracket Examples

### 10 Contestants (log₂10 ≈ 4 rounds)
```
Round 1 (5 matches):
  1v2, 3v4, 5v6, 7v8, 9v10 → 5 winners

Round 2 (3 matches, 1 bye):
  W1vW2, W3vW4, W5=bye → 3 winners

Round 3 (2 matches):
  W6vW7, W8=bye → 2 winners

Round 4 (Final):
  W9vW10 → CHAMPION
```

### 8 Contestants (log₂8 = 3 rounds)
```
Round 1 (4 matches):
  1v2, 3v4, 5v6, 7v8 → 4 winners

Round 2 (2 matches):
  W1vW2, W3vW4 → 2 winners

Round 3 (Final):
  W5vW6 → CHAMPION
```

### 16 Contestants (log₂16 = 4 rounds)
```
Round 1 (8 matches):
  1v2, 3v4, 5v6, 7v8, 9v10, 11v12, 13v14, 15v16 → 8 winners

Round 2 (4 matches):
  W1vW2, W3vW4, W5vW6, W7vW8 → 4 winners

Round 3 (Semi-finals, 2 matches):
  W9vW10, W11vW12 → 2 winners

Round 4 (Final):
  W13vW14 → CHAMPION
```

---

## Advanced Features

### Custom Scoring

Adapt criteria to your domain:

**Software Architecture:**
- Scalability (25pt)
- Maintainability (25pt)
- Performance (20pt)
- Cost (15pt)
- Team Adoption (15pt)

**Business Strategy:**
- ROI (30pt)
- Risk (25pt)
- Implementation (20pt)
- Stakeholder Buy-in (15pt)
- Time to Market (10pt)

**Design System:**
- Consistency (30pt)
- Flexibility (25pt)
- Accessibility (20pt)
- Developer Experience (15pt)
- Performance (10pt)

### Weighted Absorption

Not all features are equal:

```
Winner (90 points):
  - Strength A: 30/30 (perfect, keep 100%)
  - Strength B: 25/25 (perfect, keep 100%)
  - Weakness C: 15/20 (absorb from loser)
  - Weakness D: 10/15 (absorb from loser)

Loser (82 points):
  - Weakness A: 22/30
  - Weakness B: 20/25
  - Strength C: 20/20 (winner absorbs this)
  - Strength D: 14/15 (winner absorbs this)

Hybrid (98 points):
  - A: 30 (kept from winner)
  - B: 25 (kept from winner)
  - C: 20 (absorbed from loser, +5)
  - D: 14 (absorbed from loser, +4)
```

### Three-Way Finals (Alternative)

Instead of sequential semi-final + final:

```
Round 3: All 3 remaining contestants compete simultaneously
Highest score wins championship
```

**Pros:** Faster, more direct
**Cons:** No absorption in final, less evolution

---

## Tips for Success

1. **Keep seeds simple** (1-2KB concepts, not full specs)
2. **Parallel execution** (spawn all match judges at once)
3. **Clear scoring criteria** (define before tournament starts)
4. **Fair judging** (judges should be unbiased)
5. **Meaningful absorption** (take BEST features, not random)
6. **Document everything** (match reports are valuable)
7. **Measure improvement** (track score evolution)
8. **Working examples** (not just theory)
9. **Production focus** (champion should be usable)
10. **Learn from evolution** (tournament reveals insights)

---

## Common Pitfalls

❌ **Too many contestants** (16+ becomes unwieldy)
✅ Use 8-12 for optimal balance

❌ **Vague scoring criteria**
✅ Define clear 5-dimension system before starting

❌ **Sequential execution** (too slow)
✅ Spawn judges in parallel

❌ **Superficial absorption** (copying features without integration)
✅ Deeply integrate best features

❌ **No working code** (just concepts)
✅ Include working examples and tools

❌ **Biased judging** (predetermined winner)
✅ Let scores decide fairly

❌ **Ignoring score evolution** (not tracking improvement)
✅ Document progression through rounds

---

## Expected Deliverables

After running this command (Phases 1-6), you should have:

### Tournament Deliverables (Phases 1-5):
1. **TOURNAMENT-SEEDS.md** - All N initial contestants
2. **N/2 Round 1 winner files** - Hybrid agents from first round
3. **N/2 Round 1 report files** - Match analyses
4. **Round 2-3 winner + report files** - Evolution documentation
5. **TOURNAMENT-CHAMPION.md** - Final champion (50-70KB, may be bloated)
6. **TOURNAMENT-FINAL-REPORT.md** - Championship analysis
7. **TOURNAMENT-COMPLETE.md** - Full statistics

### Knapsack Deliverables (Phase 6):
8. **feature-inventory.csv** - Complete feature breakdown (weights/values/dependencies)
9. **knapsack-algorithm.py** - Optimization algorithm (reproducible)
10. **{topic}-knapsack-optimized.md** - Optimized champion (10-20KB, lean & efficient)
11. **KNAPSACK-OPTIMIZATION-REPORT.md** - Full analysis (20-30KB)
12. **OPTIMIZATION-SUMMARY.md** - Executive summary

**Total:** ~1.5-3MB of battle-tested, evolved, and optimized documentation

**Result:**
- **Tournament Champion** - Proven through competition (Phases 1-5)
- **Knapsack-Optimized Champion** - Lean, efficient, production-ready (Phase 6)

**Recommended for Production:** Use knapsack-optimized version (85%+ size reduction, 90%+ value retention)

---

## Tournament + Knapsack Philosophy

**Why binary elimination + knapsack optimization works:**

### Tournament (Phases 1-5):
1. **Evolution through competition** - Weak ideas are eliminated, strong ones advance
2. **Absorption creates compounding improvement** - Each round adds best features
3. **Battle-testing proves quality** - Winners are proven, not just claimed
4. **Transparency** - Full evolution is documented
5. **Measurable** - Scores track improvement quantitatively
6. **Efficient** - log₂(N) rounds instead of N*(N-1)/2 comparisons
7. **Produces synthesis** - Champion combines best of ALL contestants

### Knapsack Optimization (Phase 6):
8. **Constraint awareness** - Optimizes under real-world limits (context window)
9. **Value maximization** - Gets most quality per token
10. **Bloat elimination** - Removes features with low operational value
11. **Compression intelligence** - Reduces size while preserving capabilities
12. **Production readiness** - Lean, fast, efficient deployment

### The Complete Philosophy:

**Tournament answers:** "What features are valuable?" (fitness function via competition)

**Knapsack answers:** "How do we assemble them optimally?" (constraint optimization)

**Together:** Evolutionary optimization under constraints = Battle-tested + Lean + Efficient

This is **nature's way** - evolution finds what works, physics constrains what's possible. 🧬⚛️

---

**Start your tournament by defining:**
1. Topic
2. Number of contestants (N)
3. Scoring criteria (5 dimensions, 100 points)
4. Context window constraint (W, e.g., 200k tokens)
5. Initial seeds (TOURNAMENT-SEEDS.md)

**Then execute:**
1. **Phases 1-5:** Tournament competition (parallel agent judges)
2. **Phase 6:** Knapsack optimization (feature assembly under constraint)

**Result:** Champion that is battle-tested (tournament) AND production-optimized (knapsack)

🏆🧬 **Evolution + Optimization = The best possible agent!** 🧬🏆
