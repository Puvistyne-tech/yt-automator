import { useState } from "react";
import { useChannels, useCredentials, useDisconnectChannel } from "@/api/channels";
import { errorMessage } from "@/api/errors";
import { CHANNEL_STATUSES, PRIVACY_LABELS } from "@/api/labels";
import type { Channel } from "@/api/types";
import { ChannelDefaultsDialog } from "@/features/channels/ChannelDefaultsDialog";
import { formatDateTime } from "@/shared/format/dates";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  IconButton,
  QueryState,
  StatusBadge,
  Table,
  useToast,
} from "@/shared/ui";

function Avatar({ channel }: { channel: Channel }) {
  return channel.thumbnail_url ? (
    <img className="avatar" src={channel.thumbnail_url} alt="" />
  ) : (
    <span className="avatar avatar-fallback" aria-hidden="true">
      {channel.title.charAt(0)}
    </span>
  );
}

function ChannelRow({
  channel,
  credentialName,
  onEdit,
  onDisconnect,
}: {
  channel: Channel;
  credentialName: string;
  onEdit: () => void;
  onDisconnect: () => void;
}) {
  return (
    <tr>
      <td>
        <div className="row">
          <Avatar channel={channel} />
          <div className="cell-stack">
            <span className="cell-title">{channel.title}</span>
            <span className="subtle mono">{channel.youtube_channel_id}</span>
          </div>
        </div>
      </td>
      <td>
        <StatusBadge {...CHANNEL_STATUSES[channel.status]} />
      </td>
      <td>{credentialName}</td>
      <td>
        <div className="row">
          <Badge>{PRIVACY_LABELS[channel.defaults.privacy]}</Badge>
          {channel.defaults.made_for_kids && <Badge tone="accent">Kids</Badge>}
          <Badge>{channel.defaults.default_language.toUpperCase()}</Badge>
        </div>
      </td>
      <td>{formatDateTime(channel.connected_at)}</td>
      <td className="cell-actions">
        <Button size="sm" variant="ghost" icon="settings" onClick={onEdit}>
          Defaults
        </Button>
        <IconButton
          icon="trash"
          variant="danger"
          label={`Disconnect ${channel.title}`}
          onClick={onDisconnect}
        />
      </td>
    </tr>
  );
}

export function ChannelsPanel() {
  const channels = useChannels();
  const credentials = useCredentials();
  const disconnect = useDisconnectChannel();
  const toast = useToast();
  const [editing, setEditing] = useState<Channel | null>(null);
  const [removing, setRemoving] = useState<Channel | null>(null);
  const credentialName = (id: string) => credentials.data?.find((c) => c.id === id)?.name ?? "—";
  const confirm = (channel: Channel) =>
    disconnect.mutate(channel.id, {
      onSuccess: () => toast.success(`Disconnected ${channel.title}.`),
      onError: (error) => toast.error(errorMessage(error)),
      onSettled: () => setRemoving(null),
    });
  return (
    <Card
      title="Connected channels"
      description="Connect a channel from one of the credentials above."
      flush
    >
      <QueryState
        query={channels}
        isEmpty={(list) => list.length === 0}
        empty={
          <EmptyState
            icon="channels"
            title="No channels connected"
            description="Use Connect channel on a credential to sign in with Google."
          />
        }
      >
        {(list) => (
          <Table label="Channels">
            <thead>
              <tr>
                <th scope="col">Channel</th>
                <th scope="col">Status</th>
                <th scope="col">Credential</th>
                <th scope="col">Defaults</th>
                <th scope="col">Connected</th>
                <th scope="col" className="cell-actions">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {list.map((channel) => (
                <ChannelRow
                  key={channel.id}
                  channel={channel}
                  credentialName={credentialName(channel.credential_id)}
                  onEdit={() => setEditing(channel)}
                  onDisconnect={() => setRemoving(channel)}
                />
              ))}
            </tbody>
          </Table>
        )}
      </QueryState>
      {editing && <ChannelDefaultsDialog channel={editing} onClose={() => setEditing(null)} />}
      <ConfirmDialog
        open={removing !== null}
        title="Disconnect channel?"
        message={`The stored token for ${removing?.title ?? ""} is deleted. Automations can no longer publish there.`}
        confirmLabel="Disconnect"
        busy={disconnect.isPending}
        onConfirm={() => removing && confirm(removing)}
        onCancel={() => setRemoving(null)}
      />
    </Card>
  );
}
