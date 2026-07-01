#!/usr/bin/env python3
"""team_gc.py — Team-Lifecycle Garbage Collection (BL-349).

PROBLEM (Live-Fall 2026-06-14, Gate-A-Setup): Laeufe raeumen ihr benanntes Team nicht
zuverlaessig ab. Stufe-6-TeamDelete wird vor Session-Ende/Abbruch/Resume oft nicht erreicht,
ODER Worker mehrerer Laeufe jointen denselben lingernden Team-Context. Tote Member-Records
(Prozess weg, tmux-Pane weg, Session-Restart) persistieren in config.json und blockieren
TeamDelete ("Cannot cleanup team with N active member(s)") + damit jede neue TeamCreate
("a leader can only manage one team"). Beispiel: idf-bl-333 hatte 112 Zombie-Member.

MECHANIK (empirisch verifiziert 2026-06-14): Das Harness-TeamDelete liest member-Liveness aus
config.json. Strippt man die toten member-Records aus config.json, laeuft TeamDelete danach durch
(es entfernt die Dirs/Worktrees). Dieses Skript loescht KEINE Team-Dirs selbst — das bleibt dem
Harness-TeamDelete vorbehalten (Vermeidung von Harness-State-Inkonsistenz). Es macht NUR den
config.json-member-Strip, sodass das nachfolgende TeamDelete nicht mehr blockiert.

CONCURRENCY-SICHERHEIT (KRITISCH fuer BL-230): Unter Parallelitaet sind MEHRERE Teams/Sessions
gleichzeitig legitim aktiv. Ein breiter "strippe alles was nicht meins ist"-Sweep wuerde
nebenlaeufige Teams zerstoeren. Darum:
  - strip_team_members(team): SICHER — operiert NUR auf EINEM benannten Team, das der Caller
    explizit waehlt (= sein EIGENES Team bei Stufe-6-Teardown). Auto-aufrufbar.
  - gc_orphaned_teams(preserve, apply): Architekten-Werkzeug. Verlangt EXPLIZITE preserve-Menge
    (was NICHT angefasst wird) + ist dry-run per Default (apply=False). NICHT auto-breit-strippen.

Funktionen:
  strip_team_members(team_name, keep_lead=True) -> dict
  read_team_meta(team_name) -> dict
  list_teams() -> list[str]
  find_orphaned_teams(preserve) -> list[dict]            (Report-Kandidaten, kein Schreiben)
  gc_orphaned_teams(preserve, apply=False) -> dict        (dry-run default)

CLI:
  py team_gc.py list
  py team_gc.py meta <team>
  py team_gc.py strip <team> [--all]            (--all = auch team-lead entfernen)
  py team_gc.py gc --preserve a,b [--apply]     (ohne --apply = dry-run Report)

Test-Override: OMNI_TEAMS_DIR (teams-root fuer Tests).

====================================================================================
TEAM-TRANSITION-RECOVERY-PROTOKOLL (BL-349 AK-2, Orchestrator-Lifecycle-Konvention)
====================================================================================
Ein Hook kann das NICHT erzwingen (TeamDelete nimmt KEIN team-Argument -> Ziel = Session-
Lead-Kontext, dem Hook unbekannt). Darum Lead-Konvention an den Stufe-1/Stufe-6-Naehten
JEDES Orchestrators. Beide Recovery-Pfade sind REAKTIV (feuern nur bei echtem Block) und
CONCURRENCY-SAFE (beruehren NUR Teams, die die aktuelle Session BESITZT — nie ein Peer-Team):

  INV-TEAM-GC-1 (eigener Stufe-6-Teardown):
    TeamDelete scheitert mit "Cannot cleanup team with N active member(s)"
    -> die N sind tote Worker DIESER Session (Prozess/Pane weg, nur config-Records)
    -> `py .claude/scripts/team_gc.py strip <eigenes-team>`  (keep_lead, Backup)
    -> TeamDelete erneut (laeuft jetzt durch — Harness liest Liveness aus config.json).

  INV-TEAM-GC-2 (Stufe-1-Transition / TeamCreate-Recovery):
    TeamCreate scheitert mit "Already leading team X"
    -> X gehoert dem AKTUELLEN Lead-Kontext (das Harness sagt es genau so) -> safe.
       (Niemals ein nebenlaeufiges Peer-Team — der Fehler benennt NUR eigenes Eigentum.)
    -> `py .claude/scripts/team_gc.py strip X` -> TeamDelete (X) -> TeamCreate erneut.
    Caveat: gilt im LIFECYCLE-Kontext (Transition nach Phasen-Abschluss). Sind in X noch
    ECHT-lebende Worker, ist der Lead nicht transition-bereit — dann NICHT strippen.

  WICHTIG: team_gc strippt NUR config.json-member-Records (Backup .bak), loescht KEINE
  Dirs/Worktrees — das bleibt dem Harness-TeamDelete (kein State-Drift). Stufe-1-Cleanup
  darf sich NICHT nur auf Manifest.active_team verlassen: der Zombie sitzt oft im SESSION-
  Kontext, NICHT im Manifest (Manifest<->Session-Drift, Live-Beleg idf-bl-333 2026-06-14).
"""

import json
import os
import shutil
import sys
from pathlib import Path

LEAD_NAME = "team-lead"


def _teams_root(teams_root=None) -> Path:
    """Teams-Root: explizit > OMNI_TEAMS_DIR (Test-Override) > ~/.claude/teams.
    __file__-/home-basiert, NICHT cwd-relativ (kein cwd-Artefakt-Risiko)."""
    if teams_root is not None:
        return Path(teams_root)
    env = os.environ.get("OMNI_TEAMS_DIR")
    if env:
        return Path(env)
    return Path.home() / ".claude" / "teams"


def _config_path(team_name, teams_root=None) -> Path:
    return _teams_root(teams_root) / team_name / "config.json"


def _load_config(team_name, teams_root=None):
    p = _config_path(team_name, teams_root)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_teams(teams_root=None) -> list:
    root = _teams_root(teams_root)
    if not root.is_dir():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir() and (d / "config.json").is_file()
    )


def _is_dead(member, backward_compat_default="unknown") -> bool:
    """Gibt True zurueck wenn der Member als tot gilt.
    Fehlendes status-Feld: backward_compat_default entscheidet ("unknown" -> NICHT dead; "dead" -> dead)."""
    status = member.get("status", backward_compat_default)
    return status == "dead"


def read_team_meta(team_name, teams_root=None) -> dict:
    cfg = _load_config(team_name, teams_root)
    if cfg is None:
        return {"team": team_name, "has_config": False, "member_count": 0,
                "lead_session_id": None, "member_names": []}
    members = cfg.get("members", []) or []
    dead_count = sum(1 for m in members if _is_dead(m))
    alive_count = sum(1 for m in members if m.get("status") == "alive")
    unknown_count = sum(1 for m in members if "status" not in m)
    return {
        "team": team_name,
        "has_config": True,
        "member_count": len(members),
        "non_lead_count": sum(1 for m in members if m.get("name") != LEAD_NAME),
        "lead_session_id": cfg.get("leadSessionId"),
        "member_names": [m.get("name") for m in members],
        "dead_count": dead_count,
        "alive_count": alive_count,
        "unknown_count": unknown_count,
    }


def strip_team_members(team_name, keep_lead=True, strip_dead=False,
                       backward_compat_default="unknown", teams_root=None) -> dict:
    """Strippt Member aus config.json eines BENANNTEN Teams (Backup .bak).
    keep_lead=True behaelt nur den team-lead (Standard-Teardown); keep_lead=False leert ganz.
    strip_dead=True (zusaetzlich): entfernt Member mit status='dead' (via _is_dead).
      backward_compat_default: Fallback-Status fuer Member ohne status-Feld ("unknown"=behalten, "dead"=entfernen).
    strip_dead=False (Default): Altverhalten exakt unveraendert (nur lead-Filterung).
    Loescht KEINE Dirs (TeamDelete-Sache). Return: {team, before, after, stripped, backup, changed}.
    """
    p = _config_path(team_name, teams_root)
    if not p.is_file():
        return {"team": team_name, "error": "no_config", "changed": False}
    cfg = _load_config(team_name, teams_root)
    if cfg is None:
        return {"team": team_name, "error": "unparseable_config", "changed": False}
    members = cfg.get("members", []) or []
    before = len(members)
    if strip_dead:
        # strip_dead-Modus: entfernt dead-Member; keep_lead bewahrt zusaetzlich den Lead
        kept = [m for m in members
                if not _is_dead(m, backward_compat_default)
                and (not keep_lead or True)]  # keep_lead-Logik separat
        if keep_lead:
            # Lead immer behalten, auch wenn er als dead markiert waere
            lead_members = [m for m in members if m.get("name") == LEAD_NAME]
            non_lead_kept = [m for m in kept if m.get("name") != LEAD_NAME]
            kept = lead_members + non_lead_kept
    elif keep_lead:
        kept = [m for m in members if m.get("name") == LEAD_NAME]
    else:
        kept = []
    after = len(kept)
    if after == before:
        return {"team": team_name, "before": before, "after": after,
                "stripped": 0, "backup": None, "changed": False}
    backup = str(p) + ".bak"
    shutil.copyfile(p, backup)
    cfg["members"] = kept
    p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return {"team": team_name, "before": before, "after": after,
            "stripped": before - after, "backup": backup, "changed": True}


def get_session_team_context(teams_root=None):
    """Findet das Team dessen leadSessionId mit der aktuellen Session-ID uebereinstimmt.
    Session-Anker: CLAUDE_SESSION_ID Umgebungsvariable.
    Gibt team_name (str) zurueck wenn genau 1 Match, None bei 0 oder >1 Matches (fail-safe).
    Read-only, fail-safe (exceptions -> None).
    """
    try:
        session_id = os.environ.get("CLAUDE_SESSION_ID")
        if not session_id:
            return None
        matches = []
        for team_name in list_teams(teams_root):
            cfg = _load_config(team_name, teams_root)
            if cfg is None:
                continue
            if cfg.get("leadSessionId") == session_id:
                matches.append(team_name)
        if len(matches) == 1:
            return matches[0]
        # 0 matches: nicht gefunden; >1 matches: ambiguous — beide -> None (fail-safe)
        return None
    except Exception:
        return None


def find_orphaned_teams(preserve, teams_root=None) -> list:
    """Report (KEIN Schreiben): Teams NICHT in preserve (Menge) mit >0 Nicht-Lead-Membern.
    preserve = explizite Liste/Menge der zu schuetzenden Team-Namen (z.B. das aktive Team +
    bekannte nebenlaeufige Teams). Sicherheit liegt beim Caller (explizite preserve-Menge)."""
    preserve_set = set(preserve or [])
    out = []
    for t in list_teams(teams_root):
        if t in preserve_set:
            continue
        meta = read_team_meta(t, teams_root)
        if meta.get("non_lead_count", 0) > 0:
            out.append(meta)
    return out


def gc_orphaned_teams(preserve, apply=False, teams_root=None) -> dict:
    """Architekten-GC: strippt (apply=True) bzw. reportet (dry-run, Default) die Member
    aller Teams NICHT in preserve. NIE Dir-Loeschung. preserve MUSS explizit gesetzt sein."""
    candidates = find_orphaned_teams(preserve, teams_root)
    result = {"apply": apply, "preserve": sorted(set(preserve or [])),
              "candidates": [c["team"] for c in candidates], "stripped": []}
    if apply:
        for c in candidates:
            r = strip_team_members(c["team"], keep_lead=True, teams_root=teams_root)
            if r.get("changed"):
                result["stripped"].append({"team": r["team"], "removed": r["stripped"]})
    return result


def _main(argv):
    if not argv:
        print("usage: team_gc.py {list|meta <team>|strip <team> [--all]|gc --preserve a,b [--apply]}")
        return 1
    cmd = argv[0]
    if cmd == "list":
        for t in list_teams():
            m = read_team_meta(t)
            print(f"{t}\tmembers={m['member_count']} non_lead={m.get('non_lead_count',0)} "
                  f"lead_session={m['lead_session_id']}")
        return 0
    if cmd == "meta" and len(argv) >= 2:
        print(json.dumps(read_team_meta(argv[1]), indent=2))
        return 0
    if cmd == "strip" and len(argv) >= 2:
        keep_lead = "--all" not in argv
        print(json.dumps(strip_team_members(argv[1], keep_lead=keep_lead), indent=2))
        return 0
    if cmd == "gc":
        preserve = []
        if "--preserve" in argv:
            i = argv.index("--preserve")
            if i + 1 < len(argv):
                preserve = [x for x in argv[i + 1].split(",") if x]
        apply = "--apply" in argv
        print(json.dumps(gc_orphaned_teams(preserve, apply=apply), indent=2))
        return 0
    print("usage: team_gc.py {list|meta <team>|strip <team> [--all]|gc --preserve a,b [--apply]}")
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
