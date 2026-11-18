import { isJsonObject } from "@/shared/isJsonObject";

type Schema = Record<string, unknown>;

export interface SchemaField {
  path: string;
  title: string;
  description: string;
  leaf: boolean;
}

const LOCAL_REFERENCE = "#/";
const BRANCH_KEYS = ["anyOf", "oneOf", "allOf"] as const;

function referenced(reference: string, root: Schema): Schema {
  const target = reference
    .slice(LOCAL_REFERENCE.length)
    .split("/")
    .reduce<unknown>((node, part) => (isJsonObject(node) ? node[part] : undefined), root);
  return isJsonObject(target) ? target : {};
}

function resolveRef(node: Schema, root: Schema): Schema {
  const reference = node.$ref;
  if (typeof reference !== "string" || !reference.startsWith(LOCAL_REFERENCE)) {
    return node;
  }
  const { $ref: _, ...rest } = node;
  return { ...referenced(reference, root), ...rest };
}

function firstNonNull(options: unknown[]): Schema {
  const branches = options.filter(isJsonObject);
  return branches.find((branch) => branch.type !== "null") ?? branches[0] ?? {};
}

function narrowed(node: Schema): Schema {
  const key = BRANCH_KEYS.find((name) => Array.isArray(node[name]) && node[name].length > 0);
  return key === undefined ? node : { ...node, ...firstNonNull(node[key] as unknown[]) };
}

function resolved(node: Schema, root: Schema): Schema {
  return resolveRef(narrowed(resolveRef(node, root)), root);
}

function propertiesOf(node: Schema, root: Schema): [string, Schema][] {
  const properties = resolved(node, root).properties;
  if (!isJsonObject(properties)) {
    return [];
  }
  return Object.entries(properties).flatMap(([name, child]) =>
    isJsonObject(child) ? [[name, child] as [string, Schema]] : [],
  );
}

function textOf(key: "title" | "description", node: Schema, root: Schema): string {
  const own = resolveRef(node, root)[key];
  const fallback = resolved(node, root)[key];
  if (typeof own === "string") {
    return own;
  }
  return typeof fallback === "string" ? fallback : "";
}

function fieldsUnder(node: Schema, root: Schema, prefix: string): SchemaField[] {
  return propertiesOf(node, root).flatMap(([name, child]) => {
    const path = prefix === "" ? name : `${prefix}.${name}`;
    const children = fieldsUnder(child, root, path);
    const field = {
      path,
      title: textOf("title", child, root) || name,
      description: textOf("description", child, root),
      leaf: children.length === 0,
    };
    return [field, ...children];
  });
}

export function schemaFields(schema: Schema): SchemaField[] {
  return fieldsUnder(schema, schema, "");
}
