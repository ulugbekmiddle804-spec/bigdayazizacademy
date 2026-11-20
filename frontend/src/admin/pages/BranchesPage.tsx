import { useEffect, useState } from "react";

import { firstErrorMessage, type ApiError } from "../../api/http";
import { Icon } from "../../components/Icon";
import { Loader } from "../../components/Loader";
import { Modal } from "../../components/Modal";
import { toast } from "../../components/Toast";
import { adminApi, type Branch } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";

export default function BranchesPage() {
  const [items, setItems] = useState<Branch[] | null>(null);
  const [editing, setEditing] = useState<Partial<Branch> | null>(null);
  const [deleting, setDeleting] = useState<Branch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => adminApi.branches().then(setItems).catch((e: ApiError) => toast.error(e.message));
  useEffect(() => {
    void load();
  }, []);

  const save = async () => {
    if (!editing) return;
    setBusy(true);
    setError(null);
    try {
      await adminApi.saveBranch(editing);
      toast.success("Saqlandi");
      setEditing(null);
      void load();
    } catch (e) {
      setError(firstErrorMessage((e as ApiError).data, (e as ApiError).message));
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (b: Branch) => {
    try {
      await adminApi.saveBranch({ id: b.id, is_active: !b.is_active });
      void load();
    } catch (e) {
      toast.error((e as ApiError).message);
    }
  };

  if (!items) return <Loader />;

  return (
    <div className="admin-page">
      <div className="page-head">
        <div>
          <h1>Filiallar</h1>
          <p className="muted">{items.length} ta filial</p>
        </div>
        <button className="btn btn-primary" onClick={() => { setError(null); setEditing({ name: "", address: "", is_active: true, sort_order: items.length }); }}>
          <Icon name="plus" size={18} /> Yangi filial
        </button>
      </div>
      <div className="glass table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Nomi</th>
              <th>Manzil</th>
              <th className="num">Testlar</th>
              <th className="num">Tartib</th>
              <th>Faol</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((b) => (
              <tr key={b.id} className={b.is_active ? "" : "dim"}>
                <td><strong>{b.name}</strong></td>
                <td className="muted">{b.address || "—"}</td>
                <td className="num">{b.attempts_count}</td>
                <td className="num">{b.sort_order}</td>
                <td><button className={`switch${b.is_active ? " on" : ""}`} onClick={() => toggle(b)} aria-label="Faol" /></td>
                <td className="row-actions">
                  <button className="icon-btn" onClick={() => { setError(null); setEditing(b); }} aria-label="Tahrirlash"><Icon name="edit" size={16} /></button>
                  <button className="icon-btn" onClick={() => setDeleting(b)} aria-label="O'chirish"><Icon name="trash" size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={editing?.id ? "Filialni tahrirlash" : "Yangi filial"}
        footer={
          <>
            <button className="btn" onClick={() => setEditing(null)}>Bekor qilish</button>
            <button className="btn btn-primary" onClick={save} disabled={busy}><Icon name="check" size={18} /> Saqlash</button>
          </>
        }
      >
        {editing && (
          <div className="form-grid">
            <div className="field span-4">
              <label>Nomi</label>
              <input className="input" value={editing.name ?? ""} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
            </div>
            <div className="field span-4">
              <label>Manzil</label>
              <input className="input" value={editing.address ?? ""} onChange={(e) => setEditing({ ...editing, address: e.target.value })} />
            </div>
            <div className="field span-2">
              <label>Tartib raqami</label>
              <input type="number" className="input" value={editing.sort_order ?? 0} onChange={(e) => setEditing({ ...editing, sort_order: Number(e.target.value) || 0 })} />
            </div>
            <div className="field span-2">
              <label>Faol</label>
              <label className="checkbox" style={{ minHeight: 48 }}>
                <button type="button" className={`switch${editing.is_active ? " on" : ""}`} onClick={() => setEditing({ ...editing, is_active: !editing.is_active })} />
              </label>
            </div>
          </div>
        )}
        {error && <div className="alert" style={{ marginTop: 12 }}>{error}</div>}
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        title="Filialni o'chirasizmi?"
        danger
        confirmLabel="O'chirish"
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          if (!deleting) return;
          try {
            await adminApi.deleteBranch(deleting.id);
            toast.success("Filial o'chirildi");
            setDeleting(null);
            void load();
          } catch (e) {
            toast.error((e as ApiError).message);
          }
        }}
      >
        <p className="muted">Natijalari bor filialni o'chirib bo'lmaydi — uni nofaol qiling.</p>
      </ConfirmDialog>
    </div>
  );
}
