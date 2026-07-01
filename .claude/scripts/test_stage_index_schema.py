"""
test_stage_index_schema.py — Tests fuer BL-392 batch_4 (AK-INDEX, PL-1 code + PL-2 Narrativ-Slot).

Der `_index`-Slice ist der Identitaets-Anker einer Stage. batch_4 formalisiert sein
Schema + den slice_map-Konsistenz-Check (PL-1) und reserviert den `maintainability`-Slot
+ Narrativ (PL-2, Format-OFFEN W-AK-MAINT). KEIN LIVE-Vault-Write — read-only/Engine +
tmp-Fixtures.

Kern-DoDs (AK-INDEX):
  - `_index`-Schema: MUSS `stufe`(int) + `name` + `maintainability`(Slot) + `slice_map`
    (Map concern -> Slice-Dateiname ueber die 8 kanonischen Slices) tragen.
    Ein `_index` OHNE slice_map ist invalid.
  - slice_map-Konsistenz-Check (Kern): `check_index_slice_map(stage_handle_or_dir)`
    prueft, dass die `slice_map` im `_index` GENAU die real im Stage-Verzeichnis
    vorhandenen Slices listet — Realitaets-Quelle ist
    `resolve_vault_stage.StageHandle.slice_paths` (batch_2). Map divergiert vom
    Verzeichnis -> inkonsistent (BLOCK), mit `missing_in_map` / `extra_in_map`.
  - maintainability-Slot vorhanden (skip/None erlaubt — Format OFFEN, W-AK-MAINT).

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_stage_index_schema.py     (repo-root)
  py -3 -m pytest test_stage_index_schema.py                     (scripts-cwd)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from stage_slice_schema import CANONICAL_SLICES  # noqa: E402  (single source der 8 Slices)
from stage_index_schema import (  # noqa: E402
    INDEX_REQUIRED_FIELDS,
    IndexSchemaResult,
    SliceMapConsistency,
    build_slice_map,
    check_index_slice_map,
    validate_index_dict,
)


# ---------------------------------------------------------------------------
# Fixtures: ein konsistenter _index + ein voller Vault-Slice-Satz
# ---------------------------------------------------------------------------

# Ein kanonischer _index mit slice_map ueber die 8 Slices (alle vorhanden).
def _full_slice_map() -> dict:
    return {name: f"{name}.md" for name in CANONICAL_SLICES}


_VALID_INDEX = {
    "stufe": 3,
    "name": "integration",
    "maintainability": None,  # Slot reserviert, Format OFFEN (W-AK-MAINT)
    "slice_map": _full_slice_map(),
}


def _write_vault_stage(vault_root: Path, n: int, name: str, slice_names) -> Path:
    """Lege `{vault_root}/Stage/stage_{n}_{name}/` mit {slice}.md-Dateien an (leeres fm)."""
    stage_dir = vault_root / "Stage" / f"stage_{n}_{name}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    for slice_name in slice_names:
        text = "---\n" + yaml.safe_dump({"k": "v"}, sort_keys=False) + "---\n\n# " + slice_name + "\n"
        (stage_dir / f"{slice_name}.md").write_text(text, encoding="utf-8")
    return stage_dir


def _write_index(stage_dir: Path, index_fm: dict) -> None:
    """Schreibe das `_index.md` mit dem gegebenen Frontmatter (ueberschreibt)."""
    text = "---\n" + yaml.safe_dump(index_fm, sort_keys=False, allow_unicode=True) + "---\n\n# _index\n"
    (stage_dir / "_index.md").write_text(text, encoding="utf-8")


@pytest.fixture
def env_guard():
    """Sichert/Restored CLAUDE_VAULT_ROOT + cwd (Tests pinnen den Vault via env)."""
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


# ===========================================================================
# 1. _index-SCHEMA: Pflichtfelder (stufe/name/maintainability/slice_map)
# ===========================================================================


def test_index_required_fields_constant() -> None:
    """Die Pflichtfelder umfassen stufe/name/maintainability/slice_map."""
    assert set(INDEX_REQUIRED_FIELDS) >= {"stufe", "name", "maintainability", "slice_map"}


def test_valid_index_passes() -> None:
    """Ein vollstaendiger _index (stufe/name/maintainability-Slot/slice_map) ist valide."""
    res = validate_index_dict(_VALID_INDEX)
    assert isinstance(res, IndexSchemaResult)
    assert res.valid, res.errors


def test_index_without_slice_map_is_invalid() -> None:
    """Ein _index OHNE slice_map ist invalid (slice_map ist Pflicht)."""
    fm = {k: v for k, v in _VALID_INDEX.items() if k != "slice_map"}
    res = validate_index_dict(fm)
    assert not res.valid
    assert any("slice_map" in e for e in res.errors)


def test_index_without_stufe_is_invalid() -> None:
    """Ein _index OHNE stufe ist invalid (Identitaets-Anker)."""
    fm = {k: v for k, v in _VALID_INDEX.items() if k != "stufe"}
    res = validate_index_dict(fm)
    assert not res.valid
    assert any("stufe" in e for e in res.errors)


def test_index_stufe_must_be_int() -> None:
    """stufe MUSS int sein (nicht '3' als String)."""
    fm = dict(_VALID_INDEX)
    fm["stufe"] = "3"
    res = validate_index_dict(fm)
    assert not res.valid
    assert any("stufe" in e for e in res.errors)


def test_index_slice_map_must_be_mapping() -> None:
    """slice_map MUSS eine Map sein (kein Liste/String)."""
    fm = dict(_VALID_INDEX)
    fm["slice_map"] = ["execute.md", "setup.md"]
    res = validate_index_dict(fm)
    assert not res.valid
    assert any("slice_map" in e for e in res.errors)


# --- maintainability-Slot: vorhanden Pflicht, aber Format OFFEN (W-AK-MAINT) ---


def test_maintainability_slot_must_be_present() -> None:
    """Der maintainability-Slot MUSS vorhanden sein (auch wenn None — Format OFFEN)."""
    fm = {k: v for k, v in _VALID_INDEX.items() if k != "maintainability"}
    res = validate_index_dict(fm)
    assert not res.valid
    assert any("maintainability" in e for e in res.errors)


def test_maintainability_none_is_ok() -> None:
    """maintainability=None (reservierter Slot, Format OFFEN) ist KONFORM — keine Format-Pflicht."""
    fm = dict(_VALID_INDEX)
    fm["maintainability"] = None
    res = validate_index_dict(fm)
    assert res.valid, res.errors


@pytest.mark.parametrize("value", [True, False, "stage_3.1", "wartbar", 5])
def test_maintainability_any_format_accepted(value) -> None:
    """maintainability-Format ist OFFEN (W-AK-MAINT): Boolean/Sub-Stage-String/Zahl alle akzeptiert.

    batch_4 erfindet das Format NICHT — der Slot toleriert jeden Wert, solange er
    PRAESENT ist. Die Praezisierung ist die offene OQ W-AK-MAINT.
    """
    fm = dict(_VALID_INDEX)
    fm["maintainability"] = value
    res = validate_index_dict(fm)
    assert res.valid, f"maintainability={value!r} sollte konform sein (Format OFFEN): {res.errors}"


# ===========================================================================
# 2. slice_map-KONSISTENZ-CHECK (der Kern) — Map <-> Verzeichnis
# ===========================================================================


def test_consistent_slice_map_passes(tmp_path: Path, env_guard) -> None:
    """slice_map listet GENAU die im Verzeichnis vorhandenen Slices -> consistent."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", CANONICAL_SLICES)
    _write_index(stage_dir, _VALID_INDEX)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    from resolve_vault_stage import resolve_stage

    handle = resolve_stage(3)
    res = check_index_slice_map(handle)
    assert isinstance(res, SliceMapConsistency)
    assert res.consistent, (res.missing_in_map, res.extra_in_map)
    assert res.missing_in_map == []
    assert res.extra_in_map == []


def test_slice_missing_in_map_is_inconsistent(tmp_path: Path, env_guard) -> None:
    """Ein Slice liegt im Verzeichnis, fehlt aber in der slice_map -> inkonsistent (BLOCK)."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", CANONICAL_SLICES)
    # slice_map LAESST 'teardown' weg, obwohl teardown.md im Verzeichnis liegt.
    partial_map = {n: f"{n}.md" for n in CANONICAL_SLICES if n != "teardown"}
    fm = dict(_VALID_INDEX)
    fm["slice_map"] = partial_map
    _write_index(stage_dir, fm)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    from resolve_vault_stage import resolve_stage

    res = check_index_slice_map(resolve_stage(3))
    assert not res.consistent
    assert "teardown" in res.missing_in_map
    assert res.extra_in_map == []


def test_map_entry_without_file_is_inconsistent(tmp_path: Path, env_guard) -> None:
    """Ein slice_map-Eintrag OHNE reale Datei im Verzeichnis -> inkonsistent (extra_in_map)."""
    vault = tmp_path / "vault"
    # Verzeichnis hat NUR 7 Slices (kein health_check.md), Map listet aber alle 8.
    present = [n for n in CANONICAL_SLICES if n != "health_check"]
    stage_dir = _write_vault_stage(vault, 3, "integration", present)
    _write_index(stage_dir, _VALID_INDEX)  # _VALID_INDEX.slice_map hat alle 8
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    from resolve_vault_stage import resolve_stage

    res = check_index_slice_map(resolve_stage(3))
    assert not res.consistent
    assert "health_check" in res.extra_in_map
    assert res.missing_in_map == []


def test_skip_marked_map_entry_without_file_is_ok(tmp_path: Path, env_guard) -> None:
    """Ein als skip markierter slice_map-Eintrag braucht KEINE Datei (skip = bewusst nicht da).

    `slice_map: {health_check: skip}` ist konsistent OHNE health_check.md im Verzeichnis —
    explizit > implizit (W-SLICE-3): die Map deklariert den Concern als bewusst weggelassen.
    """
    vault = tmp_path / "vault"
    present = [n for n in CANONICAL_SLICES if n != "health_check"]
    stage_dir = _write_vault_stage(vault, 3, "integration", present)
    fm = dict(_VALID_INDEX)
    fm["slice_map"] = dict(_full_slice_map(), health_check="skip")
    _write_index(stage_dir, fm)
    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)

    from resolve_vault_stage import resolve_stage

    res = check_index_slice_map(resolve_stage(3))
    assert res.consistent, (res.missing_in_map, res.extra_in_map)


def test_check_accepts_directory_path(tmp_path: Path, env_guard) -> None:
    """check_index_slice_map akzeptiert auch direkt ein Stage-Verzeichnis (nicht nur Handle)."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", CANONICAL_SLICES)
    _write_index(stage_dir, _VALID_INDEX)

    res = check_index_slice_map(stage_dir)
    assert res.consistent, (res.missing_in_map, res.extra_in_map)


def test_check_index_without_index_file_is_inconsistent(tmp_path: Path, env_guard) -> None:
    """Fehlt das _index.md (kein slice_map lesbar) -> inkonsistent (kein stiller Pass)."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", [n for n in CANONICAL_SLICES if n != "_index"])
    # KEIN _index.md geschrieben.

    res = check_index_slice_map(stage_dir)
    assert not res.consistent


def test_legacy_handle_consistency_is_skipped_not_crash(tmp_path: Path, env_guard) -> None:
    """Ein Legacy-Handle (in-memory, kein Verzeichnis) -> consistent=False mit Hinweis, kein Crash.

    Der Dual-Read-Legacy-Monolith hat keine echten Slice-Dateien -> der Konsistenz-Check
    ist auf in-memory nicht anwendbar; fail-safe statt Exception.
    """
    vault = tmp_path / "empty_vault"
    vault.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "proj_OmniCommand"
    (project / ".claude" / "meta" / "implementation").mkdir(parents=True, exist_ok=True)
    mono = {"stufe": 3, "name": "Integration", "testbefehl": "x", "testtyp": "integration"}
    text = "---\n" + yaml.safe_dump(mono, sort_keys=False) + "---\n\n# Stage\n"
    (project / ".claude" / "meta" / "implementation" / "stage_3.md").write_text(text, encoding="utf-8")

    os.environ["CLAUDE_VAULT_ROOT"] = str(vault)
    os.chdir(project)

    from resolve_vault_stage import resolve_stage

    handle = resolve_stage(3)
    assert handle is not None and handle.is_legacy is True
    res = check_index_slice_map(handle)  # darf nicht crashen
    assert res.consistent is False


# ===========================================================================
# 3. build_slice_map — Helfer, der die Map aus dem realen Verzeichnis erzeugt
# ===========================================================================


def test_build_slice_map_from_directory(tmp_path: Path) -> None:
    """build_slice_map erzeugt die Map aus den real vorhandenen {slice}.md-Dateien."""
    vault = tmp_path / "vault"
    stage_dir = _write_vault_stage(vault, 3, "integration", CANONICAL_SLICES)
    smap = build_slice_map(stage_dir)
    assert set(smap.keys()) == set(CANONICAL_SLICES)
    assert smap["execute"] == "execute.md"


def test_build_slice_map_marks_absent_as_skip(tmp_path: Path) -> None:
    """Ein NICHT vorhandener Slice wird in der gebauten Map als 'skip' markiert (explizit > implizit)."""
    vault = tmp_path / "vault"
    present = [n for n in CANONICAL_SLICES if n != "health_check"]
    stage_dir = _write_vault_stage(vault, 3, "integration", present)
    smap = build_slice_map(stage_dir)
    assert smap["health_check"] == "skip"
    assert smap["execute"] == "execute.md"


def test_build_slice_map_roundtrips_consistent(tmp_path: Path, env_guard) -> None:
    """Eine aus dem Verzeichnis GEBAUTE slice_map ist per Konstruktion konsistent (Round-Trip)."""
    vault = tmp_path / "vault"
    present = [n for n in CANONICAL_SLICES if n not in ("setup", "teardown")]
    stage_dir = _write_vault_stage(vault, 3, "integration", present)
    fm = dict(_VALID_INDEX)
    fm["slice_map"] = build_slice_map(stage_dir)
    _write_index(stage_dir, fm)

    res = check_index_slice_map(stage_dir)
    assert res.consistent, (res.missing_in_map, res.extra_in_map)


# ===========================================================================
# 4. Schicht-Trennung: das Schema ist projekt-agnostisch (kein DCSRE-Inhalt)
# ===========================================================================


def test_schema_is_project_agnostic() -> None:
    """Das _index-Schema kodiert NUR Feld-Namen/Format, KEINE projekt-spezifischen Werte."""
    import stage_index_schema as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    low = src.lower()
    # Keine projekt-spezifischen Inhalts-Marker (Schicht-Grenze, W-SCHEMA-2).
    for forbidden in ("dcsre", "docker-compose", "fluentdocker", "5433"):
        assert forbidden not in low, f"projekt-spezifischer Wert im Engine-Schema: {forbidden}"


def test_no_modus_fields() -> None:
    """KEINE Modus-Felder im Modul (INV-MODUS-5)."""
    import stage_index_schema as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    for forbidden in ("recommended_modus", "sdf_mode", "sdf_mode_hint", "expected_sdf_mode", "mode_recommendation"):
        assert forbidden not in src, f"verbotenes Modus-Feld: {forbidden}"


# ===========================================================================
# 5. PL-2: stage_slice_migrate-_index-Anreicherung (slice_map + maintainability-Slot)
# ===========================================================================
#
# Der Migrator (batch_3) produziert jetzt einen _index mit slice_map + maintainability-
# Slot (batch_4-Anreicherung). Diese Tests verifizieren die Naht: der migrierte _index
# validiert via stage_index_schema, und die produzierte slice_map ist nach dem (dry-run-)
# Cutover auf die Platte konsistent. KEIN LIVE-Vault-Write (tmp-Fixtures).


def _find_monolith(n: int) -> Path:
    """Finde `.claude/meta/implementation/stage_{n}.md` per cwd-Walkup (read-only)."""
    rel = Path(".claude") / "meta" / "implementation" / f"stage_{n}.md"
    for parent in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parent.parent.parent]:
        candidate = parent / rel
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"stage_{n}.md nicht gefunden (cwd={Path.cwd()})")


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_migrated_index_carries_slice_map_and_maintainability(n: int) -> None:
    """Der migrierte _index (stage_slice_migrate) traegt slice_map + maintainability-Slot."""
    from stage_slice_migrate import slice_dict_frontmatter

    text = _find_monolith(n).read_text(encoding="utf-8", errors="replace")
    fm_dict = slice_dict_frontmatter(text)
    index_fm = fm_dict["_index"]
    assert "slice_map" in index_fm, f"stage_{n}: migrierter _index ohne slice_map"
    assert "maintainability" in index_fm, f"stage_{n}: migrierter _index ohne maintainability-Slot"
    assert isinstance(index_fm["slice_map"], dict)
    # maintainability-Slot reserviert (Format OFFEN, W-AK-MAINT) -> None.
    assert index_fm["maintainability"] is None


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_migrated_index_passes_index_schema(n: int) -> None:
    """Der migrierte _index validiert via stage_index_schema.validate_index_dict (Schema-PASS)."""
    from stage_slice_migrate import slice_dict_frontmatter

    text = _find_monolith(n).read_text(encoding="utf-8", errors="replace")
    index_fm = slice_dict_frontmatter(text)["_index"]
    res = validate_index_dict(index_fm)
    assert res.valid, f"stage_{n}: migrierter _index BLOCK: {res.errors}"


def test_migrated_index_slice_map_covers_all_canonical() -> None:
    """Die migrierte slice_map deckt alle 8 kanonischen Slices ab (Datei oder skip)."""
    from stage_slice_migrate import slice_dict_frontmatter

    text = _find_monolith(3).read_text(encoding="utf-8", errors="replace")
    smap = slice_dict_frontmatter(text)["_index"]["slice_map"]
    assert set(smap.keys()) == set(CANONICAL_SLICES)
    # execute ist immer eine echte Datei (Pflicht-Slice, nie skip).
    assert smap["execute"] == "execute.md"


def test_migrated_slices_written_to_disk_are_consistent(tmp_path: Path) -> None:
    """End-to-End: migrierte Slices auf die Platte geschrieben -> slice_map konsistent.

    Spiegelt den (spaeteren, quiescenz-gated) Cutover OHNE LIVE-Vault: wir schreiben die
    8 migrierten Slice-Texte in ein tmp-Stage-Verzeichnis und pruefen, dass die im _index
    produzierte slice_map mit dem realen Verzeichnis deckungsgleich ist (consistent).
    """
    from stage_slice_migrate import split_monolith_to_slices

    text = _find_monolith(3).read_text(encoding="utf-8", errors="replace")
    out = split_monolith_to_slices(text)  # {concern: markdown_text} inkl. angereichertem _index

    stage_dir = tmp_path / "stage_3_integration"
    stage_dir.mkdir(parents=True, exist_ok=True)
    for name, slice_text in out.items():
        (stage_dir / f"{name}.md").write_text(slice_text, encoding="utf-8")

    res = check_index_slice_map(stage_dir)
    assert res.consistent, (res.missing_in_map, res.extra_in_map, res.note)


def test_migrated_index_has_no_modus_fields() -> None:
    """Der angereicherte _index traegt KEINE Modus-Felder (INV-MODUS-5)."""
    from stage_slice_migrate import split_monolith_to_slices

    text = _find_monolith(3).read_text(encoding="utf-8", errors="replace")
    index_text = split_monolith_to_slices(text)["_index"]
    for forbidden in ("recommended_modus", "sdf_mode", "sdf_mode_hint", "expected_sdf_mode", "mode_recommendation"):
        assert forbidden not in index_text, f"verbotenes Modus-Feld im migrierten _index: {forbidden}"
