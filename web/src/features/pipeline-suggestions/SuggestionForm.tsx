import { audienceOptions } from "@/api/labels";
import { YOUTUBE_CATEGORIES } from "@/features/pipeline-suggestions/model/categories";
import { COMMON_REGIONS, regionName } from "@/features/pipeline-suggestions/model/regions";
import { COUNT_OPTIONS, OTHER_REGION } from "@/features/pipeline-suggestions/model/request";
import type { SuggestionsState } from "@/features/pipeline-suggestions/usePipelineSuggestions";
import { Button, FormField, Input, RadioCards, Select } from "@/shared/ui";

const AUDIENCE_OPTIONS = audienceOptions();

const REGION_OPTIONS = [
  ...COMMON_REGIONS.map((code) => ({ value: code, label: regionName(code) })),
  { value: OTHER_REGION, label: "Another country" },
];

const CATEGORY_OPTIONS = YOUTUBE_CATEGORIES.map((c) => ({ value: c.id, label: c.name }));

function RegionFields({ state }: { state: SuggestionsState }) {
  const other = state.form.region === OTHER_REGION;
  return (
    <>
      <FormField label="Country" error={other ? undefined : state.errors.region}>
        <Select
          value={state.form.region}
          options={REGION_OPTIONS}
          onChange={(event) => state.change({ region: event.target.value })}
        />
      </FormField>
      {other && (
        <FormField label="Country code" hint="Two letters, like NZ." error={state.errors.region}>
          <Input
            value={state.form.otherRegion}
            maxLength={2}
            onChange={(event) => state.change({ otherRegion: event.target.value })}
          />
        </FormField>
      )}
    </>
  );
}

function FilterFields({ state }: { state: SuggestionsState }) {
  return (
    <>
      <FormField label="YouTube category (optional)" error={state.errors.category}>
        <Select
          value={state.form.category}
          placeholder="Every category"
          options={CATEGORY_OPTIONS}
          onChange={(event) => state.change({ category: event.target.value })}
        />
      </FormField>
      <FormField label="Number of ideas" error={state.errors.count}>
        <Select
          value={String(state.form.count)}
          options={COUNT_OPTIONS}
          onChange={(event) => state.change({ count: Number(event.target.value) })}
        />
      </FormField>
    </>
  );
}

export function SuggestionForm({ state }: { state: SuggestionsState }) {
  return (
    <div className="suggestion-form">
      <RadioCards
        label="Who are the videos for?"
        columns={2}
        value={state.form.audience}
        options={AUDIENCE_OPTIONS}
        error={state.errors.audience}
        onChange={(audience) => state.change({ audience })}
      />
      <div className="suggestion-fields">
        <RegionFields state={state} />
        <FilterFields state={state} />
      </div>
      <div className="row">
        <Button variant="primary" loading={state.finding} onClick={state.find}>
          {state.finding ? "Finding ideas…" : "Find ideas"}
        </Button>
      </div>
    </div>
  );
}
