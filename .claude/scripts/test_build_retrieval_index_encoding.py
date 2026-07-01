"""
test_build_retrieval_index_encoding.py — BL-278 / BL-242-AK-ENC-PL-1 / batch_PL1
(Encoding-Robustheit) Regressions-Suite.

REGRESSION (BL-278, Realitaet-Kontakt-Beweis BL-260): `_walk_vault_nodes` las jede
.md mit strict UTF-8 (`open(path).read()` OHNE `errors=`). Der erste nicht-UTF-8-Byte
(cp1252/Latin-1, z.B. 0x97 = Word-Gedankenstrich) warf `UnicodeDecodeError` -> der
GANZE Build-Walk starb, kein Index entstand. Realer DCS-Vault (4122 Dateien) crashte
in 0.228s ("can't decode byte 0x97 in position 69"), WAEHREND 51/51 synthetische Tests
(clean-UTF-8-tmp-Fixtures) gruen waren. Grüne Coverage != Robustheit.

Fix (build_retrieval_index.py:222): `open(fpath, encoding="utf-8", errors="replace")`.

Diese Suite ist die in BL-278 fehlende **non-UTF-8-Fixture (AK-S2)** + der
**Graceful-Walk-Beweis (AK-S1)**: eine schmutzige Datei darf den Walk NICHT killen;
saubere Geschwister-Knoten werden weiter indiziert.

revert-confirm-RED (bootstrap-direkt, 2026-06-04): bewiesen ROT durch temporaeres
Entfernen von `errors="replace"` (strict UTF-8) -> `UnicodeDecodeError`; mit Fix GRUEN.
Der Fix war wegen des abgebrochenen M1-Skelett-Laufs (BL-280) bereits im Code, bevor
ein RED-Test existierte — die Revert-Probe stellt die TDD-Ehrlichkeit her.

| #  | Test                                            | AK    |
|----|-------------------------------------------------|-------|
| T1 | build_index crasht NICHT auf 0x97-Datei          | AK-S2 |
| T2 | saubere Geschwister-Knoten trotzdem indiziert    | AK-S1 |
| T3 | voller build-Pfad (main) exit 0 auf dirty Vault  | AK-S2 |
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import build_retrieval_index  # noqa: E402


# 0x97 als roher Byte ist KEIN gueltiges strict-UTF-8 (Continuation-Byte ohne Lead)
# -> reproduziert exakt den BL-278-Crash (DCS-Vault, byte 0x97 in position 69).
_DIRTY_BYTE = b"\x97"


def _write_md_bytes(root, rel_path, raw_bytes):
    """Schreibt eine .md-Datei ROH (binary) — erlaubt nicht-UTF-8-Bytes im Body."""
    target = os.path.join(str(root), rel_path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as fh:
        fh.write(raw_bytes)
    return target


def _write_md_text(root, rel_path, frontmatter_lines, body=""):
    """Saubere UTF-8-.md (parse_frontmatter-kompatibel)."""
    target = os.path.join(str(root), rel_path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n" + body + "\n"
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    return target


@pytest.fixture
def dirty_vault(tmp_path):
    """Echter tmp-Vault-Root mit (a) EINER nicht-UTF-8-Datei (rohes 0x97-Byte im Body)
    und (b) einem sauberen Geschwister-Knoten mit Keyword 'modus'. Reproduziert die
    reale Vault-Datenklasse (Word-Paste-Bytes neben sauberen Knoten)."""
    root = tmp_path / "DirtyVault"
    root.mkdir()
    # (a) schmutzige Datei: gueltiges UTF-8-Frontmatter + Body mit rohem 0x97-Byte.
    head = (
        "---\n"
        "bl: BL-DIRTY\n"
        "keywords: [encoding]\n"
        "tags: [topic/Dirty]\n"
        "node_type: note\n"
        "---\n"
        "Word-Gedankenstrich folgt: "
    ).encode("utf-8")
    tail = " danach normaler Text.\n".encode("utf-8")
    _write_md_bytes(root, "Backlog/dirty.md", head + _DIRTY_BYTE + tail)
    # (b) sauberer Geschwister-Knoten.
    _write_md_text(
        root, "Backlog/clean.md",
        ["bl: BL-CLEAN", "keywords: [modus]", "tags: [topic/Modus]",
         "node_type: spec"],
        body="Sauberer Knoten ueber modus.",
    )
    return root


def test_t1_build_index_does_not_crash_on_non_utf8_file(dirty_vault, monkeypatch):
    """AK-S2 (Regression BL-278): ein 0x97-Byte in EINER Datei darf den Build-Walk
    NICHT mit UnicodeDecodeError killen. build_index liefert ein Ergebnis-Dict.

    RED ohne Fix: _walk_vault_nodes liest strict utf-8 -> UnicodeDecodeError
    'utf-8 codec can't decode byte 0x97'. GREEN mit errors='replace'.
    """
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(dirty_vault))
    result = build_retrieval_index.build_index(roots=[str(dirty_vault)])  # darf NICHT werfen
    assert isinstance(result, dict)
    assert "keyword_index" in result


def test_t2_clean_sibling_still_indexed_despite_dirty_file(dirty_vault, monkeypatch):
    """AK-S1 (graceful): die schmutzige Datei wird tolerant gelesen (errors=replace),
    der Walk laeuft weiter -> der saubere Geschwister-Knoten ('modus') landet im Index.
    Beweis, dass EINE schmutzige Datei nicht den ganzen Index verhindert."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(dirty_vault))
    result = build_retrieval_index.build_index(roots=[str(dirty_vault)])
    assert "modus" in result["keyword_index"]


def test_t3_full_build_path_exit_zero_on_dirty_vault(dirty_vault, monkeypatch):
    """AK-S2 (Integration): der volle build-Pfad (main['build']) ueber den
    schmutzigen Vault terminiert mit exit 0 (kein Crash) — analog dem realen
    DCS-Vault-Lauf (4122 Dateien), der vor dem Fix in 0.2s starb."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(dirty_vault))
    rc = build_retrieval_index.main(["build"])
    assert rc == 0
