import { screen } from "@testing-library/react";
import type { TemplateInput } from "@/api/types";
import { renderApp } from "./renderApp";

export const TEMPLATE_INPUT: TemplateInput = {
  engine: "narrated_video",
  name: "Ocean wonders",
  description: "",
  audience: "general",
  status: "ready",
  definition: {},
};

export async function rejectionOf(call: () => Promise<unknown>): Promise<unknown> {
  try {
    await call();
  } catch (error) {
    return error;
  }
  throw new Error("expected a rejection");
}

export type PipelineAudience = "For kids" | "General audience";

export async function startNewPipeline(audience: PipelineAudience) {
  const app = renderApp("/pipelines/new");
  expect(await screen.findByText(/cannot be changed later/)).toBeInTheDocument();
  await app.user.click(screen.getByRole("radio", { name: new RegExp(`^${audience}`) }));
  await app.user.click(screen.getByRole("button", { name: "Continue" }));
  await screen.findByLabelText(/^What the videos are about/);
  return app;
}
