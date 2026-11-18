import type { SettingsSearch as SearchState } from "@/features/automation-editor/useSettingsView";
import { Input, Switch } from "@/shared/ui";
import "@/features/automation-editor/settings-view.css";

export function SettingsSearch({ search }: { search: SearchState }) {
  return (
    <search className="settings-search">
      <Input
        type="search"
        aria-label="Search settings"
        placeholder="Search settings by name or help text"
        value={search.query}
        onChange={(event) => search.setQuery(event.target.value)}
      />
      <Switch checked={search.changedOnly} onChange={search.setChangedOnly} label="Changed only" />
    </search>
  );
}
