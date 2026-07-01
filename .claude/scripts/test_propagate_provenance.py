"""BL-411: propagate_provenance cmd_update graceful handling of out-of-vault derived_from.

RED-Tests (geschrieben vom Test-Autor, NICHT vom GREEN-Implementierer — false-GREEN-Fang):
- out-of-vault Quellen (.claude/pileOfMud, .claude/output, {Vault}-Platzhalter) duerfen
  KEIN exit 2 ausloesen (legit nicht-vault-resident -> graceful SKIP, AK-1/AK-3).
- genuinely-missing VAULT-RESIDENTE Vorgaenger loesen WEITERHIN exit 2 aus (kein zu-permissiver Fix).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import propagate_provenance as pp  # noqa: E402


def _write_doc_with_derived_from(path: Path, derived_from_list):
    df = "\n".join(f"      - \"{d}\"" for d in derived_from_list)
    path.write_text(
        "---\n"
        "type: findings_crumbs\n"
        "provenance_chain:\n"
        "  - layer: 1\n"
        "    artifact: \"x\"\n"
        "    derived_from:\n"
        f"{df}\n"
        "---\n\n# Body\n",
        encoding="utf-8",
    )


def test_out_of_vault_pileofmud_is_graceful(tmp_path):
    """derived_from auf .claude/pileOfMud/* (out-of-vault) -> exit 0, kein FAIL (AK-1/AK-3)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    doc = vault / "Backlog" / "BL-X" / "Crumbs" / "findings.md"
    doc.parent.mkdir(parents=True)
    _write_doc_with_derived_from(doc, [".claude/pileOfMud/transkript.md"])
    assert pp.cmd_update(doc, vault) == 0


def test_out_of_vault_output_and_placeholder_graceful(tmp_path):
    """.claude/output/* + {Vault}-Platzhalter -> ebenfalls graceful exit 0."""
    vault = tmp_path / "vault"
    vault.mkdir()
    doc = vault / "model.md"
    _write_doc_with_derived_from(doc, [".claude/output/Assay_1.md", "{Vault}/Backlog/foo.md"])
    assert pp.cmd_update(doc, vault) == 0


def test_missing_vault_resident_predecessor_still_fails(tmp_path):
    """Echter vault-residenter, fehlender Vorgaenger -> WEITERHIN exit 2 (kein zu-permissiver Fix)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    doc = vault / "spec.md"
    _write_doc_with_derived_from(doc, ["Backlog/BL-Y/2_Model/does_not_exist.md"])
    assert pp.cmd_update(doc, vault) == 2
