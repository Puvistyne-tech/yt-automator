import type { PipelineDescriptor } from "@/api/types";
import type { SettingsView } from "@/features/automation-editor/model/settingsView";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { SettingsSearch } from "@/features/automation-editor/sections/SettingsSearch";
import type { SettingsFilterState } from "@/features/automation-editor/useSettingsView";
import { scopedErrors } from "@/shared/schema-form/errors";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";
import { Button, EmptyState } from "@/shared/ui";

interface ContentSectionProps extends SectionProps {
  pipeline: PipelineDescriptor | undefined;
  view: SettingsView;
  filter: SettingsFilterState;
}

function NoMatches({ onClear }: { onClear: () => void }) {
  return (
    <EmptyState
      icon="inbox"
      title="No settings match"
      description="Try another word, or turn off Changed only."
      action={
        <Button size="sm" onClick={onClear}>
          Clear search
        </Button>
      }
    />
  );
}

function PipelineForm(props: ContentSectionProps & { pipeline: PipelineDescriptor }) {
  const { draft, onChange, errors, pipeline, filter } = props;
  if (filter.nothingFound) {
    return <NoMatches onClear={filter.search.clear} />;
  }
  return (
    <SchemaForm
      key={pipeline.type_id}
      idPrefix="settings"
      schema={pipeline.settings_schema}
      uiSchema={pipeline.ui_schema}
      value={draft.settings}
      defaults={pipeline.default_settings}
      onChange={(settings) => onChange({ ...draft, settings })}
      errors={scopedErrors(errors, "settings")}
      visible={filter.visible}
      filtered={filter.filtered}
      concealed={filter.concealed}
    />
  );
}

export function ContentSection(props: ContentSectionProps) {
  const { pipeline, view, filter } = props;
  return (
    <EditorSection
      id="content"
      title="Content"
      description={
        pipeline
          ? `Settings defined by ${pipeline.name}. Every run uses a snapshot of these values.`
          : "Settings appear once a pipeline type is chosen."
      }
    >
      {pipeline && view === "all" && <SettingsSearch search={filter.search} />}
      {pipeline ? (
        <PipelineForm {...props} pipeline={pipeline} />
      ) : (
        <EmptyState
          icon="automations"
          title="No pipeline chosen"
          description="Choose a pipeline type in General."
        />
      )}
    </EditorSection>
  );
}
