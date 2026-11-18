import type { ErrorSchema, RJSFSchema, RJSFValidationError } from "@rjsf/utils";
import validator from "@rjsf/validator-ajv8";

export type PathErrors = Record<string, string>;

export function propertyToPath(property: string | undefined): string {
  return (property ?? "")
    .replace(/\[['"]?([^\]'"]+)['"]?\]/g, ".$1")
    .replaceAll("/", ".")
    .replace(/^\.+/, "");
}

function sentence(text: string): string {
  const trimmed = text.trim();
  const capital = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  return /[.!?]$/.test(capital) ? capital : `${capital}.`;
}

export function messageFor(error: RJSFValidationError): string {
  if (error.name === "required") {
    return "This field is required.";
  }
  return sentence(error.message ?? "Invalid value");
}

export function validateSchemaData(schema: RJSFSchema, data: unknown): PathErrors {
  const { errors } = validator.validateFormData(data, schema);
  const result: PathErrors = {};
  for (const error of errors) {
    const path = propertyToPath(error.property);
    result[path] ??= messageFor(error);
  }
  return result;
}

export function scopedErrors(errors: PathErrors, prefix: string): PathErrors {
  const head = `${prefix}.`;
  return Object.fromEntries(
    Object.entries(errors)
      .filter(([path]) => path === prefix || path.startsWith(head))
      .map(([path, message]) => [path === prefix ? "" : path.slice(head.length), message]),
  );
}

type Node = { __errors?: string[]; [key: string]: unknown };

export function toErrorSchema(errors: PathErrors): ErrorSchema {
  const root: Node = {};
  for (const [path, message] of Object.entries(errors)) {
    let node = root;
    for (const segment of path.split(".").filter(Boolean)) {
      node[segment] ??= {};
      node = node[segment] as Node;
    }
    node.__errors = [...(node.__errors ?? []), message];
  }
  return root as ErrorSchema;
}
