import type { TemplateInput } from "@/api/types";

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
