import { useMemo } from "react";
import type { FieldErrors } from "@/api/errors";
import type { PipelineDescriptor } from "@/api/types";
import type { AutomationDraft } from "@/features/automation-editor/model/draft";
import {
  applicableAdvancedFields,
  revealsHiddenError,
  settingsErrorPaths,
} from "@/features/automation-editor/model/settingsView";
import { changedPaths } from "@/shared/schema-form/defaults";
import { basicVisibility, type SettingsView } from "@/shared/settings-view/settingsView";
import {
  useSchemaView,
  useSettingsViewMode as useViewMode,
} from "@/shared/settings-view/useSettingsView";

export function useSettingsViewMode() {
  const mode = useViewMode();
  const revealErrors = (errors: FieldErrors, pipeline: PipelineDescriptor | undefined) =>
    mode.revealIf(revealsHiddenError(errors, basicVisibility(pipeline?.ui_schema)));
  return { view: mode.view, setView: mode.setView, revealErrors };
}

function useChangedPaths(pipeline: PipelineDescriptor | undefined, settings: object): string[] {
  return useMemo(() => {
    const defaults = pipeline?.default_settings ?? {};
    return changedPaths(settings, defaults, Object.keys(defaults));
  }, [pipeline, settings]);
}

export function useSettingsFilter(
  view: SettingsView,
  pipeline: PipelineDescriptor | undefined,
  draft: AutomationDraft,
  errors: FieldErrors,
) {
  return useSchemaView({
    view,
    schema: pipeline?.settings_schema,
    uiSchema: pipeline?.ui_schema,
    changed: useChangedPaths(pipeline, draft.settings),
    errorPaths: settingsErrorPaths(errors),
    hiddenRules: applicableAdvancedFields(draft).length,
  });
}

export type SettingsFilterState = ReturnType<typeof useSettingsFilter>;
