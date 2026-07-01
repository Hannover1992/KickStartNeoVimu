# -*- coding: utf-8 -*-
"""crown2_dedupe.py — BL-252 AK-4: Cluster<->Bestands-Backlog-Dedupe (mechanisch).

Crown-2 (System-Health-Deviation-Observer) urteilt pro Deviations-Cluster, ob er
eine echte SOLL<->IST-Abweichung ist (opus-Adjudikation, lebt im Skill), und
generiert dann pro NEUEM echten Cluster ein Backlog-Item via /_backlog. DIESES
Modul ist der mechanisierbare Teil der Phase 4 (DEDUPE): bevor ein BL generiert
wird, prueft `cluster_already_tracked`, ob bereits ein Bestands-BL die Abweichung
abdeckt — Schutz gegen Backlog-Zuspammen mit Duplikaten.

Design-Eigenschaften (strikt, analog [[deviation_signals.py]]):
  * REIN/deterministisch: gleiche Eingabe -> gleiche Ausgabe. Kein Urteil
    (genuine vs noise), keine BL-Generierung, kein Schreibzugriff.
  * cwd-stabil: `load_existing_bls` loest Default-Pfade ueber `Path(__file__).resolve()`
    bzw. den `vault_root`-Param auf — NIE cwd-relativ. Siehe
    [[feedback_lead_verify_from_repo_root]] (cwd-Artefakt-false-GREEN-Falle).
  * robust: fehlende/leere/kaputte Quellen -> leere Liste, kein Crash.
  * KONSERVATIV: im Zweifel KEIN match (lieber ein Item generieren, das der
    opus-Adjudikation/dem User auffaellt, als eine echte Abweichung verschlucken).

Cluster-Signatur (`cluster_signature_from_cluster` / `cluster_already_tracked`):
  kind   : str        — Anomalie-Typ des Clusters (z.B. "stale_lock_reclaim").
  terms  : list[str]  — Schluessel-Evidence-Terme (Datei/Symbol/Guard-Namen, …),
                        die einen Cluster gegen BL-Titel/Body identifizierbar machen.
"""
from __future__ import annotations

import re
from pathlib import Path

# Anteil der Signatur-Terme, der in EINEM Bestands-BL auftauchen muss, damit der
# Cluster als "bereits getrackt" gilt. Konservativ hoch: lieber generieren als
# eine echte Abweichung als Duplikat verschlucken.
_MATCH_RATIO_THRESHOLD = 0.5
# Mindestanzahl getroffener Terme (absolut) — verhindert, dass bei sehr wenigen
# Termen ein einzelner generischer Treffer (z.B. nur "lock") schon dedupet.
_MATCH_MIN_ABSOLUTE = 2

# Status, die ein BL als "erledigt/aufgeloest" markieren (open_only-Filter).
_CLOSED_STATUSES = {"DONE", "DECOMPOSED", "DROPPED", "CLOSED", "ARCHIVED"}

_BL_ID_RE = re.compile(r"^(BL-\d+)(?:[-.]|$)")


def _normalize(value) -> str:
    """-> lowercase, getrimmt. None -> "" (robust gegen fehlende Felder)."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _bl_id_from_filename(name: str):
    m = _BL_ID_RE.match(name)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Kern-Matcher (rein/deterministisch)
# ---------------------------------------------------------------------------

def cluster_already_tracked(cluster_signature: dict, existing_bls: list):
    """Prueft, ob ein Cluster bereits durch ein Bestands-BL abgedeckt ist.

    Args:
      cluster_signature: {"kind": str, "terms": list[str]}.
      existing_bls: list[{"bl_id","title","body"}] (z.B. aus `load_existing_bls`).

    Returns:
      matching_bl_id (str) wenn ein Bestands-BL die Abweichung abdeckt (-> SKIP),
      sonst False (-> generieren). KONSERVATIV: ohne verlaessliche Schluessel-Terme
      wird NIE dedupet (False).
    """
    if not existing_bls:
        return False
    terms = [_normalize(t) for t in (cluster_signature or {}).get("terms", [])]
    terms = [t for t in terms if t]
    # Ohne Schluessel-Terme ist ein blosser kind-Treffer zu schwach -> generate.
    if not terms:
        return False

    # Schwelle: genug Terme-Treffer in EINEM BL (Verhaeltnis UND absolut).
    needed = max(_MATCH_MIN_ABSOLUTE, int(round(len(terms) * _MATCH_RATIO_THRESHOLD)))
    needed = min(needed, len(terms))  # bei sehr wenigen Termen nicht ueber-fordern

    best_id = None
    best_hits = -1
    for bl in existing_bls:
        haystack = _normalize(bl.get("title")) + " " + _normalize(bl.get("body"))
        if not haystack.strip():
            continue
        hits = sum(1 for t in terms if t in haystack)
        if hits >= needed and hits > best_hits:
            best_hits = hits
            best_id = bl.get("bl_id")
    return best_id if best_id is not None else False


def cluster_signature_from_cluster(cluster: dict) -> dict:
    """Leitet eine {kind, terms}-Signatur aus einem Deviations-Cluster ab.

    `kind` = der kind des Clusters (oder der haeufigste kind seiner Signale).
    `terms` = deterministisch sortierte, deduplizierte Schluessel-Evidence-Terme
    aus den `evidence`-Werten der Signale (Datei/Symbol/Guard/Hook-Namen, …).
    Rein/deterministisch.
    """
    cluster = cluster or {}
    signals = cluster.get("signals") or []

    kind = cluster.get("kind")
    if not kind and signals:
        # haeufigster Signal-kind (deterministisch: bei Gleichstand alphabetisch)
        counts = {}
        for s in signals:
            k = s.get("kind")
            if k:
                counts[k] = counts.get(k, 0) + 1
        if counts:
            kind = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    raw_terms = set()
    # Explizit mitgegebene Terme (falls der Cluster sie schon traegt)
    for t in cluster.get("terms", []) or []:
        if _normalize(t):
            raw_terms.add(_normalize(t))
    # Terme aus den Signal-evidence-Werten ernten
    for s in signals:
        ev = s.get("evidence") or {}
        if isinstance(ev, dict):
            for v in ev.values():
                token = _normalize(v)
                # nur "wort-artige" Tokens (Symbol/Name), keine ganzen Saetze/Zahlen-Floods
                if token and len(token) <= 64 and not token.isdigit():
                    raw_terms.add(token)

    terms = sorted(raw_terms)
    return {"kind": kind, "terms": terms}


# ---------------------------------------------------------------------------
# Loader (cwd-stabil) — Index + offene BL-Nodes
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Repo-Root = zwei Ebenen ueber dieser Datei (.claude/scripts/<file>)."""
    return Path(__file__).resolve().parents[2]


def _resolve_vault_root(vault_root=None) -> Path:
    """Vault-Root: explizit gegeben, sonst Geschwister-Default — NIE cwd-relativ.

    Analog zu deviation_signals._resolve_vault_root: Repo liegt unter
    <...>/Documents/Projekt/OmniCommand/OmniCommand, Vault ist das Geschwister
    <...>/Documents/OmniCommand.
    """
    if vault_root is not None:
        return Path(vault_root)
    root = _repo_root()
    return root.parents[2] / "OmniCommand"


def _read_text(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _parse_index_rows(vault_root: Path) -> list:
    """-> list[{bl_id,title,status}] aus den Tabellen-Zeilen des Index.

    Header-anker: ermittelt Title/Status-Spalten aus der Header-Zeile. Robust
    gegen Zeilen mit abweichender Spaltenzahl (defekte/umgebrochene Titel).
    """
    txt = _read_text(vault_root / "_backlog_index.md")
    if not txt:
        return []
    rows = []
    title_col = 1
    status_col = 2
    n_cols = None
    for line in txt.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if "BL-ID" in cells:
            if "Title" in cells:
                title_col = cells.index("Title")
            if "Status" in cells:
                status_col = cells.index("Status")
            n_cols = len(cells)
            continue
        if all(set(c) <= {"-", ":"} and c for c in cells):
            continue
        bl_id = cells[0]
        if not bl_id.startswith("BL-"):
            continue
        if n_cols is not None and len(cells) != n_cols:
            continue
        title = cells[title_col] if len(cells) > title_col else ""
        status = cells[status_col] if len(cells) > status_col else ""
        rows.append({"bl_id": bl_id, "title": title, "status": status})
    return rows


def _bl_body_by_id(vault_root: Path) -> dict:
    """-> {bl_id: full_text} aus dem Backlog/-Dir (erste passende Datei je id)."""
    backlog_dir = vault_root / "Backlog"
    out = {}
    if not backlog_dir.exists():
        return out
    try:
        for fp in sorted(backlog_dir.glob("*.md")):
            bl_id = _bl_id_from_filename(fp.name)
            if bl_id is not None and bl_id not in out:
                out[bl_id] = _read_text(fp)
    except OSError:
        return out
    return out


def load_existing_bls(vault_root=None, open_only: bool = False) -> list:
    """Laedt Bestands-BLs (Index-Zeile + Node-Body) fuer den Dedupe-Match.

    Args:
      vault_root: Vault-Root (cwd-stabil aufgeloest, wenn None).
      open_only: True -> DONE/DECOMPOSED/... rausfiltern (nur offene Items).

    Returns:
      list[{"bl_id","title","status","body"}]. Robust: fehlende Quellen -> [].
    """
    vr = _resolve_vault_root(vault_root)
    rows = _parse_index_rows(vr)
    if not rows:
        return []
    bodies = _bl_body_by_id(vr)
    out = []
    for row in rows:
        if open_only and row.get("status", "").strip().upper() in _CLOSED_STATUSES:
            continue
        bl_id = row["bl_id"]
        out.append(
            {
                "bl_id": bl_id,
                "title": row.get("title", ""),
                "status": row.get("status", ""),
                "body": bodies.get(bl_id, ""),
            }
        )
    return out


if __name__ == "__main__":  # pragma: no cover — manueller Live-Lauf (read-only)
    import json
    import sys

    # Windows-stdout ist standardmaessig cp1252 -> Umlaute in BL-Titeln crashen
    # (UnicodeEncodeError). stdout auf utf-8 umstellen (Py3.7+); fail-safe.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    bls = load_existing_bls(open_only=True)
    print(f"{len(bls)} offene Bestands-BLs geladen (Dedupe-Korpus):", file=sys.stderr)
    for bl in bls:
        print(json.dumps({"bl_id": bl["bl_id"], "title": bl["title"]}, ensure_ascii=False))
