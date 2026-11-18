import { HttpResponse, http } from "msw";
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
