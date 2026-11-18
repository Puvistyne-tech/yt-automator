import type { ReviewMode } from "@/api/types";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
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

export function ReviewSection({ draft, onChange, errors }: SectionProps) {
  const policy = draft.review_policy;
  const setMode = (mode: ReviewMode) => onChange({ ...draft, review_policy: { ...policy, mode } });
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
              onValueChange={(min_score) =>
                onChange({ ...draft, review_policy: { ...policy, min_score } })
              }
            />
          </FormField>
        )}
      </div>
    </EditorSection>
  );
}
