#!/usr/bin/env python3
"""RED tests fuer view_backref_index.py (BL-491 AC-2, ARTIFACT 2).

STRIKT TDD RED: das Modul `view_backref_index` existiert noch NICHT (und es importiert
`view_id_convention`, das ebenfalls noch fehlt). Der Import am Modul-Kopf MUSS
fehlschlagen -> Collection-Error = korrektes ROT. Ein SEPARATER GREEN-Worker
implementiert das Modul spaeter (INV-BUILD-GRAIN: RED-Worker != GREEN-Worker).

Vertrag (siehe bl491_ac2_spec.md ARTIFACT 2):
  build_view_backref_index(vault: Path) -> dict mit keys:
    vault(str), backrefs({atom_rel: [{by, kind:"view_source", view_rel}, ...]}),
    view_count(int), edge_count(int), atom_count(int),
    unresolved([{view_rel, atom_rel} fuer atom-Pfade ohne Datei unter vault]).
  Pro (view, atom_rel in source_atoms):
    vid = resolve_view_id(fm, view_rel)
    backrefs[atom_rel].append({"by": vid, "kind": "view_source", "view_rel": view_rel})
  Dedupe identischer (by, atom_rel)-Paare. VIEWS-ONLY: Atom-Dateien werden NIE
  geoeffnet/geschrieben (nur ge-stat-et fuer unresolved).
  main(argv=None) -> int  (argparse --vault REQUIRED, --out <json> optional). exit 0.

Fixtures bauen echte view-node-Pfade (so dass view_node_predicate.is_view_node True
liefert): ein Model `Backlog/<bl>/2_Model/<name>_Model.md` (MIT id) und ein parking-lot
`Backlog/<bl>/6_PL/<bl>-parking-lot.md` (OHNE id). source_atoms in der real-vault
unindented block-sequence-Form (`source_atoms:\\n- a\\n- b`), die der YAML-first-Parser
(vgl. view_source_atoms_materialize) akzeptiert.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# RED: weder view_backref_index noch dessen Dependency view_id_convention existieren
# -> ModuleNotFoundError bei Collection (= ROT).
import view_backref_index
from view_backref_index import build_view_backref_index, main  # noqa: F401


# ---------------------------------------------------------------------------
# Konstanten — Pfade des Mini-Vaults
# ---------------------------------------------------------------------------

# Geteiltes Atom, das BEIDE Views in source_atoms nennen.
SHARED_ATOM_REL = "Backlog/BL-X/2_Model/truths/Shared.md"

# View 1: Model MIT Frontmatter-id (view-node via 2_Model/<name>_Model.md).
MODEL_VIEW_REL = "Backlog/BL-X/2_Model/X_Model.md"
MODEL_VIEW_ID = "VIEW.XModel"

# View 2: parking-lot OHNE id (view-node via 6_PL/<name>.md).
PARKING_VIEW_REL = "Backlog/BL-Y/6_PL/BL-Y-parking-lot.md"
# Derived id (hardcoded, RED-safe — kein Import-Dependency auf view_id_convention):
# Konvention "view::" + vault-rel posix path. Siehe bl491_ac2_spec.md ARTIFACT 1.
PARKING_DERIVED_ID = "view::Backlog/BL-Y/6_PL/BL-Y-parking-lot.md"


# ---------------------------------------------------------------------------
# Datei-Builder (Frontmatter direkt geschrieben: kontrollierte unindented
# block-sequence-Form fuer source_atoms — der real-vault-Stil).
# ---------------------------------------------------------------------------

def _write_view(root, relpath, *, view_id=None, source_atoms=None, bl="BL-X", body=None):
    """Schreibt eine View. `view_id=None` -> KEIN id-Feld (id-lose View).
    source_atoms als unindented YAML block-sequence (Spalte 0)."""
    lines = ["---"]
    if view_id is not None:
        lines.append(f"id: {view_id}")
    lines.append("tags:")
    lines.append("- type/view")
    lines.append(f"bl: {bl}")
    if source_atoms is not None:
        lines.append("source_atoms:")
        for s in source_atoms:
            lines.append(f"- {s}")
    lines.append("---")
    if body is None:
        body = "\n# View body\n\nalpha beta gamma.\n"
    content = "\n".join(lines) + body

    path = Path(root) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_atom(root, relpath, *, text="fake atom body"):
    """Schreibt eine FAKE Atom-Datei (Inhalt irrelevant). Liegt unter 2_Model/truths/
    -> is_view_node == False (kein View-Node)."""
    path = Path(root) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntype: truth\nid: NS.Shared\n---\n\n{text}\n", encoding="utf-8")
    return path


def _snapshot_files(root):
    """{abs_path_str: mtime_ns} fuer ALLE Dateien unter root (rekursiv)."""
    snap = {}
    for p in Path(root).rglob("*"):
        if p.is_file():
            snap[str(p)] = p.stat().st_mtime_ns
    return snap


# ---------------------------------------------------------------------------
# ARTIFACT-2-Kern: zwei Views (id-bearing + id-less) -> dasselbe Atom
# ---------------------------------------------------------------------------

class TestBothByForSharedAtom:
    def test_shared_atom_maps_to_both_bys(self, tmp_path):
        """Das geteilte Atom mappt auf BEIDE `by`s: die Frontmatter-id der Model-View
        UND die view::-derived id der id-losen parking-lot-View; kind == 'view_source'."""
        _write_view(tmp_path, MODEL_VIEW_REL, view_id=MODEL_VIEW_ID,
                    source_atoms=[SHARED_ATOM_REL], bl="BL-X")
        _write_view(tmp_path, PARKING_VIEW_REL, view_id=None,
                    source_atoms=[SHARED_ATOM_REL], bl="BL-Y")
        _write_atom(tmp_path, SHARED_ATOM_REL)

        result = build_view_backref_index(tmp_path)

        backrefs = result["backrefs"]
        assert SHARED_ATOM_REL in backrefs, (
            f"geteiltes Atom fehlt in backrefs: {list(backrefs)}"
        )
        entries = backrefs[SHARED_ATOM_REL]

        # Jeder Eintrag ist ein view_source-Backref mit by + view_rel.
        for e in entries:
            assert e["kind"] == "view_source", f"kind muss view_source sein: {e}"
            assert "by" in e and "view_rel" in e, f"Eintrag unvollstaendig: {e}"

        bys = {e["by"] for e in entries}
        assert MODEL_VIEW_ID in bys, f"Frontmatter-id-by fehlt: {bys}"
        assert PARKING_DERIVED_ID in bys, f"derived-id-by fehlt: {bys}"

        # view_rel zeigt korrekt auf die jeweils erzeugende View.
        by_to_view = {e["by"]: e["view_rel"] for e in entries}
        assert by_to_view[MODEL_VIEW_ID] == MODEL_VIEW_REL
        assert by_to_view[PARKING_DERIVED_ID] == PARKING_VIEW_REL

    def test_counts_present(self, tmp_path):
        """view_count/edge_count/atom_count + vault sind im Ergebnis."""
        _write_view(tmp_path, MODEL_VIEW_REL, view_id=MODEL_VIEW_ID,
                    source_atoms=[SHARED_ATOM_REL], bl="BL-X")
        _write_view(tmp_path, PARKING_VIEW_REL, view_id=None,
                    source_atoms=[SHARED_ATOM_REL], bl="BL-Y")
        _write_atom(tmp_path, SHARED_ATOM_REL)

        result = build_view_backref_index(tmp_path)

        for key in ("vault", "backrefs", "view_count", "edge_count", "atom_count", "unresolved"):
            assert key in result, f"Pflicht-Key {key} fehlt: {list(result)}"
        assert result["view_count"] >= 2
        assert result["edge_count"] >= 2  # zwei (view, atom)-Kanten
        assert result["atom_count"] >= 1


# ---------------------------------------------------------------------------
# Dedupe auf identischem (by, atom)
# ---------------------------------------------------------------------------

class TestDedupe:
    def test_repeated_identical_by_atom_deduped(self, tmp_path):
        """Eine View, die DASSELBE Atom zweimal in source_atoms listet, erzeugt
        nur EINEN Backref-Eintrag fuer (by, atom)."""
        view_rel = "Backlog/BL-D/2_Model/D_Model.md"
        _write_view(tmp_path, view_rel, view_id="VIEW.D",
                    source_atoms=[SHARED_ATOM_REL, SHARED_ATOM_REL], bl="BL-D")
        _write_atom(tmp_path, SHARED_ATOM_REL)

        result = build_view_backref_index(tmp_path)
        entries = result["backrefs"][SHARED_ATOM_REL]
        d_entries = [e for e in entries if e["by"] == "VIEW.D"]
        assert len(d_entries) == 1, f"Dedupe verletzt — VIEW.D doppelt: {entries}"


# ---------------------------------------------------------------------------
# unresolved: Atom-Pfad existiert nicht auf Disk
# ---------------------------------------------------------------------------

class TestUnresolved:
    def test_missing_atom_listed_unresolved(self, tmp_path):
        """source_atoms verweist auf eine NICHT-existente Atom-Datei
        -> unresolved listet {view_rel, atom_rel}."""
        ghost = "Backlog/BL-X/2_Model/truths/Ghost.md"
        _write_view(tmp_path, MODEL_VIEW_REL, view_id=MODEL_VIEW_ID,
                    source_atoms=[ghost], bl="BL-X")
        # GHOST wird NICHT geschrieben.

        result = build_view_backref_index(tmp_path)

        assert any(
            u["atom_rel"] == ghost and u["view_rel"] == MODEL_VIEW_REL
            for u in result["unresolved"]
        ), f"Ghost-Atom nicht als unresolved gelistet: {result['unresolved']}"


# ---------------------------------------------------------------------------
# Eine View ohne source_atoms traegt nichts bei
# ---------------------------------------------------------------------------

class TestNoSourceAtomsContributesNothing:
    def test_view_without_source_atoms_contributes_nothing(self, tmp_path):
        """Eine view-node OHNE source_atoms erzeugt keine Backrefs/Kanten/unresolved."""
        nosrc_rel = "Backlog/BL-Z/6_PL/BL-Z-parking-lot.md"
        _write_view(tmp_path, nosrc_rel, view_id=None, source_atoms=None, bl="BL-Z")

        result = build_view_backref_index(tmp_path)

        assert result["backrefs"] == {}, f"backrefs sollten leer sein: {result['backrefs']}"
        assert result["edge_count"] == 0
        assert result["unresolved"] == []


# ---------------------------------------------------------------------------
# Atom-Dateien werden NIE veraendert (mtime stabil, keine Datei erzeugt)
# ---------------------------------------------------------------------------

class TestAtomFilesNeverModified:
    def test_atom_mtime_unchanged_and_no_file_created(self, tmp_path):
        """VIEWS-ONLY-FENCE: build_view_backref_index oeffnet/schreibt KEINE Atom-Datei.
        mtime_ns des Atoms vorher == nachher; keine neue Datei im Vault."""
        _write_view(tmp_path, MODEL_VIEW_REL, view_id=MODEL_VIEW_ID,
                    source_atoms=[SHARED_ATOM_REL], bl="BL-X")
        _write_view(tmp_path, PARKING_VIEW_REL, view_id=None,
                    source_atoms=[SHARED_ATOM_REL], bl="BL-Y")
        atom_path = _write_atom(tmp_path, SHARED_ATOM_REL)

        atom_mtime_before = os.stat(atom_path).st_mtime_ns
        files_before = _snapshot_files(tmp_path)

        build_view_backref_index(tmp_path)

        assert os.stat(atom_path).st_mtime_ns == atom_mtime_before, (
            "Atom-Datei wurde beruehrt (mtime aenderte sich)"
        )
        files_after = _snapshot_files(tmp_path)
        assert set(files_after) == set(files_before), (
            f"Es wurden Dateien erzeugt/entfernt: "
            f"neu={set(files_after) - set(files_before)} "
            f"weg={set(files_before) - set(files_after)}"
        )
        # explizit: das Atom selbst unveraendert (mtime in der Snapshot-Map)
        assert files_after[str(atom_path)] == files_before[str(atom_path)]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCli:
    def test_main_writes_json_and_returns_zero(self, tmp_path):
        """main(--vault --out) liefert 0 und schreibt das Index-JSON."""
        _write_view(tmp_path, MODEL_VIEW_REL, view_id=MODEL_VIEW_ID,
                    source_atoms=[SHARED_ATOM_REL], bl="BL-X")
        _write_view(tmp_path, PARKING_VIEW_REL, view_id=None,
                    source_atoms=[SHARED_ATOM_REL], bl="BL-Y")
        _write_atom(tmp_path, SHARED_ATOM_REL)

        json_path = tmp_path / "view_backref_index.json"
        rc = main(["--vault", str(tmp_path), "--out", str(json_path)])

        assert rc == 0
        assert json_path.exists(), "--out muss das Index-JSON schreiben"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert "backrefs" in data
        assert SHARED_ATOM_REL in data["backrefs"]
