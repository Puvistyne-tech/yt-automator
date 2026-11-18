import { useState } from "react";
import { useClearSecret, useSecrets } from "@/api/system";
import type { SecretInfo } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { SecretDialog } from "@/features/secrets/SecretDialog";
import "@/features/secrets/secrets.css";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  type ConfirmTarget,
  EmptyState,
  QueryState,
  useConfirmTarget,
} from "@/shared/ui";

interface SecretHandlers {
  onSet: (secret: SecretInfo) => void;
  onClear: (secret: SecretInfo) => void;
}

function SecretRow({ secret, handlers }: { secret: SecretInfo; handlers: SecretHandlers }) {
  return (
    <li className="secret-row divided-list-item">
      <div className="cell-stack">
        <span className="row">
          <span className="cell-title">{secret.title}</span>
          <Badge tone={secret.is_set ? "success" : "neutral"} dot>
            {secret.is_set ? "Set" : "Not set"}
          </Badge>
        </span>
        <span className="subtle">{secret.description}</span>
        <span className="subtle mono">{secret.name}</span>
      </div>
      <div className="row">
        <Button size="sm" icon="key" onClick={() => handlers.onSet(secret)}>
          {secret.is_set ? "Replace" : "Set"}
        </Button>
        {secret.is_set && (
          <Button
            size="sm"
            variant="ghost"
            className="btn-danger"
            onClick={() => handlers.onClear(secret)}
          >
            Clear
          </Button>
        )}
      </div>
    </li>
  );
}

function SecretList({ list, handlers }: { list: SecretInfo[]; handlers: SecretHandlers }) {
  return (
    <ul className="list-reset divided-list">
      {list.map((secret) => (
        <SecretRow key={secret.name} secret={secret} handlers={handlers} />
      ))}
    </ul>
  );
}

function ClearSecretDialog({ confirm }: { confirm: ConfirmTarget<SecretInfo> }) {
  const clear = useClearSecret();
  const notifier = useMutationNotifier();
  const target = confirm.target;
  const onConfirm = () => {
    if (target !== null) {
      clear.mutate(
        target.name,
        notifier.handlers({ success: `${target.title} cleared.`, onDone: confirm.cancel }),
      );
    }
  };
  return (
    <ConfirmDialog
      {...confirm.dialogProps}
      title="Clear secret?"
      message={`${target?.title ?? ""} is removed from the keychain. Providers that need it become unavailable.`}
      confirmLabel="Clear secret"
      busy={clear.isPending}
      onConfirm={onConfirm}
    />
  );
}

export function SecretsPanel() {
  const secrets = useSecrets();
  const [setting, setSetting] = useState<SecretInfo | null>(null);
  const clearing = useConfirmTarget<SecretInfo>();
  const handlers: SecretHandlers = { onSet: setSetting, onClear: clearing.ask };
  return (
    <Card title="Secrets" description="API keys used by providers. Values are write-only." flush>
      <QueryState
        query={secrets}
        isEmpty={(list) => list.length === 0}
        empty={
          <EmptyState
            icon="key"
            title="No secrets needed"
            description="None of the installed providers need an API key."
          />
        }
      >
        {(list) => <SecretList list={list} handlers={handlers} />}
      </QueryState>
      {setting && <SecretDialog secret={setting} onClose={() => setSetting(null)} />}
      <ClearSecretDialog confirm={clearing} />
    </Card>
  );
}
