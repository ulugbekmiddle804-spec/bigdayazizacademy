import { useEffect, useMemo, useRef, useState } from "react";

import { downloadFile, firstErrorMessage, type ApiError } from "../../api/http";
import { Icon } from "../../components/Icon";
import { Loader } from "../../components/Loader";
import { Modal } from "../../components/Modal";
import { toast } from "../../components/Toast";
import { adminApi, difficultyLabel, type Paginated, type Question, type QuestionOption, type Subject } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { Pagination } from "../components/Pagination";
import { useDebounced } from "../components/useDebounced";
import { WordImportModal } from "../components/WordImportModal";

type Draft = Omit<Question, "id" | "subject_name" | "created_at" | "updated_at"> & { id?: number };

const emptyDraft = (subject?: number, stage = 1): Draft => ({
  subject: subject ?? 0,
  stage,
  text: "",
  difficulty: "medium",
  points: 1,
  is_active: true,
  options: [
    { text: "", is_correct: true },
    { text: "", is_correct: false },
    { text: "", is_correct: false },
    { text: "", is_correct: false },
  ],
});

export default function QuestionsPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [filters, setFilters] = useState({ subject: "", stage: "", difficulty: "", is_active: "", search: "" });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Paginated<Question> | null>(null);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [deleting, setDeleting] = useState<Question | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [wordOpen, setWordOpen] = useState(false);
  const [reload, setReload] = useState(0);
  const search = useDebounced(filters.search, 350);

  const leaves = useMemo(() => subjects.filter((s) => !s.is_group), [subjects]);

  useEffect(() => {
    adminApi.subjects().then(setSubjects).catch((e: ApiError) => toast.error(e.message));
  }, [reload]);

  const params = useMemo(
    () => ({ ...filters, search, page }),
    [filters.subject, filters.stage, filters.difficulty, filters.is_active, search, page],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    adminApi
      .questions(params)
      .then((d) => !cancelled && setData(d))
      .catch((e: ApiError) => toast.error(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [params, reload]);

  const setFilter = (k: keyof typeof filters, v: string) => {
    setFilters((f) => ({ ...f, [k]: v }));
    setPage(1);
  };

  const toggleActive = async (q: Question) => {
    try {
      const updated = await adminApi.patchQuestion(q.id, { is_active: !q.is_active });
      setData((d) => d && { ...d, results: d.results.map((x) => (x.id === q.id ? updated : x)) });
    } catch (e) {
      toast.error((e as ApiError).message);
    }
  };

  const exportParams = { subject: filters.subject, stage: filters.stage, difficulty: filters.difficulty, is_active: filters.is_active, search };

  return (
    <div className="admin-page">
      <div className="page-head">
        <div>
          <h1>Savollar</h1>
          <p className="muted">{data ? `${data.count} ta savol` : "…"}</p>
        </div>
        <div className="head-actions">
          <button className="btn" onClick={() => setWordOpen(true)}>
            <Icon name="upload" size={18} /> Word orqali
          </button>
          <button className="btn" onClick={() => setImportOpen(true)}>
            <Icon name="upload" size={18} /> Excel import
          </button>
          <button
            className="btn"
            onClick={() => downloadFile(adminApi.questionsExportUrl(exportParams), "savollar.xlsx").catch((e) => toast.error(e.message))}
          >
            <Icon name="download" size={18} /> Eksport
          </button>
          <button
            className="btn btn-primary"
            onClick={() => setDraft(emptyDraft(Number(filters.subject) || leaves[0]?.id, Number(filters.stage) || 1))}
          >
            <Icon name="plus" size={18} /> Yangi savol
          </button>
        </div>
      </div>

      <div className="filters glass">
        <div className="search-input grow">
          <Icon name="search" size={16} />
          <input className="input" placeholder="Savol matni bo'yicha qidirish" value={filters.search} onChange={(e) => setFilter("search", e.target.value)} />
        </div>
        <select className="select" value={filters.subject} onChange={(e) => setFilter("subject", e.target.value)}>
          <option value="">Barcha fanlar</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.full_name}
            </option>
          ))}
        </select>
        <select className="select" value={filters.stage} onChange={(e) => setFilter("stage", e.target.value)}>
          <option value="">Barcha bosqichlar</option>
          <option value="1">1-bosqich</option>
          <option value="2">2-bosqich</option>
        </select>
        <select className="select" value={filters.difficulty} onChange={(e) => setFilter("difficulty", e.target.value)}>
          <option value="">Har qanday qiyinlik</option>
          <option value="easy">Oson</option>
          <option value="medium">O'rta</option>
          <option value="hard">Qiyin</option>
        </select>
        <select className="select" value={filters.is_active} onChange={(e) => setFilter("is_active", e.target.value)}>
          <option value="">Faol va nofaol</option>
          <option value="true">Faqat faol</option>
          <option value="false">Faqat nofaol</option>
        </select>
      </div>

      <div className="glass table-wrap">
        {loading && !data ? (
          <Loader />
        ) : (
          <table className={`table${loading ? " loading" : ""}`}>
            <thead>
              <tr>
                <th>Savol</th>
                <th>Fan</th>
                <th className="num">Bosqich</th>
                <th>Qiyinlik</th>
                <th className="num">Ball</th>
                <th>Faol</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data?.results.map((q) => (
                <tr key={q.id} className={q.is_active ? "" : "dim"}>
                  <td className="q-text-cell">
                    <span dir="auto">{q.text}</span>
                    <div className="tiny">{q.options.length} ta variant · to'g'ri: {q.options.find((o) => o.is_correct)?.text}</div>
                  </td>
                  <td>{q.subject_name}</td>
                  <td className="num">{q.stage}</td>
                  <td>
                    <span className={`badge ${q.difficulty === "easy" ? "success" : q.difficulty === "hard" ? "danger" : "warning"}`}>
                      {difficultyLabel[q.difficulty]}
                    </span>
                  </td>
                  <td className="num">{q.points}</td>
                  <td>
                    <button className={`switch${q.is_active ? " on" : ""}`} onClick={() => toggleActive(q)} aria-label="Faol" />
                  </td>
                  <td className="row-actions">
                    <button className="icon-btn" onClick={() => setDraft({ ...q, options: q.options.map((o) => ({ ...o })) })} aria-label="Tahrirlash">
                      <Icon name="edit" size={16} />
                    </button>
                    <button className="icon-btn" onClick={() => setDeleting(q)} aria-label="O'chirish">
                      <Icon name="trash" size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {data && data.results.length === 0 && (
                <tr>
                  <td colSpan={7} className="empty">Savollar topilmadi</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
      {data && <Pagination count={data.count} page={page} pageSize={25} onChange={setPage} />}

      {draft && (
        <QuestionForm
          draft={draft}
          subjects={leaves}
          onClose={() => setDraft(null)}
          onSaved={() => {
            setDraft(null);
            setReload((r) => r + 1);
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        title="Savolni o'chirasizmi?"
        danger
        confirmLabel="O'chirish"
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          try {
            await adminApi.deleteQuestion(deleting.id);
            toast.success("Savol o'chirildi");
            setDeleting(null);
            setReload((r) => r + 1);
          } catch (e) {
            toast.error((e as ApiError).message);
          }
        }}
      >
        <p className="muted">«{deleting?.text.slice(0, 120)}»</p>
        <p className="tiny" style={{ marginTop: 8 }}>
          Avval topshirilgan testlardagi nusxasi saqlanib qoladi. Vaqtincha olib tashlash uchun savolni nofaol qilish ham mumkin.
        </p>
      </ConfirmDialog>

      <ImportModal open={importOpen} onClose={() => setImportOpen(false)} onDone={() => setReload((r) => r + 1)} />
      <WordImportModal
        open={wordOpen}
        subjects={subjects}
        initialSubject={Number(filters.subject) || undefined}
        onClose={() => setWordOpen(false)}
        onDone={() => setReload((r) => r + 1)}
      />
    </div>
  );
}

function QuestionForm({ draft, subjects, onClose, onSaved }: { draft: Draft; subjects: Subject[]; onClose: () => void; onSaved: () => void }) {
  const [q, setQ] = useState<Draft>(draft);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setOption = (i: number, patch: Partial<QuestionOption>) =>
    setQ((cur) => ({
      ...cur,
      options: cur.options.map((o, idx) =>
        patch.is_correct ? { ...o, is_correct: idx === i } : idx === i ? { ...o, ...patch } : o,
      ),
    }));

  const save = async () => {
    setError(null);
    if (!q.subject) return setError("Fanni tanlang.");
    if (q.text.trim().length < 3) return setError("Savol matnini kiriting.");
    const options = q.options.filter((o) => o.text.trim());
    if (options.length < 2) return setError("Kamida 2 ta javob varianti kiriting.");
    if (options.filter((o) => o.is_correct).length !== 1) return setError("To'g'ri javobni belgilang (to'ldirilgan variantlardan biri).");
    setBusy(true);
    try {
      await adminApi.saveQuestion({ ...q, options } as Question);
      toast.success(q.id ? "Savol yangilandi" : "Savol qo'shildi");
      onSaved();
    } catch (e) {
      setError(firstErrorMessage((e as ApiError).data, (e as ApiError).message));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      width={720}
      title={q.id ? "Savolni tahrirlash" : "Yangi savol"}
      footer={
        <>
          <button className="btn" onClick={onClose}>Bekor qilish</button>
          <button className="btn btn-primary" onClick={save} disabled={busy}>
            {busy ? <span className="spinner tiny-spinner" /> : <Icon name="check" size={18} />} Saqlash
          </button>
        </>
      }
    >
      <div className="form-grid">
        <div className="field span-2">
          <label>Fan</label>
          <select className="select" value={q.subject || ""} onChange={(e) => setQ({ ...q, subject: Number(e.target.value) })}>
            <option value="">Tanlang</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>{s.full_name}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Bosqich</label>
          <select className="select" value={q.stage} onChange={(e) => setQ({ ...q, stage: Number(e.target.value) })}>
            <option value={1}>1-bosqich</option>
            <option value={2}>2-bosqich</option>
          </select>
        </div>
        <div className="field">
          <label>Qiyinlik</label>
          <select className="select" value={q.difficulty} onChange={(e) => setQ({ ...q, difficulty: e.target.value as Draft["difficulty"] })}>
            <option value="easy">Oson</option>
            <option value="medium">O'rta</option>
            <option value="hard">Qiyin</option>
          </select>
        </div>
        <div className="field">
          <label>Ball</label>
          <input type="number" min={1} max={100} className="input" value={q.points} onChange={(e) => setQ({ ...q, points: Number(e.target.value) || 1 })} />
        </div>
        <div className="field">
          <label>Holat</label>
          <label className="checkbox" style={{ minHeight: 48 }}>
            <button type="button" className={`switch${q.is_active ? " on" : ""}`} onClick={() => setQ({ ...q, is_active: !q.is_active })} />
            {q.is_active ? "Faol" : "Nofaol"}
          </label>
        </div>
        <div className="field span-4">
          <label>Savol matni</label>
          <textarea className="textarea" value={q.text} maxLength={2000} onChange={(e) => setQ({ ...q, text: e.target.value })} dir="auto" />
        </div>
        <div className="field span-4">
          <label>Javob variantlari (to'g'ri javobni belgilang)</label>
          <div className="option-editor">
            {q.options.map((o, i) => (
              <div key={i} className={`option-row${o.is_correct ? " correct" : ""}`}>
                <button type="button" className="radio" onClick={() => setOption(i, { is_correct: true })} aria-label="To'g'ri javob">
                  {o.is_correct && <Icon name="check" size={14} />}
                </button>
                <span className="option-letter small">{"ABCDEF"[i]}</span>
                <input className="input" value={o.text} maxLength={500} onChange={(e) => setOption(i, { text: e.target.value })} placeholder={`${i + 1}-variant`} dir="auto" />
                <button
                  type="button"
                  className="icon-btn"
                  disabled={q.options.length <= 2}
                  onClick={() => setQ({ ...q, options: q.options.filter((_, idx) => idx !== i) })}
                  aria-label="Variantni o'chirish"
                >
                  <Icon name="x" size={14} />
                </button>
              </div>
            ))}
            {q.options.length < 6 && (
              <button type="button" className="btn btn-sm" onClick={() => setQ({ ...q, options: [...q.options, { text: "", is_correct: false }] })}>
                <Icon name="plus" size={14} /> Variant qo'shish
              </button>
            )}
          </div>
        </div>
      </div>
      {error && <div className="alert" style={{ marginTop: 12 }}>{error}</div>}
    </Modal>
  );
}

function ImportModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<{ row: number; error: string }[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  const upload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return setMessage("Faylni tanlang.");
    setBusy(true);
    setErrors([]);
    setMessage(null);
    try {
      const res = await adminApi.importQuestions(file);
      toast.success(`${res.created} ta savol import qilindi`);
      onDone();
      onClose();
    } catch (e) {
      const err = e as ApiError;
      const data = err.data as { errors?: { row: number; error: string }[] } | null;
      setErrors(data?.errors ?? []);
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Savollarni import qilish"
      width={620}
      footer={
        <>
          <button className="btn" onClick={() => downloadFile(adminApi.templateUrl, "savollar_shablon.xlsx").catch(() => toast.error("Yuklab bo'lmadi"))}>
            <Icon name="download" size={16} /> Shablon
          </button>
          <button className="btn btn-primary" onClick={upload} disabled={busy}>
            {busy ? <span className="spinner tiny-spinner" /> : <Icon name="upload" size={16} />} Yuklash
          </button>
        </>
      }
    >
      <p className="muted" style={{ marginBottom: 12 }}>
        Excel (.xlsx) faylda ustunlar: Fan kodi, Bosqich, Savol, A–F variantlar, To'g'ri javob harfi, Ball, Qiyinlik, Faol.
        Shablonni yuklab olib to'ldiring. Faylda bitta xato bo'lsa ham hech narsa qo'shilmaydi.
      </p>
      <input ref={fileRef} type="file" accept=".xlsx" className="input" />
      {message && <div className="alert" style={{ marginTop: 12 }}>{message}</div>}
      {errors.length > 0 && (
        <ul className="import-errors">
          {errors.map((e, i) => (
            <li key={i}>
              <b>{e.row ? `${e.row}-qator:` : ""}</b> {e.error}
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
