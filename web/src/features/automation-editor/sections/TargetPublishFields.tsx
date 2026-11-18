import { useMemo } from "react";
import type { Channel } from "@/api/types";
import {
  PUBLISH_TIMING_OPTIONS,
  publishTiming,
  publishTimingFrom,
  publishTimingHint,
  withPublishTiming,
} from "@/features/automation-editor/model/publishTiming";
import type { TargetFieldProps } from "@/features/automation-editor/sections/TargetFields";
import { timezoneSelectOptions } from "@/shared/format/schedule";
import { FormField, Input, NumberInput, Select } from "@/shared/ui";

type PublishFieldProps = Omit<TargetFieldProps, "options">;

function DelayField({ target, error, onChange }: PublishFieldProps) {
  return (
    <FormField label="Go public after (minutes)" required error={error("publish_delay_minutes")}>
      <NumberInput
        min={1}
        step={1}
        value={target.publish_delay_minutes}
        onValueChange={(publish_delay_minutes) => onChange({ publish_delay_minutes })}
      />
    </FormField>
  );
}

function TimeOfDayFields({ target, error, onChange }: PublishFieldProps) {
  const zones = useMemo(
    () => timezoneSelectOptions(target.publish_timezone),
    [target.publish_timezone],
  );
  return (
    <>
      <FormField label="Go public at" required error={error("publish_time_of_day")}>
        <Input
          type="time"
          className="mono"
          value={target.publish_time_of_day ?? ""}
          onChange={(event) => onChange({ publish_time_of_day: event.target.value })}
        />
      </FormField>
      <FormField label="Publish timezone" error={error("publish_timezone")}>
        <Select
          value={target.publish_timezone}
          options={zones}
          onChange={(event) => onChange({ publish_timezone: event.target.value })}
        />
      </FormField>
    </>
  );
}

export function PublishTimingFields(props: PublishFieldProps & { channel: Channel | undefined }) {
  const { target, onChange, channel } = props;
  const timing = publishTiming(target);
  return (
    <>
      <FormField label="Publish time" hint={publishTimingHint(target, channel)}>
        <Select
          value={timing}
          options={PUBLISH_TIMING_OPTIONS}
          onChange={(event) => onChange(withPublishTiming(publishTimingFrom(event.target.value)))}
        />
      </FormField>
      {timing === "delay" && <DelayField {...props} />}
      {timing === "time" && <TimeOfDayFields {...props} />}
    </>
  );
}
