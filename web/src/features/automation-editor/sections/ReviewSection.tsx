import type { Channel, ReviewMode, ReviewPolicy } from "@/api/types";
import { withRejectBelow } from "@/features/automation-editor/model/reviewRules";
import { automationSummary } from "@/features/automation-editor/model/summary";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { RulesSummary, ToggleField } from "@/features/automation-editor/sections/ToggleField";
import { FormField, NumberInput, RadioCards } from "@/shared/ui";

const MODES = [
  {
    value: "always" as const,
    label: "Always review",
    description: "Every run waits for your approval before publishing.",
  },
  {
    value: "auto_when_score_at_least" as const,
    label: "Auto-approve good runs",
    description: "Approve automatically when the quality score is high enough.",
  },
];

interface PolicyFieldsProps {
  policy: ReviewPolicy;
  errors: Record<string, string>;
  set: (policy: ReviewPolicy) => void;
}

function MinScoreField({ policy, errors, set }: PolicyFieldsProps) {
  return (
    <FormField
      label="Minimum score"
      required
      hint="Runs scoring below this still wait for review."
      error={errors["review_policy.min_score"]}
    >
      <NumberInput
        min={0}
        max={100}
        step={1}
        value={policy.min_score}
        onValueChange={(min_score) => set({ ...policy, min_score })}
      />
    </FormField>
  );
}

function RejectField({ policy, errors, set }: PolicyFieldsProps) {
  return (
    <ToggleField
      label="Reject low scores automatically"
      hint="A run scoring under this is rejected on its own. The reason is saved in the run log and shown on the run page."
      checked={policy.reject_below !== null}
      onChange={(on) => set(withRejectBelow(policy, on))}
    >
      <FormField
        label="Reject below score"
        required
        hint="0 to 100. With auto-approve on, keep it below the minimum score."
        error={errors["review_policy.reject_below"]}
      >
        <NumberInput
          min={0}
          max={100}
          step={1}
          value={policy.reject_below}
          onValueChange={(reject_below) => set({ ...policy, reject_below })}
        />
      </FormField>
    </ToggleField>
  );
}

export function ReviewSection({
  draft,
  onChange,
  errors,
  channels,
}: SectionProps & { channels: Channel[] }) {
  const policy = draft.review_policy;
  const set = (review_policy: ReviewPolicy) => onChange({ ...draft, review_policy });
  const setMode = (mode: ReviewMode) => set({ ...policy, mode });
  return (
    <EditorSection id="review" title="Review" description="Decide which runs need a human look.">
      <div className="stack">
        <RadioCards
          label="Review policy"
          hideLabel
          columns={2}
          options={MODES}
          value={policy.mode}
          onChange={setMode}
        />
        {policy.mode === "auto_when_score_at_least" && (
          <MinScoreField policy={policy} errors={errors} set={set} />
        )}
        <RejectField policy={policy} errors={errors} set={set} />
        <ToggleField
          label="Publish as soon as a run is approved"
          hint="Whether the score or you approve it, the run uploads to every target without pressing Publish. Each target keeps its privacy, and kids' content stays made for kids."
          checked={policy.auto_publish}
          onChange={(auto_publish) => set({ ...policy, auto_publish })}
        />
        <RulesSummary text={automationSummary(draft, channels)} />
      </div>
    </EditorSection>
  );
}
