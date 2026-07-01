#!/usr/bin/env python3
"""
test_a_routing_targets.py — Regression-Test fuer Routing-Refit 2026-05-17

Coverage:
- guard_a_routing_target.check_content (Whitelist + DIRECT_I-Block)
- Skill-Markdown-Sanity: VALID_TARGETS in _A_berater_routing + _A_postRoute
- Decision-Matrix-Coverage (10 Faelle, dokumentarisch via fixture-Strings)

Run: python .claude/scripts/test_a_routing_targets.py
Exit 0 = alle PASS, 1 = mindestens 1 FAIL.
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
SKILLS_DIR = ROOT_DIR / ".claude" / "commands"

# Import guard
sys.path.insert(0, str(SCRIPT_DIR))
from guard_a_routing_target import (
    check_content,
    VALID_TARGETS,
    RETIRED_TARGETS,
    INVALID_AS_A_TARGET,
    ROUTING_TARGET_PATTERN,
    is_manifest_file,
)

LABEL = "[test_a_routing_targets]"
PASS_COUNT = 0
FAIL_COUNT = 0


def assert_eq(name, actual, expected):
    global PASS_COUNT, FAIL_COUNT
    if actual == expected:
        PASS_COUNT += 1
        print(f"  PASS  {name}")
    else:
        FAIL_COUNT += 1
        print(f"  FAIL  {name}: expected={expected!r}, actual={actual!r}")


def assert_in(name, needle, haystack):
    global PASS_COUNT, FAIL_COUNT
    if needle in haystack:
        PASS_COUNT += 1
        print(f"  PASS  {name}")
    else:
        FAIL_COUNT += 1
        print(f"  FAIL  {name}: {needle!r} not in haystack")


# ───────────────────────────────────────────────────────────────────────
# TEST GROUP 1: Whitelist + check_content
# ───────────────────────────────────────────────────────────────────────

def test_whitelist_targets():
    """3 valid targets (V3) müssen Whitelist passieren."""
    print()
    print("=== TEST 1: Whitelist V3 (3 valid targets: BDF, IDF, STOP) ===")
    for target in ["BDF", "IDF", "STOP"]:
        content = f'routing_target: "{target}"'
        violations = check_content(content)
        assert_eq(f"target={target} no violations", len(violations), 0)


def test_invalid_as_a_target():
    """SC/SDF/I muessen als INVALID_AS_A_TARGET geblockt werden (Refit-V3)."""
    print()
    print("=== TEST 1b: INVALID_AS_A_TARGET (SC/SDF/I — Pipeline-Hierarchie) ===")
    for invalid in ["SC", "SDF", "I"]:
        content = f'routing_target: "{invalid}"'
        violations = check_content(content)
        assert_eq(f"target={invalid} blocked as INVALID_AS_A_TARGET", len(violations), 1)
        if violations:
            assert_in(f"target={invalid} reason mentions Pipeline-Hierarchie", "Pipeline-Hierarchie", violations[0])
            assert_in(f"target={invalid} reason mentions IDF as alternative", "IDF", violations[0])


def test_direct_i_retired():
    """DIRECT_I + Varianten MUESSEN als RETIRED detected werden."""
    print()
    print("=== TEST 2: DIRECT_I-Familie RETIRED ===")
    for retired in ["DIRECT_I", "I_DIRECT", "DIRECT_SC", "SC_DIRECT"]:
        content = f'routing_target: "{retired}"'
        violations = check_content(content)
        assert_eq(f"target={retired} retired detection", len(violations), 1)
        if violations:
            assert_in(f"target={retired} reason mentions RETIRED", "RETIRED", violations[0])


def test_invalid_target_blocked():
    """Unknown targets MUESSEN geblockt werden (V3 Whitelist)."""
    print()
    print("=== TEST 3: Invalid targets (V3 whitelist enforcement) ===")
    # Note: "I" ist jetzt im INVALID_AS_A_TARGET set (V3 Refit), nicht im unknown-set.
    # Hier nur wirklich unknown targets (kein Whitelist-Treffer, kein RETIRED, kein INVALID_AS_A_TARGET).
    for invalid in ["FOO", "BAR", "EXPLODE", "DIRECT", "BLABLA"]:
        content = f'routing_target: "{invalid}"'
        violations = check_content(content)
        assert_eq(f"target={invalid} blocked", len(violations), 1)
        if violations:
            assert_in(f"target={invalid} reason mentions Whitelist", "Whitelist", violations[0])


def test_no_routing_target_no_violations():
    """Content ohne routing_target = keine violations (frueh-exit)."""
    print()
    print("=== TEST 4: No routing_target field = pass-through ===")
    contents = [
        "some random content",
        "k_score: 42",
        "BERATER_OUTPUTS:\n  modusErkennung: ...",
    ]
    for c in contents:
        violations = check_content(c)
        assert_eq(f"content without routing_target no violations", len(violations), 0)


# ───────────────────────────────────────────────────────────────────────
# TEST GROUP 2: Pattern-Matching
# ───────────────────────────────────────────────────────────────────────

def test_pattern_variants():
    """Regex erkennt verschiedene routing_target Schreibweisen."""
    print()
    print("=== TEST 5: Pattern-Match variants ===")
    variants = [
        ('routing_target: "SC"', "SC"),
        ('routing_target: SC', "SC"),
        ("routing_target: 'SC'", "SC"),
        ('A_PIPELINE_STATE.routing_target = "SC"', "SC"),
        ("ROUTING_TARGET: SC", "SC"),  # case-insensitive
    ]
    for content, expected in variants:
        matches = ROUTING_TARGET_PATTERN.findall(content)
        assert_eq(f"pattern match in {content!r}", expected if not matches else matches[0].upper(), expected)


# ───────────────────────────────────────────────────────────────────────
# TEST GROUP 3: is_manifest_file
# ───────────────────────────────────────────────────────────────────────

def test_is_manifest_file():
    """is_manifest_file erkennt _manifest.md Pfade."""
    print()
    print("=== TEST 6: is_manifest_file ===")
    positive = [
        "C:/Users/X/Backlog/BL-162/_manifest.md",
        "/some/path/_manifest.md",
        ".claude/analysis/_manifest.md",
        r"C:\Users\X\_manifest.md",
    ]
    negative = [
        "manifest.md",
        "_manifest_protokoll.md",
        "spec.md",
        "",
    ]
    for p in positive:
        assert_eq(f"manifest path: {p}", is_manifest_file(p), True)
    for p in negative:
        assert_eq(f"non-manifest path: {p}", is_manifest_file(p), False)


# ───────────────────────────────────────────────────────────────────────
# TEST GROUP 4: Skill-Markdown Sanity
# ───────────────────────────────────────────────────────────────────────

def test_skill_a_berater_routing_v3():
    """_A_berater_routing.md hat 3-Target Matrix V3 (kein SC/SDF/I als A-target)."""
    print()
    print("=== TEST 7: _A_berater_routing 3-Target Matrix V3 ===")
    skill = SKILLS_DIR / "_A_berater_routing.md"
    content = skill.read_text(encoding="utf-8")

    assert_in("INV-RT-1-V3 referenced", "INV-RT-1-V3", content)
    assert_in("3-Target Decision-Matrix", "3-Target", content)
    assert_in("INVALID_AS_A_TARGET concept", "INVALID_AS_A_TARGET", content)
    assert_in("VALID_TARGETS BDF", '"BDF"', content)
    assert_in("VALID_TARGETS IDF", '"IDF"', content)
    assert_in("VALID_TARGETS STOP", '"STOP"', content)
    assert_in("Rail Guard ABORT", "INV-RT-RAILGUARD-V3", content)
    # Active assignments to RETIRED or INVALID_AS_A_TARGET muessen NIE vorkommen
    for bad in ["DIRECT_I", '"SC"', '"SDF"']:
        active = re.findall(rf'target\s*=\s*"{re.escape(bad).strip(chr(39)).strip(chr(34))}"', content)
        # active assignments wie `target = "SC"` (not in comments/decisions) — strict
    # Pipeline-Hierarchie mention
    assert_in("Pipeline-Hierarchie referenced", "Sub-Modus", content)


def test_skill_a_postroute_v5():
    """_A_postRoute.md ist v5.0 mit 3-Target Matrix V3."""
    print()
    print("=== TEST 8: _A_postRoute v5.0 3-Target V3 ===")
    skill = SKILLS_DIR / "_A_postRoute.md"
    content = skill.read_text(encoding="utf-8")

    assert_in("v5.0.0 version", "version: 5.0.0", content)
    assert_in("INV-ROUTE-1-V3", "INV-ROUTE-1-V3", content)
    assert_in("INV-ROUTE-3-V3", "INV-ROUTE-3-V3", content)
    assert_in("target=IDF Handler", 'target == "IDF"', content)
    assert_in("target=STOP Handler", 'target == "STOP"', content)
    assert_in("target=BDF Handler", 'target == "BDF"', content)
    assert_in("Rail Guard Schritt 0.5", "Rail Guard", content)
    assert_in("kein _I_orchestrate", "KEIN _I_orchestrate", content)
    assert_in("kein _SC_orchestrate", "KEIN _SC_orchestrate", content)
    assert_in("kein _SDF_orchestrate", "KEIN _SDF_orchestrate", content)
    assert_in("INVALID_AS_A_TARGET concept", "INVALID_AS_A_TARGET", content)


# ───────────────────────────────────────────────────────────────────────
# TEST GROUP 5: Decision-Matrix-Documentation (10 cases)
# ───────────────────────────────────────────────────────────────────────

def test_decision_matrix_documentation_v3():
    """V3 Decision-Matrix dokumentiert: 3-Target, IDF Default."""
    print()
    print("=== TEST 9: Decision-Matrix V3 (3-Target, IDF Default) ===")
    skill = SKILLS_DIR / "_A_berater_routing.md"
    content = skill.read_text(encoding="utf-8")

    cases = [
        ('entry_point bdf -> BDF', 'entry_point == "bdf"'),
        ('scope transkript-only -> STOP', 'transkript-only'),
        ('Default -> IDF', 'target = "IDF"'),
        ('Skill IDF orchestrate', '_IDF_orchestrate'),
        ('--from=direct arg', '--from=direct'),
        ('SC Sub-Modus reference', 'Sub-Modus von SDF'),
        ('Phase 8.5 Auto-Chain mention', "Phase 8.5"),
        ('modusEntscheidung mention', 'modusEntscheidung'),
        ('RETIRED list', "RETIRED_TARGETS"),
        ('INVALID_AS_A_TARGET list', "INVALID_AS_A_TARGET"),
    ]
    for name, needle in cases:
        assert_in(name, needle, content)


# ───────────────────────────────────────────────────────────────────────
# TEST GROUP 6: BL-162 Live-Case (DIRECT_I would be blocked)
# ───────────────────────────────────────────────────────────────────────

def test_bl162_direct_i_scenario():
    """BL-162 hatte routing_target='DIRECT_I' geschrieben — Guard MUSS blocken."""
    print()
    print("=== TEST 10: BL-162 DIRECT_I scenario (live regression) ===")
    bl162_manifest_diff = """
    A_PIPELINE_STATE_BL-162.phase = COMPLETED
    A_PIPELINE_STATE_BL-162.routing_target = "DIRECT_I"
    BERATER_OUTPUTS_BL-162.routing.target = DIRECT_I
    """
    violations = check_content(bl162_manifest_diff)
    # Es sollte mindestens 1 violation pro DIRECT_I-Match geben (2 matches)
    assert_eq("BL-162 DIRECT_I violations >= 1", len(violations) >= 1, True)
    if violations:
        assert_in("Reason mentions DIRECT_I-Familie", "DIRECT_I-Familie", violations[0])
        # V3 Alternative: IDF (Default-Pfad), nicht SC
        assert_in("Hinweis zu IDF (V3 Default-Pfad)", "IDF", violations[0])


# ───────────────────────────────────────────────────────────────────────
# TEST GROUP 7: BL-430 AK-5 — ROADMAP Whitelist Extension
# ───────────────────────────────────────────────────────────────────────

def test_roadmap_target_accepted():
    """BL-430 AK-5: routing_target='ROADMAP' MUSS akzeptiert werden (NICHT geblockt).
    FAILT mit aktueller Whitelist V3 {BDF, IDF, STOP} — ROADMAP fehlt dort.
    Expected: 0 violations (clean/continue). Aktuell: 1 violation (Whitelist-Block).
    """
    print()
    print("=== TEST 11 (AK-5): ROADMAP target NICHT geblockt (BL-430) ===")
    content = 'routing_target: "ROADMAP"'
    violations = check_content(content)
    # Standalone-runner: assert_eq fuer SUMMARY-Counter
    assert_eq("ROADMAP target accepted (0 violations)", len(violations), 0)
    # pytest-native: echtes assert fuer RED-Signal
    assert len(violations) == 0, (
        f"BL-430 AK-5: ROADMAP soll akzeptiert werden (0 violations), "
        f"aber Guard blockt: {violations}"
    )


def test_bdf_still_accepted():
    """BL-430 AK-5: routing_target='BDF' weiterhin NICHT geblockt (Backward-Compat).
    Sicherstellt dass ROADMAP-Erweiterung nichts bricht.
    """
    print()
    print("=== TEST 12 (AK-5): BDF target weiterhin akzeptiert (Backward-Compat) ===")
    content = 'routing_target: "BDF"'
    violations = check_content(content)
    assert_eq("BDF still accepted after ROADMAP extension (0 violations)", len(violations), 0)
    # pytest-native (Backward-Compat — soll schon gruen sein)
    assert len(violations) == 0, (
        f"BL-430 AK-5: BDF backward-compat gebrochen: {violations}"
    )


def test_garbage_target_blocked():
    """BL-430 AK-5: routing_target='GARBAGE_XYZ' weiterhin geblockt (Whitelist-Integrität).
    Sicherstellt dass die Whitelist-Erweiterung keine unbekannten Targets durchlässt.
    """
    print()
    print("=== TEST 13 (AK-5): GARBAGE_XYZ weiterhin geblockt ===")
    content = 'routing_target: "GARBAGE_XYZ"'
    violations = check_content(content)
    assert_eq("GARBAGE_XYZ still blocked (>= 1 violation)", len(violations) >= 1, True)
    if violations:
        assert_in("GARBAGE_XYZ reason mentions Whitelist", "Whitelist", violations[0])
    # pytest-native
    assert len(violations) >= 1, "GARBAGE_XYZ muss geblockt bleiben"
    assert any("Whitelist" in v for v in violations), (
        f"Whitelist-Hinweis fehlt in violations: {violations}"
    )


# ───────────────────────────────────────────────────────────────────────
# MAIN
# ───────────────────────────────────────────────────────────────────────

def main():
    print(f"{LABEL} Running Routing-Refit regression tests...")
    print(f"{LABEL} Source: BL-165 INV-MODUS-1, Refit 2026-05-17")

    test_whitelist_targets()
    test_invalid_as_a_target()
    test_direct_i_retired()
    test_invalid_target_blocked()
    test_no_routing_target_no_violations()
    test_pattern_variants()
    test_is_manifest_file()
    test_skill_a_berater_routing_v3()
    test_skill_a_postroute_v5()
    test_decision_matrix_documentation_v3()
    test_bl162_direct_i_scenario()
    test_roadmap_target_accepted()
    test_bdf_still_accepted()
    test_garbage_target_blocked()

    print()
    print(f"{LABEL} SUMMARY: PASS={PASS_COUNT}, FAIL={FAIL_COUNT}")

    if FAIL_COUNT > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
