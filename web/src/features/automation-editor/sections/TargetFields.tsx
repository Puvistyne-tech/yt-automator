import { usePlaylists } from "@/api/channels";
import { privacyFromValue } from "@/api/labels";
import type { Channel, PipelineDescriptor } from "@/api/types";
import type { TargetDraft } from "@/features/automation-editor/model/draft";
import {
  KIDS_CHOICES,
  kidsFromValue,
  kidsValue,
  languageOptionsWithOrphan,
  privacyOptions,
  type TargetOptions,
} from "@/features/automation-editor/model/targets";
import { FormField, NumberInput, Select, Switch } from "@/shared/ui";

export interface TargetFieldProps {
  target: TargetDraft;
  options: TargetOptions;
  error: (field: string) => string | undefined;
  onChange: (patch: Partial<TargetDraft>) => void;
}

export function ChannelField({ target, options, error, onChange }: TargetFieldProps) {
  return (
    <FormField label="Channel" required error={error("channel_id")}>
      <Select
        value={target.channel_id}
        placeholder="Choose a channel"
        options={options.channels}
        onChange={(e) => onChange({ channel_id: e.target.value })}
      />
    </FormField>
  );
}

export function LanguageField({
  target,
  options,
  error,
  onChange,
  pipeline,
}: TargetFieldProps & { pipeline: PipelineDescriptor }) {
  return (
    <FormField label="Language" required error={error("language")}>
      <Select
        value={target.language}
        placeholder="Choose a language"
        options={languageOptionsWithOrphan(options.languages, target, pipeline)}
        onChange={(e) => onChange({ language: e.target.value })}
      />
    </FormField>
  );
}

export function PrivacyField({
  target,
  onChange,
  channel,
}: Pick<TargetFieldProps, "target" | "onChange"> & { channel: Channel | undefined }) {
  return (
    <FormField label="Privacy">
      <Select
        value={target.privacy ?? ""}
        options={privacyOptions(channel)}
        onChange={(e) => onChange({ privacy: privacyFromValue(e.target.value) })}
      />
    </FormField>
  );
}

export function PlaylistField({ target, onChange }: Pick<TargetFieldProps, "target" | "onChange">) {
  const playlists = usePlaylists(target.channel_id);
  const options = (playlists.data ?? []).map((p) => ({ value: p.id, label: p.title }));
  const hint = playlists.isError ? "Playlists could not be loaded." : undefined;
  return (
    <FormField label="Playlist" hint={hint}>
      <Select
        value={target.playlist_id ?? ""}
        placeholder={playlists.isLoading ? "Loading playlists…" : "No playlist"}
        options={options}
        disabled={target.channel_id === "" || playlists.isLoading}
        onChange={(e) => onChange({ playlist_id: e.target.value === "" ? null : e.target.value })}
      />
    </FormField>
  );
}

export function KidsField({ target, options, onChange }: Omit<TargetFieldProps, "error">) {
  if (options.kidsLocked) {
    return (
      <FormField label="Made for kids" hint="Always on for kids' content pipelines.">
        <Switch checked disabled onChange={() => undefined} ariaLabel="Made for kids" />
      </FormField>
    );
  }
  return (
    <FormField label="Made for kids">
      <Select
        value={kidsValue(target.made_for_kids)}
        options={KIDS_CHOICES}
        onChange={(e) => onChange({ made_for_kids: kidsFromValue(e.target.value) })}
      />
    </FormField>
  );
}

export function DelayField({ target, error, onChange }: Omit<TargetFieldProps, "options">) {
  return (
    <FormField label="Publish delay (minutes)" error={error("publish_delay_minutes")}>
      <NumberInput
        min={0}
        step={1}
        value={target.publish_delay_minutes}
        onValueChange={(publish_delay_minutes) => onChange({ publish_delay_minutes })}
      />
    </FormField>
  );
}
