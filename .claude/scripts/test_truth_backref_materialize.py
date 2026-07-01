#!/usr/bin/env python3
"""Tests fuer truth_backref_materialize.py (BL-309 P1: referenced_by-Inversion, Materializer).

Vertrag:
1. Dry-run (apply=False): scannt + plant, schreibt NICHTS (would_update>0, updated==0).
2. Apply (apply=True): schreibt referenced_by ins Frontmatter (updated==would_update).
3. SURGICAL PATCH: nur referenced_by wird eingefuegt/ersetzt; mehrzeiliger text:-Block UNVERAENDERT.
4. Idempotenz: zweiter apply-Lauf aendert nichts mehr (updated==0).
5. Backup: bei apply+backup_dir werden betroffene Atome vorher gesichert (backed_up==updated).
"""
from __future__ import annotations

import pytest

# Dieser Import MUSS fehlschlagen (RED) — das Modul existiert noch nicht.
from truth_backref_materialize import materialize  # noqa: F401


# ---------------------------------------------------------------------------
# Hilfs-Fixtures
# ---------------------------------------------------------------------------

def _write_atom(path, local_id: str, text_block: str, extra_fields: str = "") -> None:
    """Schreibt ein minimales truth-Atom mit YAML-Frontmatter und mehrzeiligem text:-Block."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Mehrzeiliger text-Block als YAML-Literal-Block (|)
    content = (
        "---\n"
        "type: truth\n"
        f"local_id: {local_id}\n"
        f"text: |\n"
        f"  {text_block.replace(chr(10), chr(10) + '  ')}\n"
        f"{extra_fields}"
        "---\n"
        f"\n### {local_id}\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_parking_lot(path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: Dry-run schreibt NICHTS
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_returns_would_update_positive(self, tmp_path):
        """Dry-run (apply=False): would_update>0, updated==0."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine Wahrheit ueber das System.")

        pl_path = tmp_path / "6_PL" / "BL-test-parking-lot.md"
        _write_parking_lot(pl_path, "Parking-Lot deckt W01 ab.")

        result = materialize(tmp_path, apply=False)

        assert result["scanned"] >= 1
        assert result["would_update"] >= 1
        assert result["updated"] == 0

    def test_dry_run_leaves_files_byte_identical(self, tmp_path):
        """Dry-run darf Atom-Dateien NICHT veraendern (byte-identisch)."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine Wahrheit ueber das System.")

        pl_path = tmp_path / "6_PL" / "BL-test-parking-lot.md"
        _write_parking_lot(pl_path, "Parking-Lot deckt W01 ab.")

        before = atom_path.read_bytes()
        materialize(tmp_path, apply=False)
        after = atom_path.read_bytes()

        assert before == after, "Dry-run darf Atom-Datei NICHT modifizieren"

    def test_dry_run_no_refs_returns_zero_would_update(self, tmp_path):
        """Ohne Referenzen: would_update==0."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine Wahrheit ohne externe Referenzen.")
        # kein Parking-Lot -> kein Rueck-Ref

        result = materialize(tmp_path, apply=False)

        assert result["would_update"] == 0
        assert result["updated"] == 0


# ---------------------------------------------------------------------------
# Test 2: Apply schreibt referenced_by
# ---------------------------------------------------------------------------

class TestApply:
    def test_apply_updates_count_matches_would_update(self, tmp_path):
        """Apply: updated == would_update."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine Wahrheit ueber das System.")

        pl_path = tmp_path / "6_PL" / "BL-test-parking-lot.md"
        _write_parking_lot(pl_path, "Parking-Lot deckt W01 ab.")

        dry = materialize(tmp_path, apply=False)
        result = materialize(tmp_path, apply=True)

        assert result["updated"] == dry["would_update"]
        assert result["updated"] >= 1

    def test_apply_inserts_referenced_by_field(self, tmp_path):
        """Nach apply hat das Atom ein referenced_by:-Feld in der YAML-Frontmatter."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine Wahrheit ueber das System.")

        pl_path = tmp_path / "6_PL" / "BL-test-parking-lot.md"
        _write_parking_lot(pl_path, "Parking-Lot deckt W01 ab.")

        materialize(tmp_path, apply=True)

        content = atom_path.read_text(encoding="utf-8")
        assert "referenced_by" in content, "referenced_by fehlt im Frontmatter"


# ---------------------------------------------------------------------------
# Test 3: SURGICAL PATCH — text-Block bleibt byte-identisch
# ---------------------------------------------------------------------------

class TestSurgicalPatch:
    def test_multiline_text_block_preserved(self, tmp_path):
        """Apply darf NUR referenced_by einfuegen. Der mehrzeilige text:-Block muss
        byte-identisch erhalten bleiben. Alle anderen Felder ebenfalls."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W02.md"

        # Atom mit bewusst mehrzeiligem text-Block (mehrere Zeilen, Sonderzeichen)
        multiline_text = "Zeile eins: Das System muss stabil sein.\nZeile zwei: Es darf nie ausfallen.\nZeile drei: Verfuegbarkeit > 99.9%."
        _write_atom(atom_path, "W02", multiline_text)

        pl_path = tmp_path / "6_PL" / "BL-test-parking-lot.md"
        _write_parking_lot(pl_path, "PL referenziert W02 als kritische Anforderung.")

        before_content = atom_path.read_text(encoding="utf-8")
        # Extrahiere den text:-Block vor dem Apply
        before_lines = before_content.split("\n")

        materialize(tmp_path, apply=True)

        after_content = atom_path.read_text(encoding="utf-8")

        # referenced_by muss hinzugekommen sein
        assert "referenced_by" in after_content

        # Der text-Inhalt muss erhalten sein
        assert "Zeile eins: Das System muss stabil sein." in after_content
        assert "Zeile zwei: Es darf nie ausfallen." in after_content
        assert "Zeile drei: Verfuegbarkeit > 99.9%." in after_content

        # type, local_id, id muessen unveraendert sein
        assert "type: truth" in after_content
        assert "local_id: W02" in after_content

    def test_only_referenced_by_changed(self, tmp_path):
        """Prueft, dass apply AUSSCHLIESSLICH das referenced_by-Feld hinzufuegt,
        alle anderen Frontmatter-Zeilen byte-identisch bleiben."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W03.md"

        # Atom mit mehreren expliziten Feldern
        atom_path.parent.mkdir(parents=True, exist_ok=True)
        original_frontmatter = (
            "---\n"
            "type: truth\n"
            "id: BL-test.W03\n"
            "local_id: W03\n"
            "typ: FESTSTELLUNG\n"
            "status: UNGRADED\n"
            "text: |\n"
            "  Erste Zeile des Texts.\n"
            "  Zweite Zeile mit Sonderzeichen: aeoeue.\n"
            "  Dritte Zeile: Ende.\n"
            "keywords:\n"
            "  - system\n"
            "  - stabilitaet\n"
            "---\n"
            "\n### W03\n"
        )
        atom_path.write_text(original_frontmatter, encoding="utf-8")

        pl_path = tmp_path / "6_PL" / "pl.md"
        _write_parking_lot(pl_path, "PL deckt W03 ab.")

        materialize(tmp_path, apply=True)

        after = atom_path.read_text(encoding="utf-8")

        # Alle Original-Felder muessen erhalten sein
        assert "type: truth" in after
        assert "id: BL-test.W03" in after
        assert "local_id: W03" in after
        assert "typ: FESTSTELLUNG" in after
        assert "status: UNGRADED" in after
        assert "Erste Zeile des Texts." in after
        assert "Zweite Zeile mit Sonderzeichen: aeoeue." in after
        assert "Dritte Zeile: Ende." in after
        assert "keywords:" in after
        assert "- system" in after
        assert "- stabilitaet" in after

        # referenced_by NEU hinzugekommen
        assert "referenced_by" in after


# ---------------------------------------------------------------------------
# Test 4: Idempotenz
# ---------------------------------------------------------------------------

class TestIdempotenz:
    def test_second_apply_returns_zero_updated(self, tmp_path):
        """Zweiter apply-Lauf: updated==0 (keine Aenderung mehr noetig)."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine idempotente Wahrheit.")

        pl_path = tmp_path / "6_PL" / "pl.md"
        _write_parking_lot(pl_path, "PL deckt W01 ab.")

        first = materialize(tmp_path, apply=True)
        assert first["updated"] >= 1

        second = materialize(tmp_path, apply=True)
        assert second["updated"] == 0, "Zweiter apply-Lauf darf nichts aendern (Idempotenz)"

    def test_second_apply_file_byte_identical(self, tmp_path):
        """Nach zweitem apply: Atom-Datei byte-identisch zum Stand nach erstem apply."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine idempotente Wahrheit.")

        pl_path = tmp_path / "6_PL" / "pl.md"
        _write_parking_lot(pl_path, "PL deckt W01 ab.")

        materialize(tmp_path, apply=True)
        after_first = atom_path.read_bytes()

        materialize(tmp_path, apply=True)
        after_second = atom_path.read_bytes()

        assert after_first == after_second, "Datei-Inhalt darf sich beim zweiten Apply nicht aendern"


# ---------------------------------------------------------------------------
# Test 5: Backup
# ---------------------------------------------------------------------------

class TestBackup:
    def test_backup_creates_copies_before_write(self, tmp_path):
        """Apply mit backup_dir: backed_up == updated, Kopien in backup_dir vorhanden."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine gesicherte Wahrheit.")

        pl_path = tmp_path / "6_PL" / "pl.md"
        _write_parking_lot(pl_path, "PL deckt W01 ab.")

        backup_dir = tmp_path / "backup"

        result = materialize(tmp_path, apply=True, backup_dir=backup_dir)

        assert result["backed_up"] == result["updated"], "backed_up muss updated entsprechen"
        assert result["backed_up"] >= 1

        # Backup-Datei muss existieren
        assert backup_dir.exists(), "backup_dir wurde nicht erstellt"
        backup_files = list(backup_dir.glob("*.md"))
        assert len(backup_files) >= 1, "Keine Backup-Datei gefunden"

    def test_backup_contains_original_content(self, tmp_path):
        """Die Backup-Kopie enthaelt den ORIGINALEN Inhalt (vor dem Apply)."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Urspruenglicher Inhalt vor Backup.")

        pl_path = tmp_path / "6_PL" / "pl.md"
        _write_parking_lot(pl_path, "PL deckt W01 ab.")

        original_bytes = atom_path.read_bytes()
        backup_dir = tmp_path / "backup"

        materialize(tmp_path, apply=True, backup_dir=backup_dir)

        # Backup-Kopie muss den originalen Inhalt enthalten
        backup_files = list(backup_dir.glob("*.md"))
        assert any(f.read_bytes() == original_bytes for f in backup_files), \
            "Backup enthaelt nicht den originalen Datei-Inhalt"

    def test_no_backup_dir_no_backup(self, tmp_path):
        """Ohne backup_dir: backed_up==0."""
        truths_dir = tmp_path / "2_Model" / "truths"
        atom_path = truths_dir / "W01.md"
        _write_atom(atom_path, "W01", "Eine Wahrheit ohne Backup.")

        pl_path = tmp_path / "6_PL" / "pl.md"
        _write_parking_lot(pl_path, "PL deckt W01 ab.")

        result = materialize(tmp_path, apply=True, backup_dir=None)

        assert result["backed_up"] == 0, "backed_up muss 0 sein wenn kein backup_dir angegeben"


# ---------------------------------------------------------------------------
# Test 6: Return-Dict enthaelt alle Pflichtfelder
# ---------------------------------------------------------------------------

class TestReturnSchema:
    def test_return_dict_has_required_keys(self, tmp_path):
        """materialize() muss stets alle Pflicht-Schluesse liefern."""
        truths_dir = tmp_path / "2_Model" / "truths"
        _write_atom(truths_dir / "W01.md", "W01", "Eine Wahrheit.")

        result = materialize(tmp_path, apply=False)

        required_keys = {"scanned", "with_refs", "would_update", "updated", "backed_up"}
        assert required_keys.issubset(result.keys()), \
            f"Fehlende Keys: {required_keys - result.keys()}"


# ---------------------------------------------------------------------------
# Test 7 (BL-494 family): _iter_truth_atoms schliesst .claude/** aus
# ---------------------------------------------------------------------------
# _iter_truth_atoms ist der GETEILTE truth-Atom-Walker (Gate + alle backref-Stages).
# Die Capstone-out_dir ist vault/.claude/output/capstone, also schreibt Stage 4 die
# Atom-Backups nach vault/.claude/output/capstone/backref_backup/. Diese Backup-KOPIEN
# tragen gueltiges truth-Frontmatter -> der Walker zaehlt sie doppelt als Vault-Atome
# (duplizierte local_id/id -> false id_collisions im G1 des Gates). Fix: jede Datei
# ueberspringen, deren Pfad RELATIV ZU root ein `.claude`-Segment hat. Diese Tests
# pinnen genau diesen Vertrag. RED heute (kein .claude-Filter), GRUEN nach dem Fix.

from truth_backref_materialize import _iter_truth_atoms  # noqa: E402


class TestIterTruthAtomsExcludesDotClaude:
    def test_iter_truth_atoms_excludes_dotclaude(self, tmp_path):
        """Ein echtes Atom unter Backlog/... UND eine 1:1-Kopie unter
        .claude/output/capstone/backref_backup/ -> _iter_truth_atoms darf NUR das
        Nicht-.claude-Atom liefern (die .claude-Backup-Kopie ist Tooling, kein
        Vault-Content). FAELLT heute: liefert 2 (kein .claude-Filter)."""
        real = tmp_path / "Backlog" / "BL-1" / "2_Model" / "truths" / "W1.md"
        _write_atom(real, "W1", "Eine Wahrheit im echten Vault.")

        backup = tmp_path / ".claude" / "output" / "capstone" / "backref_backup" / "W1.md"
        _write_atom(backup, "W1", "Eine Wahrheit im echten Vault.")

        yielded = list(_iter_truth_atoms(tmp_path))

        assert len(yielded) == 1, (
            f"erwartet genau 1 Atom (.claude-Backup ausgeschlossen), got {len(yielded)}: "
            f"{[str(t[0]) for t in yielded]}"
        )
        for path, _content, _lid in yielded:
            rel_parts = path.relative_to(tmp_path).parts
            assert ".claude" not in rel_parts, (
                f"Kein Pfad mit .claude-Segment darf geliefert werden, got {path}"
            )

    def test_iter_truth_atoms_excludes_nested_dotclaude(self, tmp_path):
        """Ein Atom tief unter .claude/anything/deep/W2.md wird ebenfalls
        ausgeschlossen (jedes .claude-Segment in beliebiger Tiefe). Das echte Atom
        ausserhalb .claude bleibt. FAELLT heute: liefert auch das .claude-Atom."""
        real = tmp_path / "Backlog" / "BL-1" / "2_Model" / "truths" / "W1.md"
        _write_atom(real, "W1", "Atom im echten Vault.")

        nested = tmp_path / ".claude" / "anything" / "deep" / "W2.md"
        _write_atom(nested, "W2", "Atom tief unter .claude.")

        yielded = list(_iter_truth_atoms(tmp_path))
        paths = [t[0] for t in yielded]

        assert nested not in paths, (
            f".claude-verschachteltes Atom darf NICHT geliefert werden: {nested}"
        )
        for path in paths:
            rel_parts = path.relative_to(tmp_path).parts
            assert ".claude" not in rel_parts, (
                f"Kein Pfad mit .claude-Segment darf geliefert werden, got {path}"
            )
        assert len(yielded) == 1

    def test_iter_truth_atoms_keeps_non_dotclaude(self, tmp_path):
        """Regression: ein normaler Vault mit 2 Atomen AUSSERHALB .claude liefert
        beide (der Filter droppt ausschliesslich .claude). Passt heute schon."""
        a = tmp_path / "Backlog" / "BL-1" / "2_Model" / "truths" / "W1.md"
        b = tmp_path / "Backlog" / "BL-2" / "2_Model" / "truths" / "W2.md"
        _write_atom(a, "W1", "Erstes Atom.")
        _write_atom(b, "W2", "Zweites Atom.")

        yielded = list(_iter_truth_atoms(tmp_path))
        paths = {t[0] for t in yielded}

        assert a in paths, f"Atom {a} fehlt im Ergebnis: {[str(p) for p in paths]}"
        assert b in paths, f"Atom {b} fehlt im Ergebnis: {[str(p) for p in paths]}"
        assert len(yielded) == 2
