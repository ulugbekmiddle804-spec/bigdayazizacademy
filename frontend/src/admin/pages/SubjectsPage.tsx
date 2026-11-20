import { useEffect, useState } from "react";

import { firstErrorMessage, type ApiError } from "../../api/http";
import { Icon } from "../../components/Icon";
import { Loader } from "../../components/Loader";
import { Modal } from "../../components/Modal";
import { SubjectGlyph } from "../../components/SubjectGlyph";
import { toast } from "../../components/Toast";
import { adminApi, type StageConfig, type Subject } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { WordImportModal } from "../components/WordImportModal";

const ICONS = ["english", "russian", "arabic", "korean", "uzbek", "turkish", "chemistry", "biology", "math", "mental",
  "frontend", "backend", "nursing", "primary", "history", "oriental", "it", "academic", "other", "book"];

export default function SubjectsPage() {
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [editing, setEditing] = useState<Partial<Subject> | null>(null);
  const [deleting, setDeleting] = useState<Subject | null>(null);
  const [wordFor, setWordFor] = useState<number | null>(null);

  const load = () => adminApi.subjects().then(setSubjects).catch((e: ApiError) => toast.error(e.message));
  useEffect(() => {
    void load();
  }, []);

  if (!subjects) return <Loader />;
  const roots = subjects.filter((s) => !s.parent).sort((a, b) => Number(b.is_academic) - Number(a.is_academic));
  const childrenOf = (id: number) => subjects.filter((s) => s.parent === id);
  const academicTotal = subjects.find((s) => s.is_academic)?.question_counts.total ?? 0;
  const card = (s: Subject) => (
    <SubjectCard
      key={s.id}
      subject={s}
      academicTotal={academicTotal}
      onEdit={() => setEditing(s)}
      onDelete={() => setDeleting(s)}
      onWord={() => setWordFor(s.id)}
      onSaved={load}
    />
  );

  return (
    <div className="admin-page">
      <div className="page-head">
        <div>
          <h1>Fanlar va bosqichlar</h1>
          <p className="muted">
            1-bosqich odatda barcha fanlar uchun umumiy «Akademik test», 2-bosqich esa fanning o'z testi. Savollar soni,
            vaqt va savollar manbaini shu yerda belgilang.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setEditing({ name: "", slug: "", icon: "book", is_active: true, is_academic: false, sort_order: 0, parent: null, description: "" })}>
          <Icon name="plus" size={18} /> Yangi fan
        </button>
      </div>

      <div className="subject-list">
        {roots.map((s) => (
          <div key={s.id}>
            {card(s)}
            {childrenOf(s.id).length > 0 && <div className="subject-children">{childrenOf(s.id).map(card)}</div>}
          </div>
        ))}
      </div>

      {editing && (
        <SubjectForm
          subject={editing}
          groups={subjects.filter((s) => !s.parent && !s.is_academic && s.id !== editing.id && (s.is_group || s.question_counts.total === 0))}
          academicExists={subjects.some((s) => s.is_academic && s.id !== editing.id)}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void load();
          }}
        />
      )}

      <WordImportModal
        open={wordFor !== null}
        subjects={subjects}
        initialSubject={wordFor ?? undefined}
        onClose={() => setWordFor(null)}
        onDone={load}
      />

      <ConfirmDialog
        open={!!deleting}
        title="Fanni o'chirasizmi?"
        danger
        confirmLabel="O'chirish"
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          try {
            await adminApi.deleteSubject(deleting.id);
            toast.success("Fan o'chirildi");
            setDeleting(null);
            void load();
          } catch (e) {
            toast.error((e as ApiError).message);
          }
        }}
      >
        <p className="muted">Savollari yoki natijalari bor fanni o'chirib bo'lmaydi — uni nofaol qiling.</p>
      </ConfirmDialog>
    </div>
  );
}

function SubjectCard({ subject, academicTotal, onEdit, onDelete, onWord, onSaved }: {
  subject: Subject;
  academicTotal: number;
  onEdit: () => void;
  onDelete: () => void;
  onWord: () => void;
  onSaved: () => void;
}) {
  const [stages, setStages] = useState<StageConfig[]>(subject.stages);
  const [busy, setBusy] = useState(false);
  const dirty = JSON.stringify(stages) !== JSON.stringify(subject.stages);
  useEffect(() => setStages(subject.stages), [subject.stages]);

  const update = (n: number, patch: Partial<StageConfig>) => setStages((cur) => cur.map((s) => (s.number === n ? { ...s, ...patch } : s)));
  const addStage2 = () =>
    setStages((cur) => [...cur, { number: 2, title: "Fan testi", question_count: 30, duration_minutes: 40, source: "subject", is_enabled: true }]);

  const save = async () => {
    setBusy(true);
    try {
      await adminApi.saveSubject({ id: subject.id, stages });
      toast.success("Bosqich sozlamalari saqlandi");
      onSaved();
    } catch (e) {
      toast.error(firstErrorMessage((e as ApiError).data, (e as ApiError).message));
    } finally {
      setBusy(false);
    }
  };

  const toggleActive = async () => {
    try {
      await adminApi.saveSubject({ id: subject.id, is_active: !subject.is_active });
      onSaved();
    } catch (e) {
      toast.error((e as ApiError).message);
    }
  };

  return (
    <div className={`glass subject-admin-card${subject.is_active ? "" : " dim"}`}>
      <div className="panel-row">
        <div className="subject-head">
          <SubjectGlyph icon={subject.icon} size={42} />
          <div>
            <h3>
              {subject.name}
              {subject.is_academic && <span className="badge-academic">umumiy bank</span>}
            </h3>
            <span className="tiny">
              kod: {subject.slug}
              {subject.is_group ? " · guruh (yo'nalishlarga bo'linadi)" : ` · savollar: ${subject.question_counts.total}`}
            </span>
          </div>
        </div>
        <div className="head-actions">
          {!subject.is_group && (
            <button className="btn btn-sm" onClick={onWord} title="Word fayldan savollar qo'shish">
              <Icon name="upload" size={14} /> Word orqali test
            </button>
          )}
          <button className={`switch${subject.is_active ? " on" : ""}`} onClick={toggleActive} title="Faol" aria-label="Faol" />
          <button className="icon-btn" onClick={onEdit} aria-label="Tahrirlash"><Icon name="edit" size={16} /></button>
          <button className="icon-btn" onClick={onDelete} aria-label="O'chirish"><Icon name="trash" size={16} /></button>
        </div>
      </div>
      {subject.is_academic && (
        <div className="academic-note">
          Bu umumiy savollar banki. «Savollar manbai: Akademik test banki» deb belgilangan bosqichlar (odatda barcha
          fanlarning 1-bosqichi) savollarni shu yerdan tasodifiy oladi. Bankda {subject.question_counts.total} ta faol savol bor.
        </div>
      )}
      {!subject.is_group && !subject.is_academic && (
        <>
          <div className="stage-editor">
            {stages
              .slice()
              .sort((a, b) => a.number - b.number)
              .map((s) => {
                const available = s.source === "academic" ? academicTotal : subject.question_counts[String(s.number)] ?? 0;
                return (
                  <div key={s.number} className={`stage-edit${s.is_enabled ? "" : " dim"}`}>
                    <div className="panel-row">
                      <strong>{s.number}-bosqich</strong>
                      <label className="checkbox tiny">
                        <button type="button" className={`switch${s.is_enabled ? " on" : ""}`} onClick={() => update(s.number, { is_enabled: !s.is_enabled })} />
                        {s.is_enabled ? "Yoqilgan" : "O'chirilgan"}
                      </label>
                    </div>
                    <div className="stage-fields">
                      <label className="field field-wide">
                        <span className="label">Savollar manbai</span>
                        <select className="select" value={s.source} onChange={(e) => update(s.number, { source: e.target.value as StageConfig["source"] })}>
                          <option value="academic">Akademik test banki</option>
                          <option value="subject">Fanning o'z savollari</option>
                        </select>
                      </label>
                      <label className="field">
                        <span className="label">Nomi</span>
                        <input className="input" value={s.title} onChange={(e) => update(s.number, { title: e.target.value })} />
                      </label>
                      <label className="field">
                        <span className="label">Savollar soni</span>
                        <input type="number" min={1} max={200} className="input" value={s.question_count} onChange={(e) => update(s.number, { question_count: Number(e.target.value) || 1 })} />
                      </label>
                      <label className="field">
                        <span className="label">Vaqt (daqiqa)</span>
                        <input type="number" min={1} max={600} className="input" value={s.duration_minutes} onChange={(e) => update(s.number, { duration_minutes: Number(e.target.value) || 1 })} />
                      </label>
                    </div>
                    <span className={`tiny ${available < s.question_count ? "warn-text" : ""}`}>
                      {s.source === "academic" ? "Akademik bankda" : "Bazada"} faol savollar: {available}{" "}
                      {available < s.question_count ? `(kamida ${s.question_count} ta kerak)` : ""}
                    </span>
                  </div>
                );
              })}
          </div>
          <div className="head-actions" style={{ justifyContent: "flex-end" }}>
            {!stages.some((s) => s.number === 2) && (
              <button className="btn btn-sm" onClick={addStage2}><Icon name="plus" size={14} /> 2-bosqich qo'shish</button>
            )}
            {dirty && (
              <>
                <button className="btn btn-sm" onClick={() => setStages(subject.stages)}>Bekor qilish</button>
                <button className="btn btn-sm btn-primary" onClick={save} disabled={busy}>
                  <Icon name="check" size={14} /> Saqlash
                </button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SubjectForm({ subject, groups, academicExists, onClose, onSaved }: {
  subject: Partial<Subject>;
  groups: Subject[];
  academicExists: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [s, setS] = useState(subject);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const payload: Partial<Subject> = { ...s };
      delete payload.stages;
      delete payload.question_counts;
      await adminApi.saveSubject(payload);
      toast.success("Saqlandi");
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
      title={s.id ? "Fanni tahrirlash" : "Yangi fan"}
      width={600}
      footer={
        <>
          <button className="btn" onClick={onClose}>Bekor qilish</button>
          <button className="btn btn-primary" onClick={save} disabled={busy}>
            <Icon name="check" size={18} /> Saqlash
          </button>
        </>
      }
    >
      <div className="form-grid">
        <div className="field span-2">
          <label>Nomi</label>
          <input className="input" value={s.name ?? ""} onChange={(e) => setS({ ...s, name: e.target.value })} />
        </div>
        <div className="field span-2">
          <label>Kod (lotin harflari, masalan: physics)</label>
          <input className="input" value={s.slug ?? ""} onChange={(e) => setS({ ...s, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })} />
        </div>
        <div className="field span-2">
          <label>Asosiy fan (guruh)</label>
          <select className="select" value={s.parent ?? ""} onChange={(e) => setS({ ...s, parent: e.target.value ? Number(e.target.value) : null })}>
            <option value="">— Mustaqil fan —</option>
            {groups.map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </div>
        {(s.is_academic || !academicExists) && !s.parent && (
          <div className="field span-4">
            <label className="checkbox">
              <button type="button" className={`switch${s.is_academic ? " on" : ""}`} onClick={() => setS({ ...s, is_academic: !s.is_academic })} />
              Akademik test banki (barcha fanlar uchun umumiy, kirish sahifasida ko'rinmaydi)
            </label>
          </div>
        )}
        <div className="field">
          <label>Tartib</label>
          <input type="number" className="input" value={s.sort_order ?? 0} onChange={(e) => setS({ ...s, sort_order: Number(e.target.value) || 0 })} />
        </div>
        <div className="field">
          <label>Faol</label>
          <label className="checkbox" style={{ minHeight: 48 }}>
            <button type="button" className={`switch${s.is_active ? " on" : ""}`} onClick={() => setS({ ...s, is_active: !s.is_active })} />
          </label>
        </div>
        <div className="field span-4">
          <label>Qisqa tavsif</label>
          <input className="input" value={s.description ?? ""} onChange={(e) => setS({ ...s, description: e.target.value })} />
        </div>
        <div className="field span-4">
          <label>Ikonka</label>
          <div className="icon-picker">
            {ICONS.map((i) => (
              <button key={i} type="button" className={`icon-pick${s.icon === i ? " active" : ""}`} onClick={() => setS({ ...s, icon: i })}>
                <SubjectGlyph icon={i} size={36} />
              </button>
            ))}
          </div>
        </div>
      </div>
      {!s.id && !s.is_academic && (
        <p className="tiny" style={{ marginTop: 10 }}>
          Yangi fanga avtomatik 2 ta bosqich qo'shiladi: 1-bosqich «Akademik test» (20 savol, umumiy bankdan) va 2-bosqich
          «Fan testi» (30 savol). Keyin «Word orqali test» tugmasi bilan fanga savollar biriktiring.
        </p>
      )}
      {error && <div className="alert" style={{ marginTop: 12 }}>{error}</div>}
    </Modal>
  );
}
