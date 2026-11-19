import { useNavigate } from "react-router";
import { NEW_PIPELINE_PATH, newPipelineState } from "@/api/paths";
import { useSaveTemplate } from "@/api/templates";
import type { TemplateInput, TemplateSummary } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";

export function useIdeaActions(input: TemplateInput) {
  const save = useSaveTemplate(undefined);
  const notifier = useMutationNotifier();
  const navigate = useNavigate();
  const onSaved = (saved: TemplateSummary) => notifier.succeed(`Saved “${saved.name}” as a draft.`);
  return {
    use: () => void navigate(NEW_PIPELINE_PATH, { state: newPipelineState(input) }),
    saveDraft: () => save.mutate(input, { onSuccess: onSaved, onError: notifier.fail }),
    saving: save.isPending,
    saved: save.data,
  };
}

export type IdeaActions = ReturnType<typeof useIdeaActions>;
