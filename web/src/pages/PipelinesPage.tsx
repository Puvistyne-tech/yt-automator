import { TemplatesList } from "@/features/pipeline-templates";
import { ButtonLink, PageHeader } from "@/shared/ui";

export function PipelinesPage() {
  return (
    <>
      <PageHeader
        title="Pipelines"
        description="A pipeline decides what the videos are about and how they look and sound. Automations pick a pipeline type and add channels, languages and a schedule."
        actions={
          <ButtonLink to="/pipelines/new" variant="primary" icon="plus">
            New pipeline
          </ButtonLink>
        }
      />
      <TemplatesList />
    </>
  );
}
