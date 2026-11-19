import { type PathErrors, scopedErrors } from "@/shared/schema-form/errors";
import { SchemaForm } from "@/shared/schema-form/SchemaForm";
import { NoSettingsMatch } from "@/shared/settings-view/NoSettingsMatch";
import { SettingsSearch } from "@/shared/settings-view/SettingsSearch";
import type { SettingsView } from "@/shared/settings-view/settingsView";
import type { SchemaViewState } from "@/shared/settings-view/useSettingsView";

type FormValue = Record<string, unknown>;

interface FilteredSchemaFormProps {
  scope: string;
  schema: FormValue;
  uiSchema: FormValue;
  value: FormValue;
  defaults?: FormValue;
  onChange: (value: FormValue) => void;
  errors: PathErrors;
  disabled?: boolean;
  view: SettingsView;
  filter: SchemaViewState;
  offerChangedOnly?: boolean;
  emptyHint?: string;
}

function FilteredForm(props: FilteredSchemaFormProps) {
  const { scope, filter } = props;
  if (filter.nothingFound) {
    return <NoSettingsMatch onClear={filter.search.clear} hint={props.emptyHint} />;
  }
  return (
    <SchemaForm
      idPrefix={scope}
      schema={props.schema}
      uiSchema={props.uiSchema}
      value={props.value}
      defaults={props.defaults}
      onChange={props.onChange}
      errors={scopedErrors(props.errors, scope)}
      disabled={props.disabled}
      visible={filter.visible}
      filtered={filter.filtered}
      concealed={filter.concealed}
    />
  );
}

export function FilteredSchemaForm(props: FilteredSchemaFormProps) {
  return (
    <>
      {props.view === "all" && (
        <SettingsSearch search={props.filter.search} offerChangedOnly={props.offerChangedOnly} />
      )}
      <FilteredForm {...props} />
    </>
  );
}
