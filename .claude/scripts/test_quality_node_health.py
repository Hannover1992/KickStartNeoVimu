"""
test_quality_node_health.py — BL-177 AK-2 + AK-9 Node-Health Tests

8 Tests:
1. test_frontmatter_schema_valid             — valid BL passes all checks
2. test_missing_field_detected               — missing required field = ERROR
3. test_invalid_status_blocked               — invalid status = ERROR
4. test_tags_under_minimum                   — <3 tags = WARN
5. test_unknown_reifegrad                    — invalid reifegrad = ERROR
6. test_auto_fix_suggestion                  — fix_suggestion present on findings
7. test_block_severity                       — ERROR => block_status=BLOCK, exit_code=2
8. test_pass_severity                        — clean BL => PASS, exit_code=0
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from quality_node_health import (
    NodeHealthBerater,
    check_frontmatter_schema,
    check_required_fields,
    check_status_enum,
    check_reifegrad_enum,
    check_tags_min_count,
    parse_frontmatter,
)
from quality_berater_base import (
    SEVERITY_ERROR,
    SEVERITY_WARN,
    BLOCK_STATUS_BLOCK,
    BLOCK_STATUS_PASS,
    BLOCK_STATUS_WARN,
    EXIT_BLOCK,
    EXIT_PASS,
    EXIT_WARN,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_FRONTMATTER = """---
type: backlog
feature: KnowledgeGraphQualitaet
bl-item: BL-177
tags: [quality, process, vault]
status: READY
reifegrad: SC-REIF
created: '2026-05-19'
updated: '2026-05-19'
---

# BL-177 Title
"""

MISSING_TAGS_FRONTMATTER = """---
type: backlog
feature: KnowledgeGraphQualitaet
bl-item: BL-177
tags: [quality]
status: READY
reifegrad: SC-REIF
---

# BL-177 Missing Tags
"""

MISSING_STATUS_FRONTMATTER = """---
type: backlog
feature: KnowledgeGraphQualitaet
bl-item: BL-177
tags: [quality, process, vault]
---

# BL-177 Missing Status
"""

INVALID_STATUS_FRONTMATTER = """---
type: backlog
feature: KnowledgeGraphQualitaet
bl-item: BL-177
tags: [quality, process, vault]
status: WORKING
reifegrad: SC-REIF
---

# BL-177 Invalid Status
"""

INVALID_REIFEGRAD_FRONTMATTER = """---
type: backlog
feature: KnowledgeGraphQualitaet
bl-item: BL-177
tags: [quality, process, vault]
status: READY
reifegrad: SUPER-REIF
---

# BL-177 Invalid Reifegrad
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_frontmatter_schema_valid():
    """Valid BL frontmatter produces no ERROR findings."""
    findings = check_frontmatter_schema(VALID_FRONTMATTER, "BL-177")
    errors = [f for f in findings if f.severity == SEVERITY_ERROR]
    assert errors == [], f"Unexpected errors: {errors}"


def test_missing_field_detected():
    """Missing required field 'status' produces ERROR finding."""
    findings = check_frontmatter_schema(MISSING_STATUS_FRONTMATTER, "BL-177")
    error_fields = [f.field for f in findings if f.severity == SEVERITY_ERROR]
    assert "status" in error_fields, f"Expected 'status' ERROR, got: {findings}"


def test_invalid_status_blocked():
    """Invalid status 'WORKING' produces ERROR finding on 'status' field."""
    findings = check_frontmatter_schema(INVALID_STATUS_FRONTMATTER, "BL-177")
    status_errors = [f for f in findings if f.field == "status" and f.severity == SEVERITY_ERROR]
    assert len(status_errors) >= 1, f"Expected status ERROR, got: {findings}"
    assert "WORKING" in status_errors[0].message


def test_tags_under_minimum():
    """tags with only 1 entry (< 3 minimum) produces WARN finding."""
    findings = check_frontmatter_schema(MISSING_TAGS_FRONTMATTER, "BL-177")
    tag_warns = [f for f in findings if f.field == "tags" and f.severity == SEVERITY_WARN]
    assert len(tag_warns) >= 1, f"Expected tags WARN, got: {findings}"
    assert "1" in tag_warns[0].message or "minimum" in tag_warns[0].message.lower()


def test_unknown_reifegrad():
    """Invalid reifegrad 'SUPER-REIF' produces ERROR finding."""
    findings = check_frontmatter_schema(INVALID_REIFEGRAD_FRONTMATTER, "BL-177")
    rg_errors = [f for f in findings if f.field == "reifegrad" and f.severity == SEVERITY_ERROR]
    assert len(rg_errors) >= 1, f"Expected reifegrad ERROR, got: {findings}"
    assert "SUPER-REIF" in rg_errors[0].message


def test_auto_fix_suggestion():
    """ERROR findings include a fix_suggestion when applicable."""
    findings = check_frontmatter_schema(MISSING_STATUS_FRONTMATTER, "BL-177")
    for f in findings:
        if f.severity == SEVERITY_ERROR and f.field in ("status",):
            assert f.fix_suggestion is not None, f"Expected fix_suggestion on {f}"


def test_block_severity():
    """NodeHealthBerater with ERROR finding returns BLOCK and exit_code=2."""
    with tempfile.TemporaryDirectory() as tmpdir:
        berater = NodeHealthBerater(repo_root=tmpdir)
        # Provide content with invalid status
        data = {"content": INVALID_STATUS_FRONTMATTER, "bl_folder": None}
        result = berater.run(bl_id="BL-177", data=data)
        assert result.block_status == BLOCK_STATUS_BLOCK
        assert result.exit_code == EXIT_BLOCK


def test_pass_severity():
    """NodeHealthBerater with valid BL returns PASS and exit_code=0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        berater = NodeHealthBerater(repo_root=tmpdir)
        data = {"content": VALID_FRONTMATTER, "bl_folder": None}
        result = berater.run(bl_id="BL-177", data=data)
        assert result.block_status == BLOCK_STATUS_PASS
        assert result.exit_code == EXIT_PASS
