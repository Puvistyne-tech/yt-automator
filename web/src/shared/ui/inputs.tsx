import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { useFieldControl } from "@/shared/ui/FormField";

export function Input({ className, id, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  const control = useFieldControl(id);
  return (
    <input className={["input", className].filter(Boolean).join(" ")} {...control} {...rest} />
  );
}

export function Textarea({ className, id, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const control = useFieldControl(id);
  return (
    <textarea
      className={["input", "textarea", className].filter(Boolean).join(" ")}
      {...control}
      {...rest}
    />
  );
}

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  options: SelectOption[];
  placeholder?: string;
  children?: ReactNode;
};

export function Select({ className, id, options, placeholder, ...rest }: SelectProps) {
  const control = useFieldControl(id);
  return (
    <select
      className={["input", "select", className].filter(Boolean).join(" ")}
      {...control}
      {...rest}
    >
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((option) => (
        <option key={option.value} value={option.value} disabled={option.disabled}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
