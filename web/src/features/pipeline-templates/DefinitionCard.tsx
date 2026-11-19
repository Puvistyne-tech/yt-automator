import type { FieldErrors } from "@/api/errors";
import type { EngineSummary, JsonObject } from "@/api/types";
import {
  DEFINITION_SCOPE,
  type DefinitionFilter,
} from "@/features/pipeline-templates/useDefinitionView";
import { scopedErrors } from "@/shared/schema-form/errors";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";
import { NoSettingsMatch } from "@/shared/settings-view/NoSettingsMatch";
import { SettingsSearch } from "@/shared/settings-view/SettingsSearch";
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

function DefinitionForm(props: DefinitionCardProps) {
  const { engine, filter } = props;
  if (filter.nothingFound) {
    return <NoSettingsMatch onClear={filter.search.clear} hint="Try another word." />;
  }
  return (
    <SchemaForm
      idPrefix={DEFINITION_SCOPE}
      schema={engine.definition_schema}
      uiSchema={engine.definition_ui_schema}
      value={props.definition}
      onChange={props.onChange}
      errors={scopedErrors(props.errors, DEFINITION_SCOPE)}
      disabled={props.disabled}
      visible={filter.visible}
      filtered={filter.filtered}
      concealed={filter.concealed}
    />
  );
}

export function DefinitionCard(props: DefinitionCardProps) {
  return (
    <Card
      title="What the videos are like"
      description={`Built from the ${props.engine.name} template. Automations using this pipeline start from these choices.`}
    >
      {props.view === "all" && (
        <SettingsSearch search={props.filter.search} offerChangedOnly={false} />
      )}
      <DefinitionForm {...props} />
    </Card>
  );
}
