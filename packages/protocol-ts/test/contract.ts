import {
  PROTOCOL_VERSION,
  assertOperationResult,
  type OperationResult,
  type ResearchContract,
} from "../src/index.js";

const result: OperationResult = {
  schema_version: PROTOCOL_VERSION,
  session: "reaction-13",
  lineage: "reaction-13",
  operation_id: "read-1",
  revision: 3,
  model: "reaction",
  model_version: "1",
  source: "simulation",
  model_provenance: { source: "theory" },
  action: "read",
  parameters: { instrument: "thermometer" },
  start_s: 600.1,
  end_s: 600.3,
  observations: { temperature: { value: 355.2, unit: "K", noise_std: 0.08 } },
  configuration: { temperature_setpoint_k: 365.0 },
};

assertOperationResult(result);

const contract: ResearchContract = {
  schema_version: PROTOCOL_VERSION,
  domains: ["chemistry"],
  phenomena: ["kinetics"],
  questions: ["Which schedule maximizes B?"],
  observables: { b: { unit: "mol/L", description: "Intermediate concentration." } },
  latent_variables: {},
  interventions: ["set_temperature"],
  invariants: ["A+B+C is conserved."],
  failure_conditions: ["Thermal protection trips."],
  validity: {
    fidelity: "reduced-order",
    conditions: ["Well-mixed batch."],
    limitations: ["No mass-transfer limitation."],
  },
  action_semantics: {
    set_temperature: { kind: "control", description: "Set the jacket target." },
  },
  reference_methods: ["held-out schedule prediction"],
  physical_counterpart: "Jacketed batch reactor",
  metadata: {},
};

void contract;
