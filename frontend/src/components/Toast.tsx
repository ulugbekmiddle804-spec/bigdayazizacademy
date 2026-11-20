import { AnimatePresence, m } from "framer-motion";
import { create } from "zustand";

import { Icon } from "./Icon";

type Kind = "success" | "error" | "info" | "warning";
interface ToastItem {
  id: number;
  kind: Kind;
  text: string;
}

interface ToastStore {
  items: ToastItem[];
  push: (kind: Kind, text: string, ms?: number) => void;
  remove: (id: number) => void;
}

let seq = 0;
export const useToast = create<ToastStore>((set, get) => ({
  items: [],
  push: (kind, text, ms = 3800) => {
    const id = ++seq;
    set({ items: [...get().items.slice(-3), { id, kind, text }] });
    window.setTimeout(() => get().remove(id), ms);
  },
  remove: (id) => set({ items: get().items.filter((t) => t.id !== id) }),
}));

export const toast = {
  success: (t: string) => useToast.getState().push("success", t),
  error: (t: string) => useToast.getState().push("error", t, 5500),
  info: (t: string) => useToast.getState().push("info", t),
  warning: (t: string) => useToast.getState().push("warning", t, 5500),
};

const icons = { success: "check", error: "alert", info: "sparkles", warning: "clock" } as const;

export function Toaster() {
  const items = useToast((s) => s.items);
  const remove = useToast((s) => s.remove);
  return (
    <div className="toaster" role="status" aria-live="polite">
      <AnimatePresence initial={false}>
        {items.map((t) => (
          <m.div
            key={t.id}
            layout
            className={`toast ${t.kind}`}
            initial={{ opacity: 0, y: -16, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 40 }}
            onClick={() => remove(t.id)}
          >
            <Icon name={icons[t.kind]} size={18} />
            <span>{t.text}</span>
          </m.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
