import { useState } from "react";
import { NEW_PIPELINE_PATH } from "@/api/paths";
import { PipelineSuggestions } from "@/features/pipeline-suggestions";
import { TemplatesList } from "@/features/pipeline-templates";
import { Button, ButtonLink, PageHeader } from "@/shared/ui";

export function PipelinesPage() {
  const [suggesting, setSuggesting] = useState(false);
  return (
    <>
      <PageHeader
        title="Pipelines"
        description="A pipeline decides what the videos are about and how they look and sound. Automations pick a pipeline type and add channels, languages and a schedule."
        actions={
          <>
            <Button icon="spark" aria-expanded={suggesting} onClick={() => setSuggesting(true)}>
              Suggest ideas
            </Button>
            <ButtonLink to={NEW_PIPELINE_PATH} variant="primary" icon="plus">
              New pipeline
            </ButtonLink>
          </>
        }
      />
      {suggesting && <PipelineSuggestions onClose={() => setSuggesting(false)} />}
      <TemplatesList />
    </>
  );
}
