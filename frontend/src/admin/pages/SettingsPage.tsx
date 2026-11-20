import { useEffect, useState } from "react";

import type { ApiError } from "../../api/http";
import { Icon } from "../../components/Icon";
import { Loader } from "../../components/Loader";
import { toast } from "../../components/Toast";
import { adminApi, type SiteSettings } from "../api";

const toggles: { key: keyof SiteSettings; title: string; text: string }[] = [
  { key: "registration_open", title: "Test topshirish ochiq", text: "O'chirilsa, yangi foydalanuvchilar testni boshlay olmaydi." },
  { key: "show_score", title: "Natijani foydalanuvchiga ko'rsatish", text: "Test oxirida ball va to'g'ri javoblar soni ko'rsatiladi." },
  { key: "show_answer_review", title: "Javoblar kalitini ko'rsatish", text: "Test oxirida har bir savol bo'yicha to'g'ri javob ko'rsatiladi." },
  { key: "allow_retake", title: "Hamma uchun qayta topshirish", text: "O'chiq bo'lsa, qayta topshirishga faqat natija sahifasidan alohida ruxsat beriladi." },
];

export default function SettingsPage() {
  const [s, setS] = useState<SiteSettings | null>(null);
  const [title, setTitle] = useState("");
  useEffect(() => {
    adminApi.settings().then((d) => { setS(d); setTitle(d.site_title); }).catch((e: ApiError) => toast.error(e.message));
  }, []);

  const save = async (patch: Partial<SiteSettings>) => {
    try {
      const d = await adminApi.saveSettings(patch);
      setS(d);
      toast.success("Sozlama saqlandi");
    } catch (e) {
      toast.error((e as ApiError).message);
    }
  };

  if (!s) return <Loader />;
  return (
    <div className="admin-page narrow">
      <div className="page-head">
        <div>
          <h1>Sozlamalar</h1>
          <p className="muted">Platforma bo'yicha umumiy sozlamalar</p>
        </div>
      </div>
      <div className="glass panel settings">
        <div className="field">
          <label>Sayt nomi</label>
          <div className="inline-form">
            <input className="input" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} />
            <button className="btn btn-primary" disabled={title === s.site_title || !title.trim()} onClick={() => save({ site_title: title.trim() })}>
              <Icon name="check" size={18} /> Saqlash
            </button>
          </div>
        </div>
        {toggles.map((t) => (
          <div key={t.key} className="setting-row">
            <div>
              <strong>{t.title}</strong>
              <p className="muted tiny">{t.text}</p>
            </div>
            <button className={`switch${s[t.key] ? " on" : ""}`} onClick={() => save({ [t.key]: !s[t.key] })} aria-label={t.title} />
          </div>
        ))}
      </div>
      <p className="tiny" style={{ marginTop: 14 }}>
        Test vaqti va savollar soni «Fanlar va bosqichlar» bo'limida har bir fan uchun alohida belgilanadi.
      </p>
    </div>
  );
}
