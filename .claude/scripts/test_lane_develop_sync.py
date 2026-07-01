"""BL-442 AK-3: develop-Resync-Disziplin (GAP-3, SOA-2=Goal-Hook-merge-step).

RED-Tests (Test-Autor != GREEN-Implementierer). develop_sync_action entscheidet aus (ahead, behind) der Lane
ggue. develop, was zu tun ist — der per-BL Resync-Schritt (nach BL-Done mergen, vor BL-Start pullen),
der Lane-Divergenz verhindert.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lane_develop_sync as s  # noqa: E402


def test_in_sync():
    assert s.develop_sync_action(ahead=0, behind=0) == "in-sync"


def test_merge_when_ahead_clean():
    # Lane hat Commits die develop fehlen, develop nicht voraus -> clean ff-merge nach develop (per-BL-Done)
    assert s.develop_sync_action(ahead=4, behind=0) == "merge"


def test_pull_first_when_behind():
    # develop ist voraus -> erst develop integrieren (vor BL-Start), sonst Divergenz
    assert s.develop_sync_action(ahead=0, behind=3) == "pull-first"


def test_diverged_when_both():
    # beide voraus -> echte Divergenz, braucht Merge/Rebase-Aufloesung (HiL/coord)
    assert s.develop_sync_action(ahead=4, behind=3) == "diverged"


def test_should_merge_after_bl_done():
    assert s.should_merge_after_bl_done(ahead=4, behind=0) is True
    assert s.should_merge_after_bl_done(ahead=0, behind=0) is False
    assert s.should_merge_after_bl_done(ahead=4, behind=2) is False
