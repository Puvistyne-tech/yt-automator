import { type ReactNode, useId } from "react";

export interface CheckboxOption {
  value: string;
  label: string;
  description?: string | undefined;
  disabled?: boolean | undefined;
}

interface CheckboxGroupProps {
  label: ReactNode;
  options: CheckboxOption[];
  value: string[];
  onChange: (value: string[]) => void;
  error?: string | undefined;
  hint?: ReactNode;
  layout?: "inline" | "cards";
}

function toggle(values: string[], value: string, options: CheckboxOption[]): string[] {
  const next = values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
  return options.map((option) => option.value).filter((v) => next.includes(v));
}

function CheckboxChoice({
  option,
  checked,
  onToggle,
}: {
  option: CheckboxOption;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <label className="checkbox-option">
      <input type="checkbox" checked={checked} disabled={option.disabled} onChange={onToggle} />
      <span className="checkbox-text">
        <span>{option.label}</span>
        {option.description && <span className="subtle">{option.description}</span>}
      </span>
    </label>
  );
}

export function CheckboxGroup({
  label,
  options,
  value,
  onChange,
  error,
  hint,
  layout = "inline",
}: CheckboxGroupProps) {
  const id = useId();
  return (
    <fieldset
      className={["checkbox-group", `checkbox-group-${layout}`, error && "field-invalid"]
        .filter(Boolean)
        .join(" ")}
      aria-describedby={error ? `${id}-error` : undefined}
    >
      <legend className="field-label">{label}</legend>
      {hint && <p className="field-hint">{hint}</p>}
      <div className="checkbox-options">
        {options.map((option) => (
          <CheckboxChoice
            key={option.value}
            option={option}
            checked={value.includes(option.value)}
            onToggle={() => onChange(toggle(value, option.value, options))}
          />
        ))}
      </div>
      {error && (
        <p className="field-error" id={`${id}-error`} role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
