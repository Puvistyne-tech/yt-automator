import type { Artifact, PipelineDescriptor, Run, RunStatus, ScoreItem, Upload } from "@/api/types";

export interface RunActions {
  canCancel: boolean;
  canRetry: boolean;
  canReview: boolean;
  canPublish: boolean;
  canDelete: boolean;
}

const ACTIVE: RunStatus[] = ["queued", "running", "publishing"];

export function availableActions(run: Run): RunActions {
  const active = ACTIVE.includes(run.status);
  return {
    canCancel: run.status === "queued" || run.status === "running",
    canRetry: !active,
    canReview: run.status === "awaiting_review",
    canPublish: run.status === "approved",
    canDelete: !active,
  };
}

export function retryStageOptions(run: Run): { value: string; label: string }[] {
  return run.stages.map((stage, index) => ({
    value: stage.stage_id,
    label: `${index + 1}. ${stage.title}`,
  }));
}

export function defaultRetryStage(run: Run): string {
  return (run.stages.find((s) => s.status === "failed") ?? run.stages[0])?.stage_id ?? "";
}

export interface ArtifactGroup {
  key: string;
  language: string | null;
  variant: string | null;
  title: string;
  artifacts: Artifact[];
}

function groupTitle(
  language: string | null,
  variant: string | null,
  pipeline?: PipelineDescriptor,
): string {
  if (language === null && variant === null) {
    return "Shared across languages";
  }
  const languageName =
    language === null
      ? "All languages"
      : (pipeline?.languages.find((l) => l.code === language)?.name ?? language);
  const v = pipeline?.variants.find((item) => item.id === variant);
  const variantName = variant === null ? "All outputs" : v ? `${v.name} · ${v.aspect}` : variant;
  return `${languageName} — ${variantName}`;
}

function orderOf(list: string[], value: string | null): number {
  const index = value === null ? -1 : list.indexOf(value);
  return value === null ? -1 : index === -1 ? list.length : index;
}

export function groupArtifacts(run: Run, pipeline?: PipelineDescriptor): ArtifactGroup[] {
  const groups = new Map<string, ArtifactGroup>();
  for (const artifact of run.artifacts) {
    const key = `${artifact.language ?? "*"}|${artifact.variant ?? "*"}`;
    const group = groups.get(key) ?? {
      key,
      language: artifact.language,
      variant: artifact.variant,
      title: groupTitle(artifact.language, artifact.variant, pipeline),
      artifacts: [],
    };
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

export function weightedScore(items: ScoreItem[]): number | null {
  const total = items.reduce((sum, item) => sum + item.weight, 0);
  if (items.length === 0 || total <= 0) {
    return null;
  }
  return items.reduce((sum, item) => sum + item.score * item.weight, 0) / total;
}

export function uploadSummary(uploads: Upload[]): Record<"done" | "failed" | "pending", number> {
  return {
    done: uploads.filter((u) => u.status === "done").length,
    failed: uploads.filter((u) => u.status === "failed").length,
    pending: uploads.filter((u) => u.status === "pending" || u.status === "uploading").length,
  };
}

export function stageProgress(run: Run): { done: number; total: number } {
  const done = run.stages.filter((s) => s.status === "done" || s.status === "skipped").length;
  return { done, total: run.stages.length };
}
