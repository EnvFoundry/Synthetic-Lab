# Development direction

Synthetic Lab should let a researcher investigate valuable phenomena for as long as the question requires. Its common structure is experimental objects, actions, observations, time and history. Domain experts supply the science and the conditions under which a prediction can be trusted.

## Current implementation

Version 0.2 has four built-in laboratories (fiber, thermal, battery and selective reaction), two optical-metrology laboratories (thin-film fabrication and fluorescence microscopy), and an independently packaged fluid-tank example. All seven expose research questions, instruments, physical relations and assumptions through the same catalogue. Persistent sessions, experiment branches, CLI, MCP, Gymnasium and Verifiable Agent Gym reuse the local runtime. JSON Schema, TypeScript and Rust describe the public data boundary and are exercised with live experimental output. Model coefficients currently come from synthetic priors or explicitly supplied configurations.

## Experiments that would extend its scientific value

| Contribution | Concrete experiment and expected deliverable |
|---|---|
| Calibrated optical bench | Measure repeatability, detector response, drift and coupling curves from a named bench. Fit on selected runs, predict held-out movements and exposure changes, and state errors in mrad, W and camera counts |
| Thermal and fluid devices | Compare a one-body model with a distributed solver under transients. Add a second thermometer or change a flow boundary when the models disagree measurably |
| Materials and fabrication | Follow one identified sample through fabrication, spectroscopy and thermal cycling. Predict which remaining process change can correct a measured deviation |
| Energy and aging | Add an empirical voltage curve, temperature-dependent impedance and an aging model. Use later cycle data to assess predictions from short test sequences |
| Mechanics and assembly | Model contact, friction, compliance and measurement limits. Reproduce an assembly across held-out component tolerances |
| Scientific imaging | Add optical transfer, exposure history and bleaching or drift supported by measurements. Let a researcher change acquisition strategy and compare information gained per sample dose |
| Environmental experiments | Include evolving boundary conditions and observation windows. Compare sampling plans under measured spatial and temporal correlations |

Each addition should include an independent user's experiment, an executable reference method, recorded assumptions, a held-out condition and the physical meaning of its outputs. An early analytical model is a useful contribution when its scope is explicit. An empirical fidelity claim needs the corresponding real-world comparison.

## Shared infrastructure to grow with use

Cross-domain sample transfer needs stable sample identity, ownership of each state variable and an executable coupled example. Multi-rate co-simulation needs time synchronization, exchanged boundary conditions and a measured coupling error. Integration with IOP needs operation reconciliation after uncertain outcomes, shared resource ownership and device-limited timing. A digital twin needs a named physical counterpart, model updates from new measurements and a demonstrated use of its predictions in subsequent experiments.

A multi-user cloud deployment needs persistent workers, object storage for large artifacts, resource queues, tenant-aware permissions and demonstrated recovery under its target load. The local runtime provides experiment semantics that a service can reuse. Scheduling real hardware remains with its device runtime. Separate independent training workers to scale simulation before adding shared coordination.

## Keeping research and evaluation useful

Preserve fixed versions of reference experiments so that progress remains comparable. Add new batches, devices and challenging interventions as new versions. Keep calibration and model selection away from the observations used to assess them. Include appropriate domain methods alongside agent baselines, and report physical results, experiment time, specimen use and computational cost.

When a physical correction changes an answer, update the model version and rerun the relevant methods. An experiment that distinguishes two plausible models can be more valuable than a higher score on an already-solved task. Preserve failed attempts when they identify a useful constraint or rule out a design.
