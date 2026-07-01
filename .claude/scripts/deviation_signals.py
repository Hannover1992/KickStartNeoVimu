# -*- coding: utf-8 -*-
"""deviation_signals.py — BL-252 AK-1: reiner Deviation-Signal-Sammler.

Crown-2 (System-Health-Deviation-Observer) besteht aus zwei Schichten:
  * AK-1 (DIESES Modul): ein MECHANISCHER Sammler. Er erntet rohe Kandidaten-
    Signale aus den Live-Quellen (audit.jsonl, globales Manifest, Backlog-Index,
    sowie — BL-324 AK-4 — die Lead-Selbst-Reports aus disciplinary_report.jsonl)
    und liefert sie als strukturierte dicts. Er FAELLT KEIN URTEIL, ob ein Signal
    eine echte SOLL<->IST-Abweichung ist.
  * AK-2 (spaeter): ein opus-Agent, der die Signale gegen den Vision-SOLL
    adjudiziert.
  * AK-3 (spaeter): die BL-Generierung pro Cluster.

Design-Eigenschaften (strikt eingehalten):
  * REIN/deterministisch: gleiche Eingabe -> gleiche Ausgabe. Kein Urteil, keine
    BL-Generierung, KEIN Schreibzugriff (read-only Sammler).
  * cwd-stabil: Default-Pfade werden ueber `Path(__file__).resolve()` aufgeloest
    bzw. ueber den `vault_root`-Parameter — nie cwd-relativ. Siehe
    [[feedback_lead_verify_from_repo_root]] (cwd-Artefakt-false-GREEN-Falle).
  * robust: fehlende/leere/kaputte Quellen -> leere Liste, kein Crash.

Signal-Schema (jedes Signal-dict, `SIGNAL_FIELDS`):
  source         : str  — Quelle, eines von {"audit", "manifest", "index",
                          "disciplinary"}.
  kind           : str  — konkreter Anomalie-Typ (z.B. "guard_block",
                          "counter_drift", "status_drift", "stale_lock_reclaim",
                          "lead_deviation_<class>").
  evidence       : dict — rohe Belegdaten (die Event-Zeile bzw. die Feldwerte).
  severity_hint  : str  — grobe Vorab-Klassifikation {"low","medium","high"} —
                          NUR ein Hinweis, KEIN Urteil (das macht AK-2).
  first_seen     : str  — Zeitstempel des (ersten) Auftretens, soweit bekannt,
                          sonst None.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# BL-324 AK-4: die Lead-Selbst-Report-Quelle (disciplinary_report.jsonl) wird
# der 4. Crown-2-Signal-Strom. Wir REUSEN den cwd-stabilen Default-Pfad-Helper
# + die Schema-Konstanten aus disciplinary_report — keine Pfade/Klassen neu
# hardcoden. Defensiv: scheitert der Geschwister-Import (Modul fehlt/kaputt),
# faellt _scan_disciplinary_reports auf [] zurueck (siehe dort), kein Crash.
try:
    import disciplinary_report as _dr  # type: ignore
except ImportError:  # pragma: no cover — Geschwister-Modul fehlt (Defensiv-Pfad)
    _dr = None

SIGNAL_FIELDS = ("source", "kind", "evidence", "severity_hint", "first_seen")

# BL-<digits> am Anfang eines Dateinamens (Slug + .md folgen optional).
# Matcht sowohl "BL-002.md" als auch "BL-001-wahrheiten-taxonomie.md".
_BL_ID_RE = re.compile(r"^(BL-\d+)(?:[-.]|$)")


def _bl_id_from_filename(name: str):
    """-> kanonische BL-ID ("BL-001") aus einem Backlog-Dateinamen, sonst None."""
    m = _BL_ID_RE.match(name)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Pfad-Aufloesung (cwd-stabil)
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Repo-Root = zwei Ebenen ueber dieser Datei (.claude/scripts/<file>)."""
    return Path(__file__).resolve().parents[2]


def _default_audit_path() -> Path:
    return _repo_root() / ".claude" / "audit" / "audit.jsonl"


def _resolve_vault_root(vault_root=None) -> Path:
    """Vault-Root: explizit gegeben oder aus .vault_root-Pointer/Default abgeleitet.

    Fuer den Sammler ist `vault_root` der Param-Pfad. Ohne Param fallen wir auf
    einen geschwister-Default zurueck (Documents/OmniCommand neben dem Repo) —
    aber NIE cwd-relativ.
    """
    if vault_root is not None:
        return Path(vault_root)
    # Geschwister-Vault: <...>/Documents/OmniCommand (Repo liegt unter
    # <...>/Documents/Projekt/OmniCommand/OmniCommand).
    root = _repo_root()
    candidate = root.parents[2] / "OmniCommand"
    return candidate


# ---------------------------------------------------------------------------
# Audit-Anomalien
# ---------------------------------------------------------------------------

# Event -> (kind, severity_hint). NUR Anomalie-Events; Normal-Betriebsevents
# (WORKER_SPAWN/SKILL_LOAD/STATE_WRITE/HANDOFF/LOCK_CLAIMED/...) sind bewusst
# NICHT enthalten — sie sind kein Signal (kein Ueber-Melden).
_AUDIT_ANOMALY_MAP = {
    "GUARD_BLOCK": ("guard_block", "high"),
    "HARD_GATE_BLOCK": ("hard_gate_block", "high"),
    "WORKER_RUNAWAY_BLOCKED": ("worker_runaway", "high"),
    "GEIST5_CONTRACT_VIOLATION": ("contract_violation", "high"),
    "PARAM_MUTATION_BLOCKED": ("param_mutation_blocked", "high"),
    "HOOK_PREP_AGENT_BLOCKED": ("hook_prep_blocked", "medium"),
    "ROLLBACK": ("rollback", "high"),
    "LOCK_STALE_RECLAIM": ("stale_lock_reclaim", "medium"),
    "LOCK_FORCE_RELEASED": ("lock_force_released", "medium"),
    "WORKER_RUNAWAY": ("worker_runaway", "high"),
    "GUARD_WARN": ("guard_warn", "low"),
    "MOTOR_OVERRIDE": ("motor_override", "low"),
}
# Praefix-basierte Anomalien (z.B. PROCESS_BYPASS_DETECTED_SC_M4/M5/M6/M7).
_AUDIT_ANOMALY_PREFIXES = (
    ("PROCESS_BYPASS_DETECTED", "process_bypass", "high"),
)


def _classify_audit_event(event_name):
    """-> (kind, severity_hint) wenn Anomalie, sonst None (Normal-Event)."""
    if not isinstance(event_name, str):
        return None
    hit = _AUDIT_ANOMALY_MAP.get(event_name)
    if hit is not None:
        return hit
    for prefix, kind, sev in _AUDIT_ANOMALY_PREFIXES:
        if event_name.startswith(prefix):
            return (kind, sev)
    return None


def _scan_audit(audit_path=None, since=None) -> list:
    """Scannt audit.jsonl auf Anomalie-Events. Read-only, robust.

    `since` (ISO-Timestamp-String): wenn gesetzt, nur Events mit ts >= since.
    Vergleich ist lexikographisch — fuer ISO-8601-Timestamps korrekt.
    """
    path = Path(audit_path) if audit_path is not None else _default_audit_path()
    signals = []
    try:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue  # kaputte Zeile -> ueberspringen
                if not isinstance(obj, dict):
                    continue
                event_name = obj.get("event")
                classified = _classify_audit_event(event_name)
                if classified is None:
                    continue  # Normal-Event: kein Signal
                kind, sev = classified
                ts = obj.get("ts")
                if since is not None and ts is not None and str(ts) < str(since):
                    continue
                signals.append(
                    {
                        "source": "audit",
                        "kind": kind,
                        "evidence": obj,
                        "severity_hint": sev,
                        "first_seen": ts,
                    }
                )
    except OSError:
        return []
    return signals


# ---------------------------------------------------------------------------
# Counter-Drift (Manifest BACKLOG_STATE.backlog_counter vs Index-Header)
# ---------------------------------------------------------------------------

def _read_text(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _parse_manifest_counter(vault_root: Path):
    """Liest backlog_counter aus dem BACKLOG_STATE-Block des Manifests.

    Robust gegen das zweite, unabhaengige `backlog_counter:` an anderer Stelle
    im Manifest: wir verankern am `BACKLOG_STATE`-Block.
    """
    txt = _read_text(vault_root / "_manifest.md")
    if not txt:
        return None
    anchor = txt.find("BACKLOG_STATE")
    scope = txt[anchor:] if anchor >= 0 else txt
    for line in scope.splitlines():
        s = line.strip()
        if s.startswith("backlog_counter:"):
            val = s.split(":", 1)[1].strip()
            try:
                return int(val)
            except ValueError:
                return None
    return None


def _parse_index_counter(vault_root: Path):
    """Liest backlog_counter aus dem Frontmatter-Header des Index."""
    txt = _read_text(vault_root / "_backlog_index.md")
    if not txt:
        return None
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("backlog_counter:"):
            val = s.split(":", 1)[1].strip()
            try:
                return int(val)
            except ValueError:
                return None
        # Header-Tabelle erreicht -> aufhoeren
        if s.startswith("| BL-") or s.startswith("# Backlog"):
            break
    return None


def _scan_counter_drift(vault_root=None) -> list:
    """Manifest-Counter != Index-Counter -> 1 counter_drift-Signal."""
    vr = _resolve_vault_root(vault_root)
    m = _parse_manifest_counter(vr)
    i = _parse_index_counter(vr)
    if m is None or i is None:
        return []  # eine Quelle fehlt -> kein vergleichbares Signal
    if m == i:
        return []
    return [
        {
            "source": "manifest",
            "kind": "counter_drift",
            "evidence": {
                "manifest_counter": m,
                "index_counter": i,
                "delta": m - i,
            },
            "severity_hint": "medium",
            "first_seen": None,
        }
    ]


# ---------------------------------------------------------------------------
# Status-Drift (BL-Frontmatter status vs Index-Zeile status)
# ---------------------------------------------------------------------------

def _parse_index_statuses(vault_root: Path) -> dict:
    """-> {bl_id: status} aus den Tabellen-Zeilen des Index.

    Header-anker: ermittelt die Status-Spalte aus der Header-Zeile
    (`| BL-ID | Title | Status | ...`). Robust gegen Zeilen mit abweichender
    Spaltenzahl (z.B. defekte/umgebrochene Titel mit eingebetteten Pipes) —
    solche Zeilen werden uebersprungen, statt eine falsche Spalte zu lesen.
    """
    txt = _read_text(vault_root / "_backlog_index.md")
    if not txt:
        return {}
    result = {}
    status_col = 2  # Default: 3. Spalte
    n_cols = None
    for line in txt.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        # Header-Zeile erkennen
        if "BL-ID" in cells and "Status" in cells:
            status_col = cells.index("Status")
            n_cols = len(cells)
            continue
        # Trenn-Zeile (|---|---|...) ueberspringen
        if all(set(c) <= {"-", ":"} and c for c in cells):
            continue
        bl_id = cells[0]
        if not bl_id.startswith("BL-"):
            continue
        # Spaltenzahl muss zum Header passen (sonst: umgebrochene/defekte Zeile)
        if n_cols is not None and len(cells) != n_cols:
            continue
        if len(cells) <= status_col:
            continue
        result[bl_id] = cells[status_col]
    return result


def _parse_bl_frontmatter_status(bl_path: Path):
    """Liest `status:` aus dem YAML-Frontmatter einer BL-Datei."""
    txt = _read_text(bl_path)
    if not txt:
        return None
    in_fm = False
    for line in txt.splitlines():
        s = line.rstrip()
        if s.strip() == "---":
            if not in_fm:
                in_fm = True
                continue
            else:
                break  # Frontmatter-Ende
        if in_fm and s.strip().startswith("status:"):
            return s.split(":", 1)[1].strip()
    return None


def _scan_status_drift(vault_root=None) -> list:
    """BL-Frontmatter-status != Index-Zeile-status -> status_drift-Signal/BL."""
    vr = _resolve_vault_root(vault_root)
    index_statuses = _parse_index_statuses(vr)
    if not index_statuses:
        return []
    backlog_dir = vr / "Backlog"
    if not backlog_dir.exists():
        return []
    # Map bl_id -> Datei (erste passende), damit wir nicht ratemuessen.
    file_by_id = {}
    try:
        # sortiert -> deterministisch (erste Datei je id gewinnt)
        for fp in sorted(backlog_dir.glob("*.md")):
            bl_id = _bl_id_from_filename(fp.name)
            if bl_id is not None:
                file_by_id.setdefault(bl_id, fp)
    except OSError:
        return []

    signals = []
    for bl_id in sorted(index_statuses):
        index_status = index_statuses[bl_id]
        fp = file_by_id.get(bl_id)
        if fp is None:
            continue  # keine Frontmatter-Quelle -> nicht vergleichbar
        fm_status = _parse_bl_frontmatter_status(fp)
        if fm_status is None:
            continue
        if fm_status != index_status:
            signals.append(
                {
                    "source": "index",
                    "kind": "status_drift",
                    "evidence": {
                        "bl_id": bl_id,
                        "frontmatter_status": fm_status,
                        "index_status": index_status,
                        "file": str(fp),
                    },
                    "severity_hint": "medium",
                    "first_seen": None,
                }
            )
    return signals


# ---------------------------------------------------------------------------
# Lead-Selbst-Reports (disciplinary_report.jsonl) — BL-324 AK-4, 4. Quelle
# ---------------------------------------------------------------------------

# severity_hint pro Lead-Selbstmeldung: eine FALSCH-gewesene Abweichung
# (was_correct=False) wiegt schwerer als eine richtige — sie zeigt einen echten
# SOLL-Bruch, nicht nur eine Maschinen-Selbstgenuegsamkeits-Luecke. KEIN Urteil
# (das macht Crown-2 Phase 3) — nur ein grober Vorab-Hinweis, analog den anderen
# Scans. Beide bleiben unter "high": Lead-SELBST-gemeldete Abweichungen sind per
# Design legitim/begruendet (INV-DR-1, NICHT-punitiv) — die Adjudikation hebt sie
# bei Bedarf an, nicht der Sammler.
_DISCIPLINARY_SEVERITY = {True: "low", False: "medium"}


def _scan_disciplinary_reports(report_path=None) -> list:
    """Scannt disciplinary_report.jsonl auf Lead-Selbst-Reports. Read-only, robust.

    BL-324 AK-4: schliesst den Lern-Loop — die Lead-SELBST-gemeldeten Abweichungen
    (Urteils-Calls, begruendete Overrides, machine-missed-catches) fliessen als
    4. Signal-Strom in Crown-2s collect + Adjudikation + gated Generierung. So
    pickt Crown-2 wiederkehrende Lead-Abweichungen automatisch auf (mit Dedupe in
    Phase 4), statt dass sie nur im Feldjaeger-Aggregat haengen bleiben.

    Pro validem Eintrag ein Signal:
      source="disciplinary", kind="lead_deviation_<deviation_class>",
      evidence=<der Report-Eintrag>, severity_hint (was_correct->low sonst medium),
      first_seen=<ts>.

    KONSERVATIV: nur Eintraege mit `deviation_class` aus den belegten
    `DEVIATION_CLASSES` werden emittiert (reuse der disciplinary_report-
    Validierungs-Idee). Robust: fehlende/leere/kaputte Datei oder fehlendes
    Geschwister-Modul -> [], kein Crash.
    """
    if _dr is None:  # pragma: no cover — Geschwister-Modul fehlte beim Import
        return []
    path = _dr._resolve_report_path(report_path)
    signals = []
    try:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue  # kaputte Zeile -> ueberspringen
                if not isinstance(obj, dict):
                    continue
                cls = obj.get("deviation_class")
                if cls not in _dr.DEVIATION_CLASSES:
                    continue  # unbekannte/eingeschmuggelte Klasse -> kein Signal
                was_correct = obj.get("was_correct")
                signals.append(
                    {
                        "source": "disciplinary",
                        "kind": "lead_deviation_" + cls,
                        "evidence": obj,
                        # was_correct ist im Schema bool; alles andere (defensiv)
                        # faellt auf "medium" (gewichtigerer Fall).
                        "severity_hint": _DISCIPLINARY_SEVERITY.get(
                            was_correct if isinstance(was_correct, bool) else False,
                            "medium",
                        ),
                        "first_seen": obj.get("ts"),
                    }
                )
    except OSError:
        return []
    return signals


# ---------------------------------------------------------------------------
# Top-Level-Aggregator
# ---------------------------------------------------------------------------

def collect_deviation_signals(vault_root=None, audit_path=None, since=None,
                              report_path=None) -> list:
    """Sammelt alle Kandidaten-Deviation-Signale aus allen Quellen.

    Reine, read-only Aggregation der Quellen-Scans. Faellt KEIN Urteil und
    generiert KEINE Backlog-Items (das sind AK-2/AK-3). Robust: jeder Scan
    faengt fehlende/leere Quellen selbst ab und liefert im Zweifel [].

    Vier Quellen: audit.jsonl (Maschinen-Anomalien), Manifest-Counter,
    Index↔Frontmatter-Status und — BL-324 AK-4 — disciplinary_report.jsonl
    (Lead-Selbst-Reports). `report_path` ist der optionale Override fuer die
    disciplinary-Quelle (cwd-stabiler Default via disciplinary_report, wenn None).

    Returns: list[dict] mit dem `SIGNAL_FIELDS`-Schema.
    """
    signals = []
    signals.extend(_scan_audit(audit_path=audit_path, since=since))
    signals.extend(_scan_counter_drift(vault_root=vault_root))
    signals.extend(_scan_status_drift(vault_root=vault_root))
    signals.extend(_scan_disciplinary_reports(report_path=report_path))
    return signals


if __name__ == "__main__":  # pragma: no cover — manueller Live-Lauf (read-only)
    import sys

    # Windows-stdout ist standardmaessig cp1252 -> json.dumps(ensure_ascii=False)
    # crasht bei nicht-cp1252-Zeichen in evidence (UnicodeEncodeError). stdout auf
    # utf-8 umstellen (Py3.7+); fail-safe falls der Stream nicht reconfigurierbar ist.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    sigs = collect_deviation_signals()
    print(f"{len(sigs)} Deviation-Signale gesammelt:", file=sys.stderr)
    for sig in sigs:
        print(json.dumps(sig, ensure_ascii=False))
