import { useMemo } from "react";
import {
  CaptionNameSetting,
  NumberSetting,
  type SettingsCardProps,
} from "@/features/app-settings/SettingControls";
import { SettingField } from "@/features/app-settings/SettingField";
import { timezoneSelectOptions } from "@/shared/format/schedule";
import { Card, Select } from "@/shared/ui";

export function GeneralSettingsCard(card: SettingsCardProps) {
  const { input, settings, errors, onChange } = card;
  const zones = useMemo(() => timezoneSelectOptions(input.timezone), [input.timezone]);
  return (
    <Card title="General" description="Applies to every automation and run.">
      <div className="stack">
        <SettingField name="timezone" settings={settings} errors={errors}>
          {(locked) => (
            <Select
              value={input.timezone}
              options={zones}
              disabled={locked}
              onChange={(e) => onChange({ timezone: e.target.value })}
            />
          )}
        </SettingField>
        <div className="grid-2">
          <NumberSetting {...card} name="max_parallel_runs" min={1} />
          <CaptionNameSetting {...card} />
        </div>
      </div>
    </Card>
  );
}
