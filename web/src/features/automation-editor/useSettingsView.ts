import { useMemo, useState } from "react";
import type { FieldErrors } from "@/api/errors";
import type { PipelineDescriptor } from "@/api/types";
import {
  basicVisibility,
  readSettingsView,
  revealsHiddenError,
  SETTINGS_VIEW_STORAGE_KEY,
  type SettingsView,
  simpleViewSummary,
} from "@/features/automation-editor/model/settingsView";
import { useStoredChoice } from "@/shared/hooks/useStoredChoice";
import { changedPaths } from "@/shared/schema-form/defaults";
import { settingsFilter, visiblePathSet } from "@/shared/schema-form/fieldFilter";
import { schemaFields } from "@/shared/schema-form/schemaFields";

export function useSettingsViewMode() {
  const [view, setView] = useStoredChoice(SETTINGS_VIEW_STORAGE_KEY, readSettingsView);
  const revealErrors = (errors: FieldErrors, pipeline: PipelineDescriptor | undefined) => {
    if (view === "simple" && revealsHiddenError(errors, basicVisibility(pipeline?.ui_schema))) {
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
  settings: object,
) {
  const search = useSettingsSearch();
  const { query, changedOnly } = search;
  const fields = useMemo(() => schemaFields(pipeline?.settings_schema ?? {}), [pipeline]);
  const basic = useMemo(() => basicVisibility(pipeline?.ui_schema), [pipeline]);
  const changed = useChangedPaths(pipeline, settings);
  const visible = useMemo(() => {
    const rule =
      view === "simple" ? basic : settingsFilter(fields, { query, changedOnly, changed });
    return rule === undefined ? undefined : visiblePathSet(fields, rule);
  }, [view, basic, fields, query, changedOnly, changed]);
  const nothingFound = view === "all" && visible !== undefined && visible.size === 0;
  return { visible, nothingFound, summary: simpleViewSummary(fields, basic, changed), search };
}

export type SettingsFilterState = ReturnType<typeof useSettingsFilter>;
export type SettingsSearch = SettingsFilterState["search"];
