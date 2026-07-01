"""
TDD-RED BL-376 batch_1: Tests fuer canonicalize_bl_manifest + Write-Routing-Guard.

AK-1: canonicalize_bl_manifest(bl_id, vault_root) normalisiert flat BERATER_OUTPUTS_{name}:
      (top-level) zu nested BERATER_OUTPUTS:\n  {name}: — idempotent.
AK-2: Write-Routing-Guard blockiert BERATER_OUTPUTS-Write in globales (_factory_manifest.md /
      _manifest.md) und gibt Recovery-Hint auf per-BL.

Diese Tests sind RED: canonicalize_bl_manifest und write_bl_block_guard existieren nicht.
KEINE Impl-Aenderungen in diesem Schritt.
"""
from __future__ import annotations

import pytest
from pathlib import Path

# Import der noch-nicht-existenten Funktionen — das ist der RED-Beweis.
# ImportError / AttributeError macht den Test-Lauf RED.
from manifest_reader import (
    canonicalize_bl_manifest,   # AK-1 — existiert noch nicht
    write_bl_block_guard,       # AK-2 — existiert noch nicht
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_vault(tmp_path: Path) -> Path:
    """Minimales Vault-Layout: Backlog/{bl_id}/_manifest.md + _factory_manifest.md."""
    vault = tmp_path / "Vault"
    vault.mkdir()
    # split aktiv machen
    (vault / "_factory_manifest.md").write_text("## FACTORY\nstate: active\n", encoding="utf-8")
    backlog = vault / "Backlog"
    backlog.mkdir()
    return vault


def _make_bl_manifest(vault: Path, bl_id: str, content: str) -> Path:
    """Legt {vault}/Backlog/{bl_id}/_manifest.md mit gegebenem Inhalt an."""
    bl_folder = vault / "Backlog" / bl_id
    bl_folder.mkdir(parents=True, exist_ok=True)
    manifest = bl_folder / "_manifest.md"
    manifest.write_text(content, encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# AK-1: canonicalize_bl_manifest
# ---------------------------------------------------------------------------

class TestCanonicalizeBlManifest:

    def test_canonicalize_flat_to_nested(self, tmp_path: Path):
        """
        Ring 1 (Edge Case): flat BERATER_OUTPUTS_modusErkennung: ... top-level
        wird zu nested BERATER_OUTPUTS:\n  modusErkennung: ... konvertiert.
        """
        vault = _make_vault(tmp_path)
        flat_content = (
            "## A_PIPELINE_STATE\n"
            "a_status: DONE\n"
            "\n"
            "## BERATER_OUTPUTS_modusErkennung\n"
            "status: complete\n"
            "output: modus_M2\n"
        )
        manifest = _make_bl_manifest(vault, "BL-TEST-1", flat_content)

        canonicalize_bl_manifest("BL-TEST-1", vault_root=vault)

        result = manifest.read_text(encoding="utf-8")

        # nested BERATER_OUTPUTS Block muss vorhanden sein
        assert "## BERATER_OUTPUTS" in result
        # modusErkennung als Unter-Eintrag (nested)
        assert "modusErkennung" in result
        # flat-Block darf nicht mehr top-level existieren
        assert "## BERATER_OUTPUTS_modusErkennung" not in result

    def test_canonicalize_idempotent(self, tmp_path: Path):
        """
        Ring 2 (Normalfall): bereits-nested BERATER_OUTPUTS bleibt unveraendert
        nach zweitem canonicalize-Aufruf.
        """
        vault = _make_vault(tmp_path)
        nested_content = (
            "## A_PIPELINE_STATE\n"
            "a_status: DONE\n"
            "\n"
            "## BERATER_OUTPUTS\n"
            "  modusErkennung:\n"
            "    status: complete\n"
            "    output: modus_M2\n"
        )
        manifest = _make_bl_manifest(vault, "BL-TEST-2", nested_content)

        # erstes Mal
        canonicalize_bl_manifest("BL-TEST-2", vault_root=vault)
        after_first = manifest.read_text(encoding="utf-8")

        # zweites Mal (Idempotenz)
        canonicalize_bl_manifest("BL-TEST-2", vault_root=vault)
        after_second = manifest.read_text(encoding="utf-8")

        assert after_first == after_second, (
            "canonicalize_bl_manifest muss idempotent sein: zweiter Aufruf darf nichts aendern."
        )
        # nested Block muss unveraendert sein
        assert "## BERATER_OUTPUTS" in after_second
        assert "## BERATER_OUTPUTS_modusErkennung" not in after_second

    def test_canonicalize_mixed(self, tmp_path: Path):
        """
        Ring 3 (Komplex): Manifest hat SOWOHL nested-Block ALS AUCH flat-Eintraege.
        Nach canonicalize: alles in nested BERATER_OUTPUTS zusammengefuehrt,
        keine flat top-level Bloecke mehr.
        """
        vault = _make_vault(tmp_path)
        mixed_content = (
            "## A_PIPELINE_STATE\n"
            "a_status: DONE\n"
            "\n"
            "## BERATER_OUTPUTS\n"
            "  specParse:\n"
            "    status: complete\n"
            "\n"
            "## BERATER_OUTPUTS_modusErkennung\n"
            "status: complete\n"
            "output: modus_M3\n"
            "\n"
            "## BERATER_OUTPUTS_akExtraktion\n"
            "status: complete\n"
            "aks: [AK-1, AK-2]\n"
        )
        manifest = _make_bl_manifest(vault, "BL-TEST-3", mixed_content)

        canonicalize_bl_manifest("BL-TEST-3", vault_root=vault)

        result = manifest.read_text(encoding="utf-8")

        # Genau ein nested BERATER_OUTPUTS Block
        assert result.count("## BERATER_OUTPUTS") == 1, (
            "Nach canonicalize darf es nur einen ## BERATER_OUTPUTS Block geben."
        )
        # Alle drei Berater muessen als Unter-Eintraege vorhanden sein
        assert "specParse" in result
        assert "modusErkennung" in result
        assert "akExtraktion" in result
        # Keine flat-Bloecke mehr
        assert "## BERATER_OUTPUTS_modusErkennung" not in result
        assert "## BERATER_OUTPUTS_akExtraktion" not in result


# ---------------------------------------------------------------------------
# AK-2: Write-Routing-Guard
# ---------------------------------------------------------------------------

class TestWriteRoutingGuard:

    def test_write_routing_guard_blocks_global_leak(self, tmp_path: Path):
        """
        Ring 4 (Edge Case): Versuch, BERATER_OUTPUTS in globales Manifest
        (_factory_manifest.md oder _manifest.md) zu schreiben muss
        mit Fehler + Recovery-Hint geblockt werden.
        """
        vault = _make_vault(tmp_path)
        # global _manifest.md anlegen (legacy-Pfad)
        global_manifest = vault / "_manifest.md"
        global_manifest.write_text("## BDF_PIPELINE_STATE\nbdf_status: running\n", encoding="utf-8")

        with pytest.raises(Exception) as exc_info:
            # Versuch: BERATER_OUTPUTS in das globale Manifest schreiben
            write_bl_block_guard(
                target_path=global_manifest,
                field_path="BERATER_OUTPUTS.modusErkennung",
                vault_root=vault,
            )

        error_msg = str(exc_info.value)
        # Fehler muss Recovery-Hint enthalten
        assert "per-BL" in error_msg or "bl_folder" in error_msg or "BL-" in error_msg, (
            f"Recovery-Hint muss auf per-BL schreiben hinweisen. Got: {error_msg!r}"
        )
        # Globales Manifest darf nicht veraendert worden sein
        content_after = global_manifest.read_text(encoding="utf-8")
        assert "BERATER_OUTPUTS" not in content_after, (
            "Globales Manifest darf keinen BERATER_OUTPUTS-Eintrag enthalten."
        )

    def test_write_routing_per_bl_ok(self, tmp_path: Path):
        """
        Ring 5 (Normalfall): per-BL BERATER_OUTPUTS-Write in {bl_folder}/_manifest.md
        ist erlaubt und darf keinen Fehler werfen.
        """
        vault = _make_vault(tmp_path)
        bl_folder = vault / "Backlog" / "BL-TEST-5"
        bl_folder.mkdir(parents=True, exist_ok=True)
        bl_manifest = bl_folder / "_manifest.md"
        bl_manifest.write_text("## A_PIPELINE_STATE\na_status: DONE\n", encoding="utf-8")

        # Kein Fehler erwartet — per-BL Write ist OK
        write_bl_block_guard(
            target_path=bl_manifest,
            field_path="BERATER_OUTPUTS.modusErkennung",
            vault_root=vault,
        )

        result = bl_manifest.read_text(encoding="utf-8")
        # Eintrag muss vorhanden sein (guard erlaubt den Write)
        assert "BERATER_OUTPUTS" in result or "modusErkennung" in result, (
            "Per-BL Write muss in _manifest.md landen."
        )
