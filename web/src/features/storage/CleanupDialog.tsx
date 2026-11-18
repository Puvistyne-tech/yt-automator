import { useCleanUp, useCleanupPreview } from "@/api/storage";
import type { CleanupReport } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  ACTION_LABELS,
  cleanupResultMessage,
  itemTitle,
  policySummary,
} from "@/features/storage/model";
import { formatBytes } from "@/shared/format/numbers";
import { Dialog, DialogActions, QueryState, Table } from "@/shared/ui";

interface CleanupDialogProps {
  open: boolean;
  onClose: () => void;
}

function PreviewList({ report }: { report: CleanupReport }) {
  if (report.items.length === 0) {
    return <p>Nothing to clean up right now.</p>;
  }
  return (
    <>
      <Table label="Cleanup preview" columns={["Run", "What happens", "Frees"]}>
        {report.items.map((item) => (
          <tr key={`${item.action}-${item.run_id}`}>
            <td>{itemTitle(item)}</td>
            <td>{ACTION_LABELS[item.action]}</td>
            <td>{formatBytes(item.bytes)}</td>
          </tr>
        ))}
      </Table>
      <p className="cleanup-total">
        Frees <strong>{formatBytes(report.total_bytes)}</strong> in total. This cannot be undone.
      </p>
    </>
  );
}

export function CleanupDialog({ open, onClose }: CleanupDialogProps) {
  const preview = useCleanupPreview(open);
  const cleanUp = useCleanUp();
  const notifier = useMutationNotifier();
  const empty = preview.data === undefined || preview.data.items.length === 0;
  const confirm = () =>
    cleanUp.mutate(
      undefined,
      notifier.handlers<CleanupReport>({ success: cleanupResultMessage, onDone: onClose }),
    );
  const footer = (
    <DialogActions
      submitLabel="Clean up"
      tone="danger"
      busy={cleanUp.isPending}
      submitDisabled={empty}
      onSubmit={confirm}
      onCancel={onClose}
    />
  );
  return (
    <Dialog open={open} title="Clean up storage" onClose={onClose} size="md" footer={footer}>
      <QueryState query={preview} loadingLabel="Checking what can be removed">
        {(report) => (
          <div className="stack-sm">
            <p className="muted">{policySummary(report)}</p>
            <PreviewList report={report} />
          </div>
        )}
      </QueryState>
    </Dialog>
  );
}
