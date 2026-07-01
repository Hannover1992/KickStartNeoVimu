#!/usr/bin/env python3
"""RED-Tests fuer BL-309-post: truth_resolver ordner-konventions-agnostisch.

Bug (live verifiziert): _find_atomic + Step-3 legacy-scan suchen NUR unter
`{bl_folder}/2_Model/...`. Migrierte Ordner mit `Model/`, `Models/` (oder bl_folder
== Model-Ordner direkt) werden NICHT als atomic/legacy gefunden -> Resolver faellt
durch bis source=repo (Stale-Read der alten .claude/models-Kopie).

SOLL: atomic-first UND legacy-scan finden truths/Model-Dateien unter den bekannten
Konventionen — `{bl}/2_Model/...`, `{bl}/Model/...`, `{bl}/Models/...`, `{bl}/...`.
Praezedenz bleibt: atomic > alias > legacy > repo.

Diese Datei ist additiv zu test_truth_resolver.py (das die 2_Model-Konvention
weiter abdeckt = Regressions-Schutz). RED-Worker: schreibt NUR Tests, kein Prod-Code.
"""
from __future__ import annotations

import truth_resolver as tr


def _mk_truth(truths_dir, local_id, text, tid=None):
    """Baut ein Atom {truths_dir}/{local_id}.md mit type:truth (wie test_truth_resolver)."""
    truths_dir.mkdir(parents=True, exist_ok=True)
    tid = tid or f"BL-x.{local_id}"
    (truths_dir / f"{local_id}.md").write_text(
        f"---\ntype: truth\nid: {tid}\nlocal_id: {local_id}\ntext: {text}\n"
        f"typ: FESTSTELLUNG\nherkunft: INTERN\nstatus: BESTAETIGT\ntruth_grade: code_verified\n---\n\n# {local_id}\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# RED 1 (Kern): Atom unter Model/truths/ -> source=atomic (heute: repo/legacy)
# ---------------------------------------------------------------------------
def test_atomic_under_Model_singular(tmp_path):
    bl = tmp_path / "BL-041-foo"
    _mk_truth(bl / "Model" / "truths", "W1", "Wahrheit aus Model", tid="BL-041.W1")
    r = tr.resolve("W1", bl_folder=bl)
    assert r.found, "W1 unter Model/truths/ muss aufloesbar sein"
    assert r.source == tr.SOURCE_ATOMIC, f"erwartet atomic, war {r.source}"
    assert r.truth["text"] == "Wahrheit aus Model"


# ---------------------------------------------------------------------------
# RED 2: Atom unter Models/truths/ (Plural) -> source=atomic
# ---------------------------------------------------------------------------
def test_atomic_under_Models_plural(tmp_path):
    bl = tmp_path / "BL-xyz"
    _mk_truth(bl / "Models" / "truths", "W1", "Wahrheit aus Models", tid="BL-xyz.W1")
    r = tr.resolve("W1", bl_folder=bl)
    assert r.found, "W1 unter Models/truths/ muss aufloesbar sein"
    assert r.source == tr.SOURCE_ATOMIC, f"erwartet atomic, war {r.source}"
    assert r.truth["text"] == "Wahrheit aus Models"


# ---------------------------------------------------------------------------
# RED 3 (Anti-Stale): atomic in Model/truths/ "NEU" UND repo-Kopie "ALT-REPO"
# -> atomic gewinnt (source=atomic), NICHT der stale repo-Read.
# ---------------------------------------------------------------------------
def test_atomic_Model_beats_repo_anti_stale(tmp_path):
    bl = tmp_path / "BL-041-foo"
    _mk_truth(bl / "Model" / "truths", "W1", "NEU", tid="BL-041.W1")
    repo = tmp_path / "claude_models"
    repo.mkdir()
    (repo / "Meta_Model.md").write_text("### W1\nALT-REPO.\n", encoding="utf-8")
    r = tr.resolve("W1", bl_folder=bl, repo_models=repo)
    assert r.found
    assert r.source == tr.SOURCE_ATOMIC, (
        f"Praezedenz-Bruch: faellt faelschlich auf {r.source} statt atomic"
    )
    assert r.truth["text"] == "NEU", "stale repo-Kopie wurde gelesen statt atomic NEU"


# ---------------------------------------------------------------------------
# RED 4: legacy-scan ordner-agnostisch — Model/<X>Model.md mit HEADING, kein truths/
# -> source=legacy (nicht repo).
# ---------------------------------------------------------------------------
def test_legacy_scan_under_Model_singular(tmp_path):
    bl = tmp_path / "BL-041-foo"
    (bl / "Model").mkdir(parents=True)
    (bl / "Model" / "Foo_Model.md").write_text(
        "# Model\n\n### W2\nLegacy Body unter Model.\n\n### W3\nAndere.\n",
        encoding="utf-8",
    )
    r = tr.resolve("W2", bl_folder=bl)
    assert r.found, "W2 legacy unter Model/ muss aufloesbar sein"
    assert r.source == tr.SOURCE_LEGACY, f"erwartet legacy, war {r.source}"
    assert "Legacy Body unter Model." in r.truth["text"]
    assert "Andere" not in r.truth["text"]


# ---------------------------------------------------------------------------
# RED 5: bl_folder IST direkt der Model-Ordner (truths/ direkt darunter)
# -> source=atomic.
# ---------------------------------------------------------------------------
def test_atomic_when_bl_folder_is_model_dir(tmp_path):
    model_dir = tmp_path / "OmniCommand"
    _mk_truth(model_dir / "truths", "W1", "Direkt-Model-Ordner", tid="OC.W1")
    r = tr.resolve("W1", bl_folder=model_dir)
    assert r.found, "W1 unter {bl_folder}/truths/ (bl == model dir) muss aufloesbar sein"
    assert r.source == tr.SOURCE_ATOMIC, f"erwartet atomic, war {r.source}"
    assert r.truth["text"] == "Direkt-Model-Ordner"


# ---------------------------------------------------------------------------
# GRUEN-Regression: klassisch 2_Model/truths/ bleibt atomic (kein Rueckschritt)
# ---------------------------------------------------------------------------
def test_regression_2Model_truths_still_atomic(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W1", "Klassisch 2_Model", tid="BL-x.W1")
    r = tr.resolve("W1", bl_folder=bl)
    assert r.found and r.source == tr.SOURCE_ATOMIC
    assert r.truth["text"] == "Klassisch 2_Model"


# ---------------------------------------------------------------------------
# GRUEN-Regression: klassisch 2_Model/<X>Model.md legacy bleibt legacy
# ---------------------------------------------------------------------------
def test_regression_2Model_legacy_still_legacy(tmp_path):
    bl = tmp_path / "BL-x"
    (bl / "2_Model").mkdir(parents=True)
    (bl / "2_Model" / "Foo_Model.md").write_text(
        "### W5\nKlassisch legacy.\n### W6\nNext.\n", encoding="utf-8"
    )
    r = tr.resolve("W5", bl_folder=bl)
    assert r.found and r.source == tr.SOURCE_LEGACY
    assert "Klassisch legacy." in r.truth["text"]


# ---------------------------------------------------------------------------
# GRUEN-Regression: echtes not_found bleibt laut (kein falsch-positiv durch neue Scans)
# ---------------------------------------------------------------------------
def test_regression_not_found_stays_loud(tmp_path):
    bl = tmp_path / "BL-empty"
    bl.mkdir()
    r = tr.resolve("W42", bl_folder=bl)
    assert not r.found and r.source == tr.SOURCE_NOT_FOUND
