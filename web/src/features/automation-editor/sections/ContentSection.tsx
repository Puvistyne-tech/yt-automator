import type { PipelineDescriptor } from "@/api/types";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { scopedErrors } from "@/shared/schema-form/errors";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";
import { EmptyState } from "@/shared/ui";

interface ContentSectionProps extends SectionProps {
  pipeline: PipelineDescriptor | undefined;
}

export function ContentSection({ draft, onChange, errors, pipeline }: ContentSectionProps) {
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
        <SchemaForm
          key={pipeline.type_id}
          idPrefix="settings"
          schema={pipeline.settings_schema}
          uiSchema={pipeline.ui_schema}
          value={draft.settings}
          onChange={(settings) => onChange({ ...draft, settings })}
          errors={scopedErrors(errors, "settings")}
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
