import type { PipelineDescriptor } from "@/api/types";
import { applyPipeline } from "@/features/automation-editor/model/draft";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { pluralize } from "@/shared/format/text";
import { Badge, Callout, FormField, Icon, Input, RadioCards, Switch, Textarea } from "@/shared/ui";

interface GeneralSectionProps extends SectionProps {
  pipelines: PipelineDescriptor[];
  pipeline: PipelineDescriptor | undefined;
  isNew: boolean;
}

function PipelineMeta({ pipeline }: { pipeline: PipelineDescriptor }) {
  return (
    <span className="row pipeline-meta">
      <Badge>{pluralize(pipeline.languages.length, "language")}</Badge>
      <Badge>{pluralize(pipeline.variants.length, "output")}</Badge>
      <Badge>v{pipeline.version}</Badge>
    </span>
  );
}

function PipelinePicker({ pipelines, draft, onChange, errors }: GeneralSectionProps) {
  if (pipelines.length === 0) {
    return (
      <Callout tone="warning">
        <Icon name="alert" />
        <span>No pipeline types are installed, so there is nothing to automate yet.</span>
      </Callout>
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
  const { draft, onChange, errors, isNew, pipeline } = props;
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
        <FormField label="Description" hint="Optional. Only shown inside this app.">
          <Textarea
            rows={2}
            value={draft.description}
            onChange={(e) => onChange({ ...draft, description: e.target.value })}
          />
        </FormField>
        {isNew ? <PipelinePicker {...props} /> : <PipelineSummary pipeline={pipeline} />}
        <Switch
          checked={draft.enabled}
          onChange={(enabled) => onChange({ ...draft, enabled })}
          label="Enabled: run on schedule"
        />
      </div>
    </EditorSection>
  );
}
