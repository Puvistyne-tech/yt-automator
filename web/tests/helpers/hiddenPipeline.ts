import { HttpResponse, http } from "msw";
import { db } from "@/api/mocks/db";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { PipelineDescriptor } from "@/api/types";
import { findSection } from "./editor";
import { renderApp } from "./renderApp";
import { server } from "./server";

type Json = Record<string, unknown>;

export const storedBedtime = () => db.state.automations.find((a) => a.id === "auto-bedtime");

export function setBedtimeMusic(patch: Json) {
  const automation = storedBedtime();
  if (automation !== undefined) {
    const music = automation.settings.music as Json;
    automation.settings = { ...automation.settings, music: { ...music, ...patch } };
  }
}

function optionalMusic(schema: Json): Json {
  const properties = schema.properties as Json;
  const music = properties.music as Json;
  const optional = { anyOf: [music, { type: "null" }], title: music.title };
  return { ...schema, properties: { ...properties, music: optional } };
}

export function hidingPipeline(hidden: string[], { optional = false } = {}): PipelineDescriptor {
  const schema = kidsStoryPipeline.settings_schema as Json;
  return {
    ...kidsStoryPipeline,
    settings_schema: optional ? optionalMusic(schema) : schema,
    ui_schema: { ...kidsStoryPipeline.ui_schema, "ui:hidden": hidden },
  };
}

export async function openBedtimeWith(pipeline: PipelineDescriptor) {
  server.use(
    http.get("/api/pipelines", () => HttpResponse.json([pipeline])),
    http.get("/api/pipelines/:typeId", () => HttpResponse.json(pipeline)),
  );
  const app = renderApp("/automations/auto-bedtime");
  const content = await findSection("Content");
  return { ...app, content };
}
