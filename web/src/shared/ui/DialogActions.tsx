import { Button } from "@/shared/ui/Button";
import type { IconName } from "@/shared/ui/Icon";

export interface DialogActionsProps {
  submitLabel: string;
  cancelLabel?: string | undefined;
  submitIcon?: IconName | undefined;
  tone?: "primary" | "danger" | undefined;
  busy?: boolean | undefined;
  submitDisabled?: boolean | undefined;
  onSubmit: () => void;
  onCancel: () => void;
}

export function DialogActions({
  submitLabel,
  cancelLabel = "Cancel",
  submitIcon,
  tone = "primary",
  busy = false,
  submitDisabled = false,
  onSubmit,
  onCancel,
}: DialogActionsProps) {
  return (
    <>
      <Button onClick={onCancel}>{cancelLabel}</Button>
      <Button
        variant={tone}
        icon={submitIcon}
        loading={busy}
        disabled={submitDisabled}
        onClick={onSubmit}
      >
        {submitLabel}
      </Button>
    </>
  );
}
