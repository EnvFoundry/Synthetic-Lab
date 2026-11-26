# Frontier laboratory atlas

Synthetic Lab should not maximize the number of domains. It should concentrate on experimental
systems where causal intervention is expensive, slow or scarce; where simulation can expose a
useful hidden state; and where a model can be challenged by measurements. The following atlas is
a build order, not a list of folders to create at once.

## Highest-leverage laboratory families

| Priority | Laboratory family | Questions worth making executable | Minimum useful implementation |
|---|---|---|---|
| 1 | Materials synthesis and catalysis | Which composition, process and temperature path produces a target phase or property? Which measurement best distinguishes competing mechanisms? | Reaction/process state, synthesis actions, spectroscopy or diffraction observations, failed products, active experiment design and held-out recipes |
| 2 | Predictive biology and bioprocess | How does a cell population respond to a perturbation? Which intervention changes phenotype while preserving viability? | Cell-state dynamics, perturbations, batch effects, partial assays, dose and time, population variability and out-of-distribution perturbations |
| 3 | Electrochemical energy | Which pulse or cycling protocol identifies state, degradation and usable power with minimum specimen use? | Charge, transport and thermal state; impedance or voltage observations; aging interventions and held-out duty cycles |
| 4 | Semiconductor and photonic fabrication | Which process change corrects linewidth, layer, loss or spectral deviation? | Process genealogy, geometry/material state, metrology transfer functions, fabrication tolerances and sample-level provenance |
| 5 | Scientific imaging and characterization | Which acquisition reveals the structure with minimum dose, time or beam damage? | Sample state, image formation, instrument aberrations, adaptive acquisition, uncertainty and irreversible exposure effects |
| 6 | Fusion and plasma control | Which actuator schedule keeps a plasma in a useful regime while avoiding disruptive states and material limits? | Multi-rate plasma state, actuators, delayed measurements, constraints, surrogate or reduced physics and rare-event scenarios |
| 7 | Earth, climate and environmental systems | Which observations and interventions reduce uncertainty in local hazards, resources or emissions? | Coupled fields, spatial sampling, evolving boundaries, data assimilation, scenario branching and scale-aware uncertainty |
| 8 | Mechanics, manufacturing and robotics | Which sequence assembles or processes variable parts robustly? Which sensor resolves contact or defect state? | Geometry, contact, compliance, tolerances, wear, sensing, action failure and transfer across specimens |
| 9 | Quantum devices and control | Which pulses identify drift and noise, and which control remains robust across devices? | Hamiltonian or circuit state, calibration drift, finite measurements, decoherence, control constraints and held-out devices |

The first five families combine high scientific value with relatively direct experimental
observations and clear closed-loop decisions. Fusion and Earth systems have exceptional value but
require heavier multiscale solvers and carefully separated fidelity levels. Robotics and quantum
systems are strong cross-domain tests of partial observability, timing and device variation.

## Build common mechanisms, not one-off simulators

Domain laboratories should compose a small set of reusable scientific kernels:

- **reaction and transformation** — kinetics, phase change, growth, degradation and population
  transitions;
- **transport** — heat, mass, charge, fluid and particle transport across scales;
- **waves and fields** — optics, electromagnetics, acoustics, plasma and quantum evolution;
- **mechanics and contact** — rigid and deformable bodies, friction, fracture and assembly;
- **image formation and metrology** — illumination, transfer functions, detector statistics,
  calibration and finite dynamic range;
- **process genealogy** — samples, batches, fabrication steps, irreversible history and transfer
  between instruments;
- **decision and control** — action duration, resource use, delayed outcomes, constraints and
  experiment branching.

A domain package may use a closed-form model, SciPy/JAX, finite elements, molecular simulation,
a learned surrogate or an external co-simulator. All of them should expose the same laboratory
semantics and research contract.

## Fidelity progression

A valuable laboratory should evolve vertically rather than accumulating unrelated examples.

| Stage | Deliverable |
|---|---|
| Mechanism | Transparent analytical or reduced-order model with governing relations and tests |
| Discrimination | Experiments that distinguish plausible parameters or models from observations |
| Cross-fidelity | A higher-fidelity solver or surrogate compared on the same interventions |
| Empirical calibration | Named data, operating range, uncertainty and held-out prediction |
| Physical closure | The prediction changes a real experiment, and the resulting measurement updates the model |

The promotion criterion is not lower simulation error on fitted trajectories. It is improved
prediction or decision quality on a new condition that matters scientifically or operationally.

## Platform boundary

Synthetic Lab owns simulated state, experiment time, observations, branches and model scope. IOP
owns real instrument execution. Domain repositories own specialized solvers and empirical assets.
Verifiable Agent Gym owns task budgets and hidden assessment. Data systems retain trace and sample
lineage. A shared wire protocol should connect these layers without moving domain equations into
the runtime.

## Selected precedents

- A-Lab: autonomous closed-loop inorganic synthesis and characterization —
  <https://doi.org/10.1038/s41586-023-06734-w>
- Self-driving laboratories for chemistry and materials —
  <https://doi.org/10.1038/s44160-022-00231-0>
- National Academies, *Foundational Research Gaps and Future Directions for Digital Twins* —
  <https://doi.org/10.17226/26894>
- NIST digital twins for advanced manufacturing —
  <https://www.nist.gov/programs-projects/digital-twins-advanced-manufacturing>
- Arc Virtual Cell Initiative — <https://arcinstitute.org/virtual-cell>
- Destination Earth digital twins — <https://destination-earth.eu/>
