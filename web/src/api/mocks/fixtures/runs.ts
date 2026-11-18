import { autoRejectMessage, autoRetryMessage, skippedStartMessage } from "@/api/automaticEvents";
import { artifactsFor, FULL_ARTIFACTS, STORY_ARTIFACT } from "@/api/mocks/fixtures/artifacts";
import { hoursAgo, makeRun, makeUpload, stagesWith } from "@/api/mocks/fixtures/factories";
import type { LogLevel, ReviewPolicy, Run, RunLog, ScoreItem } from "@/api/types";

function log(
  hours: number,
  stage_id: string | null,
  message: string,
  level: LogLevel = "info",
): RunLog {
  return { at: hoursAgo(hours), level, stage_id, message };
}

const SCORE_DETAILS: ScoreItem[] = [
  {
    id: "story",
    title: "Story quality",
    score: 92,
    weight: 0.3,
    detail: "Clear moral, age-appropriate words.",
  },
  {
    id: "visuals",
    title: "Visual consistency",
    score: 86,
    weight: 0.25,
    detail: "Kavin looks the same in 11 of 12 scenes.",
  },
  {
    id: "audio",
    title: "Narration clarity",
    score: 90,
    weight: 0.25,
    detail: "No clipping; pace 140 wpm.",
  },
  {
    id: "safety",
    title: "Child safety",
    score: 100,
    weight: 0.2,
    detail: "No unsafe content detected.",
  },
];

const SHORTS_POLICY: ReviewPolicy = {
  mode: "auto_when_score_at_least",
  min_score: 90,
  reject_below: 60,
  auto_publish: true,
};

const SHORTS = {
  automation_id: "auto-shorts",
  automation_name: "Tamil shorts",
  languages: ["ta"],
  review_policy: SHORTS_POLICY,
  retry_policy: { auto_retry_count: 2, retry_delay_minutes: 15 },
  artifacts: [],
  score: null,
};

const RUN_LIVE = makeRun({
  id: "run-live",
  status: "running",
  trigger: "manual",
  languages: ["en", "ta"],
  stages: stagesWith(["done", "done", "running", "pending", "pending", "pending"]),
  artifacts: [STORY_ARTIFACT],
  logs: [
    log(0.29, "story", "Story written in English and Tamil"),
    log(0.25, "images", "Scene 4 needed a second attempt", "warning"),
    log(0.2, "motion", "Animating 8 scenes"),
    log(
      0.1,
      null,
      skippedStartMessage("2026-01-05 18:00 Asia/Kolkata", "run-live", "running"),
      "warning",
    ),
  ],
  skipped_start_at: hoursAgo(0.1),
  score: null,
  created_at: hoursAgo(0.3),
  started_at: hoursAgo(0.3),
  finished_at: null,
});

const RUN_REVIEW = makeRun({
  id: "run-review",
  languages: ["en", "ta"],
  artifacts: FULL_ARTIFACTS,
  score: 91.4,
  score_details: SCORE_DETAILS,
  created_at: hoursAgo(3),
});

const PUBLISHED_UPLOADS = [
  makeUpload(),
  makeUpload({
    variant: "short",
    status: "failed",
    youtube_video_id: null,
    url: null,
    error: "Upload quota exceeded for today.",
    quota_units: 0,
  }),
  makeUpload({
    target_id: "target-ta",
    channel_id: "chan-ta",
    language: "ta",
    privacy: "unlisted",
    status: "skipped",
    youtube_video_id: null,
    url: null,
    error: "Language ta is not in this run.",
    quota_units: 0,
  }),
];

const RUN_PUBLISHED = makeRun({
  id: "run-published",
  status: "published",
  score: 89,
  score_details: SCORE_DETAILS,
  artifacts: [...artifactsFor("en", "episode"), ...artifactsFor("en", "short")],
  review: { decision: "approved", notes: "Lovely one.", decided_at: hoursAgo(26) },
  uploads: PUBLISHED_UPLOADS,
  created_at: hoursAgo(27),
  started_at: hoursAgo(27),
  finished_at: hoursAgo(25),
});

const VOICE_ERROR = "Narrate: the Tamil voice model is not installed.";

const RUN_FAILED = makeRun({
  ...SHORTS,
  id: "run-failed",
  status: "failed",
  stages: stagesWith(["done", "done", "done", "failed", "pending", "pending"]),
  error: VOICE_ERROR,
  auto_retries: 1,
  retry_at: hoursAgo(-0.2),
  logs: [
    log(8.4, null, autoRetryMessage(1, 2, "voice", VOICE_ERROR)),
    log(7.95, "voice", "Kokoro has no Tamil voice, trying the next provider", "warning"),
    log(7.9, "voice", "No text-to-speech provider can speak Tamil", "error"),
    log(7.8, null, "Run failed"),
  ],
  created_at: hoursAgo(8),
  started_at: hoursAgo(8),
  finished_at: hoursAgo(7.8),
});

const RUN_QUEUED = makeRun({
  ...SHORTS,
  id: "run-queued",
  status: "queued",
  stages: stagesWith([]),
  created_at: hoursAgo(0.1),
  started_at: null,
  finished_at: null,
});

const REJECTION = autoRejectMessage(52.5, 60);

const RUN_REJECTED = makeRun({
  ...SHORTS,
  id: "run-rejected",
  status: "rejected",
  score: 52.5,
  score_details: SCORE_DETAILS,
  review: { decision: "rejected", notes: REJECTION, decided_at: hoursAgo(13) },
  logs: [log(13, null, REJECTION, "warning")],
  created_at: hoursAgo(14),
  started_at: hoursAgo(14),
  finished_at: hoursAgo(13),
});

const SEED_RUNS: Run[] = [
  RUN_LIVE,
  RUN_REVIEW,
  RUN_PUBLISHED,
  RUN_FAILED,
  RUN_QUEUED,
  RUN_REJECTED,
];

export function seedRuns(): Run[] {
  return structuredClone(SEED_RUNS);
}
