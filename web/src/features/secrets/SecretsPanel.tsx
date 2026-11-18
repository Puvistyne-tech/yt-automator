import { useState } from "react";
import { errorMessage } from "@/api/errors";
import { useClearSecret, useSecrets, useSetSecret } from "@/api/system";
import type { SecretInfo } from "@/api/types";
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  Dialog,
  EmptyState,
  FormField,
  Input,
  QueryState,
  useToast,
} from "@/shared/ui";
import "@/features/secrets/secrets.css";

function SecretDialog({ secret, onClose }: { secret: SecretInfo; onClose: () => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const save = useSetSecret();
  const toast = useToast();
  const submit = () => {
    if (value.trim() === "") {
      setError("Enter a value.");
      return;
    }
    save.mutate(
      { name: secret.name, value: value.trim() },
      {
        onSuccess: () => {
          toast.success(`${secret.title} saved.`);
          onClose();
        },
        onError: (problem) => toast.error(errorMessage(problem)),
      },
    );
  };
  return (
    <Dialog
      open
      title={`Set ${secret.title}`}
      description="Stored in the system keychain. It is never shown again or sent back by the API."
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={save.isPending} onClick={submit}>
            Save secret
          </Button>
        </>
      }
    >
      <FormField label="Value" required error={error} hint={secret.description}>
        <Input
          type="password"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </FormField>
    </Dialog>
  );
}

function SecretRow({
  secret,
  onSet,
  onClear,
}: {
  secret: SecretInfo;
  onSet: () => void;
  onClear: () => void;
}) {
  return (
    <li className="secret-row">
      <div className="cell-stack">
        <span className="row">
          <span className="cell-title">{secret.title}</span>
          {secret.is_set ? (
            <Badge tone="success" dot>
              Set
            </Badge>
          ) : (
            <Badge dot>Not set</Badge>
          )}
        </span>
        <span className="subtle">{secret.description}</span>
        <span className="subtle mono">{secret.name}</span>
      </div>
      <div className="row">
        <Button size="sm" icon="key" onClick={onSet}>
          {secret.is_set ? "Replace" : "Set"}
        </Button>
        {secret.is_set && (
          <Button size="sm" variant="ghost" className="btn-danger" onClick={onClear}>
            Clear
          </Button>
        )}
      </div>
    </li>
  );
}

export function SecretsPanel() {
  const secrets = useSecrets();
  const clear = useClearSecret();
  const toast = useToast();
  const [setting, setSetting] = useState<SecretInfo | null>(null);
  const [clearing, setClearing] = useState<SecretInfo | null>(null);
  const confirmClear = (secret: SecretInfo) =>
    clear.mutate(secret.name, {
      onSuccess: () => toast.success(`${secret.title} cleared.`),
      onError: (error) => toast.error(errorMessage(error)),
      onSettled: () => setClearing(null),
    });
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
        {(list) => (
          <ul className="secret-list">
            {list.map((secret) => (
              <SecretRow
                key={secret.name}
                secret={secret}
                onSet={() => setSetting(secret)}
                onClear={() => setClearing(secret)}
              />
            ))}
          </ul>
        )}
      </QueryState>
      {setting && <SecretDialog secret={setting} onClose={() => setSetting(null)} />}
      <ConfirmDialog
        open={clearing !== null}
        title="Clear secret?"
        message={`${clearing?.title ?? ""} is removed from the keychain. Providers that need it become unavailable.`}
        confirmLabel="Clear secret"
        busy={clear.isPending}
        onConfirm={() => clearing && confirmClear(clearing)}
        onCancel={() => setClearing(null)}
      />
    </Card>
  );
}
