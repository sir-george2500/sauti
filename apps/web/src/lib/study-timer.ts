/**
 * Daily study timer — pure logic, no React, no browser globals.
 *
 * The learner picks a daily goal (profile.daily_goal_minutes) and runs a
 * countdown while they study. Progress is per (user, local calendar day) and
 * survives reloads, so closing the tab mid-session never loses the minutes
 * already put in. Rolling into a new day starts from zero — the rhythm rule:
 * yesterday's shortfall never carries over as debt.
 */

export const GOAL_CHOICES = [10, 15, 25, 40] as const;
export const DEFAULT_GOAL_MINUTES = 25;
export const MIN_GOAL_MINUTES = 5;
export const MAX_GOAL_MINUTES = 120;

export interface TimerState {
  /** Local calendar day this progress belongs to, YYYY-MM-DD. */
  day: string;
  /** Seconds of study already banked today. */
  secondsDone: number;
}

/** Local (not UTC) calendar day — the learner's own midnight is the boundary. */
export function dayKey(now: Date): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function storageKey(userId: string): string {
  return `sauti:study-timer:${userId}`;
}

export function clampGoal(minutes: number): number {
  if (!Number.isFinite(minutes)) return DEFAULT_GOAL_MINUTES;
  return Math.min(MAX_GOAL_MINUTES, Math.max(MIN_GOAL_MINUTES, Math.round(minutes)));
}

/** Stored state for today — anything from another day resets to zero. */
export function stateForDay(stored: TimerState | null, today: string): TimerState {
  if (stored && stored.day === today) return stored;
  return { day: today, secondsDone: 0 };
}

/** Advance the timer, never past the goal (a met goal stays met, not more). */
export function tick(state: TimerState, deltaSeconds: number, goalMinutes: number): TimerState {
  if (deltaSeconds <= 0) return state;
  const goalSeconds = clampGoal(goalMinutes) * 60;
  return { ...state, secondsDone: Math.min(goalSeconds, state.secondsDone + deltaSeconds) };
}

export interface TimerView {
  /** Countdown as mm:ss — what the card shows. */
  remainingLabel: string;
  /** 0..1 of the goal completed, for the progress bar. */
  progress: number;
  done: boolean;
  minutesDone: number;
  goalMinutes: number;
}

export function timerView(state: TimerState, goalMinutes: number): TimerView {
  const goal = clampGoal(goalMinutes);
  const goalSeconds = goal * 60;
  const remaining = Math.max(0, goalSeconds - state.secondsDone);
  const mm = Math.floor(remaining / 60);
  const ss = remaining % 60;
  return {
    remainingLabel: `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`,
    progress: goalSeconds === 0 ? 1 : Math.min(1, state.secondsDone / goalSeconds),
    done: remaining === 0,
    minutesDone: Math.floor(state.secondsDone / 60),
    goalMinutes: goal,
  };
}

/** Parse persisted JSON defensively — a corrupt entry must never break Today. */
export function parseStored(raw: string | null): TimerState | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<TimerState>;
    if (typeof parsed?.day !== "string" || typeof parsed?.secondsDone !== "number") return null;
    if (!Number.isFinite(parsed.secondsDone) || parsed.secondsDone < 0) return null;
    return { day: parsed.day, secondsDone: Math.floor(parsed.secondsDone) };
  } catch {
    return null;
  }
}
