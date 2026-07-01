#!/usr/bin/env python3
"""pattern_library.py — deterministischer Add/Consult/Lifecycle-Motor fuer die Pattern-Libraries.

MOTIVATION (DCSRE-486-Audit 2026-06-02): der bestehende Capture-Pfad (promoteFromPL -> Kandidaten-Liste
-> _PT_extract -> materialisieren) ist mehrstufig + leck (~80 Signale -> ~4 gelandet). Dieser Motor macht
den Add EINSTUFIG + vault-resolved + konsistent.

BL-237 (Living Pattern System): der Reifungs-Counter existierte NUR als Prosa-Pseudocode in _PT_update.md
(Grep usage_count/broken_count ueber .claude/scripts = 0 Treffer). AK-COUNTER-0 materialisiert ihn hier
als EINE parametrisierte Funktion (scope-Parameter statt 3-4 Klone). _PT_update.md verweist darauf.
VERBOTEN: subprocess(_PT_update.md) — Markdown ist physisch nicht aufrufbar (C-2).

CLI:
  py -3 pattern_library.py next-id   --arch --layer BE-DOMAIN
  py -3 pattern_library.py add       --arch --layer BE-DOMAIN --name "Enum singular" [--tags a,b ...]
  py -3 pattern_library.py add       --semantic --layer BE-DOMAIN --target terms --name "ZEVSP" --description "..."
  py -3 pattern_library.py lifecycle PT-DOM-005 --pfad 1 --scope arch                  # usage++/promote
  py -3 pattern_library.py lifecycle PT-DOM-005 --pfad 2 --scope arch --broken-context X --broken-reason Y
  py -3 pattern_library.py migrate   --scope arch                                       # Bestands-Backfill
  py -3 pattern_library.py find      "enum"
  py -3 pattern_library.py list      --arch --layer BE-DOMAIN

Vault via resolve_vault_root.py (Override: CLAUDE_VAULT_ROOT / --vault-root).
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

LAYER_SHORT = {
    "BE-DOMAIN": "DOM", "BE-CORE": "CORE", "BE-CONT": "CONT", "BE-DTO": "DTO",
    "BE-MAP": "MAP", "BE-MID": "MID", "BE-AUTH": "AUTH", "BE-TEST": "TEST",
    "BE-MIGRATION": "MIG",
    "COMMANDS": "CMD",                     # AC-3 (BL-477) — schliesst die Prefix-Drift PT-COMMANDS -> PT-CMD
}

# ── Kanonisches Reife-Vokabular (BL-237 AK-VOCAB-0, bestaetigt 2026-06-02) ──
# SINGLE-SOURCE fuer den Counter — Schema-treu zu _PT_update.md (BL-154-Lifecycle).
#   Felder: usage_count, broken_count, status(experimental|active|PROVEN|deprecated),
#           status_promoted_at, boundary_notes[], broken_locations[], derived_from, variants[]
#   maturity = usage_count - broken_count (ABGELEITET, kein Frontmatter-Feld) — fuers Ranking.
#   APPEND-ONLY / irreversibel: kein Decrement, kein Status-Rollback (PROVEN->experimental verboten).
THRESH_ACTIVE = 5       # experimental -> active  (usage_count >=)
THRESH_PROVEN = 10      # active -> PROVEN         (usage_count >=)
THRESH_DEPRECATE = 3    # broken_count >=          -> auto-deprecate

# ── DOMAIN-GATE Design-Notiz (BL-237 batch_C4 AK-CTX-DOMAIN-GATE-PL-1, vor-entschieden) ──
# VERDIKT (fixiert, NICHT neu aufrollen): Die FACHLICHE/Domain-Achse bekommt eine EIGENE
# DomainLibrary (spiegelnd zu PatternLibrary), Factoring eine eigene FactoringLibrary — und wird
# AUSDRUECKLICH **NICHT** auf die A-Pipeline geroutet (C-1).
# Ableitung: W-AXIS-1/W-AXIS-2 (STRUKTUR vs FACHLICH/Domain sind orthogonale Diskriminatoren) +
# W-AXIS-3 (classify-Realitaet 3-Achsen, Domain als eigenstaendiger Diskriminator, code-grounded
# batch_C3b) + GOAL/SOA-2 (HiL-Design-Gate, hil=off -> GOAL-Verdikt uebernommen). STOP-Bedingung(1)
# (Nicht-Ableitbarkeit) greift NICHT — das Verdikt ist aus W-AXIS-1/2/3 + GOAL eindeutig ableitbar.
# Konsequenz im Code: _SCOPE_LIB mappt domain->DomainLibrary + factoring->FactoringLibrary (eigene
# Ordner unter Libraries/), KEIN A-Pipeline-Delegations-Pfad. Ein A-Pipeline-Routing fuer Domain
# waere eine DOMAIN-GATE-Verletzung. (Reine Design-Notiz, kein zusaetzlicher Code.)
#
# scope -> Library (AK-COUNTER-0 parametrisiert; DomainLibrary/FactoringLibrary via AK-7 bootstrappt)
_SCOPE_LIB = {"arch": "PatternLibrary", "domain": "DomainLibrary",
              "factoring": "FactoringLibrary", "semantic": "SemanticLibrary"}

# scope -> numbered-ID-Prefix (BL-237 batch_C4 F1/F3 — der 4-kind-add-Enabler).
# F2/F4-grounded (OBSERVE5): add_arch traegt bereits scope ins Frontmatter; NUR _layer_dir/next_id
# waren arch-fix. Dieser Map schliesst die scope->ID-Prefix-Luecke (F3) OHNE 3x-Klon:
# domain->DOM-, factoring->FAC- spiegeln arch->PT- (deterministisch, kollisionsfrei, analog next_id).
# Reuse-not-rebuild (DoD-21): die ID-Vergabe wird parametrisiert, nicht dupliziert. arch bleibt
# bit-identisch (default-Prefix PT, default-Scope arch).
_SCOPE_ID_PREFIX = {"arch": "PT", "domain": "DOM", "factoring": "FAC"}

# Counter-Felder mit Defaults (AK-SCHEMA-0: add schreibt sie ab Geburt; AK-MIG-0: Backfill)
_COUNTER_DEFAULTS = [
    ("status", "experimental"), ("usage_count", "0"), ("broken_count", "0"),
    ("boundary_notes", "[]"), ("broken_locations", "[]"),
    ("derived_from", "null"), ("variants", "[]"),
]


# ── Vault / Library Resolution (fixt den 486 "war leer"-Bug) ──
def resolve_vault_root(override=None) -> Path:
    # BL-374 AK-1/2: einzige kanonische Quelle (resolve_vault_root.py, ARCH-N8 SSoT) statt lokalem
    # 4-tier-Re-Impl. KEIN hardcoded OmniCommand-Fallback (Cross-Projekt-Contamination), KEIN
    # silent-swallow. override gewinnt (tier-1, AK-3 stuetzt sich darauf); sonst delegiert an den
    # kanonischen Resolver (deckt CLAUDE_VAULT_ROOT-env + .vault_root + vault-routing + cwd-Heuristik).
    # ImportError (SSoT fehlt) propagiert = fail-safe: lieber lauter Fehler als falsch-geratener
    # Library-Write.
    if override:
        return Path(override)
    import resolve_vault_root as rvr   # kanonische SSoT (ARCH-N8) — KEIN except:pass mehr
    return Path(rvr.resolve_vault_root())


def library_root(kind: str, vault_root=None) -> Path:
    # kind ist "arch"|"semantic" (Backward-Compat) ODER ein scope aus _SCOPE_LIB.
    name = _SCOPE_LIB.get(kind, "PatternLibrary" if kind == "arch" else "SemanticLibrary")
    return resolve_vault_root(vault_root) / "Libraries" / name


def _layer_dir(kind: str, layer: str, vault_root=None) -> Path:
    return library_root(kind, vault_root) / "_project" / layer


def _short(layer: str) -> str:
    return LAYER_SHORT.get(layer, layer)  # FE-* etc. behalten ihren Namen


# ── Arch / Domain / Factoring (numbered Files): EIN scope-parametrisierter ID-Generator ──
def next_id(layer: str, vault_root=None, scope: str = "arch") -> str:
    """Vergibt die naechste numerierte Pattern-ID im Layout ``{PREFIX}-{SHORT}-{NNN}``.

    BL-237 batch_C4 F1/F3: ``scope`` waehlt Library + ID-Prefix (arch->PT, domain->DOM,
    factoring->FAC) — EIN Generator statt 3x-Klon (Reuse-not-rebuild, DoD-21). arch bleibt
    bit-identisch (default scope=arch -> PT-Prefix, PatternLibrary). Der Glob-Scan ist
    deterministisch + kollisionsfrei pro (scope, layer).
    """
    short = _short(layer)
    prefix = _SCOPE_ID_PREFIX.get(scope, "PT")
    ld = _layer_dir(scope, layer, vault_root)
    nums = []
    if ld.is_dir():
        rx = re.compile(rf"^{re.escape(prefix)}-{re.escape(short)}-(\d+)", re.IGNORECASE)
        for f in ld.glob(f"{prefix}-{short}-*.md"):
            m = rx.match(f.name)
            if m:
                nums.append(int(m.group(1)))
    nxt = (max(nums) + 1) if nums else 1
    return f"{prefix}-{short}-{nxt:03d}"


def find_patterns(query: str, vault_root=None) -> list:
    """Consult-Helfer: durchsucht alle _index.md (Name/Beschreibung) + PT-Dateinamen."""
    root = library_root("arch", vault_root) / "_project"
    hits = []
    if not root.is_dir():
        return hits
    q = query.lower()
    for idx in root.glob("*/_index.md"):
        for line in idx.read_text(encoding="utf-8", errors="replace").splitlines():
            if q in line.lower() and line.strip().startswith("|"):
                hits.append(f"{idx.parent.name}: {line.strip()}")
    return hits


def _name_to_filename(pid: str, name: str, clean: bool = False) -> str:
    if clean:
        return f"{pid}.md"                 # AC-4 SCOPED arch (BL-477) — clean, konsistent zu PT-CMD-001..025
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return f"{pid}_{slug}.md"


def _dedup_hit(layer: str, name: str, description: str, vault_root=None, scope: str = "arch"):
    """Warn-Dedup: existiert ein Pattern mit sehr aehnlichem Namen?

    BL-237 batch_C4 F1: scope-aware (arch=PT, domain=DOM, factoring=FAC) — glob auf den
    scope-eigenen Prefix, damit DomainLibrary/FactoringLibrary ihren eigenen Namensraum dedupen.
    arch bleibt bit-identisch (default scope=arch -> PT-Glob in PatternLibrary).
    """
    ld = _layer_dir(scope, layer, vault_root)
    if not ld.is_dir():
        return None
    prefix = _SCOPE_ID_PREFIX.get(scope, "PT")
    key = re.sub(r"[^a-z0-9]+", "", name.lower())
    for f in ld.glob(f"{prefix}-*.md"):
        fkey = re.sub(r"[^a-z0-9]+", "", f.stem.lower())
        if key and key in fkey:
            return f.name
    return None


# BL-254 AK-S3.2 Single-Source-Guard (Option B): Domaenen-TERME -> SemanticLibrary/domain-terms.md
# (kanonisch). scope=domain ist NUR fuer Fachregel-PATTERNS (W-DOM-3). KEINE Terme in DomainLibrary.
_DOMAIN_TERM_SCOPES = {"domain", "factoring"}
_DOMAIN_TERM_TARGETS = {"terms", "naming", "glossary"}


def is_domain_term_write(scope: str, target) -> bool:
    """True genau dann, wenn ein Domaenen-TERM-Intent (target in {terms, naming, glossary})
    auf eine NICHT-semantic-Library (scope in {domain, factoring}) geschrieben werden soll.

    scope=="semantic" -> IMMER False (kanonischer Term-Pfad).
    scope=="domain"/"factoring" OHNE Term-target -> False (legitimer Fachregel-Pattern-Write).
    """
    if scope not in _DOMAIN_TERM_SCOPES:
        return False
    if target is None:
        return False
    return target in _DOMAIN_TERM_TARGETS


def add_arch(layer, name, description="", tags=None, sources=None,
             pattern="", beispiel="", abgrenzung="", pid=None, vault_root=None,
             story=None, scope="arch", derived_from=None, target=None):
    """Materialisiert EIN numeriertes Pattern direkt (kein Kandidat-Zwischenschritt).
    -> (id, path, dedup_warn).

    AK-SCHEMA-0: schreibt das VOLLE BL-154-Counter-Frontmatter ab Geburt (usage_count:0 etc.),
    damit der nachfolgende lifecycle-Call (pfad-1) nicht in eine Datei ohne das Feld schreibt.

    BL-237 batch_C4 F1 (4-kind add, KEIN 3x-Klon): ``scope`` waehlt Library + Layer-Dir + ID-Prefix
    (arch->PatternLibrary/PT, domain->DomainLibrary/DOM, factoring->FactoringLibrary/FAC). Das
    Frontmatter war schon scope-aware (F4: ``scope: {scope}``); diese Aenderung schliesst NUR die
    dir/ID-Seite (F2/F3). arch bleibt bit-identisch (default scope=arch). Reuse-not-rebuild (DoD-21):
    EINE parametrisierte add-Funktion fuer alle numerierten Scopes, statt domain/factoring zu klonen.

    BL-254 AK-S3.2 Single-Source-Guard: target=None (Default, kein Term-Intent).
    is_domain_term_write(scope, target)==True -> ValueError FAIL-LOUD.
    Domaenen-TERME gehoeren in SemanticLibrary/_project/{LAYER}/domain-terms.md (Single-Source).
    """
    if is_domain_term_write(scope, target):
        raise ValueError(
            f"add_arch scope={scope!r} target={target!r}: domain-TERM-Write gehoert in "
            "SemanticLibrary/_project/{LAYER}/domain-terms.md (kanonische Single-Source, "
            "ADR-domain-single-source); DomainLibrary ist fuer Domaenen-TERME deprecated "
            "(BL-254/Option B). Nutze add_semantic() fuer Terme."
        )
    ld = _layer_dir(scope, layer, vault_root)
    ld.mkdir(parents=True, exist_ok=True)
    dedup = _dedup_hit(layer, name, description, vault_root, scope=scope)
    if pid is None:
        pid = next_id(layer, vault_root, scope=scope)
    fname = _name_to_filename(pid, name, clean=True)   # AC-4 SCOPED arch (BL-477) — clean {pid}.md
    fpath = ld / fname
    tags = tags or []
    sources = sources or []
    fm = [
        "---",
        f"id: {pid}",
        f"scope: {scope}",
        f"layer: {layer}",
        f"name: {name}",
        f"description: {description}",
        f"tags: [{', '.join(tags)}]",
        # Counter-Frontmatter (AK-SCHEMA-0, BL-154-Schema)
        "status: experimental",
        "usage_count: 0",
        "broken_count: 0",
        "boundary_notes: []",
        "broken_locations: []",
        f"derived_from: {derived_from or 'null'}",
        "variants: []",
        "severity: RECOMMENDED",
        f"date_added: {date.today().isoformat()}",
        "sources:",
        *[f"  - {s}" for s in sources],
    ]
    if story:
        fm.append(f"added_via: /_pattern_add ({story})")
    fm.append("---")
    body = [
        "", "## Pattern", "", pattern or "- (TODO: Pattern-Regel)",
        "", "## Beispiel", "", beispiel or "```\n(TODO: Beispiel)\n```",
        "", "## Abgrenzung", "", abgrenzung or "- (TODO: Abgrenzung)", "",
    ]
    fpath.write_text("\n".join(fm + body), encoding="utf-8")
    _append_index_row(scope, layer, pid, fname, description or name, story, vault_root)
    return pid, fpath, dedup


# ── BL-307 batch_PL1 (Befund 1) · Index-Schema-Kanon (6-Spalten-Counter, BL-237) ──
# Die EINE Wahrheit fuer Emitter + Validator: jede _index.md-Tabelle traegt diese 6 Spalten.
# Seed-Indizes (z.B. /_PT_arch_init 2026-05-02 + FE-Batch) tragen ein FREMDES 7-Spalten-Schema;
# der blinde Append haengte seine 6-Spalten-Zeile darunter -> column-shift (live FE-FORM 9/13).
_CANON_IDX_COLS = ["ID", "Datei", "Kurzbeschreibung", "usage_count", "broken_count", "status"]
_CANON_IDX_HEADER = "| " + " | ".join(_CANON_IDX_COLS) + " |"
_CANON_IDX_SEP = "|----|-------|-----------------|-------------|--------------|--------|"


def _split_table_row(line: str) -> list:
    """Markdown-Tabellenzeile -> Zell-Liste (ohne fuehrendes/abschliessendes ``|``)."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_table_header(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and "ID" in s and ("Kurzbeschreibung" in s or "Name" in s)


def _is_table_separator(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and bool(s) and set(s.replace("|", "").strip()) <= set("-: ")


def _is_canon_header(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and all(c in s for c in _CANON_IDX_COLS)


def _migrate_foreign_row(cells: list) -> str:
    """Mappt eine FREMD-Schema-Daten-Zeile lossless auf den 6-Spalten-Kanon.

    Vertrag (BL-307 PL-307-1): Spalte0=ID (bleibt). Tragende Beschreibung/Name -> Kurzbeschreibung
    (zweite Zelle, der ueblichen Name/Beschreibung-Spalte). Status-Spalte -> status (eine Zelle die
    'active'/'proven'/'experimental'/... traegt, sonst Default). Datei-Link -> Datei falls vorhanden,
    sonst as-is (ID). usage_count/broken_count -> Default 0 (Fremd-Schema kennt sie nicht).
    """
    pid = cells[0] if cells else ""
    rest = cells[1:]
    desc = rest[0] if rest else ""
    # Datei: eine ``[..](..)``-Link-Zelle uebernehmen, sonst as-is = ID.
    datei = next((c for c in cells if "](" in c), pid)
    # Status: eine Zelle die wie ein Reifegrad aussieht, sonst experimental.
    known = {"experimental", "active", "proven", "deprecated", "candidate", "stable"}
    status = next((c for c in rest if c.lower() in known), "experimental")
    cols = [pid, datei, desc, "0", "0", status]
    return "| " + " | ".join(cols) + " |"


def _refresh_summary_lines(lines: list, true_count: int) -> None:
    """Haelt eine ``Patterns: N``-Bootstrap-Summary aktuell (BL-307 PL-307-5).

    Eine stale feste Zahl unter der wahren Zeilen-Menge wird NIE stehen gelassen: stimmt sie nicht
    mit ``true_count`` ueberein, wird sie auf die wahre Zahl gesetzt + als point-in-time markiert.
    """
    pat = re.compile(r"^(\s*Patterns:\s*)(\d+)(.*)$")
    for i, l in enumerate(lines):
        m = pat.match(l)
        if not m:
            continue
        if int(m.group(2)) != true_count:
            lines[i] = f"{m.group(1)}{true_count} (point-in-time {date.today().isoformat()})"


def _append_index_row(kind, layer, pid, fname, desc, story, vault_root=None,
                      usage_count=0, broken_count=0, status="experimental"):
    """Haengt EINE Index-Zeile an die ``_index.md`` der Library.

    BL-237 batch_C5 AK-8 (F3, §4.2): die Zeilen-Form traegt jetzt die Counter-Sichtbarkeit als
    eigene Spalten — ``| ID | Datei | Kurzbeschreibung | usage_count | broken_count | status |``.
    Bisher lebten die Counter NUR im Pattern-Frontmatter (``_append_index_row`` schrieb nur
    ``ID|Datei|Kurzbeschreibung``). Die Counter-Werte sind beim Geburts-Add deterministisch
    (usage_count=0/broken_count=0/status=experimental, gespiegelt von _COUNTER_DEFAULTS) — der
    organische Feed (R6b-Drain) bewegt sie spaeter via lifecycle. Additiv: bestehende Index-Leser
    bleiben tolerant (die ersten 3 Spalten sind unveraendert, K-4/53-69-Baseline regressionsfrei).
    READ-ONLY-Dashboard /_pattern_status (AK-8) rendert diese Spalten + die Frontmatter-maturity.

    BL-307 batch_PL1 (Befund 1): VOR dem Insert in den Bestands-Pfad wird das Header-Schema der
    Ziel-Tabelle gelesen. Ist es bereits der Kanon -> append wie bisher. Traegt es ein FREMDES
    Schema (z.B. 7-Spalten-Seed) -> der Index wird EINMALIG migriert (Fremd-Header/-Separator durch
    den Kanon ersetzt, jede Bestands-Daten-Zeile lossless auf 6 Spalten gemappt), DANN die neue
    Counter-Zeile angehaengt. Idempotent: ein 2. Append findet den Kanon-Header und re-migriert NICHT.
    """
    idx = _layer_dir(kind, layer, vault_root) / "_index.md"
    row = f"| {pid} | [{fname}]({fname}) | {desc} | {usage_count} | {broken_count} | {status} |"
    if not idx.exists():
        idx.write_text(
            f"# {layer} Pattern Library\n\n{_CANON_IDX_HEADER}\n{_CANON_IDX_SEP}\n{row}\n",
            encoding="utf-8")
        return
    txt = idx.read_text(encoding="utf-8", errors="replace")
    lines = txt.splitlines()

    # Schema-Detection: ist der erste Tabellen-Header schon der Kanon?
    header_idx = next((i for i, l in enumerate(lines) if _is_table_header(l)), None)
    if header_idx is not None and not _is_canon_header(lines[header_idx]):
        # FREMD-Schema -> einmalige In-Place-Migration auf den Kanon (lossless, idempotent).
        new_lines = []
        seen_table = False
        for i, l in enumerate(lines):
            if i == header_idx:
                new_lines.append(_CANON_IDX_HEADER)
                new_lines.append(_CANON_IDX_SEP)
                seen_table = True
                continue
            if seen_table and _is_table_separator(l):
                continue  # alter Fremd-Separator faellt weg (Kanon-Separator schon gesetzt)
            if seen_table and l.strip().startswith("|") and not _is_table_separator(l):
                new_lines.append(_migrate_foreign_row(_split_table_row(l)))
                continue
            new_lines.append(l)
        lines = new_lines

    # AC-1 (BL-477): Insert am Ende der Patterns-Tabelle (header_idx oben ist sie bereits),
    # NICHT an der letzten |-Zeile der ganzen Datei (die unter Bootstrap-Historie liegen kann).
    if header_idx is not None:
        # Ende der Tabelle = letzte konsekutive |-Zeile ab header_idx (Header + Separator + Daten).
        tbl_end = header_idx
        for i in range(header_idx, len(lines)):
            if lines[i].strip().startswith("|"):
                tbl_end = i
            else:
                break          # erste Nicht-|-Zeile -> Tabelle endet hier
        insert_at = tbl_end + 1
    else:
        # Kein Tabellen-Header (greenfield/degeneriert) -> Fallback auf letzte |-Zeile global.
        insert_at = max((i for i, l in enumerate(lines) if l.strip().startswith("|")),
                        default=len(lines) - 1) + 1
    lines.insert(insert_at, row)
    if story:
        lines.append("")
        lines.append(f"<!-- {pid} added via /_pattern_add ({story}) {date.today().isoformat()} -->")

    # AC-2 (BL-477): total_patterns-Frontmatter +1 if-present (1 add = +1 tatsaechlicher Insert).
    # NUR wenn das Feld existiert (greenfield-Index ohne Feld -> no-op, kein crash, kein neues Feld).
    # GETRENNT von _refresh_summary_lines (Body-Patterns:-Bullet, anderer Key) — beide koexistieren.
    _tp = re.compile(r"^(\s*total_patterns:\s*)(\d+)(.*)$")
    for i, l in enumerate(lines):
        m = _tp.match(l)
        if m:
            lines[i] = f"{m.group(1)}{int(m.group(2)) + 1}{m.group(3)}"
            break            # genau das erste Vorkommen (Frontmatter-Feld), dann fertig

    # PL-307-5: stale Bootstrap-Summary auf die wahre Zeilen-Zahl bringen (point-in-time).
    true_count = sum(1 for l in lines
                     if l.strip().startswith("|")
                     and not _is_table_header(l) and not _is_table_separator(l))
    _refresh_summary_lines(lines, true_count)

    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_index_schema(index_path) -> list:
    """READ-ONLY Schema-Sanity einer ``_index.md`` (BL-307 batch_PL1 PL-307-4).

    Liefert eine Liste von findings — SCHREIBT NICHTS (K-2-Vorbild test_pattern_status_readonly):
      - ``{"kind": "foreign_header", "line": <txt>}`` wenn der Tabellen-Header != Kanon ist.
      - ``{"kind": "column_shifted_row", "line": <txt>, "cells": <n>}`` je Daten-Zeile mit != 6 Zellen.
    Ein kanonischer Index (Header = Kanon, alle Zeilen 6 Zellen) -> []. Fehlt die Datei -> [].
    """
    p = Path(index_path)
    findings: list = []
    if not p.exists():
        return findings
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    for l in lines:
        s = l.strip()
        if not s.startswith("|"):
            continue
        if _is_table_separator(l):
            continue
        if _is_table_header(l):
            if not _is_canon_header(l):
                findings.append({"kind": "foreign_header", "line": s})
            continue
        cells = _split_table_row(l)
        if len(cells) != len(_CANON_IDX_COLS):
            findings.append({"kind": "column_shifted_row", "line": s, "cells": len(cells)})
    return findings


# ── Semantic (SemanticLibrary): per-Entry-Frontmatter-Dateien (BL-237 batch_C3b AK-CTX-SEMFORMAT) ──
# SEMFORMAT-Wurzel (SC-FULL Z4 OBSERVE4 F1/F2, §4.2): die SemanticLibrary war reines Bullet-Format
# (add_semantic:225 append-only Bullet) — ohne Per-Entry-Counter findet lifecycle(scope=semantic)
# NICHTS (F2: _find_pattern_file globt _project/<layer>/{pid}*.md mit Frontmatter). SEMFORMAT hebt
# add_semantic auf per-Term-.md-Dateien mit vollem Counter-Frontmatter ab Geburt (add_arch-gespiegelt),
# damit der EINE parametrisierte Counter-Kern (R5, scope=semantic) sie OHNE arch-Pfad-Aenderung findet.
# Die alte Bullet-Aggregat-Sicht bleibt additiv als rueckwaerts-toleranter Lese-Index liegen
# (kein Datenverlust, K-3/DoD-21: die 38 arch-Tests bleiben unberuehrt).
_SEM_TARGETS = {"terms": "domain-terms.md", "naming": "naming-conventions.md"}
_SEM_SHORT = {"terms": "TERM", "naming": "NC", "glossary": "GLOSS"}


def next_sem_id(layer, target="terms", vault_root=None) -> str:
    """Vergibt die naechste Semantic-Pattern-ID analog next_id (arch). Layout SL-{LAYER}-{TARGET}-{NNN}.

    Schema-Anker: SemanticLibrary spiegelt das arch-Glob-Layout (per-Entry-.md mit Frontmatter), die
    ID traegt Layer + Target, damit Terms/Naming/Glossary kollisionsfrei numerieren.
    """
    short = _short(layer)
    tshort = _SEM_SHORT.get(target, "TERM")
    if target == "glossary":
        ld = library_root("semantic", vault_root) / "_global"
        prefix = f"SL-GLOSS"
    else:
        ld = _layer_dir("semantic", layer, vault_root)
        prefix = f"SL-{short}-{tshort}"
    nums = []
    if ld.is_dir():
        rx = re.compile(rf"^{re.escape(prefix)}-(\d+)", re.IGNORECASE)
        for f in ld.glob(f"{prefix}-*.md"):
            m = rx.match(f.name)
            if m:
                nums.append(int(m.group(1)))
    nxt = (max(nums) + 1) if nums else 1
    return f"{prefix}-{nxt:03d}"


def _sem_file_for_name(layer, name, target="terms", vault_root=None):
    """B-2 Idempotenz-Helfer: existiert bereits eine per-Term-Datei fuer (layer, target, name)?

    Match ueber den name-Slug-Suffix (ID-unabhaengig), damit ein Migrations-Re-Run denselben Bullet
    NICHT als neue Datei dupliziert. -> Path der vorhandenen Datei oder None.
    """
    if target == "glossary":
        ld = library_root("semantic", vault_root) / "_global"
    else:
        ld = _layer_dir("semantic", layer, vault_root)
    if not ld.is_dir():
        return None
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    if not slug:
        return None
    for f in ld.glob("SL-*.md"):
        stem = f.stem.lower()
        if stem.endswith("_" + slug) or stem.endswith("-" + slug):
            return f
    return None


def add_semantic_file(layer, name, description="", target="terms", sid=None,
                      vault_root=None, story=None, scope="semantic"):
    """SEMFORMAT (B-1): materialisiert EINEN Semantic-Eintrag als per-Term-.md-Datei mit vollem
    Counter-Frontmatter ab Geburt (gespiegelt von add_arch / _COUNTER_DEFAULTS, AK-SCHEMA-0).

    Layout spiegelt das arch-Glob (_find_pattern_file F2): glossary -> _global/, sonst _project/<layer>/.
    -> (sid, fpath, created). created=False heisst: eine Datei fuer diesen Term existierte schon
    (Migration-Re-Run-Guard, B-2 idempotent). Damit findet lifecycle(scope=semantic) den Eintrag
    OHNE arch-Pfad-Aenderung (R5).
    """
    if target == "glossary":
        ld = library_root("semantic", vault_root) / "_global"
    else:
        ld = _layer_dir("semantic", layer, vault_root)
    ld.mkdir(parents=True, exist_ok=True)
    # B-2: schon eine Datei fuer diesen Term (slug-Match, ID-unabhaengig) -> idempotent zurueck.
    existing = _sem_file_for_name(layer, name, target=target, vault_root=vault_root)
    if existing is not None:
        return _fm_get(_split_fm(_read_text(existing))[0] or "", "id") or existing.stem, existing, False
    if sid is None:
        sid = next_sem_id(layer, target=target, vault_root=vault_root)
    fname = _name_to_filename(sid, name)
    fpath = ld / fname
    if fpath.exists():
        return sid, fpath, False  # idempotent: nicht ueberschreiben (Migration-Re-Run-Guard, B-2)
    fm = [
        "---",
        f"id: {sid}",
        f"scope: {scope}",
        f"layer: {layer}",
        f"target: {target}",
        f"name: {name}",
        f"description: {description}",
        # Counter-Frontmatter (AK-SCHEMA-0, BL-154-Schema — gespiegelt von add_arch)
        "status: experimental",
        "usage_count: 0",
        "broken_count: 0",
        "boundary_notes: []",
        "broken_locations: []",
        "derived_from: null",
        "variants: []",
        f"date_added: {date.today().isoformat()}",
    ]
    if story:
        fm.append(f"added_via: /_pattern_add ({story})")
    fm.append("---")
    body = ["", f"## {name}", "", description or "- (TODO: Semantic-Regel)", ""]
    fpath.write_text("\n".join(fm + body), encoding="utf-8")
    return sid, fpath, True


def add_semantic(layer, name, description="", target="terms", vault_root=None, story=None):
    """SEMFORMAT (B-1/B-3): schreibt EINE per-Term-Frontmatter-Datei mit vollem Counter-Frontmatter
    (findbar via _find_pattern_file(scope=semantic), Voraussetzung fuer R5) UND haengt den Eintrag
    additiv an die Bullet-Aggregat-Sicht (rueckwaerts-toleranter Lese-Index, kein Datenverlust).

    -> (path, entry) — der Rueckgabewert zeigt weiterhin auf die Aggregat-Datei (Kompatibilitaet);
    die per-Term-Datei wird zusaetzlich materialisiert (Counter-Symmetrie ab Geburt, AK-SEMFORMAT).
    Vault-resolved (B-3): Datei + Aggregat landen unter resolve_vault_root(override), nicht im CWD.
    """
    # (1) SEMFORMAT-Wurzel: per-Term-Frontmatter-Datei (findbar, voller Counter ab Geburt).
    add_semantic_file(layer, name, description=description, target=target,
                      vault_root=vault_root, story=story)
    # (2) Additive Bullet-Aggregat-Sicht (rueckwaerts-toleranter Lese-Index, kein Datenverlust).
    if target == "glossary":
        f = library_root("semantic", vault_root) / "_global" / "domain-glossary.md"
    else:
        f = _layer_dir("semantic", layer, vault_root) / _SEM_TARGETS.get(target, "domain-terms.md")
    f.parent.mkdir(parents=True, exist_ok=True)
    entry = f"- **{name}** — {description}" + (f"  _(via /_pattern_add, {story})_" if story else "")
    prefix = "" if (f.exists() and f.read_text(encoding='utf-8', errors='replace').endswith("\n")) else "\n"
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(prefix + entry + "\n")
    return f, entry


# Parser fuer Bestands-Bullets (Migration B-2): "- **Name** — Beschreibung" (toleranter Regex).
_SEM_BULLET_RE = re.compile(r"^\s*[-*]\s+\*\*(?P<name>.+?)\*\*\s*[—-]+\s*(?P<desc>.*?)\s*$")


def _parse_sem_bullets(text):
    """B-2: extrahiert (name, description) aus den Bestands-Bullet-Zeilen einer Aggregat-Datei.

    Toleriert Frontmatter/Header/Leerzeilen (werden uebersprungen). Liefert NUR echte Bullet-Eintraege
    im Format ``- **Name** — Beschreibung`` (em-dash oder Bindestrich-Trenner). Kein Datenverlust:
    jeder erkannte Bullet erzeugt genau 1 per-Term-Datei (1:1, idempotent ueber den Datei-Existenz-Guard).
    """
    _, body = _split_fm(text)
    out = []
    for line in body.splitlines():
        m = _SEM_BULLET_RE.match(line)
        if m:
            name = m.group("name").strip()
            desc = re.sub(r"\s*_\(via /_pattern_add[^)]*\)_\s*$", "", m.group("desc")).strip()
            if name:
                out.append((name, desc))
    return out


def migrate_semantic(layer=None, vault_root=None) -> int:
    """SEMFORMAT-Migration (B-2): hebt Bestands-Bullets der SemanticLibrary verlustfrei auf
    per-Term-Frontmatter-Dateien (1 Bullet -> 1 Datei, usage_count=0 Cold-Start). Idempotent
    (2. Lauf -> keine Duplikate via add_semantic_file-Existenz-Guard). Die Alt-Aggregat-/_index.md-
    Datei bleibt UNVERAENDERT als rueckwaerts-toleranter Lese-Index liegen (kein Datenverlust).

    layer=None migriert ALLE _project/<layer>/-Aggregate + _global/domain-glossary.md.
    -> Anzahl neu materialisierter per-Term-Dateien.
    """
    semlib = library_root("semantic", vault_root)
    migrated = 0
    sources = []  # (layer, target, aggregate_path)
    proj = semlib / "_project"
    if proj.is_dir():
        for ldir in sorted(proj.iterdir()):
            if not ldir.is_dir():
                continue
            if layer is not None and ldir.name != layer:
                continue
            for target, fname in _SEM_TARGETS.items():
                agg = ldir / fname
                if agg.is_file():
                    sources.append((ldir.name, target, agg))
    if layer is None:
        gloss = semlib / "_global" / "domain-glossary.md"
        if gloss.is_file():
            sources.append(("_global", "glossary", gloss))
    for lyr, target, agg in sources:
        text = agg.read_text(encoding="utf-8", errors="replace")
        for name, desc in _parse_sem_bullets(text):
            _sid, _fpath, created = add_semantic_file(lyr, name, description=desc, target=target,
                                                      vault_root=vault_root)
            # B-2 idempotent: nur durch DIESEN Lauf NEU erzeugte Dateien zaehlen (created=True).
            # Ein 2. Migrations-Lauf trifft den Existenz/Slug-Guard -> created=False -> 0 (keine Duplikate).
            if created:
                migrated += 1
    return migrated


# ══ Counter / Lifecycle (BL-237 AK-COUNTER-0) — EIN parametrisierter Reifungs-Counter ══

_FM_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def _read_text(path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _split_fm(text):
    """-> (fm_content, body) oder (None, text) wenn kein Frontmatter."""
    m = _FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def _join_fm(fm, body) -> str:
    return f"---\n{fm}\n---\n{body}"


def _fm_get(fm, key, default=None):
    for line in fm.splitlines():
        mm = re.match(rf"^{re.escape(key)}:\s*(.*)$", line)
        if mm:
            return mm.group(1).strip()
    return default


def _fm_set(fm, key, rendered):
    """Setzt/ergaenzt key im Frontmatter-Content (vor der schliessenden ---)."""
    out, found = [], False
    for line in fm.splitlines():
        if re.match(rf"^{re.escape(key)}:", line):
            out.append(f"{key}: {rendered}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}: {rendered}")
    return "\n".join(out)


def _fm_list(fm, key):
    v = _fm_get(fm, key)
    if not v or v in ("[]", "null", "None"):
        return []
    try:
        return json.loads(v)
    except Exception:
        return []


def _scope_library_root(scope, vault_root=None) -> Path:
    return resolve_vault_root(vault_root) / "Libraries" / _SCOPE_LIB.get(scope, "PatternLibrary")


def _find_pattern_file(pid, scope="arch", vault_root=None):
    lib = _scope_library_root(scope, vault_root)
    for pat in (f"_project/*/{pid}*.md", f"_generic/{pid}*.md", f"_project/{pid}*.md"):
        for f in lib.glob(pat):
            if f.is_file():
                return f
    return None


def read_counter(path) -> dict:
    """Liest die Counter-Felder mit Graceful-Default (deckt Bestands-Patterns ohne Felder, AK-MIG-0)."""
    fm, _ = _split_fm(_read_text(path))
    fm = fm or ""

    def gi(k, d=0):
        v = _fm_get(fm, k)
        try:
            return int(v) if v is not None else d
        except (TypeError, ValueError):
            return d

    return {
        "usage_count": gi("usage_count", 0),
        "broken_count": gi("broken_count", 0),
        "status": _fm_get(fm, "status") or "experimental",
        "scope": _fm_get(fm, "scope") or "arch",
        "boundary_notes": _fm_list(fm, "boundary_notes"),
        "broken_locations": _fm_list(fm, "broken_locations"),
        "derived_from": _fm_get(fm, "derived_from") or "null",
        "variants": _fm_list(fm, "variants"),
    }


def maturity(counter: dict) -> int:
    """ABGELEITET (AK-VOCAB-0): usage_count - broken_count. Kein Frontmatter-Feld."""
    return counter["usage_count"] - counter["broken_count"]


# ══════════════════════════════════════════════════════════════════════════
# ══ BL-237 batch_C5 AK-CTX-WORTHINESS-EXTRACT — die aufrufbare Worthiness-Heuristik ══
# ══════════════════════════════════════════════════════════════════════════
# Architektur (SC-FULL Z6 OBSERVE6 F1, §4.1): die Heuristik lag bisher NUR als Inline-
# Pseudocode in _PT_promoteFromPL.md:176-206 (5 Signal-Klassen) vor — pattern_library.py
# hatte 0 Treffer (grep is_pattern_worthy/worthiness). Der Konsument _PT_berater_materialize
# referenzierte is_pattern_worthy() SCHON mit INV-MAT-5 worthiness_pending-Fallback. AK-CTX-
# WORTHINESS-EXTRACT zieht die Code-Naht: EINE aufrufbare Single-Source statt 2x-Reimpl
# (Stage 1 gatherSignals + Stage 5/7 materialize). KEINE Wahrheits-Frage — reiner Extract-
# to-callable; die 5 Signal-Klassen werden 1:1 portiert (Extract-not-reimplement, F1/K-1):
#   arch-keyword, cross-cutting, validation-pattern, compiler-rule, has-concrete-example.

# 5 Signal-Klassen 1:1 aus _PT_promoteFromPL.md:176-206 (keine Erfindung, kein Re-Sort).
_WORTHINESS_KEYWORDS = {
    # Architektur-Signale
    "arch-keyword": ["Architektur", "Pattern", "Struktur", "Konvention"],
    # Cross-Cutting (was in jedem Projekt nuetzlich waere)
    "cross-cutting": ["Cross-Cutting", "generisch", "generic", "wiederverwendbar"],
    # Validierung/Constraints (pattern-relevant z.B. fuer FluentValidation-Patterns)
    "validation-pattern": ["Validator", "Constraint", "MaxLength", "Validation"],
    # XML-Doc / StyleCop / Compiler-Regeln (PT-GEN-* Beispiele)
    "compiler-rule": ["XML-Doc", "StyleCop", "SA1", "Analyzer"],
}

# Code-Block / Datei-Referenz-Erkennung (5. Klasse: has-concrete-example).
_CODE_BLOCK_RE = re.compile(r"```")
_FILE_PATH_RE = re.compile(r"[\w./\\-]+\.(?:cs|py|md|json|csproj|ts|tsx|js|sql|yml|yaml|xml)\b",
                           re.IGNORECASE)


def _candidate_text(candidate) -> str:
    """Normalisiert einen Worthiness-Kandidaten auf seinen durchsuchbaren Text.

    Akzeptiert (a) einen rohen String, (b) ein dict mit ``text``/``content``/``body``/``description``
    (Konsument-tolerant: _PT_berater_materialize/gatherSignals reichen unterschiedliche Shapes),
    (c) ein Objekt mit ``.text``-Attribut (Inline-Quelle ``item.text``). Fallback: ``str(candidate)``.
    """
    if candidate is None:
        return ""
    if isinstance(candidate, str):
        return candidate
    if isinstance(candidate, dict):
        for k in ("text", "content", "body", "description"):
            v = candidate.get(k)
            if isinstance(v, str) and v:
                return v
        # dict ohne erkanntes Textfeld -> alle String-Werte joinen (defensiv, kein Crash).
        return " ".join(str(v) for v in candidate.values() if isinstance(v, str))
    txt = getattr(candidate, "text", None)
    return txt if isinstance(txt, str) else str(candidate)


def worthiness_reasons(candidate) -> list:
    """BL-237 batch_C5 (F1): liefert die Liste der erfuellten Worthiness-Signal-Klassen.

    1:1-Portierung der Inline-Heuristik aus ``_PT_promoteFromPL.md:176-206`` (5 Signal-Klassen).
    Reihenfolge ist deterministisch (arch-keyword, cross-cutting, validation-pattern, compiler-rule,
    has-concrete-example) — Parity-Anker fuer den Signal-Parity-Test (K-1). Case-insensitive
    Keyword-Match wie ``item.has_keyword_any`` in der Quelle.
    """
    text = _candidate_text(candidate)
    low = text.lower()
    reasons = []
    for klass in ("arch-keyword", "cross-cutting", "validation-pattern", "compiler-rule"):
        kws = _WORTHINESS_KEYWORDS[klass]
        if any(kw.lower() in low for kw in kws):
            reasons.append(klass)
    # has-concrete-example: Code-Block ODER konkrete Datei-Referenz (item.has_code_block/has_file_path).
    if _CODE_BLOCK_RE.search(text) or _FILE_PATH_RE.search(text):
        reasons.append("has-concrete-example")
    return reasons


def is_pattern_worthy(candidate) -> bool:
    """BL-237 batch_C5 AK-CTX-WORTHINESS-EXTRACT (F1, §4.1) — der aufrufbare Engpass-Gate.

    Single-Source der Pattern-Wuerdigkeits-Heuristik: ``True`` sobald MINDESTENS eine der 5
    Signal-Klassen feuert (arch-keyword / cross-cutting / validation-pattern / compiler-rule /
    has-concrete-example). Genau die Disjunktion (``worthy = True`` bei erstem Treffer) aus
    ``_PT_promoteFromPL.md:176-206``. Loest den INV-MAT-5 ``worthiness_pending``-Fallback in
    ``_PT_berater_materialize`` auf (kein Doppel-Impl, Extract-not-reimplement).
    """
    return len(worthiness_reasons(candidate)) > 0


def _is_novelty(e: dict) -> bool:
    """BL-258 AK-S2 — Novelty-Eligibility-Praedikat.

    Ein Eintrag ist novelty-eligible wenn usage_count==0 AND broken_count==0
    (ungetestet/neu, NICHT broken/abgelehnt).
    """
    return (int(e.get("usage_count", 0) or 0) == 0
            and int(e.get("broken_count", 0) or 0) == 0)


def rank_by_maturity(entries: list, top_n: int = 5, novelty_slots: int = 0) -> list:
    """BL-237 AK-CTX-R3 — Reife-getriebenes Ranking fuer den PRE-Recommender-Seam.

    Ersetzt das alte ``top_5_by_confidence`` im patternBrief-Schritt-3-Seam: sortiert
    matched_patterns/matched_semantics nach der ABGELEITETEN maturity()=usage_count-broken_count
    (DESC, Primaer) mit ``confidence`` als deterministischem Cold-Start-Tie-Break (DESC).

    Cold-Start-Invariante (O-6, C-K1): solange alle usage_count==0 (Regel-Fall heute, bevor die
    Counter-Feeds aus batch_C3a usage_count von 0 wegbewegen) ist maturity fuer alle gleich (==
    -broken_count, default 0) -> der Tie-Break auf ``confidence`` greift und die Reihenfolge ist
    BIT-IDENTISCH zum heutigen confidence-Ranking. Erst echte Counter-Daten differenzieren.

    INV-B1-4 / INV-SL-1: ``_generic``/``_global``-Eintraege bleiben IMMER erhalten — der Top-N-Cut
    filtert sie NIE heraus; sie werden vor dem Cut abgespalten und danach (deduppt) wieder
    vorangestellt. Reine Lese-Operation auf der maturity()-Primitive (Counter-Kern unberuehrt,
    Reuse-not-rebuild / DoD-21). Vokabular strikt code-konform (W-CNT-7): nur usage_count /
    broken_count / maturity() — keine confirm_count/maturity_score(Feld)-Phantome.

    entries: Liste von Dicts mit optionalen Schluesseln ``maturity`` (oder ``usage_count`` +
             ``broken_count``), ``confidence`` (numerisch oder high/medium/low) und ``layer``/``scope``.
    """
    _CONF = {"high": 3, "medium": 2, "low": 1}

    def _conf(e):
        c = e.get("confidence", 0)
        if isinstance(c, str):
            return _CONF.get(c.strip().lower(), 0)
        try:
            return float(c)
        except (TypeError, ValueError):
            return 0

    def _mat(e):
        if "maturity" in e and e["maturity"] is not None:
            try:
                return int(e["maturity"])
            except (TypeError, ValueError):
                return 0
        return int(e.get("usage_count", 0) or 0) - int(e.get("broken_count", 0) or 0)

    def _is_preserved(e):
        # _generic/_global Eintraege NIE wegfiltern (INV-B1-4 / INV-SL-1)
        for k in ("layer", "scope", "id"):
            v = str(e.get(k, "")).lower()
            if v.startswith("_generic") or v.startswith("_global"):
                return True
        return False

    preserved = [e for e in entries if _is_preserved(e)]
    rest = [e for e in entries if not _is_preserved(e)]

    # Stabiler Sort: maturity DESC (Primaer), confidence DESC (Cold-Start-Tie-Break).
    rest_sorted = sorted(rest, key=lambda e: (_mat(e), _conf(e)), reverse=True)

    # BL-258 AK-S1/S2/S3 — Diversity-Cut: novelty_slots>0 reserviert Slots fuer neue Patterns.
    # Default novelty_slots==0 => unveraenderter alter Pfad (byte-identisch, Cold-Start-Invariante).
    if novelty_slots > 0:
        k = max(0, top_n - novelty_slots)
        mature_k = rest_sorted[:k]
        seen_mature = {id(e) for e in mature_k}
        # Novelty-eligible Kandidaten: usage_count==0 AND broken_count==0, dedup gegen mature_k.
        novelty_candidates = [e for e in rest_sorted if _is_novelty(e) and id(e) not in seen_mature]
        novelty_fill = novelty_candidates[:novelty_slots]
        # Auffuellung: fehlende Novelty-Slots mit naechst-reifen aus rest_sorted auffuellen.
        if len(novelty_fill) < novelty_slots:
            used = seen_mature | {id(e) for e in novelty_fill}
            fallback = [e for e in rest_sorted if id(e) not in used]
            novelty_fill = novelty_fill + fallback[: novelty_slots - len(novelty_fill)]
        cut = mature_k + novelty_fill
    else:
        cut = rest_sorted[: max(0, top_n)]
    # _generic/_global voranstellen, ohne Dubletten (Erhalt-Garantie unabhaengig vom Rang).
    seen = {id(e) for e in preserved}
    return preserved + [e for e in cut if id(e) not in seen]


def lifecycle(pid, pfad, scope="arch", vault_root=None, **ctx) -> dict:
    """BL-237 AK-COUNTER-0 — EIN parametrisierter Counter (Schema-treu BL-154, APPEND-ONLY).

    pfad 1 = angewandt -> usage_count++ / status-Upgrade @5/@10
    pfad 2 = gebrochen -> broken_count++ + boundary_notes/broken_locations APPEND / auto-deprecate @3
    pfad 3 = Abwandlung -> neues Pattern (derived_from) + variants-Backlink
    pfad 5 = STOP -> keine Mutation
    """
    pfad = str(pfad)
    if pfad == "5":
        return {"pfad": 5, "pid": pid, "no_pattern_found": True}

    path = _find_pattern_file(pid, scope, vault_root)
    if path is None:
        return {"pfad": pfad, "pid": pid, "scope": scope, "error": "pattern_not_found"}
    fm, body = _split_fm(_read_text(path))
    if fm is None:
        return {"pfad": pfad, "pid": pid, "error": "no_frontmatter"}
    c = read_counter(path)

    if pfad == "1":
        new_usage = c["usage_count"] + 1
        fm = _fm_set(fm, "usage_count", str(new_usage))
        old_status, new_status = c["status"], c["status"]
        if old_status == "experimental" and new_usage >= THRESH_ACTIVE:
            new_status = "active"
        elif old_status == "active" and new_usage >= THRESH_PROVEN:
            new_status = "PROVEN"
        if new_status != old_status:
            fm = _fm_set(fm, "status", new_status)
            fm = _fm_set(fm, "status_promoted_at", date.today().isoformat())
        fm = _fm_set(fm, "last_used", date.today().isoformat())
        path.write_text(_join_fm(fm, body), encoding="utf-8")
        return {"pfad": 1, "pid": pid, "usage_count": new_usage, "status": new_status,
                "maturity": new_usage - c["broken_count"]}

    if pfad == "2":
        new_broken = c["broken_count"] + 1
        fm = _fm_set(fm, "broken_count", str(new_broken))
        bctx, brsn = ctx.get("broken_context", "?"), ctx.get("broken_reason", "?")
        bn = c["boundary_notes"] + [f"broken in {bctx}: {brsn}"]
        fm = _fm_set(fm, "boundary_notes", json.dumps(bn, ensure_ascii=False))
        bl = c["broken_locations"] + [{"file": bctx, "reason": brsn, "date": date.today().isoformat()}]
        fm = _fm_set(fm, "broken_locations", json.dumps(bl, ensure_ascii=False))
        auto_dep = False
        if new_broken >= THRESH_DEPRECATE and c["status"] != "deprecated":
            fm = _fm_set(fm, "status", "deprecated")
            fm = _fm_set(fm, "deprecated_reason", f"Auto-DEPRECATED: broken_count={new_broken} >= {THRESH_DEPRECATE}")
            fm = _fm_set(fm, "deprecated_at", date.today().isoformat())
            auto_dep = True
        path.write_text(_join_fm(fm, body), encoding="utf-8")
        return {"pfad": 2, "pid": pid, "broken_count": new_broken, "auto_deprecated": auto_dep,
                "maturity": c["usage_count"] - new_broken}

    if pfad == "3":
        src_layer = _fm_get(fm, "layer") or "_generic"
        new_name = ctx.get("new_name") or f"{pid}-variant"
        new_pid, _np, _dd = add_arch(src_layer, new_name, description=ctx.get("description", ""),
                                     scope=scope, derived_from=pid, vault_root=vault_root)
        variants = c["variants"] + [new_pid]
        fm = _fm_set(fm, "variants", json.dumps(variants, ensure_ascii=False))
        path.write_text(_join_fm(fm, body), encoding="utf-8")
        return {"pfad": 3, "pid": pid, "new_id": new_pid, "derived_from": pid}

    return {"pfad": pfad, "pid": pid, "error": "unknown_pfad"}


# ══════════════════════════════════════════════════════════════════════════
# ══ BL-237 batch_C3a — Counter-Feed-Kette (LOGFMT -> R6a -> R6b-Drain -> R4) ══
# ══════════════════════════════════════════════════════════════════════════
# Architektur (SC-FULL Z3 OBSERVE3 F1-F11, ADR-PL-008):
#   R1/R2/R4 = Signal-Emitter (NUR Log-APPEND, KEIN lifecycle-Direkt-Call).
#   R6b      = EINZIGER autorisierter Drain (Log -> lifecycle pfad-1), idempotent
#              via processed-Cursor.
#   Der lifecycle()-Sink (pfad-1/2, Thresholds 5/10/3, auto-deprecate@3 IRREVERSIBEL)
#   bleibt UNVERAENDERT (Reuse-not-rebuild, DoD-21). Feed-Logik lebt hier in
#   Writer/Drain/Detektor, NICHT im Counter-Kern.

# ── LOGFMT (AK-CTX-LOGFMT) — EINE kanonische Spalten-Konvention ──
# Gehaertetes Schema: pipe-getrennt, fester Header. Anker commit_sha/file_anchor/
# fac_id/pattern_id (commit_sha/file_anchor sind R4-Gate-Vorbedingung; fac_id NUR
# Schema-Anker, Konsum erst batch_C4 NON-BLOCKING; pattern_id ist der Drain-Schluessel).
USAGE_LOG_RELPATH = Path(".claude") / "wissen" / "pattern-usage.log"
USAGE_LOG_CURSOR_RELPATH = Path(".claude") / "wissen" / "pattern-usage.cursor"

# Kanonische Spalten-Reihenfolge (LOGFMT v2). Die fuehrende Marker-Spalte "PUSE"
# diskriminiert strukturierte v2-Zeilen von alten freien 5-Spalten-Zeilen (B-3).
LOG_MARKER = "PUSE"
LOG_FIELDS = ["ts", "signal", "pattern_id", "scope", "commit_sha", "file_anchor", "fac_id", "note"]
# signal: VERIFIED (R1) | CONFORMANCE_PASS (R2) | REVERT (R4) | KEIN_PATTERN (legacy-info)


def _usage_log_path(vault_root=None) -> Path:
    """R6a-Anker (B-1): Log liegt VAULT-resolved, NICHT worktree-lokal (fixt W-FEED-1/W-LEAK-1)."""
    return resolve_vault_root(vault_root) / USAGE_LOG_RELPATH


def _usage_cursor_path(vault_root=None) -> Path:
    return resolve_vault_root(vault_root) / USAGE_LOG_CURSOR_RELPATH


def format_usage_line(signal, pattern_id, scope="arch", commit_sha="",
                      file_anchor="", fac_id="", note="", ts=None) -> str:
    """LOGFMT: serialisiert EINE strukturierte v2-Zeile in der kanonischen Konvention.

    Pipes in Feldwerten werden escaped, damit die Spalten-Konvention stabil bleibt.
    """
    ts = ts or date.today().isoformat()
    vals = [ts, signal, pattern_id or "", scope or "", commit_sha or "",
            file_anchor or "", fac_id or "", note or ""]
    cells = [str(v).replace("|", "/").strip() for v in vals]
    return LOG_MARKER + " | " + " | ".join(cells)


def parse_usage_line(line: str):
    """LOGFMT-Parser (AK-CTX-LOGFMT + B-3 rueckwaerts-tolerant).

    -> dict mit Schluesseln aus LOG_FIELDS (+ 'raw'/'structured') fuer strukturierte
    v2-Zeilen (Marker-Prefix). Alte freie 5-Spalten-Zeilen / Header / Leerzeilen
    werfen KEINE Exception: -> None (Skip-tolerant, der Drain ueberspringt sie).
    """
    if line is None:
        return None
    s = line.strip()
    if not s or s.startswith("#") or s.startswith("##"):
        return None
    parts = [p.strip() for p in s.split("|")]
    # Strukturierte v2-Zeile: erster Token == Marker
    if parts and parts[0] == LOG_MARKER:
        cells = parts[1:]
        rec = {f: (cells[i] if i < len(cells) else "") for i, f in enumerate(LOG_FIELDS)}
        rec["structured"] = True
        rec["raw"] = s
        return rec
    # Alte freie Zeile -> tolerant: kein Strukturanspruch, Drain skippt (B-3).
    return None


# ── R6a (AK-CTX-R6a) — vault-resolved + append-lock-gated Log-Writer ──
def append_usage(signal, pattern_id, scope="arch", commit_sha="", file_anchor="",
                 fac_id="", note="", vault_root=None, worker_id=None, lock_scope="pattern-usage"):
    """R6a: schreibt EINE strukturierte Usage-Signal-Zeile vault-resolved (B-1) und
    append-lock-gated (B-2, Reuse factory_lock.acquire/release; Import-Seam neu).

    SIGNAL-ONLY (ADR-PL-008): bewegt den Counter NICHT — das macht ausschliesslich
    der Drain (R6b). -> Path der Log-Datei.
    """
    log_path = _usage_log_path(vault_root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = format_usage_line(signal, pattern_id, scope=scope, commit_sha=commit_sha,
                             file_anchor=file_anchor, fac_id=fac_id, note=note)

    # B-2: APPEND zwischen acquire/release. factory_lock optional (graceful) — der
    # Writer haengt nicht an dessen Verfuegbarkeit, aber WENN da, umschliesst er den APPEND.
    fl = None
    try:
        import factory_lock as fl  # type: ignore  # Import-Seam neu (F3)
    except Exception:
        fl = None

    wid = worker_id or f"pattern-usage-{os.getpid()}"
    acquired = False
    if fl is not None:
        try:
            acquired = fl.acquire(scope=lock_scope, worker_id=wid, purpose="pattern-usage-append",
                                  vault_root=vault_root)
        except Exception:
            acquired = False
    try:
        prefix = "" if (log_path.exists()
                        and log_path.read_text(encoding="utf-8", errors="replace").endswith("\n")) else "\n"
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(prefix + line + "\n")
    finally:
        if fl is not None and acquired:
            try:
                fl.release(wid, vault_root=vault_root)
            except Exception:
                pass
    return log_path


# ── R6b (AK-CTX-R6b) — EINZIGER autorisierter Drain, idempotent via processed-Cursor ──
def _read_cursor(vault_root=None) -> int:
    p = _usage_cursor_path(vault_root)
    if not p.exists():
        return 0
    try:
        return int(p.read_text(encoding="utf-8", errors="replace").strip() or "0")
    except (TypeError, ValueError):
        return 0


def _write_cursor(n: int, vault_root=None) -> None:
    p = _usage_cursor_path(vault_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(int(n)), encoding="utf-8")


def drain_usage_log(vault_root=None, scope=None) -> dict:
    """R6b: EIN autorisierter Konsument (ADR-PL-008, F5/F9). Liest die seit dem
    letzten Drain NEUEN Zeilen (processed-Cursor = Anzahl bereits verarbeiteter
    physischer Zeilen) und ruft pro strukturiertem Signal den fertigen Sink
    (lifecycle pfad-1 fuer VERIFIED/CONFORMANCE_PASS; pfad-2 fuer REVERT).

    IDEMPOTENZ (K-1): zweimal drainen == einmal usage++. Der Cursor wird NACH dem
    Verarbeiten auf die Gesamtzeilenzahl gesetzt; ein zweiter Lauf sieht 0 neue
    Zeilen -> kein Doppel-Zaehlen. Rueckwaerts-tolerant (B-3): alte freie Zeilen
    werden uebersprungen (parse_usage_line -> None), zaehlen aber als verarbeitet
    (Cursor advanced), damit sie den Drain nicht endlos blockieren.

    -> {processed_now, usage_pp, broken_pp, cursor_before, cursor_after, skipped}
    """
    log_path = _usage_log_path(vault_root)
    if not log_path.exists():
        return {"processed_now": 0, "usage_pp": 0, "broken_pp": 0,
                "cursor_before": 0, "cursor_after": 0, "skipped": 0, "results": []}

    all_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    cursor_before = _read_cursor(vault_root)
    # Cursor jenseits aktueller Laenge (z.B. Log gekuerzt) -> defensiv auf Laenge clampen.
    if cursor_before > len(all_lines):
        cursor_before = len(all_lines)
    new_lines = all_lines[cursor_before:]

    usage_pp = 0
    broken_pp = 0
    skipped = 0
    results = []
    for raw in new_lines:
        rec = parse_usage_line(raw)
        if rec is None or not rec.get("pattern_id"):
            skipped += 1
            continue
        if scope is not None and rec.get("scope") and rec["scope"] != scope:
            skipped += 1
            continue
        sig = rec.get("signal", "")
        sc = rec.get("scope") or "arch"
        pid = rec["pattern_id"]
        if sig in ("VERIFIED", "CONFORMANCE_PASS"):
            res = lifecycle(pid, "1", scope=sc, vault_root=vault_root)
            usage_pp += 1
            results.append(res)
        elif sig == "REVERT":
            res = lifecycle(pid, "2", scope=sc, vault_root=vault_root,
                            broken_context=rec.get("file_anchor", "?"),
                            broken_reason=rec.get("note") or "git-revert (R4)")
            broken_pp += 1
            results.append(res)
        else:
            skipped += 1

    cursor_after = len(all_lines)
    _write_cursor(cursor_after, vault_root)
    return {"processed_now": len(new_lines), "usage_pp": usage_pp, "broken_pp": broken_pp,
            "cursor_before": cursor_before, "cursor_after": cursor_after,
            "skipped": skipped, "results": results}


# ── R4 (AK-CTX-R4) — git-Revert-Detektor + konservatives Anti-False-Positive-Gate ──
def is_revert_of_application(candidate, applied_commit_sha="", applied_file_anchor="") -> bool:
    """R4-Gate (K-2, F8): entscheidet KONSERVATIV, ob ``candidate`` ein echter Revert
    einer Pattern-Anwendung ist. Verlangt BEIDE LOGFMT-Anker als Match:
      - commit_sha des Revert-Ziels == die angewandte commit_sha, UND
      - file_anchor (betroffene Datei) == der angewandte file_anchor.

    Ohne diesen Doppel-Match -> False (KEIN broken++). Ein unabhaengiger Datei-Edit
    OHNE commit_sha/file_anchor-Match loest NIE pfad-2 aus (Schutz vor irreversiblem
    auto-deprecate@3, B-4). candidate ist ein dict mit optionalen Schluesseln
    ``reverted_commit_sha``/``commit_sha`` und ``file_anchor``.
    """
    if not applied_commit_sha or not applied_file_anchor:
        return False  # ohne Anker kann ein echter Revert nicht erkannt werden -> konservativ
    cand_sha = (candidate.get("reverted_commit_sha")
                or candidate.get("commit_sha") or "")
    cand_anchor = candidate.get("file_anchor", "")
    if not cand_sha or not cand_anchor:
        return False
    return cand_sha == applied_commit_sha and cand_anchor == applied_file_anchor


def detect_and_emit_revert(pattern_id, candidate, applied_commit_sha="",
                           applied_file_anchor="", scope="arch", vault_root=None) -> dict:
    """R4: prueft das Gate (is_revert_of_application) VOR jeglicher Counter-Mutation.
    Bei echtem Match wird NUR ein REVERT-Signal in den Log appendet (Signal-Pfad,
    ADR-PL-008) — den broken++ macht der Drain (R6b -> lifecycle pfad-2). Damit
    bleibt auch der irreversible auto-deprecate@3 hinter genau EINEM Konsumenten.

    -> {gated: bool, emitted: bool} — gated=True heisst: Gate hat blockiert (kein Signal).
    """
    if not is_revert_of_application(candidate, applied_commit_sha, applied_file_anchor):
        return {"gated": True, "emitted": False, "pattern_id": pattern_id}
    append_usage("REVERT", pattern_id, scope=scope,
                 commit_sha=applied_commit_sha, file_anchor=applied_file_anchor,
                 note=candidate.get("note", "git-revert (R4)"), vault_root=vault_root)
    return {"gated": False, "emitted": True, "pattern_id": pattern_id}


def migrate(scope="arch", vault_root=None) -> int:
    """AK-MIG-0: Bestands-Pattern-Backfill — Counter-Felder nachruesten (idempotent, kein Ueberschreiben).

    -> Anzahl geaenderter Files. Patterns OHNE usage_count kriegen die _COUNTER_DEFAULTS; bestehende
    Werte bleiben unangetastet (APPEND-ohne-Ueberschreiben).
    """
    lib = _scope_library_root(scope, vault_root)
    migrated = 0
    files = list(lib.glob("_project/*/*.md")) + list(lib.glob("_generic/*.md"))
    for f in files:
        if f.name == "_index.md":
            continue
        fm, body = _split_fm(_read_text(f))
        if fm is None or _fm_get(fm, "id") is None:
            continue  # kein Pattern-File
        changed = False
        if _fm_get(fm, "scope") is None:
            fm = _fm_set(fm, "scope", scope); changed = True
        for key, default in _COUNTER_DEFAULTS:
            if _fm_get(fm, key) is None:
                fm = _fm_set(fm, key, default); changed = True
        if changed:
            f.write_text(_join_fm(fm, body), encoding="utf-8")
            migrated += 1
    return migrated


# ── BL-307 batch_PL2 (PL-307-3) · Backfill fm-LOSER Pattern-Files ──
# migrate() (oben) ruestet NUR Files MIT Frontmatter-``id`` nach — fm-lose Bestands-Files
# (BE-CORE-Drift: nur Markdown-Body ab ``# PT-... — Titel``) fallen am ``fm is None -> continue``
# durch. backfill_missing_fm fuellt GENAU diese Luecke: es schreibt ADDITIV ein YAML-Frontmatter
# vor den unangetasteten Body (lossless). Getrennt von migrate(), weil migrate() bewusst
# fm-lose Nicht-Pattern-Dateien (READMEs etc.) skippt — Backfill ist die opt-in-Gegen-Operation.
_PID_RE = re.compile(r"\b(PT-[A-Z]+(?:-[A-Z]+)*-\d+)\b")


def _pid_from_fm_less(f: Path, body: str):
    """ID eines fm-losen Pattern-Files: H1-Token (``# PT-... — Titel``) vor Dateiname-Praefix."""
    for source in (body.splitlines()[0] if body.strip() else "", f.stem):
        m = _PID_RE.search(source)
        if m:
            return m.group(1)
    return None


def backfill_missing_fm(scope="arch", vault_root=None, dry_run=False) -> int:
    """BL-307 PL-307-3: frontmatter-t fm-LOSE Pattern-Files (die migrate() Z1139 skippt).

    -> Anzahl (potenziell) backfillter Files. Pro fm-loser Datei wird ADDITIV ein YAML-Frontmatter
    (id aus Dateiname/H1, layer aus dem Parent-Ordner, status=experimental default + Counter-Defaults)
    VOR den unangetasteten Body geschrieben — Body LOSSLESS (kein Byte des Markdown-Inhalts geaendert),
    danach per read_counter konsumierbar. Files MIT Frontmatter werden uebersprungen (kein Doppel-FM).
    Idempotent: ein 2. Lauf findet keine fm-losen Files mehr -> 0. ``dry_run=True`` zaehlt nur (md5
    vor==nach, mutiert NICHTS). Reuse _split_fm/_fm_set/_join_fm/_COUNTER_DEFAULTS (kein Re-Invent).
    """
    lib = _scope_library_root(scope, vault_root)
    backfilled = 0
    files = list(lib.glob("_project/*/*.md")) + list(lib.glob("_generic/*.md"))
    for f in files:
        if f.name == "_index.md":
            continue
        fm, body = _split_fm(_read_text(f))
        if fm is not None:
            continue  # hat schon Frontmatter (add_arch-geboren / migrate-genaehrt) -> nicht anfassen
        pid = _pid_from_fm_less(f, body)
        if pid is None:
            continue  # keine ableitbare Pattern-ID -> kein Pattern-File
        backfilled += 1
        if dry_run:
            continue
        layer = f.parent.name  # Parent-Ordner = Layer (BE-DOMAIN etc.)
        new_fm = (
            f"id: {pid}\n"
            f"scope: {scope}\n"
            f"layer: {layer}"
        )
        for key, default in _COUNTER_DEFAULTS:
            new_fm = _fm_set(new_fm, key, default)
        f.write_text(_join_fm(new_fm, body), encoding="utf-8")
    return backfilled


# ── BL-307 batch_PL2 (PL-307-2) · Standalone Layer-Index-Migration (Fremd-Header -> Kanon) ──
# Spiegelt die _append_index_row-In-Place-Migration (Z328-344) — aber STANDALONE: ein drifteter
# Index wird auf den 6-Spalten-Kanon gebracht OHNE dass ein Pattern-Add ihn triggert. REUSE der
# batch_PL1-Helfer (_is_canon_header/_is_table_separator/_split_table_row/_migrate_foreign_row +
# _CANON_IDX_HEADER/_CANON_IDX_SEP) — kein zweiter Migrations-Pfad. dry_run ist DEFAULT True
# (read-first), apply legt ein Backup an (Vorbild reconcile_backlog_index).
def _migrate_index_text(txt: str):
    """Reiner Text->Text-Migrator (Fremd-Header -> Kanon, lossless). -> (neuer_text, migriert?).

    Ist der Tabellen-Header schon der Kanon -> Text unveraendert + migriert=False (idempotent).
    """
    lines = txt.splitlines()
    header_idx = next((i for i, l in enumerate(lines) if _is_table_header(l)), None)
    if header_idx is None or _is_canon_header(lines[header_idx]):
        return txt, False  # schon Kanon (oder gar keine Tabelle) -> no-op
    new_lines, seen_table = [], False
    for i, l in enumerate(lines):
        if i == header_idx:
            new_lines.append(_CANON_IDX_HEADER)
            new_lines.append(_CANON_IDX_SEP)
            seen_table = True
            continue
        if seen_table and _is_table_separator(l):
            continue  # alter Fremd-Separator faellt weg (Kanon-Separator schon gesetzt)
        if seen_table and l.strip().startswith("|") and not _is_table_separator(l):
            new_lines.append(_migrate_foreign_row(_split_table_row(l)))
            continue
        new_lines.append(l)
    return "\n".join(new_lines) + "\n", True


def migrate_index(index_path, dry_run=True, vault_root=None) -> dict:
    """BL-307 PL-307-2: hebt einen drifteten Layer-Index auf den Kanon-6-Spalten — standalone.

    -> {migrated, dry_run, backup}. ``dry_run`` ist DEFAULT True (kein Schreiben ohne explizites
    ``dry_run=False``). Beim apply-Lauf wird VOR dem Ueberschreiben ein Backup angelegt (``<name>.md.
    <stamp>.bak`` — traegt den Original-Fremd-Header, restore-faehig). Idempotent: ein bereits-Kanon-
    Index wird nicht re-migriert (kein Backup, kein Schreiben). lossless (REUSE batch_PL1-Helfer).
    """
    p = Path(index_path)
    if not p.exists():
        return {"migrated": False, "dry_run": dry_run, "backup": None}
    original = p.read_text(encoding="utf-8", errors="replace")
    new_txt, migrated = _migrate_index_text(original)
    backup = None
    if migrated and not dry_run:
        import time
        backup = p.with_suffix(p.suffix + f".{int(time.time() * 1000)}.bak")
        backup.write_text(original, encoding="utf-8")  # Original-Fremd-Header restore-faehig
        p.write_text(new_txt, encoding="utf-8")
    return {"migrated": migrated, "dry_run": dry_run,
            "backup": str(backup) if backup else None}


# ══════════════════════════════════════════════════════════════════════════
# ══ BL-237 batch_C4 AK-7 — DomainLibrary + FactoringLibrary greenfield-Bootstrap ══
# ══════════════════════════════════════════════════════════════════════════
# Architektur (SC-FULL Z5 OBSERVE5 F5/F11 + DOMAIN-GATE-Verdikt F6):
#   Domain bekommt eine EIGENE DomainLibrary (spiegelnd zu PatternLibrary), Factoring eine
#   eigene FactoringLibrary — NICHT auf die A-Pipeline geroutet (C-1, vor-entschieden via
#   W-AXIS-1/2/3 + GOAL/SOA-2). Beide Libraries sind greenfield (F5: Ordner verifiziert ABWESENT).
#   bootstrap_library() legt sie im REPO an (DoD-11: NICHT 486-Live) via add_arch(scope=...) —
#   EINE parametrisierte add-Funktion, kein Klon (F1/DoD-21). Idempotent: ein 2. Lauf erzeugt
#   keine Duplikate (add_arch ist append, der Seed-Guard prueft Existenz vorab).

def bootstrap_library(scope, layer="BE-DOMAIN", seed_name=None, seed_description="",
                      vault_root=None) -> dict:
    """AK-7 (B-2): legt eine greenfield-Library (scope=domain|factoring) im Repo an:
    ``_index.md`` (via _append_index_row) + >=1 Seed-Pattern (via add_arch(scope=...)).

    Reuse-not-rebuild (DoD-21): NUTZT add_arch(scope=...)/next_id(scope=...) — KEIN
    eigener Schreib-Pfad. arch bleibt unberuehrt. Idempotent: existiert bereits ein
    Seed im Layer, wird kein zweiter erzeugt (created=False).

    -> {scope, library, layer, seed_id, seed_path, index_path, created}.
    """
    if scope not in ("domain", "factoring"):
        raise ValueError(f"bootstrap_library: scope muss domain|factoring sein, nicht {scope!r}")
    prefix = _SCOPE_ID_PREFIX[scope]
    ld = _layer_dir(scope, layer, vault_root)
    # Idempotenz (B-2): existiert schon ein scope-eigener Seed in diesem Layer? -> nicht doppeln.
    existing = sorted(ld.glob(f"{prefix}-*.md")) if ld.is_dir() else []
    if existing:
        idx = ld / "_index.md"
        return {"scope": scope, "library": _SCOPE_LIB[scope], "layer": layer,
                "seed_id": existing[0].stem.split("_")[0], "seed_path": existing[0],
                "index_path": idx if idx.exists() else None, "created": False}
    name = seed_name or f"{_SCOPE_LIB[scope]} Seed"
    desc = seed_description or (
        f"Greenfield-Seed der {_SCOPE_LIB[scope]} (BL-237 AK-7 Bootstrap). "
        f"Materialisiert via add_arch(scope={scope!r}) — EIN parametrisierter add-Pfad (kein Klon, DoD-21)."
    )
    pid, fpath, _dedup = add_arch(
        layer, name, description=desc, scope=scope, vault_root=vault_root,
        pattern=f"- (Seed-Pattern fuer die {scope}-Achse; reife via lifecycle(scope={scope!r}))",
    )
    return {"scope": scope, "library": _SCOPE_LIB[scope], "layer": layer,
            "seed_id": pid, "seed_path": fpath,
            "index_path": _layer_dir(scope, layer, vault_root) / "_index.md", "created": True}


def bootstrap_domain_factoring(vault_root=None) -> dict:
    """AK-7-Konvenienz: bootstrappt BEIDE greenfield-Libraries (DomainLibrary + FactoringLibrary)
    in einem Aufruf. -> {domain: {...}, factoring: {...}}."""
    return {
        "domain": bootstrap_library("domain", vault_root=vault_root),
        "factoring": bootstrap_library("factoring", vault_root=vault_root),
    }


# ══════════════════════════════════════════════════════════════════════════
# ══ BL-237 batch_C4 F4 — domain-glossary CONFLICT resolution_status-Trippel ══
# ══════════════════════════════════════════════════════════════════════════
# Architektur (SC-FULL Z5 OBSERVE5 F10):
#   domain-glossary CONFLICT-Eintraege werden als Lern-/Work-Items mit einem
#   resolution_status-Trippel {open|resolved|by_design} materialisiert. by_design ist
#   eine VALIDE Aufloesung (bewusste Design-Entscheidung) und wird NICHT als Noise verworfen.
#   Spiegelt die SL-GLOSS-FM-Struktur (next_sem_id target=glossary). Border (W-1, DoD-12):
#   batch_C4 materialisiert NUR die Trippel-Datenstruktur; der produktive Glossar-Diff-Detektor-
#   Owner (Vorschlag: Conformance-Berater) ist eine offene Verfeinerung und gatet NICHT auf Gold.

RESOLUTION_STATUS = ("open", "resolved", "by_design")


def make_glossary_conflict_item(term, conflict, resolution_status="open",
                                source_a="", source_b="", note="") -> dict:
    """F4 (B-4): erzeugt EIN domain-glossary CONFLICT-Work-Item mit resolution_status-Trippel.

    resolution_status MUSS in {open, resolved, by_design} liegen (sonst ValueError).
    by_design ist eine valide Aufloesung (KEINE Noise, F10) — der Aufrufer/Filter darf es
    NICHT verwerfen. Das Item-Schema spiegelt die SL-GLOSS-FM-Struktur (id/term/scope).
    """
    if resolution_status not in RESOLUTION_STATUS:
        raise ValueError(
            f"resolution_status muss in {RESOLUTION_STATUS} liegen, nicht {resolution_status!r}")
    return {
        "type": "glossary_conflict",
        "scope": "domain",
        "term": term,
        "conflict": conflict,
        "source_a": source_a,
        "source_b": source_b,
        "resolution_status": resolution_status,   # open | resolved | by_design (F4-Trippel)
        "note": note,
        "date": date.today().isoformat(),
    }


def filter_actionable_conflicts(items) -> list:
    """F4 (B-4): liefert die NICHT-erledigten CONFLICT-Items (resolution_status == "open").

    KRITISCH (F10): ``by_design`` wird NICHT als Noise verworfen — es bleibt im vollen
    Item-Bestand erhalten (s. items selbst); es ist nur nicht *actionable* (offen). Diese
    Funktion trennt actionable (open) von erledigt (resolved/by_design), OHNE by_design zu loeschen.
    """
    return [it for it in items if it.get("resolution_status") == "open"]


# ── CLI ──
def _read_arg(val):
    """- = leer; @pfad = Dateiinhalt; sonst literal."""
    if val in (None, "-"):
        return ""
    if val.startswith("@"):
        p = Path(val[1:])
        return p.read_text(encoding="utf-8") if p.exists() else ""
    return val


def main():
    ap = argparse.ArgumentParser(description="Pattern-Library Add/Consult/Lifecycle-Motor (BL-237)")
    sub = ap.add_subparsers(dest="cmd")

    def lib_flags(p):
        g = p.add_mutually_exclusive_group()
        g.add_argument("--arch", action="store_const", dest="kind", const="arch")
        g.add_argument("--semantic", action="store_const", dest="kind", const="semantic")
        # BL-237 batch_C4 F1: 4-kind add — DomainLibrary/FactoringLibrary (numerierter add-Pfad).
        g.add_argument("--domain", action="store_const", dest="kind", const="domain")
        g.add_argument("--factoring", action="store_const", dest="kind", const="factoring")
        p.add_argument("--layer", required=True)
        p.add_argument("--vault-root", default=None)

    p_add = sub.add_parser("add")
    lib_flags(p_add)
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--description", default="")
    p_add.add_argument("--tags", default="")
    p_add.add_argument("--sources", default="")
    p_add.add_argument("--pattern", default="-")
    p_add.add_argument("--beispiel", default="-")
    p_add.add_argument("--abgrenzung", default="-")
    p_add.add_argument("--id", default=None)
    p_add.add_argument("--target", default="terms", help="semantic: terms|naming|glossary")
    p_add.add_argument("--story", default=None)

    p_nid = sub.add_parser("next-id")
    p_nid.add_argument("--arch", action="store_const", dest="kind", const="arch")
    # BL-237 batch_C4 F1/F3: scope-aware ID-Generator (arch->PT, domain->DOM, factoring->FAC).
    p_nid.add_argument("--domain", action="store_const", dest="kind", const="domain")
    p_nid.add_argument("--factoring", action="store_const", dest="kind", const="factoring")
    p_nid.add_argument("--layer", required=True)
    p_nid.add_argument("--vault-root", default=None)

    p_find = sub.add_parser("find")
    p_find.add_argument("query")
    p_find.add_argument("--vault-root", default=None)

    p_list = sub.add_parser("list")
    p_list.add_argument("--arch", action="store_const", dest="kind", const="arch")
    p_list.add_argument("--domain", action="store_const", dest="kind", const="domain")
    p_list.add_argument("--factoring", action="store_const", dest="kind", const="factoring")
    p_list.add_argument("--layer", required=True)
    p_list.add_argument("--vault-root", default=None)

    p_lc = sub.add_parser("lifecycle")
    p_lc.add_argument("pid")
    p_lc.add_argument("--pfad", required=True)
    p_lc.add_argument("--scope", default="arch")
    p_lc.add_argument("--vault-root", default=None)
    p_lc.add_argument("--broken-context", default="")
    p_lc.add_argument("--broken-reason", default="")
    p_lc.add_argument("--new-name", default="")

    p_mig = sub.add_parser("migrate")
    p_mig.add_argument("--scope", default="arch")
    p_mig.add_argument("--layer", default=None, help="semantic: nur diesen Layer migrieren (default: alle)")
    p_mig.add_argument("--vault-root", default=None)

    # ── BL-237 batch_C3a: Counter-Feed CLI (R6a Writer / R6b Drain) ──
    p_au = sub.add_parser("append-usage")
    p_au.add_argument("--signal", required=True, help="VERIFIED|CONFORMANCE_PASS|REVERT")
    p_au.add_argument("--pattern-id", required=True)
    p_au.add_argument("--scope", default="arch")
    p_au.add_argument("--commit-sha", default="")
    p_au.add_argument("--file-anchor", default="")
    p_au.add_argument("--fac-id", default="")
    p_au.add_argument("--note", default="")
    p_au.add_argument("--vault-root", default=None)

    p_dr = sub.add_parser("drain")
    p_dr.add_argument("--scope", default=None)
    p_dr.add_argument("--vault-root", default=None)

    # ── BL-237 batch_C4 AK-7: greenfield-Bootstrap DomainLibrary + FactoringLibrary (Repo) ──
    p_bs = sub.add_parser("bootstrap")
    p_bs.add_argument("--scope", default="both", help="domain|factoring|both")
    p_bs.add_argument("--layer", default="BE-DOMAIN")
    p_bs.add_argument("--vault-root", default=None)

    # ── BL-307 batch_PL2: Backfill fm-loser Pattern-Files + Standalone-Index-Migration ──
    p_bf = sub.add_parser("backfill-fm")
    p_bf.add_argument("--scope", default="arch")
    p_bf.add_argument("--dry-run", action="store_true")
    p_bf.add_argument("--vault-root", default=None)

    p_mi = sub.add_parser("migrate-index")
    p_mi.add_argument("--index", required=True, help="Pfad zur _index.md")
    p_mi.add_argument("--apply", action="store_true", help="ohne --apply = dry-run (read-only)")
    p_mi.add_argument("--vault-root", default=None)

    args = ap.parse_args()

    if args.cmd == "next-id":
        print(next_id(args.layer, args.vault_root,
                      scope=(getattr(args, "kind", None) or "arch"))); return

    if args.cmd == "find":
        for h in find_patterns(args.query, args.vault_root):
            print(h)
        return

    if args.cmd == "list":
        scope = getattr(args, "kind", None) or "arch"
        prefix = _SCOPE_ID_PREFIX.get(scope, "PT")
        ld = _layer_dir(scope, args.layer, args.vault_root)
        for f in sorted(ld.glob(f"{prefix}-*.md")) if ld.is_dir() else []:
            print(f.name)
        return

    if args.cmd == "lifecycle":
        res = lifecycle(args.pid, args.pfad, scope=args.scope, vault_root=args.vault_root,
                        broken_context=args.broken_context, broken_reason=args.broken_reason,
                        new_name=args.new_name)
        print(json.dumps(res, ensure_ascii=False)); return

    if args.cmd == "migrate":
        if args.scope == "semantic":
            # SEMFORMAT-Migration (B-2): Bestands-Bullets -> per-Term-Frontmatter-Dateien (idempotent).
            n = migrate_semantic(layer=getattr(args, "layer", None), vault_root=args.vault_root)
            print(f"[MIGRATE-SEM] {n} Semantic-Bullets auf per-Term-Frontmatter-Dateien gehoben "
                  f"(idempotent, scope=semantic)"); return
        n = migrate(args.scope, args.vault_root)
        print(f"[MIGRATE] {n} Pattern-Files mit Counter-Feldern nachgeruestet (scope={args.scope})"); return

    if args.cmd == "append-usage":
        p = append_usage(args.signal, args.pattern_id, scope=args.scope,
                         commit_sha=args.commit_sha, file_anchor=args.file_anchor,
                         fac_id=args.fac_id, note=args.note, vault_root=args.vault_root)
        print(f"[USAGE-APPEND] signal={args.signal} pattern_id={args.pattern_id} -> {p}"); return

    if args.cmd == "drain":
        res = drain_usage_log(vault_root=args.vault_root, scope=args.scope)
        print(json.dumps(res, ensure_ascii=False)); return

    if args.cmd == "bootstrap":
        if args.scope == "both":
            res = bootstrap_domain_factoring(vault_root=args.vault_root)
        else:
            res = bootstrap_library(args.scope, layer=args.layer, vault_root=args.vault_root)
        # Path-Objekte fuer JSON serialisierbar machen.
        def _ser(o):
            return {k: (str(v) if isinstance(v, Path) else v) for k, v in o.items()}
        out = {k: _ser(v) for k, v in res.items()} if args.scope == "both" else _ser(res)
        print(json.dumps(out, ensure_ascii=False)); return

    if args.cmd == "backfill-fm":
        n = backfill_missing_fm(scope=args.scope, vault_root=args.vault_root, dry_run=args.dry_run)
        verb = "haetten Backfill bekommen (dry-run)" if args.dry_run else "frontmatter-t"
        print(f"[BACKFILL-FM] {n} fm-lose Pattern-Files {verb} (scope={args.scope})"); return

    if args.cmd == "migrate-index":
        res = migrate_index(args.index, dry_run=(not args.apply), vault_root=args.vault_root)
        print(json.dumps(res, ensure_ascii=False)); return

    if args.cmd == "add":
        kind = getattr(args, "kind", None) or "arch"
        if kind == "semantic":
            f, entry = add_semantic(args.layer, args.name, args.description,
                                    target=args.target, vault_root=args.vault_root, story=args.story)
            print(f"[SEMANTIC] {entry}\n  -> {f}")
            return
        # arch | domain | factoring teilen den numerierten add-Pfad (4-kind, F1 — kein 3x-Klon).
        pid, fpath, dedup = add_arch(
            args.layer, args.name, args.description,
            tags=[t.strip() for t in args.tags.split(",") if t.strip()],
            sources=[s.strip() for s in args.sources.split(",") if s.strip()],
            pattern=_read_arg(args.pattern), beispiel=_read_arg(args.beispiel),
            abgrenzung=_read_arg(args.abgrenzung), pid=args.id,
            vault_root=args.vault_root, story=args.story, scope=kind,
        )
        if dedup:
            print(f"[WARN] aehnliches Pattern existiert evtl.: {dedup}", file=sys.stderr)
        print(f"[{kind.upper()}] {pid} -> {fpath}")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
