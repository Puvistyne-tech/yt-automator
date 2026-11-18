export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: FieldErrors;

  constructor(status: number, code: string, message: string, fields: FieldErrors = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readFields(value: unknown): FieldErrors {
  if (!isRecord(value)) {
    return {};
  }
  return Object.fromEntries(
    Object.entries(value).filter(
      (entry): entry is [string, string] => typeof entry[1] === "string",
    ),
  );
}

export function apiErrorFromBody(status: number, body: unknown, fallback: string): ApiError {
  const error = isRecord(body) && isRecord(body.error) ? body.error : null;
  if (error === null) {
    return new ApiError(status, `http_${status}`, fallback);
  }
  const code = typeof error.code === "string" ? error.code : `http_${status}`;
  const message = typeof error.message === "string" ? error.message : fallback;
  return new ApiError(status, code, message, readFields(error.fields));
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message !== "") {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

export function fieldErrorsOf(error: unknown): FieldErrors {
  return error instanceof ApiError ? error.fields : {};
}

export function normalizeFieldPath(path: string): string {
  return path
    .replace(/\[(\d+)\]/g, ".$1")
    .replace(/^(body\.)/, "")
    .replace(/^\./, "");
}

export function normalizeFieldErrors(fields: FieldErrors): FieldErrors {
  return Object.fromEntries(
    Object.entries(fields).map(([path, message]) => [normalizeFieldPath(path), message]),
  );
}

export function hasErrors(errors: FieldErrors): boolean {
  return Object.keys(errors).length > 0;
}
