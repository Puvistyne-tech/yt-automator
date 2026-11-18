import { useState } from "react";
import { useProviders, useSaveProviders } from "@/api/system";
import type {
  ProviderChoice,
  ProviderConfig,
  ProviderDescriptor,
  ProvidersResponse,
} from "@/api/types";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { ChainRow } from "@/features/providers/ChainRow";
import {
  activeProvider,
  addableProviders,
  capabilitiesOf,
  chainChanged,
  chainDescription,
  chainFor,
  moveChoice,
  newChoice,
  patchChoice,
  removeChoice,
  withChain,
} from "@/features/providers/chain";
import { humanizeId } from "@/shared/format/text";
import { Card, EmptyState, QueryState, SaveBar, Select } from "@/shared/ui";
import "@/features/providers/providers.css";

interface ChainProps {
  chain: ProviderChoice[];
  descriptors: ProviderDescriptor[];
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

function ChainList({ chain, descriptors, onChange }: ChainProps) {
  if (chain.length === 0) {
    return (
      <EmptyState
        icon="providers"
        title="No providers in this chain"
        description="Add one from the menu above."
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
          onChange={(patch) => onChange(patchChoice(chain, index, patch))}
          onMove={(delta) => onChange(moveChoice(chain, index, delta))}
          onRemove={() => onChange(removeChoice(chain, index))}
        />
      ))}
    </ol>
  );
}

function CapabilityCard({ capability, ...props }: ChainProps & { capability: string }) {
  const addable = addableProviders(props.descriptors, capability, props.chain);
  const title = humanizeId(capability);
  const add = (providerId: string) => props.onChange([...props.chain, newChoice(providerId)]);
  return (
    <Card
      title={title}
      description={chainDescription(activeProvider(props.chain, props.descriptors))}
      actions={
        addable.length > 0 ? (
          <AddProviderSelect title={title} addable={addable} onAdd={add} />
        ) : undefined
      }
    >
      <ChainList {...props} />
    </Card>
  );
}

function ChainsEditor({ data }: { data: ProvidersResponse }) {
  const [config, setConfig] = useState<ProviderConfig[]>(data.config);
  const save = useSaveProviders();
  const notifier = useMutationNotifier();
  const dirty = chainChanged(config, data.config);
  const submit = () =>
    notifier.track(save.mutateAsync(config), { success: "Provider chains saved." });
  return (
    <div className="stack">
      {capabilitiesOf(data).map((capability) => (
        <CapabilityCard
          key={capability}
          capability={capability}
          chain={chainFor(config, capability)}
          descriptors={data.descriptors}
          onChange={(chain) => setConfig(withChain(config, capability, chain))}
        />
      ))}
      <SaveBar
        dirty={dirty}
        saving={save.isPending}
        saveLabel="Save chains"
        onSave={submit}
        onReset={() => setConfig(data.config)}
      />
    </div>
  );
}

export function ProviderChains() {
  const providers = useProviders();
  return (
    <QueryState query={providers} loadingLabel="Loading providers">
      {(data) => <ChainsEditor key={JSON.stringify(data.config)} data={data} />}
    </QueryState>
  );
}
