import { useEffect, useRef, useState } from "react";

import { downloadFile, type ApiError } from "../../api/http";
import { Icon } from "../../components/Icon";
import { Modal } from "../../components/Modal";
import { toast } from "../../components/Toast";
import { adminApi, type Subject, type WordImportResult } from "../api";

const LETTERS = "ABCDEF";

interface Props {
  open: boolean;
  subjects: Subject[];
  initialSubject?: number;
  onClose: () => void;
  onDone: () => void;
}

/** Attach questions to a subject from a Word file: check first (preview), then save. */
export function WordImportModal({ open, subjects, initialSubject, onClose, onDone }: Props) {
  const leaves = subjects.filter((s) => !s.is_group);
  const fileRef = useRef<HTMLInputElement>(null);
  const [subject, setSubject] = useState<number | "">("");
  const [stage, setStage] = useState(2);
  const [points, setPoints] = useState(1);
  const [difficulty, setDifficulty] = useState("medium");
  const [replace, setReplace] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<WordImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const current = leaves.find((s) => s.id === subject);
  const academic = !!current?.is_academic;

  useEffect(() => {
    if (!open) return;
    setSubject(initialSubject ?? "");
    setPreview(null);
    setError(null);
    setFile(null);
    setReplace(false);
    if (fileRef.current) fileRef.current.value = "";
  }, [open, initialSubject]);

  useEffect(() => {
    const st = academic ? 1 : 2;
    setStage(st);
    setPoints(1);
    setPreview(null);
  }, [subject, academic]);

  const run = async (save: boolean) => {
    if (!subject) return setError("Fanni tanlang.");
    if (!file) return setError("Word (.docx) faylni tanlang.");
    setBusy(true);
    setError(null);
    try {
      const res = await adminApi.importWord({ file, subject, stage, points, difficulty, replace, preview: !save });
      if (save) {
        toast.success(`${res.created} ta savol qo'shildi${res.replaced ? ` (${res.replaced} ta eski savol almashtirildi)` : ""}`);
        onDone();
        onClose();
      } else {
        setPreview(res);
      }
    } catch (e) {
      const err = e as ApiError;
      const data = err.data as WordImportResult | null;
      if (data?.problems) setPreview((p) => ({ ...(p ?? data), problems: data.problems }));
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const canSave = !!preview && preview.count > 0 && preview.problems.length === 0;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Word orqali test biriktirish"
      width={760}
      footer={
        <>
          <button
            className="btn"
            onClick={() => downloadFile(adminApi.wordTemplateUrl, "test_namuna.docx").catch(() => toast.error("Yuklab bo'lmadi"))}
          >
            <Icon name="download" size={16} /> Namuna (Word)
          </button>
          <button className="btn" onClick={() => run(false)} disabled={busy}>
            {busy && !canSave ? <span className="spinner tiny-spinner" /> : <Icon name="search" size={16} />} Tekshirish
          </button>
          <button className="btn btn-primary" onClick={() => run(true)} disabled={busy || !canSave}>
            <Icon name="check" size={16} /> {preview?.count ? `${preview.count} ta savolni saqlash` : "Saqlash"}
          </button>
        </>
      }
    >
      <p className="muted" style={{ marginBottom: 14 }}>
        Har bir savol «1.» kabi raqam bilan, variantlar «A)», «B)»… bilan alohida qatorda yoziladi. To'g'ri javoblar fayl
        oxiridagi kalit jadvalida yoki variant oldidagi * belgisi bilan ko'rsatiladi. Avval «Tekshirish»ni bosing: xato
        bo'lsa, hech narsa saqlanmaydi.
      </p>
      <div className="form-grid">
        <div className="field span-2">
          <label>Fan</label>
          <select className="select" value={subject} onChange={(e) => setSubject(e.target.value ? Number(e.target.value) : "")}>
            <option value="">— Fanni tanlang —</option>
            {leaves.map((s) => (
              <option key={s.id} value={s.id}>
                {s.is_academic ? `${s.name} (barcha fanlar 1-bosqichi)` : s.full_name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>Bosqich</label>
          <select className="select" value={stage} disabled={academic} onChange={(e) => setStage(Number(e.target.value))}>
            <option value={1}>1-bosqich</option>
            <option value={2}>2-bosqich</option>
          </select>
        </div>
        <div className="field">
          <label>Har bir savol bali</label>
          <input type="number" min={1} max={100} className="input" value={points} onChange={(e) => setPoints(Number(e.target.value) || 1)} />
        </div>
        <div className="field span-2">
          <label>Qiyinlik</label>
          <select className="select" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="easy">Oson</option>
            <option value="medium">O'rta</option>
            <option value="hard">Qiyin</option>
          </select>
        </div>
        <div className="field span-2">
          <label>Mavjud savollar</label>
          <select className="select" value={replace ? "1" : "0"} onChange={(e) => setReplace(e.target.value === "1")}>
            <option value="0">Saqlab qolinsin, yangilari qo'shilsin</option>
            <option value="1">O'chirilib, fayldagilar bilan almashtirilsin</option>
          </select>
        </div>
        <div className="field span-4">
          <label>Word fayl (.docx)</label>
          <input
            ref={fileRef}
            type="file"
            accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="input"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setPreview(null);
              setError(null);
            }}
          />
        </div>
      </div>

      {error && <div className="alert" style={{ marginTop: 12 }}>{error}</div>}

      {preview && (
        <div className="word-preview">
          <div className={`word-summary${preview.problems.length ? " bad" : " ok"}`}>
            <Icon name={preview.problems.length ? "alert" : "check"} size={18} />
            <span>
              {preview.title && <b>{preview.title}. </b>}
              Topilgan savollar: <b>{preview.count}</b>
              {preview.problems.length ? `, muammolar: ${preview.problems.length}` : ". Xato topilmadi."}
            </span>
          </div>
          {preview.problems.length > 0 && (
            <ul className="import-errors">
              {preview.problems.map((p, i) => (
                <li key={i}>
                  <b>{p.question ? `${p.question}-savol:` : ""}</b> {p.error}
                </li>
              ))}
            </ul>
          )}
          {preview.questions && preview.questions.length > 0 && (
            <ol className="word-questions">
              {preview.questions.map((q) => (
                <li key={q.number}>
                  <p dir="auto">
                    <b>{q.number}.</b> {q.text}
                  </p>
                  <ul>
                    {q.options.map((o, i) => (
                      <li key={i} className={i === q.correct ? "correct" : ""} dir="auto">
                        {LETTERS[i]}) {o}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </Modal>
  );
}
