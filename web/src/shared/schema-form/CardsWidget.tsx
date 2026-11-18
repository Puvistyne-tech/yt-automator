import { ariaDescribedByIds, type WidgetProps } from "@rjsf/utils";
import { useState } from "react";
import {
  type CardOption,
  cardGroups,
  cardOption,
  filteredCards,
  groupLabels,
  offersSearch,
  selectedLabel,
} from "@/shared/schema-form/cardOptions";
import { isLocked } from "@/shared/schema-form/widgetProps";
import "@/shared/schema-form/cards.css";

interface CardProps {
  option: CardOption;
  id: string;
  name: string;
  checked: boolean;
  disabled: boolean;
  onSelect: () => void;
}

function ChoiceCard({ option, id, name, checked, disabled, onSelect }: CardProps) {
  return (
    <label className="choice-card" htmlFor={id}>
      <input
        type="radio"
        className="choice-card-input"
        id={id}
        name={name}
        value={String(option.value)}
        checked={checked}
        disabled={disabled}
        onChange={onSelect}
      />
      {option.swatches.length > 0 && (
        <span className="choice-card-swatches" aria-hidden="true">
          {option.swatches.map((colour) => (
            <span key={colour} className="choice-card-swatch" style={{ background: colour }} />
          ))}
        </span>
      )}
      <span className="choice-card-title">{option.label}</span>
      {option.description !== "" && (
        <span className="choice-card-description">{option.description}</span>
      )}
    </label>
  );
}

interface FilterProps {
  label: string;
  labels: string[];
  search: boolean;
  query: string;
  group: string | null;
  onQuery: (query: string) => void;
  onGroup: (group: string | null) => void;
}

function CardFilters({ label, labels, search, query, group, onQuery, onGroup }: FilterProps) {
  const chips: (string | null)[] = labels.length > 1 ? [null, ...labels] : [];
  return (
    <div className="choice-card-filters">
      {search && (
        <input
          type="search"
          className="input choice-card-search"
          placeholder="Search"
          aria-label={`Search ${label}`}
          value={query}
          onChange={(event) => onQuery(event.target.value)}
        />
      )}
      {chips.length > 0 && (
        <fieldset className="choice-card-chips" aria-label={`Filter ${label}`}>
          {chips.map((chip) => (
            <button
              key={chip ?? "all"}
              type="button"
              className="choice-card-chip"
              aria-pressed={group === chip}
              onClick={() => onGroup(chip)}
            >
              {chip ?? "All"}
            </button>
          ))}
        </fieldset>
      )}
    </div>
  );
}

function CardSections({
  props,
  all,
  shown,
}: {
  props: WidgetProps;
  all: CardOption[];
  shown: CardOption[];
}) {
  const name = props.htmlName ?? props.id;
  return (
    <div
      role="radiogroup"
      className="choice-card-groups"
      aria-labelledby={`${props.id}__label`}
      aria-describedby={ariaDescribedByIds(props.id)}
    >
      {cardGroups(shown).map((section) => (
        <div key={section.label ?? "other"} className="choice-card-group">
          {section.label !== null && <p className="choice-card-group-title">{section.label}</p>}
          <div className="choice-card-grid">
            {section.options.map((option) => (
              <ChoiceCard
                key={String(option.value)}
                option={option}
                id={`${props.id}-${all.indexOf(option)}`}
                name={name}
                checked={String(props.value) === String(option.value)}
                disabled={isLocked(props)}
                onSelect={() => props.onChange(option.value)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function CardsWidget(props: WidgetProps) {
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState<string | null>(null);
  const all = (props.options.enumOptions ?? []).map(cardOption);
  const shown = filteredCards(all, query, group);
  const label = props.label || "options";
  const current = selectedLabel(all, props.value);
  return (
    <div className="choice-cards">
      <CardFilters
        label={label}
        labels={groupLabels(all)}
        search={offersSearch(all.length)}
        query={query}
        group={group}
        onQuery={setQuery}
        onGroup={setGroup}
      />
      {current !== null && <p className="choice-card-current">Selected: {current}</p>}
      <CardSections props={props} all={all} shown={shown} />
      {shown.length === 0 && <p className="field-hint">Nothing matches. Clear the search.</p>}
    </div>
  );
}
