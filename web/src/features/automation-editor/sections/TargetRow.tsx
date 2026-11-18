import { errorAt } from "@/api/errors";
import type { Channel, PipelineDescriptor } from "@/api/types";
import type { TargetDraft } from "@/features/automation-editor/model/draft";
import {
  type TargetOptions,
  targetChannelWarning,
} from "@/features/automation-editor/model/targets";
import {
  ChannelField,
  DelayField,
  KidsField,
  LanguageField,
  PlaylistField,
  PrivacyField,
} from "@/features/automation-editor/sections/TargetFields";
import { Callout, CheckboxGroup, Icon, IconButton } from "@/shared/ui";

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
  const error = (field: string) => errorAt(errors, `targets.${index}.${field}`);
  const field = { target, options, error, onChange };
  const channel = channels.find((c) => c.id === target.channel_id);
  const warning = targetChannelWarning(channel);
  return (
    <li className="target-row panel-inset panel-inset-muted" aria-label={`Target ${index + 1}`}>
      <TargetHead index={index} onRemove={props.onRemove} />
      {warning && (
        <Callout tone="warning">
          <Icon name="alert" />
          <span>{warning}</span>
        </Callout>
      )}
      <div className="target-grid">
        <ChannelField {...field} />
        <LanguageField {...field} pipeline={pipeline} />
        <PrivacyField {...field} channel={channel} />
        <PlaylistField {...field} />
        <KidsField {...field} />
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
