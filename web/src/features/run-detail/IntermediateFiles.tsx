import { useState } from "react";
import type { PipelineDescriptor } from "@/api/types";
import { ArtifactGrid } from "@/features/run-detail/ArtifactGrid";
import type { StageFiles } from "@/features/run-detail/artifacts";
import { pluralize } from "@/shared/format/text";

interface StageFilesProps {
  runId: string;
  stage: StageFiles;
  pipeline: PipelineDescriptor | undefined;
}

function StageFilesGroup({ runId, stage, pipeline }: StageFilesProps) {
  const [open, setOpen] = useState(false);
  return (
    <details className="artifact-stage" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="artifact-stage-summary">
        <span>{stage.title}</span>
        <span className="subtle">{pluralize(stage.artifacts.length, "file")}</span>
      </summary>
      {open && (
        <div className="artifact-stage-body">
          <ArtifactGrid runId={runId} artifacts={stage.artifacts} pipeline={pipeline} />
        </div>
      )}
    </details>
  );
}

interface IntermediateFilesProps {
  runId: string;
  stages: StageFiles[];
  pipeline: PipelineDescriptor | undefined;
}

export function IntermediateFiles({ runId, stages, pipeline }: IntermediateFilesProps) {
  return (
    <section className="artifact-section" aria-label="Intermediate files">
      <h3 className="artifact-section-title">Intermediate files</h3>
      <p className="subtle">Working files each stage made on the way. Open a stage to see them.</p>
      <div className="artifact-stages">
        {stages.map((stage) => (
          <StageFilesGroup key={stage.stageId} runId={runId} stage={stage} pipeline={pipeline} />
        ))}
      </div>
    </section>
  );
}
