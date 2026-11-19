import { useState } from "react";
import type { EngineSummary, TemplateAudience, TemplateSummary } from "@/api/types";
import { AUDIENCE_NOTE, AudienceChoice } from "@/features/pipeline-templates/AudienceChoice";
import { ConflictCallout } from "@/features/pipeline-templates/ConflictCallout";
import {
  draftFromInput,
  draftFromTemplate,
  newTemplateDraft,
  type TemplateDraft,
} from "@/features/pipeline-templates/model/form";
import type { NewTemplateStart } from "@/features/pipeline-templates/model/prefill";
import { SampleScriptPanel } from "@/features/pipeline-templates/SampleScriptCard";
import { DeleteTemplateDialog } from "@/features/pipeline-templates/TemplateDialogs";
import { TemplateFields } from "@/features/pipeline-templates/TemplateFields";
import { useDefinitionViewMode } from "@/features/pipeline-templates/useDefinitionView";
import { useEditorDelete } from "@/features/pipeline-templates/useEditorDelete";
import {
  type TemplateEditorState,
  useTemplateEditor,
} from "@/features/pipeline-templates/useTemplateEditor";
import type { SettingsView } from "@/shared/settings-view/settingsView";
import { Button, ButtonLink, Card, SaveBar } from "@/shared/ui";
import "@/features/pipeline-templates/pipeline-templates.css";

interface EditorProps {
  engine: EngineSummary;
  template: TemplateSummary | undefined;
  initial: TemplateDraft;
  startIn?: SettingsView;
}

function NewTemplateActions({ editor }: { editor: TemplateEditorState }) {
  return (
    <SaveBar
      dirty={editor.dirty}
      saving={editor.saving}
      saveLabel="Save and make ready"
      saveDisabled={false}
      onSave={() => editor.submit("ready")}
    >
      <ButtonLink to="/pipelines">Cancel</ButtonLink>
      <Button disabled={editor.saving} onClick={() => editor.submit("draft")}>
        Save as draft
      </Button>
    </SaveBar>
  );
}

function SavedTemplateActions({
  editor,
  template,
}: {
  editor: TemplateEditorState;
  template: TemplateSummary;
}) {
  const deleteFlow = useEditorDelete(editor);
  return (
    <SaveBar
      dirty={editor.dirty}
      saving={editor.saving}
      saveLabel="Save changes"
      saveDisabled={false}
      onSave={() => editor.submit(editor.draft.status)}
    >
      <Button variant="danger" icon="trash" onClick={() => deleteFlow.ask(template)}>
        Delete
      </Button>
      <ButtonLink to="/pipelines">Back to pipelines</ButtonLink>
      <DeleteTemplateDialog flow={deleteFlow} />
    </SaveBar>
  );
}

function Editor({ engine, template, initial, startIn }: EditorProps) {
  const mode = useDefinitionViewMode(engine, startIn);
  const editor = useTemplateEditor({
    engineId: engine.engine_id,
    definitionSchema: engine.definition_schema,
    template,
    initial,
    onErrorsShown: mode.revealErrors,
  });
  return (
    <div className="template-form">
      <TemplateFields
        engine={engine}
        draft={editor.draft}
        onChange={editor.update}
        errors={editor.problems.errors}
        revision={template?.revision}
        mode={mode}
      />
      <SampleScriptPanel
        engineId={engine.engine_id}
        draft={editor.draft}
        problems={editor.problems}
      />
      <ConflictCallout conflict={editor.problems.conflict} />
      {template === undefined ? (
        <NewTemplateActions editor={editor} />
      ) : (
        <SavedTemplateActions editor={editor} template={template} />
      )}
    </div>
  );
}

export function SavedTemplateEditor({
  engine,
  template,
}: {
  engine: EngineSummary;
  template: TemplateSummary;
}) {
  return <Editor engine={engine} template={template} initial={draftFromTemplate(template)} />;
}

function AudienceStep({ onChoose }: { onChoose: (audience: TemplateAudience) => void }) {
  const [audience, setAudience] = useState<TemplateAudience | "">("");
  return (
    <Card title="Audience" description={AUDIENCE_NOTE}>
      <div className="template-audience">
        <AudienceChoice value={audience} onChange={setAudience} />
        <div className="row">
          <Button
            variant="primary"
            disabled={audience === ""}
            onClick={() => audience !== "" && onChoose(audience)}
          >
            Continue
          </Button>
        </div>
      </div>
    </Card>
  );
}

function BlankTemplateEditor({ engine }: { engine: EngineSummary }) {
  const [audience, setAudience] = useState<TemplateAudience | null>(null);
  if (audience === null) {
    return <AudienceStep onChoose={setAudience} />;
  }
  return <NewEditor engine={engine} initial={newTemplateDraft(engine, audience)} />;
}

function NewEditor({ engine, initial }: { engine: EngineSummary; initial: TemplateDraft }) {
  return <Editor engine={engine} template={undefined} initial={initial} startIn="simple" />;
}

export function NewTemplateEditor({ start }: { start: NewTemplateStart }) {
  return start.prefill === null ? (
    <BlankTemplateEditor engine={start.engine} />
  ) : (
    <NewEditor engine={start.engine} initial={draftFromInput(start.prefill)} />
  );
}
