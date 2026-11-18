import type { Artifact, PipelineDescriptor, Run } from "@/api/types";
import { ArtifactPreview } from "@/features/run-detail/ArtifactPreview";
import { type ArtifactGroup, groupArtifacts, posterFor } from "@/features/run-detail/model";
import { EmptyState } from "@/shared/ui";

const MEDIA_KINDS = new Set<Artifact["kind"]>(["video", "thumbnail", "image", "audio"]);

function Group({ run, group }: { run: Run; group: ArtifactGroup }) {
  const poster = posterFor(group);
  const captions = group.artifacts.find((a) => a.kind === "subtitle");
  const media = group.artifacts.filter((a) => MEDIA_KINDS.has(a.kind));
  const documents = group.artifacts.filter((a) => !MEDIA_KINDS.has(a.kind));
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
    <div className="stack artifact-groups">
      {groups.map((group) => (
        <Group key={group.key} run={run} group={group} />
      ))}
    </div>
  );
}
