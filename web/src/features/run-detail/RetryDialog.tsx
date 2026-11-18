import { useState } from "react";
import { useRetryRun } from "@/api/runs";
import type { Run } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { defaultRetryStage, retryStageOptions } from "@/features/run-detail/model";
import { FormDialog, FormField, Select } from "@/shared/ui";

export function RetryDialog({
  run,
  open,
  onClose,
}: {
  run: Run;
  open: boolean;
  onClose: () => void;
}) {
  const [stage, setStage] = useState(() => defaultRetryStage(run));
  const retry = useRetryRun();
  const notifier = useMutationNotifier();
  const submit = () =>
    retry.mutate(
      { id: run.id, vars: { from_stage: stage } },
      notifier.handlers({ success: "Retry queued.", onDone: onClose }),
    );
  return (
    <FormDialog
      open={open}
      title="Retry run"
      description="Stages before the chosen one keep their artifacts."
      submitLabel="Retry from stage"
      submitIcon="refresh"
      busy={retry.isPending}
      onSubmit={submit}
      onClose={onClose}
    >
      <FormField label="Start from stage">
        <Select
          value={stage}
          options={retryStageOptions(run)}
          onChange={(e) => setStage(e.target.value)}
        />
      </FormField>
    </FormDialog>
  );
}
