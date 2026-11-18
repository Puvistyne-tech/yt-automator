import type { PipelineDescriptor, Run } from "@/api/types";
import { ArtifactPreview } from "@/features/run-detail/ArtifactPreview";
import {
  type ArtifactGroup,
  groupArtifacts,
  isTallArtifact,
  splitGroup,
} from "@/features/run-detail/artifacts";
import { EmptyState } from "@/shared/ui";

interface GroupProps {
  run: Run;
  group: ArtifactGroup;
  pipeline: PipelineDescriptor | undefined;
}

function Group({ run, group, pipeline }: GroupProps) {
  const { media, documents, captions, poster } = splitGroup(group);
  return (
    <section className="artifact-group" aria-label={group.title}>
      <h3 className="artifact-group-title">{group.title}</h3>
      {media.length > 0 && (
        <div className="artifact-media-grid">
          {media.map((artifact) => (
            <ArtifactPreview
              key={artifact.id}
              runId={run.id}
              artifact={artifact}
              tall={isTallArtifact(artifact, pipeline)}
              poster={artifact.kind === "video" ? poster : undefined}
              captions={captions}
            />
          ))}
        </div>
      )}
      {documents.length > 0 && (
        <div className="artifact-doc-grid">
          {documents.map((artifact) => (
            <ArtifactPreview key={artifact.id} runId={run.id} artifact={artifact} />
          ))}
        </div>
      )}
    </section>
  );
}

export function ArtifactsView({
  run,
  pipeline,
}: {
  run: Run;
  pipeline: PipelineDescriptor | undefined;
}) {
  const groups = groupArtifacts(run, pipeline);
  if (groups.length === 0) {
    return (
      <EmptyState
        icon="film"
        title="No artifacts yet"
        description="Files appear here as each stage finishes."
      />
    );
  }
  return (
    <div className="stack artifact-groups divided-list">
      {groups.map((group) => (
        <Group key={group.key} run={run} group={group} pipeline={pipeline} />
      ))}
    </div>
  );
}
