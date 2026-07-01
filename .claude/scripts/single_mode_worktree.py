#!/usr/bin/env python3
"""
single_mode_worktree.py — Werkzeug-Buendel fuer den Single-Mode-Worktree-Betriebspfad
(BL-328, N=1, altmodisch — KEIN Motor).

Das deterministische Werkzeug-Buendel (M3-TDD-faehig) hinter dem altmodischen
Lead+Team-Orchestrator `_single_mode_worktree.md`. Pro Welle faehrt der Skill 9
Schritte; die Git-Lifecycle-Schritte sind reine, getestete INLINE-Ops in DIESEM
Modul.

SB1 deckt die Pre-Welle-Gate-Funktionen ab (GAP-1 + GAP-6):

  - clean_tree_gate(target_tree)              — Schritt 1: Clean-Tree-Gate auf
    dem Fan-Out-ZIEL-Tree (OQ-D, INV-SM-1). Prueft AUSSCHLIESSLICH den
    uebergebenen Ziel-Tree, NIE das (dauerhaft dirtige) Engine-Repo / cwd.
  - pin_base_sha(target_tree, manifest_sha)   — Schritt 2: Base-Ref-Pin (OQ-C,
    INV-SM-7). Manifest-SHA gewinnt, sonst reproduzierbarer HEAD-Pin.
  - generate_worktree_branch_name(...)        — Schritt 2: kollisionsfreier
    Worktree-Branch-Name nach dem _B-N-Schema (reuse current_context.py
    `_MOTOR_SUFFIX_PATTERN` + Sanitizer-Idee aus worktree_aware_params.py).
  - repo_present(path)                         — T9-Guard: ist `path` ein git-Repo?

SB2 (dieser Stand) deckt die Wave-Body-Funktionen ab (GAP-2 + GAP-3 + GAP-7):

  - bootstrap_worktree(target_tree, ...)       — Schritt 3: `git worktree add` am
    gepinnten base_sha; optionaler Build-Cmd IM Worktree; misst
    `bootstrap_seconds` + `disk_bytes` (GAP-2, Telemetrie-Quelle).
  - commit_in_worktree(worktree_path, message)— Schritt 5: Commit IM Worktree-cwd
    (`git -C <worktree>`), NICHT Mothership-cwd. Repo-Guard zuerst (T9, GAP-7).
  - fan_in_merge(target_tree, worktree_branch) — Schritt 6: `git merge --no-ff`
    in den Mothership, geklammert in eine `vault_lock zweck=wave_fanin`-Sequenz
    (Lock-CODE-Pfad existiert auch bei N=1, trivial-konfliktfrei) (GAP-3).

SB3 (dieser Stand) deckt das Post-Merge-Green-Gate ab (GAP-4, Schritt 7, AK-3):

  - run_post_merge_check(target_tree, build_cmd, test_cmd) — fuehrt Build- + Test-Cmd
    IM Mothership-cwd NACH dem Fan-In-Merge aus (subprocess, cwd=target_tree) und
    erfasst die Exit-Codes. None-Cmd = uebersprungen (ok=True). Repo-Guard zuerst (T9).
  - post_merge_gate(build_ok, test_ok) — reiner done/hold-Wrapper (INV-SM-4): nur
    beide-gruen -> done; jeder nicht-vollstaendig-gruene Input -> hold + Recovery
    (Revert/Re-Batch). KEIN stilles `done` bei rot.

SB4 (dieser Stand) deckt Cleanup + 0-Orphan + Telemetrie ab (Schritt 8+9, AK-4,
INV-SM-5, INV-SM-8, OQ-E):

  - cleanup_worktree(target_tree, worktree_path, retries=2) — Schritt 8: WINDOWS-
    robuster `git worktree remove --force` + `prune`. Bei gehaltenem File-Handle /
    gecrashtem Build (B-3-Leichen-Klasse) Retry mit kurzem Backoff bis `retries`;
    als letzte Stufe best-effort Verzeichnis-Entfernung + prune. Repo-Guard (T9).
  - assert_zero_orphans(target_tree, baseline) — INV-SM-5: aktuelle Worktree-Pfade
    MINUS `baseline` (reine Set-Subtraktion) == leer? Erkennt einen liegen-
    gelassenen Worktree als echten Orphan (Negativ-Fall).
  - emit_telemetry(audit_path, **fields) — Schritt 9: EINE append-only JSON-Zeile
    (audit.jsonl-Stil; reuse `_emit_audit`-Idee aus factory_lock.py:372-387) mit den
    5 Gate-B-Feldern + event + ts. KOMMUTATIV/append-only (INV-SM-8, audit_fanin-
    kompatibel). `audit_path` ist injizierbar (Tests nutzen IMMER ein tmp-audit).

SB5 (dieser Stand) deckt die G3-Kopplung + Gate-B-Messlatte ab (Schritt 9 /
Forward-Verify, AK-5 + AK-6, GAP-5):

  - hook_green_rate(hook_results) -> float — AK-5: gruene Hook-Verdikte / gesamte
    aus einer Liste von bool ODER {"green": bool}-Dicts. Speist das Telemetrie-Feld
    `hook_green_rate` pro Batch. Leere Liste -> 1.0 (vacuously green, dokumentiert).
  - gate_b_status(telemetry_events, min_batches=10) -> dict — AK-6 Forward-Verify:
    aggregiert die `single_mode_batch_telemetry`-Events; PASS gdw >=min_batches
    Batches UND ueber ALLE gruen (hook_green_rate==1.0 ∧ orphan_count==0 ∧
    merge_result gruen), sonst PENDING(X/min). fail-safe: nie faelschlich PASS.

INV-SM-5: Nach jedem Batch MUSS `git worktree list` == Baseline sein (Set-
  Subtraktion post\baseline = leer). Cleanup laeuft IMMER (Caller: finally);
  File-Lock-Reste werden per Force/Retry behandelt (B-3-Leichen-Klasse).
INV-SM-8: Telemetrie wird als append-only audit.jsonl-Event emittiert (OQ-E),
  NIE als quiescenz-pflichtiges Manifest-Feld; Fan-In via audit_fanin (kommutativ).

INV-SM-1: Clean-Tree-Gate prueft NUR den ZIEL-Tree, nicht das Engine-Repo (OQ-D).
INV-SM-4: Ein Batch zaehlt erst als `done`, NACHDEM das Post-Merge-Green-Gate gruen
  ist (Build+Unit auf dem Mothership NACH dem Fan-In). Rot -> Batch bleibt offen +
  Recovery, kein stilles Weiterlaufen (faengt semantische Konflikte / U1 / FK-11).
INV-SM-7: Base-SHA reproduzierbar gepinnt; Worktree-Branch-Name kollisionsfrei (_B-N).

Zonen-Grenze (BL-330): das GATING ist deterministisch (Exit-Code -> done/hold) =
M3-Code hier. Das GREEN-KLARHEITS-URTEIL ("ist dieser gruene Build WIRKLICH
korrekt?") ist KOGNITIV (M2) und gehoert in den Orchestrator-Skill / den Lead,
NICHT in diese Wrapper.

Alle git-Aufrufe laufen mit `git -C <target_tree>` bzw. `git -C <worktree_path>` —
nie implizit gegen cwd.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

# Worktree-Branch-Suffix-Schema (reuse current_context.py:48 `_MOTOR_SUFFIX_PATTERN`):
# ein Branch traegt den Worktree-Index als Suffix "_B-<N>".
_B_N_SUFFIX = "_B-{n}"
# SHA-Form: 7..40 hex (kurze + volle Commit-SHA).
_SHA_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
# Datei-/Pfad-problematische Zeichen (Sanitizer-Idee aus worktree_aware_params.py:79).
_PROBLEMATIC = re.compile(r'[\\<>:"|?*]')


def _git(args: list[str], target_tree: str, timeout: int = 10) -> subprocess.CompletedProcess:
    """git -C <target_tree> <args> — nie implizit gegen cwd."""
    return subprocess.run(
        ["git", "-C", target_tree, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def repo_present(path: str) -> bool:
    """T9-Guard: ist `path` Teil eines git-Repos?

    True nur, wenn der Pfad existiert UND `git -C <path> rev-parse --git-dir`
    erfolgreich ist (deckt auch Worktrees/Subdirs ab, wo `.git` eine Datei statt
    Verzeichnis ist). Basis fuer den T9-N/A-Pfad: ein git-loser Vault soll NICHT
    crashen, sondern einen sauberen N/A-Pfad nehmen.
    """
    p = Path(path)
    if not p.exists():
        return False
    try:
        out = _git(["rev-parse", "--git-dir"], path, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return out.returncode == 0


# BL-317/INV-SM-1: bekannte VOLATILE Runtime-Log-Churn (gitignore-intent, BL-317). Diese Dateien
# churnen bei JEDEM Hook-/Audit-Write -> ein engine-self-Ziel-Tree waere sonst Dauer-dirty (Findings
# #D U4). clean_tree_gate ignoriert sie; JEDE andere Aenderung bleibt 'echt dirty' (abort).
_VOLATILE_CHURN_MARKERS = (
    ".claude/audit/audit.jsonl",
    ".claude/audit/disciplinary_report.jsonl",
    ".claude/analysis/_guard_log",
    ".claude/analysis/_berater_outputs",
    ".claude/analysis/_session_params_",
    ".claude/analysis/_manifest_",
    ".claude/scheduled_tasks.lock",
    ".hook_debug.log",
)


def _is_volatile_churn(porcelain_line: str) -> bool:
    """True wenn die git-status-porcelain-Zeile eine bekannte volatile Runtime-Log-Datei betrifft.

    Porcelain: 'XY <path>' (2 Status-Zeichen + Space + Pfad). Rename 'old -> new' -> Ziel zaehlt.
    Match ueber _VOLATILE_CHURN_MARKERS (BL-317-gitignore-Klasse). NUR diese Klasse wird toleriert.
    """
    if not porcelain_line or len(porcelain_line) < 4:
        return False
    path = porcelain_line[3:].strip().strip('"').replace("\\", "/")
    if " -> " in path:
        path = path.split(" -> ")[-1].strip().strip('"')
    return any(marker in path for marker in _VOLATILE_CHURN_MARKERS)


def clean_tree_gate(target_tree: str) -> dict:
    """Schritt 1 — Clean-Tree-Gate auf dem Fan-Out-ZIEL-Tree (OQ-D, INV-SM-1).

    Liest `git -C <target_tree> status --porcelain`:
      - git-loser Pfad (T9)  -> {"decision": "na",      "hint": <N/A-Hinweis>}
      - leerer Output        -> {"decision": "proceed", "hint": <ok-Hinweis>}
      - nicht-leerer Output  -> {"decision": "abort",   "hint": <korrektiv, mit Anzahl>}

    Prueft AUSSCHLIESSLICH den uebergebenen Ziel-Tree (via `git -C`), nie das
    cwd/Engine-Repo — ein Engine-weiter Clean-Check waere ein Dauer-Abort
    (Findings #D U4, INV-SM-1).
    """
    if not repo_present(target_tree):
        return {
            "decision": "na",
            "hint": (
                f"Ziel-Tree '{target_tree}' ist kein git-Repo (T9). "
                "Clean-Tree-Gate uebersprungen (N/A-Pfad statt Crash)."
            ),
        }

    out = _git(["status", "--porcelain"], target_tree)
    if out.returncode != 0:
        # Repo da, aber git-Aufruf scheitert (z.B. korrupter Index): korrektiv aborten.
        return {
            "decision": "abort",
            "hint": (
                f"git status auf Ziel-Tree '{target_tree}' fehlgeschlagen "
                f"(rc={out.returncode}). Recovery: Ziel-Tree pruefen/reparieren, "
                "dann Welle erneut starten."
            ),
        }

    dirty_lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
    # INV-SM-1/BL-317: bekannte volatile Runtime-Log-Churn ignorieren (sonst Dauer-Abort auf
    # engine-self-Ziel-Trees, Findings #D U4). NUR echte Aenderungen aborten.
    real_dirty = [ln for ln in dirty_lines if not _is_volatile_churn(ln)]
    if not real_dirty:
        ignored = len(dirty_lines)
        note = f" ({ignored} volatile Runtime-Log-Aenderung(en) ignoriert, INV-SM-1/BL-317)" if ignored else ""
        return {
            "decision": "proceed",
            "hint": f"Ziel-Tree '{target_tree}' sauber — Welle darf starten.{note}",
        }

    return {
        "decision": "abort",
        "hint": (
            f"Ziel-Tree '{target_tree}' ist dirty ({len(real_dirty)} echte Aenderung(en); "
            f"{len(dirty_lines) - len(real_dirty)} volatile ignoriert). "
            "Recovery: committe oder stashe die ECHTEN Aenderungen im ZIEL-Tree, dann Welle "
            "erneut starten (Clean-Tree-Gate prueft nur den Ziel-Tree, nicht das Engine-Repo; "
            "bekannte Runtime-Log-Churn wird per INV-SM-1/BL-317 toleriert)."
        ),
    }


def pin_base_sha(target_tree: str, manifest_sha: Optional[str]) -> str:
    """Schritt 2 — Base-Ref-Pin (OQ-C, INV-SM-7).

    Eine gueltige `manifest_sha` (im Repo aufloesbarer Commit) gewinnt — das ist
    der dokumentierte, reproduzierbare Base-Anker aus dem Manifest. Sonst wird
    `git -C <target_tree> rev-parse HEAD` gepinnt (reproduzierbarer impliziter
    Anker). Eine syntaktisch/inhaltlich ungueltige manifest_sha wird ignoriert,
    NICHT durchgereicht (kein kaputter Worktree-Base).
    """
    if manifest_sha and _SHA_PATTERN.match(manifest_sha.strip().lower()):
        candidate = manifest_sha.strip()
        # Im Ziel-Tree als echter Commit aufloesbar? -> bevorzugen.
        resolved = _git(["rev-parse", "--verify", f"{candidate}^{{commit}}"], target_tree)
        if resolved.returncode == 0:
            return resolved.stdout.strip()

    head = _git(["rev-parse", "HEAD"], target_tree)
    return head.stdout.strip()


def generate_worktree_branch_name(
    base_branch: str,
    n: int,
    existing: Optional[set] = None,
) -> str:
    """Schritt 2 — kollisionsfreier Worktree-Branch-Name nach dem _B-N-Schema (GAP-6).

    Haengt den Worktree-Index als Suffix `_B-<n>` an den Sanitizer-bereinigten
    Basis-Branch (reuse current_context.py `_MOTOR_SUFFIX_PATTERN`-Schema). Bei
    Kollision in `existing` wird der Suffix-Index hochgezaehlt, bis ein freier
    Name gefunden ist — so erzeugen zwei Wellen (oder zwei Aufrufe gegen ein
    akkumulierendes `existing`) garantiert verschiedene, kollisionsfreie Namen.
    """
    existing = existing or set()
    base = _sanitize_branch(base_branch)
    idx = n
    while True:
        candidate = base + _B_N_SUFFIX.format(n=idx)
        if candidate not in existing:
            return candidate
        idx += 1


def _sanitize_branch(raw: str) -> str:
    """Entfernt Datei-/Pfad-problematische Zeichen aus einem Branch-Namen.

    Behaelt "/" (in git-Branch-Namen valide, z.B. feature/...), ersetzt aber
    Backslash und die in Datei-/Worktree-Pfaden problematischen Zeichen
    (Sanitizer-Idee aus worktree_aware_params.py:71-80).
    """
    sanitized = _PROBLEMATIC.sub("_", raw).strip()
    return sanitized or "worktree"


def _dir_size_bytes(path: Path) -> int:
    """Summe der Datei-Groessen unter `path` (rekursiv) — Worktree-Disk-Footprint.

    Symlinks/unzugaengliche Eintraege werden uebersprungen (kein Crash auf einem
    halb-gecheckten Worktree). Misst die Bootstrap-Oekonomie (GAP-2/U5).
    """
    total = 0
    for f in path.rglob("*"):
        try:
            if f.is_file() and not f.is_symlink():
                total += f.stat().st_size
        except OSError:
            continue
    return total


def bootstrap_worktree(
    target_tree: str,
    worktree_path: str,
    branch: str,
    base_sha: str,
    build_cmd: Optional[list[str]] = None,
) -> dict:
    """Schritt 3 — `git worktree add` am gepinnten base_sha + Messung (GAP-2).

    Legt im `target_tree` (Mothership) einen Worktree unter `worktree_path` an,
    der einen neuen `branch` am `base_sha` aufspannt
    (`git -C <target_tree> worktree add <worktree_path> -b <branch> <base_sha>`).
    Wenn `build_cmd` gesetzt ist, wird es IM Worktree-cwd ausgefuehrt (das
    projekt-spezifische Bootstrap-Verfahren, z.B. dotnet restore / npm ci).

    Misst `bootstrap_seconds` (Wand-Zeit ueber add + optionalen Build) und
    `disk_bytes` (Worktree-Footprint) — die Telemetrie-Quelle fuer AK-4/Gate-B.

    Repo-Anwesenheits-Guard zuerst (T9): ein git-loses Ziel ergibt `ok=False` +
    N/A-Hinweis statt Crash. Roundtrip-Aufraeumung (remove --force + prune) macht
    der Caller in `finally` (Schritt 8 / INV-SM-5) — diese Funktion legt nur an.
    """
    if not repo_present(target_tree):
        return {
            "ok": False,
            "worktree_path": worktree_path,
            "branch": branch,
            "bootstrap_seconds": 0.0,
            "disk_bytes": 0,
            "hint": (
                f"Ziel-Tree '{target_tree}' ist kein git-Repo (T9). "
                "Bootstrap uebersprungen (N/A-Pfad statt Crash)."
            ),
        }

    start = time.monotonic()
    add = _git(["worktree", "add", worktree_path, "-b", branch, base_sha], target_tree, timeout=120)
    if add.returncode != 0:
        return {
            "ok": False,
            "worktree_path": worktree_path,
            "branch": branch,
            "bootstrap_seconds": round(time.monotonic() - start, 4),
            "disk_bytes": 0,
            "hint": (
                f"`git worktree add` fehlgeschlagen (rc={add.returncode}): "
                f"{add.stderr.strip()}. Recovery: Worktree-Pfad/Branch-Kollision "
                "pruefen, dann Welle erneut starten."
            ),
        }

    if build_cmd:
        # Build-Cmd IM Worktree-cwd (nicht Mothership) — projekt-spezifisches Bootstrap.
        build = subprocess.run(
            build_cmd,
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if build.returncode != 0:
            return {
                "ok": False,
                "worktree_path": worktree_path,
                "branch": branch,
                "bootstrap_seconds": round(time.monotonic() - start, 4),
                "disk_bytes": _dir_size_bytes(Path(worktree_path)),
                "hint": (
                    f"Bootstrap-Build im Worktree fehlgeschlagen (rc={build.returncode}): "
                    f"{build.stderr.strip()[:200]}. Recovery: Build-Cmd/Abhaengigkeiten "
                    "pruefen; Worktree wird vom Caller in finally aufgeraeumt."
                ),
            }

    return {
        "ok": True,
        "worktree_path": worktree_path,
        "branch": branch,
        "bootstrap_seconds": round(time.monotonic() - start, 4),
        "disk_bytes": _dir_size_bytes(Path(worktree_path)),
        "hint": f"Worktree '{worktree_path}' am base_sha {base_sha[:7]} (branch {branch}) angelegt.",
    }


def commit_in_worktree(worktree_path: str, message: str) -> dict:
    """Schritt 5 — Commit IM Worktree-cwd (GAP-7), NICHT Mothership-cwd.

    `git -C <worktree_path> add -A` + `commit -m <message>`. Die `-C`-Form ist der
    Kern von GAP-7: der Commit-Seam committet im Worktree, sodass der
    Mothership-HEAD erst beim Fan-In (Schritt 6) vorrueckt.

    Repo-Anwesenheits-Guard zuerst (T9): ein git-loser Pfad ergibt
    `committed=False` + N/A-Hinweis statt Crash.
    """
    if not repo_present(worktree_path):
        return {
            "committed": False,
            "sha": None,
            "hint": (
                f"Pfad '{worktree_path}' ist kein git-Repo (T9). "
                "Commit-Seam uebersprungen (N/A-Pfad statt Crash)."
            ),
        }

    _git(["add", "-A"], worktree_path)
    commit = _git(["commit", "-m", message], worktree_path, timeout=30)
    if commit.returncode != 0:
        return {
            "committed": False,
            "sha": None,
            "hint": (
                f"`git commit` im Worktree fehlgeschlagen (rc={commit.returncode}): "
                f"{(commit.stdout + commit.stderr).strip()[:200]} "
                "(z.B. nichts zu committen). Recovery: Stage-Output pruefen."
            ),
        }

    sha = _git(["rev-parse", "HEAD"], worktree_path).stdout.strip()
    return {
        "committed": True,
        "sha": sha,
        "hint": f"Commit {sha[:7]} im Worktree '{worktree_path}' (cwd=Worktree, nicht Mothership).",
    }


def fan_in_merge(target_tree: str, worktree_branch: str, lock_dir: Optional[str] = None) -> dict:
    """Schritt 6 — Fan-In-Merge des Worktree-Branch in den Mothership (GAP-3).

    `git -C <target_tree> merge --no-ff <worktree_branch>` bringt die
    Worktree-Branch-Commits in den Mothership. Der Merge ist in eine
    `vault_lock zweck="wave_fanin"`-Sequenz geklammert (acquire vor Merge,
    release im `finally`) — der Fan-In-Barrier-Lock-CODE-Pfad existiert damit
    auch bei N=1 (trivial-konfliktfrei), bereit fuer N>=2 (BL-230 Phase C-E).

    Der Lock ist injizierbar: `lock_dir` wird als `vault_root` an `vault_lock`
    durchgereicht (Unit-Test zeigt auf ein tmp-Verzeichnis statt den globalen
    Produktions-Vault). Schlaegt das Lock-Acquire fehl (kein Vault / Timeout),
    degradiert der Pfad sauber zu einem ungelockten Merge bei N=1 (kein Hard-Fail
    auf einem fehlenden globalen vault_root) — der Lock-CODE bleibt durchlaufen.

    Repo-Anwesenheits-Guard zuerst (T9): git-loses Ziel -> `merged=False` + N/A.
    """
    if not repo_present(target_tree):
        return {
            "merged": False,
            "conflict": False,
            "hint": (
                f"Ziel-Tree '{target_tree}' ist kein git-Repo (T9). "
                "Fan-In-Merge uebersprungen (N/A-Pfad statt Crash)."
            ),
        }

    import vault_lock

    worker_id = f"wave-fanin-{int(time.time() * 1000)}"
    vault_root = Path(lock_dir) if lock_dir else None
    lock_held = False
    try:
        try:
            lock_held = vault_lock.acquire(
                zweck="wave_fanin",
                worker_id=worker_id,
                timeout=10,
                vault_root=vault_root,
            )
        except Exception:
            # Lock-Backend nicht verfuegbar (kein vault_root o.ae.) -> bei N=1 ungelockt
            # weiterfahren; der Lock-CODE-Pfad ist durchlaufen, der Barrier wird bei
            # N>=2 (BL-230) scharf. Kein Hard-Fail auf fehlendem globalem vault_root.
            lock_held = False

        merge = _git(["merge", "--no-ff", worktree_branch, "-m",
                      f"BL-328 fan-in: merge {worktree_branch}"], target_tree, timeout=60)
        if merge.returncode != 0:
            conflict = "conflict" in (merge.stdout + merge.stderr).lower()
            if conflict:
                # Halb-fertigen Merge zuruecksetzen, damit der Mothership sauber bleibt.
                _git(["merge", "--abort"], target_tree)
            return {
                "merged": False,
                "conflict": conflict,
                "hint": (
                    f"Fan-In-Merge von '{worktree_branch}' fehlgeschlagen "
                    f"(rc={merge.returncode}, conflict={conflict}): "
                    f"{(merge.stdout + merge.stderr).strip()[:200]}. "
                    "Recovery: bei Konflikt Revert/Re-Batch (INV-SM-4)."
                ),
            }

        return {
            "merged": True,
            "conflict": False,
            "hint": f"Fan-In-Merge von '{worktree_branch}' in den Mothership erfolgreich (--no-ff).",
        }
    finally:
        if lock_held:
            try:
                vault_lock.release(worker_id=worker_id, vault_root=vault_root)
            except Exception:
                pass


def run_post_merge_check(
    target_tree: str,
    build_cmd: Optional[list[str]] = None,
    test_cmd: Optional[list[str]] = None,
) -> dict:
    """Schritt 7 — Build + Unit auf dem MOTHERSHIP NACH dem Fan-In-Merge (GAP-4, AK-3).

    Fuehrt `build_cmd` und `test_cmd` IM Mothership-cwd (`cwd=target_tree`, der
    bereits gemergte Tree) aus und erfasst die Exit-Codes deterministisch. Ein
    None-Cmd ist uebersprungen (ok=True, rc=None) — z.B. wenn ein Projekt keinen
    separaten Build-Schritt hat. Genau das deterministische Exit-Code-Gate; das
    GREEN-KLARHEITS-URTEIL bleibt KOGNITIV (Skill/Lead, BL-330-Zonen-Grenze).

    Repo-Anwesenheits-Guard zuerst (T9): ein git-loser Pfad ergibt `decision="na"`
    + build_ok/test_ok=False (fail-safe: kein gruenes Urteil ohne echten Tree).

    Return: `{"build_ok": bool, "test_ok": bool, "build_rc": int|None,
              "test_rc": int|None, "hint": str}` (bei T9 zusaetzlich "decision":"na").
    """
    if not repo_present(target_tree):
        return {
            "decision": "na",
            "build_ok": False,
            "test_ok": False,
            "build_rc": None,
            "test_rc": None,
            "hint": (
                f"Ziel-Tree '{target_tree}' ist kein git-Repo (T9). "
                "Post-Merge-Check uebersprungen (N/A-Pfad statt Crash); "
                "kein gruenes Urteil ohne echten Mothership-Tree (fail-safe)."
            ),
        }

    def _run(cmd: Optional[list[str]]) -> tuple[bool, Optional[int]]:
        if cmd is None:
            return True, None  # uebersprungen — kein konfiguriertes Verfahren.
        proc = subprocess.run(
            cmd,
            cwd=target_tree,  # Mothership-cwd (nach Merge), NICHT cwd des Aufrufers.
            capture_output=True,
            text=True,
            timeout=600,
        )
        return proc.returncode == 0, proc.returncode

    build_ok, build_rc = _run(build_cmd)
    test_ok, test_rc = _run(test_cmd)

    return {
        "build_ok": build_ok,
        "test_ok": test_ok,
        "build_rc": build_rc,
        "test_rc": test_rc,
        "hint": (
            f"Post-Merge-Check auf Mothership '{target_tree}': "
            f"build_ok={build_ok} (rc={build_rc}), test_ok={test_ok} (rc={test_rc}). "
            "Green-Urteil (ist gruen WIRKLICH korrekt?) faellt der Lead/Skill (M2)."
        ),
    }


def post_merge_gate(build_ok: bool, test_ok: bool) -> dict:
    """Schritt 7 — reiner done/hold-Wrapper ueber dem Post-Merge-Check (INV-SM-4).

    Deterministisches Exit-Code-Gate (M3): NUR wenn Build UND Unit gruen sind, gilt
    der Batch als `done`. JEDER nicht-vollstaendig-gruene Input -> `hold`
    (fail-safe-Default) + korrektiver Recovery-Hint (Revert/Re-Batch). Es gibt
    KEIN stilles `done` bei rot — das ist der billige Regressions-Anker gegen
    semantische Merge-Konflikte (U1/FK-11) bei N=1.

    Faellt KEIN GREEN-Urteil selbst (BL-330-Zonen-Grenze): die Frage, ob ein
    gruener Build WIRKLICH korrekt ist, ist kognitiv (Skill/Lead, M2). Dieser
    Wrapper schaltet nur deterministisch done<->hold auf den uebergebenen booleans.
    """
    if build_ok and test_ok:
        return {
            "decision": "done",
            "hint": (
                "Post-Merge-Green-Gate gruen (Build+Unit) — Batch darf als done "
                "markiert werden (INV-SM-4)."
            ),
        }

    failed = []
    if not build_ok:
        failed.append("Build")
    if not test_ok:
        failed.append("Unit")
    return {
        "decision": "hold",
        "hint": (
            f"Post-Merge-Green-Gate ROT ({' + '.join(failed)} fehlgeschlagen) — "
            "Batch bleibt OFFEN, NICHT done (INV-SM-4). Recovery: Revert des "
            "Fan-In-Merge oder Re-Batch des Sub-Batch; kein stilles done bei rot."
        ),
    }


def _worktree_paths(target_tree: str) -> set:
    """Normierter Set der Worktree-Pfade von `target_tree` (Backslash->Slash, lowercase).

    Spiegelt die Normierung der Test-Fixture (`_worktree_list`) — so ist die
    Set-Subtraktion gegen eine Test-Baseline kompatibel. Leer/fehlerhaft -> set().
    """
    out = _git(["worktree", "list", "--porcelain"], target_tree)
    if out.returncode != 0:
        return set()
    paths = set()
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            raw = line[len("worktree "):]
            paths.add(raw.replace("\\", "/").rstrip("/").lower())
    return paths


def _now_iso() -> str:
    """ISO-8601-UTC-Zeitstempel (reuse-Form aus factory_lock._now_iso)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cleanup_worktree(target_tree: str, worktree_path: str, retries: int = 2) -> dict:
    """Schritt 8 — Windows-robuster Worktree-Cleanup (GAP-7, INV-SM-5).

    `git -C <target_tree> worktree remove --force <worktree_path>` + `worktree prune`.
    WINDOWS-ROBUST gegen die B-3-Leichen-Klasse (gehaltenes File-Handle, gecrashter
    Build haelt einen Handle): schlaegt `remove` fehl, wird mit kurzem Backoff bis
    `retries` erneut versucht; als LETZTE Stufe wird das Worktree-Verzeichnis
    best-effort direkt entfernt (`shutil.rmtree`). `git worktree prune` laeuft IMMER
    am Ende — auch wenn `remove` nie sauber durchlief — damit die git-Worktree-Liste
    den verschwundenen Eintrag verliert (0-Orphan, INV-SM-5).

    Repo-Anwesenheits-Guard zuerst (T9): git-loses Ziel -> removed=False + N/A-Hinweis
    statt Crash.

    Return: `{"removed": bool, "pruned": bool, "attempts": int, "hint": str}`.
      - removed: hat `git worktree remove` (irgendein Versuch) rc==0 geliefert?
      - pruned:  ist der Worktree-Pfad am Ende NICHT mehr in `git worktree list`?
                 (das ist die eigentliche 0-Orphan-Wahrheit — auch via best-effort
                  rmtree + prune erreichbar.)
      - attempts: Anzahl der `remove`-Versuche (>=1).
    """
    if not repo_present(target_tree):
        return {
            "removed": False,
            "pruned": False,
            "attempts": 0,
            "hint": (
                f"Ziel-Tree '{target_tree}' ist kein git-Repo (T9). "
                "Cleanup uebersprungen (N/A-Pfad statt Crash)."
            ),
        }

    norm_wt = str(worktree_path).replace("\\", "/").rstrip("/").lower()
    removed = False
    attempts = 0
    last_err = ""
    # max(1, retries+1) Versuche: mindestens 1, sonst retries Zusatz-Anlaeufe.
    total_tries = max(1, retries + 1)
    for i in range(total_tries):
        attempts += 1
        out = _git(["worktree", "remove", "--force", str(worktree_path)], target_tree, timeout=30)
        if out.returncode == 0:
            removed = True
            break
        last_err = (out.stdout + out.stderr).strip()[:200]
        if i < total_tries - 1:
            # Kurzer Backoff: gibt einem gerade-noch-gehaltenen Handle Zeit (B-3).
            time.sleep(0.2 * (i + 1))

    # Letzte Stufe (B-3): wenn `remove` nie sauber durchlief, das Verzeichnis
    # best-effort selbst entfernen, dann prune die git-Metadaten weg.
    if not removed:
        wt = Path(worktree_path)
        if wt.exists():
            shutil.rmtree(wt, ignore_errors=True)

    # prune laeuft IMMER — auch nach erfolgreichem remove harmlos (idempotent).
    prune = _git(["worktree", "prune"], target_tree, timeout=30)

    # 0-Orphan-Wahrheit: ist der Pfad am Ende WIRKLICH aus der Liste verschwunden?
    gone = norm_wt not in _worktree_paths(target_tree)

    if removed:
        hint = (
            f"Worktree '{worktree_path}' entfernt (remove rc=0 nach {attempts} Versuch(en), "
            f"prune rc={prune.returncode})."
        )
    elif gone:
        hint = (
            f"Worktree '{worktree_path}' via best-effort rmtree + prune entfernt "
            f"(remove scheiterte {attempts}x, letzter Fehler: {last_err or 'n/a'}). "
            "0-Orphan trotzdem erreicht (B-3-Leichen-Klasse behandelt)."
        )
    else:
        hint = (
            f"Worktree '{worktree_path}' konnte NICHT entfernt werden "
            f"({attempts} Versuch(e), letzter Fehler: {last_err or 'n/a'}). "
            "Recovery: Datei-Handle pruefen (gecrashter Build?), dann erneut cleanup."
        )

    return {
        "removed": removed,
        "pruned": gone,
        "attempts": attempts,
        "hint": hint,
    }


def assert_zero_orphans(target_tree: str, baseline) -> dict:
    """INV-SM-5 — 0-Orphan-Assertion via reiner Set-Subtraktion (post \\ baseline).

    Vergleicht die AKTUELLEN `git worktree list`-Pfade mit der bei Welle-Start
    erfassten `baseline` (Set normierter Pfade). Jeder Pfad in (aktuell \\ baseline)
    ist ein Orphan — ein nach dem Batch liegengebliebener Worktree.

    Erkennt den Negativ-Fall (ein absichtlich/versehentlich liegengelassener
    Worktree -> zero_orphans=False + nennt ihn), nicht nur den leeren Happy-Path.

    Return: `{"zero_orphans": bool, "orphans": [..normierte Pfade..], "hint": str}`.
    """
    baseline_set = {
        str(p).replace("\\", "/").rstrip("/").lower() for p in (baseline or set())
    }
    current = _worktree_paths(target_tree)
    orphans = sorted(current - baseline_set)
    if not orphans:
        return {
            "zero_orphans": True,
            "orphans": [],
            "hint": (
                f"0-Orphan bestaetigt (INV-SM-5): `git worktree list` von "
                f"'{target_tree}' == Baseline."
            ),
        }
    return {
        "zero_orphans": False,
        "orphans": orphans,
        "hint": (
            f"ORPHAN(s) erkannt (INV-SM-5 verletzt): {len(orphans)} Worktree(s) ueber "
            f"Baseline hinaus: {orphans}. Recovery: cleanup_worktree(...) auf die "
            "genannten Pfade, dann erneut assert_zero_orphans."
        ),
    }


# Die 5 Gate-B-Telemetrie-Felder (AK-4/AK-6, OQ-E). Reihenfolge = Dokumentations-Reihenfolge.
TELEMETRY_FIELDS = (
    "bootstrap_seconds",
    "disk_bytes",
    "hook_green_rate",
    "orphan_count",
    "merge_result",
)


def emit_telemetry(audit_path: Optional[str], **fields) -> dict:
    """Schritt 9 — EINE append-only Telemetrie-Zeile als audit.jsonl-Event (GAP-5).

    Haengt EIN Event-Dict als JSON-Zeile an `audit_path` (audit.jsonl-Stil; reuse
    der `_emit_audit`-Emit-Idee aus factory_lock.py:372-387). Das Event traegt die
    uebergebenen `fields` (i.d.R. die 5 Gate-B-Felder `bootstrap_seconds`,
    `disk_bytes`, `hook_green_rate`, `orphan_count`, `merge_result`) plus `event`
    und `ts`. Append-only + 1-vollstaendiges-JSON-pro-Zeile => KOMMUTATIV via
    `audit_fanin` (INV-SM-8, OQ-E).

    `audit_path` ist ein PARAMETER (injizierbar) — Tests uebergeben IMMER ein
    tmp-audit; NIEMALS die echte `.claude/audit/audit.jsonl` (Pollution-Schutz,
    analog SB2 lock_dir-Lehre). Ist `audit_path` None, wird NICHT geschrieben
    (uebersprungen, emitted=False) — kein impliziter Schreib-Default in den
    Produktions-Stream.

    Return: `{"emitted": bool, "path": str|None, "hint": str}`.
    """
    if audit_path is None:
        return {
            "emitted": False,
            "path": None,
            "hint": (
                "emit_telemetry uebersprungen: audit_path=None (kein impliziter "
                "Schreib-Default in die Produktions-audit.jsonl; injiziere einen Pfad)."
            ),
        }

    entry = {
        "ts": _now_iso(),
        "event": "single_mode_batch_telemetry",
        "source": "single_mode_worktree",
        **fields,
    }
    try:
        out = Path(audit_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        return {
            "emitted": False,
            "path": str(audit_path),
            "hint": f"Telemetrie-Emit nach '{audit_path}' fehlgeschlagen: {e}.",
        }

    return {
        "emitted": True,
        "path": str(audit_path),
        "hint": (
            f"Telemetrie-Event (1 append-only Zeile) nach '{audit_path}' emittiert "
            f"(Felder: {', '.join(sorted(fields))})."
        ),
    }


# Das Telemetrie-Event-Etikett, auf das gate_b_status filtert (= emit_telemetry-`event`).
_BATCH_TELEMETRY_EVENT = "single_mode_batch_telemetry"
# merge_result-Werte, die als "gruen" (erfolgreich gemergt) gelten.
_GREEN_MERGE_RESULTS = {"merged", "merged --no-ff", "ok", "green"}


def hook_green_rate(hook_results) -> float:
    """G3-Kopplung (AK-5) — Hook-Gruen-Rate = gruene Hook-Verdikte / gesamte.

    `hook_results` ist eine Liste von Hook-Verdikten; jedes Element ist entweder
    ein `bool` (True = gruen) ODER ein `{"green": bool}`-Dict (Hook-Router-Form).
    Liefert den Anteil gruener Verdikte als float in [0.0, 1.0]. Deterministisch,
    rein.

    KONVENTION (bewusst gewaehlt + hier dokumentiert): eine LEERE Liste ergibt
    `1.0` (vacuously green). Begruendung: "es liefen keine Hooks" zaehlt als "kein
    roter Hook" — der neutrale Multiplikator fuer die Gate-B-Aggregation. Ein Batch
    ohne Hook-Lauf soll die Messlatte NICHT faelschlich auf PENDING ziehen. Im
    Single-Worktree-Pfad (N=1, namespace==None) verhaelt sich der Hook-Router
    ohnehin bit-identisch zu heute (`worktree_hook_router.py:88-89` ->
    `relevant=True`), sodass eine leere Liste hier "kein relevanter Hook lief"
    bedeutet, nicht "ein Hook lief und war rot".

    Diese Funktion liefert das Telemetrie-Feld `hook_green_rate` pro Batch
    (gate_b_status erwartet ueber ALLE Batches ==1.0 fuer Gate-B PASS).
    """
    if not hook_results:
        return 1.0

    def _is_green(verdict) -> bool:
        if isinstance(verdict, dict):
            return bool(verdict.get("green", False))
        return bool(verdict)

    green = sum(1 for v in hook_results if _is_green(v))
    return green / len(hook_results)


def _merge_is_green(merge_result) -> bool:
    """Form-tolerante Pruefung, ob `merge_result` einen erfolgreichen Merge meint.

    Akzeptiert sowohl `True` (bool) als auch die String-Etiketten aus
    `_GREEN_MERGE_RESULTS` (z.B. "merged"). Alles andere (False, "hold",
    "conflict", None, fehlend) gilt als NICHT gruen.
    """
    if merge_result is True:
        return True
    if isinstance(merge_result, str):
        return merge_result.strip().lower() in _GREEN_MERGE_RESULTS
    return False


def _batch_is_green(event: dict) -> bool:
    """Ein Batch-Telemetrie-Event ist gruen gdw alle 3 Gate-B-Bedingungen halten.

    hook_green_rate == 1.0 (mit kleiner Float-Toleranz) ∧ orphan_count == 0 ∧
    merge_result gruen. fail-safe: fehlende/uneindeutige Felder -> nicht gruen.
    """
    try:
        hook_ok = float(event.get("hook_green_rate", 0.0)) >= 1.0 - 1e-9
    except (TypeError, ValueError):
        hook_ok = False
    orphan_ok = event.get("orphan_count", None) == 0
    merge_ok = _merge_is_green(event.get("merge_result"))
    return bool(hook_ok and orphan_ok and merge_ok)


def gate_b_status(telemetry_events, min_batches: int = 10) -> dict:
    """Gate-B-Messlatte (AK-6, Forward-Verify) — Aggregation ueber Batch-Telemetrie.

    Liest die `single_mode_batch_telemetry`-Events (die `emit_telemetry`-Zeilen mit
    `hook_green_rate`/`orphan_count`/`merge_result`/... aus dem `audit.jsonl`-Stream)
    und berechnet, ob Gate-B (BL-230 Phase B) erreicht ist. Fremde audit-Events
    (anderes `event`) werden ignoriert — nur echte Single-Mode-Batch-Events zaehlen.

    PASS gdw: es gibt >=`min_batches` Batch-Events UND ueber sie ALLE gilt
    `_batch_is_green` (hook_green_rate==1.0 ∧ orphan_count==0 ∧ merge_result gruen).
    Sonst PENDING mit `progress` (X/`min_batches` gruene Batches).

    FAIL-SAFE (kein falsches PASS): zu wenige Batches, ein einziger nicht-gruener
    Batch oder uneindeutige/fehlende Felder fuehren IMMER zu PENDING — nie zu PASS.
    Das ist ein **Forward-Verify** ([[feedback_forward_verification_pattern]]): die
    Messlatte ist dormant-bauend; der echte >=10-Batch-Nachweis faellt erst bei
    realem Single-Mode-Produktions-Betrieb an.

    Return: `{"status": "PASS"|"PENDING", "green_batches": int,
              "total_batches": int, "progress": str, "hint": str}`.
    """
    batch_events = [
        e
        for e in (telemetry_events or [])
        if isinstance(e, dict) and e.get("event") == _BATCH_TELEMETRY_EVENT
    ]
    total = len(batch_events)
    green = sum(1 for e in batch_events if _batch_is_green(e))

    # PASS nur, wenn ALLE Batch-Events gruen sind UND es genug davon gibt.
    # (green == total verhindert, dass spaetere rote Batches durch fruehe gruene
    #  "ueberstimmt" werden — Gate-B verlangt eine luecklose gruene Serie.)
    passed = total >= min_batches and green == total and green >= min_batches
    progress = f"{green}/{min_batches}"

    if passed:
        return {
            "status": "PASS",
            "green_batches": green,
            "total_batches": total,
            "progress": progress,
            "hint": (
                f"Gate-B PASS: {green} konsekutive Single-Mode-Batches gruen "
                f"(hook_green_rate==1.0, 0 Orphans, Post-Merge gruen) ueber "
                f">={min_batches} Batches (AK-6)."
            ),
        }

    if total > green:
        reason = (
            f"{total - green} von {total} Batch-Event(s) NICHT gruen "
            "(hook<1.0 / Orphan / Merge nicht gruen)"
        )
    elif total < min_batches:
        reason = f"erst {total} Batch-Event(s) (< {min_batches} noetig)"
    else:
        reason = "uneindeutige Telemetrie"
    return {
        "status": "PENDING",
        "green_batches": green,
        "total_batches": total,
        "progress": progress,
        "hint": (
            f"Gate-B PENDING ({progress} gruene Batches): {reason}. "
            "Forward-Verify: die >=10-Batch-Messlatte ist dormant-bauend; der echte "
            "Nachweis faellt bei realem Single-Mode-Betrieb an (fail-safe, nie falsches PASS)."
        ),
    }
