import type { FieldErrors } from "@/api/errors";
import { AUDIENCE_LABELS } from "@/api/labels";
import type { EngineSummary } from "@/api/types";
import { AUDIENCE_NOTE, audienceDescription } from "@/features/pipeline-templates/AudienceChoice";
import { DefinitionCard } from "@/features/pipeline-templates/DefinitionCard";
import type { TemplateDraft } from "@/features/pipeline-templates/model/form";
import {
  type DefinitionViewMode,
  useDefinitionFilter,
} from "@/features/pipeline-templates/useDefinitionView";
import { SettingsViewBar } from "@/shared/settings-view/SettingsViewBar";
import { Badge, Card, FormField, Input, Switch, Textarea } from "@/shared/ui";

interface TemplateFieldsProps {
  engine: EngineSummary;
  draft: TemplateDraft;
  onChange: (draft: TemplateDraft) => void;
  errors: FieldErrors;
  revision?: number | undefined;
  disabled?: boolean;
  mode: DefinitionViewMode;
}

function AudienceSummary({ draft }: { draft: TemplateDraft }) {
  const badge = AUDIENCE_LABELS[draft.audience];
  return (
    <div className="panel-inset panel-inset-muted stack-sm">
      <span className="row">
        <Badge tone={badge.tone}>{badge.label}</Badge>
        <span className="subtle">{audienceDescription(draft.audience)}</span>
      </span>
      <span className="subtle">{AUDIENCE_NOTE}</span>
    </div>
  );
}

function StatusField({ draft, onChange, revision }: TemplateFieldsProps) {
  return (
    <div className="row-between">
      <Switch
        checked={draft.status === "ready"}
        onChange={(ready) => onChange({ ...draft, status: ready ? "ready" : "draft" })}
        label="Ready to use in automations"
      />
      <span className="subtle">Revision {revision}</span>
    </div>
  );
}

function AboutCard(props: TemplateFieldsProps) {
  const { draft, onChange, errors, disabled = false } = props;
  return (
    <Card title="About this pipeline">
      <div className="stack">
        <FormField label="Name" required error={errors.name}>
          <Input
            value={draft.name}
            disabled={disabled}
            placeholder="Space facts"
            onChange={(e) => onChange({ ...draft, name: e.target.value })}
          />
        </FormField>
        <FormField label="Description" hint="Shown when choosing a pipeline type.">
          <Textarea
            rows={2}
            value={draft.description}
            disabled={disabled}
            onChange={(e) => onChange({ ...draft, description: e.target.value })}
          />
        </FormField>
        <AudienceSummary draft={draft} />
        {props.revision !== undefined && !disabled && <StatusField {...props} />}
      </div>
    </Card>
  );
}

export function TemplateFields(props: TemplateFieldsProps) {
  const { engine, draft, onChange, errors, mode } = props;
  const filter = useDefinitionFilter(engine, mode.view, errors);
  return (
    <div className="template-form">
      <SettingsViewBar view={mode.view} summary={filter.summary} onView={mode.setView} />
      <AboutCard {...props} />
      <DefinitionCard
        engine={engine}
        definition={draft.definition}
        onChange={(definition) => onChange({ ...draft, definition })}
        errors={errors}
        disabled={props.disabled ?? false}
        view={mode.view}
        filter={filter}
      />
    </div>
  );
}
