#!/usr/bin/env python3
"""test_resolve_vault_meta.py — 3-Faelle fuer resolve_vault_meta (BL-193 PL-7).

Testet:
  1. Local-Override: .claude/meta/{path} existiert -> gewinnt (Vault ignoriert)
  2. Vault-Typ: nicht lokal, aber in Typen/DCSRE vorhanden -> Typ-Pfad
  3. Vault-Universal: nicht lokal, nicht in Typ, nur in Universal -> Universal-Pfad

Hinweis Migrations-Phase: .claude/meta/ und Vault koexistieren. Tests nutzen
temporaere Verzeichnisse als cwd um lokale Overrides zu umgehen.

BL-193 TG-1 RED-Test (AK2-PL-5):
  4. NOT_FOUND exitcode — AK2-PL-5 fordert exitcode 2, Bug: aktuell exitcode 1
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from resolve_vault_meta import resolve_meta, resolve_command_sidecar  # noqa: E402

VAULT_ROOT = Path("C:/Users/Administrator/Documents/OmniCommand")
PROJECT_ROOT = Path("C:/Users/Administrator/Documents/Projekt/OmniCommand/OmniCommand")
PASS = 0
FAIL = 0
original_cwd = str(Path.cwd())


def assert_eq(label: str, actual, expected) -> None:
    global PASS, FAIL
    if actual == expected:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label}")
        print(f"        expected: {expected}")
        print(f"        actual:   {actual}")
        FAIL += 1


def assert_not_none(label: str, actual) -> None:
    global PASS, FAIL
    if actual is not None:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        print(f"  FAIL: {label} — expected non-None, got None")
        FAIL += 1


def main() -> None:
    global PASS, FAIL
    # ---------------------------------------------------------------------------
    # Test 1: Vault-Universal lookup (file only in Universal, cwd has no local meta)
    # ---------------------------------------------------------------------------
    print("\n[Test 1] Vault-Universal: INV-PL-VAULT.md (env-pinned vault, BL-376 Fund #3)")
    tmpdir1 = tempfile.mkdtemp()
    _orig1 = os.environ.get("CLAUDE_VAULT_ROOT")
    try:
        # BL-376 Fund #3: hardcoded OmniCommand-Default RAUS -> Vault explizit env-pinnen
        # (frueher beruhte dieser Test auf dem Default aus einem neutralen tmpdir).
        os.environ["CLAUDE_VAULT_ROOT"] = str(VAULT_ROOT)
        os.chdir(tmpdir1)
        result_uni = resolve_meta("INV-PL-VAULT.md")
        expected_uni = VAULT_ROOT / "Meta" / "Universal" / "INV-PL-VAULT.md"
        assert_not_none("result not None (found in Universal)", result_uni)
        if result_uni:
            assert_eq("resolved to Universal path", result_uni, expected_uni)
    finally:
        os.chdir(original_cwd)
        if _orig1 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig1
        try:
            import shutil
            shutil.rmtree(tmpdir1, ignore_errors=True)
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # Test 2: Vault-Typ (DCSRE) lookup (file in DCSRE Typen, cwd triggers DCSRE)
    # ---------------------------------------------------------------------------
    print("\n[Test 2] Vault-Typ DCSRE: architekturKonventionen/be-core.md (env-pinned vault, BL-376 Fund #3)")
    tmpdir2 = tempfile.mkdtemp(prefix="OmniCommand_test_")
    _orig2 = os.environ.get("CLAUDE_VAULT_ROOT")
    try:
        # tmpdir2 path contains OmniCommand -> resolve_project_typ() returns DCSRE.
        # No .claude/meta/ here -> local override skipped. BL-376 Fund #3: Vault explizit env-pinnen
        # (hardcoded Default RAUS); resolve_project_typ bleibt cwd-basiert (OmniCommand-prefix -> DCSRE).
        os.environ["CLAUDE_VAULT_ROOT"] = str(VAULT_ROOT)
        os.chdir(tmpdir2)
        result_typ = resolve_meta("architekturKonventionen/be-core.md")
        expected_typ = (
            VAULT_ROOT / "Meta" / "Typen" / "DCSRE" / "architekturKonventionen" / "be-core.md"
        )
        assert_not_none("result not None (found in Typen/DCSRE)", result_typ)
        if result_typ:
            assert_eq("resolved to Typen/DCSRE path", result_typ, expected_typ)
    finally:
        os.chdir(original_cwd)
        if _orig2 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig2
        try:
            import shutil
            shutil.rmtree(tmpdir2, ignore_errors=True)
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # Test 3: Local-Override wins over Vault (AK10-PL-1: uses .claude/meta-override/)
    # ---------------------------------------------------------------------------
    print("\n[Test 3] Local-Override: sdf/state-machine.md local wins over Vault")
    # AK10-PL-1: override path is now .claude/meta-override/ (not .claude/meta/)
    tmpdir3 = tempfile.mkdtemp(prefix="proj_t3_OmniCommand_")
    try:
        _override3 = Path(tmpdir3) / ".claude" / "meta-override" / "sdf"
        _override3.mkdir(parents=True, exist_ok=True)
        (_override3 / "state-machine.md").write_text("LOCAL-OVERRIDE-CONTENT", encoding="utf-8")
        _orig3 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = str(VAULT_ROOT)
        os.chdir(tmpdir3)
        result_local = resolve_meta("sdf/state-machine.md")
        expected_local = Path(tmpdir3) / ".claude" / "meta-override" / "sdf" / "state-machine.md"
        vault_path = VAULT_ROOT / "Meta" / "Universal" / "sdf" / "state-machine.md"
        assert_not_none("result not None", result_local)
        if result_local:
            assert_eq("local override wins (meta-override path returned)", result_local, expected_local)
            if result_local != vault_path:
                print(f"  PASS: local path differs from vault path (override confirmed)")
                PASS += 1
            else:
                print(f"  FAIL: returned vault path instead of local override")
                FAIL += 1
    finally:
        os.chdir(original_cwd)
        if _orig3 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig3
        try:
            import shutil as _shutil3
            _shutil3.rmtree(tmpdir3, ignore_errors=True)
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # Test 4 (RED): NOT_FOUND exitcode — BL-193 TG-1 AK2-PL-5
    #   AK2-PL-5 fordert exitcode 2 bei NOT_FOUND.
    #   Bug: aktuell gibt resolve_vault_meta.py exitcode 1 zurueck (sys.exit(1)).
    #   Dieser Test MUSS solange FAIL zeigen bis _TDD_green den Fix anwendet.
    # ---------------------------------------------------------------------------
    print("\n[Test 4 RED] NOT_FOUND exitcode: nonexistent_key -> expected exitcode 2")
    _RESOLVE_SCRIPT = str(Path(__file__).parent / "resolve_vault_meta.py")
    _proc = subprocess.run(
        [sys.executable, _RESOLVE_SCRIPT, "--key", "nonexistent_key_bl193_tg1_red"],
        capture_output=True,
        text=True,
    )
    assert_eq(
        "test_resolve_vault_meta_not_found_exitcode_is_2 — exitcode == 2 (AK2-PL-5)",
        _proc.returncode,
        2,
    )
    # Kommentar: Aktuell gibt resolve_vault_meta.py sys.exit(1) zurueck -> Test FAIL (RED).
    # Nach _TDD_green Fix (sys.exit(1) -> sys.exit(2)) wird dieser Test PASS.

    # ---------------------------------------------------------------------------
    # Test 5 (AK-4 RED): Override-Priority-Chain — Vault-Typ gewinnt ueber Vault-Universal
    #   Wenn dieselbe Datei sowohl in Vault-Typ als auch in Vault-Universal existiert,
    #   MUSS Vault-Typ-Pfad zurueckgegeben werden (Ebene 2 > Ebene 3).
    #   RED: Kein bestehender Test prueft diesen Priority-Fall.
    # ---------------------------------------------------------------------------
    print("\n[Test 5 AK-4 RED] test_resolve_meta_override_priorities: Typ gewinnt ueber Universal")
    import shutil  # noqa: E402
    tmpvault5 = tempfile.mkdtemp(prefix="mock_vault_t5_")
    tmpdir5 = tempfile.mkdtemp(prefix="proj_t5_OmniCommand_")
    try:
        # Erstelle Mock-Vault mit Datei in BEIDEN Ebenen (Typ + Universal)
        _rel = "architekturKonventionen/test-priority.md"
        _typ_path = Path(tmpvault5) / "Meta" / "Typen" / "DCSRE" / "architekturKonventionen"
        _uni_path = Path(tmpvault5) / "Meta" / "Universal" / "architekturKonventionen"
        _typ_path.mkdir(parents=True, exist_ok=True)
        _uni_path.mkdir(parents=True, exist_ok=True)
        (_typ_path / "test-priority.md").write_text("TYP-VERSION", encoding="utf-8")
        (_uni_path / "test-priority.md").write_text("UNIVERSAL-VERSION", encoding="utf-8")

        # Kein .claude/meta/ im tmpdir5 -> Local-Override ist inaktiv
        # tmpdir5 enthaelt "OmniCommand" im Pfad -> resolve_project_typ() = DCSRE
        _orig_env = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = tmpvault5
        os.chdir(tmpdir5)
        _result5 = resolve_meta(_rel)
        _expected5 = Path(tmpvault5) / "Meta" / "Typen" / "DCSRE" / _rel
        assert_not_none("test_resolve_meta_override_priorities — result not None", _result5)
        if _result5:
            assert_eq(
                "test_resolve_meta_override_priorities — Vault-Typ gewinnt ueber Universal",
                _result5,
                _expected5,
            )
            # Zusatz-Check: Universal-Pfad wurde NICHT zurueckgegeben
            _wrong5 = Path(tmpvault5) / "Meta" / "Universal" / _rel
            if _result5 != _wrong5:
                print("  PASS: test_resolve_meta_override_priorities — Universal-Pfad korrekt ignoriert")
                PASS += 1
            else:
                print("  FAIL: test_resolve_meta_override_priorities — Universal-Pfad faelschlicherweise zurueckgegeben")
                FAIL += 1
    finally:
        os.chdir(original_cwd)
        if _orig_env is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig_env
        shutil.rmtree(tmpvault5, ignore_errors=True)
        shutil.rmtree(tmpdir5, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 6 (AK-4 RED): test_resolve_meta_priority_override — Local gewinnt ueber Typ UND Universal
    #   Wenn Datei in ALLEN 3 Ebenen (Local + Typ + Universal) existiert,
    #   MUSS die Local-Override-Version zurueckgegeben werden (Ebene 1 > Ebene 2 > Ebene 3).
    #   RED: Kein bestehender Test prueft den vollen 3-Ebenen-Priority-Stack.
    # ---------------------------------------------------------------------------
    print("\n[Test 6 AK-4 RED] test_resolve_meta_priority_override: Local gewinnt ueber Typ + Universal")
    tmpvault6 = tempfile.mkdtemp(prefix="mock_vault_t6_")
    tmpdir6 = tempfile.mkdtemp(prefix="proj_t6_OmniCommand_")
    try:
        _rel6 = "architekturKonventionen/test-priority-full.md"
        # Vault: Datei in Typ + Universal
        _typ6 = Path(tmpvault6) / "Meta" / "Typen" / "DCSRE" / "architekturKonventionen"
        _uni6 = Path(tmpvault6) / "Meta" / "Universal" / "architekturKonventionen"
        _typ6.mkdir(parents=True, exist_ok=True)
        _uni6.mkdir(parents=True, exist_ok=True)
        (_typ6 / "test-priority-full.md").write_text("TYP-VERSION", encoding="utf-8")
        (_uni6 / "test-priority-full.md").write_text("UNIVERSAL-VERSION", encoding="utf-8")
        # Local: .claude/meta-override/{rel} im tmpdir6 (AK10-PL-1: override path)
        _local6 = Path(tmpdir6) / ".claude" / "meta-override" / "architekturKonventionen"
        _local6.mkdir(parents=True, exist_ok=True)
        (_local6 / "test-priority-full.md").write_text("LOCAL-VERSION", encoding="utf-8")

        _orig_env6 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = tmpvault6
        os.chdir(tmpdir6)
        _result6 = resolve_meta(_rel6)
        _expected6 = Path(tmpdir6) / ".claude" / "meta-override" / _rel6
        assert_not_none("test_resolve_meta_priority_override — result not None", _result6)
        if _result6:
            assert_eq(
                "test_resolve_meta_priority_override — Local gewinnt ueber Typ + Universal",
                _result6,
                _expected6,
            )
            # Sicherstellen dass weder Typ noch Universal zurueckgegeben wurde
            _typ_wrong = Path(tmpvault6) / "Meta" / "Typen" / "DCSRE" / _rel6
            _uni_wrong = Path(tmpvault6) / "Meta" / "Universal" / _rel6
            if _result6 not in (_typ_wrong, _uni_wrong):
                print("  PASS: test_resolve_meta_priority_override — Vault-Pfade korrekt ignoriert")
                PASS += 1
            else:
                print("  FAIL: test_resolve_meta_priority_override — Vault-Pfad faelschlicherweise zurueckgegeben")
                FAIL += 1
    finally:
        os.chdir(original_cwd)
        if _orig_env6 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig_env6
        shutil.rmtree(tmpvault6, ignore_errors=True)
        shutil.rmtree(tmpdir6, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 7 (AK7-PL-3): meta-cache-Typ fallback — Vault FAIL + meta-cache vorhanden
    # ---------------------------------------------------------------------------
    print("\n[Test 7 AK7-PL-3] test_resolve_vault_meta_metacache_fallback")
    import uuid  # noqa: E402
    tmpvault7 = "/nonexistent/vault_" + uuid.uuid4().hex
    tmpdir7 = tempfile.mkdtemp(prefix="proj_t7_OmniCommand_")
    try:
        _rel7 = "architekturKonventionen/be-core.md"
        _cache7 = Path(tmpdir7) / ".claude" / "meta-cache" / "Typen" / "DCSRE" / "architekturKonventionen"
        _cache7.mkdir(parents=True, exist_ok=True)
        (_cache7 / "be-core.md").write_text("CACHE-CONTENT", encoding="utf-8")
        _orig7 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = tmpvault7
        os.chdir(tmpdir7)
        _result7 = resolve_meta(_rel7)
        _expected7 = Path(tmpdir7) / ".claude" / "meta-cache" / "Typen" / "DCSRE" / _rel7
        assert_not_none("test_resolve_vault_meta_metacache_fallback — result not None", _result7)
        if _result7:
            assert_eq("test_resolve_vault_meta_metacache_fallback — meta-cache-Typ geliefert", _result7, _expected7)
    finally:
        os.chdir(original_cwd)
        if _orig7 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig7
        shutil.rmtree(tmpdir7, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 8 (AK7-PL-3): meta-cache-Typ — Vault FAIL + Typ-Datei aus meta-cache
    # ---------------------------------------------------------------------------
    print("\n[Test 8 AK7-PL-3] test_resolve_vault_meta_metacache_offline_typ")
    tmpdir8 = tempfile.mkdtemp(prefix="proj_t8_OmniCommand_")
    try:
        _rel8 = "architekturKonventionen/layers.md"
        _cache8 = Path(tmpdir8) / ".claude" / "meta-cache" / "Typen" / "DCSRE" / "architekturKonventionen"
        _cache8.mkdir(parents=True, exist_ok=True)
        (_cache8 / "layers.md").write_text("DCSRE-LAYERS", encoding="utf-8")
        _orig8 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = "/nonexistent/vault_offline_8"
        os.chdir(tmpdir8)
        _result8 = resolve_meta(_rel8)
        _expected8 = Path(tmpdir8) / ".claude" / "meta-cache" / "Typen" / "DCSRE" / _rel8
        assert_not_none("test_resolve_vault_meta_metacache_offline_typ — result not None", _result8)
        if _result8:
            assert_eq("test_resolve_vault_meta_metacache_offline_typ — Typ-Datei aus meta-cache", _result8, _expected8)
    finally:
        os.chdir(original_cwd)
        if _orig8 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig8
        shutil.rmtree(tmpdir8, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 9 (AK7-PL-3): meta-cache-Universal — Vault FAIL + Universal-Datei aus meta-cache
    # ---------------------------------------------------------------------------
    print("\n[Test 9 AK7-PL-3] test_resolve_vault_meta_metacache_offline_universal")
    tmpdir9 = tempfile.mkdtemp(prefix="proj_t9_OmniCommand_")
    try:
        _rel9 = "INV-META.md"
        _cache9_uni = Path(tmpdir9) / ".claude" / "meta-cache" / "Universal"
        _cache9_uni.mkdir(parents=True, exist_ok=True)
        (_cache9_uni / "INV-META.md").write_text("UNIVERSAL-CACHE", encoding="utf-8")
        _orig9 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = "/nonexistent/vault_offline_9"
        os.chdir(tmpdir9)
        _result9 = resolve_meta(_rel9)
        _expected9 = Path(tmpdir9) / ".claude" / "meta-cache" / "Universal" / _rel9
        assert_not_none("test_resolve_vault_meta_metacache_offline_universal — result not None", _result9)
        if _result9:
            assert_eq("test_resolve_vault_meta_metacache_offline_universal — Universal aus meta-cache", _result9, _expected9)
    finally:
        os.chdir(original_cwd)
        if _orig9 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig9
        shutil.rmtree(tmpdir9, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 10 (AK7-PL-3): Vault FAIL + kein meta-cache → Exitcode 2 + "meta-snapshot" in stderr
    # ---------------------------------------------------------------------------
    print("\n[Test 10 AK7-PL-3] test_resolve_vault_meta_metacache_not_found")
    _RESOLVE_SCRIPT = str(Path(__file__).parent / "resolve_vault_meta.py")
    _env10 = {**os.environ, "CLAUDE_VAULT_ROOT": "/nonexistent/vault_no_cache_10"}
    _proc10 = subprocess.run(
        [sys.executable, _RESOLVE_SCRIPT, "some/file/that/does/not/exist.md"],
        capture_output=True,
        text=True,
        env=_env10,
        cwd=tempfile.gettempdir(),
    )
    assert_eq("test_resolve_vault_meta_metacache_not_found — exitcode 2", _proc10.returncode, 2)
    assert_eq(
        "test_resolve_vault_meta_metacache_not_found — stderr contains NOT_FOUND",
        "NOT_FOUND" in _proc10.stderr,
        True,
    )

    # ---------------------------------------------------------------------------
    # Test 11 (AK9-PL-3): _redeploy.md — kein aktiver --meta Block (nur deprecated-Block)
    # ---------------------------------------------------------------------------
    print("\n[Test 11 AK9-PL-3] test_redeploy_meta_deprecated")
    _redeploy_path = Path("C:/Users/Administrator/Documents/Projekt/OmniCommand/OmniCommand/.claude/commands/_redeploy.md")
    if _redeploy_path.exists():
        _content = _redeploy_path.read_text(encoding="utf-8")
        _lines = _content.splitlines()
        _active_meta_lines = []
        _in_deprecated_block = False
        for _line in _lines:
            if "### --meta (deprecated)" in _line:
                _in_deprecated_block = True
            elif _line.startswith("###") and _in_deprecated_block:
                _in_deprecated_block = False
            if not _in_deprecated_block and "--meta" in _line and "--meta-snapshot" not in _line and "--meta-" not in _line:
                if "--meta" in _line:
                    _active_meta_lines.append(_line.strip())
        assert_eq(
            "test_redeploy_meta_deprecated — kein aktives --meta ausserhalb Deprecated-Block",
            len(_active_meta_lines),
            0,
        )
        if _active_meta_lines:
            print(f"  DETAILS: Gefunden: {_active_meta_lines[:3]}")
    else:
        print(f"  SKIP: _redeploy.md nicht gefunden unter {_redeploy_path}")

    # ---------------------------------------------------------------------------
    # Test 12 (AK10-PL-3): test_override_wins_over_vault_typ
    #   meta-override/ + Vault-Typ beide vorhanden → Override-Pfad gewinnt
    # ---------------------------------------------------------------------------
    print("\n[Test 12 AK10-PL-3] test_override_wins_over_vault_typ")
    _tmpvault12 = tempfile.mkdtemp(prefix="mock_vault_t12_")
    _tmpdir12 = tempfile.mkdtemp(prefix="proj_t12_OmniCommand_")
    try:
        _rel12 = "architekturKonventionen/t12-override.md"
        _typ12 = Path(_tmpvault12) / "Meta" / "Typen" / "DCSRE" / "architekturKonventionen"
        _typ12.mkdir(parents=True, exist_ok=True)
        (_typ12 / "t12-override.md").write_text("TYP-CONTENT", encoding="utf-8")
        _ov12 = Path(_tmpdir12) / ".claude" / "meta-override" / "architekturKonventionen"
        _ov12.mkdir(parents=True, exist_ok=True)
        (_ov12 / "t12-override.md").write_text("OVERRIDE-CONTENT", encoding="utf-8")
        _orig12 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = _tmpvault12
        os.chdir(_tmpdir12)
        _result12 = resolve_meta(_rel12)
        _expected12 = Path(_tmpdir12) / ".claude" / "meta-override" / _rel12
        assert_not_none("test_override_wins_over_vault_typ — result not None", _result12)
        if _result12:
            assert_eq(
                "test_override_wins_over_vault_typ — meta-override gewinnt ueber Vault-Typ",
                _result12,
                _expected12,
            )
    finally:
        os.chdir(original_cwd)
        if _orig12 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig12
        shutil.rmtree(_tmpvault12, ignore_errors=True)
        shutil.rmtree(_tmpdir12, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 13 (AK10-PL-3): test_vault_typ_when_no_override
    #   kein Override, Vault-Typ hat Datei → Vault-Typ-Pfad
    # ---------------------------------------------------------------------------
    print("\n[Test 13 AK10-PL-3] test_vault_typ_when_no_override")
    _tmpvault13 = tempfile.mkdtemp(prefix="mock_vault_t13_")
    _tmpdir13 = tempfile.mkdtemp(prefix="proj_t13_OmniCommand_")
    try:
        _rel13 = "architekturKonventionen/t13-typ.md"
        _typ13 = Path(_tmpvault13) / "Meta" / "Typen" / "DCSRE" / "architekturKonventionen"
        _typ13.mkdir(parents=True, exist_ok=True)
        (_typ13 / "t13-typ.md").write_text("TYP-CONTENT", encoding="utf-8")
        _orig13 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = _tmpvault13
        os.chdir(_tmpdir13)
        _result13 = resolve_meta(_rel13)
        _expected13 = Path(_tmpvault13) / "Meta" / "Typen" / "DCSRE" / _rel13
        assert_not_none("test_vault_typ_when_no_override — result not None", _result13)
        if _result13:
            assert_eq(
                "test_vault_typ_when_no_override — Vault-Typ-Pfad zurueck",
                _result13,
                _expected13,
            )
    finally:
        os.chdir(original_cwd)
        if _orig13 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig13
        shutil.rmtree(_tmpvault13, ignore_errors=True)
        shutil.rmtree(_tmpdir13, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 14 (AK10-PL-3): test_vault_universal_fallback
    #   kein Override, kein Typ → Vault-Universal-Pfad
    # ---------------------------------------------------------------------------
    print("\n[Test 14 AK10-PL-3] test_vault_universal_fallback")
    _tmpvault14 = tempfile.mkdtemp(prefix="mock_vault_t14_")
    _tmpdir14 = tempfile.mkdtemp(prefix="proj_t14_OmniCommand_")
    try:
        _rel14 = "INV-t14-universal.md"
        _uni14 = Path(_tmpvault14) / "Meta" / "Universal"
        _uni14.mkdir(parents=True, exist_ok=True)
        (_uni14 / "INV-t14-universal.md").write_text("UNIVERSAL-CONTENT", encoding="utf-8")
        _orig14 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = _tmpvault14
        os.chdir(_tmpdir14)
        _result14 = resolve_meta(_rel14)
        _expected14 = Path(_tmpvault14) / "Meta" / "Universal" / _rel14
        assert_not_none("test_vault_universal_fallback — result not None", _result14)
        if _result14:
            assert_eq(
                "test_vault_universal_fallback — Vault-Universal-Pfad zurueck",
                _result14,
                _expected14,
            )
    finally:
        os.chdir(original_cwd)
        if _orig14 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig14
        shutil.rmtree(_tmpvault14, ignore_errors=True)
        shutil.rmtree(_tmpdir14, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 15 (AK10-PL-3): test_not_found_exitcode_2
    #   kein Override, kein Vault, kein Cache → exitcode 2
    # ---------------------------------------------------------------------------
    print("\n[Test 15 AK10-PL-3] test_not_found_when_no_override_no_vault")
    _RESOLVE_SCRIPT15 = str(Path(__file__).parent / "resolve_vault_meta.py")
    _tmpdir15 = tempfile.mkdtemp(prefix="proj_t15_empty_")
    _env15 = {**os.environ, "CLAUDE_VAULT_ROOT": "/nonexistent/vault_t15_empty"}
    _proc15 = subprocess.run(
        [sys.executable, _RESOLVE_SCRIPT15, "nonexistent_t15_file.md"],
        capture_output=True,
        text=True,
        env=_env15,
        cwd=_tmpdir15,
    )
    assert_eq(
        "test_not_found_when_no_override_no_vault — exitcode 2",
        _proc15.returncode,
        2,
    )
    assert_eq(
        "test_not_found_when_no_override_no_vault — NOT_FOUND in stderr",
        "NOT_FOUND" in _proc15.stderr,
        True,
    )
    shutil.rmtree(_tmpdir15, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 16 (AK10-PL-3 + AK10-PL-2): test_stale_override_warn
    #   Override aelter als Vault-Typ → WARN auf stderr; Override-Pfad (exitcode 0)
    # ---------------------------------------------------------------------------
    print("\n[Test 16 AK10-PL-3/PL-2] test_stale_override_warn")
    import time as _time  # noqa: E402
    _RESOLVE_SCRIPT16 = str(Path(__file__).parent / "resolve_vault_meta.py")
    _tmpvault16 = tempfile.mkdtemp(prefix="mock_vault_t16_")
    _tmpdir16 = tempfile.mkdtemp(prefix="proj_t16_OmniCommand_")
    try:
        _rel16 = "architekturKonventionen/t16-stale.md"
        # Create override first (will be older)
        _ov16 = Path(_tmpdir16) / ".claude" / "meta-override" / "architekturKonventionen"
        _ov16.mkdir(parents=True, exist_ok=True)
        _ov16_file = _ov16 / "t16-stale.md"
        _ov16_file.write_text("STALE-OVERRIDE", encoding="utf-8")
        # Force override mtime to be 10s in the past
        _old_time = _time.time() - 10
        import os as _os16
        _os16.utime(_ov16_file, (_old_time, _old_time))
        # Create vault-typ file (will be newer)
        _typ16 = Path(_tmpvault16) / "Meta" / "Typen" / "DCSRE" / "architekturKonventionen"
        _typ16.mkdir(parents=True, exist_ok=True)
        (_typ16 / "t16-stale.md").write_text("VAULT-TYP-CONTENT", encoding="utf-8")
        _env16 = {**os.environ, "CLAUDE_VAULT_ROOT": _tmpvault16}
        _proc16 = subprocess.run(
            [sys.executable, _RESOLVE_SCRIPT16, "--verbose", _rel16],
            capture_output=True,
            text=True,
            env=_env16,
            cwd=_tmpdir16,
        )
        # Override still wins (exitcode 0)
        assert_eq("test_stale_override_warn — exitcode 0 (override wins)", _proc16.returncode, 0)
        # WARN in stderr
        assert_eq(
            "test_stale_override_warn — [WARN] stale override in stderr",
            "[WARN]" in _proc16.stderr or "stale" in _proc16.stderr.lower(),
            True,
        )
        # [RESOLVED] via local-override in stderr
        assert_eq(
            "test_stale_override_warn — [RESOLVED] via local-override in stderr",
            "local-override" in _proc16.stderr,
            True,
        )
    finally:
        shutil.rmtree(_tmpvault16, ignore_errors=True)
        shutil.rmtree(_tmpdir16, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 17 (BL-193 command-migration): Legacy .claude/meta/ fallback (Tier 6)
    #   Vault FAIL + kein meta-cache + kein meta-override, aber .claude/meta/{path}
    #   existiert -> Tier 6 liefert den Legacy-Pfad (non-downgrading-Garantie fuer
    #   die {META}/X-Token-Migration der Commands).
    # ---------------------------------------------------------------------------
    print("\n[Test 17 BL-193] test_legacy_meta_fallback_tier6")
    _tmpdir17 = tempfile.mkdtemp(prefix="proj_t17_OmniCommand_")
    try:
        _rel17 = "implementation/testing.md"
        _legacy17 = Path(_tmpdir17) / ".claude" / "meta" / "implementation"
        _legacy17.mkdir(parents=True, exist_ok=True)
        (_legacy17 / "testing.md").write_text("LEGACY-META-CONTENT", encoding="utf-8")
        _orig17 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = "/nonexistent/vault_t17_legacy"
        os.chdir(_tmpdir17)
        _result17 = resolve_meta(_rel17)
        _expected17 = Path(_tmpdir17) / ".claude" / "meta" / _rel17
        assert_not_none("test_legacy_meta_fallback_tier6 — result not None", _result17)
        if _result17:
            assert_eq("test_legacy_meta_fallback_tier6 — Legacy .claude/meta/ geliefert", _result17, _expected17)
    finally:
        os.chdir(original_cwd)
        if _orig17 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig17
        shutil.rmtree(_tmpdir17, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 18 (BL-193): Vault-Typ gewinnt ueber Legacy (Tier 2 > Tier 6, kein Regress)
    # ---------------------------------------------------------------------------
    print("\n[Test 18 BL-193] test_vault_typ_wins_over_legacy")
    _tmpvault18 = tempfile.mkdtemp(prefix="mock_vault_t18_")
    _tmpdir18 = tempfile.mkdtemp(prefix="proj_t18_OmniCommand_")
    try:
        _rel18 = "architekturKonventionen/t18.md"
        _typ18 = Path(_tmpvault18) / "Meta" / "Typen" / "DCSRE" / "architekturKonventionen"
        _typ18.mkdir(parents=True, exist_ok=True)
        (_typ18 / "t18.md").write_text("VAULT-TYP", encoding="utf-8")
        _legacy18 = Path(_tmpdir18) / ".claude" / "meta" / "architekturKonventionen"
        _legacy18.mkdir(parents=True, exist_ok=True)
        (_legacy18 / "t18.md").write_text("LEGACY", encoding="utf-8")
        _orig18 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = _tmpvault18
        os.chdir(_tmpdir18)
        _result18 = resolve_meta(_rel18)
        _expected18 = Path(_tmpvault18) / "Meta" / "Typen" / "DCSRE" / _rel18
        assert_eq("test_vault_typ_wins_over_legacy — Vault-Typ gewinnt (kein Regress)", _result18, _expected18)
    finally:
        os.chdir(original_cwd)
        if _orig18 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig18
        shutil.rmtree(_tmpvault18, ignore_errors=True)
        shutil.rmtree(_tmpdir18, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 19 (BL-372 AK-9 / T1): resolve_command_sidecar — Sidecar existiert -> Path
    # ---------------------------------------------------------------------------
    print("\n[Test 19 BL-372 AK-9] test_resolve_command_sidecar_exists")
    _tmpvault19 = tempfile.mkdtemp(prefix="mock_vault_t19_")
    _tmpdir19 = tempfile.mkdtemp(prefix="proj_t19_OmniCommand_")
    try:
        _cmds19 = Path(_tmpvault19) / "_meta" / "commands"
        _cmds19.mkdir(parents=True, exist_ok=True)
        (_cmds19 / "_goal_backlog_Meta.md").write_text("SIDECAR-CONTENT", encoding="utf-8")
        _orig19 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = _tmpvault19
        os.chdir(_tmpdir19)
        _result19 = resolve_command_sidecar("_goal_backlog")
        _expected19 = Path(_tmpvault19) / "_meta" / "commands" / "_goal_backlog_Meta.md"
        assert_not_none("test_resolve_command_sidecar_exists — result not None", _result19)
        if _result19:
            assert_eq("test_resolve_command_sidecar_exists — command-keyed Sidecar-Pfad zurueck", _result19, _expected19)
    finally:
        os.chdir(original_cwd)
        if _orig19 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig19
        shutil.rmtree(_tmpvault19, ignore_errors=True)
        shutil.rmtree(_tmpdir19, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 20 (BL-372 AK-9 / T2): resolve_command_sidecar — Sidecar fehlt -> None (kein Crash)
    #   Always-Try-Load (AK-2/AK-3): fehlende Datei ist KEIN Fehler.
    # ---------------------------------------------------------------------------
    print("\n[Test 20 BL-372 AK-9] test_resolve_command_sidecar_absent_is_none")
    _tmpvault20 = tempfile.mkdtemp(prefix="mock_vault_t20_")
    _tmpdir20 = tempfile.mkdtemp(prefix="proj_t20_OmniCommand_")
    try:
        # _meta/commands/ existiert, aber NICHT der angefragte Sidecar
        (Path(_tmpvault20) / "_meta" / "commands").mkdir(parents=True, exist_ok=True)
        _orig20 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = _tmpvault20
        os.chdir(_tmpdir20)
        _result20 = resolve_command_sidecar("_command_ohne_sidecar")
        assert_eq("test_resolve_command_sidecar_absent_is_none — None bei fehlendem Sidecar (kein Crash, AK-2/AK-3)", _result20, None)
    finally:
        os.chdir(original_cwd)
        if _orig20 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig20
        shutil.rmtree(_tmpvault20, ignore_errors=True)
        shutil.rmtree(_tmpdir20, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Test 21 (BL-372 AK-9 / T3): .vault_root absent -> env-Fallback greift (MW2, NICHT .vault_root-only)
    # ---------------------------------------------------------------------------
    print("\n[Test 21 BL-372 AK-9] test_resolve_command_sidecar_no_vaultroot_env_fallback")
    _tmpvault21 = tempfile.mkdtemp(prefix="mock_vault_t21_")
    _tmpdir21 = tempfile.mkdtemp(prefix="proj_t21_NoVaultRoot_")   # KEINE .vault_root-Datei hier
    try:
        _cmds21 = Path(_tmpvault21) / "_meta" / "commands"
        _cmds21.mkdir(parents=True, exist_ok=True)
        (_cmds21 / "_help_Meta.md").write_text("HELP-SIDECAR", encoding="utf-8")
        _orig21 = os.environ.get("CLAUDE_VAULT_ROOT")
        os.environ["CLAUDE_VAULT_ROOT"] = _tmpvault21   # env-Fallback (kein .vault_root im cwd-walk noetig)
        os.chdir(_tmpdir21)
        _result21 = resolve_command_sidecar("_help")
        _expected21 = Path(_tmpvault21) / "_meta" / "commands" / "_help_Meta.md"
        assert_not_none("test_resolve_command_sidecar_no_vaultroot_env_fallback — result not None (env-Fallback)", _result21)
        if _result21:
            assert_eq("test_resolve_command_sidecar_no_vaultroot_env_fallback — env CLAUDE_VAULT_ROOT genutzt (nicht .vault_root-only, MW2)", _result21, _expected21)
    finally:
        os.chdir(original_cwd)
        if _orig21 is None:
            os.environ.pop("CLAUDE_VAULT_ROOT", None)
        else:
            os.environ["CLAUDE_VAULT_ROOT"] = _orig21
        shutil.rmtree(_tmpvault21, ignore_errors=True)
        shutil.rmtree(_tmpdir21, ignore_errors=True)

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print(f"\n{'='*40}")
    print(f"Results: {PASS} PASS, {FAIL} FAIL")
    if FAIL == 0:
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
