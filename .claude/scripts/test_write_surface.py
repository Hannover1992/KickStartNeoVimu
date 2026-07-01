#!/usr/bin/env python3
"""Tests fuer write_surface.py (BL-317 sub_batch_5, AK-7, two-surface-resolution).

TDD Stage 1 (Atomic), Modus M3. HOECHSTE VORSICHT: beruehrt Pfad-Aufloesungs-
Semantik (Spike-Kern). write_surface.py ist ein NEUES Primitiv (der Zwei-Surface-
Diskriminator + Code-Write-cwd-relativ-Resolver), KEIN Umbau bestehender Resolver.

Spike-Befund: isolation:'worktree' isoliert nur git-Kontext, NICHT abs-Datei-Writes.
Damit Code-Writes worktree-isoliert sind, muessen sie cwd/worktree-relativ aufgeloest
werden; Vault-State-Writes bleiben abs + G0 (BL-334-Lock).

Der (a)/(b)-Diskriminator existiert bereits in guard_vault_write_lock.py
(Z133-140: target startswith vault_root -> b/vault, sonst a/code). write_surface.py
MUSS dieselbe Entscheidung treffen (kein Drift zwischen den zwei Diskriminatoren).

Test-Matrix:
  (a) classify vault-Pfad (unter vault_root)                     -> "vault"
  (b) classify code-Pfad (nicht-vault / Engine-Repo / beliebig)  -> "code"
  (c) Praefix-Kollision (OmniCommandX vs OmniCommand)            -> NICHT vault ("code")
  (d) case-insensitive (Windows)                                 -> "vault"
  (e) resolve_code_write(rel-path, worktree_cwd)                 -> landet unter worktree_cwd
  (f) resolve_code_write fuer vault-Surface                      -> abs unveraendert (G0-Domaene)
  (g) Konsistenz mit guard_vault_write_lock-Klassifikator        -> gleiche Entscheidung
"""
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

import write_surface  # noqa: E402  (Modul existiert in RED-Phase noch nicht)


def _norm(p):
    return os.path.normcase(os.path.abspath(str(p)))


# ── (a) vault-Pfad -> "vault" ────────────────────────────────────────────────
def test_classify_vault_path():
    vault_root = tempfile.mkdtemp(prefix="ws_vault_")
    target = os.path.join(vault_root, "Backlog", "BL-999", "_manifest.md")
    assert write_surface.classify_write_surface(target, vault_root) == "vault", \
        "Pfad unter vault_root muss als 'vault' klassifiziert werden"


def test_classify_vault_root_itself():
    """vault_root selbst (==) ist vault (Spiegel guard-Z137: target_norm == vault_norm)."""
    vault_root = tempfile.mkdtemp(prefix="ws_vault_")
    assert write_surface.classify_write_surface(vault_root, vault_root) == "vault"


# ── (b) code-Pfad -> "code" ──────────────────────────────────────────────────
def test_classify_code_path_engine_repo():
    vault_root = tempfile.mkdtemp(prefix="ws_vault_")
    # Engine-Repo-Pfad liegt NICHT unter vault_root -> "code".
    code_path = str(SCRIPT_DIR / "guard_vault_write_lock.py")
    assert write_surface.classify_write_surface(code_path, vault_root) == "code", \
        "Engine-Repo-Pfad (nicht-vault) muss als 'code' klassifiziert werden"


def test_classify_code_path_arbitrary():
    vault_root = tempfile.mkdtemp(prefix="ws_vault_")
    other = tempfile.mkdtemp(prefix="ws_code_")  # voellig getrenntes Verzeichnis
    code_path = os.path.join(other, "src", "Foo.cs")
    assert write_surface.classify_write_surface(code_path, vault_root) == "code"


# ── (c) Praefix-Kollision -> NICHT vault ─────────────────────────────────────
def test_prefix_collision_not_vault():
    """OmniCommandX darf nicht als unter OmniCommand liegend gelten (os.sep-Grenze)."""
    base = tempfile.mkdtemp(prefix="ws_collide_")
    vault_root = os.path.join(base, "OmniCommand")
    os.makedirs(vault_root, exist_ok=True)
    sibling = os.path.join(base, "OmniCommandX")  # Praefix-Kollision
    os.makedirs(sibling, exist_ok=True)
    target = os.path.join(sibling, "file.md")
    assert write_surface.classify_write_surface(target, vault_root) == "code", \
        "OmniCommandX (Praefix-Kollision) darf NICHT als vault gelten"


# ── (d) case-insensitive (Windows) ───────────────────────────────────────────
def test_case_insensitive_vault():
    vault_root = tempfile.mkdtemp(prefix="ws_case_")
    # Ziel mit anderer Gross-/Kleinschreibung -> auf Windows (normcase) trotzdem vault.
    target = os.path.join(vault_root.upper(), "Backlog", "x.md")
    expected = "vault" if os.path.normcase("A") == os.path.normcase("a") else "code"
    assert write_surface.classify_write_surface(target, vault_root) == expected, \
        "case-insensitive (Windows normcase): upper-cased vault_root-Praefix muss matchen"


# ── (e) resolve_code_write(rel, cwd) -> landet unter cwd ─────────────────────
def test_resolve_code_write_relative_under_cwd():
    worktree_cwd = tempfile.mkdtemp(prefix="ws_wt_")
    resolved = write_surface.resolve_code_write(
        os.path.join("src", "Foo.cs"), worktree_cwd)
    assert _norm(resolved).startswith(_norm(worktree_cwd) + os.sep), \
        f"rel-Code-Pfad muss unter worktree_cwd landen, war {resolved!r}"


def test_resolve_code_write_relative_exact():
    worktree_cwd = tempfile.mkdtemp(prefix="ws_wt_")
    resolved = write_surface.resolve_code_write("Foo.cs", worktree_cwd)
    assert _norm(resolved) == _norm(os.path.join(worktree_cwd, "Foo.cs")), \
        "rel-Pfad muss exakt cwd/rel sein"


# ── (f) resolve_code_write fuer vault-Surface -> abs unveraendert ────────────
def test_resolve_code_write_vault_surface_unchanged():
    """Surface=vault (BL-334/G0-Domaene): abs-Pfad bleibt unveraendert (kein cwd-Rebase)."""
    vault_root = tempfile.mkdtemp(prefix="ws_vault_")
    worktree_cwd = tempfile.mkdtemp(prefix="ws_wt_")
    vault_abs = os.path.join(vault_root, "Backlog", "BL-999", "_manifest.md")
    resolved = write_surface.resolve_code_write(
        vault_abs, worktree_cwd, surface="vault")
    assert _norm(resolved) == _norm(vault_abs), \
        "Surface=vault muss abs-Pfad UNVERAENDERT zurueckgeben (G0-Domaene, BL-334)"


def test_resolve_code_write_absolute_code_unchanged():
    """Surface=code aber abs-Pfad: abs bleibt abs (nur relative werden gegen cwd aufgeloest)."""
    worktree_cwd = tempfile.mkdtemp(prefix="ws_wt_")
    other = tempfile.mkdtemp(prefix="ws_abs_")
    abs_code = os.path.join(other, "Foo.cs")
    resolved = write_surface.resolve_code_write(abs_code, worktree_cwd, surface="code")
    assert _norm(resolved) == _norm(abs_code), \
        "abs-Code-Pfad bleibt abs (os.path.join ignoriert cwd bei abs-Komponente)"


# ── (g) Konsistenz mit guard_vault_write_lock-Diskriminator ──────────────────
def test_consistency_with_guard_discriminator():
    """classify_write_surface trifft DIESELBE vault/code-Entscheidung wie
    guard_vault_write_lock.py fuer dieselben Pfade (kein Drift; AK-7 Konsistenz)."""
    import guard_vault_write_lock as guard

    def guard_says_vault(path, vault_root):
        # Spiegel der Guard-Logik Z133-140 (target_norm == vault_norm oder
        # startswith vault_norm + os.sep).
        target_norm = guard._norm(path)
        vault_norm = guard._norm(vault_root)
        return target_norm == vault_norm or target_norm.startswith(vault_norm + os.sep)

    base = tempfile.mkdtemp(prefix="ws_consist_")
    vault_root = os.path.join(base, "OmniCommand")
    os.makedirs(vault_root, exist_ok=True)
    cases = [
        os.path.join(vault_root, "Backlog", "BL-1", "x.md"),  # vault
        vault_root,                                            # vault (==)
        os.path.join(base, "OmniCommandX", "y.md"),            # code (Kollision)
        os.path.join(base, "Engine", "src", "z.cs"),           # code
        str(SCRIPT_DIR / "write_surface.py"),                  # code
    ]
    for path in cases:
        surf = write_surface.classify_write_surface(path, vault_root)
        guard_vault = guard_says_vault(path, vault_root)
        expected = "vault" if guard_vault else "code"
        assert surf == expected, (
            f"Drift! write_surface={surf!r}, guard={'vault' if guard_vault else 'code'!r} "
            f"fuer {path!r}")


def test_consistency_shares_guard_norm():
    """Bonus: classify nutzt dieselbe Normalisierung wie der Guard (kein subtiler Drift
    bei normcase/abspath). Beide muessen denselben normalisierten Praefix-Match anwenden."""
    import guard_vault_write_lock as guard
    p = "src/../src/Foo.cs"  # nicht-normalisierter rel-Pfad
    vr = tempfile.mkdtemp(prefix="ws_norm_")
    # Beide Diskriminatoren muessen p relativ zum CWD gleich normalisieren -> beide "code".
    assert write_surface.classify_write_surface(p, vr) == "code"
    target_norm = guard._norm(p)
    vault_norm = guard._norm(vr)
    assert not (target_norm == vault_norm or target_norm.startswith(vault_norm + os.sep))


if __name__ == "__main__":
    tests = [
        test_classify_vault_path,
        test_classify_vault_root_itself,
        test_classify_code_path_engine_repo,
        test_classify_code_path_arbitrary,
        test_prefix_collision_not_vault,
        test_case_insensitive_vault,
        test_resolve_code_write_relative_under_cwd,
        test_resolve_code_write_relative_exact,
        test_resolve_code_write_vault_surface_unchanged,
        test_resolve_code_write_absolute_code_unchanged,
        test_consistency_with_guard_discriminator,
        test_consistency_shares_guard_norm,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed+failed} ===")
    sys.exit(0 if failed == 0 else 1)
