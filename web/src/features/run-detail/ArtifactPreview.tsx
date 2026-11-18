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
  return (
    <pre className="text-preview panel-inset panel-inset-muted">
      {prettify(artifact, text.data)}
    </pre>
  );
}

interface PreviewProps {
  runId: string;
  artifact: Artifact;
  tall?: boolean;
  poster?: Artifact | undefined;
  captions?: Artifact | undefined;
}

const mediaClass = (tall: boolean) => (tall ? "media media-tall" : "media");

function VideoPreview({ runId, artifact, tall = false, poster, captions }: PreviewProps) {
  return (
    <video
      className={mediaClass(tall)}
      controls
      preload="metadata"
      src={artifactUrl(runId, artifact.id)}
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
}

function AudioPreview({ runId, artifact }: PreviewProps) {
  return (
    <audio
      className="media-audio"
      controls
      preload="none"
      src={artifactUrl(runId, artifact.id)}
      aria-label={artifact.filename}
    >
      <track kind="captions" />
    </audio>
  );
}

function ImagePreview({ runId, artifact, tall = false }: PreviewProps) {
  return (
    <img
      className={mediaClass(tall)}
      src={artifactUrl(runId, artifact.id)}
      alt={artifact.filename}
      loading="lazy"
    />
  );
}

function Media(props: PreviewProps) {
  switch (props.artifact.kind) {
    case "video":
      return <VideoPreview {...props} />;
    case "audio":
      return <AudioPreview {...props} />;
    case "image":
    case "thumbnail":
      return <ImagePreview {...props} />;
    default:
      return <TextPreview runId={props.runId} artifact={props.artifact} />;
  }
}

export function ArtifactPreview(props: PreviewProps) {
  const { runId, artifact } = props;
  return (
    <figure className={`artifact artifact-${artifact.kind}`}>
      <Media {...props} />
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
