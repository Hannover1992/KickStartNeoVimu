#!/usr/bin/env python3
"""
health_orchestrate.py — /_health_orchestrate Umbrella-Core (BL-335, batch_PL1).

STATE-Format-Drift Scan -> Report -> Heal-Dispatch. Member-Registry + Health-Report +
Mode-Dispatcher + safety_class-Policy. Abgrenzung: `_sanity_*` = PROZESS-Compliance;
`/_health` = STATE-Format-Drift + Heilung (kein gemeinsames Dach, PL-335-5/6).

1:1-Analog `resolve_format_version.py`-Stil (Vault-First-Loader + Dual-Read-Resilienz,
NIE Crash; dependency-freier Minimal-YAML-Parser). Konsumiert resolve_format_version.py
(BL-333) fuer SOLL/IST-Versions-Drift im Report.

Sicherheits-Invariante (OBERSTE): report-only (Default) erzeugt NIE eine Heal-Action.
Aufruf:
  python3 .claude/scripts/health_orchestrate.py [--mode=report-only|dry-run|heal]
"""
from __future__ import annotations

import sys
from pathlib import Path

import resolve_format_version as rfv

# __file__-RELATIVER Fallback (cwd-INVARIANT) — der Kern von G_cwd (BL-343 PL-343-1).
# .../.claude/scripts/health_orchestrate.py -> parent.parent == .../.claude
REPO_FALLBACK = Path(__file__).resolve().parent.parent / "config" / "health_registry.yaml"

# Sicherheits-Klassen + Modi (closed vocabularies).
SAFETY_CLASSES = ("auto", "lock", "hil")
MODES = ("report-only", "dry-run", "heal")
DEFAULT_MODE = "report-only"  # strukturell read-only Default

# Pflichtfelder je Member (Minimal-Parser-Default fuellt fehlende mit None).
_MEMBER_FIELDS = ("drift_typ", "detector", "healer", "safety_class", "status")


# ---------------------------------------------------------------------------
# Loader (Vault-First, fehlt -> {}, kein Crash) — Stil 1:1 resolve_format_version.py
# ---------------------------------------------------------------------------

def resolve_vault_root() -> Path | None:
    """Delegiert an resolve_format_version.resolve_vault_root (Single Source VAULT_ROOT)."""
    return rfv.resolve_vault_root()


def find_health_registry_yaml() -> Path | None:
    """Vault-First: {vault}/config/health_registry.yaml -> .claude/config/health_registry.yaml."""
    vault = resolve_vault_root()
    if vault is not None:
        candidate = vault / "config" / "health_registry.yaml"
        if candidate.is_file():
            return candidate
    if REPO_FALLBACK.is_file():
        return REPO_FALLBACK
    return None


def _parse_health_registry_minimal(text: str) -> dict:
    """Minimaler YAML-Parser fuer health_registry.yaml (ohne PyYAML-Dependency).

    Struktur:
      health_members:
        {member}:
          drift_typ: {str}
          detector: {str|null}
          healer: {str|null}
          safety_class: {auto|lock|hil}
          status: {wired|spec_only|new_to_create}

    Fuer komplexe YAMLs PyYAML installieren — dieser Parser ist Fallback.
    `null`/leer -> None (analog YAML-Semantik).
    """
    try:
        import yaml  # type: ignore
        for doc in yaml.safe_load_all(text):
            if isinstance(doc, dict) and "health_members" in doc:
                return doc.get("health_members") or {}
        return {}
    except ImportError:
        pass

    out: dict = {}
    in_root = False
    current_member: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("health_members:"):
            in_root = True
            continue
        if not in_root:
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 2 and stripped.endswith(":"):
            # neuer Member-Eintrag (z.B. "  manifest_slim:")
            current_member = stripped[:-1].strip()
            out[current_member] = {}
        elif indent >= 4 and current_member is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.strip()
            if v in ("null", "~", ""):
                out[current_member][k] = None
            else:
                out[current_member][k] = v.strip('"').strip("'")
    return out


def load_health_registry() -> dict:
    """Laedt die Member-Registry {member_name: {drift_typ, detector, healer, safety_class, status}}.

    Fehlende Registry-Datei (find->None) ODER nicht lesbar -> leere Map (kein Crash).
    """
    path = find_health_registry_yaml()
    if path is None:
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return _parse_health_registry_minimal(text)


def get_members() -> dict:
    """Volle Member-Map (Alias zu load_health_registry)."""
    return load_health_registry()


def get_member(member_name: str) -> dict | None:
    """Member-Eintrag oder None bei unbekanntem Member (KEIN KeyError)."""
    return load_health_registry().get(member_name)


def members_by_safety_class(cls: str) -> list[str]:
    """Member-Namen einer safety_class. Unbekannte/leere Klasse -> [] (kein Crash)."""
    members = load_health_registry()
    return [name for name, entry in members.items()
            if isinstance(entry, dict) and entry.get("safety_class") == cls]


def resolve_safety_class(member_name: str) -> str | None:
    """safety_class eines Members oder None bei unbekanntem Member (kein Crash)."""
    entry = get_member(member_name)
    if not isinstance(entry, dict):
        return None
    return entry.get("safety_class")


# ---------------------------------------------------------------------------
# Report (konsumiert resolve_format_version BL-333) — Dual-Read-Resilienz, NIE Crash
# ---------------------------------------------------------------------------

# Frontmatter-Schluessel der den Artefakt-Typ traegt (z.B. `type: manifest`).
_TYPE_KEY = "type"

# Drift-Signale (closed vocabulary): die Drift-Typen die der Scan pro Artefakt erkennt.
# Ein ungestempeltes Artefakt (ist==0) IST der missing_format_version-Drift; ein
# gestempeltes-aber-veraltetes (0 < ist < soll) ist version_lag. Die Heal-Recommendations
# werden PRO erkannter Drift gegen `member.drift_typ` gematcht (kein blanket-all).
DRIFT_MISSING_FORMAT_VERSION = "missing_format_version"
DRIFT_VERSION_LAG = "version_lag"

# Truth-GC-Dimension -> Health-drift_typ-Mapping (BL-399 batch_2, additiv). truth_gc.scan()
# liefert die 5 Dimensions-Keys; jeder mappt auf den drift_typ des zustaendigen GC-Members
# (truth_dup/truth_stale/truth_orphan/truth_format_drift/truth_view_bloat). Nur Dimensionen
# MIT Befunden werden in detected_drifts aufgenommen (drift-typ-gematcht, KEIN blanket-all).
_GC_DIM_TO_DRIFT_TYP = {
    "duplicates": "truth_duplicate",
    "stale": "truth_stale",
    "orphaned": "truth_orphan",
    "format_regression": "truth_format_drift",
    "accumulation": "truth_view_bloat",
}


def _read_frontmatter(path: Path) -> str:
    """Liest den Frontmatter-Block (zwischen den ersten beiden `---`) als Text.

    Kein Fence / nicht lesbar -> leerer String (Gen-0-Pfad, kein Crash).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    fm: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm.append(line)
    return "\n".join(fm)


def _artifact_typ(fm_text: str, default: str) -> str:
    """Artefakt-Typ aus dem Frontmatter (`type:`), sonst Default (Dateiname-Fallback)."""
    for raw in fm_text.splitlines():
        line = raw.strip()
        if line.startswith(f"{_TYPE_KEY}:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'") or default
    return default


def _detect_drifts(ist: int, soll) -> list[str]:
    """Leitet die konkreten Drift-Signale eines Artefakts aus IST/SOLL ab (closed vocab).

    - ist == 0 (ungestempelt/legacy) -> [missing_format_version] (Case-1944-Kanarienvogel):
      das Artefakt traegt KEINEN Stempel; der zustaendige Heiler ist der stamping_heiler.
    - 0 < ist < soll (gestempelt, aber Rueckstand) -> [version_lag].
    - sonst (kein Drift, oder soll unaufloesbar bei gestempeltem ist) -> [].

    Ein ungestempeltes Artefakt ist EINDEUTIG missing_format_version (nicht version_lag) —
    auch wenn die SOLL-Registry hier nicht aufloesbar ist (soll is None).
    """
    if ist == 0:
        return [DRIFT_MISSING_FORMAT_VERSION]
    if soll is not None and ist < soll:
        return [DRIFT_VERSION_LAG]
    return []


def _scan_gc_drift_typs(gc_roots) -> list[str]:
    """READ-ONLY Truth-GC-Scan -> Liste der drift_typen mit Befunden (additiv, BL-399 batch_2).

    gc_roots leer/None -> [] (Verhalten UNVERAENDERT, Regressionsschutz; truth_gc gar nicht
    importiert). Sonst: truth_gc.scan(gc_roots) read-only ausfuehren und je GC-Dimension MIT
    Befunden den gemappten drift_typ aufnehmen (drift-typ-gematcht, KEIN blanket-all). report-only
    — diese Funktion mutiert NIE eine Datei (truth_gc ist read-only).
    """
    if not gc_roots:
        return []
    import truth_gc  # additiv, nur bei vorhandenen gc_roots geladen
    gc_report = truth_gc.scan(list(gc_roots))
    out: list[str] = []
    for dim, drift_typ in _GC_DIM_TO_DRIFT_TYP.items():
        if gc_report.get(dim):  # nur bei Befunden in dieser Dimension
            if drift_typ not in out:
                out.append(drift_typ)
    return out


def generate_health_report(vault_root, *, gc_roots=None) -> dict:
    """Scannt den Vault-Root (mind. _manifest.md) auf Format-Drift.

    Pro Artefakt: format_version_ist (read_format_version; ungestempelt -> 0, NIE Crash) vs
    format_version_soll (resolve_format_version je Typ). Aus IST/SOLL leitet `_detect_drifts`
    die konkreten Drift-Signale ab (`detected_drifts`); pro Signal schlagen wir nur die
    Registry-Member vor, deren `drift_typ` zu diesem Signal passt (DRIFT-TYP-GEMATCHT, KEIN
    blanket-all — ein einzelner Heiler pro erkanntem Drift, nicht jeder Member).

    gc_roots (BL-399 batch_2, additiv): optionale BL-Ordner mit truths/*.md fuer den
    Truth-GC-Scan. Bei Befunden werden die gemappten GC-drift_typen (_GC_DIM_TO_DRIFT_TYP)
    den detected_drifts hinzugefuegt -> die bestehende drift-typ-gematchte Recommendation-Logik
    schlaegt die GC-Member (truth_dup/...) vor. gc_roots leer/None -> Verhalten UNVERAENDERT
    (kein truth_gc-Import, kein GC-Befund). report-only: truth_gc ist read-only, kein auto-heal.

    Struktur:
      { "per_artifact": { <typ>: {format_version_ist, format_version_soll, drift:bool,
                                   detected_drifts:[<drift_typ>,...]} },
        "heal_recommendations": [ {drift, member, safety_class}, ... ] }
    """
    root = Path(vault_root)
    per_artifact: dict = {}

    # Scanne mind. _manifest.md; weitere bekannte Top-Level-Artefakte best-effort.
    candidates = [root / "_manifest.md"]
    for cand in candidates:
        if not cand.is_file():
            continue
        fm_text = _read_frontmatter(cand)
        typ = _artifact_typ(fm_text, default=cand.stem.lstrip("_"))
        ist = rfv.read_format_version(fm_text)        # ungestempelt -> 0 (Gen-0), NIE Crash
        soll = rfv.resolve_format_version(typ)         # unbekannt/fehlt -> None (Gen-0-Sentinel)
        detected = _detect_drifts(ist, soll)
        per_artifact[typ] = {
            "format_version_ist": ist,
            "format_version_soll": soll,
            "drift": bool(detected),
            "detected_drifts": detected,
        }

    # Drift -> Heal-Recommendations DRIFT-TYP-GEMATCHT: fuer jede erkannte Drift schlagen wir
    # NUR die registrierten Member vor, deren `drift_typ` zu DIESER Drift passt. Ein einzelnes
    # ungestempeltes Manifest (missing_format_version) loest also genau den stamping_heiler aus
    # — NICHT jeden auto/lock/hil-Member (kein blanket-all; ueber-eifriger Heiler verhindert).
    # Erfindet KEINE Member: nur was real in der Registry steht mit passendem drift_typ.
    detected_drifts: list[str] = []
    for art in per_artifact.values():
        for d in art.get("detected_drifts", []):
            if d not in detected_drifts:
                detected_drifts.append(d)

    # Additiv (BL-399 batch_2): Truth-GC-drift_typen anhaengen, falls gc_roots Befunde liefern.
    # gc_roots leer/None -> _scan_gc_drift_typs liefert [] -> detected_drifts unveraendert.
    for d in _scan_gc_drift_typs(gc_roots):
        if d not in detected_drifts:
            detected_drifts.append(d)

    registry = load_health_registry()
    heal_recommendations: list[dict] = []
    seen: set = set()
    for drift_typ in detected_drifts:
        for name, entry in registry.items():
            if not isinstance(entry, dict):
                continue
            if entry.get("drift_typ") != drift_typ:
                continue
            if name in seen:  # ein Member erscheint pro Report hoechstens einmal
                continue
            seen.add(name)
            heal_recommendations.append({
                "drift": drift_typ,
                "member": name,
                "safety_class": entry.get("safety_class"),
            })

    return {
        "per_artifact": per_artifact,
        "heal_recommendations": heal_recommendations,
    }


def render_report_markdown(report: dict) -> str:
    """Rendert den Health-Report als Mensch-lesbaren Markdown-String (nicht-leer, mit Tabelle)."""
    per = report.get("per_artifact", {})
    recs = report.get("heal_recommendations", [])

    lines: list[str] = []
    lines.append("# Health-Report — STATE-Format-Drift")
    lines.append("")
    lines.append("## Artefakte (format_version IST vs SOLL)")
    lines.append("")
    lines.append("| Artefakt | IST | SOLL | Drift |")
    lines.append("|----------|-----|------|-------|")
    for typ, art in per.items():
        ist = art.get("format_version_ist")
        soll = art.get("format_version_soll")
        drift = "ja" if art.get("drift") else "nein"
        soll_s = "-" if soll is None else str(soll)
        lines.append(f"| {typ} | {ist} | {soll_s} | {drift} |")
    lines.append("")
    lines.append("## Heal-Empfehlungen")
    lines.append("")
    if recs:
        lines.append("| Member | Drift | safety_class |")
        lines.append("|--------|-------|--------------|")
        for rec in recs:
            lines.append(
                f"| {rec.get('member')} | {rec.get('drift')} | {rec.get('safety_class')} |"
            )
    else:
        lines.append("_Keine Drift erkannt — keine Heilung noetig._")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Dispatch (mode-gated; safety_class-Policy) — SICHERHEIT zuerst
# ---------------------------------------------------------------------------

def plan_heal(report: dict, mode: str = DEFAULT_MODE) -> list[dict]:
    """Plant Heal-Actions abhaengig vom Mode + safety_class-Policy.

    - report-only (Default) -> [] (OBERSTE Sicherheits-Invariante: NIE eine Action).
    - dry-run -> Plan-Eintraege, jeder mit execute==False (zeigt, fuehrt NICHT aus).
    - heal -> safety_class-Gating:
        auto -> {needs_lock:False, needs_freigabe:False, execute:True}  (direkt)
        lock -> {needs_lock:True, ...}   (Caller acquired vault_lock zweck=health_heal, BL-334)
        hil  -> {needs_freigabe:True, ...} (kein Auto-Execute)
    - unbekannter mode -> ValueError.
    """
    if mode == "report-only":
        return []
    if mode not in MODES:
        raise ValueError(
            f"Unbekannter mode {mode!r}; erlaubt: {MODES} (Default {DEFAULT_MODE!r})"
        )

    recs = report.get("heal_recommendations", []) or []

    if mode == "dry-run":
        plan: list[dict] = []
        for rec in recs:
            plan.append({
                "member": rec.get("member"),
                "drift": rec.get("drift"),
                "safety_class": rec.get("safety_class"),
                "execute": False,
            })
        return plan

    # mode == "heal": safety_class-Gating.
    plan = []
    for rec in recs:
        cls = rec.get("safety_class")
        entry = {
            "member": rec.get("member"),
            "drift": rec.get("drift"),
            "safety_class": cls,
        }
        if cls == "auto":
            entry["needs_lock"] = False
            entry["needs_freigabe"] = False
            entry["execute"] = True
        elif cls == "lock":
            entry["needs_lock"] = True
            entry["needs_freigabe"] = False
            entry["execute"] = False
        elif cls == "hil":
            entry["needs_lock"] = False
            entry["needs_freigabe"] = True
            entry["execute"] = False
        else:
            # Unbekannte/fehlende safety_class fail-safe: keine Auto-Action.
            entry["needs_lock"] = True
            entry["needs_freigabe"] = True
            entry["execute"] = False
        plan.append(entry)
    return plan


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    mode = DEFAULT_MODE
    for arg in argv[1:]:
        if arg.startswith("--mode="):
            mode = arg.split("=", 1)[1]

    if mode not in MODES:
        print(f"ERROR: Unbekannter mode {mode!r}; erlaubt: {MODES}", file=sys.stderr)
        return 1

    vault = resolve_vault_root()
    if vault is None:
        print("ERROR: VAULT_ROOT nicht aufloesbar", file=sys.stderr)
        return 1

    report = generate_health_report(vault)
    print(render_report_markdown(report))

    if mode != "report-only":
        plan = plan_heal(report, mode=mode)
        print(f"\n[{mode}] geplante Heal-Actions: {len(plan)}")
        for entry in plan:
            print(f"  - {entry}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
