import type {
  Channel,
  ChannelStatus,
  Privacy,
  RunStatus,
  StageStatus,
  TemplateAudience,
  UploadStatus,
} from "@/api/types";
import type { RadioCardOption } from "@/shared/ui/RadioCards";
import type { Tone } from "@/shared/ui/surfaces";

export interface Label {
  label: string;
  tone: Tone;
}

export const RUN_STATUSES: Record<RunStatus, Label> = {
  queued: { label: "Queued", tone: "neutral" },
  running: { label: "Running", tone: "info" },
  awaiting_review: { label: "Awaiting review", tone: "warning" },
  approved: { label: "Approved", tone: "accent" },
  rejected: { label: "Rejected", tone: "danger" },
  publishing: { label: "Publishing", tone: "info" },
  published: { label: "Published", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
  cancelled: { label: "Cancelled", tone: "neutral" },
};

export const STAGE_STATUSES: Record<StageStatus, Label> = {
  pending: { label: "Pending", tone: "neutral" },
  running: { label: "Running", tone: "info" },
  done: { label: "Done", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
  skipped: { label: "Skipped", tone: "neutral" },
};

export const UPLOAD_STATUSES: Record<UploadStatus, Label> = {
  pending: { label: "Pending", tone: "neutral" },
  uploading: { label: "Uploading", tone: "info" },
  done: { label: "Uploaded", tone: "success" },
  failed: { label: "Failed", tone: "danger" },
  skipped: { label: "Skipped", tone: "neutral" },
};

export const CHANNEL_STATUSES: Record<ChannelStatus, Label> = {
  connected: { label: "Connected", tone: "success" },
  expired: { label: "Token expired", tone: "warning" },
  revoked: { label: "Access revoked", tone: "danger" },
};

export function channelOptionLabel(channel: Pick<Channel, "title" | "status">): string {
  return channel.status === "connected"
    ? channel.title
    : `${channel.title} (${CHANNEL_STATUSES[channel.status].label})`;
}

export const PRIVACY_LABELS: Record<Privacy, string> = {
  private: "Private",
  unlisted: "Unlisted",
  public: "Public",
};

export const RUN_STATUS_ORDER = Object.keys(RUN_STATUSES) as RunStatus[];
export const PRIVACY_ORDER = Object.keys(PRIVACY_LABELS) as Privacy[];
export const PRIVACY_OPTIONS: { value: Privacy; label: string }[] = PRIVACY_ORDER.map((value) => ({
  value,
  label: PRIVACY_LABELS[value],
}));

export function privacyFromValue(value: string): Privacy | null {
  return PRIVACY_ORDER.find((privacy) => privacy === value) ?? null;
}

export const AUDIENCE_LABELS: Record<TemplateAudience, Label> = {
  kids: { label: "For kids", tone: "accent" },
  general: { label: "General audience", tone: "neutral" },
};

export const AUDIENCE_ORDER = Object.keys(AUDIENCE_LABELS) as TemplateAudience[];

export function audienceOptions(
  descriptions?: Record<TemplateAudience, string>,
): RadioCardOption<TemplateAudience>[] {
  return AUDIENCE_ORDER.map((value) => ({
    value,
    label: AUDIENCE_LABELS[value].label,
    ...(descriptions === undefined ? {} : { description: descriptions[value] }),
  }));
}
