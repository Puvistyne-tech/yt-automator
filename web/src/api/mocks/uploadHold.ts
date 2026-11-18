import type { Automation, Upload } from "@/api/types";

const MINUTE_MS = 60_000;

export type PublishDelays = Record<string, number>;

export function publishDelays(automations: Automation[]): PublishDelays {
  return Object.fromEntries(
    automations.flatMap((automation) =>
      automation.targets.map((target) => [target.id, target.publish_delay_minutes]),
    ),
  );
}

function isScheduled(upload: Upload, now: number): boolean {
  return upload.publish_at !== null && Date.parse(upload.publish_at) > now;
}

function lacksPublishTime(upload: Upload): boolean {
  const mayGoPublic = upload.privacy === "public" || upload.privacy === null;
  return upload.status === "done" && upload.publish_at === null && mayGoPublic;
}

function mayStillGoPublic(
  upload: Upload,
  finished: number,
  now: number,
  delays: PublishDelays,
): boolean {
  if (!lacksPublishTime(upload)) {
    return false;
  }
  const delay = delays[upload.target_id];
  return delay === undefined || finished + delay * MINUTE_MS > now;
}

export function holdsRun(
  upload: Upload,
  finished: number,
  now: number,
  delays: PublishDelays,
): boolean {
  const unfinished = upload.status === "pending" || upload.status === "uploading";
  return unfinished || isScheduled(upload, now) || mayStillGoPublic(upload, finished, now, delays);
}
