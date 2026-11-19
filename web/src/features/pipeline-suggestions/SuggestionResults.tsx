import { Link } from "react-router";
import type { EngineSummary, TemplateSuggestions } from "@/api/types";
import { IdeaCard } from "@/features/pipeline-suggestions/IdeaCard";
import { droppedText, sourceText } from "@/features/pipeline-suggestions/model/results";
import { withUniqueKeys } from "@/shared/uniqueKeys";

function SourceNote({ result, region }: { result: TemplateSuggestions; region: string }) {
  const dropped = droppedText(result.dropped);
  return (
    <div className="suggestion-source subtle">
      <p>
        {sourceText(result.source, region)}{" "}
        {result.source === "sample" && <Link to="/channels">Connect a channel</Link>}
      </p>
      <p>Written by {result.provider}.</p>
      {dropped !== null && <p>{dropped}</p>}
    </div>
  );
}

export function SuggestionResults({
  engine,
  result,
  region,
}: {
  engine: EngineSummary;
  result: TemplateSuggestions;
  region: string;
}) {
  return (
    <div className="stack">
      <SourceNote result={result} region={region} />
      <div className="idea-list">
        {withUniqueKeys(result.suggestions, (idea) => idea.name).map(({ key, item }) => (
          <IdeaCard key={key} engine={engine} idea={item} />
        ))}
      </div>
    </div>
  );
}
