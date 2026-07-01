"""
test_t_script.py — User-Tool /_T_script: fuehrt NUR die Tests einer Stage aus.

Kern-Anforderung (User 2026-06-04): „eine einfache Moeglichkeit, wirklich NUR diese
Tests auszufuehren" — pro Stage (stage1..stage6: Unit/Integration/E2E). Loest
`.claude/meta/implementation/stage_{N}.md` → `testbefehl` (+ optional setup/teardown)
und faehrt GENAU das, nichts sonst (keine ganze Suite).
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import t_script  # noqa: E402  (RED: Modul existiert noch nicht)


@pytest.fixture
def env_guard_ts():
    """Sichert/Restored CLAUDE_VAULT_ROOT + cwd (BL-392 Resolver-Tests pinnen Vault via env)."""
    _orig_env = os.environ.get("CLAUDE_VAULT_ROOT")
    _orig_cwd = str(Path.cwd())
    try:
        yield
    finally:
        if _orig_env is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig_env
        os.chdir(_orig_cwd)


STAGE_1 = (
    "---\n"
    "stufe: 1\n"
    "name: Atomic\n"
    'testbefehl: "dotnet test --filter Category=Unit"\n'
    "test_projekte: []\n"
    "setup:\n"
    "  commands: []\n"
    "  timeout_min: 0\n"
    "teardown:\n"
    "  commands: []\n"
    "---\n"
    "# Stufe 1\n"
)

STAGE_6 = (
    "---\n"
    "stufe: 6\n"
    "name: Controller-E2E\n"
    'testbefehl: "powershell .claude/scripts/Test-Stage6.ps1"\n'
    "setup:\n"
    "  commands:\n"
    '    - "docker-compose -f docker-compose.yml up -d"\n'
    '    - "powershell .claude/scripts/Wait-ForHealthCheck.ps1 -Url x -Timeout 120"\n'
    "  timeout_min: 5\n"
    "teardown:\n"
    "  commands:\n"
    '    - "docker-compose -f docker-compose.yml down"\n'
    "  always_run: true\n"
    "---\n"
    "# Stufe 6\n"
)


def test_resolve_stage_arg():
    assert t_script.resolve_stage_arg("3") == 3
    assert t_script.resolve_stage_arg("stage3") == 3
    assert t_script.resolve_stage_arg("--stage=6") == 6
    assert t_script.resolve_stage_arg("foo") is None
    assert t_script.resolve_stage_arg("9") is None  # nur 1-6


def test_parse_testbefehl():
    meta = t_script.parse_stage(STAGE_1)
    assert meta["testbefehl"] == "dotnet test --filter Category=Unit"
    assert meta["name"] == "Atomic"
    assert meta["setup_commands"] == []


def test_parse_strips_inquote_reminder_comment():
    """Realer stage_3.md-Fall: Reminder-Kommentar INNERHALB der Quotes wird abgeschnitten."""
    content = (
        "---\nstufe: 3\nname: Integration\n"
        'testbefehl: "dotnet test --filter \\"FullyQualifiedName~<TestName>\\"  # IMMER Einzel-Test NIEMALS alle"\n'
        "setup:\n  commands: []\nteardown:\n  commands: []\n---\n"
    )
    meta = t_script.parse_stage(content)
    assert meta["testbefehl"] == 'dotnet test --filter \\"FullyQualifiedName~<TestName>\\"'
    assert "#" not in meta["testbefehl"]


def test_parse_setup_teardown_commands():
    meta = t_script.parse_stage(STAGE_6)
    assert meta["testbefehl"] == "powershell .claude/scripts/Test-Stage6.ps1"
    assert len(meta["setup_commands"]) == 2
    assert meta["setup_commands"][0] == "docker-compose -f docker-compose.yml up -d"
    assert meta["teardown_commands"] == ["docker-compose -f docker-compose.yml down"]


def test_build_plan_test_only_default():
    """Default = NUR testbefehl (Kern-Anforderung: nur die Tests)."""
    meta = t_script.parse_stage(STAGE_6)
    plan = t_script.build_plan(meta, with_setup=False, with_teardown=False)
    assert plan == [("test", "powershell .claude/scripts/Test-Stage6.ps1")]


def test_build_plan_with_setup_teardown():
    meta = t_script.parse_stage(STAGE_6)
    plan = t_script.build_plan(meta, with_setup=True, with_teardown=True)
    kinds = [k for k, _ in plan]
    assert kinds == ["setup", "setup", "test", "teardown"]


def test_main_dry_run_only_testbefehl(tmp_path, capsys):
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "stage_1.md").write_text(STAGE_1, encoding="utf-8")
    rc = t_script.main(["1", "--dry-run", "--meta-dir=" + str(meta_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "dotnet test --filter Category=Unit" in out
    assert "docker-compose" not in out  # ohne --setup keine Setup-Commands


def test_main_missing_stage_returns_1(tmp_path):
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    rc = t_script.main(["3", "--dry-run", "--meta-dir=" + str(meta_dir)])
    assert rc == 1  # stage_3.md fehlt


def test_main_no_stage_arg_returns_2():
    assert t_script.main(["--dry-run"]) == 2


# ── DER MIX: Stage-Template x testSearch-relevante Tests ──────────────────────

def test_build_test_commands_substitutes_placeholder():
    cmds = t_script.build_test_commands(
        'dotnet test --filter "FullyQualifiedName~<TestName>"', ["A", "B"])
    assert cmds == [
        'dotnet test --filter "FullyQualifiedName~A"',
        'dotnet test --filter "FullyQualifiedName~B"',
    ]


def test_build_test_commands_cypress_spec_placeholder():
    cmds = t_script.build_test_commands("npx cypress run --spec <SPEC>", ["a.feature", "b.feature"])
    assert cmds == ["npx cypress run --spec a.feature", "npx cypress run --spec b.feature"]


def test_build_test_commands_no_tests_returns_template():
    assert t_script.build_test_commands("npx cypress run --spec <SPEC>", []) == [
        "npx cypress run --spec <SPEC>"]


def test_load_tests_from_csv_and_file(tmp_path):
    f = tmp_path / "relevant.txt"
    f.write_text("SpecA\n# comment\n\nSpecB\n", encoding="utf-8")
    tests = t_script.load_tests({"tests": "X,Y", "tests-file": str(f)})
    assert tests == ["X", "Y", "SpecA", "SpecB"]


def test_main_dry_run_with_tests_substitutes(tmp_path, capsys):
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "stage_3.md").write_text(
        "---\nstufe: 3\nname: Integration\n"
        'testbefehl: "dotnet test --filter \\"FullyQualifiedName~<TestName>\\""\n'
        "setup:\n  commands: []\nteardown:\n  commands: []\n---\n",
        encoding="utf-8",
    )
    rc = t_script.main(["3", "--tests=MyTest1,MyTest2", "--dry-run", "--meta-dir=" + str(meta_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "FullyQualifiedName~MyTest1" in out
    assert "FullyQualifiedName~MyTest2" in out
    assert "<TestName>" not in out  # vollstaendig substituiert (nur relevante Tests)


def test_build_test_commands_join_one_command():
    """Cypress: --join -> EIN Lauf mit komma-verbundenen Specs (statt N Boots)."""
    cmds = t_script.build_test_commands(
        "npx cypress run --spec <SPEC>", ["a.feature", "b.feature"], join=True)
    assert cmds == ["npx cypress run --spec a.feature,b.feature"]


def test_main_skips_placeholder_without_tests(tmp_path, capsys):
    """Stage mit Platzhalter (z.B. Cypress <SPEC>) ohne --tests -> skip, kein nackter Platzhalter-Lauf."""
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "stage_5.md").write_text(
        '---\nstufe: 5\nname: E2E\ntestbefehl: "npx cypress run --spec <SPEC>"\n'
        "setup:\n  commands: []\nteardown:\n  commands: []\n---\n",
        encoding="utf-8",
    )
    rc = t_script.main(["5", "--dry-run", "--meta-dir=" + str(meta_dir)])
    assert rc == 1
    assert "uebersprungen" in capsys.readouterr().out


def test_main_warns_tests_without_placeholder(tmp_path, capsys):
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "stage_1.md").write_text(
        '---\nstufe: 1\nname: Atomic\ntestbefehl: "dotnet test"\nsetup:\n  commands: []\n'
        "teardown:\n  commands: []\n---\n",
        encoding="utf-8",
    )
    rc = t_script.main(["1", "--tests=X", "--dry-run", "--meta-dir=" + str(meta_dir)])
    assert rc == 0
    assert "WARN" in capsys.readouterr().out  # kein Platzhalter -> Hinweis


# ── BL-392 AK-CONSUMER-REWRITE: t_script liest VIA resolve_vault_stage ─────────
# Behavior-preserving: bei nicht-migrierter Stage (kein Vault-Slice-Satz) faellt
# der Resolver auf den Legacy-Monolith im --meta-dir zurueck -> identisch zu heute.
# Bei migrierter Stage (Vault-Slice-Satz da) liest t_script den execute-Slice.


def test_load_stage_meta_helper_exists():
    """RED: t_script hat einen resolve-Helper, der die Stage-Meta via Resolver holt."""
    assert hasattr(t_script, "load_stage_meta"), \
        "t_script muss die Stage-Meta via resolve_vault_stage holen (load_stage_meta)"


def test_t_script_imports_resolver():
    """t_script importiert resolve_vault_stage (Stage-Resolution NICHT mehr direkt)."""
    import inspect
    src = inspect.getsource(t_script)
    assert "resolve_vault_stage" in src, \
        "t_script muss resolve_vault_stage nutzen (kein direkter stage_N.md-Read)"


def test_legacy_fallback_identical_to_today(tmp_path, env_guard_ts, capsys):
    """Dual-Read-Fallback: kein Vault-Slice -> Legacy-Monolith im --meta-dir, identisch.

    Exakt das heutige Verhalten: testbefehl + dry-run-Plan kommen aus dem Monolith
    in --meta-dir. Der Resolver faellt (kein Vault) byte-identisch auf diese Datei.
    """
    import os
    vault = tmp_path / "empty_vault"
    vault.mkdir()
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)  # KEIN Stage/-Verzeichnis -> Legacy

    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "stage_1.md").write_text(STAGE_1, encoding="utf-8")
    rc = t_script.main(["1", "--dry-run", "--meta-dir=" + str(meta_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "dotnet test --filter Category=Unit" in out  # aus dem Legacy-Monolith
    assert "docker-compose" not in out


def test_vault_slice_set_wins_over_legacy(tmp_path, env_guard_ts, capsys):
    """Migrierte Stage: Vault-Slice-Satz vorhanden -> testbefehl kommt aus execute-Slice."""
    import os
    import yaml

    vault = tmp_path / "vault"
    stage_dir = vault / "Stage" / "stage_3_integration"
    stage_dir.mkdir(parents=True)
    slice_set = {
        "_index": {"stufe": 3, "name": "integration"},
        "execute": {"testbefehl": "dotnet test --filter Vault~X", "testtyp": "integration"},
        "setup": {"commands": ["vault-setup"]},
        "teardown": {"commands": ["vault-teardown"]},
        "health_check": {"command": "docker info"},
        "resources": {"infrastruktur": "docker"},
        "concurrency_class": {"concurrency_class": "DEPENDS"},
        "exit_criteria": {"qg": "pass"},
    }
    for name, fm in slice_set.items():
        text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n# " + name + "\n"
        (stage_dir / f"{name}.md").write_text(text, encoding="utf-8")
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    # --meta-dir zeigt auf einen ANDEREN (Legacy) Monolith — der darf NICHT gewinnen.
    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    (meta_dir / "stage_3.md").write_text(
        '---\nstufe: 3\nname: Integration\ntestbefehl: "LEGACY-SHOULD-NOT-WIN"\n'
        "setup:\n  commands: []\nteardown:\n  commands: []\n---\n",
        encoding="utf-8",
    )
    rc = t_script.main(["3", "--dry-run", "--meta-dir=" + str(meta_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "dotnet test --filter Vault~X" in out   # aus dem Vault-execute-Slice
    assert "LEGACY-SHOULD-NOT-WIN" not in out        # Vault gewinnt vor Legacy


def test_vault_slice_setup_teardown_from_slices(tmp_path, env_guard_ts, capsys):
    """Migrierte Stage: setup/teardown-Commands kommen aus den setup/teardown-Slices."""
    import os
    import yaml

    vault = tmp_path / "vault"
    stage_dir = vault / "Stage" / "stage_6_e2e"
    stage_dir.mkdir(parents=True)
    slice_set = {
        "_index": {"stufe": 6, "name": "e2e"},
        "execute": {"testbefehl": "powershell Test-Stage6.ps1"},
        "setup": {"commands": ["docker up vault", "wait-health vault"]},
        "teardown": {"commands": ["docker down vault"]},
        "health_check": {"command": "curl x"},
        "resources": {"infrastruktur": "real-system"},
        "concurrency_class": {"concurrency_class": "EXCLUSIVE"},
        "exit_criteria": {"qg": "pass"},
    }
    for name, fm in slice_set.items():
        text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n# " + name + "\n"
        (stage_dir / f"{name}.md").write_text(text, encoding="utf-8")
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    rc = t_script.main(["6", "--setup", "--teardown", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "docker up vault" in out
    assert "wait-health vault" in out
    assert "docker down vault" in out


def test_resolved_stage_without_testbefehl_no_crash(tmp_path, env_guard_ts, capsys):
    """Regression: Stage resolved (Legacy-Monolith) ABER ohne testbefehl -> rc=1, KEIN NameError.

    Schuetzt gegen die geloeschte `path`-Variable im rewrite (BL-392): der no-testbefehl-Zweig
    darf nicht auf eine nicht mehr existierende lokale Variable verweisen.
    """
    import os
    vault = tmp_path / "empty_vault"
    vault.mkdir()
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    meta_dir = tmp_path / "meta"
    meta_dir.mkdir()
    # Monolith existiert, hat aber KEIN testbefehl-Feld.
    (meta_dir / "stage_1.md").write_text(
        "---\nstufe: 1\nname: Atomic\nsetup:\n  commands: []\nteardown:\n  commands: []\n---\n",
        encoding="utf-8",
    )
    rc = t_script.main(["1", "--dry-run", "--meta-dir=" + str(meta_dir)])
    assert rc == 1
    assert "kein testbefehl-Feld" in capsys.readouterr().out
