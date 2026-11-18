import { providerConfig, providerDescriptors } from "@/api/mocks/fixtures/providers";
import { providerConfigErrors } from "@/api/mocks/providerRules";
import type { ProviderConfig } from "@/api/types";

const llm = (chain: ProviderConfig["chain"]): ProviderConfig => ({ capability: "llm", chain });
const choice = (provider_id: string, options: Record<string, unknown> = {}) => ({
  provider_id,
  enabled: true,
  options,
});

describe("mock provider config rules", () => {
  it("accepts the seeded config", () => {
    expect(providerConfigErrors(providerConfig, providerDescriptors)).toEqual({});
  });

  it("keys every problem by its position in the request", () => {
    const configs = [
      llm([
        choice("nope"),
        choice("ffmpeg"),
        choice("ollama", { temperature: 9 }),
        choice("ollama"),
      ]),
      llm([]),
    ];
    expect(providerConfigErrors(configs, providerDescriptors)).toEqual({
      "0.chain.0.provider_id": "unknown provider 'nope'",
      "0.chain.1.provider_id": "provider does not offer llm",
      "0.chain.2.options.temperature": "Must be <= 2.",
      "0.chain.3.provider_id": "provider is listed twice",
      "1.capability": "capability is configured twice",
    });
  });
});
