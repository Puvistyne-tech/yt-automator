import type { TemplateAudience } from "@/api/types";
import { AUDIENCE_BADGES } from "@/features/pipeline-templates/model/listing";
import { type RadioCardOption, RadioCards } from "@/shared/ui";

export const AUDIENCE_NOTE =
  "The audience cannot be changed later. To change it, duplicate the pipeline and pick another audience.";

const AUDIENCE_DESCRIPTIONS: Record<TemplateAudience, string> = {
  kids: "Videos made for children. They always upload as made for kids, and scripts stay gentle and simple.",
  general:
    "Videos for teenagers and adults. They are not made for kids and must not address children.",
};

export function audienceDescription(audience: TemplateAudience): string {
  return AUDIENCE_DESCRIPTIONS[audience];
}

const AUDIENCE_OPTIONS: RadioCardOption<TemplateAudience>[] = (
  Object.keys(AUDIENCE_DESCRIPTIONS) as TemplateAudience[]
).map((value) => ({
  value,
  label: AUDIENCE_BADGES[value].label,
  description: AUDIENCE_DESCRIPTIONS[value],
}));

export function AudienceChoice({
  value,
  onChange,
}: {
  value: TemplateAudience | "";
  onChange: (audience: TemplateAudience) => void;
}) {
  return (
    <RadioCards
      label="Who are the videos for?"
      columns={2}
      value={value}
      onChange={onChange}
      options={AUDIENCE_OPTIONS}
    />
  );
}
