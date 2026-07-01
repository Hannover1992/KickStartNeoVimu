#!/usr/bin/env python3
"""Tests fuer BL-385 Welle-2-CLI-Wiring — main() exponiert die Repo-Meta-Cutover-Flags.

RED-Worker (TDD red): diese Tests beschreiben das SOLL: main() reicht die BL-385-Welle-2-Parameter
(truths_root / repo_meta_self / bootstrap_confirm) per neuen argparse-Flags an execute() durch.

Luecke (IST): execute() HAT die keyword-only Parameter `truths_root=None, repo_meta_self=False,
bootstrap_confirm=False` bereits — ABER main()/argparse exponiert sie NICHT und der execute()-Call
in main() laesst sie weg. => Welle 2 (Repo-Meta-Routing + Bootstrap-Gate) ist per CLI NICHT fahrbar.

Erwartung BEIM RED-Lauf:
  - test_cli_repo_meta_self_flag_passed     -> RED (Flag --repo-meta-self fehlt in argparse)
  - test_cli_truths_root_flag_passed        -> RED (Flag --truths-root fehlt in argparse)
  - test_cli_bootstrap_confirm_flag_passed  -> RED (Flag --bootstrap-confirm fehlt in argparse)
  - test_cli_defaults_unchanged_regression  -> GRUEN (Default-Pfad ruft execute mit den Defaults)

Konvention: main(argv) wird direkt aufgerufen; execute() wird via monkeypatch durch einen Spy ersetzt,
der die kwargs faengt (kein echter Write, kein echter Gate-Lauf). KEIN Produktiv-Code hier.
"""
from __future__ import annotations

import truth_pilot_cutover as pc


def _spy_execute(monkeypatch):
    """Ersetzt truth_pilot_cutover.execute durch einen Spy, der (args, kwargs) faengt und ein
    harmloses Dry-Run-Ergebnis zurueckgibt (kein echter Write, kein Gate-Lauf)."""
    calls = []

    def spy(vault, repo_models=None, **kwargs):
        calls.append({"vault": vault, "repo_models": repo_models, "kwargs": kwargs})
        return {"dry_run": True, "scope_count": 0, "skipped_count": 0,
                "plan": {"skipped": []}, "would_cutover": []}

    monkeypatch.setattr(pc, "execute", spy)
    return calls


# ---------------------------------------------------------------------------
# RED — die 3 neuen CLI-Flags muessen an execute() durchgereicht werden
# ---------------------------------------------------------------------------

def test_cli_repo_meta_self_flag_passed(monkeypatch):
    """RED: main([... --repo-meta-self]) ruft execute(repo_meta_self=True).
    Heute: argparse-Fehler 'unrecognized arguments: --repo-meta-self' (SystemExit) ODER
    execute ohne den kwarg -> FAIL."""
    calls = _spy_execute(monkeypatch)
    rc = pc.main(["--vault", "/tmp/v", "--repo-meta-self", "--no-gate"])
    assert rc == 0
    assert len(calls) == 1, "execute muss genau einmal gerufen werden"
    assert calls[0]["kwargs"].get("repo_meta_self") is True, \
        "--repo-meta-self muss execute(repo_meta_self=True) durchreichen"


def test_cli_truths_root_flag_passed(monkeypatch):
    """RED: main([... --truths-root T]) ruft execute(truths_root=Path(T))."""
    calls = _spy_execute(monkeypatch)
    rc = pc.main(["--vault", "/tmp/v", "--truths-root", "/tmp/meta", "--no-gate"])
    assert rc == 0
    assert len(calls) == 1
    passed = calls[0]["kwargs"].get("truths_root")
    assert passed is not None, "--truths-root muss als kwarg an execute durchgereicht werden"
    assert pc.Path(passed) == pc.Path("/tmp/meta"), \
        "--truths-root muss als Path(T) an execute(truths_root=...) gehen"


def test_cli_bootstrap_confirm_flag_passed(monkeypatch):
    """RED: main([... --bootstrap-confirm]) ruft execute(bootstrap_confirm=True)."""
    calls = _spy_execute(monkeypatch)
    rc = pc.main(["--vault", "/tmp/v", "--bootstrap-confirm", "--no-gate"])
    assert rc == 0
    assert len(calls) == 1
    assert calls[0]["kwargs"].get("bootstrap_confirm") is True, \
        "--bootstrap-confirm muss execute(bootstrap_confirm=True) durchreichen"


# ---------------------------------------------------------------------------
# GRUEN — Default-Regression: ohne die neuen Flags bleiben die Defaults
# ---------------------------------------------------------------------------

def test_cli_defaults_unchanged_regression(monkeypatch):
    """GRUEN: ohne die neuen Flags ruft main() execute() mit den unveraenderten Defaults
    (repo_meta_self=False, bootstrap_confirm=False, truths_root=None).

    Robuster Default-Check: fehlender kwarg == Default (execute selbst definiert None/False),
    ein EXPLIZIT abweichender Wert (True / nicht-None) waere ein Regress."""
    calls = _spy_execute(monkeypatch)
    rc = pc.main(["--vault", "/tmp/v", "--no-gate"])
    assert rc == 0
    assert len(calls) == 1
    kw = calls[0]["kwargs"]
    assert kw.get("repo_meta_self", False) is False, "Default repo_meta_self muss False bleiben"
    assert kw.get("bootstrap_confirm", False) is False, "Default bootstrap_confirm muss False bleiben"
    assert kw.get("truths_root", None) is None, "Default truths_root muss None bleiben"
