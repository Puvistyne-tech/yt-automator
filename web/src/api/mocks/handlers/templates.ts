import { HttpResponse, http } from "msw";
import { db, noContent, notFound, validationFailed } from "@/api/mocks/db";
import { USER_TYPE_PREFIX } from "@/api/mocks/fixtures/templates";
import {
  allTemplates,
  builtinConflict,
  copyName,
  engineErrors,
  immutableErrors,
  nameErrors,
  originErrors,
  summaryOf,
} from "@/api/mocks/templateRules";
import { DELETE_REMEDY, DRAFT_REMEDY, inUseConflict } from "@/api/mocks/templateUsage";
import type { DuplicateTemplateRequest, PipelineTemplate, TemplateInput } from "@/api/types";

const findTemplate = (id: unknown) => allTemplates(db.state).find((t) => t.id === id);

function reply(template: PipelineTemplate, status = 200) {
  return HttpResponse.json(summaryOf(db.state, template), { status });
}

function store(template: PipelineTemplate) {
  const others = db.state.templates.filter((t) => t.id !== template.id);
  db.state.templates = [...others, template];
}

function created(
  fields: Omit<PipelineTemplate, "id" | "type_id" | "revision" | "created_at" | "updated_at">,
) {
  const id = db.id("template");
  const now = db.now();
  const template = {
    ...fields,
    id,
    type_id: `${USER_TYPE_PREFIX}${id}`,
    revision: 1,
    created_at: now,
    updated_at: now,
  };
  store(template);
  return reply(template, 201);
}

function updated(current: PipelineTemplate, input: TemplateInput) {
  const errors = {
    ...immutableErrors(current, input),
    ...nameErrors(input.name),
    ...engineErrors(db.state, { ...input, engine: current.engine }),
  };
  if (Object.keys(errors).length > 0) {
    return validationFailed(errors);
  }
  const unready = current.status === "ready" && input.status === "draft";
  const conflict = unready ? inUseConflict(db.state, current.type_id, DRAFT_REMEDY) : null;
  if (conflict !== null) {
    return conflict;
  }
  const { origin: _ignored, ...edits } = input;
  const next = {
    ...current,
    ...edits,
    name: input.name.trim(),
    revision: current.revision + 1,
    updated_at: db.now(),
  };
  store(next);
  return reply(next);
}

function withEditable(
  id: unknown,
  act: (template: PipelineTemplate) => Response | Promise<Response>,
) {
  const current = findTemplate(id);
  if (current === undefined) {
    return notFound("template", id);
  }
  return current.origin === "builtin" ? builtinConflict(current) : act(current);
}

function removed(current: PipelineTemplate) {
  const conflict = inUseConflict(db.state, current.type_id, DELETE_REMEDY);
  if (conflict !== null) {
    return conflict;
  }
  db.state.templates = db.state.templates.filter((t) => t.id !== current.id);
  return noContent();
}

export const templateHandlers = [
  http.get("/api/template-engines", () => HttpResponse.json(db.state.engines)),
  http.get("/api/templates", () =>
    HttpResponse.json(allTemplates(db.state).map((t) => summaryOf(db.state, t))),
  ),
  http.get("/api/templates/:id", ({ params }) => {
    const template = findTemplate(params.id);
    return template === undefined ? notFound("template", params.id) : reply(template);
  }),
  http.post("/api/templates", async ({ request }) => {
    const input = (await request.json()) as TemplateInput;
    const errors = {
      ...originErrors(input),
      ...nameErrors(input.name),
      ...engineErrors(db.state, input),
    };
    if (Object.keys(errors).length > 0) {
      return validationFailed(errors);
    }
    return created({ origin: "blank", ...input, name: input.name.trim() });
  }),
  http.put("/api/templates/:id", ({ params, request }) =>
    withEditable(params.id, async (current) =>
      updated(current, (await request.json()) as TemplateInput),
    ),
  ),
  http.delete("/api/templates/:id", ({ params }) => withEditable(params.id, removed)),
  http.post("/api/templates/:id/duplicate", async ({ params, request }) => {
    const source = findTemplate(params.id);
    if (source === undefined) {
      return notFound("template", params.id);
    }
    const body = ((await request.json().catch(() => null)) ?? {}) as DuplicateTemplateRequest;
    const name = body.name ?? copyName(source.name);
    const audience = body.audience ?? source.audience;
    const errors = { ...nameErrors(name), ...engineErrors(db.state, source) };
    if (Object.keys(errors).length > 0) {
      return validationFailed(errors);
    }
    const {
      id: _id,
      type_id: _type,
      revision: _revision,
      created_at: _c,
      updated_at: _u,
      ...rest
    } = source;
    return created({
      ...rest,
      name: name.trim(),
      audience,
      status: "draft",
      origin: "duplicate",
    });
  }),
];
