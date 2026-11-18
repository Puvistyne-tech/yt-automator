import { useState } from "react";
import { useCredentials, useDeleteCredential } from "@/api/channels";
import type { CredentialSummary } from "@/api/types";
import { useConfirmedMutation } from "@/api/useConfirmedMutation";
import { CredentialDialog } from "@/features/channels/CredentialDialog";
import { CredentialItem } from "@/features/channels/CredentialItem";
import {
  Button,
  Card,
  ConfirmDialog,
  type ConfirmTarget,
  EmptyState,
  QueryState,
  useConfirmTarget,
} from "@/shared/ui";
import "@/features/channels/channels.css";

type Editing = { credential: CredentialSummary | undefined } | null;

function CredentialList({
  list,
  onEdit,
  onDelete,
}: {
  list: CredentialSummary[];
  onEdit: (credential: CredentialSummary) => void;
  onDelete: (credential: CredentialSummary) => void;
}) {
  return (
    <ul className="list-reset divided-list">
      {list.map((credential) => (
        <CredentialItem
          key={credential.id}
          credential={credential}
          onEdit={() => onEdit(credential)}
          onDelete={() => onDelete(credential)}
        />
      ))}
    </ul>
  );
}

function AddCredentialButton({ onAdd, primary }: { onAdd: () => void; primary?: boolean }) {
  return (
    <Button
      size={primary ? "md" : "sm"}
      variant={primary ? "primary" : "secondary"}
      icon="plus"
      onClick={onAdd}
    >
      Add credential
    </Button>
  );
}

function DeleteCredentialDialog({ confirm }: { confirm: ConfirmTarget<CredentialSummary> }) {
  const { onConfirm, busy } = useConfirmedMutation({
    confirm,
    mutation: useDeleteCredential(),
    vars: (credential) => credential.id,
    success: (credential) => `Deleted ${credential.name}.`,
  });
  return (
    <ConfirmDialog
      {...confirm.dialogProps}
      title="Delete credential?"
      message={`${confirm.target?.name ?? ""} and its stored client secret will be removed. Channels using it must be disconnected first.`}
      confirmLabel="Delete credential"
      busy={busy}
      onConfirm={onConfirm}
    />
  );
}

export function CredentialsPanel() {
  const credentials = useCredentials();
  const [editing, setEditing] = useState<Editing>(null);
  const deleting = useConfirmTarget<CredentialSummary>();
  const add = () => setEditing({ credential: undefined });
  return (
    <Card
      title="Google API credentials"
      description="Each credential is one Google Cloud project with its own daily upload quota."
      flush
      actions={<AddCredentialButton onAdd={add} />}
    >
      <QueryState
        query={credentials}
        isEmpty={(list) => list.length === 0}
        empty={
          <EmptyState
            icon="key"
            title="No credentials yet"
            description="Add an OAuth client to connect your first channel."
            action={<AddCredentialButton onAdd={add} primary />}
          />
        }
      >
        {(list) => (
          <CredentialList
            list={list}
            onEdit={(c) => setEditing({ credential: c })}
            onDelete={deleting.ask}
          />
        )}
      </QueryState>
      {editing && (
        <CredentialDialog credential={editing.credential} onClose={() => setEditing(null)} />
      )}
      <DeleteCredentialDialog confirm={deleting} />
    </Card>
  );
}
