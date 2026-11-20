import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import type { ApiError } from "../../api/http";
import { Icon } from "../../components/Icon";
import { Loader } from "../../components/Loader";
import { toast } from "../../components/Toast";
import { adminApi, difficultyLabel, fmt, statusLabel, type AttemptDetail } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";

const LETTERS = "ABCDEF";
type FilterKey = "all" | "correct" | "wrong" | "blank";

const reasonLabel: Record<string, string> = {
  submitted: "Foydalanuvchi yakunladi",
  timeout: "Vaqt tugadi",
  abandoned: "Boshlanmadi",
};

function pctClass(p: number) {
  return p >= 80 ? "good" : p >= 50 ? "mid" : "low";
}

export default function ResultDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<AttemptDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [stage, setStage] = useState<number | 0>(0);
  const [confirm, setConfirm] = useState<null | "annul" | "delete">(null);

  const load = () =>
    adminApi
      .attempt(id)
      .then(setData)
      .catch((e: ApiError) => setError(e.message));
  useEffect(() => {
    void load();
  }, [id]);

  const answers = useMemo(() => {
    if (!data) return [];
    return data.answers.filter(
      (a) => (stage === 0 || a.stage === stage) && (filter === "all" || a.result === filter),
    );
  }, [data, filter, stage]);

  if (error) return <div className="alert">{error}</div>;
  if (!data) return <Loader />;

  const counts = {
    all: data.answers.filter((a) => stage === 0 || a.stage === stage).length,
    correct: data.answers.filter((a) => (stage === 0 || a.stage === stage) && a.result === "correct").length,
    wrong: data.answers.filter((a) => (stage === 0 || a.stage === stage) && a.result === "wrong").length,
    blank: data.answers.filter((a) => (stage === 0 || a.stage === stage) && a.result === "blank").length,
  };
  const completed = data.status === "completed";

  const toggleRetake = async () => {
    try {
      const r = await adminApi.allowRetake(data.id, !data.retake_allowed);
      setData({ ...data, retake_allowed: r.retake_allowed });
      toast.success(r.retake_allowed ? "Qayta topshirishga ruxsat berildi" : "Ruxsat bekor qilindi");
    } catch (e) {
      toast.error((e as ApiError).message);
    }
  };

  return (
    <div className="admin-page">
      <div className="page-head">
        <div>
          <Link to="/admin/results" className="back-link">
            <Icon name="left" size={16} /> Natijalar
          </Link>
          <h1>
            {data.last_name} {data.first_name}
          </h1>
          <p className="muted">
            {data.branch_name} · {data.subject_name}
          </p>
        </div>
        <div className="head-actions">
          {completed && (
            <button className="btn" onClick={toggleRetake}>
              <Icon name="refresh" size={18} />
              {data.retake_allowed ? "Qayta topshirish ruxsatini bekor qilish" : "Qayta topshirishga ruxsat"}
            </button>
          )}
          {data.status !== "annulled" && (
            <button className="btn btn-danger" onClick={() => setConfirm("annul")}>
              <Icon name="x" size={18} /> Bekor qilish
            </button>
          )}
          <button className="btn btn-danger" onClick={() => setConfirm("delete")}>
            <Icon name="trash" size={18} />
          </button>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card glass">
          <span className="stat-icon"><Icon name="chart" size={20} /></span>
          <div>
            <span className="stat-label">Umumiy ball</span>
            <strong className="stat-value">{completed ? `${data.total_score} / ${data.max_score}` : "—"}</strong>
            {completed && <span className={`pct ${pctClass(data.percent)}`}>{data.percent}%</span>}
          </div>
        </div>
        <div className="stat-card glass">
          <span className="stat-icon"><Icon name="check" size={20} /></span>
          <div>
            <span className="stat-label">To'g'ri / Noto'g'ri / Bo'sh</span>
            <strong className="stat-value">
              {completed ? `${data.correct_count} / ${data.wrong_count} / ${data.blank_count}` : "—"}
            </strong>
          </div>
        </div>
        <div className="stat-card glass">
          <span className="stat-icon"><Icon name="timer" size={20} /></span>
          <div>
            <span className="stat-label">Sarflangan vaqt</span>
            <strong className="stat-value">{fmt.duration(data.duration_seconds)}</strong>
          </div>
        </div>
        <div className="stat-card glass">
          <span className="stat-icon"><Icon name="clock" size={20} /></span>
          <div>
            <span className="stat-label">Boshlangan → Tugagan</span>
            <strong className="stat-value small">{fmt.date(data.started_at)}</strong>
            <span className="tiny">{fmt.date(data.finished_at)}</span>
          </div>
        </div>
      </div>

      <div className="stage-cards">
        {data.stages.map((s) => (
          <div key={s.number} className="glass panel">
            <div className="panel-row">
              <h3>
                {s.number}. {s.title}
                {s.finished_at && s.max_score > 0 && (
                  <span className={`pct stage-pct ${pctClass(Math.round((s.score * 1000) / s.max_score) / 10)}`}>
                    {Math.round((s.score * 1000) / s.max_score) / 10}%
                  </span>
                )}
              </h3>
              <span className={`badge ${s.finished_at ? "success" : "info"}`}>
                {s.finished_at ? reasonLabel[s.finish_reason] ?? "Yakunlangan" : s.started_at ? "Jarayonda" : "Boshlanmagan"}
              </span>
            </div>
            <div className="mini-stats">
              <div><strong>{s.finished_at ? `${s.score}/${s.max_score}` : "—"}</strong><span>ball</span></div>
              <div><strong className="ok">{s.correct_count}</strong><span>to'g'ri</span></div>
              <div><strong className="bad">{s.wrong_count}</strong><span>noto'g'ri</span></div>
              <div><strong>{s.blank_count}</strong><span>bo'sh</span></div>
            </div>
            <p className="tiny">
              {fmt.date(s.started_at)} → {fmt.date(s.finished_at)} · limit {Math.round(s.duration_seconds / 60)} daqiqa
            </p>
          </div>
        ))}
      </div>

      <div className="tabs-row">
        <div className="tabs">
          {([0, ...data.stages.map((s) => s.number)] as number[]).map((n) => (
            <button key={n} className={`tab${stage === n ? " active" : ""}`} onClick={() => setStage(n)}>
              {n === 0 ? "Barcha bosqichlar" : `${n}-bosqich`}
            </button>
          ))}
        </div>
        <div className="tabs">
          {(["all", "correct", "wrong", "blank"] as FilterKey[]).map((f) => (
            <button key={f} className={`tab${filter === f ? " active" : ""}`} onClick={() => setFilter(f)}>
              {{ all: "Hammasi", correct: "To'g'ri", wrong: "Noto'g'ri", blank: "Bo'sh" }[f]} ({counts[f]})
            </button>
          ))}
        </div>
      </div>

      {!completed && data.status === "active" && (
        <div className="alert info" style={{ marginBottom: 12 }}>
          Test hali yakunlanmagan: to'g'ri/noto'g'ri belgisi bosqich yakunlangach qo'yiladi.
        </div>
      )}

      <div className="answer-list">
        {answers.map((a) => (
          <div key={a.id} className={`answer-item glass ${a.result}`}>
            <div className="answer-head">
              <span className="badge">
                {a.stage}-bosqich · {a.position}-savol
              </span>
              <span className="tiny">{difficultyLabel[a.difficulty] ?? ""} · {a.points} ball</span>
              <span className={`badge ${a.result === "correct" ? "success" : a.result === "wrong" ? "danger" : a.result === "blank" ? "warning" : ""}`}>
                {{ correct: "To'g'ri", wrong: "Noto'g'ri", blank: "Bo'sh qoldirilgan", pending: "Javob berilgan" }[a.result]}
              </span>
            </div>
            <p className="answer-q" dir="auto">{a.question_text}</p>
            <ul className="answer-options">
              {a.options.map((o, i) => {
                const isCorrect = o.id === a.correct_option;
                const isSelected = o.id === a.selected_option;
                return (
                  <li key={o.id} className={`${isCorrect ? "correct" : ""} ${isSelected && !isCorrect ? "wrong" : ""}`} dir="auto">
                    <b>{LETTERS[i]}.</b> {o.text}
                    {isSelected && <span className="pill">tanlangan</span>}
                    {isCorrect && <span className="pill ok">to'g'ri javob</span>}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        {answers.length === 0 && <p className="muted empty">Bu filtr bo'yicha savollar yo'q.</p>}
      </div>

      <p className="tiny" style={{ marginTop: 16 }}>
        Holat: {statusLabel[data.status]} · IP: {data.ip_address ?? "—"} · {data.user_agent}
      </p>

      <ConfirmDialog
        open={confirm === "annul"}
        title="Natijani bekor qilasizmi?"
        confirmLabel="Bekor qilish"
        danger
        onClose={() => setConfirm(null)}
        onConfirm={async () => {
          try {
            await adminApi.annul(data.id);
            toast.success("Natija bekor qilindi. Foydalanuvchi testni qaytadan boshlashi mumkin.");
            setConfirm(null);
            void load();
          } catch (e) {
            toast.error((e as ApiError).message);
          }
        }}
      >
        <p className="muted">Natija «bekor qilingan» deb belgilanadi va reytingga kirmaydi. Foydalanuvchi qayta test topshira oladi.</p>
      </ConfirmDialog>
      <ConfirmDialog
        open={confirm === "delete"}
        title="Natijani butunlay o'chirasizmi?"
        confirmLabel="O'chirish"
        danger
        onClose={() => setConfirm(null)}
        onConfirm={async () => {
          try {
            await adminApi.deleteAttempt(data.id);
            toast.success("O'chirildi");
            navigate("/admin/results");
          } catch (e) {
            toast.error((e as ApiError).message);
          }
        }}
      >
        <p className="muted">Bu amalni qaytarib bo'lmaydi. Barcha javoblar ham o'chiriladi.</p>
      </ConfirmDialog>
    </div>
  );
}
