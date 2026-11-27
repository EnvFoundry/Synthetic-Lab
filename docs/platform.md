# Polyglot platform boundary

Synthetic Lab uses several languages for distinct responsibilities rather than duplicating one
runtime in several languages.

| Layer | Primary language | Responsibility |
|---|---|---|
| Scientific models, calibration and learning | Python | Equations, solvers, uncertainty, domain packages and rapid scientific development |
| Operation workers | Python now; Rust for the service implementation | Claim queued work, execute domain solvers outside database transactions and commit results |
| Product and agent SDK | TypeScript | Web control plane, experiment graph, typed clients, dashboards and human/agent interaction |
| Durable relational state | SQL | Sessions, ordered operations, worker claims, model profiles and queryable lineage |
| High-performance kernels | C, C++, CUDA or external solvers | PDE, molecular, imaging and device-specific numerical kernels |

The repository supplies a JSON Schema, TypeScript types, Rust types and an executable SQLite
layout. They describe the Python runtime; they do not introduce a second source of scientific
behavior.

## Operation lifecycle

A client submits an operation in a short database transaction. A worker claims the earliest
operation for a session, copies the saved state and random state, and releases the database write
lock. The domain solver then runs in the worker process. A second short transaction commits the new
state, immutable result and snapshot together.

Operations on one session remain ordered. Different sessions can run concurrently. A worker names
the laboratories installed in its environment, so optical, biological and native-solver workers do
not need one shared dependency environment. A claim has a renewable lease; unfinished work can be
continued by another worker from the last committed experimental state.

The local `act` call preserves the original synchronous interface by submitting and executing the
operation in the caller. `submit` plus `operation` exposes the same lifecycle to long-running
services, CLI clients and MCP hosts.

Clients use saved session descriptions and public configurations without importing domain
solvers. Creating a specimen and using synchronous local `act` still require its domain package.
The current SQLite worker deployment runs on one host.

## Shared data boundary

The shared protocol contains:

- model identity and model implementation identifier;
- action parameter schemas;
- research contracts;
- operation identity, state and resulting session revision;
- normalized parameters, simulation interval, observations and visible configuration;
- model provenance and source labels.

It excludes:

- latent specimen state and random-generator state;
- domain implementation classes;
- database credentials and tenant policy;
- solver-specific arrays that belong in external data storage;
- task rewards and hidden answers owned by an evaluator.

The implemented TypeScript and Rust types cover laboratory descriptions, completed operation
results and external data references. Queue execution and claim handling currently live in Python.
The Rust service and TypeScript workbench remain future implementations.

A Rust service can implement the same claim, lease and commit lifecycle while calling Python or
native solver processes. A TypeScript client can submit operations, display their state and stream
completed results. Neither reimplements reaction, battery, optical, biological or thermal equations.

## Compatibility

Protocol additions may add optional metadata without changing existing field meaning. A changed
interpretation or required field uses a separate protocol definition. Bindings parse the same live
runtime output in continuous integration.
