import { useCallback, useState } from "react";
import type { FieldErrors } from "@/api/errors";
import { useFieldErrors } from "@/api/useFieldErrors";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { type ConflictNotice, conflictNotice } from "@/features/pipeline-templates/model/conflicts";

export interface TemplateErrors {
  errors: FieldErrors;
  conflict: ConflictNotice | null;
  validate: (problems: FieldErrors) => boolean;
  report: (error: unknown) => void;
  clear: () => void;
}

export function useTemplateErrors(): TemplateErrors {
  const notifier = useMutationNotifier();
  const fields = useFieldErrors();
  const [conflict, setConflict] = useState<ConflictNotice | null>(null);
  const { clear: clearFields, setFromServer } = fields;
  const clear = useCallback(() => {
    clearFields();
    setConflict(null);
  }, [clearFields]);
  const report = (error: unknown) => {
    const notice = conflictNotice(error);
    setConflict(notice);
    setFromServer(error);
    if (notice === null) {
      notifier.fail(error);
    }
  };
  return { errors: fields.errors, conflict, validate: fields.validate, report, clear };
}
