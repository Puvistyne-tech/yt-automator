import {
  ariaDescribedByIds,
  type BaseInputTemplateProps,
  type EnumOptionsType,
  getInputProps,
  type RegistryWidgetsType,
  type WidgetProps,
} from "@rjsf/utils";
import type { ChangeEvent } from "react";
import { Switch } from "@/shared/ui/Switch";

function common(props: WidgetProps) {
  return {
    id: props.id,
    name: props.htmlName ?? props.id,
    disabled: Boolean(props.disabled || props.readonly),
    "aria-describedby": ariaDescribedByIds(props.id),
    "aria-invalid": (props.rawErrors?.length ?? 0) > 0 ? true : undefined,
    onBlur: () => props.onBlur(props.id, props.value),
    onFocus: () => props.onFocus(props.id, props.value),
  };
}

export function BaseInputTemplate(props: BaseInputTemplateProps) {
  const inputProps = getInputProps(props.schema, props.type, props.options);
  const numeric = inputProps.type === "number" || inputProps.type === "integer";
  const value = numeric
    ? (props.value ?? props.value === 0)
      ? props.value
      : ""
    : (props.value ?? "");
  const onChange = (event: ChangeEvent<HTMLInputElement>) =>
    props.onChange(event.target.value === "" ? props.options.emptyValue : event.target.value);
  return (
    <input
      className="input"
      {...common(props)}
      {...inputProps}
      placeholder={props.placeholder}
      value={value}
      onChange={props.onChangeOverride ?? onChange}
    />
  );
}

function TextareaWidget(props: WidgetProps) {
  const rows = typeof props.options.rows === "number" ? props.options.rows : 4;
  return (
    <textarea
      className="input textarea"
      {...common(props)}
      rows={rows}
      value={props.value ?? ""}
      placeholder={props.placeholder}
      onChange={(event) =>
        props.onChange(event.target.value === "" ? props.options.emptyValue : event.target.value)
      }
    />
  );
}

function optionFor(options: EnumOptionsType[], raw: string) {
  return options.find((option) => String(option.value) === raw);
}

function toggled(values: unknown[], option: EnumOptionsType, all: EnumOptionsType[]): unknown[] {
  const has = values.some((v) => String(v) === String(option.value));
  const next = has
    ? values.filter((v) => String(v) !== String(option.value))
    : [...values, option.value];
  return all.map((o) => o.value).filter((v) => next.some((n) => String(n) === String(v)));
}

function CheckboxesWidget(props: WidgetProps) {
  const options = props.options.enumOptions ?? [];
  const values: unknown[] = Array.isArray(props.value) ? props.value : [];
  return (
    <fieldset className="checkbox-options" aria-labelledby={`${props.id}__label`}>
      {options.map((option, index) => (
        <label key={String(option.value)} className="checkbox-option">
          <input
            type="checkbox"
            id={`${props.id}-${index}`}
            checked={values.some((v) => String(v) === String(option.value))}
            disabled={Boolean(props.disabled || props.readonly)}
            onChange={() => props.onChange(toggled(values, option, options))}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </fieldset>
  );
}

function SelectWidget(props: WidgetProps) {
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
      {!props.required && <option value="">Not set</option>}
      {options.map((option) => (
        <option key={String(option.value)} value={String(option.value)}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

function CheckboxWidget(props: WidgetProps) {
  return (
    <Switch
      id={props.id}
      checked={props.value === true}
      disabled={Boolean(props.disabled || props.readonly)}
      onChange={(checked) => props.onChange(checked)}
      label={props.label}
    />
  );
}

function RangeWidget(props: WidgetProps) {
  const { min, max, step } = getInputProps(props.schema, "range", props.options);
  const value = typeof props.value === "number" ? props.value : Number(min ?? 0);
  return (
    <div className="range">
      <input
        type="range"
        className="range-input"
        {...common(props)}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => props.onChange(Number(event.target.value))}
      />
      <output className="range-value" htmlFor={props.id}>
        {value}
      </output>
    </div>
  );
}

function ColorWidget(props: WidgetProps) {
  const value = typeof props.value === "string" && props.value !== "" ? props.value : "#000000";
  return (
    <div className="color-field">
      <input
        type="color"
        className="color-swatch"
        {...common(props)}
        value={value}
        onChange={(event) => props.onChange(event.target.value)}
      />
      <span className="mono">{value}</span>
    </div>
  );
}

export const widgets: RegistryWidgetsType = {
  TextareaWidget,
  SelectWidget,
  CheckboxesWidget,
  CheckboxWidget,
  RangeWidget,
  ColorWidget,
};
