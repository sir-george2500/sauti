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
import { Card, ErrorNote, Kicker, PageTitle } from "@/components/ui";

const FACTS = [
  { big: "12–18", small: "questions" },
  { big: "~15", small: "minutes" },
  { big: "🎙", small: "includes speaking" },
] as const;

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
      <div className="mx-auto grid max-w-xl gap-6">
        <div>
          <Kicker>Placement · Result</Kicker>
          <PageTitle>You start at {state.placedLevel}.</PageTitle>
        </div>
        <Card testid="placement-result">
          <p className="ky text-5xl font-semibold text-accent-deep">{state.placedLevel}</p>
          <p className="mt-3 leading-relaxed text-ink-soft">
            {state.result ??
              "Your roadmap now begins where your Kinyarwanda actually is — the first session is ready."}
          </p>
          <button
            type="button"
            data-testid="placement-finish"
            onClick={() => router.replace("/")}
            className="mt-6 rounded-full bg-accent px-6 py-3 font-medium text-paper transition-colors hover:bg-accent-deep"
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
      <div className="mx-auto grid max-w-xl gap-6">
        <div>
          <Kicker>
            Placement · Question {number}
            {question.total ? ` of ${question.total}` : ""}
          </Kicker>
        </div>
        <Card testid="placement-question">
          {state.error ? <ErrorNote message={state.error} testid="placement-error" /> : null}
          <p className="ky mt-1 text-2xl leading-snug">{question.prompt}</p>
          <div className="mt-5 grid gap-2">
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
                  className={`rounded-xl border px-4 py-3 text-left transition-colors disabled:opacity-70 ${
                    selected
                      ? "border-accent bg-accent-soft"
                      : "border-line bg-card hover:border-accent"
                  }`}
                >
                  <span className="ky">{option}</span>
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
              className="rounded-full bg-accent px-6 py-2.5 font-medium text-paper transition-colors hover:bg-accent-deep disabled:opacity-50"
            >
              {state.submitting ? "Checking…" : "Answer"}
            </button>
          </div>
        </Card>
        <p className="text-center text-xs text-ink-soft">
          Get one right and it pushes harder; miss and it eases off. No score mid-way — just keep going.
        </p>
      </div>
    );
  }

  // intro / starting
  return (
    <div className="mx-auto grid max-w-xl gap-6">
      <div>
        <Kicker>Start here · Placement</Kicker>
        <PageTitle>Find your true starting point.</PageTitle>
        <p className="mt-3 leading-relaxed text-ink-soft">
          The test adapts as you answer — get one right and it pushes harder, miss and it
          eases off. It ends by listening to you speak, because reading level and speaking
          level are rarely the same.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {FACTS.map((f) => (
          <Card key={f.small} className="text-center">
            <p className="ky text-2xl font-semibold">{f.big}</p>
            <p className="mt-1 text-xs text-ink-soft">{f.small}</p>
          </Card>
        ))}
      </div>

      {state.phase === "intro" && state.error ? (
        <ErrorNote message={state.error} testid="placement-error" />
      ) : null}

      <div className="grid gap-3">
        <button
          type="button"
          data-testid="begin-placement"
          disabled={state.phase === "starting"}
          onClick={start}
          className="rounded-full bg-accent px-6 py-3.5 font-medium text-paper transition-colors hover:bg-accent-deep disabled:opacity-60"
        >
          {state.phase === "starting" ? "Preparing…" : "Begin placement"}
        </button>
        <Link
          href="/"
          data-testid="start-at-a1"
          className="rounded-full border border-line bg-card px-6 py-3.5 text-center text-ink-soft transition-colors hover:border-accent hover:text-ink"
        >
          I&rsquo;m brand new — start at A1
        </Link>
      </div>
    </div>
  );
}
