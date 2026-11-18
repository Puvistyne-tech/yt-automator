import { useState } from "react";
import { useSetSecret } from "@/api/system";
import type { SecretInfo } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { validateSecretValue } from "@/features/secrets/secretForm";
import { FormDialog, FormField, Input } from "@/shared/ui";

export function SecretDialog({ secret, onClose }: { secret: SecretInfo; onClose: () => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const save = useSetSecret();
  const notifier = useMutationNotifier();
  const submit = () => {
    const check = validateSecretValue(value);
    setError(check.ok ? undefined : check.error);
    if (check.ok) {
      save.mutate(
        { name: secret.name, value: check.value },
        notifier.handlers({ success: `${secret.title} saved.`, onSuccess: onClose }),
      );
    }
  };
  return (
    <FormDialog
      title={`Set ${secret.title}`}
      description="Stored in the system keychain. It is never shown again or sent back by the API."
      submitLabel="Save secret"
      busy={save.isPending}
      onSubmit={submit}
      onClose={onClose}
    >
      <FormField label="Value" required error={error} hint={secret.description}>
        <Input
          type="password"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
      </FormField>
    </FormDialog>
  );
}
