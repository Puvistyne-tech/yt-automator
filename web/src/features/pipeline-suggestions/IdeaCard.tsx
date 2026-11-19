import { useId } from "react";
import { AUDIENCE_LABELS } from "@/api/labels";
import { pipelinePath } from "@/api/paths";
import type { EngineSummary, TemplateSuggestion } from "@/api/types";
import { formatTitle } from "@/features/pipeline-suggestions/model/results";
import { type IdeaActions, useIdeaActions } from "@/features/pipeline-suggestions/useIdeaActions";
import { Badge, Button, ButtonLink } from "@/shared/ui";

const DREW_ON = "Trending videos it drew on";

function IdeaBadges({ engine, idea }: { engine: EngineSummary; idea: TemplateSuggestion }) {
  const format = formatTitle(engine, idea.input.definition);
  const audience = AUDIENCE_LABELS[idea.input.audience];
  return (
    <span className="row template-badges">
      {format !== null && <Badge tone="info">{format}</Badge>}
      <Badge tone={audience.tone}>{audience.label}</Badge>
    </span>
  );
}

function IdeaButtons({ name, actions }: { name: string; actions: IdeaActions }) {
  return (
    <div className="row">
      <Button variant="primary" onClick={actions.use}>
        Use this idea
      </Button>
      {actions.saved === undefined ? (
        <Button loading={actions.saving} onClick={actions.saveDraft}>
          Save as draft
        </Button>
      ) : (
        <ButtonLink to={pipelinePath(actions.saved.id)} aria-label={`Open ${name}`}>
          Saved as a draft: open
        </ButtonLink>
      )}
    </div>
  );
}

export function IdeaCard({ engine, idea }: { engine: EngineSummary; idea: TemplateSuggestion }) {
  const titleId = useId();
  const actions = useIdeaActions(idea.input);
  return (
    <article className="idea-card" aria-labelledby={titleId}>
      <div className="row idea-head">
        <h3 className="idea-title" id={titleId}>
          {idea.name}
        </h3>
        <IdeaBadges engine={engine} idea={idea} />
      </div>
      {idea.description && <p>{idea.description}</p>}
      <p>
        <strong>Why: </strong>
        {idea.reason}
      </p>
      <div className="subtle">
        <span>{DREW_ON}:</span>
        <ul className="idea-trends" aria-label={DREW_ON}>
          {idea.based_on.map((title) => (
            <li key={title}>{title}</li>
          ))}
        </ul>
      </div>
      <IdeaButtons name={idea.name} actions={actions} />
    </article>
  );
}
