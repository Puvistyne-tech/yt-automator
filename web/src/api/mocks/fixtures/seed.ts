import { DEFAULT_SCHEDULE_LIMITS } from "@/api/automationDefaults";
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
import { type MockStorage, SETTINGS, STORAGE } from "@/api/mocks/fixtures/settings";
import { narratedEngine } from "@/api/mocks/fixtures/templateEngine";
import { USER_TEMPLATES } from "@/api/mocks/fixtures/templates";
import type {
  AppSettings,
  Automation,
  Channel,
  CredentialView,
  EngineSummary,
  PipelineDescriptor,
  PipelineTemplate,
  Playlist,
  ProviderConfig,
  ProviderDescriptor,
  Run,
  SecretInfo,
} from "@/api/types";

export interface MockState {
  pipelines: PipelineDescriptor[];
  engines: EngineSummary[];
  templates: PipelineTemplate[];
  credentials: CredentialView[];
  channels: Channel[];
  playlists: Record<string, Playlist[]>;
  automations: Automation[];
  runs: Run[];
  publishQueue: string[];
  descriptors: ProviderDescriptor[];
  providerConfig: ProviderConfig[];
  secrets: SecretInfo[];
  settings: AppSettings;
  storage: MockStorage;
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
      publish_time_of_day: "18:00",
      publish_timezone: "Asia/Kolkata",
    }),
  ],
  schedule: {
    kind: "interval",
    every_hours: 6,
    cron: null,
    timezone: "Asia/Kolkata",
    skip_if_unfinished: true,
    max_runs_per_day: 2,
    active_from: "08:00",
    active_until: "20:00",
  },
  review_policy: {
    mode: "auto_when_score_at_least",
    min_score: 90,
    reject_below: 60,
    auto_publish: true,
  },
  retry_policy: { auto_retry_count: 2, retry_delay_minutes: 15 },
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
  schedule: {
    kind: "manual",
    every_hours: null,
    cron: null,
    timezone: "UTC",
    ...DEFAULT_SCHEDULE_LIMITS,
  },
  enabled: false,
  next_run_at: null,
});

const SPACE = makeAutomation({
  id: "auto-space",
  name: "Space facts weekly",
  description: "A short space explainer every Saturday.",
  pipeline_type: "t_space-facts",
  targets: [makeTarget({ id: "target-space", variants: ["episode"], made_for_kids: false })],
  schedule: {
    kind: "cron",
    every_hours: null,
    cron: "0 10 * * 6",
    timezone: "UTC",
    ...DEFAULT_SCHEDULE_LIMITS,
  },
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
    youtube_channel_id: "UC_bedtime_ta_002",
    title: "Kathai Neram",
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
    youtube_channel_id: "UC_bedtime_classics_003",
    title: "Story Classics",
    status: "expired",
  }),
];

const PLAYLISTS: Record<string, Playlist[]> = {
  "chan-en": [
    { id: "pl-bedtime", title: "Bedtime stories" },
    { id: "pl-kindness", title: "Kindness tales" },
  ],
  "chan-ta": [{ id: "pl-ta-shorts", title: "Tamil shorts" }],
};

const SEED: Omit<MockState, "runs"> = {
  publishQueue: [],
  pipelines: [kidsStoryPipeline],
  engines: [narratedEngine],
  templates: USER_TEMPLATES,
  credentials: CREDENTIALS,
  channels: CHANNELS,
  playlists: PLAYLISTS,
  automations: [BEDTIME, SHORTS, FESTIVAL, SPACE],
  descriptors: providerDescriptors,
  providerConfig,
  secrets,
  settings: SETTINGS,
  storage: STORAGE,
};

export function seedState(): MockState {
  return { ...structuredClone(SEED), runs: seedRuns() };
}
