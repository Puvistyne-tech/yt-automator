import { pipelineAudience } from "@/api/capabilities";
import { AUDIENCE_LABELS } from "@/api/labels";
import type { PipelineDescriptor } from "@/api/types";
import { applyPipeline } from "@/features/automation-editor/model/draft";
import { enabledSwitchLabel } from "@/features/automation-editor/model/general";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { pluralize } from "@/shared/format/text";
import { AlertCallout, Badge, FormField, Input, RadioCards, Switch, Textarea } from "@/shared/ui";

interface GeneralSectionProps extends SectionProps {
  pipelines: PipelineDescriptor[];
  pipeline: PipelineDescriptor | undefined;
  isNew: boolean;
}

function PipelineMeta({ pipeline }: { pipeline: PipelineDescriptor }) {
  const audience = AUDIENCE_LABELS[pipelineAudience(pipeline)];
  return (
    <span className="row pipeline-meta">
      <Badge tone={audience.tone}>{audience.label}</Badge>
      <Badge>{pluralize(pipeline.languages.length, "language")}</Badge>
      <Badge>{pluralize(pipeline.variants.length, "output")}</Badge>
      <Badge>v{pipeline.version}</Badge>
    </span>
  );
}

function PipelinePicker({ pipelines, draft, onChange, errors }: GeneralSectionProps) {
  if (pipelines.length === 0) {
    return (
      <AlertCallout tone="warning">
        No pipeline types are installed, so there is nothing to automate yet.
      </AlertCallout>
    );
  }
  const choose = (typeId: string) => {
    const chosen = pipelines.find((p) => p.type_id === typeId);
    if (chosen !== undefined && chosen.type_id !== draft.pipeline_type) {
      onChange(applyPipeline(draft, chosen));
    }
  };
  return (
    <RadioCards
      label="Pipeline type"
      columns={2}
      value={draft.pipeline_type}
      onChange={choose}
      error={errors.pipeline_type}
      options={pipelines.map((p) => ({
        value: p.type_id,
        label: p.name,
        description: p.description,
        meta: <PipelineMeta pipeline={p} />,
      }))}
    />
  );
}

function PipelineSummary({ pipeline }: { pipeline: PipelineDescriptor | undefined }) {
  if (pipeline === undefined) {
    return null;
  }
  return (
    <div className="pipeline-summary">
      <span className="field-label">Pipeline type</span>
      <div className="panel-inset panel-inset-muted">
        <strong>{pipeline.name}</strong>
        <p className="muted">{pipeline.description}</p>
        <PipelineMeta pipeline={pipeline} />
      </div>
    </div>
  );
}

export function GeneralSection(props: GeneralSectionProps) {
  const { draft, onChange, errors, isNew, pipeline, shows } = props;
  return (
    <EditorSection
      id="general"
      title="General"
      description="Name the automation and pick what it makes."
    >
      <div className="stack">
        <FormField label="Name" required error={errors.name}>
          <Input
            value={draft.name}
            placeholder="Bedtime stories"
            onChange={(e) => onChange({ ...draft, name: e.target.value })}
          />
        </FormField>
        {shows("description") && (
          <FormField label="Description" hint="Optional. Only shown inside this app.">
            <Textarea
              rows={2}
              value={draft.description}
              onChange={(e) => onChange({ ...draft, description: e.target.value })}
            />
          </FormField>
        )}
        {isNew ? <PipelinePicker {...props} /> : <PipelineSummary pipeline={pipeline} />}
        <Switch
          checked={draft.enabled}
          onChange={(enabled) => onChange({ ...draft, enabled })}
          label={enabledSwitchLabel(draft.schedule.kind)}
        />
      </div>
    </EditorSection>
  );
}
