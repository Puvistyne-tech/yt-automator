import { getDefaultFormState, type RJSFSchema } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";

type FormValue = Record<string, unknown>;

export function withFormDefaults(schema: FormValue, value: FormValue): FormValue {
  const rjsfSchema = schema as RJSFSchema;
  return getDefaultFormState(validator, rjsfSchema, value, rjsfSchema) as FormValue;
}
