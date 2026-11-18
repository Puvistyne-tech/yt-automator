import { type CSSProperties, type ReactNode, useId } from "react";

export interface RadioCardOption<T extends string> {
  value: T;
  label: string;
  description?: ReactNode;
  meta?: ReactNode;
}

interface RadioCardsProps<T extends string> {
  label: string;
  hideLabel?: boolean;
  options: RadioCardOption<T>[];
  value: T | "";
  onChange: (value: T) => void;
  columns?: number;
  error?: string | undefined;
}

function RadioCard<T extends string>({
  option,
  name,
  checked,
  onSelect,
}: {
  option: RadioCardOption<T>;
  name: string;
  checked: boolean;
  onSelect: () => void;
}) {
  return (
    <label className="radio-card">
      <input type="radio" name={name} value={option.value} checked={checked} onChange={onSelect} />
      <span className="radio-card-body">
        <span className="radio-card-label">{option.label}</span>
        {option.description !== undefined && (
          <span className="radio-card-description">{option.description}</span>
        )}
        {option.meta}
      </span>
    </label>
  );
}

export function RadioCards<T extends string>({
  label,
  hideLabel = false,
  options,
  value,
  onChange,
  columns = 3,
  error,
}: RadioCardsProps<T>) {
  const name = useId();
  return (
    <fieldset className={error ? "radio-cards field-invalid" : "radio-cards"}>
      <legend className={hideLabel ? "visually-hidden" : "field-label"}>{label}</legend>
      <div className="radio-cards-grid" style={{ "--radio-columns": columns } as CSSProperties}>
        {options.map((option) => (
          <RadioCard
            key={option.value}
            option={option}
            name={name}
            checked={value === option.value}
            onSelect={() => onChange(option.value)}
          />
        ))}
      </div>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}
