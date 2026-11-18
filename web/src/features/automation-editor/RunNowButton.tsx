import { useId } from "react";
import { useRunNow } from "@/api/useRunNow";
import { runNowState } from "@/features/automation-editor/model/runNow";
import { Button } from "@/shared/ui";

interface RunNowButtonProps {
  automationId: string | undefined;
  name: string;
  dirty: boolean;
}

export function RunNowButton({ automationId, name, dirty }: RunNowButtonProps) {
  const runNow = useRunNow();
  const reasonId = useId();
  const state = runNowState(automationId, dirty);
  if (state.kind === "hidden" || automationId === undefined) {
    return null;
  }
  const blocked = state.kind === "blocked";
  return (
    <>
      {blocked && (
        <span id={reasonId} className="subtle run-now-reason">
          {state.reason}
        </span>
      )}
      <Button
        icon="play"
        disabled={blocked}
        loading={runNow.starting}
        aria-describedby={blocked ? reasonId : undefined}
        onClick={() => runNow.start({ id: automationId, name })}
      >
        Run now
      </Button>
    </>
  );
}
