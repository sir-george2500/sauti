"""FSRS-4.5 pure-function tests — deterministic, no I/O."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from sauti.services import srs

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def first(grade: int) -> srs.Srs:
    return srs.apply(None, grade, NOW)


class TestFirstReview:
    def test_initial_stability_matches_weights(self):
        for grade in (1, 2, 3, 4):
            state = first(grade)
            assert state.stability == pytest.approx(srs.W[grade - 1])
            assert state.reps == 1

    def test_initial_difficulty_ordering(self):
        # Harder grades -> higher difficulty.
        d = [first(g).difficulty for g in (4, 3, 2, 1)]
        assert d == sorted(d)
        for x in d:
            assert 1.0 <= x <= 10.0

    def test_again_due_in_ten_minutes(self):
        state = first(1)
        assert state.due_at == NOW + timedelta(minutes=srs.AGAIN_RELEARN_MINUTES)

    def test_better_grades_push_due_further(self):
        dues = [first(g).due_at for g in (2, 3, 4)]
        assert dues == sorted(dues)
        assert first(4).due_at > NOW + timedelta(days=1)


class TestSubsequentReviews:
    def test_success_grows_stability(self):
        s1 = first(3)
        later = s1.due_at
        s2 = srs.apply(s1, 3, later)
        assert s2.stability > s1.stability
        assert s2.reps == 2

    def test_easy_grows_more_than_hard(self):
        s1 = first(3)
        later = s1.due_at
        hard = srs.apply(s1, 2, later)
        good = srs.apply(s1, 3, later)
        easy = srs.apply(s1, 4, later)
        assert hard.stability < good.stability < easy.stability

    def test_lapse_shrinks_stability_and_raises_difficulty(self):
        state = first(3)
        for _ in range(3):
            state = srs.apply(state, 3, state.due_at)
        lapsed = srs.apply(state, 1, state.due_at)
        assert lapsed.stability < state.stability
        assert lapsed.difficulty > state.difficulty
        assert lapsed.due_at == state.due_at + timedelta(minutes=10)

    def test_difficulty_clamped(self):
        state = first(1)
        for _ in range(30):
            state = srs.apply(state, 1, state.due_at)
        assert state.difficulty <= 10.0
        state2 = first(4)
        for _ in range(30):
            state2 = srs.apply(state2, 4, state2.due_at)
        assert state2.difficulty >= 1.0

    def test_deterministic(self):
        a = srs.apply(first(3), 3, NOW + timedelta(days=3))
        b = srs.apply(first(3), 3, NOW + timedelta(days=3))
        assert a == b

    def test_interval_capped_at_max(self):
        state = first(4)
        for _ in range(50):
            state = srs.apply(state, 4, state.due_at)
        assert (state.due_at - state.last_reviewed_at).days <= srs.MAX_INTERVAL_DAYS


class TestRetrievability:
    def test_r_at_stability_is_90pct(self):
        assert srs.retrievability(10.0, 10.0) == pytest.approx(0.9, abs=1e-9)

    def test_r_decays(self):
        assert srs.retrievability(20.0, 10.0) < srs.retrievability(5.0, 10.0)

    def test_interval_at_desired_retention_equals_stability(self):
        assert srs.interval_days(10.0) == pytest.approx(10.0, rel=1e-9)


class TestGradeMapping:
    def test_frontend_contract_exact_recovery(self):
        # docs/frontend-notes.md: grades arrive as scores 0, 1/3, 2/3, 1.
        assert srs.score_to_grade(0.0) == 1
        assert srs.score_to_grade(1 / 3) == 2
        assert srs.score_to_grade(2 / 3) == 3
        assert srs.score_to_grade(1.0) == 4

    def test_bounds(self):
        assert srs.score_to_grade(0.05) == 1
        assert srs.score_to_grade(0.95) == 4

    def test_invalid_grade_rejected(self):
        with pytest.raises(ValueError):
            srs.apply(None, 5, NOW)
        with pytest.raises(ValueError):
            srs.apply(None, 0, NOW)
