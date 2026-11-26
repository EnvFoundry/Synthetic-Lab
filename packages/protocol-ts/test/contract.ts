import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import { assertOperationResult, isOperationResult } from "../src/index.js";

const root = fileURLToPath(new URL("../../../../", import.meta.url));
const read = (name: string): unknown => JSON.parse(readFileSync(join(root, name), "utf8"));
const fixture = read("spec/examples/operation-result.json");
assertOperationResult(fixture);
const cases = read("spec/examples/operation-cases.json") as {
  name: string; patch: Record<string, unknown>; valid: boolean;
}[];
for (const example of cases) {
  assert.equal(isOperationResult({ ...fixture, ...example.patch }), example.valid, example.name);
}
for (const value of [NaN, Infinity, -Infinity]) {
  assert.equal(isOperationResult({ ...fixture, end_s: value }), false);
  assert.equal(isOperationResult({ ...fixture, observations: { intensity: value } }), false);
}
assert.equal(isOperationResult({ ...fixture, observations: { intensity: undefined } }), false);
const circular: Record<string, unknown> = {};
circular.self = circular;
assert.equal(isOperationResult({ ...fixture, observations: circular }), false);

const records = read("runs/protocol.json") as Record<string, unknown>[];
let observed = 0;
for (const record of records) {
  if ("result" in record) {
    assertOperationResult(record.result);
    observed += 1;
  }
}
assert.ok(observed > 0, "The runtime must produce instrument observations");
console.log(`Checked ${cases.length} protocol cases and ${observed} live operation results`);
