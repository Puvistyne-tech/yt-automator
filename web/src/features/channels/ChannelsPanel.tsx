import { useState } from "react";
import { useChannels, useCredentials, useDisconnectChannel } from "@/api/channels";
import { CHANNEL_STATUSES, PRIVACY_LABELS } from "@/api/labels";
import type { Channel } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { ChannelDefaultsDialog } from "@/features/channels/ChannelDefaultsDialog";
import { formatDateTime } from "@/shared/format/dates";
import {
  ACTIONS_COLUMN,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  type ConfirmTarget,
  EmptyState,
  IconButton,
  QueryState,
  StatusBadge,
  Table,
  useConfirmTarget,
} from "@/shared/ui";

const COLUMNS = ["Channel", "Status", "Credential", "Defaults", "Connected", ACTIONS_COLUMN];

interface RowHandlers {
  credentialName: (id: string) => string;
  onEdit: (channel: Channel) => void;
  onDisconnect: (channel: Channel) => void;
}

function Avatar({ channel }: { channel: Channel }) {
  return channel.thumbnail_url ? (
    <img className="avatar" src={channel.thumbnail_url} alt="" />
  ) : (
    <span className="avatar avatar-fallback" aria-hidden="true">
      {channel.title.charAt(0)}
    </span>
  );
}

function ChannelDefaultsBadges({ channel }: { channel: Channel }) {
  return (
    <div className="row">
      <Badge>{PRIVACY_LABELS[channel.defaults.privacy]}</Badge>
      {channel.defaults.made_for_kids && <Badge tone="accent">Kids</Badge>}
      <Badge>{channel.defaults.default_language.toUpperCase()}</Badge>
    </div>
  );
}

function ChannelRow({ channel, handlers }: { channel: Channel; handlers: RowHandlers }) {
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
      <td>{handlers.credentialName(channel.credential_id)}</td>
      <td>
        <ChannelDefaultsBadges channel={channel} />
      </td>
      <td>{formatDateTime(channel.connected_at)}</td>
      <td className="cell-actions">
        <Button size="sm" variant="ghost" icon="settings" onClick={() => handlers.onEdit(channel)}>
          Defaults
        </Button>
        <IconButton
          icon="trash"
          variant="danger"
          label={`Disconnect ${channel.title}`}
          onClick={() => handlers.onDisconnect(channel)}
        />
      </td>
    </tr>
  );
}

function ChannelsTable({ list, handlers }: { list: Channel[]; handlers: RowHandlers }) {
  return (
    <Table label="Channels" columns={COLUMNS}>
      {list.map((channel) => (
        <ChannelRow key={channel.id} channel={channel} handlers={handlers} />
      ))}
    </Table>
  );
}

function DisconnectDialog({ confirm }: { confirm: ConfirmTarget<Channel> }) {
  const disconnect = useDisconnectChannel();
  const notifier = useMutationNotifier();
  const target = confirm.target;
  const onConfirm = () => {
    if (target !== null) {
      disconnect.mutate(
        target.id,
        notifier.handlers({ success: `Disconnected ${target.title}.`, onDone: confirm.cancel }),
      );
    }
  };
  return (
    <ConfirmDialog
      {...confirm.dialogProps}
      title="Disconnect channel?"
      message={`The stored token for ${target?.title ?? ""} is deleted. Automations can no longer publish there.`}
      confirmLabel="Disconnect"
      busy={disconnect.isPending}
      onConfirm={onConfirm}
    />
  );
}

export function ChannelsPanel() {
  const channels = useChannels();
  const credentials = useCredentials();
  const [editing, setEditing] = useState<Channel | null>(null);
  const removing = useConfirmTarget<Channel>();
  const handlers: RowHandlers = {
    credentialName: (id) => credentials.data?.find((c) => c.id === id)?.name ?? "—",
    onEdit: setEditing,
    onDisconnect: removing.ask,
  };
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
        {(list) => <ChannelsTable list={list} handlers={handlers} />}
      </QueryState>
      {editing && <ChannelDefaultsDialog channel={editing} onClose={() => setEditing(null)} />}
      <DisconnectDialog confirm={removing} />
    </Card>
  );
}
