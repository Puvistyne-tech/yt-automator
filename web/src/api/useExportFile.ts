import { exportFileName, useExportAutomation } from "@/api/automations";
import type { AutomationDocument } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";

function exportedMessage(document: AutomationDocument): string {
  const { automation } = document;
  return `Exported “${automation.name}” to ${exportFileName(automation)}.`;
}

export function useExportFile() {
  const exporter = useExportAutomation();
  const notifier = useMutationNotifier();
  const exportFile = (automationId: string) =>
    exporter.mutate(automationId, notifier.handlers({ success: exportedMessage }));
  return { exportFile, exporting: exporter.isPending };
}
