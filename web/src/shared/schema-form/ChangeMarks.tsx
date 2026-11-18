import type { Registry } from "@rjsf/utils";
import {
  changedIn,
  fieldChanged,
  fieldDefault,
  resetPath,
  resetSection,
  trackingOf,
} from "@/shared/schema-form/changeTracking";
import { defaultPreview, type FieldPath, tracksChanges } from "@/shared/schema-form/defaults";
import { Button } from "@/shared/ui/Button";

const FOCUSABLE = "input:not([disabled]), select, textarea, button:not([disabled])";

function focusField(fieldId: string) {
  const field = document.getElementById(fieldId);
  const target = field?.matches(FOCUSABLE) ? field : field?.querySelector<HTMLElement>(FOCUSABLE);
  target?.focus();
}

interface FieldChangeProps {
  registry: Registry;
  path: FieldPath;
  label: string;
  fieldId: string;
}

export function FieldChange({ registry, path, label, fieldId }: FieldChangeProps) {
  const tracking = trackingOf(registry);
  if (tracking === null || !tracksChanges(path)) {
    return null;
  }
  if (!fieldChanged(tracking, path)) {
    return <span className="field-change" />;
  }
  const reset = () => {
    resetPath(tracking, path);
    focusField(fieldId);
  };
  return (
    <span className="field-change">
      <span className="field-changed-dot" role="img" aria-label="Changed from default" />
      <button
        type="button"
        className="field-reset"
        aria-label={`Reset ${label} to default`}
        title={`Default: ${defaultPreview(fieldDefault(tracking, path))}`}
        disabled={tracking.locked}
        onClick={reset}
      >
        Reset
      </button>
    </span>
  );
}

interface SectionChangesProps {
  registry: Registry;
  title: string;
  names: string[];
  headingId: string;
}

export function SectionChanges({ registry, title, names, headingId }: SectionChangesProps) {
  const tracking = trackingOf(registry);
  const count = tracking === null ? 0 : changedIn(tracking, names);
  if (tracking === null || count === 0) {
    return null;
  }
  const reset = () => {
    resetSection(tracking, names);
    document.getElementById(headingId)?.focus();
  };
  return (
    <div className="schema-section-changes">
      <span className="schema-section-count">{count} changed</span>
      <Button
        size="sm"
        variant="ghost"
        aria-label={`Reset ${title} section to defaults`}
        disabled={tracking.locked}
        onClick={reset}
      >
        Reset section to defaults
      </Button>
    </div>
  );
}
