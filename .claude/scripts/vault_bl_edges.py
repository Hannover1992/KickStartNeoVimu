#!/usr/bin/env python3
"""BL-446: Bidirektionale Vault-Edges zwischen BL-Sibling-Root (Hub) und Artefakten (Speichen).

API (Single-Source: migrate ruft vault_edge_link):
  - vault_edge_link(bl_id, file, vault_root=None) -> bool
      Eine bidirektionale Edge: Hub-Eintrag (## Artefakte im Sibling-Root) + Speiche-Backlink
      (frontmatter `bl_root:` ODER `> Teil von [[...]]`-Header in der Datei). At-write-time,
      idempotent (True=neu gesetzt, False=existierte bereits).
  - migrate_bl_edges(bl_folder) -> int
      Pro *.md-Artefakt (rekursiv im BL-Ordner) vault_edge_link rufen. Tolerant + idempotent.
  - migrate_all(backlog_root, skip_active=True) -> int
      Alle BL-Ordner. Skip aktive Lanes (manifest phase nicht in {INIT,DONE} bzw. status != DONE).

Wikilinks sind ORDNER-/PFAD-QUALIFIZIERT (W3), NIE nackte Basenamen:
  Hub->Speiche:  [[Backlog/BL-XXX-slug/2_Model/BL-XXX_Model]]
  Speiche->Hub:  bl_root: "[[Backlog/BL-XXX-slug/BL-XXX-slug]]"  ODER  > Teil von [[...]]
"""

from __future__ import annotations

import os
from pathlib import Path

# DRY: Working-Dir-Resolver (NUR importieren, BL-446 aendert ihn nicht).
from resolve_bl_path import resolve_bl_path

# Skip-Active: aktive Lane = phase NICHT in diesen Werten ODER status != DONE.
_INACTIVE_PHASES = {"INIT", "DONE"}


# ---------------------------------------------------------------------------
# Vault-Root + Pfad-Helfer
# ---------------------------------------------------------------------------

def _vault_root(vault_root: Path | str | None) -> Path:
    """Vault-Root aufloesen: expliziter Param > ENV CLAUDE_VAULT_ROOT > resolve_bl_path-Default."""
    if vault_root is not None:
        return Path(vault_root)
    env = os.environ.get("CLAUDE_VAULT_ROOT")
    if env:
        return Path(env)
    # Fallback: Default-Resolver aus resolve_bl_path (Heuristik-Kette).
    from resolve_bl_path import DEFAULT_VAULT_ROOT
    return Path(DEFAULT_VAULT_ROOT)


def _qualified_link(vault_root: Path, target: Path) -> str:
    """Ordner-qualifizierter Wikilink relativ zur Vault-Root, ohne .md-Suffix.

    z.B. Backlog/BL-901-alpha-feature/2_Model/BL-901_Model
    """
    rel = target.resolve().relative_to(vault_root.resolve())
    rel_no_ext = rel.with_suffix("")
    return "[[" + "/".join(rel_no_ext.parts) + "]]"


def _bl_folder_for_file(vault_root: Path, bl_id: str, file: Path) -> Path:
    """Resolve den BL-Ordner. Bevorzugt resolve_bl_path; Fallback: aus Datei-Pfad ableiten.

    Im Test ist die Datei stets unter Backlog/{bl_id}-{slug}/... — wir brauchen den
    Ordner, dessen Parent das Backlog ist (also direktes Kind von Backlog).
    """
    try:
        folder = resolve_bl_path(bl_id, vault_root)
        if folder.is_dir():
            return folder
    except (FileNotFoundError, RuntimeError, ValueError):
        pass
    # Fallback: vom Datei-Pfad nach oben bis zum Ordner, der mit bl_id beginnt.
    for parent in file.resolve().parents:
        if parent.name.startswith(f"{bl_id}-"):
            return parent
    # Letzter Fallback: direkter Parent.
    return file.resolve().parent


def _sibling_root(bl_folder: Path) -> Path:
    """Sibling-Root (Hub) NEBEN dem BL-Ordner: Backlog/{folder_name}.md."""
    return bl_folder.parent / f"{bl_folder.name}.md"


def _self_root_link(bl_folder: Path) -> str:
    """Backlink-Wikilink auf den Sibling-Root (vom Vault-Root aus qualifiziert).

    Form: [[Backlog/BL-XXX-slug/BL-XXX-slug]]
    (Der Sibling-Root liegt physisch als Backlog/BL-XXX-slug.md, aber der Wikilink
     zeigt — laut Test — auf den Ordner-internen Self-Pfad.)
    """
    name = bl_folder.name
    parent_name = bl_folder.parent.name  # "Backlog"
    return f"[[{parent_name}/{name}/{name}]]"


# ---------------------------------------------------------------------------
# Edge-Setzen (Hub + Speiche)
# ---------------------------------------------------------------------------

def _set_hub_entry(root_file: Path, link: str) -> bool:
    """Ergaenzt im Sibling-Root einen ## Artefakte-Listeneintrag fuer `link`. True=neu."""
    text = root_file.read_text(encoding="utf-8") if root_file.is_file() else ""
    if link in text:
        return False

    entry = f"- {link}"
    if "## Artefakte" in text:
        # Eintrag unter die existierende Sektion haengen.
        new_text = text.rstrip("\n") + f"\n{entry}\n"
    else:
        sep = "" if text.endswith("\n") or text == "" else "\n"
        new_text = text + f"{sep}\n## Artefakte\n\n{entry}\n"
    root_file.write_text(new_text, encoding="utf-8")
    return True


def _set_spoke_backlink(file: Path, root_link: str) -> bool:
    """Ergaenzt in `file` einen Backlink auf den Hub. True=neu.

    Mit Frontmatter -> `bl_root:`-Feld ins Frontmatter.
    Ohne Frontmatter -> `> Teil von [[...]]`-Header oben.
    """
    text = file.read_text(encoding="utf-8") if file.is_file() else ""
    if root_link in text:
        return False

    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            rest = text[end:]  # beginnt mit "\n---"
            fm_clean = fm.rstrip("\n")
            new_fm = f"{fm_clean}\nbl_root: \"{root_link}\"\n"
            new_text = "---" + new_fm + rest
            file.write_text(new_text, encoding="utf-8")
            return True

    # Kein (gueltiges) Frontmatter -> Header-Backlink oben.
    header = f"> Teil von {root_link}\n"
    sep = "\n" if text and not text.startswith("\n") else ""
    new_text = header + sep + text
    file.write_text(new_text, encoding="utf-8")
    return True


def vault_edge_link(bl_id: str, file: Path | str, vault_root: Path | str | None = None) -> bool:
    """Setzt EINE bidirektionale Edge (Hub-Eintrag + Speiche-Backlink). True=neu.

    Idempotent: zweiter Aufruf -> False, keine Mutation.
    """
    file = Path(file)
    root = _vault_root(vault_root)
    bl_folder = _bl_folder_for_file(root, bl_id, file)
    root_file = _sibling_root(bl_folder)

    hub_link = _qualified_link(root, file)
    spoke_link = _self_root_link(bl_folder)

    changed = False
    if _set_hub_entry(root_file, hub_link):
        changed = True
    if _set_spoke_backlink(file, spoke_link):
        changed = True
    return changed


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def _iter_artefacts(bl_folder: Path) -> list[Path]:
    """Alle *.md-Artefakte rekursiv, ausgeschlossen Sibling-Root + _manifest.md."""
    out = []
    for p in sorted(bl_folder.rglob("*.md")):
        if not p.is_file():
            continue
        if p.name == "_manifest.md":
            continue
        out.append(p)
    return out


def migrate_bl_edges(bl_folder: Path | str) -> int:
    """Verschaltet alle Artefakte EINES BL-Ordners. Returns #neu gesetzter Edges.

    Tolerant (leerer Ordner / fehlende Artefakte / fehlendes Frontmatter -> kein Crash).
    Idempotent. Ruft pro Datei vault_edge_link (Single-Source).
    """
    bl_folder = Path(bl_folder)
    if not bl_folder.is_dir():
        return 0

    bl_id = _bl_id_from_folder(bl_folder)
    if bl_id is None:
        return 0

    vault_root = _vault_root_from_folder(bl_folder)

    new_count = 0
    for artefact in _iter_artefacts(bl_folder):
        try:
            # Indirekt via Modul-Attribut, damit Test-Monkeypatch (spy) greift.
            import vault_bl_edges as _self
            if _self.vault_edge_link(bl_id, artefact, vault_root):
                new_count += 1
        except OSError:
            continue
    return new_count


def migrate_all(backlog_root: Path | str, skip_active: bool = True) -> int:
    """Verschaltet alle BL-Ordner unter backlog_root. Returns #neu gesetzter Edges.

    skip_active=True ueberspringt aktive Lanes (manifest phase nicht in {INIT,DONE}
    bzw. status != DONE).
    """
    backlog_root = Path(backlog_root)
    if not backlog_root.is_dir():
        return 0

    total = 0
    for folder in sorted(backlog_root.iterdir()):
        if not folder.is_dir():
            continue
        if not _bl_id_from_folder(folder):
            continue
        if skip_active and _is_active_lane(folder):
            continue
        import vault_bl_edges as _self
        total += _self.migrate_bl_edges(folder)
    return total


# ---------------------------------------------------------------------------
# Manifest / Lane-Status
# ---------------------------------------------------------------------------

def _bl_id_from_folder(folder: Path) -> str | None:
    """Extrahiert BL-ID aus Ordnernamen 'BL-XXX-slug' -> 'BL-XXX'."""
    name = folder.name
    parts = name.split("-")
    if len(parts) >= 2:
        candidate = f"{parts[0]}-{parts[1]}"
        if parts[0].isalpha() and parts[1].isdigit():
            return candidate
    return None


def _vault_root_from_folder(bl_folder: Path) -> Path:
    """Vault-Root aus BL-Ordner ableiten: parent von Backlog. Fallback: ENV/Default."""
    backlog = bl_folder.parent
    if backlog.name == "Backlog":
        return backlog.parent
    return _vault_root(None)


def _is_active_lane(bl_folder: Path) -> bool:
    """True wenn die Lane aktiv ist (manifest phase nicht in {INIT,DONE} ODER status != DONE).

    Kein Manifest -> als inaktiv behandeln (migrierbar).
    """
    manifest = bl_folder / "_manifest.md"
    if not manifest.is_file():
        return False
    try:
        text = manifest.read_text(encoding="utf-8")
    except OSError:
        return False

    phase = _read_manifest_field(text, "phase")
    status = _read_manifest_field(text, "status")

    if phase is not None and phase.upper() not in _INACTIVE_PHASES:
        return True
    if status is not None and status.upper() != "DONE":
        return True
    return False


def _read_manifest_field(text: str, field: str) -> str | None:
    """Liest ein Feld aus dem Manifest (auch eingerueckt, z.B. unter A_PIPELINE_STATE)."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{field}:"):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            if value:
                return value
    return None
