#!/usr/bin/env python3
"""
worktree_aware_params.py — Worktree-Aware Session-Parameter-Resolution (BL-172 AK-1+AK-2+AK-3).

Erlaubt parallelen Betrieb mehrerer Worktrees ohne gegenseitige _session_params.md-Kollisionen.

Kern-Idee:
  - Single-Worktree-Modus (default): liest/schreibt _session_params.md direkt (rueckwaertskompatibel)
  - Multi-Worktree-Modus: liest/schreibt _session_params_{worktree_id}.md pro Worktree
  - Namespace = git-Branch-Name (oder CLAUDE_WORKTREE_ID ENV-Override)

INV-WORKTREE-1: Jeder Worktree schreibt AUSSCHLIESSLICH in seinen eigenen Namespace.
INV-WORKTREE-2: Single-Worktree-Fallback MUSS identisches Verhalten wie Pre-BL-172 liefern.
INV-WORKTREE-3: Namespace-Resolution via get_worktree_namespace() — niemals hartcodiert.

Aufruf (CLI):
  python3 worktree_aware_params.py resolve [worktree_id]
  python3 worktree_aware_params.py namespace
  python3 worktree_aware_params.py conflict-check
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

_SCRIPT_DIR = Path(__file__).parent.absolute()
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent

# AK-8 (PL-8, SA-2): Maximale Worktree-Nesting-Tiefe. Ueberschreitung → lautes Fail.
MAX_NESTING_DEPTH = 3


# ── Mothership-/Topologie-Resolution (BL-351) ──────────────────────────────────

def _list_worktree_paths() -> list[str]:
    """Liefert die resolved Pfade aller (auch dangling) Worktrees aus
    `git worktree list --porcelain`, in Listing-Reihenfolge.

    Konservativ: bei git-Fehler/Exception/leerer Ausgabe → leere Liste.
    git wird mit cwd=resolve_mothership_root() aufgerufen (AK-3 dynamisch),
    ABER um eine Endlos-Rekursion (resolve_mothership_root → _list_worktree_paths
    → resolve_mothership_root) zu vermeiden, nutzt diese Low-Level-Funktion
    bewusst NICHT resolve_mothership_root, sondern den aktuellen git-Kontext
    (cwd-frei → git findet das Repo selbst).
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return []
        paths: list[str] = []
        for raw in result.stdout.splitlines():
            line = raw.strip()
            if line.startswith("worktree "):
                paths.append(line[len("worktree "):].strip())
        return paths
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []


def _normalize_path_str(p: str) -> str:
    """Normalisiert einen Pfad-String fuer Prefix-/Gleichheits-Vergleiche.

    POSIX- und Windows-Pfade werden auf Forward-Slash + lowercase-Laufwerk
    reduziert, damit die Topologie-Containment-Logik plattform-agnostisch
    arbeitet (Tests nutzen POSIX-Pfade wie /repo/main)."""
    return str(p).replace("\\", "/").rstrip("/")


def resolve_mothership_root(cwd: Optional[Path] = None) -> Path:
    """Loest den Mothership-Root dynamisch auf (AK-1/AK-2/AK-11).

    Statt statisch _PROJECT_ROOT zu verwenden, wird die Worktree-Topologie
    aus `git worktree list --porcelain` ausgewertet:

      - Tiefe 0 (Lauf im Haupt-/einzigen Checkout): Repo-Root selbst.
      - Tiefe >=1 (Lauf in einem Worktree): der naechste Vorfahr-Worktree
        in der Pfad-Hierarchie ist die Mothership — NICHT zwingend 'main'
        (AK-2 nested: grandchild → parent-Worktree, nicht main).

    Die Mothership-Bestimmung ist rein topologisch (Pfad-Containment), damit
    sie auch greift wenn die Mothership selbst ein Worktree ist (nested).

    Fallback (kein git-Kontext / cwd nicht in Liste): statisches _PROJECT_ROOT
    (Rueckwaerts-Kompatibilitaet — INV-WORKTREE-2).
    """
    if cwd is None:
        cwd = Path.cwd()
    cwd_norm = _normalize_path_str(cwd)

    worktree_paths = _list_worktree_paths()
    if not worktree_paths:
        return _PROJECT_ROOT

    norm_paths = [_normalize_path_str(p) for p in worktree_paths]

    # Den Worktree finden, der cwd enthaelt (laengster passender Prefix = current).
    current = _best_containing_path(cwd_norm, norm_paths)
    if current is None:
        # cwd liegt in keinem gelisteten Worktree → Fallback.
        return _PROJECT_ROOT

    # Vorfahren-Worktrees: alle, die echter Pfad-Prefix von 'current' sind.
    ancestors = [
        p for p in norm_paths
        if p != current and _is_path_prefix(p, current)
    ]
    if not ancestors:
        # Tiefe 0: 'current' ist selbst die Wurzel (Haupt-Checkout).
        return Path(current)

    # Mothership = naechster Vorfahr (laengster Prefix von current).
    mothership = max(ancestors, key=len)
    return Path(mothership)


def get_mothership_branch() -> Optional[str]:
    """Liefert den aktuellen Branch der Mothership (AK-5 Split-Anker).

    Der Worktree-Split-Anker ist der Feature-Branch der Mothership, NICHT
    pauschal 'main'. Ermittlung via `git branch --show-current` mit
    cwd=resolve_mothership_root() (AK-3/AK-5 dynamisch).

    Returns:
        Branch-Name oder None (z.B. detached HEAD → leere Ausgabe).
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=3,
            cwd=str(resolve_mothership_root()),
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            return branch if branch else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def resolve_nesting_depth(cwd: Optional[Path] = None) -> int:
    """Bestimmt die Worktree-Nesting-Tiefe rekursiv/topologisch (AK-7/AK-11).

    Tiefe = Position des aktuellen Worktrees in der `git worktree list`-Ordnung
    relativ zum Haupt-Checkout (immer Index 0):
      - 0: Haupt-/einziger Checkout (erster Eintrag = Mothership-Wurzel).
      - 1: direkter Feature-Worktree (zweiter Eintrag, 1 Ebene unter main).
      - N: geschachtelt — der N-te Eintrag in der Hierarchie-Kette.

    Bewusst NICHT die ANZAHL aller Worktrees (flat-count): bei 4 Siblings ist
    jeder einzelne Sibling Tiefe 1 (direktes Kind von main), nicht 3
    (AK-7 sibling-Test). Die Listing-Ordnung von `git worktree list` fuehrt
    main zuerst, dann die Worktrees in Erzeugungs-/Hierarchie-Reihenfolge.
    """
    if cwd is None:
        cwd = Path.cwd()
    cwd_norm = _normalize_path_str(cwd)

    norm_paths = [_normalize_path_str(p) for p in _list_worktree_paths()]
    if not norm_paths:
        return 0

    current = _best_containing_path(cwd_norm, norm_paths)
    if current is None:
        return 0

    # Tiefe = Index des current-Worktrees in der Listing-Ordnung.
    # main (Index 0) = Tiefe 0; jeder weitere Eintrag erhoeht die Tiefe.
    return norm_paths.index(current)


def resolve_merge_target(cwd: Optional[Path] = None) -> str:
    """Leitet das Merge-Ziel Mothership-relativ ab (BL-351 AK-6 / SA-3 / W8 / W15).

    Das Merge-Ziel ist NICHT hart 'develop', sondern der Branch der Mothership.
    Nur wenn get_mothership_branch() None liefert (kein Branch ermittelbar),
    wird 'develop' als Fallback verwendet.

    Tiefen-agnostisch: Bei Tiefe 0 (Mothership = aktueller Root) UND bekanntem
    Branch → Branch verwenden. Nur bei Tiefe 0 UND Branch=None → 'develop'.

    Args:
        cwd: Optionales cwd fuer resolve_nesting_depth (None = Path.cwd()).

    Returns:
        Branch-Name des Merge-Ziels (Mothership-Branch oder 'develop'-Fallback).
    """
    # Nesting-Tiefe bestimmen (fuer kuenftige Erweiterungen / Logging).
    depth = resolve_nesting_depth(cwd)  # noqa: F841 (Tiefe-Information, SA-3)

    # Mothership-Branch abfragen — immer (tiefen-agnostisch).
    mothership_branch = get_mothership_branch()
    if mothership_branch is not None:
        return mothership_branch

    # Kein Branch ermittelbar (z.B. detached HEAD, kein git-Kontext) → Default.
    return "develop"


def check_nesting_depth_cap(depth: int) -> None:
    """Erzwingt das Nesting-Tiefe-Cap (AK-8, SA-2) mit lautem Fail.

    Tiefen 0..MAX_NESTING_DEPTH sind erlaubt. Ueberschreitung wirft einen
    RuntimeError (lautes Fail, NIE stilles Durchlaufen).
    """
    if depth > MAX_NESTING_DEPTH:
        raise RuntimeError(
            f"Worktree-Nesting-Tiefe {depth} ueberschreitet das Cap "
            f"MAX_NESTING_DEPTH={MAX_NESTING_DEPTH}. Lautes Fail (BL-351 AK-8)."
        )


def _is_path_prefix(prefix: str, path: str) -> bool:
    """True, wenn 'prefix' ein echter Verzeichnis-Prefix von 'path' ist.

    Komponenten-genau (verhindert /repo/wt-a als Prefix von /repo/wt-abc)."""
    if prefix == path:
        return False
    return path.startswith(prefix + "/")


def _best_containing_path(target: str, candidates: list[str]) -> Optional[str]:
    """Liefert den Kandidaten mit laengstem Prefix-Match auf target (inkl.
    exakter Gleichheit) — der Worktree, in dem 'target' liegt."""
    matches = [
        c for c in candidates
        if c == target or _is_path_prefix(c, target)
    ]
    if not matches:
        return None
    return max(matches, key=len)


# ── Namespace-Resolution ───────────────────────────────────────────────────────

def get_worktree_namespace(worktree_id: Optional[str] = None) -> Optional[str]:
    """Bestimmt den Worktree-Namespace (worktree_id) fuer den aktuellen Kontext.

    Aufloesung-Reihenfolge:
      1. Expliziter worktree_id-Parameter (haerteste Ueberschreibung)
      2. ENV CLAUDE_WORKTREE_ID (Orchestrator-Override)
      3. git worktree list --porcelain → aktuellen Worktree-Pfad → Branch extrahieren
      4. git branch --show-current (einfachster Fallback)
      5. None → Single-Worktree-Modus aktiviert

    Returns:
        Worktree-ID (bereinigter Branch-Name) oder None.
    """
    if worktree_id is not None:
        return _sanitize_namespace(worktree_id)

    env_override = os.environ.get("CLAUDE_WORKTREE_ID", "").strip()
    if env_override:
        return _sanitize_namespace(env_override)

    # Versuche git worktree list um exakten Worktree-Branch zu ermitteln
    worktree_branch = _resolve_worktree_branch()
    if worktree_branch:
        return _sanitize_namespace(worktree_branch)

    # Einfacher Fallback: aktueller Branch
    branch = _git_current_branch()
    if branch:
        return _sanitize_namespace(branch)

    return None


def _sanitize_namespace(raw: str) -> str:
    """Bereinigt einen Branch-Namen fuer Dateinamen-Verwendung.

    feature/bdf-2026-05-14 → feature_bdf-2026-05-14
    """
    # Schraegsstriche durch Unterstrich ersetzen, Rest behalten
    sanitized = raw.replace("/", "_").replace("\\", "_").strip()
    # Leerzeichen und Sonderzeichen die in Dateinamen problematisch sind entfernen
    sanitized = re.sub(r"[<>:\"|?*]", "_", sanitized)
    return sanitized or "default"


def _resolve_worktree_branch() -> Optional[str]:
    """Ermittelt den Branch des aktuellen Worktrees via git worktree list --porcelain."""
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=5,
            cwd=str(resolve_mothership_root()),
        )
        if result.returncode != 0:
            return None

        cwd_resolved = str(Path.cwd().resolve())
        current_worktree_branch: Optional[str] = None
        active_worktree_path: Optional[str] = None

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("worktree "):
                active_worktree_path = line[len("worktree "):].strip()
                current_worktree_branch = None
            elif line.startswith("branch ") and active_worktree_path:
                branch_ref = line[len("branch "):].strip()
                # refs/heads/feature/bdf-2026-05-14 → feature/bdf-2026-05-14
                if branch_ref.startswith("refs/heads/"):
                    branch_ref = branch_ref[len("refs/heads/"):]
                worktree_path_resolved = str(Path(active_worktree_path).resolve())
                if worktree_path_resolved == cwd_resolved:
                    current_worktree_branch = branch_ref

        return current_worktree_branch
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _git_current_branch() -> Optional[str]:
    """Liefert den aktuellen git-Branch via git branch --show-current."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=3,
            cwd=str(resolve_mothership_root()),
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            return branch if branch else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


# ── Vault-Root-Resolution ──────────────────────────────────────────────────────

def _resolve_vault_root() -> Path:
    """Delegiert an resolve_vault_root.py — kanonische Vault-Resolution."""
    resolver = _SCRIPT_DIR / "resolve_vault_root.py"
    try:
        result = subprocess.run(
            [sys.executable, str(resolver)],
            capture_output=True, text=True, timeout=5,
            cwd=str(resolve_mothership_root()),
        )
        if result.returncode == 0:
            vault_str = result.stdout.strip()
            if vault_str:
                return Path(vault_str)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # Heuristik-Fallback
    return Path.home() / "Documents" / _PROJECT_ROOT.name


def _get_base_params_path(vault_root: Optional[Path] = None) -> Path:
    """Gibt den Pfad zur globalen _session_params.md zurueck (Single-Worktree-Basisdate)."""
    if vault_root is None:
        vault_root = _resolve_vault_root()
    return vault_root / "_session_params.md"


def _get_worktree_params_path(worktree_id: str, vault_root: Optional[Path] = None) -> Path:
    """Gibt den Pfad zur worktree-spezifischen _session_params_{worktree_id}.md zurueck."""
    if vault_root is None:
        vault_root = _resolve_vault_root()
    return vault_root / f"_session_params_{worktree_id}.md"


# ── Haupt-API ──────────────────────────────────────────────────────────────────

def resolve_session_params(
    worktree_id: Optional[str] = None,
    vault_root: Optional[Path] = None,
) -> tuple[Path, str]:
    """Ermittelt den richtigen Session-Params-Pfad fuer den aktuellen Kontext.

    Args:
        worktree_id: Optionale explizite Worktree-ID (None = auto-detect).
        vault_root: Optionaler Vault-Root-Override (None = auto-detect).

    Returns:
        Tuple (params_path, mode) wobei mode = "single" | "multi".

    INV-WORKTREE-2: Wenn kein Worktree-spezifisches File existiert und
    worktree_id ist None → Fallback auf _session_params.md (Single-Modus).
    """
    if vault_root is None:
        vault_root = _resolve_vault_root()

    namespace = get_worktree_namespace(worktree_id)

    if namespace is None:
        # Single-Worktree-Modus: kein Namespace ermittelbar
        return _get_base_params_path(vault_root), "single"

    worktree_path = _get_worktree_params_path(namespace, vault_root)

    # Wenn worktree-spezifische Datei existiert → Multi-Modus
    if worktree_path.exists():
        return worktree_path, "multi"

    # Wenn explizite Worktree-ID angegeben → Multi-Modus auch ohne existierende Datei
    if worktree_id is not None or os.environ.get("CLAUDE_WORKTREE_ID", "").strip():
        return worktree_path, "multi"

    # Genau ein Worktree aktiv → Single-Modus (Rueckwaertskompatibilitaet)
    active_worktrees = _count_active_worktrees()
    if active_worktrees <= 1:
        return _get_base_params_path(vault_root), "single"

    # Mehrere aktive Worktrees → Multi-Modus mit neuem Namespace-File
    return worktree_path, "multi"


def _count_active_worktrees() -> int:
    """Zaehlt ECHT aktive git-Worktrees (inkl. Main) — dangling/prunable raus.

    BL-317 SB-2 (AK-3, INV-G3-4): Der Auto-Multi-Modus-Trigger
    (resolve_session_params Z205-211) darf NICHT auf dangling/Leichen-Worktrees
    feuern. Ein Worktree zaehlt nur als "aktiv", wenn `git worktree list
    --porcelain` ihn NICHT als `prunable` markiert. Ein `locked`-Worktree ist
    explizit gehalten (nie geprunt) → zaehlt als aktiv.

    Diskriminator (porcelain-Records, durch Leerzeile getrennt):
      - `worktree <pfad>`  → startet einen neuen Record
      - `prunable <grund>` → Record ist dangling/stale → NICHT mitzaehlen
      - `locked [<grund>]` → echt aktiv (explizit gehalten) → mitzaehlen

    Konservativer Single-Default: bei jeder Unsicherheit (git-Fehler,
    Exception, leerer/zerstoerter stdout) → 1 zurueck. Multi nur bei
    eindeutig >= 2 ECHT aktiven Worktrees. Backward-compat: 1 echter
    Worktree (heutiger Normalfall) → 1.
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=5,
            cwd=str(resolve_mothership_root()),
        )
        if result.returncode != 0:
            return 1

        active = 0
        in_record = False
        record_prunable = False

        def _close_record() -> None:
            nonlocal active, in_record, record_prunable
            if in_record and not record_prunable:
                active += 1
            in_record = False
            record_prunable = False

        for raw in result.stdout.splitlines():
            line = raw.strip()
            if line.startswith("worktree "):
                # Vorigen Record abschliessen, neuen starten
                _close_record()
                in_record = True
                record_prunable = False
            elif line.startswith("prunable"):
                record_prunable = True
            # `locked`/`branch`/`HEAD`/`detached` aendern den active-Status
            # nicht (locked = explizit aktiv = NICHT prunable)
        # Letzten offenen Record abschliessen (porcelain endet oft ohne Leerzeile)
        _close_record()

        # Konservativ: kein einziger echter Worktree erkennbar → Single-Default
        return active if active >= 1 else 1
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return 1


def write_session_param(
    key: str,
    value: str,
    owner: str = "user",
    worktree_id: Optional[str] = None,
    vault_root: Optional[Path] = None,
) -> tuple[Path, str]:
    """Schreibt oder aktualisiert einen Session-Parameter in der richtigen Datei.

    INV-WORKTREE-1: Schreibt AUSSCHLIESSLICH in den korrekten Namespace.

    Args:
        key: Parameter-Key (z.B. "hil", "difficulty").
        value: Neuer Wert.
        owner: Eigentuemer ("user" | "worker" | "system").
        worktree_id: Optionale explizite Worktree-ID.
        vault_root: Optionaler Vault-Root-Override.

    Returns:
        Tuple (params_path, mode) der beschriebenen Datei.
    """
    if vault_root is None:
        vault_root = _resolve_vault_root()

    params_path, mode = resolve_session_params(worktree_id, vault_root)

    # Existierende Datei lesen oder Template erstellen
    if params_path.exists():
        content = params_path.read_text(encoding="utf-8")
    else:
        content = _generate_worktree_params_template(
            params_path.name,
            get_worktree_namespace(worktree_id),
            vault_root,
        )

    # Zeile suchen und ersetzen oder anhaengen
    owner_suffix = f"  _owner: {owner}" if owner != "system" else ""
    new_line = f"**{key}:** {value}{owner_suffix}"

    # Regex: bestehende **key:** Zeile ersetzen
    pattern = re.compile(rf"^\*\*{re.escape(key)}:\*\*.*$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(new_line, content, count=1)
    else:
        # Am Ende der Parameter-Sektion anhaengen (vor ## Sections)
        section_match = re.search(r"^##\s", content, re.MULTILINE)
        if section_match:
            insert_pos = section_match.start()
            content = content[:insert_pos] + new_line + "\n" + content[insert_pos:]
        else:
            content = content.rstrip("\n") + "\n" + new_line + "\n"

    params_path.parent.mkdir(parents=True, exist_ok=True)
    params_path.write_text(content, encoding="utf-8")
    return params_path, mode


def _generate_worktree_params_template(
    filename: str,
    namespace: Optional[str],
    vault_root: Path,
) -> str:
    """Erzeugt ein neues Worktree-Params-File basierend auf dem Basis-Template.

    Kopiert aktuelle Werte aus _session_params.md und setzt Worktree-Header.
    """
    base_path = _get_base_params_path(vault_root)
    namespace_label = namespace or "unknown"

    header = (
        f"# Schema: worktree-namespace={namespace_label} (BL-172 Multi-Worktree)\n"
        f"# Inherits defaults from _session_params.md — worktree-spezifische Overrides unten\n"
        f"# Session-Parameter\n"
    )

    if base_path.exists():
        # Basis-Params kopieren als Startpunkt
        base_content = base_path.read_text(encoding="utf-8")
        # Nur Parameter-Zeilen kopieren (nicht Aenderungs-Log-Zeilen)
        param_lines = []
        for line in base_content.splitlines():
            stripped = line.strip()
            if stripped.startswith("**") and "**:" in stripped:
                # param_change-Zeilen ueberspringen
                if not stripped.startswith("**param_change"):
                    param_lines.append(line)
        return header + "\n".join(param_lines) + "\n"

    return header


# ── Konflikt-Erkennung ─────────────────────────────────────────────────────────

def check_conflicts(vault_root: Optional[Path] = None) -> list[dict]:
    """Prueft auf potenzielle Konflikte zwischen Worktree-Params-Dateien.

    Erkennt:
      - Mehrere Worktrees mit unterschiedlichen hil= oder difficulty=-Werten
      - Gleicher Namespace in mehreren Worktrees (Kollision)

    Returns:
        Liste von Konflikt-Dictionaries mit keys: type, worktrees, key, values.
    """
    if vault_root is None:
        vault_root = _resolve_vault_root()

    conflicts: list[dict] = []

    # Alle Worktree-Param-Dateien sammeln
    worktree_files: list[tuple[str, Path]] = []

    # Main-File (Single-Modus)
    base_path = _get_base_params_path(vault_root)
    if base_path.exists():
        worktree_files.append(("_main_", base_path))

    # Namespace-Files
    if vault_root.exists():
        for p in vault_root.glob("_session_params_*.md"):
            namespace = p.stem[len("_session_params_"):]
            worktree_files.append((namespace, p))

    if len(worktree_files) < 2:
        return []

    # Parameter pro File extrahieren
    params_per_worktree: dict[str, dict] = {}
    for namespace, path in worktree_files:
        params_per_worktree[namespace] = _extract_params_from_file(path)

    # Kritische Parameter auf Konflikte pruefen
    critical_params = ["hil", "difficulty", "ceiling", "floor", "dark_factory"]
    all_namespaces = list(params_per_worktree.keys())

    for param in critical_params:
        values_seen: dict[str, list[str]] = {}
        for ns in all_namespaces:
            val = params_per_worktree[ns].get(param)
            if val is not None:
                values_seen.setdefault(val, []).append(ns)

        # Wenn verschiedene Worktrees unterschiedliche Werte haben → Konflikt melden
        if len(values_seen) > 1:
            conflicts.append({
                "type": "param_divergence",
                "key": param,
                "values": {v: ns_list for v, ns_list in values_seen.items()},
                "worktrees": all_namespaces,
            })

    return conflicts


def _extract_params_from_file(path: Path) -> dict:
    """Extrahiert key=value Paare aus einer _session_params*.md Datei."""
    params: dict = {}
    if not path.exists():
        return params
    try:
        content = path.read_text(encoding="utf-8")
        for match in re.finditer(r"^\*\*(\w+):\*\*\s*(\S+)", content, re.MULTILINE):
            key = match.group(1).lower()
            value = match.group(2).strip()
            params[key] = value
    except OSError:
        pass
    return params


# ── BL-436: bl_parallel per-Worktree-Aktivierung ──────────────────────────────

def resolve_bl_parallel(worktree_id: Optional[str] = None) -> bool:
    """Liest den bl_parallel-Wert fuer den angegebenen Worktree (BL-436 D1).

    Per-Worktree-Aktivierung: liest aus der worktree-spezifischen
    _session_params_{worktree_id}.md-Datei. Fallback = Framework-Default False.

    Args:
        worktree_id: Optionale explizite Worktree-ID (None = auto-detect via ENV
                     CLAUDE_WORKTREE_ID oder Single-Modus).

    Returns:
        True wenn der Worktree bl_parallel opted-in hat, sonst False.

    INV-WT-DIAL: bl_parallel default=False (orthogonal zu parallel_mode).
    Opt-in via worktree-spezifische _session_params_{worktree_id}.md.
    """
    try:
        params_path, _mode = resolve_session_params(worktree_id)
        if params_path.exists():
            content = params_path.read_text(encoding="utf-8")
            # Suche nach bl_parallel=true in beiden unterstuetzten Formaten:
            # Format 1: **bl_parallel:** true
            # Format 2: bl_parallel: true
            bl_parallel_pattern = re.compile(
                r"bl_parallel\s*[:\*]+\s*true",
                re.IGNORECASE | re.MULTILINE,
            )
            if bl_parallel_pattern.search(content):
                return True
    except Exception:
        pass
    # Fallback: Framework-Default False (BL-436 D1 DoD-Kern: deployable=False)
    return False


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cmd_resolve(args: argparse.Namespace) -> int:
    """CLI: resolve [worktree_id] — zeigt den aktiven Params-Pfad."""
    worktree_id = getattr(args, "worktree_id", None)
    params_path, mode = resolve_session_params(worktree_id)
    print(f"path={params_path}")
    print(f"mode={mode}")
    print(f"exists={params_path.exists()}")
    return 0


def _cmd_namespace(args: argparse.Namespace) -> int:
    """CLI: namespace — zeigt den aktuellen Worktree-Namespace."""
    ns = get_worktree_namespace()
    worktree_count = _count_active_worktrees()
    print(f"namespace={ns if ns is not None else '(none — single-worktree-mode)'}")
    print(f"active_worktrees={worktree_count}")
    return 0


def _cmd_conflict_check(args: argparse.Namespace) -> int:
    """CLI: conflict-check — prueft auf Param-Konflikte zwischen Worktrees."""
    conflicts = check_conflicts()
    if not conflicts:
        print("OK: Keine Konflikte gefunden.")
        return 0

    print(f"CONFLICTS: {len(conflicts)} Konflikt(e) gefunden:")
    for c in conflicts:
        if c["type"] == "param_divergence":
            values_str = ", ".join(f"{v}→{ns}" for v, ns in c["values"].items())
            print(f"  - [{c['key']}] Divergenz: {values_str}")
    return 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Worktree-Aware Session-Parameter-Resolution (BL-172)"
    )
    subparsers = parser.add_subparsers(dest="command")

    resolve_p = subparsers.add_parser("resolve", help="Zeigt aktiven Params-Pfad")
    resolve_p.add_argument("worktree_id", nargs="?", default=None, help="Optionale Worktree-ID")

    subparsers.add_parser("namespace", help="Zeigt aktuellen Worktree-Namespace")
    subparsers.add_parser("conflict-check", help="Prueft auf Param-Konflikte")

    args = parser.parse_args(argv[1:])

    if args.command == "resolve":
        return _cmd_resolve(args)
    elif args.command == "namespace":
        return _cmd_namespace(args)
    elif args.command == "conflict-check":
        return _cmd_conflict_check(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
