import { db } from "@/api/mocks/db";
import { makeUpload } from "@/api/mocks/fixtures/factories";
import type { Run, Target, Upload } from "@/api/types";

export const NO_UPLOAD_SUCCEEDED = "no upload succeeded";

function hasVideo(run: Run, language: string, variant: string): boolean {
  return run.artifacts.some(
    (artifact) =>
      artifact.kind === "video" && artifact.language === language && artifact.variant === variant,
  );
}

export function skipReason(run: Run, target: Target, variant: string): string | null {
  if (!run.languages.includes(target.language)) {
    return `Language ${target.language} is not in this run.`;
  }
  if (!db.state.channels.some((c) => c.id === target.channel_id)) {
    return "The channel no longer exists.";
  }
  return hasVideo(run, target.language, variant)
    ? null
    : `No ${variant} video for ${target.language} in this run.`;
}

function uploadFor(run: Run, target: Target, variant: string): Upload {
  const reason = skipReason(run, target, variant);
  return makeUpload({
    target_id: target.id,
    channel_id: target.channel_id,
    language: target.language,
    variant,
    ...(reason === null
      ? { youtube_video_id: `vid${Math.random().toString(36).slice(2, 10)}` }
      : { status: "skipped", youtube_video_id: null, url: null, error: reason, quota_units: 0 }),
  });
}

function uploadsFor(run: Run): Upload[] {
  const automation = db.state.automations.find((a) => a.id === run.automation_id);
  return (automation?.targets ?? []).flatMap((target) =>
    target.variants.map((variant) => uploadFor(run, target, variant)),
  );
}

export function publishRun(run: Run): Run {
  const uploads = uploadsFor(run);
  if (uploads.some((upload) => upload.status === "done")) {
    return { ...run, status: "published", uploads, error: null, finished_at: db.now() };
  }
  return { ...run, status: "approved", uploads, error: NO_UPLOAD_SUCCEEDED };
}
