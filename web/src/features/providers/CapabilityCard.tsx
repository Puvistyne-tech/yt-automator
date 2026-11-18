import type { FieldErrors } from "@/api/errors";
import type { ProviderChoice, ProviderDescriptor } from "@/api/types";
import { ChainRow } from "@/features/providers/ChainRow";
import {
  activeProvider,
  addableProviders,
  cardError,
  chainDescription,
  choiceErrors,
  defaultOrderDescription,
  moveChoice,
  newChoice,
  patchChoice,
  removeChoice,
} from "@/features/providers/chain";
import { humanizeId } from "@/shared/format/text";
import { Callout, Card, EmptyState, Icon, Select } from "@/shared/ui";

export interface CapabilityCardProps {
  capability: string;
  chain: ProviderChoice[];
  descriptors: ProviderDescriptor[];
  errors: FieldErrors;
  onChange: (chain: ProviderChoice[]) => void;
}

function AddProviderSelect({
  title,
  addable,
  onAdd,
}: {
  title: string;
  addable: ProviderDescriptor[];
  onAdd: (providerId: string) => void;
}) {
  return (
    <Select
      aria-label={`Add a ${title} provider`}
      value=""
      placeholder="Add provider…"
      options={addable.map((d) => ({ value: d.provider_id, label: d.name }))}
      onChange={(e) => e.target.value && onAdd(e.target.value)}
    />
  );
}

function ChainList({
  chain,
  descriptors,
  errors,
  onChange,
}: Omit<CapabilityCardProps, "capability">) {
  if (chain.length === 0) {
    return (
      <EmptyState
        icon="providers"
        title="Using the default order"
        description="Add a provider from the menu above to choose your own order."
      />
    );
  }
  return (
    <ol className="list-stack list-stack-sm">
      {chain.map((choice, index) => (
        <ChainRow
          key={choice.provider_id}
          index={index}
          total={chain.length}
          choice={choice}
          descriptor={descriptors.find((d) => d.provider_id === choice.provider_id)}
          errors={choiceErrors(errors, index)}
          onChange={(patch) => onChange(patchChoice(chain, index, patch))}
          onMove={(delta) => onChange(moveChoice(chain, index, delta))}
          onRemove={() => onChange(removeChoice(chain, index))}
        />
      ))}
    </ol>
  );
}

function describeChain({ capability, chain, descriptors }: CapabilityCardProps): string {
  return chain.length === 0
    ? defaultOrderDescription(descriptors, capability)
    : chainDescription(activeProvider(chain, descriptors));
}

export function CapabilityCard(props: CapabilityCardProps) {
  const { capability, ...listProps } = props;
  const addable = addableProviders(props.descriptors, capability, props.chain);
  const title = humanizeId(capability);
  const add = (providerId: string) => props.onChange([...props.chain, newChoice(providerId)]);
  const problem = cardError(props.errors);
  return (
    <Card
      title={title}
      description={describeChain(props)}
      actions={
        addable.length > 0 ? (
          <AddProviderSelect title={title} addable={addable} onAdd={add} />
        ) : undefined
      }
    >
      {problem && (
        <Callout tone="danger" role="alert">
          <Icon name="alert" />
          <span>{problem}</span>
        </Callout>
      )}
      <ChainList {...listProps} />
    </Card>
  );
}
