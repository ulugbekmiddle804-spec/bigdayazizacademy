import { useCallback, useEffect, useRef } from "react";

import { examApi } from "../api/exam";
import { ApiError } from "../api/http";
import { useExam } from "../store/exam";

interface Options {
  /** Server says the stage/attempt state changed (time over, already finished...). */
  onConflict: () => void;
  /** Attempt no longer exists or was annulled. */
  onLost: () => void;
}

/**
 * Reliable answer saving:
 *  - every change is stored in localStorage first (zustand persist),
 *  - then sent to the server in small batches (debounced),
 *  - failed requests are retried with exponential backoff and when the
 *    browser comes back online,
 *  - pending answers are flushed with `keepalive` when the tab is hidden/closed.
 */
export function useAnswerSync({ onConflict, onLost }: Options) {
  const inFlight = useRef(false);
  const attempt = useRef(0);
  const timer = useRef<number | undefined>(undefined);
  const callbacks = useRef({ onConflict, onLost });
  callbacks.current = { onConflict, onLost };

  const flush = useCallback(async (keepalive = false): Promise<boolean> => {
    const s = useExam.getState();
    if (!s.attemptId || !s.token) return true;
    const keys = Object.keys(s.dirty);
    if (keys.length === 0) return true;
    if (inFlight.current) return false;
    inFlight.current = true;
    const sent: Record<string, string | null> = {};
    for (const k of keys) sent[k] = s.answers[k] ?? null;
    s.setSyncStatus("saving");
    try {
      await examApi.save(
        s.attemptId,
        s.token,
        s.stage,
        keys.map((k) => ({ id: Number(k), option: sent[k] })),
        keepalive,
      );
      const st = useExam.getState();
      st.markSynced(sent);
      attempt.current = 0;
      const remaining = Object.keys(useExam.getState().dirty).length;
      st.setSyncStatus(remaining ? "saving" : "saved");
      if (remaining) schedule(250);
      return remaining === 0;
    } catch (err) {
      const e = err as ApiError;
      const st = useExam.getState();
      if (e.status === 409) {
        callbacks.current.onConflict();
      } else if (e.status === 404) {
        callbacks.current.onLost();
      } else if (e.status === 400) {
        // Invalid payload (should not happen): drop it and resync with the server.
        st.markSynced(sent);
        callbacks.current.onConflict();
      } else {
        st.setSyncStatus(e.isNetwork || !navigator.onLine ? "offline" : "error");
        attempt.current += 1;
        schedule(Math.min(15000, 1000 * 2 ** Math.min(attempt.current, 4)));
      }
      return false;
    } finally {
      inFlight.current = false;
    }
  }, []);

  const schedule = useCallback(
    (delay: number) => {
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => void flush(), delay);
    },
    [flush],
  );

  useEffect(() => {
    // Debounced save after each change.
    const unsub = useExam.subscribe((state, prev) => {
      if (state.dirty !== prev.dirty && Object.keys(state.dirty).length > 0) schedule(350);
    });
    const onOnline = () => {
      attempt.current = 0;
      void flush();
    };
    const onOffline = () => useExam.getState().setSyncStatus("offline");
    const onHide = () => {
      if (document.visibilityState === "hidden") void flush(true);
    };
    const onPageHide = () => void flush(true);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", onPageHide);
    const interval = window.setInterval(() => {
      if (Object.keys(useExam.getState().dirty).length && !inFlight.current) void flush();
    }, 5000);
    // Anything left from a previous page load is sent right away.
    void flush();
    return () => {
      unsub();
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", onPageHide);
      window.clearInterval(interval);
      window.clearTimeout(timer.current);
    };
  }, [flush, schedule]);

  return { flush };
}
