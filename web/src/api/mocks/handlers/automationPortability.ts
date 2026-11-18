import { HttpResponse, http } from "msw";
import {
  choiceErrors,
  documentErrors,
  exportDocument,
  importPreview,
  missingChoiceErrors,
  refusalMessage,
} from "@/api/mocks/automationImport";
import { apiError, db, notFound, validationFailed } from "@/api/mocks/db";
import { inputErrors, save } from "@/api/mocks/handlers/automations";
import type {
  AutomationDocument,
  AutomationInput,
  ImportPreview,
  ImportRequest,
} from "@/api/types";
import { isJsonObject } from "@/shared/isJsonObject";

type Errors = Record<string, string>;

function ruleErrors(input: AutomationInput): Errors {
  const known = new Set(db.state.channels.map((channel) => channel.id));
  const hidden = new Set(
    input.targets.flatMap((target, index) =>
      known.has(target.channel_id) ? [] : [`targets.${index}.channel_id`],
    ),
  );
  return Object.fromEntries(
    Object.entries(inputErrors(input))
      .filter(([path]) => !hidden.has(path))
      .map(([path, message]) => [`automation.${path}`, message]),
  );
}

type Checked = { preview: ImportPreview; errors: Errors } | { refused: Response };

async function checked(request: Request): Promise<Checked> {
  const body = (await request.json()) as Partial<ImportRequest>;
  const raw = body.document;
  if (!isJsonObject(raw)) {
    return { refused: validationFailed({ document: "Input should be a valid dictionary" }) };
  }
  const problems = documentErrors(raw);
  if (Object.keys(problems).length > 0) {
    return { refused: apiError(400, "validation_failed", refusalMessage(problems), problems) };
  }
  const chosen = body.channel_map ?? {};
  const document = raw as unknown as AutomationDocument;
  const { channels, pipelines } = db.state;
  const preview = importPreview(document, channels, chosen, pipelines);
  const errors = { ...choiceErrors(chosen, channels), ...ruleErrors(preview.automation) };
  return { preview, errors };
}

export const portabilityHandlers = [
  http.get("/api/automations/:id/export", ({ params }) => {
    const automation = db.state.automations.find((a) => a.id === params.id);
    return automation
      ? HttpResponse.json(exportDocument(automation, db.state.channels))
      : notFound("automation", params.id);
  }),
  http.post("/api/automations/import/preview", async ({ request }) => {
    const result = await checked(request);
    if ("refused" in result) {
      return result.refused;
    }
    const { preview, errors } = result;
    return Object.keys(errors).length > 0 ? validationFailed(errors) : HttpResponse.json(preview);
  }),
  http.post("/api/automations/import", async ({ request }) => {
    const result = await checked(request);
    if ("refused" in result) {
      return result.refused;
    }
    const errors = { ...result.errors, ...missingChoiceErrors(result.preview.unknown_channels) };
    return Object.keys(errors).length > 0
      ? validationFailed(errors)
      : save(result.preview.automation);
  }),
];
