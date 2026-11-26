"""Scientific scope and observable quantities of the fed-batch laboratory."""

from synthetic_lab.research import ResearchContract

RESEARCH = ResearchContract(
    domains=(
        "bioprocess engineering",
        "synthetic biology",
        "biomanufacturing",
        "spectroscopy",
    ),
    phenomena=(
        "fed-batch growth",
        "substrate limitation",
        "oxygen transfer",
        "optical induction",
        "reporter dynamics",
        "metabolic burden",
        "Raman mixture spectra",
    ),
    questions=(
        (
            "When should induction begin to maximize product-sensitive Raman signal "
            "without sacrificing excessive biomass?"
        ),
        "How should feed and aeration be coordinated as oxygen demand rises?",
        (
            "Which combination of OD, fluorescence, Raman and oxygen measurements "
            "best separates culture states?"
        ),
        (
            "Can an induction schedule learned on one culture remain useful under "
            "batch-to-batch kinetic variation?"
        ),
    ),
    observables={
        "od600": {
            "unit": None,
            "description": "Saturating optical-density estimate of biomass concentration.",
        },
        "reporter_fluorescence": {
            "unit": "count/s",
            "description": ("Reporter fluorescence proportional to biomass and expression state."),
        },
        "raman_intensity": {
            "unit": "a.u.",
            "description": ("Five-channel Raman spectrum mixing substrate, product and biomass."),
        },
        "dissolved_oxygen": {
            "unit": "%",
            "description": "Optical oxygen-sensor reading as percent air saturation.",
        },
    },
    latent_variables={
        "volume": {
            "unit": "L",
            "description": "Liquid volume after substrate feeding.",
        },
        "temperature": {
            "unit": "K",
            "description": "Actual culture temperature with finite thermal response.",
        },
        "oxygen": {
            "unit": "%",
            "description": "Dissolved oxygen before optical sensor noise.",
        },
        "biomass_mass": {
            "unit": "g",
            "description": "Total viable biomass in the vessel.",
        },
        "substrate_mass": {
            "unit": "g",
            "description": "Remaining carbon-source mass.",
        },
        "product_mass": {
            "unit": "g",
            "description": "Accumulated target-product mass.",
        },
        "reporter_state": {
            "unit": None,
            "description": "Finite-response optical reporter expression state.",
        },
        "burden": {
            "unit": None,
            "description": "Reversible growth burden induced by production conditions.",
        },
    },
    interventions=("feed", "aeration", "temperature", "induction"),
    invariants=(
        "Culture volume never exceeds the configured working volume.",
        "Biomass, substrate and product masses remain nonnegative.",
        (
            "Substrate remaining plus cumulative substrate use equals initial "
            "substrate plus supplied substrate."
        ),
    ),
    validity_conditions=(
        "Well-mixed fed-batch vessel with no liquid outflow.",
        "One limiting carbon source and one lumped dissolved-oxygen state.",
        (
            "Optical signals follow fixed response coefficients over the represented "
            "concentration range."
        ),
    ),
    limitations=(
        "Oxygen uptake is growth-associated; maintenance and product-specific oxygen costs are omitted.",
        "Feed is deoxygenated; optical readings sample the state at acquisition completion.",
        (
            "No population heterogeneity, morphology, pH, acetate overflow or "
            "explicit gas-phase dynamics."
        ),
        ("Reporter and Raman coefficients are generic rather than strain-specific measurements."),
        (
            "The model represents hours-scale process decisions rather than "
            "intracellular molecular kinetics."
        ),
    ),
    failure_conditions=(
        "OD response compresses at high biomass and cannot identify biomass alone.",
        "Reporter fluorescence confounds biomass amount with expression level.",
        (
            "Raman bands overlap and require multiple channels to separate "
            "substrate, product and biomass contributions."
        ),
    ),
    fidelity="reduced-order",
    action_semantics={
        "feed": {
            "kind": "control",
            "description": "Set concentrated substrate-feed rate.",
        },
        "aeration": {
            "kind": "control",
            "description": "Set the oxygen-transfer coefficient.",
        },
        "temperature": {
            "kind": "control",
            "description": "Set the vessel temperature target.",
        },
        "induction": {
            "kind": "intervention",
            "description": "Set normalized optical induction intensity.",
        },
        "read": {
            "kind": "measurement",
            "description": "Acquire one optical process measurement.",
        },
        "wait": {
            "kind": "wait",
            "description": "Advance culture dynamics without acquiring a measurement.",
        },
    },
    reference_methods=(
        "Monod kinetic fitting",
        "oxygen-transfer balance",
        "multivariate Raman regression",
        "reporter-based induction timing",
    ),
    physical_counterpart=(
        "A stirred fed-batch bioreactor with OD, fluorescence, Raman and optical oxygen sensing"
    ),
)
