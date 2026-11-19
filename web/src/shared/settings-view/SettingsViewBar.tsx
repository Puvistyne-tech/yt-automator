import {
  hiddenOptionsText,
  SETTINGS_VIEWS,
  type SettingsView,
  type SimpleViewSummary,
} from "@/shared/settings-view/settingsView";
import { Button } from "@/shared/ui";
import "@/shared/settings-view/settings-view.css";

interface SettingsViewBarProps {
  view: SettingsView;
  summary: SimpleViewSummary;
  onView: (view: SettingsView) => void;
}

export function SettingsViewBar({ view, summary, onView }: SettingsViewBarProps) {
  return (
    <div className="settings-view-bar">
      <fieldset className="view-toggle" aria-label="Settings view">
        {SETTINGS_VIEWS.map((option) => (
          <button
            key={option.id}
            type="button"
            className="view-toggle-option"
            aria-pressed={view === option.id}
            onClick={() => onView(option.id)}
          >
            {option.label}
          </button>
        ))}
      </fieldset>
      {view === "simple" && (
        <p className="settings-view-hint muted">
          <span>{hiddenOptionsText(summary)}</span>
          <Button size="sm" variant="ghost" onClick={() => onView("all")}>
            Show all settings
          </Button>
        </p>
      )}
    </div>
  );
}
