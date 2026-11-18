import { useAppSettings, useSaveAppSettings } from "@/api/system";
import type { AppSettings } from "@/api/types";
import { useFieldErrors } from "@/api/useFieldErrors";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { GeneralSettingsCard } from "@/features/app-settings/GeneralSettingsCard";
import { settingsChanged, settingsInput, validateSettings } from "@/features/app-settings/validate";
import { usePatchState } from "@/shared/hooks/usePatchState";
import { QueryState, SaveBar } from "@/shared/ui";

function SettingsEditor({ settings }: { settings: AppSettings }) {
  const [input, patch, setInput] = usePatchState(() => settingsInput(settings));
  const fields = useFieldErrors();
  const save = useSaveAppSettings();
  const notifier = useMutationNotifier();
  const dirty = settingsChanged(input, settings);
  const submit = () => {
    if (fields.validate(validateSettings(input))) {
      void notifier.track(save.mutateAsync(input), {
        success: "Settings saved.",
        onError: fields.setFromServer,
      });
    }
  };
  return (
    <div className="stack settings-form">
      <GeneralSettingsCard
        input={input}
        dataDir={settings.data_dir}
        errors={fields.errors}
        onChange={patch}
      />
      <SaveBar
        dirty={dirty}
        saving={save.isPending}
        saveLabel="Save settings"
        saveDisabled={!dirty}
        onSave={submit}
        onReset={() => setInput(settingsInput(settings))}
      />
    </div>
  );
}

export function AppSettingsForm() {
  const settings = useAppSettings();
  return (
    <QueryState query={settings} loadingLabel="Loading settings">
      {(data) => <SettingsEditor key={JSON.stringify(data)} settings={data} />}
    </QueryState>
  );
}
