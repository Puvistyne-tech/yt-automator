import { useMemo, useState } from "react";
import { usePipelines } from "@/api/catalog";
import { PREVIEW_UNAVAILABLE, unavailableMessageOf } from "@/api/templateErrors";
import { usePreviewTemplateScript, useTemplates } from "@/api/templates";
import type { TemplateDraft } from "@/features/pipeline-templates/model/form";
import {
  chosenLanguage,
  engineLanguages,
  previewRequest,
} from "@/features/pipeline-templates/model/preview";
import type { TemplateErrors } from "@/features/pipeline-templates/useTemplateErrors";

export interface SampleInput {
  engineId: string;
  draft: TemplateDraft;
  problems: TemplateErrors;
}

function useEngineLanguages(engineId: string) {
  const templates = useTemplates();
  const pipelines = usePipelines();
  return useMemo(
    () => engineLanguages(engineId, templates.data ?? [], pipelines.data ?? []),
    [engineId, templates.data, pipelines.data],
  );
}

export function useSampleScript({ engineId, draft, problems }: SampleInput) {
  const preview = usePreviewTemplateScript();
  const languages = useEngineLanguages(engineId);
  const [language, setLanguage] = useState("");
  const [topic, setTopic] = useState("");
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const onError = (error: unknown) => {
    const message = unavailableMessageOf(error, PREVIEW_UNAVAILABLE);
    setUnavailable(message);
    if (message === null) {
      problems.report(error);
    }
  };
  const write = () => {
    setUnavailable(null);
    problems.clear();
    const choice = { language: chosenLanguage(language, languages), topic };
    preview.mutate(previewRequest(draft, engineId, choice), { onError });
  };
  return {
    languages,
    language: chosenLanguage(language, languages) ?? "",
    setLanguage,
    topic,
    setTopic,
    write,
    writing: preview.isPending,
    sample: preview.data,
    unavailable,
    errors: problems.errors,
  };
}

export type SampleScriptState = ReturnType<typeof useSampleScript>;
