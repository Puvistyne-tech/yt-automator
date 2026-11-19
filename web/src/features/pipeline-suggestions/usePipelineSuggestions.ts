import { useState } from "react";
import { SUGGESTIONS_UNAVAILABLE, unavailableMessageOf } from "@/api/templateErrors";
import { useSuggestTemplates } from "@/api/templates";
import type { EngineSummary } from "@/api/types";
import { useFieldErrors } from "@/api/useFieldErrors";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import {
  initialForm,
  type SuggestionForm,
  suggestionRequest,
} from "@/features/pipeline-suggestions/model/request";

export function usePipelineSuggestions(engine: EngineSummary) {
  const suggest = useSuggestTemplates();
  const fields = useFieldErrors();
  const notifier = useMutationNotifier();
  const [form, setForm] = useState(() => initialForm(navigator.language));
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const change = (changes: Partial<SuggestionForm>) => setForm({ ...form, ...changes });
  const onError = (error: unknown) => {
    const message = unavailableMessageOf(error, SUGGESTIONS_UNAVAILABLE);
    setUnavailable(message);
    if (message === null) {
      fields.setFromServer(error);
      notifier.fail(error);
    }
  };
  const find = () => {
    setUnavailable(null);
    fields.clear();
    suggest.mutate(suggestionRequest(form, engine.engine_id), { onError });
  };
  return {
    form,
    change,
    find,
    finding: suggest.isPending,
    result: suggest.data,
    region: suggest.variables?.region ?? "",
    unavailable,
    errors: fields.errors,
  };
}

export type SuggestionsState = ReturnType<typeof usePipelineSuggestions>;
