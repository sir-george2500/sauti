from __future__ import annotations

import pytest

from sauti.services import placement


class TestThetaUpdates:
    def test_first_step_is_full_k(self):
        assert placement.step_theta(0.0, True, 0) == pytest.approx(placement.K)
        assert placement.step_theta(0.0, False, 0) == pytest.approx(-placement.K)

    def test_steps_shrink(self):
        deltas = [
            abs(placement.step_theta(0.0, True, n)) for n in range(6)
        ]
        assert deltas == sorted(deltas, reverse=True)
        assert deltas[5] == pytest.approx(placement.K / 6)

    def test_all_correct_converges_upward(self):
        theta = 0.0
        for n in range(12):
            theta = placement.step_theta(theta, True, n)
        assert theta > 2.0

    def test_alternating_answers_hover_near_zero(self):
        theta = 0.0
        for n in range(12):
            theta = placement.step_theta(theta, n % 2 == 0, n)
        assert abs(theta) < 1.0


class TestStopRule:
    def test_never_done_before_minimum(self):
        for n in range(placement.MIN_QUESTIONS):
            assert not placement.is_done(n)

    def test_done_at_minimum_and_beyond(self):
        assert placement.is_done(placement.MIN_QUESTIONS)
        assert placement.is_done(placement.MAX_QUESTIONS)


class TestCefrMapping:
    def test_bands(self):
        assert placement.theta_to_cefr(-2.0) == "A1"
        assert placement.theta_to_cefr(-0.5) == "A2"
        assert placement.theta_to_cefr(0.5) == "B1"
        assert placement.theta_to_cefr(1.5) == "B2"
        assert placement.theta_to_cefr(2.5) == "C1"
        assert placement.theta_to_cefr(4.0) == "C2"

    def test_clamped_to_available_levels(self):
        # Course only has A1+A2 seeded: a B2 theta places at A2.
        assert placement.theta_to_cefr(1.5, ["A1", "A2"]) == "A2"
        assert placement.theta_to_cefr(-2.0, ["A1", "A2"]) == "A1"


class TestItemSelection:
    def test_picks_nearest_difficulty(self):
        candidates = [("i1", "A1"), ("i2", "A2"), ("i3", "B1")]
        assert placement.pick_next(-1.5, candidates) == "i1"
        assert placement.pick_next(0.5, candidates) == "i3"

    def test_tie_breaks_deterministically_by_id(self):
        candidates = [("b", "A2"), ("a", "A2")]
        assert placement.pick_next(-0.5, candidates) == "a"

    def test_empty_pool(self):
        assert placement.pick_next(0.0, []) is None
