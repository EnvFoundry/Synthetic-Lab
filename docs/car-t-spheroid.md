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

In the bundled 18 h experiment, the untreated branch ended with 264 viable tumor cells. Fast-, intermediate- and slow-off CAR designs left 88, 69 and 67 viable cells. Increasing dwell time raised cumulative kills from 153 to 203, but mean exhaustion rose from 0.0298 to 0.0396, the infiltrating fraction fell from 0.175 to 0.1125, and the antigen-low fraction among surviving tumor cells rose from 0.659 to 0.881. The fast-off design generated 1,058 serial contacts and was selected by the stated joint burden–escape–exhaustion–infiltration objective.

The principal measurements are viable tumor cell count, residual viable burden relative to a matched untreated branch, antigen-low fraction among survivors, CAR-T infiltration depth, continuous exhaustion, cumulative contacts and cumulative kills. The model is intended for comparative in-vitro questions and CAR design hypotheses, not clinical prediction.
