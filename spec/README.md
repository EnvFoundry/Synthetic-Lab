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
3. **Additive evolution is preferred.** New optional metadata may be added within version 1;
   renamed fields or changed interpretations require a new protocol version.

Bindings in `packages/protocol-ts` and `crates/protocol` implement the same field names. The fixture
in `spec/examples` is parsed by both bindings. Python remains the reference scientific API; the
bindings are not duplicate simulators.
