import {
  type BaseInputTemplateProps,
  getInputProps,
  type RegistryWidgetsType,
  type WidgetProps,
} from "@rjsf/utils";
import type { ChangeEvent } from "react";
import { CheckboxesWidget, RadioWidget, SelectWidget } from "@/shared/schema-form/choiceWidgets";
import { positiveNumberOption } from "@/shared/schema-form/options";
import { common, isLocked } from "@/shared/schema-form/widgetProps";
import { Switch } from "@/shared/ui/Switch";

const DEFAULT_TEXTAREA_ROWS = 4;

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
  const rows = positiveNumberOption(props.options, "rows") ?? DEFAULT_TEXTAREA_ROWS;
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

function CheckboxWidget(props: WidgetProps) {
  return (
    <Switch
      id={props.id}
      checked={props.value === true}
      disabled={isLocked(props)}
      onChange={(checked) => props.onChange(checked)}
      label={props.label}
    />
  );
}

function RangeWidget(props: WidgetProps) {
  const spec = getInputProps(props.schema, "range", props.options);
  const { min, max } = spec;
  const step = positiveNumberOption(props.options, "step") ?? spec.step;
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
  RadioWidget,
  CheckboxesWidget,
  CheckboxWidget,
  RangeWidget,
  ColorWidget,
};
