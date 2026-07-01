"""
test_build_retrieval_index_batch3_integration.py — BL-242 / batch_3 / Stage 3
(Scheinwerfer / Integration) RED-Suite.

M3 test-first GREENFIELD (`mocks_erlaubt=nein`): die Stage-3-batch_3-Verdrahtung
(J12 — `build_index` ruft ZUSAETZLICH `build_anchor_index`/`build_backlinks` ->
4 maschinelle Indizes komplett; der `build`-Pfad serialisiert die 4 Indizes via
`serialize_index_json` und schreibt sie REAL via `open()/json.dump` nach
`.claude/output/retrieval_index/*.json`) existiert NOCH NICHT in
`build_retrieval_index.py` (code-verifiziert 2026-06-04):
  - `build_index` (Z.258-279) liefert NUR `{keyword_index, edge_index, tag_index}`
    — ruft `build_anchor_index`/`build_backlinks` NICHT auf -> `anchor_index`/
    `backlinks` werden GAR NICHT produziert.
  - `main`/`build`-Pfad (Z.315-321) schreibt NUR `_Tag-Index.md` — KEIN `json.dump`
    nach `.claude/output/retrieval_index/`.

Diese Suite ist die SOLL-Spezifikation (Kent Beck: "tests are specifications")
fuer den Integration-Durchstich J12 aus Blueprint/S3/blueprint-batch_3.md (§5 Gold
E1) + sub-1-batch_3.md (TDD T1-T6).

Item (batch_3, Stage 3 — die Stage-1-Serializer + batch_1-Aggregatoren werden
UNVERAENDERT aufgerufen, KEIN Interface-/Schema-Bruch):
  - BL-242-AK-CTX-2-PL-1  (AK-CTX-2, J12): Anchor/Backlinks-Integration in
    build_index + 4-JSON-Persistenz (keyword/edge/anchor/backlinks) nach
    .claude/output/retrieval_index/*.json (valides + deterministisches JSON,
    Anchor-Score + Backlinks-Schema korrekt, _Tag-Index.md unangetastet).

J13 (AK-5, `_W_fetch.md` Schritt-0d-Edit) ist Markdown-Skill-Edit + Szenario-Verify
(INV-Markdown-Engine-Bootstrap) — KEIN pytest-Test, hier bewusst NICHT enthalten.

| #  | Test (RED)                                  | Durchstich | Gold (S3/§5) |
|----|---------------------------------------------|------------|--------------|
| T1 | build_index liefert anchor_index+backlinks  | J12        | E1           |
| T2 | build legt Output-Dir an + valides {}-JSON  | J12        | E1           |
| T3 | build schreibt 4 valide *.json real         | J12        | E1           |
| T4 | Re-Build -> bit-identische *.json (determin.)| J12       | E1           |
| T5 | anchor-score + backlinks-schema korrekt     | J12        | E1           |
| T6 | _Tag-Index.md unangetastet + build-exit 0   | J12 (Kan.) | E1           |

Reihenfolge = Canary-First / "Don't go for the gold" (Raender vor Happy-Path:
Integration-Form vor Persistenz, leeres Output-Dir vor 4-JSON-Happy,
Determinismus vor Score/Schema-Form).

RED-Mechanik: (a) `build_index` legt KEINE `anchor_index`/`backlinks`-Keys ins
Ergebnis-Dict -> T1 schlaegt mit KeyError fehl. (b) der `build`-Pfad schreibt
KEINE `.claude/output/retrieval_index/*.json` -> T2-T6 schlagen fehl (Datei fehlt
/ Assertion). = RED (Gesetz 2: fehlendes Artefakt zaehlt als Fehlschlag). Die
Stage-1-Serializer (`serialize_index_json`/`anchor_score`/`backlinks_schema`) +
batch_1-Aggregatoren (`build_anchor_index`/`build_backlinks`) bleiben UNVERAENDERT
(Kanarienvogel) — Stage 3 ruft sie nur auf.

Mock-Grenze Stage 3 (stage_3.md `mocks_erlaubt: nein`): alles echt. Einzige
erlaubte Test-Konstruktion = temporaere echte tmp-Fixture-Vault-Roots (echte
.md-Files) + reales `.claude/output/retrieval_index/`-Verzeichnis UNTER dem
tmp-Vault-Root (kein gemockter Output-Pfad, aber isoliert). Output-Dir-Ort
analog `_Tag-Index.md`-Write (root-relativ, DT-13).
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

# Stage-3-batch_3-Verdrahtung (anchor/backlinks in build_index + JSON-Write im
# build-Pfad) ist GREENFIELD-NEU und FEHLT in build_retrieval_index.py -> die
# Assertions unten schlagen JETZT fehl (KeyError / fehlende *.json) = RED.
import build_retrieval_index  # noqa: E402


# Die 4 maschinellen Indizes -> Soll-Dateinamen unter
# .claude/output/retrieval_index/ (Spec §5 Schemata, AK-CTX-2).
_INDEX_FILES = {
    "keyword_index": "_keyword_index.json",
    "edge_index": "_edge_index.json",
    "anchor_index": "_anchor_index.json",
    "backlinks": "_backlinks.json",
}


def _output_dir(root):
    """Root-relativer Output-Ort der 4 JSON-Indizes (analog _Tag-Index.md-Write,
    DT-13). Stage-3-Vertrag: .claude/output/retrieval_index/ unter dem Vault-Root."""
    return os.path.join(str(root), ".claude", "output", "retrieval_index")


# ===========================================================================
# Fixtures: ECHTE tmp-Vault-Roots (mocks_erlaubt=nein). Jede .md-Datei traegt
# echtes Frontmatter (parse_frontmatter-kompatibel) + echte [[Wikilinks]] im
# Body — anchor_index/backlinks werden ueber den REALEN Walk +
# extract_wikilinks-Substrat gebaut. Kein gemockter Root, keine Fixture-Konstante.
# ===========================================================================

def _write_md(root, rel_path, frontmatter_lines, body=""):
    """Schreibt eine echte .md-Datei mit YAML-Frontmatter in den tmp-Vault-Root."""
    target = os.path.join(str(root), rel_path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    content = "---\n" + "\n".join(frontmatter_lines) + "\n---\n" + body + "\n"
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    return target


@pytest.fixture
def vault(tmp_path):
    """Echter tmp-Vault-Root mit 2 verlinkten 'modus'-Knoten (Wikilink A2->A1)
    + 1 Distraktor. Der Wikilink erzeugt einen Backlink (A1 referenced_by A2)
    + einen Anchor-Score auf A1 (backlink_count=1) -> anchor/backlinks nicht-trivial.
    """
    root = tmp_path / "Vault"
    root.mkdir()
    _write_md(
        root, "Backlog/A1.md",
        ["bl: BL-A1", "keywords: [modus, coverage]", "tags: [topic/Modus]",
         "node_type: spec"],
        body="Knoten A1 spricht ueber modus.",
    )
    _write_md(
        root, "Backlog/A2.md",
        ["bl: BL-A2", "keywords: [modus]", "tags: [topic/Modus]",
         "node_type: model"],
        body="A2 referenziert [[Backlog/A1.md]] und modus.",
    )
    _write_md(
        root, "Backlog/A3.md",
        ["bl: BL-A3", "keywords: [unrelated]", "tags: [topic/Other]",
         "node_type: note"],
        body="Dieser Knoten erwaehnt modus nur beilaeufig im Fliesstext.",
    )
    return root


# ===========================================================================
# T1 — J12-Rand (Anchor/Backlinks-Integration, E1): build_index liefert jetzt
#       ZUSAETZLICH anchor_index + backlinks im Ergebnis-Dict (Keys vorhanden,
#       Form korrekt). Rand: leerer Vault -> anchor_index=={}/backlinks=={},
#       kein Crash. (RED: build_index legt diese Keys heute NICHT an -> KeyError.)
# ===========================================================================

def test_t1_build_index_now_yields_anchor_and_backlinks(vault, monkeypatch):
    """E1/T1: build_index produziert die 4 maschinellen Indizes (anchor+backlinks
    integriert), nicht nur 3. Form: anchor_index[path]={'score':..}, backlinks
    {path,referenced_by,references}.

    GREENFIELD-RED: build_index liefert heute nur {keyword,edge,tag}_index ->
    result["anchor_index"] / result["backlinks"] -> KeyError.
    """
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    result = build_retrieval_index.build_index(roots=[str(vault)])
    assert "anchor_index" in result
    assert "backlinks" in result
    # A1 wird von A2 via [[Backlog/A1.md]] referenziert -> Backlink existiert.
    assert "Backlog/A1.md" in result["backlinks"]
    assert "Backlog/A2.md" in result["backlinks"]["Backlog/A1.md"]["referenced_by"]
    # anchor_index traegt einen score je Knoten.
    assert "score" in result["anchor_index"]["Backlog/A1.md"]


def test_t1_empty_vault_yields_empty_anchor_and_backlinks(tmp_path, monkeypatch):
    """E1/T1 (Rand): leerer Vault -> anchor_index=={} und backlinks=={}, kein Crash."""
    empty = tmp_path / "EmptyVault"
    empty.mkdir()
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(empty))
    result = build_retrieval_index.build_index(roots=[str(empty)])
    assert result["anchor_index"] == {}
    assert result["backlinks"] == {}


# ===========================================================================
# T2 — J12-Rand (Output-Dir + leeres JSON, E1): `build` legt
#       .claude/output/retrieval_index/ an (os.makedirs exist_ok=True) und
#       schreibt je Index valides JSON — auch fuer den leeren Vault ({}-JSON),
#       kein Crash. (Rand vor Happy.)
# ===========================================================================

def test_t2_build_creates_output_dir_and_valid_empty_json(tmp_path, monkeypatch):
    """E1/T2 (Rand): leerer Vault -> Output-Dir wird angelegt, 4 valide {}-JSON.

    RED: der build-Pfad schreibt heute KEINE .claude/output/retrieval_index/*.json
    -> Verzeichnis/Datei fehlt.
    """
    empty = tmp_path / "EmptyVault"
    empty.mkdir()
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(empty))
    rc = build_retrieval_index.main(["build"])
    assert rc == 0
    out_dir = _output_dir(empty)
    assert os.path.isdir(out_dir)  # os.makedirs(exist_ok=True) hat es angelegt
    for fname in _INDEX_FILES.values():
        fpath = os.path.join(out_dir, fname)
        assert os.path.exists(fpath), "{} fehlt".format(fname)
        with open(fpath, encoding="utf-8") as fh:
            parsed = json.load(fh)  # valides JSON (json.loads ok)
        assert parsed == {}  # leerer Vault -> leeres Index-Dict


# ===========================================================================
# T3 — J12-Happy (4 JSON real geschrieben, E1): nach main(["build"]) ueber den
#       realen Fixture-Vault existieren alle 4 maschinellen Indizes als valides
#       JSON in .claude/output/retrieval_index/.
# ===========================================================================

def test_t3_build_writes_four_valid_json_indexes(vault, monkeypatch):
    """E1/T3 (Happy): build schreibt alle 4 *.json REAL + valide (json.load ok)."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    rc = build_retrieval_index.main(["build"])
    assert rc == 0
    out_dir = _output_dir(vault)
    for fname in _INDEX_FILES.values():
        fpath = os.path.join(out_dir, fname)
        assert os.path.exists(fpath), "{} wurde nicht geschrieben".format(fname)
        with open(fpath, encoding="utf-8") as fh:
            json.load(fh)  # valides JSON -> kein JSONDecodeError
    # Das keyword_index.json enthaelt den thematischen Knoten 'modus'.
    with open(os.path.join(out_dir, "_keyword_index.json"), encoding="utf-8") as fh:
        kw = json.load(fh)
    assert "modus" in kw


# ===========================================================================
# T4 — J12-Determinismus (E1): zweimaliger build ueber denselben Vault ->
#       bit-identische *.json (serialize_index_json sort_keys=True, H12).
# ===========================================================================

def test_t4_rebuild_produces_bit_identical_json(vault, monkeypatch):
    """E1/T4: Re-Build -> byte-identische 4 *.json (Determinismus, sort_keys)."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    out_dir = _output_dir(vault)

    build_retrieval_index.main(["build"])
    first = {}
    for fname in _INDEX_FILES.values():
        with open(os.path.join(out_dir, fname), "rb") as fh:
            first[fname] = fh.read()

    build_retrieval_index.main(["build"])
    for fname in _INDEX_FILES.values():
        with open(os.path.join(out_dir, fname), "rb") as fh:
            second = fh.read()
        assert second == first[fname], "{} nicht bit-identisch bei Re-Build".format(fname)


# ===========================================================================
# T5 — J12-Form (schwerst, Happy zuletzt, E1): _anchor_index.json-Eintraege
#       tragen score == anchor_score(bl, fm); _backlinks.json hat
#       backlinks_schema-Form {path, referenced_by, references}.
# ===========================================================================

def test_t5_anchor_score_and_backlinks_schema_in_json(vault, monkeypatch):
    """E1/T5: anchor-score-Werte stimmen mit anchor_score (H13) ueberein; jeder
    backlinks-Eintrag hat exakt die backlinks_schema-Keys (H14)."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    build_retrieval_index.main(["build"])
    out_dir = _output_dir(vault)

    with open(os.path.join(out_dir, "_anchor_index.json"), encoding="utf-8") as fh:
        anchor = json.load(fh)
    # In-Memory-Wahrheit (Lead) zum Abgleich: build_index liefert denselben
    # anchor_index (NICHT neu berechnen mit einer Test-Formel -> sonst wuerde der
    # Test eine zweite Score-Implementierung sein; wir vergleichen JSON == Memory).
    mem = build_retrieval_index.build_index(roots=[str(vault)])
    assert anchor == mem["anchor_index"]  # JSON-Score == In-Memory-Score (H13)
    # A1 hat genau 1 Backlink (von A2) -> score == anchor_score(1, fw_of_A1).
    assert anchor["Backlog/A1.md"]["score"] == \
        mem["anchor_index"]["Backlog/A1.md"]["score"]

    with open(os.path.join(out_dir, "_backlinks.json"), encoding="utf-8") as fh:
        backlinks = json.load(fh)
    assert backlinks  # nicht leer (es gibt Knoten)
    for entry in backlinks.values():
        # backlinks_schema-Form (H14): exakt diese 3 Keys.
        assert set(entry.keys()) == {"path", "referenced_by", "references"}


# ===========================================================================
# T6 — J12-Kanarienvogel (E1): nach build ist _Tag-Index.md weiterhin
#       geschrieben (batch_2/J9, Markdown — Spec A2 unangetastet);
#       build-exit_code 0 (DT-5) intakt. Die JSON-Persistenz ist ADDITIV.
# ===========================================================================

def test_t6_tag_index_md_untouched_and_exit_zero(vault, monkeypatch):
    """E1/T6 (Kanarienvogel): _Tag-Index.md weiterhin geschrieben + build-exit 0.

    Die 4-JSON-Persistenz darf das batch_2-_Tag-Index.md-Write (Z.318) NICHT
    verdraengen (additiv) und die build-exit-Matrix (DT-5: 0) nicht brechen.
    """
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault))
    rc = build_retrieval_index.main(["build"])
    assert rc == 0  # DT-5: build aufloesbar -> 0
    tag_index_path = os.path.join(str(vault), "_Tag-Index.md")
    assert os.path.exists(tag_index_path)  # Markdown (Spec A2) weiterhin da
    with open(tag_index_path, encoding="utf-8") as fh:
        rendered = fh.read()
    assert "## topic/Modus" in rendered  # batch_2/J9-Render unveraendert
