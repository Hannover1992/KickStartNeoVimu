# -*- coding: utf-8 -*-
"""
test_manifest_drift_detector.py — BL-454 RED-Tests (Stufe 1, Iteration 1).

RED-Worker: Tests fuer manifest_drift_detector.py (vom GREEN-Worker zu bauen).
Das Modul existiert NOCH NICHT -> alle Tests failen mit ImportError (RED bestaetigt).

CONTRACT (fuer GREEN-Worker):
  Modul: .claude/scripts/manifest_drift_detector.py
  READ-ONLY, DI/fixture-testbar (read-fns injizierbar), keine Korrekturen.

  Funktionen:
    detect_duplicate_blocks(manifest_text: str) -> list[str]
      - Findet top-level `## BLOCK_NAME`-Header die MEHR ALS EINMAL vorkommen.
      - Block-Header-Regex: r'^##\\s+(\\S+)' (erste Nicht-Leerzeichen-Token nach ##).
      - Liefert Liste der duplizierten Block-Namen (dedupliziert, Reihenfolge egal).
      - Sauberer Text (keine Dups) -> [].

    detect_split_brain(vault_root_manifest_text: str, stub_manifest_text: str) -> list[str]
      - Findet BL-State-Bloecke die in BEIDEN Texten vorkommen.
      - Vergleicht alle top-level ## BLOCK_NAME-Header aus beiden Texten.
      - Liefert Liste der Block-Namen die in beiden vorhanden sind.
      - Disjunkte Texte -> [].

    scan_manifest_drift(vault_root: str | Path,
                        read_vault_fn=None, read_stub_fn=None) -> dict
      - Orchestriert: liest {vault_root}/_manifest.md + .claude/analysis/_manifest.md
        (relativ zum Repo-Root, ermittelt aus vault_root-Nachbar-Konvention ODER
        via resolve_vault_root.py-aequivalent).
      - read_vault_fn / read_stub_fn: optionale DI-Reader (path -> str), default=None
        -> realer Filesystem-Read.
      - Rueckgabe-dict enthaelt mindestens:
          duplicate_blocks: list[str]
          split_brain_blocks: list[str]
      - READ-ONLY, KEINE Korrekturen.

ANMERKUNG BLOCK-HEADER-REGEX fuer GREEN-Worker:
  ^##\\s+(\\S+) matched die erste Nicht-Leerzeichen-Sequenz nach "## ".
  Beispiele:
    "## FOO"              -> "FOO"
    "## DF_BATCH_STATE"   -> "DF_BATCH_STATE"
    "## IDF_PIPELINE_STATE_BL-456" -> "IDF_PIPELINE_STATE_BL-456"
  Kein Match auf ###, ####, etc. (nur genau zwei #).
  Trailing-Tokens (z.B. "(Round 11)") werden ignoriert fuer Dup-Erkennung
  — Vereinfachung: nur der erste Token nach ## zaehlt als Block-Name.
"""

import pytest

# RED: dieses Import muss failen (Modul existiert nicht).
# Alle Tests in diesem File werden mit ImportError / ModuleNotFoundError rot.
from manifest_drift_detector import (  # type: ignore  # noqa: E402
    detect_duplicate_blocks,
    detect_split_brain,
    scan_manifest_drift,
)


# ---------------------------------------------------------------------------
# T1: detect_duplicate_blocks
# ---------------------------------------------------------------------------

class TestDetectDuplicateBlocks:
    """T1 — Erkennung doppelter top-level ##-Header."""

    def test_t1a_duplicate_found(self):
        """Text mit ## FOO ... ## BAR ... ## FOO -> liefert ['FOO']."""
        manifest_text = (
            "## FOO\n"
            "some content\n"
            "\n"
            "## BAR\n"
            "other content\n"
            "\n"
            "## FOO\n"
            "duplicate!\n"
        )
        result = detect_duplicate_blocks(manifest_text)
        assert "FOO" in result, f"Erwartet 'FOO' in result, got: {result}"

    def test_t1b_no_duplicate_clean_text(self):
        """Sauberer Text ohne Dups -> leere Liste."""
        manifest_text = (
            "## ALPHA\n"
            "content a\n"
            "\n"
            "## BETA\n"
            "content b\n"
            "\n"
            "## GAMMA\n"
            "content c\n"
        )
        result = detect_duplicate_blocks(manifest_text)
        assert result == [], f"Erwartet [], got: {result}"

    def test_t1c_multiple_duplicates(self):
        """Zwei verschiedene Bloecke sind je doppelt -> beide in result."""
        manifest_text = (
            "## FOO\ncontent\n"
            "## BAR\ncontent\n"
            "## FOO\ncontent\n"
            "## BAR\ncontent\n"
        )
        result = detect_duplicate_blocks(manifest_text)
        assert "FOO" in result
        assert "BAR" in result

    def test_t1d_triple_header_not_matched(self):
        """### DEEP_HEADER ist kein top-level ## Block -> kein Dup-Signal."""
        manifest_text = (
            "### DEEP\ncontent\n"
            "### DEEP\ncontent\n"
        )
        result = detect_duplicate_blocks(manifest_text)
        assert result == [], f"### sollte ignoriert werden, got: {result}"

    def test_t1e_empty_text(self):
        """Leerer Text -> keine Bloecke -> []."""
        result = detect_duplicate_blocks("")
        assert result == []

    def test_t1f_real_state_block_names(self):
        """BL-Spezifische State-Bloecke koennen Duplikate sein (BL-NEW-44.1)."""
        manifest_text = (
            "## DF_BATCH_STATE_BL-456\ncontent\n"
            "## IDF_PIPELINE_STATE_BL-332\ncontent\n"
            "## DF_BATCH_STATE_BL-456\ncontent again\n"
        )
        result = detect_duplicate_blocks(manifest_text)
        assert "DF_BATCH_STATE_BL-456" in result


# ---------------------------------------------------------------------------
# T2: detect_split_brain
# ---------------------------------------------------------------------------

class TestDetectSplitBrain:
    """T2 — Split-brain-Erkennung: gleiche Bloecke in vault-root + stub."""

    def test_t2a_split_brain_detected(self):
        """Gleicher Block in beiden Texten -> split_brain gemeldet."""
        vault_text = (
            "## DF_BATCH_STATE_BL-456\n"
            "modus: M2\n"
        )
        stub_text = (
            "## DF_BATCH_STATE_BL-456\n"
            "modus: M3\n"  # divergenter State -> split-brain
        )
        result = detect_split_brain(vault_text, stub_text)
        assert "DF_BATCH_STATE_BL-456" in result, f"Erwartet split-brain, got: {result}"

    def test_t2b_disjoint_no_split_brain(self):
        """Disjunkte Bloecke -> keine Ueberschneidung -> []."""
        vault_text = "## A_PIPELINE_STATE\ncontent\n"
        stub_text = "## IDF_PIPELINE_STATE\ncontent\n"
        result = detect_split_brain(vault_text, stub_text)
        assert result == [], f"Erwartet [], got: {result}"

    def test_t2c_empty_stub(self):
        """Leerer Stub -> keine Ueberschneidung moeglich -> []."""
        vault_text = "## DF_BATCH_STATE_BL-456\ncontent\n"
        result = detect_split_brain(vault_text, "")
        assert result == []

    def test_t2d_multiple_split_brain_blocks(self):
        """Mehrere ueberschneidende Bloecke -> alle gemeldet."""
        vault_text = (
            "## DF_BATCH_STATE_BL-456\ncontent\n"
            "## IDF_PIPELINE_STATE_BL-332\ncontent\n"
        )
        stub_text = (
            "## DF_BATCH_STATE_BL-456\ncontent\n"
            "## IDF_PIPELINE_STATE_BL-332\ncontent\n"
        )
        result = detect_split_brain(vault_text, stub_text)
        assert "DF_BATCH_STATE_BL-456" in result
        assert "IDF_PIPELINE_STATE_BL-332" in result


# ---------------------------------------------------------------------------
# T3: scan_manifest_drift (E2E, DI-fixture)
# ---------------------------------------------------------------------------

class TestScanManifestDrift:
    """T3 — E2E-Orchestrierung via DI-injizierte Reader (kein echtes Filesystem)."""

    def test_t3a_duplicate_and_split_brain_both_detected(self):
        """1 Dup + 1 split-brain -> dict enthaelt beide."""
        vault_content = (
            "## FOO\ncontent\n"
            "## FOO\nduplicate\n"
            "## DF_BATCH_STATE_BL-456\ncontent\n"
        )
        stub_content = (
            "## DF_BATCH_STATE_BL-456\ncontent\n"  # split-brain
        )

        def read_vault_fn(_path):
            return vault_content

        def read_stub_fn(_path):
            return stub_content

        result = scan_manifest_drift(
            vault_root="/fake/vault",
            read_vault_fn=read_vault_fn,
            read_stub_fn=read_stub_fn,
        )

        assert "duplicate_blocks" in result
        assert "split_brain_blocks" in result
        assert "FOO" in result["duplicate_blocks"]
        assert "DF_BATCH_STATE_BL-456" in result["split_brain_blocks"]

    def test_t3b_clean_pair_empty_lists(self):
        """Sauberes Paar -> beide Listen leer."""
        vault_content = "## ALPHA\ncontent\n## BETA\ncontent\n"
        stub_content = "## GAMMA\ncontent\n"

        def read_vault_fn(_path):
            return vault_content

        def read_stub_fn(_path):
            return stub_content

        result = scan_manifest_drift(
            vault_root="/fake/vault",
            read_vault_fn=read_vault_fn,
            read_stub_fn=read_stub_fn,
        )

        assert result["duplicate_blocks"] == []
        assert result["split_brain_blocks"] == []

    def test_t3c_missing_stub_graceful(self):
        """Fehlendes/leeres Stub -> scan_manifest_drift robust, kein Crash."""
        vault_content = "## FOO\ncontent\n## FOO\ndup\n"

        def read_vault_fn(_path):
            return vault_content

        def read_stub_fn(_path):
            return ""  # Stub fehlt/leer

        result = scan_manifest_drift(
            vault_root="/fake/vault",
            read_vault_fn=read_vault_fn,
            read_stub_fn=read_stub_fn,
        )

        assert "duplicate_blocks" in result
        assert "FOO" in result["duplicate_blocks"]
        assert result["split_brain_blocks"] == []
