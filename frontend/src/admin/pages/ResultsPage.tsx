import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { downloadFile, type ApiError } from "../../api/http";
import { Icon } from "../../components/Icon";
import { Loader } from "../../components/Loader";
import { toast } from "../../components/Toast";
import { adminApi, fmt, statusLabel, type AttemptRow, type Branch, type Paginated, type Subject } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Pagination } from "../components/Pagination";
import { useDebounced } from "../components/useDebounced";

const CONFIRM_WORD = "O'CHIRISH";

function pctClass(p: number) {
  return p >= 80 ? "good" : p >= 50 ? "mid" : "low";
}

function Pct({ value, sub }: { value: number | null; sub?: string }) {
  if (value === null) return <span className="muted">—</span>;
  return (
    <span className="pct-cell">
      <b className={`pct ${pctClass(value)}`}>{value}%</b>
      {sub && <span className="tiny muted">{sub}</span>}
    </span>
  );
}

const SORTS: { value: string; label: string }[] = [
  { value: "-started_at", label: "Eng yangi" },
  { value: "started_at", label: "Eng eski" },
  { value: "-total_score", label: "Ball: yuqoridan" },
  { value: "total_score", label: "Ball: pastdan" },
  { value: "duration", label: "Vaqt: tezroq" },
  { value: "-duration", label: "Vaqt: sekinroq" },
  { value: "last_name", label: "Familiya A–Z" },
];

export default function ResultsPage() {
  const [params, setParams] = useSearchParams();
  const [branches, setBranches] = useState<Branch[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [data, setData] = useState<Paginated<AttemptRow> | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirm, setConfirm] = useState<null | "selected" | "all" | { id: string; name: string }>(null);
  const [confirmText, setConfirmText] = useState("");
  const [reload, setReload] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [firstName, setFirstName] = useState(params.get("first_name") ?? "");
  const [lastName, setLastName] = useState(params.get("last_name") ?? "");
  const dFirst = useDebounced(firstName, 350);
  const dLast = useDebounced(lastName, 350);

  const get = (k: string) => params.get(k) ?? "";
  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    if (k !== "page") next.delete("page");
    setParams(next, { replace: true });
  };

  useEffect(() => {
    adminApi.branches().then(setBranches).catch(() => undefined);
    adminApi.subjects().then(setSubjects).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (dFirst !== get("first_name")) set("first_name", dFirst);
  }, [dFirst]);
  useEffect(() => {
    if (dLast !== get("last_name")) set("last_name", dLast);
  }, [dLast]);

  const query = useMemo(() => {
    const q: Record<string, string> = {};
    for (const k of ["first_name", "last_name", "branch", "subject", "status", "date_from", "date_to", "ordering", "page"]) {
      const v = params.get(k);
      if (v) q[k] = v;
    }
    return q;
  }, [params]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    adminApi
      .attempts(query)
      .then((d) => !cancelled && setData(d))
      .catch((e: ApiError) => toast.error(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [query, reload]);

  useEffect(() => setSelected(new Set()), [query]);

  const pageIds = data?.results.map((r) => r.id) ?? [];
  const allOnPage = pageIds.length > 0 && pageIds.every((id) => selected.has(id));
  const toggle = (id: string) =>
    setSelected((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const toggleAll = () => setSelected(allOnPage ? new Set() : new Set(pageIds));

  const openConfirm = (c: typeof confirm) => {
    setConfirmText("");
    setConfirm(c);
  };

  const doDelete = async () => {
    try {
      let res: { deleted: number };
      if (confirm === "all") {
        const filters = { ...query };
        delete filters.page;
        delete filters.ordering;
        res = await adminApi.deleteAllAttempts(filters);
      } else if (confirm === "selected") {
        res = await adminApi.deleteAttempts([...selected]);
      } else if (confirm) {
        res = await adminApi.deleteAttempts([confirm.id]);
      } else return;
      toast.success(`${res.deleted} ta natija o'chirildi`);
      setConfirm(null);
      setSelected(new Set());
      if (get("page") && data && res.deleted >= data.results.length) set("page", "");
      else setReload((n) => n + 1);
    } catch (e) {
      toast.error((e as ApiError).message);
    }
  };

  const exportXlsx = async (answers: boolean) => {
    setExporting(true);
    try {
      const filters = { ...query };
      delete filters.page;
      await downloadFile(adminApi.attemptsExportUrl({ ...filters, answers: answers ? 1 : undefined }), "natijalar.xlsx");
    } catch (e) {
      toast.error((e as ApiError).message);
    } finally {
      setExporting(false);
    }
  };

  const sortBy = (field: string) => {
    const cur = get("ordering") || "-started_at";
    set("ordering", cur === `-${field}` ? field : `-${field}`);
  };
  const sortMark = (field: string) => {
    const cur = get("ordering") || "-started_at";
    return cur === field ? " ↑" : cur === `-${field}` ? " ↓" : "";
  };

  const hasFilters = Object.keys(query).some((k) => !["ordering", "page"].includes(k));

  return (
    <div className="admin-page">
      <div className="page-head">
        <div>
          <h1>Natijalar</h1>
          <p className="muted">{data ? `${data.count} ta yozuv` : "…"}</p>
        </div>
        <div className="head-actions">
          <button className="btn" onClick={() => exportXlsx(false)} disabled={exporting}>
            <Icon name="download" size={18} /> Excel
          </button>
          <button className="btn" onClick={() => exportXlsx(true)} disabled={exporting}>
            <Icon name="download" size={18} /> Excel (javoblar bilan)
          </button>
          <button className="btn btn-danger" onClick={() => openConfirm("all")} disabled={!data?.count}>
            <Icon name="trash" size={18} /> {hasFilters ? "Filtrdagilarni o'chirish" : "Hammasini o'chirish"}
          </button>
        </div>
      </div>

      <div className={`filters glass${filtersOpen ? "" : " collapsed"}`}>
        <div className="search-input">
          <Icon name="search" size={16} />
          <input className="input" placeholder="Ism" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
        </div>
        <div className="search-input">
          <Icon name="search" size={16} />
          <input className="input" placeholder="Familiya" value={lastName} onChange={(e) => setLastName(e.target.value)} />
        </div>
        <button className="btn btn-ghost filters-toggle" onClick={() => setFiltersOpen((v) => !v)} aria-expanded={filtersOpen}>
          <Icon name="settings" size={16} /> {filtersOpen ? "Filtrlarni yopish" : `Filtrlar${hasFilters ? " (yoqilgan)" : ""}`}
        </button>
        <select className="select" value={get("branch")} onChange={(e) => set("branch", e.target.value)}>
          <option value="">Barcha filiallar</option>
          {branches.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <select className="select" value={get("subject")} onChange={(e) => set("subject", e.target.value)}>
          <option value="">Barcha fanlar</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.full_name}
            </option>
          ))}
        </select>
        <select className="select" value={get("status")} onChange={(e) => set("status", e.target.value)}>
          <option value="">Barcha holatlar</option>
          <option value="completed">Yakunlangan</option>
          <option value="active">Jarayonda</option>
          <option value="annulled">Bekor qilingan</option>
        </select>
        <select className="select" value={get("ordering") || "-started_at"} onChange={(e) => set("ordering", e.target.value)}>
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <label className="date-field">
          <span className="tiny">Dan</span>
          <input type="date" className="input" value={get("date_from")} onChange={(e) => set("date_from", e.target.value)} />
        </label>
        <label className="date-field">
          <span className="tiny">Gacha</span>
          <input type="date" className="input" value={get("date_to")} onChange={(e) => set("date_to", e.target.value)} />
        </label>
        {hasFilters && (
          <button
            className="btn btn-ghost"
            onClick={() => {
              setFirstName("");
              setLastName("");
              setParams(new URLSearchParams(), { replace: true });
            }}
          >
            <Icon name="x" size={16} /> Tozalash
          </button>
        )}
      </div>

      {selected.size > 0 && (
        <div className="selection-bar glass">
          <span>
            Tanlandi: <b>{selected.size}</b>
          </span>
          <button className="btn btn-ghost" onClick={() => setSelected(new Set())}>
            Bekor qilish
          </button>
          <button className="btn btn-danger" onClick={() => openConfirm("selected")}>
            <Icon name="trash" size={16} /> O'chirish
          </button>
        </div>
      )}

      <div className="glass table-wrap">
        {loading && !data ? (
          <Loader />
        ) : (
          <table className={`table results-table${loading ? " loading" : ""}`}>
            <thead>
              <tr>
                <th className="check-col">
                  <input type="checkbox" aria-label="Hammasini tanlash" checked={allOnPage} onChange={toggleAll} />
                </th>
                <th className="sortable" onClick={() => sortBy("last_name")}>F.I.Sh{sortMark("last_name")}</th>
                <th>Filial</th>
                <th>Fan</th>
                <th className="sortable" onClick={() => sortBy("started_at")}>Boshlangan{sortMark("started_at")}</th>
                <th className="sortable num" onClick={() => sortBy("duration")}>Vaqt{sortMark("duration")}</th>
                <th className="num sortable" onClick={() => sortBy("stage1_score")}>1. Akademik{sortMark("stage1_score")}</th>
                <th className="num sortable" onClick={() => sortBy("stage2_score")}>2. Fan testi{sortMark("stage2_score")}</th>
                <th className="num sortable" onClick={() => sortBy("total_score")}>Umumiy{sortMark("total_score")}</th>
                <th>Holat</th>
                <th className="actions-col" aria-label="Amallar" />
              </tr>
            </thead>
            <tbody>
              {data?.results.map((r) => {
                const done = r.status === "completed";
                const name = `${r.last_name} ${r.first_name}`;
                return (
                  <tr key={r.id} className={selected.has(r.id) ? "selected" : ""}>
                    <td className="check-col">
                      <input type="checkbox" aria-label={`${name} ni tanlash`} checked={selected.has(r.id)} onChange={() => toggle(r.id)} />
                    </td>
                    <td className="name-col" data-label="F.I.Sh">
                      <Link to={`/admin/results/${r.id}`} className="row-link">
                        {name}
                      </Link>
                    </td>
                    <td data-label="Filial">{r.branch_name}</td>
                    <td data-label="Fan">{r.subject_name}</td>
                    <td className="nowrap" data-label="Boshlangan">{fmt.date(r.started_at)}</td>
                    <td className="num" data-label="Vaqt">{fmt.duration(r.duration_seconds)}</td>
                    <td className="num" data-label="1. Akademik">
                      {done ? <Pct value={r.stage1_percent} sub={`${r.stage1_score} ball · ${r.stage1_correct} ✓`} /> : "—"}
                    </td>
                    <td className="num" data-label="2. Fan testi">
                      {done ? (
                        <Pct value={r.stage_count < 2 ? null : r.stage2_percent} sub={`${r.stage2_score} ball · ${r.stage2_correct} ✓`} />
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="num total-col" data-label="Umumiy">
                      {done ? <Pct value={r.percent} sub={`${r.total_score}/${r.max_score} ball`} /> : "—"}
                    </td>
                    <td data-label="Holat">
                      <span className={`badge ${done ? "success" : r.status === "active" ? "info" : ""}`}>{statusLabel[r.status]}</span>
                      {r.retake_allowed && <span className="badge warning" style={{ marginLeft: 4 }}>Qayta ruxsat</span>}
                    </td>
                    <td className="actions-col">
                      <button className="icon-btn danger" title="O'chirish" aria-label={`${name} natijasini o'chirish`} onClick={() => openConfirm({ id: r.id, name })}>
                        <Icon name="trash" size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {data && data.results.length === 0 && (
                <tr>
                  <td colSpan={11} className="empty">
                    Hech narsa topilmadi
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
      {data && <Pagination count={data.count} page={Number(get("page") || 1)} pageSize={25} onChange={(p) => set("page", String(p))} />}

      <ConfirmDialog
        open={confirm !== null}
        title={confirm === "all" ? (hasFilters ? "Filtrdagi natijalarni o'chirish" : "Barcha natijalarni o'chirish") : "Natijani o'chirish"}
        confirmLabel="O'chirish"
        danger
        disabled={confirm === "all" && confirmText.trim().toUpperCase() !== CONFIRM_WORD}
        onClose={() => setConfirm(null)}
        onConfirm={doDelete}
      >
        {confirm === "all" ? (
          <>
            <p>
              {hasFilters ? "Joriy filtrga mos keladigan" : "Bazadagi"} <b>{data?.count ?? 0} ta</b> natija javoblari bilan butunlay
              o'chiriladi. Buni qaytarib bo'lmaydi.
            </p>
            <p className="muted" style={{ margin: "10px 0 6px" }}>
              Tasdiqlash uchun <b>{CONFIRM_WORD}</b> deb yozing:
            </p>
            <input className="input" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} placeholder={CONFIRM_WORD} autoFocus />
          </>
        ) : confirm === "selected" ? (
          <p>
            Tanlangan <b>{selected.size} ta</b> natija javoblari bilan butunlay o'chiriladi. Buni qaytarib bo'lmaydi.
          </p>
        ) : confirm ? (
          <p>
            <b>{confirm.name}</b> natijasi javoblari bilan butunlay o'chiriladi. U testni qaytadan topshira oladi.
          </p>
        ) : null}
      </ConfirmDialog>
    </div>
  );
}
