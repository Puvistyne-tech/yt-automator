import { usePlaylists } from "@/api/channels";
import { PRIVACY_LABELS, PRIVACY_ORDER } from "@/api/labels";
import type { Channel, PipelineDescriptor, Privacy } from "@/api/types";
import type { TargetDraft } from "@/features/automation-editor/model/draft";
import {
  languageOptionsWithOrphan,
  type TargetOptions,
} from "@/features/automation-editor/model/targets";
import { CheckboxGroup, FormField, IconButton, Input, Select, Switch } from "@/shared/ui";

interface TargetRowProps {
  index: number;
  target: TargetDraft;
  options: TargetOptions;
  pipeline: PipelineDescriptor;
  channels: Channel[];
  errors: Record<string, string>;
  onChange: (patch: Partial<TargetDraft>) => void;
  onRemove: () => void;
}

const KIDS_CHOICES = [
  { value: "default", label: "Channel default" },
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

function kidsValue(value: boolean | null): string {
  if (value === null) {
    return "default";
  }
  return value ? "yes" : "no";
}

function PlaylistField({
  channelId,
  value,
  onChange,
}: {
  channelId: string;
  value: string | null;
  onChange: (id: string | null) => void;
}) {
  const playlists = usePlaylists(channelId);
  const options = (playlists.data ?? []).map((p) => ({ value: p.id, label: p.title }));
  const hint = playlists.isError ? "Playlists could not be loaded." : undefined;
  return (
    <FormField label="Playlist" hint={hint}>
      <Select
        value={value ?? ""}
        placeholder={playlists.isLoading ? "Loading playlists…" : "No playlist"}
        options={options}
        disabled={channelId === "" || playlists.isLoading}
        onChange={(e) => onChange(e.target.value === "" ? null : e.target.value)}
      />
    </FormField>
  );
}

function privacyOptions(channel: Channel | undefined) {
  const fallback = channel ? ` (${PRIVACY_LABELS[channel.defaults.privacy]})` : "";
  return [
    { value: "", label: `Channel default${fallback}` },
    ...PRIVACY_ORDER.map((privacy) => ({ value: privacy, label: PRIVACY_LABELS[privacy] })),
  ];
}

function KidsField({
  target,
  options,
  onChange,
}: Pick<TargetRowProps, "target" | "options" | "onChange">) {
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
        onChange={(e) =>
          onChange({
            made_for_kids: e.target.value === "default" ? null : e.target.value === "yes",
          })
        }
      />
    </FormField>
  );
}

export function TargetRow({
  index,
  target,
  options,
  pipeline,
  channels,
  errors,
  onChange,
  onRemove,
}: TargetRowProps) {
  const at = (field: string) => errors[`targets.${index}.${field}`];
  const channel = channels.find((c) => c.id === target.channel_id);
  return (
    <li className="target-row" aria-label={`Target ${index + 1}`}>
      <div className="target-row-head">
        <span className="target-index">Target {index + 1}</span>
        <IconButton
          icon="trash"
          variant="danger"
          label={`Remove target ${index + 1}`}
          onClick={onRemove}
        />
      </div>
      <div className="target-grid">
        <FormField label="Channel" required error={at("channel_id")}>
          <Select
            value={target.channel_id}
            placeholder="Choose a channel"
            options={options.channels}
            onChange={(e) => onChange({ channel_id: e.target.value })}
          />
        </FormField>
        <FormField label="Language" required error={at("language")}>
          <Select
            value={target.language}
            placeholder="Choose a language"
            options={languageOptionsWithOrphan(options.languages, target, pipeline)}
            onChange={(e) => onChange({ language: e.target.value })}
          />
        </FormField>
        <FormField label="Privacy">
          <Select
            value={target.privacy ?? ""}
            options={privacyOptions(channel)}
            onChange={(e) =>
              onChange({ privacy: e.target.value === "" ? null : (e.target.value as Privacy) })
            }
          />
        </FormField>
        <PlaylistField
          channelId={target.channel_id}
          value={target.playlist_id}
          onChange={(playlist_id) => onChange({ playlist_id })}
        />
        <KidsField target={target} options={options} onChange={onChange} />
        <FormField label="Publish delay (minutes)" error={at("publish_delay_minutes")}>
          <Input
            type="number"
            min={0}
            step={1}
            value={Number.isNaN(target.publish_delay_minutes) ? "" : target.publish_delay_minutes}
            onChange={(e) => onChange({ publish_delay_minutes: e.target.valueAsNumber })}
          />
        </FormField>
      </div>
      <CheckboxGroup
        label="Outputs"
        options={options.variants}
        value={target.variants}
        onChange={(variants) => onChange({ variants })}
        error={at("variants")}
      />
    </li>
  );
}
