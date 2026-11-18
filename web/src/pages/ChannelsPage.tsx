import { ChannelsPanel, CredentialsPanel, useOAuthReturn } from "@/features/channels";
import { PageHeader } from "@/shared/ui";

export function ChannelsPage() {
  useOAuthReturn();
  return (
    <>
      <PageHeader
        title="Channels"
        description="Google API credentials, the YouTube channels connected through them and each channel's upload defaults."
      />
      <div className="stack">
        <CredentialsPanel />
        <ChannelsPanel />
      </div>
    </>
  );
}
