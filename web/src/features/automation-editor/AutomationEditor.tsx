import type { Channel, PipelineDescriptor } from "@/api/types";
import type { AutomationDraft } from "@/features/automation-editor/model/draft";
import {
  EDITOR_SECTIONS,
  errorCounts,
  sectionAnchor,
} from "@/features/automation-editor/model/sections";
import { RunNowButton } from "@/features/automation-editor/RunNowButton";
import { ContentSection } from "@/features/automation-editor/sections/ContentSection";
import { GeneralSection } from "@/features/automation-editor/sections/GeneralSection";
import { LanguagesSection } from "@/features/automation-editor/sections/LanguagesSection";
import { ReviewSection } from "@/features/automation-editor/sections/ReviewSection";
import { ScheduleSection } from "@/features/automation-editor/sections/ScheduleSection";
import { TargetsSection } from "@/features/automation-editor/sections/TargetsSection";
import { useAutomationEditor } from "@/features/automation-editor/useAutomationEditor";
import { ButtonLink, SaveBar } from "@/shared/ui";
import "@/features/automation-editor/editor.css";

interface AutomationEditorProps {
  automationId: string | undefined;
  initial: AutomationDraft;
  pipelines: PipelineDescriptor[];
  channels: Channel[];
}

function EditorNav({ errors }: { errors: Record<string, string> }) {
  const counts = errorCounts(errors);
  return (
    <nav className="editor-nav" aria-label="Editor sections">
      {EDITOR_SECTIONS.map((section) => (
        <a key={section.id} href={`#${sectionAnchor(section.id)}`} className="editor-nav-link">
          <span>{section.title}</span>
          {counts[section.id] > 0 && (
            <span
              className="editor-nav-errors"
              role="img"
              aria-label={`${counts[section.id]} problems`}
            >
              {counts[section.id]}
            </span>
          )}
        </a>
      ))}
    </nav>
  );
}

export function AutomationEditor(props: AutomationEditorProps) {
  const editor = useAutomationEditor(props);
  const { draft, update, pipeline, errors } = editor;
  const common = { draft, onChange: update, errors };
  return (
    <div className="editor">
      <EditorNav errors={errors} />
      <div className="editor-main">
        <GeneralSection
          {...common}
          pipelines={props.pipelines}
          pipeline={pipeline}
          isNew={props.automationId === undefined}
        />
        <ContentSection {...common} pipeline={pipeline} />
        {pipeline && <LanguagesSection {...common} pipeline={pipeline} />}
        {pipeline && <TargetsSection {...common} pipeline={pipeline} channels={props.channels} />}
        <ScheduleSection {...common} channels={props.channels} />
        <ReviewSection {...common} channels={props.channels} />
        <SaveBar
          dirty={editor.dirty}
          saving={editor.saving}
          saveLabel={props.automationId === undefined ? "Create automation" : "Save changes"}
          saveDisabled={false}
          onSave={editor.submit}
        >
          <RunNowButton automationId={props.automationId} name={draft.name} dirty={editor.dirty} />
          <ButtonLink to="/automations">Cancel</ButtonLink>
        </SaveBar>
      </div>
    </div>
  );
}
