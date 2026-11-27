# Solid-tumor CAR-T spheroid

The `physicell-car-t-spheroid` laboratory studies a question that cannot be reduced to nominal binding affinity: how receptor engagement kinetics alter the spatial and functional trajectory of engineered T cells inside a solid tumor.

A session begins as one seeded three-dimensional spheroid. Experiment branches preserve the same tumor geometry, cell-level antigen distribution and hidden response draw. Each branch can then receive a different CAR-T design:

```text
seeded spheroid
      │
      ├── no CAR-T
      ├── slow detachment / long dwell
      ├── intermediate dwell
      └── fast detachment / short dwell
```

The modeled state of each CAR-T cell includes position, engagement state, cumulative contact time, contact count, kill count and a continuous exhaustion variable `e` on `[0, 1]`. During tumor contact and hypoxia,

```text
de/dt = (k_contact * I_contact + k_hypoxia * H(O)) * (1 - e)
        - k_recovery * I_free * e.
```

Exhaustion reduces both killing and motility but does not make either identically zero. Tumor-cell recognition depends on a separate CAR-target antigen variable rather than the growth-driving oncoprotein in the upstream example. Antigen is heterogeneous before treatment and can decrease during CAR-T contact.

The environment therefore separates four failure modes:

1. insufficient CAR-T delivery;
2. poor penetration into the spheroid;
3. functional exhaustion after repeated or prolonged engagement;
4. survival of an antigen-low or antigen-negative remnant.

Tumor control is compared by residual viable cell burden relative to a forked untreated spheroid, not by the fraction of cells still viable at the endpoint. Dead-cell clearance can leave a treated remnant with a viable fraction near one even when most of the original burden has been eliminated.

Model 2 counts a kill only when a live target enters apoptosis, even when several CAR-T cells
share that target. Killing and detachment are competing hazards: an event occurs with probability
`1 - exp(-(kill + off) * dt)` and is a kill with probability `kill / (kill + off)`. Contact and kill
totals persist when individual immune cells disappear. Contact-induced antigen loss runs on the
mechanics clock, so a short engagement does not consume a full six-minute phenotype interval.

CAR-T cells are placed uniformly by volume in a bounded spherical shell outside the actual tumor
at infusion. The same infusion-time radius is retained for infiltration measurements after treatment;
it does not shrink as tumor cells die. A shell that cannot fit the configured domain stops the assay
before creating cells. Solver exceptions propagate to the operation instead of returning partial
endpoints. Culture time ends at the requested time, including fractional infusion times.

The bundled 18 h example with seed 2029 and one OpenMP thread gave these model-2 results:

| Design | Live tumor cells | Antigen-low live cells | Contacts | Kills | Infiltrating fraction | Mean exhaustion |
|---|---:|---:|---:|---:|---:|---:|
| No CAR-T | 289 | 69 | 0 | 0 | 0 | 0 |
| 5 min dwell | 80 | 63 | 966 | 153 | 0.18125 | 0.02636 |
| 20 min dwell | 86 | 72 | 427 | 148 | 0.15000 | 0.02541 |
| 90 min dwell | 85 | 75 | 259 | 155 | 0.35625 | 0.02752 |

These replace the earlier model-1 numbers. This draw does not support a monotonic loss of
infiltration as dwell time increases. The illustrative weighted objective selects 5 min, but the
weights express a research preference; additional seeds and parameter populations are needed to
estimate a ranking or a Pareto surface. Antigen-low cell count and fraction are both reported, since
enrichment among survivors can coexist with a reduction in their absolute number.

One `infuse` operation runs the entire culture. Reads and snapshots expose ideal simulated endpoints
without assay noise; mid-culture observations and further infusions are not implemented. Fractions
and means for empty populations use zero alongside the corresponding counts. The retained
`equivalent_diameter` field is the origin-centred bounding diameter. The default is one OpenMP
thread; identical seeds need not produce identical trajectories with multiple threads.

Stored model-1 results remain readable. Continuing model-1 operations requires the original Python
implementation and executable. Rebuild the C++ executable when installing model 2.

The principal measurements are viable tumor cell count, residual viable burden relative to a matched untreated branch, antigen-low fraction among survivors, CAR-T infiltration depth, continuous exhaustion, cumulative contacts and cumulative kills. The model is intended for comparative in-vitro questions and CAR design hypotheses, not clinical prediction.
