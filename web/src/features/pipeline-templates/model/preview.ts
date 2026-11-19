import type {
  LanguageOption,
  PipelineDescriptor,
  PipelineTemplate,
  SampleScene,
  TemplatePreviewInput,
} from "@/api/types";
import { type TemplateDraft, templateInput } from "@/features/pipeline-templates/model/form";

export interface SampleChoice {
  language: string | null;
  topic: string;
}

export function engineLanguages(
  engineId: string,
  templates: readonly PipelineTemplate[],
  pipelines: readonly PipelineDescriptor[],
): LanguageOption[] {
  const types = new Set(templates.filter((t) => t.engine === engineId).map((t) => t.type_id));
  const offered = pipelines.filter((p) => types.has(p.type_id)).flatMap((p) => p.languages);
  return offered.filter(
    (option, index) => offered.findIndex((other) => other.code === option.code) === index,
  );
}

export function chosenLanguage(
  choice: string,
  languages: readonly LanguageOption[],
): string | null {
  return choice || (languages[0]?.code ?? null);
}

export interface NumberedScene {
  number: number;
  scene: SampleScene;
}

export function numberedScenes(scenes: readonly SampleScene[]): NumberedScene[] {
  return scenes.map((scene, position) => ({ number: position + 1, scene }));
}

export function previewRequest(
  draft: TemplateDraft,
  engineId: string,
  choice: SampleChoice,
): TemplatePreviewInput {
  return { ...templateInput(draft, engineId, draft.status), ...choice };
}
