import { useState } from "react";
import { errorMessage } from "@/api/errors";
import { useProviders, useSaveProviders } from "@/api/system";
import type { ProviderChoice, ProviderConfig, ProvidersResponse } from "@/api/types";
import { ChainRow } from "@/features/providers/ChainRow";
import {
  activeProvider,
  addableProviders,
  capabilitiesOf,
  capabilityTitle,
  chainFor,
  moveChoice,
  patchChoice,
  removeChoice,
  withChain,
} from "@/features/providers/chain";
import {
  Button,
  Card,
  EmptyState,
  QueryState,
  Select,
  UnsavedChangesPrompt,
  useToast,
} from "@/shared/ui";
import "@/features/providers/providers.css";

interface CapabilityProps {
  capability: string;
  chain: ProviderChoice[];
  data: ProvidersResponse;
  onChange: (chain: ProviderChoice[]) => void;
}

function CapabilityCard({ capability, chain, data, onChange }: CapabilityProps) {
  const addable = addableProviders(data.descriptors, capability, chain);
  const active = activeProvider(chain, data.descriptors);
  const title = capabilityTitle(capability);
  const add = (providerId: string) =>
    providerId && onChange([...chain, { provider_id: providerId, enabled: true, options: {} }]);
  return (
    <Card
      title={title}
      description={
        active
          ? `Runs use ${active.name}, then fall back down the list.`
          : "No available provider is enabled. Runs that need this will fail."
      }
      actions={
        addable.length > 0 ? (
          <Select
            aria-label={`Add a ${title} provider`}
            value=""
            placeholder="Add provider…"
            options={addable.map((d) => ({ value: d.provider_id, label: d.name }))}
            onChange={(e) => add(e.target.value)}
          />
        ) : undefined
      }
    >
      {chain.length === 0 ? (
        <EmptyState
          icon="providers"
          title="No providers in this chain"
          description="Add one from the menu above."
        />
      ) : (
        <ol className="chain">
          {chain.map((choice, index) => (
            <ChainRow
              key={choice.provider_id}
              index={index}
              total={chain.length}
              choice={choice}
              descriptor={data.descriptors.find((d) => d.provider_id === choice.provider_id)}
              onChange={(patch) => onChange(patchChoice(chain, index, patch))}
              onMove={(delta) => onChange(moveChoice(chain, index, delta))}
              onRemove={() => onChange(removeChoice(chain, index))}
            />
          ))}
        </ol>
      )}
    </Card>
  );
}

function ChainsEditor({ data }: { data: ProvidersResponse }) {
  const [config, setConfig] = useState<ProviderConfig[]>(data.config);
  const save = useSaveProviders();
  const toast = useToast();
  const dirty = JSON.stringify(config) !== JSON.stringify(data.config);
  const submit = () =>
    save.mutateAsync(config).then(
      () => toast.success("Provider chains saved."),
      (error: unknown) => toast.error(errorMessage(error)),
    );
  return (
    <div className="stack">
      {capabilitiesOf(data).map((capability) => (
        <CapabilityCard
          key={capability}
          capability={capability}
          chain={chainFor(config, capability)}
          data={data}
          onChange={(chain) => setConfig(withChain(config, capability, chain))}
        />
      ))}
      <div className="action-bar providers-footer">
        <span className="action-bar-status">{dirty ? "Unsaved changes" : "All changes saved"}</span>
        <Button disabled={!dirty} onClick={() => setConfig(data.config)}>
          Reset
        </Button>
        <Button
          variant="primary"
          icon="check"
          disabled={!dirty}
          loading={save.isPending}
          onClick={submit}
        >
          Save chains
        </Button>
      </div>
      <UnsavedChangesPrompt when={dirty && !save.isPending} />
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
