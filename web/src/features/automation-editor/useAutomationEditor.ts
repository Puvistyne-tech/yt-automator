import { useSaveAutomation } from "@/api/automations";
import { type FieldErrors, hasErrors } from "@/api/errors";
import { automationPath } from "@/api/paths";
import type { Automation, Channel, PipelineDescriptor } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  type AutomationDraft,
  draftSignature,
  draftToInput,
} from "@/features/automation-editor/model/draft";
import { firstErrorSection, sectionAnchor } from "@/features/automation-editor/model/sections";
import { useEditorErrors } from "@/features/automation-editor/useEditorErrors";
import { useDraftState } from "@/shared/hooks/useDraftState";
import { useNavigateAfterCreate } from "@/shared/hooks/useNavigateAfterCreate";

interface EditorInput {
  automationId: string | undefined;
  initial: AutomationDraft;
  pipelines: PipelineDescriptor[];
  channels: Channel[];
  onErrorsShown: (errors: FieldErrors, pipeline: PipelineDescriptor | undefined) => void;
}

function scrollToSection(errors: FieldErrors) {
  const section = firstErrorSection(errors);
  if (section !== null) {
    document.getElementById(sectionAnchor(section))?.scrollIntoView?.({ behavior: "smooth" });
  }
}

function errorRevealer(
  onErrorsShown: EditorInput["onErrorsShown"],
  pipeline: PipelineDescriptor | undefined,
) {
  return (errors: FieldErrors) => {
    onErrorsShown(errors, pipeline);
    scrollToSection(errors);
  };
}

export function useAutomationEditor(input: EditorInput) {
  const { automationId, initial, pipelines, channels, onErrorsShown } = input;
  const { draft, setDraft, dirty, markSaved } = useDraftState(initial, draftSignature);
  const pipeline = pipelines.find((p) => p.type_id === draft.pipeline_type);
  const editorErrors = useEditorErrors(draft, pipeline, channels);
  const onCreated = useNavigateAfterCreate(dirty, automationPath);
  const save = useSaveAutomation(automationId);
  const notifier = useMutationNotifier();
  const update = (next: AutomationDraft) => {
    setDraft(next);
    editorErrors.server.clear();
  };
  const onSaved = (saved: Automation) => {
    markSaved();
    if (automationId === undefined) {
      onCreated(saved.id);
    }
  };
  const showErrors = errorRevealer(onErrorsShown, pipeline);
  const submit = () => {
    editorErrors.reveal();
    if (hasErrors(editorErrors.clientErrors)) {
      notifier.warn("Fix the highlighted fields before saving.");
      showErrors(editorErrors.clientErrors);
      return;
    }
    save.mutate(
      draftToInput(draft, pipeline),
      notifier.handlers({
        success: (saved: Automation) => `Saved “${saved.name}”.`,
        onSuccess: onSaved,
        onError: (error) => showErrors(editorErrors.server.setFromServer(error)),
      }),
    );
  };
  const { errors } = editorErrors;
  return { draft, update, pipeline, errors, dirty, saving: save.isPending, submit };
}

export type AutomationEditorState = ReturnType<typeof useAutomationEditor>;
