"""
test_sanity_check_stage.py — TDD-RED Tests fuer BL-412 batch_6 (AK-SC-PL-2).

Ziel-API (noch NICHT implementiert — diese Tests sind RED):
  sanity_check_stage(stage_nr, *, vault_root=None, live=False) -> dict

  Rueckgabe-Shape:
    {
      "verdict": "PASS" | "FAIL" | "WARN",
      "checks": {
        "a": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
        "b": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
        "c": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
        "d": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
        "e": {"status": "PASS"|"FAIL"|"WARN", "hint": str|None},
      },
      "stage_dir": str | None,
    }

  Sub-Checks laut _stage_sanity_check.md:
    (a) execute.testbefehl syntaktisch valide -> PASS/FAIL
    (b) Filter-Parameter deklariert -> PASS/WARN
    (c) concurrency_class + validate_slice_set vollstaendig -> PASS/FAIL
    (d) Monitor-Kanal (LogFileName/TDD-STATE) in testbefehl ableitbar -> PASS/WARN
    (e) INFRA_CONDITIONAL-Slices vollstaendig ODER skip:true -> PASS/FAIL

  Verdikt = worst_case(a, b, c, d, e):  FAIL > WARN > PASS

  Strukturell-Tier (live=False): laeuft IMMER ohne laufendes System.

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_sanity_check_stage.py     (repo-root)
  py -3 -m pytest test_sanity_check_stage.py                     (scripts-cwd)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

# TARGET (noch nicht existierend -> diese Datei provoziert RED)
from sanity_check_stage import sanity_check_stage  # type: ignore[import]


# ---------------------------------------------------------------------------
# Hilfs-Funktionen: tmp_path-Stage-Slice-Set anlegen
# ---------------------------------------------------------------------------

def _write_slice(stage_dir: Path, slice_name: str, fm: dict) -> None:
    """Schreibe einen einzelnen Slice als {slice_name}.md mit YAML-Frontmatter."""
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n# " + slice_name + "\n"
    (stage_dir / f"{slice_name}.md").write_text(text, encoding="utf-8")


def _make_stage_dir(tmp_path: Path, stage_nr: int, name: str = "test") -> Path:
    """Erstelle das korrekte Stage-Slice-Verzeichnis unter {tmp_path}/Stage/stage_{nr}_{name}/."""
    stage_dir = tmp_path / "Stage" / f"stage_{stage_nr}_{name}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    return stage_dir


def _write_full_valid_slice_set(stage_dir: Path, *, testbefehl: str = "dotnet test --filter Category=Unit --LogFileName TDD-STATE.md") -> None:
    """Schreibe ein vollstaendiges, valides Slice-Set (alle 8 Slices) in stage_dir."""
    _write_slice(stage_dir, "_index", {"stufe": 1, "name": "unit"})
    _write_slice(stage_dir, "execute", {"testbefehl": testbefehl, "testtyp": "unit"})
    _write_slice(stage_dir, "setup", {"skip": True})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    _write_slice(stage_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(stage_dir, "exit_criteria", {"qg": "pass"})


# ---------------------------------------------------------------------------
# Testfall 1: vollstaendiges valides Slice-Set -> verdict PASS
# (alle 5 Sub-Checks a-e PASS)
# ---------------------------------------------------------------------------

def test_full_valid_slice_set_verdict_pass(tmp_path: Path) -> None:
    """Vollstaendiges valides Slice-Set: alle Sub-Checks PASS -> Gesamt PASS.

    Konfiguration:
      - execute.testbefehl gesetzt, enthaelt --filter + LogFileName (a=PASS, b=PASS, d=PASS)
      - validate_slice_set PASS + concurrency_class vorhanden (c=PASS)
      - setup/teardown/health_check: skip:true (INFRA_CONDITIONAL -> e=PASS)
    """
    stage_dir = _make_stage_dir(tmp_path, stage_nr=1, name="unit")
    _write_full_valid_slice_set(stage_dir)

    result = sanity_check_stage(1, vault_root=tmp_path, live=False)

    assert result["verdict"] == "PASS"
    checks = result["checks"]
    assert checks["a"]["status"] == "PASS"
    assert checks["b"]["status"] == "PASS"
    assert checks["c"]["status"] == "PASS"
    assert checks["d"]["status"] == "PASS"
    assert checks["e"]["status"] == "PASS"


# ---------------------------------------------------------------------------
# Testfall 2: execute.testbefehl fehlt -> Sub-Check (a) FAIL -> verdict FAIL
# ---------------------------------------------------------------------------

def test_execute_testbefehl_missing_check_a_fail(tmp_path: Path) -> None:
    """execute.testbefehl fehlt (Leer-Defekt) -> Sub-Check (a) FAIL -> Gesamt FAIL.

    Kein gezielter Test moeglich ohne testbefehl.
    """
    stage_dir = _make_stage_dir(tmp_path, stage_nr=2, name="unit")
    # Alle Slices korrekt ausser execute: testbefehl fehlt
    _write_slice(stage_dir, "_index", {"stufe": 2, "name": "unit"})
    _write_slice(stage_dir, "execute", {"testtyp": "unit"})  # kein testbefehl
    _write_slice(stage_dir, "setup", {"skip": True})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    _write_slice(stage_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(stage_dir, "exit_criteria", {"qg": "pass"})

    result = sanity_check_stage(2, vault_root=tmp_path, live=False)

    assert result["verdict"] == "FAIL"
    assert result["checks"]["a"]["status"] == "FAIL"
    assert result["checks"]["a"]["hint"] is not None


def test_execute_testbefehl_null_check_a_fail(tmp_path: Path) -> None:
    """execute.testbefehl explizit null -> Sub-Check (a) FAIL -> Gesamt FAIL."""
    stage_dir = _make_stage_dir(tmp_path, stage_nr=3, name="unit")
    _write_slice(stage_dir, "_index", {"stufe": 3, "name": "unit"})
    _write_slice(stage_dir, "execute", {"testbefehl": None, "testtyp": "unit"})
    _write_slice(stage_dir, "setup", {"skip": True})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    _write_slice(stage_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(stage_dir, "exit_criteria", {"qg": "pass"})

    result = sanity_check_stage(3, vault_root=tmp_path, live=False)

    assert result["verdict"] == "FAIL"
    assert result["checks"]["a"]["status"] == "FAIL"


# ---------------------------------------------------------------------------
# Testfall 3: setup ohne Wert + kein skip -> Sub-Check (e) FAIL -> verdict FAIL
# ---------------------------------------------------------------------------

def test_setup_no_value_no_skip_check_e_fail(tmp_path: Path) -> None:
    """setup.commands Leer-Defekt (kein Wert, kein skip:true) -> Sub-Check (e) FAIL -> FAIL.

    Vertrag (INV-STAGE-SC-3 Umkehrung): INFRA_CONDITIONAL ohne Wert UND ohne
    Skip-Sentinel ist ein Defekt.
    """
    stage_dir = _make_stage_dir(tmp_path, stage_nr=4, name="integration")
    _write_slice(stage_dir, "_index", {"stufe": 4, "name": "integration"})
    _write_slice(stage_dir, "execute", {"testbefehl": "dotnet test --filter X --LogFileName TDD-STATE.md", "testtyp": "unit"})
    # setup: commands fehlt, KEIN skip-Sentinel -> Leer-Defekt
    _write_slice(stage_dir, "setup", {"timeout_min": 5})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    _write_slice(stage_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(stage_dir, "exit_criteria", {"qg": "pass"})

    result = sanity_check_stage(4, vault_root=tmp_path, live=False)

    assert result["verdict"] == "FAIL"
    assert result["checks"]["e"]["status"] == "FAIL"
    assert result["checks"]["e"]["hint"] is not None
    assert "setup" in result["checks"]["e"]["hint"]


# ---------------------------------------------------------------------------
# Testfall 4: skip:true auf INFRA_CONDITIONAL -> Sub-Check (e) PASS
# (Skip-Sentinel = explizit valide, INV-STAGE-SC-3)
# ---------------------------------------------------------------------------

def test_infra_conditional_skip_true_check_e_pass(tmp_path: Path) -> None:
    """skip:true auf setup/teardown/health_check -> (e) PASS: Skip-Sentinel ist explizit valide.

    INV-STAGE-SC-3: skip:true ist KEIN Leer-Defekt fuer INFRA_CONDITIONAL-Slices.
    """
    stage_dir = _make_stage_dir(tmp_path, stage_nr=5, name="unit")
    _write_slice(stage_dir, "_index", {"stufe": 5, "name": "unit"})
    _write_slice(stage_dir, "execute", {"testbefehl": "pytest tests/ --filter unit -k fast --log-file TDD-STATE.md", "testtyp": "unit"})
    # Explizite skip:true Sentinels
    _write_slice(stage_dir, "setup", {"skip": True})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    _write_slice(stage_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(stage_dir, "exit_criteria", {"qg": "pass"})

    result = sanity_check_stage(5, vault_root=tmp_path, live=False)

    assert result["checks"]["e"]["status"] == "PASS"
    # hint ist None wenn kein Problem
    assert result["checks"]["e"]["hint"] is None


# ---------------------------------------------------------------------------
# Testfall 5: unvollstaendiges Slice-Set (validate_slice_set faellt) -> FAIL (Sub-Check c)
# ---------------------------------------------------------------------------

def test_incomplete_slice_set_validate_fails_check_c_fail(tmp_path: Path) -> None:
    """Unvollstaendiger Slice-Satz (concurrency_class.md fehlt) -> (c) FAIL -> Gesamt FAIL.

    validate_slice_set meldet Defekte -> Sub-Check (c) FAIL.
    """
    stage_dir = _make_stage_dir(tmp_path, stage_nr=6, name="unit")
    _write_slice(stage_dir, "_index", {"stufe": 6, "name": "unit"})
    _write_slice(stage_dir, "execute", {"testbefehl": "dotnet test --filter X --LogFileName TDD-STATE.md", "testtyp": "unit"})
    _write_slice(stage_dir, "setup", {"skip": True})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    # concurrency_class.md FEHLT absichtlich
    _write_slice(stage_dir, "exit_criteria", {"qg": "pass"})

    result = sanity_check_stage(6, vault_root=tmp_path, live=False)

    assert result["verdict"] == "FAIL"
    assert result["checks"]["c"]["status"] == "FAIL"
    assert result["checks"]["c"]["hint"] is not None


# ---------------------------------------------------------------------------
# Zusatz: Stage nicht gefunden -> NOT_FOUND / FAIL
# ---------------------------------------------------------------------------

def test_stage_not_found_returns_fail(tmp_path: Path) -> None:
    """Stage-Nummer ohne Vault-Verzeichnis -> FAIL (Stage nicht gefunden)."""
    # tmp_path hat keine Stage/stage_99_*/ Unterverzeichnisse
    result = sanity_check_stage(99, vault_root=tmp_path, live=False)

    assert result["verdict"] == "FAIL"


# ---------------------------------------------------------------------------
# Zusatz: verdict = worst_case(a..e) korrekt aggregiert
# (WARN schlaegt PASS, FAIL schlaegt WARN)
# ---------------------------------------------------------------------------

def test_verdict_warn_when_no_filter_all_else_pass(tmp_path: Path) -> None:
    """testbefehl ohne --filter oder execute.filter -> (b) WARN; rest PASS -> Gesamt WARN.

    INV-STAGE-SC-4 (worst_case): WARN schlaegt PASS.
    """
    stage_dir = _make_stage_dir(tmp_path, stage_nr=7, name="unit")
    # testbefehl OHNE --filter, ABER mit LogFileName (damit d=PASS)
    _write_slice(stage_dir, "_index", {"stufe": 7, "name": "unit"})
    _write_slice(stage_dir, "execute", {"testbefehl": "dotnet test --LogFileName TDD-STATE.md", "testtyp": "unit"})
    _write_slice(stage_dir, "setup", {"skip": True})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    _write_slice(stage_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(stage_dir, "exit_criteria", {"qg": "pass"})

    result = sanity_check_stage(7, vault_root=tmp_path, live=False)

    assert result["checks"]["a"]["status"] == "PASS"   # testbefehl gesetzt
    assert result["checks"]["b"]["status"] == "WARN"   # kein --filter
    assert result["checks"]["b"]["hint"] is not None
    assert result["verdict"] == "WARN"                 # worst_case: WARN schlaegt PASS


def test_fail_overrides_warn_in_worst_case(tmp_path: Path) -> None:
    """FAIL in Sub-Check (a) + WARN in Sub-Check (b) -> Gesamt FAIL (FAIL > WARN > PASS)."""
    stage_dir = _make_stage_dir(tmp_path, stage_nr=8, name="unit")
    # execute: testbefehl fehlt -> (a) FAIL; kein --filter waere (b) WARN, aber (a) FAIL reicht
    _write_slice(stage_dir, "_index", {"stufe": 8, "name": "unit"})
    _write_slice(stage_dir, "execute", {"testtyp": "unit"})  # kein testbefehl
    _write_slice(stage_dir, "setup", {"skip": True})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    _write_slice(stage_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(stage_dir, "exit_criteria", {"qg": "pass"})

    result = sanity_check_stage(8, vault_root=tmp_path, live=False)

    assert result["checks"]["a"]["status"] == "FAIL"
    assert result["verdict"] == "FAIL"


# ---------------------------------------------------------------------------
# Zusatz: Rueckgabe-Shape vollstaendig
# ---------------------------------------------------------------------------

def test_return_shape_complete(tmp_path: Path) -> None:
    """Rueckgabe-dict enthaelt verdict + checks{a,b,c,d,e,A,C,D,F,REG,E} + stage_dir (Shape-Vertrag).

    BL-486 batch_1 erweitert den checks-Key-Satz von 5 (a-e) auf 10 (a-e + A/C/D/F/REG).
    BL-486 batch_2 (E-CHK) ergaenzt den 11. Key Gross-"E" (_behavior_check_e_elevation).
    Exact-11-Key-Match konsistent mit G-INT-2 (TestBL486BehaviorGate) + G-E-CHK (TestBL486AKEElevationGate).
    """
    stage_dir = _make_stage_dir(tmp_path, stage_nr=9, name="unit")
    _write_full_valid_slice_set(stage_dir)

    result = sanity_check_stage(9, vault_root=tmp_path, live=False)

    assert "verdict" in result
    assert "checks" in result
    assert set(result["checks"].keys()) == {"a", "b", "c", "d", "e", "A", "C", "D", "F", "REG", "E"}
    for key, check in result["checks"].items():
        assert "status" in check, f"check[{key}] muss 'status' enthalten"
        assert check["status"] in ("PASS", "FAIL", "WARN"), f"check[{key}].status ungueltig"
        assert "hint" in check, f"check[{key}] muss 'hint' enthalten"
    assert "stage_dir" in result


# ==========================================================================
# BL-486 batch_1 RED Tests — 5 neue Behavior-Gate-Checks
#
# Alle Tests in dieser Klasse FAILEN initial (vor GREEN) weil die
# _behavior_check_*-Funktionen noch nicht existieren:
#   AttributeError: Funktion nicht vorhanden
#   AssertionError/KeyError: "A"/"C"/"D"/"F"/"REG" fehlen in checks-Dict
#
# Nach GREEN-Phase: Tests werden GRUEN.
#
# Erwartete Check-Verdikts gegen aktuellen Engine-State:
#   A (is_legacy)        : FAIL  -- A3: kein {VAULT}/Stage/, alle Stages is_legacy=True
#   C (acquire_all)      : FAIL  -- C1: acquire_all nur Markdown-Prosa, kein Call-Site
#   D (granularity)      : FAIL -> PASS nach _TDD_execute.md-Fix (COMBINED AK-D)
#   F (release_all/ETA)  : FAIL  -- F1+F2 beide fehlend (release_all + hold_decision)
#   REG (registry)       : PASS  -- stage_infra_schema.py kein IO, kein dritter Kanal
#
# Gold-Ref: 4_Blueprint/BL-486_batch1_gold_2026-06-27.md (34 Gold-Assertions, 5+5 INT)
# ==========================================================================

import types as _types  # Lightweight Mock-Namespace fuer StageHandle-Stubs


class TestBL486BehaviorGate:
    """BL486BehaviorGateTests — RED Tests fuer 5 neue Behavior-Gate-Checks (BL-486 batch_1, M3, Stage 1).

    Testklasse enthaelt ~31 neue Tests (alle initial FAILING -- RED-Zustand).
    GREEN-Worker implementiert _behavior_check_a_legacy, _behavior_check_c_acquire,
    _behavior_check_d_granularity, _behavior_check_f_release_eta,
    _behavior_check_reg_registry in sanity_check_stage.py und verdrahtet sie in
    sanity_check_stage() + _print_report().
    """

    # ======================================================================
    # Hilfsmethoden fuer Stage-Setup in Integration-Tests
    # ======================================================================

    @staticmethod
    def _setup_valid_stage(tmp_path: Path, stage_nr: int = 1) -> Path:
        """Lege vollstaendiges valides Slice-Set unter tmp_path/Stage/stage_{nr}_unit/ an."""
        stage_dir = _make_stage_dir(tmp_path, stage_nr=stage_nr, name="unit")
        _write_full_valid_slice_set(stage_dir)
        return stage_dir

    # ======================================================================
    # CHECK A -- _behavior_check_a_legacy
    # 6 Gold-Assertions (G-A-1 bis G-A-6)
    # Erwartet-Verdikt: FAIL (A3: kein {VAULT}/Stage/; alle Stages is_legacy=True)
    # ======================================================================

    def test_check_a_function_exists(self) -> None:
        """G-A-1: _behavior_check_a_legacy existiert in sanity_check_stage als callable.

        FAILT in RED: AttributeError (Funktion noch nicht implementiert).
        """
        import sanity_check_stage as _scs
        func = getattr(_scs, "_behavior_check_a_legacy", None)
        assert func is not None and callable(func), (
            "_behavior_check_a_legacy fehlt in sanity_check_stage.py "
            "(GREEN implementiert sie — BL-486-AK-A-CHK-PL-1)"
        )

    def test_check_a_returns_fail_when_no_vault_stage_dir(self, tmp_path: Path) -> None:
        """G-A-2: FAIL wenn vault_stage_root (Vault/Stage/) nicht existiert (A3-Detektor).

        FAILT in RED: AttributeError. Nach GREEN: FAIL wegen fehlendem Stage/-Dir.
        """
        import sanity_check_stage as _scs
        handle = _types.SimpleNamespace(is_legacy=True, number=1, stage_dir=None)
        result = _scs._behavior_check_a_legacy(handle=handle, vault_root=tmp_path)
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn kein {VAULT}/Stage/-Verzeichnis vorhanden (A3)"
        )
        assert result["hint"] is not None, "hint muss bei FAIL gesetzt sein"

    def test_check_a_returns_fail_when_stage_root_exists_but_no_index_doc(
        self, tmp_path: Path
    ) -> None:
        """G-A-3: FAIL wenn Vault/Stage/ existiert aber kein globales Index-Dokument (A2).

        FAILT in RED: AttributeError. Nach GREEN: FAIL wegen fehlendem Index-Doc.
        """
        import sanity_check_stage as _scs
        vault_stage = tmp_path / "Stage"
        vault_stage.mkdir()
        handle = _types.SimpleNamespace(is_legacy=True, number=1, stage_dir=None)
        result = _scs._behavior_check_a_legacy(handle=handle, vault_root=tmp_path)
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn Stage/-Verzeichnis vorhanden aber kein _index.md (A2)"
        )

    def test_check_a_returns_fail_when_legacy_despite_vault_stage_and_index(
        self, tmp_path: Path
    ) -> None:
        """G-A-4: FAIL wenn handle.is_legacy==True UND vault_stage_root + Index-Doc vorhanden (A1).

        FAILT in RED: AttributeError. Nach GREEN: FAIL wegen is_legacy=True (A1).
        """
        import sanity_check_stage as _scs
        vault_stage = tmp_path / "Stage"
        vault_stage.mkdir()
        (vault_stage / "_index.md").write_text("# Stage Index\n", encoding="utf-8")
        handle = _types.SimpleNamespace(is_legacy=True, number=1, stage_dir=None)
        result = _scs._behavior_check_a_legacy(handle=handle, vault_root=tmp_path)
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn is_legacy=True trotz vorhandenem Stage/-Dir + Index-Doc (A1)"
        )

    def test_check_a_returns_pass_when_vault_resident_not_legacy(
        self, tmp_path: Path
    ) -> None:
        """G-A-5: PASS wenn Stage/-Dir + Index-Doc vorhanden + handle.is_legacy==False.

        FAILT in RED: AttributeError. Nach GREEN: PASS (Idealszenario).
        """
        import sanity_check_stage as _scs
        vault_stage = tmp_path / "Stage"
        vault_stage.mkdir()
        (vault_stage / "_index.md").write_text("# Stage Index\n", encoding="utf-8")
        handle = _types.SimpleNamespace(is_legacy=False, number=1, stage_dir=None)
        result = _scs._behavior_check_a_legacy(handle=handle, vault_root=tmp_path)
        assert result["status"] == "PASS", (
            "Erwartet PASS wenn is_legacy=False + Stage/-Dir + Index-Doc vorhanden (G-A-5)"
        )

    def test_sanity_check_stage_includes_check_a_in_result(self, tmp_path: Path) -> None:
        """G-A-6: sanity_check_stage() liefert Key 'A' unter checks-Dict.

        FAILT in RED: AssertionError (Key 'A' nicht vorhanden, da nicht verdrahtet).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        assert "A" in result["checks"], (
            "Key 'A' fehlt in checks-Dict -- _behavior_check_a_legacy nicht verdrahtet (G-A-6)"
        )

    # ======================================================================
    # CHECK C -- _behavior_check_c_acquire
    # 5 Gold-Assertions (G-C-1 bis G-C-5)
    # Erwartet-Verdikt: FAIL (C1: acquire_all nur Markdown-Prosa, kein Call-Site)
    # ======================================================================

    def test_check_c_function_exists(self) -> None:
        """G-C-1: _behavior_check_c_acquire existiert in sanity_check_stage als callable.

        FAILT in RED: AttributeError (Funktion noch nicht implementiert).
        """
        import sanity_check_stage as _scs
        func = getattr(_scs, "_behavior_check_c_acquire", None)
        assert func is not None and callable(func), (
            "_behavior_check_c_acquire fehlt in sanity_check_stage.py "
            "(GREEN implementiert sie -- BL-486-AK-C-CHK-PL-1)"
        )

    def test_check_c_returns_fail_when_no_acquire_callsite_in_engine(
        self, tmp_path: Path
    ) -> None:
        """G-C-2: FAIL wenn kein acquire_all-Call-Site in Engine-Quellen (C1).

        Nur resource_allocator.py enthaelt acquire_all (als Implementierung, nicht Call-Site).
        FAILT in RED: AttributeError. Nach GREEN: FAIL (C1).
        """
        import sanity_check_stage as _scs
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "resource_allocator.py").write_text(
            "def acquire_all(): pass\n", encoding="utf-8"
        )
        result = _scs._behavior_check_c_acquire(scripts_dir=scripts_dir)
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn acquire_all nur in resource_allocator.py (Implementierung, "
            "kein ausgefuehrter Call-Site in anderem Engine-Modul) -- C1"
        )
        assert result["hint"] is not None

    def test_check_c_filter_excludes_registry_and_allocator(
        self, tmp_path: Path
    ) -> None:
        """G-C-3: Scan filtert resource_allocator.py und stage_resource_registry.py heraus.

        Auch wenn stage_resource_registry.py acquire_all() aufruft -- ist excluded.
        FAILT in RED: AttributeError. Nach GREEN: FAIL (kein externer Call-Site).
        """
        import sanity_check_stage as _scs
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "resource_allocator.py").write_text(
            "def acquire_all(): pass\n", encoding="utf-8"
        )
        (scripts_dir / "stage_resource_registry.py").write_text(
            "from resource_allocator import acquire_all\nacquire_all()\n",
            encoding="utf-8",
        )
        result = _scs._behavior_check_c_acquire(scripts_dir=scripts_dir)
        assert result["status"] == "FAIL", (
            "FAIL erwartet: stage_resource_registry.py wird ausgefiltert; "
            "kein externer Call-Site verbleibt (G-C-3)"
        )

    def test_check_c_returns_warn_when_callsite_found_but_guard_missing(
        self, tmp_path: Path
    ) -> None:
        """G-C-4: WARN wenn acquire_all-Call-Site gefunden (C1 bestanden) aber guard fehlt (C2).

        FAILT in RED: AttributeError. Nach GREEN: WARN (C1 ok, C2 WARN).
        """
        import sanity_check_stage as _scs
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "resource_allocator.py").write_text(
            "def acquire_all(): pass\n", encoding="utf-8"
        )
        (scripts_dir / "dispatch_caller.py").write_text(
            "from resource_allocator import acquire_all\nacquire_all()\n",
            encoding="utf-8",
        )
        # Kein guard_stage_acquire_enforce.py in scripts_dir
        result = _scs._behavior_check_c_acquire(scripts_dir=scripts_dir)
        assert result["status"] == "WARN", (
            "Erwartet WARN wenn acquire_all-Call-Site in dispatch_caller.py gefunden "
            "aber guard_stage_acquire_enforce.py fehlt (C2) -- G-C-4"
        )

    def test_sanity_check_stage_includes_check_c_in_result(self, tmp_path: Path) -> None:
        """G-C-5: sanity_check_stage() liefert Key 'C' unter checks-Dict.

        FAILT in RED: AssertionError (Key 'C' nicht vorhanden).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        assert "C" in result["checks"], (
            "Key 'C' fehlt in checks-Dict -- _behavior_check_c_acquire nicht verdrahtet (G-C-5)"
        )

    # ======================================================================
    # CHECK D -- _behavior_check_d_granularity
    # 7 Gold-Assertions (G-D-1 bis G-D-7)
    # Erwartet: FAIL jetzt -> PASS nach GREEN (_TDD_execute.md COMBINED-Fix)
    # ======================================================================

    def test_check_d_function_exists(self) -> None:
        """G-D-1: _behavior_check_d_granularity existiert in sanity_check_stage als callable.

        FAILT in RED: AttributeError (Funktion noch nicht implementiert).
        """
        import sanity_check_stage as _scs
        func = getattr(_scs, "_behavior_check_d_granularity", None)
        assert func is not None and callable(func), (
            "_behavior_check_d_granularity fehlt in sanity_check_stage.py "
            "(GREEN implementiert sie -- BL-486-AK-D-PL-1)"
        )

    def test_check_d_returns_fail_when_no_granularity_selector(
        self, tmp_path: Path
    ) -> None:
        """G-D-2: FAIL wenn _TDD_execute.md keinen 3-Werte-Granularitaets-Selektor hat (D1).

        FAILT in RED: AttributeError. Nach GREEN: FAIL (D1 -- kein einzeln/handvoll/granularit).
        """
        import sanity_check_stage as _scs
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "_TDD_execute.md").write_text(
            "# TDD Execute\n\nFuehre Tests aus.\n", encoding="utf-8"
        )
        result = _scs._behavior_check_d_granularity(commands_dir=commands_dir)
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn _TDD_execute.md kein einzeln/handvoll/granularit enthaelt (D1)"
        )
        assert result["hint"] is not None

    def test_check_d_returns_fail_when_granularity_present_but_no_guard(
        self, tmp_path: Path
    ) -> None:
        """G-D-3: FAIL wenn D1 bestanden (Granularitaets-Selektor da) aber Voll-Suite-Guard fehlt (D2).

        FAILT in RED: AttributeError. Nach GREEN: FAIL (D2 -- kein GUARD/voll-suite-guard).
        """
        import sanity_check_stage as _scs
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "_TDD_execute.md").write_text(
            "# TDD Execute\n\nGranularitaet: einzeln / handvoll / alle\n",
            encoding="utf-8",
        )
        result = _scs._behavior_check_d_granularity(commands_dir=commands_dir)
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn Granularitaets-Selektor vorhanden aber Voll-Suite-Guard fehlt (D2)"
        )

    def test_check_d_returns_warn_when_d1_d2_pass_but_no_default_testsearch(
        self, tmp_path: Path
    ) -> None:
        """G-D-4: WARN wenn D1+D2 bestanden aber kein Default=testSearch deklariert (D3).

        FAILT in RED: AttributeError. Nach GREEN: WARN (D3).
        """
        import sanity_check_stage as _scs
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "_TDD_execute.md").write_text(
            "# TDD Execute\n\nGranularitaet: einzeln / handvoll / alle\n"
            "GUARD: Voll-Suite-Lauf erfordert explizite Bestaetigung.\n",
            encoding="utf-8",
        )
        result = _scs._behavior_check_d_granularity(commands_dir=commands_dir)
        assert result["status"] == "WARN", (
            "Erwartet WARN wenn D1+D2 bestanden aber Default=testSearch nicht deklariert (D3)"
        )

    def test_check_d_returns_pass_when_all_d1_d2_d3_present(
        self, tmp_path: Path
    ) -> None:
        """G-D-5: PASS wenn D1+D2+D3 alle bestanden (vollstaendige _TDD_execute.md).

        FAILT in RED: AttributeError. Nach GREEN: PASS.
        """
        import sanity_check_stage as _scs
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        (commands_dir / "_TDD_execute.md").write_text(
            "# TDD Execute\n\nGranularitaet: einzeln / handvoll / alle\n"
            "GUARD: Voll-Suite-Lauf erfordert explizite Bestaetigung.\n"
            "default_granularity=testsearch\n",
            encoding="utf-8",
        )
        result = _scs._behavior_check_d_granularity(commands_dir=commands_dir)
        assert result["status"] == "PASS", (
            "Erwartet PASS wenn alle D1/D2/D3-Elemente in _TDD_execute.md vorhanden (G-D-5)"
        )

    def test_tdd_execute_md_contains_granularity_section_after_green(self) -> None:
        """G-D-6: Reale _TDD_execute.md enthaelt nach GREEN Granularitaets-Selektor (COMBINED-Fix).

        FAILT in RED: AssertionError (Abschnitt fehlt -- GREEN-Fix noch nicht angewendet).
        """
        tdd_execute = Path(__file__).parent.parent / "commands" / "_TDD_execute.md"
        assert tdd_execute.exists(), (
            "_TDD_execute.md nicht gefunden unter .claude/commands/"
        )
        content = tdd_execute.read_text(encoding="utf-8", errors="replace")
        has_granularity = (
            ("einzeln" in content or "single" in content)
            and ("handvoll" in content or "handful" in content)
            and "granularit" in content.lower()
        )
        assert has_granularity, (
            "G-D-6: _TDD_execute.md enthaelt keinen 3-Werte-Granularitaets-Selektor "
            "(einzeln/handvoll/alle) -- GREEN-Fix AK-D-COMBINED noch nicht angewendet"
        )

    def test_sanity_check_stage_includes_check_d_in_result(self, tmp_path: Path) -> None:
        """G-D-7: sanity_check_stage() liefert Key 'D' unter checks-Dict.

        FAILT in RED: AssertionError (Key 'D' nicht vorhanden).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        assert "D" in result["checks"], (
            "Key 'D' fehlt in checks-Dict -- _behavior_check_d_granularity nicht verdrahtet (G-D-7)"
        )

    # ======================================================================
    # CHECK F -- _behavior_check_f_release_eta
    # 5 Gold-Assertions (G-F-1 bis G-F-5)
    # Erwartet-Verdikt: FAIL (F1: release_all fehlt; F2: stage_hold_decision.py fehlt)
    # ======================================================================

    def test_check_f_function_exists(self) -> None:
        """G-F-1: _behavior_check_f_release_eta existiert in sanity_check_stage als callable.

        FAILT in RED: AttributeError (Funktion noch nicht implementiert).
        """
        import sanity_check_stage as _scs
        func = getattr(_scs, "_behavior_check_f_release_eta", None)
        assert func is not None and callable(func), (
            "_behavior_check_f_release_eta fehlt in sanity_check_stage.py "
            "(GREEN implementiert sie -- BL-486-AK-F-CHK-PL-1)"
        )

    def test_check_f_returns_fail_when_release_all_missing_in_real_codebase(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G-F-2: FAIL wenn release_all fehlt (F1) UND stage_hold_decision.py fehlt (F2).

        BL-486 batch_3 RECONCILIATION (Verdict-Flip, KEINE Test-Aufweichung):
        Dieser Test wurde in batch_1 mit der Voraussetzung geschrieben, dass
        stage_resource_registry.release_all real NOCH NICHT existiert ("sollte erst in
        batch_3 gebaut werden"). batch_3 (BL-486-AK-F1-FIX-PL-1, F1-FIX) hat release_all
        nun GEBAUT -> die alte real-codebase-Voraussetzung ist strukturell ueberholt.
        Die ORIGINAL-Test-Intention (F1-fehlt -> FAIL) bleibt UNVERAENDERT; nur der
        Mechanismus zum Erzeugen der F1-Absenz wechselt von "verlasse dich auf die echte
        Codebasis" auf monkeypatch.delattr (symmetrische Inverse zu
        test_check_f_returns_warn_when_release_all_exists_but_hold_missing, das F1-Praesenz
        monkeypatcht). F2 (stage_hold_decision.py) fehlt weiterhin real (batch_4).
        FAILT in RED: AttributeError. Nach GREEN: FAIL (F1 detektiert korrekt).
        """
        import stage_resource_registry as _srr
        import sanity_check_stage as _scs
        # F1-Absenz deterministisch erzwingen (release_all existiert real seit batch_3).
        monkeypatch.delattr(_srr, "release_all", raising=False)
        result = _scs._behavior_check_f_release_eta()
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn release_all fehlt (F1 -- via monkeypatch.delattr erzwungen)"
        )

    def test_check_f_fail_combined_f1_and_f2_both_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G-F-2 Variante: FAIL-Verdikt und hint wenn BEIDE F1+F2 fehlen.

        F1: release_all nicht vorhanden; F2: stage_hold_decision.py nicht vorhanden.

        BL-486 batch_3 RECONCILIATION (Verdict-Flip, KEINE Test-Aufweichung): seit
        F1-FIX (BL-486-AK-F1-FIX-PL-1) existiert release_all real -> um den
        "beide fehlen"-Pfad weiterhin zu pruefen, wird F1-Absenz via monkeypatch.delattr
        erzwungen. Assertions (FAIL + hint gesetzt) UNVERAENDERT.
        FAILT in RED: AttributeError. Nach GREEN: FAIL mit kombiniertem hint.
        """
        import stage_resource_registry as _srr
        import sanity_check_stage as _scs
        monkeypatch.delattr(_srr, "release_all", raising=False)
        result = _scs._behavior_check_f_release_eta()
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn F1 (release_all) + F2 (stage_hold_decision.py) beide fehlen"
        )
        assert result["hint"] is not None, "hint muss bei FAIL gesetzt sein"

    def test_check_f_returns_warn_when_release_all_exists_but_hold_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """G-F-4: WARN wenn release_all vorhanden (F1 ok) aber stage_hold_decision.py fehlt (F2).

        Monkeypatcht stage_resource_registry.release_all um F1 zu simulieren.
        FAILT in RED: AttributeError. Nach GREEN: WARN (F2 detektiert korrekt).
        """
        import stage_resource_registry as _srr
        import sanity_check_stage as _scs
        monkeypatch.setattr(_srr, "release_all", lambda: None, raising=False)
        result = _scs._behavior_check_f_release_eta()
        assert result["status"] == "WARN", (
            "Erwartet WARN wenn release_all gemockt vorhanden (F1 ok) "
            "aber stage_hold_decision.py fehlt (F2) -- G-F-4"
        )

    def test_sanity_check_stage_includes_check_f_in_result(self, tmp_path: Path) -> None:
        """G-F-5: sanity_check_stage() liefert Key 'F' unter checks-Dict.

        FAILT in RED: AssertionError (Key 'F' nicht vorhanden).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        assert "F" in result["checks"], (
            "Key 'F' fehlt in checks-Dict -- _behavior_check_f_release_eta nicht verdrahtet (G-F-5)"
        )

    # ======================================================================
    # CHECK REG -- _behavior_check_reg_registry
    # 6 Gold-Assertions (G-REG-1 bis G-REG-6)
    # Erwartet-Verdikt nach GREEN: PASS (stage_infra_schema.py kein IO; kein dritter Kanal)
    # ======================================================================

    def test_check_reg_function_exists(self) -> None:
        """G-REG-1: _behavior_check_reg_registry existiert in sanity_check_stage als callable.

        FAILT in RED: AttributeError (Funktion noch nicht implementiert).
        """
        import sanity_check_stage as _scs
        func = getattr(_scs, "_behavior_check_reg_registry", None)
        assert func is not None and callable(func), (
            "_behavior_check_reg_registry fehlt in sanity_check_stage.py "
            "(GREEN implementiert sie -- BL-486-AK-REG-PL-1)"
        )

    def test_check_reg_returns_fail_when_stage_infra_schema_has_io(
        self, tmp_path: Path
    ) -> None:
        """G-REG-2: FAIL wenn stage_infra_schema.py IO-Aufrufe (open/read_text) enthaelt (REG1).

        Stub mit open()-Call in tmp scripts_dir.
        FAILT in RED: AttributeError. Nach GREEN: FAIL (REG1 detektiert IO).
        """
        import sanity_check_stage as _scs
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "stage_infra_schema.py").write_text(
            "with open('stage_1.md') as f:\n    data = f.read()\n",
            encoding="utf-8",
        )
        result = _scs._behavior_check_reg_registry(scripts_dir=scripts_dir)
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn stage_infra_schema.py open()-Aufruf enthaelt (REG1)"
        )

    def test_check_reg_returns_warn_when_stage_infra_schema_not_found(
        self, tmp_path: Path
    ) -> None:
        """G-REG-3: WARN wenn stage_infra_schema.py nicht gefunden (REG1-Degradation).

        FAILT in RED: AttributeError. Nach GREEN: WARN (Datei fehlt -> Degradation).
        """
        import sanity_check_stage as _scs
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        # stage_infra_schema.py nicht anlegen
        result = _scs._behavior_check_reg_registry(scripts_dir=scripts_dir)
        assert result["status"] == "WARN", (
            "Erwartet WARN wenn stage_infra_schema.py in scripts_dir nicht gefunden (G-REG-3)"
        )

    def test_check_reg_returns_fail_when_third_channel_acquire_found(
        self, tmp_path: Path
    ) -> None:
        """G-REG-4: FAIL wenn srr.acquire( ausserhalb Registry-Schicht gefunden (REG2 dritter Kanal).

        Stub some_consumer.py mit srr.acquire(...)-Aufruf.
        FAILT in RED: AttributeError. Nach GREEN: FAIL (REG2 dritter Kanal detektiert).
        """
        import sanity_check_stage as _scs
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "stage_infra_schema.py").write_text(
            "def normalize(entry): return entry\n", encoding="utf-8"
        )
        (scripts_dir / "stage_resource_registry.py").write_text(
            "def acquire(bl_id): pass\n", encoding="utf-8"
        )
        (scripts_dir / "resource_allocator.py").write_text(
            "def acquire_all(): pass\n", encoding="utf-8"
        )
        (scripts_dir / "some_consumer.py").write_text(
            "srr.acquire(bl_id='BL-123')\n", encoding="utf-8"
        )
        result = _scs._behavior_check_reg_registry(scripts_dir=scripts_dir)
        assert result["status"] == "FAIL", (
            "Erwartet FAIL wenn srr.acquire( in some_consumer.py (dritter Kanal, REG2)"
        )

    def test_check_reg_returns_pass_for_current_codebase(self) -> None:
        """G-REG-5: PASS fuer aktuellen Codebase (stage_infra_schema kein IO; kein dritter Kanal).

        Echter Scan gegen .claude/scripts/-Verzeichnis.
        FAILT in RED: AttributeError. Nach GREEN: PASS (stabiler Zustand).
        """
        import sanity_check_stage as _scs
        scripts_dir = Path(__file__).parent
        result = _scs._behavior_check_reg_registry(scripts_dir=scripts_dir)
        assert result["status"] == "PASS", (
            "Erwartet PASS fuer aktuellen Codebase: stage_infra_schema.py ist reiner "
            "In-Memory-Parser (kein IO) und kein dritter acquire-Kanal vorhanden (G-REG-5)"
        )

    def test_sanity_check_stage_includes_check_reg_in_result(
        self, tmp_path: Path
    ) -> None:
        """G-REG-6: sanity_check_stage() liefert Key 'REG' unter checks-Dict.

        FAILT in RED: AssertionError (Key 'REG' nicht vorhanden).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        assert "REG" in result["checks"], (
            "Key 'REG' fehlt in checks-Dict -- _behavior_check_reg_registry nicht verdrahtet (G-REG-6)"
        )

    # ======================================================================
    # INTEGRATION -- alle 5 Checks in sanity_check_stage() verdrahtet
    # 5 Gold-Assertions (G-INT-1 bis G-INT-3; G-INT-4/5 sind N/A bis GREEN)
    # ======================================================================

    def test_sanity_check_stage_has_all_new_behavior_check_keys(
        self, tmp_path: Path
    ) -> None:
        """G-INT-1: Rueckgabe-Dict hat alle Keys A, C, D, F, REG unter checks.

        FAILT in RED: AssertionError (Keys fehlen da Checks nicht implementiert).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        missing = [k for k in ("A", "C", "D", "F", "REG") if k not in result["checks"]]
        assert not missing, (
            f"Fehlende Behavior-Gate-Check-Keys in checks-Dict: {missing} "
            "(alle 5 muessen nach GREEN verdrahtet sein -- G-INT-1)"
        )

    def test_sanity_check_stage_checks_dict_has_all_ten_keys(
        self, tmp_path: Path
    ) -> None:
        """G-INT-2: checks-Dict enthaelt alle erwarteten Keys (a/b/c/d/e + A/C/D/F/REG + E).

        Prueft dass checks-Dict genau die 11 erwarteten Keys enthaelt.
        BL-486 batch_2 (E-CHK) ergaenzt den 11. Key Gross-"E" (_behavior_check_e_elevation).
        FAILT in RED: AssertionError (Key "E" fehlt, da E-CHK noch nicht verdrahtet).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        expected_keys = {"a", "b", "c", "d", "e", "A", "C", "D", "F", "REG", "E"}
        present_keys = set(result["checks"].keys())
        fehlt = expected_keys - present_keys
        extra = present_keys - expected_keys
        assert not fehlt, (
            f"Fehlende Keys in checks-Dict: {fehlt} (G-INT-2)"
        )
        assert not extra, (
            f"Unerwartete Extra-Keys in checks-Dict: {extra} (G-INT-2)"
        )
        for k, v in result["checks"].items():
            assert v["status"] in ("PASS", "WARN", "FAIL"), (
                f"checks[{k!r}].status={v['status']!r} kein gueltiger Status"
            )

    def test_sanity_check_stage_print_report_outputs_new_behavior_labels(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """G-INT-3: _print_report() gibt neue Labels (A), (C), (D), (F), (REG) aus.

        FAILT in RED: AttributeError (Funktion liefert kein result['checks']['A'] etc.)
        oder AssertionError (Labels fehlen in Ausgabe).
        """
        import sanity_check_stage as _scs
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        _scs._print_report(1, result, live=False)
        out = capsys.readouterr().out
        for label in ("(A)", "(C)", "(D)", "(F)", "(REG)"):
            assert label in out, (
                f"Label {label!r} fehlt in _print_report()-Ausgabe (G-INT-3)"
            )


# ==========================================================================
# BL-486 batch_2 RED Tests — 6. Behavior-Gate-Check (AK-E Post-SDF-Elevation)
#
# Alle Tests in dieser Klasse FAILEN initial (vor GREEN) weil
# _behavior_check_e_elevation noch nicht existiert (AttributeError) und Key "E"
# noch nicht in den checks-Dict eingehaengt ist (KeyError/AssertionError).
#
# E-CHK ist der 6. Gate-Check neben der batch_1-Familie (A/C/D/F/REG). Sein
# Verdikt = worst_case(E1-Assert, E2-Assert, E3-Assert, E4-Assert), wobei jede
# Assertion das LIVE-Substrat introspektiert (Symbol-/Code-Scan, analog batch_1):
#   E1: guard_geist9b_sdf_post_inline.py — Post-SDF-Pfad vom enforce_active()-
#       file-Gate ENTKOPPELT (kein agent-erreichbarer Self-Unlock); OMNI_ENFORCE_ALL_OFF
#       (Owner-env) bleibt einzige Notbremse.
#   E2: guard_stage_elevation_audit.py — traegt stage_increment_has_preceding_post
#       (off-the-books-Elevation-Detektor, audit.jsonl-Rueckwaerts-Scan).
#   E3: manifest_schema.py — "epoch" in MANIFEST_SCHEMA["current_stage"] +
#       "batch_stages_original" required=True.
#   E4: guard_elevation_atomic.elevation_flush_is_atomic() == True
#       (temp + os.replace/_atomic_write + Rollback-Pfad belegt).
#
# Erwartetes Verdikt nach GREEN (Substrat E1-E4 JETZT alle gebaut+gruen):
#   worst_case(E1,E2,E3,E4) == PASS.
# Ehrlich (kein Wunsch-PASS): faengt eine Sub-Introspektion das Substrat NICHT,
# verdiktiert die Aggregation FAIL (wie batch_1 A/C/F bei fehlendem Substrat).
#
# Gold-Ref: 4_Blueprint/BL-486_batch2_gold_2026-06-29.md (E-CHK: 3 Exit-Kriterien)
# Blueprint-Ref: 4_Blueprint/BL-486_batch2_blueprint_2026-06-29.md §7 Item 2
# ==========================================================================


class TestBL486AKEElevationGate:
    """BL486-AK-E-CHK RED Tests — 6. Behavior-Gate-Check _behavior_check_e_elevation.

    RED-Zustand: _behavior_check_e_elevation existiert noch nicht (GREEN baut es).
    Verdict = worst_case(E1..E4); jede Sub-Assertion introspektiert das LIVE-Substrat.
    GREEN-Worker implementiert die Funktion + haengt sie unter Key "E" in den
    checks-Dict ein (sanity_check_stage.py:510-548), OHNE Gross-E in den globalen
    _worst_case (@:527-533) aufzunehmen (NOTE-Konvention, Namensraum klein-e != Gross-E).
    """

    @staticmethod
    def _setup_valid_stage(tmp_path: Path, stage_nr: int = 1) -> Path:
        """Lege vollstaendiges valides Slice-Set unter tmp_path/Stage/stage_{nr}_unit/ an."""
        stage_dir = _make_stage_dir(tmp_path, stage_nr=stage_nr, name="unit")
        _write_full_valid_slice_set(stage_dir)
        return stage_dir

    # ----------------------------------------------------------------------
    # Existenz + Signatur
    # ----------------------------------------------------------------------

    def test_check_e_function_exists(self) -> None:
        """G-E-1: _behavior_check_e_elevation existiert in sanity_check_stage als callable.

        FAILT in RED: AttributeError (Funktion noch nicht implementiert).
        """
        import sanity_check_stage as _scs
        func = getattr(_scs, "_behavior_check_e_elevation", None)
        assert func is not None and callable(func), (
            "_behavior_check_e_elevation fehlt in sanity_check_stage.py "
            "(GREEN implementiert sie -- BL-486-AK-E-CHK-PL-1)"
        )

    # ----------------------------------------------------------------------
    # Einhaengung: Key "E" im checks-Dict + Namensraum-Invariante (Gross-E != klein-e)
    # ----------------------------------------------------------------------

    def test_sanity_check_stage_includes_check_e_in_result(self, tmp_path: Path) -> None:
        """G-E-2: sanity_check_stage() liefert Key 'E' unter checks-Dict (Gross-E).

        FAILT in RED: AssertionError (Key 'E' nicht vorhanden, da nicht verdrahtet).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        assert "E" in result["checks"], (
            "Key 'E' fehlt in checks-Dict -- _behavior_check_e_elevation nicht "
            "verdrahtet (G-E-2 / Gold E-CHK Exit-Kriterium 1)"
        )

    def test_check_e_key_distinct_from_lowercase_e(self, tmp_path: Path) -> None:
        """G-E-3: Gross-'E' (AK-E) und klein-'e' (BL-412 Setup/Teardown) sind getrennte Keys.

        Namensraum-Invariante: kein Overwrite. Beide muessen unabhaengig im Dict liegen.
        FAILT in RED: KeyError/AssertionError (Gross-'E' fehlt).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        checks = result["checks"]
        assert "e" in checks, "klein-'e' (BL-412 Setup/Teardown) muss erhalten bleiben"
        assert "E" in checks, "Gross-'E' (AK-E Elevation-Gate) muss zusaetzlich vorhanden sein"
        # Verschiedene Dict-Eintraege (kein versehentlicher Alias/Overwrite).
        assert checks["e"] is not checks["E"], (
            "klein-'e' und Gross-'E' duerfen nicht dasselbe Check-Objekt sein "
            "(Namensraum-Kollision G-E-3)"
        )

    def test_check_e_status_is_valid_verdict(self, tmp_path: Path) -> None:
        """G-E-4: checks['E']['status'] ist ein gueltiger Verdict (PASS/WARN/FAIL) + hat hint-Key.

        FAILT in RED: KeyError (Key 'E' fehlt).
        """
        self._setup_valid_stage(tmp_path)
        result = sanity_check_stage(1, vault_root=tmp_path, live=False)
        check_e = result["checks"]["E"]
        assert "status" in check_e, "checks['E'] muss 'status' enthalten"
        assert check_e["status"] in ("PASS", "WARN", "FAIL"), (
            f"checks['E'].status={check_e['status']!r} kein gueltiger Verdict"
        )
        assert "hint" in check_e, "checks['E'] muss 'hint' enthalten"

    # ----------------------------------------------------------------------
    # Verdict-Aggregation = worst_case(E1..E4), introspektiert LIVE-Substrat
    # ----------------------------------------------------------------------

    def test_check_e_verdict_is_worst_case_of_four_subasserts(self) -> None:
        """G-E-5: _behavior_check_e_elevation verdiktiert worst_case(E1,E2,E3,E4).

        Da E1-E4 jetzt alle gebaut+gruen sind (LIVE-Substrat), erwartet PASS.
        Ehrlich: keine Wunsch-PASS-Klausel — wenn eine Sub-Introspektion das
        Substrat nicht findet, verdiktiert die Aggregation FAIL.

        FAILT in RED: AttributeError (_behavior_check_e_elevation existiert nicht).
        """
        import sanity_check_stage as _scs
        scripts_dir = Path(__file__).parent
        result = _scs._behavior_check_e_elevation(scripts_dir=scripts_dir)
        assert result["status"] == "PASS", (
            "Erwartet PASS: E1 (geist9b vom enforce_active()-Gate entkoppelt), "
            "E2 (stage-elevation-audit-Detektor), E3 (manifest_schema epoch), "
            "E4 (elevation_flush atomic) sind alle gebaut+gruen -> worst_case=PASS. "
            f"Got: {result}"
        )

    # ----------------------------------------------------------------------
    # E1-Sub-Assertion: geist9b blockt ohne Post-SDF (enforce_active()-Entkopplung)
    # ----------------------------------------------------------------------

    def test_check_e_e1_subassert_geist9b_decoupled(self) -> None:
        """G-E-6 (E1): E-CHK detektiert geist9b vom enforce_active()-file-Gate ENTKOPPELT.

        Substrat LIVE: guard_geist9b_sdf_post_inline.py existiert; der Post-SDF-Pfad
        haengt NICHT mehr hinter `if not enforce_active(): continue` (agent-erreichbarer
        Bypass entfernt); OMNI_ENFORCE_ALL_OFF (Owner-env) bleibt einzige Notbremse.
        E-CHK soll dieses Substrat als E1-PASS introspektieren.

        FAILT in RED: AttributeError (_behavior_check_e_elevation existiert nicht).
        """
        import sanity_check_stage as _scs
        scripts_dir = Path(__file__).parent
        result = _scs._behavior_check_e_elevation(scripts_dir=scripts_dir)
        # E-CHK ist PASS nur wenn ALLE 4 Sub-Asserts PASS -> E1 ist Teil davon.
        assert result["status"] == "PASS", (
            "E1-Sub-Assertion soll das geist9b-Substrat (enforce_active()-Entkopplung) "
            f"als PASS introspektieren. Aggregat-Verdikt: {result}"
        )

    # ----------------------------------------------------------------------
    # E2-Sub-Assertion: stage-elevation-audit faengt off-the-books-Elevation
    # ----------------------------------------------------------------------

    def test_check_e_e2_subassert_elevation_audit_present(self) -> None:
        """G-E-7 (E2): E-CHK detektiert guard_stage_elevation_audit.py + Detektor-Logik.

        Substrat LIVE: guard_stage_elevation_audit.py existiert + traegt
        stage_increment_has_preceding_post (audit.jsonl-Rueckwaerts-Scan).
        E-CHK soll dieses Substrat als E2-PASS introspektieren.

        FAILT in RED: AttributeError (_behavior_check_e_elevation existiert nicht).
        """
        import sanity_check_stage as _scs
        scripts_dir = Path(__file__).parent
        result = _scs._behavior_check_e_elevation(scripts_dir=scripts_dir)
        assert result["status"] == "PASS", (
            "E2-Sub-Assertion soll guard_stage_elevation_audit.py "
            f"(stage_increment_has_preceding_post) als PASS introspektieren. Aggregat: {result}"
        )

    # ----------------------------------------------------------------------
    # E3-Sub-Assertion: manifest_schema hat epoch + batch_stages_original required
    # ----------------------------------------------------------------------

    def test_check_e_e3_subassert_manifest_schema_epoch(self) -> None:
        """G-E-8 (E3): E-CHK detektiert manifest_schema.py epoch + batch_stages_original.

        Substrat LIVE: manifest_schema.MANIFEST_SCHEMA hat 'epoch' in
        current_stage.fields + 'batch_stages_original' required=True.
        E-CHK soll dieses Substrat als E3-PASS introspektieren (hard dep, kein false-FAIL).

        FAILT in RED: AttributeError (_behavior_check_e_elevation existiert nicht).
        """
        import sanity_check_stage as _scs
        scripts_dir = Path(__file__).parent
        result = _scs._behavior_check_e_elevation(scripts_dir=scripts_dir)
        assert result["status"] == "PASS", (
            "E3-Sub-Assertion soll manifest_schema.py (epoch + batch_stages_original "
            f"required) als PASS introspektieren. Aggregat: {result}"
        )

    # ----------------------------------------------------------------------
    # E4-Sub-Assertion: elevation_flush_is_atomic() (temp + os.replace + Rollback)
    # ----------------------------------------------------------------------

    def test_check_e_e4_subassert_elevation_flush_atomic(self) -> None:
        """G-E-9 (E4): E-CHK detektiert elevation_flush_is_atomic() == True.

        Substrat LIVE: guard_elevation_atomic.elevation_flush_is_atomic() returnt True
        (stage_elevation_flush.py traegt temp + os.replace/_atomic_write + Rollback-Pfad).
        E-CHK soll dieses Substrat als E4-PASS introspektieren.

        FAILT in RED: AttributeError (_behavior_check_e_elevation existiert nicht).
        """
        import sanity_check_stage as _scs
        scripts_dir = Path(__file__).parent
        result = _scs._behavior_check_e_elevation(scripts_dir=scripts_dir)
        assert result["status"] == "PASS", (
            "E4-Sub-Assertion soll elevation_flush_is_atomic() == True "
            f"(temp+os.replace+Rollback) als PASS introspektieren. Aggregat: {result}"
        )

    # ----------------------------------------------------------------------
    # Namensraum-Invariante (Code-Scan): Gross-E NICHT im globalen _worst_case
    # ----------------------------------------------------------------------

    def test_uppercase_e_not_in_global_worst_case(self) -> None:
        """G-E-10: Gross-'E' wird NICHT in den globalen worst_case eingerechnet.

        Wie A/C/D/F/REG (NOTE-Konvention :519-525): der globale _worst_case-Aufruf
        @:527-533 aggregiert NUR klein-a..e. Gross-E (+ A/C/D/F/REG) bleiben "N/A bis GREEN"
        -- ihr eigenes Verdikt steht im checks-Dict, korrumpiert aber die Gesamt-PASS-Rate nicht.

        Verifikation (verhaltensbasiert): selbst wenn checks['E'] != PASS waere, darf
        der globale verdict bei sonst-vollvalidem Stage PASS bleiben.

        FAILT in RED: KeyError (Key 'E' fehlt im checks-Dict).
        """
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            self._setup_valid_stage(tmp_path)
            result = sanity_check_stage(1, vault_root=tmp_path, live=False)
            # Key 'E' muss existieren (sonst RED).
            assert "E" in result["checks"], (
                "Key 'E' fehlt -- E-CHK nicht verdrahtet (G-E-10 Vorbedingung)"
            )
            # Globaler verdict spiegelt NUR klein-a..e (Gross-E ausserhalb).
            lowercase_verdict = _worst_case_helper(
                result["checks"]["a"]["status"],
                result["checks"]["b"]["status"],
                result["checks"]["c"]["status"],
                result["checks"]["d"]["status"],
                result["checks"]["e"]["status"],
            )
            assert result["verdict"] == lowercase_verdict, (
                "Globaler verdict muss worst_case(klein-a..e) sein -- Gross-E (und A/C/D/F/REG) "
                f"NICHT eingerechnet. verdict={result['verdict']!r}, "
                f"erwartet(klein-a..e)={lowercase_verdict!r} (G-E-10)"
            )


_RANK_HELPER = {"FAIL": 2, "WARN": 1, "PASS": 0}


def _worst_case_helper(*statuses: str) -> str:
    """Test-lokaler Spiegel von sanity_check_stage._worst_case (FAIL>WARN>PASS).

    Bewusst dupliziert (kein Import des privaten Symbols), damit der Test die
    Namensraum-Invariante UNABHAENGIG vom Produktiv-Code verifiziert.
    """
    best = 0
    for s in statuses:
        best = max(best, _RANK_HELPER.get(s, 0))
    return ("PASS", "WARN", "FAIL")[best]
