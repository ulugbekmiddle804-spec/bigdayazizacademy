import { useState, type ReactNode } from "react";

import { Modal } from "../../components/Modal";

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel = "Tasdiqlash",
  danger = false,
  disabled = false,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  children?: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  disabled?: boolean;
  onConfirm: () => Promise<void> | void;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      width={440}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={busy}>
            Bekor qilish
          </button>
          <button
            className={`btn ${danger ? "btn-danger" : "btn-primary"}`}
            disabled={busy || disabled}
            onClick={async () => {
              setBusy(true);
              try {
                await onConfirm();
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy && <span className="spinner tiny-spinner" />} {confirmLabel}
          </button>
        </>
      }
    >
      {children}
    </Modal>
  );
}
