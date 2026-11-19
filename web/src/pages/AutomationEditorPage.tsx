import { Link, useParams, useSearchParams } from "react-router";
import { useAutomation } from "@/api/automations";
import { usePipelines } from "@/api/catalog";
import { useChannels } from "@/api/channels";
import { isNotFound } from "@/api/errors";
import { PIPELINE_QUERY } from "@/api/paths";
import { useAppSettings } from "@/api/system";
import { AutomationEditor, initialDraft } from "@/features/automation-editor";
import { ButtonLink, EmptyState, ErrorState, Icon, LoadingState, PageHeader } from "@/shared/ui";

function useEditorData(id: string | undefined) {
  const automation = useAutomation(id);
  const pipelines = usePipelines();
  const channels = useChannels();
  const settings = useAppSettings();
  const queries = id === undefined ? [pipelines, channels] : [pipelines, channels, automation];
  return {
    automation,
    pipelines,
    channels,
    timezone: settings.data?.timezone,
    pending: queries.some((q) => q.isPending) || (id === undefined && settings.isPending),
    error: queries.find((q) => q.error !== null)?.error ?? null,
    retry: () => queries.forEach((q) => void q.refetch()),
  };
}

function AutomationNotFound() {
  return (
    <EmptyState
      icon="alert"
      title="Automation not found"
      description="It may have been deleted. Runs it made are still listed under Runs."
      action={
        <ButtonLink to="/automations" variant="primary">
          Back to automations
        </ButtonLink>
      }
    />
  );
}

function LoadFailure({ error, retry }: { error: Error; retry: () => void }) {
  return isNotFound(error) ? (
    <AutomationNotFound />
  ) : (
    <ErrorState message={error.message} onRetry={retry} />
  );
}

export function AutomationEditorPage() {
  const { id } = useParams();
  const [search] = useSearchParams();
  const data = useEditorData(id);
  const preferredType = search.get(PIPELINE_QUERY) ?? undefined;
  const title =
    id === undefined ? "New automation" : (data.automation.data?.name ?? "Edit automation");
  return (
    <>
      <PageHeader
        back={
          <Link to="/automations" className="back-link">
            <Icon name="left" size={14} /> Automations
          </Link>
        }
        title={title}
        description="Everything this automation does is configured here. Changes apply to the next run."
      />
      {data.pending && <LoadingState label="Loading editor" />}
      {!data.pending && data.error && <LoadFailure error={data.error} retry={data.retry} />}
      {!data.pending && !data.error && (
        <AutomationEditor
          key={id ?? "new"}
          automationId={id}
          initial={initialDraft(
            data.pipelines.data ?? [],
            data.automation.data,
            data.timezone,
            preferredType,
          )}
          pipelines={data.pipelines.data ?? []}
          channels={data.channels.data ?? []}
        />
      )}
    </>
  );
}
