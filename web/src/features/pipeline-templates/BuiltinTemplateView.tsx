import type { EngineSummary, TemplateSummary } from "@/api/types";
import { draftFromTemplate } from "@/features/pipeline-templates/model/form";
import { DuplicateTemplateDialog } from "@/features/pipeline-templates/TemplateDialogs";
import { TemplateFields } from "@/features/pipeline-templates/TemplateFields";
import { useDuplicateTemplateFlow } from "@/features/pipeline-templates/useTemplateFlows";
import { Button, Callout } from "@/shared/ui";
import "@/features/pipeline-templates/pipeline-templates.css";

export function BuiltinTemplateView({
  engine,
  template,
}: {
  engine: EngineSummary;
  template: TemplateSummary;
}) {
  const duplicate = useDuplicateTemplateFlow();
  return (
    <div className="template-form">
      <Callout tone="info">
        <span>
          Built-in pipelines cannot be changed. Duplicate this one to make your own version.
        </span>
        <Button variant="primary" icon="copy" onClick={() => duplicate.ask(template)}>
          Duplicate to customise
        </Button>
      </Callout>
      <TemplateFields
        engine={engine}
        draft={draftFromTemplate(template)}
        onChange={() => undefined}
        errors={{}}
        disabled
      />
      <DuplicateTemplateDialog flow={duplicate} />
    </div>
  );
}
