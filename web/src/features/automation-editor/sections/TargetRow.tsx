import type { Channel, PipelineDescriptor } from "@/api/types";
import type { TargetDraft } from "@/features/automation-editor/model/draft";
import type { TargetOptions } from "@/features/automation-editor/model/targets";
import {
  ChannelField,
  DelayField,
  KidsField,
  LanguageField,
  PlaylistField,
  PrivacyField,
} from "@/features/automation-editor/sections/TargetFields";
import { CheckboxGroup, IconButton } from "@/shared/ui";

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

function TargetHead({ index, onRemove }: Pick<TargetRowProps, "index" | "onRemove">) {
  return (
    <div className="target-row-head">
      <span className="target-index">Target {index + 1}</span>
      <IconButton
        icon="trash"
        variant="danger"
        label={`Remove target ${index + 1}`}
        onClick={onRemove}
      />
    </div>
  );
}

export function TargetRow(props: TargetRowProps) {
  const { index, target, options, pipeline, channels, errors, onChange } = props;
  const error = (field: string) => errors[`targets.${index}.${field}`];
  const field = { target, options, error, onChange };
  const channel = channels.find((c) => c.id === target.channel_id);
  return (
    <li className="target-row panel-inset panel-inset-muted" aria-label={`Target ${index + 1}`}>
      <TargetHead index={index} onRemove={props.onRemove} />
      <div className="target-grid">
        <ChannelField {...field} />
        <LanguageField {...field} pipeline={pipeline} />
        <PrivacyField target={target} onChange={onChange} channel={channel} />
        <PlaylistField target={target} onChange={onChange} />
        <KidsField target={target} options={options} onChange={onChange} />
        <DelayField target={target} error={error} onChange={onChange} />
      </div>
      <CheckboxGroup
        label="Outputs"
        options={options.variants}
        value={target.variants}
        onChange={(variants) => onChange({ variants })}
        error={error("variants")}
      />
    </li>
  );
}
