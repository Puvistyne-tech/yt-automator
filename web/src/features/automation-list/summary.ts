import type { Automation, Channel, PipelineDescriptor } from "@/api/types";
import { formatRelative } from "@/shared/format/dates";

export function pipelineName(pipelines: PipelineDescriptor[], typeId: string): string {
  return pipelines.find((p) => p.type_id === typeId)?.name ?? typeId;
}

export function languagesLabel(codes: string[], pipeline: PipelineDescriptor | undefined): string {
  if (codes.length === 0) {
    return "—";
  }
  return codes
    .map((code) => pipeline?.languages.find((l) => l.code === code)?.name ?? code)
    .join(", ");
}

export function targetsLabel(automation: Automation, channels: Channel[]): string {
  const titles = automation.targets.map(
    (target) => channels.find((c) => c.id === target.channel_id)?.title ?? "Unknown channel",
  );
  const unique = [...new Set(titles)];
  if (unique.length === 0) {
    return "No targets";
  }
  return unique.length <= 2
    ? unique.join(", ")
    : `${unique.slice(0, 2).join(", ")} +${unique.length - 2}`;
}

export function sortAutomations(automations: Automation[]): Automation[] {
  return [...automations].sort(
    (a, b) => Number(b.enabled) - Number(a.enabled) || a.name.localeCompare(b.name),
  );
}

export function nextRunLabel(automation: Automation): string {
  return automation.enabled ? `Next ${formatRelative(automation.next_run_at)}` : "Paused";
}
