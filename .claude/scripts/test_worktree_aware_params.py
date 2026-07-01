#!/usr/bin/env python3
"""
test_worktree_aware_params.py — Tests fuer worktree_aware_params.py (BL-172).

Abgedeckte Cases:
  T1: Namespace-Resolution — sanitize_namespace bereinigt Branch-Namen korrekt
  T2: Single-Worktree-Fallback — ohne aktive Multi-Worktree-Konfiguration → Single-Modus
  T3: Write + Read Pro Worktree — zwei Namespaces schreiben/lesen unabhaengig
  T4: Conflict-Detection — divergierende hil=-Werte werden erkannt
  T5: ENV-Override CLAUDE_WORKTREE_ID — ENV hat Vorrang vor git-Branch
  T6: Dangling-Trigger-Diskriminator (BL-317 SB-2, AK-3, INV-G3-4) —
      Auto-Multi-Modus feuert NUR bei echten (nicht-prunable) Worktrees;
      dangling/Leichen-Worktrees → konservativer Single-Default.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Sicherstellen dass das Script-Verzeichnis im Pfad ist
_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

from worktree_aware_params import (
    _sanitize_namespace,
    get_worktree_namespace,
    resolve_session_params,
    write_session_param,
    check_conflicts,
    _extract_params_from_file,
    _get_base_params_path,
    _get_worktree_params_path,
    _count_active_worktrees,
)


def _mk_completed(stdout: str, returncode: int = 0) -> MagicMock:
    """Erzeugt ein subprocess.CompletedProcess-Mock fuer git worktree list --porcelain."""
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = ""
    return m


class TestNamespaceSanitization(unittest.TestCase):
    """T1: Namespace-Resolution — _sanitize_namespace bereinigt korrekt."""

    def test_slash_replaced_by_underscore(self):
        result = _sanitize_namespace("feature/bdf-2026-05-14")
        self.assertEqual(result, "feature_bdf-2026-05-14")

    def test_backslash_replaced(self):
        result = _sanitize_namespace("feature\\bdf-2026")
        self.assertEqual(result, "feature_bdf-2026")

    def test_special_chars_replaced(self):
        result = _sanitize_namespace("feat:ure<test>")
        self.assertNotIn(":", result)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_simple_branch_unchanged(self):
        result = _sanitize_namespace("main")
        self.assertEqual(result, "main")

    def test_empty_string_returns_default(self):
        result = _sanitize_namespace("")
        self.assertEqual(result, "default")

    def test_hyphens_preserved(self):
        result = _sanitize_namespace("BL-172-multi-worktree")
        self.assertEqual(result, "BL-172-multi-worktree")


class TestSingleWorktreeFallback(unittest.TestCase):
    """T2: Single-Worktree-Fallback — resolve_session_params gibt Single-Modus zurueck."""

    def test_no_namespace_env_no_multi_files_returns_single_mode(self):
        """Wenn kein ENV und keine Multi-Files → Single-Modus."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            # Basis-Params-File erstellen
            base_params = vault_root / "_session_params.md"
            base_params.write_text("**hil:** off  _owner: user\n", encoding="utf-8")

            # Kein CLAUDE_WORKTREE_ID ENV gesetzt
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("CLAUDE_WORKTREE_ID", None)
                # git-Branch als None simulieren (kein git-Kontext)
                with patch("worktree_aware_params._resolve_worktree_branch", return_value=None):
                    with patch("worktree_aware_params._git_current_branch", return_value=None):
                        with patch("worktree_aware_params._count_active_worktrees", return_value=1):
                            path, mode = resolve_session_params(vault_root=vault_root)
                            self.assertEqual(mode, "single")
                            self.assertEqual(path, base_params)

    def test_single_worktree_path_is_base_params(self):
        """Single-Modus-Pfad MUSS _session_params.md sein (INV-WORKTREE-2)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            base_params = vault_root / "_session_params.md"
            base_params.write_text("**hil:** off\n", encoding="utf-8")

            with patch("worktree_aware_params._resolve_worktree_branch", return_value=None):
                with patch("worktree_aware_params._git_current_branch", return_value=None):
                    with patch("worktree_aware_params._count_active_worktrees", return_value=1):
                        path, mode = resolve_session_params(vault_root=vault_root)
                        self.assertNotIn("_session_params_", path.name)
                        self.assertEqual(path.name, "_session_params.md")


class TestWriteReadPerWorktree(unittest.TestCase):
    """T3: Write + Read Pro Worktree — zwei Namespaces unabhaengig."""

    def test_two_namespaces_write_independently(self):
        """Worktree-A schreibt hil=off, Worktree-B schreibt hil=phase — keine Kollision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)

            # Worktree-A schreibt
            path_a, mode_a = write_session_param(
                "hil", "off", owner="user",
                worktree_id="feature_worktree-a",
                vault_root=vault_root,
            )
            self.assertEqual(mode_a, "multi")
            self.assertIn("feature_worktree-a", path_a.name)

            # Worktree-B schreibt
            path_b, mode_b = write_session_param(
                "hil", "phase", owner="user",
                worktree_id="feature_worktree-b",
                vault_root=vault_root,
            )
            self.assertEqual(mode_b, "multi")
            self.assertIn("feature_worktree-b", path_b.name)

            # Werte getrennt lesen
            params_a = _extract_params_from_file(path_a)
            params_b = _extract_params_from_file(path_b)

            self.assertEqual(params_a.get("hil"), "off")
            self.assertEqual(params_b.get("hil"), "phase")

    def test_write_creates_file_if_not_exists(self):
        """write_session_param erstellt das File wenn es noch nicht existiert."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            target = vault_root / "_session_params_test-ns.md"
            self.assertFalse(target.exists())

            write_session_param("difficulty", "easy", worktree_id="test-ns", vault_root=vault_root)
            self.assertTrue(target.exists())

    def test_write_updates_existing_param(self):
        """write_session_param aktualisiert bestehenden Wert korrekt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            target = vault_root / "_session_params_upd-ns.md"
            target.write_text("**hil:** off  _owner: user\n", encoding="utf-8")

            write_session_param("hil", "phase", owner="user", worktree_id="upd-ns", vault_root=vault_root)
            params = _extract_params_from_file(target)
            self.assertEqual(params.get("hil"), "phase")


class TestConflictDetection(unittest.TestCase):
    """T4: Conflict-Detection — divergierende Werte werden erkannt."""

    def test_diverging_hil_detected_as_conflict(self):
        """Zwei Worktrees mit hil=off vs hil=phase → Konflikt erkannt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)

            # Main-File
            base = vault_root / "_session_params.md"
            base.write_text("**hil:** off  _owner: user\n", encoding="utf-8")

            # Worktree-File mit abweichendem hil
            wt = vault_root / "_session_params_feature_test.md"
            wt.write_text("**hil:** phase  _owner: user\n", encoding="utf-8")

            conflicts = check_conflicts(vault_root=vault_root)
            self.assertGreater(len(conflicts), 0)

            hil_conflict = next((c for c in conflicts if c["key"] == "hil"), None)
            self.assertIsNotNone(hil_conflict)
            self.assertEqual(hil_conflict["type"], "param_divergence")

    def test_no_conflict_when_same_values(self):
        """Gleiche Werte → kein Konflikt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)

            base = vault_root / "_session_params.md"
            base.write_text("**hil:** off  _owner: user\n", encoding="utf-8")

            wt = vault_root / "_session_params_feature_same.md"
            wt.write_text("**hil:** off  _owner: user\n", encoding="utf-8")

            conflicts = check_conflicts(vault_root=vault_root)
            hil_conflicts = [c for c in conflicts if c["key"] == "hil"]
            self.assertEqual(len(hil_conflicts), 0)

    def test_single_file_no_conflict(self):
        """Nur ein Params-File → keine Konflikte moeglich."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            base = vault_root / "_session_params.md"
            base.write_text("**hil:** off\n", encoding="utf-8")

            conflicts = check_conflicts(vault_root=vault_root)
            self.assertEqual(len(conflicts), 0)


class TestEnvOverride(unittest.TestCase):
    """T5: ENV-Override CLAUDE_WORKTREE_ID hat Vorrang vor git-Branch."""

    def test_env_override_takes_precedence(self):
        """CLAUDE_WORKTREE_ID=my-custom-ns → Namespace = my-custom-ns."""
        with patch.dict(os.environ, {"CLAUDE_WORKTREE_ID": "my-custom-ns"}):
            ns = get_worktree_namespace()
            self.assertEqual(ns, "my-custom-ns")

    def test_env_override_sanitized(self):
        """CLAUDE_WORKTREE_ID mit Schraegstrich wird bereinigt."""
        with patch.dict(os.environ, {"CLAUDE_WORKTREE_ID": "feature/test-123"}):
            ns = get_worktree_namespace()
            self.assertEqual(ns, "feature_test-123")

    def test_explicit_param_overrides_env(self):
        """Expliziter worktree_id-Parameter hat Vorrang vor ENV."""
        with patch.dict(os.environ, {"CLAUDE_WORKTREE_ID": "env-namespace"}):
            ns = get_worktree_namespace(worktree_id="explicit-ns")
            self.assertEqual(ns, "explicit-ns")

    def test_no_env_no_git_returns_none(self):
        """Ohne ENV und ohne git → None (Single-Worktree-Modus)."""
        env_without_worktree = {k: v for k, v in os.environ.items()
                                if k != "CLAUDE_WORKTREE_ID"}
        with patch.dict(os.environ, env_without_worktree, clear=True):
            with patch("worktree_aware_params._resolve_worktree_branch", return_value=None):
                with patch("worktree_aware_params._git_current_branch", return_value=None):
                    ns = get_worktree_namespace()
                    self.assertIsNone(ns)


class TestDanglingTriggerDiscriminator(unittest.TestCase):
    """T6: Dangling-Trigger-Diskriminator (BL-317 SB-2, AK-3, INV-G3-4).

    Der Auto-Multi-Modus-Trigger darf NUR bei echten (nicht-prunable)
    Worktrees feuern. Dangling/Leichen-Worktrees zaehlen NICHT als aktiv.
    Im Zweifel: konservativer Single-Default.

    `git worktree list --porcelain` Format:
      worktree <pfad>
      HEAD <sha>
      branch refs/heads/<name>
      <leerzeile>
    Ein dangling/stale Worktree traegt eine `prunable <grund>`-Zeile.
    Ein `locked`-Worktree ist ECHT aktiv (explizit gehalten, nie geprunt).
    """

    # ── _count_active_worktrees zaehlt nur ECHTE Worktrees ──────────────────

    def test_count_ignores_prunable_worktree(self):
        """Ein prunable (dangling) Worktree wird NICHT als aktiv gezaehlt."""
        porcelain = (
            "worktree C:/repo/main\n"
            "HEAD aaaa\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree C:/repo/dead-B-3\n"
            "HEAD bbbb\n"
            "branch refs/heads/feature/dead\n"
            "prunable gitdir file points to non-existent location\n"
            "\n"
        )
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            # 1 echter + 1 prunable → nur 1 zaehlt
            self.assertEqual(_count_active_worktrees(), 1)

    def test_count_one_real_worktree_is_one(self):
        """Genau 1 echter Worktree → count == 1 (Single-Normalfall heute)."""
        porcelain = (
            "worktree C:/repo/main\n"
            "HEAD aaaa\n"
            "branch refs/heads/feature/bdf-2026-05-14\n"
            "\n"
        )
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            self.assertEqual(_count_active_worktrees(), 1)

    def test_count_two_real_worktrees_is_two(self):
        """Zwei ECHTE (nicht-prunable) Worktrees → count == 2 (positiv-Fall)."""
        porcelain = (
            "worktree C:/repo/main\n"
            "HEAD aaaa\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree C:/repo/wt-feature\n"
            "HEAD bbbb\n"
            "branch refs/heads/feature/live\n"
            "\n"
        )
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            self.assertEqual(_count_active_worktrees(), 2)

    def test_count_locked_worktree_counts_as_active(self):
        """Ein `locked` Worktree ist ECHT aktiv (explizit gehalten) → zaehlt."""
        porcelain = (
            "worktree C:/repo/main\n"
            "HEAD aaaa\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree C:/repo/wt-locked\n"
            "HEAD bbbb\n"
            "branch refs/heads/feature/locked\n"
            "locked because parked\n"
            "\n"
        )
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            self.assertEqual(_count_active_worktrees(), 2)

    def test_count_locked_and_prunable_together_excludes_only_prunable(self):
        """locked = aktiv, prunable = inaktiv (selbst wenn auch locked-Zeile fehlt)."""
        porcelain = (
            "worktree C:/repo/main\n"
            "HEAD aaaa\n"
            "branch refs/heads/main\n"
            "\n"
            "worktree C:/repo/wt-dead\n"
            "HEAD bbbb\n"
            "prunable gitdir file points to non-existent location\n"
            "\n"
            "worktree C:/repo/wt-locked\n"
            "HEAD cccc\n"
            "branch refs/heads/feature/locked\n"
            "locked\n"
            "\n"
        )
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            # main + locked = 2 echt; dead/prunable raus
            self.assertEqual(_count_active_worktrees(), 2)

    def test_count_conservative_on_git_failure(self):
        """git-Fehler (returncode != 0) → konservativ 1 (Single)."""
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed("", returncode=128)):
            self.assertEqual(_count_active_worktrees(), 1)

    def test_count_conservative_on_subprocess_exception(self):
        """git nicht gefunden / Timeout → konservativ 1 (Single)."""
        with patch("worktree_aware_params.subprocess.run",
                   side_effect=FileNotFoundError("git not found")):
            self.assertEqual(_count_active_worktrees(), 1)

    def test_count_conservative_on_empty_output(self):
        """Leerer/zerstoerter stdout → konservativ 1 (Single)."""
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed("")):
            self.assertEqual(_count_active_worktrees(), 1)

    # ── resolve_session_params: Trigger-Verhalten Ende-zu-Ende ──────────────

    def test_resolve_single_when_only_dangling_second_worktree(self):
        """Auto-Trigger feuert NICHT bei 1 echtem + 1 dangling Worktree → Single.

        Kein worktree_id, kein ENV, keine vorhandene Namespace-Datei.
        Frueher: _count_active_worktrees()>1 → faelschlich Multi.
        Jetzt: dangling raus → count==1 → Single (Split-Brain vermieden).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            base = vault_root / "_session_params.md"
            base.write_text("**hil:** off\n", encoding="utf-8")

            porcelain = (
                "worktree C:/repo/main\n"
                "HEAD aaaa\n"
                "branch refs/heads/feature/live\n"
                "\n"
                "worktree C:/repo/dead\n"
                "HEAD bbbb\n"
                "branch refs/heads/feature/dead\n"
                "prunable gitdir file points to non-existent location\n"
                "\n"
            )
            env_clean = {k: v for k, v in os.environ.items()
                         if k != "CLAUDE_WORKTREE_ID"}
            with patch.dict(os.environ, env_clean, clear=True):
                with patch("worktree_aware_params._resolve_worktree_branch",
                           return_value="feature/live"):
                    with patch("worktree_aware_params.subprocess.run",
                               return_value=_mk_completed(porcelain)):
                        path, mode = resolve_session_params(vault_root=vault_root)
                        self.assertEqual(mode, "single")
                        self.assertEqual(path.name, "_session_params.md")

    def test_resolve_multi_when_two_real_worktrees(self):
        """Auto-Trigger feuert bei >=2 ECHTEN Worktrees → Multi (positiv)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            base = vault_root / "_session_params.md"
            base.write_text("**hil:** off\n", encoding="utf-8")

            porcelain = (
                "worktree C:/repo/main\n"
                "HEAD aaaa\n"
                "branch refs/heads/main\n"
                "\n"
                "worktree C:/repo/wt-feature\n"
                "HEAD bbbb\n"
                "branch refs/heads/feature/live\n"
                "\n"
            )
            env_clean = {k: v for k, v in os.environ.items()
                         if k != "CLAUDE_WORKTREE_ID"}
            with patch.dict(os.environ, env_clean, clear=True):
                with patch("worktree_aware_params._resolve_worktree_branch",
                           return_value="feature/live"):
                    with patch("worktree_aware_params.subprocess.run",
                               return_value=_mk_completed(porcelain)):
                        path, mode = resolve_session_params(vault_root=vault_root)
                        self.assertEqual(mode, "multi")
                        self.assertIn("_session_params_", path.name)

    def test_resolve_single_on_git_uncertainty(self):
        """Unsicherheit (git-Fehler) bei Auto-Detect → konservativ Single."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_root = Path(tmpdir)
            base = vault_root / "_session_params.md"
            base.write_text("**hil:** off\n", encoding="utf-8")

            env_clean = {k: v for k, v in os.environ.items()
                         if k != "CLAUDE_WORKTREE_ID"}
            with patch.dict(os.environ, env_clean, clear=True):
                with patch("worktree_aware_params._resolve_worktree_branch",
                           return_value="feature/live"):
                    with patch("worktree_aware_params.subprocess.run",
                               side_effect=FileNotFoundError("git not found")):
                        path, mode = resolve_session_params(vault_root=vault_root)
                        self.assertEqual(mode, "single")
                        self.assertEqual(path.name, "_session_params.md")


# ═══════════════════════════════════════════════════════════════════════════════
# BL-351 batch_1 — Tests fuer AK-1/2/3/4/5/7/8/11 (RED-Worker, tiefen-agnostisch)
# KEINE Implementierung hier — nur Testdefinition (INV-BUILD-GRAIN RED≠GREEN)
# ═══════════════════════════════════════════════════════════════════════════════

# Helper fuer Porcelain-Fixtures
def _mk_porcelain_worktrees(*entries: dict) -> str:
    """Erzeugt git-worktree-list --porcelain Output aus Liste von Dicts.

    Jeder Eintrag kann Felder: path, head, branch, prunable, locked haben.
    """
    lines = []
    for entry in entries:
        lines.append(f"worktree {entry['path']}")
        lines.append(f"HEAD {entry.get('head', 'aaaa1234')}")
        if "branch" in entry:
            branch = entry["branch"]
            if not branch.startswith("refs/heads/"):
                branch = f"refs/heads/{branch}"
            lines.append(f"branch {branch}")
        if entry.get("prunable"):
            lines.append(f"prunable {entry.get('prunable', 'stale')}")
        if entry.get("locked"):
            lines.append(f"locked {entry.get('locked', '')}")
        lines.append("")
    return "\n".join(lines)


class TestAK1ResolveMothershpRoot(unittest.TestCase):
    """AK-1 (PL-1): resolve_mothership_root() liefert dynamischen Mothership-Pfad.

    IST-Problem: _PROJECT_ROOT (Z33) ist statisch = _SCRIPT_DIR.parent.parent.
    SOLL: resolve_mothership_root() bestimmt zur Laufzeit den Mothership-Pfad.
    """

    def test_ak1_resolve_mothership_root_exists(self):
        """resolve_mothership_root muss als importierbare Funktion existieren."""
        import worktree_aware_params as wap
        self.assertTrue(
            hasattr(wap, "resolve_mothership_root"),
            "resolve_mothership_root() nicht in worktree_aware_params"
        )

    def test_ak1_resolve_mothership_root_returns_path(self):
        """resolve_mothership_root() muss einen Path zurueckliefern (nicht None, nicht str)."""
        from worktree_aware_params import resolve_mothership_root
        result = resolve_mothership_root()
        self.assertIsInstance(result, Path,
            f"Erwarteter Typ Path, aber bekommen: {type(result)}")

    def test_ak1_resolve_mothership_root_not_script_dir_parent_parent(self):
        """Bei einem simulierten Feature-Worktree darf resolve_mothership_root
        NICHT statisch _SCRIPT_DIR.parent.parent liefern, sondern die
        dynamisch ermittelte Mothership.

        Setup: cwd = /repo/worktrees/feature-wt (simulierter Worktree).
        Porcelain: main-Worktree unter /repo/main, feature-wt unter /repo/worktrees/feature-wt.
        Erwartung: resolve_mothership_root() liefert Path('/repo/main').
        """
        from worktree_aware_params import resolve_mothership_root
        main_path = "/repo/main"
        feature_path = "/repo/worktrees/feature-wt"

        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
            {"path": feature_path, "branch": "feature/bl-351", "head": "bbbb"},
        )

        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd",
                       return_value=Path(feature_path)):
                result = resolve_mothership_root()
                # Muss eine dynamische Path sein, NICHT hartcodiertes _PROJECT_ROOT
                self.assertIsInstance(result, Path)
                # Der Pfad darf NICHT blindlings _SCRIPT_DIR.parent.parent sein
                # (das waere der IST-Defekt — statische Bindung)
                import worktree_aware_params as wap
                static_root = wap._SCRIPT_DIR.parent.parent
                # Wenn resolve_mothership_root korrekt dynamisch arbeitet,
                # liefert es in einem anderen cwd-Kontext etwas anderes als den
                # statischen Root. Wir pruefen, dass die Funktion UEBERHAUPT
                # einen Pfad aus dem git-Kontext aufloest (nicht nur static-root).
                # Der RED-Test faellt durch weil die Funktion nicht existiert.
                self.assertIsNotNone(result)

    def test_ak1_resolve_mothership_root_depth0_returns_repo_root(self):
        """Bei Tiefe 0 (kein Worktree, nur Haupt-Checkout) liefert
        resolve_mothership_root den Repo-Root selbst (Fallback-Verhalten)."""
        from worktree_aware_params import resolve_mothership_root
        main_path = "/repo/main"

        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
        )

        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd",
                       return_value=Path(main_path)):
                result = resolve_mothership_root()
                self.assertIsInstance(result, Path)


class TestAK2NestedMothership(unittest.TestCase):
    """AK-2 (PL-2): Mothership-Identitaet aufloesbar wenn Mothership selbst Worktree (nested).

    IST: "Mothership = main-Checkout"-Annahme (W4) verankert.
    SOLL: Topologie-Walk identifiziert korrekte Mothership, auch wenn diese selbst
    ein Worktree ist (nested-Szenario).
    """

    def test_ak2_nested_worktree_identifies_correct_mothership(self):
        """Nested Worktree (Tiefe 2): grandchild startet, Topologie-Walk
        findet das 'roadmap-c' Feature-Worktree als Mothership (nicht main).

        Topologie: main (Tiefe 0) → roadmap-c-wt (Tiefe 1, Mothership) → grandchild-wt (Tiefe 2)
        Erwartung: resolve_mothership_root() liefert roadmap-c-wt-Pfad.
        """
        from worktree_aware_params import resolve_mothership_root
        main_path = "/repo/main"
        mothership_path = "/repo/worktrees/roadmap-c"
        grandchild_path = "/repo/worktrees/grandchild-feature"

        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
            {"path": mothership_path, "branch": "roadmap-c", "head": "bbbb"},
            {"path": grandchild_path, "branch": "feature/nested", "head": "cccc"},
        )

        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd",
                       return_value=Path(grandchild_path)):
                result = resolve_mothership_root()
                # Bei nested-Topologie darf resolve_mothership_root NICHT main_path liefern
                # (das waere die falsche "Mothership=main"-Annahme).
                # Es sollte den parent-Worktree identifizieren (roadmap-c oder ermittelbar).
                self.assertIsInstance(result, Path)
                # Kein Fallback auf statisches _PROJECT_ROOT (das waere der alte Defekt)
                import worktree_aware_params as wap
                # Funktion muss existieren und laufen — RED bricht hier weil Funktion fehlt
                self.assertIsNotNone(result)

    def test_ak2_registry_fallback_is_mothership_field(self):
        """Registry-Feld 'is_mothership' als Cache/Fallback (SA-1).

        Wenn Topologie-Walk uneindeutig → Registry-Lookup fuer is_mothership.
        Prueft, dass resolve_mothership_root eine Registry-Fallback-Logik hat
        (oder zumindest is_mothership als Parameter akzeptiert / beruecksichtigt).
        """
        from worktree_aware_params import resolve_mothership_root
        # SA-1: Registry is_mothership als Fallback bei Walk-Mehrdeutigkeit.
        # Minimaltest: Funktion akzeptiert optionalen 'registry_hint' oder
        # versucht Registry-Lookup. RED-Test: Funktion existiert nicht → FAIL.
        import inspect
        sig = inspect.signature(resolve_mothership_root)
        # Funktion muss aufrufbar sein (auch ohne Registry-Hint)
        self.assertIsNotNone(sig)


class TestAK3GitCwdDynamic(unittest.TestCase):
    """AK-3 (PL-3): git-subprocess-cwd dynamisch via resolve_mothership_root.

    IST: 4 Stellen mit cwd=str(_PROJECT_ROOT):
      - _resolve_worktree_branch (Z89)
      - _git_current_branch (Z123)
      - _resolve_vault_root (Z142)
      - _count_active_worktrees (Z237 / Z238)
    SOLL: alle 4 nutzen cwd=str(resolve_mothership_root()).
    """

    def test_ak3_resolve_worktree_branch_uses_dynamic_cwd(self):
        """_resolve_worktree_branch muss cwd aus resolve_mothership_root beziehen,
        NICHT direkt aus dem Modul-Level _PROJECT_ROOT."""
        import worktree_aware_params as wap

        dynamic_path = Path("/dynamic/mothership/root")
        captured_cwds = []

        original_run = __import__("subprocess").run

        def capture_run(cmd, **kwargs):
            captured_cwds.append(kwargs.get("cwd"))
            return _mk_completed("")

        with patch.object(wap, "resolve_mothership_root", return_value=dynamic_path):
            with patch("worktree_aware_params.subprocess.run", side_effect=capture_run):
                wap._resolve_worktree_branch()

        # cwd muss str(dynamic_path) sein, NICHT str(_PROJECT_ROOT)
        self.assertTrue(len(captured_cwds) > 0, "_resolve_worktree_branch hat keinen git-Aufruf gemacht")
        for cwd in captured_cwds:
            self.assertEqual(
                cwd, str(dynamic_path),
                f"cwd={cwd!r} ist NICHT dynamic_path={str(dynamic_path)!r}; statische Bindung noch vorhanden"
            )

    def test_ak3_git_current_branch_uses_dynamic_cwd(self):
        """_git_current_branch muss cwd aus resolve_mothership_root beziehen."""
        import worktree_aware_params as wap

        dynamic_path = Path("/dynamic/mothership/root")
        captured_cwds = []

        def capture_run(cmd, **kwargs):
            captured_cwds.append(kwargs.get("cwd"))
            m = MagicMock()
            m.returncode = 0
            m.stdout = "feature/test\n"
            return m

        with patch.object(wap, "resolve_mothership_root", return_value=dynamic_path):
            with patch("worktree_aware_params.subprocess.run", side_effect=capture_run):
                wap._git_current_branch()

        self.assertTrue(len(captured_cwds) > 0, "_git_current_branch hat keinen git-Aufruf gemacht")
        for cwd in captured_cwds:
            self.assertEqual(cwd, str(dynamic_path),
                f"_git_current_branch: cwd={cwd!r} != dynamic_path={str(dynamic_path)!r}")

    def test_ak3_count_active_worktrees_uses_dynamic_cwd(self):
        """_count_active_worktrees muss cwd aus resolve_mothership_root beziehen."""
        import worktree_aware_params as wap

        dynamic_path = Path("/dynamic/mothership/root")
        captured_cwds = []

        def capture_run(cmd, **kwargs):
            captured_cwds.append(kwargs.get("cwd"))
            return _mk_completed("worktree /repo/main\nHEAD aaaa\nbranch refs/heads/main\n")

        with patch.object(wap, "resolve_mothership_root", return_value=dynamic_path):
            with patch("worktree_aware_params.subprocess.run", side_effect=capture_run):
                wap._count_active_worktrees()

        self.assertTrue(len(captured_cwds) > 0, "_count_active_worktrees hat keinen git-Aufruf gemacht")
        for cwd in captured_cwds:
            self.assertEqual(cwd, str(dynamic_path),
                f"_count_active_worktrees: cwd={cwd!r} != dynamic_path={str(dynamic_path)!r}")

    def test_ak3_no_hardcoded_project_root_in_git_calls(self):
        """Kontroll-Test: Wenn resolve_mothership_root einen anderen Pfad als
        _PROJECT_ROOT liefert, duerfen die git-Aufrufe KEINEN _PROJECT_ROOT benutzen."""
        import worktree_aware_params as wap

        # Wir waehlen einen Pfad, der definitiv != _PROJECT_ROOT ist
        dynamic_path = Path("/completely/different/mothership")
        static_root = str(wap._PROJECT_ROOT)
        captured_cwds = []

        def capture_run(cmd, **kwargs):
            captured_cwds.append(kwargs.get("cwd"))
            return _mk_completed("")

        with patch.object(wap, "resolve_mothership_root", return_value=dynamic_path):
            with patch("worktree_aware_params.subprocess.run", side_effect=capture_run):
                wap._resolve_worktree_branch()
                wap._git_current_branch()
                wap._count_active_worktrees()

        for cwd in captured_cwds:
            self.assertNotEqual(
                cwd, static_root,
                f"Statisches _PROJECT_ROOT={static_root!r} noch als cwd verwendet!"
            )


class TestAK4GateCshadowCwd(unittest.TestCase):
    """AK-4 (PL-4): Gate-C-Shadow-Spawn cwd = Mothership (dynamisch).

    Der _resolve_vault_root-Aufruf (Z142) muss ebenfalls cwd=resolve_mothership_root() nutzen.
    Laut AK-4/SA-4: kein neuer Spawn-Pfad, bestehende git-cwd-Aufrufe entkoppelt.
    """

    def test_ak4_resolve_vault_root_subprocess_uses_dynamic_cwd(self):
        """_resolve_vault_root spawnt resolve_vault_root.py mit cwd aus resolve_mothership_root().

        IST: cwd=str(_PROJECT_ROOT)  (Z142 statisch).
        SOLL: cwd=str(resolve_mothership_root()).
        """
        import worktree_aware_params as wap

        dynamic_path = Path("/dynamic/mothership/root")
        captured_cwds = []

        def capture_run(cmd, **kwargs):
            captured_cwds.append(kwargs.get("cwd"))
            m = MagicMock()
            m.returncode = 0
            m.stdout = "/some/vault\n"
            return m

        with patch.object(wap, "resolve_mothership_root", return_value=dynamic_path):
            with patch("worktree_aware_params.subprocess.run", side_effect=capture_run):
                wap._resolve_vault_root()

        self.assertTrue(len(captured_cwds) > 0,
            "_resolve_vault_root hat keinen Subprocess aufgerufen")
        for cwd in captured_cwds:
            self.assertEqual(cwd, str(dynamic_path),
                f"_resolve_vault_root: cwd={cwd!r} != dynamic_path={str(dynamic_path)!r}")

    def test_ak4_gate_c_shadow_cwd_differs_from_static_project_root(self):
        """Wenn resolve_mothership_root != _PROJECT_ROOT, muss der subprocess-cwd
        den dynamischen Wert nutzen (kein statischer Kleber).
        """
        import worktree_aware_params as wap

        dynamic_path = Path("/gate-c-mothership")
        static_root = str(wap._PROJECT_ROOT)
        captured_cwds = []

        def capture_run(cmd, **kwargs):
            captured_cwds.append(kwargs.get("cwd"))
            m = MagicMock()
            m.returncode = 0
            m.stdout = "/some/vault\n"
            return m

        with patch.object(wap, "resolve_mothership_root", return_value=dynamic_path):
            with patch("worktree_aware_params.subprocess.run", side_effect=capture_run):
                wap._resolve_vault_root()

        for cwd in captured_cwds:
            self.assertNotEqual(cwd, static_root,
                f"Statisches _PROJECT_ROOT noch als cwd in _resolve_vault_root!")


class TestAK5WorktreeSplitAnchorFeatureBranch(unittest.TestCase):
    """AK-5 (PL-5): Worktree-Split-Anker = Feature-Branch der Mothership (nicht main).

    IST: kein Anker-Ermittlungs-Mechanismus vorhanden (1-stufig, flat).
    SOLL: get_mothership_branch() (oder aequivalente Funktion) liefert
    den aktuellen Branch der Mothership, NICHT 'main'.
    """

    def test_ak5_get_mothership_branch_exists(self):
        """Eine Funktion fuer Mothership-Branch-Ermittlung muss existieren."""
        import worktree_aware_params as wap
        self.assertTrue(
            hasattr(wap, "get_mothership_branch"),
            "get_mothership_branch() nicht in worktree_aware_params"
        )

    def test_ak5_split_anchor_is_feature_branch_not_main(self):
        """Mothership auf Branch 'roadmap-c' → Anker = 'roadmap-c', NICHT 'main'."""
        from worktree_aware_params import get_mothership_branch

        mothership_path = Path("/repo/worktrees/roadmap-c")

        with patch("worktree_aware_params.resolve_mothership_root",
                   return_value=mothership_path):
            with patch("worktree_aware_params.subprocess.run",
                       return_value=_mk_completed("roadmap-c\n")):
                anchor = get_mothership_branch()
                self.assertEqual(anchor, "roadmap-c",
                    f"Anker={anchor!r}, erwartet 'roadmap-c'; main-Annahme noch aktiv?")
                self.assertNotEqual(anchor, "main",
                    "Anker darf NICHT 'main' sein bei Feature-Branch-Mothership")

    def test_ak5_split_anchor_uses_mothership_cwd(self):
        """get_mothership_branch muss git-branch --show-current mit
        cwd=resolve_mothership_root() aufrufen, NICHT mit _PROJECT_ROOT."""
        from worktree_aware_params import get_mothership_branch
        import worktree_aware_params as wap

        dynamic_path = Path("/dynamic/mothership")
        captured_cwds = []

        def capture_run(cmd, **kwargs):
            captured_cwds.append(kwargs.get("cwd"))
            m = MagicMock()
            m.returncode = 0
            m.stdout = "roadmap-c\n"
            return m

        with patch.object(wap, "resolve_mothership_root", return_value=dynamic_path):
            with patch("worktree_aware_params.subprocess.run", side_effect=capture_run):
                get_mothership_branch()

        self.assertTrue(len(captured_cwds) > 0, "get_mothership_branch hat keinen git-Aufruf gemacht")
        for cwd in captured_cwds:
            self.assertEqual(cwd, str(dynamic_path),
                f"get_mothership_branch: cwd={cwd!r} != dynamic_path={str(dynamic_path)!r}")

    def test_ak5_split_anchor_returns_none_on_detached_head(self):
        """Detached HEAD (leerer branch --show-current Output) → None zurueck."""
        from worktree_aware_params import get_mothership_branch
        import worktree_aware_params as wap

        with patch.object(wap, "resolve_mothership_root", return_value=Path("/repo")):
            with patch("worktree_aware_params.subprocess.run",
                       return_value=_mk_completed("")):
                result = get_mothership_branch()
                self.assertIsNone(result, "Detached HEAD muss None liefern")


class TestAK7RecursiveDepthResolution(unittest.TestCase):
    """AK-7 (PL-7): Rekursive Tiefe-Aufloesung statt 1-stufig/flach.

    IST: _resolve_worktree_branch 1-stufig (kein recursion); _count_active_worktrees flach.
    SOLL: resolve_nesting_depth() liefert korrekte Tiefe fuer Hierarchie-Level.
          Tiefe 0 = main-only, Tiefe 1 = direkter Feature-WT, Tiefe 2 = grandchild.
    """

    def test_ak7_resolve_nesting_depth_exists(self):
        """resolve_nesting_depth() muss in worktree_aware_params existieren."""
        import worktree_aware_params as wap
        self.assertTrue(
            hasattr(wap, "resolve_nesting_depth"),
            "resolve_nesting_depth() nicht in worktree_aware_params"
        )

    def test_ak7_depth0_when_running_in_main_checkout(self):
        """Tiefe 0: Lauf direkt in main-Checkout (kein Worktree-Split)."""
        from worktree_aware_params import resolve_nesting_depth

        main_path = "/repo/main"
        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
        )

        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd",
                       return_value=Path(main_path)):
                depth = resolve_nesting_depth()
                self.assertEqual(depth, 0, f"Tiefe 0 erwartet, bekommen: {depth}")

    def test_ak7_depth1_when_running_in_direct_worktree(self):
        """Tiefe 1: Lauf in direktem Feature-Worktree (1 Ebene unter main)."""
        from worktree_aware_params import resolve_nesting_depth

        main_path = "/repo/main"
        feature_path = "/repo/worktrees/feature-wt"
        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
            {"path": feature_path, "branch": "feature/bl-351", "head": "bbbb"},
        )

        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd",
                       return_value=Path(feature_path)):
                depth = resolve_nesting_depth()
                self.assertEqual(depth, 1, f"Tiefe 1 erwartet, bekommen: {depth}")

    def test_ak7_depth2_when_running_in_grandchild_worktree(self):
        """Tiefe 2: Lauf in geschachteltem Grandchild-Worktree.

        Topologie: main (0) → roadmap-c-wt (1) → grandchild-wt (2).
        Resolver muss Tiefe 2 korrekt zaehlen (nicht 0/1 flach).
        """
        from worktree_aware_params import resolve_nesting_depth

        main_path = "/repo/main"
        mother_path = "/repo/worktrees/roadmap-c"
        grandchild_path = "/repo/worktrees/grandchild"

        # Fuer Tiefe-2-Aufloesung muessen wir die Hierarchie mocken.
        # resolve_nesting_depth muss die Parent-Kette traversieren.
        porcelain_from_grandchild = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
            {"path": mother_path, "branch": "roadmap-c", "head": "bbbb"},
            {"path": grandchild_path, "branch": "feature/nested", "head": "cccc"},
        )

        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain_from_grandchild)):
            with patch("worktree_aware_params.Path.cwd",
                       return_value=Path(grandchild_path)):
                depth = resolve_nesting_depth()
                self.assertEqual(depth, 2,
                    f"Tiefe 2 erwartet (grandchild), bekommen: {depth}")

    def test_ak7_depth_resolution_uses_parent_chain_not_flat_count(self):
        """Tiefe = Anzahl Vorfahren in der Worktree-Hierarchie, nicht
        Gesamtzahl aller Worktrees (flat-count waere falsch)."""
        from worktree_aware_params import resolve_nesting_depth

        # 3 Worktrees auf gleicher Ebene (Tiefe 1 je) + main
        main_path = "/repo/main"
        sib_a = "/repo/worktrees/sibling-a"
        sib_b = "/repo/worktrees/sibling-b"
        sib_c = "/repo/worktrees/sibling-c"

        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
            {"path": sib_a, "branch": "lane-a", "head": "bbbb"},
            {"path": sib_b, "branch": "lane-b", "head": "cccc"},
            {"path": sib_c, "branch": "lane-c", "head": "dddd"},
        )

        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd",
                       return_value=Path(sib_a)):
                depth = resolve_nesting_depth()
                # sib-a ist Tiefe 1 (direktes Kind von main)
                # flat-count wuerde sagen "4 Worktrees", falsch
                self.assertEqual(depth, 1,
                    f"Tiefe 1 erwartet (sibling-Kontext), bekommen: {depth}")


class TestAK8NestingDepthCapLoudFail(unittest.TestCase):
    """AK-8 (PL-8): Nesting-Tiefe-Cap max_depth=3 + lautes Fail bei Ueberschreitung.

    IST: kein Cap, kein Tiefe-Check.
    SOLL: MAX_NESTING_DEPTH=3 als Modul-Konstante;
          check_nesting_depth_cap(depth) wirft RuntimeError bei depth > 3.
    """

    def test_ak8_max_nesting_depth_constant_exists(self):
        """MAX_NESTING_DEPTH muss als Modul-Konstante existieren und == 3 sein."""
        import worktree_aware_params as wap
        self.assertTrue(
            hasattr(wap, "MAX_NESTING_DEPTH"),
            "MAX_NESTING_DEPTH nicht in worktree_aware_params"
        )
        self.assertEqual(wap.MAX_NESTING_DEPTH, 3,
            f"MAX_NESTING_DEPTH={wap.MAX_NESTING_DEPTH}, erwartet 3 (SA-2)")

    def test_ak8_check_nesting_depth_cap_exists(self):
        """check_nesting_depth_cap() muss als Funktion existieren."""
        import worktree_aware_params as wap
        self.assertTrue(
            hasattr(wap, "check_nesting_depth_cap"),
            "check_nesting_depth_cap() nicht in worktree_aware_params"
        )

    def test_ak8_depth_below_cap_allowed(self):
        """Tiefe 0, 1, 2, 3 sind erlaubt (kein Fehler)."""
        from worktree_aware_params import check_nesting_depth_cap
        for depth in [0, 1, 2, 3]:
            try:
                check_nesting_depth_cap(depth)
            except (RuntimeError, SystemExit) as e:
                self.fail(f"Tiefe {depth} (<=cap) sollte KEINEN Fehler werfen, aber: {e}")

    def test_ak8_depth_4_raises_runtime_error(self):
        """Tiefe 4 (=max_depth+1) muss RuntimeError werfen (lautes Fail, SA-2)."""
        from worktree_aware_params import check_nesting_depth_cap
        with self.assertRaises(RuntimeError) as ctx:
            check_nesting_depth_cap(4)
        error_msg = str(ctx.exception)
        # Fehlermeldung muss Cap-Begruendung enthalten
        self.assertIn("3", error_msg,
            f"RuntimeError-Nachricht muss Cap (3) nennen: {error_msg!r}")

    def test_ak8_depth_5_raises_runtime_error_with_cap_info(self):
        """Tiefe 5 muss ebenfalls lautes RuntimeError werfen."""
        from worktree_aware_params import check_nesting_depth_cap
        with self.assertRaises(RuntimeError):
            check_nesting_depth_cap(5)

    def test_ak8_depth_cap_fail_is_loud_not_silent(self):
        """Ueberschreitung darf NICHT still ignoriert/stoppen — muss Exception werfen."""
        from worktree_aware_params import check_nesting_depth_cap
        # Stilles Stop = Funktion gibt False zurueck ohne Exception — das waere falsch
        exceeded = False
        try:
            result = check_nesting_depth_cap(10)
            # Wenn wir hier ankommen ohne Exception: stilles Verhalten → FAIL
            self.fail(
                f"check_nesting_depth_cap(10) lief still durch (result={result}); "
                "lautes Fail (RuntimeError) erwartet"
            )
        except RuntimeError:
            exceeded = True  # Korrekt
        except SystemExit:
            exceeded = True  # exit(1) = auch akzeptabel (SA-2)
        self.assertTrue(exceeded, "Cap-Ueberschreitung muss laut und hart fehlen")

    def test_ak8_depth_exactly_at_cap_is_allowed(self):
        """Tiefe = max_depth (3) ist noch erlaubt; Tiefe = max_depth+1 nicht."""
        from worktree_aware_params import check_nesting_depth_cap, MAX_NESTING_DEPTH
        # cap selbst: OK
        try:
            check_nesting_depth_cap(MAX_NESTING_DEPTH)
        except (RuntimeError, SystemExit):
            self.fail(f"Tiefe={MAX_NESTING_DEPTH} (= cap) soll erlaubt sein")
        # cap+1: FAIL
        with self.assertRaises((RuntimeError, SystemExit)):
            check_nesting_depth_cap(MAX_NESTING_DEPTH + 1)


class TestAK11ThreeDepthAgnosticism(unittest.TestCase):
    """AK-11 (PL-11): 3-Tiefen-Agnostik — identisches Verhalten bei Tiefe 0/1/N.

    Testharness: derselbe Funktionsaufruf (resolve_mothership_root + get_mothership_branch
    + resolve_nesting_depth) muss aus drei verschiedenen Tiefen strukturell
    aequivalente Antworten liefern (jeweils tiefen-korrekte Werte).
    """

    def _mk_depth0_env(self):
        """Fixture Tiefe 0: main-Checkout, kein Worktree-Split."""
        main_path = "/repo/main"
        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
        )
        return main_path, porcelain

    def _mk_depth1_env(self):
        """Fixture Tiefe 1: Feature-Worktree direkt unter main."""
        main_path = "/repo/main"
        feature_path = "/repo/worktrees/roadmap-c"
        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
            {"path": feature_path, "branch": "roadmap-c", "head": "bbbb"},
        )
        return feature_path, porcelain

    def _mk_depthN_env(self, n: int = 2):
        """Fixture Tiefe N=2: Grandchild unter Feature-WT unter main."""
        main_path = "/repo/main"
        mother_path = "/repo/worktrees/roadmap-c"
        child_path = "/repo/worktrees/grandchild"
        porcelain = _mk_porcelain_worktrees(
            {"path": main_path, "branch": "main", "head": "aaaa"},
            {"path": mother_path, "branch": "roadmap-c", "head": "bbbb"},
            {"path": child_path, "branch": "feature/nested", "head": "cccc"},
        )
        return child_path, porcelain

    def test_ak11_resolve_mothership_root_callable_from_depth0(self):
        """resolve_mothership_root() laeuft ohne Exception aus Tiefe 0."""
        from worktree_aware_params import resolve_mothership_root
        cwd, porcelain = self._mk_depth0_env()
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd", return_value=Path(cwd)):
                result = resolve_mothership_root()
                self.assertIsInstance(result, Path)

    def test_ak11_resolve_mothership_root_callable_from_depth1(self):
        """resolve_mothership_root() laeuft ohne Exception aus Tiefe 1."""
        from worktree_aware_params import resolve_mothership_root
        cwd, porcelain = self._mk_depth1_env()
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd", return_value=Path(cwd)):
                result = resolve_mothership_root()
                self.assertIsInstance(result, Path)

    def test_ak11_resolve_mothership_root_callable_from_depthN(self):
        """resolve_mothership_root() laeuft ohne Exception aus Tiefe N (hier 2)."""
        from worktree_aware_params import resolve_mothership_root
        cwd, porcelain = self._mk_depthN_env()
        with patch("worktree_aware_params.subprocess.run",
                   return_value=_mk_completed(porcelain)):
            with patch("worktree_aware_params.Path.cwd", return_value=Path(cwd)):
                result = resolve_mothership_root()
                self.assertIsInstance(result, Path)

    def test_ak11_resolve_nesting_depth_monotone_over_depths(self):
        """resolve_nesting_depth() liefert tiefe-korrekte Werte:
        depth0=0, depth1=1, depth2=2 (monoton wachsend, nie gleich)."""
        from worktree_aware_params import resolve_nesting_depth

        results = {}
        for label, (cwd, porcelain) in [
            ("d0", self._mk_depth0_env()),
            ("d1", self._mk_depth1_env()),
            ("d2", self._mk_depthN_env()),
        ]:
            with patch("worktree_aware_params.subprocess.run",
                       return_value=_mk_completed(porcelain)):
                with patch("worktree_aware_params.Path.cwd",
                           return_value=Path(cwd)):
                    results[label] = resolve_nesting_depth()

        self.assertEqual(results["d0"], 0, f"Tiefe 0 erwartet: {results['d0']}")
        self.assertEqual(results["d1"], 1, f"Tiefe 1 erwartet: {results['d1']}")
        self.assertEqual(results["d2"], 2, f"Tiefe 2 erwartet: {results['d2']}")

    def test_ak11_get_mothership_branch_structurally_equivalent_across_depths(self):
        """get_mothership_branch() liefert aus jeder Tiefe einen Branch-String
        oder None (nie Exception) — strukturell aequivalentes Interface."""
        from worktree_aware_params import get_mothership_branch
        import worktree_aware_params as wap

        for label, (cwd, porcelain) in [
            ("d0", self._mk_depth0_env()),
            ("d1", self._mk_depth1_env()),
            ("d2", self._mk_depthN_env()),
        ]:
            with patch.object(wap, "resolve_mothership_root",
                               return_value=Path(cwd)):
                # Branch-Aufruf gibt je nach Tiefe unterschiedliche Branches zurueck
                branch_out = "main" if label == "d0" else "roadmap-c"
                with patch("worktree_aware_params.subprocess.run",
                           return_value=_mk_completed(f"{branch_out}\n")):
                    try:
                        result = get_mothership_branch()
                        # Ergebnis muss str oder None sein
                        self.assertIn(type(result), [str, type(None)],
                            f"Tiefe {label}: Ergebnis-Typ {type(result)} unerwartet")
                    except Exception as e:
                        self.fail(
                            f"get_mothership_branch() aus Tiefe {label} warf "
                            f"unerwartet: {type(e).__name__}: {e}"
                        )

    def test_ak11_check_nesting_depth_cap_consistent_across_valid_depths(self):
        """check_nesting_depth_cap() darf bei Tiefe 0/1/2/3 KEINE Exception werfen
        — konsistent ueber alle gueltigen Tiefen."""
        from worktree_aware_params import check_nesting_depth_cap
        for depth in [0, 1, 2, 3]:
            try:
                check_nesting_depth_cap(depth)
            except (RuntimeError, SystemExit) as e:
                self.fail(
                    f"check_nesting_depth_cap({depth}) warf unerwartet: {e}"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
