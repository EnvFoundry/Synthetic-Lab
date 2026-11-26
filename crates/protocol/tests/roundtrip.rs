use synthetic_lab_protocol::{
    ArtifactReference, OperationResult, PROTOCOL_VERSION,
};

#[test]
fn parses_and_round_trips_protocol_fixture() {
    let source = include_str!("../../../spec/examples/operation-result.json");
    let result: OperationResult = serde_json::from_str(source).expect("fixture should parse");
    result
        .validate()
        .expect("fixture should satisfy protocol invariants");
    assert_eq!(result.schema_version, PROTOCOL_VERSION);
    assert_eq!(result.model, "reaction");

    let encoded = serde_json::to_string(&result).expect("result should serialize");
    let decoded: OperationResult = serde_json::from_str(&encoded).expect("round trip should parse");
    assert_eq!(decoded, result);
}

#[test]
fn parses_external_artifact_reference() {
    let source = include_str!("../../../spec/examples/artifact-reference.json");
    let reference: ArtifactReference = serde_json::from_str(source).expect("fixture should parse");
    reference
        .validate()
        .expect("fixture should contain a coherent artifact URI");
    assert_eq!(reference.artifact.size_bytes, 4823);
}

#[test]
fn shared_operation_cases_agree_with_typescript() {
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("../../../spec/examples/operation-result.json")).unwrap();
    let cases: Vec<serde_json::Value> =
        serde_json::from_str(include_str!("../../../spec/examples/operation-cases.json")).unwrap();
    for case in cases {
        let mut value = fixture.clone();
        for (key, replacement) in case["patch"].as_object().unwrap() {
            value[key] = replacement.clone();
        }
        let accepted = serde_json::from_value::<OperationResult>(value)
            .is_ok_and(|result| result.validate().is_ok());
        assert_eq!(
            accepted,
            case["valid"].as_bool().unwrap(),
            "{}",
            case["name"]
        );
    }
}

#[test]
fn native_nonfinite_times_are_not_valid_operations() {
    let mut result: OperationResult =
        serde_json::from_str(include_str!("../../../spec/examples/operation-result.json")).unwrap();
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        result.end_s = value;
        assert!(result.validate().is_err());
    }
}
