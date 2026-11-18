import type {
  ArrayFieldItemTemplateProps,
  ArrayFieldTemplateProps,
  FieldTemplateProps,
  TemplatesType,
} from "@rjsf/utils";
import { getTemplate, getUiOptions } from "@rjsf/utils";
import type { ReactNode } from "react";
import {
  CopyButton,
  MoveDownButton,
  MoveUpButton,
  RemoveButton,
} from "@/shared/schema-form/arrayButtons";
import { FieldChange } from "@/shared/schema-form/ChangeMarks";
import { ObjectFieldTemplate } from "@/shared/schema-form/ObjectFieldTemplate";
import { BaseInputTemplate } from "@/shared/schema-form/widgets";
import { Button } from "@/shared/ui/Button";

function isContainer(props: FieldTemplateProps): boolean {
  const type = props.schema.type;
  const multiSelect = getUiOptions(props.uiSchema).widget === "checkboxes";
  return type === "object" || (type === "array" && !multiSelect);
}

function FieldLabel(props: FieldTemplateProps) {
  const { id, label, required } = props;
  return (
    <label className="field-label" htmlFor={id} id={`${id}__label`}>
      {label}
      {required && (
        <span className="field-required" aria-hidden="true">
          *
        </span>
      )}
    </label>
  );
}

function FieldHead({ props, children }: { props: FieldTemplateProps; children: ReactNode }) {
  return (
    <div className="field-head">
      {children}
      <FieldChange
        registry={props.registry}
        path={props.fieldPathId.path}
        label={props.label}
        fieldId={props.id}
      />
    </div>
  );
}

function FieldTemplate(props: FieldTemplateProps) {
  const { id, children, rawErrors = [], rawDescription, hidden } = props;
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
      {isBoolean ? (
        <FieldHead props={props}>
          <div className="field-control">{children}</div>
        </FieldHead>
      ) : (
        <>
          <FieldHead props={props}>
            {props.displayLabel !== false && <FieldLabel {...props} />}
          </FieldHead>
          <div className="field-control">{children}</div>
        </>
      )}
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

function itemTitleOf(props: ArrayFieldTemplateProps): string {
  const itemSchema = props.schema.items;
  return typeof itemSchema === "object" && !Array.isArray(itemSchema) && itemSchema.title
    ? itemSchema.title
    : "item";
}

function ArrayFieldTemplate(props: ArrayFieldTemplateProps) {
  const options = getUiOptions(props.uiSchema);
  const title = options.title ?? props.title;
  const description = options.description ?? props.schema.description;
  const errors = props.rawErrors ?? [];
  const id = props.fieldPathId.$id;
  return (
    <fieldset className="schema-array" id={id}>
      <legend className="schema-group-title schema-group-head">
        <span>{title}</span>
        <FieldChange
          registry={props.registry}
          path={props.fieldPathId.path}
          label={title}
          fieldId={id}
        />
      </legend>
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
          Add {itemTitleOf(props).toLowerCase()}
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
