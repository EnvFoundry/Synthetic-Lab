# Protocol v1

`synthetic-lab.schema.json` is the language-neutral boundary between scientific model packages,
experiment services and clients. It covers laboratory discovery, research contracts and immutable
operation results. Persistent database layout and domain equations are outside the wire schema.

The protocol follows three rules:

1. **Scientific meaning is explicit.** Units, model identifiers, provenance, action semantics and
   validity conditions travel with discovery or results.
2. **Latent state stays owner-side.** A client receives observations and visible configuration,
   never specimen parameters, random state or evaluator answers.
3. **Metadata stays in its declared maps.** Metadata maps permit additional keys; top-level
   fields retain their declared names and meanings.

Large values use an artifact reference in the position where the inline JSON value would otherwise
appear:

```json
{
  "$artifact": {
    "id": "5f16a5f40e5d4cf5b4a1d8d9d329a5ae",
    "uri": "artifact://5f16a5f40e5d4cf5b4a1d8d9d329a5ae",
    "media_type": "application/json",
    "encoding": "utf-8",
    "size_bytes": 4823
  }
}
```

The containing observation still carries its units, shape, axes, acquisition window and other
scientific metadata. The artifact contains only the externalized value. Clients can decide whether
to display metadata, retrieve the value, or pass the reference to a domain computation service.

Bindings in `packages/protocol-ts` and `crates/protocol` implement the same field names and artifact
reference. The fixtures in `spec/examples` and the accepted/rejected operation cases are shared by
both bindings. Runtime checks also require nonblank identifiers, finite times, end time at least
start time and revisions between 1 and JavaScript's largest exactly representable integer.

Maintained laboratories all provide a research contract. The field is optional on the wire so that
older external model packages can still be discovered. The catalogue's capabilities indicate its
presence.

Exercise the bindings with actual output from every installed instrument:

```sh
python -m pip install -e . -e examples/tank-package -e labs/optical-metrology \
  -e labs/spectroscopic-bioprocess
python scripts/export_protocol_fixtures.py runs/protocol.json
npm ci --prefix packages/protocol-ts
npm test --prefix packages/protocol-ts
cargo test --workspace --locked
cargo run --locked --example check_runtime -- runs/protocol.json
```

The live export uses a small artifact threshold so at least one real image or field crosses the
external-data boundary. Rust and TypeScript parse the same descriptions, operation results and
artifact references. Domain equations remain in their scientific packages.
