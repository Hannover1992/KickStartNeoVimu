"""
test_resolve_format_version.py — BL-333 / batch_PL1 / Stufe 1 (Atomic / Laserpointer)

Zentraler RED-Test-Host fuer die format_version-Schicht (Registry + Loader + Stamping
+ Dual-Read-Gen-0 + WARN-Haken). Greenfield: resolve_format_version.py und
.claude/config/format_versions.yaml existieren NOCH NICHT -> Import schlaegt fehl ->
RED fuer alle G1*/G2b/G2d/G2e/G3* (ImportError). G2a importiert render_index aus dem
Bestands-Writer (existiert) und faellt per AssertionError (Stamp noch nicht emittiert).

Isolation: KEIN Vault-IO. tmp_path fuer Registry-Dateien, monkeypatch auf den
Resolver-Pfad. mocks_erlaubt=ja (stage_1.md).

Gold-Map (sub-1.md §Gold-Definition):
  G1a registry_parst_pflichttypen   G1b resolve_gibt_yaml_version
  G1c unbekannter_typ_gibt_none      G1d fehlende_registry_gibt_none
  G2a render_index_traegt_format_version (Bestands-Writer-Host, AssertionError)
  G2b reconcile_rewrite_format_version (additiv / kein Duplikat)
  G2d ungestempelt_ist_gen0          G2e loader_fehlt_stamp_weggelassen
  G3a migration_disposition_fehlt_warnt (backlog-frontmatter, non-blocking)
  G3b manifest_migration_disposition_warnt (manifest-schema, non-blocking)
"""
import textwrap
from pathlib import Path

import pytest


# Greenfield-Modul: existiert noch nicht -> ImportError = RED fuer G1*/G2b/G2d/G2e/G3*.
# Bewusst KEIN try/except: der Import-Fehler IST der RED-Beweis fuer den Loader-Ring.
import resolve_format_version as rfv


# Pflicht-Typen aus sub-1.md §1 (truth_graph VORGESEHEN, kein Writer).
PFLICHT_TYPEN = ("manifest", "model", "backlog_index", "parking_lot", "truth_graph")


SAMPLE_REGISTRY = textwrap.dedent(
    """\
    format_versions:
      manifest:
        version: 1
        seit_bl: BL-333
        migrations_chain: []
      model:
        version: 1
        seit_bl: BL-333
        migrations_chain: []
      backlog_index:
        version: 1
        seit_bl: BL-333
        migrations_chain: []
      parking_lot:
        version: 1
        seit_bl: BL-333
        migrations_chain: []
      truth_graph:
        version: 1
        seit_bl: BL-333
        migrations_chain: []
    """
)


def _write_registry(tmp_path: Path, text: str = SAMPLE_REGISTRY) -> Path:
    reg = tmp_path / "format_versions.yaml"
    reg.write_text(text, encoding="utf-8")
    return reg


def _pin_registry(monkeypatch, reg_path):
    """Resolver auf eine Test-Registry pinnen (kein Vault-IO).

    reg_path=None simuliert 'Registry-Datei fehlt' (G1d).
    """
    monkeypatch.setattr(rfv, "find_format_versions_yaml", lambda: reg_path)


# ---------------------------------------------------------------------------
# Ring 0 (Fundament) — G1a..G1d
# ---------------------------------------------------------------------------

def test_registry_parst_pflichttypen(tmp_path, monkeypatch):
    """G1a: YAML parst; je Pflicht-Typ {version, seit_bl, migrations_chain}; chain=Liste."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    config = rfv.load_format_versions()
    for typ in PFLICHT_TYPEN:
        assert typ in config, f"Pflicht-Typ '{typ}' fehlt in Registry"
        entry = config[typ]
        assert "version" in entry, f"'{typ}': 'version' fehlt"
        assert "seit_bl" in entry, f"'{typ}': 'seit_bl' fehlt"
        assert "migrations_chain" in entry, f"'{typ}': 'migrations_chain' fehlt"
        assert isinstance(entry["migrations_chain"], list), (
            f"'{typ}': migrations_chain muss Liste sein, ist {type(entry['migrations_chain'])}"
        )


def test_resolve_gibt_yaml_version(tmp_path, monkeypatch):
    """G1b: resolve_format_version(typ) == YAML-version, deterministisch je Typ."""
    reg = _write_registry(
        tmp_path,
        SAMPLE_REGISTRY.replace(
            "  backlog_index:\n    version: 1",
            "  backlog_index:\n    version: 3",
        ),
    )
    _pin_registry(monkeypatch, reg)
    assert rfv.resolve_format_version("backlog_index") == 3
    assert rfv.resolve_format_version("manifest") == 1
    # Deterministisch: zweiter Aufruf liefert denselben Wert.
    assert rfv.resolve_format_version("backlog_index") == 3


def test_unbekannter_typ_gibt_none(tmp_path, monkeypatch):
    """G1c: unbekannter Typ -> None (Gen-0-Sentinel), KEIN KeyError/Crash (kein pytest.raises)."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    # Darf NICHT werfen — Gen-0-Sentinel statt Crash.
    assert rfv.resolve_format_version("gibt_es_nicht") is None


def test_fehlende_registry_gibt_none(monkeypatch):
    """G1d: Registry-Datei fehlt (find_format_versions_yaml->None) -> None, KEIN Traceback."""
    _pin_registry(monkeypatch, None)
    assert rfv.resolve_format_version("manifest") is None


# ---------------------------------------------------------------------------
# Ring 1a (Stamping) — G2a (Bestands-Writer-Host) + G2b
# ---------------------------------------------------------------------------

def test_render_index_traegt_format_version(monkeypatch):
    """G2a: render_index()-Output traegt ^format_version:-Zeile; Wert == resolve('backlog_index').

    Host = Bestands-Writer regenerate_backlog_index.render_index (importierbar) ->
    faellt per AssertionError (Stamp noch nicht emittiert) = RED.
    """
    import regenerate_backlog_index as rbi

    # Loader-Wert determinieren (Writer=Follow, kein eigenes Literal).
    monkeypatch.setattr(rbi, "resolve_format_version", lambda typ: 1, raising=False)

    items = {
        "BL-1": {"bl_id": "BL-1", "title": "T", "status": "OPEN",
                 "vault_path": "p", "created": "2026-06-13", "reifegrad": "UNREIF"},
    }
    out = rbi.render_index(items, total_count=1)
    fm_lines = out.split("---", 2)[1].splitlines()
    fv_lines = [ln for ln in fm_lines if ln.startswith("format_version:")]
    assert len(fv_lines) == 1, f"genau 1 format_version-Zeile im Frontmatter erwartet, fand {fv_lines}"
    assert fv_lines[0].split(":", 1)[1].strip() == "1", (
        f"format_version-Wert muss resolve('backlog_index')==1 sein, ist {fv_lines[0]!r}"
    )


def test_reconcile_rewrite_format_version():
    """G2b: Re-Write — fehlt -> genau 1 Zeile additiv; MIT vorhandenem Stempel -> kein Duplikat."""
    # Helper-Heimat = resolve_format_version.py (Writer=Follow, Wert via Loader-Call).
    # fehlt -> additiv einfuegen:
    lines_ohne = ["---", "backlog_counter: 5", "backlog_last_update: '2026-06-13'", "---"]
    out_neu = rfv.stamp_format_version_lines(lines_ohne, "backlog_index", version=1)
    fv = [ln for ln in out_neu if ln.startswith("format_version:")]
    assert len(fv) == 1, f"fehlend -> genau 1 format_version-Zeile additiv, fand {fv}"

    # MIT vorhandenem Stempel -> kein Duplikat (idempotent):
    out_idem = rfv.stamp_format_version_lines(out_neu, "backlog_index", version=1)
    fv_idem = [ln for ln in out_idem if ln.startswith("format_version:")]
    assert len(fv_idem) == 1, f"vorhanden -> kein Duplikat, fand {fv_idem}"


# ---------------------------------------------------------------------------
# Ring 2 (Resilienz-Insel — OBERSTER Kanarienvogel) — G2d / G2e
# ---------------------------------------------------------------------------

def test_ungestempelt_ist_gen0():
    """G2d: ungestempeltes/legacy Frontmatter (kein format_version) -> Generation-0, NIE Crash.

    Case-Study 1944: 234KB-Manifest ohne Stempel -> Python-Bruch. Hier: read_format_version
    muss 0 (Gen-0) liefern statt zu werfen.
    """
    legacy_fm = "---\ntype: manifest\nbacklog_counter: 42\n---\n\n# body\n"
    gen = rfv.read_format_version(legacy_fm)
    assert gen == 0, f"ungestempeltes Artefakt muss als Gen-0 gelesen werden, war {gen!r}"


def test_loader_fehlt_stamp_weggelassen(monkeypatch):
    """G2e: Loader nicht ladbar (resolve gibt None) -> Writer laesst Stamp WEG, KEIN Crash.

    Symmetrie zu G2d: stamp_format_version_lines mit version=None fuegt KEINE Zeile ein.
    """
    lines = ["---", "backlog_counter: 5", "---"]
    out = rfv.stamp_format_version_lines(lines, "backlog_index", version=None)
    fv = [ln for ln in out if ln.startswith("format_version:")]
    assert fv == [], f"Loader-fehlt -> Stamp WEGGELASSEN (kein Crash, keine Zeile), fand {fv}"


# ---------------------------------------------------------------------------
# Ring 1b (WARN-Haken) — G3a / G3b (non-blocking, additiv zu REQUIRED/C1-C3)
# ---------------------------------------------------------------------------

def test_migration_disposition_fehlt_warnt():
    """G3a: fehlt migration_disposition -> WARN (non-blocking), REQUIRED unveraendert.

    Pruef-Haken-Kontrakt: check_migration_disposition(fm) -> WARN-Liste (>=1 Eintrag
    wenn Feld fehlt), eskaliert NIE zu exit!=0. REQUIRED-Pflichtfelder bleiben unberuehrt.
    """
    fm_ohne = {"id": "BL-1", "title": "T", "status": "OPEN",
               "reifegrad": "UNREIF", "created": "2026-06-13"}
    warns = rfv.check_migration_disposition(fm_ohne)
    assert isinstance(warns, list)
    assert len(warns) == 1, f"fehlendes migration_disposition -> genau 1 WARN, fand {warns}"
    assert "migration_disposition" in warns[0]

    # MIT gueltigem Wert -> keine WARN.
    fm_mit = dict(fm_ohne, migration_disposition="retroaktiv")
    assert rfv.check_migration_disposition(fm_mit) == []


def test_manifest_migration_disposition_warnt():
    """G3b: dito fuer Manifest-Schema (Follow zu A6); non-blocking, C1/C2/C3 unveraendert."""
    manifest_ohne = "---\ntype: manifest\nbacklog_counter: 1\n---\n"
    warns = rfv.check_migration_disposition_manifest(manifest_ohne)
    assert isinstance(warns, list)
    assert len(warns) == 1, f"Manifest ohne migration_disposition -> genau 1 WARN, fand {warns}"

    manifest_mit = "---\ntype: manifest\nmigration_disposition: forward-compat-only\n---\n"
    assert rfv.check_migration_disposition_manifest(manifest_mit) == []


# ---------------------------------------------------------------------------
# Ring 3 (cwd-Stabilitaet — Kanarienvogel, BL-343 PL-343-1) — G_cwd
# ---------------------------------------------------------------------------

def test_cwd_stabil(monkeypatch):
    """G_cwd (BL-343 PL-343-1): find_format_versions_yaml() ist cwd-INVARIANT.

    Analog gc_budgets G_cwd (PL-336-4-Lehre). Heute ist REPO_FALLBACK cwd-relativ
    (Path(".claude/config/format_versions.yaml")) -> aus dem scripts-cwd zeigt der
    Fallback auf .claude/scripts/.claude/config/... (Phantom) statt auf den Repo-
    Default; das Ergebnis weicht je cwd ab -> false-GREEN-Risiko (BL-335/336-Klasse).
    GREEN baut den REPO_FALLBACK __file__-relativ
    (Path(__file__).resolve().parent.parent / "config" / "format_versions.yaml").

    Kein Vault-IO: resolve_vault_root auf None gepinnt, damit nur der Repo-Fallback
    geprueft wird (sonst koennte ein vorhandener Vault das Ergebnis maskieren).
    """
    import os

    # Vault ausblenden -> nur der Repo-Fallback entscheidet (reiner cwd-Test).
    monkeypatch.setattr(rfv, "resolve_vault_root", lambda: None)

    scripts_dir = Path(__file__).resolve().parent
    repo_root = scripts_dir.parent.parent  # .../OmniCommand (repo-root)

    orig_cwd = os.getcwd()
    try:
        os.chdir(repo_root)
        from_repo_root = rfv.find_format_versions_yaml()

        os.chdir(scripts_dir)
        from_scripts = rfv.find_format_versions_yaml()
    finally:
        os.chdir(orig_cwd)

    # 1) cwd-invariant: identisches Ergebnis aus beiden cwds.
    assert from_repo_root == from_scripts, (
        f"find_format_versions_yaml ist cwd-abhaengig: repo-root={from_repo_root!r} "
        f"!= scripts-cwd={from_scripts!r} (cwd-Artefakt — Fallback NICHT __file__-relativ?)"
    )

    # 2) Kein Phantom: entweder existierender Pfad oder None — nie ein cwd-Doppelpfad.
    if from_repo_root is not None:
        assert from_repo_root.is_file(), (
            f"find_format_versions_yaml lieferte nicht-existenten Pfad {from_repo_root!r} "
            "(Phantom statt None)"
        )
