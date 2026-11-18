import { artifactUrl, useArtifactText } from "@/api/runs";
import type { Artifact } from "@/api/types";
import { formatBytes } from "@/shared/format/numbers";
import { Badge, Icon, Spinner } from "@/shared/ui";

function prettify(artifact: Artifact, text: string): string {
  if (artifact.kind !== "metadata") {
    return text;
  }
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

function TextPreview({ runId, artifact }: { runId: string; artifact: Artifact }) {
  const text = useArtifactText(runId, artifact.id);
  if (text.isPending) {
    return <Spinner label={`Loading ${artifact.filename}`} />;
  }
  if (text.isError) {
    return <p className="field-error">Could not load {artifact.filename}.</p>;
  }
  return <pre className="text-preview">{prettify(artifact, text.data)}</pre>;
}

interface PreviewProps {
  runId: string;
  artifact: Artifact;
  poster?: Artifact | undefined;
  captions?: Artifact | undefined;
}

function Media({ runId, artifact, poster, captions }: PreviewProps) {
  const src = artifactUrl(runId, artifact.id);
  const tall =
    artifact.variant === "short" || Number(artifact.meta.height) > Number(artifact.meta.width);
  switch (artifact.kind) {
    case "video":
      return (
        <video
          className={tall ? "media media-tall" : "media"}
          controls
          preload="metadata"
          src={src}
          poster={poster ? artifactUrl(runId, poster.id) : undefined}
          aria-label={artifact.filename}
        >
          <track
            kind="captions"
            src={captions ? artifactUrl(runId, captions.id) : undefined}
            srcLang={captions?.language ?? undefined}
            label={captions ? (captions.language ?? "subtitles").toUpperCase() : undefined}
          />
        </video>
      );
    case "audio":
      return (
        <audio
          className="media-audio"
          controls
          preload="none"
          src={src}
          aria-label={artifact.filename}
        >
          <track kind="captions" />
        </audio>
      );
    case "image":
    case "thumbnail":
      return (
        <img
          className={tall ? "media media-tall" : "media"}
          src={src}
          alt={artifact.filename}
          loading="lazy"
        />
      );
    default:
      return <TextPreview runId={runId} artifact={artifact} />;
  }
}

export function ArtifactPreview({ runId, artifact, poster, captions }: PreviewProps) {
  return (
    <figure className={`artifact artifact-${artifact.kind}`}>
      <Media runId={runId} artifact={artifact} poster={poster} captions={captions} />
      <figcaption className="artifact-caption">
        <Badge>{artifact.kind}</Badge>
        <span className="artifact-name">{artifact.filename}</span>
        <span className="subtle">{formatBytes(artifact.size_bytes)}</span>
        <a
          className="artifact-open"
          href={artifactUrl(runId, artifact.id)}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open ${artifact.filename}`}
        >
          <Icon name="external" />
        </a>
      </figcaption>
    </figure>
  );
}
