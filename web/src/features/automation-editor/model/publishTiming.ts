import type { Channel } from "@/api/types";
import type { TargetDraft } from "@/features/automation-editor/model/draft";

export type PublishTiming = "upload" | "delay" | "time";

export const DEFAULT_PUBLISH_DELAY_MINUTES = 60;
export const DEFAULT_PUBLISH_TIME = "18:00";

export const PUBLISH_TIMING_OPTIONS: { value: PublishTiming; label: string }[] = [
  { value: "upload", label: "As soon as it uploads" },
  { value: "delay", label: "After a delay" },
  { value: "time", label: "At a time of day" },
];

export function publishTimingFrom(value: string): PublishTiming {
  return PUBLISH_TIMING_OPTIONS.find((option) => option.value === value)?.value ?? "upload";
}

type TimingFields = Pick<TargetDraft, "publish_delay_minutes" | "publish_time_of_day">;

export function publishTiming(target: TimingFields): PublishTiming {
  if (target.publish_time_of_day !== null) {
    return "time";
  }
  return target.publish_delay_minutes > 0 ? "delay" : "upload";
}

export function withPublishTiming(timing: PublishTiming): TimingFields {
  switch (timing) {
    case "upload":
      return { publish_delay_minutes: 0, publish_time_of_day: null };
    case "delay":
      return { publish_delay_minutes: DEFAULT_PUBLISH_DELAY_MINUTES, publish_time_of_day: null };
    case "time":
      return { publish_delay_minutes: 0, publish_time_of_day: DEFAULT_PUBLISH_TIME };
  }
}

export const SCHEDULED_PUBLISH_RULE =
  "Only public videos are scheduled: YouTube keeps the video private until this time, then makes it public.";

export function publishTimingHint(
  target: TargetDraft,
  channel: Channel | undefined,
): string | undefined {
  if (publishTiming(target) === "upload") {
    return undefined;
  }
  const fallback = target.privacy === null ? channel?.defaults.privacy : undefined;
  if (fallback !== undefined && fallback !== "public") {
    return `The channel default is ${fallback}, so this video is not scheduled. Set privacy to Public to use this.`;
  }
  return SCHEDULED_PUBLISH_RULE;
}
