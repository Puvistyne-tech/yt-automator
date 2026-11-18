import type { Channel, PipelineDescriptor } from "@/api/types";
import { type AutomationDraft, newTarget } from "@/features/automation-editor/model/draft";
import {
  type TargetOptions,
  targetOptions,
  updateTarget,
} from "@/features/automation-editor/model/targets";
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

function AddTargetButton({ reason, onAdd }: { reason: string | null; onAdd: () => void }) {
  return (
    <Button
      size="sm"
      icon="plus"
      onClick={onAdd}
      disabled={reason !== null}
      title={reason ?? undefined}
    >
      Add target
    </Button>
  );
}

function TargetList({
  draft,
  onChange,
  errors,
  pipeline,
  channels,
  options,
}: TargetsSectionProps & { options: TargetOptions }) {
  const remove = (key: string) =>
    onChange({ ...draft, targets: draft.targets.filter((t) => t.key !== key) });
  return (
    <ol className="list-stack">
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
  );
}

function withNewTarget(draft: AutomationDraft, pipeline: PipelineDescriptor, channels: Channel[]) {
  return { ...draft, targets: [...draft.targets, newTarget(draft, pipeline, channels)] };
}

export function TargetsSection(props: TargetsSectionProps) {
  const { draft, onChange, pipeline, channels } = props;
  const options = targetOptions(pipeline, draft, channels);
  const add = () => onChange(withNewTarget(draft, pipeline, channels));
  return (
    <EditorSection
      id="targets"
      title="Targets"
      description="Where each language and output is published once a run is approved."
      actions={<AddTargetButton reason={options.addBlockedReason} onAdd={add} />}
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
        <TargetList {...props} options={options} />
      )}
    </EditorSection>
  );
}
