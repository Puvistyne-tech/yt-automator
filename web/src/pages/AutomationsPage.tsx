import { AutomationsTable } from "@/features/automation-list";
import { ButtonLink, PageHeader } from "@/shared/ui";

export function AutomationsPage() {
  return (
    <>
      <PageHeader
        title="Automations"
        description="Each automation is a pipeline with its own settings, languages, channels, schedule and review rule."
        actions={
          <ButtonLink to="/automations/new" variant="primary" icon="plus">
            New automation
          </ButtonLink>
        }
      />
      <AutomationsTable />
    </>
  );
}
