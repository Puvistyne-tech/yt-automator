import type { ReactNode } from "react";
import { Dialog } from "@/shared/ui/Dialog";
import { DialogActions, type DialogActionsProps } from "@/shared/ui/DialogActions";

type FormDialogProps = Omit<DialogActionsProps, "onCancel" | "tone"> & {
  open?: boolean;
  title: string;
  description?: ReactNode;
  onClose: () => void;
  children: ReactNode;
};

export function FormDialog({
  open = true,
  title,
  description,
  onClose,
  children,
  ...actions
}: FormDialogProps) {
  return (
    <Dialog
      open={open}
      title={title}
      description={description}
      onClose={onClose}
      footer={<DialogActions {...actions} onCancel={onClose} />}
    >
      {children}
    </Dialog>
  );
}
