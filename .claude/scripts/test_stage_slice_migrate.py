"""
test_stage_slice_migrate.py — Tests fuer BL-392 batch_3 (AK-MIGRATION determ-Anteil, PL-1/PL-2).

`stage_slice_migrate.split_monolith_to_slices(monolith_text) -> {concern: slice_text}`
zerlegt einen monolithischen `stage_N.md` (1 Datei, alle YAML-Bloecke) in die 8
atomaren Slices (`stage_slice_schema.CANONICAL_SLICES`) — read-only/dry-run, KEIN
Vault-Write (der Cutover ist quiescenz-gated und bewusst NICHT Teil dieses Builds).

Kern-DoDs (AK-MIGRATION):
  - VERLUSTFREI (Round-Trip, der Kern wie die Truth-Migration): die Vereinigung der
    8 Slice-Frontmatter reproduziert JEDES Monolith-Frontmatter-Feld in genau einem
    Slice — kein Concern verloren (Monolith-Felder == Vereinigung der Slice-Felder).
  - SCHEMA-PASS: der Output validiert via stage_slice_schema.validate_slice_dict.
  - grep-NEGATIV: der migrierte stage_3-Output traegt KEINE docker-compose-Fiktion
    (kein "docker-compose", kein "docker-compose.integration.yml") — sondern den
    ECHTEN FluentDocker/in-process-Mechanismus (Korrektur-Sicherung).
  - skip-SENTINEL: stage_1 (kein Infra) -> setup/teardown/health_check tragen
    EXPLIZIT `skip`/`none` (nicht leer, W-SLICE-3 explizit > implizit).

Input-Fixtures = die ECHTEN Monolithe `.claude/meta/implementation/stage_1.md` +
`stage_3.md` (read-only).

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_stage_slice_migrate.py     (repo-root)
  py -3 -m pytest test_stage_slice_migrate.py                     (scripts-cwd)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from stage_slice_migrate import (  # noqa: E402
    CONCERN_FIELD_MAP,
    cutover_to_vault,
    monolith_fields,
    slice_dict_frontmatter,
    split_monolith_to_slices,
)
from stage_slice_schema import CANONICAL_SLICES, validate_slice_dict  # noqa: E402

# ---------------------------------------------------------------------------
# Echte Monolith-Fixtures (read-only) — vom cwd-unabhaengig per Walkup gefunden
# ---------------------------------------------------------------------------


def _find_monolith(n: int) -> Path:
    """Finde `.claude/meta/implementation/stage_{n}.md` per cwd-Walkup (read-only)."""
    rel = Path(".claude") / "meta" / "implementation" / f"stage_{n}.md"
    for parent in [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parent.parent.parent]:
        candidate = parent / rel
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"stage_{n}.md nicht gefunden (cwd={Path.cwd()})")


@pytest.fixture(scope="module")
def stage1_text() -> str:
    return _find_monolith(1).read_text(encoding="utf-8", errors="replace")


@pytest.fixture(scope="module")
def stage3_text() -> str:
    return _find_monolith(3).read_text(encoding="utf-8", errors="replace")


def _parse_fm(text: str) -> dict:
    """Lies das YAML-Frontmatter (zwischen den ersten zwei '---') aus text."""
    lines = text.splitlines()
    assert lines and lines[0].strip() == "---"
    fm_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    data = yaml.safe_load("\n".join(fm_lines))
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Struktur des Outputs
# ---------------------------------------------------------------------------


def test_output_has_all_eight_slices(stage3_text: str) -> None:
    """Der Output traegt genau die 8 kanonischen Slices (Schluessel)."""
    out = split_monolith_to_slices(stage3_text)
    assert set(out.keys()) == set(CANONICAL_SLICES)


def test_output_slices_are_markdown_with_frontmatter(stage3_text: str) -> None:
    """Jeder Slice-Output ist ein Markdown-String mit '---'-Frontmatter-Block."""
    out = split_monolith_to_slices(stage3_text)
    for name, slice_text in out.items():
        assert isinstance(slice_text, str), name
        assert slice_text.startswith("---"), f"{name} hat keinen Frontmatter-Block"
        # genau zwei '---'-Delimiter (Frontmatter-Oeffnung + -Schluss).
        assert slice_text.count("\n---") >= 1 or slice_text.split("\n").count("---") >= 2


def test_concern_field_map_covers_all_canonical() -> None:
    """CONCERN_FIELD_MAP ordnet jedem kanonischen Slice ein Feld-Set zu."""
    for name in CANONICAL_SLICES:
        assert name in CONCERN_FIELD_MAP


# ---------------------------------------------------------------------------
# KERN-DoD 1: VERLUSTFREI (Round-Trip) — jedes Monolith-Feld in genau einem Slice
# ---------------------------------------------------------------------------


# Geschachtelte Lifecycle-Concerns: im Monolith ein Key (value=dict), im Slice
# AUSGEPACKT (Slice-fm == das innere dict). Round-Trip muss sie re-wrappen.
_NESTED_CONCERNS = ("setup", "teardown", "health_check")

# Migrations-additive Felder (kein Monolith-Datum, aber legitim — s. Rationale unten).
# slice_map + maintainability sind die _index-Anreicherung aus batch_4 (AK-INDEX):
# der migrierte _index traegt zusaetzlich die slice_map (concern -> Datei|skip) + den
# reservierten maintainability-Slot — additive Schema-Felder, KEIN Monolith-Concern-Verlust.
_ADDITIVE_FIELDS = {"maintainability", "slice_map", "skip", "none", "infrastruktur", "qg"}


# Die Lifecycle-Concerns + die concurrency_rationale (Prosa) tragen in stage_3 die
# docker-compose-Fiktion -> sie sind die bewusst korrigierten PL-2-Felder.
_STAGE3_CORRECTED_FIELDS = ("setup", "teardown", "health_check", "concurrency_rationale")


def _reconstruct_from_slices(out: dict) -> dict:
    """Inverse der Migration: baue aus den 8 Slice-fm das Monolith-fm zurueck.

    Scalar-Slices (_index/execute/resources/concurrency_class/exit_criteria) liefern
    ihre Top-Level-Felder direkt; die geschachtelten Lifecycle-Slices werden unter
    ihren Concern-Key RE-gewrappt (Spiegel: setup-Slice-fm -> mono['setup']). Das skip-
    Sentinel wird beim Re-Wrap der Lifecycle-Concerns entfernt (es war nie im Monolith);
    sonst NICHTS gefiltert (infrastruktur/qg bleiben drin und werden ueber die Key-Set-
    Differenz als additiv toleriert).
    """
    recon: dict = {}
    for name in CANONICAL_SLICES:
        fm = _parse_fm(out[name])
        if name in _NESTED_CONCERNS:
            inner = {k: v for k, v in fm.items() if k not in ("skip", "none")}
            # health_check: null im Monolith -> leerer Slice (nur skip) -> kein Re-Wrap.
            if inner:
                recon[name] = inner
        else:
            for key, value in fm.items():
                recon[key] = value
    return recon


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_roundtrip_lossless_every_concern_preserved(n: int) -> None:
    """Verlustfrei: jeder Monolith-Concern ueberlebt die Migration (re-gewrappt == Monolith).

    Fuer stage_3 sind die docker-compose-Fiktiv-Felder (setup/teardown/health_check +
    concurrency_rationale-Prosa) BEWUSST inhaltlich korrigiert (PL-2) -> ihre WERTE
    duerfen abweichen; ihre PRAESENZ (der Concern-Key) muss erhalten bleiben. Alle
    anderen Felder: 1:1 verlustfrei. Migrations-additive Felder (skip/maintainability/
    infrastruktur/qg) sind erlaubt, soweit nicht im Monolith.
    """
    text = _find_monolith(n).read_text(encoding="utf-8", errors="replace")
    mono = monolith_fields(text)
    out = split_monolith_to_slices(text)
    recon = _reconstruct_from_slices(out)

    mono_keys = set(mono.keys())
    recon_keys = set(recon.keys())

    # skip-REPRAESENTIERTE Lifecycle-Concerns: der Monolith liess sie implizit-leer
    # (health_check: null / setup: {commands: []}); die Migration normalisiert sie zum
    # EXPLIZITEN skip-Sentinel (W-SLICE-3 explizit > implizit). Das ist KEIN Verlust —
    # der Concern ist als skip REPRAESENTIERT. Beim Round-Trip gelten sie als vorhanden
    # (nicht missing) + Wert-exempt (der Wert ist bewusst zum skip normalisiert).
    skip_represented = {
        concern
        for concern in _NESTED_CONCERNS
        if _parse_fm(out[concern]).get("skip") in (True, "skip", "true")
    }

    # Kein Concern verloren: jeder Monolith-Key ist re-konstruierbar ODER skip-repraesentiert.
    missing = mono_keys - recon_keys - skip_represented
    assert not missing, f"stage_{n}: Concerns verloren bei der Migration: {sorted(missing)}"

    # Keine Concerns erfunden — AUSSER den legitim migrations-additiven Schema-Feldern
    # (infrastruktur=none fuer Nicht-Infra-Stages, qg aus exit_criteria-Liste, der
    # reservierte maintainability-Slot, die slice_map aus der batch_4-_index-Anreicherung).
    # Diese sind kein Monolith-Datenverlust (additive Schema-Felder, AK-INDEX).
    allowed_new = {"maintainability", "slice_map", "infrastruktur", "qg"}
    invented = recon_keys - mono_keys - allowed_new
    assert not invented, f"stage_{n}: Concerns erfunden (nicht im Monolith): {sorted(invented)}"

    # Werte 1:1 — AUSSER (a) den fuer stage_3 bewusst korrigierten Fiktiv-Feldern und
    # (b) den skip-repraesentierten (implizit-leer -> explizites skip, W-SLICE-3).
    is_corrected_integration = str(mono.get("testtyp", "")).strip().lower() == "integration"
    corrected = set(_STAGE3_CORRECTED_FIELDS) if is_corrected_integration else set()
    value_exempt = corrected | skip_represented
    for key, value in mono.items():
        if key in value_exempt:
            continue
        assert recon.get(key) == value, (
            f"stage_{n}: Wert von '{key}' veraendert (stiller Edit): {value!r} -> {recon.get(key)!r}"
        )


def test_stage3_corrected_concerns_still_present(stage3_text: str) -> None:
    """stage_3: die korrigierten Lifecycle-Concerns sind PRAESENT (nicht verloren), nur inhaltlich neu."""
    out = split_monolith_to_slices(stage3_text)
    for concern in _NESTED_CONCERNS:
        fm = _parse_fm(out[concern])
        assert fm, f"stage_3 {concern} ist nach Korrektur LEER (Concern verloren)"


def test_non_integration_values_fully_preserved(n: int = 1) -> None:
    """Nicht-Integration-Stage (stage_1): ALLE Werte 1:1 verlustfrei (keine Korrektur)."""
    text = _find_monolith(1).read_text(encoding="utf-8", errors="replace")
    mono = monolith_fields(text)
    out = split_monolith_to_slices(text)
    recon = _reconstruct_from_slices(out)
    for key, value in mono.items():
        assert recon.get(key) == value, f"stage_1: Wert von '{key}' veraendert: {value!r} -> {recon.get(key)!r}"


def test_slice_dict_frontmatter_helper_matches(stage3_text: str) -> None:
    """slice_dict_frontmatter liefert die Frontmatter-dicts passend zu split_monolith_to_slices."""
    fm_dict = slice_dict_frontmatter(stage3_text)
    out = split_monolith_to_slices(stage3_text)
    assert set(fm_dict.keys()) == set(out.keys())
    for name in CANONICAL_SLICES:
        assert _parse_fm(out[name]) == fm_dict[name]


# ---------------------------------------------------------------------------
# KERN-DoD 2: SCHEMA-PASS — der Output validiert via stage_slice_schema
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_output_passes_slice_schema(n: int) -> None:
    """Der migrierte 8-Slice-Satz JEDER Stage validiert via stage_slice_schema.validate_slice_dict."""
    text = _find_monolith(n).read_text(encoding="utf-8", errors="replace")
    fm_dict = slice_dict_frontmatter(text)
    res = validate_slice_dict(fm_dict)
    assert res.valid, (
        f"stage_{n}: Slice-Schema BLOCK: missing={res.missing_slices}, "
        f"errors={[(e.slice, e.message) for e in res.errors]}"
    )


# ---------------------------------------------------------------------------
# KERN-DoD 3: grep-NEGATIV — stage_3-Output traegt KEINE docker-compose-Fiktion
# ---------------------------------------------------------------------------


def test_stage3_output_has_no_docker_compose_fiction(stage3_text: str) -> None:
    """Der migrierte stage_3-Output enthaelt KEINEN docker-compose-String (Fiktiv-Defekt behoben)."""
    out = split_monolith_to_slices(stage3_text)
    full = "\n".join(out.values()).lower()
    assert "docker-compose" not in full, "stage_3-Output traegt noch die docker-compose-Fiktion"
    assert "docker-compose.integration.yml" not in full


def test_stage3_output_carries_real_fluentdocker_mechanism(stage3_text: str) -> None:
    """Der migrierte stage_3-Output traegt den ECHTEN Mechanismus (FluentDocker/in-process)."""
    out = split_monolith_to_slices(stage3_text)
    full = "\n".join(out.values())
    # Die echten Mechanismus-Anker (Korrektur-Sicherung, BL-392-Body).
    for anchor in (
        "FluentDocker",
        "ContainerIntegrationTestBase",
        "DockerSemaphore",
        "RunInitialMigrations",
        "WebApplicationTestFactory",
    ):
        assert anchor in full, f"echter Mechanismus-Anker fehlt im stage_3-Output: {anchor}"
    # Merksatz (Code -> recompile. Image -> rmi + rebuild.)
    assert "rmi" in full and "recompile" in full


def test_stage3_health_gate_is_docker_daemon_not_port(stage3_text: str) -> None:
    """Das stage_3-Health-Gate ist 'Docker-Daemon erreichbar' (docker version), KEIN fester Port 5433."""
    out = split_monolith_to_slices(stage3_text)
    health = out["health_check"].lower()
    assert "docker version" in health or "docker-daemon" in health or "docker daemon" in health
    assert "5433" not in out["health_check"], "fiktiver fester Port 5433 noch im Health-Gate"


# ---------------------------------------------------------------------------
# KERN-DoD 4: skip-SENTINEL — stage_1 (kein Infra) traegt setup/teardown/health_check=skip
# ---------------------------------------------------------------------------


def test_stage1_non_infra_slices_carry_skip(stage1_text: str) -> None:
    """stage_1 (kein Infra) -> setup/teardown/health_check tragen EXPLIZIT skip/none (nicht leer)."""
    fm_dict = slice_dict_frontmatter(stage1_text)
    for concern in ("setup", "teardown", "health_check"):
        fm = fm_dict[concern]
        assert isinstance(fm, dict) and fm, f"stage_1 {concern} ist leer (W-SLICE-3 verletzt)"
        is_skip = (
            fm.get("skip") in (True, "skip", "true")
            or fm.get("none") in (True, "none", "true")
            or str(fm.get(_concern_lead(concern))).strip().lower() in ("skip", "none")
        )
        assert is_skip, f"stage_1 {concern} traegt kein explizites skip/none-Sentinel: {fm}"


def _concern_lead(concern: str) -> str:
    return {"setup": "commands", "teardown": "commands", "health_check": "command"}[concern]


def test_stage1_skip_output_passes_schema(stage1_text: str) -> None:
    """Der stage_1-skip-Output validiert (skip ist KONFORM, nicht BLOCK)."""
    fm_dict = slice_dict_frontmatter(stage1_text)
    res = validate_slice_dict(fm_dict)
    assert res.valid, f"stage_1 skip-Output BLOCK: {[(e.slice, e.message) for e in res.errors]}"


# ---------------------------------------------------------------------------
# QUIESCENZ / DEFERRED CUTOVER — cutover_to_vault ist KEIN Vault-Write in diesem Build
# ---------------------------------------------------------------------------


def test_cutover_is_dry_run_no_op(tmp_path: Path, stage3_text: str) -> None:
    """cutover_to_vault ist bewusst ein dry-run/no-op-Stub: schreibt NICHTS, liefert die Zielpfade.

    Der eigentliche Write in den LIVE-DCS-Vault ist der quiescenz-gated Owner-Schritt
    (wie PHASE-B) und NICHT Teil dieses Builds.
    """
    out = split_monolith_to_slices(stage3_text)
    target = tmp_path / "stage_3_integration"
    planned = cutover_to_vault(out, target, dry_run=True)
    # dry_run schreibt NICHTS auf die Platte.
    assert not target.exists(), "cutover_to_vault(dry_run=True) hat in einen Vault geschrieben (verboten)"
    # liefert aber die geplanten Zielpfade (Transparenz).
    assert set(planned.keys()) == set(CANONICAL_SLICES)
    for name, path in planned.items():
        assert path.name == f"{name}.md"


def test_cutover_default_is_dry_run(stage3_text: str, tmp_path: Path) -> None:
    """Default ist dry_run=True (sicher): ohne explizites dry_run=False wird NICHT geschrieben."""
    out = split_monolith_to_slices(stage3_text)
    target = tmp_path / "stage_3_integration"
    cutover_to_vault(out, target)  # kein dry_run-Arg -> default dry-run
    assert not target.exists()


# ---------------------------------------------------------------------------
# Output-Hygiene: BOM-frei, LF, keine Modus-Felder
# ---------------------------------------------------------------------------


def test_output_is_bom_free_and_lf(stage3_text: str) -> None:
    """Slice-Output ist BOM-frei UTF-8 mit LF (keine CRLF, kein BOM)."""
    out = split_monolith_to_slices(stage3_text)
    for name, slice_text in out.items():
        assert not slice_text.startswith("﻿"), f"{name} hat ein BOM"
        assert "\r" not in slice_text, f"{name} hat CRLF/CR"


def test_output_has_no_modus_fields(stage3_text: str) -> None:
    """KEINE Modus-Felder im Output (INV-MODUS-5: kein recommended_modus/sdf_mode/...)."""
    out = split_monolith_to_slices(stage3_text)
    full = "\n".join(out.values())
    for forbidden in ("recommended_modus", "sdf_mode", "sdf_mode_hint", "expected_sdf_mode", "mode_recommendation"):
        assert forbidden not in full, f"verbotenes Modus-Feld im Output: {forbidden}"


# ===========================================================================
# BL-419 batch_1 — cutover_to_vault(dry_run=False) LIVE-Write-Pfad (5 coverable AKs)
#
# Quiescenz-gated Owner-Cutover: schreibt die 8 CANONICAL_SLICES in
# {VAULT}/Stage/stage_N_<name>/ UNTER dem Factory-Global-Lock (D-W5), VOR jeglichem
# Write erworben + im finally freigegeben. RED zuerst (RED!=GREEN, Spec BL-419_Spec.md):
# der heutige cutover_to_vault(dry_run=False) ist ein NotImplementedError-no-op-Stub.
# ===========================================================================

import importlib  # noqa: E402

import factory_lock  # noqa: E402  — D-W5: Factory-Global-Lock-Fassade (Spec AK-QUIESCENZ)
import resolve_vault_stage as rvs  # noqa: E402  — AK-ROUNDTRIP (Vault-View nach Write)


# Die canonical (N, name)-Eingabe der echten stage_3 (Integration) — fuer dirname-Ableitung.
def _stage_n_name(text: str) -> tuple[int, str]:
    fm = monolith_fields(text)
    return int(fm.get("stufe")), str(fm.get("name"))


class _LockSpy:
    """Mockt factory_lock.acquire/release + zaehlt Slice-Writes zwischendurch.

    acquire_calls/release_calls protokollieren worker_id; write_count_at_acquire
    haelt fest, wie viele {name}.md schon existierten als acquire gerufen wurde
    (muss 0 sein — acquire VOR Write, DoD-1a).
    """

    def __init__(self, target_dir: Path, acquire_returns: bool = True) -> None:
        self.target_dir = target_dir
        self.acquire_returns = acquire_returns
        self.acquire_calls: list[dict] = []
        self.release_calls: list[str] = []
        self.write_count_at_acquire: int | None = None
        self.held = False

    def _existing_md_count(self) -> int:
        if not self.target_dir.exists():
            return 0
        return len(list(self.target_dir.glob("*.md")))

    def acquire(self, *args, **kwargs):  # noqa: ANN002
        self.write_count_at_acquire = self._existing_md_count()
        self.acquire_calls.append(dict(kwargs))
        if self.acquire_returns:
            self.held = True
        return self.acquire_returns

    def release(self, worker_id, *args, **kwargs):  # noqa: ANN002
        self.release_calls.append(worker_id)
        self.held = False
        return True


@pytest.fixture
def lock_spy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Patcht factory_lock.acquire/release im echten Modul (Impl importiert factory_lock)."""
    target = tmp_path / "stage_3_integration"
    spy = _LockSpy(target)
    monkeypatch.setattr(factory_lock, "acquire", spy.acquire, raising=False)
    monkeypatch.setattr(factory_lock, "release", spy.release, raising=False)
    return spy


# ---------------------------------------------------------------------------
# AK-QUIESCENZ (DoD-1) — Lock VOR Write, release im finally, Single-Writer
# ---------------------------------------------------------------------------


def test_cutover_quiescenz_acquire_before_any_write(lock_spy: _LockSpy, stage3_text: str) -> None:
    """DoD-1a: acquire erfolgt STRUKTURELL vor dem ersten {name}.md-Write (write_count==0 @ acquire)."""
    out = split_monolith_to_slices(stage3_text)
    cutover_to_vault(out, lock_spy.target_dir, dry_run=False)
    assert lock_spy.acquire_calls, "acquire wurde nie gerufen (kein Quiescenz-Lock)"
    assert lock_spy.write_count_at_acquire == 0, (
        f"acquire erfolgte NACH einem Write (count={lock_spy.write_count_at_acquire}) — "
        "Lock muss VOR jeglichem Slice-Write erworben werden (DoD-1a)"
    )


def test_cutover_quiescenz_release_in_finally_on_success(lock_spy: _LockSpy, stage3_text: str) -> None:
    """DoD-1b (Erfolgsfall): nach erfolgreichem Cutover ist der Lock freigegeben (release gerufen)."""
    out = split_monolith_to_slices(stage3_text)
    cutover_to_vault(out, lock_spy.target_dir, dry_run=False)
    assert lock_spy.release_calls, "release wurde nicht gerufen (Lock nicht freigegeben)"
    assert not lock_spy.held, "Lock ist nach dem Aufruf noch gehalten"


def test_cutover_quiescenz_release_in_finally_on_exception(
    lock_spy: _LockSpy, stage3_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD-1b (Exception-Fall): wirft ein Slice-Write, wird der Lock TROTZDEM freigegeben (finally)."""
    out = split_monolith_to_slices(stage3_text)

    real_write_text = Path.write_text

    def _boom(self, *args, **kwargs):  # noqa: ANN001
        raise OSError("simulierter Write-Fehler waehrend des Cutovers")

    monkeypatch.setattr(Path, "write_text", _boom, raising=True)
    with pytest.raises(OSError):
        cutover_to_vault(out, lock_spy.target_dir, dry_run=False)
    # write_text wieder herstellen ist nicht noetig (monkeypatch undo), aber der
    # release MUSS im finally gelaufen sein:
    assert lock_spy.release_calls, "release fehlt im Exception-Fall (kein finally-release)"
    assert not lock_spy.held, "Lock blieb nach Exception gehalten (finally verletzt)"
    _ = real_write_text  # Referenz halten (lint)


def test_cutover_quiescenz_acquire_fail_no_write(
    tmp_path: Path, stage3_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD-1c: scheitert acquire (False/timeout) -> KEIN Slice-Write + Scheitern signalisiert."""
    target = tmp_path / "stage_3_integration"
    spy = _LockSpy(target, acquire_returns=False)
    monkeypatch.setattr(factory_lock, "acquire", spy.acquire, raising=False)
    monkeypatch.setattr(factory_lock, "release", spy.release, raising=False)
    out = split_monolith_to_slices(stage3_text)
    with pytest.raises(Exception) as exc_info:  # noqa: B017 — Vertrag: Scheitern signalisiert
        cutover_to_vault(out, target, dry_run=False)
    # Das Scheitern muss aus dem ACQUIRE-Fehlschlag kommen, NICHT aus dem alten
    # NotImplementedError-no-op-Stub (sonst ist der Test falsch-gruen gegen den Stub).
    assert not isinstance(exc_info.value, NotImplementedError), (
        "Scheitern kam aus dem no-op-Stub (NotImplementedError), nicht aus acquire-Fehlschlag — "
        "der quiescenz-gated Write-Pfad existiert noch nicht (RED)"
    )
    # acquire wurde versucht (Lock-Pfad lief), Write aber unterlassen (Lock nicht erworben).
    assert spy.acquire_calls, "acquire wurde gar nicht versucht (kein Lock-Pfad)"
    md_files = list(target.glob("*.md")) if target.exists() else []
    assert not md_files, f"trotz fehlgeschlagenem acquire wurden Dateien geschrieben: {md_files}"


def test_cutover_quiescenz_release_owner_gated(lock_spy: _LockSpy, stage3_text: str) -> None:
    """DoD-1d: release ist owner-gated — derselbe worker_id wie bei acquire (kein Fremd-Release)."""
    out = split_monolith_to_slices(stage3_text)
    cutover_to_vault(out, lock_spy.target_dir, dry_run=False)
    assert lock_spy.acquire_calls and lock_spy.release_calls
    acquire_wid = lock_spy.acquire_calls[0].get("worker_id")
    assert acquire_wid is not None, "acquire ohne worker_id (owner-gating unmoeglich)"
    assert lock_spy.release_calls[0] == acquire_wid, (
        f"release worker_id ({lock_spy.release_calls[0]!r}) != acquire worker_id "
        f"({acquire_wid!r}) — release nicht owner-gated (DoD-1d)"
    )


# ---------------------------------------------------------------------------
# AK-WRITE (DoD-2) — 8 Slices als {name}.md, utf-8/LF/BOM-frei, SSoT-Root, genau-1-Dir
# ---------------------------------------------------------------------------


def test_cutover_write_eight_files_census(lock_spy: _LockSpy, stage3_text: str) -> None:
    """DoD-2a: nach dem Aufruf existieren GENAU 8 {name}.md, Namen == CANONICAL_SLICES."""
    out = split_monolith_to_slices(stage3_text)
    cutover_to_vault(out, lock_spy.target_dir, dry_run=False)
    assert lock_spy.target_dir.exists(), "Ziel-Verzeichnis wurde nicht angelegt (mkdir fehlt)"
    written = {p.stem for p in lock_spy.target_dir.glob("*.md")}
    assert written == set(CANONICAL_SLICES), (
        f"geschriebener Datei-Satz {sorted(written)} != CANONICAL_SLICES {sorted(CANONICAL_SLICES)}"
    )


def test_cutover_write_byte_identical_no_bom_no_crlf(lock_spy: _LockSpy, stage3_text: str) -> None:
    """DoD-2b: jede Datei ist byte-identisch zum Input-Text, ohne BOM, ohne CRLF."""
    out = split_monolith_to_slices(stage3_text)
    cutover_to_vault(out, lock_spy.target_dir, dry_run=False)
    for name in CANONICAL_SLICES:
        raw = (lock_spy.target_dir / f"{name}.md").read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{name}.md traegt ein UTF-8-BOM"
        assert b"\r\n" not in raw, f"{name}.md traegt CRLF"
        assert raw == out[name].encode("utf-8"), f"{name}.md nicht byte-identisch zum Input-Text"


def test_cutover_write_return_map_equals_dry_run(lock_spy: _LockSpy, stage3_text: str) -> None:
    """DoD-2e: Rueckgabe-Map (dry_run=False) == dry_run=True-Plan-Map (Planung==Realitaet)."""
    out = split_monolith_to_slices(stage3_text)
    planned = cutover_to_vault(out, lock_spy.target_dir, dry_run=True)
    written = cutover_to_vault(out, lock_spy.target_dir, dry_run=False)
    assert written == planned, "dry_run=False-Map weicht von dry_run=True-Plan-Map ab (Inkonsistenz)"
    # und die zurueckgegebenen Pfade existieren tatsaechlich (geschrieben).
    for name, path in written.items():
        assert path.exists(), f"zurueckgegebener Pfad {path} (Slice {name}) wurde nicht geschrieben"


def test_cutover_write_root_via_ssot_env(
    tmp_path: Path, stage3_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD-2d: ohne target_dir-Override landet der Write unter {CLAUDE_VAULT_ROOT}/Stage/stage_N_<name>/."""
    vault = tmp_path / "vault"
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    n, name = _stage_n_name(stage3_text)
    out = split_monolith_to_slices(stage3_text)
    written = cutover_to_vault(out, target_dir=None, dry_run=False)
    expected_dir = vault / "Stage" / f"stage_{n}_{name}"
    assert expected_dir.is_dir(), (
        f"SSoT-Root nicht beachtet: {expected_dir} existiert nicht. "
        f"geschrieben statt: {[str(p) for p in written.values()][:2]}"
    )
    for name_slice in CANONICAL_SLICES:
        assert (expected_dir / f"{name_slice}.md").exists()


def test_cutover_write_exactly_one_stage_dir_idempotent(
    tmp_path: Path, stage3_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD-2c: genau-1-Verzeichnis pro Nummer; Re-Run schreibt in dasselbe Dir (kein zweites Postfix)."""
    vault = tmp_path / "vault"
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    n, _ = _stage_n_name(stage3_text)
    out = split_monolith_to_slices(stage3_text)
    cutover_to_vault(out, target_dir=None, dry_run=False)
    cutover_to_vault(out, target_dir=None, dry_run=False)  # Re-Run (Idempotenz)
    stage_root = vault / "Stage"
    matches = sorted(d for d in stage_root.glob(f"stage_{n}_*") if d.is_dir())
    assert len(matches) == 1, f"erwartet genau 1 stage_{n}_*-Verzeichnis, gefunden: {[m.name for m in matches]}"
    # _glob_stage_dir (resolve_vault_stage W8) wirft NICHT + findet genau 1.
    assert rvs._glob_stage_dir(vault, n) == matches[0]


# ---------------------------------------------------------------------------
# AK-DIRNAME (DoD-3) — deterministischer stage_{N}_<name>, target_dir-Override
# ---------------------------------------------------------------------------


def test_cutover_dirname_deterministic(
    tmp_path: Path, stage3_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD-3a: zwei Aufrufe mit gleichem (N, name) liefern denselben target-Pfad."""
    vault = tmp_path / "vault"
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    out = split_monolith_to_slices(stage3_text)
    first = cutover_to_vault(out, target_dir=None, dry_run=True)
    second = cutover_to_vault(out, target_dir=None, dry_run=True)
    assert first == second, "abgeleiteter Pfad nicht deterministisch fuer gleiches (N, name)"


def test_cutover_dirname_format_matches_ssot(
    tmp_path: Path, stage3_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD-3b: abgeleiteter Pfad == {resolve_vault_root()}/Stage/stage_{N}_<name>/{slice}.md."""
    vault = tmp_path / "vault"
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    n, name = _stage_n_name(stage3_text)
    out = split_monolith_to_slices(stage3_text)
    planned = cutover_to_vault(out, target_dir=None, dry_run=True)
    expected_dir = vault / "Stage" / f"stage_{n}_{name}"
    for slice_name in CANONICAL_SLICES:
        assert planned[slice_name] == expected_dir / f"{slice_name}.md", (
            f"{slice_name}: {planned[slice_name]} != {expected_dir / f'{slice_name}.md'}"
        )


def test_cutover_dirname_target_dir_override_wins(lock_spy: _LockSpy, stage3_text: str) -> None:
    """DoD-3c: explizites target_dir ueberschreibt die N+name-Ableitung (tmp-Steuerbarkeit)."""
    out = split_monolith_to_slices(stage3_text)
    planned = cutover_to_vault(out, lock_spy.target_dir, dry_run=True)
    for name in CANONICAL_SLICES:
        assert planned[name] == lock_spy.target_dir / f"{name}.md", (
            f"target_dir-Override nicht beachtet fuer {name}: {planned[name]}"
        )


# ---------------------------------------------------------------------------
# AK-ROUNDTRIP (DoD-4) — nach Write: resolve_stage(N) is_legacy=False, verlustfrei
# ---------------------------------------------------------------------------


def test_cutover_roundtrip_resolve_stage_not_legacy(
    tmp_path: Path, stage3_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD-4a: nach dem Write liefert resolve_stage(N) einen Handle mit is_legacy == False."""
    vault = tmp_path / "vault"
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    n, _ = _stage_n_name(stage3_text)
    out = split_monolith_to_slices(stage3_text)
    cutover_to_vault(out, target_dir=None, dry_run=False)
    handle = rvs.resolve_stage(n, vault_root=vault, legacy_meta_dir=tmp_path / "no_legacy")
    assert handle is not None, "resolve_stage findet die frisch geschriebene Vault-Stage nicht"
    assert handle.is_legacy is False, "Handle ist is_legacy=True trotz vorhandener Vault-Slice-Dir"


def test_cutover_roundtrip_census_lossless(
    tmp_path: Path, stage3_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DoD-4b/c: Vereinigung der slice_view-Felder (von Platte) reproduziert die Monolith-Felder.

    stage_3 ist die korrigierte Integration-Stage -> die docker-compose-Fiktiv-Concerns
    (setup/teardown/health_check + concurrency_rationale) sind bewusst inhaltlich neu
    (PRAESENZ bleibt). Alle anderen Felder: Wert 1:1 verlustfrei gegen monolith_fields.
    """
    vault = tmp_path / "vault"
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    n, _ = _stage_n_name(stage3_text)
    out = split_monolith_to_slices(stage3_text)
    cutover_to_vault(out, target_dir=None, dry_run=False)
    handle = rvs.resolve_stage(n, vault_root=vault, legacy_meta_dir=tmp_path / "no_legacy")
    assert handle is not None and handle.is_legacy is False

    mono = monolith_fields(stage3_text)
    value_exempt = set(_STAGE3_CORRECTED_FIELDS)

    # Census: jeder Monolith-Concern ist in irgendeinem Slice-View praesent (kein Verlust).
    for key, value in mono.items():
        found = False
        matched_value = None
        for slice_name in CANONICAL_SLICES:
            view = handle.slice_view(slice_name) or {}
            if slice_name in _NESTED_CONCERNS and key == slice_name:
                # nested concern wird als ausgepackter Slice gefuehrt (Praesenz via Slice-Inhalt).
                found = bool(view)
                matched_value = view
                break
            if key in view:
                found = True
                matched_value = view[key]
                break
        assert found, f"Concern '{key}' nach Roundtrip aus keinem Vault-Slice-View lesbar (Verlust)"
        if key not in value_exempt and key not in _NESTED_CONCERNS:
            assert matched_value == value, (
                f"Wert von '{key}' nach Roundtrip veraendert: {value!r} -> {matched_value!r}"
            )


def test_cutover_roundtrip_field_distribution_matches_legacy_view() -> None:
    """DoD-4d: _legacy_slice_view-Verteilung (resolve_vault_stage) ist Teilmenge von CONCERN_FIELD_MAP.

    Migrator (CONCERN_FIELD_MAP) und Resolver-Legacy-View (_LEGACY_SCALAR_FIELDS) muessen
    deckungsgleich bleiben — jedes Legacy-View-Skalar-Feld faellt im Migrator in DENSELBEN
    Slice (sonst laufen Write-Verteilung und Read-View auseinander -> Roundtrip-Bruch).
    """
    for slice_name, fields in rvs._LEGACY_SCALAR_FIELDS.items():
        mig_fields = set(CONCERN_FIELD_MAP.get(slice_name, ()))
        for f in fields:
            assert f in mig_fields, (
                f"Feld '{f}' liegt im Legacy-View unter '{slice_name}', aber NICHT in "
                f"CONCERN_FIELD_MAP['{slice_name}'] — Write/Read-Verteilung divergiert (DoD-4d)"
            )


# ---------------------------------------------------------------------------
# AK-NOOP-REMOVED (DoD-5) — kein NotImplementedError mehr; dry_run=True unveraendert
# ---------------------------------------------------------------------------


def test_cutover_noop_removed_no_not_implemented(lock_spy: _LockSpy, stage3_text: str) -> None:
    """DoD-5a: cutover_to_vault(dry_run=False) wirft KEIN NotImplementedError mehr."""
    out = split_monolith_to_slices(stage3_text)
    try:
        cutover_to_vault(out, lock_spy.target_dir, dry_run=False)
    except NotImplementedError as exc:  # pragma: no cover - das ist der RED-Fang
        pytest.fail(f"cutover_to_vault(dry_run=False) wirft noch NotImplementedError: {exc}")


def test_cutover_noop_removed_dry_run_unchanged(tmp_path: Path, stage3_text: str) -> None:
    """DoD-5b: dry_run=True bleibt unveraendert — Plan-Map zurueck, KEIN Write."""
    out = split_monolith_to_slices(stage3_text)
    target = tmp_path / "stage_3_integration"
    planned = cutover_to_vault(out, target, dry_run=True)
    assert not target.exists(), "dry_run=True hat geschrieben (Verhalten veraendert)"
    assert set(planned.keys()) == set(CANONICAL_SLICES)


def test_cutover_noop_removed_docstring_no_deferred_strings() -> None:
    """DoD-5c: Modul-Source traegt NICHT mehr die DEFERRED/no-op-Stub-Strings."""
    src_path = Path(__file__).resolve().parent / "stage_slice_migrate.py"
    src = src_path.read_text(encoding="utf-8", errors="replace")
    for forbidden in ("no-op-Stub", "NICHT verdrahtet und wirft", "DEFERRED CUTOVER"):
        assert forbidden not in src, (
            f"Doc-Drift: veralteter Stub-String '{forbidden}' noch im Source (AK-NOOP-REMOVED DoD-5c)"
        )
    _ = importlib  # Referenz halten (lint)
