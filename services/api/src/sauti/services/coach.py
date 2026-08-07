"""CoachPolicy — a product rule, not a model behaviour.

The LLM only proposes candidates (praise + correction candidates) via a forced
structured call; this policy decides what the learner actually sees:
  - praise first: a praise note leads whenever anything is shown;
  - at most ONE correction per turn;
  - corrections only after a successful exchange (never on the learner's first turn).
Pure function — thoroughly unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sauti.schemas.common import CoachNote


@dataclass(frozen=True)
class CoachCandidates:
    praise: str | None = None
    corrections: list[dict] = field(default_factory=list)  # [{title, body}]


def evaluate(candidates: CoachCandidates, user_turn_index: int) -> list[CoachNote]:
    """user_turn_index is 1-based (1 = the learner's first message).

    Returns ordered notes: praise first, then at most one fix.
    """
    notes: list[CoachNote] = []
    allow_correction = user_turn_index >= 2 and bool(candidates.corrections)

    if candidates.praise:
        notes.append(CoachNote(title="Keep going", body=candidates.praise, kind="praise"))

    if allow_correction:
        first = candidates.corrections[0]
        title = str(first.get("title") or "One small fix")
        body = str(first.get("body") or "").strip()
        if body:
            if not notes:
                # Praise-first rule: never show a bare correction.
                notes.append(
                    CoachNote(
                        title="Keep going",
                        body="Wabivuze neza — good effort, you were understood.",
                        kind="praise",
                    )
                )
            notes.append(CoachNote(title=title, body=body, kind="fix"))

    return notes
