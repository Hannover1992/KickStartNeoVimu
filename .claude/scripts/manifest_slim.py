#!/usr/bin/env python3
"""manifest_slim.py — BL-229 AK-A/A1/C/CTX-1: Round-granulares Manifest-Slim-Tool.

Produktisiert den battle-tested 06-05-GC-Workflow (Map -> Split -> Verify) als robustes
wiederverwendbares Tool. Verwandelt ein degeneriertes Report-Manifest (DCSRE-486: 703 KB /
13k Zeilen) zurueck in einen schlanken Sync-Zustand: behalte den KOMPLETTEN State der
LETZTEN Round je Familie ("nackter Zustand"), lagere nur FRUEHERE Rounds verlustfrei aus.

NICHT keep-last-block-per-family (fragmentiert -> items_routed_ready-Verlust, Pilot-Beweis),
NICHT greedy block-span manifest_gc.py (over-capturing, haette round15-YAML zerrissen,
W-EMP-3 / AK-CTX-3). Round-granular = die hoechste Round-Instanz je Familie bleibt zusammen.

Harte Invariante (AK-A1, W-INV-1, 486-Race-Beweis 2026-05-30): VOR jedem destruktiven Write
ruft das Tool manifest_quiescence.require_quiescent — Lock ODER bewiesene Quiescenz, NICHT
durch User-Autorisierung ersetzbar. 3 Gates (AK-A): MD5-lossless / currentStatePresent /
missing=leer. Bei Gate-Verletzung -> Abort + Rollback, KEIN partieller Write.

Usage:
  py -3 manifest_slim.py slim BL-229 [--dry-run] [--manifest PATH] [--worker-id ID]
    exit 0 = Slim erfolgreich (3 Gates GREEN), 1 = Gate verletzt / nicht quiescent (Rollback).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# AK-A1/AK-E: das Quiescenz-Hard-Gate als Pre-Condition (W-INV-1, 486-Race-Schutz).
from manifest_quiescence import require_quiescent  # noqa: F401  (monkeypatch-Anker in Tests)

# BL-336: Format-Version-Generations-Guard. `rfv`-Alias ist der Monkeypatch-Anker in
# Tests (manifest_slim.rfv.read_format_version / .resolve_format_version).
import resolve_format_version as rfv  # noqa: F401

# AK-C: State-Familien-Keywords kanonisch aus guard_manifest_antibloat.py:28-31 (Single-Source).
FAMILY_KEYWORDS = ("BERATER_OUTPUTS", "PIPELINE_STATE", "BATCH_STATE",
                   "PHASE_3_STATE", "FINAL_SUMMARY", "POST_SDF")

# Round-Identitaet: `(Round N)`, `_roundN` oder versionierte Orphan-Marker (`vN-orphan`).
_ROUND_PAREN = re.compile(r"\(\s*Round\s*(\d+)", re.IGNORECASE)
_ROUND_SUFFIX = re.compile(r"_round(\d+)", re.IGNORECASE)
_ROUND_VERSION = re.compile(r"\bv(\d+)-orphan", re.IGNORECASE)

# AK-CTX-1: maschinenlesbarer Zweck-Header (ersetzt die gescheiterte Prosa-Konvention
# 2026-05-13 durch Header + Guard; W-AK-A, W-IST-4).
PURPOSE_HEADER_MARKER = "<!-- MANIFEST-PURPOSE: nackter Zustand zum Sync, KEIN Report (BL-229 AK-CTX-1) -->"


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


class Block:
    """Ein `## Header ... Body`-Span im Manifest (bis zum naechsten `## `-Header).

    (BL-229 AK-A, 2026-06-10)
    """

    __slots__ = ("family", "header", "text", "round_ord", "is_working_set")

    def __init__(self, family: str, header: str, text: str, round_ord: int):
        self.family = family
        self.header = header
        self.text = text
        self.round_ord = round_ord
        self.is_working_set = False  # wird in map_rounds gesetzt


def _round_ordinal(header: str) -> int:
    """Round-Ordinalzahl aus dem Header extrahieren (hoechste gefundene Zahl).

    (Round 8) / _round8 / v8-orphan -> 8. Bare-canonical (kein Marker) -> 0.
    (BL-229 AK-A, 2026-06-10)
    """
    ords = []
    for rx in (_ROUND_PAREN, _ROUND_SUFFIX, _ROUND_VERSION):
        m = rx.search(header)
        if m:
            ords.append(int(m.group(1)))
    return max(ords) if ords else 0


def _family_of(header: str) -> str:
    """Familien-Name = erstes Token nach `## ` ohne den parenthetisierten Descriptor.

    `## BERATER_OUTPUTS.modelSync (recluster v6-orphan ...)` -> `BERATER_OUTPUTS.modelSync`.
    (BL-229 AK-A, 2026-06-10)
    """
    name = header[3:].strip()  # `## ` weg
    # parenthetisierten / bracketed Descriptor abschneiden
    for sep in (" (", "  [", " ["):
        idx = name.find(sep)
        if idx != -1:
            name = name[:idx]
    return name.strip()


def _is_state_family(family: str) -> bool:
    return any(k in family for k in FAMILY_KEYWORDS)


def _split_blocks(content: str):
    """Manifest in (preamble, [Block,...]) zerlegen — Block-Grenze = `## `-Header.

    (BL-229 AK-A, 2026-06-10)
    """
    lines = content.splitlines(keepends=True)
    preamble: list[str] = []
    blocks: list[Block] = []
    cur_header = None
    cur_body: list[str] = []

    def flush():
        if cur_header is not None:
            text = cur_header + "".join(cur_body)
            family = _family_of(cur_header)
            blocks.append(Block(family, cur_header.rstrip("\n"), text, _round_ordinal(cur_header)))

    for line in lines:
        if line.startswith("## "):
            flush()
            cur_header = line
            cur_body = []
        elif cur_header is None:
            preamble.append(line)
        else:
            cur_body.append(line)
    flush()
    return "".join(preamble), blocks


def _mark_working_set(blocks: list) -> dict:
    """Setzt is_working_set auf der GEGEBENEN Block-Liste (in-place) + gruppiert nach Familie.

    Working-Set = die hoechste (= letzte) Round-Instanz je Familie. Bei nicht-State-Familien
    (kein Round-Marker, max_ord==0) bleibt der Block ohnehin erhalten (round-granular, nichts
    auszulagern). Nur frueher-Round-State-Familien sind Garbage. (BL-229 AK-A, 2026-06-10)
    """
    families: dict[str, list[Block]] = {}
    for b in blocks:
        families.setdefault(b.family, []).append(b)
    for group in families.values():
        max_ord = max(b.round_ord for b in group)
        for b in group:
            b.is_working_set = (b.round_ord == max_ord)
    return families


def map_rounds(content: str) -> dict:
    """MAP: Bloecke nach Familie gruppieren; hoechste Round-Instanz je Familie = Working-Set.

    Returns: {family: [Block,...]} wobei genau die Block(s) mit max round_ord
    is_working_set=True tragen. (BL-229 AK-A, 2026-06-10)
    """
    _, blocks = _split_blocks(content)
    return _mark_working_set(blocks)


def verify_split(original: str, kept: str, archived: str, archive_md5: str,
                 live_markers: list | None = None):
    """VERIFY: 3 Gates. -> (all_pass: bool, report: dict).

    (1) lossless    : archive_md5 == md5(archived) (kein Datenverlust beim Auslagern).
    (2) currentState: alle Live-Marker der letzten Round sind im behaltenen Slim vorhanden.
    (3) missing     : keine nicht-leere Original-Zeile, die WEDER in kept NOCH in archived steht.
    (BL-229 AK-A, 2026-06-10)
    """
    report: dict = {}

    # Gate 1: MD5-lossless
    report["lossless"] = (archive_md5 == _md5(archived))

    # Gate 2: currentStatePresent
    markers = live_markers or []
    missing_markers = [m for m in markers if m not in kept]
    report["currentStatePresent"] = (len(missing_markers) == 0)
    report["missing_markers"] = missing_markers

    # Gate 3: missing=leer — jede nicht-leere Original-Zeile muss in kept oder archived sein.
    kept_lines = set(l for l in kept.splitlines() if l.strip())
    arch_lines = set(l for l in archived.splitlines() if l.strip())
    seen = kept_lines | arch_lines
    missing = [l for l in original.splitlines() if l.strip() and l not in seen]
    report["missing"] = missing

    all_pass = report["lossless"] and report["currentStatePresent"] and not missing
    return all_pass, report


def offload_history(content: str, manifest_path, history_date: str | None = None):
    """AK-C: fruehere-Round State-Familien-Snapshots -> _manifest_history_{date}.md.

    Verlustfreies Archiv mit MD5 (OQ-2 RESOLVED, KEIN Hard-Delete). Behaelt nur den
    Working-Set (letzte Round je Familie) im Manifest; alles aeltere wandert ins Archiv.
    -> {kept, archived, archive_md5, archive_path}. (BL-229 AK-C, 2026-06-10)
    """
    manifest_path = Path(manifest_path)
    history_date = history_date or datetime.now().strftime("%Y-%m-%d")
    preamble, blocks = _split_blocks(content)
    # Working-Set auf DERSELBEN Block-Liste markieren (kein id()-Mismatch ueber Aufrufe).
    _mark_working_set(blocks)

    kept_parts: list[str] = []
    archived_parts: list[str] = []
    for b in blocks:
        # Nur frueher-Round State-Familien sind Garbage; Working-Set + Nicht-State bleiben.
        if b.is_working_set or not _is_state_family(b.family):
            kept_parts.append(b.text)
        else:
            archived_parts.append(b.text)

    kept = preamble + "".join(kept_parts)
    archived = "".join(archived_parts)
    archive_md5 = _md5(archived)
    archive_path = manifest_path.parent / f"_manifest_history_{history_date}.md"

    return {
        "kept": kept,
        "archived": archived,
        "archive_md5": archive_md5,
        "archive_path": _write_archive(archive_path, archived, archive_md5, history_date),
    }


def _write_archive(archive_path: Path, archived: str, archive_md5: str, history_date: str) -> Path:
    """Archiv-Datei schreiben (verlustfrei, mit MD5-Header). (BL-229 AK-C, 2026-06-10)"""
    head = (
        f"# Manifest-Historie (ausgelagert {history_date})\n\n"
        f"<!-- BL-229 AK-C: verlustfreies Round-Archiv, MD5={archive_md5} -->\n\n"
    )
    archive_path.write_text(head + archived, encoding="utf-8")
    return archive_path


def _collect_live_markers(families: dict) -> list:
    """Live-Marker = nicht-leere Body-Zeilen der Working-Set-State-Bloecke.

    Diese MUESSEN das Slim ueberleben (currentStatePresent-Gate). (BL-229 AK-A, 2026-06-10)
    """
    markers: list[str] = []
    for group in families.values():
        for b in group:
            if b.is_working_set and _is_state_family(b.family):
                body = b.text[len(b.header):]
                markers.extend(l for l in body.splitlines() if l.strip())
    return markers


def _extract_frontmatter(content: str) -> str:
    """Top-Level-Frontmatter-Block (zwischen den ersten beiden `---`).

    Kein Fence -> leerer FM-String (read_format_version gibt dann 0 zurueck).
    Analog _read_frontmatter in health_orchestrate.py. (BL-336)
    """
    if not content.startswith("---"):
        return ""
    end = content.find("\n---", 3)
    if end == -1:
        return ""
    return content[3:end]


def _assert_manifest_generation(content: str) -> None:
    """BL-336 Generations-Guard: VOR jedem Map/Write die Manifest-Generation pruefen.

    Liest die erkannte Generation (ist) aus dem Frontmatter + die zustaendige
    Soll-Generation (resolve_format_version("manifest")) und entscheidet:
      - soll is None              -> PROCEED (Dual-Read-Resilienz, fehlende Registry nie Crash)
      - ist == soll               -> PROCEED (zustaendige Generation, normaler slim-Lauf)
      - ist == 0 (ungestempelt)   -> PROCEED + stderr-WARN (Gen-0-Policy, least-stall)
      - ist > 0 und ist != soll   -> SAFE-ABORT (RuntimeError, KEIN Byte-Write)

    Gen-0-Policy (BL-336, Lead-Review-Verbindlich): Stempelung ist noch nicht universal
    gewired (ALLE Bestands-Manifeste sind Gen-0). Ein hartes Abort-on-Gen-0 wuerde die
    Fabrik stallen. Darum: ungestempelt -> PROCEED (Dual-Read; der lossless-verify-Gate
    schuetzt interim) + Stempelungs-Empfehlung. SAFE-ABORT NUR auf explizit gestempelte
    FREMDE Generation ohne registrierte Migration — das ist der echte
    "inkompatible Generation"-Fall (1944-Klasse). Strikter Abort auf ungestempelte
    Alt-STRUKTUR ist Follow-up, sobald die Stempelung universal gewired ist.

    Gleiches "kein destruktiver Write"-Prinzip wie der require_quiescent-Abbruch:
    raised VOR jedem Manifest-Write. (BL-336)
    """
    fm = _extract_frontmatter(content)
    ist = rfv.read_format_version(fm)          # ungestempelt -> 0, NIE Crash
    soll = rfv.resolve_format_version("manifest")  # None = Registry nicht aufloesbar
    if soll is None or ist == soll:
        return
    if ist == 0:
        # Ungestempeltes Gen-0-Manifest: proceed (least-stall), Stempelung empfohlen.
        print(
            "[SLIM-GEN BL-336] WARN: ungestempeltes Manifest (Gen-0); empfehle stempeln "
            "via /_health_orchestrate stamping_heiler. slim laeuft (Dual-Read), aber "
            "Stempelung empfohlen.",
            file=sys.stderr,
        )
        return
    # ist > 0 und ist != soll: explizit gestempelte FREMDE Generation -> echter Abort-Fall.
    raise RuntimeError(
        f"[SLIM-GEN BL-336] Manifest-Generation inkompatibel: erkannte Generation {ist}, "
        f"erwartete Generation {soll} -> SAFE-ABORT, kein partieller Write. "
        f"Erst stempeln via /_health_orchestrate stamping_heiler, dann erneut slimmen."
    )


def slim_manifest(bl_id: str, manifest_path, dry_run: bool = False,
                  worker_id: str | None = None, vault_root: str | None = None,
                  settle_seconds: float = 2.0):
    """AK-A Kern: Map -> Split -> Verify (+ AK-A1 Pre-Gate, AK-CTX-1 Header).

    1. AK-A1: require_quiescent — bei nicht-Quiescenz raise (kein Byte veraendert).
    2. MAP/SPLIT via offload_history (Working-Set behalten, frueher-Round auslagern).
    3. VERIFY 3 Gates; bei Verletzung -> RuntimeError (kein partieller Write).
    4. WRITE: Zweck-Header + Working-Set; vorher Backup (Rollback-Faehigkeit).
    -> {gates, kept_path, archive_path, dry_run}. (BL-229 AK-A/A1/CTX-1, 2026-06-10)
    """
    manifest_path = Path(manifest_path)
    content = manifest_path.read_text(encoding="utf-8")

    # ── 0. BL-336: Generations-Guard VOR Quiescenz + jedem Map/Write. ──
    # SAFE-ABORT bei fremder Manifest-Generation (ungestempelt/alt) statt Traceback.
    _assert_manifest_generation(content)

    # ── 1. AK-A1: Quiescenz-Pre-Gate VOR jedem Map/Write (W-INV-1). ──
    # Modul-globaler Name (monkeypatch-bar in Tests) — raised bei fremder Lock/mtime-instabil.
    require_quiescent(manifest_path, bl_id=bl_id,
                      self_worker_id=worker_id, vault_root=vault_root,
                      settle_seconds=settle_seconds)

    # ── 2. MAP + SPLIT ──
    families = map_rounds(content)
    live_markers = _collect_live_markers(families)
    off = offload_history(content, manifest_path)
    kept_body = off["kept"]

    # AK-CTX-1: Zweck-Header in den Kopf des geslimmten Manifests.
    kept = _inject_purpose_header(kept_body)

    # ── 3. VERIFY 3 Gates (auf dem finalen kept inkl. Header) ──
    all_pass, report = verify_split(
        original=content, kept=kept, archived=off["archived"],
        archive_md5=off["archive_md5"], live_markers=live_markers,
    )
    gates = {
        "lossless": report["lossless"],
        "currentStatePresent": report["currentStatePresent"],
        "missing": report["missing"],
    }
    if not all_pass:
        # Bei dry_run wurde nichts geschrieben; sonst noch kein Manifest-Write erfolgt
        # (Backup/WRITE kommen erst nach PASS). Kein Rollback noetig — nur Archiv aufraeumen.
        if not dry_run and off["archive_path"].exists():
            off["archive_path"].unlink()
        raise RuntimeError(
            f"[SLIM-GATE BL-229 AK-A] Verify fehlgeschlagen fuer {bl_id}: "
            f"lossless={gates['lossless']} currentStatePresent={gates['currentStatePresent']} "
            f"missing={len(gates['missing'])} Zeile(n) -> ABORT, kein partieller Write."
        )

    if dry_run:
        # Archiv-Probe wieder entfernen (dry-run veraendert nichts).
        if off["archive_path"].exists():
            off["archive_path"].unlink()
        return {"gates": gates, "kept_path": manifest_path,
                "archive_path": off["archive_path"], "dry_run": True}

    # ── 4. WRITE mit Backup (Rollback-Faehigkeit) ──
    backup = manifest_path.parent / (
        f"{manifest_path.stem}.bak_{datetime.now().strftime('%Y-%m-%d')}_pre_split.md"
    )
    shutil.copy2(manifest_path, backup)
    manifest_path.write_text(kept, encoding="utf-8")

    return {"gates": gates, "kept_path": manifest_path,
            "archive_path": off["archive_path"], "backup_path": backup, "dry_run": False}


def _inject_purpose_header(content: str) -> str:
    """AK-CTX-1: Zweck-Header nach der Frontmatter (oder ganz oben) einfuegen.

    (BL-229 AK-CTX-1, 2026-06-10)
    """
    if PURPOSE_HEADER_MARKER in content:
        return content
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            cut = content.find("\n", end + 1)
            cut = cut + 1 if cut != -1 else len(content)
            return content[:cut] + "\n" + PURPOSE_HEADER_MARKER + "\n" + content[cut:]
    return PURPOSE_HEADER_MARKER + "\n" + content


def _cli(argv=None):
    ap = argparse.ArgumentParser(description="BL-229 AK-A Manifest-Slim-Tool (round-granular)")
    sub = ap.add_subparsers(dest="cmd")
    ps = sub.add_parser("slim")
    ps.add_argument("bl_id")
    ps.add_argument("--manifest", default=None, help="Manifest-Pfad (default: via resolve_bl_path)")
    ps.add_argument("--dry-run", action="store_true")
    ps.add_argument("--worker-id", default=None)
    ps.add_argument("--vault-root", default=None)
    ps.add_argument("--settle", type=float, default=2.0)
    args = ap.parse_args(argv)

    if args.cmd != "slim":
        ap.print_help()
        return 2

    manifest = args.manifest
    if manifest is None:
        try:
            import resolve_bl_path
            folder = resolve_bl_path.resolve_bl_path(args.bl_id)
            manifest = str(Path(folder) / "_manifest.md")
        except Exception as e:
            print(f"ERROR: Manifest-Pfad nicht aufloesbar ({e})", file=sys.stderr)
            return 1

    try:
        result = slim_manifest(
            args.bl_id, manifest_path=manifest, dry_run=args.dry_run,
            worker_id=args.worker_id, vault_root=args.vault_root, settle_seconds=args.settle,
        )
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    g = result["gates"]
    tag = "DRY-RUN" if result["dry_run"] else "DONE"
    print(f"[SLIM {tag}] {args.bl_id}: lossless={g['lossless']} "
          f"currentStatePresent={g['currentStatePresent']} missing={len(g['missing'])} "
          f"archive={result['archive_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
