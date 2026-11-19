import { useMemo, useRef, useState } from "react";
import { useStoredChoice } from "@/shared/hooks/useStoredChoice";
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
import {
  basicVisibility,
  readSettingsView,
  SETTINGS_VIEW_STORAGE_KEY,
  type SettingsView,
  simpleViewSummary,
  withErrorPaths,
} from "@/shared/settings-view/settingsView";

export function useSettingsViewMode(startIn?: SettingsView) {
  const [remembered, remember] = useStoredChoice(SETTINGS_VIEW_STORAGE_KEY, readSettingsView);
  const [opening, setOpening] = useState(startIn);
  const view = opening ?? remembered;
  const current = useRef(view);
  current.current = view;
  const setView = (next: SettingsView) => {
    setOpening(undefined);
    remember(next);
  };
  const revealIf = (hidden: boolean) => {
    if (current.current === "simple" && hidden) {
      setView("all");
    }
  };
  return { view, setView, revealIf };
}

export type SettingsViewMode = ReturnType<typeof useSettingsViewMode>;

function useSettingsSearch() {
  const [query, setQuery] = useState("");
  const [changedOnly, setChangedOnly] = useState(false);
  const clear = () => {
    setQuery("");
    setChangedOnly(false);
  };
  return { query, setQuery, changedOnly, setChangedOnly, clear };
}

export type SettingsSearchState = ReturnType<typeof useSettingsSearch>;

function useSchemaFields(schema: Record<string, unknown> | undefined, uiSchema: unknown) {
  return useMemo(() => {
    const all = schemaFields(schema ?? {});
    const concealed = concealedBy(all, readHiddenPaths(uiSchema));
    const basic = basicVisibility(uiSchema);
    return { all, concealed, basic, fields: revealedFields(all, concealed) };
  }, [schema, uiSchema]);
}

export interface SchemaViewInput {
  view: SettingsView;
  schema: Record<string, unknown> | undefined;
  uiSchema: unknown;
  changed: readonly string[];
  errorPaths: readonly string[];
  hiddenRules: number;
}

export function useSchemaView(input: SchemaViewInput) {
  const search = useSettingsSearch();
  const { all, concealed, basic, fields } = useSchemaFields(input.schema, input.uiSchema);
  const changed = revealedPaths(input.changed, concealed);
  const searched = settingsFilter(fields, { ...search, changed });
  const chosen = input.view === "simple" ? basic : searched;
  const rule = withErrorPaths(withoutConcealed(chosen, concealed), input.errorPaths);
  const visible = rule === undefined ? undefined : visiblePathSet(all, rule);
  const nothingFound = input.view === "all" && visible?.size === 0 && input.errorPaths.length === 0;
  const summary = simpleViewSummary(fields, basic, changed, input.hiddenRules);
  return { visible, filtered: chosen !== undefined, concealed, nothingFound, summary, search };
}

export type SchemaViewState = ReturnType<typeof useSchemaView>;
