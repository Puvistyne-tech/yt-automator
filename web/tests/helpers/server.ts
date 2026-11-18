import { HttpResponse, http, type JsonBodyType } from "msw";
import { setupServer } from "msw/node";
import { handlers } from "@/api/mocks/handlers";

export const server = setupServer(...handlers);

type Method = "get" | "post" | "put" | "patch" | "delete";

export function failWith(
  method: Method,
  path: string,
  status: number,
  error: { code?: string; message: string; fields?: Record<string, string> },
) {
  server.use(
    http[method](`/api${path}`, () =>
      HttpResponse.json(
        {
          error: {
            code: error.code ?? "error",
            message: error.message,
            fields: error.fields ?? {},
          },
        },
        { status },
      ),
    ),
  );
}

export function captureBody(method: Method, path: string, reply: JsonBodyType): () => unknown {
  let body: unknown;
  server.use(
    http[method](`/api${path}`, async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(reply);
    }),
  );
  return () => body;
}
