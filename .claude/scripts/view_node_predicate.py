#!/usr/bin/env python3
"""
view_node_predicate.py — Canonical view-node predicate (SSoT, BL-460).

This module is the Single-Source-of-Truth for the is_view_node predicate,
shared by:
  - P1 swarm corpus builder (schwarm_decomposer.py)
  - P2 PostToolUse Write/Edit hook (hook_view_forward_reference.py)

Both consumers import from here; neither defines its own copy.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_view_node(path: str, vault_root: str) -> bool:
    """Return True iff path is inside vault_root AND matches a view-node glob.

    View-node patterns (all relative to vault_root):
        Backlog/<bl>/2_Model/<name>_Model.md  (NOT truths/ subdir)
        Backlog/<bl>/arc42/<name>.md
        Backlog/<bl>/6_PL/<name>.md
        Docs/**/*.md  (including Docs/*.md at top-level)

    Exclusions (always False):
        Backlog/<bl>/2_Model/truths/*.md
        _manifest.md  (any filename == _manifest.md)
        non-.md files
        outside vault_root
        .claude/ directory
    """
    try:
        # Normalise both paths
        norm_path = os.path.normcase(os.path.normpath(os.path.abspath(str(path))))
        norm_vault = os.path.normcase(os.path.normpath(os.path.abspath(str(vault_root))))

        p = Path(norm_path)
        vault = Path(norm_vault)

        # Must end in .md
        if p.suffix.lower() != ".md":
            return False

        # Must be inside vault
        try:
            common = Path(os.path.commonpath([str(p), str(vault)]))
            if common != vault:
                return False
        except ValueError:
            # Different drives on Windows
            return False

        # Must not be _manifest.md
        if p.name == "_manifest.md":
            return False

        # Relative path from vault root
        try:
            rel = p.relative_to(vault)
        except ValueError:
            return False

        # Use lowercase parts for case-insensitive matching (normcase lowercases on Windows)
        rel_parts = tuple(part.lower() for part in rel.parts)

        # Exclude .claude/ subtree
        if rel_parts and rel_parts[0] == ".claude":
            return False

        # Exclude _legacy/ subtree
        if rel_parts and rel_parts[0] == "_legacy":
            return False

        # --- Docs/**/*.md ---
        if rel_parts and rel_parts[0] == "docs":
            return True

        # --- Libraries/** knowledge-views (NOT templates/indexes/readmes/schemas/drafts) ---
        if rel_parts and rel_parts[0] == "libraries":
            basename = rel_parts[-1]  # already lowercase
            _LIB_INFRA = {"_index.md", "readme.md", "template.md", "convention.md",
                          "frontmatter-schema.md", "crossref_index.md"}
            if basename in _LIB_INFRA:
                return False
            if basename.endswith("_template.md"):
                return False
            if "_drafts" in rel_parts:
                return False
            return True

        # --- Backlog/<bl>/2_Model/truths/*.md: EXCLUDED (atoms, not views) ---
        # Must check truths BEFORE the generic 2_model match
        if (len(rel_parts) >= 5
                and rel_parts[0] == "backlog"
                and rel_parts[2] == "2_model"
                and rel_parts[3] == "truths"):
            return False

        # --- Backlog/<bl>/Model/truths/*.md: EXCLUDED (legacy folder, atoms) ---
        # Must check truths BEFORE the legacy model match
        if (len(rel_parts) >= 5
                and rel_parts[0] == "backlog"
                and rel_parts[2] == "model"
                and rel_parts[3] == "truths"):
            return False

        # --- Backlog/<bl>/2_Model/<name>_Model.md  (NOT truths/) ---
        # rel_parts: ("backlog", "<bl>", "2_model", "<name>_model.md")
        if (len(rel_parts) == 4
                and rel_parts[0] == "backlog"
                and rel_parts[2] == "2_model"
                and rel_parts[3].endswith("_model.md")):
            return True

        # --- Backlog/<bl>/arc42/<name>.md ---
        if (len(rel_parts) == 4
                and rel_parts[0] == "backlog"
                and rel_parts[2] == "arc42"):
            return True

        # --- Backlog/<bl>/6_PL/<name>.md ---
        if (len(rel_parts) == 4
                and rel_parts[0] == "backlog"
                and rel_parts[2] == "6_pl"):
            return True

        # --- Backlog/<bl>/Model/<name>_Model.md  (legacy folder, depth 4, NOT truths/) ---
        if (len(rel_parts) == 4
                and rel_parts[0] == "backlog"
                and rel_parts[2] == "model"
                and rel_parts[3].endswith("_model.md")):
            return True

        # --- Models/<name>_Model.md  (vault-top Models/ dir, depth 2) ---
        if (len(rel_parts) == 2
                and rel_parts[0] == "models"
                and rel_parts[1].endswith("_model.md")):
            return True

        # --- <name>_Model.md at vault root (depth 1) ---
        if len(rel_parts) == 1 and rel_parts[0].endswith("_model.md"):
            return True

        return False

    except Exception:
        return False
