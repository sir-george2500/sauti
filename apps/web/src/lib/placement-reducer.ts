import type { Cefr, PlacementAnswerResponse, PlacementQuestion } from "./api/types";

/**
 * State machine for the adaptive placement flow (SPEC §5 /placement/start,
 * /placement/answer; §6 screen 9). Pure reducer so the loop is unit-testable
 * without the network.
 */

export type PlacementState =
  | { phase: "intro"; error: string | null }
  | { phase: "starting"; error: null }
  | {
      phase: "question";
      sessionId: string;
      question: PlacementQuestion;
      answered: number;
      selected: string | null;
      submitting: boolean;
      error: string | null;
    }
  | { phase: "result"; placedLevel: Cefr; result: string | null };

export type PlacementAction =
  | { type: "START" }
  | { type: "START_SUCCESS"; sessionId: string; question: PlacementQuestion }
  | { type: "SELECT"; option: string }
  | { type: "SUBMIT" }
  | { type: "ANSWER_SUCCESS"; response: PlacementAnswerResponse }
  | { type: "FAIL"; message: string };

export const placementInitialState: PlacementState = { phase: "intro", error: null };

export function placementReducer(
  state: PlacementState,
  action: PlacementAction,
): PlacementState {
  switch (action.type) {
    case "START":
      if (state.phase !== "intro") return state;
      return { phase: "starting", error: null };

    case "START_SUCCESS":
      if (state.phase !== "starting") return state;
      return {
        phase: "question",
        sessionId: action.sessionId,
        question: action.question,
        answered: 0,
        selected: null,
        submitting: false,
        error: null,
      };

    case "SELECT":
      if (state.phase !== "question" || state.submitting) return state;
      return { ...state, selected: action.option, error: null };

    case "SUBMIT":
      if (state.phase !== "question" || state.selected === null || state.submitting) {
        return state;
      }
      return { ...state, submitting: true, error: null };

    case "ANSWER_SUCCESS": {
      if (state.phase !== "question") return state;
      const { response } = action;
      if (response.placed_level) {
        return {
          phase: "result",
          placedLevel: response.placed_level,
          result: response.result ?? null,
        };
      }
      if (response.question) {
        return {
          ...state,
          question: response.question,
          answered: state.answered + 1,
          selected: null,
          submitting: false,
          error: null,
        };
      }
      return {
        ...state,
        submitting: false,
        error: "The placement service sent an unexpected response.",
      };
    }

    case "FAIL":
      if (state.phase === "starting") return { phase: "intro", error: action.message };
      if (state.phase === "question") {
        return { ...state, submitting: false, error: action.message };
      }
      return state;

    default:
      return state;
  }
}
