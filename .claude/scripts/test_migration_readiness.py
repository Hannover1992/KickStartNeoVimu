"""RED-Worker Tests fuer BL-253 batch_1 (M3) — migration_readiness.py.

RED != GREEN: dieser Worker schreibt NUR Tests. migration_readiness.py existiert
NOCH NICHT (GREEN-Worker baut spaeter). Tests definieren die erwartete API:

  - check_uncommitted(repo) -> dict {green: bool, count: int, ...}   (AK-CHECK-UNCOMMITTED)
  - check_unpushed(repo)    -> dict {green: bool, ahead_of_remote: int, ...} (AK-CHECK-UNPUSHED)
  - check_lane_divergenz(repo, ...) -> dict {green, action, ...}     (AK-CHECK-LANE-DIVERGENZ)
  - check_untracked_product(repo) -> dict {green, untracked_products: list} (AK-CHECK-UNTRACKED-PRODUKT)
  - vault_sync_status(vault_root) -> dict {green/warn, status, ...}  (AK-VAULT-SYNC)
  - migration_ready(repo, vault_root) -> dict {migration_ready, verdict, checks, red_checks} (AK-VERDICT)
  - main(argv) -> int  (CLI: --json, --vault-root, exit 0/1)         (AK-CLI-RESOLVER)

Reine subprocess-git-Mocks. KEIN echter Push/Commit. lane_develop_sync /
resolve_vault_root werden read-only importiert (DRY-Reuse, nicht re-implementiert) —
in den Tests gegen den migration_readiness-Modul-Namespace gepatcht.
"""

import json
import subprocess
from pathlib import Path

import pytest  # noqa: F401  (Fixtures: monkeypatch/tmp_path/capsys)

# Modul unter Test. In der RED-Phase existiert migration_readiness.py NOCH NICHT
# -> harte ImportError beim Collect = beabsichtigtes RED. Der GREEN-Worker baut
# das Modul; dann gruenen die Tests.
import migration_readiness as mr


# ---------------------------------------------------------------------------
# Helpers: subprocess.run-Mock-Fabriken
# ---------------------------------------------------------------------------

def _make_run_stub(responses):
    """Baut einen subprocess.run-Stub.

    responses: dict, das einen Teilstring der Kommando-Liste auf ein
    CompletedProcess-aehnliches Ergebnis (stdout, returncode) mappt — oder
    auf eine Exception, die geworfen wird.
    """

    def _run(cmd, *args, **kwargs):
        joined = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        for needle, result in responses.items():
            if needle in joined:
                if isinstance(result, Exception):
                    raise result
                rc, out = result
                return subprocess.CompletedProcess(
                    args=cmd, returncode=rc, stdout=out, stderr=""
                )
        # Default: leer & erfolgreich
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    return _run


# ===========================================================================
# AK-CHECK-UNCOMMITTED (W1/C1)  — 3 Tests
# ===========================================================================

def test_uncommitted_clean_is_green(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, "")}),
    )
    res = mr.check_uncommitted(str(tmp_path))
    assert res["green"] is True
    assert res["count"] == 0


def test_uncommitted_dirty_is_red_with_count(monkeypatch, tmp_path):
    porcelain = " M x.py\n?? y\n"
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, porcelain)}),
    )
    res = mr.check_uncommitted(str(tmp_path))
    assert res["green"] is False
    # 2 Zeilen Working-Tree-Aenderungen (modified + untracked)
    assert res["count"] == 2


def test_uncommitted_exposes_count_key(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, " M a.py\n M b.py\n M c.py\n")}),
    )
    res = mr.check_uncommitted(str(tmp_path))
    assert "count" in res
    assert res["count"] == 3
    assert res["green"] is False


# ===========================================================================
# AK-CHECK-UNPUSHED (W1/C2)  — 3 Tests
# ===========================================================================

def test_unpushed_zero_is_green(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"rev-list": (0, "0\n")}),
    )
    res = mr.check_unpushed(str(tmp_path))
    assert res["green"] is True
    assert res["ahead_of_remote"] == 0


def test_unpushed_three_is_red(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"rev-list": (0, "3\n")}),
    )
    res = mr.check_unpushed(str(tmp_path))
    assert res["green"] is False
    assert res["ahead_of_remote"] == 3


def test_unpushed_no_upstream_is_marked_not_crash(monkeypatch, tmp_path):
    # @{u} ohne Upstream -> git liefert non-zero / wirft CalledProcessError.
    err = subprocess.CalledProcessError(128, ["git", "rev-list"])
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"rev-list": err}),
    )
    res = mr.check_unpushed(str(tmp_path))
    # deterministisch: eigener Status-Marker, als RED/WARN behandelt, kein Crash
    assert res["green"] is False
    assert res.get("status") == "no_upstream"


# ===========================================================================
# AK-CHECK-LANE-DIVERGENZ (W4/C3)  — 5 Tests (DRY-Reuse lane_develop_sync)
# ===========================================================================

def test_lane_divergenz_in_sync_is_green(monkeypatch, tmp_path):
    monkeypatch.setattr(mr, "ahead_behind", lambda *a, **k: (0, 0))
    res = mr.check_lane_divergenz(str(tmp_path))
    assert res["green"] is True
    assert res["action"] == "in-sync"


def test_lane_divergenz_merge_is_red(monkeypatch, tmp_path):
    monkeypatch.setattr(mr, "ahead_behind", lambda *a, **k: (2, 0))
    res = mr.check_lane_divergenz(str(tmp_path))
    assert res["green"] is False
    assert res["action"] == "merge"


def test_lane_divergenz_pull_first_is_red(monkeypatch, tmp_path):
    monkeypatch.setattr(mr, "ahead_behind", lambda *a, **k: (0, 3))
    res = mr.check_lane_divergenz(str(tmp_path))
    assert res["green"] is False
    assert res["action"] == "pull-first"


def test_lane_divergenz_diverged_is_red(monkeypatch, tmp_path):
    monkeypatch.setattr(mr, "ahead_behind", lambda *a, **k: (1, 1))
    res = mr.check_lane_divergenz(str(tmp_path))
    assert res["green"] is False
    assert res["action"] == "diverged"


def test_lane_divergenz_ahead_behind_none_is_red_with_marker(monkeypatch, tmp_path):
    monkeypatch.setattr(mr, "ahead_behind", lambda *a, **k: None)
    res = mr.check_lane_divergenz(str(tmp_path))
    assert res["green"] is False
    # Marker bei git-Fehler (ahead_behind == None)
    assert res.get("status") in ("git_error", "ahead_behind_failed", "error") or res.get("action") in (None, "error")


def test_lane_divergenz_reuses_develop_sync_action():
    # DRY-Reuse-Beweis: migration_readiness importiert develop_sync_action aus
    # lane_develop_sync (kein Re-Implement).
    import lane_develop_sync
    assert mr.develop_sync_action is lane_develop_sync.develop_sync_action


# ===========================================================================
# AK-CHECK-UNTRACKED-PRODUKT (W5/C4, <-AK-S4)  — 4 Tests
# ===========================================================================

def test_untracked_product_py_is_red(monkeypatch, tmp_path):
    porcelain = "?? .claude/scripts/build_retrieval_index.py\n"
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, porcelain)}),
    )
    res = mr.check_untracked_product(str(tmp_path))
    assert res["green"] is False
    assert ".claude/scripts/build_retrieval_index.py" in res["untracked_products"]


def test_untracked_non_product_md_is_green(monkeypatch, tmp_path):
    porcelain = "?? notes.md\n"
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, porcelain)}),
    )
    res = mr.check_untracked_product(str(tmp_path))
    assert res["green"] is True
    assert res["untracked_products"] == []


def test_untracked_empty_is_green(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, "")}),
    )
    res = mr.check_untracked_product(str(tmp_path))
    assert res["green"] is True
    assert res["untracked_products"] == []


def test_untracked_build_retrieval_index_regression_fixture(monkeypatch, tmp_path):
    # BL-242 build_retrieval_index.py als Regression-Fixture (mehrere ?? Zeilen).
    porcelain = (
        "?? .claude/scripts/build_retrieval_index.py\n"
        "?? notes.md\n"
        "?? .claude/scripts/another_tool.py\n"
    )
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, porcelain)}),
    )
    res = mr.check_untracked_product(str(tmp_path))
    assert res["green"] is False
    assert ".claude/scripts/build_retrieval_index.py" in res["untracked_products"]
    assert ".claude/scripts/another_tool.py" in res["untracked_products"]
    # .md wird NICHT als Produkt gelistet
    assert "notes.md" not in res["untracked_products"]


# ===========================================================================
# AK-VAULT-SYNC (W6/C5, teil-gated)  — 3 Tests
# ===========================================================================

def test_vault_no_git_is_warn_not_versioned(monkeypatch, tmp_path):
    # Vault-Root ohne .git -> Status vault_not_versioned, WARN (nicht migration-blockend default).
    vault = tmp_path / "vault"
    vault.mkdir()
    res = mr.vault_sync_status(str(vault))
    assert res["status"] == "vault_not_versioned"
    # WARN-Klassifikation: default nicht hartes Fail
    assert res.get("warn") is True
    assert res.get("blocking", False) is False


def test_vault_with_git_clean_is_green(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, ""), "rev-list": (0, "0\n")}),
    )
    res = mr.vault_sync_status(str(vault))
    assert res["green"] is True


def test_vault_with_git_dirty_is_red(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, " M BL-x.md\n"), "rev-list": (0, "0\n")}),
    )
    res = mr.vault_sync_status(str(vault))
    assert res["green"] is False


# ===========================================================================
# AK-VERDICT (W1)  — 3 Tests
# ===========================================================================

def _all_green_subprocess(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, ""), "rev-list": (0, "0\n")}),
    )
    monkeypatch.setattr(mr, "ahead_behind", lambda *a, **k: (0, 0))


def test_verdict_all_green_is_ready(monkeypatch, tmp_path):
    _all_green_subprocess(monkeypatch)
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    res = mr.migration_ready(str(tmp_path), str(vault))
    assert res["migration_ready"] is True
    assert res["verdict"] == "READY"
    assert res["red_checks"] == []


def test_verdict_one_red_is_not_ready(monkeypatch, tmp_path):
    # uncommitted dirty -> C1 RED
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, " M x.py\n"), "rev-list": (0, "0\n")}),
    )
    monkeypatch.setattr(mr, "ahead_behind", lambda *a, **k: (0, 0))
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    res = mr.migration_ready(str(tmp_path), str(vault))
    assert res["migration_ready"] is False
    assert res["verdict"] == "NOT_READY"
    assert len(res["red_checks"]) >= 1


def test_verdict_json_shape_stable(monkeypatch, tmp_path):
    _all_green_subprocess(monkeypatch)
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    res = mr.migration_ready(str(tmp_path), str(vault))
    for key in ("migration_ready", "verdict", "checks", "red_checks"):
        assert key in res
    assert isinstance(res["checks"], dict)
    # C1..C5 vorhanden
    for ck in ("c1", "c2", "c3", "c4", "c5"):
        assert ck in res["checks"]


# ===========================================================================
# AK-CLI-RESOLVER (W7)  — 4 Tests
# ===========================================================================

def test_cli_json_all_green_exit_zero(monkeypatch, tmp_path, capsys):
    _all_green_subprocess(monkeypatch)
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    rc = mr.main(["--repo", str(tmp_path), "--vault-root", str(vault), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)  # valides JSON, kein Human-Text
    assert data["migration_ready"] is True


def test_cli_json_one_red_exit_one(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        subprocess, "run",
        _make_run_stub({"status --porcelain": (0, " M x.py\n"), "rev-list": (0, "0\n")}),
    )
    monkeypatch.setattr(mr, "ahead_behind", lambda *a, **k: (0, 0))
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    rc = mr.main(["--repo", str(tmp_path), "--vault-root", str(vault), "--json"])
    assert rc == 1
    data = json.loads(capsys.readouterr().out)
    assert data["migration_ready"] is False


def test_cli_vault_root_override_used(monkeypatch, tmp_path):
    # --vault-root Override wird genutzt; Resolver wird NICHT gerufen.
    _all_green_subprocess(monkeypatch)
    called = {"resolver": False}
    monkeypatch.setattr(mr, "resolve_vault_root", lambda *a, **k: called.__setitem__("resolver", True) or Path("/should/not/be/used"))
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    rc = mr.main(["--repo", str(tmp_path), "--vault-root", str(vault), "--json"])
    assert rc == 0
    assert called["resolver"] is False


def test_cli_default_calls_resolve_vault_root(monkeypatch, tmp_path):
    # ohne --vault-root -> resolve_vault_root (gemockt) wird gerufen.
    _all_green_subprocess(monkeypatch)
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    called = {"resolver": False}

    def fake_resolver(*a, **k):
        called["resolver"] = True
        return vault

    monkeypatch.setattr(mr, "resolve_vault_root", fake_resolver)
    rc = mr.main(["--repo", str(tmp_path), "--json"])
    assert called["resolver"] is True
    assert rc == 0


def test_cli_reuses_resolve_vault_root_primitive():
    # DRY-Reuse-Beweis: resolve_vault_root aus dem Resolver-Modul importiert.
    import resolve_vault_root as rvr
    assert mr.resolve_vault_root is rvr.resolve_vault_root
