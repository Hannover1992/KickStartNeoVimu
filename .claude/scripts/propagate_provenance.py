#!/usr/bin/env python3
"""
propagate_provenance.py -- Bidirektionale Provenance-Verlinkung (Hebb-Pattern)

BL-160 AK-6: Wenn Doc X als derived_from Doc Y referenziert, dann muss Doc Y
automatisch X in used_in haben. Skript synchronisiert beide Seiten.

Aufruf:
    python propagate_provenance.py update <doc_path>
        Liest doc_path. Fuer jedes derived_from-Eintrag: oeffnet Vorgaenger-Doc,
        appended sich selbst in used_in (falls noch nicht drin).

    python propagate_provenance.py validate <vault_root>
        Scannt alle .md-Dateien im vault_root. Findet Bidirectional-Mismatches
        (X derived_from Y aber Y hat X NICHT in used_in).

    python propagate_provenance.py reverse <target>
        Reverse-Lookup: gibt alle Layer von target bis Original-URL aus (Tabelle).
        target kann Vault-Pfad ODER "Code:./service.cs:42" ODER "AK:BL-160:AK-3" sein.
        (Stub fuer AK-4 Reverse-Lookup, hier nur Skelett.)

Exit-Codes:
    0  OK (alle Bidir-Links konsistent)
    1  WARN (Optional-Feld fehlt, nicht-blocking)
    2  ERROR (Bidir-Mismatch, Schema-Violation)
"""

import sys
import os
import argparse
import re
import tempfile
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install via: pip install pyyaml", file=sys.stderr)
    sys.exit(3)

# Regex zum Erkennen von YAML-Frontmatter (---\n...\n---\n)
_FRONTMATTER_RE = re.compile(r"^---\n(.+?)\n---\n(.*)", re.DOTALL)


def _default_vault_root() -> Path:
    """
    Resolvt den Vault-Root via resolve_vault_root.py (vault-routing.json),
    Fallback cwd NUR wenn die Resolution fehlschlaegt.

    BL-310-Fix (2026-06-10): Default war Path.cwd() -- vom Repo-CWD aufgerufen
    wurde das REPO zum 'Vault' (3x Live-FAIL im BL-255-Lauf: spec/kscore/gap).
    Folgefehler: _normalise_path fiel auf absolute Pfade zurueck (falsche
    derived_from/used_in-Annotation). Gleiche Resolution-Familie wie
    guard_geist5/_manifest_resolver.
    """
    try:
        import subprocess
        resolver = Path(__file__).parent / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5,
            )
            if proc.returncode == 0:
                root = proc.stdout.strip()
                if root and Path(root).is_dir():
                    return Path(root)
    except Exception:
        pass
    print(
        "WARN: resolve_vault_root.py nicht verfuegbar -- Fallback auf cwd "
        "(Vault-Root ggf. falsch, explizit --vault-root setzen)",
        file=sys.stderr,
    )
    return Path.cwd()


def read_frontmatter(path: Path) -> tuple[Optional[dict], str]:
    """
    Liest YAML-Frontmatter + Body aus einer Markdown-Datei.

    Rueckgabe: (frontmatter_dict, body_str). Wenn kein Frontmatter vorhanden,
    gibt (None, vollstaendiger_Inhalt) zurueck.
    """
    content = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None, content
    fm_raw, body = match.group(1), match.group(2)
    try:
        fm = yaml.safe_load(fm_raw)
        if not isinstance(fm, dict):
            return None, content
    except yaml.YAMLError as exc:
        print(f"WARN: YAML-Parse-Fehler in {path}: {exc}", file=sys.stderr)
        return None, content
    return fm, body


def write_frontmatter(path: Path, fm: dict, body: str) -> None:
    """
    Schreibt Frontmatter + Body atomisch zurueck (tmp-file + rename).

    Stellt sicher dass kein partieller Schreibzustand entsteht, auch
    bei Unterbrechung.
    """
    fm_str = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    new_content = f"---\n{fm_str}---\n{body}"

    # Atomisches Schreiben: temporaere Datei im gleichen Verzeichnis,
    # dann os.replace (atomic auf POSIX + Windows-NTFS)
    dir_ = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_, prefix=".tmp_prov_", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path, path)
    except Exception:
        # Aufraeumen falls replace fehlschlaegt
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _normalise_path(p: Path, vault_root: Path) -> str:
    """
    Konvertiert einen absoluten Pfad zu einem vault_root-relativen Pfad
    mit Forward-Slashes (Windows-safe).
    """
    try:
        rel = p.relative_to(vault_root)
    except ValueError:
        # Pfad liegt ausserhalb des Vaults -- absoluten Pfad als Fallback
        return str(p).replace("\\", "/")
    return str(rel).replace("\\", "/")


def update_used_in(predecessor_path: Path, successor_path: Path, vault_root: Path) -> bool:
    """
    Oeffnet predecessor_path und appended successor_path in dessen
    provenance_chain[-1]["used_in"] (list-set-Semantik, keine Duplikate).

    Rueckgabe: True wenn eine Aenderung geschrieben wurde.
    """
    fm, body = read_frontmatter(predecessor_path)
    if fm is None:
        print(
            f"WARN: {predecessor_path} hat kein Frontmatter -- used_in-Update uebersprungen",
            file=sys.stderr,
        )
        return False

    chain = fm.get("provenance_chain")
    if not chain or not isinstance(chain, list):
        # Kein provenance_chain vorhanden -- lege Struktur an (WARN, nicht ERROR)
        print(
            f"WARN: {predecessor_path} hat kein provenance_chain -- lege used_in an",
            file=sys.stderr,
        )
        fm.setdefault("provenance_chain", [{}])
        chain = fm["provenance_chain"]

    # Letzten Layer bearbeiten (neuester Eintrag traegt used_in)
    last_layer: dict = chain[-1]
    used_in: list = last_layer.get("used_in", [])
    if not isinstance(used_in, list):
        used_in = []

    successor_rel = _normalise_path(successor_path, vault_root)

    if successor_rel in used_in:
        return False  # Bereits eingetragen, keine Aenderung noetig

    used_in.append(successor_rel)
    last_layer["used_in"] = used_in
    chain[-1] = last_layer
    fm["provenance_chain"] = chain

    write_frontmatter(predecessor_path, fm, body)
    return True


def _is_out_of_vault_source(predecessor_rel: str) -> bool:
    """
    Gibt True zurueck wenn predecessor_rel eine legitim nicht-vault-residenten Quelle
    bezeichnet — kein Bidir-Backlink moeglich, kein Fehler.

    Faelle:
      - {Vault}/{vault}/{VAULT}-Platzhalter (z.B. "{Vault}/some/path")
      - .claude/-Pfade (repo-cwd-relativ, z.B. .claude/pileOfMud/..., .claude/output/...)
    """
    normalized = predecessor_rel.replace("\\", "/")
    if "{Vault}" in predecessor_rel or "{vault}" in predecessor_rel or "{VAULT}" in predecessor_rel:
        return True
    if normalized.startswith(".claude/"):
        return True
    return False


def cmd_update(doc_path: Path, vault_root: Path) -> int:
    """
    Update-Modus: liest doc_path, propagiert derived_from-Eintraege
    als used_in rueckwaerts in alle Vorgaenger-Dokumente.
    """
    if not doc_path.exists():
        print(f"ERROR: {doc_path} existiert nicht", file=sys.stderr)
        return 2

    fm, _body = read_frontmatter(doc_path)
    if fm is None or "provenance_chain" not in fm:
        print(
            f"WARN: {doc_path} hat keine provenance_chain -- nichts zu propagieren",
            file=sys.stderr,
        )
        return 1

    changed = 0
    errors = 0
    skipped_oov = 0

    for layer in fm["provenance_chain"]:
        if not isinstance(layer, dict):
            continue
        for predecessor_rel in layer.get("derived_from", []):
            if _is_out_of_vault_source(predecessor_rel):
                skipped_oov += 1
                continue
            predecessor_path = vault_root / predecessor_rel
            if not predecessor_path.exists():
                print(
                    f"ERROR: derived_from '{predecessor_rel}' nicht gefunden "
                    f"(Vault-Root: {vault_root})",
                    file=sys.stderr,
                )
                errors += 1
                continue
            if update_used_in(predecessor_path, doc_path, vault_root):
                changed += 1
                print(f"  UPDATED used_in: {predecessor_path}")

    if skipped_oov:
        print(
            f"NOTE: {skipped_oov} out-of-vault Quelle(n) uebersprungen "
            f"(pileOfMud/output/{{Vault}} -- keine Bidir-Backlinks moeglich, benign)",
            file=sys.stderr,
        )

    if errors:
        print(f"FAIL: {errors} Fehler, {changed} Bidir-Links propagiert von {doc_path}")
        return 2

    print(f"OK: {changed} Bidir-Links propagiert von {doc_path}")
    return 0


def cmd_validate(vault_root: Path) -> int:
    """
    Validate-Modus: scannt alle .md-Dateien im vault_root auf
    Bidirektionale Mismatches (X derived_from Y aber Y hat X NICHT in used_in).
    """
    if not vault_root.is_dir():
        print(f"ERROR: vault_root '{vault_root}' ist kein Verzeichnis", file=sys.stderr)
        return 2

    mismatches: list[tuple[str, str, str]] = []  # (doc_a, doc_b, grund)
    scanned = 0

    for md_path in sorted(vault_root.rglob("*.md")):
        fm, _ = read_frontmatter(md_path)
        if fm is None or "provenance_chain" not in fm:
            continue
        scanned += 1

        for layer in fm["provenance_chain"]:
            if not isinstance(layer, dict):
                continue
            for pred_rel in layer.get("derived_from", []):
                pred_path = vault_root / pred_rel
                if not pred_path.exists():
                    mismatches.append((
                        _normalise_path(md_path, vault_root),
                        pred_rel,
                        "predecessor_missing",
                    ))
                    continue

                pred_fm, _ = read_frontmatter(pred_path)
                if pred_fm is None:
                    mismatches.append((
                        _normalise_path(md_path, vault_root),
                        pred_rel,
                        "predecessor_no_frontmatter",
                    ))
                    continue

                self_rel = _normalise_path(md_path, vault_root)
                found_in_used_in = False
                for pred_layer in pred_fm.get("provenance_chain", []):
                    if not isinstance(pred_layer, dict):
                        continue
                    if self_rel in pred_layer.get("used_in", []):
                        found_in_used_in = True
                        break

                if not found_in_used_in:
                    mismatches.append((self_rel, pred_rel, "used_in_missing"))

    print(f"Gescannt: {scanned} Docs mit provenance_chain in {vault_root}")

    if mismatches:
        print(f"FAIL: {len(mismatches)} Bidir-Mismatches:")
        for doc_a, doc_b, grund in mismatches[:20]:
            print(f"  {doc_a} -> {doc_b}: {grund}")
        if len(mismatches) > 20:
            print(f"  ... ({len(mismatches) - 20} weitere)")
        return 2

    print("OK: alle Bidir-Links konsistent")
    return 0


def cmd_reverse(target: str, vault_root: Path) -> int:
    """
    Reverse-Lookup: traversiert derived_from-Kette von target bis zum
    Ursprungsdokument (Layer 0 / kein derived_from mehr).

    Skelett-Implementation fuer AK-4. Vollstaendige Impl in BL-160 SB-7.
    Unterstuetzt Vault-Pfad, "Code:./service.cs:42", "AK:BL-160:AK-3".
    """
    print(f"Reverse-Lookup fuer: {target}")
    print("-" * 60)

    # Target-Typ erkennen und in Vault-Pfad aufloesen
    vault_path: Optional[Path] = None

    if target.startswith("Code:"):
        # Format: Code:./relative/path.cs:42  (Zeilennummer optional)
        parts = target[len("Code:"):].split(":")
        code_rel = parts[0]
        line_nr = parts[1] if len(parts) > 1 else None
        # STUB: Code-zu-Vault-Zuordnung noch nicht implementiert
        print(f"STUB AK-4: Code-Referenz '{code_rel}' (Zeile {line_nr}) -- "
              "Vault-Zuordnung benoetigt BL-160 SB-7 Code-Index")
        return 0

    elif target.startswith("AK:"):
        # Format: AK:BL-160:AK-3
        parts = target[len("AK:"):].split(":")
        bl_id = parts[0] if len(parts) > 0 else ""
        ak_id = parts[1] if len(parts) > 1 else ""
        # STUB: AK-zu-Doc-Zuordnung noch nicht implementiert
        print(f"STUB AK-4: Akzeptanzkriterium '{bl_id}/{ak_id}' -- "
              "Vault-Zuordnung benoetigt BL-160 SB-7 AK-Index")
        return 0

    else:
        # Vault-Pfad direkt
        candidate = Path(target)
        if candidate.is_absolute() and candidate.exists():
            vault_path = candidate
        else:
            candidate2 = vault_root / target
            if candidate2.exists():
                vault_path = candidate2

    if vault_path is None:
        print(f"STUB AK-4: Reverse-Lookup fuer '{target}' -- "
              "Vollstaendige Impl in BL-160 SB-7")
        print("Plan: parse target -> finde Vault-Doc -> traversiere derived_from "
              "rueckwaerts bis layer=0")
        return 0

    # Kettentraversal (vereinfacht: folge provenance_chain[0].derived_from[0])
    print(f"{'Layer':<6} {'Dokument':<60} {'Quelle'}")
    print("-" * 100)

    current_path = vault_path
    layer_nr = 0
    visited: set[str] = set()

    while current_path is not None:
        path_key = str(current_path)
        if path_key in visited:
            print(f"WARN: Zyklus erkannt bei {current_path}", file=sys.stderr)
            break
        visited.add(path_key)

        fm, _ = read_frontmatter(current_path)
        rel_display = _normalise_path(current_path, vault_root)
        source_url = ""

        if fm:
            chain = fm.get("provenance_chain", [])
            if chain and isinstance(chain[0], dict):
                source_url = chain[0].get("source_url", "")

        print(f"{layer_nr:<6} {rel_display:<60} {source_url}")

        # Naechsten Vorgaenger suchen
        next_path = None
        if fm:
            for chain_layer in fm.get("provenance_chain", []):
                if not isinstance(chain_layer, dict):
                    continue
                preds = chain_layer.get("derived_from", [])
                if preds:
                    pred_path = vault_root / preds[0]
                    if pred_path.exists():
                        next_path = pred_path
                    break

        current_path = next_path
        layer_nr += 1

    print("-" * 100)
    print(f"STUB AK-4: Vollstaendige Reverse-Lookup-Impl in BL-160 SB-7")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="propagate_provenance",
        description="Bidir Provenance-Propagation (BL-160 AK-6 Hebb-Pattern)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_upd = sub.add_parser("update", help="Propagiere doc-Aenderungen in Predecessors")
    p_upd.add_argument("doc_path", type=Path, help="Pfad zum Nachfolger-Dokument")
    p_upd.add_argument(
        "--vault-root",
        type=Path,
        default=None,
        help="Vault-Wurzelverzeichnis (default: via resolve_vault_root.py, BL-310)",
    )

    p_val = sub.add_parser("validate", help="Scanne Vault auf Bidir-Mismatches")
    p_val.add_argument("vault_root", type=Path, help="Vault-Wurzelverzeichnis")

    p_rev = sub.add_parser(
        "reverse",
        help="Reverse-Lookup target -> Original-URL (Skelett fuer AK-4)",
    )
    p_rev.add_argument(
        "target",
        type=str,
        help="Vault-Pfad, 'Code:./file.cs:42', oder 'AK:BL-160:AK-3'",
    )
    p_rev.add_argument(
        "--vault-root",
        type=Path,
        default=None,
        help="Vault-Wurzelverzeichnis (default: via resolve_vault_root.py, BL-310)",
    )

    args = parser.parse_args()

    # BL-310: --vault-root nicht explizit gesetzt -> via vault-routing resolven (NIE blind cwd)
    if getattr(args, "vault_root", None) is None and args.cmd in ("update", "reverse"):
        args.vault_root = _default_vault_root()

    if args.cmd == "update":
        return cmd_update(args.doc_path, args.vault_root)
    elif args.cmd == "validate":
        return cmd_validate(args.vault_root)
    elif args.cmd == "reverse":
        return cmd_reverse(args.target, args.vault_root)

    return 0


if __name__ == "__main__":
    sys.exit(main())
