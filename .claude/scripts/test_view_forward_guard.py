"""
test_view_forward_guard.py — RED-phase tests for BL-480 view_forward_guard.py

These tests MUST FAIL on current code because view_forward_guard.py does not exist.

IMPORTANT DESIGN NOTE FOR GREEN PHASE:
  The guard must call view_forward_reference.forward_reference_view via the
  MODULE REFERENCE (i.e. `view_forward_reference.forward_reference_view(...)`)
  and NOT via a directly-imported name like `from view_forward_reference import
  forward_reference_view`.  Monkeypatching only works when the guard calls
  through the module object — if the guard imports the name directly the patch
  target would be view_forward_guard's local binding and monkeypatch.setattr on
  the view_forward_reference module would have no effect.

  Correct guard code:
      import view_forward_reference
      ...
      result = view_forward_reference.forward_reference_view(view_path, vault_root, ...)

  Wrong (breaks monkeypatch):
      from view_forward_reference import forward_reference_view
      ...
      result = forward_reference_view(view_path, vault_root, ...)
"""
from __future__ import annotations

import os
import sys

import pytest

# Make scripts/ importable when running from repo root or from this directory.
sys.path.insert(0, os.path.dirname(__file__))

# --- The module under test (does NOT exist yet → ImportError = RED) ---
import view_forward_guard  # noqa: E402  (must stay after sys.path.insert)
from view_forward_guard import enforce, forward_status  # noqa: E402

import view_forward_reference  # noqa: E402  (real module — used for monkeypatching)


# ---------------------------------------------------------------------------
# Helpers — build a minimal synthetic vault under tmp_path
# ---------------------------------------------------------------------------

def _write(path, text):
    """Create parent dirs and write text to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_vault(tmp_path):
    """
    Vault layout:

    BL-100-x — view WITH source_atoms + derivable substrate
        Backlog/BL-100-x/2_Model/BL-100-x_Model.md   <- view (is_view_node=True)
        Backlog/BL-100-x/2_Model/truths/W1.md         <- truth-atom (substrate)
        Backlog/BL-100-x/3_Spec/BL-100-x_Spec.md      <- spec with AK (substrate)
        Backlog/BL-100-x/_manifest.md                  <- non-view (is_view_node=False)

    BL-101-y — view WITHOUT source_atoms but derivable substrate
        Backlog/BL-101-y/2_Model/BL-101-y_Model.md    <- view (no source_atoms key)
        Backlog/BL-101-y/2_Model/truths/W1.md          <- truth-atom (substrate)

    BL-102-z — view whose BL has NO substrate (fragile)
        Backlog/BL-102-z/6_PL/BL-102-z-parking-lot.md <- view (no source_atoms, no substrate)
    """
    vault = tmp_path / "Vault"

    # ---- BL-100-x ----
    # View WITH source_atoms
    _write(
        vault / "Backlog" / "BL-100-x" / "2_Model" / "BL-100-x_Model.md",
        "---\ntype: model\nsource_atoms:\n  - Backlog/BL-100-x/2_Model/truths/W1.md\n---\n\n# Model BL-100-x\n",
    )
    # Truth atom (gives gather_substrate atoms=[...])
    _write(
        vault / "Backlog" / "BL-100-x" / "2_Model" / "truths" / "W1.md",
        "# W1\nAtomic truth for BL-100-x.\n",
    )
    # Spec with AK (gives gather_substrate aks=[...])
    _write(
        vault / "Backlog" / "BL-100-x" / "3_Spec" / "BL-100-x_Spec.md",
        "# Spec BL-100-x\n\n### AK-1: Foo works correctly\nDescription.\n",
    )
    # Non-view: _manifest.md
    _write(
        vault / "Backlog" / "BL-100-x" / "_manifest.md",
        "---\ntype: manifest\n---\n",
    )

    # ---- BL-101-y ----
    # View WITHOUT source_atoms key (model type, but no source_atoms in frontmatter)
    _write(
        vault / "Backlog" / "BL-101-y" / "2_Model" / "BL-101-y_Model.md",
        "---\ntype: model\n---\n\n# Model BL-101-y\n",
    )
    # Truth atom → substrate exists
    _write(
        vault / "Backlog" / "BL-101-y" / "2_Model" / "truths" / "W1.md",
        "# W1\nAtomic truth for BL-101-y.\n",
    )

    # ---- BL-102-z ----
    # Parking-lot view, no source_atoms, NO substrate at all
    _write(
        vault / "Backlog" / "BL-102-z" / "6_PL" / "BL-102-z-parking-lot.md",
        "---\ntype: parking_lot\n---\n\n# PL BL-102-z\n",
    )
    # No spec, no truth-atoms — gather_substrate.has_substrate == False

    return vault


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def vault(tmp_path):
    return _build_vault(tmp_path)


@pytest.fixture()
def bl100_model(vault):
    return str(vault / "Backlog" / "BL-100-x" / "2_Model" / "BL-100-x_Model.md")


@pytest.fixture()
def bl100_manifest(vault):
    return str(vault / "Backlog" / "BL-100-x" / "_manifest.md")


@pytest.fixture()
def bl101_model(vault):
    return str(vault / "Backlog" / "BL-101-y" / "2_Model" / "BL-101-y_Model.md")


@pytest.fixture()
def bl102_parking(vault):
    return str(vault / "Backlog" / "BL-102-z" / "6_PL" / "BL-102-z-parking-lot.md")


# ---------------------------------------------------------------------------
# Tests — forward_status()
# ---------------------------------------------------------------------------

class TestForwardStatus:
    def test_status_ok(self, vault, bl100_model):
        """BL-100 model view: has source_atoms + derivable substrate → status='ok'."""
        result = forward_status(bl100_model, str(vault))

        assert result["is_view"] is True
        assert result["has_source_atoms"] is True
        assert result["projector_derivable"] is True
        assert result["status"] == "ok"
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    def test_status_needs_ref(self, vault, bl101_model):
        """BL-101 model view: NO source_atoms but substrate exists → status='needs_ref'."""
        result = forward_status(bl101_model, str(vault))

        assert result["is_view"] is True
        assert result["has_source_atoms"] is False
        assert result["projector_derivable"] is True
        assert result["status"] == "needs_ref"
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    def test_status_fragile(self, vault, bl102_parking):
        """BL-102 parking view: no substrate → status='fragile', projector_derivable=False."""
        result = forward_status(bl102_parking, str(vault))

        assert result["is_view"] is True
        assert result["projector_derivable"] is False
        assert result["status"] == "fragile"
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0

    def test_status_skip_nonview(self, vault, bl100_manifest):
        """_manifest.md is not a view node → status='skip', is_view=False."""
        result = forward_status(bl100_manifest, str(vault))

        assert result["is_view"] is False
        assert result["status"] == "skip"
        assert isinstance(result["reason"], str)


# ---------------------------------------------------------------------------
# Tests — enforce()
# ---------------------------------------------------------------------------

class TestEnforce:
    def test_enforce_warn_flags_needs_ref(self, vault, bl101_model):
        """
        mode='warn' on needs_ref file:
          - action == 'warn'
          - non-empty message (LOUD warning)
          - file bytes UNCHANGED (warn never writes)
        """
        view_path = bl101_model
        before_bytes = open(view_path, "rb").read()

        result = enforce(view_path, str(vault), mode="warn")

        after_bytes = open(view_path, "rb").read()

        assert result["action"] == "warn"
        assert isinstance(result["message"], str)
        assert len(result["message"]) > 0
        # warn must NEVER write
        assert before_bytes == after_bytes, "enforce(mode='warn') must not modify the file"

    def test_enforce_fix_sets_source_atoms(self, vault, bl101_model, monkeypatch):
        """
        mode='fix' on needs_ref file with monkeypatched forward_reference_view:
          - fake writes a source_atoms line into the view file
          - action == 'fixed'
          - file now contains 'source_atoms'

        The guard MUST call view_forward_reference.forward_reference_view(...)
        through the module so this monkeypatch takes effect.
        """
        view_path = bl101_model

        def fake_forward_reference_view(vp, vr, *, atom_index, write, gate_mode, **kwargs):
            """Simulate a successful fix: write source_atoms into the file."""
            p = __import__("pathlib").Path(vp)
            text = p.read_text(encoding="utf-8")
            if "source_atoms:" not in text:
                # Insert after first ---\n (after opening frontmatter line)
                text = text.replace(
                    "---\ntype: model\n---",
                    "---\ntype: model\nsource_atoms:\n  - Backlog/BL-101-y/2_Model/truths/W1.md\n---",
                )
                p.write_text(text, encoding="utf-8")
            return {"action": "written", "n_proposed": 1}

        monkeypatch.setattr(
            view_forward_reference,
            "forward_reference_view",
            fake_forward_reference_view,
        )

        result = enforce(view_path, str(vault), mode="fix", atom_index={})

        assert result["action"] == "fixed"
        file_content = open(view_path, encoding="utf-8").read()
        assert "source_atoms" in file_content, "File should now contain source_atoms after fix"

    def test_enforce_fix_fragile_cannot_fix(self, vault, bl102_parking):
        """
        mode='fix' on fragile view (no substrate):
          - action == 'cannot_fix' (never fabricates)
          - file bytes UNCHANGED
        """
        view_path = bl102_parking
        before_bytes = open(view_path, "rb").read()

        result = enforce(view_path, str(vault), mode="fix")

        after_bytes = open(view_path, "rb").read()

        assert result["action"] == "cannot_fix"
        assert before_bytes == after_bytes, "enforce on fragile must not modify the file"
