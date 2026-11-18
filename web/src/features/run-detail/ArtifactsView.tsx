import type { PipelineDescriptor, Run } from "@/api/types";
import { ArtifactGrid } from "@/features/run-detail/ArtifactGrid";
import {
  type ArtifactGroup,
  finalOutputs,
  groupArtifacts,
  intermediateByStage,
} from "@/features/run-detail/artifacts";
import { IntermediateFiles } from "@/features/run-detail/IntermediateFiles";
import { EmptyState } from "@/shared/ui";
import "@/features/run-detail/artifacts.css";

interface ViewProps {
  run: Run;
  pipeline: PipelineDescriptor | undefined;
}

function Group({ run, group, pipeline }: ViewProps & { group: ArtifactGroup }) {
  return (
    <section className="artifact-group" aria-label={group.title}>
      <h4 className="artifact-group-title">{group.title}</h4>
      <ArtifactGrid runId={run.id} artifacts={group.artifacts} pipeline={pipeline} />
    </section>
  );
}

function FinalOutputs({ run, pipeline }: ViewProps) {
  const groups = groupArtifacts(run, pipeline, finalOutputs(run));
  return (
    <section className="artifact-section" aria-label="Final outputs">
      <h3 className="artifact-section-title">Final outputs</h3>
      {groups.length === 0 ? (
        <p className="subtle">No videos, thumbnails, captions or metadata yet.</p>
      ) : (
        <div className="stack artifact-groups divided-list">
          {groups.map((group) => (
            <Group key={group.key} run={run} group={group} pipeline={pipeline} />
          ))}
        </div>
      )}
    </section>
  );
}

export function ArtifactsView({ run, pipeline }: ViewProps) {
  if (run.artifacts.length === 0) {
    return (
      <EmptyState
        icon="film"
        title="No artifacts yet"
        description="Files appear here as each stage finishes."
      />
    );
  }
  const stages = intermediateByStage(run);
  return (
    <div className="stack artifact-sections">
      <FinalOutputs run={run} pipeline={pipeline} />
      {stages.length > 0 && (
        <IntermediateFiles runId={run.id} stages={stages} pipeline={pipeline} />
      )}
    </div>
  );
}
