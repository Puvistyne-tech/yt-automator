import type { ProviderConfig, ProviderDescriptor, SecretInfo } from "@/api/types";

type DescriptorSeed = Pick<
  ProviderDescriptor,
  "provider_id" | "capability" | "name" | "description"
> &
  Partial<ProviderDescriptor>;

function descriptor(seed: DescriptorSeed): ProviderDescriptor {
  return {
    options_schema: { type: "object", properties: {} },
    required_secrets: [],
    offline: true,
    available: true,
    unavailable_reason: "",
    ...seed,
  };
}

const temperature = {
  type: "number",
  title: "Temperature",
  description: "Higher values give more surprising stories.",
  minimum: 0,
  maximum: 2,
  default: 0.8,
};

export const providerDescriptors: ProviderDescriptor[] = [
  descriptor({
    provider_id: "ollama",
    capability: "llm",
    name: "Ollama",
    description: "Local language models served by Ollama.",
    options_schema: {
      type: "object",
      properties: {
        model: { type: "string", title: "Model", default: "llama3.1:8b" },
        temperature,
      },
    },
  }),
  descriptor({
    provider_id: "gemini",
    capability: "llm",
    name: "Google Gemini",
    description: "Hosted Gemini models on the free tier.",
    offline: false,
    required_secrets: ["gemini_api_key"],
    available: false,
    unavailable_reason: "Secret gemini_api_key is not set.",
    options_schema: {
      type: "object",
      properties: {
        model: { type: "string", title: "Model", default: "gemini-2.5-flash" },
        temperature,
      },
    },
  }),
  descriptor({
    provider_id: "fake-llm",
    capability: "llm",
    name: "Offline fake",
    description: "Deterministic text for tests and dry runs.",
  }),
  descriptor({
    provider_id: "mflux",
    capability: "image",
    name: "MFLUX",
    description: "FLUX image models on Apple silicon.",
    options_schema: {
      type: "object",
      properties: {
        steps: { type: "integer", title: "Steps", minimum: 1, maximum: 50, default: 4 },
        quality: {
          type: "string",
          title: "Quality",
          enum: ["draft", "standard", "high"],
          default: "standard",
        },
      },
    },
  }),
  descriptor({
    provider_id: "fake-image",
    capability: "image",
    name: "Offline fake",
    description: "Solid colour frames.",
  }),
  descriptor({
    provider_id: "ken-burns",
    capability: "motion",
    name: "Ken Burns",
    description: "Pan and zoom with ffmpeg.",
  }),
  descriptor({
    provider_id: "kokoro",
    capability: "tts",
    name: "Kokoro",
    description: "Small local text-to-speech model.",
    available: false,
    unavailable_reason: "Model files not found. Run scripts/setup.sh on the Mac.",
  }),
  descriptor({
    provider_id: "fake-tts",
    capability: "tts",
    name: "Offline fake",
    description: "Silent narration of the right length.",
  }),
  descriptor({
    provider_id: "musicgen",
    capability: "music",
    name: "MusicGen",
    description: "Local music generation.",
  }),
  descriptor({
    provider_id: "ffmpeg",
    capability: "media",
    name: "FFmpeg",
    description: "Composes videos, extracts frames and measures loudness.",
  }),
];

export const providerConfig: ProviderConfig[] = [
  {
    capability: "llm",
    chain: [
      { provider_id: "ollama", enabled: true, options: { model: "llama3.1:8b", temperature: 0.8 } },
      { provider_id: "gemini", enabled: false, options: {} },
      { provider_id: "fake-llm", enabled: true, options: {} },
    ],
  },
  {
    capability: "image",
    chain: [
      { provider_id: "mflux", enabled: true, options: { steps: 4, quality: "standard" } },
      { provider_id: "fake-image", enabled: true, options: {} },
    ],
  },
  { capability: "motion", chain: [{ provider_id: "ken-burns", enabled: true, options: {} }] },
  {
    capability: "tts",
    chain: [
      { provider_id: "kokoro", enabled: true, options: {} },
      { provider_id: "fake-tts", enabled: true, options: {} },
    ],
  },
  { capability: "music", chain: [] },
  { capability: "media", chain: [{ provider_id: "ffmpeg", enabled: true, options: {} }] },
];

export const secrets: SecretInfo[] = [
  {
    name: "gemini_api_key",
    title: "Gemini API key",
    description: "From Google AI Studio. Enables the Gemini text provider.",
    is_set: false,
  },
  {
    name: "pixabay_api_key",
    title: "Pixabay API key",
    description: "Optional stock music fallback.",
    is_set: true,
  },
];
