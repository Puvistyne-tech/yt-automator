import { ariaDescribedByIds, type EnumOptionsType, type WidgetProps } from "@rjsf/utils";
import { offersNotSet } from "@/shared/schema-form/choices";
import { common, isLocked } from "@/shared/schema-form/widgetProps";

function optionFor(options: EnumOptionsType[], raw: string) {
  return options.find((option) => String(option.value) === raw);
}

function sameValue(left: unknown, right: unknown): boolean {
  return String(left) === String(right);
}

function toggled(values: unknown[], option: EnumOptionsType, all: EnumOptionsType[]): unknown[] {
  const has = values.some((v) => sameValue(v, option.value));
  const next = has ? values.filter((v) => !sameValue(v, option.value)) : [...values, option.value];
  return all.map((o) => o.value).filter((v) => next.some((n) => sameValue(n, v)));
}

export function CheckboxesWidget(props: WidgetProps) {
  const options = props.options.enumOptions ?? [];
  const values: unknown[] = Array.isArray(props.value) ? props.value : [];
  return (
    <fieldset className="checkbox-options" aria-labelledby={`${props.id}__label`}>
      {options.map((option, index) => (
        <label key={String(option.value)} className="checkbox-option">
          <input
            type="checkbox"
            id={`${props.id}-${index}`}
            checked={values.some((v) => sameValue(v, option.value))}
            disabled={isLocked(props)}
            onChange={() => props.onChange(toggled(values, option, options))}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </fieldset>
  );
}

export function RadioWidget(props: WidgetProps) {
  const options = props.options.enumOptions ?? [];
  return (
    <fieldset
      className="checkbox-options radio-options"
      aria-labelledby={`${props.id}__label`}
      aria-describedby={ariaDescribedByIds(props.id)}
    >
      {options.map((option, index) => (
        <label key={String(option.value)} className="checkbox-option">
          <input
            type="radio"
            id={`${props.id}-${index}`}
            name={props.htmlName ?? props.id}
            value={String(option.value)}
            checked={sameValue(props.value, option.value)}
            disabled={isLocked(props)}
            onChange={() => props.onChange(option.value)}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </fieldset>
  );
}

export function SelectWidget(props: WidgetProps) {
  if (props.multiple) {
    return <CheckboxesWidget {...props} />;
  }
  const options = props.options.enumOptions ?? [];
  return (
    <select
      className="input select"
      {...common(props)}
      value={props.value === undefined || props.value === null ? "" : String(props.value)}
      onChange={(event) =>
        props.onChange(optionFor(options, event.target.value)?.value ?? props.options.emptyValue)
      }
    >
      {offersNotSet(props.required, props.schema) && <option value="">Not set</option>}
      {options.map((option) => (
        <option key={String(option.value)} value={String(option.value)}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
