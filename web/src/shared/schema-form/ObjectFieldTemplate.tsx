import type {
  ObjectFieldTemplatePropertyType,
  ObjectFieldTemplateProps,
  Registry,
} from "@rjsf/utils";
import { SectionChanges } from "@/shared/schema-form/ChangeMarks";
import { groupIntoSections, readSections, type Section } from "@/shared/schema-form/sections";

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

function SchemaSection({
  section,
  registry,
  idPrefix,
}: {
  section: Section<ObjectFieldTemplatePropertyType>;
  registry: Registry;
  idPrefix: string;
}) {
  const title = section.title ?? "Other";
  const headingId = `${idPrefix}__section-${title.toLowerCase().replace(/\W+/g, "-")}`;
  return (
    <section className="schema-section" aria-labelledby={headingId}>
      <div className="schema-section-head">
        <h3 className="schema-section-title" id={headingId} tabIndex={-1}>
          {title}
        </h3>
        <SectionChanges
          registry={registry}
          title={title}
          names={section.properties.map((property) => property.name)}
          headingId={headingId}
        />
      </div>
      <Properties properties={section.properties} />
    </section>
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
        <SchemaSection
          key={section.title ?? "other"}
          section={section}
          registry={props.registry}
          idPrefix={props.fieldPathId.$id}
        />
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
