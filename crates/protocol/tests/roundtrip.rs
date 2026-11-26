use synthetic_lab_protocol::{OperationResult, PROTOCOL_VERSION};

#[test]
fn parses_and_round_trips_protocol_fixture() {
    let source = include_str!("../../../spec/examples/operation-result.json");
    let result: OperationResult = serde_json::from_str(source).expect("fixture should parse");
    result.validate().expect("fixture should satisfy protocol invariants");
    assert_eq!(result.schema_version, PROTOCOL_VERSION);
    assert_eq!(result.model, "reaction");

    let encoded = serde_json::to_string(&result).expect("result should serialize");
    let decoded: OperationResult = serde_json::from_str(&encoded).expect("round trip should parse");
    assert_eq!(decoded, result);
}
