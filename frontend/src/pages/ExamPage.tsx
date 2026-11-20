import { AnimatePresence, m } from "framer-motion";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { examApi } from "../api/exam";
import { ApiError } from "../api/http";
import type { AttemptState, QuestionItem } from "../api/types";
import { Background } from "../components/Background";
import { Icon } from "../components/Icon";
import { Loader } from "../components/Loader";
import { Modal } from "../components/Modal";
import { toast } from "../components/Toast";
import { useAnswerSync } from "../lib/useAnswerSync";
import { serverNow, useExam, type SyncStatus } from "../store/exam";
import "./exam.css";

const LETTERS = "ABCDEF";

export default function ExamPage() {
  const navigate = useNavigate();
  const attemptId = useExam((s) => s.attemptId);
  const token = useExam((s) => s.token);
  const snapshot = useExam((s) => s.snapshot);
  const finished = useExam((s) => s.finished);
  const [refreshing, setRefreshing] = useState(false);
  const [finishing, setFinishing] = useState<null | "manual" | "timeout">(null);
  const [waitingNetwork, setWaitingNetwork] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [startingStage, setStartingStage] = useState(false);
  const finishingRef = useRef(false);

  const handleState = useCallback(
    (state: AttemptState) => {
      const st = useExam.getState();
      if (state.status === "completed") {
        st.complete(state);
        navigate("/done", { replace: true });
      } else if (state.status === "annulled") {
        st.clearSession();
        toast.error("Test administrator tomonidan bekor qilingan.");
        navigate("/", { replace: true });
      } else {
        st.applyServerState(state);
      }
    },
    [navigate],
  );

  const refresh = useCallback(async () => {
    const st = useExam.getState();
    if (!st.attemptId || !st.token) return;
    setRefreshing(true);
    try {
      handleState(await examApi.state(st.attemptId, st.token));
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 404) {
        st.clearSession();
        toast.error("Test topilmadi. Qaytadan boshlang.");
        navigate("/", { replace: true });
      }
      // Network problems: keep working from the locally saved copy.
    } finally {
      setRefreshing(false);
    }
  }, [handleState, navigate]);

  const { flush } = useAnswerSync({
    onConflict: () => void refresh(),
    onLost: () => {
      useExam.getState().clearSession();
      toast.error("Test topilmadi yoki bekor qilingan.");
      navigate("/", { replace: true });
    },
  });

  useEffect(() => {
    if (!attemptId) {
      navigate(finished ? "/done" : "/", { replace: true });
      return;
    }
    void refresh();
  }, []);

  const currentStage = snapshot?.stages.find((s) => s.number === snapshot.current_stage);

  const finishStage = useCallback(
    async (reason: "manual" | "timeout") => {
      const st = useExam.getState();
      if (finishingRef.current || !st.attemptId || !st.token) return;
      finishingRef.current = true;
      setFinishing(reason);
      setConfirmOpen(false);
      const stageNo = st.stage;
      const send = async (): Promise<boolean> => {
        const s = useExam.getState();
        const answers = Object.keys(s.dirty).map((k) => ({ id: Number(k), option: s.answers[k] ?? null }));
        try {
          const state = await examApi.finishStage(s.attemptId!, s.token!, stageNo, answers);
          setWaitingNetwork(false);
          handleState(state);
          return true;
        } catch (err) {
          const e = err as ApiError;
          if (e.status === 409 || e.status === 404) {
            await refresh();
            return true;
          }
          setWaitingNetwork(true);
          return false;
        }
      };
      let ok = await send();
      let delay = 2000;
      while (!ok) {
        await new Promise((r) => setTimeout(r, delay));
        delay = Math.min(delay * 1.5, 10000);
        ok = await send();
      }
      finishingRef.current = false;
      setFinishing(null);
    },
    [handleState, refresh],
  );

  const startNextStage = async () => {
    if (!attemptId || !token || !currentStage) return;
    setStartingStage(true);
    try {
      handleState(await examApi.startStage(attemptId, token, currentStage.number));
    } catch (err) {
      toast.error((err as ApiError).message);
    } finally {
      setStartingStage(false);
    }
  };

  // Warn before closing the tab only if something is not yet on the server.
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (Object.keys(useExam.getState().dirty).length) {
        void flush(true);
        e.preventDefault();
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [flush]);

  if (!snapshot || !currentStage) {
    return (
      <div className="page-center">
        <Background calm />
        <Loader label={refreshing ? "Test yuklanmoqda..." : "Kutilmoqda..."} />
      </div>
    );
  }

  if (!currentStage.started_at) {
    const prev = snapshot.stages.find((s) => s.number === currentStage.number - 1);
    return (
      <main className="page-center">
        <Background />
        <m.div
          className="glass stage-break"
          initial={{ opacity: 0, y: 30, rotateX: 10 }}
          animate={{ opacity: 1, y: 0, rotateX: 0 }}
          transition={{ type: "spring", stiffness: 200, damping: 22 }}
        >
          <div className="success-orb small">
            <Icon name="check" size={34} />
          </div>
          <h1>{prev ? `${prev.title} yakunlandi` : "Tayyormisiz?"}</h1>
          <p className="muted">
            {prev?.finish_reason === "timeout"
              ? "Ajratilgan vaqt tugadi, javoblaringiz saqlandi."
              : "Javoblaringiz muvaffaqiyatli saqlandi."}
          </p>
          <div className="next-stage">
            <span className="badge info">Keyingi bosqich</span>
            <h2>{currentStage.title}</h2>
            <div className="next-stats">
              <div>
                <strong>{currentStage.question_count}</strong>
                <span>savol</span>
              </div>
              <div>
                <strong>{Math.round(currentStage.duration_seconds / 60)}</strong>
                <span>daqiqa</span>
              </div>
            </div>
          </div>
          <button className="btn btn-primary btn-lg btn-block" onClick={startNextStage} disabled={startingStage}>
            {startingStage ? <span className="spinner" /> : <Icon name="right" size={20} />}
            {currentStage.title}ni boshlash
          </button>
        </m.div>
      </main>
    );
  }

  return (
    <ExamView
      key={`${snapshot.id}-${currentStage.number}`}
      snapshot={snapshot}
      stageTitle={currentStage.title}
      deadline={currentStage.deadline!}
      totalStages={snapshot.stages.length}
      onFinishRequest={() => setConfirmOpen(true)}
      onTimeout={() => {
        toast.warning("Vaqt tugadi. Bosqich avtomatik yakunlanmoqda.");
        void finishStage("timeout");
      }}
      finishing={finishing}
      waitingNetwork={waitingNetwork}
      confirmOpen={confirmOpen}
      closeConfirm={() => setConfirmOpen(false)}
      confirmFinish={() => void finishStage("manual")}
    />
  );
}

interface ViewProps {
  snapshot: AttemptState;
  stageTitle: string;
  deadline: string;
  totalStages: number;
  onFinishRequest: () => void;
  onTimeout: () => void;
  finishing: null | "manual" | "timeout";
  waitingNetwork: boolean;
  confirmOpen: boolean;
  closeConfirm: () => void;
  confirmFinish: () => void;
}

function ExamView(props: ViewProps) {
  const { snapshot, stageTitle, deadline } = props;
  const questions = snapshot.questions;
  const answers = useExam((s) => s.answers);
  const index = useExam((s) => s.index);
  const setIndex = useExam((s) => s.setIndex);
  const select = useExam((s) => s.select);
  const syncStatus = useExam((s) => s.syncStatus);
  const [direction, setDirection] = useState(1);

  const total = questions.length;
  const answered = useMemo(() => questions.filter((q) => answers[String(q.id)]).length, [questions, answers]);
  const unanswered = useMemo(
    () => questions.map((q, i) => (answers[String(q.id)] ? -1 : i)).filter((i) => i >= 0),
    [questions, answers],
  );
  const question = questions[Math.min(index, total - 1)];

  const go = useCallback(
    (i: number) => {
      if (i < 0 || i >= total) return;
      setDirection(i > useExam.getState().index ? 1 : -1);
      setIndex(i);
    },
    [setIndex, total],
  );

  const choose = useCallback(
    (optionId: string) => {
      const key = String(question.id);
      const current = useExam.getState().answers[key];
      select(question.id, current === optionId ? null : optionId);
    },
    [question, select],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (props.confirmOpen || e.target instanceof HTMLInputElement || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "ArrowRight") go(useExam.getState().index + 1);
      else if (e.key === "ArrowLeft") go(useExam.getState().index - 1);
      else {
        const k = e.key.toUpperCase();
        const idx = /^[1-6]$/.test(k) ? Number(k) - 1 : LETTERS.indexOf(k);
        if (idx >= 0 && k.length === 1 && question.options[idx]) choose(question.options[idx].id);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, choose, question, props.confirmOpen]);

  const selected = answers[String(question.id)] ?? null;
  const progress = total ? (answered / total) * 100 : 0;

  return (
    <div className="exam">
      <Background calm />
      <header className="exam-top">
        <div className="exam-title">
          <span className="badge">{snapshot.subject}</span>
          <h1>
            {stageTitle}
            <small>
              {" "}
              · {snapshot.current_stage}/{props.totalStages}
            </small>
          </h1>
        </div>
        <div className="exam-tools">
          <SyncBadge status={syncStatus} />
          <Timer deadline={deadline} onExpire={props.onTimeout} />
        </div>
      </header>

      <div className="progress" aria-label={`${answered} / ${total} javob berildi`}>
        <m.div className="progress-bar" animate={{ width: `${progress}%` }} transition={{ type: "spring", stiffness: 120, damping: 20 }} />
      </div>

      <div className="exam-body">
        <section className="question-area">
          <div className="question-meta">
            <span>
              Savol <strong>{index + 1}</strong> / {total}
            </span>
            <span className="muted">
              Javob berildi: {answered}/{total}
            </span>
          </div>
          <div className="question-stage">
            <AnimatePresence mode="wait" custom={direction} initial={false}>
              <m.article
                key={question.id}
                className="question-card glass"
                custom={direction}
                initial={{ opacity: 0, x: direction * 50, rotateY: direction * 8 }}
                animate={{ opacity: 1, x: 0, rotateY: 0 }}
                exit={{ opacity: 0, x: direction * -50, rotateY: direction * -8 }}
                transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
              >
                <QuestionText text={question.text} />
                <div className="options" role="radiogroup" aria-label="Javob variantlari">
                  {question.options.map((o, i) => (
                    <OptionButton
                      key={o.id}
                      letter={LETTERS[i]}
                      text={o.text}
                      active={selected === o.id}
                      onClick={() => choose(o.id)}
                    />
                  ))}
                </div>
              </m.article>
            </AnimatePresence>
          </div>
          <div className="question-nav-buttons">
            <button className="btn" onClick={() => go(index - 1)} disabled={index === 0}>
              <Icon name="left" size={18} /> <span className="hide-sm">Oldingi</span>
            </button>
            {index < total - 1 ? (
              <button className="btn btn-primary" onClick={() => go(index + 1)}>
                <span className="hide-sm">Keyingi</span> <Icon name="right" size={18} />
              </button>
            ) : (
              <button className="btn btn-primary finish-last" onClick={props.onFinishRequest}>
                Bosqichni yakunlash <Icon name="check" size={18} />
              </button>
            )}
          </div>
          <nav className="q-strip glass" aria-label="Savollar">
            <QuestionGrid questions={questions} answers={answers} current={index} onPick={go} />
          </nav>
        </section>

      </div>

      <Modal
        open={props.confirmOpen}
        onClose={props.closeConfirm}
        title={`${stageTitle}ni yakunlaysizmi?`}
        footer={
          <>
            <button className="btn" onClick={props.closeConfirm}>
              Davom etish
            </button>
            <button className="btn btn-primary" onClick={props.confirmFinish}>
              <Icon name="check" size={18} /> Ha, yakunlash
            </button>
          </>
        }
      >
        <div className="confirm-stats">
          <div>
            <strong className="ok">{answered}</strong>
            <span>javob berilgan</span>
          </div>
          <div>
            <strong className={unanswered.length ? "warn" : "ok"}>{unanswered.length}</strong>
            <span>bo'sh qolgan</span>
          </div>
        </div>
        {unanswered.length > 0 && (
          <>
            <p className="muted" style={{ margin: "14px 0 8px" }}>
              Bo'sh qolgan savollar:
            </p>
            <div className="chips">
              {unanswered.slice(0, 40).map((i) => (
                <button
                  key={i}
                  className="chip"
                  onClick={() => {
                    props.closeConfirm();
                    go(i);
                  }}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          </>
        )}
      </Modal>

      <AnimatePresence>
        {props.finishing && (
          <m.div className="finishing-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="glass finishing-card">
              {props.waitingNetwork ? (
                <>
                  <Icon name="wifiOff" size={36} />
                  <h3>Internet aloqasi yo'q</h3>
                  <p className="muted">
                    Javoblaringiz qurilmada saqlangan. Ulanish tiklanishi bilan avtomatik yuboriladi — sahifani
                    yopmang.
                  </p>
                  <span className="spinner" />
                </>
              ) : (
                <>
                  <Loader label="Javoblar yuborilmoqda..." />
                </>
              )}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const OptionButton = memo(function OptionButton({
  letter,
  text,
  active,
  onClick,
}: {
  letter: string;
  text: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" role="radio" aria-checked={active} className={`option${active ? " active" : ""}`} onClick={onClick}>
      <span className="option-letter">{letter}</span>
      <span className="option-text" dir="auto">
        {text}
      </span>
      <span className="option-check" aria-hidden="true">
        <Icon name="check" size={16} />
      </span>
    </button>
  );
});

const QuestionGrid = memo(function QuestionGrid({
  questions,
  answers,
  current,
  onPick,
}: {
  questions: QuestionItem[];
  answers: Record<string, string | null>;
  current: number;
  onPick: (i: number) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  // Keep the current question's number visible in the scrolling row (without scrolling the page).
  useEffect(() => {
    const row = ref.current;
    const cell = row?.children[current] as HTMLElement | undefined;
    if (!row || !cell) return;
    // Measure against the row itself (offsetLeft would be relative to an outer element).
    const offset = cell.getBoundingClientRect().left - row.getBoundingClientRect().left + row.scrollLeft;
    const left = offset - (row.clientWidth - cell.offsetWidth) / 2;
    row.scrollTo({ left: Math.max(0, left), behavior: "smooth" });
  }, [current]);
  return (
    <div className="q-grid" ref={ref}>
      {questions.map((q, i) => (
        <button
          key={q.id}
          className={`q-cell${answers[String(q.id)] ? " answered" : ""}${i === current ? " current" : ""}`}
          onClick={() => onPick(i)}
          aria-label={`${i + 1}-savol`}
        >
          {i + 1}
        </button>
      ))}
    </div>
  );
});

function SyncBadge({ status }: { status: SyncStatus }) {
  const pending = useExam((s) => Object.keys(s.dirty).length);
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  if (!online || status === "offline") {
    return (
      <span className="sync offline" title="Javoblar qurilmada saqlanmoqda">
        <Icon name="wifiOff" size={16} /> <span className="hide-sm">Oflayn</span>
      </span>
    );
  }
  if (pending > 0 || status === "saving") {
    return (
      <span className="sync saving">
        <span className="spinner tiny-spinner" /> <span className="hide-sm">Saqlanmoqda</span>
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="sync offline">
        <Icon name="refresh" size={16} /> <span className="hide-sm">Qayta urinilmoqda</span>
      </span>
    );
  }
  return (
    <span className="sync saved">
      <Icon name="cloud" size={16} /> <span className="hide-sm">Saqlandi</span>
    </span>
  );
}

const Timer = memo(function Timer({ deadline, onExpire }: { deadline: string; onExpire: () => void }) {
  const offset = useExam((s) => s.clockOffset);
  const end = useMemo(() => new Date(deadline).getTime(), [deadline]);
  const calc = useCallback(() => Math.max(0, Math.round((end - serverNow(offset)) / 1000)), [end, offset]);
  const [left, setLeft] = useState(calc);
  const expired = useRef(false);
  const warned = useRef<Record<number, boolean>>({});
  const expireRef = useRef(onExpire);
  expireRef.current = onExpire;

  useEffect(() => {
    const tick = () => {
      const value = calc();
      setLeft(value);
      for (const mark of [300, 60]) {
        if (value <= mark && value > mark - 5 && !warned.current[mark]) {
          warned.current[mark] = true;
          toast.warning(mark === 300 ? "5 daqiqa qoldi!" : "1 daqiqa qoldi!");
        }
      }
      if (value <= 0 && !expired.current) {
        expired.current = true;
        expireRef.current();
      }
    };
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [calc]);

  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  const level = left <= 60 ? "danger" : left <= 300 ? "warning" : "";
  return (
    <span className={`timer ${level}`} role="timer" aria-live="off">
      <Icon name="clock" size={18} />
      <span className="timer-digits">
        {mm}:{ss}
      </span>
    </span>
  );
});

const CODE_HINT = /[{};]|=>|console\.|\bdef |print\(|\bSELECT\b|<\/?[a-z]+>|^\s{2,}\S/m;

/** First line is the question; following lines (code, a reading passage) keep their layout. */
function QuestionText({ text }: { text: string }) {
  const [head, ...rest] = text.split("\n");
  const body = rest.join("\n");
  return (
    <>
      <h2 className="question-text" dir="auto">
        {head}
      </h2>
      {body.trim() && (
        <pre className={`question-body${CODE_HINT.test(body) ? " code" : ""}`} dir="auto">
          {body}
        </pre>
      )}
    </>
  );
}
