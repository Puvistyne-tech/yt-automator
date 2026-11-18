import { nextLocalTime } from "@/api/mocks/publishTime";
import type { Automation, Target, Upload } from "@/api/types";

const MINUTE_MS = 60_000;

export type PublishTargets = Record<string, Target>;

export function publishTargets(automations: Automation[]): PublishTargets {
  return Object.fromEntries(
    automations.flatMap((automation) => automation.targets.map((target) => [target.id, target])),
  );
}

function isScheduled(upload: Upload, now: number): boolean {
  return upload.publish_at !== null && Date.parse(upload.publish_at) > now;
}

function lacksPublishTime(upload: Upload): boolean {
  const mayGoPublic = upload.privacy === "public" || upload.privacy === null;
  return upload.status === "done" && upload.publish_at === null && mayGoPublic;
}

export function latestRelease(target: Target, finished: number): number | null {
  const time = target.publish_time_of_day;
  if (time === null) {
    return finished + target.publish_delay_minutes * MINUTE_MS;
  }
  try {
    return nextLocalTime(finished, time, target.publish_timezone);
  } catch {
    return null;
  }
}

function mayStillGoPublic(
  upload: Upload,
  finished: number,
  now: number,
  targets: PublishTargets,
): boolean {
  if (!lacksPublishTime(upload)) {
    return false;
  }
  const target = targets[upload.target_id];
  const release = target === undefined ? null : latestRelease(target, finished);
  return release === null || release > now;
}

export function holdsRun(
  upload: Upload,
  finished: number,
  now: number,
  targets: PublishTargets,
): boolean {
  const unfinished = upload.status === "pending" || upload.status === "uploading";
  return unfinished || isScheduled(upload, now) || mayStillGoPublic(upload, finished, now, targets);
}
