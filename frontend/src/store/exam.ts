import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { AttemptState, ResultSummary, ReviewItem } from "../api/types";

export type SyncStatus = "idle" | "saving" | "saved" | "offline" | "error";

export interface FinishedInfo {
  name: string;
  subject: string;
  result: ResultSummary | null;
  review: ReviewItem[] | null;
  finishedAt: string;
}

interface ExamStore {
  attemptId: string | null;
  token: string | null;
  snapshot: AttemptState | null;
  /** question id -> selected option id (current stage only) */
  answers: Record<string, string | null>;
  /** question ids changed locally and not yet confirmed by the server */
  dirty: Record<string, true>;
  stage: number;
  index: number;
  clockOffset: number;
  finished: FinishedInfo | null;
  syncStatus: SyncStatus;
  lastSavedAt: number | null;

  begin: (token: string, state: AttemptState) => void;
  applyServerState: (state: AttemptState) => void;
  select: (questionId: number, optionId: string | null) => void;
  markSynced: (sent: Record<string, string | null>) => void;
  setIndex: (index: number) => void;
  setSyncStatus: (status: SyncStatus) => void;
  complete: (state: AttemptState) => void;
  clearSession: () => void;
  reset: () => void;
}

const empty = {
  attemptId: null,
  token: null,
  snapshot: null,
  answers: {},
  dirty: {},
  stage: 1,
  index: 0,
  clockOffset: 0,
  syncStatus: "idle" as SyncStatus,
  lastSavedAt: null,
};

/** Safe localStorage: private mode / blocked storage must never break the exam. */
const safeStorage = createJSONStorage(() => ({
  getItem: (name: string) => {
    try {
      return window.localStorage.getItem(name);
    } catch {
      return null;
    }
  },
  setItem: (name: string, value: string) => {
    try {
      window.localStorage.setItem(name, value);
    } catch {
      /* storage full or blocked: answers still live in memory and on the server */
    }
  },
  removeItem: (name: string) => {
    try {
      window.localStorage.removeItem(name);
    } catch {
      /* ignore */
    }
  },
}));

export const useExam = create<ExamStore>()(
  persist(
    (set, get) => ({
      ...empty,
      finished: null,

      begin: (token, state) => {
        set({ ...empty, token, attemptId: state.id, finished: null });
        get().applyServerState(state);
      },

      applyServerState: (state) => {
        const prev = get();
        const offset = new Date(state.server_time).getTime() - Date.now();
        const stageChanged = prev.stage !== state.current_stage || prev.snapshot?.id !== state.id;
        const answers: Record<string, string | null> = {};
        const dirty: Record<string, true> = stageChanged ? {} : { ...prev.dirty };
        for (const q of state.questions) {
          const key = String(q.id);
          // Unsynced local choices are newer than what the server knows.
          answers[key] = dirty[key] ? (prev.answers[key] ?? null) : q.selected;
        }
        for (const key of Object.keys(dirty)) {
          if (!(key in answers)) delete dirty[key];
        }
        set({
          snapshot: state,
          stage: state.current_stage,
          answers,
          dirty,
          clockOffset: offset,
          index: stageChanged ? 0 : Math.min(prev.index, Math.max(0, state.questions.length - 1)),
        });
      },

      select: (questionId, optionId) => {
        const key = String(questionId);
        set((s) => ({ answers: { ...s.answers, [key]: optionId }, dirty: { ...s.dirty, [key]: true } }));
      },

      markSynced: (sent) => {
        set((s) => {
          const dirty = { ...s.dirty };
          for (const [key, value] of Object.entries(sent)) {
            if ((s.answers[key] ?? null) === value) delete dirty[key];
          }
          return { dirty, lastSavedAt: Date.now() };
        });
      },

      setIndex: (index) => set({ index }),
      setSyncStatus: (syncStatus) => set({ syncStatus }),

      complete: (state) => {
        set({
          ...empty,
          finished: {
            name: `${state.first_name} ${state.last_name}`,
            subject: state.subject,
            result: state.result,
            review: state.review,
            finishedAt: new Date().toISOString(),
          },
        });
      },

      clearSession: () => set({ ...empty }),
      reset: () => set({ ...empty, finished: null }),
    }),
    {
      name: "otp-exam-v1",
      storage: safeStorage,
      partialize: (s) => ({
        attemptId: s.attemptId,
        token: s.token,
        snapshot: s.snapshot,
        answers: s.answers,
        dirty: s.dirty,
        stage: s.stage,
        index: s.index,
        clockOffset: s.clockOffset,
        finished: s.finished,
      }),
    },
  ),
);

export function serverNow(offset: number) {
  return Date.now() + offset;
}
