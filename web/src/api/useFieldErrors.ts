import { useCallback, useState } from "react";
import { type FieldErrors, fieldErrorsOf, hasErrors, normalizeFieldErrors } from "@/api/errors";

export interface FieldErrorState {
  errors: FieldErrors;
  validate: (problems: FieldErrors) => boolean;
  setFromServer: (error: unknown) => FieldErrors;
  clear: () => void;
}

export function useFieldErrors(): FieldErrorState {
  const [errors, setErrors] = useState<FieldErrors>({});
  const validate = useCallback((problems: FieldErrors) => {
    setErrors(problems);
    return !hasErrors(problems);
  }, []);
  const setFromServer = useCallback((error: unknown) => {
    const fields = normalizeFieldErrors(fieldErrorsOf(error));
    setErrors(fields);
    return fields;
  }, []);
  const clear = useCallback(() => setErrors({}), []);
  return { errors, validate, setFromServer, clear };
}
