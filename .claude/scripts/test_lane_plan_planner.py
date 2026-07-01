"""BL-442 AK-4: zentraler Planer — next_bl_for_lane (SOA-1=BDF-extend Kern-Logik).

RED-Tests (Test-Autor != GREEN-Implementierer). next_bl_for_lane waehlt das naechste Queue-Item einer Lane,
das (a) nicht done ist und (b) nicht von einer ANDEREN Lane gehalten wird (Kollisions-frei) -> der zentrale
"wer baut als naechstes was"-Zuteiler (GAP-4). None wenn die Lane-Queue durch ist.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lane_plan as lp  # noqa: E402

PLAN = {
    "B": {"branch": "roadmap-b", "queue": ["BL-442", "BL-348", "BL-415"]},
    "C": {"branch": "roadmap-c", "queue": ["BL-415", "BL-416"]},
}


def test_next_skips_done():
    # BL-442 done -> next = BL-348
    assert lp.next_bl_for_lane("B", PLAN, done={"BL-442"}) == "BL-348"


def test_next_skips_other_lane_owned():
    # BL-442+BL-348 done -> naechstes B-Queue ist BL-415, ABER das haelt Lane C -> skip -> None
    assert lp.next_bl_for_lane("B", PLAN, done={"BL-442", "BL-348"}) is None


def test_next_first_open():
    # nichts done -> erstes B-Queue-Item BL-442
    assert lp.next_bl_for_lane("B", PLAN, done=set()) == "BL-442"


def test_next_for_own_owned_bl():
    # Lane C: BL-415 gehoert C selbst -> kein skip -> next = BL-415
    assert lp.next_bl_for_lane("C", PLAN, done=set()) == "BL-415"
