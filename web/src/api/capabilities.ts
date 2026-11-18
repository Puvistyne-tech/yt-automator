import type { PipelineDescriptor } from "@/api/types";

export const KIDS_CAPABILITY = "kids_content";

export function isKidsPipeline(pipeline: PipelineDescriptor | undefined): boolean {
  return pipeline?.capabilities.includes(KIDS_CAPABILITY) ?? false;
}
