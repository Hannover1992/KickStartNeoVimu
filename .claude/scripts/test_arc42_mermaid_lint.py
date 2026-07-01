"""Tests fuer arc42_mermaid_lint.py (BL-378 AK-3). Lead-verify aus Repo-Root."""
import arc42_mermaid_lint as lint


def _ok(code):
    assert lint.lint_block(code) == [], lint.lint_block(code)


def _bad(code):
    assert lint.lint_block(code) != []


# --- valide Bloecke (kein false-RED) ---
def test_valid_flowchart():
    _ok("flowchart TD\n  A[Start] --> B[Ende]")


def test_valid_graph_lr():
    _ok("graph LR\n  A --> B")


def test_valid_sequence():
    _ok("sequenceDiagram\n  A->>B: Anfrage\n  B-->>A: Antwort")


def test_valid_er_relationship():
    _ok("erDiagram\n  CUSTOMER ||--o{ ORDER : places")


def test_valid_er_entity_only():
    _ok("erDiagram\n  CUSTOMER {\n    string name\n  }")


def test_valid_class():
    _ok("classDiagram\n  class Foo {\n    +bar()\n  }")


def test_valid_state_v2():
    _ok("stateDiagram-v2\n  [*] --> Idle\n  Idle --> Run")


def test_valid_mindmap():
    _ok("mindmap\n  root((arc42))\n    Kontext\n    Bausteine")


def test_c4_rejected_no_c4_policy():
    # User-Direktive 2026-06-16: kein C4, nur reines Mermaid -> C4Context = unbekannter Typ (geflaggt).
    _bad('C4Context\n  Person(u, "User")\n  System(s, "Sys")')


def test_comment_before_header_ok():
    _ok("%% Kontextdiagramm\nflowchart LR\n  A --> B")


# --- harte Defekte (muessen flaggen) ---
def test_empty_block():
    _bad("   \n   ")


def test_unknown_type():
    _bad("foobar\n  A --> B")


def test_unbalanced_brackets():
    _bad("flowchart TD\n  A[unclosed --> B")


def test_unbalanced_quotes():
    _bad('flowchart TD\n  A["offen --> B')


def test_sequence_without_arrow():
    _bad("sequenceDiagram\n  participant A")


def test_er_without_anything():
    _bad("erDiagram")


# --- Extraktion + Datei-Ebene ---
def test_extract_two_blocks():
    md = "x\n```mermaid\nflowchart TD\n A-->B\n```\ny\n```mermaid\ngraph LR\n C-->D\n```\n"
    assert len(lint.extract_mermaid_blocks(md)) == 2


def test_lint_text_mixed_fails():
    md = "```mermaid\nflowchart TD\n A-->B\n```\n```mermaid\nfoobar\n```\n"
    res = lint.lint_text(md)
    assert res["block_count"] == 2
    assert res["ok"] is False


def test_lint_text_no_blocks_ok():
    res = lint.lint_text("nur prosa, kein diagramm")
    assert res["block_count"] == 0
    assert res["ok"] is True
