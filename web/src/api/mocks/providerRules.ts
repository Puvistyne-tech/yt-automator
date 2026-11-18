import type { FieldErrors } from "@/api/errors";
import type { ProviderChoice, ProviderConfig, ProviderDescriptor } from "@/api/types";
import { validateSchemaData } from "@/shared/schema-form/errors";

function choiceProblem(
  choice: ProviderChoice,
  capability: string,
  descriptor: ProviderDescriptor | undefined,
  seen: Set<string>,
): string | null {
  if (descriptor === undefined) {
    return `unknown provider '${choice.provider_id}'`;
  }
  if (descriptor.capability !== capability) {
    return `provider does not offer ${capability}`;
  }
  return seen.has(choice.provider_id) ? "provider is listed twice" : null;
}

function optionErrors(prefix: string, choice: ProviderChoice, descriptor: ProviderDescriptor) {
  const problems = validateSchemaData(descriptor.options_schema, choice.options);
  return Object.fromEntries(
    Object.entries(problems).map(([field, message]) => [`${prefix}.options.${field}`, message]),
  );
}

function chainErrors(index: number, config: ProviderConfig, descriptors: ProviderDescriptor[]) {
  const errors: FieldErrors = {};
  const seen = new Set<string>();
  config.chain.forEach((choice, position) => {
    const prefix = `${index}.chain.${position}`;
    const descriptor = descriptors.find((d) => d.provider_id === choice.provider_id);
    const problem = choiceProblem(choice, config.capability, descriptor, seen);
    if (problem !== null) {
      errors[`${prefix}.provider_id`] = problem;
    } else if (descriptor !== undefined) {
      Object.assign(errors, optionErrors(prefix, choice, descriptor));
    }
    seen.add(choice.provider_id);
  });
  return errors;
}

export function providerConfigErrors(
  configs: ProviderConfig[],
  descriptors: ProviderDescriptor[],
): FieldErrors {
  const errors: FieldErrors = {};
  const seen = new Set<string>();
  configs.forEach((config, index) => {
    if (seen.has(config.capability)) {
      errors[`${index}.capability`] = "capability is configured twice";
    }
    seen.add(config.capability);
    Object.assign(errors, chainErrors(index, config, descriptors));
  });
  return errors;
}
