import { useState } from "react";
import { useChannels } from "@/api/channels";
import { errorMessage } from "@/api/errors";
import { UPLOAD_STATUSES } from "@/api/labels";
import { usePublishRun } from "@/api/runs";
import type { Run, Upload } from "@/api/types";
import { uploadSummary } from "@/features/run-detail/model";
import { formatNumber, humanizeId } from "@/shared/format/numbers";
import { Button, Card, ConfirmDialog, Icon, StatusBadge, Table, useToast } from "@/shared/ui";

function UploadRow({ upload, channelTitle }: { upload: Upload; channelTitle: string }) {
  return (
    <tr>
      <td>{channelTitle}</td>
      <td className="mono">{upload.language.toUpperCase()}</td>
      <td>{humanizeId(upload.variant)}</td>
      <td>
        <div className="cell-stack">
          <StatusBadge {...UPLOAD_STATUSES[upload.status]} />
          {upload.error && <span className="field-error">{upload.error}</span>}
        </div>
      </td>
      <td>{formatNumber(upload.quota_units)}</td>
      <td className="cell-actions">
        {upload.url && (
          <a href={upload.url} target="_blank" rel="noreferrer" className="row">
            Watch on YouTube <Icon name="external" />
          </a>
        )}
      </td>
    </tr>
  );
}

function UploadsTable({ uploads }: { uploads: Upload[] }) {
  const channels = useChannels();
  const title = (id: string) => channels.data?.find((c) => c.id === id)?.title ?? id;
  return (
    <Table label="Uploads">
      <thead>
        <tr>
          <th scope="col">Channel</th>
          <th scope="col">Language</th>
          <th scope="col">Output</th>
          <th scope="col">Status</th>
          <th scope="col">Quota</th>
          <th scope="col">
            <span className="visually-hidden">Link</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {uploads.map((upload) => (
          <UploadRow
            key={`${upload.target_id}-${upload.variant}`}
            upload={upload}
            channelTitle={title(upload.channel_id)}
          />
        ))}
      </tbody>
    </Table>
  );
}

export function PublishPanel({ run, canPublish }: { run: Run; canPublish: boolean }) {
  const [confirming, setConfirming] = useState(false);
  const publish = usePublishRun();
  const toast = useToast();
  const summary = uploadSummary(run.uploads);
  const start = () =>
    publish
      .mutateAsync({ id: run.id, vars: undefined })
      .then(
        () => toast.success("Publishing started."),
        (error: unknown) => toast.error(errorMessage(error)),
      )
      .finally(() => setConfirming(false));
  const description =
    run.uploads.length > 0
      ? `${summary.done} uploaded · ${summary.failed} failed · ${summary.pending} pending`
      : "Approved and ready. Publishing creates one upload per target and output.";
  return (
    <Card
      title="Publishing"
      description={description}
      flush={run.uploads.length > 0}
      actions={
        canPublish ? (
          <Button variant="primary" icon="upload" onClick={() => setConfirming(true)}>
            Publish
          </Button>
        ) : undefined
      }
    >
      {run.uploads.length > 0 ? <UploadsTable uploads={run.uploads} /> : null}
      <ConfirmDialog
        open={confirming}
        tone="primary"
        title="Publish this run?"
        message="Videos, thumbnails and captions are uploaded to every target channel using today's quota."
        confirmLabel="Publish now"
        busy={publish.isPending}
        onConfirm={start}
        onCancel={() => setConfirming(false)}
      />
    </Card>
  );
}
