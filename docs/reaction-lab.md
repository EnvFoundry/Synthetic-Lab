# Selective reaction laboratory

The `reaction` laboratory is a reduced-order environment for experiment design in catalysis and
chemical synthesis. It is not a calibrated compound model. Its purpose is to make four coupled
choices operational: reaction temperature, finite experiment time, catalyst deactivation and
measurement modality.

## State and kinetics

A constant-volume, well-mixed batch contains consecutive irreversible reactions

\[
A \xrightarrow{k_1(T)a_c} B \xrightarrow{k_2(T)a_c} C,
\qquad
k_i(T)=A_i\exp\left(-\frac{E_i}{RT}\right),
\]

where `a_c` is catalyst activity. Activity decays according to

\[
\frac{d a_c}{dt}=-k_d(T)a_c.
\]

For each short integration interval, the consecutive first-order concentration update is
analytical and conserves `A + B + C`. Catalyst activity, temperature and reaction rates are then
advanced together at intervals of at most 0.5 s.

The reactor temperature follows a lumped energy balance. Exothermic reaction heat, ambient heat
loss and a bounded proportional jacket controller determine the temperature trajectory. Crossing
the configured shutdown temperature latches thermal protection and changes the target to ambient.

## Instruments

| Instrument | Duration | Observation | Scientific role |
|---|---:|---|---|
| Thermometer | 0.2 s | Reactor temperature | Fast process state, no composition information |
| Spectrometer | 1 s | Three mixed absorbance channels | Frequent but composition-ambiguous signal |
| Chromatograph | 20 s | Species-resolved A, B and C | Slow, directly interpretable composition measurement |

All instruments observe one continuing latent reaction state. A chromatographic measurement is
therefore not a free query: reaction and deactivation continue during its acquisition.

## Reference experiment

`examples/optimize_reaction.py` creates one specimen and forks it before applying three equal-time
temperature programmes. It uses only public measurements and selects the programme with the
highest measured intermediate-B concentration. Sharing the initial state makes the comparison
about the intervention rather than specimen-to-specimen variation.

```sh
python examples/optimize_reaction.py
```

The example is deliberately small. A research-grade chemistry package should add compound-specific
reaction networks, calibrated spectra, realistic sampling and mixing, uncertainty over mechanisms,
and prediction on measurements held out by batch, instrument or temperature schedule.

## What this model can and cannot establish

It can support algorithm development for active measurement, kinetic identification, selective
process control, model discrimination and branch-based counterfactual comparison. It checks mass
conservation, nonnegative concentrations, persistent hidden parameters and thermal protection.

It cannot establish a synthesis route, yield, safety envelope or catalyst lifetime for a real
chemical system. Those claims require a named material system, measured kinetics and heat release,
instrument calibration, independent validation, and an apparatus-specific operating range.
