import type { Channel, PipelineDescriptor } from "@/api/types";
import { newTarget } from "@/features/automation-editor/model/draft";
import { targetOptions, updateTarget } from "@/features/automation-editor/model/targets";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { TargetRow } from "@/features/automation-editor/sections/TargetRow";
import { Button, EmptyState } from "@/shared/ui";

interface TargetsSectionProps extends SectionProps {
  pipeline: PipelineDescriptor;
  channels: Channel[];
}

export function TargetsSection({
  draft,
  onChange,
  errors,
  pipeline,
  channels,
}: TargetsSectionProps) {
  const options = targetOptions(pipeline, draft, channels);
  const add = () =>
    onChange({ ...draft, targets: [...draft.targets, newTarget(draft, pipeline, channels)] });
  const remove = (key: string) =>
    onChange({ ...draft, targets: draft.targets.filter((t) => t.key !== key) });
  const addButton = (
    <Button
      size="sm"
      icon="plus"
      onClick={add}
      disabled={options.addBlockedReason !== null}
      title={options.addBlockedReason ?? undefined}
    >
      Add target
    </Button>
  );
  return (
    <EditorSection
      id="targets"
      title="Targets"
      description="Where each language and output is published once a run is approved."
      actions={addButton}
    >
      {draft.targets.length === 0 ? (
        <EmptyState
          icon="channels"
          title="No targets yet"
          description={
            options.addBlockedReason ??
            "Runs will still produce videos for review, but nothing is published until you add a target."
          }
        />
      ) : (
        <ol className="target-list">
          {draft.targets.map((target, index) => (
            <TargetRow
              key={target.key}
              index={index}
              target={target}
              options={options}
              pipeline={pipeline}
              channels={channels}
              errors={errors}
              onChange={(patch) => onChange(updateTarget(draft, target.key, patch))}
              onRemove={() => remove(target.key)}
            />
          ))}
        </ol>
      )}
    </EditorSection>
  );
}
