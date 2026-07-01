#!/usr/bin/env python3
"""
BL-171: Tests fuer BERATER_OUTPUTS Pointer-Pattern
Deckt ab: write+read Pointer, Legacy-Inline-Compat, Migration, Fehlerbehandlung.
BL-229 AK-B (2026-06-10): T5 — Regex 108 Varianten + ungefenct.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Lokales Skript importieren
sys.path.insert(0, str(Path(__file__).parent))
from berater_outputs_pointer import (
    audit_manifest,
    gc_delete_pointer,
    is_pointer,
    make_pointer,
    migrate_inline_to_pointer,
    read_berater_output,
    write_berater_output,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MANIFEST_WITH_INLINE = """---
bl_id: BL-TEST
name: test-bl
status: DONE_A
---

## A_PIPELINE_STATE

```yaml
modus: fresh
```

## BERATER_OUTPUTS

```yaml
modusEntscheidung: {modus: M2, k_score: 75, status: DONE}
patternBrief: {patterns: [P1, P2], status: DONE}
```
"""

MANIFEST_EMPTY = """---
bl_id: BL-TEST
name: test-bl
status: DONE_A
---

## A_PIPELINE_STATE

```yaml
modus: fresh
```
"""


def _make_tmp_manifest(content: str) -> Path:
    """Erstellt temporaeres Manifest-File und gibt Pfad zurueck."""
    tmp_dir = Path(tempfile.mkdtemp())
    manifest = tmp_dir / "_manifest.md"
    manifest.write_text(content, encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# T1: Write + Read Pointer (einfachster Pfad)
# ---------------------------------------------------------------------------

class TestWriteReadPointer(unittest.TestCase):
    """T1: write_berater_output schreibt Pointer; read_berater_output liest ihn."""

    def test_write_creates_pointer_in_manifest(self):
        # Arrange
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)
        payload = {"modus": "M3", "k_score": 80, "status": "DONE"}

        # Act
        content_file = write_berater_output(
            manifest_path=manifest,
            phase="neuePhase",
            batch_key="b1",
            payload=payload,
        )

        # Assert: Content-File existiert
        self.assertTrue(content_file.exists(), "Content-File muss existieren")
        # Assert: Manifest enthaelt Pointer (path-Feld)
        from berater_outputs_pointer import _load_manifest_raw
        berater_outputs, _ = _load_manifest_raw(manifest)
        entry = berater_outputs.get("neuePhase_b1")
        self.assertIsNotNone(entry, "Pointer-Key muss im Manifest sein")
        self.assertIn("path", entry, "Pointer muss 'path'-Feld haben")
        self.assertIn("status", entry, "Pointer muss 'status'-Feld haben")
        self.assertIn("completed_at", entry, "Pointer muss 'completed_at'-Feld haben")
        self.assertEqual(entry["schema_version"], 1, "schema_version muss 1 sein")

    def test_read_returns_payload_from_pointer(self):
        # Arrange
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)
        payload = {"modus": "M3", "k_score": 80, "status": "DONE"}
        write_berater_output(
            manifest_path=manifest,
            phase="neuePhase",
            batch_key=None,
            payload=payload,
        )

        # Act
        result = read_berater_output(manifest_path=manifest, phase="neuePhase")

        # Assert
        self.assertIsNotNone(result, "read muss Payload zurueckgeben")
        self.assertEqual(result.get("modus"), "M3", "Payload muss korrekt gelesen werden")
        self.assertEqual(result.get("k_score"), 80)

    def test_read_missing_key_returns_none(self):
        # Arrange: Guard-Test (einfachster Edge Case)
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)

        # Act
        result = read_berater_output(manifest_path=manifest, phase="nichtVorhanden")

        # Assert
        self.assertIsNone(result, "Fehlender Key muss None zurueckgeben")

    def test_write_pointer_path_is_relative(self):
        # Arrange: INV-POINTER-3 Pruefung
        manifest = _make_tmp_manifest(MANIFEST_EMPTY)
        payload = {"data": "test"}

        # Act
        write_berater_output(manifest_path=manifest, phase="testPhase", batch_key=None, payload=payload)

        # Assert: Pfad ist relativ (kein absoluter Pfad)
        from berater_outputs_pointer import _load_manifest_raw
        berater_outputs, _ = _load_manifest_raw(manifest)
        entry = berater_outputs.get("testPhase")
        self.assertIsNotNone(entry)
        ptr_path = entry["path"]
        self.assertFalse(Path(ptr_path).is_absolute(), "Pointer-Pfad muss relativ sein (INV-POINTER-3)")
        self.assertTrue(ptr_path.startswith("6_PL/"), "Pointer-Pfad muss in 6_PL/ liegen")


# ---------------------------------------------------------------------------
# T2: Legacy-Inline-Compat (INV-POINTER-1)
# ---------------------------------------------------------------------------

class TestLegacyInlineCompat(unittest.TestCase):
    """T2: read_berater_output liest Legacy-Inline-Format (INV-POINTER-1)."""

    def test_read_inline_returns_dict(self):
        # Arrange: altes Manifest mit Inline-BERATER_OUTPUTS
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)

        # Act
        result = read_berater_output(manifest_path=manifest, phase="modusEntscheidung")

        # Assert: Inline-Daten direkt zurueckgegeben
        self.assertIsNotNone(result, "Inline-Eintrag muss lesbar sein")
        self.assertEqual(result.get("modus"), "M2", "Inline-Modus muss korrekt gelesen werden")
        self.assertEqual(result.get("k_score"), 75)

    def test_read_inline_and_pointer_same_interface(self):
        # Arrange: Manifest mit gemischtem Inhalt (Inline + Pointer)
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)
        payload = {"patterns": ["P3", "P4"], "status": "DONE"}
        write_berater_output(
            manifest_path=manifest,
            phase="neuePhase",
            batch_key=None,
            payload=payload,
        )

        # Act: Beide Formate lesen
        inline_result = read_berater_output(manifest_path=manifest, phase="modusEntscheidung")
        pointer_result = read_berater_output(manifest_path=manifest, phase="neuePhase")

        # Assert: Beide geben dict zurueck (gleiche Interface)
        self.assertIsInstance(inline_result, dict, "Inline muss dict zurueckgeben")
        self.assertIsInstance(pointer_result, dict, "Pointer muss dict zurueckgeben")

    def test_is_pointer_discriminates_correctly(self):
        # Arrange
        pointer_entry = {"path": "6_PL/test.md", "status": "DONE", "version": 1, "completed_at": "2026-05-17"}
        inline_entry = {"modus": "M2", "status": "DONE"}
        scalar_entry = "irgendwas"

        # Act + Assert
        self.assertTrue(is_pointer(pointer_entry), "Dict mit 'path' ist Pointer")
        self.assertFalse(is_pointer(inline_entry), "Dict ohne 'path' ist kein Pointer")
        self.assertFalse(is_pointer(scalar_entry), "String ist kein Pointer")


# ---------------------------------------------------------------------------
# T3: Migration (AK-6)
# ---------------------------------------------------------------------------

class TestMigration(unittest.TestCase):
    """T3: migrate_inline_to_pointer konvertiert Inline -> Pointer."""

    def test_migration_converts_inline_entries(self):
        # Arrange
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)

        # Act
        migrated = migrate_inline_to_pointer(manifest, dry_run=False)

        # Assert: beide Inline-Eintraege wurden migriert
        self.assertIn("modusEntscheidung", migrated, "modusEntscheidung muss migriert werden")
        self.assertIn("patternBrief", migrated, "patternBrief muss migriert werden")
        self.assertEqual(len(migrated), 2, "Genau 2 Keys muss migriert werden")

    def test_migration_creates_backup(self):
        # Arrange
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)
        from datetime import date
        today_str = date.today().isoformat()

        # Act
        migrate_inline_to_pointer(manifest, dry_run=False)

        # Assert: Backup-Datei existiert
        backup = manifest.parent / f"_backup_pre_bl171_{today_str}.md"
        self.assertTrue(backup.exists(), "Backup-Datei muss erstellt werden")

    def test_migration_dry_run_no_changes(self):
        # Arrange
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)
        original_content = manifest.read_text(encoding="utf-8")

        # Act
        migrated = migrate_inline_to_pointer(manifest, dry_run=True)

        # Assert: Manifest unveraendert
        current_content = manifest.read_text(encoding="utf-8")
        self.assertEqual(original_content, current_content, "Dry-Run darf Manifest nicht veraendern")
        self.assertEqual(len(migrated), 2, "Dry-Run muss trotzdem migrierbare Keys zaehlen")

    def test_migration_leaves_existing_pointers_intact(self):
        # Arrange: Manifest mit bereits vorhandenen Pointer-Eintraegen
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)
        payload = {"data": "test"}
        write_berater_output(manifest_path=manifest, phase="neuePhase", batch_key=None, payload=payload)

        # Act
        migrated = migrate_inline_to_pointer(manifest, dry_run=False)

        # Assert: neuePhase (bereits Pointer) nicht in migrated
        self.assertNotIn("neuePhase", migrated, "Vorhandene Pointer duerfen nicht re-migriert werden")

    def test_migrated_data_readable_after_migration(self):
        # Arrange
        manifest = _make_tmp_manifest(MANIFEST_WITH_INLINE)
        migrate_inline_to_pointer(manifest, dry_run=False)

        # Act: Nach Migration lesbar (INV-POINTER-1 gilt auch fuer neu-migrierte)
        result = read_berater_output(manifest_path=manifest, phase="modusEntscheidung")

        # Assert
        self.assertIsNotNone(result, "Migrierter Eintrag muss lesbar sein")
        self.assertEqual(result.get("modus"), "M2", "Migrierter Inhalt muss korrekt sein")


# ---------------------------------------------------------------------------
# T4: Fehlerbehandlung + GC
# ---------------------------------------------------------------------------

class TestErrorHandlingAndGC(unittest.TestCase):
    """T4: Fehlerbehandlung bei defekten Pointern + GC-Loeschung."""

    def test_read_broken_pointer_returns_none(self):
        # Arrange: Pointer zeigt auf nicht-existente Datei
        manifest = _make_tmp_manifest(MANIFEST_EMPTY)
        payload = {"data": "test"}
        content_file = write_berater_output(
            manifest_path=manifest, phase="testPhase", batch_key=None, payload=payload
        )
        # Content-File loeschen (kaputten Pointer simulieren)
        content_file.unlink()

        # Act
        result = read_berater_output(manifest_path=manifest, phase="testPhase")

        # Assert: None statt Exception
        self.assertIsNone(result, "Defekter Pointer muss None zurueckgeben, nicht Exception werfen")

    def test_audit_detects_broken_pointer(self):
        # Arrange
        manifest = _make_tmp_manifest(MANIFEST_EMPTY)
        payload = {"data": "test"}
        content_file = write_berater_output(
            manifest_path=manifest, phase="testPhase", batch_key=None, payload=payload
        )
        content_file.unlink()  # kaputten Pointer simulieren

        # Act
        report = audit_manifest(manifest)

        # Assert
        self.assertIn("testPhase", report["broken_pointer"], "Audit muss kaputten Pointer erkennen")
        self.assertEqual(report["pointer"], 1)

    def test_gc_delete_removes_pointer_and_file(self):
        # Arrange: INV-POINTER-4 (atomic loeschen)
        manifest = _make_tmp_manifest(MANIFEST_EMPTY)
        payload = {"data": "test"}
        content_file = write_berater_output(
            manifest_path=manifest, phase="gcPhase", batch_key=None, payload=payload
        )
        self.assertTrue(content_file.exists(), "Content-File muss existieren vor GC")

        # Act
        deleted = gc_delete_pointer(manifest_path=manifest, phase_key="gcPhase")

        # Assert
        self.assertTrue(deleted, "GC muss True zurueckgeben bei Erfolg")
        self.assertFalse(content_file.exists(), "Content-File muss nach GC weg sein (INV-POINTER-4)")
        result = read_berater_output(manifest_path=manifest, phase="gcPhase")
        self.assertIsNone(result, "Nach GC muss read None zurueckgeben")

    def test_gc_nonexistent_key_returns_false(self):
        # Arrange
        manifest = _make_tmp_manifest(MANIFEST_EMPTY)

        # Act
        deleted = gc_delete_pointer(manifest_path=manifest, phase_key="nichtVorhanden")

        # Assert: kein Fehler, False zurueck
        self.assertFalse(deleted, "GC auf nicht-existenten Key muss False zurueckgeben")

    def test_make_pointer_required_fields(self):
        # Arrange + Act
        ptr = make_pointer(content_path_relative="6_PL/BERATER_OUTPUTS/test.md")

        # Assert: Pflichtfelder gemaess AK-1
        self.assertIn("path", ptr)
        self.assertIn("status", ptr)
        self.assertIn("version", ptr)
        self.assertIn("completed_at", ptr)
        self.assertIn("schema_version", ptr)
        self.assertEqual(ptr["schema_version"], 1)


# ---------------------------------------------------------------------------
# T5: BL-229 AK-B — 108 Block-Varianten + ungefenct (2026-06-10)
# ---------------------------------------------------------------------------

# Fixtures fuer 108-Varianten-Tests
# Fenced-Varianten: Block-Header gefolgt von ```yaml ... ```
# Ungefenct-Varianten: Block-Header gefolgt direkt von YAML (kein Fence)

def _make_fenced_manifest(block_header: str, yaml_content: str = "modus: M3\nstatus: DONE\n") -> str:
    """Hilfsfunktion: Manifest mit einem fenced BERATER_OUTPUTS-Block."""
    return (
        "---\nbl_id: BL-TEST\nstatus: DONE_A\n---\n\n"
        f"## {block_header}\n\n```yaml\n{yaml_content}```\n"
    )


def _make_unfenced_manifest(block_header: str, yaml_content: str = "modus: M3\nstatus: DONE\n") -> str:
    """Hilfsfunktion: Manifest mit einem ungefencten BERATER_OUTPUTS-Block (kein yaml-Fence)."""
    return (
        "---\nbl_id: BL-TEST\nstatus: DONE_A\n---\n\n"
        f"## {block_header}\n\n{yaml_content}\n"
    )


# Repraesentative Auswahl aus den 108 Varianten (Spec: suffixed + ungefenct)
BLOCK_VARIANTS_FENCED = [
    # bare (Standard, BL-171 original)
    "BERATER_OUTPUTS",
    # dot-suffixed Varianten (Berater-Name mit Punkt)
    "BERATER_OUTPUTS.dependencyAnalyzer",
    "BERATER_OUTPUTS.plBewertung",
    "BERATER_OUTPUTS.validator",
    "BERATER_OUTPUTS.modusEntscheidung",
    "BERATER_OUTPUTS.patternBrief",
    # underscore-suffixed Varianten (Berater-Name mit Unterstrich)
    "BERATER_OUTPUTS_dependencyAnalyzer",
    "BERATER_OUTPUTS_plBewertung",
    "BERATER_OUTPUTS_validator",
    # round-suffixed (mit Runden-Nummer: _roundN)
    "BERATER_OUTPUTS_plBewertung_round15",
    "BERATER_OUTPUTS_validator_round11",
    "BERATER_OUTPUTS_modusEntscheidung_round3",
    # dot+underscore gemischt (IDF-Prefix)
    "BERATER_OUTPUTS_IDF.validator_round11",
    "BERATER_OUTPUTS_SDF.patternBrief_round7",
    # paren-Form Round-Suffix (Spec: \(\s*Round\s*\d)
    "BERATER_OUTPUTS (Round 5)",
    "BERATER_OUTPUTS.dependencyAnalyzer (Round 12)",
    # kombinierte Formen aus dem 486-Live-Case
    "BERATER_OUTPUTS_berater_modusEntscheidung_round8",
    "BERATER_OUTPUTS_berater_plBewertung_round2",
]

BLOCK_VARIANTS_UNFENCED = [
    # Gleiche Block-Header aber OHNE yaml-Fence (ungefenct)
    "BERATER_OUTPUTS",
    "BERATER_OUTPUTS.dependencyAnalyzer",
    "BERATER_OUTPUTS_plBewertung_round15",
    "BERATER_OUTPUTS_IDF.validator_round11",
    "BERATER_OUTPUTS (Round 5)",
]


class TestBlockVariants108(unittest.TestCase):
    """T5 (BL-229 AK-B): Regex erkennt ALLE 108 Block-Varianten (fenced + ungefenct).

    RED-Phase: Tests schlagen fehl wenn Regex nur 'BERATER_OUTPUTS' (ohne Suffix) matcht.
    GREEN-Phase: Regex auf volle Variantenmenge erweitert.
    """

    def _assert_block_detected(self, block_header: str, is_fenced: bool) -> None:
        """Hilfsmethode: Prueft ob der Block-Header vom Loader erkannt wird."""
        from berater_outputs_pointer import _load_manifest_raw
        yaml_content = "modus: M3\nstatus: DONE\n"
        if is_fenced:
            content = _make_fenced_manifest(block_header, yaml_content)
        else:
            content = _make_unfenced_manifest(block_header, yaml_content)
        manifest = _make_tmp_manifest(content)
        data, _ = _load_manifest_raw(manifest)
        self.assertNotEqual(
            data,
            {},
            f"Block '{block_header}' ({'fenced' if is_fenced else 'ungefenct'}) "
            f"muss von _load_manifest_raw erkannt werden (nicht leeres Dict)",
        )

    def _assert_block_saved(self, block_header: str, is_fenced: bool) -> None:
        """Hilfsmethode: Prueft ob _save_manifest_raw den Block zurückschreiben kann."""
        from berater_outputs_pointer import _load_manifest_raw, _save_manifest_raw
        yaml_content = "modus: M3\nstatus: DONE\n"
        if is_fenced:
            content = _make_fenced_manifest(block_header, yaml_content)
        else:
            content = _make_unfenced_manifest(block_header, yaml_content)
        manifest = _make_tmp_manifest(content)
        data, original_text = _load_manifest_raw(manifest)
        if data:
            # Kleines Update
            data["_test_marker"] = True
            _save_manifest_raw(manifest, data, original_text)
            data2, _ = _load_manifest_raw(manifest)
            self.assertIn(
                "_test_marker",
                data2,
                f"Nach _save_manifest_raw muss _test_marker im Block '{block_header}' stehen",
            )

    # --- Fenced-Varianten ---

    def test_fenced_bare_berater_outputs(self):
        """Basis-Test: original BL-171-Block (bare, fenced) muss erkannt werden."""
        self._assert_block_detected("BERATER_OUTPUTS", is_fenced=True)

    def test_fenced_dot_suffix_dependencyAnalyzer(self):
        self._assert_block_detected("BERATER_OUTPUTS.dependencyAnalyzer", is_fenced=True)

    def test_fenced_dot_suffix_plBewertung(self):
        self._assert_block_detected("BERATER_OUTPUTS.plBewertung", is_fenced=True)

    def test_fenced_dot_suffix_validator(self):
        self._assert_block_detected("BERATER_OUTPUTS.validator", is_fenced=True)

    def test_fenced_dot_suffix_modusEntscheidung(self):
        self._assert_block_detected("BERATER_OUTPUTS.modusEntscheidung", is_fenced=True)

    def test_fenced_dot_suffix_patternBrief(self):
        self._assert_block_detected("BERATER_OUTPUTS.patternBrief", is_fenced=True)

    def test_fenced_underscore_suffix_dependencyAnalyzer(self):
        self._assert_block_detected("BERATER_OUTPUTS_dependencyAnalyzer", is_fenced=True)

    def test_fenced_underscore_suffix_plBewertung(self):
        self._assert_block_detected("BERATER_OUTPUTS_plBewertung", is_fenced=True)

    def test_fenced_underscore_suffix_validator(self):
        self._assert_block_detected("BERATER_OUTPUTS_validator", is_fenced=True)

    def test_fenced_round_suffix_plBewertung_round15(self):
        self._assert_block_detected("BERATER_OUTPUTS_plBewertung_round15", is_fenced=True)

    def test_fenced_round_suffix_validator_round11(self):
        self._assert_block_detected("BERATER_OUTPUTS_IDF.validator_round11", is_fenced=True)

    def test_fenced_round_suffix_modusEntscheidung_round3(self):
        self._assert_block_detected("BERATER_OUTPUTS_modusEntscheidung_round3", is_fenced=True)

    def test_fenced_idf_dot_suffix_round(self):
        self._assert_block_detected("BERATER_OUTPUTS_IDF.validator_round11", is_fenced=True)

    def test_fenced_sdf_dot_suffix_round(self):
        self._assert_block_detected("BERATER_OUTPUTS_SDF.patternBrief_round7", is_fenced=True)

    def test_fenced_paren_round_form(self):
        self._assert_block_detected("BERATER_OUTPUTS (Round 5)", is_fenced=True)

    def test_fenced_dot_suffix_paren_round(self):
        self._assert_block_detected("BERATER_OUTPUTS.dependencyAnalyzer (Round 12)", is_fenced=True)

    def test_fenced_berater_modusEntscheidung_round8(self):
        self._assert_block_detected("BERATER_OUTPUTS_berater_modusEntscheidung_round8", is_fenced=True)

    def test_fenced_berater_plBewertung_round2(self):
        self._assert_block_detected("BERATER_OUTPUTS_berater_plBewertung_round2", is_fenced=True)

    # --- Ungefenct-Varianten (kein ```yaml...``` Fence) ---

    def test_unfenced_bare_berater_outputs(self):
        """Ungefencter bare-Block muss erkannt werden."""
        self._assert_block_detected("BERATER_OUTPUTS", is_fenced=False)

    def test_unfenced_dot_suffix_dependencyAnalyzer(self):
        self._assert_block_detected("BERATER_OUTPUTS.dependencyAnalyzer", is_fenced=False)

    def test_unfenced_round_suffix_plBewertung_round15(self):
        self._assert_block_detected("BERATER_OUTPUTS_plBewertung_round15", is_fenced=False)

    def test_unfenced_idf_dot_suffix_round(self):
        self._assert_block_detected("BERATER_OUTPUTS_IDF.validator_round11", is_fenced=False)

    def test_unfenced_paren_round_form(self):
        self._assert_block_detected("BERATER_OUTPUTS (Round 5)", is_fenced=False)

    # --- Save-Roundtrip (fenced + ungefenct) ---

    def test_save_roundtrip_fenced_dot_suffix(self):
        """_save_manifest_raw muss fenced Block mit Suffix korrekt zurueckschreiben."""
        self._assert_block_saved("BERATER_OUTPUTS.dependencyAnalyzer", is_fenced=True)

    def test_save_roundtrip_unfenced_bare(self):
        """_save_manifest_raw muss ungefencten bare-Block korrekt zurueckschreiben."""
        self._assert_block_saved("BERATER_OUTPUTS", is_fenced=False)

    def test_save_roundtrip_fenced_round_suffix(self):
        """_save_manifest_raw muss fenced Block mit round-Suffix korrekt zurueckschreiben."""
        self._assert_block_saved("BERATER_OUTPUTS_plBewertung_round15", is_fenced=True)

    def test_all_fenced_variants_detected(self):
        """Sammel-Test: ALLE 18 fenced Varianten muessen erkannt werden."""
        from berater_outputs_pointer import _load_manifest_raw
        failed = []
        for variant in BLOCK_VARIANTS_FENCED:
            content = _make_fenced_manifest(variant)
            manifest = _make_tmp_manifest(content)
            data, _ = _load_manifest_raw(manifest)
            if data == {}:
                failed.append(variant)
        self.assertEqual(
            failed,
            [],
            f"Folgende fenced Varianten wurden NICHT erkannt: {failed}",
        )

    def test_all_unfenced_variants_detected(self):
        """Sammel-Test: ALLE 5 ungefencten Varianten muessen erkannt werden."""
        from berater_outputs_pointer import _load_manifest_raw
        failed = []
        for variant in BLOCK_VARIANTS_UNFENCED:
            content = _make_unfenced_manifest(variant)
            manifest = _make_tmp_manifest(content)
            data, _ = _load_manifest_raw(manifest)
            if data == {}:
                failed.append(variant)
        self.assertEqual(
            failed,
            [],
            f"Folgende ungefencten Varianten wurden NICHT erkannt: {failed}",
        )


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
