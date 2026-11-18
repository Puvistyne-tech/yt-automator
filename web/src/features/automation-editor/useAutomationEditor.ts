import { useState } from "react";
import { useSaveAutomation } from "@/api/automations";
import { type FieldErrors, hasErrors } from "@/api/errors";
import type { Automation, Channel, PipelineDescriptor } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  type AutomationDraft,
  draftSignature,
  draftToInput,
} from "@/features/automation-editor/model/draft";
import { firstErrorSection, sectionAnchor } from "@/features/automation-editor/model/sections";
import { useEditorErrors } from "@/features/automation-editor/useEditorErrors";
import { useNavigateAfterCreate } from "@/features/automation-editor/useNavigateAfterCreate";

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
  const pipeline = pipelines.find((p) => p.type_id === draft.pipeline_type);
  const dirty = draftSignature(draft) !== baseline;
  const editorErrors = useEditorErrors(draft, pipeline, channels);
  const onCreated = useNavigateAfterCreate(dirty);
  const save = useSaveAutomation(automationId);
  const notifier = useMutationNotifier();
  const update = (next: AutomationDraft) => {
    setDraft(next);
    editorErrors.server.clear();
  };
  const onSaved = (saved: Automation) => {
    setBaseline(draftSignature(draft));
    if (automationId === undefined) {
      onCreated(saved.id);
    }
  };
  const submit = () => {
    editorErrors.reveal();
    if (hasErrors(editorErrors.clientErrors)) {
      notifier.warn("Fix the highlighted fields before saving.");
      scrollToSection(editorErrors.clientErrors);
      return;
    }
    save.mutate(
      draftToInput(draft, pipeline),
      notifier.handlers({
        success: (saved: Automation) => `Saved “${saved.name}”.`,
        onSuccess: onSaved,
        onError: (error) => scrollToSection(editorErrors.server.setFromServer(error)),
      }),
    );
  };
  const errors = editorErrors.errors;
  return { draft, update, pipeline, errors, dirty, saving: save.isPending, submit };
}

export type AutomationEditorState = ReturnType<typeof useAutomationEditor>;
