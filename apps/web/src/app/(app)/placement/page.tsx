"use client";

import Link from "next/link";
import { useReducer } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { placementAnswer, placementStart } from "@/lib/api/endpoints";
import {
  placementInitialState,
  placementReducer,
} from "@/lib/placement-reducer";
import { btnGhost, btnPrimary, Card, CardLabel, ErrorNote, Kicker, Lead, PageTitle } from "@/components/ui";

export default function PlacementPage() {
  const [state, dispatch] = useReducer(placementReducer, placementInitialState);
  const router = useRouter();
  const queryClient = useQueryClient();

  const start = async () => {
    dispatch({ type: "START" });
    try {
      const res = await placementStart();
      dispatch({ type: "START_SUCCESS", sessionId: res.session_id, question: res.question });
    } catch {
      dispatch({ type: "FAIL", message: "The placement couldn't start. Try again in a moment." });
    }
  };

  const submit = async () => {
    if (state.phase !== "question" || state.selected === null) return;
    const { sessionId, question, selected } = state;
    dispatch({ type: "SUBMIT" });
    try {
      const res = await placementAnswer({
        session_id: sessionId,
        item_id: question.item_id,
        answer: selected,
      });
      dispatch({ type: "ANSWER_SUCCESS", response: res });
      if (res.placed_level) {
        // Level changed server-side — roadmap and session are stale now.
        void queryClient.invalidateQueries();
      }
    } catch {
      dispatch({ type: "FAIL", message: "That answer didn't go through — try again." });
    }
  };

  if (state.phase === "result") {
    return (
      <div className="grid gap-5">
        <div>
          <Kicker>Placement · Result</Kicker>
          <PageTitle>You start at {state.placedLevel}.</PageTitle>
        </div>
        <Card testid="placement-result">
          <span className="flex h-11 w-14 items-center justify-center rounded-btn bg-accent font-mono text-[15px] font-semibold text-on-accent">
            {state.placedLevel}
          </span>
          <p className="mt-4 max-w-lg leading-relaxed text-ink-soft">
            {state.result ??
              "Your roadmap now begins where your Kinyarwanda actually is — the first session is ready."}
          </p>
          <button
            type="button"
            data-testid="placement-finish"
            onClick={() => router.replace("/")}
            className={`mt-6 ${btnPrimary}`}
          >
            Go to today&rsquo;s session
          </button>
        </Card>
      </div>
    );
  }

  if (state.phase === "question") {
    const { question } = state;
    const number = question.number ?? state.answered + 1;
    return (
      <div className="grid gap-5">
        <div>
          <Kicker>
            Placement · Question {number}
            {question.total ? ` of ${question.total}` : ""}
          </Kicker>
        </div>
        <Card testid="placement-question">
          {state.error ? <ErrorNote message={state.error} testid="placement-error" /> : null}
          <p className="ky mt-1 text-lg leading-snug">{question.prompt}</p>
          <div className="mt-4 grid gap-2">
            {question.options.map((option) => {
              const selected = state.selected === option;
              return (
                <button
                  key={option}
                  type="button"
                  data-testid="placement-answer"
                  aria-pressed={selected}
                  disabled={state.submitting}
                  onClick={() => dispatch({ type: "SELECT", option })}
                  className={`flex cursor-pointer items-center rounded-btn border-[1.5px] px-4 py-3 text-left transition-colors disabled:cursor-default disabled:opacity-70 ${
                    selected
                      ? "border-accent bg-accent-soft"
                      : "border-line bg-card hover:border-accent"
                  }`}
                >
                  <span className="ky text-base">{option}</span>
                </button>
              );
            })}
          </div>
          <div className="mt-5 flex justify-end">
            <button
              type="button"
              data-testid="placement-submit"
              disabled={state.selected === null || state.submitting}
              onClick={submit}
              className={btnPrimary}
            >
              {state.submitting ? "Checking…" : "Answer"}
            </button>
          </div>
        </Card>
        <p className="text-center text-xs text-ink-faint">
          Get one right and it pushes harder; miss and it eases off. No score mid-way — just keep going.
        </p>
      </div>
    );
  }

  // intro / starting
  return (
    <div className="grid gap-5">
      <div>
        <Kicker>Start here · Placement</Kicker>
        <PageTitle>Find your true starting point.</PageTitle>
        <Lead className="max-w-[560px]">
          The test adapts as you answer — get one right and it pushes harder, miss and it
          eases off. It ends by listening to you speak, because reading level and speaking
          level are rarely the same.
        </Lead>
      </div>

      <div className="flex flex-wrap gap-2.5">
        <span className="rounded-full border border-line bg-cream px-3.5 py-[7px] text-[12.5px] font-semibold text-ink-soft">
          12–18 questions
        </span>
        <span className="rounded-full border border-line bg-cream px-3.5 py-[7px] text-[12.5px] font-semibold text-ink-soft">
          ~15 minutes
        </span>
        <span className="rounded-full border border-green-line bg-green-soft px-3.5 py-[7px] text-[12.5px] font-semibold text-green">
          Includes speaking
        </span>
      </div>

      <Card>
        <CardLabel>How it works</CardLabel>
        <p className="ky mt-2 text-lg">
          Twelve to eighteen questions, then a short speaking check — most people finish in a
          quarter of an hour.
        </p>
      </Card>

      {state.phase === "intro" && state.error ? (
        <ErrorNote message={state.error} testid="placement-error" />
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          data-testid="begin-placement"
          disabled={state.phase === "starting"}
          onClick={start}
          className={btnPrimary}
        >
          {state.phase === "starting" ? "Preparing…" : "Begin placement"}
        </button>
        <Link href="/" data-testid="start-at-a1" className={btnGhost}>
          I&rsquo;m brand new — start at A1
        </Link>
      </div>
    </div>
  );
}
