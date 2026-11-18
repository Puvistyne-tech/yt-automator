import { useUpdateChannelDefaults } from "@/api/channels";
import { type FieldErrors, hasErrors } from "@/api/errors";
import { PRIVACY_OPTIONS, privacyFromValue } from "@/api/labels";
import type { Channel, ChannelDefaults } from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { channelDefaultsPayload, validateChannelDefaults } from "@/features/channels/defaultsForm";
import { usePatchState } from "@/shared/hooks/usePatchState";
import { FormDialog, FormField, Input, Select, Switch } from "@/shared/ui";

interface DefaultsFieldsProps {
  defaults: ChannelDefaults;
  errors: FieldErrors;
  onChange: (patch: Partial<ChannelDefaults>) => void;
}

function CodeFields({ defaults, errors, onChange }: DefaultsFieldsProps) {
  return (
    <div className="grid-2">
      <FormField
        label="Category id"
        required
        hint="YouTube category, for example 1 for Film and Animation."
        error={errors.category_id}
      >
        <Input
          value={defaults.category_id}
          onChange={(e) => onChange({ category_id: e.target.value })}
        />
      </FormField>
      <FormField
        label="Default language"
        required
        hint="BCP-47 code such as en or ta."
        error={errors.default_language}
      >
        <Input
          value={defaults.default_language}
          onChange={(e) => onChange({ default_language: e.target.value })}
        />
      </FormField>
    </div>
  );
}

function DefaultsFields({ defaults, errors, onChange }: DefaultsFieldsProps) {
  return (
    <>
      <FormField label="Privacy">
        <Select
          value={defaults.privacy}
          options={PRIVACY_OPTIONS}
          onChange={(e) =>
            onChange({ privacy: privacyFromValue(e.target.value) ?? defaults.privacy })
          }
        />
      </FormField>
      <CodeFields defaults={defaults} errors={errors} onChange={onChange} />
      <Switch
        checked={defaults.made_for_kids}
        onChange={(made_for_kids) => onChange({ made_for_kids })}
        label="Made for kids"
      />
      <Switch
        checked={defaults.notify_subscribers}
        onChange={(notify_subscribers) => onChange({ notify_subscribers })}
        label="Notify subscribers on upload"
      />
    </>
  );
}

export function ChannelDefaultsDialog({
  channel,
  onClose,
}: {
  channel: Channel;
  onClose: () => void;
}) {
  const [defaults, patch] = usePatchState<ChannelDefaults>(channel.defaults);
  const update = useUpdateChannelDefaults();
  const notifier = useMutationNotifier();
  const errors = validateChannelDefaults(defaults);
  const submit = () =>
    update.mutate(
      { id: channel.id, defaults: channelDefaultsPayload(defaults) },
      notifier.handlers({ success: `Saved defaults for ${channel.title}.`, onSuccess: onClose }),
    );
  return (
    <FormDialog
      title={`Upload defaults for ${channel.title}`}
      description="Targets use these unless an automation overrides them."
      submitLabel="Save defaults"
      busy={update.isPending}
      submitDisabled={hasErrors(errors)}
      onSubmit={submit}
      onClose={onClose}
    >
      <DefaultsFields defaults={defaults} errors={errors} onChange={patch} />
    </FormDialog>
  );
}
