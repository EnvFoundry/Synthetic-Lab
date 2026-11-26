use serde_json::Value;
use std::{env, error::Error, fs};
use synthetic_lab_protocol::{LaboratoryDescription, OperationResult};

fn main() -> Result<(), Box<dyn Error>> {
    let path = env::args()
        .nth(1)
        .ok_or("Provide an exported runtime fixture path")?;
    let records: Vec<Value> = serde_json::from_str(&fs::read_to_string(path)?)?;
    if records.is_empty() {
        return Err("No runtime records supplied".into());
    }
    for record in &records {
        if let Some(value) = record.get("result") {
            let result: OperationResult = serde_json::from_value(value.clone())?;
            result.validate()?;
            let decoded: OperationResult = serde_json::from_str(&serde_json::to_string(&result)?)?;
            assert_eq!(result, decoded);
        } else if let Some(value) = record.get("laboratory") {
            let lab: LaboratoryDescription = serde_json::from_value(value.clone())?;
            let decoded: LaboratoryDescription =
                serde_json::from_str(&serde_json::to_string(&lab)?)?;
            assert_eq!(lab, decoded);
        } else {
            return Err("Unknown runtime record".into());
        }
    }
    println!("Round-tripped {} live runtime records", records.len());
    Ok(())
}
