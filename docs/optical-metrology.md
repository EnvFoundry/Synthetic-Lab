# Optical metrology laboratories

Optical measurements connect a large fraction of experimental science: they can observe chemical
composition without contact, measure nanometre-scale film growth through interference, resolve
spatial structure, follow living samples and operate during fabrication. The optical-metrology
package turns two high-leverage cases into persistent experiments rather than isolated forward
functions.

## Thin-film deposition and endpoint selection

`thin-film` couples process history to three optical instruments. The hidden film state contains
physical thickness, porosity, effective refractive index, extinction, RMS roughness, temperature
and specimen-specific deposition gain. Material arrives only when the shutter is open. Elevated
temperature densifies the film and smooths the surface.
Annealing conserves solid material per unit area, \(d(1-p)\), so physical thickness decreases
as porosity \(p\) decreases. Deposition adds material with the as-deposited porosity.

At normal incidence, the complex reflection amplitude of a single film is

\[
r(\lambda)=\frac{r_{01}+r_{12}e^{2 i \delta}}
                   {1+r_{01}r_{12}e^{2 i \delta}},
\qquad
\delta=\frac{2\pi \tilde n_1 d}{\lambda},
\qquad
R=|r|^2.
\]

The convention is \(\tilde n=n+i\kappa\) with \(\exp(-i\omega t)\) time dependence, so positive
extinction attenuates propagation. An opaque film approaches its front-surface reflectance.
A roughness factor attenuates the reflected intensity. The broadband reflectometer returns eight
wavelength channels. The interferometer returns phase modulo \(2\pi\), so one wavelength alone
cannot determine absolute thickness. The pyrometer gives a fast temperature observation.

`examples/coat_thin_film.py` forks one starting specimen, applies three candidate deposition times,
then selects the spectrum closest to a target coating. This represents endpoint selection under
unknown growth-rate gain rather than direct access to thickness.

## Dose-limited fluorescence microscopy

`fluorescence-microscopy` contains a hidden sparse emitter field with shared positions, green and
red spectral weights and remaining fluorophore brightness. The camera uses a Gaussian
approximation to a diffraction-limited point-spread function,

\[
\sigma_{xy}^2 \approx \left(0.21\frac{\lambda}{\mathrm{NA}}\right)^2
+ (0.38\,\Delta z)^2.
\]

The Gaussian PSF is integrated over each pixel area. Light outside the finite field is lost.
The measurement includes background, detector offset, photon-dependent variance, read noise and
finite detector range. Sample drift continues during every action. Illumination dose irreversibly
reduces later fluorescence:

\[
F_{t+1}=F_t\exp(-k_b P\Delta t).
\]

Photon yield integrates this decay throughout the exposure using
\((1-\exp(-k_bP\Delta t))/(k_bP)\), with limit \(\Delta t\) at zero bleach rate.
Emitter positions are sampled at the exposure midpoint; intra-exposure motion blur is not modeled.
Excitation is synchronized to camera and photometer acquisitions; waiting and stage motion are dark.

The photometer and camera collect the same field. The photometer is fast and field-integrated;
the camera is slower and spatially informative.
`examples/adaptive_microscopy.py` compares a direct high-dose exposure with a low-dose focus sweep
followed by a shorter image, using branches from the same pre-illumination specimen.
The report includes total dose from focus search, final acquisition and the remaining-signal probe,
along with elapsed time. Raw Laplacian energy depends on photon dose as well as focus; it is used
to select focus among equal-exposure images, not as a dose-independent comparison of both routes.

## Why these two laboratories belong together

They share the same experimental structure while representing different scientific regimes:

| Property | Thin-film fabrication | Fluorescence microscopy |
|---|---|---|
| Persistent hidden state | Thickness, porosity, roughness, index | Emitters, focus plane, drift, remaining brightness |
| Optical ambiguity | Periodic interference phase | Defocus and overlapping spatial signals |
| Irreversible process | Material growth and annealing | Photobleaching |
| Fast measurement | Pyrometry or phase | Integrated photometer |
| Rich measurement | Broadband reflectance | Camera image |
| Central decision | When to stop or anneal | Where, how sharply and with how much dose to image |

The package therefore exercises a reusable design principle: instruments reveal different
projections of one evolving specimen, and every measurement has duration and consequence.

## Extension path

The next useful increments are not more synthetic knobs. They are higher-fidelity domain packages:

- multilayer transfer matrices, oblique incidence and ellipsometry for photonic stacks;
- spatial thickness maps and wafer-stage sampling for semiconductor process control;
- measured spectral response, wavelength calibration and detector nonlinearity;
- vectorial or experimentally measured point-spread functions;
- three-dimensional samples, scattering background and fluorophore state transitions;
- sample identity carried from fabrication into microscopy, spectroscopy and device testing.
