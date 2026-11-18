import type { FieldErrors } from "@/api/errors";
import type {
  ProviderChoice,
  ProviderConfig,
  ProviderDescriptor,
  ProvidersResponse,
} from "@/api/types";
import { scopedErrors } from "@/shared/schema-form/errors";

export function capabilitiesOf(response: ProvidersResponse): string[] {
  const ordered = response.config.map((c) => c.capability);
  const extra = response.descriptors.map((d) => d.capability).filter((c) => !ordered.includes(c));
  return [...new Set([...ordered, ...extra])];
}

export function chainFor(config: ProviderConfig[], capability: string): ProviderChoice[] {
  return config.find((c) => c.capability === capability)?.chain ?? [];
}

export function withChain(
  config: ProviderConfig[],
  capability: string,
  chain: ProviderChoice[],
): ProviderConfig[] {
  const exists = config.some((c) => c.capability === capability);
  return exists
    ? config.map((c) => (c.capability === capability ? { ...c, chain } : c))
    : [...config, { capability, chain }];
}

export function moveChoice(
  chain: ProviderChoice[],
  index: number,
  delta: -1 | 1,
): ProviderChoice[] {
  const target = index + delta;
  const item = chain[index];
  const other = chain[target];
  if (item === undefined || other === undefined) {
    return chain;
  }
  const next = [...chain];
  next[index] = other;
  next[target] = item;
  return next;
}

export function patchChoice(
  chain: ProviderChoice[],
  index: number,
  patch: Partial<ProviderChoice>,
): ProviderChoice[] {
  return chain.map((choice, i) => (i === index ? { ...choice, ...patch } : choice));
}

export function removeChoice(chain: ProviderChoice[], index: number): ProviderChoice[] {
  return chain.filter((_, i) => i !== index);
}

export function addableProviders(
  descriptors: ProviderDescriptor[],
  capability: string,
  chain: ProviderChoice[],
): ProviderDescriptor[] {
  const used = new Set(chain.map((c) => c.provider_id));
  return descriptors.filter((d) => d.capability === capability && !used.has(d.provider_id));
}

export function activeProvider(
  chain: ProviderChoice[],
  descriptors: ProviderDescriptor[],
): ProviderDescriptor | undefined {
  return chain
    .filter((choice) => choice.enabled)
    .map((choice) => descriptors.find((d) => d.provider_id === choice.provider_id))
    .find((descriptor) => descriptor?.available === true);
}

export function hasOptions(descriptor: ProviderDescriptor | undefined): boolean {
  const properties = descriptor?.options_schema.properties;
  return (
    typeof properties === "object" && properties !== null && Object.keys(properties).length > 0
  );
}

export function chainDescription(active: ProviderDescriptor | undefined): string {
  return active
    ? `Runs use ${active.name}, then fall back down the list.`
    : "No available provider is enabled. Runs that need this will fail.";
}

export function chainChanged(config: ProviderConfig[], saved: ProviderConfig[]): boolean {
  return JSON.stringify(config) !== JSON.stringify(saved);
}

export function newChoice(providerId: string): ProviderChoice {
  return { provider_id: providerId, enabled: true, options: {} };
}

export function defaultOrderDescription(
  descriptors: ProviderDescriptor[],
  capability: string,
): string {
  const names = descriptors.filter((d) => d.capability === capability).map((d) => d.name);
  return names.length === 0
    ? "No installed provider offers this capability."
    : `No order saved: runs try ${names.join(", ")} in turn.`;
}

export interface ChoiceErrors {
  message: string | undefined;
  options: FieldErrors;
}

const CHAIN_PREFIX = "chain.";
const OPTIONS_PREFIX = "options.";

function firstErrorOutside(errors: FieldErrors, prefix: string): string | undefined {
  return Object.entries(errors).find(([path]) => !path.startsWith(prefix))?.[1];
}

export function configErrors(
  errors: FieldErrors,
  config: ProviderConfig[],
  capability: string,
): FieldErrors {
  const index = config.findIndex((c) => c.capability === capability);
  return index === -1 ? {} : scopedErrors(errors, String(index));
}

export function cardError(errors: FieldErrors): string | undefined {
  return firstErrorOutside(errors, CHAIN_PREFIX);
}

export function choiceErrors(errors: FieldErrors, position: number): ChoiceErrors {
  const scoped = scopedErrors(errors, `${CHAIN_PREFIX}${position}`);
  return {
    message: firstErrorOutside(scoped, OPTIONS_PREFIX),
    options: scopedErrors(scoped, "options"),
  };
}
