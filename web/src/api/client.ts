import { ApiError, apiErrorFromBody } from "@/api/errors";

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type QueryValue = string | number | undefined;

export const API_BASE = "/api";
const REQUEST_ID = "X-Request-Id";

export function apiUrl(path: string, query: Record<string, QueryValue> = {}): string {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text === "") {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function send(method: Method, url: string, body?: unknown): Promise<Response> {
  const init: RequestInit = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    init.headers = { Accept: "application/json", "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  try {
    return await fetch(url, init);
  } catch {
    throw new ApiError(0, "network_error", "The server could not be reached.");
  }
}

export async function request<T>(
  method: Method,
  path: string,
  options: { body?: unknown; query?: Record<string, QueryValue> } = {},
): Promise<T> {
  const response = await send(method, apiUrl(path, options.query), options.body);
  const body = await readBody(response);
  if (!response.ok) {
    const fallback = response.statusText || "Request failed";
    throw apiErrorFromBody(response.status, body, fallback, response.headers.get(REQUEST_ID));
  }
  return body as T;
}

export async function requestText(path: string): Promise<string> {
  const response = await send("GET", apiUrl(path));
  if (!response.ok) {
    throw apiErrorFromBody(response.status, await readBody(response), "Could not load file");
  }
  return response.text();
}

export const api = {
  get: <T>(path: string, query?: Record<string, QueryValue>) =>
    request<T>("GET", path, query === undefined ? {} : { query }),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, { body }),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, { body }),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, { body }),
  delete: (path: string) => request<null>("DELETE", path),
};
