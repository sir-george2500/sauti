"""PlacementEngine — simple adaptive IRT (pure math here, DB glue in the router).

Theta starts at 0. Each answer steps theta by ±K/(1+n) (right/wrong, n = number
answered so far). The next item served is the unserved item whose difficulty is
nearest theta. 12–18 questions; early stop once the step size is negligible.
"""
from __future__ import annotations

from sauti.schemas.common import CEFR_ORDER

K = 1.0
MIN_QUESTIONS = 12
MAX_QUESTIONS = 18

# Item difficulty is derived from its level's CEFR.
LEVEL_DIFFICULTY = {"A1": -1.5, "A2": -0.5, "B1": 0.5, "B2": 1.5, "C1": 2.5, "C2": 3.5}

# theta upper bounds per placed level (first match wins)
THETA_BANDS = [(-1.0, "A1"), (0.0, "A2"), (1.0, "B1"), (2.0, "B2"), (3.0, "C1")]


def step_theta(theta: float, correct: bool, n_answered: int) -> float:
    """n_answered = questions answered BEFORE this one (0-based)."""
    step = K / (1.0 + n_answered)
    return theta + step if correct else theta - step


def is_done(n_answered: int) -> bool:
    if n_answered >= MAX_QUESTIONS:
        return True
    if n_answered < MIN_QUESTIONS:
        return False
    # After MIN_QUESTIONS the remaining step is K/(1+n) <= K/13 — negligible.
    return True


def theta_to_cefr(theta: float, available: list[str] | None = None) -> str:
    placed = "C2"
    for upper, cefr in THETA_BANDS:
        if theta < upper:
            placed = cefr
            break
    if available:
        # Clamp to the highest level that actually exists in the course.
        ranked = [c for c in CEFR_ORDER if c in available]
        if placed not in ranked and ranked:
            idx = CEFR_ORDER.index(placed)
            below = [c for c in ranked if CEFR_ORDER.index(c) <= idx]
            placed = below[-1] if below else ranked[0]
    return placed


def pick_next(
    theta: float,
    candidates: list[tuple[str, str]],  # (item_id, cefr) not yet served
) -> str | None:
    """Return the candidate item id whose difficulty is nearest theta.

    Ties break deterministically by item id so the flow is reproducible.
    """
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda c: (abs(LEVEL_DIFFICULTY.get(c[1], 0.0) - theta), c[0]),
    )[0]
