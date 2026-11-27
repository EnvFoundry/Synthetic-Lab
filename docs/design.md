# Design

An experiment changes a persistent physical situation and receives a restricted observation of that situation. Scientific goals and the decision to continue belong to the researcher. A task can attach a reward and a budget to the same experiment.

## State, observations and time

A model implements `initial(rng)`, `advance(state, seconds)`, `perform(state, rng, action, parameters)` and `visible(state)`. Its state is a finite JSON object containing `time_s`. It includes every latent variable that affects future evolution. The runtime saves that state and the complete random generator state. Instrument controls appear in `visible`; latent parameters remain in the owner-held database.

`perform` mutates a private state copy and returns instrument observations. Readings use a `value` and `unit`; sensor noise standard deviations are explicitly labelled. Arrays additionally describe their shape and axes. Values can be saturated or missing according to the instrument. Numerical values and JSON serialization must remain finite.

The built-in models advance simulation time only during actions and waiting. Their action durations are part of their physical description. Closing a Python process preserves the experiment at its last committed simulation time. A wall-clock-driven device requires its own execution semantics and IOP coordination. In a cloud deployment an agent process may disconnect while an instrument is still running; that requires a durable device operation, observation of its actual outcome, and resource ownership.

## Operations and workers

SQLite stores ordered operations with pending, running, succeeded and failed states. Submission and
claiming use short transactions. A worker reads a committed state, releases the database write lock,
and runs the domain model. The final state, result and snapshot are committed together. Different
sessions can compute concurrently; operations on one session follow submission order.

Each claim has a distinct attempt identifier and a renewable lifetime. Reusing a worker name does
not let an earlier computation finish a newer claim. After a worker exits, another worker can
recalculate the unfinished operation from its original committed state. This does not resume an
intermediate numerical step. Models must keep external side effects with IOP.

Completed operation identifiers return their original result for the same normalized request. A
failed request submitted again joins the end of its session queue. An explicit expected revision
is compared with the state before execution. The synchronous `act` method computes locally and
requires the domain package; `submit`, `operation` and `wait_operation` support detached clients.

Sessions retain their public action description and initial configuration. Later configurations
come from completed operation results. A client can describe, submit, observe and fork an existing
session without loading its solver or materializing its hidden arrays. Creation runs in an
environment containing the domain package. For older databases, call `describe_session(id)` once
in that environment to populate each existing session's description.

SQLite WAL is used by processes on one host. Multi-host scheduling needs a server database.
Large JSON values live in the [external data store](artifacts.md). Histories and file exports are
read in batches. A saved snapshot can be branched while its parent is computing; the branch starts
from committed state and does not inherit queued work.

## Resumption, branches and versions

Every committed revision has a state and random-state snapshot. `fork(at_revision=...)` starts a new branch whose revision counter begins at zero. It retains the source model, configuration, profile references, simulation time and latent state. Parent identity, parent revision and common lineage identify related data. A branch's exported operations start at its fork; recover its earlier history through the parent reference.

Branches initially share the same pseudorandom state for matched comparisons. Different measurement sequences consume that state differently. For independent specimens, use `create` with different seeds. For dataset splits, group branches by lineage and consider device or batch grouping as appropriate.

Executing an operation compares the stored model version with the installed implementation. A mismatch raises a conflict so that migration or an older model version can be selected explicitly. A new physics interpretation should carry a new model version. Old database records without a profile reference retain `theory` as their recorded model origin.

## Extending the science

Installed entry points in `synthetic_lab.models` provide domain model classes. The registration name is unique. The registry is cached per process, so restart after installing a plugin. Dependencies and solvers belong to the domain package. The independently packaged tank is a working example of this path.

The runtime treats a model as the owner of one coherent simulated scene. The thermal model couples electrical and thermal processes internally. Multiple independent sessions currently represent different scenes. Cross-package exchange of a common specimen needs explicit sample identity, state transfer, units, boundary conditions and a coupling algorithm. A future implementation should start with a useful coupled experiment and preserve the ownership rules in the charter.

The conversion table covers the built-in instrument units. A domain can use a new canonical unit without modifying the runtime. Conversions into that unit require an explicit converter. A JSON quantity already expressed in the canonical unit is accepted. Dimensional compatibility alone cannot establish reference-plane, coordinate-frame or calibration equivalence.

## Scientific records and trust

The Python API and SQLite database belong to a trusted experiment owner. The MCP server gives its host control of that database's research sessions. A scored Agent receives only the tools for its assigned episode. The Verifiable Agent Gym adapter owns an isolated database and keeps the reference thermal resistance in the verifier. Evaluators should run agents without filesystem access to the owner database or process.

Model parameters, calibration references and observations have different roles. `provenance` records whether a configured model was built from theory, simulation or measurements, plus a data reference. Future readouts from that model still carry `source=simulation`. Original traces are retained when a new calibrated session is created.

The runtime validates arguments and finite serialization. Physical validity is established by each model's equations, numerical accuracy, operating conditions and empirical comparison. The repository includes tests for energy and charge balance, known limits, monotone time, failure rollback, repeatable resumption and independent branches. Adding a real device requires measurements under independent conditions before declaring a device-specific fidelity range.
