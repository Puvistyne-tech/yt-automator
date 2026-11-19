import type { FieldErrors } from "@/api/errors";
import type { EngineSummary } from "@/api/types";
import {
  basicVisibility,
  hidesScopedError,
  type SettingsView,
  scopedErrorPaths,
} from "@/shared/settings-view/settingsView";
import { useSchemaView, useSettingsViewMode } from "@/shared/settings-view/useSettingsView";

export const DEFINITION_SCOPE = "definition";
const NOTHING_CHANGED: readonly string[] = [];

export function useDefinitionViewMode(engine: EngineSummary, startIn?: SettingsView) {
  const mode = useSettingsViewMode(startIn);
  const revealErrors = (errors: FieldErrors) => {
    const basic = basicVisibility(engine.definition_ui_schema);
    mode.revealIf(hidesScopedError(errors, DEFINITION_SCOPE, basic));
  };
  return { view: mode.view, setView: mode.setView, revealErrors };
}

export function useDefinitionFilter(
  engine: EngineSummary,
  view: SettingsView,
  errors: FieldErrors,
) {
  return useSchemaView({
    view,
    schema: engine.definition_schema,
    uiSchema: engine.definition_ui_schema,
    changed: NOTHING_CHANGED,
    errorPaths: scopedErrorPaths(errors, DEFINITION_SCOPE),
    hiddenRules: 0,
  });
}

export type DefinitionViewMode = ReturnType<typeof useDefinitionViewMode>;
export type DefinitionFilter = ReturnType<typeof useDefinitionFilter>;
