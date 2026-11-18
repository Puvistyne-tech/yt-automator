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
          <label key={option.value} className="checkbox-option">
            <input
              type="checkbox"
              checked={value.includes(option.value)}
              disabled={option.disabled}
              onChange={() => onChange(toggle(value, option.value, options))}
            />
            <span className="checkbox-text">
              <span>{option.label}</span>
              {option.description && <span className="subtle">{option.description}</span>}
            </span>
          </label>
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
