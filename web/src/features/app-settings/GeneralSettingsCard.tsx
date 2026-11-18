import { useMemo } from "react";
import type { FieldErrors } from "@/api/errors";
import type { AppSettingsInput } from "@/api/types";
import { timezoneSelectOptions } from "@/shared/format/schedule";
import { Card, FormField, Input, NumberInput, Select } from "@/shared/ui";

interface GeneralSettingsCardProps {
  input: AppSettingsInput;
  dataDir: string;
  errors: FieldErrors;
  onChange: (patch: Partial<AppSettingsInput>) => void;
}

function LimitFields({ input, errors, onChange }: Omit<GeneralSettingsCardProps, "dataDir">) {
  return (
    <div className="grid-2">
      <FormField
        label="Parallel runs"
        hint="How many runs may render at the same time."
        error={errors.max_parallel_runs}
      >
        <NumberInput
          min={1}
          step={1}
          value={input.max_parallel_runs}
          onValueChange={(max_parallel_runs) => onChange({ max_parallel_runs })}
        />
      </FormField>
      <FormField
        label="Keep runs for (days)"
        hint="Older runs and their files are deleted."
        error={errors.keep_runs_days}
      >
        <NumberInput
          min={1}
          step={1}
          value={input.keep_runs_days}
          onValueChange={(keep_runs_days) => onChange({ keep_runs_days })}
        />
      </FormField>
    </div>
  );
}

export function GeneralSettingsCard({
  input,
  dataDir,
  errors,
  onChange,
}: GeneralSettingsCardProps) {
  const zones = useMemo(() => timezoneSelectOptions(input.timezone), [input.timezone]);
  return (
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
            onChange={(e) => onChange({ timezone: e.target.value })}
          />
        </FormField>
        <LimitFields input={input} errors={errors} onChange={onChange} />
        <FormField label="Data folder" hint="Set when the app starts. Read only.">
          <Input className="mono" value={dataDir} readOnly />
        </FormField>
      </div>
    </Card>
  );
}
