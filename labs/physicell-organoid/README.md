# PhysiCell tumor-organoid laboratory

`physicell-tumor-organoid` represents one tumor-organoid assay well. It uses the official PhysiCell
1.14.2 `cancer_biorobots` project as its numerical base, removes the delivery robots, supplies a
therapy through the culture boundary, and adds seeded sensitive and high-repair tumor phenotypes.
BioFVM resolves oxygen and treatment transport; PhysiCell resolves cell mechanics, proliferation,
hypoxic necrosis, damage, repair and apoptosis.

The laboratory is intentionally one-well/one-exposure. Fork an untreated session to compare dose,
exposure and recovery conditions under the same hidden patient-response draw.

## Build the external solver

```sh
git clone --depth 1 --branch 1.14.2 https://github.com/MathCancer/PhysiCell.git ../PhysiCell-organoid
python labs/physicell-organoid/build_physicell.py ../PhysiCell-organoid
make -C ../PhysiCell-organoid -j2
export PHYSICELL_ORGANOID_EXECUTABLE="$PWD/../PhysiCell-organoid/organoid_therapy"
python -m pip install -e . -e labs/physicell-organoid
python examples/screen_tumor_organoid.py
```

The build script patches only a disposable PhysiCell checkout. It does not copy PhysiCell source into
this package. The executable and its generated `config/PhysiCell_settings.xml` remain in that checkout.

## Current scientific scope

This is a generic mechanistic assay, not a prediction for a named patient or compound. A calibrated
successor should replace the hidden response distribution with measurements from one organoid line,
fit compound-specific transport and damage parameters, and test held-out doses, exposure schedules
and organoid sizes.
