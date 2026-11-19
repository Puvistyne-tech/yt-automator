import { useTemplateEngines } from "@/api/templates";
import type { EngineSummary } from "@/api/types";
import { SuggestionForm } from "@/features/pipeline-suggestions/SuggestionForm";
import { SuggestionResults } from "@/features/pipeline-suggestions/SuggestionResults";
import { usePipelineSuggestions } from "@/features/pipeline-suggestions/usePipelineSuggestions";
import { Card, EmptyState, IconButton, LinkCallout, ProgressLine, QueryState } from "@/shared/ui";
import "@/features/pipeline-suggestions/pipeline-suggestions.css";

const TITLE = "Suggest ideas";
const FINDING = "Finding ideas";

function SuggestionsBody({ engine }: { engine: EngineSummary }) {
  const state = usePipelineSuggestions(engine);
  return (
    <div className="stack">
      <SuggestionForm state={state} />
      {state.finding && (
        <ProgressLine label={FINDING}>
          {FINDING} in what is trending. This can take a minute.
        </ProgressLine>
      )}
      <LinkCallout message={state.unavailable} to="/providers" action="Open Providers" />
      {state.result !== undefined && (
        <SuggestionResults engine={engine} result={state.result} region={state.region} />
      )}
    </div>
  );
}

export function PipelineSuggestions({ onClose }: { onClose: () => void }) {
  const engines = useTemplateEngines();
  return (
    <Card
      title={TITLE}
      aria-label={TITLE}
      className="suggestions-panel"
      description="A text model reads what is trending and suggests new pipelines. Nothing is saved until you choose."
      actions={<IconButton icon="x" label="Close" onClick={onClose} />}
    >
      <QueryState
        query={engines}
        loadingLabel="Loading"
        isEmpty={(list) => list.length === 0}
        empty={<EmptyState icon="pipelines" title="No pipeline templates are installed" />}
      >
        {([engine]) => engine !== undefined && <SuggestionsBody engine={engine} />}
      </QueryState>
    </Card>
  );
}
