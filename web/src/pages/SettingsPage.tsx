import { AppSettingsForm } from "@/features/app-settings";
import { StorageUsage } from "@/features/storage";
import { PageHeader } from "@/shared/ui";

export function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="App-wide preferences, storage and diagnostics." />
      <AppSettingsForm storageUsage={<StorageUsage />} />
    </>
  );
}
