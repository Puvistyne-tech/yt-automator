import { Link, useParams } from "react-router";
import { useAutomation } from "@/api/automations";
import { usePipelines } from "@/api/catalog";
import { useChannels } from "@/api/channels";
import { useAppSettings } from "@/api/system";
import { AutomationEditor, initialDraft } from "@/features/automation-editor";
import { ErrorState, Icon, LoadingState, PageHeader } from "@/shared/ui";

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

export function AutomationEditorPage() {
  const { id } = useParams();
  const data = useEditorData(id);
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
      {!data.pending && data.error && (
        <ErrorState message={data.error.message} onRetry={data.retry} />
      )}
      {!data.pending && !data.error && (
        <AutomationEditor
          key={id ?? "new"}
          automationId={id}
          initial={initialDraft(data.pipelines.data ?? [], data.automation.data, data.timezone)}
          pipelines={data.pipelines.data ?? []}
          channels={data.channels.data ?? []}
        />
      )}
    </>
  );
}
