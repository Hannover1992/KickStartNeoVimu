#!/usr/bin/env python3
"""arc42_mermaid_lint.py -- pragmatischer, dependency-freier Mermaid-Lint (BL-378 AK-3).

Validiert ```mermaid-Bloecke in arc42-Sektionsdateien STRUKTURELL (kein node/mmdc noetig):
Block-Extraktion, bekannter Diagrammtyp, nicht-leer, Klammer-/Quote-Balance, per-Typ-Minimalform.
Ziel: still kaputtes Rendering fangen, OHNE false-RED -> nur HARTE Defekte werden gemeldet
(Direction/Tabs etc. werden bewusst NICHT geflaggt, um korrekt-gruene Diagramme nicht zu zerhacken).

CLI:  py -3 arc42_mermaid_lint.py <datei.md> [<datei2.md> ...]
      exit 0 = alle Bloecke valide ; exit 2 = mind. 1 Defekt ; exit 3 = Datei fehlt/usage.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Bekannte Mermaid-Diagrammtypen (erstes Token der ersten signifikanten Zeile).
# User-Direktive 2026-06-16: NUR reines Mermaid + Markdown — KEIN C4. C4* steht bewusst NICHT in
# KNOWN_TYPES -> ein C4-Block wird als "unbekannter Diagrammtyp" geflaggt (No-C4-Enforcement).
# C4-Semantik (Context/Container/Component/Deployment) wird via flowchart+subgraph ausgedrueckt.
KNOWN_TYPES = {
    "flowchart", "graph", "sequenceDiagram", "stateDiagram", "stateDiagram-v2",
    "classDiagram", "erDiagram", "mindmap", "journey", "gantt", "pie",
    "gitGraph", "timeline", "quadrantChart", "requirementDiagram", "sankey-beta",
}

# Nur diese Typen nutzen ()[]{} als echte Knoten-Form-Paare -> Klammer-Balance ist hier zuverlaessig.
# erDiagram (Kardinalitaet o{ }| |{ }o) + mindmap (Cloud-/Shape-Syntax )text() machen naive Balance
# zu false-RED -> dort uebersprungen (no-false-RED-Doktrin).
BRACKET_CHECK_TYPES = {
    "flowchart", "graph", "classDiagram", "stateDiagram", "stateDiagram-v2",
}

_FENCE_RE = re.compile(r"```mermaid[ \t]*\r?\n(.*?)```", re.DOTALL)
_SEQ_ARROW_RE = re.compile(r"--?>>?|--?x|--?\)")          # ->  -->  ->>  -->>  -x  --x  -)  --)
_FLOW_EDGE_RE = re.compile(r"-\.-+>?|==+>|--+>?")          # -->  ---  -.->  ==>
_ER_REL_RE = re.compile(r"\|\||\}o|o\{|\}\||\|\{|--|\{")  # ||--o{ etc. ODER Entitaets-Block {


def extract_mermaid_blocks(markdown: str) -> list:
    """Alle ```mermaid-Bloecke (roher Code zwischen den Fences)."""
    return [m.group(1) for m in _FENCE_RE.finditer(markdown)]


def _first_significant_line(code: str) -> str:
    for raw in code.splitlines():
        line = raw.strip()
        if not line or line.startswith("%%"):
            continue
        return line
    return ""


def _balanced(code: str):
    """(klammern_ok, quotes_ok) -- Klammern nur AUSSERHALB von \"...\" zaehlen."""
    pairs = {")": "(", "]": "[", "}": "{"}
    openers = set(pairs.values())
    stack = []
    in_quote = False
    quote_count = 0
    for ch in code:
        if ch == '"':
            in_quote = not in_quote
            quote_count += 1
            continue
        if in_quote:
            continue
        if ch in openers:
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                return False, (quote_count % 2 == 0)
            stack.pop()
    return (len(stack) == 0), (quote_count % 2 == 0)


def lint_block(code: str) -> list:
    """Harte Defekte eines einzelnen Mermaid-Blocks (leere Liste = valide)."""
    if not code.strip():
        return ["leerer mermaid-Block"]

    issues = []
    header = _first_significant_line(code)
    token = header.split()[0] if header else ""
    if token not in KNOWN_TYPES:
        issues.append("unbekannter Diagrammtyp: %r" % token)

    brackets_ok, quotes_ok = _balanced(code)
    if token in BRACKET_CHECK_TYPES and not brackets_ok:
        issues.append("unbalancierte Klammern ()[]{}")
    if not quotes_ok:
        issues.append('unbalancierte Anfuehrungszeichen "')

    # Per-Typ-Minimalform (nur eindeutig-kaputte Faelle).
    if token == "sequenceDiagram" and not _SEQ_ARROW_RE.search(code):
        issues.append("sequenceDiagram ohne Nachricht/Pfeil")
    if token == "erDiagram" and not _ER_REL_RE.search(code):
        issues.append("erDiagram ohne Entitaet/Beziehung")
    if token in ("flowchart", "graph"):
        if not _FLOW_EDGE_RE.search(code) and not re.search(r"\w+\s*[\[\(\{]", code):
            issues.append("flowchart/graph ohne Kante oder Knoten")
    if token == "mindmap":
        sig = [s for s in (x.strip() for x in code.splitlines()) if s and not s.startswith("%%")]
        if len(sig) < 2:
            issues.append("mindmap ohne Kind-Knoten")
    return issues


def lint_text(markdown: str) -> dict:
    blocks = extract_mermaid_blocks(markdown)
    per_block = [lint_block(b) for b in blocks]
    return {
        "block_count": len(blocks),
        "issues": per_block,
        "ok": all(len(i) == 0 for i in per_block),
    }


def lint_file(path) -> dict:
    res = lint_text(Path(path).read_text(encoding="utf-8"))
    res["path"] = str(path)
    return res


def main(argv) -> int:
    if len(argv) < 2:
        print("usage: arc42_mermaid_lint.py <datei.md> [...]", file=sys.stderr)
        return 3
    any_fail = False
    for arg in argv[1:]:
        p = Path(arg)
        if not p.is_file():
            print("ERROR: Datei fehlt: %s" % p, file=sys.stderr)
            return 3
        res = lint_file(p)
        if res["ok"]:
            print("OK: %s (%d mermaid-Bloecke valide)" % (p, res["block_count"]))
        else:
            any_fail = True
            print("FAIL: %s" % p)
            for idx, iss in enumerate(res["issues"]):
                if iss:
                    print("  Block %d: %s" % (idx + 1, "; ".join(iss)))
    return 2 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
