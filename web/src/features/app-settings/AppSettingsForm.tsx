import type { ReactNode } from "react";
import { useAppSettings, useSaveAppSettings } from "@/api/system";
import type { AppSettings } from "@/api/types";
import { useFieldErrors } from "@/api/useFieldErrors";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { GeneralSettingsCard } from "@/features/app-settings/GeneralSettingsCard";
import { LoggingSettingsCard } from "@/features/app-settings/LoggingSettingsCard";
import { StorageSettingsCard } from "@/features/app-settings/StorageSettingsCard";
import { settingsChanged, settingsInput, validateSettings } from "@/features/app-settings/validate";
import { usePatchState } from "@/shared/hooks/usePatchState";
import { QueryState, SaveBar } from "@/shared/ui";
import "@/features/app-settings/settings.css";

interface AppSettingsFormProps {
  storageUsage?: ReactNode;
}

function SettingsEditor({
  settings,
  storageUsage,
}: AppSettingsFormProps & { settings: AppSettings }) {
  const [input, patch, setInput] = usePatchState(() => settingsInput(settings));
  const fields = useFieldErrors();
  const save = useSaveAppSettings();
  const notifier = useMutationNotifier();
  const submit = () => {
    if (fields.validate(validateSettings(input, settings.locked))) {
      void notifier.track(save.mutateAsync(input), {
        success: "Settings saved.",
        onError: fields.setFromServer,
      });
    }
  };
  const card = { input, settings, errors: fields.errors, onChange: patch };
  return (
    <div className="stack settings-form">
      <GeneralSettingsCard {...card} />
      <StorageSettingsCard {...card} usage={storageUsage} />
      <LoggingSettingsCard {...card} />
      <SaveBar
        dirty={settingsChanged(input, settings)}
        saving={save.isPending}
        saveLabel="Save settings"
        onSave={submit}
        onReset={() => setInput(settingsInput(settings))}
      />
    </div>
  );
}

export function AppSettingsForm({ storageUsage }: AppSettingsFormProps) {
  const settings = useAppSettings();
  return (
    <QueryState query={settings} loadingLabel="Loading settings">
      {(data) => (
        <SettingsEditor key={JSON.stringify(data)} settings={data} storageUsage={storageUsage} />
      )}
    </QueryState>
  );
}
