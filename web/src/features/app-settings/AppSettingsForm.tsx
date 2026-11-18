import { useMemo, useState } from "react";
import { errorMessage, type FieldErrors, fieldErrorsOf, normalizeFieldErrors } from "@/api/errors";
import { useAppSettings, useSaveAppSettings } from "@/api/system";
import type { AppSettings, AppSettingsInput } from "@/api/types";
import { settingsInput, validateSettings } from "@/features/app-settings/validate";
import { timezoneOptions } from "@/shared/format/schedule";
import {
  Button,
  Card,
  FormField,
  Input,
  QueryState,
  Select,
  UnsavedChangesPrompt,
  useToast,
} from "@/shared/ui";

function numberOrNaN(value: number): number | string {
  return Number.isNaN(value) ? "" : value;
}

function SettingsEditor({ settings }: { settings: AppSettings }) {
  const [input, setInput] = useState<AppSettingsInput>(() => settingsInput(settings));
  const [errors, setErrors] = useState<FieldErrors>({});
  const save = useSaveAppSettings();
  const toast = useToast();
  const zones = useMemo(
    () => timezoneOptions(input.timezone).map((z) => ({ value: z, label: z })),
    [input.timezone],
  );
  const dirty = JSON.stringify(input) !== JSON.stringify(settingsInput(settings));
  const set = (patch: Partial<AppSettingsInput>) =>
    setInput((current) => ({ ...current, ...patch }));
  const submit = () => {
    const problems = validateSettings(input);
    setErrors(problems);
    if (Object.keys(problems).length > 0) {
      return;
    }
    save.mutateAsync(input).then(
      () => toast.success("Settings saved."),
      (error: unknown) => {
        setErrors(normalizeFieldErrors(fieldErrorsOf(error)));
        toast.error(errorMessage(error));
      },
    );
  };
  return (
    <div className="stack settings-form">
      <Card title="General" description="Applies to every automation and run.">
        <div className="stack">
          <FormField
            label="Timezone"
            hint="Used for dates in the app and as the default for new schedules."
            error={errors.timezone}
          >
            <Select
              value={input.timezone}
              options={zones}
              onChange={(e) => set({ timezone: e.target.value })}
            />
          </FormField>
          <div className="grid-2">
            <FormField
              label="Parallel runs"
              hint="How many runs may render at the same time."
              error={errors.max_parallel_runs}
            >
              <Input
                type="number"
                min={1}
                step={1}
                value={numberOrNaN(input.max_parallel_runs)}
                onChange={(e) => set({ max_parallel_runs: e.target.valueAsNumber })}
              />
            </FormField>
            <FormField
              label="Keep runs for (days)"
              hint="Older runs and their files are deleted."
              error={errors.keep_runs_days}
            >
              <Input
                type="number"
                min={1}
                step={1}
                value={numberOrNaN(input.keep_runs_days)}
                onChange={(e) => set({ keep_runs_days: e.target.valueAsNumber })}
              />
            </FormField>
          </div>
          <FormField label="Data folder" hint="Set when the app starts. Read only.">
            <Input className="mono" value={settings.data_dir} readOnly />
          </FormField>
        </div>
      </Card>
      <div className="action-bar">
        <span className="action-bar-status">{dirty ? "Unsaved changes" : "All changes saved"}</span>
        <Button disabled={!dirty} onClick={() => setInput(settingsInput(settings))}>
          Reset
        </Button>
        <Button
          variant="primary"
          icon="check"
          disabled={!dirty}
          loading={save.isPending}
          onClick={submit}
        >
          Save settings
        </Button>
      </div>
      <UnsavedChangesPrompt when={dirty && !save.isPending} />
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
