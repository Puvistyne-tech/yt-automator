import { useState } from "react";
import { pipelinePath } from "@/api/paths";
import { useSaveTemplate } from "@/api/templates";
import type { TemplateStatus, TemplateSummary } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  draftFromTemplate,
  draftProblems,
  type TemplateDraft,
  templateInput,
} from "@/features/pipeline-templates/model/form";
import { useTemplateErrors } from "@/features/pipeline-templates/useTemplateErrors";
import { useNavigateAfterCreate } from "@/shared/hooks/useNavigateAfterCreate";

interface EditorInput {
  engineId: string;
  template: TemplateSummary | undefined;
  initial: TemplateDraft;
}

function useDraftState(initial: TemplateDraft) {
  const [draft, setDraft] = useState(initial);
  const [baseline, setBaseline] = useState(() => JSON.stringify(initial));
  const dirty = JSON.stringify(draft) !== baseline;
  const markSaved = (saved: TemplateDraft) => {
    setDraft(saved);
    setBaseline(JSON.stringify(saved));
  };
  return { draft, setDraft, dirty, markSaved };
}

export function useTemplateEditor({ engineId, template, initial }: EditorInput) {
  const { draft, setDraft, dirty, markSaved } = useDraftState(initial);
  const problems = useTemplateErrors();
  const save = useSaveTemplate(template?.id);
  const notifier = useMutationNotifier();
  const onCreated = useNavigateAfterCreate(dirty, pipelinePath);
  const update = (next: TemplateDraft) => {
    setDraft(next);
    problems.clear();
  };
  const onSaved = (saved: TemplateSummary) => {
    notifier.succeed(`Saved “${saved.name}”.`);
    markSaved(draftFromTemplate(saved));
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
