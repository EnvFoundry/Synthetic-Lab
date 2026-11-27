# Meep photonic-cavity laboratory

`meep-photonic-cavity` turns a full-wave electromagnetic simulation into a persistent device
experiment.

## Device and instruments

The represented device is a dielectric waveguide perforated by a periodic sequence of air holes.
A larger central spacing forms a defect cavity. The commanded design contains hole radius and defect
spacing. Fabrication draws one hidden radius and spacing offset from the seeded process distribution;
every later measurement uses the same sample.

Broadband transmission uses two Meep runs:

1. a straight waveguide establishes incident flux;
2. the fabricated cavity gives transmitted flux.

Their ratio is reported versus wavelength. A central-band peak gives the resonance wavelength,
transmission contrast and a sampled quality-factor estimate. The reported resonance contains both
the strongest sampled wavelength and, when the local three-point shape supports it, a quadratic
sub-bin estimate. Field imaging requires a prior spectrum or resonance measurement, then runs a
narrowband calculation at that measured resonance and returns a two-dimensional electric-field
intensity map.

## Research use

The laboratory supports:

- resonance targeting under fabrication variation;
- adaptive selection of spectral measurements;
- comparison of approximate optical models with full-wave Maxwell simulation;
- experiment branches that share the same fabrication draw;
- large field maps stored outside the operation database;
- independent Meep workers serving lightweight clients.

The bundled design experiment compares defect spacings of 1.25, 1.40 and 1.55 μm under the same
fabrication draw. With 8 pixels per micrometre and 21 frequency samples, all three strongest sampled
resonances occurred at 5.37634 μm, inside a 5.35 ± 0.20 μm target band. Their normalized spectral
contrasts were 0.62021, 0.40788 and 0.33083, so the 1.25 μm design was selected. The experiment does
not infer equal physical resonance wavelengths from a shared coarse spectral bin.

The current model is two-dimensional, nondispersive and lossless. A device-specific successor should
import measured refractive index, SEM geometry and spectrometer response, then predict spectra for
devices and wavelengths not used to fit those quantities.
