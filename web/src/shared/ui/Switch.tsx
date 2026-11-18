import { type ReactNode, useId } from "react";
import { useFieldControl } from "@/shared/ui/FormField";

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: ReactNode;
  ariaLabel?: string;
  disabled?: boolean;
  id?: string;
}

export function Switch({ checked, onChange, label, ariaLabel, disabled = false, id }: SwitchProps) {
  const field = useFieldControl(id);
  const fallbackId = useId();
  const control = { ...field, id: field.id ?? fallbackId };
  return (
    <span className="switch-wrap">
      <button
        type="button"
        role="switch"
        className="switch"
        aria-checked={checked}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        {...control}
      >
        <span className="switch-thumb" />
      </button>
      {label !== undefined && (
        <label className="switch-label" htmlFor={control.id}>
          {label}
        </label>
      )}
    </span>
  );
}
