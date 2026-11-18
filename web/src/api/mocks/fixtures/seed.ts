import {
  hoursAgo,
  makeAutomation,
  makeChannel,
  makeCredential,
  makeTarget,
} from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import { providerConfig, providerDescriptors, secrets } from "@/api/mocks/fixtures/providers";
import { seedRuns } from "@/api/mocks/fixtures/runs";
import type {
  AppSettings,
  Automation,
  Channel,
  CredentialView,
  PipelineDescriptor,
  Playlist,
  ProviderConfig,
  ProviderDescriptor,
  Run,
  SecretInfo,
} from "@/api/types";

export interface MockState {
  pipelines: PipelineDescriptor[];
  credentials: CredentialView[];
  channels: Channel[];
  playlists: Record<string, Playlist[]>;
  automations: Automation[];
  runs: Run[];
  descriptors: ProviderDescriptor[];
  providerConfig: ProviderConfig[];
  secrets: SecretInfo[];
  settings: AppSettings;
}

const BEDTIME = makeAutomation({
  languages: ["en", "ta"],
  targets: [
    makeTarget(),
    makeTarget({ id: "target-ta", channel_id: "chan-ta", language: "ta", variants: ["episode"] }),
  ],
  last_run: {
    id: "run-review",
    status: "awaiting_review",
    score: 91.4,
    created_at: hoursAgo(3),
    finished_at: hoursAgo(1),
  },
});

const SHORTS = makeAutomation({
  id: "auto-shorts",
  name: "Tamil shorts",
  description: "Vertical shorts every six hours.",
  languages: ["ta"],
  targets: [
    makeTarget({
      id: "target-ta-short",
      channel_id: "chan-ta",
      language: "ta",
      variants: ["short"],
      privacy: "public",
    }),
  ],
  schedule: { kind: "interval", every_hours: 6, cron: null, timezone: "UTC" },
  review_policy: { mode: "auto_when_score_at_least", min_score: 90 },
  next_run_at: hoursAgo(-2),
  last_run: {
    id: "run-failed",
    status: "failed",
    score: null,
    created_at: hoursAgo(8),
    finished_at: hoursAgo(7.8),
  },
});

const FESTIVAL = makeAutomation({
  id: "auto-festival",
  name: "Festival specials",
  description: "Hand-triggered festival episodes.",
  targets: [makeTarget({ id: "target-classics", channel_id: "chan-old", variants: ["episode"] })],
  schedule: { kind: "manual", every_hours: null, cron: null, timezone: "UTC" },
  enabled: false,
  next_run_at: null,
});

const CREDENTIALS = [
  makeCredential(),
  makeCredential({
    id: "cred-spare",
    name: "Spare project",
    client_id: "5678-spare.apps.googleusercontent.com",
    has_secret: false,
    quota_used_today: 0,
  }),
];

const CHANNELS = [
  makeChannel(),
  makeChannel({
    id: "chan-ta",
    youtube_channel_id: "UC_kutty_ta_002",
    title: "Kutty Kathaigal",
    defaults: {
      privacy: "unlisted",
      made_for_kids: true,
      category_id: "1",
      default_language: "ta",
      notify_subscribers: true,
    },
  }),
  makeChannel({
    id: "chan-old",
    youtube_channel_id: "UC_kutty_classics_003",
    title: "Kutty Classics",
    status: "expired",
  }),
];

const PLAYLISTS: Record<string, Playlist[]> = {
  "chan-en": [
    { id: "pl-bedtime", title: "Bedtime stories" },
    { id: "pl-kindness", title: "Kindness tales" },
  ],
  "chan-ta": [{ id: "pl-ta-shorts", title: "Kutty shorts" }],
};

const SETTINGS: AppSettings = {
  timezone: "Asia/Kolkata",
  max_parallel_runs: 1,
  keep_runs_days: 30,
  data_dir: "~/Library/Application Support/YouTube Automator",
};

const SEED: Omit<MockState, "runs"> = {
  pipelines: [kidsStoryPipeline],
  credentials: CREDENTIALS,
  channels: CHANNELS,
  playlists: PLAYLISTS,
  automations: [BEDTIME, SHORTS, FESTIVAL],
  descriptors: providerDescriptors,
  providerConfig,
  secrets,
  settings: SETTINGS,
};

export function seedState(): MockState {
  return { ...structuredClone(SEED), runs: seedRuns() };
}
