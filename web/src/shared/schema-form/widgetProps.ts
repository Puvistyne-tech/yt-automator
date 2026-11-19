import { ariaDescribedByIds, type WidgetProps } from "@rjsf/utils";

export function common(props: WidgetProps) {
  return {
    id: props.id,
    name: props.htmlName ?? props.id,
    disabled: isLocked(props),
    "aria-describedby": ariaDescribedByIds(props.id),
    "aria-invalid": (props.rawErrors?.length ?? 0) > 0 ? true : undefined,
    onBlur: () => props.onBlur(props.id, props.value),
    onFocus: () => props.onFocus(props.id, props.value),
  };
}

export function isLocked(props: { disabled?: boolean; readonly?: boolean }): boolean {
  return Boolean(props.disabled || props.readonly);
}
