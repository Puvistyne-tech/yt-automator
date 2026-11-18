import type { ReactNode } from "react";
import type { AutomationDraft } from "@/features/automation-editor/model/draft";
import { type EditorSectionId, sectionAnchor } from "@/features/automation-editor/model/sections";
import { Card } from "@/shared/ui";

interface EditorSectionProps {
  id: EditorSectionId;
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function EditorSection({ id, title, description, actions, children }: EditorSectionProps) {
  return (
    <Card
      id={sectionAnchor(id)}
      className="editor-section"
      title={title}
      description={description}
      actions={actions}
      aria-label={title}
    >
      {children}
    </Card>
  );
}

export interface SectionProps {
  draft: AutomationDraft;
  onChange: (draft: AutomationDraft) => void;
  errors: Record<string, string>;
}
