import type { Artifact, PipelineDescriptor } from "@/api/types";
import { ArtifactPreview } from "@/features/run-detail/ArtifactPreview";
import { isTallArtifact, splitArtifacts } from "@/features/run-detail/artifacts";

interface ArtifactGridProps {
  runId: string;
  artifacts: Artifact[];
  pipeline: PipelineDescriptor | undefined;
}

export function ArtifactGrid({ runId, artifacts, pipeline }: ArtifactGridProps) {
  const { media, documents, captions, poster } = splitArtifacts(artifacts);
  return (
    <>
      {media.length > 0 && (
        <div className="artifact-media-grid">
          {media.map((artifact) => (
            <ArtifactPreview
              key={artifact.id}
              runId={runId}
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
            <ArtifactPreview key={artifact.id} runId={runId} artifact={artifact} />
          ))}
        </div>
      )}
    </>
  );
}
