#!/usr/bin/env python3
"""RED tests fuer view_source_atoms_prune.py (BL-491 G3-rest).

STRICT TDD RED: dieses Modul testet das NOCH-NICHT-EXISTIERENDE Tool
`view_source_atoms_prune`. Ein separater GREEN-Worker implementiert die Produktion
(INV-BUILD-GRAIN: RED-Worker != GREEN-Worker).

Was das Tool tut (Contract bl491_prune_spec.md):
  Entfernt chirurgisch die NICHT-aufloesenden (stalen) `source_atoms:`-Eintraege aus
  den View-Frontmattern (z.B. BL-folder-relative A-Pipeline-Stage-Pfade wie
  `3_Spec/BL-387_Spec.md`, die vom Vault-Root NICHT aufloesen). FRONTMATTER-ONLY,
  VIEW-FILES-ONLY: der Body (inkl. `## Verwandte Wahrheiten` `- Verwandt: ...`-Zeilen)
  und alle anderen FM-Felder bleiben BYTE-FUER-BYTE erhalten; Atom-Dateien werden NIE
  angefasst.

API (exakt — Tests haengen daran):
  read_source_atoms(view_path) -> list[str]
  _rewrite_source_atoms_block(content, new_atoms) -> str
  prune_unresolved_source_atoms(view_path, vault, *, write) -> dict
  run(vault, *, write, views=None) -> dict
  main(argv) -> int

RED-Beweis: `view_source_atoms_prune` existiert NOCH NICHT. Der Top-Level-Import
schlaegt fehl -> pytest COLLECTION ERROR -> jeder Test ist RED. Das IST der RED-Zustand.
Der GREEN-Worker erstellt das Modul, ohne diese Tests zu editieren.
"""
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Harter Top-Level-Import: solange das Modul fehlt (RED-Phase) -> ImportError ->
# pytest meldet COLLECTION ERROR fuer die ganze Datei = RED. (Bare-Import-Stil wie
# die Sibling-Suiten; sys.path enthaelt SCRIPT_DIR.)
from view_source_atoms_prune import (  # noqa: E402  (RED: Modul existiert noch nicht)
    read_source_atoms,
    _rewrite_source_atoms_block,
    prune_unresolved_source_atoms,
    run,
    main,
)

CRLF = "\r\n"

# Der LOAD-BEARING Body: ein `## Verwandte Wahrheiten`-Block mit `- Verwandt: ...`-Zeilen.
# Genau diese Body-Bytes MUESSEN nach jedem Prune unveraendert bleiben (das Tool darf
# NUR den Frontmatter-source_atoms-Block anfassen, NIE Body-`- `-Zeilen).
BODY = (
    CRLF
    + "# Body" + CRLF
    + CRLF
    + "## Verwandte Wahrheiten" + CRLF
    + "- Verwandt: W1 some summary" + CRLF
    + "- Verwandt: W2 other" + CRLF
)
BODY_BYTES = BODY.encode("utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures — match the REAL vault: UNINDENTED block-sequence source_atoms, CRLF.
# ──────────────────────────────────────────────────────────────────────────────
def _make_content(source_atoms, *, feature="BL-387") -> str:
    """Echtes-Vault-Frontmatter-Form: `source_atoms:` gefolgt von UNINDENTIERTEN
    Block-Sequence-Items auf Spalte 0 (`- 3_Spec/BL-387_Spec.md`), CRLF.

    source_atoms=None  -> KEIN source_atoms-Key (abwesend).
    source_atoms=[...]  -> Block-Sequence mit den Items.
    Body (BODY) wird immer angehaengt (Verwandte-Wahrheiten-Sektion)."""
    fm = ["---", "type: parking_lot", f"feature: {feature}"]
    if source_atoms is not None:
        fm.append("source_atoms:")
        fm += [f"- {sa}" for sa in source_atoms]
    fm += ["edges: []", "---"]
    return CRLF.join(fm) + CRLF + BODY


def _make_content_inline_empty(*, feature="BL-387") -> str:
    """Frontmatter mit leerer Inline-Liste `source_atoms: []`."""
    fm = [
        "---",
        "type: parking_lot",
        f"feature: {feature}",
        "source_atoms: []",
        "edges: []",
        "---",
    ]
    return CRLF.join(fm) + CRLF + BODY


def _write_view(vault: Path, bl_folder: str, source_atoms) -> Path:
    """Lege einen View-Node an: Backlog/<bl_folder>/6_PL/<bl_folder>-parking-lot.md
    (von view_node_predicate.is_view_node akzeptiert). Schreibt BYTES (CRLF erhalten)."""
    view = vault / "Backlog" / bl_folder / "6_PL" / f"{bl_folder}-parking-lot.md"
    view.parent.mkdir(parents=True, exist_ok=True)
    view.write_bytes(_make_content(source_atoms).encode("utf-8"))
    return view


def _create_atoms(vault: Path, rel_paths) -> list:
    """Erzeuge die (aufloesenden) Atom-Dateien unter vault/<rel> -> ein Eintrag
    `a` loest auf gdw `(vault / a).exists()`."""
    created = []
    for rel in rel_paths:
        ap = vault / rel
        ap.parent.mkdir(parents=True, exist_ok=True)
        ap.write_text("---\ntype: truth\n---\nbody\n", encoding="utf-8")
        created.append(ap)
    return created


def _snapshot_mtimes(root: Path, exclude) -> dict:
    """{vault-rel-Pfad: st_mtime_ns} fuer ALLE Dateien unter root ausser `exclude`.
    Gleichheit vor/nach beweist: keine Datei erstellt/geloescht, keine mtime geaendert."""
    excl = {str(Path(p).resolve()) for p in exclude}
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and str(p.resolve()) not in excl:
            out[p.relative_to(root).as_posix()] = p.stat().st_mtime_ns
    return out


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 1 — read_source_atoms
# ══════════════════════════════════════════════════════════════════════════════
def test_read_source_atoms_unindented_block_and_absent_empty(tmp_path):
    """read_source_atoms: UNINDENTIERTE Block-Sequence (`source_atoms:\\r\\n- a/b.md\\r\\n
    - c/d.md`) -> ["a/b.md","c/d.md"]; abwesend -> []; leer (`source_atoms: []`) -> []."""
    view = _write_view(tmp_path, "BL-387-x", ["a/b.md", "c/d.md"])
    assert read_source_atoms(view) == ["a/b.md", "c/d.md"], \
        "unindentierte Block-Sequence muss als Liste der Pfad-Strings geparst werden"

    absent = _write_view(tmp_path, "BL-388-x", None)
    assert read_source_atoms(absent) == [], "abwesendes source_atoms -> []"

    empty = tmp_path / "Backlog" / "BL-389-x" / "6_PL" / "BL-389-x-parking-lot.md"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_bytes(_make_content_inline_empty().encode("utf-8"))
    assert read_source_atoms(empty) == [], "leeres `source_atoms: []` -> []"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 2 — _rewrite_source_atoms_block (subset)
# ══════════════════════════════════════════════════════════════════════════════
def test_rewrite_block_keeps_subset_crlf_preserved():
    """_rewrite_source_atoms_block: 4-Item-Block -> 2-Item kept -> NUR die 2 bleiben
    (unindentierte `- `), andere FM-Felder + Body unveraendert, CRLF erhalten."""
    content = _make_content(["A/a.md", "B/b.md", "C/c.md", "D/d.md"])
    kept = ["A/a.md", "C/c.md"]

    new = _rewrite_source_atoms_block(content, kept)

    # Genau die kept-Items, unindentiert, in-place (gefolgt vom naechsten FM-Feld `edges`).
    expected_block = (
        "source_atoms:" + CRLF + "- A/a.md" + CRLF + "- C/c.md" + CRLF + "edges: []"
    )
    assert expected_block in new, (
        "kept-Items muessen den Block ersetzen (unindentiert, in-place vor `edges:`):\n"
        + repr(new)
    )
    # Entfernte Items duerfen NICHT mehr auftauchen.
    assert "- B/b.md" not in new and "- D/d.md" not in new, \
        "entfernte source_atoms-Items duerfen nicht im Output sein"
    # Andere FM-Felder erhalten.
    assert "type: parking_lot" in new and "feature: BL-387" in new and "edges: []" in new, \
        "andere Frontmatter-Felder muessen erhalten bleiben"
    # Body byte-identisch.
    assert new.encode("utf-8").endswith(BODY_BYTES), "Body muss byte-identisch bleiben"
    # CRLF erhalten: jedes \n ist Teil eines \r\n (kein bare \n).
    assert "\n" not in new.replace(CRLF, ""), "CRLF muss erhalten bleiben (kein bare \\n)"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 3 — _rewrite_source_atoms_block (empty -> remove key)
# ══════════════════════════════════════════════════════════════════════════════
def test_rewrite_block_empty_removes_key():
    """_rewrite_source_atoms_block mit new_atoms=[] -> der source_atoms-Key UND seine
    Item-Zeilen sind GONE; andere FM + Body intakt; weiterhin valides
    `---`...`---`-Frontmatter."""
    content = _make_content(["3_Spec/BL-387_Spec.md", "2_Model/BL-387_Model.md"])

    new = _rewrite_source_atoms_block(content, [])

    assert "source_atoms" not in new, "der source_atoms-Key muss komplett entfernt sein"
    assert "3_Spec/BL-387_Spec.md" not in new and "2_Model/BL-387_Model.md" not in new, \
        "die Item-Zeilen muessen mit-entfernt sein"
    # Andere FM-Felder bleiben + ruecken zusammen (feature direkt vor edges).
    assert "feature: BL-387" + CRLF + "edges: []" in new, \
        "uebrige Frontmatter-Felder muessen erhalten + zusammengeruekt sein"
    # Weiterhin valides `---`...`---`-Frontmatter (oeffnende + schliessende Fence + Body).
    assert new.startswith("---" + CRLF), "muss weiterhin mit oeffnender --- starten"
    assert "edges: []" + CRLF + "---" + CRLF in new, "schliessende Fence muss erhalten sein"
    # Body byte-identisch.
    assert new.encode("utf-8").endswith(BODY_BYTES), "Body muss byte-identisch bleiben"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 4 — prune_unresolved_source_atoms (write) + idempotent
# ══════════════════════════════════════════════════════════════════════════════
def test_prune_unresolved_writes_kept_and_idempotent(tmp_path):
    """View mit 2 aufloesenden + 2 nicht-aufloesenden source_atoms -> write=True ->
    removed == die 2 nicht-aufloesenden, kept == die 2 aufloesenden (Reihenfolge erhalten);
    Datei listet danach NUR die 2 aufloesenden. Idempotent (2. Lauf action 'noop')."""
    resolving = [
        "Backlog/BL-387-x/2_Model/truths/W1.md",
        "Backlog/BL-387-x/2_Model/truths/W2.md",
    ]
    nonresolving = ["3_Spec/BL-387_Spec.md", "2_Model/BL-387_Model.md"]
    # Interleaved, um Reihenfolge-Erhaltung zu pruefen.
    atoms = [resolving[0], nonresolving[0], resolving[1], nonresolving[1]]

    view = _write_view(tmp_path, "BL-387-x", atoms)
    _create_atoms(tmp_path, resolving)  # nur die resolving-Pfade existieren

    res = prune_unresolved_source_atoms(view, tmp_path, write=True)
    assert res["removed"] == nonresolving, \
        f"removed muss == die nicht-aufloesenden (Reihenfolge) sein, war {res.get('removed')!r}"
    assert res["changed"] is True, "changed muss True sein"
    assert res["action"] == "pruned", f"action 'pruned' erwartet, war {res.get('action')!r}"
    assert res["n_before"] == 4 and res["n_kept"] == 2 and res["n_removed"] == 2, \
        f"Zaehler n_before=4/n_kept=2/n_removed=2 erwartet, war {res!r}"

    # Datei listet danach NUR die 2 aufloesenden (Reihenfolge erhalten).
    assert read_source_atoms(view) == resolving, \
        "die Datei muss nach Prune nur die aufloesenden source_atoms listen"

    # Idempotent: 2. Lauf -> keine Aenderung.
    before2 = view.read_bytes()
    res2 = prune_unresolved_source_atoms(view, tmp_path, write=True)
    assert res2["changed"] is False, "2. Lauf darf nichts mehr aendern (changed False)"
    assert res2["action"] == "noop", f"2. Lauf action 'noop' erwartet, war {res2.get('action')!r}"
    assert res2["removed"] == [] and res2["n_removed"] == 0, "2. Lauf entfernt nichts"
    assert view.read_bytes() == before2, "idempotent: Datei-Bytes muessen gleich bleiben"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 5 — prune where ALL entries non-resolving -> key removed
# ══════════════════════════════════════════════════════════════════════════════
def test_prune_all_unresolved_removes_key(tmp_path):
    """ALLE Eintraege nicht-aufloesend -> kept leer -> source_atoms-Key entfernt;
    View hat danach KEIN source_atoms (read_source_atoms -> []); Body erhalten."""
    atoms = ["3_Spec/BL-459_Spec.md", "4_K-Score/BL-459_K-SCORE.md", "5_Gap/BL-459_Gap.md"]
    view = _write_view(tmp_path, "BL-459-x", atoms)  # KEINE der Pfade existiert
    body_before = view.read_bytes()
    assert body_before.endswith(BODY_BYTES)  # Sanity

    res = prune_unresolved_source_atoms(view, tmp_path, write=True)
    assert res["removed"] == atoms, "alle Eintraege muessen removed sein"
    assert res["n_kept"] == 0 and res["n_removed"] == 3, f"kept 0 / removed 3 erwartet, war {res!r}"
    assert res["changed"] is True and res["action"] == "pruned"

    new = view.read_bytes()
    assert b"source_atoms" not in new, "der source_atoms-Key muss komplett entfernt sein"
    assert read_source_atoms(view) == [], "View hat danach kein source_atoms mehr"
    assert new.endswith(BODY_BYTES), "Body muss byte-identisch erhalten bleiben"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 6 — dry-run reports but does NOT write
# ══════════════════════════════════════════════════════════════════════════════
def test_prune_dryrun_reports_but_no_write(tmp_path):
    """write=False -> action 'dry-run', Datei BYTE-unveraendert auf Platte, ABER das
    Ergebnis meldet die zu entfernenden Eintraege (removed)."""
    resolving = ["Backlog/BL-474-x/2_Model/truths/W1.md"]
    nonresolving = ["3_Spec/BL-474_Spec.md"]
    view = _write_view(tmp_path, "BL-474-x", resolving + nonresolving)
    _create_atoms(tmp_path, resolving)
    before = view.read_bytes()

    res = prune_unresolved_source_atoms(view, tmp_path, write=False)
    assert res["action"] == "dry-run", f"action 'dry-run' erwartet, war {res.get('action')!r}"
    assert res["changed"] is True, "dry-run meldet trotzdem changed True"
    assert res["removed"] == nonresolving, \
        f"dry-run muss removed melden, war {res.get('removed')!r}"
    assert res["n_removed"] == 1
    assert view.read_bytes() == before, "DRY-RUN darf die Datei NICHT veraendern"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 7 — FENCE: atom files NEVER touched
# ══════════════════════════════════════════════════════════════════════════════
def test_prune_fence_atoms_untouched(tmp_path):
    """FENCE: ein aufloesendes Atom (das die View referenziert) + ein nicht-aufloesender
    Ref. Prune entfernt den NICHT-aufloesenden -> das Atom-mtime_ns ist unveraendert und
    KEINE Atom-Datei wird erstellt/geloescht (View-FILES-ONLY)."""
    resolving = "Backlog/BL-477-x/2_Model/truths/W1.md"
    nonresolving = "5_Gap/BL-477_Gap.md"
    view = _write_view(tmp_path, "BL-477-x", [resolving, nonresolving])
    (atom,) = _create_atoms(tmp_path, [resolving])

    atom_mtime_before = os.stat(atom).st_mtime_ns
    # Schnappschuss ALLER Nicht-View-Dateien (Atom inklusive).
    snap_before = _snapshot_mtimes(tmp_path, exclude=[view])

    res = prune_unresolved_source_atoms(view, tmp_path, write=True)
    assert res["removed"] == [nonresolving], "der nicht-aufloesende Ref muss entfernt sein"
    assert read_source_atoms(view) == [resolving], "der aufloesende Ref muss erhalten bleiben"

    assert os.stat(atom).st_mtime_ns == atom_mtime_before, \
        "Atom-mtime_ns MUSS unveraendert bleiben (FENCE)"
    assert _snapshot_mtimes(tmp_path, exclude=[view]) == snap_before, \
        "keine Atom-Datei darf erstellt/geloescht/veraendert werden (View-FILES-ONLY)"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 8 — body `- Verwandt:` lines byte-identical (LOAD-BEARING safety)
# ══════════════════════════════════════════════════════════════════════════════
def test_prune_preserves_body_verwandt_lines(tmp_path):
    """LOAD-BEARING: eine View mit `## Verwandte Wahrheiten`-Sektion aus `- Verwandt: ...`-
    Zeilen -> nach Prune sind genau diese Body-Bytes IDENTISCH. Das Tool darf NUR den
    Frontmatter-source_atoms-Block anfassen, NIE Body-`- `-Zeilen."""
    resolving = ["Backlog/BL-387-x/2_Model/truths/W1.md"]
    nonresolving = ["3_Spec/BL-387_Spec.md", "2_Model/BL-387_Model.md"]
    view = _write_view(tmp_path, "BL-387-x", resolving + nonresolving)
    _create_atoms(tmp_path, resolving)

    before = view.read_bytes()
    assert before.endswith(BODY_BYTES), "Sanity: Fixture-Body == BODY"

    res = prune_unresolved_source_atoms(view, tmp_path, write=True)
    assert res["changed"] is True and res["removed"] == nonresolving

    after = view.read_bytes()
    # Die EXAKTEN Body-Bytes (inkl. der `- Verwandt:`-Zeilen) muessen unveraendert sein.
    assert after.endswith(BODY_BYTES), \
        "die Body-Bytes (`## Verwandte Wahrheiten` + `- Verwandt:`-Zeilen) muessen byte-identisch bleiben"
    assert b"- Verwandt: W1 some summary" + CRLF.encode("utf-8") in after, \
        "die `- Verwandt: W1 ...`-Body-Zeile muss byte-identisch erhalten sein"
    assert b"- Verwandt: W2 other" + CRLF.encode("utf-8") in after, \
        "die `- Verwandt: W2 ...`-Body-Zeile muss byte-identisch erhalten sein"
    # ... aber die Frontmatter wurde tatsaechlich beschnitten.
    assert read_source_atoms(view) == resolving, "Frontmatter source_atoms wurde beschnitten"


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED TEST 9 — run() over explicit views + main(--write)
# ══════════════════════════════════════════════════════════════════════════════
def test_run_explicit_views_and_main_write(tmp_path):
    """run(views=[...]) prunet jeden -> total_removed korrekt, views_changed korrekt.
    main(['--vault', v, '--write']) -> 0 (und prunet die scan-erkannten Views)."""
    # ── run() ueber explizite Views ──────────────────────────────────────────
    r_resolve = "Backlog/BL-387-x/2_Model/truths/W1.md"
    v1 = _write_view(tmp_path, "BL-387-x", [r_resolve, "3_Spec/BL-387_Spec.md"])
    v2 = _write_view(tmp_path, "BL-459-x", [
        "Backlog/BL-459-x/2_Model/truths/W1.md",
        "5_Gap/BL-459_Gap.md",
        "4_K-Score/BL-459_K-SCORE.md",
    ])
    _create_atoms(tmp_path, [r_resolve, "Backlog/BL-459-x/2_Model/truths/W1.md"])

    out = run(tmp_path, write=True, views=[v1, v2])
    assert out["write"] is True, "write True erwartet"
    assert isinstance(out["results"], list) and len(out["results"]) == 2, \
        f"results muss je Ziel-View einen Eintrag haben, war {out.get('results')!r}"
    # v1 entfernt 1, v2 entfernt 2 -> total 3, beide geaendert.
    assert out["total_removed"] == 3, f"total_removed 3 erwartet, war {out.get('total_removed')!r}"
    assert out["views_changed"] == 2, f"views_changed 2 erwartet, war {out.get('views_changed')!r}"
    assert read_source_atoms(v1) == [r_resolve], "v1 muss beschnitten sein"
    assert read_source_atoms(v2) == ["Backlog/BL-459-x/2_Model/truths/W1.md"], \
        "v2 muss beschnitten sein"

    # ── main([... --write]) -> 0 (Scan-Pfad, views=None) ─────────────────────
    vault2 = tmp_path / "vault2"
    res2 = "Backlog/BL-474-x/2_Model/truths/W1.md"
    v3 = _write_view(vault2, "BL-474-x", [res2, "3_Spec/BL-474_Spec.md"])
    _create_atoms(vault2, [res2])

    rc = main(["--vault", str(vault2), "--write"])
    assert rc == 0, f"exit 0 erwartet, war {rc}"
    assert read_source_atoms(v3) == [res2], \
        "main(--write) muss den stalen Ref aus der scan-erkannten View entfernen"
