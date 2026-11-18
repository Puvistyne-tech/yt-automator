import { createContext, type ReactNode, useContext, useId } from "react";

interface FieldControl {
  id: string;
  describedBy: string | undefined;
  invalid: boolean;
}

const FieldContext = createContext<FieldControl | null>(null);

export function useFieldControl(ownId?: string) {
  const field = useContext(FieldContext);
  return {
    id: ownId ?? field?.id,
    "aria-describedby": field?.describedBy,
    "aria-invalid": field?.invalid ? true : undefined,
  };
}

interface FormFieldProps {
  label: ReactNode;
  hint?: ReactNode;
  error?: string | undefined;
  required?: boolean;
  inline?: boolean;
  className?: string;
  children: ReactNode;
}

export function FormField({
  label,
  hint,
  error,
  required = false,
  inline = false,
  className,
  children,
}: FormFieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  const classes = ["field", inline && "field-inline", error && "field-invalid", className];
  return (
    <FieldContext.Provider value={{ id, describedBy, invalid: Boolean(error) }}>
      <div className={classes.filter(Boolean).join(" ")}>
        <label className="field-label" htmlFor={id}>
          {label}
          {required && (
            <span className="field-required" aria-hidden="true">
              *
            </span>
          )}
        </label>
        <div className="field-control">{children}</div>
        {hint && (
          <p className="field-hint" id={hintId}>
            {hint}
          </p>
        )}
        {error && (
          <p className="field-error" id={errorId} role="alert">
            {error}
          </p>
        )}
      </div>
    </FieldContext.Provider>
  );
}
