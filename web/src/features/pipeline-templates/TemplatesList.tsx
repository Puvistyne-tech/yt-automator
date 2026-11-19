import { useTemplates } from "@/api/templates";
import {
  DeleteTemplateDialog,
  DuplicateTemplateDialog,
} from "@/features/pipeline-templates/TemplateDialogs";
import { TemplateItem } from "@/features/pipeline-templates/TemplateItem";
import {
  useDeleteTemplateFlow,
  useDuplicateTemplateFlow,
} from "@/features/pipeline-templates/useTemplateFlows";
import { ButtonLink, Card, EmptyState, QueryState } from "@/shared/ui";
import "@/features/pipeline-templates/pipeline-templates.css";

function TemplatesEmpty() {
  return (
    <EmptyState
      icon="pipelines"
      title="No pipelines yet"
      description="A pipeline decides what the videos are about and how they look and sound."
      action={
        <ButtonLink to="/pipelines/new" variant="primary" icon="plus">
          New pipeline
        </ButtonLink>
      }
    />
  );
}

export function TemplatesList() {
  const templates = useTemplates();
  const duplicateFlow = useDuplicateTemplateFlow();
  const deleteFlow = useDeleteTemplateFlow();
  const actions = { duplicate: duplicateFlow.ask, remove: deleteFlow.ask };
  return (
    <Card flush>
      <QueryState
        query={templates}
        loadingLabel="Loading pipelines"
        isEmpty={(list) => list.length === 0}
        empty={<TemplatesEmpty />}
      >
        {(list) => (
          <ul className="list-reset divided-list" aria-label="Pipelines">
            {list.map((template) => (
              <TemplateItem key={template.id} template={template} actions={actions} />
            ))}
          </ul>
        )}
      </QueryState>
      <DuplicateTemplateDialog flow={duplicateFlow} />
      <DeleteTemplateDialog flow={deleteFlow} />
    </Card>
  );
}
