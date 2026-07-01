"""BL-442 AK-5: lane_plan.py — Maschinen-Schema fuer _lane_plan.md + Cross-Lane-Collision-Check.

RED-Tests (Test-Autor != GREEN-Implementierer, false-GREEN-Fang). Erwartetes Verhalten:
- parse_lane_plan(path) liest einen YAML-fenced ```yaml LANE_PLAN:```-Block -> dict{lane: {...}}.
- lane_of_bl(bl_id, plan) -> Lane die das BL haelt (oder None).
- is_collision(bl_id, my_lane, plan) -> True wenn eine ANDERE Lane das BL haelt (roadmap lane-aware Fundament, GAP-2).
- roundtrip: write_lane_plan(path, plan) dann parse_lane_plan(path) == plan (idempotent, BOM-frei/LF).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import lane_plan as lp  # noqa: E402

SAMPLE = """---
type: lane-plan
---
# Lane-Plan

Prosa-Teil hier (wird ignoriert).

```yaml
LANE_PLAN:
  A:
    branch: roadmap-a
    worktree: OmniCommand-wtA
    domain: [orchestrator-skills, modusEntscheidung]
    current: BL-404
    queue: [BL-404, BL-403, BL-422]
  B:
    branch: roadmap-b
    worktree: OmniCommand-wtB
    domain: [scripts, guards, index, arc42]
    current: BL-442
    queue: [BL-442]
  C:
    branch: roadmap-c
    worktree: OmniCommand-wtC
    domain: [stage, allocator]
    current: BL-412
    queue: [BL-412, BL-413, BL-415, BL-416, BL-409]
```
"""


def _write(tmp_path, text=SAMPLE):
    p = tmp_path / "_lane_plan.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_parse_returns_three_lanes(tmp_path):
    plan = lp.parse_lane_plan(_write(tmp_path))
    assert set(plan.keys()) == {"A", "B", "C"}
    assert plan["B"]["branch"] == "roadmap-b"
    assert plan["C"]["queue"] == ["BL-412", "BL-413", "BL-415", "BL-416", "BL-409"]


def test_lane_of_bl(tmp_path):
    plan = lp.parse_lane_plan(_write(tmp_path))
    assert lp.lane_of_bl("BL-403", plan) == "A"
    assert lp.lane_of_bl("BL-415", plan) == "C"
    assert lp.lane_of_bl("BL-999", plan) is None


def test_is_collision(tmp_path):
    plan = lp.parse_lane_plan(_write(tmp_path))
    # BL-415 gehoert Lane C -> Kollision wenn Lane B es ziehen will
    assert lp.is_collision("BL-415", "B", plan) is True
    # BL-442 gehoert Lane B selbst -> keine Kollision fuer B
    assert lp.is_collision("BL-442", "B", plan) is False
    # unbekanntes BL -> keine Kollision
    assert lp.is_collision("BL-999", "B", plan) is False


def test_roundtrip_idempotent(tmp_path):
    p = _write(tmp_path)
    plan = lp.parse_lane_plan(p)
    lp.write_lane_plan(p, plan)
    raw = p.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "BOM-frei"
    assert b"\r\n" not in raw, "reines LF"
    assert lp.parse_lane_plan(p) == plan, "roundtrip-stabil"
