"""FSRS-4.5 scheduler as pure functions.

Grades: 1=again, 2=hard, 3=good, 4=easy.
State is a small frozen dataclass; `apply(state, grade, now)` returns the next
state deterministically (injectable clock — no hidden time reads).

Reference: FSRS-4.5 (open-spaced-repetition). Retrievability model:
    R(t, S) = (1 + FACTOR * t / S) ** DECAY,  DECAY = -0.5, FACTOR = 19/81
so that R(S, S) = 0.9 — an interval equal to stability targets 90% retention.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

# Default FSRS-4.5 weights.
W = (
    0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031,
    1.6474, 0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755,
)

DECAY = -0.5
FACTOR = 19.0 / 81.0
DESIRED_RETENTION = 0.9
MAX_INTERVAL_DAYS = 365.0
AGAIN_RELEARN_MINUTES = 10

GRADE_AGAIN, GRADE_HARD, GRADE_GOOD, GRADE_EASY = 1, 2, 3, 4


@dataclass(frozen=True)
class Srs:
    stability: float
    difficulty: float
    reps: int
    due_at: datetime
    last_reviewed_at: datetime | None = None


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def retrievability(elapsed_days: float, stability: float) -> float:
    if stability <= 0:
        return 0.0
    return (1.0 + FACTOR * max(elapsed_days, 0.0) / stability) ** DECAY


def interval_days(stability: float, retention: float = DESIRED_RETENTION) -> float:
    """Days until retrievability decays to `retention`."""
    ivl = (stability / FACTOR) * (retention ** (1.0 / DECAY) - 1.0)
    return clamp(ivl, 0.0, MAX_INTERVAL_DAYS)


def init_stability(grade: int) -> float:
    return max(W[grade - 1], 0.1)


def init_difficulty(grade: int) -> float:
    return clamp(W[4] - (grade - 3) * W[5], 1.0, 10.0)


def next_difficulty(d: float, grade: int) -> float:
    d_prime = d - W[6] * (grade - 3)
    # Mean reversion towards D0(good)
    d_next = W[7] * init_difficulty(GRADE_GOOD) + (1.0 - W[7]) * d_prime
    return clamp(d_next, 1.0, 10.0)


def next_stability_on_success(s: float, d: float, r: float, grade: int) -> float:
    hard_penalty = W[15] if grade == GRADE_HARD else 1.0
    easy_bonus = W[16] if grade == GRADE_EASY else 1.0
    growth = (
        math.exp(W[8])
        * (11.0 - d)
        * s ** (-W[9])
        * (math.exp(W[10] * (1.0 - r)) - 1.0)
        * hard_penalty
        * easy_bonus
    )
    return s * (1.0 + growth)


def next_stability_on_lapse(s: float, d: float, r: float) -> float:
    s_next = (
        W[11]
        * d ** (-W[12])
        * ((s + 1.0) ** W[13] - 1.0)
        * math.exp(W[14] * (1.0 - r))
    )
    return clamp(s_next, 0.1, s)  # a lapse never increases stability


def apply(state: Srs | None, grade: int, now: datetime) -> Srs:
    """Pure FSRS transition. `state is None` means first-ever review of the item."""
    if grade not in (1, 2, 3, 4):
        raise ValueError(f"grade must be 1..4, got {grade}")

    if state is None or state.reps == 0:
        s = init_stability(grade)
        d = init_difficulty(grade)
        reps = 1
    else:
        elapsed = 0.0
        if state.last_reviewed_at is not None:
            elapsed = (now - state.last_reviewed_at).total_seconds() / 86400.0
        r = retrievability(elapsed, state.stability)
        d = next_difficulty(state.difficulty, grade)
        if grade == GRADE_AGAIN:
            s = next_stability_on_lapse(state.stability, state.difficulty, r)
        else:
            s = next_stability_on_success(state.stability, state.difficulty, r, grade)
        reps = state.reps + 1

    if grade == GRADE_AGAIN:
        due = now + timedelta(minutes=AGAIN_RELEARN_MINUTES)
    else:
        due = now + timedelta(days=max(interval_days(s), 1.0 / 144.0))
    return Srs(stability=s, difficulty=d, reps=reps, due_at=due, last_reviewed_at=now)


def score_to_grade(score: float) -> int:
    """Map a 0..1 attempt score to an FSRS grade.

    Frontend contract (docs/frontend-notes.md): review grades arrive as evenly
    spaced scores 0, 1/3, 2/3, 1 and are recovered exactly as 1 + round(score*3).
    """
    return int(clamp(1 + round(score * 3), 1, 4))
