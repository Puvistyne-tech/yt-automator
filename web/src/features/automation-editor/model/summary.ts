import type { Channel, Privacy, RetryPolicy, ReviewPolicy, Schedule } from "@/api/types";
import type { AutomationDraft, TargetDraft } from "@/features/automation-editor/model/draft";
import { describeCron } from "@/shared/format/cron";
import { describeInterval } from "@/shared/format/schedule";

const PRIVACY_WORDS: Record<Privacy, string> = {
  private: "privately",
  unlisted: "as unlisted",
  public: "publicly",
};

function lowerFirst(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

function cadence(schedule: Schedule): string {
  if (schedule.kind === "interval") {
    return `Runs ${lowerFirst(describeInterval(schedule.every_hours))}`;
  }
  const described = describeCron(schedule.cron ?? "");
  const readable = described.startsWith("Every") || described.startsWith("On ");
  return readable ? `Runs ${lowerFirst(described)}` : `Runs on cron "${schedule.cron ?? ""}"`;
}

function zoneNote(schedule: Schedule): string {
  return schedule.timezone === "UTC" ? "" : ` (${schedule.timezone})`;
}

function cap(count: number): string {
  return count === 1 ? "at most once a day" : `at most ${count} a day`;
}

export function schedulePhrase(schedule: Schedule): string {
  if (schedule.kind === "manual") {
    return "Runs only when you press Run now.";
  }
  const parts = [cadence(schedule)];
  if (schedule.active_from !== null && schedule.active_until !== null) {
    parts.push(`${schedule.active_from} to ${schedule.active_until}${zoneNote(schedule)}`);
  } else if (schedule.kind === "cron") {
    parts[0] = `${parts[0]}${zoneNote(schedule)}`;
  }
  if (schedule.max_runs_per_day !== null) {
    parts.push(cap(schedule.max_runs_per_day));
  }
  const overlap = schedule.skip_if_unfinished ? "" : " Scheduled runs may overlap.";
  return `${parts.join(", ")}.${overlap}`;
}

export function retryPhrase(policy: RetryPolicy): string {
  const count = policy.auto_retry_count;
  if (count <= 0) {
    return "";
  }
  const times = count === 1 ? "once" : `up to ${count} times`;
  const delay = policy.retry_delay_minutes;
  const wait = delay <= 0 ? "right away" : `after ${delay} minute${delay === 1 ? "" : "s"}`;
  return `Retries a failed run ${times}, ${wait}.`;
}

export function privacyWord(targets: TargetDraft[], channels: Channel[]): string | null {
  const words = new Set(
    targets.map((target) => {
      const privacy = effectivePrivacy(target, channels);
      return privacy === undefined ? "with the channel default" : PRIVACY_WORDS[privacy];
    }),
  );
  if (words.size === 0) {
    return null;
  }
  return words.size === 1 ? ([...words][0] ?? null) : "with each target's privacy";
}

function effectivePrivacy(target: TargetDraft, channels: Channel[]): Privacy | undefined {
  return target.privacy ?? channels.find((c) => c.id === target.channel_id)?.defaults.privacy;
}

export function publishTimePhrase(targets: TargetDraft[], channels: Channel[]): string {
  const times = new Set(
    targets
      .filter((target) => effectivePrivacy(target, channels) === "public")
      .flatMap((target) =>
        target.publish_time_of_day === null
          ? []
          : [`${target.publish_time_of_day} (${target.publish_timezone})`],
      ),
  );
  return times.size === 0 ? "" : `Goes public at ${[...times].join(" and ")}.`;
}

function approvalPhrase(policy: ReviewPolicy): string {
  return policy.mode === "auto_when_score_at_least"
    ? `when the score reaches ${policy.min_score}, otherwise after you approve`
    : "after you approve";
}

export function reviewPhrase(policy: ReviewPolicy, privacy: string | null): string {
  const rejects =
    policy.reject_below === null ? "" : `Rejects runs scoring under ${policy.reject_below}. `;
  if (privacy === null) {
    return `${rejects}Nothing publishes until you add a target.`;
  }
  if (policy.auto_publish) {
    return `${rejects}Publishes ${privacy} ${approvalPhrase(policy)}.`;
  }
  const approves =
    policy.mode === "auto_when_score_at_least"
      ? `Approves runs scoring ${policy.min_score} or more. `
      : "";
  return `${rejects}${approves}Publishes ${privacy} when you press Publish after approval.`;
}

export function automationSummary(draft: AutomationDraft, channels: Channel[]): string {
  const privacy = privacyWord(draft.targets, channels);
  return [
    schedulePhrase(draft.schedule),
    retryPhrase(draft.retry_policy),
    reviewPhrase(draft.review_policy, privacy),
    publishTimePhrase(draft.targets, channels),
  ]
    .filter((part) => part !== "")
    .join(" ");
}
