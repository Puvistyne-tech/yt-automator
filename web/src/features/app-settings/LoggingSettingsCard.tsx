import type { ServerLogLevel } from "@/api/types";
import { LOG_LEVEL_OPTIONS } from "@/features/app-settings/fieldText";
import { NumberSetting, type SettingsCardProps } from "@/features/app-settings/SettingControls";
import { SettingField } from "@/features/app-settings/SettingField";
import { Card, FormField, Input, Select } from "@/shared/ui";

export function LoggingSettingsCard(card: SettingsCardProps) {
  const { input, settings, errors, onChange } = card;
  return (
    <Card title="Logging and diagnostics" description="Run logs, the server log and health checks.">
      <div className="stack">
        <div className="grid-3">
          <NumberSetting {...card} name="max_run_log_entries" min={1} />
          <SettingField name="log_level" settings={settings} errors={errors}>
            {(locked) => (
              <Select
                value={input.log_level}
                options={LOG_LEVEL_OPTIONS}
                disabled={locked}
                onChange={(e) => onChange({ log_level: e.target.value as ServerLogLevel })}
              />
            )}
          </SettingField>
          <NumberSetting {...card} name="doctor_min_free_gb" min={0} step={0.5} />
        </div>
        <FormField label="Data folder" hint="Set when the app starts. Read only.">
          <Input className="mono" value={settings.data_dir} readOnly />
        </FormField>
      </div>
    </Card>
  );
}
