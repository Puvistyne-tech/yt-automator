import { AppSettingsForm } from "@/features/app-settings";
import { PageHeader } from "@/shared/ui";

export function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="App-wide preferences." />
      <AppSettingsForm />
    </>
  );
}
