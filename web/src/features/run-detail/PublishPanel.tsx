import { useState } from "react";
import { useChannels } from "@/api/channels";
import { UPLOAD_STATUSES } from "@/api/labels";
import { usePublishRun } from "@/api/runs";
import type { Run, Upload } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { publishDescription, uploadAudience, uploadNote } from "@/features/run-detail/model";
import { formatNumber } from "@/shared/format/numbers";
import { humanizeId } from "@/shared/format/text";
import { Button, Card, ConfirmDialog, Icon, StatusBadge, Table } from "@/shared/ui";

const UPLOAD_COLUMNS = [
  "Channel",
  "Language",
  "Output",
  "Privacy",
  "Made for kids",
  "Status",
  "Quota",
  { label: "Link", hidden: true },
];

function UploadStatus({ upload }: { upload: Upload }) {
  const note = uploadNote(upload);
  return (
    <div className="cell-stack">
      <StatusBadge {...UPLOAD_STATUSES[upload.status]} />
      {note && (
        <span className={note.tone === "error" ? "field-error" : "subtle"}>{note.text}</span>
      )}
    </div>
  );
}

function UploadRow({ upload, channelTitle }: { upload: Upload; channelTitle: string }) {
  const audience = uploadAudience(upload);
  return (
    <tr>
      <td>{channelTitle}</td>
      <td className="mono">{upload.language.toUpperCase()}</td>
      <td>{humanizeId(upload.variant)}</td>
      <td>{audience.privacy}</td>
      <td>{audience.madeForKids}</td>
      <td className="cell-wrap">
        <UploadStatus upload={upload} />
      </td>
      <td>{formatNumber(upload.quota_units)}</td>
      <td className="cell-actions">
        {upload.url && (
          <a
            href={upload.url}
            target="_blank"
            rel="noreferrer"
            className="row"
            aria-label="Watch on YouTube"
            title="Watch on YouTube"
          >
            Watch <Icon name="external" />
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
    <Table label="Uploads" columns={UPLOAD_COLUMNS}>
      {uploads.map((upload) => (
        <UploadRow
          key={`${upload.target_id}-${upload.variant}`}
          upload={upload}
          channelTitle={title(upload.channel_id)}
        />
      ))}
    </Table>
  );
}

export function PublishPanel({ run, canPublish }: { run: Run; canPublish: boolean }) {
  const [confirming, setConfirming] = useState(false);
  const publish = usePublishRun();
  const notifier = useMutationNotifier();
  const start = () =>
    publish.mutate(
      { id: run.id, vars: undefined },
      notifier.handlers({ success: "Publishing started.", onDone: () => setConfirming(false) }),
    );
  const hasUploads = run.uploads.length > 0;
  return (
    <Card
      title="Publishing"
      description={publishDescription(run)}
      flush={hasUploads}
      actions={
        canPublish ? (
          <Button variant="primary" icon="upload" onClick={() => setConfirming(true)}>
            Publish
          </Button>
        ) : undefined
      }
    >
      {hasUploads ? <UploadsTable uploads={run.uploads} /> : null}
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
