"""
test_build_retrieval_index_batch2_integration.py — BL-242 / batch_2 / Stage 3
(Scheinwerfer / Integration) RED-Suite.

M3 test-first GREENFIELD (`mocks_erlaubt=nein`): die Stage-3-Verdrahtung
(`main(argv)` + argparse-CLI-Haut + `build`-Orchestrator: reale
`vault-routing.json`-Root-Resolution via Lead `resolve_vault_root`, realer
2-Vault-Walk, tatsaechliches `{VAULT}/_Tag-Index.md`-File-Write, realer
`grep`-Subprozess als AK-4-Baseline) existiert NOCH NICHT in
`build_retrieval_index.py` (code-verifiziert 2026-06-04: KEIN `def main`,
KEIN `argparse`, KEIN `if __name__`, KEIN `build`-Orchestrator). Diese Suite
ist die SOLL-Spezifikation (Kent Beck: "tests are specifications") fuer die
vier Integration-Durchstiche J8-J11 + die CLI-exit_code-Matrix aus
Blueprint/S3/blueprint-batch_2.md (§5 Gold E1-E5) + sub-1-batch_2.md (TDD T1-T8).

Items (batch_2, Stage 3 — die 4 reinen Stage-1-Fn werden UNVERAENDERT aufgerufen):
  - BL-242-AK-CTX-1-PL-1  (AK-CTX-1, J8):  Cross-Vault-`build` (resolve -> Walk -> merge), SOA-1 Single-Vault graceful
  - BL-242-AK-2-PL-1      (AK-2, J9):      `_Tag-Index.md` TATSAECHLICH aufs FS schreiben (echtes open()/write())
  - BL-242-AK-4-PL-1      (AK-4, J10):     `query --term=modus` schlaegt REALEN grep-Subprozess (query ⊆ thematisch ∧ |query| < |grep|)
  - BL-242-AK-6-PL-1      (AK-6, J11):     `--incremental --path=X` patcht nur X-Eintraege; exit 1 bei Pfad nicht im Vault

Mock-Grenze Stage 3 (stage_3.md `mocks_erlaubt: nein`): alles echt. Einzige
erlaubte Test-Konstruktion = temporaere echte tmp-Fixture-Vault-Roots (echte
.md-Files in echten tmp-Verzeichnissen) + via Lead `resolve_vault_root`
(Stufe 1 ENV CLAUDE_VAULT_ROOT) aufgeloest. KEINE gemockten Roots, KEINE
Fixture-Konstante fuer das, was Stage 1 als Konstante mockte, KEIN Mock<grep>.

| #  | Test (RED)                         | Durchstich | Gold (S3/§5) |
|----|------------------------------------|------------|--------------|
| T1 | CLI-Haut main()/argparse-Skeleton  | CLI        | E5           |
| T2 | J8-SOA-1 (1 Root) + leerer Vault    | J8         | E1           |
| T3 | J8-Happy (2-Vault-Merge, vault_origin) | J8      | E1           |
| T4 | J9 reales _Tag-Index.md-File-Write  | J9         | E2           |
| T5 | J11 exit-1-Rand (Pfad nicht im Vault) | J11      | E4           |
| T6 | J11-Happy (Patch-Isolation, Rest bit-identisch) | J11 | E4    |
| T7 | J10 query vs. REALER grep-Subprozess | J10       | E3           |
| T8 | CLI exit_code-Matrix (DT-5: 0/1/2)  | CLI        | E5           |

Reihenfolge = Canary-First / "Don't go for the gold" (Raender vor Happy-Path,
kritischer Pfad CLI+J8 zuerst, J10 realer grep schwerst-testbar zuletzt).

RED-Mechanik: `build_retrieval_index` hat KEIN `main`/`build_index`-Symbol ->
die Aufrufe unten schlagen JETZT fehl (AttributeError) = RED (Gesetz 2:
fehlendes Symbol zaehlt als Fehlschlag). Die 4 reinen Stage-1-Fn + batch_1-
Aggregatoren bleiben UNVERAENDERT (Kanarienvogel) — Stage 3 ruft sie nur auf.
"""

import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

# Stage-3-Verdrahtung (main(argv) + build-Orchestrator) ist GREENFIELD-NEU und
# FEHLT in build_retrieval_index.py -> die main()/build_index()-Aufrufe unten
# loesen AttributeError aus = RED.
import build_retrieval_index  # noqa: E402


# ===========================================================================
# Fixtures: ECHTE tmp-Vault-Roots (mocks_erlaubt=nein). Jede .md-Datei traegt
# echtes Frontmatter (parse_frontmatter-kompatibel: simple key: value /
# key: [list]) — keyword_index/edge_index/tag_index werden ueber den REALEN
# Walk gebaut. Kein gemockter Root, keine Fixture-Index-Konstante.
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
def vault_a(tmp_path):
    """Echter tmp-Vault-Root A mit 2 thematischen 'modus'-Knoten + 1 Distraktor."""
    root = tmp_path / "VaultA"
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
    # Distraktor: enthaelt das Wort 'modus' nur im Fliesstext (grep findet es,
    # der praezise keyword/graph-Walk NICHT) -> beweist |query| < |grep|.
    _write_md(
        root, "Backlog/A3.md",
        ["bl: BL-A3", "keywords: [unrelated]", "tags: [topic/Other]",
         "node_type: note"],
        body="Dieser Knoten erwaehnt modus nur beilaeufig im Fliesstext.",
    )
    return root


@pytest.fixture
def vault_b(tmp_path):
    """Echter tmp-Vault-Root B mit einem 'modus'-Knoten (Cross-Vault-Merge)."""
    root = tmp_path / "VaultB"
    root.mkdir()
    _write_md(
        root, "Backlog/B1.md",
        ["bl: BL-B1", "keywords: [modus]", "tags: [topic/Modus]",
         "node_type: spec"],
        body="VaultB-Knoten ueber modus.",
    )
    return root


# ===========================================================================
# T1 — CLI-Haut (E5): main(argv) + argparse-Subcommand-Skeleton existiert
#       (Canary-First: kritischer Pfad CLI zuerst). Lead-Vorbild:
#       resolve_vault_root.py:155 `def main(argv) -> int`.
# ===========================================================================

def test_cli_main_exists_and_dispatches_build(vault_a, monkeypatch):
    """E5/T1: `main(["build"])` existiert + ist ein int-Returner (DT-5).

    GREENFIELD-RED: build_retrieval_index hat KEIN `main` -> AttributeError.
    Resolution via Lead resolve_vault_root Stufe 1 (ENV CLAUDE_VAULT_ROOT).
    """
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault_a))
    rc = build_retrieval_index.main(["build"])
    assert isinstance(rc, int)
    assert rc == 0  # build ueber aufloesbaren Root -> Erfolg


# ===========================================================================
# T2 — J8-SOA-1 (E1): nur 1 Root aufloesbar -> Single-Vault-Build, kein Crash,
#       vault_origin korrekt. + leerer Vault -> kein Crash. (Rand zuerst.)
# ===========================================================================

def test_j8_soa1_single_vault_graceful(vault_a, monkeypatch):
    """E1/T2 (SOA-1): genau 1 aufloesbarer Root -> Single-Vault-Index, kein Crash.

    Jeder Eintrag traegt vault_origin == VaultA-Root; keine VaultB-Eintraege.
    """
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault_a))
    result = build_retrieval_index.build_index(roots=[str(vault_a)])
    kw_index = result["keyword_index"]
    assert "modus" in kw_index
    # Exakt die 2 thematischen Knoten A1+A2 (nicht der 'unrelated'-Distraktor A3)
    assert len(kw_index["modus"]) == 2
    origins = {e.get("vault_origin") for e in kw_index["modus"]}
    assert origins == {str(vault_a)}  # nur VaultA, Single-Vault graceful


def test_j8_empty_vault_does_not_crash(tmp_path, monkeypatch):
    """E1/T2 (Rand): leerer Vault-Root -> kein Crash, leere/triviale Indizes."""
    empty = tmp_path / "EmptyVault"
    empty.mkdir()
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(empty))
    result = build_retrieval_index.build_index(roots=[str(empty)])
    # Vollstaendig leerer Durchstich: ALLE drei Indizes leer (kein Crash, keine
    # Teil-Materialisierung) — nicht nur keyword_index.
    assert result["keyword_index"] == {}
    assert result["edge_index"] == {}
    assert result["tag_index"] == {}


# ===========================================================================
# T3 — J8-Happy (E1): 2 reale Roots -> 1 gemergter Cross-Vault-Index mit
#       korrektem vault_origin; gemeinsamer Key -> konkatenierte Liste.
# ===========================================================================

def test_j8_cross_vault_merge_sets_vault_origin(vault_a, vault_b, monkeypatch):
    """E1/T3 (Happy): build ueber 2 Roots -> merge mit vault_origin ∈ {A, B}."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault_a))
    result = build_retrieval_index.build_index(roots=[str(vault_a), str(vault_b)])
    kw_index = result["keyword_index"]
    assert "modus" in kw_index
    origins = {e.get("vault_origin") for e in kw_index["modus"]}
    # gemeinsamer Key 'modus' cross-vault -> beide Origins, Listen konkateniert
    assert origins == {str(vault_a), str(vault_b)}
    # Exakt A1+A2 (VaultA) + B1 (VaultB) = 3 konkatenierte Eintraege (kein
    # Drop, kein Dup) — praezise statt untere Schranke.
    assert len(kw_index["modus"]) == 3


# ===========================================================================
# T4 — J9 (E2): nach build existiert {VAULT}/_Tag-Index.md als ECHTE Datei,
#       re-einlesbar, jeder Tag hat eine Sektion (echtes open()/write()).
# ===========================================================================

def test_j9_writes_real_tag_index_file(vault_a, monkeypatch):
    """E2/T4: build schreibt {VaultA}/_Tag-Index.md TATSAECHLICH aufs FS."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault_a))
    build_retrieval_index.main(["build"])
    tag_index_path = os.path.join(str(vault_a), "_Tag-Index.md")
    assert os.path.exists(tag_index_path)  # KEINE Fixture-Konstante — echtes File
    with open(tag_index_path, encoding="utf-8") as fh:
        rendered = fh.read()
    # Frontmatter-Tag 'topic/Modus' (aus A1/A2) hat eine eigene Sektion ...
    assert "## topic/Modus" in rendered
    # ... und diese Sektion listet BEIDE referenzierenden Files (Living-Doc:
    # der Tag-Index dokumentiert wer den Tag traegt, nicht nur dass er existiert).
    assert "Backlog/A1.md" in rendered
    assert "Backlog/A2.md" in rendered


# ===========================================================================
# T5 — J11 exit-1-Rand (E4): --incremental --path=X mit X NICHT im Vault
#       -> exit 1. (Rand vor Happy.)
# ===========================================================================

def test_j11_incremental_path_not_in_vault_exits_1(vault_a, monkeypatch):
    """E4/T5: --incremental --path=<nicht im Vault> -> exit 1 (DT-5)."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault_a))
    build_retrieval_index.main(["build"])
    rc = build_retrieval_index.main(
        ["--incremental", "--path=Backlog/DOES_NOT_EXIST.md"]
    )
    assert rc == 1


# ===========================================================================
# T6 — J11-Happy (E4): --incremental --path=X patcht nur X-Eintraege; alle
#       anderen Index-Eintraege bit-identisch zum Vor-Patch-Zustand.
# ===========================================================================

def test_j11_incremental_patches_only_target_path(vault_a, monkeypatch):
    """E4/T6: --incremental --path=A2.md aendert nur A2-Eintraege, Rest identisch."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault_a))
    before = build_retrieval_index.build_index(roots=[str(vault_a)])
    rc = build_retrieval_index.main(["--incremental", "--path=Backlog/A2.md"])
    assert rc == 0
    after = build_retrieval_index.build_index(roots=[str(vault_a)])
    # 'coverage' kommt nur in A1 vor (nicht A2) -> bit-identisch nach A2-Patch
    assert after["keyword_index"].get("coverage") == \
        before["keyword_index"].get("coverage")


# ===========================================================================
# T7 — J10 (E3): query --term=modus ueber REAL gebauten Index schlaegt einen
#       REALEN grep-Subprozess. query ⊆ thematisch UND |query| < |grep|.
#       (Happy-Path, schwerst-testbar, zuletzt. mocks_erlaubt=nein -> echter grep.)
# ===========================================================================

def _real_grep_hits(root, term):
    """REALER Subprozess: zaehlt Files die `term` im Roh-Text enthalten.

    Bevorzugt `grep -rl` (Unix); faellt auf einen echten Python-Subprozess
    zurueck, falls grep auf der Plattform fehlt (Windows-CI). KEIN Konstanten-
    Mock — immer ein echter externer Prozess ueber den realen Fixture-Vault.
    """
    grep = shutil.which("grep")
    if grep:
        proc = subprocess.run(
            [grep, "-rl", term, str(root)],
            capture_output=True, text=True, timeout=30,
        )
        return [ln for ln in proc.stdout.splitlines() if ln.strip()]
    # Fallback: echter python-Subprozess (kein In-Process-Mock)
    snippet = (
        "import sys,os;t=sys.argv[1];r=sys.argv[2];"
        "[print(os.path.join(d,f)) for d,_,fs in os.walk(r) for f in fs "
        "if f.endswith('.md') and t in open(os.path.join(d,f),encoding='utf-8').read()]"
    )
    proc = subprocess.run(
        [sys.executable, "-c", snippet, term, str(root)],
        capture_output=True, text=True, timeout=30,
    )
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def test_j10_query_precision_beats_real_grep(vault_a, monkeypatch):
    """E3/T7: query('modus') ⊆ thematisch UND echt < realer grep-Trefferzahl.

    grep findet auch den Fliesstext-Distraktor A3 (keyword 'unrelated'); die
    praezise query soll A3 NICHT zurueckgeben -> |query| < |grep|.
    """
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault_a))
    built = build_retrieval_index.build_index(roots=[str(vault_a)])
    query_hits = build_retrieval_index.query(
        "modus", built["keyword_index"], built["edge_index"]
    )
    grep_hits = _real_grep_hits(vault_a, "modus")

    # query ⊆ thematische Knoten: kein Treffer stammt aus dem Distraktor A3
    query_paths = {
        (h.get("path") if isinstance(h, dict) else h) for h in query_hits
    }
    assert all("A3" not in str(p) for p in query_paths)
    # Praezision: echt weniger Treffer als der rohe grep-Subprozess
    assert len(query_hits) < len(grep_hits)


# ===========================================================================
# T8 — CLI exit_code-Matrix (E5, DT-5): build 0/1/2, query 0/1,
#       --incremental 0/1 ueber main(argv) assertbar.
# ===========================================================================

def test_t8_cli_exit_code_matrix(vault_a, monkeypatch):
    """E5/T8: exit_code-Matrix der Subcommands korrekt (DT-5: 0/1/2)."""
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(vault_a))
    # build ueber aufloesbaren Root -> 0
    assert build_retrieval_index.main(["build"]) == 0
    # query mit Treffer -> 0
    assert build_retrieval_index.main(["query", "--term=modus"]) == 0
    # query ohne Treffer -> 1
    assert build_retrieval_index.main(["query", "--term=gibtsnicht_xyz"]) == 1


# ===========================================================================
# BL-494 / Stage-6 fix (approach a) — explizites `--root` (Alias `--vault`)
# ueberschreibt resolve_vault_root. OmniCommand-Verhalten (arg-loser Pfad)
# UNVERAENDERT. RED-Mechanik: main() kennt KEIN --root/--vault -> argparse
# verwirft das Flag (SystemExit 2) bzw. faellt auf resolve_vault_root zurueck
# und schreibt in den falschen Root. Tests 1/2/4 schlagen JETZT fehl; Test 3
# (Backward-Compat, kein --root) ist Regressions-Wache und besteht heute schon.
#
# | #  | Test (RED)                                   | Erwartung |
# |----|----------------------------------------------|-----------|
# | 1  | --root schlaegt Resolver                     | RED       |
# | 2  | --vault-Alias identisch                      | RED       |
# | 3  | kein --root -> Resolver (Backward-Compat)    | GREEN     |
# | 4  | --root honoriert auch wenn Resolver wirft    | RED       |
# ===========================================================================

def test_bl494_explicit_root_overrides_resolver(tmp_path, monkeypatch):
    """BL-494 T1: explizites --root schlaegt resolve_vault_root.

    CLAUDE_VAULT_ROOT zeigt auf resolver_dir, --root auf foreign_dir ->
    der build MUSS in foreign_dir schreiben, NICHT in resolver_dir.
    RED: main() ignoriert/verwirft --root -> schreibt resolver_dir.
    """
    resolver_dir = tmp_path / "ResolverVault"
    resolver_dir.mkdir()
    foreign_dir = tmp_path / "ForeignVault"
    foreign_dir.mkdir()
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(resolver_dir))

    rc = build_retrieval_index.main(["build", "--root", str(foreign_dir)])
    assert rc == 0
    assert (foreign_dir / "_Tag-Index.md").exists() is True
    assert (resolver_dir / "_Tag-Index.md").exists() is False


def test_bl494_vault_alias_behaves_identically(tmp_path, monkeypatch):
    """BL-494 T2: --vault ist Alias fuer --root -> schreibt ebenfalls foreign_dir.

    RED: main() kennt KEIN --vault -> argparse verwirft das Flag.
    """
    resolver_dir = tmp_path / "ResolverVault"
    resolver_dir.mkdir()
    foreign_dir = tmp_path / "ForeignVault"
    foreign_dir.mkdir()
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(resolver_dir))

    rc = build_retrieval_index.main(["build", "--vault", str(foreign_dir)])
    assert rc == 0
    assert (foreign_dir / "_Tag-Index.md").exists() is True
    assert (resolver_dir / "_Tag-Index.md").exists() is False


def test_bl494_backward_compat_no_root_uses_resolver(tmp_path, monkeypatch):
    """BL-494 T3 (Regressions-Wache): main(["build"]) OHNE --root schreibt in
    den Resolver-Root (= heutiges Verhalten, MUSS unveraendert bleiben).

    GREEN heute: der arg-lose Pfad ist Backward-Compat und darf nie brechen.
    """
    resolver_dir = tmp_path / "ResolverVault"
    resolver_dir.mkdir()
    monkeypatch.setenv("CLAUDE_VAULT_ROOT", str(resolver_dir))

    rc = build_retrieval_index.main(["build"])
    assert rc == 0
    assert (resolver_dir / "_Tag-Index.md").exists() is True


def test_bl494_explicit_root_does_not_consult_resolver(tmp_path, monkeypatch):
    """BL-494 T4: bei explizitem --root wird resolve_vault_root NIE konsultiert.

    resolve_vault_root wird auf eine werfende Funktion gepatcht; main(["build",
    "--root", foreign]) MUSS trotzdem rc 0 liefern + foreign schreiben (beweist:
    der Resolver wird bei gegebenem --root nicht aufgerufen).
    RED: main() ruft resolve_vault_root unbedingt (bzw. argparse verwirft --root).
    """
    foreign_dir = tmp_path / "ForeignVault"
    foreign_dir.mkdir()

    def _boom(*args, **kwargs):
        raise RuntimeError("resolver must not be consulted when --root is given")

    monkeypatch.setattr(build_retrieval_index, "resolve_vault_root", _boom)

    rc = build_retrieval_index.main(["build", "--root", str(foreign_dir)])
    assert rc == 0
    assert (foreign_dir / "_Tag-Index.md").exists() is True
