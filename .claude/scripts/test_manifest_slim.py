#!/usr/bin/env python3
"""Tests fuer manifest_slim.py (BL-229 AK-A/A1/C/CTX-1).

M3-TDD: schreibt zuerst RED (Modul existiert nicht), dann minimaler GREEN.
Deckt die 3 Gates (lossless / currentStatePresent / missing=leer), den
require_quiescent-Pre-Gate-Call (AK-A1), den offload_history MD5-lossless
(AK-C) und den Zweck-Header (AK-CTX-1) ab.
"""
import hashlib

import pytest

import manifest_slim
from manifest_slim import (
    PURPOSE_HEADER_MARKER,
    map_rounds,
    offload_history,
    slim_manifest,
    verify_split,
)


# ── Fixtures: synthetisches Manifest mit Working-Set + Garbage-Rounds ──
# Round-Identitaet im 486-Stil: `## FAMILY (... Round N / vN-orphan ...)` Header.
WORKING_SET_MARKER = "items_routed_ready: 7"  # Live-Marker der LETZTEN Round

BLOATED_MANIFEST = """\
---
bl_id: BL-TEST
type: manifest
---

## IDF_PIPELINE_STATE (recluster v6-orphan, 2026-06-05 — Round 6)
phase: idf_done
items: 3

## BERATER_OUTPUTS.modelSync (recluster v6-orphan, 2026-06-05 — Round 6)
status: done
note: alte runde 6

## IDF_PIPELINE_STATE (recluster v8-orphan, 2026-06-09 — Round 8)
phase: idf_done
items: 5
items_routed_ready: 7

## BERATER_OUTPUTS.modelSync (recluster v8-orphan, 2026-06-09 — Round 8)
status: done
note: aktuelle runde 8

## BL_LIFECYCLE_STATE
status: in_progress
"""


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


@pytest.fixture
def manifest_file(tmp_path):
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")
    return m


# ── MAP: Rounds erkennen, letzte Round = Working-Set (AK-A, T2) ──
def test_map_groups_rounds_per_family():
    rounds = map_rounds(BLOATED_MANIFEST)
    # Mind. die zwei Familien mit je 2 Round-Instanzen erkannt
    assert "IDF_PIPELINE_STATE" in rounds
    assert "BERATER_OUTPUTS.modelSync" in rounds
    assert len(rounds["IDF_PIPELINE_STATE"]) == 2


def test_map_last_round_is_working_set():
    rounds = map_rounds(BLOATED_MANIFEST)
    # Die hoechste Round-Instanz je Familie ist Working-Set (round 8 > round 6)
    idf = rounds["IDF_PIPELINE_STATE"]
    working = [b for b in idf if b.is_working_set]
    garbage = [b for b in idf if not b.is_working_set]
    assert len(working) == 1
    assert len(garbage) == 1
    assert "Round 8" in working[0].header


# ── VERIFY: 3 Gates isoliert (AK-A, T1) ──
def test_gate_lossless_passes_when_archive_plus_kept_equals_original():
    ok, report = verify_split(
        original=BLOATED_MANIFEST,
        kept="A\nB\n",
        archived="C\nD\n",
        archive_md5=_md5("C\nD\n"),
    )
    assert report["lossless"] is True


def test_gate_lossless_fails_on_archive_corruption():
    ok, report = verify_split(
        original=BLOATED_MANIFEST,
        kept="A\n",
        archived="C\n",
        archive_md5="deadbeef",  # falscher MD5 -> Datenverlust-Verdacht
    )
    assert ok is False
    assert report["lossless"] is False


def test_gate_current_state_present_passes():
    kept = "## IDF_PIPELINE_STATE (Round 8)\nitems_routed_ready: 7\n"
    ok, report = verify_split(
        original=BLOATED_MANIFEST,
        kept=kept,
        archived="",
        archive_md5=_md5(""),
        live_markers=[WORKING_SET_MARKER],
    )
    assert report["currentStatePresent"] is True


def test_gate_current_state_present_fails_when_live_marker_dropped():
    kept = "## IDF_PIPELINE_STATE (Round 6)\nold stuff\n"  # Round-8-Marker fehlt
    ok, report = verify_split(
        original=BLOATED_MANIFEST,
        kept=kept,
        archived="",
        archive_md5=_md5(""),
        live_markers=[WORKING_SET_MARKER],
    )
    assert ok is False
    assert report["currentStatePresent"] is False


def test_gate_missing_empty_passes_when_nothing_lost():
    ok, report = verify_split(
        original="X\nY\nZ\n",
        kept="X\nY\n",
        archived="Z\n",
        archive_md5=_md5("Z\n"),
    )
    assert report["missing"] == []


def test_gate_missing_detects_lost_line():
    # 'Y' weder in kept noch archived -> Verlust
    ok, report = verify_split(
        original="X\nY\nZ\n",
        kept="X\n",
        archived="Z\n",
        archive_md5=_md5("Z\n"),
    )
    assert ok is False
    assert "Y" in report["missing"]


# ── offload_history MD5-lossless (AK-C, T7) ──
def test_offload_history_writes_archive(tmp_path):
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")
    result = offload_history(BLOATED_MANIFEST, manifest_path=m)
    archive_path = result["archive_path"]
    assert archive_path.exists()
    # Round-6-Garbage steht im Archiv
    assert "alte runde 6" in archive_path.read_text(encoding="utf-8")


def test_offload_history_md5_lossless(tmp_path):
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")
    result = offload_history(BLOATED_MANIFEST, manifest_path=m)
    # Das verzeichnete archive_md5 stimmt mit dem realen Archiv-Inhalt ueberein
    archived_text = result["archived"]
    assert result["archive_md5"] == _md5(archived_text)
    assert _md5(result["archive_path"].read_text(encoding="utf-8")) is not None


# ── require_quiescent Pre-Gate-Call (AK-A1, T4) ──
def test_slim_aborts_when_not_quiescent(tmp_path, monkeypatch):
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")

    called = {"flag": False}

    def fake_require(*a, **kw):
        called["flag"] = True
        raise RuntimeError("[QUIESCENCE-GATE] fremde Lock")

    monkeypatch.setattr(manifest_slim, "require_quiescent", fake_require)
    before = m.read_text(encoding="utf-8")
    with pytest.raises(RuntimeError, match="QUIESCENCE-GATE"):
        slim_manifest("BL-TEST", manifest_path=m)
    # Pre-Gate wurde aufgerufen UND kein Byte veraendert
    assert called["flag"] is True
    assert m.read_text(encoding="utf-8") == before


def test_slim_calls_quiescent_before_any_write(tmp_path, monkeypatch):
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")
    order = []
    monkeypatch.setattr(manifest_slim, "require_quiescent",
                        lambda *a, **kw: order.append("quiescent") or True)
    slim_manifest("BL-TEST", manifest_path=m)
    assert order and order[0] == "quiescent"


# ── slim end-to-end: Working-Set bleibt, Garbage ausgelagert (AK-A) ──
def test_slim_keeps_working_set_drops_garbage(tmp_path, monkeypatch):
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    result = slim_manifest("BL-TEST", manifest_path=m)
    slimmed = m.read_text(encoding="utf-8")
    # Round-8-Working-Set (Live-Marker) bleibt; Round-6-Garbage weg
    assert WORKING_SET_MARKER in slimmed
    assert "alte runde 6" not in slimmed
    assert result["gates"]["lossless"] is True
    assert result["gates"]["currentStatePresent"] is True
    assert result["gates"]["missing"] == []


def test_slim_dry_run_writes_nothing(tmp_path, monkeypatch):
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    before = m.read_text(encoding="utf-8")
    slim_manifest("BL-TEST", manifest_path=m, dry_run=True)
    assert m.read_text(encoding="utf-8") == before


# ── Zweck-Header (AK-CTX-1, DoD-11) ──
def test_slim_writes_purpose_header(tmp_path, monkeypatch):
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    slim_manifest("BL-TEST", manifest_path=m)
    assert PURPOSE_HEADER_MARKER in m.read_text(encoding="utf-8")


# ── AK-CTX-3: kein manifest_gc-Import/-Call (Negativ-Constraint, DoD-12) ──
# Der Negativ-Constraint verbietet das BENUTZEN von manifest_gc.py (greedy block-span),
# NICHT die Erwaehnung als Provenance-Begruendung im Docstring. Pruefe darum auf echten
# Import/Call via AST statt auf das blosse Vorkommen des Strings.
def test_no_manifest_gc_dependency():
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(manifest_slim))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
    assert "manifest_gc" not in imported
    # auch kein dynamischer __import__("manifest_gc")
    assert "manifest_gc" not in manifest_slim.__dict__


# ── BL-336: Format-Version-Generations-Guard (Pre-Write, 4 Zweige) ──
# Der Guard liest VOR jedem Map/Write den Frontmatter-format_version (ist) +
# die Soll-Generation (resolve_format_version('manifest')) und entscheidet:
#   (1) soll is None        -> PROCEED (Dual-Read-Resilienz, fehlende Registry nie Crash)
#   (2) ist == soll         -> PROCEED (zustaendige Generation, normaler slim-Lauf)
#   (3) ist == 0 (Gen-0)    -> PROCEED + stderr-WARN (Gen-0-Policy, least-stall:
#       Stempelung noch nicht universal gewired; lossless-verify-Gate schuetzt interim)
#   (4) ist > 0, ist != soll -> SAFE-ABORT (kein Byte-Write); echte FREMD-Generation
#       (1944-Klasse) — nur explizit gestempelte fremde Gen, NICHT ungestempelte Alt-Struktur.
#
# GREEN-IMPORT-KONVENTION (verbindlich, damit GREEN konsistent baut):
#   In manifest_slim.py: `import resolve_format_version as rfv`
#   Guard nutzt: rfv.read_format_version(<frontmatter>) und rfv.resolve_format_version("manifest")
#   Monkeypatch-Anker in Tests: manifest_slim.rfv.read_format_version / .resolve_format_version
# Determinismus: die Soll-Quelle wird gepinnt (sonst cwd-abhaengig wie BL-335);
# require_quiescent wird durchgewunken, damit der Generations-Guard isoliert geprueft wird.


def _pin_soll(monkeypatch, value):
    """Pinnt die Soll-Generation (resolve_format_version('manifest')) deterministisch.

    RED-Phase-Bruecke: solange GREEN den `import resolve_format_version as rfv` noch
    nicht gebaut hat, existiert manifest_slim.rfv nicht. Dann legen wir ein Stub-Modul
    als Monkeypatch-Anker an (raising=False), damit die PROCEED-Tests heute schon gruen
    laufen (Guard fehlt -> proceed ist Default) und NUR der Abort-Test ROT bleibt.
    Nach GREEN trifft der Patch das echte rfv-Modul. (BL-336)
    """
    import types
    if not hasattr(manifest_slim, "rfv"):
        monkeypatch.setattr(manifest_slim, "rfv", types.ModuleType("rfv"), raising=False)
    monkeypatch.setattr(manifest_slim.rfv, "resolve_format_version",
                        lambda typ: value, raising=False)


STAMPED_MANIFEST = """\
---
bl_id: BL-TEST
type: manifest
format_version: 1
---

## IDF_PIPELINE_STATE (recluster v8-orphan, 2026-06-09 — Round 8)
phase: idf_done
items: 5
items_routed_ready: 7

## BL_LIFECYCLE_STATE
status: in_progress
"""

# Explizit gestempelte FREMDE Generation (ist=2, soll=1): der echte 1944-Klasse-Abort-Fall.
FOREIGN_STAMPED_MANIFEST = """\
---
bl_id: BL-TEST
type: manifest
format_version: 2
---

## IDF_PIPELINE_STATE (recluster v8-orphan, 2026-06-09 — Round 8)
phase: idf_done
items: 5
items_routed_ready: 7

## BL_LIFECYCLE_STATE
status: in_progress
"""


def test_slim_aborts_on_foreign_stamped_generation(tmp_path, monkeypatch):
    # AK-1 echter Abort-Fall (1944-Klasse): explizit gestempelte FREMDE Generation
    # (ist==2) + soll==1, keine registrierte Migration -> SAFE-ABORT statt Traceback,
    # KEIN Byte veraendert. (Ungestempelte Gen-0 proceedet — siehe Gen-0-Test.)
    m = tmp_path / "_manifest.md"
    m.write_text(FOREIGN_STAMPED_MANIFEST, encoding="utf-8")  # format_version: 2 (fremd)
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    _pin_soll(monkeypatch, 1)

    before = m.read_text(encoding="utf-8")
    with pytest.raises(RuntimeError):
        slim_manifest("BL-TEST", manifest_path=m)
    # SAFE-ABORT: kein partieller / destruktiver Write am Manifest.
    assert m.read_text(encoding="utf-8") == before


def test_slim_proceeds_on_unstamped_gen0(tmp_path, monkeypatch):
    # Gen-0-Policy (least-stall): ungestempeltes Manifest (ist==0) + soll==1
    # -> PROCEED (kein RuntimeError; Working-Set ueberlebt) + WARN auf stderr.
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")  # KEIN format_version
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    _pin_soll(monkeypatch, 1)

    result = slim_manifest("BL-TEST", manifest_path=m)
    slimmed = m.read_text(encoding="utf-8")
    assert WORKING_SET_MARKER in slimmed  # Working-Set ueberlebt (kein Abort)
    assert "alte runde 6" not in slimmed  # bestehendes Slim-Verhalten unveraendert
    assert result["gates"]["lossless"] is True


def test_slim_gen0_emits_stderr_warning(tmp_path, monkeypatch, capsys):
    # Gen-0-Proceed gibt eine WARN-Zeile auf stderr aus (Stempelungs-Empfehlung).
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")  # KEIN format_version
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    _pin_soll(monkeypatch, 1)

    slim_manifest("BL-TEST", manifest_path=m)
    err = capsys.readouterr().err
    assert "SLIM-GEN BL-336" in err and "Gen-0" in err


def test_slim_proceeds_on_current_generation(tmp_path, monkeypatch):
    # ist == soll (gestempelt format_version: 1, soll==1) -> PROCEED, slimt normal.
    m = tmp_path / "_manifest.md"
    m.write_text(STAMPED_MANIFEST, encoding="utf-8")
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    _pin_soll(monkeypatch, 1)

    result = slim_manifest("BL-TEST", manifest_path=m)
    slimmed = m.read_text(encoding="utf-8")
    assert WORKING_SET_MARKER in slimmed  # Working-Set ueberlebt
    assert result["gates"]["lossless"] is True


def test_slim_proceeds_when_no_registry(tmp_path, monkeypatch):
    # soll is None (Registry nicht aufloesbar) -> PROCEED (Dual-Read-Resilienz);
    # ungestempeltes Manifest darf NICHT crashen/abbrechen wenn keine Soll-Gen existiert.
    m = tmp_path / "_manifest.md"
    m.write_text(BLOATED_MANIFEST, encoding="utf-8")  # KEIN format_version
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    _pin_soll(monkeypatch, None)

    result = slim_manifest("BL-TEST", manifest_path=m)
    slimmed = m.read_text(encoding="utf-8")
    assert WORKING_SET_MARKER in slimmed
    assert "alte runde 6" not in slimmed  # bestehendes Slim-Verhalten unveraendert


def test_slim_abort_message_names_generations(tmp_path, monkeypatch):
    # Die SAFE-ABORT-Meldung benennt erkannte (ist) UND erwartete (soll) Generation.
    # Echter Abort-Fall = gestempelte FREMD-Generation (ist=2, soll=1).
    m = tmp_path / "_manifest.md"
    m.write_text(FOREIGN_STAMPED_MANIFEST, encoding="utf-8")  # format_version: 2 (fremd)
    monkeypatch.setattr(manifest_slim, "require_quiescent", lambda *a, **kw: True)
    _pin_soll(monkeypatch, 1)

    with pytest.raises(RuntimeError) as exc:
        slim_manifest("BL-TEST", manifest_path=m)
    msg = str(exc.value)
    assert "2" in msg and "1" in msg  # erkannte Gen=2, erwartete Gen=1
