#!/usr/bin/env python3
"""
truth_schema.py — Kanonischer `type: truth` Vertrag (BL-309 Phase A / Truth-Atomisierung).

Eine WAHRHEIT ist das Atom: 1 Wahrheit = 1 Datei. Models/K-Score/SRS/Gap/arc42 werden
generierte Views darueber (Rebuildability-LAW, BL-384). Dieses Modul ist die EINE Quelle
der `type: truth`-Frontmatter-Definition — validate_vault_schema, truth_resolver und der
Atomizer importieren von hier (kein Schema-Duplikat = kein Drift).

Design-Basis: Konzepte/Truth-Migration-Architektur_2026-06-10 (Ziel-Schema) +
Truth-Atomisierung_PriorArt-Assay_2026-06-16 (6 Borrow-Lektionen):
  1. Rebuildability-LAW (Event-Sourcing)  — Views rebuildbar (hier nicht erzwungen, Prinzip)
  2. retract-statt-mutate + Zeit (Datomic) — last_verified_commit + Status-Vokabular mit RETRACTED/INTEGRATED
  3. typisierte edges (RDF-Praedikate)     — edges[] mit rel-Typ
  4. content_hash (Git-CAS)                — optionaler Integritaets-/Dedup-Fingerprint
  5. conref/keyref (DITA)                  — Resolver-Sache, nicht Schema
  6. Ideen-Granularitaet (Zettelkasten)    — Parser-/Atomizer-Sache, nicht Schema

API:
    validate_truth(fm: dict) -> list[tuple[str, str]]
        Prueft NUR die truth-spezifischen Felder/Enums (severity, message).
        PFLICHT_ALL (feature/bl-item/tags/created/updated/type) prueft weiterhin
        validate_vault_schema (truths tragen die auch — Schema-Kompatibilitaet).
    canonical_id(namespace: str, local_id: str) -> str
"""
from __future__ import annotations

import re

# ─── Settled Enums (aus Truth-Migration-Architektur, NICHT mehr verhandelbar) ───
TYP_VALUES: set[str] = {"FESTSTELLUNG", "SOLL", "FRAGE"}
HERKUNFT_VALUES: set[str] = {"INTERN", "EXTERN"}  # treibt SC/WP-Routing
TRUTH_GRADE_VALUES: set[str] = {"code_verified", "vault_hypothesis", "code_contradicted"}

# ─── CANONICAL_STATUS: bekannte Menge; UNBEKANNT = WARN (nicht ERROR), weil die
#     finale Status-Mapping-Tabelle ein Phase-2-HiL-HARD-Gate ist (Konzept-Doc).
#     Migration legalisiert Legacy-Status via status_verbatim. ───
CANONICAL_STATUS: set[str] = {
    "OFFEN", "BESTAETIGT", "AKTIV_BESTAETIGT", "WIDERLEGT", "RETRACTED",
    "INTEGRATED", "VERALTET_DATEI_GELOESCHT", "EXPERIMENT_PROVABLE", "UNGRADED",
}

# ─── Typisierte Kanten (RDF-Praedikat-Lektion). UNBEKANNT = WARN. ───
EDGE_RELS: set[str] = {
    "depends_on", "contradicts", "refines", "supersedes", "superseded_by",
    "getragen_von", "traegt", "kondensiert_aus", "relates_to",
}

# ─── Schema v2 (User-approved 2026-06-16, one-shot-kritisch) ───
# R2: Lebenszyklus als eigene Dimension (neben truth_grade). Reifungs-Maschine = BL-325 Scientific-Mode.
LIFECYCLE_VALUES: set[str] = {
    "asserted", "reviewed", "experiment_proven", "contradicted", "retracted",
}
# R1: Inverse-Index — wer zeigt auf diese Wahrheit (bidirektional, fuer Ripple/Observer BL-388).
REFERENCED_BY_KINDS: set[str] = {
    "pl_source_w", "spec_link", "kscore_ref", "truth_edge", "srs", "arc42", "gap", "task_def",
}

# truth-spezifische Pflichtfelder (zusaetzlich zu PFLICHT_ALL aus validate_vault_schema)
REQUIRED_TRUTH_FIELDS: list[str] = [
    "id", "local_id", "text", "typ", "herkunft", "status", "truth_grade",
]

# id = {namespace}.{local_id} (Fork-1: Punkt-Trenner). namespace = BL-SLUG (kein Punkt im local_id-Teil).
_ID_RE = re.compile(r"^[^.]+\.[^.\s]+$")
_CONTENT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")  # sha256 hex


def canonical_id(namespace: str, local_id: str) -> str:
    """Baut die globale Truth-ID. namespace = BL-SLUG (z.B. 'BL-309-truth-migration')."""
    return f"{namespace}.{local_id}"


def _check_enum(fm: dict, field: str, allowed: set[str], severity: str) -> list[tuple[str, str]]:
    val = fm.get(field)
    if val is None or val == "":
        return []  # Fehlen wird separat als Pflichtfeld-Check behandelt
    if str(val) not in allowed:
        return [(severity, f"truth '{field}'={val!r} nicht in {sorted(allowed)}")]
    return []


def _check_edges(fm: dict) -> list[tuple[str, str]]:
    """edges[] sollten typisiert sein: {rel: <EDGE_RELS>, ziel: <id>}. Untypisiert/unbekannt = WARN."""
    issues: list[tuple[str, str]] = []
    edges = fm.get("edges")
    if edges is None:
        return issues
    if not isinstance(edges, list):
        return [("WARN", "truth 'edges' sollte eine Liste sein")]
    for i, edge in enumerate(edges):
        if isinstance(edge, dict):
            rel = edge.get("rel")
            if rel is None:
                issues.append(("WARN", f"edges[{i}] ohne 'rel' (RDF-Lektion: Kanten typisieren)"))
            elif str(rel) not in EDGE_RELS:
                issues.append(("WARN", f"edges[{i}].rel={rel!r} nicht in {sorted(EDGE_RELS)}"))
            if not edge.get("ziel"):
                issues.append(("WARN", f"edges[{i}] ohne 'ziel'"))
        else:
            issues.append(("WARN", f"edges[{i}] untypisiert ({edge!r}) — auf {{rel, ziel}} migrieren (RDF-Lektion)"))
    return issues


def _check_referenced_by(fm: dict) -> list[tuple[str, str]]:
    """R1 Inverse-Index: referenced_by[] sollte {by, kind} sein. Untypisiert/unbekannt = WARN."""
    issues: list[tuple[str, str]] = []
    rb = fm.get("referenced_by")
    if rb is None:
        return issues
    if not isinstance(rb, list):
        return [("WARN", "truth 'referenced_by' sollte eine Liste sein (Inverse-Index)")]
    for i, ref in enumerate(rb):
        if isinstance(ref, dict):
            if not ref.get("by"):
                issues.append(("WARN", f"referenced_by[{i}] ohne 'by'"))
            kind = ref.get("kind")
            if kind is not None and str(kind) not in REFERENCED_BY_KINDS:
                issues.append(("WARN", f"referenced_by[{i}].kind={kind!r} nicht in {sorted(REFERENCED_BY_KINDS)}"))
        else:
            issues.append(("WARN", f"referenced_by[{i}] untypisiert ({ref!r}) — auf {{by, kind}}"))
    return issues


def validate_truth(fm: dict) -> list[tuple[str, str]]:
    """Validiert die truth-spezifischen Felder eines Frontmatter-Dicts.

    Returns Liste von (severity, message). severity in {ERROR, WARN}.
    ERROR blockt Write (settled enums + Pflichtfelder); WARN ist nicht-blockend
    (Status-Mapping/ID-Form/Kanten — migrationsbedingt noch im Fluss).
    """
    issues: list[tuple[str, str]] = []
    if not isinstance(fm, dict):
        return [("ERROR", "truth: Frontmatter ist kein Dict")]

    # 1. Pflichtfelder (truth-spezifisch)
    for field in REQUIRED_TRUTH_FIELDS:
        val = fm.get(field)
        if val is None or val == "" or val == []:
            issues.append(("ERROR", f"truth: Pflicht-Feld '{field}' fehlt oder leer"))

    # 2. Settled Enums → ERROR bei Verletzung (typ/herkunft/truth_grade sind nicht verhandelbar)
    issues += _check_enum(fm, "typ", TYP_VALUES, "ERROR")
    issues += _check_enum(fm, "herkunft", HERKUNFT_VALUES, "ERROR")
    issues += _check_enum(fm, "truth_grade", TRUTH_GRADE_VALUES, "ERROR")

    # 3. status → WARN bei Unbekannt (Mapping ist Phase-2-HiL-Gate; status_verbatim traegt den Roh-Wert)
    issues += _check_enum(fm, "status", CANONICAL_STATUS, "WARN")

    # 4. ID-Form: {namespace}.{local_id} (Fork-1 Punkt) + Suffix == local_id (Konnektions-Erhalt)
    truth_id = fm.get("id")
    local_id = fm.get("local_id")
    if truth_id:
        if not _ID_RE.match(str(truth_id)):
            issues.append(("WARN", f"truth 'id'={truth_id!r} nicht in Form {{namespace}}.{{local_id}} (Fork-1 Punkt-Trenner)"))
        elif local_id and not str(truth_id).endswith("." + str(local_id)):
            issues.append(("WARN", f"truth 'id'={truth_id!r} endet nicht auf '.{local_id}' (local_id-Konsistenz/never-renumber)"))

    # 5. content_hash (Git-CAS-Lektion): optional, aber wenn da → sha256-hex
    chash = fm.get("content_hash")
    if chash and not _CONTENT_HASH_RE.match(str(chash)):
        issues.append(("WARN", f"truth 'content_hash'={chash!r} kein sha256-hex (64 hex-Zeichen)"))

    # 6. typisierte Kanten
    issues += _check_edges(fm)

    # ─── Schema v2 (one-shot-kritisch) ───
    # 7. lifecycle (R2) — settled enum (ERROR bei Verletzung); Fehlen ok (Atomizer defaultet 'asserted')
    issues += _check_enum(fm, "lifecycle", LIFECYCLE_VALUES, "ERROR")
    # 8. referenced_by[] (R1 Inverse-Index, fuer Ripple BL-388)
    issues += _check_referenced_by(fm)
    # 9. keywords[] (R3 thematische Suche, BL-389)
    kw = fm.get("keywords")
    if kw is not None and not isinstance(kw, list):
        issues.append(("WARN", "truth 'keywords' sollte eine Liste sein (thematische Suche)"))

    return issues
