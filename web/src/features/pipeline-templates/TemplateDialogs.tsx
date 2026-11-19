import { useState } from "react";
import type { DuplicateTemplateRequest, TemplateSummary } from "@/api/types";
import { AUDIENCE_NOTE, AudienceChoice } from "@/features/pipeline-templates/AudienceChoice";
import { ConflictCallout } from "@/features/pipeline-templates/ConflictCallout";
import { duplicateRequest } from "@/features/pipeline-templates/model/form";
import type { TemplateFlow } from "@/features/pipeline-templates/useTemplateFlows";
import { ConfirmDialog, FormDialog, FormField, Input } from "@/shared/ui";

type DeleteFlow = TemplateFlow<void>;
type DuplicateFlow = TemplateFlow<DuplicateTemplateRequest>;

export function DeleteTemplateDialog({ flow }: { flow: DeleteFlow }) {
  const target = flow.confirm.target;
  if (target === null) {
    return null;
  }
  return (
    <ConfirmDialog
      {...flow.confirm.dialogProps}
      title="Delete pipeline?"
      message={
        <div className="template-dialog">
          <p>“{target.name}” will be removed. Runs it already made are kept.</p>
          <ConflictCallout conflict={flow.problems.conflict} />
        </div>
      }
      confirmLabel="Delete pipeline"
      busy={flow.busy}
      onConfirm={() => flow.submit(target)}
    />
  );
}

function DuplicateForm({ flow, source }: { flow: DuplicateFlow; source: TemplateSummary }) {
  const [name, setName] = useState("");
  const [audience, setAudience] = useState(source.audience);
  return (
    <FormDialog
      title={`Duplicate “${source.name}”`}
      description="The copy starts as a draft you can change freely."
      submitLabel="Duplicate"
      submitIcon="copy"
      busy={flow.busy}
      onSubmit={() => flow.submit(source, duplicateRequest(name, audience))}
      onClose={flow.confirm.cancel}
    >
      <div className="template-dialog">
        <FormField
          label="Name of the copy"
          hint="Leave empty to add “(copy)” to the name."
          error={flow.problems.errors.name}
        >
          <Input
            value={name}
            placeholder={`${source.name} (copy)`}
            onChange={(e) => setName(e.target.value)}
          />
        </FormField>
        <AudienceChoice value={audience} onChange={setAudience} />
        <p className="subtle">{AUDIENCE_NOTE}</p>
        <ConflictCallout conflict={flow.problems.conflict} />
      </div>
    </FormDialog>
  );
}

export function DuplicateTemplateDialog({ flow }: { flow: DuplicateFlow }) {
  const source = flow.confirm.target;
  return source === null ? null : <DuplicateForm key={source.id} flow={flow} source={source} />;
}
