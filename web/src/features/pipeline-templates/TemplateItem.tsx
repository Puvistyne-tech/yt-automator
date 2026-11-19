import { Link } from "react-router";
import { newAutomationPath, pipelinePath } from "@/api/paths";
import type { TemplateSummary } from "@/api/types";
import {
  canStartAutomation,
  openLabel,
  templateBadges,
  usageLabel,
} from "@/features/pipeline-templates/model/listing";
import { Badge, ButtonLink, IconButton } from "@/shared/ui";

export interface TemplateItemActions {
  duplicate: (template: TemplateSummary) => void;
  remove: (template: TemplateSummary) => void;
}

function TemplateBadges({ template }: { template: TemplateSummary }) {
  return (
    <span className="badge-row">
      {templateBadges(template).map((badge) => (
        <Badge key={badge.label} tone={badge.tone}>
          {badge.label}
        </Badge>
      ))}
    </span>
  );
}

function TemplateMain({ template }: { template: TemplateSummary }) {
  return (
    <div className="template-main">
      <div className="row">
        <Link to={pipelinePath(template.id)} className="cell-title">
          {template.name}
        </Link>
        <TemplateBadges template={template} />
      </div>
      {template.description && <span className="subtle">{template.description}</span>}
      <span className="subtle">{usageLabel(template.automations_using)}</span>
    </div>
  );
}

function TemplateActions({
  template,
  actions,
}: {
  template: TemplateSummary;
  actions: TemplateItemActions;
}) {
  const name = template.name;
  const open = openLabel(template);
  return (
    <div className="template-actions">
      {canStartAutomation(template) && (
        <ButtonLink
          to={newAutomationPath(template.type_id)}
          size="sm"
          icon="plus"
          aria-label={`New automation with ${name}`}
        >
          New automation
        </ButtonLink>
      )}
      <ButtonLink
        to={pipelinePath(template.id)}
        size="sm"
        variant="ghost"
        icon="edit"
        aria-label={`${open} ${name}`}
        className="btn-icon"
      />
      <IconButton
        icon="copy"
        label={`Duplicate ${name}`}
        onClick={() => actions.duplicate(template)}
      />
      {!template.builtin && (
        <IconButton
          icon="trash"
          variant="danger"
          label={`Delete ${name}`}
          onClick={() => actions.remove(template)}
        />
      )}
    </div>
  );
}

export function TemplateItem({
  template,
  actions,
}: {
  template: TemplateSummary;
  actions: TemplateItemActions;
}) {
  return (
    <li className="template-item divided-list-item" aria-label={template.name}>
      <TemplateMain template={template} />
      <TemplateActions template={template} actions={actions} />
    </li>
  );
}
