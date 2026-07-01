"""
BL-165 PL-7-01: Regression-Test — no setter-patterns for modus keys in _*.md commands.

Verifies that no .claude/commands/_*.md file contains active setter patterns:
  recommended_modus[:=], sdf_mode_hint[:=], sdf_mode[:=],
  expected_sdf_mode[:=], mode_recommendation[:=]

Allowed: REVOKED-notes, not_writes-lists, comments (terms may be mentioned
but not as setters).

Regression-guard for F98-Deploy 2026-05-08 (BL-165).
"""

import re
import pytest
from pathlib import Path

COMMANDS_DIR = Path(__file__).parent.parent / "commands"

SETTER_PATTERNS = [
    re.compile(r'recommended_modus\s*[:=]', re.IGNORECASE),
    re.compile(r'sdf_mode_hint\s*[:=]', re.IGNORECASE),
    re.compile(r'sdf_mode\s*[:=]', re.IGNORECASE),
    re.compile(r'expected_sdf_mode\s*[:=]', re.IGNORECASE),
    re.compile(r'mode_recommendation\s*[:=]', re.IGNORECASE),
]

ALLOWED_CONTEXT_PATTERNS = [
    re.compile(r'REVOKED', re.IGNORECASE),
    re.compile(r'not_writes', re.IGNORECASE),
    re.compile(r'^\s*#'),
    re.compile(r'VERBOTEN', re.IGNORECASE),
    re.compile(r'NIEMALS', re.IGNORECASE),
    re.compile(r'darf.*nicht|not.*allowed|prohibited', re.IGNORECASE),
    re.compile(r'INV-MODUS', re.IGNORECASE),
    re.compile(r'Black-List|Blacklist|blacklist', re.IGNORECASE),
]


def _is_allowed_context(line: str) -> bool:
    return any(p.search(line) for p in ALLOWED_CONTEXT_PATTERNS)


def _match_outside_code_span(line: str, pattern) -> bool:
    """Return True if pattern matches anywhere OUTSIDE backtick code spans.

    A match that lies entirely within a `...` span is a documentation mention,
    not an active setter.  Only matches whose start position falls outside every
    backtick span count as real setters.
    """
    backtick_spans = [
        (m.start(), m.end())
        for m in re.finditer(r'`[^`]*`', line)
    ]

    def _inside_backtick(pos: int) -> bool:
        return any(start <= pos < end for start, end in backtick_spans)

    return any(
        not _inside_backtick(m.start())
        for m in pattern.finditer(line)
    )


def _collect_skill_files():
    return sorted(COMMANDS_DIR.glob("_*.md"))


def test_commands_dir_exists():
    assert COMMANDS_DIR.exists(), f"commands dir not found: {COMMANDS_DIR}"
    assert COMMANDS_DIR.is_dir()


def test_no_active_modus_setter_patterns():
    """No _*.md may contain active setter patterns for forbidden modus keys (BL-165 F98)."""
    violations = []
    for path in _collect_skill_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in SETTER_PATTERNS:
                if _match_outside_code_span(line, pattern) and not _is_allowed_context(line):
                    violations.append(f"{path.name}:{lineno}: {line.strip()}")

    assert not violations, (
        f"Found {len(violations)} forbidden modus setter(s) in .claude/commands/:\n"
        + "\n".join(violations)
        + "\n\nThese fields are reserved for SDF Phase 1.1 (_SDF_berater_modusEntscheidung)."
        + " Mention them only in REVOKED-notes, not_writes-lists, or comment lines."
        + " (BL-165 INV-MODUS-1/5, F98-Deploy 2026-05-08)"
    )


# ───── BL-410 AK-2+AK-3b: Anti-Rueckkehr-Fixture — list-dash-Form via Substring-Match ─────


@pytest.mark.parametrize("key,pattern", [
    ("recommended_modus",   SETTER_PATTERNS[0]),
    ("sdf_mode_hint",       SETTER_PATTERNS[1]),
    ("sdf_mode",            SETTER_PATTERNS[2]),
    ("expected_sdf_mode",   SETTER_PATTERNS[3]),
    ("mode_recommendation", SETTER_PATTERNS[4]),
])
def test_setter_patterns_catch_listform(key, pattern):
    """AK-2+AK-3/BL-410: SETTER_PATTERNS fangen list-dash-Form bereits via Substring-Match.

    Beweist W-VAL-3: unanchored re.search matcht '  - sdf_mode: heavy' ohne
    expliziten (?:-\\s*)?-Prefix. Anti-Rueckkehr-Guarantee: falls jemand die
    Patterns auf r'^{key}\\s*[:=]' verschaerft (anchored), schlaegt dieser Test RED.
    """
    list_dash_line = f"  - {key}: val"
    assert pattern.search(list_dash_line), (
        f"BL-410: SETTER_PATTERNS[{key}] muss list-dash-Form '{list_dash_line}' matchen "
        f"(W-VAL-3). Pattern: {pattern.pattern!r}"
    )


# ───── BL-406 AK-1: Backtick-Code-Span = Doku-Mention, kein aktiver Setter ─────


def test_backtick_doc_mention_not_flagged():
    """BL-406: key:val INNERHALB Backticks (Code-Span) gilt als Doku-Mention, nicht Setter.

    Beispiel: backtick-recommended_modus: "M3"-backtick in _K_score.md:1435
    Nach dem Fix soll _match_outside_code_span(line, pattern) False zurueckgeben.
    RED: _match_outside_code_span existiert noch nicht -> AttributeError/ImportError.
    """
    from regression_test_modus_keys import _match_outside_code_span  # noqa: F401 — RED-marker
    line = '- `recommended_modus: "M3"` (Beispiel)'
    assert _match_outside_code_span(line, SETTER_PATTERNS[0]) is False, (
        "BL-406: Backtick-umschlossene Doku-Mention darf nicht als aktiver Setter gelten."
    )


def test_active_setter_still_flagged():
    """BL-406 Negativ-Schutz: echter aktiver Setter (ohne Backticks) muss weiter erkannt werden.

    Schutzt gegen zu-permissiven Fix: _match_outside_code_span(line, pattern) muss True
    zurueckgeben wenn kein Code-Span vorhanden ist.
    RED: _match_outside_code_span existiert noch nicht -> AttributeError/ImportError.
    """
    from regression_test_modus_keys import _match_outside_code_span  # noqa: F401 — RED-marker
    line = '  recommended_modus: M3'
    assert _match_outside_code_span(line, SETTER_PATTERNS[0]) is True, (
        "BL-406: Echter aktiver Setter (kein Backtick) muss weiterhin als Setter erkannt werden."
    )
