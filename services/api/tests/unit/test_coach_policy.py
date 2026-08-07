from __future__ import annotations

from sauti.services.coach import CoachCandidates, evaluate


def cands(praise=None, corrections=None) -> CoachCandidates:
    return CoachCandidates(praise=praise, corrections=corrections or [])


class TestCoachPolicy:
    def test_no_candidates_no_notes(self):
        assert evaluate(cands(), user_turn_index=1) == []

    def test_praise_passes_through(self):
        notes = evaluate(cands(praise="Byiza!"), user_turn_index=1)
        assert len(notes) == 1
        assert notes[0].kind == "praise"
        assert notes[0].body == "Byiza!"

    def test_no_correction_on_first_turn(self):
        notes = evaluate(
            cands(praise="Byiza!", corrections=[{"title": "Fix", "body": "Say Muraho"}]),
            user_turn_index=1,
        )
        assert [n.kind for n in notes] == ["praise"]

    def test_at_most_one_correction(self):
        notes = evaluate(
            cands(
                praise="Byiza!",
                corrections=[
                    {"title": "Fix 1", "body": "first"},
                    {"title": "Fix 2", "body": "second"},
                    {"title": "Fix 3", "body": "third"},
                ],
            ),
            user_turn_index=3,
        )
        fixes = [n for n in notes if n.kind == "fix"]
        assert len(fixes) == 1
        assert fixes[0].body == "first"  # most important candidate wins

    def test_praise_always_precedes_fix(self):
        notes = evaluate(
            cands(praise="Byiza!", corrections=[{"title": "Fix", "body": "x"}]),
            user_turn_index=2,
        )
        assert [n.kind for n in notes] == ["praise", "fix"]

    def test_bare_correction_gets_synthetic_praise_first(self):
        notes = evaluate(
            cands(corrections=[{"title": "Fix", "body": "x"}]), user_turn_index=2
        )
        assert [n.kind for n in notes] == ["praise", "fix"]

    def test_blank_correction_body_dropped(self):
        notes = evaluate(
            cands(praise="Byiza!", corrections=[{"title": "Fix", "body": "   "}]),
            user_turn_index=2,
        )
        assert [n.kind for n in notes] == ["praise"]
