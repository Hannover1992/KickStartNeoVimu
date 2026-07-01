#!/usr/bin/env python3
"""RED tests fuer truth_capstone_gate.py (BL-484 — Capstone-Gate Stage 8 G1-G6).

STRIKT TDD RED: dieses Modul (`truth_capstone_gate`) existiert noch NICHT.
Der Import am Modul-Kopf MUSS fehlschlagen -> Collection-Error = korrektes ROT.
Ein SEPARATER GREEN-Worker implementiert `truth_capstone_gate.py` spaeter und macht
diese Tests gruen OHNE die Tests zu aendern (INV-BUILD-GRAIN: RED-Worker != GREEN-Worker).

Vertrag (siehe BL-484_gate_contract.md):
  run_capstone_gate(vault: Path, *, live_g4: bool = True) -> dict mit keys:
    vault, atoms, views, gates(list[6] je {gate,name,green,missing_stage,detail}),
    green_count, total(==6), migration_complete(bool == alle 6 gruen).
  main(argv) -> int  (CLI: --vault PATH [--out report.json] [--quiet] [--no-live-g4];
                      exit 0 GENAU DANN wenn alle 6 gruen, sonst nonzero).

Die Fixtures bauen SYNTHETISCHE Mini-Vaults in tmp_path (kein echter Vault).
- healthy_vault: alle G1-G6 GRUEN.
- pro Kriterium ein gebrochener Vault: GENAU EIN flip -> GENAU EIN Gate ROT,
  die anderen FUENF bleiben GRUEN (Isolation = was das Gate vertrauenswuerdig macht).

Atom content_hash wird IMMER mit dem echten truth_atomizer._sha256(text) gesetzt,
ueber yaml.safe_dump/safe_load-Roundtrip (identisch zur Real-Serialisierung in
truth_atomizer.truth_to_md), damit G5 auf dem gesunden Vault gruen ist.
"""
from __future__ import annotations

import json

import pytest
import yaml

# RED: dieses Modul existiert noch NICHT -> ModuleNotFoundError bei Collection (= ROT).
import truth_capstone_gate
from truth_capstone_gate import main, run_capstone_gate  # noqa: F401

# Echter Hash-Primitiv (damit G5 auf dem gesunden Vault gruen ist).
from truth_atomizer import _sha256


# ---------------------------------------------------------------------------
# Konstanten — Pfade/IDs des Mini-Vaults (Test + Builder muessen sich einig sein)
# ---------------------------------------------------------------------------

BL = "BL-001"
ATOM_A_REL = "Backlog/BL-001/2_Model/truths/A1.md"   # Atom NS.A1 (nicht view-node)
ATOM_B_REL = "Backlog/BL-001/2_Model/truths/B1.md"   # Atom NS.B1 (nicht view-node)
VIEW_REL = "Backlog/BL-001/2_Model/Sample_Model.md"  # View (is_view_node == True)
VIEW_ID = "VIEW.Sample"

# Gesunde Atom-Parameter (broken-Tests kopieren + kippen GENAU EIN Feld).
_A_PARAMS = dict(
    atom_id="NS.A1",
    local_id="A1",
    keywords=["alpha", "beta", "gamma", "delta"],
    text="Atom A discusses alpha beta gamma delta in full detail.",
    edges=[{"ziel": "NS.B1", "kind": "truth_edge"}],
    referenced_by=[
        {"by": "NS.B1", "kind": "truth_edge"},   # B1 -> A1 (bidirektional)
        {"by": VIEW_ID, "kind": "view_source"},  # View -> A1 (G3 backward)
    ],
)
_B_PARAMS = dict(
    atom_id="NS.B1",
    local_id="B1",
    keywords=["epsilon", "zeta", "eta", "theta"],
    text="Atom B explains epsilon zeta eta theta thoroughly.",
    edges=[{"ziel": "NS.A1", "kind": "truth_edge"}],
    referenced_by=[{"by": "NS.A1", "kind": "truth_edge"}],  # A1 -> B1
)


# ---------------------------------------------------------------------------
# Datei-Builder (yaml.safe_dump-Frontmatter, identisch zur Real-Serialisierung)
# ---------------------------------------------------------------------------

def _wikilink_body(ziel: str = "NS.B1") -> str:
    """Body MIT Wikilink-Sektion (G6: Atome mit edges brauchen die Sektion)."""
    return (
        "\n## Verwandte Wahrheiten\n\n"
        f"- Verwandt: [[{ziel}|{ziel.split('.')[-1]}]]\n"
    )


def _write_atom(
    root,
    relpath,
    *,
    atom_id,
    local_id,
    keywords,
    text,
    edges=None,
    referenced_by=None,
    body=None,
    content_hash=None,
):
    """Schreibt ein truth-Atom. content_hash default = echter _sha256(text)."""
    fm: dict = {
        "type": "truth",
        "id": atom_id,
        "local_id": local_id,
        "keywords": list(keywords),
        "content_hash": content_hash if content_hash is not None else _sha256(text),
        "text": text,
    }
    if edges is not None:
        fm["edges"] = edges
    if referenced_by is not None:
        fm["referenced_by"] = referenced_by

    if body is None:
        body = _wikilink_body() if edges else "\nAtom body ohne edges.\n"

    dumped = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    content = f"---\n{dumped}---\n{body}"

    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_view(root, relpath, *, view_id, source_atoms, bl=BL, body=None):
    """Schreibt eine View (is_view_node == True via Pfad Backlog/<bl>/2_Model/*_Model.md)."""
    fm: dict = {
        "id": view_id,
        "tags": ["type/model"],
        "bl": bl,
        "source_atoms": list(source_atoms),
    }
    if body is None:
        body = (
            "\n# Sample Model\n\n"
            "alpha beta gamma delta epsilon zeta eta theta.\n\n"
            "- [[NS.A1|A1]]\n"
        )
    dumped = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    content = f"---\n{dumped}---\n{body}"

    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _build_healthy(root):
    """Baut einen Vault, in dem ALLE G1-G6 gruen sind."""
    _write_atom(root, ATOM_A_REL, **_A_PARAMS)
    _write_atom(root, ATOM_B_REL, **_B_PARAMS)
    _write_view(root, VIEW_REL, view_id=VIEW_ID, source_atoms=[ATOM_A_REL])
    return root


@pytest.fixture
def healthy_vault(tmp_path):
    return _build_healthy(tmp_path)


# ---------------------------------------------------------------------------
# Assertion-Helfer
# ---------------------------------------------------------------------------

def _gate(result, gid):
    for g in result["gates"]:
        if g["gate"] == gid:
            return g
    raise AssertionError(f"Gate {gid} fehlt im Ergebnis: {[g['gate'] for g in result['gates']]}")


def _assert_all_green(result):
    assert result["migration_complete"] is True, f"erwartet migration_complete, got {result}"
    assert result["total"] == 6
    assert result["green_count"] == 6, [g for g in result["gates"] if not g["green"]]
    assert len(result["gates"]) == 6
    for g in result["gates"]:
        assert g["green"] is True, f"Gate {g['gate']} unerwartet ROT: {g}"
        assert g["missing_stage"] is None, f"GRUEN-Gate {g['gate']} darf kein missing_stage haben"


def _assert_only_red(result, red_gid):
    """GENAU red_gid ist ROT, die anderen FUENF sind GRUEN (Isolation)."""
    assert result["migration_complete"] is False, "ein gebrochener Vault darf nicht complete sein"
    assert result["total"] == 6
    assert len(result["gates"]) == 6

    red = _gate(result, red_gid)
    assert red["green"] is False, f"{red_gid} sollte ROT sein, ist aber GRUEN: {red}"
    assert isinstance(red["missing_stage"], str) and red["missing_stage"].strip(), (
        f"{red_gid} ROT braucht ein nicht-leeres missing_stage (BL-483-Stage), got {red['missing_stage']!r}"
    )

    others = [g for g in result["gates"] if g["gate"] != red_gid]
    assert len(others) == 5
    for g in others:
        assert g["green"] is True, f"Nur {red_gid} darf ROT sein, aber {g['gate']} ist auch ROT: {g}"
        assert g["missing_stage"] is None, f"GRUEN-Gate {g['gate']} darf kein missing_stage haben"

    assert result["green_count"] == 5


def _disable_forward_garantie(monkeypatch):
    """G4-RED-Strategie (MONKEYPATCH): die Forward-Garantie-Engine wird zu einem no-op,
    der KEINEN Referenten produziert und NICHT schreibt.

    Warum monkeypatch statt Fixture-Trick (kein-keyword-overlap-Sandbox): robust +
    deterministisch. Die "kein-overlap"-Variante haengt davon ab, WIE der GREEN-Worker
    die Sandbox-View baut und was extract_keywords/search_truths als salient werten
    (Schwellen-/Korpus-abhaengig) — fragil. Der Patch erzwingt das Ergebnis "kein
    Referent produziert" unabhaengig von der Scoring-Heuristik.

    Gepatcht werden die laut Contract genutzten Engine-Eintrittspunkte auf BEIDEN
    Modulen (Quelle + truth_capstone_gate), um beide Import-Stile abzudecken:
      - `import view_forward_reference; view_forward_reference.forward_reference_new_view(...)`
      - `from view_forward_reference import forward_reference_new_view` (Name auf truth_capstone_gate)
    """
    def _no_referent(*args, **kwargs):
        view = str(args[0]) if args else str(kwargs.get("view_path", ""))
        return {
            "view": view,
            "proposed_atoms": [],
            "n_proposed": 0,
            "action": "dry-run",
            "reason": "patched: forward-garantie deaktiviert (G4 ROT Simulation)",
        }

    import view_forward_reference

    for mod in (view_forward_reference, truth_capstone_gate):
        for fname in ("forward_reference_new_view", "forward_reference_view"):
            monkeypatch.setattr(mod, fname, _no_referent, raising=False)


# ===========================================================================
# Shape / Healthy / CLI
# ===========================================================================

class TestShape:
    def test_run_capstone_gate_shape(self, healthy_vault):
        """run_capstone_gate liefert die vertragliche Struktur."""
        result = run_capstone_gate(healthy_vault)

        for key in ("vault", "atoms", "views", "gates", "green_count", "total", "migration_complete"):
            assert key in result, f"Pflicht-Key {key} fehlt im Ergebnis"

        assert result["total"] == 6
        assert isinstance(result["gates"], list)
        assert len(result["gates"]) == 6

        assert [g["gate"] for g in result["gates"]] == ["G1", "G2", "G3", "G4", "G5", "G6"]
        for g in result["gates"]:
            for k in ("gate", "name", "green", "missing_stage", "detail"):
                assert k in g, f"Gate-Key {k} fehlt in {g}"
            assert isinstance(g["green"], bool)
            assert isinstance(g["detail"], dict)
            assert isinstance(g["name"], str) and g["name"]

        # 2 Atome, 1 View im Mini-Vault.
        assert result["atoms"] == 2
        assert result["views"] == 1


class TestHealthyAllGreen:
    def test_healthy_vault_all_six_green(self, healthy_vault):
        """Alle G1-G6 GRUEN, migration_complete True, green_count 6, missing_stage None."""
        result = run_capstone_gate(healthy_vault)
        _assert_all_green(result)

    def test_main_healthy_exit_zero(self, healthy_vault):
        """main(--vault healthy) == 0 (alle 6 gruen, live G4 inklusive)."""
        rc = main(["--vault", str(healthy_vault)])
        assert rc == 0

    def test_main_healthy_out_and_quiet(self, healthy_vault):
        """CLI akzeptiert --out + --quiet; Report-JSON enthaelt das vertragliche Ergebnis."""
        out = healthy_vault / "capstone_report.json"
        rc = main(["--vault", str(healthy_vault), "--out", str(out), "--quiet"])
        assert rc == 0
        assert out.exists(), "--out muss eine Report-Datei schreiben"
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["migration_complete"] is True
        assert data["total"] == 6
        assert data["green_count"] == 6


# ===========================================================================
# G1 — Truths=Nodes (substrat-vollstaendig)
# ===========================================================================

class TestG1Red:
    def test_g1_red_id_local_mismatch(self, tmp_path):
        """A1: local_id 'AX', aber id bleibt 'NS.A1' -> id endet NICHT auf '.AX' -> G1 ROT.
        Die id bleibt NS.A1, damit ALLE edges/referenced_by/scope weiter aufloesen
        (G2/G3/G5/G6 bleiben gruen)."""
        _build_healthy(tmp_path)
        params = dict(_A_PARAMS)
        params["local_id"] = "AX"
        _write_atom(tmp_path, ATOM_A_REL, **params)

        result = run_capstone_gate(tmp_path)
        _assert_only_red(result, "G1")


# ===========================================================================
# G2 — Bidirektionale Edges (forward + referenced_by, 0 dangling)
# ===========================================================================

class TestG2Red:
    def test_g2_red_dangling_edge(self, tmp_path):
        """A1 bekommt eine zusaetzliche forward-edge auf ein NICHT-existentes Atom
        -> dangling > 0 -> G2 ROT. (build_edge_backref_index filtert dangling, daher
        bleibt der referenced_by-Abgleich gruen -> ROT ausschliesslich via dangling.)"""
        _build_healthy(tmp_path)
        params = dict(_A_PARAMS)
        params["edges"] = [
            {"ziel": "NS.B1", "kind": "truth_edge"},
            {"ziel": "NS.NICHTDA", "kind": "truth_edge"},  # dangling
        ]
        _write_atom(tmp_path, ATOM_A_REL, **params)

        result = run_capstone_gate(tmp_path)
        _assert_only_red(result, "G2")

    def test_g2_red_missing_backref(self, tmp_path):
        """Forward A1->B1 existiert, aber B1.referenced_by hat KEIN by:NS.A1
        -> missing_backref > 0 -> G2 ROT. (B1 behaelt seine edge B1->A1, daher
        bleibt A1.referenced_by konsistent -> ROT ausschliesslich via missing_backref.)"""
        _build_healthy(tmp_path)
        params = dict(_B_PARAMS)
        params["referenced_by"] = None  # B1 verliert seinen Rueck-Ref auf A1
        _write_atom(tmp_path, ATOM_B_REL, **params)

        result = run_capstone_gate(tmp_path)
        _assert_only_red(result, "G2")


# ===========================================================================
# G3 — Views-as-Referents (source_atoms bidirektional)
# ===========================================================================

class TestG3Red:
    def test_g3_red_unresolved_source_atom(self, tmp_path):
        """View.source_atoms enthaelt einen Pfad, der nicht existiert
        -> unresolved > 0 -> G3 ROT. (A1 bleibt aufloesbar, View behaelt Quellen.)"""
        _build_healthy(tmp_path)
        _write_view(
            tmp_path,
            VIEW_REL,
            view_id=VIEW_ID,
            source_atoms=[ATOM_A_REL, "Backlog/BL-001/2_Model/truths/GHOST.md"],
        )

        result = run_capstone_gate(tmp_path)
        _assert_only_red(result, "G3")

    def test_g3_red_missing_view_backref(self, tmp_path):
        """View->A1 loest auf, aber A1.referenced_by nennt die View NICHT
        -> missing_view_backref > 0 -> G3 ROT. (A1 behaelt den truth_edge-Rueck-Ref
        auf NS.B1, daher bleibt G2 gruen.)"""
        _build_healthy(tmp_path)
        params = dict(_A_PARAMS)
        params["referenced_by"] = [{"by": "NS.B1", "kind": "truth_edge"}]  # VIEW.Sample entfernt
        _write_atom(tmp_path, ATOM_A_REL, **params)

        result = run_capstone_gate(tmp_path)
        _assert_only_red(result, "G3")


# ===========================================================================
# G4 — FORWARD-GARANTIE aktiv (LIVE)
# ===========================================================================

class TestG4Red:
    def test_g4_red_forward_garantie_inactive(self, healthy_vault, monkeypatch):
        """Strategie MONKEYPATCH: die Forward-Garantie-Engine wird zu no-op (kein
        Referent, kein Write). Der Vault ist ansonsten GESUND -> nur G4 wird ROT,
        G1/G2/G3/G5/G6 (statisch auf dem gesunden Vault) bleiben GRUEN.
        Begruendung der Wahl: siehe _disable_forward_garantie (robust gegen die
        Scoring-Heuristik; die 'kein-keyword-overlap'-Variante waere fragil)."""
        _disable_forward_garantie(monkeypatch)

        result = run_capstone_gate(healthy_vault, live_g4=True)
        _assert_only_red(result, "G4")


# ===========================================================================
# G5 — Loss=0 (content_hash byte-coverage)
# ===========================================================================

class TestG5Red:
    def test_g5_red_corrupt_content_hash(self, tmp_path):
        """A1.content_hash wird um EIN hex-Zeichen verfaelscht (bleibt valides
        64-hex, ist aber != _sha256(text)) -> hash_mismatch > 0 -> G5 ROT.
        content_hash beruehrt kein anderes Gate -> Isolation."""
        _build_healthy(tmp_path)
        real = _sha256(_A_PARAMS["text"])
        corrupt = ("1" if real[0] != "1" else "0") + real[1:]
        assert corrupt != real and len(corrupt) == 64
        params = dict(_A_PARAMS)
        _write_atom(tmp_path, ATOM_A_REL, content_hash=corrupt, **params)

        result = run_capstone_gate(tmp_path)
        _assert_only_red(result, "G5")


# ===========================================================================
# G6 — Navigierbar (wikilinks / edge-index)
# ===========================================================================

class TestG6Red:
    def test_g6_red_missing_wikilink_section(self, tmp_path):
        """A1 HAT forward-edges, aber sein Body hat KEINE Wikilink-Sektion
        -> missing_wikilinks > 0 -> G6 ROT. (Frontmatter/edges/hash unveraendert,
        B1 behaelt seine Sektion -> alle anderen Gates gruen.)"""
        _build_healthy(tmp_path)
        params = dict(_A_PARAMS)
        _write_atom(
            tmp_path,
            ATOM_A_REL,
            body="\n### A1\n\nKein Wikilink-Abschnitt in diesem Body.\n",
            **params,
        )

        result = run_capstone_gate(tmp_path)
        _assert_only_red(result, "G6")


# ===========================================================================
# main() — nonzero auf gebrochenem Vault
# ===========================================================================

class TestMainBroken:
    def test_main_broken_exit_nonzero(self, tmp_path):
        """main(--vault broken) liefert nonzero (nicht alle 6 gruen).
        Verwendet den G5-corrupt-Vault: live G4 bleibt gruen, G5 ROT -> nonzero."""
        _build_healthy(tmp_path)
        real = _sha256(_A_PARAMS["text"])
        corrupt = ("1" if real[0] != "1" else "0") + real[1:]
        params = dict(_A_PARAMS)
        _write_atom(tmp_path, ATOM_A_REL, content_hash=corrupt, **params)

        rc = main(["--vault", str(tmp_path)])
        assert isinstance(rc, int)
        assert rc != 0


# ===========================================================================
# ARTIFACT 3 (BL-491 AC-2) — id-LOSE View via DERIVED view-id (G3-backward)
# ===========================================================================
#
# RED jetzt: das Gate setzt im _load_views noch `id = fm.get("id")` (= None bei
# id-loser View) und check_g3 kennt keinen `views_with_derived_id`-Key. Nach der
# GREEN-Phase nutzt _load_views resolve_view_id(fm, rel) -> die DERIVED id wird
# erkannt (Atom.referenced_by nennt sie) und ein Diagnose-Key wird gemeldet.
#
# Hardcoded derived id (RED-safe: KEIN Import-Dependency auf view_id_convention,
# das erst nach der GREEN-Phase existiert). Konvention: "view::" + vault-rel posix
# path der View. Siehe bl491_ac2_spec.md ARTIFACT 1.
_DERIVED_VIEW_ID = "view::" + VIEW_REL  # "view::Backlog/BL-001/2_Model/Sample_Model.md"


def _write_view_without_id(root, relpath, *, source_atoms, bl=BL, body=None):
    """Wie _write_view, aber OHNE `id`-Feld im Frontmatter (id-lose View —
    parking-lot/arc42-Klasse). source_atoms bleibt vorhanden."""
    fm: dict = {
        "tags": ["type/model"],
        "bl": bl,
        "source_atoms": list(source_atoms),
    }
    if body is None:
        body = (
            "\n# Sample Model (id-los)\n\n"
            "alpha beta gamma delta epsilon zeta eta theta.\n\n"
            "- [[NS.A1|A1]]\n"
        )
    dumped = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    content = f"---\n{dumped}---\n{body}"

    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TestG3DerivedViewId:
    def test_g3_green_via_derived_view_id(self, tmp_path):
        """Gesunder Vault, ABER die View hat KEIN `id` (id-los) und HAT source_atoms
        -> A1. A1.referenced_by nennt die View per DERIVED id (view::<view_rel>,
        kind view_source) PLUS seinen truth_edge-Rueck-Ref (haelt G2 gruen).

        Erwartung NACH GREEN-Wiring: G3 GRUEN (derived id erkannt) und
        G3-detail.views_with_derived_id >= 1.
        RED jetzt: id = None -> missing_view_backref -> G3 ROT, und der detail-Key
        views_with_derived_id existiert noch nicht."""
        _build_healthy(tmp_path)

        # View OHNE id ueberschreiben (source_atoms bleibt -> A1).
        _write_view_without_id(tmp_path, VIEW_REL, source_atoms=[ATOM_A_REL])

        # A1.referenced_by: truth_edge (G2) + view_source via DERIVED id (G3-backward).
        params = dict(_A_PARAMS)
        params["referenced_by"] = [
            {"by": "NS.B1", "kind": "truth_edge"},             # haelt G2 gruen
            {"by": _DERIVED_VIEW_ID, "kind": "view_source"},   # G3-backward via DERIVED id
        ]
        _write_atom(tmp_path, ATOM_A_REL, **params)

        result = run_capstone_gate(tmp_path)

        g3 = _gate(result, "G3")
        assert g3["green"] is True, f"G3 sollte GRUEN sein (derived id erkannt): {g3}"
        assert g3["detail"].get("views_with_derived_id", 0) >= 1, (
            f"G3-detail braucht views_with_derived_id>=1: {g3['detail']}"
        )


# ===========================================================================
# BL-494 family — .claude-Backup-Kopie darf KEINE false G1-id_collision erzeugen
# ===========================================================================
#
# Stage 4 schreibt Atom-Backups nach <vault>/.claude/output/capstone/backref_backup/.
# Das Gate laedt Atome via truth_backref_materialize._iter_truth_atoms (kein .claude-
# Filter heute) -> die Backup-KOPIE wird mitgewalkt -> duplizierte id NS.A1 ->
# verify_all meldet eine id_collision -> G1 faelschlich ROT. Erwartung nach dem Fix:
# der Walker schliesst .claude/** aus -> G1 bleibt GRUEN. RED heute.

class TestG1NoFalseCollisionFromDotClaudeBackup:
    def test_g1_no_false_collision_from_dotclaude_backup(self, tmp_path):
        """Gesunder Mini-Vault -> G1 GRUEN. Dann EINE Atom-Datei 1:1 nach
        <vault>/.claude/output/capstone/backref_backup/ kopiert (duplizierte id NS.A1,
        aber unter .claude = Tooling/Backup, kein Vault-Atom). G1 MUSS GRUEN bleiben:
        die .claude-Kopie darf KEINE id_collision einfuehren.

        FAELLT heute: _iter_truth_atoms walkt die .claude-Kopie mit -> doppelte id
        NS.A1 -> id_collision_count>0 -> G1 ROT. GRUEN nach dem .claude-Filter-Fix.
        live_g4=False, weil dieser Test ausschliesslich das G1-Collision-Verdikt prueft.
        """
        _build_healthy(tmp_path)

        # Vorbedingung: gesunder Vault ist G1-GRUEN.
        before = run_capstone_gate(tmp_path, live_g4=False)
        g1_before = _gate(before, "G1")
        assert g1_before["green"] is True, (
            f"Setup-Fehler: G1 muss vor der .claude-Kopie GRUEN sein: {g1_before}"
        )
        assert g1_before["detail"]["id_collision_count"] == 0, g1_before["detail"]

        # Stage-4-artiges Backup: dieselbe Atom-Datei unter
        # .claude/output/capstone/backref_backup/ (duplizierte id NS.A1).
        src = tmp_path / ATOM_A_REL
        dst = tmp_path / ".claude" / "output" / "capstone" / "backref_backup" / "A1.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

        after = run_capstone_gate(tmp_path, live_g4=False)
        g1_after = _gate(after, "G1")

        assert g1_after["green"] is True, (
            f"G1 darf durch die .claude-Backup-Kopie NICHT ROT werden "
            f"(false id_collision): {g1_after}"
        )
        assert g1_after["detail"]["id_collision_count"] == 0, (
            f"Die .claude-Kopie darf keine id_collision einfuehren: {g1_after['detail']}"
        )
