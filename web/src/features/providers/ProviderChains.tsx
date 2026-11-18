import { useState } from "react";
import { useProviders, useSaveProviders } from "@/api/system";
import type { ProviderConfig, ProvidersResponse } from "@/api/types";
import { useFieldErrors } from "@/api/useFieldErrors";
import { useMutationNotifier } from "@/api/useMutationNotifier";
import { CapabilityCard } from "@/features/providers/CapabilityCard";
import {
  capabilitiesOf,
  chainChanged,
  chainFor,
  configErrors,
  withChain,
} from "@/features/providers/chain";
import { QueryState, SaveBar } from "@/shared/ui";
import "@/features/providers/providers.css";

function ChainsEditor({ data }: { data: ProvidersResponse }) {
  const [config, setConfig] = useState<ProviderConfig[]>(data.config);
  const serverErrors = useFieldErrors();
  const save = useSaveProviders();
  const notifier = useMutationNotifier();
  const dirty = chainChanged(config, data.config);
  const edit = (next: ProviderConfig[]) => {
    setConfig(next);
    serverErrors.clear();
  };
  const submit = () =>
    notifier.track(save.mutateAsync(config), {
      success: "Provider chains saved.",
      onError: serverErrors.setFromServer,
    });
  return (
    <div className="stack">
      {capabilitiesOf(data).map((capability) => (
        <CapabilityCard
          key={capability}
          capability={capability}
          chain={chainFor(config, capability)}
          descriptors={data.descriptors}
          errors={configErrors(serverErrors.errors, config, capability)}
          onChange={(chain) => edit(withChain(config, capability, chain))}
        />
      ))}
      <SaveBar
        dirty={dirty}
        saving={save.isPending}
        saveLabel="Save chains"
        onSave={submit}
        onReset={() => edit(data.config)}
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
