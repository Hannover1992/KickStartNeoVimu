"""
test_health_orchestrate.py — BL-335 / batch_PL1 / Stage 1 (Unit, M3 het code-portion)

Zentraler RED-Test-Host fuer den /_health_orchestrate Umbrella-Core (Member-Registry +
Health-Report + Mode-Dispatcher + safety_class-Policy). Greenfield: health_orchestrate.py
und .claude/config/health_registry.yaml existieren NOCH NICHT -> Import schlaegt fehl ->
RED fuer alle 12 Gold-Punkte (ImportError beim Sammeln).

Isolation: KEIN Vault-IO. tmp_path fuer Registry-Datei + Fake-Artefakte, monkeypatch auf
health_orchestrate.find_health_registry_yaml (analog _pin_registry im Vorbild
test_resolve_format_version.py). Fuer G2a/G2b zusaetzlich resolve_vault_root auf tmp_path
gepinnt + ungestempeltes Fake-Manifest -> Gen-0-Pfad ohne echtes Vault-IO.
mocks_erlaubt=ja (stage_1.md). 1:1-Analog test_resolve_format_version.py.

Gold-Map (Blueprint_BL-335.md §4 + goldDefine_slot):
  Ring 0 (Registry, PL-335-1):
    G1a registry_parst_pflichtfelder    G1b unbekannter_member_gibt_none
    G1c fehlende_registry_gibt_leer      G1d members_by_safety_class
    G1e resolve_safety_class
  Ring 1 (Report, PL-335-2 — konsumiert resolve_format_version BL-333):
    G2a report_struktur_ist_soll         G2b ungestempelt_ist_gen0
    G2c render_report_markdown_nicht_leer
  Ring 2 (Dispatch, PL-335-3/4 — SICHERHEIT zuerst):
    G3a report_only_keine_heal_action    G3b dry_run_plan_ohne_execute
    G3c heal_safety_class_gating         G3d default_mode_ist_report_only
"""
import textwrap
from pathlib import Path

import pytest


# Greenfield-Modul: existiert noch nicht -> ImportError = RED fuer alle 12 Gold-Punkte.
# Bewusst KEIN try/except: der Import-Fehler IST der RED-Beweis (Greenfield-Import).
import health_orchestrate as ho


# Registry-Member mit allen drei safety_class-Auspraegungen, damit G1d/G1e/G3c
# auto/lock/hil disjunkt belegt sind. Form 1:1 analog format_versions.yaml
# (Minimal-Parser-kompatibel, 2-Space-Einrueckung).
SAMPLE_REGISTRY = textwrap.dedent(
    """\
    health_members:
      manifest_slim:
        drift_typ: manifest_bloat
        detector: manifest_slim.py
        healer: "manifest_slim.py slim {bl_id}"
        safety_class: lock
        status: wired
      reconcile_backlog_index:
        drift_typ: index_split_brain
        detector: reconcile_backlog_index.py
        healer: "reconcile_backlog_index.py --apply --ts {DATUM}"
        safety_class: auto
        status: wired
      stamping_heiler:
        drift_typ: missing_format_version
        detector: "resolve_format_version.read_format_version (ist==0)"
        healer: "resolve_format_version.stamp_format_version_lines (+ write-back)"
        safety_class: auto
        status: wired
      validate_backlog_frontmatter:
        drift_typ: frontmatter_schema
        detector: validate_backlog_frontmatter.py
        healer: null
        safety_class: auto
        status: wired
      d_kollaps:
        drift_typ: truth_bloat
        detector: null
        healer: "/_D_kollaps {feature}"
        safety_class: hil
        status: wired
      truth_migration:
        drift_typ: truth_format_drift
        detector: null
        healer: null
        safety_class: hil
        status: spec_only
    """
)


def _write_registry(tmp_path: Path, text: str = SAMPLE_REGISTRY) -> Path:
    reg = tmp_path / "health_registry.yaml"
    reg.write_text(text, encoding="utf-8")
    return reg


def _pin_registry(monkeypatch, reg_path):
    """Loader auf eine Test-Registry pinnen (kein Vault-IO).

    reg_path=None simuliert 'Registry-Datei fehlt' (G1c).
    """
    monkeypatch.setattr(ho, "find_health_registry_yaml", lambda: reg_path)


# ---------------------------------------------------------------------------
# Ring 0 (Registry-Fundament) — G1a..G1e
# ---------------------------------------------------------------------------

def test_registry_parst_pflichtfelder(tmp_path, monkeypatch):
    """G1a: YAML parst; je Member {drift_typ, detector, healer, safety_class, status}.

    safety_class in {auto,lock,hil}; status in {wired,spec_only,new_to_create}.
    """
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    members = ho.load_health_registry()
    assert isinstance(members, dict) and members, "Registry darf nicht leer parsen"
    for name, entry in members.items():
        assert "drift_typ" in entry, f"'{name}': 'drift_typ' fehlt"
        assert "safety_class" in entry, f"'{name}': 'safety_class' fehlt"
        assert "status" in entry, f"'{name}': 'status' fehlt"
        assert entry["safety_class"] in ho.SAFETY_CLASSES, (
            f"'{name}': safety_class {entry['safety_class']!r} nicht in {ho.SAFETY_CLASSES}"
        )
        assert entry["status"] in ("wired", "spec_only", "new_to_create"), (
            f"'{name}': status {entry['status']!r} unbekannt"
        )


def test_unbekannter_member_gibt_none(tmp_path, monkeypatch):
    """G1b: unbekannter Member -> get_member is None, KEIN KeyError (kein pytest.raises)."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    # Darf NICHT werfen — None statt KeyError.
    assert ho.get_member("gibt_es_nicht") is None


def test_fehlende_registry_gibt_leer(monkeypatch):
    """G1c: Registry-Datei fehlt (find->None gepinnt) -> load_health_registry() == {}, kein Crash."""
    _pin_registry(monkeypatch, None)
    assert ho.load_health_registry() == {}


def test_members_by_safety_class(tmp_path, monkeypatch):
    """G1d: members_by_safety_class('auto') >=1; 'lock'/'hil' disjunkt + korrekt belegt."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)

    auto = set(ho.members_by_safety_class("auto"))
    lock = set(ho.members_by_safety_class("lock"))
    hil = set(ho.members_by_safety_class("hil"))

    assert len(auto) >= 1, f"'auto'-Klasse muss >=1 Member liefern, war {auto}"
    assert "manifest_slim" in lock, f"'lock' muss manifest_slim enthalten, war {lock}"
    assert {"d_kollaps", "truth_migration"} <= hil, f"'hil' muss d_kollaps+truth_migration enthalten, war {hil}"
    # Disjunkt: kein Member in zwei Klassen.
    assert auto.isdisjoint(lock) and auto.isdisjoint(hil) and lock.isdisjoint(hil), (
        f"safety_class-Mengen muessen disjunkt sein: auto={auto} lock={lock} hil={hil}"
    )


def test_resolve_safety_class(tmp_path, monkeypatch):
    """G1e: resolve_safety_class je Member korrekt; unbekannter Member -> None."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    assert ho.resolve_safety_class("manifest_slim") == "lock"
    assert ho.resolve_safety_class("reconcile_backlog_index") == "auto"
    assert ho.resolve_safety_class("d_kollaps") == "hil"
    # Unbekannter Member -> None (kein Crash).
    assert ho.resolve_safety_class("gibt_es_nicht") is None


# ---------------------------------------------------------------------------
# Ring 1 (Report — konsumiert resolve_format_version BL-333) — G2a..G2c
# ---------------------------------------------------------------------------

def _fake_vault(tmp_path: Path, monkeypatch) -> Path:
    """Tmp-'Vault' mit ungestempeltem Fake-Manifest; resolve_vault_root + Registry gepinnt.

    Kein echtes Vault-IO. Ungestempeltes Frontmatter (kein format_version) -> der Report
    muss format_version_ist==0 (Gen-0) lesen, NIE crashen (Case-1944-Kanarienvogel).
    """
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    monkeypatch.setattr(ho, "resolve_vault_root", lambda: tmp_path, raising=False)
    # Ungestempeltes Manifest (KEIN format_version-Stempel) als Fake-Artefakt.
    manifest = tmp_path / "_manifest.md"
    manifest.write_text("---\ntype: manifest\nbacklog_counter: 42\n---\n\n# body\n", encoding="utf-8")
    return tmp_path


def test_report_struktur_ist_soll(tmp_path, monkeypatch):
    """G2a: generate_health_report liefert per_artifact (ist+soll je Artefakt) + heal_recommendations."""
    vault = _fake_vault(tmp_path, monkeypatch)
    report = ho.generate_health_report(vault)
    assert isinstance(report, dict)
    assert "per_artifact" in report, "Report braucht 'per_artifact'"
    assert "heal_recommendations" in report, "Report braucht 'heal_recommendations'"
    assert isinstance(report["heal_recommendations"], list)
    per = report["per_artifact"]
    assert isinstance(per, dict) and per, "per_artifact darf nicht leer sein"
    for typ, art in per.items():
        assert "format_version_ist" in art, f"'{typ}': format_version_ist fehlt"
        assert "format_version_soll" in art, f"'{typ}': format_version_soll fehlt"


def test_ungestempelt_ist_gen0(tmp_path, monkeypatch):
    """G2b: ungestempeltes/legacy Artefakt -> format_version_ist==0 (Gen-0), NIE Crash.

    Resilienz-Kanarienvogel (Case-Study 1944: 234KB-Manifest ohne Stempel -> Python-Bruch).
    """
    vault = _fake_vault(tmp_path, monkeypatch)
    report = ho.generate_health_report(vault)
    ist_werte = [art.get("format_version_ist") for art in report["per_artifact"].values()]
    assert 0 in ist_werte, (
        f"ungestempeltes Artefakt muss als Gen-0 (format_version_ist==0) gelesen werden, fand {ist_werte}"
    )


def test_render_report_markdown_nicht_leer(tmp_path, monkeypatch):
    """G2c: render_report_markdown(report) -> nicht-leerer str mit Markdown-Struktur."""
    vault = _fake_vault(tmp_path, monkeypatch)
    report = ho.generate_health_report(vault)
    md = ho.render_report_markdown(report)
    assert isinstance(md, str) and md.strip(), "Markdown-Report darf nicht leer sein"
    assert "#" in md, "Markdown-Report braucht Markdown-Struktur (z.B. Ueberschrift)"


# ---------------------------------------------------------------------------
# Ring 2 (Dispatch + Modes) — SICHERHEIT zuerst — G3a..G3d
# ---------------------------------------------------------------------------

def _report_mit_recommendations(tmp_path, monkeypatch) -> dict:
    """Echter Report aus dem Fake-Vault (enthaelt heal_recommendations fuer plan_heal)."""
    vault = _fake_vault(tmp_path, monkeypatch)
    return ho.generate_health_report(vault)


def test_report_only_keine_heal_action(tmp_path, monkeypatch):
    """G3a: plan_heal(report, 'report-only') == [] — OBERSTE Sicherheits-Invariante (read-only)."""
    report = _report_mit_recommendations(tmp_path, monkeypatch)
    assert ho.plan_heal(report, mode="report-only") == [], (
        "report-only darf NIE eine Heal-Action erzeugen (read-only Garantie)"
    )


def test_dry_run_plan_ohne_execute(tmp_path, monkeypatch):
    """G3b: plan_heal(report, 'dry-run') liefert Plan-Eintraege, alle mit execute==False."""
    report = _report_mit_recommendations(tmp_path, monkeypatch)
    plan = ho.plan_heal(report, mode="dry-run")
    assert isinstance(plan, list) and plan, "dry-run muss Plan-Eintraege liefern"
    for eintrag in plan:
        assert eintrag.get("execute") is False, (
            f"dry-run-Eintrag muss execute==False tragen (zeigt, fuehrt nicht aus), war {eintrag}"
        )


def test_heal_safety_class_gating(tmp_path, monkeypatch):
    """G3c: plan_heal(report, 'heal') — auto direkt; lock needs_lock; hil needs_freigabe."""
    report = _report_mit_recommendations(tmp_path, monkeypatch)
    plan = ho.plan_heal(report, mode="heal")
    assert isinstance(plan, list) and plan, "heal-Mode muss Plan-Eintraege liefern"
    by_class = {}
    for eintrag in plan:
        by_class.setdefault(eintrag["safety_class"], []).append(eintrag)

    for eintrag in by_class.get("auto", []):
        assert eintrag.get("needs_lock") is False, f"auto-Member darf keinen Lock brauchen: {eintrag}"
        assert eintrag.get("needs_freigabe") is False, f"auto-Member braucht keine Freigabe: {eintrag}"
    for eintrag in by_class.get("lock", []):
        assert eintrag.get("needs_lock") is True, f"lock-Member braucht Lock (BL-334): {eintrag}"
    for eintrag in by_class.get("hil", []):
        assert eintrag.get("needs_freigabe") is True, f"hil-Member braucht Freigabe (kein Auto-Execute): {eintrag}"


def test_default_mode_ist_report_only(tmp_path, monkeypatch):
    """G3d: plan_heal(report) ohne mode-Arg verhaelt sich wie report-only ([]) — Default strukturell safe."""
    report = _report_mit_recommendations(tmp_path, monkeypatch)
    assert ho.plan_heal(report) == [], "Default-Mode (kein Arg) muss report-only sein: leerer Plan"


def test_heal_gating_alle_klassen_synthetic():
    """G3c-Erweiterung: plan_heal('heal') gated ALLE drei safety_classes korrekt — SYNTHETISCH.

    Nach dem Drift-Typ-Matching (kein blanket-all) wird das lock/hil-Gating von den
    Scan-abgeleiteten Recommendations des Fake-Vaults (nur stamping_heiler=auto) nicht mehr
    exerziert. Dieser Test entkoppelt das Gating vollstaendig von der Scan-Logik: ein
    handgebauter Report mit je einem auto/lock/hil-Member prueft das Gating direkt (KEIN
    Vault-IO, KEINE Registry).
    """
    report = {
        "per_artifact": {},
        "heal_recommendations": [
            {"member": "reconcile_backlog_index", "drift": "x", "safety_class": "auto"},
            {"member": "manifest_slim", "drift": "y", "safety_class": "lock"},
            {"member": "d_kollaps", "drift": "z", "safety_class": "hil"},
        ],
    }
    plan = ho.plan_heal(report, mode="heal")
    by_class = {}
    for eintrag in plan:
        by_class.setdefault(eintrag["safety_class"], []).append(eintrag)

    # auto: direkt ausfuehrbar (kein Lock, keine Freigabe).
    assert len(by_class.get("auto", [])) == 1, f"genau 1 auto-Eintrag erwartet, plan={plan}"
    for eintrag in by_class["auto"]:
        assert eintrag.get("needs_lock") is False, f"auto darf keinen Lock brauchen: {eintrag}"
        assert eintrag.get("needs_freigabe") is False, f"auto braucht keine Freigabe: {eintrag}"
        assert eintrag.get("execute") is True, f"auto muss direkt ausfuehrbar sein: {eintrag}"

    # lock: braucht vault_lock (BL-334), kein Auto-Execute.
    assert len(by_class.get("lock", [])) == 1, f"genau 1 lock-Eintrag erwartet, plan={plan}"
    for eintrag in by_class["lock"]:
        assert eintrag.get("needs_lock") is True, f"lock braucht Lock (BL-334): {eintrag}"
        assert eintrag.get("execute") is False, f"lock darf nicht auto-ausfuehren: {eintrag}"

    # hil: braucht Mensch-Freigabe, kein Auto-Execute.
    assert len(by_class.get("hil", [])) == 1, f"genau 1 hil-Eintrag erwartet, plan={plan}"
    for eintrag in by_class["hil"]:
        assert eintrag.get("needs_freigabe") is True, f"hil braucht Freigabe: {eintrag}"
        assert eintrag.get("execute") is False, f"hil darf nicht auto-ausfuehren: {eintrag}"


# ---------------------------------------------------------------------------
# Ring 3 (cwd-Stabilitaet — Kanarienvogel, BL-343 PL-343-1) — G_cwd
# ---------------------------------------------------------------------------

def test_cwd_stabil(monkeypatch):
    """G_cwd (BL-343 PL-343-1): find_health_registry_yaml() ist cwd-INVARIANT.

    Gleicher Bug wie resolve_format_version: REPO_FALLBACK ist heute cwd-relativ
    (Path(".claude/config/health_registry.yaml")) -> aus dem scripts-cwd zeigt der
    Fallback auf .claude/scripts/.claude/config/... (Phantom) statt auf den Repo-
    Default; das Ergebnis weicht je cwd ab -> false-GREEN-Risiko (BL-335/336-Klasse).
    GREEN baut den REPO_FALLBACK __file__-relativ
    (Path(__file__).resolve().parent.parent / "config" / "health_registry.yaml").

    Kein Vault-IO: resolve_vault_root auf None gepinnt, damit nur der Repo-Fallback
    geprueft wird (sonst koennte ein vorhandener Vault das Ergebnis maskieren).
    """
    import os

    # Vault ausblenden -> nur der Repo-Fallback entscheidet (reiner cwd-Test).
    monkeypatch.setattr(ho, "resolve_vault_root", lambda: None, raising=False)

    scripts_dir = Path(__file__).resolve().parent
    repo_root = scripts_dir.parent.parent  # .../OmniCommand (repo-root)

    orig_cwd = os.getcwd()
    try:
        os.chdir(repo_root)
        from_repo_root = ho.find_health_registry_yaml()

        os.chdir(scripts_dir)
        from_scripts = ho.find_health_registry_yaml()
    finally:
        os.chdir(orig_cwd)

    # 1) cwd-invariant: identisches Ergebnis aus beiden cwds.
    assert from_repo_root == from_scripts, (
        f"find_health_registry_yaml ist cwd-abhaengig: repo-root={from_repo_root!r} "
        f"!= scripts-cwd={from_scripts!r} (cwd-Artefakt — Fallback NICHT __file__-relativ?)"
    )

    # 2) Kein Phantom: entweder existierender Pfad oder None — nie ein cwd-Doppelpfad.
    if from_repo_root is not None:
        assert from_repo_root.is_file(), (
            f"find_health_registry_yaml lieferte nicht-existenten Pfad {from_repo_root!r} "
            "(Phantom statt None)"
        )
