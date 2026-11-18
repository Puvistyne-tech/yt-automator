import type { Artifact, PipelineDescriptor, Run } from "@/api/types";

export interface ArtifactGroup {
  key: string;
  language: string | null;
  variant: string | null;
  title: string;
  artifacts: Artifact[];
}

export interface GroupParts {
  media: Artifact[];
  documents: Artifact[];
  captions: Artifact | undefined;
  poster: Artifact | undefined;
}

const MEDIA_KINDS = new Set<Artifact["kind"]>(["video", "thumbnail", "image", "audio"]);

function languageTitle(language: string | null, pipeline?: PipelineDescriptor): string {
  if (language === null) {
    return "All languages";
  }
  return pipeline?.languages.find((l) => l.code === language)?.name ?? language;
}

function variantTitle(variant: string | null, pipeline?: PipelineDescriptor): string {
  if (variant === null) {
    return "All outputs";
  }
  const option = pipeline?.variants.find((item) => item.id === variant);
  return option ? `${option.name} · ${option.aspect}` : variant;
}

function groupTitle(
  language: string | null,
  variant: string | null,
  pipeline?: PipelineDescriptor,
): string {
  if (language === null && variant === null) {
    return "Shared across languages";
  }
  return `${languageTitle(language, pipeline)} — ${variantTitle(variant, pipeline)}`;
}

function orderOf(list: string[], value: string | null): number {
  if (value === null) {
    return -1;
  }
  const index = list.indexOf(value);
  return index === -1 ? list.length : index;
}

function newGroup(key: string, artifact: Artifact, pipeline?: PipelineDescriptor): ArtifactGroup {
  return {
    key,
    language: artifact.language,
    variant: artifact.variant,
    title: groupTitle(artifact.language, artifact.variant, pipeline),
    artifacts: [],
  };
}

export function groupArtifacts(run: Run, pipeline?: PipelineDescriptor): ArtifactGroup[] {
  const groups = new Map<string, ArtifactGroup>();
  for (const artifact of run.artifacts) {
    const key = `${artifact.language ?? "*"}|${artifact.variant ?? "*"}`;
    const group = groups.get(key) ?? newGroup(key, artifact, pipeline);
    group.artifacts.push(artifact);
    groups.set(key, group);
  }
  const variants = pipeline?.variants.map((v) => v.id) ?? [];
  return [...groups.values()].sort(
    (a, b) =>
      orderOf(run.languages, a.language) - orderOf(run.languages, b.language) ||
      orderOf(variants, a.variant) - orderOf(variants, b.variant),
  );
}

export function posterFor(group: ArtifactGroup): Artifact | undefined {
  return group.artifacts.find((a) => a.kind === "thumbnail");
}

export function splitGroup(group: ArtifactGroup): GroupParts {
  return {
    media: group.artifacts.filter((a) => MEDIA_KINDS.has(a.kind)),
    documents: group.artifacts.filter((a) => !MEDIA_KINDS.has(a.kind)),
    captions: group.artifacts.find((a) => a.kind === "subtitle"),
    poster: posterFor(group),
  };
}

export function isTallArtifact(artifact: Artifact, pipeline?: PipelineDescriptor): boolean {
  const aspect = pipeline?.variants.find((v) => v.id === artifact.variant)?.aspect;
  if (aspect !== undefined) {
    return aspect === "9:16";
  }
  return Number(artifact.meta.height) > Number(artifact.meta.width);
}
