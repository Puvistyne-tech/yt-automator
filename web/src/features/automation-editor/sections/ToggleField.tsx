import type { ReactNode } from "react";
import { Switch } from "@/shared/ui";

interface ToggleFieldProps {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  children?: ReactNode;
}

export function ToggleField({ label, hint, checked, onChange, children }: ToggleFieldProps) {
  return (
    <div className="toggle-field">
      <Switch checked={checked} onChange={onChange} label={label} />
      <p className="field-hint toggle-field-hint">{hint}</p>
      {checked && children !== undefined && <div className="toggle-field-body">{children}</div>}
    </div>
  );
}

export function RulesSummary({ text }: { text: string }) {
  return (
    <p className="rules-summary" aria-live="polite">
      <span className="rules-summary-label">What will happen</span>
      <span>{text}</span>
    </p>
  );
}
