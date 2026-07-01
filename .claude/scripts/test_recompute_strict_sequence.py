"""
BL-165 AK-13 PL-13-04 — Strict R1->R2->R3 sequence tests.
Validates that R2 cannot run before R1, R3 cannot run before R1+R2,
and parallel execution raises an error.
"""
import pytest


class SequenceTracker:
    """Tracks which phases have been completed and enforces STRICT ordering."""

    def __init__(self):
        self._done = set()
        self._running = set()

    def start(self, phase: str):
        if self._running:
            raise RuntimeError(f"Parallel execution forbidden: {self._running} already running")
        if phase == "R2" and "R1" not in self._done:
            raise RuntimeError(f"R2 cannot start before R1 is done (STRICT-SEQUENCE)")
        if phase == "R3" and not {"R1", "R2"}.issubset(self._done):
            raise RuntimeError(f"R3 cannot start before R1+R2 are done (STRICT-SEQUENCE)")
        self._running.add(phase)

    def finish(self, phase: str):
        self._running.discard(phase)
        self._done.add(phase)

    def run_phase(self, phase: str, items: list) -> list:
        self.start(phase)
        result = list(items)  # simulate processing
        self.finish(phase)
        return result


def run_recompute_strict(batch_items: list, *, force_parallel: bool = False):
    """Simulate R1->R2->R3 pipeline. Raises on constraint violation."""
    tracker = SequenceTracker()

    if force_parallel:
        # Attempt to start R2 while R1 is still running
        tracker._running.add("R1")
        tracker.start("R2")  # should raise
        return

    r1_result = tracker.run_phase("R1", batch_items)
    r2_result = tracker.run_phase("R2", r1_result)
    r3_result = tracker.run_phase("R3", r2_result)
    return r3_result


class TestRecomputeStrictSequence:

    def test_r1_before_r2(self):
        """R2 must not run before R1 is done."""
        tracker = SequenceTracker()
        # R1 not finished yet — R2 start must raise
        with pytest.raises(RuntimeError, match="R2 cannot start before R1"):
            tracker.start("R2")

    def test_r3_after_r1_r2(self):
        """R3 must not run unless both R1 and R2 are done."""
        tracker = SequenceTracker()
        # Neither R1 nor R2 done
        with pytest.raises(RuntimeError, match="R3 cannot start before R1\\+R2"):
            tracker.start("R3")

        # Only R1 done
        tracker.finish("R1")
        with pytest.raises(RuntimeError, match="R3 cannot start before R1\\+R2"):
            tracker.start("R3")

        # Both R1+R2 done — R3 is now allowed
        tracker.finish("R2")
        tracker.start("R3")  # must NOT raise
        tracker.finish("R3")

    def test_parallel_forbidden(self):
        """Parallel execution of any two phases must raise an error."""
        with pytest.raises(RuntimeError, match="Parallel execution forbidden"):
            run_recompute_strict(batch_items=["item1", "item2"], force_parallel=True)

    def test_happy_path_strict_sequence(self):
        """Full R1->R2->R3 run in correct order must succeed."""
        items = ["item1", "item2", "item3"]
        result = run_recompute_strict(items)
        assert result == items

    def test_r1_then_r2_then_r3_order(self):
        """Verify order is enforced via tracker state machine."""
        tracker = SequenceTracker()

        # R1
        tracker.start("R1")
        tracker.finish("R1")
        assert "R1" in tracker._done

        # R2 (after R1)
        tracker.start("R2")
        tracker.finish("R2")
        assert "R2" in tracker._done

        # R3 (after R1+R2)
        tracker.start("R3")
        tracker.finish("R3")
        assert "R3" in tracker._done
