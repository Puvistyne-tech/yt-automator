import { useExportFile } from "@/api/useExportFile";
import { Button } from "@/shared/ui";

interface ExportButtonProps {
  automationId: string | undefined;
  dirty: boolean;
}

export const EXPORT_SAVED_HINT = "Exports the saved version, without your unsaved changes.";

export function ExportButton({ automationId, dirty }: ExportButtonProps) {
  const exporter = useExportFile();
  if (automationId === undefined) {
    return null;
  }
  return (
    <Button
      icon="file"
      loading={exporter.exporting}
      title={dirty ? EXPORT_SAVED_HINT : undefined}
      onClick={() => exporter.exportFile(automationId)}
    >
      Export
    </Button>
  );
}
