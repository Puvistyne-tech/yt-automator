import type { ReactNode } from "react";
import { Button } from "@/shared/ui/Button";
import { UnsavedChangesPrompt } from "@/shared/ui/UnsavedChangesPrompt";

interface SaveBarProps {
  dirty: boolean;
  saving: boolean;
  saveLabel: string;
  onSave: () => void;
  onReset?: () => void;
  saveDisabled?: boolean;
  className?: string;
  children?: ReactNode;
}

export function SaveBar({
  dirty,
  saving,
  saveLabel,
  onSave,
  onReset,
  saveDisabled = !dirty,
  className,
  children,
}: SaveBarProps) {
  return (
    <>
      <div className={["action-bar", className].filter(Boolean).join(" ")}>
        <span className="action-bar-status" aria-live="polite">
          {dirty ? "Unsaved changes" : "All changes saved"}
        </span>
        {children}
        {onReset && (
          <Button disabled={!dirty} onClick={onReset}>
            Reset
          </Button>
        )}
        <Button
          variant="primary"
          icon="check"
          disabled={saveDisabled}
          loading={saving}
          onClick={onSave}
        >
          {saveLabel}
        </Button>
      </div>
      <UnsavedChangesPrompt when={dirty && !saving} />
    </>
  );
}
