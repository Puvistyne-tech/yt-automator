import type { CredentialView } from "@/api/types";
import { useStartConnect } from "@/features/channels/useStartConnect";
import { formatNumber } from "@/shared/format/numbers";
import { Badge, Button, IconButton, ProgressMeter } from "@/shared/ui";

interface CredentialItemProps {
  credential: CredentialView;
  onEdit: () => void;
  onDelete: () => void;
}

function CredentialViewBlock({ credential }: { credential: CredentialView }) {
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

function CredentialQuota({ credential }: { credential: CredentialView }) {
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
  const connect = useStartConnect();
  return (
    <div className="credential-actions">
      <Button
        size="sm"
        variant="primary"
        icon="link"
        loading={connect.pending}
        disabled={!credential.has_secret}
        title={credential.has_secret ? undefined : "Add the client secret first"}
        onClick={() => connect.start(credential.id)}
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
      <CredentialViewBlock credential={props.credential} />
      <CredentialQuota credential={props.credential} />
      <CredentialActions {...props} />
    </li>
  );
}
