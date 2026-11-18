import {
  DEFAULT_RETRY_POLICY,
  DEFAULT_REVIEW_POLICY,
  DEFAULT_SCHEDULE_LIMITS,
} from "@/api/automationDefaults";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type {
  Artifact,
  Automation,
  Channel,
  CredentialView,
  Run,
  StageRun,
  StageStatus,
  Target,
  Upload,
} from "@/api/types";

export const FIXED_NOW = new Date().toISOString();

export function hoursAgo(hours: number, from = FIXED_NOW): string {
  return new Date(new Date(from).getTime() - hours * 3_600_000).toISOString();
}

export function makeCredential(overrides: Partial<CredentialView> = {}): CredentialView {
  return {
    id: "cred-main",
    name: "Main Google project",
    client_id: "1234-main.apps.googleusercontent.com",
    daily_quota_units: 10_000,
    created_at: hoursAgo(24 * 30),
    has_secret: true,
    quota_used_today: 3_250,
    ...overrides,
  };
}

export function makeChannel(overrides: Partial<Channel> = {}): Channel {
  return {
    id: "chan-en",
    credential_id: "cred-main",
    youtube_channel_id: "UC_bedtime_en_001",
    title: "Bedtime tales",
    thumbnail_url: "",
    status: "connected",
    defaults: {
      privacy: "private",
      made_for_kids: true,
      category_id: "1",
      default_language: "en",
      notify_subscribers: false,
    },
    connected_at: hoursAgo(24 * 20),
    ...overrides,
  };
}

export function makeTarget(overrides: Partial<Target> = {}): Target {
  return {
    id: "target-en",
    channel_id: "chan-en",
    language: "en",
    variants: ["episode", "short"],
    privacy: null,
    made_for_kids: true,
    playlist_id: null,
    publish_delay_minutes: 0,
    publish_time_of_day: null,
    publish_timezone: "Asia/Kolkata",
    ...overrides,
  };
}

export function makeAutomation(overrides: Partial<Automation> = {}): Automation {
  return {
    id: "auto-bedtime",
    name: "Bedtime stories",
    description: "Nightly kindness stories for the English and Tamil channels.",
    pipeline_type: kidsStoryPipeline.type_id,
    settings: structuredClone(kidsStoryPipeline.default_settings),
    languages: ["en"],
    targets: [makeTarget()],
    schedule: {
      kind: "cron",
      every_hours: null,
      cron: "0 18 * * *",
      timezone: "Asia/Kolkata",
      ...DEFAULT_SCHEDULE_LIMITS,
    },
    review_policy: { ...DEFAULT_REVIEW_POLICY },
    retry_policy: { ...DEFAULT_RETRY_POLICY },
    enabled: true,
    created_at: hoursAgo(24 * 14),
    updated_at: hoursAgo(24 * 2),
    next_run_at: hoursAgo(-6),
    last_run: null,
    ...overrides,
  };
}

export function stagesWith(statuses: StageStatus[]): StageRun[] {
  return kidsStoryPipeline.stages.map((stage, index) => {
    const status = statuses[index] ?? "pending";
    const started = status === "pending" ? null : hoursAgo(2 - index * 0.1);
    return {
      stage_id: stage.id,
      title: stage.title,
      status,
      provider: status === "pending" ? "" : `fake-${stage.id}`,
      message: status === "done" ? `${stage.title} finished` : "",
      started_at: started,
      finished_at: status === "done" || status === "failed" ? hoursAgo(1.95 - index * 0.1) : null,
    };
  });
}

export function makeArtifact(overrides: Partial<Artifact> = {}): Artifact {
  return {
    id: "art-video-en-episode",
    kind: "video",
    stage_id: "render",
    language: "en",
    variant: "episode",
    filename: "episode-en.mp4",
    media_type: "video/mp4",
    size_bytes: 48_000_000,
    meta: { duration_seconds: 312, width: 1920, height: 1080 },
    ...overrides,
  };
}

export function makeRun(overrides: Partial<Run> = {}): Run {
  return {
    id: "run-review",
    automation_id: "auto-bedtime",
    automation_name: "Bedtime stories",
    pipeline_type: kidsStoryPipeline.type_id,
    status: "awaiting_review",
    trigger: "schedule",
    languages: ["en"],
    settings_snapshot: structuredClone(kidsStoryPipeline.default_settings),
    review_policy: { ...DEFAULT_REVIEW_POLICY },
    retry_policy: { ...DEFAULT_RETRY_POLICY },
    auto_retries: 0,
    retry_at: null,
    skipped_start_at: null,
    stages: stagesWith(["done", "done", "done", "done", "done", "done"]),
    artifacts: [makeArtifact()],
    score: 88,
    score_details: [],
    review: null,
    uploads: [],
    logs: [],
    error: null,
    created_at: hoursAgo(2),
    started_at: hoursAgo(2),
    finished_at: hoursAgo(1),
    intermediate_removed_at: null,
    ...overrides,
  };
}

export function makeUpload(overrides: Partial<Upload> = {}): Upload {
  return {
    target_id: "target-en",
    channel_id: "chan-en",
    language: "en",
    variant: "episode",
    status: "done",
    youtube_video_id: "dQw4w9WgXcQ",
    url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    error: null,
    quota_units: 2050,
    privacy: "private",
    made_for_kids: true,
    publish_at: null,
    ...overrides,
  };
}
