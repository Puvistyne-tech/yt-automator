import { useSaveCredential } from "@/api/channels";
import type { FieldErrors } from "@/api/errors";
import type { Credential, CredentialSummary } from "@/api/types";
import { useFieldErrors } from "@/api/useFieldErrors";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  type CredentialValues,
  credentialPayload,
  credentialSecretHint,
  credentialValues,
  validateCredential,
} from "@/features/channels/credentialForm";
import { usePatchState } from "@/shared/hooks/usePatchState";
import { FormDialog, FormField, Input, NumberInput } from "@/shared/ui";

interface CredentialDialogProps {
  credential: CredentialSummary | undefined;
  onClose: () => void;
}

interface CredentialFieldsProps {
  credential: CredentialSummary | undefined;
  values: CredentialValues;
  errors: FieldErrors;
  onChange: (patch: Partial<CredentialValues>) => void;
}

function SecretField({ credential, values, errors, onChange }: CredentialFieldsProps) {
  return (
    <FormField
      label="Client secret"
      required={credential === undefined}
      error={errors.client_secret}
      hint={credentialSecretHint(credential)}
    >
      <Input
        type="password"
        autoComplete="off"
        value={values.client_secret}
        onChange={(e) => onChange({ client_secret: e.target.value })}
      />
    </FormField>
  );
}

function CredentialFields({ credential, values, errors, onChange }: CredentialFieldsProps) {
  return (
    <>
      <FormField label="Name" required error={errors.name}>
        <Input value={values.name} onChange={(e) => onChange({ name: e.target.value })} />
      </FormField>
      <FormField label="Client id" required error={errors.client_id}>
        <Input
          className="mono"
          value={values.client_id}
          onChange={(e) => onChange({ client_id: e.target.value })}
        />
      </FormField>
      <SecretField credential={credential} values={values} errors={errors} onChange={onChange} />
      <FormField
        label="Daily quota (units)"
        error={errors.daily_quota_units}
        hint="Google's default is 10,000 units per day."
      >
        <NumberInput
          min={1}
          step={1}
          value={values.daily_quota_units}
          onValueChange={(daily_quota_units) => onChange({ daily_quota_units })}
        />
      </FormField>
    </>
  );
}

export function CredentialDialog({ credential, onClose }: CredentialDialogProps) {
  const isNew = credential === undefined;
  const [values, patch] = usePatchState<CredentialValues>(() => credentialValues(credential));
  const fields = useFieldErrors();
  const save = useSaveCredential(credential?.id);
  const notifier = useMutationNotifier();
  const submit = () => {
    if (fields.validate(validateCredential(values, isNew))) {
      save.mutate(
        credentialPayload(values, isNew),
        notifier.handlers({
          success: (saved: Credential) => `${isNew ? "Added" : "Updated"} ${saved.name}.`,
          onSuccess: onClose,
          onError: fields.setFromServer,
        }),
      );
    }
  };
  return (
    <FormDialog
      title={isNew ? "Add Google API credential" : `Edit ${credential.name}`}
      description="An OAuth client from Google Cloud Console with the YouTube Data API enabled."
      submitLabel={isNew ? "Add credential" : "Save"}
      busy={save.isPending}
      onSubmit={submit}
      onClose={onClose}
    >
      <CredentialFields
        credential={credential}
        values={values}
        errors={fields.errors}
        onChange={patch}
      />
    </FormDialog>
  );
}
