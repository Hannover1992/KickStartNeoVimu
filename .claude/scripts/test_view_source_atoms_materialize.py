#!/usr/bin/env python3
"""RED tests fuer view_source_atoms_materialize.py (BL-460, Lane B).

STRICT TDD RED: dieses Modul testet die NOCH-NICHT-EXISTIERENDE Lane-B Batch-Tool
`view_source_atoms_materialize`. Ein separater GREEN-Worker implementiert die
Produktion (INV-BUILD-GRAIN: RED-Worker != GREEN-Worker).

Was das Tool tut (Contract BL-460_materializer_contract.md):
  Fuer jede substrate-habende View, die KEINE `source_atoms` hat, schreibt es die
  OWN-BL-Atome der View als `source_atoms:` + `## Verwandte Wahrheiten`-Wikilinks
  (`- Verwandt: [[<path>|md]]`). VIEW-FILES-ONLY, substrate-grounded, NIE fabriziert.
  Reuse-Primitive: wikilink_materializer.write_source_atoms + view_node_predicate.is_view_node.

API (exakt — Tests haengen daran):
  bl_of_view(view_path) -> str | None
  own_atoms_for_bl(bl, vault) -> list[str]        # sorted, vault-rel, forward-slash
  view_has_source_atoms(view_path) -> bool
  discover_targets(vault, *, parking_only=False) -> list[dict]
  materialize_view(view_path, vault, *, write) -> dict
  run(vault, *, write=False, parking_only=False) -> dict
  main(argv) -> int

RED-Beweis: `view_source_atoms_materialize` existiert NOCH NICHT. Der Top-Level-Import
schlaegt fehl -> pytest COLLECTION ERROR -> jeder Test ist RED. Das IST der RED-Zustand.
Der GREEN-Worker erstellt das Modul, ohne diese Tests zu editieren.
"""
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Harter Top-Level-Import: solange das Modul fehlt (RED-Phase) -> ImportError ->
# pytest meldet COLLECTION ERROR fuer die ganze Datei = RED. (Bare-Import-Stil
# wie die Sibling-Suiten; sys.path enthaelt SCRIPT_DIR.)
from view_source_atoms_materialize import (  # noqa: E402  (RED: Modul existiert noch nicht)
    bl_of_view,
    own_atoms_for_bl,
    view_has_source_atoms,
    discover_targets,
    materialize_view,
    run,
    main,
)

WIKILINK_HEADER = "## Verwandte Wahrheiten"


# ──────────────────────────────────────────────────────────────────────────────
# Synthetische Mini-Vault-Helfer (NIE der echte Vault; alles in tmp_path).
# ──────────────────────────────────────────────────────────────────────────────
def _atom_text(bl: str, local_id: str) -> str:
    return (
        "---\n"
        "type: truth\n"
        f"id: {bl}-{local_id}\n"
        f"local_id: {local_id}\n"
        "---\n"
        f"# {local_id}\n\nTruth body for {bl} {local_id}.\n"
    )


def _fm_source_atoms_lines(source_atoms):
    """Frontmatter-Zeilen fuer source_atoms: None=>keine, []=>'source_atoms: []',
    Liste=>Block."""
    if source_atoms is None:
        return []
    if len(source_atoms) == 0:
        return ["source_atoms: []"]
    out = ["source_atoms:"]
    for sa in source_atoms:
        out.append(f"  - {sa}")
    return out


def _view_text(typ: str, bl: str, source_atoms) -> str:
    lines = ["---", f"type: {typ}"]
    lines += _fm_source_atoms_lines(source_atoms)
    lines += ["---", f"# {bl} {typ}", "", "Some body content.", ""]
    return "\n".join(lines)


def _make_bl(vault: Path, num: str, slug: str, n_atoms: int, *,
             parking: bool = True, parking_sources=None,
             model_view: bool = False, model_sources=None) -> dict:
    """Lege `Backlog/BL-<num>-<slug>` an: n_atoms Truth-Atome unter 2_Model/truths/,
    optional eine Parking-View (6_PL/BL-<num>-parking-lot.md) und/oder Model-View
    (2_Model/<Slug>_Model.md). source_atoms vorseedbar via *_sources."""
    bl = f"BL-{num}"
    folder = vault / "Backlog" / f"{bl}-{slug}"
    truths_dir = folder / "2_Model" / "truths"
    truths_dir.mkdir(parents=True, exist_ok=True)
    atom_paths = []
    for i in range(1, n_atoms + 1):
        lid = f"W{i}"
        ap = truths_dir / f"{lid}.md"
        ap.write_text(_atom_text(bl, lid), encoding="utf-8")
        atom_paths.append(ap)
    info = {"bl": bl, "slug": slug, "folder": folder, "atoms": atom_paths}
    if parking:
        pl_dir = folder / "6_PL"
        pl_dir.mkdir(parents=True, exist_ok=True)
        pv = pl_dir / f"{bl}-parking-lot.md"
        pv.write_text(_view_text("parking_lot", bl, parking_sources), encoding="utf-8")
        info["parking"] = pv
    if model_view:
        mv = folder / "2_Model" / f"{slug.capitalize()}_Model.md"
        mv.write_text(_view_text("model", bl, model_sources), encoding="utf-8")
        info["model"] = mv
    return info


def _expected_own(bl: str, slug: str, n: int) -> list:
    return sorted(
        f"Backlog/{bl}-{slug}/2_Model/truths/W{i}.md" for i in range(1, n + 1)
    )


def _mtimes(paths) -> dict:
    """mtime_ns je Datei — der UNTOUCHED-Beweis fuer Atom-Dateien."""
    return {str(p): os.stat(p).st_mtime_ns for p in paths}


def _parse_source_atoms(text: str) -> list:
    """Extrahiere die source_atoms:-Block-Items (geschriebenes Format:
    `source_atoms:` + `  - <path>`) in Reihenfolge."""
    out = []
    capturing = False
    for line in text.splitlines():
        if not capturing:
            if line.rstrip() == "source_atoms:":
                capturing = True
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            out.append(stripped[2:].strip())
        else:
            break
    return out


def _build_run_vault(vault: Path):
    """2 Targets (BL-001 parking, BL-004 model) + 2 Nicht-Targets
    (BL-002 has-sources, BL-003 no-atoms)."""
    t1 = _make_bl(vault, "001", "alpha", 3)  # parking, keine sources -> TARGET
    _make_bl(vault, "002", "beta", 2,
             parking_sources=["Backlog/BL-002-beta/2_Model/truths/W1.md"])  # has sources -> raus
    _make_bl(vault, "003", "gamma", 0)  # 0 Atome -> raus
    t4 = _make_bl(vault, "004", "delta", 2, parking=False, model_view=True)  # model -> TARGET
    return t1, t4


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────
def test_own_atoms_sorted_relative_forwardslash(tmp_path):
    """own_atoms_for_bl: sortierte, vault-relative, forward-slash Truth-Pfade der
    BL; [] fuer eine BL ohne Atome."""
    _make_bl(tmp_path, "001", "alpha", 3)
    _make_bl(tmp_path, "002", "beta", 0)  # keine Atome

    got = own_atoms_for_bl("BL-001", tmp_path)
    expected = _expected_own("BL-001", "alpha", 3)
    assert got == expected, f"erwartet {expected}, war {got}"
    assert got == sorted(got), "Ergebnis muss sortiert sein"
    for p in got:
        assert "\\" not in p, f"forward-slash erwartet, Backslash in {p!r}"
        assert p.startswith("Backlog/"), f"vault-relativ erwartet, war {p!r}"
        assert ":" not in p, f"kein Drive-Letter / absoluter Pfad erlaubt: {p!r}"

    assert own_atoms_for_bl("BL-002", tmp_path) == [], \
        "BL ohne Truths -> [] erwartet"


def test_bl_of_view_extracts_and_none(tmp_path):
    """bl_of_view: extrahiert BL-001 aus einem Parking-View-Pfad; None bei Nicht-BL."""
    pv = tmp_path / "Backlog" / "BL-001-alpha" / "6_PL" / "BL-001-parking-lot.md"
    assert bl_of_view(pv) == "BL-001", "BL aus Parking-View-Pfad erwartet"
    assert bl_of_view(str(pv)) == "BL-001", "auch str-Form muss BL liefern"
    non_bl = tmp_path / "Docs" / "guide.md"
    assert bl_of_view(non_bl) is None, "Nicht-BL-Pfad -> None erwartet"


def test_view_has_source_atoms(tmp_path):
    """view_has_source_atoms: True bei nicht-leerer source_atoms-Liste,
    False bei abwesend ODER leer ([])."""
    no_src = _make_bl(tmp_path, "001", "alpha", 2)  # parking ohne sources
    assert view_has_source_atoms(no_src["parking"]) is False, \
        "abwesendes source_atoms -> False"

    with_src = _make_bl(
        tmp_path, "002", "beta", 2,
        parking_sources=["Backlog/BL-002-beta/2_Model/truths/W1.md"],
    )
    assert view_has_source_atoms(with_src["parking"]) is True, \
        "nicht-leeres source_atoms -> True"

    empty = tmp_path / "Backlog" / "BL-003-gamma" / "6_PL" / "BL-003-parking-lot.md"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text(_view_text("parking_lot", "BL-003", []), encoding="utf-8")
    assert view_has_source_atoms(empty) is False, "leeres source_atoms: [] -> False"


def test_view_has_source_atoms_realvault_formats(tmp_path):
    """REAL-VAULT-Formate (Verifier-Fund 2026-06-25): die existierenden ~140 Parking-
    Views schreiben source_atoms als UNINDENTIERTE Block-Sequence (`- item` auf Spalte 0,
    wie die Atom-keywords). Der erste Parser verlangte EINGERUECKTE Items -> 138 False-
    Negatives (haette 105 schon-besetzte Views ueberschrieben). Diese Faelle MUESSEN
    erkannt werden, sonst dupliziert/korrumpiert das Tool existierende Views."""
    def _pv(name, fm_sa_block):
        p = tmp_path / "Backlog" / f"BL-{name}-x" / "6_PL" / f"BL-{name}-parking-lot.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\ntype: parking_lot\n{fm_sa_block}\n---\n\n# body\n", encoding="utf-8")
        return p

    # 1) UNINDENTED block sequence (das echte Vault-Format) -> True
    unindented = _pv("900", "source_atoms:\n- Backlog/BL-051-x/Model/truths/W25.md\n- _meta_truths/X/truths/W16.md")
    assert view_has_source_atoms(unindented) is True, "unindentierte Block-Sequence -> True (echtes Vault-Format)"

    # 2) UNINDENTED mit nachfolgendem Feld (Block endet korrekt) -> True
    with_trailing = _pv("901", "source_atoms:\n- Backlog/BL-051-x/Model/truths/W25.md\nother_field: value")
    assert view_has_source_atoms(with_trailing) is True, "unindentiert + Folgefeld -> True"

    # 3) Inline-Flow-Liste -> True
    inline = _pv("902", "source_atoms: [Backlog/BL-051-x/Model/truths/W25.md]")
    assert view_has_source_atoms(inline) is True, "inline [a] -> True"

    # 4) leere Inline-Liste -> False (kein false-positive)
    assert view_has_source_atoms(_pv("903", "source_atoms: []")) is False, "[] -> False"


def test_discover_targets(tmp_path):
    """discover_targets: nimmt substrate-habende View OHNE source_atoms; schliesst
    has-sources-View und no-atoms-View aus; dict-Shape; parking_only-Filter."""
    _make_bl(tmp_path, "001", "alpha", 3)  # parking, keine sources -> TARGET
    _make_bl(tmp_path, "002", "beta", 2,
             parking_sources=["Backlog/BL-002-beta/2_Model/truths/W1.md"])  # has sources -> raus
    _make_bl(tmp_path, "003", "gamma", 0)  # 0 Atome -> raus
    _make_bl(tmp_path, "004", "delta", 2, parking=False, model_view=True)  # model -> TARGET

    targets = discover_targets(tmp_path)
    bls = {d["bl"] for d in targets}
    assert "BL-001" in bls, "substrate-habende Parking-View ohne sources MUSS Target sein"
    assert "BL-004" in bls, "substrate-habende Model-View ohne sources MUSS Target sein"
    assert "BL-002" not in bls, "View MIT source_atoms muss ausgeschlossen sein"
    assert "BL-003" not in bls, "View deren BL 0 Atome hat muss ausgeschlossen sein"

    d1 = next(d for d in targets if d["bl"] == "BL-001")
    for key in ("view", "rel", "bl", "own_atoms", "has_sources"):
        assert key in d1, f"Target-dict braucht Key {key!r}"
    assert isinstance(d1["view"], Path) and d1["view"].is_absolute(), \
        "view muss ein absoluter Path sein"
    assert d1["view"].exists(), "view muss existieren"
    assert d1["has_sources"] is False, "Target hat keine sources"
    assert d1["own_atoms"] == own_atoms_for_bl("BL-001", tmp_path), \
        "own_atoms im Target muss own_atoms_for_bl spiegeln"
    assert "BL-001-parking-lot.md" in d1["rel"].replace("\\", "/"), \
        "rel muss auf die Parking-View zeigen"

    parking_targets = discover_targets(tmp_path, parking_only=True)
    pbls = {d["bl"] for d in parking_targets}
    assert "BL-001" in pbls, "parking_only behaelt die /6_PL/-View"
    assert "BL-004" not in pbls, "parking_only schliesst die Model-View (nicht /6_PL/) aus"


def test_materialize_view_dryrun_writes_nothing(tmp_path):
    """materialize_view(write=False): liefert berechnete own_atoms (n_own_atoms>0),
    schreibt NICHTS — View-Bytes unveraendert, jede Atom-mtime_ns unveraendert."""
    t = _make_bl(tmp_path, "001", "alpha", 3)
    view = t["parking"]
    before_bytes = view.read_bytes()
    atom_mtimes = _mtimes(t["atoms"])

    res = materialize_view(view, tmp_path, write=False)
    assert res["action"] == "dry-run", f"action 'dry-run' erwartet, war {res.get('action')!r}"
    assert res["n_own_atoms"] == 3, f"n_own_atoms 3 erwartet, war {res.get('n_own_atoms')!r}"

    assert view.read_bytes() == before_bytes, "DRY-RUN darf die View-Datei NICHT aendern"
    assert _mtimes(t["atoms"]) == atom_mtimes, "DRY-RUN darf Atom-mtime_ns NICHT aendern"


def test_materialize_view_write_sets_sources_and_wikilinks(tmp_path):
    """materialize_view(write=True): View hat danach source_atoms == own-BL-Atome
    (Reihenfolge own_atoms_for_bl) + ## Verwandte Wahrheiten-Wikilinks;
    Atom-Dateien UNTOUCHED (mtime_ns); action == 'written'."""
    t = _make_bl(tmp_path, "001", "alpha", 3)
    view = t["parking"]
    atom_mtimes = _mtimes(t["atoms"])
    expected = own_atoms_for_bl("BL-001", tmp_path)

    res = materialize_view(view, tmp_path, write=True)
    assert res["action"] == "written", f"action 'written' erwartet, war {res.get('action')!r}"
    assert res["n_own_atoms"] == 3

    text = view.read_text(encoding="utf-8")
    assert _parse_source_atoms(text) == expected, \
        "source_atoms muss exakt == own_atoms_for_bl (gleiche Reihenfolge) sein"
    assert WIKILINK_HEADER in text, "## Verwandte Wahrheiten-Sektion fehlt"
    for p in expected:
        assert f"- Verwandt: [[{p}|md]]" in text, f"Wikilink fuer {p} fehlt"
    assert _mtimes(t["atoms"]) == atom_mtimes, "WRITE darf Atom-mtime_ns NICHT aendern"


def test_materialize_view_skips_malformed_frontmatter(tmp_path):
    """SAFETY (Verifier-Fund 2026-06-26): viele echte Model/arc42-Views sind VOR-
    KORRUMPIERT — sie starten NICHT mit einem sauberen `---`-Frontmatter, sondern mit
    verirrten `source_atoms:`-Bloecken oder einem BOM. write_source_atoms findet dann
    kein Frontmatter und HAENGT einen weiteren verirrten Block oben an -> verschlimmert
    die Korruption. materialize_view MUSS solche Views SKIPpen (action 'skip',
    reason malformed/no_clean_frontmatter) und die Datei BYTE-IDENTISCH lassen — auch
    bei write=True. Nur Views mit sauberem `---`-Frontmatter (Byte 0) werden geschrieben."""
    # BL mit Substrat, aber die View ist vor-korrumpiert (startet mit verirrtem Block).
    folder = tmp_path / "Backlog" / "BL-001-alpha"
    truths = folder / "2_Model" / "truths"
    truths.mkdir(parents=True)
    for i in (1, 2):
        (truths / f"W{i}.md").write_text(
            f"---\ntype: truth\nid: NS.W{i}\nlocal_id: W{i}\n---\nA{i}\n", encoding="utf-8"
        )
    pl = folder / "6_PL"
    pl.mkdir()
    view = pl / "BL-001-parking-lot.md"
    # vor-korrumpiert: verirrter source_atoms-Block + BOM VOR dem echten Frontmatter
    malformed = (
        "source_atoms:\n  - _meta_truths/X/truths/Wstray.md\n"
        "﻿---\ntype: parking_lot\n---\n\n# body\n"
    )
    view.write_text(malformed, encoding="utf-8")
    before = view.read_bytes()

    res = materialize_view(view, tmp_path, write=True)
    assert res["action"] == "skip", f"malformed view muss SKIP sein, war {res.get('action')!r}"
    assert "malformed" in (res.get("reason") or "") or "frontmatter" in (res.get("reason") or ""), \
        f"reason soll die malformed-Ursache nennen, war {res.get('reason')!r}"
    assert view.read_bytes() == before, "malformed view MUSS byte-identisch bleiben (kein Schreiben)"


def test_materialize_view_idempotent(tmp_path):
    """Zweiter write -> keine Aenderung (action 'idempotent' oder n_added==0);
    View-Bytes nach 1. und 2. Lauf gleich."""
    t = _make_bl(tmp_path, "001", "alpha", 2)
    view = t["parking"]

    res1 = materialize_view(view, tmp_path, write=True)
    assert res1["action"] == "written"
    after_first = view.read_bytes()

    res2 = materialize_view(view, tmp_path, write=True)
    assert res2["action"] == "idempotent" or res2.get("n_added") == 0, \
        f"2. write muss idempotent sein, war {res2!r}"
    after_second = view.read_bytes()
    assert after_first == after_second, "View-Bytes muessen nach 2. write identisch sein"


def test_materialize_view_skip_no_substrate(tmp_path):
    """materialize_view auf View deren BL 0 Atome hat -> action 'skip', schreibt nichts."""
    t = _make_bl(tmp_path, "003", "gamma", 0)  # parking, 0 Atome
    view = t["parking"]
    before = view.read_bytes()

    res = materialize_view(view, tmp_path, write=True)
    assert res["action"] == "skip", f"action 'skip' erwartet, war {res.get('action')!r}"
    assert res["n_own_atoms"] == 0, "keine own atoms erwartet"
    assert view.read_bytes() == before, "skip darf nichts schreiben"


def test_run_dryrun_and_write(tmp_path):
    """run(write=False) -> {targets, written:0, dry_run:True, results:[...]} + nichts
    geschrieben. run(write=True) -> alle Targets geschrieben, Atom-Dateien UNTOUCHED."""
    t1, t4 = _build_run_vault(tmp_path)
    all_atoms = t1["atoms"] + t4["atoms"]
    atom_mtimes = _mtimes(all_atoms)
    v1_before = t1["parking"].read_bytes()
    v4_before = t4["model"].read_bytes()

    r = run(tmp_path, write=False)
    assert r["dry_run"] is True, "dry_run True erwartet"
    assert r["written"] == 0, "dry-run darf 0 schreiben"
    assert r["targets"] == 2, f"2 Targets erwartet, war {r.get('targets')!r}"
    assert isinstance(r["results"], list), "results muss eine Liste sein"
    assert t1["parking"].read_bytes() == v1_before, "dry-run aenderte Parking-View"
    assert t4["model"].read_bytes() == v4_before, "dry-run aenderte Model-View"
    assert _mtimes(all_atoms) == atom_mtimes, "dry-run aenderte Atom-mtimes"

    r2 = run(tmp_path, write=True)
    assert r2["dry_run"] is False, "write -> dry_run False"
    assert r2["targets"] == 2
    assert r2["written"] == 2, f"2 geschrieben erwartet, war {r2.get('written')!r}"
    assert view_has_source_atoms(t1["parking"]) is True, "Parking-View muss source_atoms haben"
    assert view_has_source_atoms(t4["model"]) is True, "Model-View muss source_atoms haben"
    assert _mtimes(all_atoms) == atom_mtimes, "write aenderte Atom-mtimes"


def test_main_dryrun_writes_nothing(tmp_path):
    """main(['--vault', v]) (Default DRY-RUN) -> 0 und schreibt nichts."""
    t1, t4 = _build_run_vault(tmp_path)
    all_atoms = t1["atoms"] + t4["atoms"]
    atom_mtimes = _mtimes(all_atoms)
    v1 = t1["parking"].read_bytes()
    v4 = t4["model"].read_bytes()

    rc = main(["--vault", str(tmp_path)])
    assert rc == 0, f"exit 0 erwartet, war {rc}"
    assert t1["parking"].read_bytes() == v1, "main dry-run aenderte Parking-View"
    assert t4["model"].read_bytes() == v4, "main dry-run aenderte Model-View"
    assert _mtimes(all_atoms) == atom_mtimes, "main dry-run aenderte Atom-mtimes"


def test_main_write_materializes(tmp_path):
    """main(['--vault', v, '--write']) -> 0, materialisiert; Atom-Dateien UNTOUCHED."""
    t1, t4 = _build_run_vault(tmp_path)
    atom_mtimes = _mtimes(t1["atoms"] + t4["atoms"])

    rc = main(["--vault", str(tmp_path), "--write"])
    assert rc == 0, f"exit 0 erwartet, war {rc}"
    assert view_has_source_atoms(t1["parking"]) is True
    assert view_has_source_atoms(t4["model"]) is True
    assert _mtimes(t1["atoms"] + t4["atoms"]) == atom_mtimes, "main write aenderte Atom-mtimes"


def test_main_out_report_json(tmp_path):
    """main(['--vault', v, '--out', report]) schreibt einen JSON-Report."""
    _build_run_vault(tmp_path)
    report = tmp_path / "report.json"

    rc = main(["--vault", str(tmp_path), "--out", str(report)])
    assert rc == 0, f"exit 0 erwartet, war {rc}"
    assert report.exists(), "JSON-Report-Datei muss existieren"
    data = json.loads(report.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Report muss valides JSON-Objekt sein"


# ══════════════════════════════════════════════════════════════════════════════
# BL-491 follow-on — `--ensure-frontmatter` mode (RED-Phase, NOCH-NICHT-implementiert).
#
# Diese Klassen testen NEUE, NOCH-NICHT-EXISTIERENDE API in
# view_source_atoms_materialize:
#     _view_classify_type, _view_feature, _minimal_frontmatter_block,
#     _is_frontmatter_less, _create_minimal_frontmatter
#     + neuer keyword-only Param materialize_view(..., ensure_frontmatter=False)
#     + run(..., ensure_frontmatter=False) + main-Flag --ensure-frontmatter.
#
# RED-Beweis-Mechanik: Wir greifen NICHT ueber den Top-Level
# `from view_source_atoms_materialize import (...)` (existierende API) auf die neuen
# Namen zu — das wuerde den Import sprengen -> COLLECTION ERROR -> faelschlich auch
# die BESTEHENDEN Tests RED. Stattdessen via Modul-Alias `vsam`: fehlende Funktionen
# -> AttributeError, fehlender Param/Flag -> TypeError/SystemExit = RED, NUR fuer die
# neuen Tests. Der GREEN-Worker implementiert; diese Tests werden NICHT editiert.
# ══════════════════════════════════════════════════════════════════════════════
import view_source_atoms_materialize as vsam  # noqa: E402  (Modul existiert; neue Namen NICHT)

# Shape-B frontmatter-less Body (BYTES, explizit CRLF) + ein NOCH-korrupter
# (stray-prefix) Fixture-Body. In BYTES, weil frontmatter-less/korrupt byte-genau sind.
_FM_LESS_BODY = b"# BL-365 Parking Lot\r\n\r\ncontent\r\n"
_CORRUPT_STRAY = (
    b"source_atoms:\r\n  - Backlog/BL-050/Model/truths/W17.md\r\n# Heading\r\n"
)


def _make_fm_less_view_with_substrate(vault: Path, num: str = "777",
                                      slug: str = "omega") -> dict:
    """Echtes tmp-Vault: ein frontmatter-loser View-Node
    `Backlog/BL-<num>-<slug>/6_PL/BL-<num>-<slug>-parking-lot.md` (body-only, CRLF)
    + Substrat-Atom unter `Backlog/BL-<num>-<slug>/2_Model/truths/W1.md`, damit
    own_atoms_for_bl("BL-<num>") NICHT leer ist. Gibt {bl, view, atom, body}."""
    bl = f"BL-{num}"
    folder = vault / "Backlog" / f"{bl}-{slug}"
    truths = folder / "2_Model" / "truths"
    truths.mkdir(parents=True, exist_ok=True)
    atom = truths / "W1.md"
    atom.write_text(_atom_text(bl, "W1"), encoding="utf-8")  # Substrat (irgendein Inhalt)
    pl = folder / "6_PL"
    pl.mkdir(parents=True, exist_ok=True)
    view = pl / f"{bl}-{slug}-parking-lot.md"
    body = f"# {bl} Parking Lot\r\n\r\ncontent here\r\n".encode("utf-8")  # frontmatter-less
    view.write_bytes(body)
    return {"bl": bl, "view": view, "atom": atom, "body": body}


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 1 — _view_classify_type
# ──────────────────────────────────────────────────────────────────────────────
class TestViewClassifyType:
    """_view_classify_type(view_rel): path-derived view type (lowercased parts)."""

    def test_arc42_path(self):
        assert vsam._view_classify_type("Backlog/BL-100-x/arc42/05_building.md") == "arc42"

    def test_6pl_path_is_parking_lot(self):
        assert vsam._view_classify_type(
            "Backlog/BL-100-x/6_PL/BL-100-x-parking-lot.md"
        ) == "parking_lot"

    def test_model_basename(self):
        assert vsam._view_classify_type("Backlog/BL-100-x/2_Model/Alpha_Model.md") == "model"

    def test_other_is_view(self):
        assert vsam._view_classify_type("Docs/guide.md") == "view"


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 2 — _view_feature
# ──────────────────────────────────────────────────────────────────────────────
class TestViewFeature:
    """_view_feature(view_rel): Backlog/<folder>/... -> <folder>, sonst None."""

    def test_backlog_folder_slug(self):
        assert vsam._view_feature("Backlog/BL-365-x/6_PL/y.md") == "BL-365-x"

    def test_non_backlog_is_none(self):
        assert vsam._view_feature("Docs/guide.md") is None


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 3 — _minimal_frontmatter_block
# ──────────────────────────────────────────────────────────────────────────────
class TestMinimalFrontmatterBlock:
    """_minimal_frontmatter_block(view_rel, *, newline): minimal, deterministic,
    NON-fabricated frontmatter (nur path-derived Felder), valides YAML."""

    def _inner_yaml(self, block: str):
        # zwischen oeffnender und schliessender `---`-Fence (kein Feldwert enthaelt `---`)
        parts = block.split("---")
        assert len(parts) == 3, f"genau 2 Fences (3 split-Teile) erwartet, war {len(parts)}"
        return parts[1]

    def test_with_feature_shape_and_yaml(self):
        import yaml
        nl = "\r\n"
        block = vsam._minimal_frontmatter_block("Backlog/BL-365-x/6_PL/y.md")
        assert block.startswith("---"), "muss mit oeffnender --- starten"
        assert block.count("---") == 2, "genau oeffnende + schliessende Fence"
        assert block.rstrip(nl).endswith("---"), "schliessende --- ist letzte Inhaltszeile"
        assert nl + nl in block, "schliessende --- + EINE Leerzeile am Ende"
        assert "type:" in block and "view_frontmatter_generated: BL-491" in block
        assert "feature: BL-365-x" in block

        data = yaml.safe_load(self._inner_yaml(block))
        assert isinstance(data, dict), f"inner block muss dict sein, war {type(data)}"
        assert data["type"] == "parking_lot"
        assert data["feature"] == "BL-365-x"
        assert data["edges"] == []
        assert data["view_frontmatter_generated"] == "BL-491"

    def test_no_feature_omits_line(self):
        import yaml
        block = vsam._minimal_frontmatter_block("Docs/guide.md")
        assert "feature:" not in block, "feature-Zeile MUSS entfallen wenn feature None"
        data = yaml.safe_load(self._inner_yaml(block))
        assert isinstance(data, dict)
        assert data["type"] == "view"
        assert "feature" not in data
        assert data["edges"] == []
        assert data["view_frontmatter_generated"] == "BL-491"

    def test_deterministic(self):
        a = vsam._minimal_frontmatter_block("Backlog/BL-365-x/6_PL/y.md")
        b = vsam._minimal_frontmatter_block("Backlog/BL-365-x/6_PL/y.md")
        assert a == b, "deterministisch — identischer Input -> identischer Output"


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 4 — _is_frontmatter_less
# ──────────────────────────────────────────────────────────────────────────────
class TestIsFrontmatterLess:
    """_is_frontmatter_less(view_path): True nur wenn NICHT mit `---` startet UND
    NICHT korrupt (find_stray_run_end is None)."""

    def test_body_only_is_true(self, tmp_path):
        p = tmp_path / "body.md"
        p.write_bytes(b"# Heading\r\nbody\r\n")
        assert vsam._is_frontmatter_less(p) is True

    def test_has_frontmatter_is_false(self, tmp_path):
        p = tmp_path / "fm.md"
        p.write_bytes(b"---\ntype: parking_lot\n---\n\nbody\n")
        assert vsam._is_frontmatter_less(p) is False

    def test_corrupt_stray_prefix_is_false(self, tmp_path):
        # stray `source_atoms:`-Block am Byte 0 -> korrupt -> NIE als frontmatter-less behandeln
        p = tmp_path / "corrupt.md"
        p.write_bytes(b"source_atoms:\r\n  - a/b.md\r\n# H\r\n")
        assert vsam._is_frontmatter_less(p) is False


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 5 — _create_minimal_frontmatter
# ──────────────────────────────────────────────────────────────────────────────
class TestCreateMinimalFrontmatter:
    """_create_minimal_frontmatter(view_path, vault): erstellt minimale FM NUR auf
    genuinely-frontmatter-less Views; NIE auf korrupten; idempotent; CRLF-erhaltend."""

    def test_creates_preserves_body_and_idempotent(self, tmp_path):
        view = tmp_path / "Backlog" / "BL-365-x" / "6_PL" / "BL-365-x-parking-lot.md"
        view.parent.mkdir(parents=True)
        view.write_bytes(_FM_LESS_BODY)

        created = vsam._create_minimal_frontmatter(view, tmp_path)
        assert created is True, "frontmatter-less -> True"
        new = view.read_bytes()
        assert new.startswith(b"---"), "Datei startet jetzt mit ---"
        assert new.startswith(b"---\r\n"), "CRLF-Body -> Block benutzt CRLF"
        assert new.endswith(_FM_LESS_BODY), "ORIGINAL-Body bytes sind exaktes Suffix"

        # idempotent: 2. Aufruf -> False, bytes unveraendert
        again = vsam._create_minimal_frontmatter(view, tmp_path)
        assert again is False, "2. Aufruf auf nun-FM-haltiger Datei -> False"
        assert view.read_bytes() == new, "2. Aufruf darf bytes NICHT aendern"

    def test_corrupt_file_is_noop(self, tmp_path):
        view = tmp_path / "Backlog" / "BL-050-x" / "6_PL" / "BL-050-x-parking-lot.md"
        view.parent.mkdir(parents=True)
        view.write_bytes(_CORRUPT_STRAY)

        created = vsam._create_minimal_frontmatter(view, tmp_path)
        assert created is False, "korrupt -> NIE FM erstellen -> False"
        assert view.read_bytes() == _CORRUPT_STRAY, "korrupte Datei bleibt byte-identisch"


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 6 — materialize_view(write=True, ensure_frontmatter=True) end-to-end
# ──────────────────────────────────────────────────────────────────────────────
class TestMaterializeViewEnsureFrontmatterEndToEnd:
    """Frontmatter-less View-Node MIT Substrat -> ensure_frontmatter erstellt minimale
    FM, schreibt OWN-BL source_atoms; Original-Body bleibt verbatim erhalten."""

    def test_write_creates_fm_then_source_atoms(self, tmp_path):
        info = _make_fm_less_view_with_substrate(tmp_path, num="777", slug="omega")
        view, body = info["view"], info["body"]

        # Vorbedingungen: echter View-Node (view_node_predicate) + Substrat vorhanden
        assert vsam.is_view_node(str(view), str(tmp_path)) is True, \
            "gewaehlter Pfad MUSS is_view_node erfuellen"
        assert vsam.own_atoms_for_bl(info["bl"], tmp_path), "Substrat-Atome erwartet"

        res = vsam.materialize_view(view, tmp_path, write=True, ensure_frontmatter=True)
        assert res["action"] == "written", f"action 'written' erwartet, war {res!r}"
        assert res.get("created_frontmatter") is True, \
            f"created_frontmatter True erwartet, war {res!r}"

        new = view.read_bytes()
        assert new.startswith(b"---"), "Datei startet jetzt mit Frontmatter"
        assert b"source_atoms" in new, "source_atoms-Block muss vorhanden sein"
        assert body in new, "ORIGINAL-Body muss verbatim im File erscheinen"
        assert vsam.view_has_source_atoms(view) is True, "source_atoms muss erkannt werden"


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 7 — Backward-compat (default ensure_frontmatter=False unveraendert)
# ──────────────────────────────────────────────────────────────────────────────
class TestEnsureFrontmatterBackwardCompat:
    """Dieselbe frontmatter-less View mit ensure_frontmatter=False (default) ->
    action 'skip', reason 'malformed_frontmatter' (Default-Verhalten EXAKT unveraendert)."""

    def test_default_off_skips_malformed(self, tmp_path):
        info = _make_fm_less_view_with_substrate(tmp_path, num="782", slug="beta")
        view, body = info["view"], info["body"]
        before = view.read_bytes()

        res = vsam.materialize_view(view, tmp_path, write=True, ensure_frontmatter=False)
        assert res["action"] == "skip", f"action 'skip' erwartet, war {res!r}"
        assert res.get("reason") == "malformed_frontmatter", \
            f"reason 'malformed_frontmatter' erwartet, war {res!r}"
        assert view.read_bytes() == before == body, "Default-OFF darf NICHTS schreiben"


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 8 — dry-run (write=False, ensure_frontmatter=True)
# ──────────────────────────────────────────────────────────────────────────────
class TestEnsureFrontmatterDryRun:
    """write=False + ensure_frontmatter=True auf frontmatter-less View ->
    action 'dry-run', reason 'would_create_frontmatter', File byte-unveraendert."""

    def test_dryrun_would_create_no_write(self, tmp_path):
        info = _make_fm_less_view_with_substrate(tmp_path, num="783", slug="gamma")
        view = info["view"]
        before = view.read_bytes()

        res = vsam.materialize_view(view, tmp_path, write=False, ensure_frontmatter=True)
        assert res["action"] == "dry-run", f"action 'dry-run' erwartet, war {res!r}"
        assert res.get("reason") == "would_create_frontmatter", \
            f"reason 'would_create_frontmatter' erwartet, war {res!r}"
        assert view.read_bytes() == before, "dry-run darf das File NICHT veraendern"


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 9 — FENCE: Atom-Dateien unter truths/ werden NIE veraendert
# ──────────────────────────────────────────────────────────────────────────────
class TestEnsureFrontmatterFenceAtomsUntouched:
    """ensure_frontmatter write -> Atom-Dateien unter truths/ UNTOUCHED (mtime_ns
    Snapshot vor == nach)."""

    def test_atom_mtime_unchanged(self, tmp_path):
        info = _make_fm_less_view_with_substrate(tmp_path, num="784", slug="delta")
        atom = info["atom"]
        before = _mtimes([atom])

        res = vsam.materialize_view(info["view"], tmp_path, write=True, ensure_frontmatter=True)
        assert res["action"] == "written", f"action 'written' erwartet, war {res!r}"
        assert _mtimes([atom]) == before, "Atom-mtime_ns MUSS unveraendert bleiben (FENCE)"


# ──────────────────────────────────────────────────────────────────────────────
# REQUIRED TEST 10 — run(...) + main(--ensure-frontmatter)
# ──────────────────────────────────────────────────────────────────────────────
class TestRunAndMainEnsureFrontmatter:
    """run(ensure_frontmatter=True) materialisiert das frontmatter-less Target;
    main([..., '--ensure-frontmatter']) liefert 0."""

    def test_run_materializes_frontmatterless(self, tmp_path):
        info = _make_fm_less_view_with_substrate(tmp_path, num="785", slug="epsilon")
        view = info["view"]

        r = vsam.run(tmp_path, write=True, ensure_frontmatter=True)
        assert r["dry_run"] is False, "write -> dry_run False"
        assert vsam.view_has_source_atoms(view) is True, \
            "frontmatter-less Target muss materialisiert sein"
        assert view.read_bytes().startswith(b"---"), "Target hat jetzt Frontmatter"

    def test_main_flag_returns_zero(self, tmp_path):
        _make_fm_less_view_with_substrate(tmp_path, num="786", slug="zeta")
        rc = vsam.main(["--vault", str(tmp_path), "--write", "--ensure-frontmatter"])
        assert rc == 0, f"exit 0 erwartet, war {rc}"


if __name__ == "__main__":
    import shutil
    import tempfile

    _tests = [
        obj for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    passed = failed = 0
    for t in _tests:
        d = Path(tempfile.mkdtemp(prefix="vsam_"))
        try:
            t(d)
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
        finally:
            shutil.rmtree(d, ignore_errors=True)
    print(f"\n=== {passed}/{passed + failed} ===")
    sys.exit(0 if failed == 0 else 1)
