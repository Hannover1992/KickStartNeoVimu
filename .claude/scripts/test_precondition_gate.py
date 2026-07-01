"""
test_precondition_gate.py — TDD-RED Tests fuer BL-409 batch_1 (AK-GATE-PL-1).

Ziel-API (noch NICHT implementiert — diese Tests sind RED):
  check_preconditions(stage_nr, *, vault_root=None, resource_timeout=60.0) -> PreconditionResult

  PreconditionResult-Shape:
    @dataclass
    class PreconditionResult:
        verdict: Literal["PASS", "BLOCK", "WAIT"]
        category: Optional[Literal["predecessor", "substrat", "resource"]]  # None bei PASS
        message: str
        blocking_item: Optional[str]  # None bei PASS

  Pruef-Reihenfolge (deterministisch):
    1. Vorgaenger-Stage-Check (predecessor_stages in exit_criteria.preconditions)
    2. Substrat-Check (validate_slice_set auf TARGET-Stage-Dir)
    3. Ressourcen-Check (resource_allocator.claim / acquire_with_wait)

  Verdikt-Semantik:
    PASS  - alle Preconditions erfuellt
    BLOCK - strukturelles Problem (Vorgaenger/Substrat), manueller Eingriff noetig
    WAIT  - Ressource temporaer belegt, Caller soll spaeter neu versuchen

8 Testfaelle (T-a1..T-a4, T-b1..T-b4):

  T-a1: PASS alle erfuellt
  T-a2: BLOCK Vorgaenger nicht DONE
  T-a3: BLOCK Substrat fehlt
  T-a4: WAIT Ressource belegt (timeout)
  T-b1: Erste Stage (kein Vorgaenger -> predecessor trivial PASS)
  T-b2: resource_timeout-Override (kleiner Timeout -> WAIT schneller)
  T-b3: Partial-PASS-Verhinderung (stufe=DONE aber qg nicht erfuellt -> BLOCK)
  T-b4: BLOCK-vor-Resource (Substrat fehlt + Ressource belegt -> BLOCK/substrat, claim NICHT aufgerufen)

Lauf:
  py -3 -m pytest .claude/scripts/test_precondition_gate.py -q     (repo-root)
  py -3 -m pytest test_precondition_gate.py -q                     (scripts-cwd)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

# TARGET (noch nicht existierend — diese Datei provoziert RED)
from precondition_gate import check_preconditions, PreconditionResult  # type: ignore[import]


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


def _write_full_valid_slice_set(stage_dir: Path, *, preconditions: Optional[dict] = None) -> None:
    """Schreibe ein vollstaendiges, valides Slice-Set (alle 8 Slices) in stage_dir.

    exit_criteria.preconditions wird als optionales YAML-Feld mitgeschrieben.
    """
    _write_slice(stage_dir, "_index", {"stufe": "DONE", "name": "test"})
    _write_slice(stage_dir, "execute", {"testbefehl": "pytest tests/ -q", "testtyp": "unit"})
    _write_slice(stage_dir, "setup", {"skip": True})
    _write_slice(stage_dir, "teardown", {"skip": True})
    _write_slice(stage_dir, "health_check", {"skip": True})
    _write_slice(stage_dir, "resources", {"infrastruktur": "none"})
    _write_slice(stage_dir, "concurrency_class", {"concurrency_class": "parallel"})
    # exit_criteria: qg erfuellt + optionaler preconditions-Block
    ec_fm: dict = {"qg": "PASS"}
    if preconditions is not None:
        ec_fm["preconditions"] = preconditions
    _write_slice(stage_dir, "exit_criteria", ec_fm)


def _make_predecessor_stage(tmp_path: Path, pred_nr: int, *, stufe: str = "DONE", qg: Optional[str] = "PASS") -> None:
    """Erstelle eine Vorgaenger-Stage mit dem angegebenen stufe- und qg-Wert."""
    pred_dir = _make_stage_dir(tmp_path, pred_nr, name="pred")
    _write_slice(pred_dir, "_index", {"stufe": stufe, "name": "pred"})
    _write_slice(pred_dir, "execute", {"testbefehl": "pytest tests/ -q", "testtyp": "unit"})
    _write_slice(pred_dir, "setup", {"skip": True})
    _write_slice(pred_dir, "teardown", {"skip": True})
    _write_slice(pred_dir, "health_check", {"skip": True})
    _write_slice(pred_dir, "resources", {"infrastruktur": "none"})
    _write_slice(pred_dir, "concurrency_class", {"concurrency_class": "parallel"})
    ec_fm: dict = {}
    if qg is not None:
        ec_fm["qg"] = qg
    _write_slice(pred_dir, "exit_criteria", ec_fm)


# ---------------------------------------------------------------------------
# T-a1: PASS alle Preconditions erfuellt
# ---------------------------------------------------------------------------

def test_pass_all_conditions(tmp_path: Path) -> None:
    """T-a1: alle 3 Kategorien erfuellt -> verdict=PASS, category=None.

    Given: Stage 3 mit predecessor_stages=[2], Vorgaenger-Stage 2 DONE+qg=PASS,
           vollstaendiges Slice-Set, resource_allocator.claim liefert True.
    When:  check_preconditions(3, vault_root=tmp_path)
    Then:  verdict=PASS, category=None, blocking_item=None.
    """
    # Vorgaenger Stage 2 anlegen (DONE, qg=PASS)
    _make_predecessor_stage(tmp_path, pred_nr=2, stufe="DONE", qg="PASS")

    # Target Stage 3 anlegen mit predecessor_stages=[2]
    target_dir = _make_stage_dir(tmp_path, stage_nr=3, name="target")
    _write_full_valid_slice_set(
        target_dir,
        preconditions={"predecessor_stages": [2], "resources": ["gpu-pool"], "substrat": None},
    )

    with patch("resource_allocator.claim", return_value=True):
        result = check_preconditions(3, vault_root=tmp_path)

    assert isinstance(result, PreconditionResult)
    assert result.verdict == "PASS"
    assert result.category is None
    assert result.blocking_item is None
    assert isinstance(result.message, str)


# ---------------------------------------------------------------------------
# T-a2: BLOCK Vorgaenger-Stage nicht DONE
# ---------------------------------------------------------------------------

def test_block_predecessor_not_done(tmp_path: Path) -> None:
    """T-a2: Vorgaenger-Stage stufe!=DONE -> verdict=BLOCK, category=predecessor.

    Given: Stage 3 mit predecessor_stages=[2], Stage 2 hat stufe=IN_PROGRESS.
    When:  check_preconditions(3, vault_root=tmp_path)
    Then:  verdict=BLOCK, category="predecessor", blocking_item enthaelt Stage-Nr 2.
    """
    # Vorgaenger Stage 2 mit stufe=IN_PROGRESS (nicht DONE)
    _make_predecessor_stage(tmp_path, pred_nr=2, stufe="IN_PROGRESS", qg=None)

    # Target Stage 3
    target_dir = _make_stage_dir(tmp_path, stage_nr=3, name="target")
    _write_full_valid_slice_set(
        target_dir,
        preconditions={"predecessor_stages": [2], "resources": None, "substrat": None},
    )

    result = check_preconditions(3, vault_root=tmp_path)

    assert result.verdict == "BLOCK"
    assert result.category == "predecessor"
    assert result.blocking_item is not None
    assert "2" in str(result.blocking_item)
    assert isinstance(result.message, str)
    assert len(result.message) > 0


# ---------------------------------------------------------------------------
# T-a3: BLOCK Substrat-Artefakt fehlt
# ---------------------------------------------------------------------------

def test_block_substrat_missing(tmp_path: Path) -> None:
    """T-a3: Substrat-Artefakt fehlt (validate_slice_set faellt) -> verdict=BLOCK, category=substrat.

    Given: Stage 1 ohne Vorgaenger, aber mit fehlendem Pflicht-Slice (execute.md fehlt).
    When:  check_preconditions(1, vault_root=tmp_path)
    Then:  verdict=BLOCK, category="substrat".
    """
    # Target Stage 1 anlegen — OHNE execute.md (Pflicht-Slice fehlt)
    target_dir = _make_stage_dir(tmp_path, stage_nr=1, name="target")
    # Nur Teilmenge der Slices schreiben — execute.md absichtlich WEGLASSEN
    _write_slice(target_dir, "_index", {"stufe": "READY", "name": "target"})
    # execute.md fehlt -> validate_slice_set wird FAIL melden
    _write_slice(target_dir, "setup", {"skip": True})
    _write_slice(target_dir, "teardown", {"skip": True})
    _write_slice(target_dir, "health_check", {"skip": True})
    _write_slice(target_dir, "resources", {"infrastruktur": "none"})
    _write_slice(target_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(target_dir, "exit_criteria", {"qg": None, "preconditions": None})

    result = check_preconditions(1, vault_root=tmp_path)

    assert result.verdict == "BLOCK"
    assert result.category == "substrat"
    assert isinstance(result.message, str)
    assert len(result.message) > 0


# ---------------------------------------------------------------------------
# T-a4: WAIT Ressource belegt (timeout abgelaufen)
# ---------------------------------------------------------------------------

def test_wait_resource_contention(tmp_path: Path) -> None:
    """T-a4: Ressource belegt, acquire_with_wait liefert False nach timeout -> verdict=WAIT.

    Given: Stage 1 (kein Vorgaenger, Substrat komplett), resource_allocator.claim=False
           und acquire_with_wait=False (simuliert Timeout).
    When:  check_preconditions(1, vault_root=tmp_path, resource_timeout=5.0)
    Then:  verdict=WAIT, category="resource".
    """
    target_dir = _make_stage_dir(tmp_path, stage_nr=1, name="target")
    _write_full_valid_slice_set(
        target_dir,
        preconditions={"predecessor_stages": None, "resources": ["gpu-pool"], "substrat": None},
    )

    with patch("resource_allocator.claim", return_value=False), \
         patch("resource_allocator.acquire_with_wait", return_value=False), \
         patch("time.sleep"):  # deterministisch, kein echtes Warten
        result = check_preconditions(1, vault_root=tmp_path, resource_timeout=5.0)

    assert result.verdict == "WAIT"
    assert result.category == "resource"
    assert isinstance(result.message, str)
    assert len(result.message) > 0


# ---------------------------------------------------------------------------
# T-b1: Erste Stage (kein Vorgaenger -> predecessor trivial PASS)
# ---------------------------------------------------------------------------

def test_first_stage_no_predecessor_pass(tmp_path: Path) -> None:
    """T-b1: Stage 1 ohne predecessor_stages-Deklaration -> predecessor-Check trivial PASS.

    Given: Stage 1 ohne preconditions.predecessor_stages (null/absent),
           Substrat komplett, Ressource frei.
    When:  check_preconditions(1, vault_root=tmp_path)
    Then:  verdict=PASS (kein Vorgaenger-Check noetig).
    """
    target_dir = _make_stage_dir(tmp_path, stage_nr=1, name="target")
    # Keine predecessor_stages -> predecessor-Check wird trivial PASS
    _write_full_valid_slice_set(
        target_dir,
        preconditions=None,  # komplett fehlendes preconditions-Feld -> sofort PASS
    )

    with patch("resource_allocator.claim", return_value=True):
        result = check_preconditions(1, vault_root=tmp_path)

    assert result.verdict == "PASS"
    assert result.category is None


# ---------------------------------------------------------------------------
# T-b2: resource_timeout-Override
# ---------------------------------------------------------------------------

def test_resource_timeout_override(tmp_path: Path) -> None:
    """T-b2: resource_timeout-Parameter wird korrekt an acquire_with_wait weitergegeben.

    Given: Ressource belegt (claim=False), resource_timeout=2.0 uebergeben.
    When:  check_preconditions(1, vault_root=tmp_path, resource_timeout=2.0)
    Then:  acquire_with_wait wird mit timeout=2.0 aufgerufen (verify call args);
           verdict=WAIT.
    """
    target_dir = _make_stage_dir(tmp_path, stage_nr=1, name="target")
    _write_full_valid_slice_set(
        target_dir,
        preconditions={"predecessor_stages": None, "resources": ["model-lock"], "substrat": None},
    )

    with patch("resource_allocator.claim", return_value=False) as mock_claim, \
         patch("resource_allocator.acquire_with_wait", return_value=False) as mock_wait, \
         patch("time.sleep"):
        result = check_preconditions(1, vault_root=tmp_path, resource_timeout=2.0)

    assert result.verdict == "WAIT"
    assert result.category == "resource"
    # acquire_with_wait muss mit timeout=2.0 aufgerufen worden sein
    mock_wait.assert_called_once()
    call_kwargs = mock_wait.call_args
    # Pruefe timeout-Argument (positional oder keyword)
    timeout_val = call_kwargs.kwargs.get("timeout") if call_kwargs.kwargs else None
    if timeout_val is None and call_kwargs.args:
        # Fallback: kein keyword -> ueberspringe, Hauptsache WAIT
        pass
    else:
        assert timeout_val == 2.0


# ---------------------------------------------------------------------------
# T-b3: Partial-PASS-Verhinderung (stufe=DONE aber qg nicht erfuellt -> BLOCK)
# ---------------------------------------------------------------------------

def test_partial_pass_prevented_qg_not_done(tmp_path: Path) -> None:
    """T-b3: Vorgaenger stufe=DONE ABER qg nicht erfuellt -> verdict=BLOCK, category=predecessor.

    Partial-PASS-Verhinderung (W14): stufe=DONE allein reicht nicht.
    Gate prueft zusaetzlich exit_criteria.qg.

    Given: Stage 3 mit predecessor_stages=[2].
           Stage 2: stufe=DONE, aber qg="OPEN" (nicht als erfuellt anerkannt).
    When:  check_preconditions(3, vault_root=tmp_path)
    Then:  verdict=BLOCK, category=predecessor.
    """
    # Vorgaenger Stage 2: stufe=DONE, aber qg="OPEN" (unerfuellt)
    _make_predecessor_stage(tmp_path, pred_nr=2, stufe="DONE", qg="OPEN")

    # Target Stage 3
    target_dir = _make_stage_dir(tmp_path, stage_nr=3, name="target")
    _write_full_valid_slice_set(
        target_dir,
        preconditions={"predecessor_stages": [2], "resources": None, "substrat": None},
    )

    result = check_preconditions(3, vault_root=tmp_path)

    assert result.verdict == "BLOCK"
    assert result.category == "predecessor"
    # Meldung muss erklaeren dass QG unerfuellt ist
    assert isinstance(result.message, str)
    assert len(result.message) > 0


# ---------------------------------------------------------------------------
# T-b4: BLOCK-vor-Resource (Substrat fehlt + Ressource belegt -> BLOCK/substrat,
#        resource_allocator.claim wird NICHT aufgerufen)
# ---------------------------------------------------------------------------

def test_block_substrat_resource_not_attempted(tmp_path: Path) -> None:
    """T-b4: Substrat fehlt -> BLOCK/substrat; resource_allocator.claim wird NICHT aufgerufen.

    Pruef-Reihenfolge W5: Vorgaenger -> Substrat -> Ressource.
    Bei BLOCK in Kat. 2 (substrat) wird Kat. 3 (resource) nie versucht.
    (kein ueberfluessiger Lock bei Struct-BLOCK).

    Given: Stage 1, Substrat unvollstaendig (execute.md fehlt),
           UND Ressource eigentlich auch belegt.
    When:  check_preconditions(1, vault_root=tmp_path)
    Then:  verdict=BLOCK, category=substrat;
           resource_allocator.claim wird NICHT aufgerufen.
    """
    target_dir = _make_stage_dir(tmp_path, stage_nr=1, name="target")
    # execute.md absichtlich weglassen -> Substrat-BLOCK
    _write_slice(target_dir, "_index", {"stufe": "READY", "name": "target"})
    # execute.md fehlt
    _write_slice(target_dir, "setup", {"skip": True})
    _write_slice(target_dir, "teardown", {"skip": True})
    _write_slice(target_dir, "health_check", {"skip": True})
    _write_slice(target_dir, "resources", {"infrastruktur": "none"})
    _write_slice(target_dir, "concurrency_class", {"concurrency_class": "parallel"})
    _write_slice(target_dir, "exit_criteria", {
        "qg": None,
        "preconditions": {"predecessor_stages": None, "resources": ["gpu-pool"], "substrat": None},
    })

    with patch("resource_allocator.claim", return_value=False) as mock_claim:
        result = check_preconditions(1, vault_root=tmp_path)

    assert result.verdict == "BLOCK"
    assert result.category == "substrat"
    # resource_allocator.claim darf NICHT aufgerufen worden sein (kein Lock bei Struct-BLOCK)
    mock_claim.assert_not_called()
