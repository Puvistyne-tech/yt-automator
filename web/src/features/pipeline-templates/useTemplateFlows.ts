import { useNavigate } from "react-router";
import { pipelinePath } from "@/api/paths";
import { useDeleteTemplate, useDuplicateTemplate } from "@/api/templates";
import type { DuplicateTemplateRequest, TemplateSummary } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  type TemplateErrors,
  useTemplateErrors,
} from "@/features/pipeline-templates/useTemplateErrors";
import { type ConfirmTarget, useConfirmTarget } from "@/shared/ui";

export interface TemplateFlow<V> {
  confirm: ConfirmTarget<TemplateSummary>;
  problems: TemplateErrors;
  ask: (template: TemplateSummary) => void;
  submit: (template: TemplateSummary, vars: V) => void;
  busy: boolean;
}

function useAskedTarget() {
  const confirm = useConfirmTarget<TemplateSummary>();
  const problems = useTemplateErrors();
  const ask = (template: TemplateSummary) => {
    problems.clear();
    confirm.ask(template);
  };
  return { confirm, problems, ask };
}

export function useDeleteTemplateFlow(onDeleted?: () => void): TemplateFlow<void> {
  const asked = useAskedTarget();
  const mutation = useDeleteTemplate();
  const notifier = useMutationNotifier();
  const submit = (target: TemplateSummary) => {
    mutation.mutate(target.id, {
      onSuccess: () => {
        notifier.succeed(`Deleted “${target.name}”.`);
        asked.confirm.cancel();
        onDeleted?.();
      },
      onError: asked.problems.report,
    });
  };
  return { ...asked, submit, busy: mutation.isPending };
}

export function useDuplicateTemplateFlow(): TemplateFlow<DuplicateTemplateRequest> {
  const asked = useAskedTarget();
  const mutation = useDuplicateTemplate();
  const notifier = useMutationNotifier();
  const navigate = useNavigate();
  const submit = (target: TemplateSummary, request: DuplicateTemplateRequest) => {
    mutation.mutate(
      { id: target.id, request },
      {
        onSuccess: (copy) => {
          notifier.succeed(`Created “${copy.name}”.`);
          asked.confirm.cancel();
          void navigate(pipelinePath(copy.id));
        },
        onError: asked.problems.report,
      },
    );
  };
  return { ...asked, submit, busy: mutation.isPending };
}
