#!/usr/bin/env python3
"""
view_id_convention.py — SSOT for the PATH-derived view-id convention (BL-491 AC-2).

id-less views (parking-lots, arc42, …) cannot be named in any atom's
`referenced_by.by`, so the Capstone-Gate G3-backward can never go green for them.
This module defines a DETERMINISTIC, path-derived view-id so the backward link
becomes possible and verifiable.

Convention: a derived view-id is `PREFIX + <vault-relative POSIX path>`. Paths are
unique, so derived ids are unique; the same path always derives the same id (stable).
Vault paths carry no spaces -> the id is a YAML-safe plain scalar. A frontmatter `id`
(when present and non-empty) always WINS over the derived id (backward-compat).

Pure functions, no IO.
"""
from __future__ import annotations

PREFIX = "view::"


def derive_view_id(view_rel: str) -> str:
    """Derive a stable view-id from a vault-relative view path.

    Normalize backslashes to "/", strip a single leading "./" (or ".\\", which
    becomes "./" after normalization), then prefix with PREFIX. Deterministic.

    >>> derive_view_id("Backlog/BL-365-x/6_PL/BL-365-parking-lot.md")
    'view::Backlog/BL-365-x/6_PL/BL-365-parking-lot.md'
    """
    normalized = str(view_rel).replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return PREFIX + normalized


def resolve_view_id(fm: dict, view_rel: str) -> str:
    """Resolve the effective view-id.

    If `fm["id"]` is a non-empty (after strip) string -> return it verbatim
    (frontmatter id wins, backward-compat). Otherwise -> derive_view_id(view_rel).
    """
    if isinstance(fm, dict):
        raw = fm.get("id")
        if isinstance(raw, str) and raw.strip():
            return raw
    return derive_view_id(view_rel)


def is_derived_id(view_id: str) -> bool:
    """True iff `view_id` is a string carrying the derived-id PREFIX."""
    return isinstance(view_id, str) and view_id.startswith(PREFIX)
