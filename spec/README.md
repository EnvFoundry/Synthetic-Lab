# Protocol v1

`synthetic-lab.schema.json` is the language-neutral boundary between scientific model packages,
experiment services and clients. It covers laboratory discovery, research contracts and immutable
operation results. Persistent database layout and domain equations are deliberately outside the
wire schema.

The protocol follows three rules:

1. **Scientific meaning is explicit.** Units, model versions, provenance, action semantics and
   validity conditions travel with discovery or results.
2. **Latent state stays owner-side.** A client receives observations and visible configuration,
   never specimen parameters, random state or verifier answers.
3. **Metadata stays in its declared maps.** Metadata maps permit additional keys; top-level
   fields retain their declared names and meanings. A changed interpretation requires a new protocol.

Bindings in `packages/protocol-ts` and `crates/protocol` implement the same field names. The fixture
in `spec/examples` and the accepted/rejected operation cases are shared by both bindings. Runtime
checks also require nonblank identifiers, finite times, end time at least start time and revisions
between 1 and JavaScript's largest exactly representable integer. The time ordering is a semantic
check in addition to JSON Schema's structural checks.

Maintained laboratories all provide a research contract. The field is optional on the wire so that
older external model packages can still be discovered. The catalogue's capabilities indicate its
presence.

Exercise the bindings with actual output from every installed instrument:

```sh
python -m pip install -e . -e examples/tank-package -e labs/optical-metrology
python scripts/export_protocol_fixtures.py runs/protocol.json
npm ci --prefix packages/protocol-ts
npm test --prefix packages/protocol-ts
cargo test --workspace --locked
cargo run --locked --example check_runtime -- runs/protocol.json
```

The Rust example parses and round-trips the catalogue and operations; TypeScript executes its
result assertions. Python tests check those same live descriptions and observations against the
JSON Schema. Domain equations remain in their scientific packages.
