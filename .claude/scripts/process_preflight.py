#!/usr/bin/env python3
"""
Process-Preflight-Check (2026-05-27).

Scannt vor `/_goal_backlog` oder `/_goal_parking_lot` den aktiven Vault auf
existing Drift-Pattern die im hard-enforce-Mode HARD BLOCKEN wuerden.

Zweck: dem User vor Lauf-Start ZEIGEN welche Compatibility-Gaps zwischen
existing Skills/Manifests + neuen Hooks bestehen.

Output: Liste der zu erwartenden Hook-Triggers pro Hook + Severity.

Usage:
  py -3 .claude/scripts/process_preflight.py [--vault-root=PATH]
  py -3 .claude/scripts/process_preflight.py --json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent


def find_vault_root(override=None):
    if override:
        return Path(override)
    try:
        import subprocess
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run([sys.executable, str(resolver)],
                                   capture_output=True, text=True, timeout=5)
            if proc.returncode == 0 and proc.stdout.strip():
                return Path(proc.stdout.strip())
    except Exception:
        pass
    return ROOT_DIR


def check_idf_batch_modes_drift(vault):
    """G#5: existing IDF schreibt batch_modes ohne batch_modes_set_by."""
    triggers = []
    for manifest_name in ["_factory_manifest.md", "_manifest.md"]:
        m = vault / manifest_name
        if not m.exists():
            continue
        try:
            content = m.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^\s*batch_modes\s*:", content, re.MULTILINE):
                has_writer = re.search(r"batch_modes_set_by\s*:\s*_SDF_berater_modusEntscheidung", content)
                if not has_writer:
                    triggers.append({
                        "hook": "guard_modus_writer + guard_geist5",
                        "severity": "HIGH",
                        "file": str(m.relative_to(vault) if m.is_relative_to(vault) else m),
                        "drift": "batch_modes ohne batch_modes_set_by",
                        "fix": "BL-218 IDF Rename umsetzen, oder existing batch_modes manuell mit set_by-Marker erweitern"
                    })
        except Exception:
            pass
    return triggers


def check_berater_provenance_drift(vault):
    """S#1: existing BERATER_OUTPUTS-Blocks ohne vollstaendige Provenance (set_by/exit_code/ts)."""
    triggers = []
    incomplete_count = 0
    for manifest_name in ["_factory_manifest.md", "_manifest.md"]:
        m = vault / manifest_name
        if not m.exists():
            continue
        try:
            content = m.read_text(encoding="utf-8", errors="replace")
            # Finde BERATER_OUTPUTS-Bloecke
            blocks = re.findall(r"##+\s+(BERATER_OUTPUTS[._]\w+).*?(?=##+|\Z)", content, re.DOTALL)
            for block in blocks:
                has_set_by = "set_by:" in block or "set_by =" in block
                has_exit_code = "exit_code:" in block
                has_ts = "ts:" in block or "timestamp:" in block
                if not (has_set_by and has_exit_code and has_ts):
                    incomplete_count += 1
            if incomplete_count > 0:
                triggers.append({
                    "hook": "guard_stab1_berater_provenance",
                    "severity": "HIGH",
                    "file": str(m.relative_to(vault) if m.is_relative_to(vault) else m),
                    "drift": f"{incomplete_count} BERATER_OUTPUTS-Bloecke ohne vollstaendige Provenance",
                    "fix": "Skills patchen damit set_by + exit_code + ts geschrieben werden. ODER: existing Bloecke unangetastet lassen — Hook prueft nur NEU geschriebene."
                })
        except Exception:
            pass
    return triggers


def check_manifest_duplicate_drift(vault):
    """S#9: existing Manifest hat 2x DF_BATCH_STATE ohne Suffix."""
    triggers = []
    singleton_sections = ["BDF_PIPELINE_STATE", "DF_BATCH_STATE", "FACTORY_STATES",
                          "BL_LIFECYCLE_STATE", "IDF_PIPELINE_STATE", "DF_PIPELINE_STATE"]
    for manifest_name in ["_factory_manifest.md", "_manifest.md"]:
        m = vault / manifest_name
        if not m.exists():
            continue
        try:
            content = m.read_text(encoding="utf-8", errors="replace")
            for section in singleton_sections:
                pattern = rf"^##\s+{section}\s*(\(.*?\))?\s*$"
                matches = re.findall(pattern, content, re.MULTILINE)
                if len(matches) > 1:
                    # Pruefe ob alle ein Suffix haben oder mehrere ohne
                    no_suffix = sum(1 for s in matches if not s)
                    if no_suffix > 1:
                        triggers.append({
                            "hook": "guard_stab9_manifest_dup",
                            "severity": "HIGH",
                            "file": str(m.relative_to(vault) if m.is_relative_to(vault) else m),
                            "drift": f"{no_suffix}x ## {section} ohne Round-Suffix",
                            "fix": "Manifest aufraeumen: alte DF_BATCH_STATE in Round-Suffix umbenennen oder loeschen"
                        })
        except Exception:
            pass
    return triggers


def check_modelsync_phantom_skips(vault):
    """S#2 + S#5: modelSync SKIP ohne reason."""
    triggers = []
    count = 0
    for manifest_name in ["_factory_manifest.md", "_manifest.md"]:
        m = vault / manifest_name
        if not m.exists():
            continue
        try:
            content = m.read_text(encoding="utf-8", errors="replace")
            skips = re.findall(r"phase_3_5_modelSync\s*:\s*SKIP", content)
            with_reason = re.findall(r"phase_3_5_modelSync[\s\S]{0,400}modelSync_skip_reason", content)
            unprotected = len(skips) - len(with_reason)
            if unprotected > 0:
                count += unprotected
                triggers.append({
                    "hook": "guard_stab2_phase_order + guard_stab5_empty_berater",
                    "severity": "MEDIUM",
                    "file": str(m.relative_to(vault) if m.is_relative_to(vault) else m),
                    "drift": f"{unprotected} phase_3_5_modelSync: SKIP ohne modelSync_skip_reason",
                    "fix": "Bei jedem SKIP einen skip_reason-Hinweis hinzufuegen ODER alte Skips als Legacy markieren"
                })
        except Exception:
            pass
    return triggers


def check_branch_hygiene():
    """S#6: viele uncommitted Files."""
    try:
        import subprocess
        result = subprocess.run(["git", "status", "--porcelain"],
                                 capture_output=True, text=True, timeout=10, cwd=str(ROOT_DIR))
        if result.returncode == 0:
            count = len([line for line in result.stdout.splitlines() if line.strip()])
            if count > 20:
                return [{
                    "hook": "guard_stab6_branch_hygiene",
                    "severity": "MEDIUM",
                    "file": "git status",
                    "drift": f"{count} modified files (Threshold: 20)",
                    "fix": "Commit der current branch ODER OMNI_BRANCH_HYGIENE_SKIP=1 setzen"
                }]
    except Exception:
        pass
    return []


def run_preflight(vault_root_override=None):
    vault = find_vault_root(vault_root_override)
    all_triggers = []
    all_triggers.extend(check_idf_batch_modes_drift(vault))
    all_triggers.extend(check_berater_provenance_drift(vault))
    all_triggers.extend(check_manifest_duplicate_drift(vault))
    all_triggers.extend(check_modelsync_phantom_skips(vault))
    all_triggers.extend(check_branch_hygiene())
    return {"vault": str(vault), "triggers": all_triggers, "count": len(all_triggers)}


def main(argv):
    p = argparse.ArgumentParser(description="Process-Preflight-Check vor /_goal_backlog/_goal_parking_lot")
    p.add_argument("--vault-root", help="Vault-Root Override")
    p.add_argument("--json", action="store_true", help="JSON-Output")
    args = p.parse_args(argv[1:])

    result = run_preflight(args.vault_root)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"=== Process-Preflight (Vault: {result['vault']}) ===")
        print(f"Drift-Trigger gefunden: {result['count']}")
        if not result['triggers']:
            print("\nGREEN — keine bekannten Drift-Pattern.")
            print("Sicher fuer --enforce-process=hard.")
        else:
            severities = {t['severity'] for t in result['triggers']}
            print(f"\nSeverity: {', '.join(sorted(severities))}")
            print("\nEmpfehlung: --enforce-process=warn (NICHT hard) bis Drift behoben.")
            print(f"\nTriggers:")
            for t in result['triggers']:
                print(f"\n  [{t['severity']}] {t['hook']}")
                print(f"    File:  {t['file']}")
                print(f"    Drift: {t['drift']}")
                print(f"    Fix:   {t['fix']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
