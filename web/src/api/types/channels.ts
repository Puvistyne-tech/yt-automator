import type { Privacy } from "@/api/types/common";

export type ChannelStatus = "connected" | "expired" | "revoked";

export interface Credential {
  id: string;
  name: string;
  client_id: string;
  daily_quota_units: number;
  created_at: string;
}

export interface CredentialView extends Credential {
  has_secret: boolean;
  quota_used_today: number;
}

export interface CredentialInput {
  name: string;
  client_id: string;
  client_secret: string;
  daily_quota_units?: number;
}

export type CredentialPatch = Partial<CredentialInput>;

export interface ChannelDefaults {
  privacy: Privacy;
  made_for_kids: boolean;
  category_id: string;
  default_language: string;
  notify_subscribers: boolean;
}

export interface Channel {
  id: string;
  credential_id: string;
  youtube_channel_id: string;
  title: string;
  thumbnail_url: string;
  status: ChannelStatus;
  defaults: ChannelDefaults;
  connected_at: string;
}

export interface Playlist {
  id: string;
  title: string;
}
