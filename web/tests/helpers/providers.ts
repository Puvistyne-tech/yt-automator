import { db } from "@/api/mocks/db";

export function disableWriters() {
  db.state.providerConfig = db.state.providerConfig.map((config) => ({
    ...config,
    chain: config.chain.map((choice) => ({ ...choice, enabled: false })),
  }));
}
