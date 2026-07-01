#!/usr/bin/env python3
"""test_no_import_time_sys_exit.py -- Hygiene-Guard (BL-345 AK-3).

Verhindert die Wiederkehr der BL-345-Klasse: ein Test-Modul mit einem
import-zeitig erreichbaren ``sys.exit(...)`` (auf Modul-Ebene, NICHT in einer
Funktion/Klasse und NICHT im ``if __name__ == "__main__":``-Block) kippt die
GESAMTE pytest-Bulk-Collection (``INTERNALERROR> SystemExit``).

Dieser Guard scannt per AST alle ``.claude/scripts/**/test_*.py`` und meldet
jeden Aufruf von ``sys.exit`` / ``os._exit`` / ``exit`` / ``quit`` /
``raise SystemExit``, der auf Modul-Ebene ausserhalb eines
``if __name__ == "__main__":``-Guards steht (== import-zeitig erreichbar).

Standalone-Runner-Konvention: die self-test-Demo + ihr ``sys.exit`` gehoeren
in den ``__main__``-Block — nicht auf Modul-Ebene.
"""
import ast
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SELF_NAME = Path(__file__).name


def _is_dunder_main_guard(node: ast.If) -> bool:
    """True wenn der If-Knoten ein ``if __name__ == "__main__":``-Guard ist."""
    test = node.test
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return False
    if not isinstance(test.ops[0], ast.Eq):
        return False
    left, right = test.left, test.comparators[0]
    name_side = None
    str_side = None
    for side in (left, right):
        if isinstance(side, ast.Name) and side.id == "__name__":
            name_side = side
        elif isinstance(side, ast.Constant) and side.value == "__main__":
            str_side = side
    return name_side is not None and str_side is not None


def _exit_call_label(node: ast.AST):
    """Gibt ein Label zurueck wenn node ein Prozess-Exit ist, sonst None."""
    if isinstance(node, ast.Raise):
        exc = node.exc
        if isinstance(exc, ast.Name) and exc.id == "SystemExit":
            return "raise SystemExit"
        if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.func.id == "SystemExit":
            return "raise SystemExit(...)"
        return None
    if isinstance(node, ast.Call):
        func = node.func
        # sys.exit(...) / os._exit(...)
        if isinstance(func, ast.Attribute):
            if func.attr == "exit" and isinstance(func.value, ast.Name) and func.value.id == "sys":
                return "sys.exit(...)"
            if func.attr == "_exit" and isinstance(func.value, ast.Name) and func.value.id == "os":
                return "os._exit(...)"
        # bare exit(...) / quit(...)
        if isinstance(func, ast.Name) and func.id in ("exit", "quit"):
            return f"{func.id}(...)"
    return None


def _find_module_level_exits(tree: ast.Module):
    """Liefert [(lineno, label)] aller import-zeitig erreichbaren Exits.

    Import-zeitig erreichbar = auf Modul-Ebene ODER in einem Modul-Ebenen-
    Kontrollfluss-Block (if/for/while/try), ABER NICHT innerhalb einer
    Funktion/Klasse und NICHT im ``if __name__ == "__main__":``-Guard.
    """
    hits = []

    def walk_stmts(stmts):
        for stmt in stmts:
            # __main__-Guard: gesamter Body ist NICHT import-zeitig -> ueberspringen.
            if isinstance(stmt, ast.If) and _is_dunder_main_guard(stmt):
                continue
            # Funktions-/Klassen-Defs: deren Inhalt laeuft nicht beim Import.
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            # Direkter Exit-Ausdruck auf dieser Ebene?
            if isinstance(stmt, ast.Expr):
                label = _exit_call_label(stmt.value)
                if label:
                    hits.append((stmt.lineno, label))
            if isinstance(stmt, ast.Raise):
                label = _exit_call_label(stmt)
                if label:
                    hits.append((stmt.lineno, label))
            # Modul-Ebenen-Kontrollfluss: rekursiv (bleibt import-zeitig erreichbar).
            if isinstance(stmt, ast.If):
                walk_stmts(stmt.body)
                walk_stmts(stmt.orelse)
            elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
                walk_stmts(stmt.body)
                walk_stmts(stmt.orelse)
            elif isinstance(stmt, ast.With):
                walk_stmts(stmt.body)
            elif isinstance(stmt, ast.Try):
                walk_stmts(stmt.body)
                for handler in stmt.handlers:
                    walk_stmts(handler.body)
                walk_stmts(stmt.orelse)
                walk_stmts(stmt.finalbody)

    walk_stmts(tree.body)
    return hits


def _scan_offenders():
    offenders = {}
    for path in sorted(SCRIPTS_DIR.rglob("test_*.py")):
        if path.name == SELF_NAME:
            continue
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        hits = _find_module_level_exits(tree)
        if hits:
            offenders[path] = hits
    return offenders


def test_no_test_module_has_import_time_sys_exit():
    """Kein test_*.py-Modul darf ein import-zeitig erreichbares sys.exit haben."""
    offenders = _scan_offenders()
    if offenders:
        lines = []
        for path, hits in offenders.items():
            for lineno, label in hits:
                lines.append(f"  {path}:{lineno}  {label}")
        detail = "\n".join(lines)
        raise AssertionError(
            "Import-zeitig erreichbares Prozess-Exit in Test-Modul(en) gefunden "
            "(kippt pytest-Bulk-Collection, BL-345). Verlagere die Modul-Ebenen-"
            "Ausfuehrung + Exit in einen 'if __name__ == \"__main__\":'-Block:\n"
            + detail
        )


if __name__ == "__main__":
    test_no_test_module_has_import_time_sys_exit()
    print("PASS: kein import-zeitig erreichbares sys.exit in Test-Modulen (BL-345 AK-3)")
