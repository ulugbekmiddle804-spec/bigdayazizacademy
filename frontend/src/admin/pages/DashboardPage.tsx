import { m } from "framer-motion";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import type { ApiError } from "../../api/http";
import { Icon, type IconName } from "../../components/Icon";
import { Loader } from "../../components/Loader";
import { adminApi, fmt, statusLabel, type Dashboard } from "../api";

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = () =>
      adminApi
        .dashboard()
        .then(setData)
        .catch((e: ApiError) => setError(e.message));
    load();
    const id = window.setInterval(load, 30000); // live "active now" counter
    return () => window.clearInterval(id);
  }, []);

  if (error) return <div className="alert">{error}</div>;
  if (!data) return <Loader />;

  const stats: { label: string; value: string | number; icon: IconName; hint?: string }[] = [
    { label: "Jami topshirishlar", value: data.attempts_total, icon: "list" },
    { label: "Yakunlangan", value: data.completed_total, icon: "check", hint: `Bugun: ${data.today}` },
    { label: "Hozir test topshirmoqda", value: data.active_now, icon: "timer" },
    { label: "O'rtacha natija", value: data.avg_percent !== null ? `${data.avg_percent}%` : "—", icon: "chart",
      hint: `O'rtacha vaqt: ${fmt.duration(data.avg_duration)}` },
    { label: "Faol savollar", value: data.questions_total, icon: "book" },
    { label: "Filiallar", value: data.branches_total, icon: "building" },
  ];
  const maxDaily = Math.max(1, ...data.daily.map((d) => d.count));

  return (
    <div className="admin-page">
      <div className="page-head">
        <div>
          <h1>Boshqaruv paneli</h1>
          <p className="muted">Platforma bo'yicha umumiy ko'rsatkichlar</p>
        </div>
        <Link to="/admin/results" className="btn btn-primary">
          <Icon name="list" size={18} /> Barcha natijalar
        </Link>
      </div>

      {data.warnings.length > 0 && (
        <div className="alert warning" style={{ marginBottom: 18 }}>
          <strong>Savollar yetarli emas:</strong>{" "}
          {data.warnings.map((w) => `${w.subject} (${w.stage}-bosqich: ${w.available}/${w.required})`).join(", ")}.
          Bunday holatda test mavjud savollar soni bilan o'tkaziladi.
        </div>
      )}

      <div className="stat-grid">
        {stats.map((s, i) => (
          <m.div
            key={s.label}
            className="stat-card glass"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <span className="stat-icon">
              <Icon name={s.icon} size={20} />
            </span>
            <div>
              <span className="stat-label">{s.label}</span>
              <strong className="stat-value">{s.value}</strong>
              {s.hint && <span className="tiny">{s.hint}</span>}
            </div>
          </m.div>
        ))}
      </div>

      <div className="dash-grid">
        <section className="glass panel">
          <h3>So'nggi 14 kun</h3>
          <div className="bars" role="img" aria-label="Kunlik yakunlangan testlar">
            {data.daily.map((d) => (
              <div key={d.date} className="bar-col" title={`${d.date}: ${d.count}`}>
                <span className="bar-val">{d.count || ""}</span>
                <m.span
                  className="bar"
                  initial={{ height: 0 }}
                  animate={{ height: `${(d.count / maxDaily) * 100}%` }}
                  transition={{ type: "spring", stiffness: 120, damping: 18 }}
                />
                <span className="bar-label">{d.date.slice(8)}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="glass panel">
          <h3>Fanlar bo'yicha</h3>
          {data.by_subject.length === 0 && <p className="muted">Hali natijalar yo'q.</p>}
          <div className="hbars">
            {data.by_subject.map((s) => (
              <div key={s.subject} className="hbar">
                <div className="hbar-head">
                  <span>{s.subject}</span>
                  <span className="muted">
                    {s.count} ta · {s.avg_percent}%
                  </span>
                </div>
                <div className="hbar-track">
                  <m.div className="hbar-fill" initial={{ width: 0 }} animate={{ width: `${s.avg_percent}%` }} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="glass panel">
          <h3>Filiallar bo'yicha</h3>
          {data.by_branch.length === 0 && <p className="muted">Hali natijalar yo'q.</p>}
          <table className="table compact">
            <tbody>
              {data.by_branch.map((b) => (
                <tr key={b.branch}>
                  <td>{b.branch}</td>
                  <td className="num">{b.count} ta</td>
                  <td className="num muted">o'rt. {b.avg} ball</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="glass panel">
          <h3>So'nggi topshirishlar</h3>
          <table className="table compact">
            <tbody>
              {data.recent.map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/admin/results/${r.id}`}>
                      {r.last_name} {r.first_name}
                    </Link>
                    <div className="tiny">{r.subject_name}</div>
                  </td>
                  <td>
                    <span className={`badge ${r.status === "completed" ? "success" : r.status === "active" ? "info" : ""}`}>
                      {statusLabel[r.status]}
                    </span>
                  </td>
                  <td className="num">{r.status === "completed" ? `${r.total_score}/${r.max_score}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}
