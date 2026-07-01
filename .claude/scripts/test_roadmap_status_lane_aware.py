"""BL-442 AK-2: roadmap_status lane-aware target selection (GAP-2).

RED-Tests (Test-Autor != GREEN-Implementierer). Erwartetes Verhalten:
- roadmap_status(..., lane_plan=plan, my_lane="B") ueberspringt bei der target-Wahl BLs, die eine ANDERE
  Lane haelt (is_collision), und nimmt das naechste nicht-kollidierende BL. Solche BLs landen in
  state["blocked_other_lane"].
- OHNE lane_plan/my_lane: UNVERAENDERTES Verhalten (backward-compat) — target = erstes remaining BL.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import roadmap_status as rs  # noqa: E402

ROADMAP = """<!-- ROADMAP-ORDER:START -->
- BL-415
- BL-348
<!-- ROADMAP-ORDER:END -->
"""
INDEX = {
    "BL-415": {"status": "DRAFT", "reifegrad": "UNREIF"},
    "BL-348": {"status": "DRAFT", "reifegrad": "SC-REIF"},
}
PLAN = {
    "B": {"branch": "roadmap-b", "queue": ["BL-348"]},
    "C": {"branch": "roadmap-c", "queue": ["BL-415", "BL-416"]},
}


def test_backward_compat_no_lane_params():
    """Ohne lane-Params: target = erstes remaining (BL-415), wie bisher."""
    st = rs.roadmap_status(ROADMAP, INDEX, done_ids=set())
    assert st["target"] == "BL-415"


def test_lane_aware_skips_other_lane_bl():
    """my_lane=B: BL-415 gehoert Lane C -> skip -> target=BL-348; BL-415 in blocked_other_lane."""
    st = rs.roadmap_status(ROADMAP, INDEX, done_ids=set(), lane_plan=PLAN, my_lane="B")
    assert st["target"] == "BL-348", f"erwartet BL-348, war {st['target']}"
    assert "BL-415" in st.get("blocked_other_lane", []), "BL-415 muss als other-lane geblockt gelistet sein"


def test_lane_aware_own_lane_not_blocked():
    """my_lane=C: BL-415 gehoert C selbst -> kein skip -> target=BL-415."""
    st = rs.roadmap_status(ROADMAP, INDEX, done_ids=set(), lane_plan=PLAN, my_lane="C")
    assert st["target"] == "BL-415"
