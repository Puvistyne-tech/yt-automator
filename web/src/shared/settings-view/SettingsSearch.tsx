import type { SettingsSearchState } from "@/shared/settings-view/useSettingsView";
import { Input, Switch } from "@/shared/ui";
import "@/shared/settings-view/settings-view.css";

interface SettingsSearchProps {
  search: SettingsSearchState;
  offerChangedOnly?: boolean;
}

export function SettingsSearch({ search, offerChangedOnly = true }: SettingsSearchProps) {
  return (
    <search className="settings-search">
      <Input
        type="search"
        aria-label="Search settings"
        placeholder="Search settings by name or help text"
        value={search.query}
        onChange={(event) => search.setQuery(event.target.value)}
      />
      {offerChangedOnly && (
        <Switch
          checked={search.changedOnly}
          onChange={search.setChangedOnly}
          label="Changed only"
        />
      )}
    </search>
  );
}
