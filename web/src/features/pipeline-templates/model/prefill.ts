import type { EngineSummary, TemplateInput } from "@/api/types";

export interface NewTemplateStart {
  engine: EngineSummary;
  prefill: TemplateInput | null;
}

export function newTemplateStart(
  engines: readonly EngineSummary[],
  prefill: TemplateInput | null,
): NewTemplateStart | null {
  const prefillEngine = engines.find((engine) => engine.engine_id === prefill?.engine);
  if (prefill !== null && prefillEngine !== undefined) {
    return { engine: prefillEngine, prefill };
  }
  const [first] = engines;
  return first === undefined ? null : { engine: first, prefill: null };
}
