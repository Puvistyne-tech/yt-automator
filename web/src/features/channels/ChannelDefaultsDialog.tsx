import { useState } from "react";
import { useUpdateChannelDefaults } from "@/api/channels";
import { errorMessage } from "@/api/errors";
import { PRIVACY_LABELS, PRIVACY_ORDER } from "@/api/labels";
import type { Channel, ChannelDefaults, Privacy } from "@/api/types";
import { Button, Dialog, FormField, Input, Select, Switch, useToast } from "@/shared/ui";

const PRIVACY_OPTIONS = PRIVACY_ORDER.map((value) => ({ value, label: PRIVACY_LABELS[value] }));

export function ChannelDefaultsDialog({
  channel,
  onClose,
}: {
  channel: Channel;
  onClose: () => void;
}) {
  const [defaults, setDefaults] = useState<ChannelDefaults>(channel.defaults);
  const update = useUpdateChannelDefaults();
  const toast = useToast();
  const set = (patch: Partial<ChannelDefaults>) =>
    setDefaults((current) => ({ ...current, ...patch }));
  const missing = defaults.category_id.trim() === "" || defaults.default_language.trim() === "";
  const submit = () =>
    update.mutate(
      {
        id: channel.id,
        defaults: {
          ...defaults,
          category_id: defaults.category_id.trim(),
          default_language: defaults.default_language.trim(),
        },
      },
      {
        onSuccess: () => {
          toast.success(`Saved defaults for ${channel.title}.`);
          onClose();
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  return (
    <Dialog
      open
      title={`Upload defaults for ${channel.title}`}
      description="Targets use these unless an automation overrides them."
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" loading={update.isPending} disabled={missing} onClick={submit}>
            Save defaults
          </Button>
        </>
      }
    >
      <FormField label="Privacy">
        <Select
          value={defaults.privacy}
          options={PRIVACY_OPTIONS}
          onChange={(e) => set({ privacy: e.target.value as Privacy })}
        />
      </FormField>
      <div className="grid-2">
        <FormField
          label="Category id"
          required
          hint="YouTube category, for example 1 for Film and Animation."
          error={defaults.category_id.trim() === "" ? "Required." : undefined}
        >
          <Input
            value={defaults.category_id}
            onChange={(e) => set({ category_id: e.target.value })}
          />
        </FormField>
        <FormField
          label="Default language"
          required
          hint="BCP-47 code such as en or ta."
          error={defaults.default_language.trim() === "" ? "Required." : undefined}
        >
          <Input
            value={defaults.default_language}
            onChange={(e) => set({ default_language: e.target.value })}
          />
        </FormField>
      </div>
      <Switch
        checked={defaults.made_for_kids}
        onChange={(made_for_kids) => set({ made_for_kids })}
        label="Made for kids"
      />
      <Switch
        checked={defaults.notify_subscribers}
        onChange={(notify_subscribers) => set({ notify_subscribers })}
        label="Notify subscribers on upload"
      />
    </Dialog>
  );
}
