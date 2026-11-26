export const PROTOCOL_VERSION = 1 as const;

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface NumericParameter {
  type: "number";
  unit: string | null;
  minimum: number;
  maximum: number;
}

export interface EnumParameter {
  type: "string";
  enum: string[];
}

export type Parameter = NumericParameter | EnumParameter;

export interface VariableDescription {
  description: string;
  unit: string | null;
  [key: string]: JsonValue;
}

export type ActionKind =
  | "configure"
  | "control"
  | "intervention"
  | "measurement"
  | "wait";

export interface ActionSemantic {
  kind: ActionKind;
  description: string;
  [key: string]: JsonValue;
}

export type Fidelity =
  | "analytical"
  | "reduced-order"
  | "surrogate"
  | "empirical"
  | "hybrid";

export interface ResearchContract {
  schema_version: 1;
  domains: string[];
  phenomena: string[];
  questions: string[];
  observables: Record<string, VariableDescription>;
  latent_variables: Record<string, VariableDescription>;
  interventions: string[];
  invariants: string[];
  failure_conditions: string[];
  validity: {
    fidelity: Fidelity;
    conditions: string[];
    limitations: string[];
  };
  action_semantics: Record<string, ActionSemantic>;
  reference_methods: string[];
  physical_counterpart: string | null;
  metadata: Record<string, JsonValue>;
}

export interface LaboratoryDescription {
  name: string;
  model_version: string;
  description: string;
  source: "simulation";
  validation: string;
  capabilities: string[];
  actions: Record<string, Record<string, Parameter>>;
  research_contract?: ResearchContract;
}

export interface OperationResult {
  schema_version: 1;
  session: string;
  lineage: string;
  operation_id: string;
  revision: number;
  model: string;
  model_version: string;
  source: "simulation";
  model_provenance: Record<string, JsonValue>;
  action: string;
  parameters: Record<string, JsonValue>;
  start_s: number;
  end_s: number;
  observations: Record<string, JsonValue>;
  configuration: Record<string, JsonValue>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null &&
    (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}

function isJsonValue(value: unknown, parents = new Set<object>()): value is JsonValue {
  if (value === null || typeof value === "string" || typeof value === "boolean") return true;
  if (typeof value === "number") return Number.isFinite(value);
  if (!Array.isArray(value) && !isRecord(value)) return false;
  if (parents.has(value)) return false;
  parents.add(value);
  const children = Array.isArray(value) ? Array.from(value) : Object.values(value);
  const valid = children.every(child => isJsonValue(child, parents));
  parents.delete(value);
  return valid;
}

export function isOperationResult(value: unknown): value is OperationResult {
  if (!isRecord(value) || !isJsonValue(value)) return false;
  const fields = [
    "schema_version", "session", "lineage", "operation_id", "revision", "model",
    "model_version", "source", "model_provenance", "action", "parameters", "start_s",
    "end_s", "observations", "configuration",
  ];
  if (Object.keys(value).length !== fields.length || !fields.every(key => Object.hasOwn(value, key))) {
    return false;
  }
  const identifiers = ["session", "lineage", "operation_id", "model", "model_version", "action"];
  if (!identifiers.every(key => typeof value[key] === "string" && value[key].trim().length > 0)) {
    return false;
  }
  return (
    value.schema_version === PROTOCOL_VERSION &&
    typeof value.session === "string" &&
    typeof value.lineage === "string" &&
    typeof value.operation_id === "string" &&
    typeof value.revision === "number" && Number.isSafeInteger(value.revision) && value.revision > 0 &&
    typeof value.model === "string" &&
    typeof value.model_version === "string" &&
    value.source === "simulation" &&
    typeof value.action === "string" &&
    typeof value.start_s === "number" &&
    typeof value.end_s === "number" && value.start_s >= 0 && value.end_s >= value.start_s &&
    isRecord(value.model_provenance) &&
    isRecord(value.parameters) &&
    isRecord(value.observations) &&
    isRecord(value.configuration)
  );
}

export function assertOperationResult(value: unknown): asserts value is OperationResult {
  if (!isOperationResult(value)) {
    throw new TypeError("Value is not a Synthetic Lab protocol-v1 operation result");
  }
}
