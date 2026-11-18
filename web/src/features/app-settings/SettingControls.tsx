import type { FieldErrors } from "@/api/errors";
import type { AppSettings, AppSettingsInput } from "@/api/types";
import { SettingField } from "@/features/app-settings/SettingField";
import { Input, NumberInput, Switch } from "@/shared/ui";

type NumberName = {
  [K in keyof AppSettingsInput]: AppSettingsInput[K] extends number ? K : never;
}[keyof AppSettingsInput];

export interface SettingsCardProps {
  input: AppSettingsInput;
  settings: AppSettings;
  errors: FieldErrors;
  onChange: (patch: Partial<AppSettingsInput>) => void;
}

interface NumberSettingProps extends SettingsCardProps {
  name: NumberName;
  min: number;
  step?: number;
}

export function NumberSetting({ name, min, step = 1, ...card }: NumberSettingProps) {
  return (
    <SettingField name={name} settings={card.settings} errors={card.errors}>
      {(locked) => (
        <NumberInput
          min={min}
          step={step}
          disabled={locked}
          value={card.input[name]}
          onValueChange={(value) => card.onChange({ [name]: value })}
        />
      )}
    </SettingField>
  );
}

export function AutoCleanupSetting(card: SettingsCardProps) {
  return (
    <SettingField name="auto_cleanup_enabled" settings={card.settings} errors={card.errors}>
      {(locked) => (
        <Switch
          checked={card.input.auto_cleanup_enabled}
          disabled={locked}
          onChange={(checked) => card.onChange({ auto_cleanup_enabled: checked })}
        />
      )}
    </SettingField>
  );
}

export function CaptionNameSetting(card: SettingsCardProps) {
  return (
    <SettingField name="caption_track_name" settings={card.settings} errors={card.errors}>
      {(locked) => (
        <Input
          value={card.input.caption_track_name}
          disabled={locked}
          placeholder="No name"
          onChange={(event) => card.onChange({ caption_track_name: event.target.value })}
        />
      )}
    </SettingField>
  );
}
