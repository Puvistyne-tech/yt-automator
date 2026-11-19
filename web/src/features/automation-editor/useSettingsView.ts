import { useMemo, useRef, useState } from "react";
import type { FieldErrors } from "@/api/errors";
import type { PipelineDescriptor } from "@/api/types";
import type { AutomationDraft } from "@/features/automation-editor/model/draft";
import {
  applicableAdvancedFields,
  basicVisibility,
  readSettingsView,
  revealsHiddenError,
  SETTINGS_VIEW_STORAGE_KEY,
  type SettingsView,
  settingsErrorPaths,
  simpleViewSummary,
  withErrorPaths,
} from "@/features/automation-editor/model/settingsView";
import { useStoredChoice } from "@/shared/hooks/useStoredChoice";
import { changedPaths } from "@/shared/schema-form/defaults";
import {
  concealedBy,
  readHiddenPaths,
  revealedFields,
  revealedPaths,
  settingsFilter,
  visiblePathSet,
  withoutConcealed,
} from "@/shared/schema-form/fieldFilter";
import { schemaFields } from "@/shared/schema-form/schemaFields";

export function useSettingsViewMode() {
  const [view, setView] = useStoredChoice(SETTINGS_VIEW_STORAGE_KEY, readSettingsView);
  const current = useRef(view);
  current.current = view;
  const revealErrors = (errors: FieldErrors, pipeline: PipelineDescriptor | undefined) => {
    const hidden = revealsHiddenError(errors, basicVisibility(pipeline?.ui_schema));
    if (current.current === "simple" && hidden) {
      setView("all");
    }
  };
  return { view, setView, revealErrors };
}

function useChangedPaths(pipeline: PipelineDescriptor | undefined, settings: object): string[] {
  return useMemo(() => {
    const defaults = pipeline?.default_settings ?? {};
    return changedPaths(settings, defaults, Object.keys(defaults));
  }, [pipeline, settings]);
}

function usePipelineFields(pipeline: PipelineDescriptor | undefined) {
  return useMemo(() => {
    const all = schemaFields(pipeline?.settings_schema ?? {});
    const concealed = concealedBy(all, readHiddenPaths(pipeline?.ui_schema));
    return { all, concealed, fields: revealedFields(all, concealed) };
  }, [pipeline]);
}

function useSettingsSearch() {
  const [query, setQuery] = useState("");
  const [changedOnly, setChangedOnly] = useState(false);
  const clear = () => {
    setQuery("");
    setChangedOnly(false);
  };
  return { query, setQuery, changedOnly, setChangedOnly, clear };
}

export function useSettingsFilter(
  view: SettingsView,
  pipeline: PipelineDescriptor | undefined,
  draft: AutomationDraft,
  errors: FieldErrors,
) {
  const search = useSettingsSearch();
  const { all, concealed, fields } = usePipelineFields(pipeline);
  const basic = useMemo(() => basicVisibility(pipeline?.ui_schema), [pipeline]);
  const changed = revealedPaths(useChangedPaths(pipeline, draft.settings), concealed);
  const errorPaths = settingsErrorPaths(errors);
  const searched = settingsFilter(fields, { ...search, changed });
  const shown = withoutConcealed(view === "simple" ? basic : searched, concealed);
  const rule = withErrorPaths(shown, errorPaths);
  const visible = rule === undefined ? undefined : visiblePathSet(all, rule);
  const nothingFound = view === "all" && visible?.size === 0 && errorPaths.length === 0;
  const hiddenRules = applicableAdvancedFields(draft).length;
  const summary = simpleViewSummary(fields, basic, changed, hiddenRules);
  return { visible, nothingFound, summary, search };
}

export type SettingsFilterState = ReturnType<typeof useSettingsFilter>;
export type SettingsSearch = SettingsFilterState["search"];
