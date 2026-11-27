"""Scientific scope for the Meep photonic-cavity laboratory."""

from synthetic_lab.research import ResearchContract


def cavity_contract():
    return ResearchContract(
        domains=(
            "photonics",
            "electromagnetic simulation",
            "photonic integrated circuits",
            "optical spectroscopy",
        ),
        phenomena=(
            "Maxwell-wave propagation",
            "photonic band gaps",
            "defect-mode resonance",
            "waveguide transmission",
            "radiative and coupling loss",
            "fabrication variation",
        ),
        questions=(
            "How do hole radius and defect spacing move a photonic-cavity resonance?",
            "Which broadband measurement best separates design error from fabrication variation?",
            "When does a coarse design cease to predict the full-wave transmission spectrum?",
            "How much spectral information is required to choose the next device geometry?",
        ),
        observables={
            "transmission_spectrum": {
                "unit": None,
                "description": (
                    "Normalized transmitted power versus wavelength from a reference "
                    "waveguide and the fabricated cavity."
                ),
            },
            "resonance_wavelength": {
                "unit": "um",
                "description": "Wavelength of the strongest central-band transmission peak.",
            },
            "peak_transmission": {
                "unit": None,
                "description": "Normalized transmission at the extracted resonance.",
            },
            "spectral_contrast": {
                "unit": None,
                "description": "Peak transmission minus the central-band transmission floor.",
            },
            "quality_factor": {
                "unit": None,
                "description": (
                    "Frequency divided by the half-prominence linewidth when resolved "
                    "by the sampled spectrum."
                ),
            },
            "field_intensity": {
                "unit": "a.u.",
                "description": (
                    "Two-dimensional electric-field intensity at the extracted resonance."
                ),
            },
        },
        latent_variables={
            "fabricated_hole_radius": {
                "unit": "um",
                "description": "Actual hole radius after fabrication variation.",
            },
            "fabricated_defect_spacing": {
                "unit": "um",
                "description": "Actual central defect spacing after fabrication variation.",
            },
            "electromagnetic_field": {
                "unit": None,
                "description": "Time-domain Maxwell field represented by Meep.",
            },
            "radiative_loss_channels": {
                "unit": None,
                "description": "Power leaving the guided transmission channel.",
            },
        },
        interventions=("fabricate",),
        invariants=(
            "A fabricated sample keeps the same hidden geometry for all later measurements.",
            "Transmission is normalized by a straight waveguide with the same cell and source.",
            "Experiment time advances by fabrication and acquisition duration, not solver wall time.",
        ),
        validity_conditions=(
            "The device is represented by a two-dimensional effective-index geometry.",
            "The dielectric is linear, isotropic, nondispersive and lossless over the source band.",
            "The spatial resolution and run duration resolve the spectral feature being interpreted.",
        ),
        limitations=(
            "The model omits three-dimensional slab leakage and material dispersion.",
            "Fabrication variation is represented by scalar radius and defect-spacing offsets.",
            "The spectrometer adds independent Gaussian power noise without wavelength drift.",
            "The package is not calibrated to a named fabricated device.",
        ),
        failure_conditions=(
            "The resonance lies outside the configured source band.",
            "The sampled spectrum is too coarse to resolve a linewidth.",
            "The time-domain field has not decayed enough for a stable flux spectrum.",
        ),
        fidelity="hybrid",
        action_semantics={
            "design": {
                "kind": "configure",
                "description": "Set the commanded hole radius and defect spacing before fabrication.",
            },
            "fabricate": {
                "kind": "intervention",
                "description": "Create one persistent sample with hidden geometric variation.",
            },
            "measure": {
                "kind": "measurement",
                "description": (
                    "Acquire a normalized transmission spectrum, resonance summary or "
                    "resonant field map."
                ),
            },
        },
        reference_methods=(
            "finite-difference time-domain electromagnetics",
            "broadband flux normalization",
            "photonic-crystal defect-mode spectroscopy",
            "effective-index device modelling",
        ),
        physical_counterpart=(
            "A fabricated photonic-crystal waveguide cavity measured with a broadband "
            "source and transmission spectrometer"
        ),
        metadata={
            "solver_backend": "Meep",
            "solver_equations": "time-domain Maxwell equations",
            "geometry": "two-dimensional holey dielectric waveguide",
            "upstream_project": "NanoComp/meep",
            "normalization": "straight-waveguide reference",
        },
    )
