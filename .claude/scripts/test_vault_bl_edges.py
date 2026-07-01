#!/usr/bin/env python3
"""RED-Tests fuer BL-446 batch_1 (M3): vault_bl_edges.py — AK-1 migrate + AK-2a helper.

Test-Strategie (Spec): Python-Unit-Tests gegen `vault_bl_edges.py` mit tmp-BL-Ordnern
(synthetischer Mini-Korpus, KEINE echte Vault-Mutation, alles unter tmp_path).

API definiert durch diese Tests (RED — vault_bl_edges existiert noch nicht):
  - vault_edge_link(bl_id, file, vault_root=None) -> bool   (AK-2a, W6)
  - migrate_bl_edges(bl_folder) -> int|list                 (AK-1, W5)
  - migrate_all(backlog_root, skip_active=True) -> ...       (AK-1, W5)

Wikilink-Format (W3): ordner-/pfad-qualifiziert, NIE nackte Basenamen:
  Hub->Speiche:  [[Backlog/BL-XXX-slug/2_Model/BL-XXX_Model]]
  Speiche->Hub:  bl_root: "[[Backlog/BL-XXX-slug/BL-XXX-slug]]"  ODER  > Teil von [[...]]
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# RED: import schlaegt fehl (ModuleNotFoundError) bis GREEN vault_bl_edges.py anlegt.
import vault_bl_edges


# ---------------------------------------------------------------------------
# Synthetischer tmp-Korpus (KEINE echte Vault-Mutation)
# ---------------------------------------------------------------------------

def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _make_bl(
    backlog: Path,
    bl_id: str,
    slug: str,
    *,
    status: str = "DONE",
    phase: str = "DONE",
    artefacts: dict[str, str] | None = None,
    with_manifest: bool = True,
) -> Path:
    """Erzeugt einen synthetischen BL-Ordner + Sibling-Root, gibt den Ordner zurueck.

    Layout (entspricht resolve_bl_path-Erwartung + Spec W2 Sibling-Root):
      Backlog/{bl_id}-{slug}.md                <- Sibling-Root (Hub)
      Backlog/{bl_id}-{slug}/2_Model/...md     <- Artefakte (Speichen)
      Backlog/{bl_id}-{slug}/_manifest.md      <- Skip-Active-Signal (optional)
    """
    folder_name = f"{bl_id}-{slug}"
    folder = backlog / folder_name

    # Sibling-Root (Hub) NEBEN dem Ordner
    _write(
        backlog / f"{folder_name}.md",
        f"---\ntype: backlog-item\nid: {bl_id}\ntitle: {slug}\nstatus: {status}\n---\n\n# {bl_id}\n",
    )

    if artefacts is None:
        artefacts = {
            "2_Model/{id}_Model.md": "---\ntype: model\nbl-item: {id}\n---\n\n# Model\n",
            "3_Spec/{id}_Spec.md": "---\ntype: spec\nbl-item: {id}\n---\n\n# Spec\n",
            "1_Task/{id}_Task.md": "---\ntype: task\nbl-item: {id}\n---\n\n# Task\n",
        }
    for rel, body in artefacts.items():
        rel_r = rel.format(id=bl_id)
        _write(folder / rel_r, body.format(id=bl_id))

    if with_manifest:
        _write(
            folder / "_manifest.md",
            "---\ntype: manifest\n"
            f"bl_id: {bl_id}\n"
            "A_PIPELINE_STATE:\n"
            f"  phase: {phase}\n"
            f"status: {status}\n"
            "---\n",
        )
    return folder


@pytest.fixture()
def corpus(tmp_path, monkeypatch):
    """2+ DONE-BL-Ordner mit Sibling-Root + gemischt benannten Artefakten (F-3).

    Setzt CLAUDE_VAULT_ROOT auf tmp_path damit resolve_bl_path / Default-Resolver
    den synthetischen Korpus auflöst (keine echte Vault-Berührung).
    """
    backlog = tmp_path / "Backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(tmp_path))

    f1 = _make_bl(backlog, "BL-901", "alpha-feature")
    f2 = _make_bl(
        backlog,
        "BL-902",
        "beta-feature",
        artefacts={
            # gemischt benannte Artefakte (F-3: feste Namen NICHT erwartbar)
            "2_Model/{id}_Model.md": "---\ntype: model\n---\n\n# M\n",
            "Crumbs/batch_1.md": "# batch 1 (kein frontmatter)\n",
            "6_PL/{id}-parking-lot.md": "---\ntype: pl\n---\n\n# PL\n",
        },
    )
    return {
        "vault_root": tmp_path,
        "backlog": backlog,
        "bl1": "BL-901",
        "bl1_slug": "alpha-feature",
        "bl1_folder": f1,
        "bl2": "BL-902",
        "bl2_slug": "beta-feature",
        "bl2_folder": f2,
    }


# Helper-Assertions ----------------------------------------------------------

NAKED_BASENAME_LINK = re.compile(r"\[\[(?!Backlog/)[^\]/]+\]\]")
QUALIFIED_LINK = re.compile(r"\[\[Backlog/BL-\d+-[^\]]+\]\]")


def _root_sibling(corp, which: str) -> Path:
    bl = corp[which]
    slug = corp[f"{which}_slug"]
    return corp["backlog"] / f"{bl}-{slug}.md"


# ===========================================================================
# AK-2a — vault_edge_link(bl_id, file)  (Helper, Single-Source)
# ===========================================================================

class TestAk2aVaultEdgeLink:
    def test_ak2a_sets_artefakte_entry_in_root_sibling(self, corpus):
        """DoD-2a.1: Helper ergaenzt ## Artefakte-Eintrag im Root-Sibling."""
        f = corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md"
        vault_bl_edges.vault_edge_link("BL-901", f)
        root = _root_sibling(corpus, "bl1").read_text(encoding="utf-8")
        assert "## Artefakte" in root
        assert "BL-901_Model" in root

    def test_ak2a_sets_backlink_in_artefact(self, corpus):
        """DoD-2a.1: Helper ergaenzt bl_root-Backlink in der Datei (W4)."""
        f = corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md"
        vault_bl_edges.vault_edge_link("BL-901", f)
        body = f.read_text(encoding="utf-8")
        assert "bl_root:" in body or "> Teil von" in body

    def test_ak2a_returns_true_when_newly_set(self, corpus):
        """DoD-2a.2: Rueckgabe True bei neu gesetzter Edge."""
        f = corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md"
        assert vault_bl_edges.vault_edge_link("BL-901", f) is True

    def test_ak2a_returns_false_when_already_present(self, corpus):
        """DoD-2a.2/2a.3: zweiter Aufruf -> False, idempotent."""
        f = corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md"
        vault_bl_edges.vault_edge_link("BL-901", f)
        assert vault_bl_edges.vault_edge_link("BL-901", f) is False

    def test_ak2a_idempotent_no_diff_second_call(self, corpus):
        """DoD-2a.3: zweiter Aufruf mutiert nichts (byte-stabil)."""
        f = corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md"
        root_p = _root_sibling(corpus, "bl1")
        vault_bl_edges.vault_edge_link("BL-901", f)
        root_after_1 = root_p.read_text(encoding="utf-8")
        file_after_1 = f.read_text(encoding="utf-8")
        vault_bl_edges.vault_edge_link("BL-901", f)
        assert root_p.read_text(encoding="utf-8") == root_after_1
        assert f.read_text(encoding="utf-8") == file_after_1

    def test_ak2a_wikilink_is_folder_qualified(self, corpus):
        """W3/DoD-2a.1: Hub-Eintrag ist ordner-qualifiziert, KEIN nackter Basename."""
        f = corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md"
        vault_bl_edges.vault_edge_link("BL-901", f)
        root = _root_sibling(corpus, "bl1").read_text(encoding="utf-8")
        assert QUALIFIED_LINK.search(root), f"kein qualifizierter Link in:\n{root}"
        assert "[[Backlog/BL-901-alpha-feature/2_Model/BL-901_Model]]" in root

    def test_ak2a_no_naked_basename_link(self, corpus):
        """W3: NIE nackter Basename-Wikilink (Kollisionsschutz)."""
        f = corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md"
        vault_bl_edges.vault_edge_link("BL-901", f)
        root = _root_sibling(corpus, "bl1").read_text(encoding="utf-8")
        body = f.read_text(encoding="utf-8")
        assert not NAKED_BASENAME_LINK.search(root), f"nackter Link in root:\n{root}"
        assert not NAKED_BASENAME_LINK.search(body), f"nackter Link in artefact:\n{body}"

    def test_ak2a_backlink_points_to_sibling_root(self, corpus):
        """W3/W4: Speiche->Hub Backlink zeigt auf Sibling-Pfad (kein Ordner-Inneres)."""
        f = corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md"
        vault_bl_edges.vault_edge_link("BL-901", f)
        body = f.read_text(encoding="utf-8")
        assert "[[Backlog/BL-901-alpha-feature/BL-901-alpha-feature]]" in body

    def test_ak2a_backlink_in_file_without_frontmatter_uses_header(self, corpus):
        """W4: Datei ohne Frontmatter bekommt `> Teil von`-Header-Backlink (tolerant)."""
        f = corpus["bl2_folder"] / "Crumbs" / "batch_1.md"  # kein frontmatter
        vault_bl_edges.vault_edge_link("BL-902", f)
        body = f.read_text(encoding="utf-8")
        assert "> Teil von [[Backlog/BL-902-beta-feature/BL-902-beta-feature]]" in body


# ===========================================================================
# AK-1 — migrate_bl_edges / migrate_all
# ===========================================================================

class TestAk1Migrate:
    def test_ak1_root_has_artefakte_section_after_migrate(self, corpus):
        """DoD-1.1: Root-Sibling hat ## Artefakte mit qualifiziertem Link je Artefakt."""
        vault_bl_edges.migrate_bl_edges(corpus["bl1_folder"])
        root = _root_sibling(corpus, "bl1").read_text(encoding="utf-8")
        assert "## Artefakte" in root
        assert "[[Backlog/BL-901-alpha-feature/2_Model/BL-901_Model]]" in root
        assert "[[Backlog/BL-901-alpha-feature/3_Spec/BL-901_Spec]]" in root
        assert "[[Backlog/BL-901-alpha-feature/1_Task/BL-901_Task]]" in root

    def test_ak1_sibling_self_excluded_from_artefakte(self, corpus):
        """DoD-1.1: Sibling-Root selbst ist KEIN Artefakt-Eintrag (kein Selbst-Link)."""
        vault_bl_edges.migrate_bl_edges(corpus["bl1_folder"])
        root = _root_sibling(corpus, "bl1").read_text(encoding="utf-8")
        # Der Hub verlinkt nicht auf sich selbst als Artefakt-Speiche
        assert "[[Backlog/BL-901-alpha-feature/BL-901-alpha-feature]]" not in root

    def test_ak1_each_artefact_gets_backlink(self, corpus):
        """DoD-1.2: Jede migrierte Artefakt-Datei traegt einen Root-Backlink."""
        vault_bl_edges.migrate_bl_edges(corpus["bl1_folder"])
        model = (corpus["bl1_folder"] / "2_Model" / "BL-901_Model.md").read_text("utf-8")
        spec = (corpus["bl1_folder"] / "3_Spec" / "BL-901_Spec.md").read_text("utf-8")
        for body in (model, spec):
            assert "bl_root:" in body or "> Teil von" in body
            assert "[[Backlog/BL-901-alpha-feature/BL-901-alpha-feature]]" in body

    def test_ak1_all_links_folder_qualified(self, corpus):
        """W3/DoD-1.1: KEIN nackter Basename-Link nach Migration."""
        vault_bl_edges.migrate_bl_edges(corpus["bl1_folder"])
        root = _root_sibling(corpus, "bl1").read_text(encoding="utf-8")
        assert QUALIFIED_LINK.search(root)
        assert not NAKED_BASENAME_LINK.search(root)

    def test_ak1_idempotent_no_double_entries(self, corpus):
        """DoD-1.3: zweiter migrate-Lauf -> keine Doppel-Eintraege, byte-stabil."""
        vault_bl_edges.migrate_bl_edges(corpus["bl1_folder"])
        root_p = _root_sibling(corpus, "bl1")
        after_1 = root_p.read_text(encoding="utf-8")
        vault_bl_edges.migrate_bl_edges(corpus["bl1_folder"])
        after_2 = root_p.read_text(encoding="utf-8")
        assert after_1 == after_2
        # exakt 1 Eintrag pro Artefakt (kein Doppel)
        assert after_2.count("[[Backlog/BL-901-alpha-feature/2_Model/BL-901_Model]]") == 1

    def test_ak1_tolerant_empty_folder_no_crash(self, corpus, tmp_path):
        """DoD-1.4: leerer/artefaktloser Ordner -> Skip, kein Crash."""
        empty_folder = corpus["backlog"] / "BL-903-empty"
        empty_folder.mkdir(parents=True, exist_ok=True)
        _write(corpus["backlog"] / "BL-903-empty.md",
               "---\nid: BL-903\nstatus: DONE\n---\n# empty\n")
        # darf nicht werfen
        vault_bl_edges.migrate_bl_edges(empty_folder)

    def test_ak1_tolerant_missing_frontmatter_uses_header(self, corpus):
        """DoD-1.4/W4: Artefakt ohne Frontmatter -> Header-Backlink, kein Crash."""
        vault_bl_edges.migrate_bl_edges(corpus["bl2_folder"])
        batch = (corpus["bl2_folder"] / "Crumbs" / "batch_1.md").read_text("utf-8")
        assert "> Teil von [[Backlog/BL-902-beta-feature/BL-902-beta-feature]]" in batch

    def test_ak1_migrate_all_processes_multiple_bls(self, corpus):
        """DoD-1.1 (Korpus): migrate_all verschaltet >=2 BL-Ordner."""
        vault_bl_edges.migrate_all(corpus["backlog"])
        r1 = _root_sibling(corpus, "bl1").read_text("utf-8")
        r2 = _root_sibling(corpus, "bl2").read_text("utf-8")
        assert "## Artefakte" in r1
        assert "## Artefakte" in r2
        assert "[[Backlog/BL-902-beta-feature/2_Model/BL-902_Model]]" in r2

    def test_ak1_skip_active_lane_not_mutated(self, corpus, monkeypatch):
        """DoD-1.5: aktive Lane (phase != DONE / status != DONE) bleibt unveraendert (F-5)."""
        backlog = corpus["backlog"]
        active_folder = _make_bl(
            backlog, "BL-904", "active-feature",
            status="IN_PROGRESS", phase="STARTED",
        )
        active_root = backlog / "BL-904-active-feature.md"
        before = active_root.read_text(encoding="utf-8")
        vault_bl_edges.migrate_all(backlog, skip_active=True)
        after = active_root.read_text(encoding="utf-8")
        assert after == before, "aktive Lane darf NICHT mutiert werden"
        assert "## Artefakte" not in after

    def test_ak1_skip_active_false_processes_active(self, corpus):
        """DoD-1.5: skip_active=False verarbeitet auch aktive Lanes (Opt-out)."""
        backlog = corpus["backlog"]
        _make_bl(backlog, "BL-905", "force-feature",
                 status="IN_PROGRESS", phase="STARTED")
        force_root = backlog / "BL-905-force-feature.md"
        vault_bl_edges.migrate_all(backlog, skip_active=False)
        after = force_root.read_text(encoding="utf-8")
        assert "## Artefakte" in after

    def test_ak1_migrate_uses_helper_single_source(self, corpus, monkeypatch):
        """DoD-2a.4: migrate ruft den Helper vault_edge_link pro Datei (Single-Source)."""
        calls = []
        real = vault_bl_edges.vault_edge_link

        def spy(bl_id, file, *a, **kw):
            calls.append((bl_id, Path(file).name))
            return real(bl_id, file, *a, **kw)

        monkeypatch.setattr(vault_bl_edges, "vault_edge_link", spy)
        vault_bl_edges.migrate_bl_edges(corpus["bl1_folder"])
        assert calls, "migrate hat vault_edge_link NICHT aufgerufen (kein Single-Source)"
        names = {n for _, n in calls}
        assert "BL-901_Model.md" in names
        assert "BL-901_Spec.md" in names
