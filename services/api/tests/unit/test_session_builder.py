from __future__ import annotations

import uuid

from sauti.services.session_builder import LessonRef, SpeakRef, assemble_plan

LESSON = LessonRef(
    id=uuid.uuid4(),
    title="Amakuru? — asking how someone is",
    unit_title="Greetings & people",
    situation_tag="greetings",
)
SPEAK = SpeakRef(item_id=uuid.uuid4(), sentence="Amakuru?", gloss="How are you?")


class TestAssemblePlan:
    def test_full_plan_is_25_minutes(self):
        plan = assemble_plan(5, LESSON, SPEAK, "speak", review_deck_tag="greetings")
        assert [b.kind for b in plan.blocks] == ["review", "lesson", "speak"]
        assert plan.total_min == 25
        assert plan.total_min == sum(b.mins for b in plan.blocks)

    def test_review_block_carries_deck_tag(self):
        plan = assemble_plan(3, LESSON, SPEAK, "speak", review_deck_tag="market")
        review = plan.blocks[0]
        assert review.ref_id == "market"  # frontend routes to /vocab/market
        assert "3" in review.title

    def test_no_due_reviews_drops_block_and_keeps_25(self):
        plan = assemble_plan(0, LESSON, SPEAK, "listen")
        assert [b.kind for b in plan.blocks] == ["lesson", "speak"]
        assert plan.total_min == 25  # lesson block grows to fill the session

    def test_due_count_capped_in_title(self):
        plan = assemble_plan(30, LESSON, SPEAK, "speak")
        assert "8" in plan.blocks[0].title

    def test_speak_block_names_weakest_skill(self):
        plan = assemble_plan(2, LESSON, SPEAK, "listen")
        speak = plan.blocks[-1]
        assert speak.kind == "speak"
        assert "listening" in speak.sub
        assert speak.ref_id == str(SPEAK.item_id)

    def test_lesson_ref_id_is_lesson_uuid(self):
        plan = assemble_plan(1, LESSON, SPEAK, "speak")
        lesson_block = next(b for b in plan.blocks if b.kind == "lesson")
        assert lesson_block.ref_id == str(LESSON.id)
        assert lesson_block.tag == "GREETINGS"
        assert lesson_block.sub == "Greetings & people"

    def test_course_finished_no_lesson(self):
        plan = assemble_plan(4, None, None, "speak")
        assert [b.kind for b in plan.blocks] == ["review"]
