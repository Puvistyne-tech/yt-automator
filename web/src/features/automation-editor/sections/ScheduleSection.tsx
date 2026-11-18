import { useMemo } from "react";
import type { Schedule } from "@/api/types";
import { withEveryHours, withScheduleKind } from "@/features/automation-editor/model/draft";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { describeSchedule, timezoneSelectOptions } from "@/shared/format/schedule";
import { FormField, Icon, Input, NumberInput, RadioCards, Select } from "@/shared/ui";

const KINDS = [
  { value: "manual" as const, label: "Manual", description: "Only when you press Run now." },
  {
    value: "interval" as const,
    label: "Every few hours",
    description: "A fixed number of hours apart.",
  },
  {
    value: "cron" as const,
    label: "Cron expression",
    description: "Full control with 5 cron fields.",
  },
];

interface ScheduleFieldsProps {
  schedule: Schedule;
  errors: Record<string, string>;
  onChange: (schedule: Schedule) => void;
}

function IntervalFields({ schedule, errors, onChange }: ScheduleFieldsProps) {
  return (
    <FormField label="Every (hours)" required error={errors["schedule.every_hours"]}>
      <NumberInput
        min={1}
        step={1}
        value={schedule.every_hours}
        onValueChange={(hours) => onChange(withEveryHours(schedule, hours))}
      />
    </FormField>
  );
}

function CronFields({ schedule, errors, onChange }: ScheduleFieldsProps) {
  const zones = useMemo(() => timezoneSelectOptions(schedule.timezone), [schedule.timezone]);
  return (
    <div className="grid-2">
      <FormField
        label="Cron expression"
        required
        hint="minute hour day-of-month month day-of-week"
        error={errors["schedule.cron"]}
      >
        <Input
          className="mono"
          value={schedule.cron ?? ""}
          spellCheck={false}
          onChange={(e) => onChange({ ...schedule, cron: e.target.value })}
        />
      </FormField>
      <FormField label="Timezone" error={errors["schedule.timezone"]}>
        <Select
          value={schedule.timezone}
          options={zones}
          onChange={(e) => onChange({ ...schedule, timezone: e.target.value })}
        />
      </FormField>
    </div>
  );
}

export function ScheduleSection({ draft, onChange, errors }: SectionProps) {
  const schedule = draft.schedule;
  const set = (next: Schedule) => onChange({ ...draft, schedule: next });
  return (
    <EditorSection id="schedule" title="Schedule" description="When new runs start on their own.">
      <div className="stack">
        <RadioCards
          label="Run"
          hideLabel
          options={KINDS}
          value={schedule.kind}
          onChange={(kind) => set(withScheduleKind(schedule, kind))}
        />
        {schedule.kind === "interval" && (
          <IntervalFields schedule={schedule} errors={errors} onChange={set} />
        )}
        {schedule.kind === "cron" && (
          <CronFields schedule={schedule} errors={errors} onChange={set} />
        )}
        <p className="schedule-preview" aria-live="polite">
          <Icon name="clock" />
          <span>{describeSchedule(schedule)}</span>
        </p>
      </div>
    </EditorSection>
  );
}
