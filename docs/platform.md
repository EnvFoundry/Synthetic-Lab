# Polyglot platform boundary

Synthetic Lab should use several languages for different reasons, not duplicate one runtime in
several languages.

| Layer | Primary language | Responsibility |
|---|---|---|
| Scientific models, calibration and learning | Python | Equations, solvers, uncertainty, domain packages and rapid scientific development |
| Deterministic execution service | Rust | Durable workers, cancellation, resource ownership, high-concurrency state transitions and binary solver adapters |
| Product and agent SDK | TypeScript | Web control plane, experiment graph, typed clients, dashboards and human/agent interaction |
| Durable relational state | SQL | Sessions, operations, model profiles, resource leases and queryable lineage |
| High-performance kernels | C, C++, CUDA or external solvers | PDE, molecular, imaging and device-specific numerical kernels |

The repository begins this separation with a JSON Schema, TypeScript types, Rust types and an
executable SQLite migration. They describe the existing Python runtime; they do not introduce a
second source of scientific truth.

## Stable boundary

The shared protocol contains:

- model identity and version;
- action parameter schemas;
- research contracts;
- immutable operation identity and revision;
- normalized parameters, simulation interval, observations and visible configuration;
- model provenance and source labels.

It excludes:

- latent specimen state and random-generator state;
- domain implementation classes;
- database credentials and tenant policy;
- solver-specific arrays or checkpoints that belong in artifact storage;
- task rewards and hidden answers owned by an evaluator.

The first Rust service should therefore wrap the operation lifecycle and call Python or native
solver workers through this boundary. The first TypeScript client should render the catalogue,
construct valid actions and stream immutable results. Neither should reimplement the reaction,
battery, optical or thermal equations.

## Evolution

Version 1 permits additive metadata while preserving field meaning. A changed interpretation,
renamed required field or different operation identity rule requires a new protocol version.
Bindings must parse the same fixture and CI must type-check or round-trip them independently.
