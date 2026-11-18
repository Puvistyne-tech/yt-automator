import type {
  ArrayFieldItemTemplateProps,
  ArrayFieldTemplateProps,
  FieldTemplateProps,
  IconButtonProps,
  TemplatesType,
} from "@rjsf/utils";
import { getTemplate, getUiOptions } from "@rjsf/utils";
import { ObjectFieldTemplate } from "@/shared/schema-form/ObjectFieldTemplate";
import { BaseInputTemplate } from "@/shared/schema-form/widgets";
import { Button, IconButton } from "@/shared/ui/Button";
import type { IconName } from "@/shared/ui/Icon";

function isContainer(props: FieldTemplateProps): boolean {
  const type = props.schema.type;
  const multiSelect = getUiOptions(props.uiSchema).widget === "checkboxes";
  return type === "object" || (type === "array" && !multiSelect);
}

function FieldTemplate(props: FieldTemplateProps) {
  const { id, label, children, rawErrors = [], rawDescription, hidden, required } = props;
  if (hidden) {
    return <div hidden>{children}</div>;
  }
  if (isContainer(props)) {
    return children;
  }
  const isBoolean = props.schema.type === "boolean";
  const errorText = rawErrors.join(" ");
  return (
    <div className={rawErrors.length > 0 ? "field field-invalid" : "field"}>
      {!isBoolean && props.displayLabel !== false && (
        <label className="field-label" htmlFor={id} id={`${id}__label`}>
          {label}
          {required && (
            <span className="field-required" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      <div className="field-control">{children}</div>
      {rawDescription && (
        <p className="field-hint" id={`${id}__description`}>
          {rawDescription}
        </p>
      )}
      {errorText !== "" && (
        <p className="field-error" id={`${id}__error`} role="alert">
          {errorText}
        </p>
      )}
    </div>
  );
}

function ArrayFieldTemplate(props: ArrayFieldTemplateProps) {
  const options = getUiOptions(props.uiSchema);
  const title = options.title ?? props.title;
  const description = options.description ?? props.schema.description;
  const itemSchema = props.schema.items;
  const itemTitle =
    typeof itemSchema === "object" && !Array.isArray(itemSchema) && itemSchema.title
      ? itemSchema.title
      : "item";
  const errors = props.rawErrors ?? [];
  return (
    <fieldset className="schema-array" id={props.fieldPathId.$id}>
      <legend className="schema-group-title">{title}</legend>
      {description && <p className="field-hint">{description}</p>}
      <div className="schema-array-items">{props.items}</div>
      {errors.length > 0 && (
        <p className="field-error" role="alert">
          {errors.join(" ")}
        </p>
      )}
      {props.canAdd && (
        <Button
          size="sm"
          icon="plus"
          onClick={props.onAddClick}
          disabled={props.disabled || props.readonly}
        >
          Add {itemTitle.toLowerCase()}
        </Button>
      )}
    </fieldset>
  );
}

function ArrayFieldItemTemplate(props: ArrayFieldItemTemplateProps) {
  const Buttons = getTemplate(
    "ArrayFieldItemButtonsTemplate",
    props.registry,
    getUiOptions(props.uiSchema),
  );
  return (
    <div className="schema-array-item">
      <div className="schema-array-item-body">{props.children}</div>
      {props.hasToolbar && (
        <div className="schema-array-item-toolbar">
          <Buttons {...props.buttonsProps} />
        </div>
      )}
    </div>
  );
}

function SchemaIconButton({
  props,
  icon,
  label,
  danger = false,
}: {
  props: IconButtonProps;
  icon: IconName;
  label: string;
  danger?: boolean;
}) {
  return (
    <IconButton
      icon={icon}
      label={label}
      variant={danger ? "danger" : "ghost"}
      {...(props.id === undefined ? {} : { id: props.id })}
      disabled={props.disabled}
      onClick={props.onClick}
    />
  );
}

function MoveUpButton(props: IconButtonProps) {
  return <SchemaIconButton props={props} icon="up" label="Move up" />;
}

function MoveDownButton(props: IconButtonProps) {
  return <SchemaIconButton props={props} icon="down" label="Move down" />;
}

function CopyButton(props: IconButtonProps) {
  return <SchemaIconButton props={props} icon="copy" label="Duplicate" />;
}

function RemoveButton(props: IconButtonProps) {
  return <SchemaIconButton props={props} icon="trash" label="Remove" danger />;
}

function Nothing() {
  return null;
}

export const templates: Partial<Omit<TemplatesType, "ButtonTemplates">> & {
  ButtonTemplates: Partial<TemplatesType["ButtonTemplates"]>;
} = {
  FieldTemplate,
  ObjectFieldTemplate,
  ArrayFieldTemplate,
  ArrayFieldItemTemplate,
  BaseInputTemplate,
  ErrorListTemplate: Nothing,
  FieldErrorTemplate: Nothing,
  FieldHelpTemplate: Nothing,
  ButtonTemplates: {
    SubmitButton: Nothing,
    MoveUpButton,
    MoveDownButton,
    CopyButton,
    RemoveButton,
  },
};
