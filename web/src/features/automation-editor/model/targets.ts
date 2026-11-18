import { CHANNEL_STATUSES, PRIVACY_LABELS, PRIVACY_OPTIONS } from "@/api/labels";
import type { Channel, PipelineDescriptor } from "@/api/types";
import {
  type AutomationDraft,
  isKidsPipeline,
  type TargetDraft,
} from "@/features/automation-editor/model/draft";
import type { CheckboxOption, SelectOption } from "@/shared/ui";

export interface TargetOptions {
  channels: SelectOption[];
  languages: SelectOption[];
  variants: CheckboxOption[];
  kidsLocked: boolean;
  addBlockedReason: string | null;
}

export function languageName(pipeline: PipelineDescriptor | undefined, code: string): string {
  return pipeline?.languages.find((l) => l.code === code)?.name ?? code;
}

function channelOption(channel: Channel): SelectOption {
  const suffix =
    channel.status === "connected" ? "" : ` (${CHANNEL_STATUSES[channel.status].label})`;
  return { value: channel.id, label: `${channel.title}${suffix}` };
}

function addBlockedReason(draft: AutomationDraft, channels: Channel[]): string | null {
  if (channels.length === 0) {
    return "Connect a YouTube channel first.";
  }
  if (draft.languages.length === 0) {
    return "Choose at least one language first.";
  }
  return null;
}

export function targetOptions(
  pipeline: PipelineDescriptor,
  draft: AutomationDraft,
  channels: Channel[],
): TargetOptions {
  return {
    channels: channels.map(channelOption),
    languages: pipeline.languages
      .filter((language) => draft.languages.includes(language.code))
      .map((language) => ({ value: language.code, label: language.name })),
    variants: pipeline.variants.map((variant) => ({
      value: variant.id,
      label: `${variant.name} · ${variant.aspect}`,
      description: variant.description,
    })),
    kidsLocked: isKidsPipeline(pipeline),
    addBlockedReason: addBlockedReason(draft, channels),
  };
}

export function languageOptionsWithOrphan(
  options: SelectOption[],
  target: TargetDraft,
  pipeline: PipelineDescriptor,
): SelectOption[] {
  if (target.language === "" || options.some((o) => o.value === target.language)) {
    return options;
  }
  return [
    ...options,
    { value: target.language, label: `${languageName(pipeline, target.language)} (not selected)` },
  ];
}

export function orphanTargets(targets: TargetDraft[], languages: string[]): TargetDraft[] {
  return targets.filter((target) => target.language !== "" && !languages.includes(target.language));
}

export function withoutOrphanTargets(draft: AutomationDraft): AutomationDraft {
  const orphans = new Set(orphanTargets(draft.targets, draft.languages).map((t) => t.key));
  return { ...draft, targets: draft.targets.filter((target) => !orphans.has(target.key)) };
}

export function updateTarget(
  draft: AutomationDraft,
  key: string,
  patch: Partial<TargetDraft>,
): AutomationDraft {
  return {
    ...draft,
    targets: draft.targets.map((target) => {
      if (target.key !== key) {
        return target;
      }
      const channelChanged =
        patch.channel_id !== undefined && patch.channel_id !== target.channel_id;
      return { ...target, ...patch, ...(channelChanged ? { playlist_id: null } : {}) };
    }),
  };
}

export type KidsChoice = "default" | "yes" | "no";

export const KIDS_CHOICES: { value: KidsChoice; label: string }[] = [
  { value: "default", label: "Channel default" },
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

export function kidsValue(value: boolean | null): KidsChoice {
  if (value === null) {
    return "default";
  }
  return value ? "yes" : "no";
}

export function kidsFromValue(value: string): boolean | null {
  return value === "default" ? null : value === "yes";
}

export function privacyOptions(channel: Channel | undefined): SelectOption[] {
  const fallback = channel ? ` (${PRIVACY_LABELS[channel.defaults.privacy]})` : "";
  return [{ value: "", label: `Channel default${fallback}` }, ...PRIVACY_OPTIONS];
}
