import type { ObjectFieldTemplatePropertyType, ObjectFieldTemplateProps } from "@rjsf/utils";
import { groupIntoSections, readSections } from "@/shared/schema-form/sections";

function Properties({ properties }: { properties: ObjectFieldTemplatePropertyType[] }) {
  return (
    <div className="schema-grid">
      {properties.map((property) =>
        property.hidden ? null : (
          <div key={property.name} className="schema-cell">
            {property.content}
          </div>
        ),
      )}
    </div>
  );
}

function RootObject(props: ObjectFieldTemplateProps) {
  const sections = groupIntoSections(props.properties, readSections(props.uiSchema));
  if (sections.length === 1 && sections[0]?.title === null) {
    return <Properties properties={props.properties} />;
  }
  return (
    <div className="schema-sections">
      {sections.map((section) => (
        <section key={section.title ?? "other"} className="schema-section">
          <h3 className="schema-section-title">{section.title ?? "Other"}</h3>
          <Properties properties={section.properties} />
        </section>
      ))}
    </div>
  );
}

export function ObjectFieldTemplate(props: ObjectFieldTemplateProps) {
  if (props.fieldPathId.path.length === 0) {
    return <RootObject {...props} />;
  }
  const title = props.title;
  const isArrayItem = typeof props.fieldPathId.path.at(-1) === "number";
  return (
    <fieldset className={isArrayItem ? "schema-object schema-object-item" : "schema-object"}>
      {title && !isArrayItem && <legend className="schema-group-title">{title}</legend>}
      {props.description && <p className="field-hint">{props.description}</p>}
      <Properties properties={props.properties} />
    </fieldset>
  );
}
