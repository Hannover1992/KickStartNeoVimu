"""
BL-165 PL-3-02: CI-ready pytest for modus→routing_decision naming consistency.

Verifies that no .claude/commands/_*.md file contains a legacy
`modus = "refine"|"proceed"|"defer"` setter pattern.

These patterns should have been migrated to DF_BATCH_STATE.routing_decision
(BDF-Post-A field). DF_BATCH_STATE.modus is reserved for SDF M1..M9 mode
values written exclusively by _SDF_berater_modusEntscheidung.
"""

import re
from pathlib import Path

COMMANDS_DIR = Path(__file__).parent.parent / "commands"

LEGACY_PATTERNS = [
    re.compile(r'modus\s*=\s*["\']refine["\']', re.IGNORECASE),
    re.compile(r'modus\s*=\s*["\']proceed["\']', re.IGNORECASE),
    re.compile(r'modus\s*=\s*["\']defer["\']', re.IGNORECASE),
]


def _collect_skill_files():
    return sorted(COMMANDS_DIR.glob("_*.md"))


def test_commands_dir_exists():
    assert COMMANDS_DIR.exists(), f"commands dir not found: {COMMANDS_DIR}"
    assert COMMANDS_DIR.is_dir()


def test_no_legacy_modus_setters():
    """No _*.md file may set modus = refine|proceed|defer (BL-165 migration)."""
    violations = []
    for path in _collect_skill_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in LEGACY_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{path.name}:{lineno}: {line.strip()}")

    assert not violations, (
        f"Found {len(violations)} legacy modus setter(s) in .claude/commands/:\n"
        + "\n".join(violations)
        + "\n\nMigrate these to DF_BATCH_STATE.routing_decision (BL-165 AK-2)."
    )


def test_routing_decision_present_in_bdf_orchestrate():
    """_BDF_orchestrate.md must reference routing_decision (migration complete)."""
    bdf_file = COMMANDS_DIR / "_BDF_orchestrate.md"
    assert bdf_file.exists(), "_BDF_orchestrate.md not found"
    content = bdf_file.read_text(encoding="utf-8", errors="replace")
    assert "routing_decision" in content, (
        "_BDF_orchestrate.md does not reference routing_decision — PL-2-02 migration incomplete."
    )
