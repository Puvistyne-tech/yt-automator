import { Link, useParams } from "react-router";
import { isNotFound } from "@/api/errors";
import { useTemplate, useTemplateEngines } from "@/api/templates";
import type { EngineSummary, TemplateSummary } from "@/api/types";
import {
  BuiltinTemplateView,
  NewTemplateEditor,
  SavedTemplateEditor,
} from "@/features/pipeline-templates";
import {
  AlertCallout,
  ButtonLink,
  EmptyState,
  ErrorState,
  Icon,
  LoadingState,
  PageHeader,
} from "@/shared/ui";

function PipelineNotFound() {
  return (
    <EmptyState
      icon="alert"
      title="Pipeline not found"
      description="It may have been deleted. Automations that used it keep their settings."
      action={
        <ButtonLink to="/pipelines" variant="primary">
          Back to pipelines
        </ButtonLink>
      }
    />
  );
}

function MissingEngine() {
  return (
    <AlertCallout tone="warning">
      The template this pipeline is built from is not installed, so it cannot be shown.
    </AlertCallout>
  );
}

function TemplateView({
  engines,
  template,
}: {
  engines: EngineSummary[];
  template: TemplateSummary;
}) {
  const engine = engines.find((e) => e.engine_id === template.engine);
  if (engine === undefined) {
    return <MissingEngine />;
  }
  return template.builtin ? (
    <BuiltinTemplateView engine={engine} template={template} />
  ) : (
    <SavedTemplateEditor key={template.id} engine={engine} template={template} />
  );
}

function PipelineContent({ id, engines }: { id: string | undefined; engines: EngineSummary[] }) {
  const template = useTemplate(id);
  const [engine] = engines;
  if (id === undefined) {
    return engine === undefined ? <MissingEngine /> : <NewTemplateEditor engine={engine} />;
  }
  if (template.isPending) {
    return <LoadingState label="Loading pipeline" />;
  }
  if (template.error !== null) {
    return isNotFound(template.error) ? (
      <PipelineNotFound />
    ) : (
      <ErrorState message={template.error.message} onRetry={() => void template.refetch()} />
    );
  }
  return <TemplateView engines={engines} template={template.data} />;
}

export function PipelineEditorPage() {
  const { id } = useParams();
  const engines = useTemplateEngines();
  const template = useTemplate(id);
  const title = id === undefined ? "New pipeline" : (template.data?.name ?? "Pipeline");
  return (
    <>
      <PageHeader
        back={
          <Link to="/pipelines" className="back-link">
            <Icon name="left" size={14} /> Pipelines
          </Link>
        }
        title={title}
        description="A pipeline sets what the videos are about and how they look and sound."
      />
      {engines.isPending && <LoadingState label="Loading pipeline" />}
      {engines.error !== null && (
        <ErrorState message={engines.error.message} onRetry={() => void engines.refetch()} />
      )}
      {engines.data !== undefined && <PipelineContent id={id} engines={engines.data} />}
    </>
  );
}
