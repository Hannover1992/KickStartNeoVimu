#!/usr/bin/env python3
"""RED-phase tests for truth_view_backref_materialize.py (Lane C, BL-491 G3-backward).

The module truth_view_backref_materialize does NOT exist yet.
Import at collection time fails with ModuleNotFoundError -- correct RED state.
No implementation created. No real vault touched. All fixtures use tmp_path only.

G3-backward contract: each source atom's referenced_by must name the view that lists
it in source_atoms. The new tool consumes view_backref_index.build_view_backref_index
and WRITES atoms surgically (reusing truth_backref_materialize._build_new_content),
merging with existing referenced_by entries (truth_edge entries PRESERVED), deduped.

Fixture layout:
  Backlog/BL-T/2_Model/T_Model.md          <- VIEW (is_view_node True; has id VIEW.TModel)
  Backlog/BL-T/2_Model/truths/AtomA.md     <- truth atom (is_view_node False)
  Backlog/BL-T/2_Model/truths/AtomB.md     <- truth atom (clean, no existing refs)

View carries source_atoms: [ATOM_A_REL, ATOM_B_REL].
AtomA has a pre-existing referenced_by entry {by: NS.SomeSource, kind: truth_edge}
plus edges + keywords fields -> used for PRESERVE and SURGICAL tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

# Ensure scripts dir is importable (mirrors other modules in this dir).
_SCRIPTS_DIR = Path(__file__).parent.absolute()
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# RED: truth_view_backref_materialize does NOT exist yet.
# ModuleNotFoundError at collection = correct RED state.
import truth_view_backref_materialize  # noqa: E402
from truth_view_backref_materialize import materialize, main  # noqa: E402, F401


# ──────────────────────────────────────────────────────────────────────────────
# Fixture layout constants
# ──────────────────────────────────────────────────────────────────────────────

# VIEW: Backlog/<bl>/2_Model/<name>_Model.md -> is_view_node returns True (depth-4 rule).
VIEW_REL = "Backlog/BL-T/2_Model/T_Model.md"
VIEW_ID = "VIEW.TModel"  # explicit frontmatter id -> resolve_view_id returns this

# Truth atoms: Backlog/<bl>/2_Model/truths/*.md -> is_view_node returns False.
ATOM_A_REL = "Backlog/BL-T/2_Model/truths/AtomA.md"
ATOM_B_REL = "Backlog/BL-T/2_Model/truths/AtomB.md"

# Existing truth_edge reference on AtomA (must survive materialize).
EXISTING_REF_BY = "NS.SomeSource"
EXISTING_REF_KIND = "truth_edge"


# ──────────────────────────────────────────────────────────────────────────────
# File builders (tmp_path only -- never the real vault)
# ──────────────────────────────────────────────────────────────────────────────

def _write_view(
    root: Path,
    rel: str,
    *,
    view_id: str | None,
    source_atoms: list[str],
) -> Path:
    """Write a VIEW node file recognized by is_view_node.

    Uses the real-vault unindented block-sequence form for source_atoms (column 0)
    which YAML-first parsers in view_backref_index accept.
    """
    lines = ["---"]
    if view_id is not None:
        lines.append(f"id: {view_id}")
    lines.append("tags:")
    lines.append("- type/view")
    lines.append("source_atoms:")
    for atom_rel in source_atoms:
        lines.append(f"- {atom_rel}")
    lines.append("---")
    lines.append("")
    lines.append("# View body")
    lines.append("")

    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_atom(
    root: Path,
    rel: str,
    *,
    local_id: str,
    text_val: str = "example atom text",
    edges: list[dict] | None = None,
    keywords: list[str] | None = None,
    existing_ref: dict | None = None,
) -> Path:
    """Write a truth atom with proper ---...--- frontmatter.

    The frontmatter matches _parse_frontmatter's ^---\\n(.*?)\\n---\\n regex.
    All fields that must survive materialize (text, edges, keywords) are written here.
    An optional existing_ref adds a pre-existing referenced_by entry.
    """
    fm_lines: list[str] = []
    fm_lines.append("---")
    fm_lines.append(f"id: {local_id}")
    fm_lines.append(f"local_id: {local_id}")
    fm_lines.append("type: truth")
    fm_lines.append(f"text: {text_val}")
    if edges:
        fm_lines.append("edges:")
        for e in edges:
            fm_lines.append(f"  - by: {e['by']}")
            fm_lines.append(f"    kind: {e['kind']}")
    if keywords:
        fm_lines.append("keywords:")
        for kw in keywords:
            fm_lines.append(f"  - {kw}")
    if existing_ref:
        fm_lines.append("referenced_by:")
        fm_lines.append(f"  - by: {existing_ref['by']}")
        fm_lines.append(f"    kind: {existing_ref['kind']}")
    fm_lines.append("---")
    fm_lines.append("")
    fm_lines.append("Body paragraph alpha beta gamma.")
    fm_lines.append("")

    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(fm_lines), encoding="utf-8")
    return path


def _parse_fm(path: Path) -> dict:
    """Parse the YAML frontmatter of an atom file. Returns {} on failure."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    fm_text = content[3:end]
    if yaml is not None:
        try:
            result = yaml.safe_load(fm_text)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
    return {}


def _get_body(content: str) -> str:
    """Return everything after the closing frontmatter delimiter."""
    end = content.find("\n---\n", 3)
    if end == -1:
        return content
    return content[end + 5:]


def _setup_vault(root: Path) -> None:
    """Canonical vault fixture:
    - ONE view (VIEW_REL, id=VIEW_ID) listing both atoms in source_atoms.
    - AtomA: has existing truth_edge ref + edges + keywords fields.
    - AtomB: clean (no existing refs, no edges, no keywords).
    """
    _write_view(root, VIEW_REL, view_id=VIEW_ID, source_atoms=[ATOM_A_REL, ATOM_B_REL])
    _write_atom(
        root,
        ATOM_A_REL,
        local_id="NS.AtomA",
        text_val="atom a body text",
        edges=[{"by": "NS.Other", "kind": "truth_edge"}],
        keywords=["alpha", "beta"],
        existing_ref={"by": EXISTING_REF_BY, "kind": EXISTING_REF_KIND},
    )
    _write_atom(root, ATOM_B_REL, local_id="NS.AtomB")


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: G3 contract -- atom gets view_source referenced_by after apply=True
# ──────────────────────────────────────────────────────────────────────────────

class TestG3Contract:
    """After materialize(vault, apply=True), source atoms gain a view_source entry."""

    def test_atom_a_gets_view_source_backref(self, tmp_path):
        """G3: AtomA's referenced_by contains {by: VIEW_ID, kind: view_source}."""
        _setup_vault(tmp_path)
        materialize(tmp_path, apply=True)

        fm = _parse_fm(tmp_path / ATOM_A_REL)
        rb = fm.get("referenced_by") or []
        assert any(
            e.get("by") == VIEW_ID and e.get("kind") == "view_source"
            for e in rb
        ), f"Expected view_source with by={VIEW_ID!r} in referenced_by, got: {rb}"

    def test_atom_b_gets_view_source_backref(self, tmp_path):
        """G3: AtomB (clean atom, no prior refs) also gets view_source entry."""
        _setup_vault(tmp_path)
        materialize(tmp_path, apply=True)

        fm = _parse_fm(tmp_path / ATOM_B_REL)
        rb = fm.get("referenced_by") or []
        assert any(
            e.get("by") == VIEW_ID and e.get("kind") == "view_source"
            for e in rb
        ), f"Expected view_source with by={VIEW_ID!r} in referenced_by, got: {rb}"

    def test_result_dict_keys_and_types(self, tmp_path):
        """materialize() returns dict with int keys: views, atoms, would_update,
        updated, backed_up, added_backrefs."""
        _setup_vault(tmp_path)
        result = materialize(tmp_path, apply=True)

        for key in ("views", "atoms", "would_update", "updated", "backed_up", "added_backrefs"):
            assert key in result, (
                f"Missing key '{key}' in result dict. Keys present: {sorted(result)}"
            )
            assert isinstance(result[key], int), (
                f"Key '{key}' must be int, got {type(result[key])!r}: {result[key]!r}"
            )

    def test_updated_count_positive_after_apply(self, tmp_path):
        """After apply=True on a fresh vault, updated >= 1."""
        _setup_vault(tmp_path)
        result = materialize(tmp_path, apply=True)

        assert result["updated"] >= 1, (
            f"Expected at least 1 atom updated after apply=True, got: {result['updated']}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: PRESERVE -- existing truth_edge entry survives alongside new view_source
# ──────────────────────────────────────────────────────────────────────────────

class TestPreserveExisting:
    """Pre-existing {by: EXISTING_REF_BY, kind: truth_edge} must not be lost."""

    def test_existing_truth_edge_preserved(self, tmp_path):
        """AtomA had {by: NS.SomeSource, kind: truth_edge} before materialize.
        That entry must still be in referenced_by after apply=True."""
        _setup_vault(tmp_path)
        materialize(tmp_path, apply=True)

        fm = _parse_fm(tmp_path / ATOM_A_REL)
        rb = fm.get("referenced_by") or []
        assert any(
            e.get("by") == EXISTING_REF_BY and e.get("kind") == EXISTING_REF_KIND
            for e in rb
        ), (
            f"Existing {EXISTING_REF_KIND!r} entry (by={EXISTING_REF_BY!r}) lost "
            f"after materialize. referenced_by now: {rb}"
        )

    def test_both_entries_coexist(self, tmp_path):
        """After apply=True, AtomA's referenced_by has BOTH the original truth_edge
        AND the new view_source entry (merged, not replaced)."""
        _setup_vault(tmp_path)
        materialize(tmp_path, apply=True)

        fm = _parse_fm(tmp_path / ATOM_A_REL)
        rb = fm.get("referenced_by") or []

        has_truth_edge = any(
            e.get("by") == EXISTING_REF_BY and e.get("kind") == EXISTING_REF_KIND
            for e in rb
        )
        has_view_source = any(
            e.get("by") == VIEW_ID and e.get("kind") == "view_source"
            for e in rb
        )
        assert has_truth_edge and has_view_source, (
            f"Expected both truth_edge AND view_source in referenced_by.\n"
            f"truth_edge present={has_truth_edge}, view_source present={has_view_source}\n"
            f"referenced_by: {rb}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: DEDUP / IDEMPOTENT -- second run: updated==0, no duplicate entries
# ──────────────────────────────────────────────────────────────────────────────

class TestDedup:
    """materialize is idempotent: second run does not re-write atoms."""

    def test_second_run_updated_zero(self, tmp_path):
        """Running materialize(apply=True) twice: second run returns updated==0."""
        _setup_vault(tmp_path)
        materialize(tmp_path, apply=True)         # first run
        result2 = materialize(tmp_path, apply=True)  # second run

        assert result2["updated"] == 0, (
            f"Second apply run must be idempotent (updated==0), got: {result2['updated']}"
        )

    def test_no_duplicate_view_source_after_double_run(self, tmp_path):
        """After two apply runs, AtomA has exactly ONE view_source entry for VIEW_ID."""
        _setup_vault(tmp_path)
        materialize(tmp_path, apply=True)
        materialize(tmp_path, apply=True)

        fm = _parse_fm(tmp_path / ATOM_A_REL)
        rb = fm.get("referenced_by") or []
        view_source_count = sum(
            1 for e in rb
            if e.get("by") == VIEW_ID and e.get("kind") == "view_source"
        )
        assert view_source_count == 1, (
            f"Expected exactly 1 view_source entry for {VIEW_ID!r}, "
            f"got {view_source_count}. referenced_by: {rb}"
        )

    def test_second_run_would_update_zero(self, tmp_path):
        """After first apply, second run's would_update==0 (already current)."""
        _setup_vault(tmp_path)
        materialize(tmp_path, apply=True)
        result2 = materialize(tmp_path, apply=True)

        assert result2["would_update"] == 0, (
            f"Second run would_update must be 0, got: {result2['would_update']}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: DRY-RUN -- apply=False: would_update>=1, updated==0, file unchanged
# ──────────────────────────────────────────────────────────────────────────────

class TestDryRun:
    """apply=False: no writes, but would_update reflects pending changes."""

    def test_dry_run_updated_is_zero(self, tmp_path):
        """apply=False -> updated==0 even when backrefs would be added."""
        _setup_vault(tmp_path)
        result = materialize(tmp_path, apply=False)

        assert result["updated"] == 0, (
            f"Dry-run must not write (updated must be 0), got: {result['updated']}"
        )

    def test_dry_run_would_update_positive(self, tmp_path):
        """apply=False -> would_update>=1 (atoms need new view_source entries)."""
        _setup_vault(tmp_path)
        result = materialize(tmp_path, apply=False)

        assert result["would_update"] >= 1, (
            f"Dry-run expected would_update>=1 (pending backrefs), got: {result}"
        )

    def test_dry_run_atom_a_file_unchanged(self, tmp_path):
        """apply=False: AtomA on disk is byte-identical before and after dry-run."""
        _setup_vault(tmp_path)
        atom_a = tmp_path / ATOM_A_REL
        content_before = atom_a.read_bytes()

        materialize(tmp_path, apply=False)

        content_after = atom_a.read_bytes()
        assert content_before == content_after, (
            "Dry-run changed AtomA on disk (content differs)"
        )

    def test_dry_run_atom_b_file_unchanged(self, tmp_path):
        """apply=False: AtomB on disk is byte-identical before and after dry-run."""
        _setup_vault(tmp_path)
        atom_b = tmp_path / ATOM_B_REL
        content_before = atom_b.read_bytes()

        materialize(tmp_path, apply=False)

        content_after = atom_b.read_bytes()
        assert content_before == content_after, (
            "Dry-run changed AtomB on disk (content differs)"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: SURGICAL -- only referenced_by changed; text/edges/keywords/body intact
# ──────────────────────────────────────────────────────────────────────────────

class TestSurgical:
    """After apply=True, all fields except referenced_by are byte-/value-identical."""

    def test_text_field_unchanged(self, tmp_path):
        """'text' frontmatter field is value-identical after materialize."""
        _setup_vault(tmp_path)
        fm_before = _parse_fm(tmp_path / ATOM_A_REL)
        text_before = fm_before.get("text")

        materialize(tmp_path, apply=True)

        fm_after = _parse_fm(tmp_path / ATOM_A_REL)
        assert fm_after.get("text") == text_before, (
            f"'text' field changed: {text_before!r} -> {fm_after.get('text')!r}"
        )

    def test_edges_field_unchanged(self, tmp_path):
        """'edges' frontmatter field is value-identical after materialize."""
        _setup_vault(tmp_path)
        fm_before = _parse_fm(tmp_path / ATOM_A_REL)
        edges_before = fm_before.get("edges")

        materialize(tmp_path, apply=True)

        fm_after = _parse_fm(tmp_path / ATOM_A_REL)
        assert fm_after.get("edges") == edges_before, (
            f"'edges' field changed: {edges_before!r} -> {fm_after.get('edges')!r}"
        )

    def test_keywords_field_unchanged(self, tmp_path):
        """'keywords' frontmatter field is value-identical after materialize."""
        _setup_vault(tmp_path)
        fm_before = _parse_fm(tmp_path / ATOM_A_REL)
        keywords_before = fm_before.get("keywords")

        materialize(tmp_path, apply=True)

        fm_after = _parse_fm(tmp_path / ATOM_A_REL)
        assert fm_after.get("keywords") == keywords_before, (
            f"'keywords' field changed: {keywords_before!r} -> {fm_after.get('keywords')!r}"
        )

    def test_body_unchanged(self, tmp_path):
        """Content after the closing '---\\n' (body) is byte-identical after materialize."""
        _setup_vault(tmp_path)
        content_before = (tmp_path / ATOM_A_REL).read_text(encoding="utf-8")
        body_before = _get_body(content_before)

        materialize(tmp_path, apply=True)

        content_after = (tmp_path / ATOM_A_REL).read_text(encoding="utf-8")
        body_after = _get_body(content_after)
        assert body_after == body_before, (
            f"Body changed after materialize.\nBefore: {body_before!r}\nAfter:  {body_after!r}"
        )

    def test_frontmatter_yaml_valid_after_apply(self, tmp_path):
        """After apply, AtomA's frontmatter parses cleanly with yaml.safe_load."""
        _setup_vault(tmp_path)
        materialize(tmp_path, apply=True)

        content = (tmp_path / ATOM_A_REL).read_text(encoding="utf-8")
        assert content.startswith("---"), "Opening frontmatter delimiter missing after apply"
        end = content.find("\n---", 3)
        assert end != -1, "Closing frontmatter delimiter missing after apply"
        fm_text = content[3:end]

        if yaml is not None:
            parsed = yaml.safe_load(fm_text)
            assert isinstance(parsed, dict), (
                f"Frontmatter did not parse to dict after apply: {parsed!r}"
            )
            assert parsed.get("type") == "truth", (
                f"'type: truth' missing after apply: {parsed!r}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Test 6: BACKUP -- backup_dir copies pre-write atom at backup_dir/<atom_rel>
# ──────────────────────────────────────────────────────────────────────────────

class TestBackup:
    """apply=True + backup_dir: backed_up==updated; backup at backup_dir/<atom_rel>."""

    def _setup_in_subvault(self, root: Path) -> tuple[Path, Path]:
        """Create vault + backup as siblings under root to test rel-path preservation."""
        vault = root / "vault"
        backup = root / "backup"
        vault.mkdir()
        _setup_vault(vault)
        return vault, backup

    def test_backed_up_equals_updated(self, tmp_path):
        """backed_up count equals updated count when backup_dir is provided."""
        vault, backup = self._setup_in_subvault(tmp_path)
        result = materialize(vault, apply=True, backup_dir=backup)

        assert result["backed_up"] == result["updated"], (
            f"backed_up ({result['backed_up']}) must equal updated ({result['updated']})"
        )
        assert result["updated"] >= 1, (
            "Expected at least 1 atom updated (and thus backed up)"
        )

    def test_backup_exists_at_rel_path(self, tmp_path):
        """Backup for ATOM_A_REL exists at backup_dir/ATOM_A_REL (rel path preserved)."""
        vault, backup = self._setup_in_subvault(tmp_path)
        materialize(vault, apply=True, backup_dir=backup)

        expected_backup = backup / ATOM_A_REL
        assert expected_backup.exists(), (
            f"Backup for {ATOM_A_REL!r} not found at expected path: {expected_backup}\n"
            f"Files in backup: {list(backup.rglob('*.md'))}"
        )

    def test_backup_contains_original_content(self, tmp_path):
        """The backup file contains the PRE-WRITE (original) atom content."""
        vault, backup = self._setup_in_subvault(tmp_path)
        atom_a = vault / ATOM_A_REL
        original_bytes = atom_a.read_bytes()

        materialize(vault, apply=True, backup_dir=backup)

        backup_atom_a = backup / ATOM_A_REL
        assert backup_atom_a.exists(), f"Backup not found: {backup_atom_a}"
        assert backup_atom_a.read_bytes() == original_bytes, (
            "Backup must contain the PRE-WRITE content of the atom, not the updated content"
        )

    def test_no_backup_when_no_backup_dir(self, tmp_path):
        """When backup_dir is None, backed_up==0 regardless of updates."""
        _setup_vault(tmp_path)
        result = materialize(tmp_path, apply=True, backup_dir=None)

        assert result["backed_up"] == 0, (
            f"backed_up must be 0 when no backup_dir given, got: {result['backed_up']}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Test 7: CLI -- main() argparse interface
# ──────────────────────────────────────────────────────────────────────────────

class TestCli:
    """CLI: main(argv) -> int; --vault REQUIRED; --apply; --backup-dir DIR."""

    def test_main_dry_run_exits_zero(self, tmp_path):
        """main(["--vault", str(vault)]) exits 0 (dry-run by default)."""
        _setup_vault(tmp_path)
        rc = main(["--vault", str(tmp_path)])
        assert rc == 0, f"main dry-run must return 0, got: {rc}"

    def test_main_dry_run_no_write(self, tmp_path):
        """main without --apply does not modify atom files on disk."""
        _setup_vault(tmp_path)
        content_before = (tmp_path / ATOM_A_REL).read_bytes()

        main(["--vault", str(tmp_path)])

        content_after = (tmp_path / ATOM_A_REL).read_bytes()
        assert content_before == content_after, (
            "main dry-run (no --apply) must not change atom files"
        )

    def test_main_apply_exits_zero(self, tmp_path):
        """main(["--vault", str(vault), "--apply"]) exits 0."""
        _setup_vault(tmp_path)
        rc = main(["--vault", str(tmp_path), "--apply"])
        assert rc == 0, f"main --apply must return 0, got: {rc}"

    def test_main_apply_materializes_view_source(self, tmp_path):
        """main --apply adds view_source backref to atom files."""
        _setup_vault(tmp_path)
        main(["--vault", str(tmp_path), "--apply"])

        fm = _parse_fm(tmp_path / ATOM_A_REL)
        rb = fm.get("referenced_by") or []
        assert any(
            e.get("by") == VIEW_ID and e.get("kind") == "view_source"
            for e in rb
        ), f"main --apply did not add view_source backref. referenced_by: {rb}"

    def test_main_nonexistent_vault_returns_two(self, tmp_path):
        """main(["--vault", "<nonexistent>"]) returns 2."""
        rc = main(["--vault", str(tmp_path / "no_such_dir")])
        assert rc == 2, (
            f"Expected exit code 2 for non-existent vault, got: {rc}"
        )

    def test_main_apply_with_backup_dir(self, tmp_path):
        """main(["--vault", ..., "--apply", "--backup-dir", ...]) exits 0."""
        vault = tmp_path / "vault"
        backup = tmp_path / "backup"
        vault.mkdir()
        _setup_vault(vault)

        rc = main(["--vault", str(vault), "--apply", "--backup-dir", str(backup)])
        assert rc == 0, f"main --apply --backup-dir must return 0, got: {rc}"
        # Backup dir should exist and have content
        assert backup.exists(), "backup_dir was not created by main --apply --backup-dir"
