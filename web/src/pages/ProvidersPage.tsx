import { ProviderChains } from "@/features/providers";
import { SecretsPanel } from "@/features/secrets";
import { PageHeader } from "@/shared/ui";

export function ProvidersPage() {
  return (
    <>
      <PageHeader
        title="Providers"
        description="For each capability, runs use the first available provider in the chain and fall back to the next."
      />
      <div className="providers-layout">
        <ProviderChains />
        <SecretsPanel />
      </div>
    </>
  );
}
