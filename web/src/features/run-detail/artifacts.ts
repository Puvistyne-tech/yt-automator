import type { Artifact, PipelineDescriptor, Run } from "@/api/types";
import { isFinalOutput } from "@/shared/artifacts";

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

export interface StageFiles {
  stageId: string;
  title: string;
  artifacts: Artifact[];
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

export function groupArtifacts(
  run: Run,
  pipeline?: PipelineDescriptor,
  artifacts: Artifact[] = run.artifacts,
): ArtifactGroup[] {
  const groups = new Map<string, ArtifactGroup>();
  for (const artifact of artifacts) {
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

export function splitArtifacts(artifacts: Artifact[]): GroupParts {
  return {
    media: artifacts.filter((a) => MEDIA_KINDS.has(a.kind)),
    documents: artifacts.filter((a) => !MEDIA_KINDS.has(a.kind)),
    captions: artifacts.find((a) => a.kind === "subtitle"),
    poster: artifacts.find((a) => a.kind === "thumbnail"),
  };
}

export function finalOutputs(run: Run): Artifact[] {
  return run.artifacts.filter(isFinalOutput);
}

export function intermediateByStage(run: Run): StageFiles[] {
  const intermediate = run.artifacts.filter((a) => !isFinalOutput(a));
  const order = run.stages.map((s) => s.stage_id);
  const stageIds = [...new Set(intermediate.map((a) => a.stage_id))].sort(
    (a, b) => orderOf(order, a) - orderOf(order, b),
  );
  return stageIds.map((stageId) => ({
    stageId,
    title: run.stages.find((s) => s.stage_id === stageId)?.title ?? stageId,
    artifacts: intermediate.filter((a) => a.stage_id === stageId),
  }));
}

export function isTallArtifact(artifact: Artifact, pipeline?: PipelineDescriptor): boolean {
  const aspect = pipeline?.variants.find((v) => v.id === artifact.variant)?.aspect;
  if (aspect !== undefined) {
    return aspect === "9:16";
  }
  return Number(artifact.meta.height) > Number(artifact.meta.width);
}
