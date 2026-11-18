import { makeArtifact } from "@/api/mocks/fixtures/factories";
import { kidsStoryPipeline } from "@/api/mocks/fixtures/pipeline";
import type { Artifact, ArtifactKind } from "@/api/types";

const WIDE = { size_bytes: 48_000_000, meta: { duration_seconds: 312, width: 1920, height: 1080 } };
const TALL = { size_bytes: 9_400_000, meta: { duration_seconds: 58, width: 1080, height: 1920 } };

function isTallVariant(variant: string): boolean {
  return kidsStoryPipeline.variants.find((v) => v.id === variant)?.aspect === "9:16";
}

function frameOf(variant: string) {
  return isTallVariant(variant) ? TALL : WIDE;
}

function videoArtifact(language: string, variant: string): Artifact {
  return makeArtifact({
    id: `art-video-${language}-${variant}`,
    language,
    variant,
    filename: `${variant}-${language}.mp4`,
    ...frameOf(variant),
  });
}

function thumbnailArtifact(language: string, variant: string): Artifact {
  const { width, height } = frameOf(variant).meta;
  return makeArtifact({
    id: `art-thumb-${language}-${variant}`,
    kind: "thumbnail",
    language,
    variant,
    filename: `thumb-${language}-${variant}.svg`,
    media_type: "image/svg+xml",
    size_bytes: 180_000,
    meta: { width, height },
  });
}

interface DocumentSpec {
  kind: ArtifactKind;
  prefix: string;
  extension: string;
  media_type: string;
  size_bytes: number;
}

const SUBTITLES: DocumentSpec = {
  kind: "subtitle",
  prefix: "subs",
  extension: "vtt",
  media_type: "text/vtt",
  size_bytes: 4_200,
};

const METADATA: DocumentSpec = {
  kind: "metadata",
  prefix: "meta",
  extension: "json",
  media_type: "application/json",
  size_bytes: 1_100,
};

function documentArtifact(spec: DocumentSpec, language: string, variant: string): Artifact {
  return makeArtifact({
    id: `art-${spec.prefix}-${language}-${variant}`,
    kind: spec.kind,
    language,
    variant,
    filename: `${language}-${variant}.${spec.extension}`,
    media_type: spec.media_type,
    size_bytes: spec.size_bytes,
    meta: {},
  });
}

export function artifactsFor(language: string, variant: string): Artifact[] {
  return [
    videoArtifact(language, variant),
    thumbnailArtifact(language, variant),
    documentArtifact(SUBTITLES, language, variant),
    documentArtifact(METADATA, language, variant),
  ];
}

export const STORY_ARTIFACT = makeArtifact({
  id: "art-story",
  kind: "text",
  stage_id: "story",
  language: null,
  variant: null,
  filename: "story.md",
  media_type: "text/markdown",
  size_bytes: 6_400,
  meta: {},
});

export const FULL_ARTIFACTS: Artifact[] = [
  STORY_ARTIFACT,
  ...artifactsFor("en", "episode"),
  ...artifactsFor("en", "short"),
  ...artifactsFor("ta", "episode"),
  ...artifactsFor("ta", "short"),
];
