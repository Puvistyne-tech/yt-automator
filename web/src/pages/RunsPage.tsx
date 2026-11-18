import { RunsList } from "@/features/runs-list";
import { PageHeader } from "@/shared/ui";

export function RunsPage() {
  return (
    <>
      <PageHeader title="Runs" description="Every execution of every automation, newest first." />
      <RunsList />
    </>
  );
}
