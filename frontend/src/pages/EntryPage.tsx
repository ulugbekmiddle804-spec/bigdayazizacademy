import { AnimatePresence, m } from "framer-motion";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { examApi } from "../api/exam";
import { ApiError } from "../api/http";
import type { Meta, SubjectNode } from "../api/types";
import { Background } from "../components/Background";
import { Icon } from "../components/Icon";
import { Loader } from "../components/Loader";
import { Logo } from "../components/Logo";
import { Modal } from "../components/Modal";
import { PageTransition } from "../components/PageTransition";
import { TiltCard } from "../components/TiltCard";
import { useExam } from "../store/exam";
import "./entry.css";

const NAME_RE = /^[\p{L}]+(?:[ \-'ʻʼ’‘`][\p{L}]*)*$/u;

function validateName(value: string, label: string): string | null {
  const v = value.trim().replace(/\s+/g, " ");
  if (v.length < 2) return `${label} kamida 2 ta harfdan iborat bo'lsin`;
  if (v.length > 50) return `${label} juda uzun`;
  if (!NAME_RE.test(v)) return `${label} faqat harflardan iborat bo'lsin`;
  return null;
}

export function EntryPage() {
  const navigate = useNavigate();
  const activeAttempt = useExam((s) => s.attemptId);
  const begin = useExam((s) => s.begin);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [branchId, setBranchId] = useState<number | "">("");
  const [group, setGroup] = useState<SubjectNode | null>(null);
  const [subject, setSubject] = useState<SubjectNode | null>(null);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoadError(null);
    examApi
      .meta()
      .then(setMeta)
      .catch((e: ApiError) => setLoadError(e.message));
  };
  useEffect(load, []);

  const errors = {
    first: validateName(firstName, "Ism"),
    last: validateName(lastName, "Familiya"),
  };
  const ready = !errors.first && !errors.last && branchId !== "" && subject !== null;
  const stages = subject?.stages ?? [];

  const pickSubject = (id: number | null) => {
    setError(null);
    for (const s of meta?.subjects ?? []) {
      if (s.selectable && s.id === id) {
        setGroup(null);
        setSubject(s);
        return;
      }
      const child = s.children.find((c) => c.id === id);
      if (child) {
        setGroup(s);
        setSubject(child);
        return;
      }
    }
    setGroup(null);
    setSubject(null);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setTouched({ first: true, last: true, branch: true });
    if (ready) setConfirm(true);
  };

  const start = async () => {
    if (!subject || branchId === "") return;
    setBusy(true);
    setError(null);
    try {
      const res = await examApi.start({
        first_name: firstName.trim().replace(/\s+/g, " "),
        last_name: lastName.trim().replace(/\s+/g, " "),
        branch_id: Number(branchId),
        subject_id: subject.id,
      });
      begin(res.token, res.state);
      navigate("/test");
    } catch (err) {
      setConfirm(false);
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const branchName = meta?.branches.find((b) => b.id === branchId)?.name;
  const subjectLabel = subject ? (group ? `${group.name} — ${subject.name}` : subject.name) : "";

  return (
    <PageTransition className="entry">
      <Background />
      <header className="entry-header container">
        <Logo title={meta?.site.title ?? "Aziz Academy"} />
        <span className="badge info">
          <Icon name="shield" size={14} /> Xavfsiz test tizimi
        </span>
      </header>

      <div className="entry-grid container">
        <TiltCard className="form-card glass">
          {activeAttempt && (
            <div className="alert info resume">
              <span>Sizda tugallanmagan test bor.</span>
              <button className="btn btn-sm btn-primary" onClick={() => navigate("/test")}>
                Davom ettirish <Icon name="right" size={16} />
              </button>
            </div>
          )}
          {!meta && !loadError && <Loader label="Ma'lumotlar yuklanmoqda..." />}
          {loadError && (
            <div className="alert">
              {loadError}{" "}
              <button className="btn btn-sm" onClick={load} style={{ marginLeft: 8 }}>
                <Icon name="refresh" size={16} /> Qayta urinish
              </button>
            </div>
          )}
          {meta && !meta.site.registration_open && (
            <div className="alert warning">Hozircha test topshirish yopiq. Keyinroq urinib ko'ring.</div>
          )}
          {meta && meta.site.registration_open && (
            <form onSubmit={onSubmit} noValidate>
              <div className="form-head">
                <span className="form-orb">
                  <img src="/logo.png" alt="Aziz Academy" width={44} height={44} />
                </span>
                <h1 className="form-title">Ism va familiyangizni kiriting</h1>
              </div>
              <div className="row-2">
                <div className="field">
                  <label htmlFor="first">Ism</label>
                  <div className="with-icon">
                    <Icon name="user" size={18} />
                  <input
                    id="first"
                    className={`input${touched.first && errors.first ? " invalid" : ""}`}
                    value={firstName}
                    autoComplete="given-name"
                    maxLength={50}
                    placeholder="Masalan: Aziz"
                    onChange={(e) => setFirstName(e.target.value)}
                    onBlur={() => setTouched((t) => ({ ...t, first: true }))}
                  />
                  </div>
                  {touched.first && errors.first && <span className="field-error">{errors.first}</span>}
                </div>
                <div className="field">
                  <label htmlFor="last">Familiya</label>
                  <div className="with-icon">
                    <Icon name="user" size={18} />
                  <input
                    id="last"
                    className={`input${touched.last && errors.last ? " invalid" : ""}`}
                    value={lastName}
                    autoComplete="family-name"
                    maxLength={50}
                    placeholder="Masalan: Karimov"
                    onChange={(e) => setLastName(e.target.value)}
                    onBlur={() => setTouched((t) => ({ ...t, last: true }))}
                  />
                  </div>
                  {touched.last && errors.last && <span className="field-error">{errors.last}</span>}
                </div>
              </div>

              <div className="field">
                <label htmlFor="branch">Filial</label>
                <div className="with-icon">
                  <Icon name="building" size={18} />
                <select
                  id="branch"
                  className="select"
                  value={branchId}
                  onChange={(e) => setBranchId(e.target.value ? Number(e.target.value) : "")}
                >
                  <option value="">Filialni tanlang</option>
                  {meta.branches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
                </div>
                {touched.branch && branchId === "" && <span className="field-error">Filialni tanlang</span>}
              </div>

              <div className="field">
                <label htmlFor="subject">Fan</label>
                <div className="with-icon">
                  <Icon name="book" size={18} />
                <select
                  id="subject"
                  className="select"
                  value={subject?.id ?? ""}
                  onChange={(e) => pickSubject(e.target.value ? Number(e.target.value) : null)}
                >
                  <option value="">Fanni tanlang</option>
                  {meta.subjects.map((s) =>
                    s.selectable ? (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ) : (
                      <optgroup key={s.id} label={s.name}>
                        {s.children.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </optgroup>
                    ),
                  )}
                </select>
                </div>
                {touched.branch && !subject && <span className="field-error">Fanni tanlang</span>}
              </div>

              <AnimatePresence>
                {subject && stages.length > 0 && (
                  <m.div
                    className="stage-summary"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                  >
                    {stages.map((s) => (
                      <div key={s.number}>
                        <strong>{s.title}</strong>
                        <span>
                          {s.question_count} savol · {s.duration_minutes} daqiqa
                        </span>
                      </div>
                    ))}
                  </m.div>
                )}
              </AnimatePresence>

              {error && <div className="alert">{error}</div>}

              <AnimatePresence>
                {ready && (
                  <m.div
                    initial={{ opacity: 0, y: 16, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10 }}
                    transition={{ type: "spring", stiffness: 300, damping: 22 }}
                  >
                    <button type="submit" className="btn btn-primary btn-lg btn-block start-btn">
                      Testni boshlash <Icon name="right" size={20} />
                    </button>
                  </m.div>
                )}
              </AnimatePresence>
            </form>
          )}
        </TiltCard>
      </div>

      <Modal
        open={confirm}
        onClose={() => !busy && setConfirm(false)}
        title="Testni boshlashga tayyormisiz?"
        footer={
          <>
            <button className="btn" onClick={() => setConfirm(false)} disabled={busy}>
              Ortga
            </button>
            <button className="btn btn-primary" onClick={start} disabled={busy}>
              {busy ? <span className="spinner" /> : <Icon name="check" size={18} />} Boshlash
            </button>
          </>
        }
      >
        <div className="confirm-info">
          <div>
            <Icon name="user" size={18} /> {firstName.trim()} {lastName.trim()}
          </div>
          <div>
            <Icon name="building" size={18} /> {branchName}
          </div>
          <div>
            <Icon name="book" size={18} /> {subjectLabel}
          </div>
        </div>
      </Modal>
    </PageTransition>
  );
}
