#!/usr/bin/env python3
"""Tests fuer truth_edge_backref.py (BL-451 AC-2a: praezise referenced_by-Inversion via edges).

RED: truth_edge_backref existiert noch nicht — alle Tests MUSS fehlschlagen mit ModuleNotFoundError.

Vertrag:
1. build_edge_backref_index(root): scannt type==truth, invertiert edges[].ziel -> {by, kind:"truth_edge"}.
   - Dangling (ziel-id nicht im id_set) werden ausgelassen.
   - Self-Edges werden ausgelassen.
   - Dedup pro Ziel auf (by, kind).
2. materialize_edges(root, apply=False, backup_dir=None): surgischer Write via _build_new_content.
   - Dry-run (apply=False): updated==0, would_update>0.
   - apply=True: schreibt referenced_by (by, kind:"truth_edge") ins Frontmatter.
   - Idempotent: zweiter Lauf updated==0.
   - backup_dir + apply: backed_up==updated.
   - Text-Block byte-identisch nach Apply.
"""
from __future__ import annotations

import pytest

# RED: dieses Modul existiert noch NICHT -> ModuleNotFoundError erwartet.
from truth_edge_backref import build_edge_backref_index, materialize_edges  # noqa: F401


# ---------------------------------------------------------------------------
# Hilfs-Funktionen
# ---------------------------------------------------------------------------

def _write_truth_atom(
    path,
    full_id: str,
    local_id: str,
    edges: list[dict] | None = None,
    text_block: str = "Atom-Text.",
    keywords: list[str] | None = None,
) -> None:
    """Schreibt ein truth-Atom mit YAML-Frontmatter.

    edges: Liste von {rel, ziel}-Dicts (ziel = volle id).
    text_block: einfacher oder mehrzeiliger Text (als YAML-Literal-Block |).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Edges-Sektion aufbauen
    edges_yaml = ""
    if edges:
        edges_yaml = "edges:\n"
        for e in edges:
            rel = e.get("rel", "references")
            ziel = e.get("ziel", "")
            edges_yaml += f"  - rel: {rel}\n"
            edges_yaml += f"    ziel: {ziel}\n"

    # Keywords-Sektion aufbauen
    keywords_yaml = ""
    if keywords:
        keywords_yaml = "keywords:\n"
        for k in keywords:
            keywords_yaml += f"  - {k}\n"

    # Mehrzeiligen text-Block als YAML-Literal-Block | kodieren
    indented_text = text_block.replace("\n", "\n  ")
    content = (
        "---\n"
        "type: truth\n"
        f"id: {full_id}\n"
        f"local_id: {local_id}\n"
        f"text: |\n"
        f"  {indented_text}\n"
        f"{edges_yaml}"
        f"{keywords_yaml}"
        "---\n"
        f"\n### {local_id}\n"
    )
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: Index invertiert praezise
# ---------------------------------------------------------------------------

class TestIndexInvertsPrecise:
    def test_index_inverts_precise(self, tmp_path):
        """3 Atome A, B, C — A und C zeigen auf B.
        Index["NS.B1"] enthaelt beide {by:NS.A1} + {by:NS.C1}.
        Index hat KEINEN Eintrag fuer NS.A1 oder NS.C1 (niemand zeigt drauf)."""
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[{"rel": "uses", "ziel": "NS.B1"}],
        )
        _write_truth_atom(
            tmp_path / "B.md",
            full_id="NS.B1",
            local_id="B1",
            edges=[],  # B zeigt auf niemanden
        )
        _write_truth_atom(
            tmp_path / "C.md",
            full_id="NS.C1",
            local_id="C1",
            edges=[{"rel": "references", "ziel": "NS.B1"}],
        )

        index = build_edge_backref_index(tmp_path)

        # B muss zwei Rueck-Refs haben
        assert "NS.B1" in index, "NS.B1 fehlt im Index"
        entries = index["NS.B1"]
        bys = {e["by"] for e in entries}
        assert "NS.A1" in bys, "NS.A1 fehlt als Rueck-Ref auf NS.B1"
        assert "NS.C1" in bys, "NS.C1 fehlt als Rueck-Ref auf NS.B1"
        # kind muss truth_edge sein
        for e in entries:
            assert e["kind"] == "truth_edge", f"falscher kind: {e['kind']}"

        # A und C sollen NICHT im Index stehen (niemand zeigt drauf)
        assert "NS.A1" not in index, "NS.A1 darf nicht im Index stehen (kein Rueck-Ref)"
        assert "NS.C1" not in index, "NS.C1 darf nicht im Index stehen (kein Rueck-Ref)"


# ---------------------------------------------------------------------------
# Test 2: Dangling-Edges werden ausgelassen
# ---------------------------------------------------------------------------

class TestIndexSkipsDangling:
    def test_index_skips_dangling(self, tmp_path):
        """Atom A hat edge auf NS.NICHTDA (kein Atom mit dieser id).
        NS.NICHTDA darf NICHT im Index erscheinen."""
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[{"rel": "uses", "ziel": "NS.NICHTDA"}],
        )

        index = build_edge_backref_index(tmp_path)

        assert "NS.NICHTDA" not in index, "Dangling-Ziel NS.NICHTDA darf nicht im Index stehen"


# ---------------------------------------------------------------------------
# Test 3: Self-Edges werden ausgelassen
# ---------------------------------------------------------------------------

class TestIndexSkipsSelfEdge:
    def test_index_skips_self_edge(self, tmp_path):
        """Atom A(id=NS.A1) hat edge auf sich selbst (ziel:NS.A1).
        Kein Self-Backref — NS.A1 darf nicht mit by==NS.A1 im Index stehen."""
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[{"rel": "self_ref", "ziel": "NS.A1"}],
        )

        index = build_edge_backref_index(tmp_path)

        # Entweder gar nicht im Index, oder ohne by==NS.A1
        if "NS.A1" in index:
            self_entries = [e for e in index["NS.A1"] if e["by"] == "NS.A1"]
            assert len(self_entries) == 0, "Self-Edge darf keinen Backref erzeugen"


# ---------------------------------------------------------------------------
# Test 4: Dedup bei doppelten Edges
# ---------------------------------------------------------------------------

class TestIndexDedups:
    def test_index_dedups(self, tmp_path):
        """Atom A hat ZWEI edges beide mit ziel:NS.B1.
        index["NS.B1"] enthaelt {by:NS.A1, kind:truth_edge} nur EINMAL."""
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[
                {"rel": "uses", "ziel": "NS.B1"},
                {"rel": "references", "ziel": "NS.B1"},
            ],
        )
        _write_truth_atom(
            tmp_path / "B.md",
            full_id="NS.B1",
            local_id="B1",
            edges=[],
        )

        index = build_edge_backref_index(tmp_path)

        assert "NS.B1" in index
        a1_entries = [e for e in index["NS.B1"] if e["by"] == "NS.A1" and e["kind"] == "truth_edge"]
        assert len(a1_entries) == 1, f"Dedup fehlgeschlagen: {a1_entries}"


# ---------------------------------------------------------------------------
# Test 5: materialize_edges schreibt referenced_by (apply=True)
# ---------------------------------------------------------------------------

class TestMaterializeWritesReferencedBy:
    def test_materialize_writes_referenced_by(self, tmp_path):
        """Nach materialize_edges(root, apply=True) hat B's Datei einen
        referenced_by-Block mit by:NS.A1 und by:NS.C1."""
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[{"rel": "uses", "ziel": "NS.B1"}],
        )
        _write_truth_atom(
            tmp_path / "B.md",
            full_id="NS.B1",
            local_id="B1",
            edges=[],
        )
        _write_truth_atom(
            tmp_path / "C.md",
            full_id="NS.C1",
            local_id="C1",
            edges=[{"rel": "references", "ziel": "NS.B1"}],
        )

        result = materialize_edges(tmp_path, apply=True)

        b_content = (tmp_path / "B.md").read_text(encoding="utf-8")

        assert "referenced_by" in b_content, "referenced_by-Block fehlt in B"
        assert "NS.A1" in b_content, "by: NS.A1 fehlt in referenced_by"
        assert "NS.C1" in b_content, "by: NS.C1 fehlt in referenced_by"
        assert result["updated"] >= 1


# ---------------------------------------------------------------------------
# Test 6: Dry-run schreibt NICHTS
# ---------------------------------------------------------------------------

class TestMaterializeDryRunNoWrite:
    def test_materialize_dry_run_no_write(self, tmp_path):
        """materialize_edges(root, apply=False) aendert keine Datei.
        updated==0, would_update>0."""
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[{"rel": "uses", "ziel": "NS.B1"}],
        )
        _write_truth_atom(
            tmp_path / "B.md",
            full_id="NS.B1",
            local_id="B1",
            edges=[],
        )

        b_before = (tmp_path / "B.md").read_bytes()
        result = materialize_edges(tmp_path, apply=False)
        b_after = (tmp_path / "B.md").read_bytes()

        assert b_before == b_after, "Dry-run hat B.md veraendert (verboten)"
        assert result["updated"] == 0, f"updated={result['updated']} aber muss 0 sein"
        assert result["would_update"] > 0, "would_update muss >0 sein (B hat Refs)"


# ---------------------------------------------------------------------------
# Test 7: Idempotenz
# ---------------------------------------------------------------------------

class TestMaterializeIdempotent:
    def test_materialize_idempotent(self, tmp_path):
        """materialize_edges(apply=True) zweimal — zweiter Lauf updated==0."""
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[{"rel": "uses", "ziel": "NS.B1"}],
        )
        _write_truth_atom(
            tmp_path / "B.md",
            full_id="NS.B1",
            local_id="B1",
            edges=[],
        )

        first = materialize_edges(tmp_path, apply=True)
        assert first["updated"] >= 1, "Erster Lauf soll mindestens 1 Datei aendern"

        second = materialize_edges(tmp_path, apply=True)
        assert second["updated"] == 0, "Zweiter Lauf muss 0 Updates haben (Idempotenz)"


# ---------------------------------------------------------------------------
# Test 8: Mehrzeiliger text-Block bleibt unveraendert
# ---------------------------------------------------------------------------

class TestMaterializePreservesMultilineText:
    def test_materialize_preserves_multiline_text(self, tmp_path):
        """B hat einen mehrzeiligen text:-Block. Nach apply ist der text-Block
        UNVERAENDERT — nur referenced_by wurde hinzugefuegt."""
        multiline = (
            "Erste Zeile des Atoms.\n"
            "Zweite Zeile mit Sonderzeichen: ae oe ue.\n"
            "Dritte Zeile: Ende der Beschreibung."
        )
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[{"rel": "uses", "ziel": "NS.B1"}],
        )
        _write_truth_atom(
            tmp_path / "B.md",
            full_id="NS.B1",
            local_id="B1",
            text_block=multiline,
            edges=[],
        )

        b_before = (tmp_path / "B.md").read_text(encoding="utf-8")
        materialize_edges(tmp_path, apply=True)
        b_after = (tmp_path / "B.md").read_text(encoding="utf-8")

        # referenced_by muss hinzugekommen sein
        assert "referenced_by" in b_after, "referenced_by fehlt nach Apply"

        # Alle Textzeilen muessen erhalten sein
        assert "Erste Zeile des Atoms." in b_after
        assert "Zweite Zeile mit Sonderzeichen: ae oe ue." in b_after
        assert "Dritte Zeile: Ende der Beschreibung." in b_after

        # type, id, local_id unveraendert
        assert "type: truth" in b_after
        assert "id: NS.B1" in b_after
        assert "local_id: B1" in b_after


# ---------------------------------------------------------------------------
# Test 9: Backup
# ---------------------------------------------------------------------------

class TestMaterializeBackup:
    def test_materialize_backup(self, tmp_path):
        """backup_dir + apply: zu aendernde Dateien werden nach backup_dir kopiert.
        backed_up == updated."""
        _write_truth_atom(
            tmp_path / "A.md",
            full_id="NS.A1",
            local_id="A1",
            edges=[{"rel": "uses", "ziel": "NS.B1"}],
        )
        _write_truth_atom(
            tmp_path / "B.md",
            full_id="NS.B1",
            local_id="B1",
            edges=[],
        )

        b_original = (tmp_path / "B.md").read_bytes()
        backup_dir = tmp_path / "backup"

        result = materialize_edges(tmp_path, apply=True, backup_dir=backup_dir)

        assert result["backed_up"] == result["updated"], (
            f"backed_up={result['backed_up']} != updated={result['updated']}"
        )
        assert result["backed_up"] >= 1, "backed_up muss >=1 sein"

        assert backup_dir.exists(), "backup_dir wurde nicht erstellt"
        backup_files = list(backup_dir.glob("*.md"))
        assert len(backup_files) >= 1, "Keine Backup-Datei in backup_dir"

        # Backup enthaelt originalen Inhalt (vor referenced_by-Einf.)
        assert any(f.read_bytes() == b_original for f in backup_files), (
            "Backup-Kopie enthaelt nicht den originalen B.md-Inhalt"
        )
