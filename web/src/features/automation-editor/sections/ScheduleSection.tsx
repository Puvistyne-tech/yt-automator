import { useMemo } from "react";
import type { Schedule, ScheduleKind } from "@/api/types";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { describeSchedule, timezoneOptions } from "@/shared/format/schedule";
import { FormField, Icon, Input, RadioCards, Select } from "@/shared/ui";

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

function withKind(schedule: Schedule, kind: ScheduleKind): Schedule {
  return {
    ...schedule,
    kind,
    every_hours: kind === "interval" ? (schedule.every_hours ?? 24) : schedule.every_hours,
    cron: kind === "cron" ? (schedule.cron ?? "0 18 * * *") : schedule.cron,
  };
}

export function ScheduleSection({ draft, onChange, errors }: SectionProps) {
  const schedule = draft.schedule;
  const set = (next: Schedule) => onChange({ ...draft, schedule: next });
  const zones = useMemo(
    () => timezoneOptions(schedule.timezone).map((z) => ({ value: z, label: z })),
    [schedule.timezone],
  );
  return (
    <EditorSection id="schedule" title="Schedule" description="When new runs start on their own.">
      <div className="stack">
        <RadioCards
          label="Run"
          hideLabel
          options={KINDS}
          value={schedule.kind}
          onChange={(kind) => set(withKind(schedule, kind))}
        />
        {schedule.kind === "interval" && (
          <FormField label="Every (hours)" required error={errors["schedule.every_hours"]}>
            <Input
              type="number"
              min={1}
              step={1}
              value={schedule.every_hours ?? ""}
              onChange={(e) =>
                set({
                  ...schedule,
                  every_hours: Number.isNaN(e.target.valueAsNumber) ? null : e.target.valueAsNumber,
                })
              }
            />
          </FormField>
        )}
        {schedule.kind === "cron" && (
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
                onChange={(e) => set({ ...schedule, cron: e.target.value })}
              />
            </FormField>
            <FormField label="Timezone" error={errors["schedule.timezone"]}>
              <Select
                value={schedule.timezone}
                options={zones}
                onChange={(e) => set({ ...schedule, timezone: e.target.value })}
              />
            </FormField>
          </div>
        )}
        <p className="schedule-preview" aria-live="polite">
          <Icon name="clock" />
          <span>{describeSchedule(schedule)}</span>
        </p>
      </div>
    </EditorSection>
  );
}
