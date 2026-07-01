"""
test_gc_budgets.py — BL-338 / batch_PL1 / PL-338-1 (Bloat-Budgets, M3, Stufe 1)

RED-Test-Host fuer die gc_budgets-Schicht (Budget-Registry + Loader + Resolver +
Over-Budget-Praedikat). Generalisiert den O(1)-Budget-Begriff aus manifest_slim.py
(Working-Set-Schwellwert) auf eine Policy-Registry je Artefakt-Typ: pro Typ ein
{budget_bytes|budget_lines, strategy_hint}, aufgeloest aus EINER YAML-Quelle.

Greenfield: gc_budgets.py und .claude/config/gc_budgets.yaml existieren NOCH NICHT
-> `import gc_budgets` schlaegt fehl -> ImportError = RED fuer alle G1*/G_cwd.
Bewusst KEIN try/except: der Import-Fehler IST der RED-Beweis fuer den Loader-Ring
(1:1-Analog zu test_resolve_format_version.py).

Isolation: KEIN Vault-IO. tmp_path fuer Registry-Dateien, monkeypatch auf
find_gc_budgets_yaml. Stil-Vorlage: resolve_format_version.py (load_*/find_*_yaml/
resolve_*).

cwd-STABILITAETS-MANDAT (PL-336-4-Lehre, hier proaktiv verankert):
  find_gc_budgets_yaml() MUSS den REPO_FALLBACK __file__-RELATIV aufloesen
  (Path(__file__).resolve().parent.parent / "config" / "gc_budgets.yaml"), NICHT
  cwd-relativ. So liefert resolve_budget(typ) aus JEDEM cwd identische Werte
  (vermeidet die cwd-Artefakt-false-GREEN von BL-335/336). G_cwd verifiziert das:
  die ECHTE (ungepinnte) find_gc_budgets_yaml() findet entweder einen EXISTIERENDEN
  Pfad oder None — nie ein cwd-abhaengiges Doppelpfad-Artefakt — und das identisch
  aus repo-root UND aus dem scripts-cwd.

Gold-Map (PL-338-1 §Gold-Definition):
  G1a registry_parst_pflichttypen     G1b resolve_budget_gibt_wert
  G1c unbekannter_typ_gibt_none        G1d fehlende_registry_gibt_leer
  G1e over_budget_true_wenn_drueber    G1f over_budget_false_wenn_drunter
  G_cwd cwd_stabil (__file__-relativer Fallback, cwd-invariant)
"""
import textwrap
from pathlib import Path

import pytest


# Greenfield-Modul: existiert noch nicht -> ImportError = RED fuer alle Tests.
# Bewusst KEIN try/except: der Import-Fehler IST der RED-Beweis fuer den Loader-Ring.
import gc_budgets as gb


# Pflicht-Typen aus PL-338-1 §Gold-Contract (mind. diese 4 Artefakt-Typen).
PFLICHT_TYPEN = ("manifest", "parking_lot", "backlog_index", "model")


SAMPLE_REGISTRY = textwrap.dedent(
    """\
    gc_budgets:
      manifest:
        budget_bytes: 80000
        strategy_hint: manifest_slim
      parking_lot:
        budget_bytes: 150000
        strategy_hint: round_offload
      backlog_index:
        budget_bytes: 100000
        strategy_hint: reconcile
      model:
        budget_bytes: 150000
        strategy_hint: model_split
    """
)


def _write_registry(tmp_path: Path, text: str = SAMPLE_REGISTRY) -> Path:
    reg = tmp_path / "gc_budgets.yaml"
    reg.write_text(text, encoding="utf-8")
    return reg


def _pin_registry(monkeypatch, reg_path):
    """Loader auf eine Test-Registry pinnen (kein Vault-IO, kein __file__-Fallback).

    reg_path=None simuliert 'Registry-Datei fehlt' (G1d).
    """
    monkeypatch.setattr(gb, "find_gc_budgets_yaml", lambda: reg_path)


# ---------------------------------------------------------------------------
# Ring 0 (Fundament) — G1a..G1d
# ---------------------------------------------------------------------------

def test_registry_parst_pflichttypen(tmp_path, monkeypatch):
    """G1a: YAML parst; je Pflicht-Typ ein Budget vorhanden (budget_bytes ODER budget_lines)."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    config = gb.load_gc_budgets()
    for typ in PFLICHT_TYPEN:
        assert typ in config, f"Pflicht-Typ '{typ}' fehlt in Budget-Registry"
        entry = config[typ]
        assert ("budget_bytes" in entry) or ("budget_lines" in entry), (
            f"'{typ}': weder budget_bytes noch budget_lines vorhanden, ist {entry!r}"
        )


def test_resolve_budget_gibt_wert(tmp_path, monkeypatch):
    """G1b: resolve_budget(typ) == YAML-Budget-Wert, deterministisch je Typ."""
    reg = _write_registry(
        tmp_path,
        SAMPLE_REGISTRY.replace(
            "  backlog_index:\n    budget_bytes: 100000",
            "  backlog_index:\n    budget_bytes: 123456",
        ),
    )
    _pin_registry(monkeypatch, reg)
    assert gb.resolve_budget("backlog_index") == 123456
    assert gb.resolve_budget("parking_lot") == 150000
    # Deterministisch: zweiter Aufruf liefert denselben Wert.
    assert gb.resolve_budget("backlog_index") == 123456


def test_unbekannter_typ_gibt_none(tmp_path, monkeypatch):
    """G1c: unbekannter Typ -> None, KEIN KeyError/Crash (kein pytest.raises)."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    # Darf NICHT werfen — None-Sentinel statt Crash.
    assert gb.resolve_budget("gibt_es_nicht") is None


def test_fehlende_registry_gibt_leer(monkeypatch):
    """G1d: Registry-Datei fehlt (find_gc_budgets_yaml->None) -> load=={} + resolve->None, KEIN Crash."""
    _pin_registry(monkeypatch, None)
    assert gb.load_gc_budgets() == {}
    assert gb.resolve_budget("manifest") is None


# ---------------------------------------------------------------------------
# Ring 1 (Over-Budget-Praedikat) — G1e / G1f
# ---------------------------------------------------------------------------

def test_over_budget_true_wenn_drueber(tmp_path, monkeypatch):
    """G1e: actual > budget -> True (Artefakt ueber Policy-Schwellwert)."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    # parking_lot Budget == 150000; 200000 liegt darueber.
    assert gb.over_budget("parking_lot", 200000) is True


def test_over_budget_false_wenn_drunter(tmp_path, monkeypatch):
    """G1f: actual <= budget -> False; unbekannter Typ (budget None) -> False, nie Crash."""
    reg = _write_registry(tmp_path)
    _pin_registry(monkeypatch, reg)
    # parking_lot Budget == 150000; 100000 liegt darunter.
    assert gb.over_budget("parking_lot", 100000) is False
    # budget None (unbekannter Typ) -> False statt Crash.
    assert gb.over_budget("gibt_es_nicht", 999999999) is False


# ---------------------------------------------------------------------------
# Ring 2 (cwd-Stabilitaet — OBERSTER Kanarienvogel, PL-336-4-Lehre) — G_cwd
# ---------------------------------------------------------------------------

def test_cwd_stabil(monkeypatch):
    """G_cwd: find_gc_budgets_yaml() ist cwd-INVARIANT (kein Doppelpfad-Artefakt).

    Die ECHTE (ungepinnte) find_gc_budgets_yaml() muss aus JEDEM cwd dasselbe
    liefern: entweder einen EXISTIERENDEN Pfad ODER None — nie ein cwd-relatives
    Phantom. GREEN baut den REPO_FALLBACK __file__-relativ
    (Path(__file__).resolve().parent.parent / "config" / "gc_budgets.yaml"), darum
    ist das Ergebnis identisch aus repo-root und aus dem scripts-cwd.
    """
    import os

    scripts_dir = Path(__file__).resolve().parent
    repo_root = scripts_dir.parent.parent  # .../OmniCommand (repo-root)

    orig_cwd = os.getcwd()
    try:
        os.chdir(repo_root)
        from_repo_root = gb.find_gc_budgets_yaml()

        os.chdir(scripts_dir)
        from_scripts = gb.find_gc_budgets_yaml()
    finally:
        os.chdir(orig_cwd)

    # 1) cwd-invariant: identisches Ergebnis aus beiden cwds.
    assert from_repo_root == from_scripts, (
        f"find_gc_budgets_yaml ist cwd-abhaengig: repo-root={from_repo_root!r} "
        f"!= scripts-cwd={from_scripts!r} (cwd-Artefakt — Fallback NICHT __file__-relativ?)"
    )

    # 2) Kein Phantom: entweder existierender Pfad oder None — nie ein Doppelpfad-Artefakt.
    if from_repo_root is not None:
        assert from_repo_root.is_file(), (
            f"find_gc_budgets_yaml lieferte nicht-existenten Pfad {from_repo_root!r} "
            "(Phantom statt None)"
        )

    # 3) resolve_budget liefert konsistent aus beiden cwds (None ODER int — nie Crash).
    try:
        os.chdir(repo_root)
        r1 = gb.resolve_budget("parking_lot")
        os.chdir(scripts_dir)
        r2 = gb.resolve_budget("parking_lot")
    finally:
        os.chdir(orig_cwd)
    assert r1 == r2, f"resolve_budget cwd-abhaengig: {r1!r} != {r2!r}"
