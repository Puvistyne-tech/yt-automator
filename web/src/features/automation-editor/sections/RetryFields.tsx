import { MAX_AUTO_RETRIES, MAX_RETRY_DELAY_MINUTES } from "@/api/automationDefaults";
import type { RetryPolicy } from "@/api/types";
import { FormField, NumberInput } from "@/shared/ui";

interface RetryFieldsProps {
  policy: RetryPolicy;
  errors: Record<string, string>;
  onChange: (policy: RetryPolicy) => void;
}

export function RetryFields({ policy, errors, onChange }: RetryFieldsProps) {
  return (
    <fieldset className="option-group">
      <legend className="option-group-title">When a run fails</legend>
      <div className="grid-2">
        <FormField
          label="Retry automatically (times)"
          hint="0 turns this off. A retry restarts from the stage that failed and keeps earlier work."
          error={errors["retry_policy.auto_retry_count"]}
        >
          <NumberInput
            min={0}
            max={MAX_AUTO_RETRIES}
            step={1}
            value={policy.auto_retry_count}
            onValueChange={(auto_retry_count) => onChange({ ...policy, auto_retry_count })}
          />
        </FormField>
        <FormField
          label="Wait before retrying (minutes)"
          hint="Gives a busy model or network time to recover."
          error={errors["retry_policy.retry_delay_minutes"]}
        >
          <NumberInput
            min={0}
            max={MAX_RETRY_DELAY_MINUTES}
            step={1}
            value={policy.retry_delay_minutes}
            disabled={policy.auto_retry_count === 0}
            onValueChange={(retry_delay_minutes) => onChange({ ...policy, retry_delay_minutes })}
          />
        </FormField>
      </div>
    </fieldset>
  );
}
