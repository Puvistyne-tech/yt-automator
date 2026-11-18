import { useConnectChannel } from "@/api/channels";
import type { CredentialSummary } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { formatNumber } from "@/shared/format/numbers";
import { useExternalNavigate } from "@/shared/hooks/externalNavigation";
import { Badge, Button, IconButton, ProgressMeter } from "@/shared/ui";

interface CredentialItemProps {
  credential: CredentialSummary;
  onEdit: () => void;
  onDelete: () => void;
}

function CredentialSummaryBlock({ credential }: { credential: CredentialSummary }) {
  return (
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
  );
}

function CredentialQuota({ credential }: { credential: CredentialSummary }) {
  const used = credential.quota_used_today;
  const limit = credential.daily_quota_units;
  return (
    <div className="credential-quota">
      <ProgressMeter
        label="Quota used today"
        value={used}
        max={limit}
        detail={`${formatNumber(used)} / ${formatNumber(limit)}`}
      />
    </div>
  );
}

function CredentialActions({ credential, onEdit, onDelete }: CredentialItemProps) {
  const connect = useConnectChannel();
  const navigateExternal = useExternalNavigate();
  const notifier = useMutationNotifier();
  const start = () =>
    connect.mutate(credential.id, {
      onSuccess: ({ authorization_url }) => navigateExternal(authorization_url),
      onError: notifier.fail,
    });
  return (
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
  );
}

export function CredentialItem(props: CredentialItemProps) {
  return (
    <li className="credential divided-list-item">
      <CredentialSummaryBlock credential={props.credential} />
      <CredentialQuota credential={props.credential} />
      <CredentialActions {...props} />
    </li>
  );
}
