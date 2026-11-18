import { hoursAgo, makeArtifact, makeRun, stagesWith } from "@/api/mocks/fixtures/factories";
import type { Artifact, Run } from "@/api/types";

function artifactsFor(language: string, variant: string): Artifact[] {
  const base = `${language}-${variant}`;
  const tall = variant === "short";
  return [
    makeArtifact({
      id: `art-video-${base}`,
      language,
      variant,
      filename: `${variant}-${language}.mp4`,
      size_bytes: tall ? 9_400_000 : 48_000_000,
      meta: tall
        ? { duration_seconds: 58, width: 1080, height: 1920 }
        : { duration_seconds: 312, width: 1920, height: 1080 },
    }),
    makeArtifact({
      id: `art-thumb-${base}`,
      kind: "thumbnail",
      language,
      variant,
      filename: `thumb-${base}.svg`,
      media_type: "image/svg+xml",
      size_bytes: 180_000,
      meta: {},
    }),
    makeArtifact({
      id: `art-subs-${base}`,
      kind: "subtitle",
      language,
      variant,
      filename: `${base}.vtt`,
      media_type: "text/vtt",
      size_bytes: 4_200,
      meta: {},
    }),
    makeArtifact({
      id: `art-meta-${base}`,
      kind: "metadata",
      language,
      variant,
      filename: `${base}.json`,
      media_type: "application/json",
      size_bytes: 1_100,
      meta: {},
    }),
  ];
}

const fullArtifacts = [
  makeArtifact({
    id: "art-story",
    kind: "text",
    stage_id: "story",
    language: null,
    variant: null,
    filename: "story.md",
    media_type: "text/markdown",
    size_bytes: 6_400,
    meta: {},
  }),
  ...artifactsFor("en", "episode"),
  ...artifactsFor("en", "short"),
  ...artifactsFor("ta", "episode"),
  ...artifactsFor("ta", "short"),
];

const scoreDetails = [
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
    detail: "Kutty looks the same in 11 of 12 scenes.",
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

export function seedRuns(): Run[] {
  return [
    makeRun({
      id: "run-live",
      status: "running",
      trigger: "manual",
      languages: ["en", "ta"],
      stages: stagesWith(["done", "done", "running", "pending", "pending", "pending"]),
      artifacts: [fullArtifacts[0] as Artifact],
      score: null,
      created_at: hoursAgo(0.3),
      started_at: hoursAgo(0.3),
      finished_at: null,
    }),
    makeRun({
      id: "run-review",
      languages: ["en", "ta"],
      artifacts: fullArtifacts,
      score: 91.4,
      score_details: scoreDetails,
      created_at: hoursAgo(3),
    }),
    makeRun({
      id: "run-published",
      status: "published",
      score: 89,
      score_details: scoreDetails,
      artifacts: [...artifactsFor("en", "episode"), ...artifactsFor("en", "short")],
      review: { decision: "approved", notes: "Lovely one.", decided_at: hoursAgo(26) },
      uploads: [
        {
          target_id: "target-en",
          channel_id: "chan-en",
          language: "en",
          variant: "episode",
          status: "done",
          youtube_video_id: "dQw4w9WgXcQ",
          url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
          error: null,
          quota_units: 2050,
        },
        {
          target_id: "target-en",
          channel_id: "chan-en",
          language: "en",
          variant: "short",
          status: "failed",
          youtube_video_id: null,
          url: null,
          error: "Upload quota exceeded for today.",
          quota_units: 0,
        },
      ],
      created_at: hoursAgo(27),
      started_at: hoursAgo(27),
      finished_at: hoursAgo(25),
    }),
    makeRun({
      id: "run-failed",
      automation_id: "auto-shorts",
      automation_name: "Tamil shorts",
      status: "failed",
      languages: ["ta"],
      stages: stagesWith(["done", "done", "done", "failed", "pending", "pending"]),
      artifacts: [],
      score: null,
      error: "Narrate: the Tamil voice model is not installed.",
      created_at: hoursAgo(8),
      started_at: hoursAgo(8),
      finished_at: hoursAgo(7.8),
    }),
    makeRun({
      id: "run-queued",
      automation_id: "auto-shorts",
      automation_name: "Tamil shorts",
      status: "queued",
      languages: ["ta"],
      stages: stagesWith([]),
      artifacts: [],
      score: null,
      created_at: hoursAgo(0.1),
      started_at: null,
      finished_at: null,
    }),
  ];
}
