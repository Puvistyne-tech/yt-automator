import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { useSaveAutomation } from "@/api/automations";
import { errorMessage, type FieldErrors, fieldErrorsOf, normalizeFieldErrors } from "@/api/errors";
import type { Automation, Channel, PipelineDescriptor } from "@/api/types";
import {
  type AutomationDraft,
  draftSignature,
  draftToInput,
} from "@/features/automation-editor/model/draft";
import { firstErrorSection, sectionAnchor } from "@/features/automation-editor/model/sections";
import { validateDraft } from "@/features/automation-editor/model/validate";
import { validateSchemaData } from "@/shared/schema-form/errors";
import { useToast } from "@/shared/ui";

interface EditorInput {
  automationId: string | undefined;
  initial: AutomationDraft;
  pipelines: PipelineDescriptor[];
  channels: Channel[];
}

function scrollToSection(errors: FieldErrors) {
  const section = firstErrorSection(errors);
  if (section !== null) {
    document.getElementById(sectionAnchor(section))?.scrollIntoView?.({ behavior: "smooth" });
  }
}

export function useAutomationEditor({ automationId, initial, pipelines, channels }: EditorInput) {
  const [draft, setDraft] = useState(initial);
  const [baseline, setBaseline] = useState(() => draftSignature(initial));
  const [showErrors, setShowErrors] = useState(false);
  const [serverErrors, setServerErrors] = useState<FieldErrors>({});
  const [createdId, setCreatedId] = useState<string | null>(null);
  const save = useSaveAutomation(automationId);
  const toast = useToast();
  const navigate = useNavigate();
  const pipeline = pipelines.find((p) => p.type_id === draft.pipeline_type);

  const clientErrors = useMemo(() => {
    const settingsErrors = pipeline
      ? validateSchemaData(pipeline.settings_schema, draft.settings)
      : {};
    return validateDraft(draft, { pipeline, channels, settingsErrors });
  }, [draft, pipeline, channels]);

  const errors = showErrors ? { ...clientErrors, ...serverErrors } : serverErrors;
  const dirty = draftSignature(draft) !== baseline;

  useEffect(() => {
    if (createdId !== null && !dirty) {
      navigate(`/automations/${createdId}`, { replace: true });
    }
  }, [createdId, dirty, navigate]);

  const update = (next: AutomationDraft) => {
    setDraft(next);
    setServerErrors({});
  };

  const onSaved = (saved: Automation) => {
    setBaseline(draftSignature(draft));
    toast.success(`Saved “${saved.name}”.`);
    if (automationId === undefined) {
      setCreatedId(saved.id);
    }
  };

  const onFailed = (error: unknown) => {
    const fields = normalizeFieldErrors(fieldErrorsOf(error));
    setServerErrors(fields);
    toast.error(errorMessage(error));
    scrollToSection(fields);
  };

  const submit = () => {
    setShowErrors(true);
    if (Object.keys(clientErrors).length > 0) {
      toast.error("Fix the highlighted fields before saving.");
      scrollToSection(clientErrors);
      return;
    }
    save.mutate(draftToInput(draft, pipeline), { onSuccess: onSaved, onError: onFailed });
  };

  return { draft, update, pipeline, errors, dirty, saving: save.isPending, submit };
}

export type AutomationEditorState = ReturnType<typeof useAutomationEditor>;
