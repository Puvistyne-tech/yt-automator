import { db } from "@/api/mocks/db";

const PLACEHOLDER_WRITER = "fake-llm";

export function disconnectChannels() {
  db.state.channels = db.state.channels.map((channel) => ({ ...channel, status: "expired" }));
}

export function onlyPlaceholderWriter() {
  db.state.providerConfig = db.state.providerConfig.map((config) => ({
    ...config,
    chain: config.chain.map((choice) => ({
      ...choice,
      enabled: choice.provider_id === PLACEHOLDER_WRITER,
    })),
  }));
}
