import { AnimatePresence, m } from "framer-motion";
import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { Icon } from "./Icon";

interface Props {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: number;
  dismissible?: boolean;
}

export function Modal({ open, onClose, title, children, footer, width = 520, dismissible = true }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && dismissible) onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose, dismissible]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <m.div
          className="modal-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && dismissible) onClose();
          }}
        >
          <m.div
            role="dialog"
            aria-modal="true"
            className="modal glass"
            style={{ maxWidth: width }}
            initial={{ opacity: 0, y: 30, scale: 0.96, rotateX: 8 }}
            animate={{ opacity: 1, y: 0, scale: 1, rotateX: 0 }}
            exit={{ opacity: 0, y: 20, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
          >
            {(title || dismissible) && (
              <div className="modal-head">
                <h3>{title}</h3>
                {dismissible && (
                  <button className="icon-btn" onClick={onClose} aria-label="Yopish">
                    <Icon name="x" size={18} />
                  </button>
                )}
              </div>
            )}
            <div className="modal-body">{children}</div>
            {footer && <div className="modal-foot">{footer}</div>}
          </m.div>
        </m.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
