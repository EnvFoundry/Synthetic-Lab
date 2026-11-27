# Meep photonics laboratory

This package connects Synthetic Lab to Meep for full-wave, time-domain spectroscopy of a
photonic-crystal waveguide cavity.

## Install

Meep is distributed through conda-forge rather than PyPI.

```sh
conda env create -f labs/meep-photonics/environment.yml
conda activate synthetic-lab-meep
python -m pip install -e .
python -m pip install -e labs/meep-photonics
```

## Experiment

A session starts as an unfabricated design. `design` changes the commanded hole radius and central
defect spacing. `fabricate` creates one persistent sample whose actual geometry includes seeded
variation. Later measurements reuse that same hidden geometry.

```python
from synthetic_lab import Lab

with Lab("runs/photonics.sqlite") as lab:
    sample = lab.create("meep-photonic-cavity", seed=7)
    sample.act("design", hole_radius=0.36, defect_spacing=1.40)
    sample.act("fabricate")
    spectrum = sample.act("measure", instrument="spectrum")
    resonance = sample.act("measure", instrument="resonance")
    field = sample.act("measure", instrument="field")
```

The spectrum is normalized by a separate straight-waveguide simulation with the same source,
monitor, cell and resolution. Meep supplies the Maxwell solver. Synthetic Lab supplies sample
identity, fabrication variation, experiment time, branching, workers, observations and external
storage for spectra and field maps.

Field acquisition drives the device at the peak inferred from the latest noisy public spectrum.
A new spectrum replaces that drive frequency and discards the previous field image. The image is
the complex-field intensity after `field_run_time` Meep time units; a steady-state field requires
increasing that duration until the result settles. The reported linewidth is interpolated between
the two half-prominence crossings. Quality factor is absent when those crossings are not resolved
inside the sampled band. It is a spectral estimate, not a cavity-decay measurement.

Model 2 corrects frequency selection and linewidth extraction. Stored model-1 results remain
readable; continuing a model-1 session requires its original implementation.

The present geometry is two-dimensional and uses a lossless, nondispersive dielectric. It is suited
to device-design, spectroscopy and model-selection experiments, not to direct prediction of a
specific fabricated chip without measured material and geometry data.
