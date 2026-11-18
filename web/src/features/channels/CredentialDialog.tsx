import { useState } from "react";
import { useSaveCredential } from "@/api/channels";
import { errorMessage, type FieldErrors, fieldErrorsOf, normalizeFieldErrors } from "@/api/errors";
import type { CredentialSummary } from "@/api/types";
import {
  type CredentialValues,
  credentialPayload,
  credentialValues,
  validateCredential,
} from "@/features/channels/credentialForm";
import { Button, Dialog, FormField, Input, useToast } from "@/shared/ui";

interface CredentialDialogProps {
  credential: CredentialSummary | undefined;
  onClose: () => void;
}

export function CredentialDialog({ credential, onClose }: CredentialDialogProps) {
  const isNew = credential === undefined;
  const [values, setValues] = useState<CredentialValues>(() => credentialValues(credential));
  const [errors, setErrors] = useState<FieldErrors>({});
  const save = useSaveCredential(credential?.id);
  const toast = useToast();
  const set = (patch: Partial<CredentialValues>) =>
    setValues((current) => ({ ...current, ...patch }));
  const submit = () => {
    const problems = validateCredential(values, isNew);
    setErrors(problems);
    if (Object.keys(problems).length > 0) {
      return;
    }
    save.mutate(credentialPayload(values, isNew), {
      onSuccess: (saved) => {
        toast.success(isNew ? `Added ${saved.name}.` : `Updated ${saved.name}.`);
        onClose();
      },
      onError: (error) => {
        setErrors(normalizeFieldErrors(fieldErrorsOf(error)));
        toast.error(errorMessage(error));
      },
    });
  };
  return (
    <Dialog
      open
      title={isNew ? "Add Google API credential" : `Edit ${credential.name}`}
      description="An OAuth client from Google Cloud Console with the YouTube Data API enabled."
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={save.isPending} onClick={submit}>
            {isNew ? "Add credential" : "Save"}
          </Button>
        </>
      }
    >
      <FormField label="Name" required error={errors.name}>
        <Input value={values.name} onChange={(e) => set({ name: e.target.value })} />
      </FormField>
      <FormField label="Client id" required error={errors.client_id}>
        <Input
          className="mono"
          value={values.client_id}
          onChange={(e) => set({ client_id: e.target.value })}
        />
      </FormField>
      <FormField
        label="Client secret"
        required={isNew}
        error={errors.client_secret}
        hint={
          isNew
            ? "Stored in the keychain. It is never shown again."
            : credential.has_secret
              ? "A secret is stored. Leave blank to keep it."
              : "No secret stored yet."
        }
      >
        <Input
          type="password"
          autoComplete="off"
          value={values.client_secret}
          onChange={(e) => set({ client_secret: e.target.value })}
        />
      </FormField>
      <FormField
        label="Daily quota (units)"
        error={errors.daily_quota_units}
        hint="Google's default is 10,000 units per day."
      >
        <Input
          type="number"
          min={1}
          step={1}
          value={Number.isNaN(values.daily_quota_units) ? "" : values.daily_quota_units}
          onChange={(e) => set({ daily_quota_units: e.target.valueAsNumber })}
        />
      </FormField>
    </Dialog>
  );
}
