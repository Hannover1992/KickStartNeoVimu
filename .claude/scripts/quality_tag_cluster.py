"""
quality_tag_cluster.py — BL-177 AK-4 Tag-Cluster-Consistency Checker

Finds topic clusters from tags, checks for singleton topics, cross-references.

CLI: py -3 quality_tag_cluster.py check --bl=BL-XXX [--vault=PATH]
     py -3 quality_tag_cluster.py clusters --vault=PATH

Exit codes (INV-QUALITY-1):
  0 = PASS
  1 = WARN (singleton cluster)
  2 = BLOCK (ERROR in tag structure)
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from quality_berater_base import (
    BaseQualityBerater,
    QualityResult,
    Finding,
    SEVERITY_ERROR,
    SEVERITY_WARN,
    SEVERITY_INFO,
)
from quality_node_health import parse_frontmatter, VALID_SUBFOLDERS_ALL


# ---------------------------------------------------------------------------
# Topic / Cluster helpers
# ---------------------------------------------------------------------------

def extract_tags(frontmatter: dict) -> list[str]:
    """Extract normalized tag list from frontmatter."""
    tags = frontmatter.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    return [str(t).strip().lower() for t in tags if t]


def find_topic_clusters(all_bls: list[dict]) -> dict[str, list[str]]:
    """
    Group BL IDs by tag (topic).
    all_bls: list of {bl_id: str, frontmatter: dict}
    Returns: {tag: [bl_id, ...]}
    """
    clusters: dict[str, list[str]] = defaultdict(list)
    for bl_info in all_bls:
        bl_id = bl_info.get("bl_id", "")
        fm = bl_info.get("frontmatter") or {}
        for tag in extract_tags(fm):
            clusters[tag].append(bl_id)
    return dict(clusters)


def check_singleton_topics(clusters: dict[str, list[str]]) -> list[Finding]:
    """
    WARN when a topic/tag has only 1 BL referencing it (isolated tag).
    Exception: tags that are BL-specific IDs (e.g. 'bl-177') are skipped.
    """
    findings = []
    for tag, bls in sorted(clusters.items()):
        # Skip tags that look like BL IDs
        if re.match(r'^bl-\d+$', tag, re.IGNORECASE):
            continue
        if len(bls) == 1:
            findings.append(Finding(
                SEVERITY_WARN,
                f"Tag '{tag}' appears in only 1 BL ({bls[0]}) — potential orphan topic",
                field="tags",
                fix_suggestion=f"Consider merging '{tag}' with a related tag or adding it to more BLs",
            ))
    return findings


def check_cross_references_for_topic(
    topic: str,
    bls_in_topic: list[str],
    all_bls_fm: dict[str, dict],
) -> list[Finding]:
    """
    Check that BLs sharing a topic have at least some cross-references (related_bl or builds_on).
    Returns WARN if BLs in the same topic have NO cross-links.
    """
    findings = []
    if len(bls_in_topic) < 2:
        return findings  # only makes sense with 2+

    for bl_id in bls_in_topic:
        fm = all_bls_fm.get(bl_id, {})
        related = fm.get("related_bl") or []
        builds_on = fm.get("builds_on") or []
        if isinstance(related, str):
            related = [related]
        if isinstance(builds_on, str):
            builds_on = [builds_on]

        all_refs = [str(r).upper() for r in related + builds_on]
        peers = [b.upper() for b in bls_in_topic if b.upper() != bl_id.upper()]
        has_cross_ref = any(p in all_refs for p in peers)

        if not has_cross_ref and len(bls_in_topic) > 2:
            findings.append(Finding(
                SEVERITY_INFO,
                f"{bl_id} shares topic '{topic}' with {len(bls_in_topic)-1} peers but has no cross-reference",
                field="related_bl",
                fix_suggestion=f"Add related_bl: [{', '.join(peers[:2])}] to strengthen topic cluster",
            ))
    return findings


def check_tag_format(tags: list[str], bl_id: str) -> list[Finding]:
    """
    Check tags follow kebab-case convention (no spaces, no uppercase).
    """
    findings = []
    for tag in tags:
        if " " in tag:
            findings.append(Finding(
                SEVERITY_ERROR,
                f"Tag '{tag}' in {bl_id} contains spaces — use kebab-case",
                field="tags",
                fix_suggestion=f"Replace '{tag}' with '{tag.replace(' ', '-')}'",
            ))
        elif tag != tag.lower():
            findings.append(Finding(
                SEVERITY_WARN,
                f"Tag '{tag}' in {bl_id} is not lowercase — convention requires lowercase",
                field="tags",
                fix_suggestion=f"Replace '{tag}' with '{tag.lower()}'",
            ))
    return findings


# ---------------------------------------------------------------------------
# Tag Cluster Berater
# ---------------------------------------------------------------------------

class TagClusterBerater(BaseQualityBerater):
    """
    Quality-Berater for tag cluster consistency.

    data dict expected keys:
        frontmatter (dict)       — of the BL being checked
        all_bls (list[dict])     — [{bl_id, frontmatter}, ...] for cluster analysis
    """

    check_type = "tag_cluster"

    def run_checks(self, bl_id: str, data: dict, auto_fix: bool = False) -> QualityResult:
        result = QualityResult(bl_id=bl_id, check_type=self.check_type)

        fm = data.get("frontmatter") or {}
        all_bls = data.get("all_bls") or []

        # Tag format check
        tags = extract_tags(fm)
        for f in check_tag_format(tags, bl_id):
            result.add_finding(f)

        # Cluster analysis (if all_bls provided)
        if all_bls:
            clusters = find_topic_clusters(all_bls)
            singleton_findings = check_singleton_topics(clusters)

            # Only report findings relevant to this BL's tags
            for f in singleton_findings:
                # f.message contains the tag name
                for tag in tags:
                    if f"'{tag}'" in f.message:
                        result.add_finding(f)
                        break

        return result


# ---------------------------------------------------------------------------
# Vault scanner
# ---------------------------------------------------------------------------

def scan_vault_bls(vault_root: str) -> list[dict]:
    """
    Scan vault and return list of {bl_id, frontmatter} for all BLs.
    """
    result = []
    backlog_dir = os.path.join(vault_root, "Backlog")

    def _process_folder(folder_path: str, bl_id: str) -> None:
        manifest = os.path.join(folder_path, "_manifest.md")
        if os.path.isfile(manifest):
            with open(manifest, encoding="utf-8") as fh:
                content = fh.read()
            fm = parse_frontmatter(content) or {}
            result.append({"bl_id": bl_id, "frontmatter": fm})

    if os.path.isdir(backlog_dir):
        for entry in os.listdir(backlog_dir):
            full = os.path.join(backlog_dir, entry)
            if os.path.isdir(full):
                m = re.match(r'^(BL-\d+)', entry, re.IGNORECASE)
                if m:
                    _process_folder(full, m.group(1).upper())

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_check(args: argparse.Namespace) -> int:
    vault_root = os.path.abspath(args.vault)
    all_bls = scan_vault_bls(vault_root)
    all_bls_fm = {b["bl_id"]: b["frontmatter"] for b in all_bls}

    bl_id = args.bl.upper()
    fm = all_bls_fm.get(bl_id, {})
    if not fm:
        print(f"[WARN] No frontmatter found for {bl_id}")

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    berater = TagClusterBerater(repo_root=repo_root)
    data = {"frontmatter": fm, "all_bls": all_bls}
    result = berater.run(bl_id=bl_id, data=data)
    berater.write_output(result)
    return result.exit_code


def cmd_clusters(args: argparse.Namespace) -> int:
    """Print cluster visualization (Mermaid + text)."""
    vault_root = os.path.abspath(args.vault)
    all_bls = scan_vault_bls(vault_root)

    clusters = find_topic_clusters(all_bls)
    singletons = check_singleton_topics(clusters)

    print(f"\n=== Tag Cluster Report ({len(all_bls)} BLs, {len(clusters)} tags) ===\n")

    # Sort by cluster size descending
    for tag, bls in sorted(clusters.items(), key=lambda x: -len(x[1])):
        marker = " [SINGLETON]" if len(bls) == 1 else ""
        print(f"  {tag} ({len(bls)} BLs){marker}: {', '.join(sorted(bls)[:8])}")

    if singletons:
        print(f"\n[WARN] {len(singletons)} singleton tag(s) found.")
    else:
        print("\n[OK] No singleton tags found.")

    return 1 if singletons else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="BL-177 Tag Cluster Checker")
    sub = parser.add_subparsers(dest="cmd")

    chk = sub.add_parser("check", help="Check tag cluster for single BL")
    chk.add_argument("--bl", required=True)
    chk.add_argument("--vault", default=os.path.join(os.path.dirname(__file__), "..", "..", "..", "OmniCommand"))

    cl = sub.add_parser("clusters", help="Show all tag clusters across vault")
    cl.add_argument("--vault", default=os.path.join(os.path.dirname(__file__), "..", "..", "..", "OmniCommand"))

    args = parser.parse_args()
    if args.cmd == "check":
        return cmd_check(args)
    elif args.cmd == "clusters":
        return cmd_clusters(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
