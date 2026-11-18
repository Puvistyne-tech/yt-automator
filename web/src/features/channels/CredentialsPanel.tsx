import { useState } from "react";
import { useConnectChannel, useCredentials, useDeleteCredential } from "@/api/channels";
import { errorMessage } from "@/api/errors";
import type { CredentialSummary } from "@/api/types";
import { CredentialDialog } from "@/features/channels/CredentialDialog";
import { formatNumber } from "@/shared/format/numbers";
import { useExternalNavigate } from "@/shared/hooks/externalNavigation";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  IconButton,
  ProgressMeter,
  QueryState,
  useToast,
} from "@/shared/ui";
import "@/features/channels/channels.css";

type Editing = { credential: CredentialSummary | undefined } | null;

function CredentialItem({
  credential,
  onEdit,
  onDelete,
}: {
  credential: CredentialSummary;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const connect = useConnectChannel();
  const navigateExternal = useExternalNavigate();
  const toast = useToast();
  const start = () =>
    connect.mutate(credential.id, {
      onSuccess: ({ authorization_url }) => navigateExternal(authorization_url),
      onError: (error) => toast.error(errorMessage(error)),
    });
  return (
    <li className="credential">
      <div className="credential-main">
        <div className="row">
          <span className="cell-title">{credential.name}</span>
          {credential.has_secret ? (
            <Badge tone="success">Secret stored</Badge>
          ) : (
            <Badge tone="warning">No secret</Badge>
          )}
        </div>
        <span className="subtle mono">{credential.client_id}</span>
      </div>
      <div className="credential-quota">
        <ProgressMeter
          label="Quota used today"
          value={credential.quota_used_today}
          max={credential.daily_quota_units}
          detail={`${formatNumber(credential.quota_used_today)} / ${formatNumber(credential.daily_quota_units)}`}
        />
      </div>
      <div className="credential-actions">
        <Button
          size="sm"
          variant="primary"
          icon="link"
          loading={connect.isPending}
          disabled={!credential.has_secret}
          title={credential.has_secret ? undefined : "Add the client secret first"}
          onClick={start}
        >
          Connect channel
        </Button>
        <IconButton icon="edit" label={`Edit ${credential.name}`} onClick={onEdit} />
        <IconButton
          icon="trash"
          variant="danger"
          label={`Delete ${credential.name}`}
          onClick={onDelete}
        />
      </div>
    </li>
  );
}

export function CredentialsPanel() {
  const credentials = useCredentials();
  const remove = useDeleteCredential();
  const toast = useToast();
  const [editing, setEditing] = useState<Editing>(null);
  const [deleting, setDeleting] = useState<CredentialSummary | null>(null);
  const confirmDelete = (credential: CredentialSummary) =>
    remove.mutate(credential.id, {
      onSuccess: () => toast.success(`Deleted ${credential.name}.`),
      onError: (error) => toast.error(errorMessage(error)),
      onSettled: () => setDeleting(null),
    });
  return (
    <Card
      title="Google API credentials"
      description="Each credential is one Google Cloud project with its own daily upload quota."
      flush
      actions={
        <Button size="sm" icon="plus" onClick={() => setEditing({ credential: undefined })}>
          Add credential
        </Button>
      }
    >
      <QueryState
        query={credentials}
        isEmpty={(list) => list.length === 0}
        empty={
          <EmptyState
            icon="key"
            title="No credentials yet"
            description="Add an OAuth client to connect your first channel."
            action={
              <Button
                variant="primary"
                icon="plus"
                onClick={() => setEditing({ credential: undefined })}
              >
                Add credential
              </Button>
            }
          />
        }
      >
        {(list) => (
          <ul className="credential-list">
            {list.map((credential) => (
              <CredentialItem
                key={credential.id}
                credential={credential}
                onEdit={() => setEditing({ credential })}
                onDelete={() => setDeleting(credential)}
              />
            ))}
          </ul>
        )}
      </QueryState>
      {editing && (
        <CredentialDialog credential={editing.credential} onClose={() => setEditing(null)} />
      )}
      <ConfirmDialog
        open={deleting !== null}
        title="Delete credential?"
        message={`${deleting?.name ?? ""} and its stored client secret will be removed. Channels using it must be disconnected first.`}
        confirmLabel="Delete credential"
        busy={remove.isPending}
        onConfirm={() => deleting && confirmDelete(deleting)}
        onCancel={() => setDeleting(null)}
      />
    </Card>
  );
}
