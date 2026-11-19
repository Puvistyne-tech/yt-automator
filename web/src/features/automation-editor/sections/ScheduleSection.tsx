import { useMemo } from "react";
import type { Channel, Schedule } from "@/api/types";
import { withEveryHours, withScheduleKind } from "@/features/automation-editor/model/schedule";
import type { PlatformShows } from "@/features/automation-editor/model/settingsView";
import { automationSummary } from "@/features/automation-editor/model/summary";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { RetryFields } from "@/features/automation-editor/sections/RetryFields";
import { RulesSummary } from "@/features/automation-editor/sections/RulesSummary";
import {
  type ScheduleFieldsProps,
  ScheduleLimits,
} from "@/features/automation-editor/sections/ScheduleLimits";
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

function CadenceField({ schedule, errors, onChange }: ScheduleFieldsProps) {
  if (schedule.kind === "interval") {
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
  return (
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
  );
}

function TimezoneField({ schedule, errors, onChange }: ScheduleFieldsProps) {
  const zones = useMemo(() => timezoneSelectOptions(schedule.timezone), [schedule.timezone]);
  return (
    <FormField
      label="Timezone"
      hint="Used for cron times, active hours and the daily cap."
      error={errors["schedule.timezone"]}
    >
      <Select
        value={schedule.timezone}
        options={zones}
        onChange={(e) => onChange({ ...schedule, timezone: e.target.value })}
      />
    </FormField>
  );
}

function TimingFields(props: ScheduleFieldsProps & { shows: PlatformShows }) {
  return (
    <div className="grid-2">
      <CadenceField {...props} />
      {props.shows("timezone") && <TimezoneField {...props} />}
    </div>
  );
}

export function ScheduleSection({
  draft,
  onChange,
  errors,
  channels,
  shows,
}: SectionProps & { channels: Channel[] }) {
  const schedule = draft.schedule;
  const set = (next: Schedule) => onChange({ ...draft, schedule: next });
  const fields = { schedule, errors, onChange: set };
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
        {schedule.kind !== "manual" && <TimingFields {...fields} shows={shows} />}
        <p className="schedule-preview" aria-live="polite">
          <Icon name="clock" />
          <span>{describeSchedule(schedule)}</span>
        </p>
        {schedule.kind !== "manual" && shows("schedule_limits") && <ScheduleLimits {...fields} />}
        {shows("retry_policy") && (
          <RetryFields
            policy={draft.retry_policy}
            errors={errors}
            onChange={(retry_policy) => onChange({ ...draft, retry_policy })}
          />
        )}
        <RulesSummary text={automationSummary(draft, channels)} />
      </div>
    </EditorSection>
  );
}
