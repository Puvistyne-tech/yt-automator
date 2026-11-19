import type { EngineSummary, TemplateSummary } from "@/api/types";
import { draftFromTemplate } from "@/features/pipeline-templates/model/form";
import { SampleScriptPanel } from "@/features/pipeline-templates/SampleScriptCard";
import { DuplicateTemplateDialog } from "@/features/pipeline-templates/TemplateDialogs";
import { TemplateFields } from "@/features/pipeline-templates/TemplateFields";
import { useDefinitionViewMode } from "@/features/pipeline-templates/useDefinitionView";
import { useTemplateErrors } from "@/features/pipeline-templates/useTemplateErrors";
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
  const mode = useDefinitionViewMode(engine);
  const problems = useTemplateErrors(mode.revealErrors);
  const draft = draftFromTemplate(template);
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
        draft={draft}
        onChange={() => undefined}
        errors={problems.errors}
        disabled
        mode={mode}
      />
      <SampleScriptPanel engineId={engine.engine_id} draft={draft} problems={problems} />
      <DuplicateTemplateDialog flow={duplicate} />
    </div>
  );
}
