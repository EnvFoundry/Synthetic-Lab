use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const PROTOCOL_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type")]
pub enum Parameter {
    #[serde(rename = "number")]
    Numeric {
        unit: Option<String>,
        minimum: f64,
        maximum: f64,
    },
    #[serde(rename = "string")]
    Enum {
        #[serde(rename = "enum")]
        choices: Vec<String>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct VariableDescription {
    pub description: String,
    pub unit: Option<String>,
    #[serde(flatten)]
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "kebab-case")]
pub enum Fidelity {
    Analytical,
    ReducedOrder,
    Surrogate,
    Empirical,
    Hybrid,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum ActionKind {
    Configure,
    Control,
    Intervention,
    Measurement,
    Wait,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ActionSemantic {
    pub kind: ActionKind,
    pub description: String,
    #[serde(flatten)]
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Validity {
    pub fidelity: Fidelity,
    pub conditions: Vec<String>,
    pub limitations: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ResearchContract {
    pub schema_version: u32,
    pub domains: Vec<String>,
    pub phenomena: Vec<String>,
    pub questions: Vec<String>,
    pub observables: BTreeMap<String, VariableDescription>,
    pub latent_variables: BTreeMap<String, VariableDescription>,
    pub interventions: Vec<String>,
    pub invariants: Vec<String>,
    pub failure_conditions: Vec<String>,
    pub validity: Validity,
    pub action_semantics: BTreeMap<String, ActionSemantic>,
    pub reference_methods: Vec<String>,
    pub physical_counterpart: Option<String>,
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LaboratoryDescription {
    pub name: String,
    pub model_version: String,
    pub description: String,
    pub source: String,
    pub validation: String,
    pub capabilities: Vec<String>,
    pub actions: BTreeMap<String, BTreeMap<String, Parameter>>,
    pub research_contract: ResearchContract,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct OperationResult {
    pub schema_version: u32,
    pub session: String,
    pub lineage: String,
    pub operation_id: String,
    pub revision: u64,
    pub model: String,
    pub model_version: String,
    pub source: String,
    pub model_provenance: BTreeMap<String, Value>,
    pub action: String,
    pub parameters: BTreeMap<String, Value>,
    pub start_s: f64,
    pub end_s: f64,
    pub observations: BTreeMap<String, Value>,
    pub configuration: BTreeMap<String, Value>,
}

impl OperationResult {
    pub fn validate(&self) -> Result<(), &'static str> {
        if self.schema_version != PROTOCOL_VERSION {
            return Err("unsupported schema version");
        }
        if self.session.is_empty() || self.operation_id.is_empty() || self.model.is_empty() {
            return Err("required identifiers cannot be empty");
        }
        if self.revision == 0 || self.start_s < 0.0 || self.end_s < self.start_s {
            return Err("invalid revision or time interval");
        }
        if self.source != "simulation" {
            return Err("operation results must identify their simulated source");
        }
        Ok(())
    }
}
