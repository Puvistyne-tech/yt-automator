import type { Schedule } from "@/api/types";
import { withActiveHours, withDailyCap } from "@/features/automation-editor/model/schedule";
import { ToggleField } from "@/features/automation-editor/sections/ToggleField";
import { FormField, Input, NumberInput } from "@/shared/ui";

export interface ScheduleFieldsProps {
  schedule: Schedule;
  errors: Record<string, string>;
  onChange: (schedule: Schedule) => void;
}

function TimeInput({ value, onValue }: { value: string | null; onValue: (value: string) => void }) {
  return (
    <Input
      type="time"
      className="mono"
      value={value ?? ""}
      onChange={(event) => onValue(event.target.value)}
    />
  );
}

function ActiveHours({ schedule, errors, onChange }: ScheduleFieldsProps) {
  return (
    <ToggleField
      label="Only start during active hours"
      hint={`Scheduled runs start only between these times in ${schedule.timezone}; a start outside them waits for the next opening. An end before the start crosses midnight.`}
      checked={schedule.active_from !== null || schedule.active_until !== null}
      onChange={(on) => onChange(withActiveHours(schedule, on))}
    >
      <div className="grid-2">
        <FormField label="From" required error={errors["schedule.active_from"]}>
          <TimeInput
            value={schedule.active_from}
            onValue={(active_from) => onChange({ ...schedule, active_from })}
          />
        </FormField>
        <FormField label="Until" required error={errors["schedule.active_until"]}>
          <TimeInput
            value={schedule.active_until}
            onValue={(active_until) => onChange({ ...schedule, active_until })}
          />
        </FormField>
      </div>
    </ToggleField>
  );
}

function DailyCap({ schedule, errors, onChange }: ScheduleFieldsProps) {
  return (
    <ToggleField
      label="Limit runs per day"
      hint="Once this many runs started on a day (Run now included), scheduled starts wait for the next day. Run now always works."
      checked={schedule.max_runs_per_day !== null}
      onChange={(on) => onChange(withDailyCap(schedule, on))}
    >
      <FormField label="At most (runs a day)" required error={errors["schedule.max_runs_per_day"]}>
        <NumberInput
          min={1}
          step={1}
          value={schedule.max_runs_per_day}
          onValueChange={(max_runs_per_day) => onChange({ ...schedule, max_runs_per_day })}
        />
      </FormField>
    </ToggleField>
  );
}

export function ScheduleLimits(props: ScheduleFieldsProps) {
  const { schedule, onChange } = props;
  return (
    <fieldset className="option-group">
      <legend className="option-group-title">Limits</legend>
      <ActiveHours {...props} />
      <DailyCap {...props} />
      <ToggleField
        label="Skip a start while the last run is unfinished"
        hint="Recommended: overlapping runs of one automation compete for the Mac's GPU. A skipped start is noted in the unfinished run's log."
        checked={schedule.skip_if_unfinished}
        onChange={(skip_if_unfinished) => onChange({ ...schedule, skip_if_unfinished })}
      />
    </fieldset>
  );
}
