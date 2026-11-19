import type { PipelineDescriptor } from "@/api/types";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import type { SettingsFilterState } from "@/features/automation-editor/useSettingsView";
import { FilteredSchemaForm } from "@/shared/settings-view/FilteredSchemaForm";
import type { SettingsView } from "@/shared/settings-view/settingsView";
import { EmptyState } from "@/shared/ui";

interface ContentSectionProps extends SectionProps {
  pipeline: PipelineDescriptor | undefined;
  view: SettingsView;
  filter: SettingsFilterState;
}

export function ContentSection(props: ContentSectionProps) {
  const { pipeline, view, filter, draft, onChange, errors } = props;
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
      {pipeline ? (
        <FilteredSchemaForm
          key={pipeline.type_id}
          scope="settings"
          schema={pipeline.settings_schema}
          uiSchema={pipeline.ui_schema}
          value={draft.settings}
          defaults={pipeline.default_settings}
          onChange={(settings) => onChange({ ...draft, settings })}
          errors={errors}
          view={view}
          filter={filter}
        />
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
