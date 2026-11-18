import type { ReactNode } from "react";
import { Dialog } from "@/shared/ui/Dialog";
import { DialogActions } from "@/shared/ui/DialogActions";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: ReactNode;
  confirmLabel: string;
  cancelLabel?: string;
  tone?: "danger" | "primary";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  tone = "danger",
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      title={title}
      onClose={onCancel}
      size="sm"
      footer={
        <DialogActions
          submitLabel={confirmLabel}
          cancelLabel={cancelLabel}
          tone={tone}
          busy={busy}
          onSubmit={onConfirm}
          onCancel={onCancel}
        />
      }
    >
      <div className="confirm-message">{message}</div>
    </Dialog>
  );
}
