import { useMemo, useState } from "react";
import type { FieldErrors } from "@/api/errors";
import type { Channel, PipelineDescriptor } from "@/api/types";
import { type FieldErrorState, useFieldErrors } from "@/api/useFieldErrors";
import type { AutomationDraft } from "@/features/automation-editor/model/draft";
import { validateDraft } from "@/features/automation-editor/model/validate";
import { validateSchemaData } from "@/shared/schema-form/errors";

export interface EditorErrors {
  clientErrors: FieldErrors;
  errors: FieldErrors;
  reveal: () => void;
  server: FieldErrorState;
}

export function useEditorErrors(
  draft: AutomationDraft,
  pipeline: PipelineDescriptor | undefined,
  channels: Channel[],
): EditorErrors {
  const [shown, setShown] = useState(false);
  const server = useFieldErrors();
  const clientErrors = useMemo(() => {
    const settingsErrors = pipeline
      ? validateSchemaData(pipeline.settings_schema, draft.settings)
      : {};
    return validateDraft(draft, { pipeline, channels, settingsErrors });
  }, [draft, pipeline, channels]);
  const errors = shown ? { ...clientErrors, ...server.errors } : server.errors;
  return { clientErrors, errors, reveal: () => setShown(true), server };
}
