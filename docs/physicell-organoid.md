# Tumor-organoid treatment response with PhysiCell

The `physicell-tumor-organoid` laboratory represents one assay well containing a seeded tumor
organoid section. An untreated session can be forked into multiple wells before treatment, preserving
the same hidden response parameters and initial random seed.

## Governing structure

BioFVM solves oxygen and therapeutic diffusion and decay. PhysiCell resolves off-lattice cell
mechanics, growth, oxygen-dependent proliferation and necrosis, intracellular damage and repair, and
damage-dependent apoptosis. Treatment enters through the culture boundary during a finite exposure
window and is removed during recovery. A high-repair subpopulation is assigned before treatment, so a
strong exposure can reduce total viable burden while enriching the surviving resistant fraction.

The public experiment is:

```text
untreated organoid
        │
        ├── fork → concentration c1 → exposure → recovery → imaging
        ├── fork → concentration c2 → exposure → recovery → imaging
        └── fork → concentration c3 → exposure → recovery → imaging
```

Available endpoint panels report viability, apoptosis, necrosis, hypoxia, resistant survivors,
equivalent diameter, mean damage and mean local therapeutic concentration. `snapshot` returns the
cell-resolved final map and therefore uses the repository's external data layer when it exceeds the
configured threshold.

## Interpretation

The model can separate three causes of weak apparent response:

1. poor transport, visible as low intracellular therapeutic concentration toward the organoid core;
2. hypoxia-associated quiescence and necrosis;
3. high repair in a pre-existing resistant subpopulation.

It cannot identify a clinical treatment for an individual patient. That requires measured organoid
geometry, drug-specific transport and pharmacodynamics, stromal and immune compartments where
relevant, and predictive performance on doses and schedules not used to fit the model.
