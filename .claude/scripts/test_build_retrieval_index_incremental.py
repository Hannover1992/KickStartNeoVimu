"""
test_build_retrieval_index_incremental.py — BL-275 / AK-S1 (Forward Write→Index-Seam).

Der `_W_push_global`-Seam (Schritt 4b) ruft nach jedem Vault-Push
`build_retrieval_index.py --incremental --path=X` — DAMIT der vorab gebaute
Schnell-Index (keyword/edge/anchor/backlinks-JSON + _Tag-Index.md) frisch bleibt
und `_W_fetch` Schritt 0d (Index-First) den neuen Knoten findet.

BEFUND (vor Fix): die `--incremental`-CLI-Branch (build_retrieval_index.py main)
machte NUR einen in-memory `build_index(...)` und `return 0` — sie PERSISTIERTE
NICHTS (kein `_write_index_json`, kein _Tag-Index.md-Write). Der Seam waere ein
No-Op gewesen: der Push schreibt den Vault-Knoten, aber der Schnell-Index bleibt
stale -> _W_fetch faellt ewig auf RAG/Walk zurueck. Genau die „ab-jetzt-sauber"-
Luecke, die BL-275 schliessen soll.

| #  | Test                                                | AK    |
|----|-----------------------------------------------------|-------|
| T1 | --incremental --path=X PERSISTIERT die Index-JSON   | AK-S1 |
| T2 | --incremental --path=X schreibt _Tag-Index.md       | AK-S1 |
| T3 | --incremental --path=<nicht im Vault> -> exit 1     | (Guard, unveraendert) |
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import build_retrieval_index  # noqa: E402


def _seed_vault(tmp_path):
    """Echter tmp-Vault-Root mit 1 Knoten (keyword 'modus')."""
    root = tmp_path / "Vault"
    root.mkdir()
    (root / "A.md").write_text(
        "---\nkeywords: [modus]\ntags: [topic/Modus]\nnode_type: spec\n---\nKnoten A ueber modus.\n",
        encoding="utf-8",
    )
    return root


def _index_dir(root):
    return os.path.join(str(root), ".claude", "output", "retrieval_index")


def test_t1_incremental_persists_keyword_index_json(tmp_path, monkeypatch):
    """AK-S1: --incremental --path=X muss die 4 maschinellen Indizes als JSON
    PERSISTIEREN (nicht nur in-memory rebuilden). RED vor Fix: keine *.json."""
    root = _seed_vault(tmp_path)
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(root))
    rc = build_retrieval_index.main(["--incremental", "--path=A.md"])
    assert rc == 0
    kw_json = os.path.join(_index_dir(root), "_keyword_index.json")
    assert os.path.exists(kw_json), "--incremental muss _keyword_index.json persistieren (BL-275 AK-S1)"
    with open(kw_json, encoding="utf-8") as fh:
        kw = json.load(fh)
    assert "modus" in kw  # der frische Knoten ist im persistierten Schnell-Index


def test_t2_incremental_writes_tag_index_md(tmp_path, monkeypatch):
    """AK-S1: --incremental schreibt auch _Tag-Index.md (was _W_fetch Schritt 0d liest)."""
    root = _seed_vault(tmp_path)
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(root))
    rc = build_retrieval_index.main(["--incremental", "--path=A.md"])
    assert rc == 0
    assert os.path.exists(os.path.join(str(root), "_Tag-Index.md"))


def test_t3_incremental_nonexistent_path_returns_1(tmp_path, monkeypatch):
    """Pfad-Guard unveraendert: --incremental --path=<nicht im Vault> -> exit 1."""
    root = _seed_vault(tmp_path)
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(root))
    rc = build_retrieval_index.main(["--incremental", "--path=ghost.md"])
    assert rc == 1
