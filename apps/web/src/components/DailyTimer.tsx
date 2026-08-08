"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { useMutation } from "@tanstack/react-query";
import { patchProfile } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth";
import {
  DEFAULT_GOAL_MINUTES,
  GOAL_CHOICES,
  dayKey,
  stateForDay,
  tick,
  timerView,
} from "@/lib/study-timer";
import { getServerSnapshot, getSnapshot, subscribe, write } from "@/lib/study-timer-store";
import { Card, CardLabel } from "@/components/ui";

/**
 * "Learn for 15 minutes today" — a countdown against the learner's daily goal.
 *
 * It only runs while the tab is visible (a timer ticking in a background tab
 * would credit minutes nobody studied), and banks progress per local calendar
 * day so a reload mid-session loses nothing.
 */
export function DailyTimer() {
  const { me, refresh } = useAuth();
  const userId = me?.user?.id ?? "anon";
  const goalMinutes = me?.profile?.daily_goal_minutes ?? DEFAULT_GOAL_MINUTES;

  const stored = useSyncExternalStore(
    subscribe,
    useCallback(() => getSnapshot(userId), [userId]),
    getServerSnapshot,
  );
  const state = stateForDay(stored, dayKey(new Date()));

  const [running, setRunning] = useState(false);
  const [editingGoal, setEditingGoal] = useState(false);

  const view = timerView(state, goalMinutes);
  // A met goal stops the clock without an effect writing state back.
  const active = running && !view.done;

  // Tick on a wall-clock delta rather than counting intervals: a throttled tab
  // fires fewer of them, and the banked seconds should still be truthful.
  useEffect(() => {
    if (!active) return;
    let last = Date.now();
    const id = window.setInterval(() => {
      const now = Date.now();
      const delta = Math.round((now - last) / 1000);
      if (delta <= 0) return;
      last = now;
      const current = stateForDay(getSnapshot(userId), dayKey(new Date()));
      write(userId, tick(current, delta, goalMinutes));
    }, 1000);
    return () => window.clearInterval(id);
  }, [active, userId, goalMinutes]);

  // Studying means being here: pause when the tab goes away.
  useEffect(() => {
    const onVisibility = () => {
      if (document.visibilityState === "hidden") setRunning(false);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  const setGoal = useMutation({
    mutationFn: (minutes: number) => patchProfile({ daily_goal_minutes: minutes }),
    onSuccess: async () => {
      setEditingGoal(false);
      await refresh();
    },
  });

  return (
    <Card testid="daily-timer">
      <div className="flex items-start justify-between gap-3">
        <CardLabel>Today&rsquo;s minutes</CardLabel>
        <button
          type="button"
          data-testid="change-goal"
          onClick={() => setEditingGoal((v) => !v)}
          className="cursor-pointer font-mono text-[10px] tracking-[0.1em] text-ink-faint uppercase transition-colors hover:text-accent"
        >
          {view.goalMinutes} min goal
        </button>
      </div>

      {editingGoal ? (
        <div className="mt-3 flex flex-wrap gap-1.5" data-testid="goal-options">
          {GOAL_CHOICES.map((minutes) => (
            <button
              key={minutes}
              type="button"
              data-testid={`goal-option-${minutes}`}
              onClick={() => setGoal.mutate(minutes)}
              disabled={setGoal.isPending}
              className={`cursor-pointer rounded-full border-[1.5px] px-3 py-1.5 text-[13px] font-semibold transition-colors disabled:opacity-60 ${
                minutes === view.goalMinutes
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-line bg-card text-ink-soft hover:border-accent"
              }`}
            >
              {minutes} min
            </button>
          ))}
        </div>
      ) : null}

      <div className="mt-3 flex items-center gap-4">
        <p
          data-testid="timer-remaining"
          className={`font-mono text-[34px] leading-none font-semibold tabular-nums ${
            view.done ? "text-green" : "text-ink"
          }`}
        >
          {view.remainingLabel}
        </p>
        {!view.done ? (
          <button
            type="button"
            data-testid="timer-toggle"
            aria-pressed={active}
            onClick={() => setRunning((r) => !r)}
            className={`cursor-pointer rounded-full border-[1.5px] px-4 py-2 text-[13px] font-semibold transition-colors ${
              active
                ? "border-accent bg-accent text-on-accent"
                : "border-accent bg-transparent text-accent hover:bg-accent-soft"
            }`}
          >
            {active ? "Pause" : state.secondsDone > 0 ? "Resume" : "Start"}
          </button>
        ) : null}
      </div>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-line">
        <div
          data-testid="timer-progress"
          className={`h-full rounded-full transition-[width] duration-500 ${
            view.done ? "bg-green" : "bg-accent"
          }`}
          style={{ width: `${Math.round(view.progress * 100)}%` }}
        />
      </div>

      <p className="mt-2.5 text-[12.5px] text-ink-soft" data-testid="timer-status">
        {view.done ? (
          <span className="ky font-semibold text-green">
            Wagize umunsi mwiza! &mdash; goal met today.
          </span>
        ) : active ? (
          `${view.minutesDone} of ${view.goalMinutes} min in — keep going.`
        ) : state.secondsDone > 0 ? (
          `Paused at ${view.minutesDone} of ${view.goalMinutes} min.`
        ) : (
          `Set aside ${view.goalMinutes} minutes — rhythm beats streaks.`
        )}
      </p>
    </Card>
  );
}
