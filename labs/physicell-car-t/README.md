# PhysiCell CAR-T spheroid laboratory

`physicell-car-t-spheroid` is a three-dimensional solid-tumor co-culture backed by PhysiCell 1.14.2 and BioFVM. One session represents one seeded tumor spheroid before immune-cell addition. Fork the untreated session to compare CAR designs or doses under the same cell-level antigen distribution and hidden patient-response draw.

The model resolves:

- tumor growth, oxygen uptake and oxygen-dependent death;
- CAR-T chemotaxis toward tumor-derived immunostimulatory factor;
- antigen-dependent attachment and killing;
- finite receptor dwell time through stochastic detachment;
- contact- and hypoxia-driven exhaustion with disengaged recovery;
- pre-existing antigen-negative cells and contact-induced antigen loss;
- cell-resolved tumor and CAR-T positions, antigen, oxygen and exhaustion.

The public intervention is:

```python
result = spheroid.act(
    "infuse",
    car_t_cells=160,
    pre_growth_hours=0,
    treatment_hours=18,
    attachment_rate_per_min=0.20,
    dwell_time_min=15,
    kill_rate_per_min=0.08,
    motility_speed_um_min=1.0,
)
```

Build the external solver from a disposable PhysiCell checkout:

```bash
git clone --depth 1 --branch 1.14.2 https://github.com/MathCancer/PhysiCell.git ../PhysiCell-car-t
python labs/physicell-car-t/build_physicell.py ../PhysiCell-car-t
make -C ../PhysiCell-car-t -j2
export PHYSICELL_CART_EXECUTABLE="$PWD/../PhysiCell-car-t/car_t_spheroid"
export PHYSICELL_CART_CONFIG="$PWD/../PhysiCell-car-t/config/PhysiCell_settings.xml"
python -m pip install -e . -e labs/physicell-car-t
python examples/compare_car_t_kinetics.py
```

The environment is a comparative mechanistic assay. It is not calibrated to a named tumor, antigen, CAR construct or patient and does not produce clinical treatment recommendations.
