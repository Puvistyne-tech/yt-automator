import type { FieldErrors } from "@/api/errors";
import type { EngineSummary, JsonObject } from "@/api/types";
import {
  DEFINITION_SCOPE,
  type DefinitionFilter,
} from "@/features/pipeline-templates/useDefinitionView";
import { FilteredSchemaForm } from "@/shared/settings-view/FilteredSchemaForm";
import type { SettingsView } from "@/shared/settings-view/settingsView";
import { Card } from "@/shared/ui";

interface DefinitionCardProps {
  engine: EngineSummary;
  definition: JsonObject;
  onChange: (definition: JsonObject) => void;
  errors: FieldErrors;
  disabled: boolean;
  view: SettingsView;
  filter: DefinitionFilter;
}

export function DefinitionCard({ engine, definition, view, ...rest }: DefinitionCardProps) {
  return (
    <Card
      title="What the videos are like"
      description={`Built from the ${engine.name} template. Automations using this pipeline start from these choices.`}
    >
      <FilteredSchemaForm
        {...rest}
        scope={DEFINITION_SCOPE}
        schema={engine.definition_schema}
        uiSchema={engine.definition_ui_schema}
        value={definition}
        view={view}
        offerChangedOnly={false}
        emptyHint="Try another word."
      />
    </Card>
  );
}
