import { useState } from "react";
import type { FieldErrors } from "@/api/errors";
import { pipelinePath } from "@/api/paths";
import { useSaveTemplate } from "@/api/templates";
import type { JsonObject, TemplateStatus, TemplateSummary } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  draftFromTemplate,
  draftProblems,
  settledDraft,
  type TemplateDraft,
  templateInput,
} from "@/features/pipeline-templates/model/form";
import { useTemplateErrors } from "@/features/pipeline-templates/useTemplateErrors";
import { useDraftState } from "@/shared/hooks/useDraftState";
import { useNavigateAfterCreate } from "@/shared/hooks/useNavigateAfterCreate";

interface EditorInput {
  engineId: string;
  definitionSchema: JsonObject;
  template: TemplateSummary | undefined;
  initial: TemplateDraft;
  onErrorsShown: (errors: FieldErrors) => void;
}

export function useTemplateEditor(input: EditorInput) {
  const { engineId, template, definitionSchema } = input;
  const settled = (next: TemplateDraft) => settledDraft(next, definitionSchema);
  const [start] = useState(() => settled(input.initial));
  const { draft, setDraft, dirty, markSaved } = useDraftState(start, JSON.stringify);
  const problems = useTemplateErrors(input.onErrorsShown);
  const save = useSaveTemplate(template?.id);
  const notifier = useMutationNotifier();
  const onCreated = useNavigateAfterCreate(dirty, pipelinePath);
  const update = (next: TemplateDraft) => {
    setDraft(next);
    problems.clear();
  };
  const onSaved = (saved: TemplateSummary) => {
    notifier.succeed(`Saved “${saved.name}”.`);
    markSaved(settled(draftFromTemplate(saved)));
    if (template === undefined) {
      onCreated(saved.id);
    }
  };
  const submit = (status: TemplateStatus) => {
    if (!problems.validate(draftProblems(draft))) {
      notifier.warn("Fix the highlighted fields before saving.");
      return;
    }
    save.mutate(templateInput(draft, engineId, status), {
      onSuccess: onSaved,
      onError: problems.report,
    });
  };
  return { draft, update, dirty, problems, saving: save.isPending, submit };
}

export type TemplateEditorState = ReturnType<typeof useTemplateEditor>;
