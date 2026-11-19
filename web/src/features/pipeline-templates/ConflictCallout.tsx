import type { ConflictNotice } from "@/features/pipeline-templates/model/conflicts";
import { AlertCallout } from "@/shared/ui";

export function ConflictCallout({ conflict }: { conflict: ConflictNotice | null }) {
  if (conflict === null) {
    return null;
  }
  return (
    <AlertCallout tone="danger" role="alert">
      <strong>{conflict.title}.</strong> {conflict.message}
    </AlertCallout>
  );
}
