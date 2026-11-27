"""Scientific scope of the tumor-organoid treatment laboratory."""

from synthetic_lab.research import ResearchContract


def contract():
    return ResearchContract(
        domains=(
            "patient-derived tumor organoids",
            "cancer pharmacology",
            "multicellular treatment response",
        ),
        phenomena=(
            "drug diffusion through a multicellular spheroid",
            "oxygen-limited proliferation and necrosis",
            "reversible intracellular damage",
            "therapy-induced apoptosis",
            "pre-existing resistant subpopulations",
            "resistant-clone enrichment after treatment",
        ),
        questions=(
            "Which exposure suppresses viable tumor burden without merely enriching a resistant subpopulation?",
            "How do organoid size, oxygen limitation and drug penetration alter apparent treatment response?",
            "When does post-exposure recovery reverse damage rather than commit cells to apoptosis?",
            "Which measurements distinguish poor penetration from intrinsic resistance?",
        ),
        observables={
            "viable_cells": {
                "unit": "count",
                "description": "Absolute live tumor count; normalize to a matched untreated well for treatment response.",
            },
            "resistant_viable_cells": {
                "unit": "count",
                "description": "Live cells carrying the inherited resistant phenotype label.",
            },
            "viable_fraction": {
                "unit": None,
                "description": "Fraction of final tumor cells that are not in a death program.",
            },
            "apoptotic_fraction": {
                "unit": None,
                "description": "Fraction of final tumor cells in the PhysiCell apoptosis program.",
            },
            "necrotic_fraction": {
                "unit": None,
                "description": "Fraction of final tumor cells in the PhysiCell necrosis program.",
            },
            "hypoxic_viable_fraction": {
                "unit": None,
                "description": "Fraction of viable cells below the configured oxygen threshold.",
            },
            "resistant_viable_fraction": {
                "unit": None,
                "description": "Fraction of viable cells carrying the seeded resistant phenotype label.",
            },
            "equivalent_diameter": {
                "unit": "um",
                "description": "Two times the maximum radial cell extent in the simulated section.",
            },
            "mean_damage": {
                "unit": None,
                "description": "Mean PhysiCell integrity damage across tumor cells at the endpoint.",
            },
            "cell_map": {
                "unit": None,
                "description": "Cell-resolved position, oxygen, therapeutic concentration, damage, death state and resistance phenotype.",
            },
        },
        latent_variables={
            "patient_response_draw": {
                "unit": None,
                "description": "Seeded resistant fraction and sensitive/resistant damage-repair parameters shared by experiment branches.",
            },
            "oxygen_field": {
                "unit": "mmHg",
                "description": "BioFVM oxygen field coupled to cell uptake and oxygen-dependent phenotype changes.",
            },
            "therapeutic_field": {
                "unit": None,
                "description": "BioFVM treatment field supplied at the culture boundary and transported into the organoid.",
            },
        },
        interventions=("expose",),
        invariants=(
            "Forks made before exposure retain the same hidden patient-response draw and initial random seed.",
            "A session represents one assay well and accepts at most one exposure protocol.",
            "Treatment is absent before the requested start, present at the culture boundary during exposure and absent during recovery.",
            "The committed intervention is replayed unchanged whenever the external PhysiCell solver is invoked.",
        ),
        validity_conditions=(
            "A two-dimensional organoid section is adequate for the comparative question.",
            "The generic oxygen, diffusion, damage and repair parameters span the assay being studied.",
            "Boundary concentration is a suitable representation of treatment delivery in the culture well.",
        ),
        limitations=(
            "The current package is not calibrated to a named patient, tumor type, drug or assay platform.",
            "It does not represent immune, stromal or vascular compartments.",
            "The treatment mechanism is a generic diffusible damage-and-repair model rather than compound-specific pharmacology.",
            "Equivalent diameter is extracted from a two-dimensional section and is not a three-dimensional volume measurement.",
            "The solver reconstructs the assay from the committed protocol rather than serializing the internal PhysiCell state.",
        ),
        failure_conditions=(
            "The PhysiCell executable or generated configuration is unavailable.",
            "The external solver fails, times out or returns non-finite summary values.",
            "A conclusion depends on patient-specific pharmacology or cell compartments omitted by the model.",
        ),
        fidelity="hybrid",
        action_semantics={
            "expose": {
                "kind": "intervention",
                "description": "Culture, expose and recover one seeded organoid, then execute the full PhysiCell/BioFVM assay.",
            },
            "read": {
                "kind": "measurement",
                "description": "Read a selected endpoint panel from the completed assay without rerunning the solver.",
            },
            "snapshot": {
                "kind": "measurement",
                "description": "Return the final cell-resolved map for spatial analysis and external storage.",
            },
        },
        reference_methods=(
            "organoid dose-response assay",
            "live/dead fluorescence imaging",
            "hypoxia imaging",
            "single-cell phenotype profiling",
            "PhysiCell agent-based multicellular simulation",
            "BioFVM reaction-diffusion simulation",
        ),
        physical_counterpart=(
            "A tumor-organoid culture well exposed to a diffusible therapy and read by endpoint imaging"
        ),
        metadata={
            "solver_backend": "PhysiCell 1.14.2 with BioFVM",
            "upstream_project": "MathCancer/PhysiCell",
            "upstream_tag": "1.14.2",
            "geometry": "two-dimensional organoid section",
            "observation_model": "cell-resolved solver state summarized as endpoint assay measurements",
            "treatment_model": "time-windowed boundary concentration with diffusion, decay, damage, repair and apoptosis",
        },
    )
