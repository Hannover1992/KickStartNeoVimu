"""
BL-450 Stufe-5 Integrations-Test -- RED-Worker (INV-BUILD-GRAIN: != GREEN-Worker)

Prueft die ECHTE Naht zwischen _extraction_orchestrate.run_stage5_edges und
keyword_edge_writer.main — kein subprocess/import-Mock.

Defekt: run_stage5_edges haengt --idempotent an argv (default idempotent=True),
aber keyword_edge_writer.argparse kennt nur --vault/--dry-run -> parse_args
lehnt --idempotent ab -> SystemExit(2).

Tests:
  1. test_edges_mode_dry_run_real_seam        -- Orchestrator-CLI via echte Naht -> exit 0 (AKTUELL RED)
  2. test_keyword_edge_writer_accepts_idempotent -- kew.main([..., --idempotent]) -> exit 0 (AKTUELL RED)
  3. test_edges_dry_run_no_writes             -- dry-run mutiert Atom-Dateien NICHT (byte-identisch)
"""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import sys

import pytest


# ---------------------------------------------------------------------------
# Import-Helpers (echter Import aus .claude/scripts, kein Mock)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = pathlib.Path(__file__).parent


def _import_module(name: str, filename: str):
    """Importiere Modul via Pfad (umgeht sys.path-Abhaengigkeit)."""
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    # Stelle sicher dass Modul sich selbst per Name importieren kann
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _get_eo():
    """Gibt _extraction_orchestrate Modul zurueck (mit Cache)."""
    if "_extraction_orchestrate" not in sys.modules:
        _import_module("_extraction_orchestrate", "_extraction_orchestrate.py")
    return sys.modules["_extraction_orchestrate"]


def _get_kew():
    """Gibt keyword_edge_writer Modul zurueck (mit Cache)."""
    if "keyword_edge_writer" not in sys.modules:
        _import_module("keyword_edge_writer", "keyword_edge_writer.py")
    return sys.modules["keyword_edge_writer"]


# ---------------------------------------------------------------------------
# Mini-Vault-Fixture: 3 Atom-.md Dateien mit ueberlappenden keywords
# ---------------------------------------------------------------------------

_ATOM_A = """\
---
id: BL-X.atom-a
local_id: atom-a
type: truth
title: Atom A
keywords:
  - graph
  - edges
status: aktiv
created: "2026-01-01"
updated: "2026-01-01"
tags: []
bl_item: BL-X
feature: test
---

Inhalt Atom A.
"""

_ATOM_B = """\
---
id: BL-X.atom-b
local_id: atom-b
type: truth
title: Atom B
keywords:
  - graph
  - nodes
status: aktiv
created: "2026-01-01"
updated: "2026-01-01"
tags: []
bl_item: BL-X
feature: test
---

Inhalt Atom B. Teilt 'graph' mit Atom A.
"""

_ATOM_C = """\
---
id: BL-X.atom-c
local_id: atom-c
type: truth
title: Atom C
keywords:
  - nodes
  - routing
status: aktiv
created: "2026-01-01"
updated: "2026-01-01"
tags: []
bl_item: BL-X
feature: test
---

Inhalt Atom C. Teilt 'nodes' mit Atom B.
"""


@pytest.fixture()
def mini_vault(tmp_path: pathlib.Path) -> pathlib.Path:
    """Legt einen Mini-Vault mit 3 Atom-Dateien unter Backlog/BL-X/2_Model/truths/ an."""
    truths_dir = tmp_path / "Backlog" / "BL-X" / "2_Model" / "truths"
    truths_dir.mkdir(parents=True)
    (truths_dir / "atom-a.md").write_text(_ATOM_A, encoding="utf-8")
    (truths_dir / "atom-b.md").write_text(_ATOM_B, encoding="utf-8")
    (truths_dir / "atom-c.md").write_text(_ATOM_C, encoding="utf-8")
    return tmp_path


def _file_sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExtractionOrchestrateIntegration:

    def test_edges_mode_dry_run_real_seam(self, mini_vault: pathlib.Path):
        """
        Test 1 (RED): _extraction_orchestrate.main(["--mode=edges","--vault",str(mini_vault),"--dry-run"])
        ruft via DIREKTEM IMPORT run_stage5_edges -> keyword_edge_writer.main(argv) auf.
        run_stage5_edges haengt --idempotent an argv (idempotent=True default).
        keyword_edge_writer.argparse kennt kein --idempotent -> SystemExit(2).

        Erwartung nach Fix: exit 0.
        AKTUELL: SystemExit(2) wegen 'unrecognized arguments: --idempotent' -> RED.
        """
        eo = _get_eo()
        # Stelle sicher dass keyword_edge_writer im sys.modules liegt,
        # damit _extraction_orchestrate.run_stage5_edges "import keyword_edge_writer" findet.
        _get_kew()

        try:
            rc = eo.main(["--mode=edges", "--vault", str(mini_vault), "--dry-run"])
        except SystemExit as exc:
            rc = int(exc.code) if exc.code is not None else 1

        assert rc == 0, (
            f"NAHT-DEFEKT: _extraction_orchestrate --mode=edges haengt --idempotent an argv, "
            f"aber keyword_edge_writer.argparse kennt --idempotent nicht -> exit {rc} (erwartet 0). "
            "Fix: --idempotent in keyword_edge_writer argparse registrieren."
        )

    def test_keyword_edge_writer_accepts_idempotent(self, mini_vault: pathlib.Path):
        """
        Test 2 (RED): keyword_edge_writer.main(["--vault",str(mini_vault),"--dry-run","--idempotent"])
        direkt aufrufen.
        AKTUELL: SystemExit(2) weil argparse --idempotent nicht kennt -> RED.
        Erwartung nach Fix: exit 0.
        """
        kew = _get_kew()

        try:
            rc = kew.main(["--vault", str(mini_vault), "--dry-run", "--idempotent"])
        except SystemExit as exc:
            rc = int(exc.code) if exc.code is not None else 1

        assert rc == 0, (
            f"keyword_edge_writer.main lehnt --idempotent ab (exit {rc}). "
            "argparse kennt nur --vault/--dry-run -- --idempotent fehlt. "
            "Fix: parser.add_argument('--idempotent', action='store_true') in keyword_edge_writer.py."
        )

    def test_edges_dry_run_no_writes(self, mini_vault: pathlib.Path):
        """
        Test 3: dry-run-Lauf veraendert Atom-Dateien NICHT (byte-identisch vor/nach).
        Dieser Test ist GREEN-faehig sobald Test 1+2 gefixt sind (--idempotent akzeptiert),
        haengt aber von der --dry-run-Semantik ab.

        Prueft: mtime/hash aller .md-Dateien identisch nach keyword_edge_writer --dry-run.
        """
        truths_dir = mini_vault / "Backlog" / "BL-X" / "2_Model" / "truths"
        atom_files = sorted(truths_dir.glob("*.md"))
        assert len(atom_files) == 3, "Fixture-Fehler: 3 Atom-Dateien erwartet"

        # Hashes VOR dem Lauf
        hashes_before = {f: _file_sha256(f) for f in atom_files}

        kew = _get_kew()
        try:
            rc = kew.main(["--vault", str(mini_vault), "--dry-run"])
        except SystemExit as exc:
            rc = int(exc.code) if exc.code is not None else 1

        # Test schlaegt fehl wenn kew.main selbst crashed (wegen unbekanntem Arg
        # in Test 1/2 -- hier ohne --idempotent, daher kein Absturz durch diesen Bug).
        assert rc == 0, f"keyword_edge_writer --dry-run (ohne --idempotent) exit {rc}, erwartet 0"

        # Hashes NACH dem Lauf -- muessen identisch sein
        for f in atom_files:
            after = _file_sha256(f)
            assert hashes_before[f] == after, (
                f"dry-run hat Datei mutiert: {f.name} "
                f"(sha256 vorher={hashes_before[f][:12]}... nachher={after[:12]}...)"
            )
