import { DashboardOverview } from "@/features/dashboard";
import { ButtonLink, PageHeader } from "@/shared/ui";

export function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="What is running, what needs your review and how much upload quota is left today."
        actions={
          <ButtonLink to="/automations/new" variant="primary" icon="plus">
            New automation
          </ButtonLink>
        }
      />
      <DashboardOverview />
    </>
  );
}
