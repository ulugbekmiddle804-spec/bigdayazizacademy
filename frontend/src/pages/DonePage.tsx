import { m } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Background } from "../components/Background";
import { Icon } from "../components/Icon";
import { PageTransition } from "../components/PageTransition";
import { useExam } from "../store/exam";
import "./exam.css";
import "./done.css";

const LETTERS = "ABCDEF";

export default function DonePage() {
  const navigate = useNavigate();
  const finished = useExam((s) => s.finished);
  const reset = useExam((s) => s.reset);
  const [showReview, setShowReview] = useState(false);

  useEffect(() => {
    if (!finished) navigate("/", { replace: true });
  }, [finished, navigate]);

  const sparks = useMemo(
    () => Array.from({ length: 14 }, (_, i) => ({ angle: (i / 14) * 360, delay: (i % 4) * 0.05, dist: 70 + (i % 3) * 22 })),
    [],
  );

  if (!finished) return null;
  const r = finished.result;

  return (
    <PageTransition className="page-center done-page">
      <Background />
      <div className="glass done-card">
        <div className="done-burst" aria-hidden="true">
          {sparks.map((s, i) => (
            <m.span
              key={i}
              className="spark"
              initial={{ opacity: 0, x: 0, y: 0, scale: 0.4 }}
              animate={{
                opacity: [0, 1, 0],
                x: Math.cos((s.angle * Math.PI) / 180) * s.dist,
                y: Math.sin((s.angle * Math.PI) / 180) * s.dist,
                scale: 1,
              }}
              transition={{ duration: 1.1, delay: 0.35 + s.delay, ease: "easeOut" }}
            />
          ))}
          <m.div
            className="success-orb"
            initial={{ scale: 0, rotate: -90 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 220, damping: 14, delay: 0.1 }}
          >
            <svg viewBox="0 0 24 24" width="46" height="46" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <m.path
                d="M5 12.5l4.5 4.5L19 7.5"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.5, delay: 0.45 }}
              />
            </svg>
          </m.div>
        </div>

        <m.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          <h1>Test muvaffaqiyatli topshirildi!</h1>
          <p className="muted done-sub">
            Rahmat, <strong>{finished.name}</strong>!
          </p>
        </m.div>

        {r ? (
          <m.div className="score-box" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.65 }}>
            <div className="score-main">
              <span className="gradient-text">{r.total_score}</span>
              <small>/ {r.max_score} ball</small>
            </div>
            <div className="score-stats">
              <span className="badge success">To'g'ri: {r.correct}</span>
              <span className="badge danger">Noto'g'ri: {r.wrong}</span>
              <span className="badge">Bo'sh: {r.blank}</span>
              <span className="badge info">{r.percent}%</span>
            </div>
            <div className="score-stages">
              {r.stages.map((s) => (
                <div key={s.number}>
                  <strong>{s.title}</strong>
                  <span>
                    {s.score}/{s.max_score} ball · {s.correct}/{s.total} to'g'ri
                  </span>
                </div>
              ))}
            </div>
          </m.div>
        ) : (
          <m.p className="alert info" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.65 }}>
            Natijalar administrator tomonidan ko'rib chiqiladi va e'lon qilinadi.
          </m.p>
        )}

        <div className="done-actions">
          {finished.review && (
            <button className="btn" onClick={() => setShowReview((v) => !v)}>
              <Icon name="eye" size={18} /> {showReview ? "Yashirish" : "Javoblarni ko'rish"}
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={() => {
              reset();
              navigate("/");
            }}
          >
            <Icon name="home" size={18} /> Bosh sahifa
          </button>
        </div>

        {showReview && finished.review && (
          <div className="review-list">
            {finished.review.map((q) => (
              <div key={`${q.stage}-${q.position}`} className="review-item">
                <div className="review-head">
                  <span className="badge">
                    {q.stage}-bosqich · {q.position}
                  </span>
                  {q.selected === null ? (
                    <span className="badge warning">Bo'sh</span>
                  ) : q.selected === q.correct ? (
                    <span className="badge success">To'g'ri</span>
                  ) : (
                    <span className="badge danger">Noto'g'ri</span>
                  )}
                </div>
                <p className="review-q" dir="auto">{q.text}</p>
                <ul>
                  {q.options.map((o, i) => (
                    <li
                      key={o.id}
                      className={o.id === q.correct ? "correct" : o.id === q.selected ? "wrong" : ""}
                      dir="auto"
                    >
                      <b>{LETTERS[i]}.</b> {o.text}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageTransition>
  );
}
