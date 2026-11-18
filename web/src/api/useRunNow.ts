import { useNavigate } from "react-router";
import { useRunAutomation } from "@/api/automations";
import type { Automation, Run } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";

export function runPath(run: Pick<Run, "id">): string {
  return `/runs/${encodeURIComponent(run.id)}`;
}

export function useRunNow() {
  const run = useRunAutomation();
  const notifier = useMutationNotifier();
  const navigate = useNavigate();
  const start = (automation: Pick<Automation, "id" | "name">) =>
    run.mutate(
      automation.id,
      notifier.handlers({
        success: `Run queued for ${automation.name}.`,
        action: (queued: Run) => ({ label: "View run", onClick: () => navigate(runPath(queued)) }),
      }),
    );
  return { start, starting: run.isPending };
}
