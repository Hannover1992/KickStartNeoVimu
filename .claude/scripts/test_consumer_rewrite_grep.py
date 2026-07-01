"""
test_consumer_rewrite_grep.py — BL-392 batch_6 (AK-CONSUMER-REWRITE) grep-Vollstaendigkeit.

W-CON-2-Adjudikation (Spec Sec. 0) / AK-CONSUMER-REWRITE DoD-4: ein
grep-Vollstaendigkeits-Check belegt, dass KEIN umgestellter Code-Consumer noch einen
DIREKTEN `.claude/meta/implementation/stage_*`-Glob/-Read in AUSFUEHRBAREM Code traegt —
die Stage-Resolution laeuft ueber die kanonische `resolve_vault_stage`-Resolution
(Dual-Read: Vault-Slice-Satz wenn migriert, sonst Legacy-Monolith).

SCOPE der umgestellten Code-Consumer (per grep gegen die Script-Basis verifiziert,
Task-Message batch_6):
  - t_script.py            (Stage-Test-Ausfuehrung -> execute/setup/teardown-Slice)
  - tdd_stages_ready.py    (Gate-Resolution -> Slice-Set-Validator / Legacy-Fallback)

NICHT-Consumer (grep-verifiziert, KEINE Stage-Datei-Resolution):
  - stage_infra_schema.py  reiner dict-Normalisierer (KEIN File-IO; bekommt bereits
                           geparste setup.commands-Eintraege) -> nichts umzustellen.

Methode: AST-basiert (robust gegen Doc-Strings/Kommentare) — ein direkter Stage-Read
ist ein String-Literal `.claude/meta/implementation/stage_` ODER ein `stage_*`-Glob,
das NICHT in einem Docstring/Kommentar steht. Wir tokenisieren die Quelle und ignorieren
String-Literale, die als Docstring stehen; ausfuehrbare String-Literale mit dem
Legacy-Pfad-Glob duerfen NICHT vorkommen.

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_consumer_rewrite_grep.py     (repo-root)
  py -3 -m pytest test_consumer_rewrite_grep.py                     (scripts-cwd)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

_SCRIPTS = Path(__file__).parent

# Die umgestellten Code-Consumer (batch_6 Scope).
REWRITTEN_CONSUMERS = ("t_script.py", "tdd_stages_ready.py")

# Ein direkter Legacy-Glob ist ein Discovery-Glob ueber das Implementation-Verzeichnis.
_DIRECT_GLOB_MARKERS = (
    ".claude/meta/implementation/stage_*",
    ".claude\\meta\\implementation\\stage_*",
    "meta/implementation/stage_*.md",
)


def _executable_string_literals(source: str) -> list[str]:
    """Alle String-Literale aus AUSFUEHRBAREM Code (Docstrings ausgeschlossen).

    Ein Docstring ist ein Str-Expr als erstes Statement eines Module/Func/Class-Bodys.
    Die sammeln wir NICHT — nur echte ausfuehrbare String-Literale (Glob-Argumente,
    open()-Pfade etc.).
    """
    tree = ast.parse(source)
    docstring_nodes: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                    and isinstance(first.value.value, str):
                docstring_nodes.add(id(first.value))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstring_nodes:
                continue
            out.append(node.value)
    return out


@pytest.mark.parametrize("consumer", REWRITTEN_CONSUMERS)
def test_consumer_imports_resolver(consumer: str) -> None:
    """Jeder umgestellte Consumer nutzt resolve_vault_stage (kanonische Resolution)."""
    src = (_SCRIPTS / consumer).read_text(encoding="utf-8")
    assert "resolve_vault_stage" in src, \
        f"{consumer} muss resolve_vault_stage nutzen (AK-CONSUMER-REWRITE)"


@pytest.mark.parametrize("consumer", REWRITTEN_CONSUMERS)
def test_consumer_has_no_direct_legacy_glob(consumer: str) -> None:
    """KEIN direkter `.claude/meta/implementation/stage_*`-Glob in ausfuehrbarem Code.

    Doc-Strings duerfen den Legacy-Pfad erwaehnen (Erklaerung); ausfuehrbarer Code
    NICHT — die Stage-Resolution laeuft ueber resolve_vault_stage.
    """
    src = (_SCRIPTS / consumer).read_text(encoding="utf-8")
    literals = _executable_string_literals(src)
    for lit in literals:
        for marker in _DIRECT_GLOB_MARKERS:
            assert marker not in lit, (
                f"{consumer}: direkter Legacy-Glob '{marker}' in ausfuehrbarem "
                f"String-Literal gefunden ({lit!r}) — muss ueber resolve_vault_stage laufen."
            )


def test_stage_infra_schema_does_no_file_io() -> None:
    """stage_infra_schema.py ist reiner dict-Normalisierer (KEIN File-IO -> kein Consumer).

    Es liest KEINE Stage-Datei (es bekommt bereits geparste setup.commands-Eintraege),
    also gibt es dort nichts auf resolve_vault_stage umzustellen. Falsifikation: taucht
    ein open()/glob/read_text auf, waere es doch ein Datei-Consumer.
    """
    src = (_SCRIPTS / "stage_infra_schema.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    io_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in {"open", "glob", "iterdir", "read_text", "rglob", "listdir"}:
                io_calls.append(name)
    assert io_calls == [], \
        f"stage_infra_schema.py soll kein File-IO machen (gefunden: {io_calls})"
