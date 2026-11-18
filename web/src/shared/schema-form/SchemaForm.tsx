import type { IChangeEvent } from "@rjsf/core";
import { withTheme } from "@rjsf/core";
import type { RJSFSchema, UiSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";
import { useMemo } from "react";
import { useChangeTracking } from "@/shared/schema-form/changeTracking";
import { type PathErrors, toErrorSchema } from "@/shared/schema-form/errors";
import { templates } from "@/shared/schema-form/templates";
import { widgets } from "@/shared/schema-form/widgets";
import "@/shared/schema-form/schema-form.css";

const ThemedForm = withTheme({ templates, widgets });

type FormValue = Record<string, unknown>;

interface SchemaFormProps {
  schema: Record<string, unknown>;
  uiSchema?: Record<string, unknown>;
  value: FormValue;
  onChange: (value: FormValue) => void;
  errors?: PathErrors;
  defaults?: FormValue;
  idPrefix: string;
  disabled?: boolean;
  visible?: ReadonlySet<string> | undefined;
}

export function SchemaForm({
  schema,
  uiSchema = {},
  value,
  onChange,
  errors = {},
  defaults,
  idPrefix,
  disabled = false,
  visible,
}: SchemaFormProps) {
  const extraErrors = useMemo(() => toErrorSchema(errors), [errors]);
  const changes = useChangeTracking(value, defaults, onChange, disabled);
  const formContext = useMemo(() => ({ changes, visible }), [changes, visible]);
  const resolvedUi = useMemo<UiSchema>(
    () => ({ ...uiSchema, "ui:submitButtonOptions": { norender: true } }),
    [uiSchema],
  );
  const handleChange = (event: IChangeEvent<FormValue>) => {
    if (event.formData !== undefined) {
      onChange(event.formData);
    }
  };
  return (
    <div className="schema-form">
      <ThemedForm
        tagName="div"
        schema={schema as RJSFSchema}
        uiSchema={resolvedUi}
        formData={value}
        validator={validator}
        onChange={handleChange}
        extraErrors={extraErrors}
        formContext={formContext}
        noValidate
        showErrorList={false}
        idPrefix={idPrefix}
        disabled={disabled}
      />
    </div>
  );
}
