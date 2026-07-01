#!/usr/bin/env python3
"""
test_g3_worktree_forward_verify.py — BL-317 SB-6 (AK-6) Forward-Verify-Harness.

Messkriterium BL-230 Z94 (ACTIONABLE-Anteil). Verifiziert dass die G3-Verdrahtung
(SB-1..5) in einem ECHTEN, kurzlebigen Test-Worktree zusammenhält. KEIN Produktiv-
Code, KEINE SB-1..5-Datei wird geändert — reines read/measure.

SICHERHEIT (nicht verhandelbar, Spec §HÖCHSTE VORSICHT):
  - Baseline = 1 Worktree (Main). B-3-Leiche ist ENTFERNT (Spec §0). Test-Worktrees
    liegen AUSSCHLIESSLICH in os.tmpdir() mit eindeutigem Präfix 'bl317-wt-' (NIE im
    Repo-Tree). Teardown IMMER in finally + 'git worktree prune' (kein Leak).
  - Audit = read-only Set-Subtraktion (post \\ baseline). Es entfernt NICHTS aus dem
    Baseline-Set. B-3-immun: ein bereits vorhandener Worktree wäre im baseline-Set und
    erschiene nie im delta (kein False-Positive). Nur der Test räumt seinen eigenen WT.

Verify-Contract (Spec AK-6 + Prompt-Scope a/b/c):
  (a) HOOK-KETTE GRÜN: `worktree_hook_router.py hook` liefert im Worktree-Kontext
      {"continue": true} (fail-open, INV-G3-1). Der Hook-Router blockiert NIE einen
      Tool-Call im Worktree.
  (b) CURRENT_CONTEXT IM WORKTREE-CWD: current_context.py löst, aufgerufen MIT
      CWD=Worktree (ein fremder git-Tree, NICHT die Repo-Root), den vault_root korrekt
      auf (SB-1 __file__-Anker greift). DIESE Assertion wäre OHNE SB-1 GEFAILT:
      vor SB-1 lief der Resolver-Subprocess über einen cwd-relativen Skript-String
      ('.claude/scripts/resolve_vault_root.py') → im Worktree-cwd nicht gefunden →
      vault_root=None (BL-310-Klasse). Beleg: test_b_*WOULD_HAVE_FAILED* unten.
  (c) ABS-LEAK-PROBE / DISKRIMINATOR-GRENZE: classify_write_surface klassifiziert
      einen abs-Vault-Pfad als "vault" (würde NICHT worktree-isoliert, G0/BL-334) und
      einen cwd-relativen Code-Pfad als "code" (Isolations-Grenze, INV-G3-3).

DORMANT-FORWARD (NICHT gebaut, nur dokumentiert):
  Die echte „≥10 konsekutive Produktions-Batches im Worktree mit 100% Hook-Grün +
  0 Orphans"-Messung (BL-230 Z94) braucht echte Produktions-Worktrees (N>=2) und ist
  an die BL-230-Wellen-Phase forward-delegiert. Heute N=1 → 0 Concurrency → der
  Live-Anteil ist strukturell nicht messbar (nur 1 Tree existiert). Dieser Harness
  liefert den sofort-messbaren Anteil: 1 Hook-Suite-Lauf im echten Worktree = grün +
  current_context-CWD-Auflösung + Diskriminator-Grenze, leak-frei.
  Siehe test_dormant_production_measurement_is_documented().
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

# In-process Import des Diskriminators (SB-5). Reuse, kein Re-Bau.
import write_surface  # noqa: E402

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
_HOOK_ROUTER = _SCRIPT_DIR / "worktree_hook_router.py"
_CURRENT_CONTEXT = _SCRIPT_DIR / "resolve_vault_root.py"  # nur Existenz-Anker (s.u.)
_CURRENT_CONTEXT_SCRIPT = _SCRIPT_DIR / "current_context.py"
_RESOLVE_VAULT_ROOT = _SCRIPT_DIR / "resolve_vault_root.py"
PY = sys.executable


# ── Worktree-Lifecycle-Helper (BL-316-Pattern, ECHT, kein Mock) ──────────────────

def _git(cmd: list[str], cwd: Path | str = _REPO_ROOT) -> subprocess.CompletedProcess:
    """Führt ein git-Kommando aus (Repo-Root cwd default)."""
    return subprocess.run(
        ["git", *cmd], cwd=str(cwd), capture_output=True, text=True, timeout=30,
    )


def _wt_norm(p: str) -> str:
    """Pfad-Normalisierung für den list-Membership-Vergleich (Windows case-insensitiv,
    Backslash→Slash, Trailing-Slash strippen). git speichert Forward-Slash-Pfade."""
    return str(p).replace("\\", "/").rstrip("/").lower()


def worktree_baseline() -> list[str]:
    """Aktueller Worktree-Snapshot (Porcelain) als Liste roher absoluter Pfade."""
    out = _git(["worktree", "list", "--porcelain"]).stdout
    return [
        line[len("worktree "):]
        for line in out.splitlines()
        if line.startswith("worktree ")
    ]


def worktree_audit(baseline: list[str], current: list[str]) -> dict:
    """Teardown-Audit: delta = current \\ baseline (normiert). Read-only Set-Subtraktion;
    ein Baseline-Worktree erscheint nie im delta (kein False-Positive)."""
    base_set = {_wt_norm(p) for p in (baseline or [])}
    delta = [p for p in (current or []) if _wt_norm(p) not in base_set]
    return {
        "baseline": [_wt_norm(p) for p in (baseline or [])],
        "current": [_wt_norm(p) for p in (current or [])],
        "delta": delta,
    }


class _RealTestWorktree:
    """Context-Manager: echter, kurzlebiger Test-Worktree in os.tmpdir().

    add --no-checkout --detach (schnell, leichten-frei) → yield Path →
    finally: remove --force + prune (IMMER, auch bei Exception → kein Leak).
    """

    def __init__(self) -> None:
        tmp_real = os.path.realpath(tempfile.gettempdir())
        self.path = Path(tmp_real) / f"bl317-wt-{uuid.uuid4().hex[:12]}"
        # Sicherheits-Assert: der Worktree-Pfad darf NICHT unter REPO_ROOT liegen.
        assert not _wt_norm(str(self.path)).startswith(_wt_norm(str(_REPO_ROOT)) + "/"), \
            "Test-Worktree-Pfad darf NICHT im Repo-Tree liegen (Leak-Schutz)"

    def __enter__(self) -> Path:
        cp = _git(["worktree", "add", "--no-checkout", "--detach", str(self.path), "HEAD"])
        assert cp.returncode == 0, f"worktree add fehlgeschlagen: {cp.stderr!r}"
        return self.path

    def __exit__(self, *exc) -> bool:
        # Teardown IMMER (kein Leak), Fehler beim Cleanup schlucken.
        try:
            _git(["worktree", "remove", "--force", str(self.path)])
        except Exception:
            pass
        try:
            _git(["worktree", "prune"])
        except Exception:
            pass
        return False  # Exceptions NICHT unterdrücken


def _parse_json_stdout(stdout: str) -> dict:
    """Extrahiert das JSON-Objekt aus stdout (Deprecation-Warnings → stderr; robust ab '{')."""
    idx = stdout.find("{")
    assert idx != -1, f"kein JSON in stdout: {stdout!r}"
    return json.loads(stdout[idx:])


# ── (a) Hook-Kette grün im Worktree ──────────────────────────────────────────────

class TestAHookChainGreenInWorktree(unittest.TestCase):
    """(a) worktree_hook_router.py hook liefert {continue:true} im Worktree-Kontext."""

    def test_a_router_hook_returns_continue_true_in_worktree(self):
        """Der Hook-Router blockiert im echten Worktree-cwd NIE (fail-open, INV-G3-1)."""
        with _RealTestWorktree() as wt:
            cp = subprocess.run(
                [PY, str(_HOOK_ROUTER), "hook"],
                input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": "x.py"}}),
                cwd=str(wt), capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(cp.returncode, 0, f"Hook-Router muss exit 0 liefern; stderr={cp.stderr!r}")
            out = _parse_json_stdout(cp.stdout)
            self.assertIs(out.get("continue"), True,
                          "Hook-Kette im Worktree muss continue:true sein (fail-open)")

    def test_a_router_hook_empty_stdin_still_continue(self):
        """Leerer stdin im Worktree → fail-open continue:true (kein Block)."""
        with _RealTestWorktree() as wt:
            cp = subprocess.run(
                [PY, str(_HOOK_ROUTER), "hook"],
                input="", cwd=str(wt), capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(cp.returncode, 0)
            self.assertIs(_parse_json_stdout(cp.stdout).get("continue"), True)

    def test_a_router_namespace_resolves_in_worktree(self):
        """`namespace`-Subcommand läuft im Worktree-cwd ohne Crash (mode single|multi)."""
        with _RealTestWorktree() as wt:
            cp = subprocess.run(
                [PY, str(_HOOK_ROUTER), "namespace"],
                cwd=str(wt), capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(cp.returncode, 0, f"stderr={cp.stderr!r}")
            self.assertIn("mode=", cp.stdout)


# ── (b) current_context im Worktree-cwd löst vault_root auf (SB-1-Beleg) ─────────

class TestBCurrentContextResolvesInWorktreeCwd(unittest.TestCase):
    """(b) SB-1 __file__-Anker greift bei CWD=Worktree (fremder git-Tree, NICHT Repo-Root)."""

    def test_b_vault_root_resolves_when_cwd_is_worktree_WOULD_HAVE_FAILED_without_SB1(self):
        """current_context.py MIT CWD=Worktree → vault_root NICHT None.

        BELEG (Prompt-Scope): diese Assertion wäre OHNE SB-1 GEFAILT. Vor SB-1 rief
        current_context._resolve_vault_root() den Resolver über einen cwd-relativen
        String-Pfad auf; mit CWD=Worktree (≠ Repo-Root) fand der Subprocess das Skript
        nicht → vault_root=None. SB-1 (__file__-Anker + cwd=Repo-Root im Subprocess)
        macht die Auflösung CWD-unabhängig. Der Worktree ist der härteste Fall: ein
        SEPARATER git-Arbeitsbaum, dessen .git ein Datei-Pointer ist."""
        with _RealTestWorktree() as wt:
            cp = subprocess.run(
                [PY, str(_CURRENT_CONTEXT_SCRIPT), "--format=json"],
                cwd=str(wt), capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(cp.returncode, 0, f"stderr={cp.stderr!r}")
            ctx = _parse_json_stdout(cp.stdout)
            self.assertIsNotNone(
                ctx["vault_root"],
                "vault_root MUSS bei CWD=Worktree aufgelöst sein (SB-1 __file__-Anker); "
                "None hier = SB-1-Regression (BL-310-Klasse)",
            )

    def test_b_worktree_vault_root_equals_repo_root_vault_root(self):
        """vault_root aus Worktree-cwd == vault_root aus Repo-Root (Anker, nicht CWD)."""
        from_root = _parse_json_stdout(
            subprocess.run([PY, str(_CURRENT_CONTEXT_SCRIPT), "--format=json"],
                           cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=30).stdout
        )
        with _RealTestWorktree() as wt:
            from_wt = _parse_json_stdout(
                subprocess.run([PY, str(_CURRENT_CONTEXT_SCRIPT), "--format=json"],
                               cwd=str(wt), capture_output=True, text=True, timeout=30).stdout
            )
        self.assertEqual(
            from_wt["vault_root"], from_root["vault_root"],
            "vault_root muss über __file__-Anker CWD-unabhängig sein",
        )

    def test_b_cwd_field_reflects_the_worktree(self):
        """Das cwd-FELD reflektiert den echten Worktree-cwd (nicht den Anker)."""
        with _RealTestWorktree() as wt:
            ctx = _parse_json_stdout(
                subprocess.run([PY, str(_CURRENT_CONTEXT_SCRIPT), "--format=json"],
                               cwd=str(wt), capture_output=True, text=True, timeout=30).stdout
            )
            self.assertEqual(
                Path(ctx["cwd"]).resolve(), wt.resolve(),
                "cwd-Feld muss der tatsächliche Worktree-Arbeitsbaum sein",
            )

    def test_b_never_empty_stdout_in_worktree(self):
        """fail-safe non-regression (INV-G3-2): stdout im Worktree NIE leer/non-JSON."""
        with _RealTestWorktree() as wt:
            cp = subprocess.run(
                [PY, str(_CURRENT_CONTEXT_SCRIPT), "--format=json"],
                cwd=str(wt), capture_output=True, text=True, timeout=30,
            )
            self.assertTrue(cp.stdout.strip(), "stdout darf im Worktree NIE leer sein")
            _parse_json_stdout(cp.stdout)  # parsebar


# ── (c) abs-Leak-Probe / Diskriminator-Grenze (SB-5) ─────────────────────────────

class TestCAbsLeakDiscriminator(unittest.TestCase):
    """(c) classify_write_surface zeichnet die Isolations-Grenze (INV-G3-3)."""

    def _vault_root(self) -> str:
        cp = subprocess.run([PY, str(_RESOLVE_VAULT_ROOT)],
                            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=10)
        vr = cp.stdout.strip()
        self.assertTrue(vr, "resolve_vault_root muss einen Pfad liefern (Vorbedingung)")
        return vr

    def test_c_abs_vault_path_classified_as_vault(self):
        """Ein abs-Pfad UNTER vault_root → 'vault' (würde NICHT worktree-isoliert; G0/BL-334)."""
        vr = self._vault_root()
        target = os.path.join(vr, "Backlog", "BL-317", "_manifest.md")
        self.assertEqual(
            write_surface.classify_write_surface(target, vr), write_surface.VAULT,
            "abs-Pfad unter vault_root muss als 'vault' klassifiziert werden (Leak-Grenze)",
        )

    def test_c_vault_root_itself_is_vault(self):
        """Der vault_root-Pfad selbst → 'vault' (Grenz-Gleichheit, kein off-by-one)."""
        vr = self._vault_root()
        self.assertEqual(write_surface.classify_write_surface(vr, vr), write_surface.VAULT)

    def test_c_cwd_relative_code_path_classified_as_code(self):
        """Ein cwd-relativer Code-Pfad → 'code' (worktree-isolierbar; MUSS cwd-relativ bleiben)."""
        vr = self._vault_root()
        code_rel = os.path.join(".claude", "scripts", "worktree_hook_router.py")
        self.assertEqual(
            write_surface.classify_write_surface(code_rel, vr), write_surface.CODE,
            "cwd-relativer Code-Pfad muss als 'code' klassifiziert werden (Isolations-Seite)",
        )

    def test_c_abs_repo_code_path_classified_as_code(self):
        """Ein abs-Pfad im Repo-Tree (außerhalb vault_root) → 'code'."""
        vr = self._vault_root()
        repo_code = str(_REPO_ROOT / ".claude" / "scripts" / "current_context.py")
        self.assertEqual(write_surface.classify_write_surface(repo_code, vr), write_surface.CODE)

    def test_c_prefix_collision_not_misclassified(self):
        """Praefix-Kollision (vault_root + 'X' Sibling) darf NICHT als 'vault' gelten
        (os.sep-Grenze, gegen OmniCommandX vs OmniCommand)."""
        vr = self._vault_root()
        sibling = vr.rstrip("/\\") + "X" + os.sep + "file.md"
        self.assertEqual(
            write_surface.classify_write_surface(sibling, vr), write_surface.CODE,
            "Praefix-Kollisions-Sibling darf nicht als 'vault' klassifiziert werden",
        )

    def test_c_resolve_code_write_rebases_relative_into_worktree(self):
        """resolve_code_write(rel, worktree) hängt relativen Code-Pfad UNTER den Worktree
        (die Isolation-Mechanik) — abs bleibt abs (os.path.join abs-aware)."""
        wt_cwd = os.path.join(os.path.realpath(tempfile.gettempdir()), "bl317-fake-wt")
        rebased = write_surface.resolve_code_write("out/x.py", wt_cwd, surface="code")
        self.assertTrue(_wt_norm(rebased).startswith(_wt_norm(wt_cwd) + "/"),
                        "relativer Code-Write muss unter den Worktree-cwd rebasen")
        # Vault-Surface bleibt unverändert abs (G0).
        vault_abs = os.path.join(self._vault_root(), "_manifest.md")
        self.assertEqual(write_surface.resolve_code_write(vault_abs, wt_cwd, surface="vault"), vault_abs)


# ── Dormant-Forward-Dokumentation + Leak-Beweis ──────────────────────────────────

class TestDormantAndLeakProof(unittest.TestCase):

    def test_dormant_production_measurement_is_documented(self):
        """Die echte ≥10-Batch-Produktions-Messung (BL-230 Z94) ist DORMANT-forward.

        Dieser Test ist die executable Dokumentation des Deferrals:
        - Bei N=1 (bl_parallel=False, Single-Worktree): der Live-Anteil ist strukturell
          nicht messbar (nur 1 Tree existiert) → Messung dormant, an BL-230-Welle
          delegiert. KEIN Live-Produktions-Lauf hier — by-design dormant.
        - Bei N>=2 (bl_parallel=True, Multi-Worktree-Split, BL-436 DoD): N>=2 Worktrees
          sind erlaubt/erwartet. Die ≥10-Batch-Messung IST dann messbar (nicht mehr
          dormant). Assertion toleriert >=1 ohne Hardcap auf 1.

        KEIN Live-Produktions-Lauf wird hier ausgeführt — reines Baseline-Read.

        BL-436 DoD-Autorisierung: test_g3 toleriert N>=2 bei bl_parallel=true."""
        from worktree_aware_params import resolve_bl_parallel  # lokaler Import (BL-436)
        bl_parallel = resolve_bl_parallel()
        base = worktree_baseline()
        if bl_parallel:
            # Multi-Worktree-Split aktiv: N>=2 erwartet, kein Hardcap auf 1.
            self.assertGreaterEqual(
                len(base), 1,
                f"bl_parallel=True: mindestens 1 Worktree erwartet, gefunden: {len(base)}; "
                "echte ≥10-Batch-Messung ist bei N>=2 NICHT mehr dormant (BL-436 DoD)"
            )
        else:
            # Single-Worktree-Modus: N=1 ist der Normalfall (dormant-forward).
            self.assertGreaterEqual(
                len(base), 1,
                f"bl_parallel=False: mindestens 1 Worktree (Main) erwartet, gefunden: {len(base)}; "
                "echte ≥10-Batch-Messung braucht N>=2 → dormant BL-230-Welle"
            )

    def test_leak_proof_baseline_restored_after_roundtrip(self):
        """LEAK-BEWEIS: nach add+teardown eines Test-Worktrees == Baseline (kein Leak)."""
        baseline = worktree_baseline()
        with _RealTestWorktree() as wt:
            during = worktree_baseline()
            # Während des Roundtrips erscheint der Test-Worktree im delta.
            audit_during = worktree_audit(baseline, during)
            self.assertEqual(len(audit_during["delta"]), 1,
                             "genau der eine Test-Worktree muss im delta erscheinen")
            self.assertEqual(_wt_norm(audit_during["delta"][0]), _wt_norm(str(wt)))
        # Nach Teardown: delta leer → Baseline wiederhergestellt.
        after = worktree_baseline()
        audit_after = worktree_audit(baseline, after)
        self.assertEqual(audit_after["delta"], [],
                         f"LEAK: Test-Worktree nicht aufgeräumt: {audit_after['delta']}")
        self.assertEqual(
            {_wt_norm(p) for p in after}, {_wt_norm(p) for p in baseline},
            "git worktree list muss exakt auf die Baseline zurück (kein Leak)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
