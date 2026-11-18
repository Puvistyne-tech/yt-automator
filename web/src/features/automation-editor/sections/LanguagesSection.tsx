import type { PipelineDescriptor } from "@/api/types";
import {
  languageName,
  orphanTargets,
  withoutOrphanTargets,
} from "@/features/automation-editor/model/targets";
import {
  EditorSection,
  type SectionProps,
} from "@/features/automation-editor/sections/EditorSection";
import { pluralize } from "@/shared/format/text";
import { Button, Callout, CheckboxGroup } from "@/shared/ui";

interface LanguagesSectionProps extends SectionProps {
  pipeline: PipelineDescriptor;
}

function OrphanNotice({ draft, onChange, pipeline }: LanguagesSectionProps) {
  const orphans = orphanTargets(draft.targets, draft.languages);
  if (orphans.length === 0) {
    return null;
  }
  const names = [...new Set(orphans.map((t) => languageName(pipeline, t.language)))].join(", ");
  return (
    <Callout tone="warning">
      <span>
        {pluralize(orphans.length, "target")} still publish in {names}, which is no longer selected.
      </span>
      <Button size="sm" variant="danger" onClick={() => onChange(withoutOrphanTargets(draft))}>
        Remove {pluralize(orphans.length, "target")}
      </Button>
    </Callout>
  );
}

export function LanguagesSection(props: LanguagesSectionProps) {
  const { draft, onChange, errors, pipeline } = props;
  return (
    <EditorSection
      id="languages"
      title="Languages"
      description="Each run produces narration, subtitles and metadata in every selected language."
    >
      <div className="stack">
        <CheckboxGroup
          label="Output languages"
          layout="cards"
          value={draft.languages}
          onChange={(languages) => onChange({ ...draft, languages })}
          error={errors.languages}
          options={pipeline.languages.map((language) => ({
            value: language.code,
            label: language.name,
            description: language.code,
          }))}
        />
        <OrphanNotice {...props} />
      </div>
    </EditorSection>
  );
}
